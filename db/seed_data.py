"""
Seed data generator: Populates initial realistic memories, context associations,
negative space suppressions, and baseline evidence logs.
"""

from sqlalchemy.orm import Session
from core.models import DBMemory, DBEvidenceLog
from core.memory_engine import MemoryEngine
from db.database import SessionLocal, init_db, reset_db


SEED_ENTRIES = [
    {
        "canonical_term": "Aaditya",
        "category": "person",
        "aliases": ["Aditya", "Adithya", "Aadithya"],
        "context_triggers": ["review", "sarvam", "service", "pr", "meeting", "team", "code", "assigned"],
        "negative_contexts": [],
        "confidence_score": 0.95,
        "source_type": "explicit_correction",
        "notes": "Co-founder / Tech Lead name spelling preference"
    },
    {
        "canonical_term": "Kivi",
        "category": "product",
        "aliases": ["Kiwi", "Keevi", "Kivee"],
        "context_triggers": ["sarvam", "service", "speech", "transcribe", "voice", "model", "app", "dictionary", "dictation"],
        "negative_contexts": ["fruit", "eat", "slice", "salad", "smoothie", "supermarket", "grocery", "bird", "new zealand"],
        "confidence_score": 0.98,
        "source_type": "explicit_correction",
        "notes": "Sarvam's speech product name. Never substitute when discussing the fruit or bird."
    },
    {
        "canonical_term": "Sarvam",
        "category": "organization",
        "aliases": ["Serve hum", "Sarwam", "Sarvamm"],
        "context_triggers": ["ai", "kivi", "indic", "models", "company", "bangalore", "service"],
        "negative_contexts": [],
        "confidence_score": 0.99,
        "source_type": "manual_dictionary",
        "notes": "Company name"
    },
    {
        "canonical_term": "Deeksha",
        "category": "person",
        "aliases": ["Diksha", "Deekshya"],
        "context_triggers": ["product", "roadmap", "sync", "jira", "call", "designer"],
        "negative_contexts": ["ceremony", "initiation", "spiritual"],
        "confidence_score": 0.92,
        "source_type": "explicit_correction",
        "notes": "Product Manager name"
    },
    {
        "canonical_term": "PyTorch",
        "category": "jargon",
        "aliases": ["pie torch", "py torch", "pie torch"],
        "context_triggers": ["training", "cuda", "gpu", "model", "tensor", "backprop", "deep learning", "framework"],
        "negative_contexts": ["baking", "oven", "apple pie", "recipe", "flashlight", "fire torch"],
        "confidence_score": 0.94,
        "source_type": "manual_dictionary",
        "notes": "ML Framework. Suppress in culinary or campfire contexts."
    },
    {
        "canonical_term": "Supabase",
        "category": "product",
        "aliases": ["super base", "superbase"],
        "context_triggers": ["database", "postgres", "auth", "backend", "table", "sql", "migration"],
        "negative_contexts": ["baseball", "superhero", "fortress", "military base"],
        "confidence_score": 0.90,
        "source_type": "manual_dictionary",
        "notes": "Backend DB service"
    },
    {
        "canonical_term": "Kubernetes",
        "category": "jargon",
        "aliases": ["coober nettees", "k eights", "k8s"],
        "context_triggers": ["cluster", "pod", "nodes", "deploy", "docker", "helm", "devops", "cloud"],
        "negative_contexts": [],
        "confidence_score": 0.93,
        "source_type": "manual_dictionary",
        "notes": "Container orchestration system"
    },
    {
        "canonical_term": "Neil",
        "category": "person",
        "aliases": ["kneel"],
        "context_triggers": ["meeting", "call", "slack", "manager", "engineer", "sent", "talked"],
        "negative_contexts": ["down", "floor", "prayer", "leg", "knee", "ground", "stand"],
        "confidence_score": 0.90,
        "source_type": "explicit_correction",
        "notes": "Team member name. Suppress when user means the physical action of kneeling."
    }
]


def seed_database(db: Session):
    """Populates initial seed data if table is empty or on reset."""
    engine = MemoryEngine(db)
    for entry in SEED_ENTRIES:
        engine.create_or_update_memory(
            canonical_term=entry["canonical_term"],
            category=entry["category"],
            aliases=entry["aliases"],
            context_triggers=entry["context_triggers"],
            negative_contexts=entry["negative_contexts"],
            confidence_score=entry["confidence_score"],
            source_type=entry["source_type"],
            notes=entry["notes"]
        )
    db.commit()


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    seed_database(db)
    print("Database seeded successfully with initial memories.")
