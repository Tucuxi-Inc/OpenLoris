# Loris

**Intelligent Q&A Platform for Domain Experts**

<p align="center">
  <img src="docs/loris-planning/Loris.png" alt="Loris" width="200">
</p>

Loris connects business users with domain experts, delivering curated, expert-validated answers instead of search results. Think "Glean+" — not just finding documents, but providing actual answers.

**Legal Loris** is the first implementation, focused on legal departments.

## How It Works

<table>
<tr>
<td width="25%" align="center">
<img src="docs/loris-planning/Thinking_Loris.png" width="100"><br>
<strong>1. Ask</strong><br>
<em>User submits question</em>
</td>
<td width="25%" align="center">
<img src="docs/loris-planning/TransWarp_Loris.png" width="100"><br>
<strong>2. Check</strong><br>
<em>System checks for automation match</em>
</td>
<td width="25%" align="center">
<img src="docs/loris-planning/Scholar_Loris.png" width="100"><br>
<strong>3. Analyze</strong><br>
<em>AI performs gap analysis</em>
</td>
<td width="25%" align="center">
<img src="docs/loris-planning/Celebration_Loris.png" width="100"><br>
<strong>4. Answer</strong><br>
<em>Expert validates & delivers</em>
</td>
</tr>
</table>

## Key Features

- **Turbo Loris** — User-controlled fast-answer mode that delivers AI-generated responses instantly when knowledge confidence exceeds a user-selected threshold (50%/75%/90%)
- **Progressive Automation** — Each answered question can become an automated response for similar future questions
- **Gap Analysis** — AI identifies what's covered by existing knowledge and what needs expert input
- **Knowledge Base** — Upload documents, extract facts, build an organizational knowledge graph
- **Analytics Dashboard** — Track automation performance, question trends, knowledge coverage
- **Sub-Domain Routing** — Questions routed to the right experts based on sub-domain classification (manual or AI)
- **Reassignment Workflow** — Experts can flag misrouted questions; admins approve reassignments
- **Department & Org Settings** — Configurable departments, required fields, admin settings panel
- **In-App Notifications** — Real-time alerts for answers, assignments, routing, expiring content
- **GUD Enforcement** — "Good Until Date" system automatically expires and deactivates stale content
- **Multi-Provider AI** — Supports Ollama (local + cloud), Anthropic Claude, AWS Bedrock, Azure OpenAI
- **Data Privacy** — Local Ollama models keep data on-premise; Ollama cloud uses encrypted transport with no prompt/output retention
- **MoltenLoris** — Coming soon: autonomous Slack-monitoring agent powered by your knowledge base

## Prerequisites

- **Docker Desktop** — [Install Docker](https://www.docker.com/products/docker-desktop/)
- **Ollama** — [Install Ollama](https://ollama.ai) (runs on your host machine, not inside Docker)

## Quick Start

### 1. Clone and start

```bash
git clone https://github.com/Tucuxi-Inc/Loris.git
cd Loris

# Copy environment config (defaults work out of the box)
cp .env.example .env

# Start all services
docker-compose up -d
```

This starts four containers:

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3005 | React app |
| Backend API | http://localhost:8005 | FastAPI REST API |
| API Docs | http://localhost:8005/docs | Swagger/OpenAPI interactive docs |
| PostgreSQL | localhost:5435 | Database with pgvector extension |
| Redis | localhost:6385 | Cache |

### 2. Pull Ollama models

Ollama must be running on your host machine. The backend connects to it from Docker via `host.docker.internal`.

```bash
# Required: embedding model for automation matching (274 MB)
ollama pull nomic-embed-text

# Default inference model (runs on Ollama cloud - works on any machine)
ollama pull qwen3-vl:235b-cloud

# Fallback inference model
ollama pull gpt-oss:120b-cloud
```

**Cloud models** (names ending in `-cloud`) run on Ollama's infrastructure. Traffic is encrypted and prompts/outputs are not stored. AI features work on any machine regardless of local GPU capacity.

If you prefer fully local inference, edit `.env` and set `OLLAMA_MODEL` to any local model (e.g., `llama3.2`).

**Note:** If Ollama is unavailable, the embedding service falls back to a hash-based approximation. This is fine for development but won't produce meaningful automation matches.

### 3. Verify

```bash
# Backend health check
curl http://localhost:8005/health
# Expected: {"status":"healthy","service":"loris-api"}

# Open the app
open http://localhost:3005
```

### 4. Log in

The login page has **quick-login buttons** for three dev accounts. On first click, each account is auto-registered; subsequent clicks log in:

| Account | Email | Role | What they can do |
|---------|-------|------|------------------|
| Carol | carol@loris.dev | Business User | Ask questions, view answers, give feedback |
| Bob | bob@loris.dev | Domain Expert | All above + answer queue, knowledge base, documents, analytics |
| Alice | alice@loris.dev | Admin | All above + user management, sub-domains, settings |

Password for all: `Test1234!`

### 5. Try the workflow

1. Log in as **Carol**, ask a question
2. Log in as **Bob**, go to Queue, assign the question, answer it
3. Log in as **Carol**, see the answer, give a 5-star rating
4. Log in as **Bob**, go to the answered question, click "Create Automation Rule"
5. Log in as **Carol**, ask a similar question — it gets auto-answered instantly
6. Check **Analytics** (Bob or Alice) to see the metrics

## Database

### No migrations required

Tables are auto-created on backend startup via SQLAlchemy's `Base.metadata.create_all()`. There are no Alembic migrations. When you run `docker-compose up`, the backend creates all tables automatically.

The PostgreSQL init script (`database/init.sql`) only installs the `uuid-ossp` and `vector` extensions.

### Resetting the database

To drop all data and start fresh:

```bash
docker exec loris-postgres-1 psql -U loris -d loris -c \
  "DROP SCHEMA public CASCADE; CREATE SCHEMA public; \
   CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"; \
   CREATE EXTENSION IF NOT EXISTS \"vector\";"
docker-compose restart backend
```

Tables are recreated automatically on backend restart. Dev accounts will need to be re-registered (just click the quick-login buttons on the login page).

### Linux note

On Linux, Docker containers may not resolve `host.docker.internal` by default. Add this to the `backend` service in `docker-compose.yml`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## Development

### Rebuilding after code changes

```bash
# Rebuild backend
docker-compose up -d --build backend

# Rebuild frontend (needed after adding new dependencies)
docker-compose up -d --build frontend

# Restart frontend (needed after adding new .tsx files for Vite to detect them)
docker-compose restart frontend

# View backend logs
docker logs loris-backend-1 -f
```

### Running locally (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

Requires PostgreSQL with pgvector and Redis running locally. Update `DATABASE_URL` and `REDIS_URL` in `.env` accordingly.

### Optional admin tools

```bash
# Start with pgAdmin and Redis Commander
docker-compose --profile tools up -d

# pgAdmin: http://localhost:5055 (admin@loris.dev / admin)
# Redis Commander: http://localhost:8085
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 15 + pgvector |
| Cache | Redis 7 |
| Frontend | React 18, TypeScript 5+, Vite, Tailwind CSS |
| Charts | Recharts |
| Scheduler | APScheduler (in-process, daily GUD checks) |
| AI (Inference) | Ollama (local/cloud), Anthropic, AWS Bedrock, Azure OpenAI |
| AI (Embeddings) | Ollama nomic-embed-text (768 dimensions) |

## Project Structure

```
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── main.py         # App factory, router registration, scheduler lifecycle
│   │   ├── api/v1/         # REST endpoints
│   │   │   ├── auth.py     # Register, login, JWT tokens
│   │   │   ├── questions.py # Q&A lifecycle + automation integration
│   │   │   ├── automation.py # Automation rule CRUD
│   │   │   ├── knowledge.py # Knowledge facts, search, gap analysis
│   │   │   ├── documents.py # Document upload, extraction, GUD
│   │   │   ├── analytics.py # Metrics dashboard (5 endpoints)
│   │   │   ├── notifications.py # Notification list, read, dismiss
│   │   │   ├── users.py    # User management (admin)
│   │   │   ├── subdomains.py # Sub-domain CRUD, routing, reassignment
│   │   │   ├── org_settings.py # Organization settings
│   │   │   └── settings.py # AI provider config
│   │   ├── models/         # SQLAlchemy models (18 tables)
│   │   ├── services/       # Business logic
│   │   │   ├── analytics_service.py    # Metrics computation
│   │   │   ├── automation_service.py   # Matching + auto-answer delivery
│   │   │   ├── knowledge_service.py    # Semantic search, gap analysis
│   │   │   ├── document_service.py     # PDF/DOCX parsing, fact extraction
│   │   │   ├── notification_service.py # Notification lifecycle
│   │   │   ├── scheduler_service.py    # Daily GUD expiry checks
│   │   │   ├── embedding_service.py    # Ollama + hash fallback
│   │   │   ├── subdomain_service.py   # AI classification, SLA monitoring
│   │   │   └── ai_provider_service.py  # Multi-provider AI abstraction
│   │   └── core/           # Config, database setup
│   └── Dockerfile
├── frontend/               # React application
│   └── src/
│       ├── components/     # Layout, NotificationBell
│       ├── contexts/       # Auth state
│       ├── pages/          # User, Expert, Admin, Notifications
│       │   ├── user/       # Dashboard, QuestionDetail
│       │   ├── expert/     # Dashboard, Queue, Knowledge, Documents, Analytics
│       │   └── admin/      # UserManagement, SubDomains, Reassignments, OrgSettings
│       ├── lib/api/        # API clients (questions, knowledge, documents, analytics, etc.)
│       └── styles/         # Tufte design system
├── database/               # init.sql (pgvector extension)
├── docs/                   # Planning documentation
├── docker-compose.yml
└── .env.example
```

## API Endpoints

All endpoints are documented in the interactive Swagger UI at http://localhost:8005/docs.

| Group | Prefix | Endpoints | Auth |
|-------|--------|-----------|------|
| Auth | `/api/v1/auth` | Register, login, refresh, profile | Public (register/login) |
| Questions | `/api/v1/questions` | Submit, list, detail, feedback, accept/reject auto-answer, expert queue, assign, answer, clarification | User+ |
| Automation | `/api/v1/automation` | Rule CRUD, create from answered question | Expert+ |
| Knowledge | `/api/v1/knowledge` | Facts CRUD, semantic search, gap analysis, stats | Expert+ |
| Documents | `/api/v1/documents` | Upload, extraction, fact candidates, GUD, departments | Expert+ |
| Analytics | `/api/v1/analytics` | Overview, question trends, automation performance, knowledge coverage, expert performance | Expert+ |
| Notifications | `/api/v1/notifications` | Unread count, list, mark read, dismiss | User+ |
| Users | `/api/v1/users` | User CRUD, role/status management, sub-domain assignment | Admin |
| Sub-Domains | `/api/v1/subdomains` | CRUD, expert assignment, routing, reassignment | Admin (CRUD), User+ (list), Expert+ (detail/routing) |
| Org Settings | `/api/v1/org` | Department management, question requirements | Admin (write), User+ (read) |
| Settings | `/api/v1/settings` | AI provider config, available models | Expert+ |

## AI Provider Configuration

Edit `.env` to switch AI providers:

| Provider | `AI_PROVIDER` value | Requires |
|----------|-------------------|----------|
| Ollama (default) | `local_ollama` | Ollama running on host |
| Anthropic Claude | `cloud_anthropic` | `ANTHROPIC_API_KEY` |
| AWS Bedrock | `cloud_bedrock` | AWS credentials configured |
| Azure OpenAI | `cloud_azure` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY` |

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0: Foundation | Complete | Docker, project structure, branding |
| Phase 1: Auth | Complete | JWT auth, RBAC, registration |
| Phase 2: Questions | Complete | Full Q&A lifecycle, expert queue, feedback |
| Phase 3: Automation | Complete | Rule CRUD, embedding matching, auto-answer delivery |
| Phase 4: Knowledge + Documents + UI | Complete | Knowledge base, document management, role-based UI |
| Phase 5: Notifications & GUD | Complete | In-app notifications, scheduled GUD enforcement |
| Phase 6: Analytics | Complete | Metrics dashboard, question trends, automation performance |
| Phase 6.5: Sub-Domain Routing & Org Settings | Complete | Sub-domains, expert routing, reassignment, departments, org settings |
| Phase 8: Turbo Loris | Complete | User-controlled fast-answer mode with confidence thresholds, MoltenLoris placeholder |
| Phase 7: Testing & Docs | Not started | Unit/integration tests, Alembic migrations |

## Documentation

See `docs/loris-planning/` for detailed planning documents:
- [Project Vision](docs/loris-planning/01-PROJECT-VISION.md)
- [User Personas](docs/loris-planning/02-USER-PERSONAS.md)
- [System Architecture](docs/loris-planning/03-SYSTEM-ARCHITECTURE.md)
- [Data Model](docs/loris-planning/04-DATA-MODEL.md)
- [API Specification](docs/loris-planning/05-API-SPECIFICATION.md)
- [Automation Workflow](docs/loris-planning/06-AUTOMATION-WORKFLOW.md)
- [Migration Strategy](docs/loris-planning/08-MIGRATION-STRATEGY.md)

## License

Proprietary — Tucuxi Inc.
