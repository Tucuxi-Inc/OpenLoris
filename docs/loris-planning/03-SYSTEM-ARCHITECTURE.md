# Loris: System Architecture

## Document Overview
**Version:** 0.1.0 (Draft)
**Last Updated:** January 2026

---

## Architecture Overview

Loris follows a **three-tier architecture** with a React frontend, FastAPI backend, and PostgreSQL database, building on the proven CounselScope infrastructure while adding new components for Q&A workflow management.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LORIS ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PRESENTATION TIER                             │   │
│  │                                                                       │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                    │   │
│  │  │   Business User     │  │   Expert/Admin      │                    │   │
│  │  │   Dashboard         │  │   Dashboard         │                    │   │
│  │  │   (React SPA)       │  │   (React SPA)       │                    │   │
│  │  └─────────────────────┘  └─────────────────────┘                    │   │
│  │              │                      │                                 │   │
│  │              └──────────┬───────────┘                                 │   │
│  │                         │                                             │   │
│  └─────────────────────────│─────────────────────────────────────────────┘   │
│                            │ HTTPS (REST API)                               │
│  ┌─────────────────────────│─────────────────────────────────────────────┐   │
│  │                    APPLICATION TIER                                   │   │
│  │                         │                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                    FastAPI Backend                          │     │   │
│  │  │                                                             │     │   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │     │   │
│  │  │  │   Auth    │ │ Questions │ │ Knowledge │ │ Analytics │   │     │   │
│  │  │  │  Service  │ │  Service  │ │  Service  │ │  Service  │   │     │   │
│  │  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │     │   │
│  │  │                                                             │     │   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │     │   │
│  │  │  │Automation │ │    AI     │ │  Notify   │ │  Billing  │   │     │   │
│  │  │  │  Engine   │ │ Provider  │ │  Service  │ │ Intelligence│  │     │   │
│  │  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │     │   │
│  │  │                                                             │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                         │                                             │   │
│  └─────────────────────────│─────────────────────────────────────────────┘   │
│                            │                                                │
│  ┌─────────────────────────│─────────────────────────────────────────────┐   │
│  │                      DATA TIER                                        │   │
│  │                         │                                             │   │
│  │  ┌──────────────────────┴──────────────────────┐                     │   │
│  │  │                                              │                     │   │
│  │  │  ┌────────────────────┐  ┌────────────────┐ │                     │   │
│  │  │  │    PostgreSQL      │  │     Redis      │ │                     │   │
│  │  │  │    + pgvector      │  │    (Cache)     │ │                     │   │
│  │  │  │                    │  │                │ │                     │   │
│  │  │  │ • Users/Orgs       │  │ • Sessions     │ │                     │   │
│  │  │  │ • Questions        │  │ • Rate limits  │ │                     │   │
│  │  │  │ • Knowledge        │  │ • Queue state  │ │                     │   │
│  │  │  │ • Automation Rules │  │ • Notifications│ │                     │   │
│  │  │  │ • Embeddings       │  │                │ │                     │   │
│  │  │  └────────────────────┘  └────────────────┘ │                     │   │
│  │  │                                              │                     │   │
│  │  └──────────────────────────────────────────────┘                     │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                      EXTERNAL SERVICES                                │   │
│  │                                                                       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │   │
│  │  │   Ollama    │ │  Anthropic  │ │ AWS Bedrock │ │ Azure OpenAI│     │   │
│  │  │   (Local)   │ │   Claude    │ │             │ │             │     │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘     │   │
│  │                       AI Inference Providers                          │   │
│  │                                                                       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                     │   │
│  │  │Google Drive │ │  OneDrive   │ │ SharePoint  │  (Phase 3)          │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                     │   │
│  │                    Document Repositories                              │   │
│  │                                                                       │   │
│  │  ┌─────────────┐ ┌─────────────┐                                     │   │
│  │  │   SendGrid  │ │   Slack     │  (Notifications - Phase 3)          │   │
│  │  └─────────────┘ └─────────────┘                                     │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### From CounselScope (Retained)

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Backend Framework** | FastAPI | 0.104+ | Async Python API framework |
| **ORM** | SQLAlchemy | 2.0 | Async database operations |
| **Database** | PostgreSQL | 15 | Primary data store |
| **Vector Search** | pgvector | 0.5+ | Semantic similarity search |
| **Cache** | Redis | 7 | Session, queue, caching |
| **Migrations** | Alembic | 1.12+ | Schema version control |
| **Validation** | Pydantic | v2 | Request/response schemas |
| **Auth** | python-jose | 3.3+ | JWT tokens |
| **Security** | passlib[bcrypt] | 1.7+ | Password hashing |
| **HTTP Client** | httpx | 0.25+ | External API calls |
| **Embeddings** | sentence-transformers | 2.2+ | Vector generation |
| **Frontend** | React | 18 | UI framework |
| **Type System** | TypeScript | 5+ | Type safety |
| **Build** | Vite | 4.5+ | Fast bundling |
| **Styling** | Tailwind CSS | 3.3+ | Utility CSS |
| **State** | React Query + Zustand | 5+ | Server + client state |
| **Routing** | React Router | 6+ | Navigation |
| **Components** | Radix UI | Latest | Accessible primitives |
| **Charts** | Recharts | 2.8+ | Data visualization |

### New for Loris

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Real-time** | WebSockets (FastAPI) | Live notifications |
| **Email** | SendGrid / SMTP | Email notifications |
| **Background Jobs** | Celery + Redis | Async task processing |
| **File Storage** | S3-compatible | Document storage |

---

## Core Services Architecture

### 1. Authentication Service

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION SERVICE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Responsibilities:                                                          │
│  • User registration and login                                              │
│  • JWT token issuance and validation                                        │
│  • Role-based access control (RBAC)                                         │
│  • Organization/tenant management                                           │
│  • Session management via Redis                                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         USER TYPES                                   │   │
│  │                                                                       │   │
│  │   BUSINESS_USER          DOMAIN_EXPERT          ADMIN                │   │
│  │   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐      │   │
│  │   │ • Ask       │        │ • All above │        │ • All above │      │   │
│  │   │   questions │        │ • View queue│        │ • User mgmt │      │   │
│  │   │ • View own  │        │ • Answer    │        │ • Settings  │      │   │
│  │   │   history   │        │ • Automate  │        │ • Analytics │      │   │
│  │   │ • Feedback  │        │ • Knowledge │        │ • Billing   │      │   │
│  │   └─────────────┘        └─────────────┘        └─────────────┘      │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Endpoints:                                                                 │
│  POST /api/v1/auth/register          - Create new user                      │
│  POST /api/v1/auth/login             - Authenticate, get tokens             │
│  POST /api/v1/auth/refresh           - Refresh access token                 │
│  POST /api/v1/auth/logout            - Invalidate session                   │
│  GET  /api/v1/auth/me                - Current user profile                 │
│  PUT  /api/v1/auth/me                - Update profile                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Questions Service

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          QUESTIONS SERVICE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Responsibilities:                                                          │
│  • Question submission and lifecycle management                             │
│  • Status tracking and transitions                                          │
│  • User question history                                                    │
│  • Expert queue management                                                  │
│  • Response time tracking                                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    QUESTION LIFECYCLE                                │   │
│  │                                                                       │   │
│  │   SUBMITTED ──► PROCESSING ──┬──► AUTO_ANSWERED ──► RESOLVED         │   │
│  │                              │           │                            │   │
│  │                              │           ▼                            │   │
│  │                              │    HUMAN_REQUESTED                     │   │
│  │                              │           │                            │   │
│  │                              ▼           ▼                            │   │
│  │                        EXPERT_QUEUE ──► ANSWERED ──► RESOLVED        │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │                      NEEDS_CLARIFICATION ──► (back to EXPERT_QUEUE)  │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Endpoints:                                                                 │
│  POST /api/v1/questions/                  - Submit new question             │
│  GET  /api/v1/questions/                  - List user's questions           │
│  GET  /api/v1/questions/{id}              - Get question details            │
│  POST /api/v1/questions/{id}/feedback     - User feedback on answer         │
│  POST /api/v1/questions/{id}/clarify      - User provides clarification     │
│                                                                             │
│  Expert Endpoints:                                                          │
│  GET  /api/v1/questions/queue             - Get expert queue                │
│  POST /api/v1/questions/{id}/answer       - Submit answer                   │
│  POST /api/v1/questions/{id}/request-info - Request clarification           │
│  POST /api/v1/questions/{id}/assign       - Assign to expert                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Automation Engine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AUTOMATION ENGINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Responsibilities:                                                          │
│  • Match incoming questions to automated answers                            │
│  • Manage automation rules created by experts                               │
│  • Track automation acceptance/rejection metrics                            │
│  • Semantic similarity matching using embeddings                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTOMATION FLOW                                   │   │
│  │                                                                       │   │
│  │   New Question                                                        │   │
│  │        │                                                              │   │
│  │        ▼                                                              │   │
│  │   ┌─────────────────┐                                                │   │
│  │   │ Generate        │                                                │   │
│  │   │ Embedding       │                                                │   │
│  │   └────────┬────────┘                                                │   │
│  │            │                                                          │   │
│  │            ▼                                                          │   │
│  │   ┌─────────────────┐                                                │   │
│  │   │ Search Active   │ ◄──── automation_rules table                   │   │
│  │   │ Automation Rules│       (enabled rules with embeddings)          │   │
│  │   └────────┬────────┘                                                │   │
│  │            │                                                          │   │
│  │            ▼                                                          │   │
│  │   ┌─────────────────┐                                                │   │
│  │   │ Similarity      │                                                │   │
│  │   │ Score Check     │                                                │   │
│  │   └────────┬────────┘                                                │   │
│  │            │                                                          │   │
│  │     ┌──────┴──────┐                                                  │   │
│  │     │             │                                                  │   │
│  │  ≥ 0.85       < 0.85                                                 │   │
│  │     │             │                                                  │   │
│  │     ▼             ▼                                                  │   │
│  │  Deliver       Continue to                                           │   │
│  │  Auto-Answer   Expert Queue                                          │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Endpoints:                                                                 │
│  GET  /api/v1/automation/rules              - List automation rules         │
│  POST /api/v1/automation/rules              - Create new rule               │
│  PUT  /api/v1/automation/rules/{id}         - Update rule                   │
│  PUT  /api/v1/automation/rules/{id}/toggle  - Enable/disable rule           │
│  GET  /api/v1/automation/metrics            - Automation statistics         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Knowledge Service (Enhanced from CounselScope)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          KNOWLEDGE SERVICE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Retained from CounselScope:                                                │
│  • Document upload and parsing                                              │
│  • Fact extraction with expert validation                                   │
│  • Semantic search via pgvector                                             │
│  • Good Until Date (GUD) management                                         │
│  • Wisdom tiers (confidence levels)                                         │
│                                                                             │
│  Enhanced for Loris:                                                        │
│  • Integration with Q&A answers (answers become knowledge)                  │
│  • Question-to-knowledge relevance scoring                                  │
│  • Gap analysis for incomplete coverage                                     │
│  • Knowledge effectiveness metrics                                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    GAP ANALYSIS FLOW                                 │   │
│  │                                                                       │   │
│  │   Question                                                            │   │
│  │      │                                                                │   │
│  │      ▼                                                                │   │
│  │   ┌─────────────────────────────────────────────┐                    │   │
│  │   │ Semantic Search Against Knowledge Base      │                    │   │
│  │   │ (wisdom_facts + wisdom_embeddings)          │                    │   │
│  │   └─────────────────────────────────────────────┘                    │   │
│  │      │                                                                │   │
│  │      ▼                                                                │   │
│  │   ┌─────────────────────────────────────────────┐                    │   │
│  │   │ AI Analysis (via AI Provider Service)       │                    │   │
│  │   │ • What knowledge is relevant?               │                    │   │
│  │   │ • What parts of question are answered?      │                    │   │
│  │   │ • What gaps remain?                         │                    │   │
│  │   │ • What clarifications needed?               │                    │   │
│  │   └─────────────────────────────────────────────┘                    │   │
│  │      │                                                                │   │
│  │      ▼                                                                │   │
│  │   ┌─────────────────────────────────────────────┐                    │   │
│  │   │ Output: GapAnalysisResult                   │                    │   │
│  │   │ {                                           │                    │   │
│  │   │   relevant_knowledge: [...],               │                    │   │
│  │   │   coverage_percentage: 65%,                │                    │   │
│  │   │   identified_gaps: [...],                  │                    │   │
│  │   │   proposed_answer: "...",                  │                    │   │
│  │   │   confidence_score: 0.72,                  │                    │   │
│  │   │   suggested_clarifications: [...]          │                    │   │
│  │   │ }                                           │                    │   │
│  │   └─────────────────────────────────────────────┘                    │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Endpoints (from CounselScope):                                             │
│  POST /api/v1/documents/upload             - Upload document                │
│  GET  /api/v1/documents/                   - List documents                 │
│  POST /api/v1/documents/{id}/extract-facts - Trigger AI extraction          │
│  POST /api/v1/documents/{id}/approve       - Approve extracted fact         │
│  GET  /api/v1/wisdom/search                - Semantic search                │
│  GET  /api/v1/wisdom/facts/                - List wisdom facts              │
│                                                                             │
│  New for Loris:                                                             │
│  POST /api/v1/knowledge/analyze-gaps       - Gap analysis for question      │
│  POST /api/v1/knowledge/from-answer        - Create fact from Q&A answer    │
│  GET  /api/v1/knowledge/effectiveness      - Knowledge usage metrics        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. AI Provider Service (From CounselScope)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI PROVIDER SERVICE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Supports multiple AI backends for data privacy flexibility:                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       PROVIDER OPTIONS                               │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐                                                 │   │
│  │  │ LOCAL_OLLAMA    │  All data stays on your servers                 │   │
│  │  │ localhost:11434 │  Models: llama3.2, mistral, mixtral, etc.       │   │
│  │  └─────────────────┘                                                 │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐                                                 │   │
│  │  │ CLOUD_ANTHROPIC │  Data sent to Anthropic                         │   │
│  │  │ Claude API      │  Best quality, suitable for non-privileged      │   │
│  │  └─────────────────┘                                                 │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐                                                 │   │
│  │  │ CLOUD_BEDROCK   │  Data stays in your AWS account                 │   │
│  │  │ AWS Bedrock     │  Claude via AWS, enterprise compliance          │   │
│  │  └─────────────────┘                                                 │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐                                                 │   │
│  │  │ CLOUD_AZURE     │  Data stays in your Azure tenant                │   │
│  │  │ Azure OpenAI    │  Enterprise compliance, regional data           │   │
│  │  └─────────────────┘                                                 │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Interface:                                                                 │
│  - generate_response(prompt, context) -> str                                │
│  - generate_embedding(text) -> List[float]                                  │
│  - analyze_gaps(question, knowledge) -> GapAnalysisResult                   │
│  - propose_answer(question, knowledge, gaps) -> ProposedAnswer              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6. Notification Service (New)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NOTIFICATION SERVICE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Responsibilities:                                                          │
│  • Notify users when answers are ready                                      │
│  • Notify experts of new questions                                          │
│  • Track notification preferences                                           │
│  • Support multiple channels (in-app, email, webhook)                       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    NOTIFICATION EVENTS                               │   │
│  │                                                                       │   │
│  │  Event                        Recipients          Channels           │   │
│  │  ─────────────────────────────────────────────────────────────────   │   │
│  │  question.submitted           Expert(s)           In-app, Email      │   │
│  │  question.answered            Asker               In-app, Email      │   │
│  │  question.auto_answered       Asker               In-app             │   │
│  │  question.needs_clarification Asker               In-app, Email      │   │
│  │  question.human_requested     Expert(s)           In-app             │   │
│  │  question.sla_warning         Expert(s), Admin    In-app, Email      │   │
│  │  automation.triggered         Admin               In-app             │   │
│  │  knowledge.expired            Expert(s)           In-app, Email      │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Architecture:                                                              │
│  • Background worker (Celery) processes notification queue                  │
│  • Redis pub/sub for real-time in-app notifications                         │
│  • WebSocket connection for live updates                                    │
│  • Email via SMTP/SendGrid for async delivery                               │
│                                                                             │
│  Endpoints:                                                                 │
│  GET  /api/v1/notifications/              - User's notifications            │
│  PUT  /api/v1/notifications/{id}/read     - Mark as read                    │
│  PUT  /api/v1/notifications/preferences   - Update preferences              │
│  WS   /api/v1/ws/notifications            - Real-time notification stream   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7. Analytics Service

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ANALYTICS SERVICE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Metrics Categories:                                                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ VOLUME METRICS                                                       │   │
│  │ • Questions submitted (daily/weekly/monthly)                         │   │
│  │ • Questions by category/topic                                        │   │
│  │ • Questions by department/user                                       │   │
│  │ • Peak submission times                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RESPONSE METRICS                                                     │   │
│  │ • Average response time                                              │   │
│  │ • Response time by expert                                            │   │
│  │ • Response time by category                                          │   │
│  │ • SLA compliance rate                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ AUTOMATION METRICS                                                   │   │
│  │ • Automation rate (% auto-answered)                                  │   │
│  │ • Automation acceptance rate                                         │   │
│  │ • Human review requests                                              │   │
│  │ • Time saved through automation                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ QUALITY METRICS                                                      │   │
│  │ • User satisfaction ratings                                          │   │
│  │ • Follow-up question rate                                            │   │
│  │ • Answer accuracy (spot-check)                                       │   │
│  │ • Knowledge reuse rate                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BUSINESS VALUE (from CounselScope)                                   │   │
│  │ • Cost avoidance vs. external counsel                                │   │
│  │ • Expert time saved                                                  │   │
│  │ • Knowledge asset growth                                             │   │
│  │ • ROI analysis                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Endpoints:                                                                 │
│  GET /api/v1/analytics/overview           - Dashboard summary               │
│  GET /api/v1/analytics/questions          - Question metrics                │
│  GET /api/v1/analytics/automation         - Automation metrics              │
│  GET /api/v1/analytics/experts            - Expert performance              │
│  GET /api/v1/analytics/roi                - Business value metrics          │
│  GET /api/v1/analytics/export             - Export to CSV/PDF               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Question Submission Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   User     │     │  Frontend  │     │  Backend   │     │  Database  │
│            │     │   (React)  │     │  (FastAPI) │     │ (Postgres) │
└─────┬──────┘     └─────┬──────┘     └─────┬──────┘     └─────┬──────┘
      │                  │                  │                  │
      │ 1. Type question │                  │                  │
      │─────────────────►│                  │                  │
      │                  │                  │                  │
      │                  │ 2. POST /questions                  │
      │                  │─────────────────►│                  │
      │                  │                  │                  │
      │                  │                  │ 3. Create question
      │                  │                  │─────────────────►│
      │                  │                  │                  │
      │                  │                  │ 4. Generate embedding
      │                  │                  │────────┐         │
      │                  │                  │        │ (AI)    │
      │                  │                  │◄───────┘         │
      │                  │                  │                  │
      │                  │                  │ 5. Search automation rules
      │                  │                  │─────────────────►│
      │                  │                  │◄─────────────────│
      │                  │                  │                  │
      │                  │                  │ 6. Match found? ─┐
      │                  │                  │                  │
      │                  │   YES: Return    │                  │
      │                  │◄──auto answer────│                  │
      │                  │                  │                  │
      │◄─ Show answer ───│                  │                  │
      │   (TransWarp)    │                  │                  │
      │                  │                  │                  │
      │                  │   NO: Queue for  │                  │
      │                  │◄── expert ───────│                  │
      │                  │                  │                  │
      │◄─ Show status ───│                  │ 7. Run gap analysis
      │   (Researching)  │                  │────────┐         │
      │                  │                  │        │ (AI)    │
      │                  │                  │◄───────┘         │
      │                  │                  │                  │
      │                  │                  │ 8. Notify expert │
      │                  │                  │─────────────────►│
      │                  │                  │                  │
```

### Expert Answer Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   Expert   │     │  Frontend  │     │  Backend   │     │  Database  │
│            │     │   (React)  │     │  (FastAPI) │     │ (Postgres) │
└─────┬──────┘     └─────┬──────┘     └─────┬──────┘     └─────┬──────┘
      │                  │                  │                  │
      │ 1. View queue    │                  │                  │
      │─────────────────►│                  │                  │
      │                  │ GET /questions/queue                │
      │                  │─────────────────►│                  │
      │                  │                  │─────────────────►│
      │                  │◄─────────────────│◄─────────────────│
      │◄─ Show queue ────│                  │                  │
      │                  │                  │                  │
      │ 2. Select question                  │                  │
      │─────────────────►│                  │                  │
      │                  │ GET /questions/{id}                 │
      │                  │─────────────────►│                  │
      │                  │                  │ Fetch + gap analysis
      │                  │◄─────────────────│◄────────────────►│
      │◄─ Show detail ───│                  │                  │
      │   + AI analysis  │                  │                  │
      │                  │                  │                  │
      │ 3. Edit answer   │                  │                  │
      │─────────────────►│                  │                  │
      │                  │                  │                  │
      │ 4. Submit answer │                  │                  │
      │─────────────────►│                  │                  │
      │                  │ POST /questions/{id}/answer         │
      │                  │─────────────────►│                  │
      │                  │                  │ Store answer     │
      │                  │                  │─────────────────►│
      │                  │                  │                  │
      │                  │                  │ Notify user      │
      │                  │                  │─────────────────►│
      │                  │◄─────────────────│                  │
      │◄─ Confirm sent ──│                  │                  │
      │                  │                  │                  │
      │ 5. Enable automation (optional)     │                  │
      │─────────────────►│                  │                  │
      │                  │ POST /automation/rules              │
      │                  │─────────────────►│                  │
      │                  │                  │ Create rule +    │
      │                  │                  │ embedding        │
      │                  │                  │─────────────────►│
      │                  │◄─────────────────│                  │
      │◄─ Confirm ───────│                  │                  │
      │                  │                  │                  │
```

---

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DOCKER COMPOSE (Development)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │    frontend     │  │    backend      │  │    postgres     │             │
│  │    (Vite)       │  │    (FastAPI)    │  │  + pgvector     │             │
│  │    :3001        │  │    :8001        │  │    :5433        │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │     redis       │  │    ollama       │  │    pgadmin      │             │
│  │    :6380        │  │   :11434        │  │    :5050        │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ redis-commander │                                                        │
│  │    :8081        │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Production Environment (Target)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           CDN / Load Balancer                        │   │
│  │                         (CloudFront / ALB)                           │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│        ┌──────────────────────────┼──────────────────────────┐             │
│        │                          │                          │             │
│        ▼                          ▼                          ▼             │
│  ┌───────────┐             ┌───────────┐             ┌───────────┐         │
│  │  Static   │             │  API      │             │  WebSocket│         │
│  │  Assets   │             │  Servers  │             │  Servers  │         │
│  │  (S3)     │             │  (ECS)    │             │  (ECS)    │         │
│  └───────────┘             └─────┬─────┘             └─────┬─────┘         │
│                                  │                         │               │
│                   ┌──────────────┼─────────────────────────┘               │
│                   │              │                                          │
│                   ▼              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         VPC Private Subnet                           │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │   PostgreSQL    │  │   Redis         │  │   Celery        │       │   │
│  │  │   (RDS)         │  │   (ElastiCache) │  │   Workers       │       │   │
│  │  │   + pgvector    │  │                 │  │   (ECS)         │       │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JWT AUTHENTICATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Login Request                                                           │
│     POST /auth/login { email, password }                                    │
│                                                                             │
│  2. Server validates credentials                                            │
│     - Check user exists                                                     │
│     - Verify password hash (bcrypt)                                         │
│     - Check user is active                                                  │
│                                                                             │
│  3. Issue tokens                                                            │
│     {                                                                       │
│       access_token: JWT (30 min expiry),                                    │
│       refresh_token: JWT (7 day expiry),                                    │
│       token_type: "bearer"                                                  │
│     }                                                                       │
│                                                                             │
│  4. Client stores tokens                                                    │
│     - Access token: Memory (Zustand store)                                  │
│     - Refresh token: HttpOnly cookie                                        │
│                                                                             │
│  5. API requests include Authorization header                               │
│     Authorization: Bearer <access_token>                                    │
│                                                                             │
│  6. Token refresh when access token expires                                 │
│     POST /auth/refresh (with HttpOnly cookie)                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Role-Based Access Control

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               RBAC MODEL                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Users belong to Organizations (multi-tenancy)                              │
│  Users have Roles within their Organization                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PERMISSION CHECKS                             │   │
│  │                                                                       │   │
│  │  Endpoint                     Required Role    Additional Checks      │   │
│  │  ──────────────────────────────────────────────────────────────────   │   │
│  │  POST /questions              Any              -                      │   │
│  │  GET /questions               Any              Own questions only*    │   │
│  │  GET /questions/queue         Expert+          -                      │   │
│  │  POST /questions/{id}/answer  Expert+          -                      │   │
│  │  POST /automation/rules       Expert+          -                      │   │
│  │  POST /documents/upload       Expert+          -                      │   │
│  │  GET /analytics/overview      Expert           Own metrics only       │   │
│  │  GET /analytics/*             Admin            -                      │   │
│  │  POST /users                  Admin            -                      │   │
│  │  PUT /settings/*              Admin            -                      │   │
│  │                                                                       │   │
│  │  * Experts can see all questions in their domain                     │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Migration from CounselScope

### Components to Retain

| Component | Location | Action |
|-----------|----------|--------|
| Database models | `backend/app/models/` | Retain, extend |
| AI Provider Service | `backend/app/services/ai_provider_service.py` | Retain as-is |
| Knowledge Service | `backend/app/services/knowledge_*.py` | Retain, enhance |
| Document Service | `backend/app/services/document_*.py` | Retain as-is |
| Billing Intelligence | `backend/app/services/billing_*.py` | Retain, integrate |
| Embedding Service | `backend/app/services/` | Retain as-is |
| Frontend Components | `frontend/src/components/` | Retain base UI, adapt |
| API Schemas | `backend/app/schemas/` | Retain, extend |
| Database migrations | `backend/alembic/` | Continue from current |
| Docker Compose | `docker-compose.yml` | Retain, modify services |

### Components to Replace/Rewrite

| Component | Current | New |
|-----------|---------|-----|
| Conversation Flow | Multi-phase refinement | Q&A workflow |
| Main Dashboard | Query refinement page | User/Expert dashboards |
| User Model | Basic (partial) | Full auth with roles |
| Routing | Single-purpose | Role-based routing |

### New Components to Add

| Component | Purpose |
|-----------|---------|
| Questions Service | Q&A lifecycle management |
| Automation Engine | Auto-answer matching |
| Notification Service | Real-time + email notifications |
| User Dashboards | Business user + Expert views |
| Queue Management | Expert work queue |

---

## API Versioning Strategy

```
/api/v1/...   - CounselScope legacy (if needed for migration)
/api/v2/...   - Loris API

Or clean break:
/api/v1/...   - Loris API (starting fresh)
```

Recommendation: **Clean break** with v1 as Loris API, since we're creating a new product. CounselScope-specific endpoints (conversation refinement) can be deprecated.

---

*This architecture document will evolve as implementation progresses.*
