# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Loris** is an intelligent Q&A platform that connects business users with domain experts. It delivers curated, expert-validated answers instead of search results ("Glean+"). **Legal Loris** is the first implementation, focused on legal departments.

Core workflow: User asks question → System checks automation rules → If match: instant answer (TransWarp) → If no match: expert queue with gap analysis → Expert answers → Expert can elect to create automation rule for similar future questions.

**Important:** Auto-answering only happens when a domain expert has explicitly created an automation rule from an answered question. There is no automatic rule creation.

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0: Preparation | COMPLETE | Docker, project structure, README, Loris branding |
| Phase 1: Auth | COMPLETE | JWT auth, RBAC, registration returns tokens |
| Phase 2: Questions | COMPLETE | Full Q&A lifecycle, expert queue, feedback |
| Phase 3: Automation | COMPLETE | AutomationRule CRUD, embedding matching, auto-answer delivery |
| Phase 4: Gap Analysis | NOT STARTED | Knowledge base search, AI gap analysis for experts |
| Phase 5: GUD & Notifications | NOT STARTED | Good Until Date management, WebSocket notifications |
| Phase 6: Analytics | NOT STARTED | Metrics dashboard, automation performance |
| Phase 7: Testing & Docs | NOT STARTED | Unit/integration tests, documentation |

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 15 + pgvector for semantic search |
| Cache | Redis 7 |
| Frontend | React 18, TypeScript 5+, Vite, Tailwind CSS |
| State | React Query + Zustand (planned) |
| Components | Radix UI primitives (planned) |
| AI | Multi-provider: Ollama (local), Anthropic Claude, AWS Bedrock, Azure OpenAI |
| Embeddings | Ollama nomic-embed-text (768 dims), hash-based fallback |
| Background Jobs | Celery + Redis (planned) |
| Real-time | WebSockets (planned) |

## Ollama Models Required

The system expects these Ollama models to be available:

| Model | Purpose | Pull Command |
|-------|---------|--------------|
| `nomic-embed-text` | **Primary embedding model** (768 dims) for automation matching | `ollama pull nomic-embed-text` |
| `qwen3-vl:235b-cloud` | **Default inference model** for gap analysis and AI features | `ollama pull qwen3-vl:235b-cloud` |
| `gpt-oss:120b-cloud` | **Fallback inference model** if primary unavailable | `ollama pull gpt-oss:120b-cloud` |

Cloud models (names ending in `-cloud`) run on Ollama's infrastructure. Traffic is encrypted and Ollama does not store prompts or outputs. This provides a good balance of privacy and performance — works on any machine without local GPU requirements.

Domain experts can select a different inference model from any model available on their Ollama instance via the Settings API (`GET /api/v1/settings/ollama-models`).

**Alternative embedding models** available but not default:
- `qwen3-embedding:0.6b` (639 MB)
- `granite-embedding:278m` (562 MB)
- `embeddinggemma:latest` (621 MB)

**Ollama access from Docker:** The backend container reaches Ollama at `http://host.docker.internal:11434`. This works on macOS Docker Desktop. On Linux, you may need `--add-host=host.docker.internal:host-gateway` in docker-compose.yml.

If Ollama is unavailable, the embedding service falls back to a hash-based TF-IDF embedding that produces reasonable similarity scores for development/testing.

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

# Rebuild backend after code changes
docker-compose up -d --build backend

# Reset database (drops all data)
docker exec loris-postgres-1 psql -U loris -d loris -c \
  "DROP SCHEMA public CASCADE; CREATE SCHEMA public; \
   CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"; \
   CREATE EXTENSION IF NOT EXISTS \"vector\";"
docker-compose restart backend

# View backend logs
docker logs loris-backend-1 -f

# Backend only (with hot reload)
docker-compose up backend

# Frontend only (Vite dev server)
cd frontend && npm run dev
```

## Architecture

### Three-Tier Structure
```
frontend/          React SPA (Business User + Expert dashboards)
    ↓ HTTPS
backend/           FastAPI (Services: Auth, Questions, Automation, Knowledge, Analytics)
    ↓
data tier          PostgreSQL + pgvector, Redis
    ↓
Ollama             Local LLM + embeddings (host machine)
```

### Backend File Structure
```
backend/app/
├── main.py                          # FastAPI app factory, router registration
├── core/
│   ├── config.py                    # Pydantic settings (ports, AI, JWT, etc.)
│   └── database.py                  # Async SQLAlchemy engine + session
├── models/
│   ├── __init__.py                  # Model registry (import all models here)
│   ├── base.py                      # Base, UUIDMixin, TimestampMixin
│   ├── organization.py              # Multi-tenant Organization
│   ├── user.py                      # User with UserRole enum
│   ├── questions.py                 # Question, QuestionMessage, status enums
│   ├── answers.py                   # Answer with AnswerSource enum
│   └── automation.py                # AutomationRule, Embedding, Log models
├── api/v1/
│   ├── health.py                    # /health endpoint
│   ├── auth.py                      # Register, login, /me, JWT tokens
│   ├── questions.py                 # Q&A workflow + automation integration
│   └── automation.py                # CRUD for automation rules
└── services/
    ├── ai_provider_service.py       # Multi-provider AI (Ollama/Anthropic/etc.)
    ├── embedding_service.py         # Embeddings (Ollama → hash fallback)
    └── automation_service.py        # Matching, auto-answer delivery, metrics
```

### Key Services

| Service | File | Purpose |
|---------|------|---------|
| Auth | `api/v1/auth.py` | JWT auth, RBAC (business_user, domain_expert, admin) |
| Questions | `api/v1/questions.py` | Q&A lifecycle: submit → check automation → answer → resolve |
| Automation API | `api/v1/automation.py` | CRUD for automation rules, create-from-answer |
| AutomationService | `services/automation_service.py` | Cosine similarity matching, auto-answer delivery, metrics |
| EmbeddingService | `services/embedding_service.py` | Vector embeddings via Ollama nomic-embed-text |
| AIProviderService | `services/ai_provider_service.py` | Abstraction over Ollama/Anthropic/Bedrock/Azure |

### Question Lifecycle
```
SUBMITTED → (automation check) → AUTO_ANSWERED → RESOLVED (user accepts)
                 ↓                    ↓
           EXPERT_QUEUE          HUMAN_REQUESTED (user rejects)
                 ↓                    ↓
           IN_PROGRESS ←──────────────┘
                 ↓
           ANSWERED → RESOLVED (user gives feedback)
```

### Automation Flow (Expert-Driven)
```
1. Question arrives → checked against automation rules
2. If NO rules match → goes to expert queue
3. Expert answers manually
4. Expert EXPLICITLY creates automation rule from that Q&A pair
5. Future similar questions auto-answered by that rule
6. User can accept (→ resolved) or reject (→ expert queue)
7. Metrics tracked: triggered, accepted, rejected
```

### User Roles
- **business_user**: Ask questions, view own history, provide feedback, accept/reject auto-answers
- **domain_expert**: All above + answer queue, create automation rules, manage knowledge
- **admin**: All above + user management, settings, full analytics

## Key Bugs Fixed (For Reference)

These patterns should be followed to avoid regressions:

1. **SQLAlchemy Enum values**: Use `SAEnum(MyEnum, values_callable=lambda obj: [e.value for e in obj])` to store lowercase values in PostgreSQL
2. **Async lazy loading**: Never access relationships like `question.answer` in async context. Use explicit queries: `select(Answer).where(Answer.question_id == id)`
3. **Timezone handling**: Use `datetime.now(timezone.utc)` not `datetime.utcnow()` when comparing with `DateTime(timezone=True)` columns
4. **bcrypt compatibility**: Pin `bcrypt==4.0.1` in requirements.txt for passlib compatibility
5. **Pydantic model ordering**: Define referenced models before models that reference them (e.g., `AnswerResponse` before `QuestionSubmitResponse`)
6. **Registration endpoint**: Returns tokens + user data via `RegisterResponse` schema

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

### Core Entities (Implemented)
- `Organization` - Multi-tenant support (slug, domain, settings JSONB)
- `User` - With role (business_user, domain_expert, admin), auth, preferences
- `Question` - Full lifecycle with status, priority, gap_analysis JSONB, metrics
- `QuestionMessage` - Clarification threading
- `Answer` - With source (expert, ai_approved, ai_edited, automation), citations JSONB
- `AutomationRule` - Canonical Q&A pair, similarity_threshold, GUD date, metrics
- `AutomationRuleEmbedding` - JSONB embedding_data, model_name
- `AutomationLog` - Audit trail (matched, delivered, accepted, rejected)

### Planned Entities (Not Yet Implemented)
- `WisdomFact` - Knowledge facts with tier (0A/0B/0C), GUD dates
- `WisdomEmbedding` - For knowledge base semantic search
- `Notification` - In-app and email notifications
- `DailyMetrics` - Aggregated analytics

### Vector Search
Currently using JSONB for embedding storage with application-level cosine similarity.
For production scale, migrate to native pgvector columns with IVFFlat index.

## API Endpoints (Implemented)

### Auth (`/api/v1/auth/`)
- `POST /register` - Register user (returns tokens) - accepts organization_name, role
- `POST /login` - OAuth2 form login
- `POST /refresh` - Refresh JWT token
- `GET /me` - Current user info
- `PUT /me` - Update profile

### Questions (`/api/v1/questions/`)
- `POST /` - Submit question (checks automation, returns auto-answer if matched)
- `GET /` - List own questions
- `GET /{id}` - Question detail
- `POST /{id}/feedback` - Rate answer (1-5)
- `POST /{id}/accept-auto` - Accept auto-answer
- `POST /{id}/request-human` - Reject auto-answer, request expert
- `GET /queue/pending` - Expert queue (expert-only)
- `POST /{id}/assign` - Claim question (expert-only)
- `POST /{id}/answer` - Submit answer (expert-only)
- `POST /{id}/request-clarification` - Ask for more info (expert-only)

### Automation (`/api/v1/automation/`)
- `GET /rules` - List rules (expert-only)
- `GET /rules/{id}` - Get rule detail
- `POST /rules` - Create rule directly
- `POST /rules/from-answer` - Create rule from answered question
- `PUT /rules/{id}` - Update rule
- `DELETE /rules/{id}` - Delete rule

### Settings (`/api/v1/settings/`)
- `GET /ai-provider` - Current AI provider config (expert-only)
- `GET /ollama-models` - List available Ollama models (expert-only)

## Frontend State

Frontend pages are scaffolded with placeholder data. They need to be wired to real API endpoints:
- `LoginPage.tsx` - Working (uses AuthContext)
- `DashboardPage.tsx` - Placeholder data
- `AskQuestionPage.tsx` - Placeholder data
- `ExpertQueuePage.tsx` - Placeholder data

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

1. **Automation is expert-driven**: Only domain experts can create automation rules. Rules are created explicitly from answered Q&A pairs.
2. **Default similarity threshold**: 0.85 for auto-answering (configurable per rule)
3. **Embedding model**: nomic-embed-text via Ollama (768 dimensions). Hash fallback for dev without Ollama.
4. **GUD (Good Until Date)**: Automation rules can have expiry dates. Expired rules stop matching.
5. **Gap analysis**: Stored as JSON on Question model for expert review
6. **Multi-provider AI**: Configure via AI_PROVIDER env var. Supports local (Ollama) for data privacy.
7. **Database reset**: Tables auto-created on backend startup via `init_db()`. No Alembic migrations yet.
