# SPEC C: Database Schema & Migrations (MVP)

**Status:** Specification (not yet implemented)  
**Purpose:** Define new tables and fields needed for MVP pipeline  
**Dependencies:** SafetyClassifier output fields (SPEC D ✅ complete)  
**Blocks:** Step 2 implementation, Step 6 (PromptBuilder), ResponseValidator

---

## 1. New Tables

### 1.1 `current_turn_input` Table

Captures the structured input from mobile form submission.

```sql
CREATE TABLE current_turn_input (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID NOT NULL REFERENCES sessions(id),
    
    -- MVP form input (6 emotion markers only, optional text, daily signals)
    emotion_marker VARCHAR(20) NOT NULL,  -- 'happy', 'calm', 'okay', 'anxious', 'sad', 'tired'
    user_text TEXT,                        -- optional diary/note entry
    
    -- Daily signals from form
    sleep_hours FLOAT,                     -- e.g., 7.5
    sleep_quality INT,                     -- 1-10 or NULL
    activity_minutes INT,                  -- minutes of movement
    social_connection INT,                 -- 1-10 scale (feeling of connection)
    
    -- Metadata
    input_row_id UUID UNIQUE NOT NULL,    -- Used to link back from conversation_message/daily_comment
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_current_turn_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_current_turn_user_session ON current_turn_input(user_id, session_id);
CREATE INDEX idx_current_turn_input_row_id ON current_turn_input(input_row_id);
```

### 1.2 Update `conversation_message` Table

Add FK to link back to current_turn_input:

```sql
ALTER TABLE conversation_message 
ADD COLUMN input_row_id UUID REFERENCES current_turn_input(id);

CREATE INDEX idx_conversation_message_input_row ON conversation_message(input_row_id);
```

### 1.3 Update `daily_comment` Table

Add FK to link back to current_turn_input (replaces synthetic chunk creation):

```sql
ALTER TABLE daily_comment
ADD COLUMN input_row_id UUID REFERENCES current_turn_input(id);

CREATE INDEX idx_daily_comment_input_row ON daily_comment(input_row_id);
```

### 1.4 `safety_classification_record` Table (Optional Audit)

Stores SafetyClassifier output for audit trail:

```sql
CREATE TABLE safety_classification_record (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- SafetyClassification output
    safety_mode VARCHAR(50) NOT NULL,  -- 'crisis' | 'close_conversation' | 'safe_support' | 'normal'
    risk_flags JSONB,                   -- array of flags, e.g., ["crisis:explicit_self_harm"]
    safety_instructions JSONB,          -- array of instructions per mode
    confidence FLOAT DEFAULT 1.0,       -- always 1.0 for deterministic rules
    
    -- Triggers matched (debug)
    raw_triggers JSONB,
    latency_ms INT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_safety_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_safety_user_request ON safety_classification_record(user_id, request_id);
```

---

## 2. Request/Response JSON Contracts

### 2.1 Mobile → Backend: `SupportDecisionRequest` (UPDATED)

```json
{
  "user_id": "uuid",
  "session_id": "uuid",
  "client_timestamp": "2026-05-02T14:30:00Z",
  
  "input_row_id": "uuid",
  
  "emotion_marker": "okay",
  "user_text": "Had a hard day at work",
  
  "signals": {
    "sleep_hours": 7.5,
    "sleep_quality": 7,
    "activity_minutes": 45,
    "social_connection": 6
  },
  
  "dialogue_state": {
    "version": 1,
    "turn_index": 1,
    "last_bot_action": "asked_followup",
    "stop_requested": false,
    "ui_state": "followup_wait"
  },
  
  "client_safety_precheck_result": {
    "flags": []
  }
}
```

**Key Change:** Added `input_row_id` field to link back from backend outputs.
Legacy `dialogue_state.state` is accepted during transition and mapped to `dialogue_state.ui_state`.

### 2.2 Backend → Mobile: `SupportDecisionResponse` (UPDATED)

```json
{
  "request_id": "uuid",
  "session_id": "uuid",
  
  "llm_response": "string",
  "safety_mode": "normal",
  "decision": {
    "support_mode": "context_first_support",
    "assessor_action": "validate_and_ask_one_question"
  },
  "practice_card_id": "breathing_2min",
  "recommended_action": "breathing_2min",
  "recommended_action_deprecated": true,
  
  "llm_meta": {
    "used_fallback": false,
    "fallback_reason": null,
    "latency_ms": 250
  },
  
  "dialogue_state": "followup_wait",
  "safe_mode": false,
  "should_continue_dialogue": true
}
```

`decision.assessor_action` and `practice_card_id` are different domains. Top-level
`recommended_action` is deprecated compatibility and should be removed after mobile
clients no longer depend on it.

### 2.3 Backend Health States

- `ok`: retrieval enabled and backend/BGE/pgvector dimensions match.
- `degraded`: `MEMORY_RETRIEVAL_ENABLED=false`; BGE and pgvector checks are skipped.
- `unhealthy`: retrieval enabled and embedding dimension contract failed.

---

## 3. Data Flow: `input_row_id` Linkage

**Step 1 (Mobile):** Form submission creates unique `input_row_id` (UUID)

```
Mobile form → POST /api/v1/support-decision with input_row_id
```

**Step 2 (Backend):** Save input_row_id to `current_turn_input` table

```python
current_turn_input_record = await current_turn_input_repo.save(
    user_id=payload.user_id,
    session_id=session_id,
    emotion_marker=payload.emotion_marker,
    user_text=payload.user_text,
    sleep_hours=payload.signals.sleep_hours,
    input_row_id=payload.input_row_id,  # UUID from mobile
)
```

**Step 3 (Backend):** Link `conversation_message` FK to `current_turn_input`

```python
if latest_user_message:
    msg_id = await conversation_repo.save_user_message(
        session_id=session_id,
        user_id=payload.user_id,
        text=latest_user_message,
        input_row_id=current_turn_input_record.id,  # FK!
    )
```

**Step 4 (Backend):** Link `daily_comment` FK to `current_turn_input` (no synthetic chunks)

```python
if current_diary_note:
    comment_id = await daily_comment_repo.save_comment(
        user_id=payload.user_id,
        entry_date=payload.client_timestamp.date(),
        emotion_marker=payload.emotion_marker,
        comment_text=current_diary_note,
        input_row_id=current_turn_input_record.id,  # FK!
    )
```

**Step 5 (Backend):** SafetyClassifier processes (mode is immutable downstream)

```python
safety_classification = classifier.classify(
    latest_user_message=latest_user_message,
    latest_diary_note=current_diary_note,
    client_safety_precheck_result=client_safety_precheck,
)
# safety_classification.mode is read-only, cannot be changed by LLM
```

**Step 6 (Backend):** PromptBuilder uses SafetyClassification (not just decision flags)

```python
prompt_result = prompt_builder.build_messages(
    decision=decision,
    safety_classification=safety_classification,  # NEW: deterministic mode
    latest_user_message=latest_user_message,
    latest_diary_note=current_diary_note,
)
```

**Step 7 (Backend):** Store `safety_classification_record` (audit trail)

```python
await safety_repo.save_record(
    request_id=request_id,
    user_id=payload.user_id,
    safety_mode=safety_classification.mode.value,
    risk_flags=safety_classification.risk_flags,
    safety_instructions=safety_classification.safety_instructions,
    raw_triggers=safety_classification.raw_triggers,
)
```

---

## 4. Schema Migration Path (Alembic)

### New Migration File

**File:** `backend/migrations/versions/2026_05_02_add_current_turn_input.py`

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create current_turn_input table
    op.create_table(
        'current_turn_input',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emotion_marker', sa.VARCHAR(20), nullable=False),
        sa.Column('user_text', sa.Text()),
        sa.Column('sleep_hours', sa.Float()),
        sa.Column('sleep_quality', sa.Integer()),
        sa.Column('activity_minutes', sa.Integer()),
        sa.Column('social_connection', sa.Integer()),
        sa.Column('input_row_id', postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
    )
    
    op.create_index('idx_current_turn_user_session', 'current_turn_input', 
                    ['user_id', 'session_id'])
    op.create_index('idx_current_turn_input_row_id', 'current_turn_input', 
                    ['input_row_id'])
    
    # Add FK to conversation_message
    op.add_column('conversation_message', 
                  sa.Column('input_row_id', postgresql.UUID(as_uuid=True)))
    op.create_foreign_key('fk_conv_msg_input_row', 'conversation_message', 
                          'current_turn_input', ['input_row_id'], ['id'])
    op.create_index('idx_conversation_message_input_row', 'conversation_message', 
                    ['input_row_id'])
    
    # Add FK to daily_comment
    op.add_column('daily_comment', 
                  sa.Column('input_row_id', postgresql.UUID(as_uuid=True)))
    op.create_foreign_key('fk_daily_comment_input_row', 'daily_comment', 
                          'current_turn_input', ['input_row_id'], ['id'])
    op.create_index('idx_daily_comment_input_row', 'daily_comment', 
                    ['input_row_id'])
    
    # Create safety_classification_record table (audit trail)
    op.create_table(
        'safety_classification_record',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('safety_mode', sa.VARCHAR(50), nullable=False),
        sa.Column('risk_flags', postgresql.JSONB()),
        sa.Column('safety_instructions', postgresql.JSONB()),
        sa.Column('confidence', sa.Float(), server_default='1.0'),
        sa.Column('raw_triggers', postgresql.JSONB()),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    op.create_index('idx_safety_user_request', 'safety_classification_record', 
                    ['user_id', 'request_id'])

def downgrade():
    op.drop_table('safety_classification_record')
    op.drop_constraint('fk_daily_comment_input_row', 'daily_comment', type_='foreignkey')
    op.drop_index('idx_daily_comment_input_row', 'daily_comment')
    op.drop_column('daily_comment', 'input_row_id')
    op.drop_constraint('fk_conv_msg_input_row', 'conversation_message', type_='foreignkey')
    op.drop_index('idx_conversation_message_input_row', 'conversation_message')
    op.drop_column('conversation_message', 'input_row_id')
    op.drop_table('current_turn_input')
```

---

## 5. Repository Methods (NEW)

### `CurrentTurnInputRepository`

```python
class CurrentTurnInputRepository:
    async def save(
        self,
        *,
        user_id: str,
        session_id: str,
        emotion_marker: str,
        user_text: str | None,
        sleep_hours: float | None,
        sleep_quality: int | None,
        activity_minutes: int | None,
        social_connection: int | None,
        input_row_id: str,  # UUID from mobile
    ) -> CurrentTurnInputRecord:
        """Save current turn input and return the record."""
        
    async def get_by_input_row_id(self, *, input_row_id: str) -> CurrentTurnInputRecord | None:
        """Get record by mobile-generated input_row_id."""
```

### Update `ConversationRepository`

```python
async def save_user_message(
    self,
    *,
    session_id: str,
    user_id: str,
    text: str,
    input_row_id: str | None = None,  # NEW: link to current_turn_input
) -> str:
    """Save user message and optionally link to current_turn_input."""
```

### Update `DailyCommentRepository`

```python
async def save_comment(
    self,
    *,
    user_id: str,
    entry_date: date,
    emotion_marker: str,
    comment_text: str,
    input_row_id: str | None = None,  # NEW: link to current_turn_input
) -> str:
    """Save daily comment and optionally link to current_turn_input."""
```

---

## 6. Decision Pipeline Changes

### Remove Synthetic Chunk Creation

**OLD:** If message not persisted, create synthetic `ContextMemory` with `request_id:user` source

**NEW:** All inputs are persisted via `current_turn_input_repo.save()`, no synthetic chunks needed.

### Remove Pattern Analysis Service

- `PatternAnalysisService` → DELETED ✅
- All analysis fields now come from SafetyClassification (immutable)

### Integration Points

1. **Decision Pipeline (`ChatOrchestratorService.run()`):**
   - Create `current_turn_input` record immediately
   - Get SafetyClassification from SafetyClassifier
   - Pass SafetyClassification to PromptBuilder (not just decision)
   - Store `safety_classification_record` for audit

2. **PromptBuilder:**
   - Receives SafetyClassification (step 5 output)
   - Uses mode to select system prompt
   - Never allows LLM to change mode (immutable)

3. **ResponseValidator (step 8):**
   - Validates response matches SafetyClassification.mode
   - If response_mode mismatch → use fallback

---

## 7. Backward Compatibility Notes

- Existing `conversation_message` and `daily_comment` records have `input_row_id = NULL`
- Queries must handle nullable `input_row_id`
- Old synthetic chunks stay in database (no cleanup needed)
- New records always have `input_row_id` populated

---

## 8. Implementation Checklist

- [ ] Create Alembic migration file
- [ ] Run `alembic upgrade head` (creates tables)
- [ ] Implement `CurrentTurnInputRepository`
- [ ] Update `ConversationRepository.save_user_message()`
- [ ] Update `DailyCommentRepository.save_comment()`
- [ ] Update `ChatOrchestratorService.run()` to use new tables
- [ ] Remove synthetic chunk creation logic
- [ ] Update PromptBuilder to accept `SafetyClassification`
- [ ] Implement `SafetyClassificationRecordRepository` (optional audit)
- [ ] Update request/response schemas with `input_row_id`
- [ ] Test end-to-end: form → DB → pipeline → response

---

## Next Steps

After SPEC C is approved:
1. **Step 2 Implementation:** Run migrations, implement repositories
2. **Step 1 Implementation:** Update mobile form with emotion picker
3. **Step 6 Implementation:** Update PromptBuilder to enforce 6-slot structure
4. **Step 8 Implementation:** Create ResponseValidator with forbidden phrase scanning
