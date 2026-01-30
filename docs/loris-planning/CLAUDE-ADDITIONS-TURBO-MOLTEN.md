# CLAUDE.md Additions: Turbo Loris & MoltenLoris

**Add this section to CLAUDE.md after the existing implementation status table.**

---

## Phase 8: Turbo Loris (PLANNED)

Turbo Loris is a user-controlled fast-answer mode that delivers AI-generated responses when knowledge confidence exceeds a user-selected threshold.

### Core Concept

| Mode | Behavior | Threshold |
|------|----------|-----------|
| Standard | Expert-validated answers | N/A |
| Turbo | Knowledge-matched instant answers | User-selected (50%, 75%, 90%) |

**Key principle:** User controls their risk tolerance. They choose the confidence threshold.

### Data Model Changes

```sql
-- Add to questions table
ALTER TABLE questions ADD COLUMN turbo_mode BOOLEAN DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN turbo_threshold FLOAT;
ALTER TABLE questions ADD COLUMN turbo_confidence FLOAT;
ALTER TABLE questions ADD COLUMN turbo_sources UUID[];

-- New table for attributions
CREATE TABLE turbo_attributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,  -- 'fact', 'document', 'automation_rule'
    source_id UUID NOT NULL,
    attributed_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    attributed_department_id UUID NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    contribution_type VARCHAR(50) NOT NULL,
    contribution_date TIMESTAMP NOT NULL,
    confidence_score FLOAT NOT NULL,
    semantic_similarity FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_turbo_attr_question ON turbo_attributions(question_id);
CREATE INDEX idx_turbo_attr_source ON turbo_attributions(source_type, source_id);
```

### New Models

**backend/app/models/turbo.py:**
```python
class TurboAttribution(Base, UUIDMixin, TimestampMixin):
    """Records knowledge sources that contributed to a Turbo Loris answer."""
    __tablename__ = "turbo_attributions"
    
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id"))
    source_type: Mapped[str]  # "fact", "document", "automation_rule"
    source_id: Mapped[UUID]
    attributed_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    attributed_department_id: Mapped[UUID]
    display_name: Mapped[str]
    contribution_type: Mapped[str]  # "uploaded", "authored", "approved", "created_rule"
    contribution_date: Mapped[datetime]
    confidence_score: Mapped[float]
    semantic_similarity: Mapped[float]
```

### New Service

**backend/app/services/turbo_service.py:**

Key methods:
- `calculate_turbo_confidence(question_embedding, matched_facts, matched_docs) -> float`
- `generate_turbo_answer(question, threshold) -> TurboAnswerResult | None`
- `create_attributions(question_id, sources) -> List[TurboAttribution]`
- `handle_user_departure(user_id) -> int` (batch update attributions)

### API Changes

**Question submission (extended):**
```python
class QuestionCreateTurbo(BaseModel):
    text: str
    category: str | None = None
    priority: str = "medium"
    department: str | None = None
    subdomain_id: UUID | None = None
    turbo_mode: bool = False
    turbo_threshold: float = 0.75
```

**Question response (extended):**
```python
class QuestionResponseTurbo(BaseModel):
    question: QuestionDetail
    turbo_answered: bool
    turbo_confidence: float | None
    turbo_threshold: float | None
    attributions: List[TurboAttributionResponse]
    answer: AnswerDetail | None
    confidence_message: str | None
    attribution_message: str | None
```

### Frontend Changes

1. **AskQuestionPage.tsx**: Add Turbo mode toggle with threshold selector
2. **QuestionDetailPage.tsx**: Handle Turbo answer display with attributions
3. **TurboAnswerCard.tsx**: New component for Turbo Loris answer display
4. **AttributionList.tsx**: Show contributors with confidence scores

### Confidence Calculation

```python
def calculate_turbo_confidence(
    question_embedding: List[float],
    matched_facts: List[WisdomFact],
    matched_documents: List[DocumentChunk]
) -> float:
    """
    Weighted aggregate:
    - Best match similarity: 40%
    - Tier score (0a=1.0, 0b=0.9, 0c=0.7): 30%
    - Coverage breadth: 30%
    """
    # See 09-TURBO-AND-MOLTEN-LORIS.md for full implementation
```

### Departed Employee Handling

When a user is deactivated:
1. `UserService.deactivate_user()` calls `TurboService.handle_user_departure(user_id)`
2. Batch update all attributions: set `attributed_user_id = NULL`, update `display_name` to department name
3. Log for audit trail

### Admin Settings

Add to `Organization.settings` JSONB:
```json
{
  "turbo_loris": {
    "enabled": true,
    "min_threshold": 0.50,
    "default_threshold": 0.75,
    "threshold_options": [0.50, 0.75, 0.90],
    "require_tier_0_facts": false,
    "show_contributor_names": true
  }
}
```

---

## Phase 9: MoltenLoris Agent (PLANNED)

MoltenLoris is an autonomous agent that monitors Slack and answers questions using Loris's knowledge base. It runs in an isolated VM and accesses resources via MCP.

### Architecture

MoltenLoris is NOT part of the Loris codebase. It's a separate Moltbot instance configured to:
1. Monitor Slack via Zapier MCP
2. Read documents from Google Drive via Zapier MCP
3. Query Loris API for knowledge search
4. Post answers back to Slack

### Loris API Endpoints for MoltenLoris

Add these endpoints to support MoltenLoris integration:

**backend/app/api/v1/molten.py:**

```python
@router.post("/submit")
async def molten_submit_question(
    request: MoltenQuestionRequest,
    current_user: User = Depends(get_molten_bot_user)
) -> MoltenQuestionResponse:
    """
    Submit a question from MoltenLoris.
    Creates a Turbo-style question with source='moltenloris'.
    """
    
@router.post("/learn")
async def molten_learn_from_expert(
    request: MoltenLearnRequest,
    current_user: User = Depends(get_molten_bot_user)
) -> MoltenLearnResponse:
    """
    Submit an expert answer observed by MoltenLoris.
    Creates an ExtractedFactCandidate for review.
    """
    
@router.get("/search")
async def molten_search_knowledge(
    q: str,
    limit: int = 5,
    current_user: User = Depends(get_molten_bot_user)
) -> MoltenSearchResponse:
    """
    Search knowledge base (facts + documents).
    Returns matches with confidence scores.
    """
```

### Authentication

Create a special "bot" user type for MoltenLoris:
- Role: `bot` (new role, read-only knowledge access)
- Auth: API key (not JWT)
- Rate limit: 100 requests/hour

### Schemas

```python
class MoltenQuestionRequest(BaseModel):
    text: str
    slack_channel: str
    slack_message_id: str
    slack_user_name: str | None = None

class MoltenLearnRequest(BaseModel):
    question_text: str
    answer_text: str
    expert_name: str
    slack_channel: str
    slack_thread_id: str

class MoltenSearchResponse(BaseModel):
    facts: List[MoltenFactMatch]
    documents: List[MoltenDocMatch]
    best_confidence: float
```

### Setup Documentation

See `docs/loris-planning/09-TURBO-AND-MOLTEN-LORIS.md` for:
- VM setup guide (UTM)
- Moltbot installation
- Zapier MCP configuration
- SOUL.md template
- Troubleshooting guide

---

## Implementation Order

### Turbo Loris (implement first)
1. Backend: Models → Service → API
2. Frontend: Question form → Answer display → Analytics

### MoltenLoris (implement second)
1. API endpoints for bot integration
2. Bot user authentication
3. Documentation and setup guide

---

## Key Design Decisions

### Turbo Loris

1. **User-controlled thresholds** — The requester sets their risk tolerance, not the system.

2. **Attribution to individuals** — Contributors get credit, which incentivizes knowledge sharing.

3. **Department fallback** — When users leave, attributions shift to department level automatically.

4. **No silent automation** — Turbo answers are clearly labeled as AI-generated.

### MoltenLoris

1. **Isolation first** — Runs in VM, accesses resources via MCP. Can't touch host system.

2. **Loris as source of truth** — MoltenLoris queries Loris API, doesn't maintain separate knowledge.

3. **Learning requires expert validation** — MoltenLoris submits candidates, experts approve.

4. **Escalation by default** — When unsure, MoltenLoris asks a human rather than guessing.

---

## Testing Notes

### Turbo Loris

```bash
# Create a fact with high confidence
curl -X POST "$BASE/knowledge/facts" -H "Authorization: Bearer $EXPERT_TOKEN" \
  -d '{"content":"Standard vendor contract terms are 12 months.","category":"contracts","tier":"tier_0b"}'

# Submit a Turbo question
curl -X POST "$BASE/questions/" -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"text":"What are standard vendor contract terms?","turbo_mode":true,"turbo_threshold":0.75}'

# Should return turbo_answered=true with attributions
```

### MoltenLoris API

```bash
# Search knowledge (as MoltenLoris bot)
curl -X GET "$BASE/molten/search?q=vendor+contract" -H "X-API-Key: $MOLTEN_API_KEY"

# Submit learned Q&A
curl -X POST "$BASE/molten/learn" -H "X-API-Key: $MOLTEN_API_KEY" \
  -d '{"question_text":"...","answer_text":"...","expert_name":"Sarah Chen","slack_channel":"#legal"}'
```
