"""add user_memory_embeddings with pgvector-friendly schema

Revision ID: 20260501_0002
Revises: 20260424_0001
Create Date: 2026-05-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260501_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_memory_embeddings (
            id VARCHAR(96) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            memory_chunk_id VARCHAR(64) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            date VARCHAR(10) NOT NULL,
            text TEXT NOT NULL,
            metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
            embedding VECTOR(1024) NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.create_index("ix_user_memory_embeddings_user_id", "user_memory_embeddings", ["user_id"])
    op.create_index("ix_user_memory_embeddings_chunk_id", "user_memory_embeddings", ["memory_chunk_id"])
    op.create_index("ix_user_memory_embeddings_date", "user_memory_embeddings", ["date"])
    op.create_index("ix_user_memory_embeddings_source_type", "user_memory_embeddings", ["source_type"])
    op.create_index("ix_user_memory_embeddings_content_hash", "user_memory_embeddings", ["content_hash"])
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_user_memory_embeddings_user_chunk
        ON user_memory_embeddings(user_id, memory_chunk_id)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_memory_embeddings_content_hash", table_name="user_memory_embeddings")
    op.drop_index("ix_user_memory_embeddings_source_type", table_name="user_memory_embeddings")
    op.drop_index("ix_user_memory_embeddings_date", table_name="user_memory_embeddings")
    op.drop_index("ix_user_memory_embeddings_chunk_id", table_name="user_memory_embeddings")
    op.drop_index("ix_user_memory_embeddings_user_id", table_name="user_memory_embeddings")
    op.execute("DROP INDEX IF EXISTS ux_user_memory_embeddings_user_chunk")
    op.drop_table("user_memory_embeddings")
