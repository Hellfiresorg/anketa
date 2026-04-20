"""invitation_notes table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitation_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invitation_id", sa.String(20), nullable=False),
        sa.Column("manager_id", sa.UUID(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invitation_id"], ["invitations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_id"], ["managers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_invitation_notes_invitation_id",
        "invitation_notes",
        ["invitation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_invitation_notes_invitation_id", table_name="invitation_notes")
    op.drop_table("invitation_notes")
