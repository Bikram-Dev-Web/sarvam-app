"""Create the initial Kivi memory schema.

Revision ID: 0001_initial_schema
Revises: None
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("canonical_term", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("phonetic_code", sa.String(length=255), nullable=False),
        sa.Column("normalized_phonetic", sa.String(length=255), nullable=False),
        sa.Column("soundex_code", sa.String(length=64), nullable=True),
        sa.Column("aliases_json", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("reinforcement_count", sa.Integer(), nullable=True),
        sa.Column("last_reinforced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("context_triggers_json", sa.Text(), nullable=True),
        sa.Column("negative_contexts_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memories_category", "memories", ["category"])
    op.create_index("ix_memories_canonical_term", "memories", ["canonical_term"], unique=True)
    op.create_index("ix_memories_id", "memories", ["id"])
    op.create_index("ix_memories_normalized_phonetic", "memories", ["normalized_phonetic"])
    op.create_index("ix_memories_phonetic_code", "memories", ["phonetic_code"])

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("total_cases", sa.Integer(), nullable=True),
        sa.Column("passed_cases", sa.Integer(), nullable=True),
        sa.Column("failed_cases", sa.Integer(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("false_intervention_rate", sa.Float(), nullable=True),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("results_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_runs_id", "eval_runs", ["id"])

    op.create_table(
        "evidence_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("memory_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text(), nullable=True),
        sa.Column("delta_terms_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_logs_id", "evidence_logs", ["id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_logs_id", table_name="evidence_logs")
    op.drop_table("evidence_logs")
    op.drop_index("ix_eval_runs_id", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_index("ix_memories_phonetic_code", table_name="memories")
    op.drop_index("ix_memories_normalized_phonetic", table_name="memories")
    op.drop_index("ix_memories_id", table_name="memories")
    op.drop_index("ix_memories_canonical_term", table_name="memories")
    op.drop_index("ix_memories_category", table_name="memories")
    op.drop_table("memories")
