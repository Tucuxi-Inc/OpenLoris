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
- **Multi-Provider AI** — Supports Ollama (local), Anthropic Claude, AWS Bedrock, Azure OpenAI
- **Data Privacy** — Keep sensitive data on-premise with local AI providers
- **Expert Workflow** — Approve, edit, or request clarification with AI-assisted drafts

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Tucuxi-Inc/Loris.git
cd Loris

# Copy environment config
cp .env.example .env

# Start all services
docker-compose up -d
```

Access the app:
- **Frontend**: http://localhost:3005
- **API Docs**: http://localhost:8005/docs

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 15 + pgvector |
| Cache | Redis 7 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| AI | Ollama, Anthropic, AWS Bedrock, Azure OpenAI |

## Project Structure

```
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # REST endpoints
│   │   ├── models/    # SQLAlchemy models
│   │   └── services/  # Business logic & AI providers
│   └── alembic/       # Database migrations
├── frontend/          # React application
│   └── src/
│       ├── components/
│       ├── pages/
│       └── lib/api/
├── docs/              # Planning documentation
└── docker-compose.yml
```

## Documentation

See `docs/loris-planning/` for detailed planning documents:
- Project Vision
- System Architecture
- Data Model
- API Specification
- Automation Workflow

## License

Proprietary — Tucuxi Inc.
