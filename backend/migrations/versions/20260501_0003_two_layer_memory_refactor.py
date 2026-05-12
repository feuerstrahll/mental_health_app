"""two-layer memory refactor with source tables and vector index normalization

Revision ID: 20260501_0003
Revises: 20260501_0002
Create Date: 2026-05-01
"""

from alembic import op


revision = "20260501_0003"
down_revision = "20260501_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id VARCHAR(96) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_comments (
            id VARCHAR(96) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            entry_date DATE NOT NULL,
            emotion_marker VARCHAR(50) NULL,
            comment_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_chunks (
            id VARCHAR(96) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            source_id VARCHAR(128) NOT NULL,
            text TEXT NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            importance_score DOUBLE PRECISION NULL,
            expires_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_current_turn BOOLEAN NOT NULL DEFAULT FALSE,
            request_id VARCHAR(96) NULL
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_user_created ON chat_messages(user_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_comments_user_entry ON daily_comments(user_id, entry_date, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_chunks_user_id ON memory_chunks(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_chunks_source_ref ON memory_chunks(user_id, source_type, source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_chunks_content_hash ON memory_chunks(user_id, content_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_chunks_created_at ON memory_chunks(created_at)")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_memory_chunks_source_content
        ON memory_chunks(user_id, source_type, source_id, content_hash)
        """
    )

    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS entry_date DATE NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS sleep_duration_hours DOUBLE PRECISION NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS sleep_quality VARCHAR(16) NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS sleep_regularity VARCHAR(16) NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS physical_activity_minutes DOUBLE PRECISION NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS sedentary_time_minutes DOUBLE PRECISION NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS outdoor_time_minutes DOUBLE PRECISION NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS social_connectedness_score DOUBLE PRECISION NULL")
    op.execute("ALTER TABLE wellbeing_records ADD COLUMN IF NOT EXISTS routine_regularity VARCHAR(16) NULL")

    op.execute("ALTER TABLE user_memory_embeddings ALTER COLUMN memory_chunk_id DROP NOT NULL")
    op.execute("ALTER TABLE user_memory_embeddings ALTER COLUMN memory_chunk_id TYPE VARCHAR(96)")
    op.execute("ALTER TABLE user_memory_embeddings ADD COLUMN IF NOT EXISTS model VARCHAR(128)")
    op.execute("ALTER TABLE user_memory_embeddings ADD COLUMN IF NOT EXISTS dim INTEGER")
    op.execute("ALTER TABLE user_memory_embeddings ADD COLUMN IF NOT EXISTS metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("UPDATE user_memory_embeddings SET model = COALESCE(NULLIF(model, ''), 'BAAI/bge-m3')")
    op.execute("UPDATE user_memory_embeddings SET dim = COALESCE(dim, 1024)")
    op.execute("ALTER TABLE user_memory_embeddings ALTER COLUMN model SET NOT NULL")
    op.execute("ALTER TABLE user_memory_embeddings ALTER COLUMN dim SET NOT NULL")

    op.execute(
        """
        CREATE TEMP TABLE tmp_legacy_chunk_backfill AS
        SELECT
            ume.id AS old_embedding_id,
            ume.user_id AS user_id,
            COALESCE(NULLIF(ume.memory_chunk_id, ''), 'legacy_' || substr(md5(ume.id || ':chunk'), 1, 32)) AS generated_chunk_id,
            COALESCE(NULLIF(ume.text, ''), '[legacy embedding without text]') AS chunk_text,
            COALESCE(NULLIF(ume.content_hash, ''), md5(COALESCE(ume.text, '') || ':' || ume.id)) AS content_hash,
            COALESCE(ume.created_at, NOW()) AS created_at
        FROM user_memory_embeddings ume
        LEFT JOIN memory_chunks mc ON mc.id = ume.memory_chunk_id
        WHERE ume.memory_chunk_id IS NULL OR mc.id IS NULL
        """
    )
    op.execute(
        """
        INSERT INTO memory_chunks (
            id,
            user_id,
            source_type,
            source_id,
            text,
            content_hash,
            created_at,
            metadata_jsonb,
            is_current_turn,
            request_id
        )
        SELECT
            b.generated_chunk_id,
            b.user_id,
            'legacy_embedding',
            b.generated_chunk_id,
            b.chunk_text,
            b.content_hash,
            b.created_at,
            jsonb_build_object('old_embedding_id', b.old_embedding_id),
            FALSE,
            NULL
        FROM tmp_legacy_chunk_backfill b
        ON CONFLICT (user_id, source_type, source_id, content_hash) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE user_memory_embeddings ume
        SET memory_chunk_id = b.generated_chunk_id
        FROM tmp_legacy_chunk_backfill b
        WHERE ume.id = b.old_embedding_id
          AND (ume.memory_chunk_id IS NULL OR ume.memory_chunk_id <> b.generated_chunk_id)
        """
    )
    op.execute("DROP TABLE IF EXISTS tmp_legacy_chunk_backfill")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM user_memory_embeddings WHERE memory_chunk_id IS NULL) THEN
                RAISE EXCEPTION 'user_memory_embeddings.memory_chunk_id still has NULL values after backfill';
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE user_memory_embeddings ALTER COLUMN memory_chunk_id SET NOT NULL")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_user_memory_embeddings_memory_chunk'
            ) THEN
                ALTER TABLE user_memory_embeddings
                ADD CONSTRAINT fk_user_memory_embeddings_memory_chunk
                FOREIGN KEY (memory_chunk_id) REFERENCES memory_chunks(id)
                ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )

    op.execute("DROP INDEX IF EXISTS ux_user_memory_embeddings_user_chunk")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_user_memory_embeddings_chunk_model_dim
        ON user_memory_embeddings(memory_chunk_id, model, dim)
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_memory_embeddings_user_id2 ON user_memory_embeddings(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_memory_embeddings_chunk_id2 ON user_memory_embeddings(memory_chunk_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_memory_embeddings_content_hash2 ON user_memory_embeddings(content_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_memory_embeddings_created_at ON user_memory_embeddings(created_at)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_memory_embeddings_embedding_cosine
        ON user_memory_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_memory_embeddings_embedding_cosine")
    op.execute("DROP INDEX IF EXISTS ix_user_memory_embeddings_created_at")
    op.execute("DROP INDEX IF EXISTS ix_user_memory_embeddings_content_hash2")
    op.execute("DROP INDEX IF EXISTS ix_user_memory_embeddings_chunk_id2")
    op.execute("DROP INDEX IF EXISTS ix_user_memory_embeddings_user_id2")
    op.execute("DROP INDEX IF EXISTS ux_user_memory_embeddings_chunk_model_dim")
    op.execute("ALTER TABLE user_memory_embeddings DROP CONSTRAINT IF EXISTS fk_user_memory_embeddings_memory_chunk")
    op.execute("ALTER TABLE user_memory_embeddings DROP COLUMN IF EXISTS dim")
    op.execute("ALTER TABLE user_memory_embeddings DROP COLUMN IF EXISTS model")

    op.execute("DROP INDEX IF EXISTS ux_memory_chunks_source_content")
    op.execute("DROP INDEX IF EXISTS ix_memory_chunks_created_at")
    op.execute("DROP INDEX IF EXISTS ix_memory_chunks_content_hash")
    op.execute("DROP INDEX IF EXISTS ix_memory_chunks_source_ref")
    op.execute("DROP INDEX IF EXISTS ix_memory_chunks_user_id")
    op.execute("DROP TABLE IF EXISTS memory_chunks")

    op.execute("DROP INDEX IF EXISTS ix_daily_comments_user_entry")
    op.execute("DROP TABLE IF EXISTS daily_comments")

    op.execute("DROP INDEX IF EXISTS ix_chat_messages_user_created")
    op.execute("DROP TABLE IF EXISTS chat_messages")
