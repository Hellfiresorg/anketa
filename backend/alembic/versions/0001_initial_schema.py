"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "survey_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "survey_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["template_id"], ["survey_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "order_index"),
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(20), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_name", sa.String(), nullable=False),
        sa.Column("client_phone", sa.String(), nullable=True),
        sa.Column("client_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["manager_id"], ["managers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["survey_templates.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invitations_created_at", "invitations", ["created_at"])
    op.create_index("ix_invitations_status", "invitations", ["status"])
    op.create_index("ix_invitations_manager_id", "invitations", ["manager_id"])

    op.create_table(
        "responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitation_id", sa.String(20), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audio_path", sa.Text(), nullable=False),
        sa.Column("audio_duration_sec", sa.Float(), nullable=True),
        sa.Column("audio_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("audio_mime", sa.String(50), nullable=True),
        sa.Column("transcription", sa.Text(), nullable=True),
        sa.Column("transcription_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("transcription_error", sa.Text(), nullable=True),
        sa.Column("transcription_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("transcribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invitation_id"], ["invitations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["survey_questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_responses_transcription_status",
        "responses",
        ["transcription_status"],
        postgresql_where=sa.text("transcription_status IN ('pending', 'processing', 'failed')"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["manager_id"], ["managers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_manager_id", "audit_log", ["manager_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("responses")
    op.drop_table("invitations")
    op.drop_table("survey_questions")
    op.drop_table("survey_templates")
    op.drop_table("managers")
