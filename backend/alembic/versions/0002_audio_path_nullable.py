"""make audio_path nullable

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18
"""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column('responses', 'audio_path', nullable=True)

def downgrade() -> None:
    op.execute("UPDATE responses SET audio_path = '' WHERE audio_path IS NULL")
    op.alter_column('responses', 'audio_path', nullable=False)
