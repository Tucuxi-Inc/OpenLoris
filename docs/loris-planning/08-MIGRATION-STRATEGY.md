# Loris: Migration Strategy from CounselScope

## Document Overview
**Version:** 0.1.0 (Draft)
**Last Updated:** January 2026

---

## Executive Summary

This document outlines the strategy for transforming CounselScope into Loris (Legal Loris for v1). The approach maximizes code reuse while introducing the new Q&A workflow system.

**Key principle:** Evolution, not revolution. We retain proven infrastructure and add new capabilities on top.

---

## What We're Building

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    COUNSELSCOPE → LORIS TRANSFORMATION                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COUNSELSCOPE (Current)                  LORIS (Target)                      │
│  ─────────────────────                   ─────────────────                   │
│                                                                              │
│  • Query refinement workflow             • Q&A workflow (ASK → ANSWER)       │
│  • Expert-facing only                    • Business user + Expert views      │
│  • Manual knowledge entry                • Knowledge from Q&A answers        │
│  • No automation                         • Intelligent automation            │
│  • Billing analysis                      • Billing analysis (retained)       │
│  • Document management                   • Document management (retained)    │
│  • Semantic search                       • Semantic search (enhanced)        │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                              │
│  RETAINED INFRASTRUCTURE                 NEW COMPONENTS                      │
│  ───────────────────────                 ──────────────                      │
│                                                                              │
│  ✅ PostgreSQL + pgvector               🆕 Questions service                 │
│  ✅ Redis caching                        🆕 Automation engine                 │
│  ✅ FastAPI backend                      🆕 Notification service              │
│  ✅ React + TypeScript frontend          🆕 User dashboards                   │
│  ✅ AI provider abstraction              🆕 Expert queue                      │
│  ✅ Document processing                  🆕 Full authentication               │
│  ✅ Knowledge/wisdom system              🆕 Gap analysis                      │
│  ✅ Embedding generation                 🆕 GUD management                    │
│  ✅ Billing intelligence                                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Migration Phases

### Phase 0: Preparation (Week 1)

**Goal:** Set up development environment and establish migration foundation.

| Task | Details | Effort |
|------|---------|--------|
| Create feature branch | `loris-v1` branch from main | 1 hour |
| Update project naming | Rename references, update README | 2 hours |
| Add Loris assets | Add Loris images to frontend assets | 1 hour |
| Set up new schema migrations | Create Alembic migration for new tables | 4 hours |
| Configure CI/CD for Loris | Update build/deploy scripts | 2 hours |

**Deliverables:**
- [ ] Feature branch created
- [ ] Project renamed to Loris
- [ ] Loris images added
- [ ] Database migration scripts ready

---

### Phase 1: Authentication & User Management (Weeks 1-2)

**Goal:** Implement full authentication with role-based access control.

#### 1.1 Backend Changes

```python
# Enhance existing User model
# backend/app/models/user.py

class UserRole(str, Enum):
    BUSINESS_USER = "business_user"
    DOMAIN_EXPERT = "domain_expert"
    ADMIN = "admin"

class User(Base):
    # Existing fields...

    # Add new fields
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.BUSINESS_USER
    )
    notification_preferences: Mapped[dict] = mapped_column(
        JSONB,
        default={}
    )
    department: Mapped[str | None]
    title: Mapped[str | None]
    last_login_at: Mapped[datetime | None]
```

```python
# Implement auth service
# backend/app/services/auth_service.py

class AuthService:
    async def register(self, data: UserCreate) -> User: ...
    async def login(self, email: str, password: str) -> TokenPair: ...
    async def refresh_token(self, refresh_token: str) -> str: ...
    async def logout(self, user_id: UUID) -> None: ...
    async def get_current_user(self, token: str) -> User: ...
```

#### 1.2 Frontend Changes

```typescript
// Add authentication context
// frontend/src/contexts/AuthContext.tsx

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isExpert: boolean;
  isAdmin: boolean;
}
```

#### 1.3 Migration Tasks

| Task | From | To | Effort |
|------|------|-----|--------|
| Enhance User model | Basic model | Full model with roles | 4 hours |
| Create auth endpoints | Partial | Full CRUD + token refresh | 8 hours |
| Implement JWT middleware | Incomplete | Full validation + refresh | 4 hours |
| Create login UI | None | Login/register pages | 8 hours |
| Add route guards | None | Protected routes by role | 4 hours |
| Session management | None | Redis sessions | 4 hours |

**Deliverables:**
- [ ] Working login/register flow
- [ ] JWT authentication with refresh
- [ ] Role-based route protection
- [ ] User session management

---

### Phase 2: Question System (Weeks 2-4)

**Goal:** Implement the core Q&A workflow replacing conversation refinement.

#### 2.1 New Database Models

```python
# backend/app/models/questions.py

class QuestionStatus(str, Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    AUTO_ANSWERED = "auto_answered"
    HUMAN_REQUESTED = "human_requested"
    EXPERT_QUEUE = "expert_queue"
    IN_PROGRESS = "in_progress"
    NEEDS_CLARIFICATION = "needs_clarification"
    ANSWERED = "answered"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Question(Base):
    __tablename__ = "questions"

    id: Mapped[UUID]
    organization_id: Mapped[UUID]
    asked_by_id: Mapped[UUID]

    original_text: Mapped[str]
    category: Mapped[str | None]
    tags: Mapped[list[str]]
    status: Mapped[QuestionStatus]
    priority: Mapped[QuestionPriority]

    assigned_to_id: Mapped[UUID | None]
    automation_rule_id: Mapped[UUID | None]
    gap_analysis: Mapped[dict | None]

    # ... timestamps, relationships
```

#### 2.2 Questions Service

```python
# backend/app/services/questions_service.py

class QuestionsService:
    async def submit_question(
        self,
        user_id: UUID,
        text: str,
        category: str | None = None,
        attachments: list[Attachment] | None = None
    ) -> QuestionSubmitResult:
        """
        Submit a new question.
        1. Create question record
        2. Check for automation match
        3. If match: deliver auto-answer
        4. If no match: queue for expert with gap analysis
        """
        ...

    async def get_user_questions(
        self,
        user_id: UUID,
        filters: QuestionFilters
    ) -> list[Question]:
        """Get questions submitted by a user."""
        ...

    async def get_expert_queue(
        self,
        expert_id: UUID,
        filters: QueueFilters
    ) -> ExpertQueue:
        """Get questions awaiting expert attention."""
        ...

    async def submit_answer(
        self,
        question_id: UUID,
        expert_id: UUID,
        content: str,
        options: AnswerOptions
    ) -> Answer:
        """Expert submits answer to question."""
        ...
```

#### 2.3 Frontend Components

```
frontend/src/
├── pages/
│   ├── user/
│   │   ├── DashboardPage.tsx      # Business user dashboard
│   │   ├── AskQuestionPage.tsx    # Question submission
│   │   └── QuestionDetailPage.tsx # View question/answer
│   └── expert/
│       ├── QueuePage.tsx          # Expert queue
│       ├── QuestionReviewPage.tsx # Review + answer
│       └── AnalyticsPage.tsx      # Expert metrics
├── components/
│   ├── questions/
│   │   ├── QuestionCard.tsx
│   │   ├── QuestionForm.tsx
│   │   ├── AnswerView.tsx
│   │   └── StatusIndicator.tsx
│   ├── expert/
│   │   ├── GapAnalysisPanel.tsx
│   │   ├── AnswerComposer.tsx
│   │   └── QueueFilters.tsx
│   └── loris/
│       ├── LorisIndicator.tsx
│       └── LorisImages.tsx
```

#### 2.4 Migration Tasks

| Task | Effort |
|------|--------|
| Create Question, Answer, QuestionMessage models | 8 hours |
| Create database migrations | 4 hours |
| Implement QuestionsService | 16 hours |
| Create question submission API endpoints | 8 hours |
| Create expert queue API endpoints | 8 hours |
| Build business user dashboard UI | 16 hours |
| Build question submission flow UI | 8 hours |
| Build expert queue UI | 12 hours |
| Build question review/answer UI | 12 hours |
| Integrate Loris imagery | 4 hours |

**Deliverables:**
- [ ] Questions can be submitted and tracked
- [ ] Expert queue shows pending questions
- [ ] Experts can answer questions
- [ ] Users receive answers and can provide feedback

---

### Phase 3: Automation Engine (Weeks 4-5)

**Goal:** Implement intelligent auto-answering for similar questions.

#### 3.1 Automation Models

```python
# backend/app/models/automation.py

class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[UUID]
    organization_id: Mapped[UUID]
    created_by_id: Mapped[UUID]

    name: Mapped[str]
    canonical_question: Mapped[str]
    canonical_answer: Mapped[str]

    similarity_threshold: Mapped[float] = 0.85
    category_filter: Mapped[str | None]
    exclude_keywords: Mapped[list[str]]

    good_until_date: Mapped[date | None]
    is_enabled: Mapped[bool] = True

    # Metrics
    times_triggered: Mapped[int] = 0
    times_accepted: Mapped[int] = 0
    times_rejected: Mapped[int] = 0


class AutomationRuleEmbedding(Base):
    __tablename__ = "automation_rule_embeddings"

    id: Mapped[UUID]
    rule_id: Mapped[UUID]  # FK unique
    embedding: Mapped[Vector]  # pgvector
    model_name: Mapped[str]
```

#### 3.2 Automation Service

```python
# backend/app/services/automation_service.py

class AutomationService:
    async def check_for_automation(
        self,
        question_text: str,
        question_embedding: list[float],
        organization_id: UUID,
        category: str | None = None
    ) -> AutomationMatch | None:
        """
        Check if an automation rule matches the question.
        Uses pgvector similarity search.
        """
        ...

    async def create_rule_from_answer(
        self,
        answer: Answer,
        config: AutomationRuleConfig
    ) -> AutomationRule:
        """Create automation rule from an expert's answer."""
        ...

    async def handle_user_feedback(
        self,
        question_id: UUID,
        accepted: bool,
        rejection_reason: str | None = None
    ) -> None:
        """Update metrics when user accepts/rejects auto-answer."""
        ...
```

#### 3.3 Integration with Question Flow

```python
# In QuestionsService.submit_question():

async def submit_question(self, ...):
    # Create question
    question = await self._create_question(...)

    # Generate embedding
    embedding = await self.embedding_service.generate(question.original_text)

    # Check automation
    match = await self.automation_service.check_for_automation(
        question_text=question.original_text,
        question_embedding=embedding,
        organization_id=question.organization_id,
        category=question.category
    )

    if match and match.similarity >= match.rule.similarity_threshold:
        # Deliver auto-answer
        return await self._deliver_auto_answer(question, match)
    else:
        # Queue for expert
        return await self._queue_for_expert(question, embedding)
```

#### 3.4 Migration Tasks

| Task | Effort |
|------|--------|
| Create AutomationRule, AutomationRuleEmbedding models | 4 hours |
| Create AutomationLog model | 2 hours |
| Database migrations | 2 hours |
| Implement AutomationService | 12 hours |
| Integrate with question submission | 4 hours |
| Create automation management API | 8 hours |
| Build automation rules UI for experts | 8 hours |
| Implement user feedback flow | 4 hours |
| Add TransWarp Loris flow | 4 hours |

**Deliverables:**
- [ ] Similar questions get auto-answered
- [ ] Experts can create automation rules
- [ ] Users can accept or request human review
- [ ] Automation metrics tracked

---

### Phase 4: Gap Analysis Enhancement (Weeks 5-6)

**Goal:** Enhance the existing knowledge search with gap analysis for expert support.

#### 4.1 Gap Analysis Service

```python
# backend/app/services/gap_analysis_service.py

class GapAnalysisService:
    def __init__(
        self,
        knowledge_service: KnowledgeService,
        ai_provider: AIProviderService
    ):
        self.knowledge_service = knowledge_service
        self.ai_provider = ai_provider

    async def analyze(
        self,
        question: Question,
        question_embedding: list[float]
    ) -> GapAnalysisResult:
        """
        Analyze a question against the knowledge base.

        Returns:
        - Relevant knowledge facts with citations
        - Coverage percentage
        - Identified gaps
        - Proposed answer
        - Suggested clarifications
        """

        # 1. Search knowledge base
        relevant_facts = await self.knowledge_service.semantic_search(
            embedding=question_embedding,
            organization_id=question.organization_id,
            limit=10
        )

        # 2. Use AI to analyze gaps
        analysis = await self.ai_provider.analyze_gaps(
            question=question.original_text,
            context=question.rejection_reason,
            knowledge=relevant_facts
        )

        return GapAnalysisResult(
            relevant_knowledge=relevant_facts,
            coverage_percentage=analysis.coverage,
            identified_gaps=analysis.gaps,
            proposed_answer=analysis.proposed_answer,
            confidence_score=analysis.confidence,
            suggested_clarifications=analysis.clarifications
        )
```

#### 4.2 Leveraging Existing CounselScope Services

The gap analysis builds on these existing services:

```
CounselScope Services (Retain)          Loris Enhancement
───────────────────────────────         ─────────────────

KnowledgeEvaluationService              GapAnalysisService
├─ semantic_search()          ────────► Uses for knowledge lookup
├─ calculate_relevance()      ────────► Uses for scoring
└─ find_gaps()                ────────► Enhanced with AI

AIProviderService
├─ generate_response()        ────────► Uses for gap analysis prompt
└─ generate_embedding()       ────────► Uses for question embedding

DocumentIngestionService
├─ extract_facts()            ────────► Retained for documents
└─ validate_facts()           ────────► Retained for expert validation
```

#### 4.3 Migration Tasks

| Task | Effort |
|------|--------|
| Create GapAnalysisService | 8 hours |
| Enhance AI prompts for gap analysis | 4 hours |
| Integrate with question queue | 4 hours |
| Build GapAnalysisPanel component | 8 hours |
| Store/display analysis in expert view | 4 hours |

**Deliverables:**
- [ ] Questions in queue have gap analysis
- [ ] Experts see relevant knowledge + gaps
- [ ] AI-proposed answers available for editing

---

### Phase 5: GUD Management & Notifications (Week 6)

**Goal:** Implement Good Until Date management and notification system.

#### 5.1 GUD Management

```python
# backend/app/services/gud_service.py

class GUDService:
    async def get_expiring_items(
        self,
        organization_id: UUID,
        within_days: int = 30
    ) -> ExpiringItems:
        """Get automation rules and knowledge facts expiring soon."""
        ...

    async def renew_item(
        self,
        item_type: str,
        item_id: UUID,
        new_gud: date
    ) -> None:
        """Extend the GUD date for an item."""
        ...

    async def run_daily_check(self) -> None:
        """Daily job to check expirations and send notifications."""
        ...
```

#### 5.2 Notification Service

```python
# backend/app/services/notification_service.py

class NotificationService:
    async def notify(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        data: dict
    ) -> Notification:
        """Create notification and optionally send email."""
        ...

    async def broadcast_to_experts(
        self,
        organization_id: UUID,
        notification_type: NotificationType,
        data: dict
    ) -> list[Notification]:
        """Notify all experts in an organization."""
        ...
```

#### 5.3 WebSocket for Real-time

```python
# backend/app/api/v1/websocket.py

@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time notifications."""
    user = await auth_service.get_user_from_token(token)

    await websocket.accept()

    async with notification_service.subscribe(user.id) as notifications:
        async for notification in notifications:
            await websocket.send_json(notification.dict())
```

#### 5.4 Migration Tasks

| Task | Effort |
|------|--------|
| Create Notification model | 2 hours |
| Implement NotificationService | 8 hours |
| Implement GUDService | 4 hours |
| Create daily GUD check job (Celery) | 4 hours |
| Set up WebSocket notifications | 8 hours |
| Build notifications UI | 8 hours |
| Build "Expiring Soon" dashboard | 4 hours |
| Email notification integration | 4 hours |

**Deliverables:**
- [ ] Notifications for answered questions
- [ ] Expert notifications for new questions
- [ ] GUD expiration warnings
- [ ] Real-time notification updates

---

### Phase 6: Analytics & Polish (Week 7)

**Goal:** Implement analytics dashboard and final polish.

#### 6.1 Analytics Service

```python
# backend/app/services/analytics_service.py

class AnalyticsService:
    async def get_overview(
        self,
        organization_id: UUID,
        period: AnalyticsPeriod
    ) -> AnalyticsOverview:
        """Get dashboard overview metrics."""
        ...

    async def get_automation_metrics(
        self,
        organization_id: UUID,
        period: AnalyticsPeriod
    ) -> AutomationMetrics:
        """Get automation performance metrics."""
        ...

    async def aggregate_daily_metrics(
        self,
        organization_id: UUID,
        date: date
    ) -> DailyMetrics:
        """Aggregate and store daily metrics (run nightly)."""
        ...
```

#### 6.2 Migration Tasks

| Task | Effort |
|------|--------|
| Create DailyMetrics model | 2 hours |
| Implement AnalyticsService | 8 hours |
| Create analytics API endpoints | 4 hours |
| Build analytics dashboard UI | 12 hours |
| Daily aggregation job | 4 hours |
| Export functionality | 4 hours |

**Deliverables:**
- [ ] Analytics dashboard with key metrics
- [ ] Automation performance tracking
- [ ] Question volume trends
- [ ] ROI/value metrics

---

### Phase 7: Testing & Documentation (Week 8)

**Goal:** Comprehensive testing and documentation.

#### 7.1 Testing

| Test Type | Coverage Target |
|-----------|-----------------|
| Unit tests (services) | 80% |
| Integration tests (API) | 70% |
| E2E tests (critical flows) | Key user journeys |

#### 7.2 Documentation

| Document | Purpose |
|----------|---------|
| README.md | Updated for Loris |
| API documentation | OpenAPI/Swagger |
| Deployment guide | Docker, production |
| User guide | For business users |
| Admin guide | For experts/admins |

#### 7.3 Migration Tasks

| Task | Effort |
|------|--------|
| Write unit tests for new services | 16 hours |
| Write API integration tests | 12 hours |
| Write E2E tests for key flows | 8 hours |
| Update README and documentation | 8 hours |
| API documentation (OpenAPI) | 4 hours |
| Deployment guide update | 4 hours |

---

## Code Mapping

### Files to Retain (Unchanged or Minor Updates)

| File/Directory | Action |
|----------------|--------|
| `backend/app/core/config.py` | Minor updates for new settings |
| `backend/app/core/database.py` | Unchanged |
| `backend/app/models/documents.py` | Unchanged |
| `backend/app/models/wisdom.py` | Minor updates for Answer source |
| `backend/app/models/billing.py` | Unchanged |
| `backend/app/services/ai_provider_service.py` | Minor updates for new prompts |
| `backend/app/services/document_ingestion_service.py` | Unchanged |
| `backend/app/services/embedding_service.py` | Unchanged |
| `backend/app/services/billing_intelligence_service.py` | Unchanged |
| `backend/app/api/v1/documents.py` | Unchanged |
| `backend/app/api/v1/wisdom.py` | Minor updates |
| `backend/app/api/v1/billing.py` | Unchanged |
| `frontend/src/components/ui/*` | Unchanged (base components) |
| `frontend/src/lib/*` | Unchanged |
| `docker-compose.yml` | Minor updates |

### Files to Significantly Modify

| File/Directory | Changes |
|----------------|---------|
| `backend/app/models/user.py` | Add role, preferences, department |
| `backend/app/api/v1/auth.py` | Full auth implementation |
| `backend/app/main.py` | Update routes, middleware |
| `frontend/src/App.tsx` | New routing structure |
| `frontend/src/pages/*` | Replace with new pages |

### Files to Create (New)

| File/Directory | Purpose |
|----------------|---------|
| `backend/app/models/questions.py` | Question, Answer, QuestionMessage |
| `backend/app/models/automation.py` | AutomationRule, AutomationLog |
| `backend/app/models/notifications.py` | Notification |
| `backend/app/services/questions_service.py` | Q&A workflow |
| `backend/app/services/automation_service.py` | Auto-answer matching |
| `backend/app/services/gap_analysis_service.py` | Gap analysis |
| `backend/app/services/notification_service.py` | Notifications |
| `backend/app/services/gud_service.py` | GUD management |
| `backend/app/services/analytics_service.py` | Analytics |
| `backend/app/api/v1/questions.py` | Question endpoints |
| `backend/app/api/v1/automation.py` | Automation endpoints |
| `backend/app/api/v1/notifications.py` | Notification endpoints |
| `backend/app/api/v1/analytics.py` | Analytics endpoints |
| `backend/app/api/v1/websocket.py` | WebSocket endpoints |
| `frontend/src/pages/user/*` | Business user pages |
| `frontend/src/pages/expert/*` | Expert pages |
| `frontend/src/components/questions/*` | Question components |
| `frontend/src/components/expert/*` | Expert components |
| `frontend/src/components/loris/*` | Loris imagery |
| `frontend/src/contexts/AuthContext.tsx` | Auth state |
| `frontend/src/contexts/NotificationContext.tsx` | Notification state |

### Files to Remove/Archive

| File/Directory | Reason |
|----------------|--------|
| `backend/app/services/conversational_refinement_service.py` | Replaced by questions flow |
| `backend/app/api/v1/conversation.py` | Replaced by questions API |
| `frontend/src/pages/ConversationalRefinementPage.tsx` | Replaced by new pages |
| `frontend/src/pages/QueryRefinementPage.tsx` | Replaced by new pages |

---

## Database Migration Plan

### Migration Order

1. **Add new tables** (non-breaking)
   ```sql
   CREATE TABLE questions (...);
   CREATE TABLE answers (...);
   CREATE TABLE question_messages (...);
   CREATE TABLE automation_rules (...);
   CREATE TABLE automation_rule_embeddings (...);
   CREATE TABLE automation_logs (...);
   CREATE TABLE notifications (...);
   CREATE TABLE daily_metrics (...);
   ```

2. **Modify existing tables** (non-breaking)
   ```sql
   ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'business_user';
   ALTER TABLE users ADD COLUMN notification_preferences JSONB DEFAULT '{}';
   ALTER TABLE users ADD COLUMN department VARCHAR(255);
   ALTER TABLE users ADD COLUMN title VARCHAR(255);
   ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;

   ALTER TABLE wisdom_facts ADD COLUMN source_answer_id UUID REFERENCES answers(id);
   ```

3. **Create indexes**
   ```sql
   CREATE INDEX idx_questions_org_status ON questions(organization_id, status);
   CREATE INDEX idx_automation_embeddings_vector ON automation_rule_embeddings
       USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
   -- etc.
   ```

4. **Data migration** (if needed)
   - Migrate existing conversation data to questions format
   - Set default roles for existing users

5. **Drop old tables** (after verification)
   - Only after confirming new system works
   - Keep backup for rollback

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Embedding model performance | Test with production-scale data early |
| pgvector query latency | Add proper indexes, consider caching |
| WebSocket scalability | Use Redis pub/sub for horizontal scaling |
| Migration data loss | Comprehensive backup before migration |

### Process Risks

| Risk | Mitigation |
|------|------------|
| Scope creep | Strict phase gates, MVP focus |
| Integration issues | Early integration testing between phases |
| Knowledge transfer | Document as we go, pair programming |

---

## Timeline Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 0: Preparation | Week 1 | Development environment ready |
| 1: Authentication | Weeks 1-2 | Login, roles, protected routes |
| 2: Questions | Weeks 2-4 | Core Q&A workflow |
| 3: Automation | Weeks 4-5 | Auto-answering |
| 4: Gap Analysis | Weeks 5-6 | Expert support tools |
| 5: GUD & Notifications | Week 6 | Freshness management |
| 6: Analytics | Week 7 | Metrics dashboard |
| 7: Testing & Docs | Week 8 | Quality assurance |

**Total estimated duration: 8 weeks**

---

## Success Criteria

### MVP (End of Phase 4)

- [ ] Users can submit questions and receive answers
- [ ] Experts can review and answer from queue
- [ ] Similar questions get auto-answered
- [ ] Users can request human review
- [ ] Gap analysis supports expert decisions

### Full v1 (End of Phase 7)

- [ ] All MVP criteria
- [ ] GUD management for knowledge freshness
- [ ] Real-time notifications
- [ ] Analytics dashboard
- [ ] 80% test coverage
- [ ] Production-ready documentation

---

*This migration plan will be refined as implementation progresses.*
