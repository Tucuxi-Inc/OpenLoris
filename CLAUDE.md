# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Loris** is an intelligent Q&A platform that connects business users with domain experts. It delivers curated, expert-validated answers instead of search results ("Glean+"). **Legal Loris** is the first implementation, focused on legal departments.

Core workflow: User asks question → System checks automation rules → If match: instant answer (TransWarp) → If no match: expert queue with gap analysis → Expert answers → Answer can become automation rule.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 15 + pgvector for semantic search |
| Cache | Redis 7 |
| Frontend | React 18, TypeScript 5+, Vite, Tailwind CSS |
| State | React Query + Zustand |
| Components | Radix UI primitives |
| AI | Multi-provider: Ollama (local), Anthropic Claude, AWS Bedrock, Azure OpenAI |
| Background Jobs | Celery + Redis |
| Real-time | WebSockets (FastAPI) |

## Port Configuration

| Service | Internal Port | External Port |
|---------|---------------|---------------|
| Backend | 8000 | 8005 |
| Frontend | 3000 | 3005 |
| PostgreSQL | 5432 | 5435 |
| Redis | 6379 | 6385 |

Access the app at http://localhost:3005 (frontend) or http://localhost:8005/docs (API docs).

## Development Commands

```bash
# Start all services
docker-compose up -d

# Backend only (with hot reload)
docker-compose up backend

# Frontend only (Vite dev server)
cd frontend && npm run dev

# Database migrations
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "description"

# Run backend tests
docker-compose exec backend pytest
docker-compose exec backend pytest tests/unit/services/test_questions_service.py -v

# Run frontend tests
cd frontend && npm test
cd frontend && npm test -- --watch

# Type checking
cd frontend && npm run typecheck
docker-compose exec backend mypy app/

# Linting
cd frontend && npm run lint
docker-compose exec backend ruff check .
```

## Architecture

### Three-Tier Structure
```
frontend/          React SPA (Business User + Expert dashboards)
    ↓ HTTPS
backend/           FastAPI (Services: Auth, Questions, Automation, Knowledge, Analytics)
    ↓
data tier          PostgreSQL + pgvector, Redis
```

### Key Services

| Service | Purpose |
|---------|---------|
| `AuthService` | JWT auth, RBAC (business_user, domain_expert, admin) |
| `QuestionsService` | Q&A lifecycle: submit → process → answer → resolve |
| `AutomationService` | Match questions to existing answers via pgvector similarity |
| `GapAnalysisService` | Analyze question against knowledge base, identify gaps |
| `KnowledgeService` | Wisdom facts, document management, semantic search |
| `NotificationService` | Real-time (WebSocket) + email notifications |
| `AIProviderService` | Abstraction over Ollama/Anthropic/Bedrock/Azure |

### Question Lifecycle
```
SUBMITTED → PROCESSING → AUTO_ANSWERED → RESOLVED
                ↓              ↓
          EXPERT_QUEUE   HUMAN_REQUESTED
                ↓              ↓
          IN_PROGRESS ←────────┘
                ↓
          ANSWERED → RESOLVED
```

### User Roles
- **business_user**: Ask questions, view own history, provide feedback
- **domain_expert**: All above + answer queue, manage knowledge, create automation
- **admin**: All above + user management, settings, full analytics

## Design System: Tufte-Inspired

The UI follows Edward Tufte's principles of information design.

### Colors
```css
--bg-primary: #FFFEF8;      /* Cream - main background */
--bg-secondary: #FAF9F6;    /* Cards */
--text-primary: #1A1A1A;    /* Near-black body text */
--ink-accent: #8B5A2B;      /* Loris brown - links, actions */
--ink-success: #2E5E4E;     /* Forest green */
--ink-warning: #8B6914;     /* Ochre */
--ink-error: #8B2E2E;       /* Burgundy */
--rule-light: #E5E4E0;      /* Hairline rules */
```

### Typography
- Primary: Georgia/Times serif for body and headings
- Secondary: IBM Plex Mono for code, data, labels
- Max content width: 65ch for readability

### What NOT to Use
- No neon/bright colors, no gradients, no glowing effects
- No rounded pill shapes (use `border-radius: 2px`)
- No box shadows on cards (flat, printed appearance)
- Status indicators are typographic, not colorful badges

### Loris Illustrations
Display as scientific illustrations (field guide style). Variants:
- Standard Loris: Welcome, general UI
- TransWarp Loris: Automated instant answer
- Research Loris: In expert queue
- Thinking Loris: Processing state
- Celebration Loris: Resolved

## Database Models

### Core Entities
- `Organization` - Multi-tenant support
- `User` - With role (business_user, domain_expert, admin)
- `Question` - With status, priority, gap_analysis JSON
- `Answer` - With source (expert, ai_approved, ai_edited, automation)
- `AutomationRule` - Canonical question/answer with similarity_threshold
- `WisdomFact` - Knowledge facts with tier (0A/0B/0C), GUD dates
- `Notification` - In-app and email notifications

### Vector Search (pgvector)
- `AutomationRuleEmbedding` - For matching questions to automation rules
- `WisdomEmbedding` - For knowledge base semantic search

Use IVFFlat index with cosine similarity: `vector_cosine_ops WITH (lists = 100)`

## API Patterns

### Endpoint Structure
```
/api/v1/auth/*          - Authentication
/api/v1/questions/*     - Q&A workflow
/api/v1/automation/*    - Automation rules
/api/v1/knowledge/*     - Knowledge/wisdom
/api/v1/notifications/* - Notifications
/api/v1/analytics/*     - Metrics
```

### Service Layer Pattern
```python
class QuestionsService:
    def __init__(self, db: AsyncSession, automation_service, gap_analysis_service, embedding_service):
        ...

    async def submit_question(self, user_id: UUID, text: str, category: str | None) -> QuestionSubmitResult:
        # 1. Create question
        # 2. Generate embedding
        # 3. Check automation match
        # 4. If match >= threshold: deliver auto-answer
        # 5. If no match: run gap analysis, queue for expert
```

## Frontend Patterns

### Component Structure
```
src/
├── components/
│   ├── ui/           # Base design system (Button, Card, Input, Table)
│   ├── loris/        # LorisIllustration component + images
│   ├── questions/    # QuestionCard, QuestionForm, AnswerView
│   └── expert/       # GapAnalysisPanel, AnswerComposer, QueueFilters
├── pages/
│   ├── user/         # Dashboard, AskQuestion, QuestionDetail
│   └── expert/       # Queue, QuestionReview, Analytics
├── contexts/         # AuthContext, NotificationContext
├── lib/api/          # API client functions
└── styles/           # globals.css, tufte.css
```

### API Client Pattern
```typescript
export const questionsApi = {
  async submit(data: QuestionSubmit): Promise<QuestionResult> {
    return apiClient.post('/questions', data);
  },
  async list(filters?: QuestionFilters): Promise<PaginatedList<Question>> {
    return apiClient.get('/questions', { params: filters });
  },
};
```

## Testing

### Backend
- Unit tests: `backend/tests/unit/services/`
- Integration tests: `backend/tests/integration/api/`
- Target: 80% coverage for services, 70% for API

### Frontend
- Component tests: `frontend/src/__tests__/components/`
- Page tests: `frontend/src/__tests__/pages/`

## Planning Documents

Read these in order for full context:
1. `docs/loris-planning/01-PROJECT-VISION.md` - What we're building
2. `docs/loris-planning/02-USER-PERSONAS.md` - User journeys
3. `docs/loris-planning/03-SYSTEM-ARCHITECTURE.md` - Technical architecture
4. `docs/loris-planning/04-DATA-MODEL.md` - Database schema
5. `docs/loris-planning/05-API-SPECIFICATION.md` - REST API details
6. `docs/loris-planning/06-AUTOMATION-WORKFLOW.md` - Auto-answering flow
7. `docs/loris-planning/08-MIGRATION-STRATEGY.md` - Implementation phases
8. `docs/loris-planning/CLAUDE-CODE-GUIDE.md` - Design system details

## Key Implementation Notes

1. **Automation threshold**: Default similarity threshold is 0.85 for auto-answering
2. **GUD (Good Until Date)**: Knowledge facts and automation rules can expire
3. **Gap analysis**: Stored as JSON on Question model for expert review
4. **Multi-provider AI**: Configure via environment, supports local (Ollama) for data privacy
5. **Real-time notifications**: WebSocket at `/api/v1/ws/notifications`
