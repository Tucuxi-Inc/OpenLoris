# Loris

**Intelligent Q&A Platform for Domain Experts**

<p align="center">
  <img src="docs/loris-planning/Loris.png" alt="Loris" width="200">
</p>

Loris connects business users with domain experts, delivering curated, expert-validated answers instead of search results. Think "Glean+" — not just finding documents, but providing actual answers.

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

- **Progressive Automation** — Each answered question can become an automated response for similar future questions
- **Gap Analysis** — AI identifies what's covered by existing knowledge and what needs expert input
- **Multi-Provider AI** — Supports Ollama (local + cloud), Anthropic Claude, AWS Bedrock, Azure OpenAI
- **Data Privacy** — Local Ollama models keep data on-premise; Ollama cloud models use encrypted transport with no prompt/output retention
- **Expert Workflow** — Approve, edit, or request clarification with AI-assisted drafts

## Prerequisites

- **Docker Desktop** — [Install Docker](https://www.docker.com/products/docker-desktop/)
- **Ollama** — [Install Ollama](https://ollama.ai) (runs on your host machine, not inside Docker)

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/Tucuxi-Inc/Loris.git
cd Loris
cp .env.example .env
```

### 2. Pull required Ollama models

Ollama must be running on your host machine. The backend connects to it from Docker via `host.docker.internal`.

```bash
# Required: embedding model for automation matching (274 MB)
ollama pull nomic-embed-text

# Default inference model (runs on Ollama cloud - works on any machine)
ollama pull qwen3-vl:235b-cloud

# Fallback inference model (used if primary is unavailable)
ollama pull gpt-oss:120b-cloud
```

**Cloud models** (names ending in `-cloud`) run on Ollama's infrastructure. Traffic is encrypted and Ollama does not store prompts or outputs. This means the AI features work on any machine regardless of local GPU capacity.

If you prefer fully local inference, edit `.env` and set `OLLAMA_MODEL` to any local model you have pulled (e.g., `llama3.2`, `qwen3:30b-a3b`).

### 3. Start services

```bash
docker-compose up -d
```

This starts four containers:

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3005 | React app (login, ask questions, expert queue) |
| Backend API | http://localhost:8005 | FastAPI (REST endpoints) |
| API Docs | http://localhost:8005/docs | Swagger/OpenAPI interactive docs |
| PostgreSQL | localhost:5435 | Database with pgvector extension |
| Redis | localhost:6385 | Cache and future job queue |

### 4. Verify

```bash
# Backend health check
curl http://localhost:8005/health
# Expected: {"status":"healthy","service":"loris-api"}

# Frontend
open http://localhost:3005
# Should see the Loris login page
```

### Rebuilding after code changes

```bash
# Rebuild backend (code is volume-mounted, so most changes auto-reload)
docker-compose up -d --build backend

# Reset database (drops all data, recreates tables on backend restart)
docker exec loris-postgres-1 psql -U loris -d loris -c \
  "DROP SCHEMA public CASCADE; CREATE SCHEMA public; \
   CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"; \
   CREATE EXTENSION IF NOT EXISTS \"vector\";"
docker-compose restart backend

# View logs
docker logs loris-backend-1 -f
```

### Linux note

On Linux, Docker containers may not resolve `host.docker.internal` by default. Add this to the `backend` service in `docker-compose.yml`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 15 + pgvector |
| Cache | Redis 7 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| AI (Inference) | Ollama (local/cloud), Anthropic, AWS Bedrock, Azure OpenAI |
| AI (Embeddings) | Ollama nomic-embed-text (768 dimensions) |

## Project Structure

```
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/v1/    # REST endpoints (auth, questions, automation, settings)
│   │   ├── models/    # SQLAlchemy models
│   │   ├── services/  # Business logic & AI providers
│   │   └── core/      # Config, database setup
│   └── Dockerfile
├── frontend/          # React application
│   └── src/
│       ├── components/
│       ├── contexts/  # Auth state
│       ├── pages/     # Login, Dashboard, Ask, Expert Queue
│       └── lib/api/   # API client
├── database/          # Init SQL (pgvector extension)
├── docs/              # Planning documentation
├── docker-compose.yml
└── .env.example
```

## AI Provider Configuration

Edit `.env` to switch AI providers:

| Provider | `AI_PROVIDER` value | Requires |
|----------|-------------------|----------|
| Ollama (default) | `local_ollama` | Ollama running on host |
| Anthropic Claude | `cloud_anthropic` | `ANTHROPIC_API_KEY` |
| AWS Bedrock | `cloud_bedrock` | AWS credentials configured |
| Azure OpenAI | `cloud_azure` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY` |

Domain experts can view available Ollama models and the current AI configuration via the Settings API (`GET /api/v1/settings/ollama-models`).

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
