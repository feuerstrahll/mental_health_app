"""MVP: current_turn_input table and safety_classification_record audit trail

Adds structured input capture and deterministic safety classification audit.
Replaces synthetic chunk creation with explicit FK linkage.

Revision ID: 20260502_0004
Revises: 20260501_0003
Create Date: 2026-05-02
"""

from alembic import op


revision = "20260502_0004"
down_revision = "20260501_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create current_turn_input table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS current_turn_input (
            id VARCHAR(96) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            session_id VARCHAR(96),
            
            -- MVP form input (emotion_marker + optional text + daily signals)
            emotion_marker VARCHAR(20) NOT NULL,
            user_text TEXT,
            
            -- Daily signals from form
            sleep_hours FLOAT,
            sleep_quality INT,
            activity_minutes INT,
            social_connection INT,
            
            -- Linkage: used to connect conversation_message / daily_comment back to this input row
            input_row_id VARCHAR(96) UNIQUE NOT NULL,
            
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            CONSTRAINT fk_current_turn_user FOREIGN KEY (user_id) 
                REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_current_turn_user_session ON current_turn_input(user_id, session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_current_turn_input_row_id ON current_turn_input(input_row_id)"
    )
    
    # Add input_row_id column to conversation_message (link back to current_turn_input)
    op.execute(
        """
        ALTER TABLE IF EXISTS chat_messages
        ADD COLUMN IF NOT EXISTS input_row_id VARCHAR(96)
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_input_row_id ON chat_messages(input_row_id)"
    )
    
    # Add input_row_id column to daily_comment (link back to current_turn_input)
    op.execute(
        """
        ALTER TABLE IF EXISTS daily_comments
        ADD COLUMN IF NOT EXISTS input_row_id VARCHAR(96)
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_comments_input_row_id ON daily_comments(input_row_id)"
    )
    
    # Create safety_classification_record table (audit trail for deterministic safety classifications)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS safety_classification_record (
            id VARCHAR(96) PRIMARY KEY,
            request_id VARCHAR(96) NOT NULL,
            user_id VARCHAR(64) NOT NULL,
            
            -- SafetyClassification output
            safety_mode VARCHAR(50) NOT NULL,
            risk_flags JSONB,
            safety_instructions JSONB,
            confidence FLOAT DEFAULT 1.0,
            
            -- Triggers matched (debug)
            raw_triggers JSONB,
            latency_ms INT,
            
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            CONSTRAINT fk_safety_user FOREIGN KEY (user_id) 
                REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_safety_user_request ON safety_classification_record(user_id, request_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_safety_mode ON safety_classification_record(safety_mode)"
    )


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_safety_mode")
    op.execute("DROP INDEX IF EXISTS idx_safety_user_request")
    
    # Drop tables
    op.execute("DROP TABLE IF EXISTS safety_classification_record")
    
    # Drop columns from existing tables
    op.execute("DROP INDEX IF EXISTS idx_daily_comments_input_row_id")
    op.execute("ALTER TABLE IF EXISTS daily_comments DROP COLUMN IF EXISTS input_row_id")
    
    op.execute("DROP INDEX IF EXISTS idx_chat_messages_input_row_id")
    op.execute("ALTER TABLE IF EXISTS chat_messages DROP COLUMN IF EXISTS input_row_id")
    
    # Drop current_turn_input
    op.execute("DROP INDEX IF EXISTS idx_current_turn_input_row_id")
    op.execute("DROP INDEX IF EXISTS idx_current_turn_user_session")
    op.execute("DROP TABLE IF EXISTS current_turn_input")
