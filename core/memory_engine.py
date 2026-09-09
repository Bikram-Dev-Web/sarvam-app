"""
Core Memory Engine for Kivi:
Manages phonetic memory persistence, evidence accumulation, contextual co-occurrence,
reinforcement, decay, and candidate retrieval.
"""

import re
import json
import difflib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from core.models import DBMemory, DBEvidenceLog, MemoryCreate
from core.phonetics import get_phonetic_keys, compute_phonetic_similarity, normalize_indian_phonetics


STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does",
    "did", "can", "could", "will", "would", "should", "it", "this", "that", "these",
    "those", "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "their", "our", "its", "please", "just", "so", "as"
}

# ==========================================
# Composite decision-score policy constants
#
# These three numbers are product decisions, not implementation details, and
# they are validated empirically rather than picked by feel - see
# eval/ablation.py and ablation_report.md for the sweep that justifies them.
# ==========================================
DEFAULT_COMPOSITE_WEIGHTS: Tuple[float, float, float] = (0.45, 0.30, 0.25)  # phonetic, context, confidence
DEFAULT_INTERVENTION_THRESHOLD = 0.65
MIN_PHONETIC_SIMILARITY = 0.60  # below this, a span is not even considered a candidate

# Evidence-decay policy for when a memory turns out to be wrong (see
# learn_negative_correction). A single false positive should cost more than
# a single true positive earns, because an unwanted substitution is worse
# for the user than a missed one - see README "Decisions & Validation".
NEGATIVE_EVIDENCE_PENALTY = 0.15
MIN_ACTIVE_CONFIDENCE = 0.20  # below this, a memory is deactivated (soft-removed), not deleted


def compute_composite_score(
    phonetic_sim: float,
    context_affinity: float,
    evidence_confidence: float,
    weights: Tuple[float, float, float] = DEFAULT_COMPOSITE_WEIGHTS
) -> Tuple[float, str]:
    """
    Pure function combining the three decision factors into one gating score.
    Kept separate from find_best_candidate so eval/ablation.py can recompute
    scores under alternative weightings without re-running the whole pipeline,
    and so there is exactly one place this formula is implemented.

    A negative context_affinity is an absolute veto (matched negative-context
    trigger word) regardless of weighting - false interventions are treated
    as categorically worse than missed ones, not just numerically worse.
    """
    if context_affinity < 0:
        return 0.0, "vetoed_by_negative_context"
    w_phonetic, w_context, w_confidence = weights
    composite = (
        w_phonetic * phonetic_sim +
        w_context * context_affinity +
        w_confidence * evidence_confidence
    )
    return round(max(0.0, min(1.0, composite)), 4), "weighted_composite"


def extract_context_keywords(text: str, exclude_terms: Optional[List[str]] = None) -> List[str]:
    """Extracts non-stopword normalized contextual tokens from text."""
    exclude = set(w.lower() for w in (exclude_terms or []))
    words = re.findall(r'\b[a-zA-Z0-9_\-]{2,}\b', text.lower())
    keywords = [w for w in words if w not in STOPWORDS and w not in exclude]
    return list(dict.fromkeys(keywords))  # preserve order, unique


class MemoryEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_or_update_memory(
        self,
        canonical_term: str,
        category: str = "general",
        aliases: Optional[List[str]] = None,
        context_triggers: Optional[List[str]] = None,
        negative_contexts: Optional[List[str]] = None,
        confidence_score: float = 0.85,
        source_type: str = "manual_dictionary",
        notes: Optional[str] = None
    ) -> DBMemory:
        """Adds a new term to memory or reinforces an existing one."""
        canonical_clean = canonical_term.strip()
        phonetic_data = get_phonetic_keys(canonical_clean)

        existing = self.db.query(DBMemory).filter(
            DBMemory.canonical_term.ilike(canonical_clean)
        ).first()

        aliases = aliases or []
        context_triggers = [t.lower() for t in (context_triggers or [])]
        negative_contexts = [t.lower() for t in (negative_contexts or [])]

        if existing:
            # Reinforce existing memory
            existing_aliases = json.loads(existing.aliases_json or "[]")
            for a in aliases:
                if a.lower() not in [x.lower() for x in existing_aliases]:
                    existing_aliases.append(a)
            existing.aliases_json = json.dumps(existing_aliases)

            existing_triggers = json.loads(existing.context_triggers_json or "[]")
            for ct in context_triggers:
                if ct not in existing_triggers:
                    existing_triggers.append(ct)
            existing.context_triggers_json = json.dumps(existing_triggers)

            existing_negatives = json.loads(existing.negative_contexts_json or "[]")
            for nc in negative_contexts:
                if nc not in existing_negatives:
                    existing_negatives.append(nc)
            existing.negative_contexts_json = json.dumps(existing_negatives)

            # Asymptotic confidence boost on reinforcement
            existing.reinforcement_count += 1
            existing.confidence_score = min(0.99, existing.confidence_score + (1.0 - existing.confidence_score) * 0.25)
            existing.last_reinforced_at = datetime.now(timezone.utc)
            existing.is_active = True
            if notes:
                existing.notes = notes
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create fresh memory entry
            memory = DBMemory(
                canonical_term=canonical_clean,
                category=category,
                phonetic_code=phonetic_data["metaphone"],
                normalized_phonetic=phonetic_data["normalized"],
                soundex_code=phonetic_data["soundex"],
                aliases_json=json.dumps(aliases),
                confidence_score=max(0.1, min(1.0, confidence_score)),
                reinforcement_count=1,
                last_reinforced_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                source_type=source_type,
                context_triggers_json=json.dumps(context_triggers),
                negative_contexts_json=json.dumps(negative_contexts),
                is_active=True,
                notes=notes
            )
            self.db.add(memory)
            self.db.commit()
            self.db.refresh(memory)
            return memory

    def learn_from_correction(
        self,
        original_text: str,
        corrected_text: str,
        source: str = "user_correction"
    ) -> List[Dict[str, Any]]:
        """
        Extracts token-level differences between original transcript and user's correction.
        Learns the new phonetic mappings and extracts context triggers automatically.
        """
        orig_words = original_text.split()
        corr_words = corrected_text.split()

        matcher = difflib.SequenceMatcher(None, orig_words, corr_words)
        learned_entries = []
        delta_map = {}

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                orig_span = " ".join(orig_words[i1:i2]).strip('.,!?:;"()')
                corr_span = " ".join(corr_words[j1:j2]).strip('.,!?:;"()')

                # Canonical casing is part of a personal term's preferred form.
                # Treat mid-sentence `siobhan` -> `Siobhan` and `pytorch` ->
                # `PyTorch` as real corrections. Ignore a case-only change at a
                # sentence boundary, where capitalization is formatting rather
                # than evidence of a personal term (`we` -> `We`).
                case_only_change = orig_span.lower() == corr_span.lower()
                at_sentence_boundary = i1 == 0 or bool(
                    re.search(r'[.!?]["\']?$', orig_words[i1 - 1])
                )
                should_learn = (
                    orig_span
                    and corr_span
                    and orig_span != corr_span
                    and not (case_only_change and at_sentence_boundary)
                )
                if should_learn:
                    delta_map[orig_span] = corr_span

                    # Context triggers = the rest of the sentence, MINUS every word
                    # that belongs to either the wrong span or the corrected span
                    # itself. Without this, a multi-word entity's own words (e.g.
                    # "pie", "torch" from "pie torch" -> "PyTorch") would leak into
                    # its own trigger list as if they were independent contextual
                    # evidence, which then also defeats any negative-context veto
                    # keyed on those same words (a sentence about baking a literal
                    # pie would satisfy the positive trigger it's supposed to be
                    # vetoed by). Discovered while building the holdout eval suite.
                    span_own_words = orig_span.lower().split() + corr_span.lower().split()
                    span_context = extract_context_keywords(corrected_text, exclude_terms=span_own_words)

                    mem = self.create_or_update_memory(
                        canonical_term=corr_span,
                        category="learned_entity",
                        aliases=[orig_span],
                        context_triggers=span_context,
                        confidence_score=0.88,
                        source_type="explicit_correction",
                        notes=f"Learned from user correction: '{orig_span}' -> '{corr_span}'"
                    )
                    
                    # Log evidence
                    log = DBEvidenceLog(
                        memory_id=mem.id,
                        source=source,
                        original_text=original_text,
                        corrected_text=corrected_text,
                        delta_terms_json=json.dumps({orig_span: corr_span}),
                        created_at=datetime.now(timezone.utc)
                    )
                    self.db.add(log)
                    learned_entries.append({
                        "original_span": orig_span,
                        "canonical_term": corr_span,
                        "memory_id": mem.id,
                        "confidence": mem.confidence_score,
                        "context_triggers": span_context
                    })

        self.db.commit()
        return learned_entries

    def learn_negative_correction(
        self,
        memory_aware_text: str,
        user_reverted_text: str,
        source: str = "negative_correction"
    ) -> List[Dict[str, Any]]:
        """
        The mirror image of learn_from_correction: the user reverted a substitution
        Kivi made, i.e. Kivi's memory-aware output contained a term the user did NOT
        want here. This is the system's only source of ground truth that a memory's
        evidence is *wrong in this context*, so it must be able to act on it, not
        just log it.

        For each span Kivi changed that the user has now changed back, we do not
        weaken or delete the memory globally (the substitution may still be correct
        in other contexts - e.g. "Kivi" is still right when the sentence is about
        the speech product). Instead we:
          1. record the sentence's context words as new negative_contexts for that
             memory (learning the specific situation where it must stay silent);
          2. apply a confidence penalty that is larger than the reinforcement gain
             from a single correct correction, because an unwanted substitution is a
             worse product outcome than a missed one (see README "Decisions &
             Validation" for the empirical case);
          3. if repeated false positives drop confidence below
             MIN_ACTIVE_CONFIDENCE, deactivate the memory (is_active=False) rather
             than deleting it outright - it stays inspectable in the memory store
             but stops being offered as a candidate, and can be reinforced back to
             active status by a future correct correction.

        Returns one entry per span that was actually attributed to a known memory;
        spans that don't match any memory are ignored (nothing to penalize).
        """
        wrong_words = memory_aware_text.split()
        right_words = user_reverted_text.split()

        matcher = difflib.SequenceMatcher(None, wrong_words, right_words)
        penalized_entries: List[Dict[str, Any]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'replace':
                continue

            wrong_span = " ".join(wrong_words[i1:i2]).strip('.,!?:;"()')
            right_span = " ".join(right_words[j1:j2]).strip('.,!?:;"()')
            if not wrong_span or wrong_span.lower() == right_span.lower():
                continue

            wrong_span_clean = wrong_span.strip('.,!?:;"()').lower()

            # Identify which memory produced this span: either its canonical term
            # or one of its recorded aliases.
            offending_memory = None
            for mem in self.get_all_memories(active_only=True):
                if mem.canonical_term.strip().lower() == wrong_span_clean:
                    offending_memory = mem
                    break
                aliases = json.loads(mem.aliases_json or "[]")
                if any(a.lower() == wrong_span_clean for a in aliases):
                    offending_memory = mem
                    break

            if offending_memory is None:
                # Nothing in memory claims this span - can't attribute blame, skip.
                continue

            # Same fix as learn_from_correction: exclude every word belonging to
            # either span (not just full-string equality) so the entity's own
            # name never ends up vetoing itself in legitimate contexts.
            span_own_words = wrong_span.lower().split() + right_span.lower().split()

            # Also exclude this memory's OWN positive triggers. A revert proves
            # the substitution was wrong *here*, but the sentence proving it is
            # still a sentence about the entity's subject matter - a reverted
            # "Temporal" sits in a sentence that legitimately says "workflow"
            # and "retry". Recording those as negative contexts would veto the
            # memory in exactly the situations it was taught for, and since a
            # matched negative context is an absolute veto, a single revert
            # would silence the entity permanently. Phrase triggers contribute
            # their component words too ("deep learning" -> deep, learning),
            # because negative contexts are matched per word as well as per
            # phrase. What is left after this filter is what actually
            # distinguishes the wrong context from the right one.
            positive_triggers = json.loads(offending_memory.context_triggers_json or "[]")
            trigger_words = {t.lower() for t in positive_triggers}
            trigger_words.update(w for t in positive_triggers for w in t.lower().split())

            span_context = [
                c for c in extract_context_keywords(user_reverted_text, exclude_terms=span_own_words)
                if c.lower() not in trigger_words
            ]
            existing_negatives = json.loads(offending_memory.negative_contexts_json or "[]")
            added_negatives = []
            for c in span_context:
                if c not in existing_negatives:
                    existing_negatives.append(c)
                    added_negatives.append(c)
            offending_memory.negative_contexts_json = json.dumps(existing_negatives)

            offending_memory.confidence_score = max(0.0, offending_memory.confidence_score - NEGATIVE_EVIDENCE_PENALTY)
            deactivated = False
            if offending_memory.confidence_score < MIN_ACTIVE_CONFIDENCE:
                offending_memory.is_active = False
                deactivated = True

            note_suffix = f"Reverted in context ({', '.join(span_context) or 'no distinguishing words'}); confidence -{NEGATIVE_EVIDENCE_PENALTY}"
            offending_memory.notes = f"{(offending_memory.notes or '').strip()} | {note_suffix}".strip(" |")

            log = DBEvidenceLog(
                memory_id=offending_memory.id,
                source=source,
                original_text=memory_aware_text,
                corrected_text=user_reverted_text,
                delta_terms_json=json.dumps({wrong_span: right_span}),
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(log)

            penalized_entries.append({
                "wrong_span": wrong_span,
                "reverted_to": right_span,
                "memory_id": offending_memory.id,
                "canonical_term": offending_memory.canonical_term,
                "new_confidence": offending_memory.confidence_score,
                "added_negative_contexts": added_negatives,
                "deactivated": deactivated
            })

        self.db.commit()
        return penalized_entries

    def get_all_memories(self, active_only: bool = True) -> List[DBMemory]:
        """Returns all memory records."""
        query = self.db.query(DBMemory)
        if active_only:
            query = query.filter(DBMemory.is_active == True)
        return query.order_by(DBMemory.confidence_score.desc()).all()

    def get_memory_by_id(self, memory_id: int) -> Optional[DBMemory]:
        return self.db.query(DBMemory).filter(DBMemory.id == memory_id).first()

    def delete_memory(self, memory_id: int) -> bool:
        mem = self.get_memory_by_id(memory_id)
        if mem:
            self.db.delete(mem)
            self.db.commit()
            return True
        return False

    def compute_context_affinity(
        self,
        memory: DBMemory,
        sentence_context_tokens: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculates how strongly the sentence context matches the memory's positive triggers vs negative contexts.
        Returns:
            (affinity_score, matched_positive_triggers, matched_negative_triggers)
            affinity_score ranges from -1.0 (strongly forbidden) to +1.0 (strongly reinforced).
        """
        positive_triggers = json.loads(memory.context_triggers_json or "[]")
        negative_contexts = json.loads(memory.negative_contexts_json or "[]")

        normalized_tokens = [t.lower() for t in sentence_context_tokens]
        context_units = set(normalized_tokens)

        # Context configuration may contain phrases (`deep learning`,
        # `new zealand`, `apple pie`). Build only the n-grams needed by the
        # configured triggers so phrase rules work without bloating the normal
        # keyword representation used by the learning path.
        configured_contexts = positive_triggers + negative_contexts
        max_context_words = max(
            (len(context.split()) for context in configured_contexts),
            default=1,
        )
        for size in range(2, max_context_words + 1):
            context_units.update(
                " ".join(normalized_tokens[start:start + size])
                for start in range(0, len(normalized_tokens) - size + 1)
            )

        matched_pos = [p for p in positive_triggers if p.lower() in context_units]
        matched_neg = [n for n in negative_contexts if n.lower() in context_units]

        # Negative triggers are absolute vetoes / strong suppression
        if matched_neg:
            return -1.0, matched_pos, matched_neg

        if not positive_triggers:
            # If no context triggers configured, neutral default
            return 0.1, matched_pos, matched_neg

        pos_ratio = len(matched_pos) / max(len(positive_triggers), 1)
        # Scale to 0.0 -> 1.0
        affinity = min(1.0, 0.2 + (pos_ratio * 0.8)) if matched_pos else 0.0
        return round(affinity, 3), matched_pos, matched_neg

    def find_best_candidate(
        self,
        word_span: str,
        sentence_context_tokens: List[str],
        memories: Optional[List[DBMemory]] = None,
        weights: Tuple[float, float, float] = DEFAULT_COMPOSITE_WEIGHTS
    ) -> Optional[Tuple[DBMemory, float, Dict[str, Any]]]:
        """
        Searches active memories to find the best phonetic and contextual match for a word span.

        `memories` lets a caller that is scanning many spans in the same transcript
        (TranscriptProcessor.process) fetch the active memory set once per request
        instead of once per token - see README "Decisions & Validation" for why this
        matters for latency. Direct callers (tests, the API, the REPL) can omit it and
        it will be fetched internally, exactly as before.

        `weights` lets eval/ablation.py recompute decisions under alternative
        phonetic/context/confidence weightings without duplicating this method.
        """
        if memories is None:
            memories = self.get_all_memories(active_only=True)
        if not memories:
            return None

        span_original = word_span.strip()
        span_clean = span_original.lower()
        span_word_count = len(span_clean.split())
        best_candidate: Optional[DBMemory] = None
        highest_composite_score = 0.0
        # Rank by final score first, then phonetic strength and evidence. Keeping
        # a zero-scored, negative-context-vetoed candidate is intentional: the
        # processor needs it to emit an inspectable SUPPRESSED trace explaining
        # why it did nothing. Any viable positive-scored candidate still wins.
        best_candidate_rank: Tuple[float, float, float] = (-1.0, -1.0, -1.0)
        best_details: Dict[str, Any] = {}

        for mem in memories:
            target_original = mem.canonical_term.strip()
            target_clean = target_original.lower()
            target_word_count = len(target_clean.split())
            aliases = json.loads(mem.aliases_json or "[]")
            is_known_alias = any(a.lower() == span_clean for a in aliases)

            # Rule: If candidate span has multiple words (e.g. 2 words),
            # it should only match if the memory itself is multi-word OR if span is an explicit alias.
            if span_word_count > 1 and target_word_count == 1 and not is_known_alias:
                continue

            # 1. Skip only a genuinely exact canonical match. A case-only
            # difference is still useful personalization (`siobhan` ->
            # `Siobhan`, `pytorch` -> `PyTorch`) and should be evaluated.
            if target_original == span_original:
                continue

            # 2. Phonetic similarity
            phonetic_sim, sim_details = compute_phonetic_similarity(mem.canonical_term, span_clean)
            
            # If known alias, give strong phonetic base
            if is_known_alias:
                phonetic_sim = max(phonetic_sim, 0.95)

            # Skip if phonetic similarity is too weak
            if phonetic_sim < MIN_PHONETIC_SIMILARITY:
                continue

            # 3. Contextual affinity
            context_affinity, pos_matched, neg_matched = self.compute_context_affinity(mem, sentence_context_tokens)

            # 4. Composite decision score (single source of truth: compute_composite_score)
            composite, _score_kind = compute_composite_score(
                phonetic_sim, context_affinity, mem.confidence_score, weights
            )
            if context_affinity < 0:
                decision_reason = f"Suppressed: Negative context detected ({', '.join(neg_matched)})"
            else:
                decision_reason = "High phonetic & contextual agreement"

            candidate_rank = (composite, phonetic_sim, mem.confidence_score)
            if candidate_rank > best_candidate_rank:
                best_candidate_rank = candidate_rank
                highest_composite_score = composite
                best_candidate = mem
                best_details = {
                    "phonetic_similarity": phonetic_sim,
                    "context_score": context_affinity,
                    "evidence_confidence": mem.confidence_score,
                    "composite_score": round(composite, 4),
                    "pos_matched_triggers": pos_matched,
                    "neg_matched_triggers": neg_matched,
                    "is_known_alias": is_known_alias,
                    "reason": decision_reason,
                    "phonetic_details": sim_details
                }

        if best_candidate:
            return best_candidate, highest_composite_score, best_details
        return None
