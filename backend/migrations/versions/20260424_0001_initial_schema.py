"""initial schema placeholder

Revision ID: 20260424_0001
Revises:
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wellbeing_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("emotion_marker", sa.String(length=50), nullable=False),
        sa.Column("diary_note", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default="low"),
    )


def downgrade() -> None:
    op.drop_table("wellbeing_records")
