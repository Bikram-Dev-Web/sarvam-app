"""
Transcript Processor:
Executes the three-tier transcript transformation pipeline:
1. ASR Output -> 2. Formatted Output -> 3. Memory-Aware Output
With full inspectability, decision tracing, token span replacement, and latency measurement.
"""

import time
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from core.models import (
    TranscriptProcessRequest,
    TranscriptProcessResponse,
    DecisionTrace
)
from core.memory_engine import MemoryEngine, extract_context_keywords


def format_raw_asr(asr_text: str) -> str:
    """
    Standard formatting module simulating LLM-cleaned punctuation & capitalization
    without personal word-level memory.
    """
    if not asr_text:
        return ""
    text = asr_text.strip()
    
    # Capitalize first letter
    text = text[0].upper() + text[1:] if len(text) > 0 else ""
    
    # Add period if no ending punctuation
    if text and text[-1] not in ".?!":
        text += "."
        
    # Capitalize after sentence terminators
    def cap_sent(m):
        return m.group(1) + m.group(2).upper()
    text = re.sub(r'([.?!]\s+)([a-z])', cap_sent, text)
    
    return text


def preserve_case_and_punctuation(original_token: str, replacement_token: str) -> str:
    """
    Preserves surrounding punctuation and appropriate casing style from original token.
    """
    leading_punct = re.match(r'^[^\w\s]+', original_token)
    trailing_punct = re.search(r'[^\w\s]+$', original_token)
    
    lead = leading_punct.group(0) if leading_punct else ""
    trail = trailing_punct.group(0) if trailing_punct else ""
    
    core_orig = original_token[len(lead):len(original_token)-len(trail)] if trail else original_token[len(lead):]
    
    rep = replacement_token
    # If original was ALL CAPS and longer than 1 char
    if core_orig.isupper() and len(core_orig) > 1:
        rep = rep.upper()
    # If original was Title Case
    elif core_orig and core_orig[0].isupper() and not rep[0].isupper():
        rep = rep[0].upper() + rep[1:]
        
    return f"{lead}{rep}{trail}"


class TranscriptProcessor:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.engine = MemoryEngine(db_session)

    def process(self, request: TranscriptProcessRequest) -> TranscriptProcessResponse:
        start_time = time.perf_counter()

        asr_text = request.asr_output.strip()
        formatted_text = request.formatted_output.strip() if request.formatted_output else format_raw_asr(asr_text)
        confidence_threshold = request.confidence_threshold

        # Extract sentence-wide context keywords from both ASR and formatted text
        context_tokens = extract_context_keywords(f"{asr_text} {formatted_text}")

        # Fetch the active memory set once per transcript instead of once per
        # token/n-gram. find_best_candidate was previously re-querying the database
        # for every span it evaluated (up to ~2 DB round trips per token), which
        # dominated latency on longer transcripts without changing any decision -
        # memories don't change mid-request. See README "Decisions & Validation".
        active_memories = self.engine.get_all_memories(active_only=True)

        tokens = formatted_text.split()
        modified_tokens = list(tokens)
        traces: List[DecisionTrace] = []
        interventions_count = 0
        suppressed_count = 0

        # Scan from the longest configured canonical term/alias down to a single
        # token. The span limit is data-driven, so adding a three-word product name
        # does not require changing processor code.
        max_configured_span = 1
        for memory in active_memories:
            configured_terms = [memory.canonical_term] + json.loads(memory.aliases_json or "[]")
            max_configured_span = max(
                max_configured_span,
                *(len(term.split()) for term in configured_terms if term.strip()),
            )

        n = len(tokens)
        idx = 0

        while idx < n:
            intervened_span_size = 0

            for span_size in range(min(max_configured_span, n - idx), 0, -1):
                original_span = " ".join(tokens[idx:idx + span_size])
                clean_span = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', original_span)
                if not clean_span:
                    continue

                candidate_res = self.engine.find_best_candidate(
                    clean_span,
                    context_tokens,
                    memories=active_memories,
                )
                if not candidate_res:
                    continue

                mem, comp_score, details = candidate_res
                if comp_score >= confidence_threshold:
                    modified_tokens[idx] = preserve_case_and_punctuation(
                        original_span, mem.canonical_term
                    )
                    for consumed_idx in range(idx + 1, idx + span_size):
                        modified_tokens[consumed_idx] = ""
                    interventions_count += 1
                    intervened_span_size = span_size
                    traces.append(DecisionTrace(
                        original_span=original_span,
                        start_pos=idx,
                        end_pos=idx + span_size - 1,
                        matched_memory_term=mem.canonical_term,
                        memory_id=mem.id,
                        phonetic_similarity=details["phonetic_similarity"],
                        context_score=details["context_score"],
                        evidence_confidence=details["evidence_confidence"],
                        composite_decision_score=details["composite_score"],
                        threshold=confidence_threshold,
                        decision="INTERVENED",
                        reason=(
                            f"Replaced '{clean_span}' with personal term '{mem.canonical_term}'. "
                            f"Score {details['composite_score']} >= {confidence_threshold}."
                        ),
                        details=details,
                    ))
                    break

                suppressed_count += 1
                traces.append(DecisionTrace(
                    original_span=original_span,
                    start_pos=idx,
                    end_pos=idx + span_size - 1,
                    matched_memory_term=mem.canonical_term,
                    memory_id=mem.id,
                    phonetic_similarity=details["phonetic_similarity"],
                    context_score=details["context_score"],
                    evidence_confidence=details["evidence_confidence"],
                    composite_decision_score=details["composite_score"],
                    threshold=confidence_threshold,
                    decision="SUPPRESSED",
                    reason=(
                        f"Candidate {mem.canonical_term} was deliberately suppressed: "
                        f"{details['reason']} (score {details['composite_score']} "
                        f"vs threshold {confidence_threshold})."
                    ),
                    details=details,
                ))

            idx += intervened_span_size or 1

        # Reconstruct memory-aware output
        memory_aware_tokens = [t for t in modified_tokens if t != ""]
        memory_aware_output = " ".join(memory_aware_tokens)

        # Fix any punctuation spacing artifacts
        memory_aware_output = re.sub(r'\s+([.,!?:;])', r'\1', memory_aware_output)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return TranscriptProcessResponse(
            asr_output=asr_text,
            formatted_output=formatted_text,
            memory_aware_output=memory_aware_output,
            interventions_count=interventions_count,
            suppressed_count=suppressed_count,
            processing_latency_ms=latency_ms,
            traces=traces
        )
