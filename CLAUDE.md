# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Loris** is an intelligent Q&A platform that connects business users with domain experts. It delivers curated, expert-validated answers instead of search results ("Glean+"). **Legal Loris** is the first implementation, focused on legal departments.

Core workflow: User asks question → System checks automation rules → If match: instant answer (TransWarp) → If no match: expert queue with gap analysis → Expert answers → Expert can elect to create automation rule for similar future questions.

**Important:** Auto-answering only happens when a domain expert has explicitly created an automation rule from an answered question. There is no automatic rule creation.

**Tagline:** "Slow is smooth, smooth is fast"

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0: Preparation | COMPLETE | Docker, project structure, README, Loris branding |
| Phase 1: Auth | COMPLETE | JWT auth, RBAC, registration returns tokens |
| Phase 2: Questions | COMPLETE | Full Q&A lifecycle, expert queue, feedback |
| Phase 3: Automation | COMPLETE | AutomationRule CRUD, embedding matching, auto-answer delivery |
| Phase 4: Knowledge + Documents + UI | COMPLETE | Knowledge base, document management, role-based UI, user management |
| Phase 5: GUD & Notifications | NOT STARTED | WebSocket notifications, scheduled expiry checks |
| Phase 6: Analytics | NOT STARTED | Metrics dashboard, automation performance |
| Phase 7: Testing & Docs | NOT STARTED | Unit/integration tests, documentation |

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 15 + pgvector for semantic search |
| Cache | Redis 7 |
| Frontend | React 18, TypeScript 5+, Vite, Tailwind CSS |
| AI | Multi-provider: Ollama (local), Anthropic Claude, AWS Bedrock, Azure OpenAI |
| Embeddings | Ollama nomic-embed-text (768 dims), hash-based fallback |
| Background Jobs | Celery + Redis (planned) |
| Real-time | WebSockets (planned) |

## Ollama Models Required

| Model | Purpose | Pull Command |
|-------|---------|--------------|
| `nomic-embed-text` | **Primary embedding model** (768 dims) for automation matching | `ollama pull nomic-embed-text` |
| `qwen3-vl:235b-cloud` | **Default inference model** for gap analysis and AI features | `ollama pull qwen3-vl:235b-cloud` |
| `gpt-oss:120b-cloud` | **Fallback inference model** if primary unavailable | `ollama pull gpt-oss:120b-cloud` |

Cloud models (names ending in `-cloud`) run on Ollama's infrastructure. Traffic is encrypted and Ollama does not store prompts or outputs.

**Ollama access from Docker:** The backend container reaches Ollama at `http://host.docker.internal:11434`. On Linux, you may need `--add-host=host.docker.internal:host-gateway` in docker-compose.yml.

If Ollama is unavailable, the embedding service falls back to a hash-based TF-IDF embedding for development/testing.

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

# Restart frontend (needed after adding new files for Vite to pick them up)
docker-compose restart frontend

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
frontend/          React SPA (Business User + Expert + Admin dashboards)
    ↓ Vite proxy (/api → backend:8000)
backend/           FastAPI (Services: Auth, Questions, Automation, Knowledge, Documents, Users)
    ↓
data tier          PostgreSQL + pgvector, Redis
    ↓
Ollama             Local LLM + embeddings (host machine)
```

**Important:** `VITE_API_URL` must be empty/unset in docker-compose.yml so all `/api` calls go through the Vite proxy. Do not set it to `http://localhost:8005` — that causes split routing issues between AuthContext (which uses bare `/api` paths) and the apiClient.

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
│   ├── automation.py                # AutomationRule, Embedding, Log models
│   ├── wisdom.py                    # WisdomFact, WisdomEmbedding, WisdomTier
│   └── documents.py                 # KnowledgeDocument, DocumentChunk, ExtractedFactCandidate, Department
├── api/v1/
│   ├── health.py                    # /health endpoint
│   ├── auth.py                      # Register, login, /me, JWT tokens
│   ├── questions.py                 # Q&A workflow + automation + gap analysis integration
│   ├── automation.py                # CRUD for automation rules
│   ├── knowledge.py                 # Knowledge facts CRUD, search, stats, gap analysis
│   ├── documents.py                 # Document upload, extraction, GUD, departments
│   └── users.py                     # User CRUD, role/status management (admin-only)
└── services/
    ├── ai_provider_service.py       # Multi-provider AI (Ollama/Anthropic/etc.)
    ├── embedding_service.py         # Embeddings (Ollama → hash fallback)
    ├── automation_service.py        # Matching, auto-answer delivery, metrics
    ├── knowledge_service.py         # Knowledge facts CRUD, semantic search, gap analysis
    ├── document_service.py          # Document upload, parsing, fact extraction
    └── document_expiration_service.py  # GUD enforcement, expiry checks, renewal
```

### Frontend File Structure
```
frontend/src/
├── App.tsx                          # Role-based routing
├── contexts/AuthContext.tsx         # Auth state, isExpert, isAdmin helpers
├── components/Layout.tsx            # Role-aware navigation
├── lib/api/
│   ├── client.ts                    # Axios client with auth interceptors
│   ├── questions.ts                 # Q&A API client
│   ├── knowledge.ts                 # Knowledge facts API (normalizes backend response shapes)
│   ├── documents.ts                 # Documents API (upload, extraction, GUD)
│   └── users.ts                     # User management API (CRUD, role, status)
├── pages/
│   ├── LoginPage.tsx                # Splash page with hero, login, dev quick-login buttons
│   ├── user/
│   │   ├── DashboardPage.tsx        # Business user dashboard (wired to API)
│   │   └── QuestionDetailPage.tsx   # Question detail with auto-answer accept/reject, feedback
│   ├── expert/
│   │   ├── ExpertDashboard.tsx      # Expert landing (metrics, queue preview, knowledge summary)
│   │   ├── ExpertQueuePage.tsx      # Expert queue (wired to API, filters, pagination)
│   │   ├── ExpertQuestionDetail.tsx # Question + gap analysis + answer form
│   │   ├── KnowledgeManagementPage.tsx  # Facts CRUD, search, tier management
│   │   └── DocumentManagementPage.tsx   # Upload, extraction, candidate review, GUD
│   └── admin/
│       └── UserManagementPage.tsx   # User CRUD, role changes, activate/deactivate
└── styles/globals.css               # Tufte design system
```

### Key Services

| Service | File | Purpose |
|---------|------|---------|
| Auth | `api/v1/auth.py` | JWT auth, RBAC (business_user, domain_expert, admin) |
| Questions | `api/v1/questions.py` | Q&A lifecycle: submit → check automation → answer → resolve |
| Automation API | `api/v1/automation.py` | CRUD for automation rules, create-from-answer |
| Knowledge API | `api/v1/knowledge.py` | Facts CRUD, semantic search, gap analysis, stats |
| Documents API | `api/v1/documents.py` | Upload, parsing, fact extraction, GUD management |
| Users API | `api/v1/users.py` | User CRUD (admin), role/status management |
| AutomationService | `services/automation_service.py` | Cosine similarity matching, auto-answer delivery |
| KnowledgeService | `services/knowledge_service.py` | Semantic search, gap analysis, fact lifecycle |
| DocumentService | `services/document_service.py` | Document ingestion, parsing (PDF/DOCX/TXT), fact extraction |
| DocumentExpirationService | `services/document_expiration_service.py` | GUD enforcement, expiry checking, renewal |
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

### Gap Analysis Integration
When a question enters EXPERT_QUEUE or gets HUMAN_REQUESTED, the system runs gap analysis (non-blocking, try/except):
1. Searches knowledge base for relevant WisdomFacts via semantic similarity
2. Calls AI to analyze coverage gaps and propose an answer
3. Stores result in `question.gap_analysis` JSONB field
4. Expert sees the analysis when viewing the question, with a pre-populated answer they can edit

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

### User Roles & Navigation
- **business_user**: My Questions, Ask Question
- **domain_expert**: All above + Expert Dashboard, Queue, Knowledge, Documents
- **admin**: All above + User Management

### API Response Shape Normalization
The frontend API clients normalize backend response shapes:
- Backend returns `{facts: [...]}` → frontend normalizes to `{items: [...]}`
- Backend returns `{documents: [...]}` → frontend normalizes to `{items: [...]}`
- Backend stats returns `{tier_counts, domains_covered, facts_expiring_soon}` → frontend normalizes to `{by_tier, by_domain, expiring_soon}`

This translation happens in `frontend/src/lib/api/knowledge.ts` and `documents.ts`.

## Key Bugs Fixed (For Reference)

These patterns should be followed to avoid regressions:

1. **SQLAlchemy Enum values**: Use `SAEnum(MyEnum, values_callable=lambda obj: [e.value for e in obj])` to store lowercase values in PostgreSQL
2. **Async lazy loading**: Never access relationships like `question.answer` in async context. Use explicit queries: `select(Answer).where(Answer.question_id == id)`
3. **Timezone handling**: Use `datetime.now(timezone.utc)` not `datetime.utcnow()` when comparing with `DateTime(timezone=True)` columns
4. **bcrypt compatibility**: Pin `bcrypt==4.0.1` in requirements.txt for passlib compatibility
5. **Pydantic model ordering**: Define referenced models before models that reference them
6. **Registration endpoint**: Returns tokens + user data via `RegisterResponse` schema
7. **VITE_API_URL must be empty**: Set `VITE_API_URL=` (empty) in docker-compose.yml so all API calls route through the Vite proxy. Setting it to a URL causes split routing between AuthContext and apiClient.
8. **Docker file detection**: After creating new frontend files, run `docker-compose restart frontend` for Vite to detect them.
9. **Tailwind `text-accent` is invisible**: The accent color (`hsl(40 10% 96%)`) is nearly identical to the cream background. Use `text-ink-secondary` or `text-ink-primary` for visible text.

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

**Note:** `text-accent` in Tailwind maps to `hsl(40 10% 96%)` which is a near-white cream. Do not use it for text — it's invisible against the background. Use `text-ink-secondary` instead.

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
- `WisdomFact` - Knowledge facts with tier (0A/0B/0C), GUD dates, usage tracking
- `WisdomEmbedding` - For knowledge base semantic search
- `KnowledgeDocument` - Uploaded documents with parsing/extraction status, GUD
- `DocumentChunk` - Parsed document chunks with embeddings
- `ChunkEmbedding` - Chunk-level embeddings for search
- `ExtractedFactCandidate` - AI-extracted facts pending expert review
- `Department` - Organization departments for document ownership

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

### Knowledge (`/api/v1/knowledge/`)
- `GET /facts` - List facts (filterable by category, tier, domain, paginated)
- `GET /facts/{id}` - Get single fact
- `POST /facts` - Create fact directly
- `POST /facts/from-answer` - Create fact from answered question
- `PUT /facts/{id}` - Update fact (regenerates embedding if content changed)
- `DELETE /facts/{id}` - Soft-archive fact
- `GET /search` - Semantic search (query param `q`)
- `POST /analyze-gaps` - Run gap analysis on arbitrary text
- `GET /stats` - Knowledge base statistics
- `GET /expiring` - Facts expiring within N days

### Documents (`/api/v1/documents/`)
- `POST /upload` - Upload document (multipart form with metadata + GUD fields)
- `GET /` - List documents (filterable, paginated)
- `GET /{id}` - Document detail + processing status
- `PUT /{id}` - Update metadata and GUD
- `DELETE /{id}` - Delete document
- `POST /{id}/extract` - Trigger fact extraction
- `GET /{id}/facts` - Extracted fact candidates
- `POST /facts/{candidate_id}/approve` - Approve → create WisdomFact
- `POST /facts/{candidate_id}/reject` - Reject with reason
- `POST /{id}/extend` - Extend GUD
- `GET /expiring/list` - Documents expiring soon
- `GET /departments/list` - List departments
- `POST /departments` - Create department

### Users (`/api/v1/users/`)
- `GET /` - List users in organization (expert+)
- `GET /{id}` - User detail (expert+)
- `POST /` - Create user (admin-only)
- `PUT /{id}` - Edit user details (admin-only)
- `DELETE /{id}` - Delete user (admin-only, cannot delete self)
- `PUT /{id}/role` - Update role (admin-only, cannot change own role)
- `PUT /{id}/status` - Activate/deactivate (admin-only, cannot change own status)

### Settings (`/api/v1/settings/`)
- `GET /ai-provider` - Current AI provider config (expert-only)
- `GET /ollama-models` - List available Ollama models (expert-only)

## Frontend Pages

### Login / Splash Page
- Hero section with Loris logo, title, tagline
- "Have a question? Get a definitive answer from Loris."
- Standard login form
- Dev quick-login buttons for test accounts (Carol=business_user, Bob=expert, Alice=admin, password: `Test1234!`)

### Role-Based Dashboard
- **Business users** → `/dashboard` — actionable items first (auto-answered, needs attention), question list with status filters
- **Experts** → `/expert` — metrics (pending queue, fact count, expiring), queue preview, knowledge summary
- **All** → role-appropriate navigation in sidebar

### Test Accounts (Development)
After fresh DB reset, register via the splash page quick-login buttons or manually:
- `carol@loris.dev` / `Test1234!` — business_user
- `bob@loris.dev` / `Test1234!` — domain_expert
- `alice@loris.dev` / `Test1234!` — admin

Note: Quick-login buttons attempt login first, then auto-register if the account doesn't exist. After DB reset, first click registers; subsequent clicks login.

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
4. **GUD (Good Until Date)**: Automation rules, knowledge facts, and documents can have expiry dates.
5. **Gap analysis**: Run when questions enter expert queue. Stored as JSON on Question model. Expert sees proposed answer pre-populated in answer form.
6. **Multi-provider AI**: Configure via AI_PROVIDER env var. Supports local (Ollama) for data privacy.
7. **Database reset**: Tables auto-created on backend startup via `init_db()`. No Alembic migrations yet.
8. **Document parsing**: Supports PDF (pdfplumber), DOCX (python-docx), TXT. Documents are chunked and facts extracted by AI.
9. **Knowledge tiers**: tier_0a (authoritative), tier_0b (expert-validated), tier_0c (AI-generated), pending, archived.
