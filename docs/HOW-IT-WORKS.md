# How Open Loris Works

A comprehensive guide to Open Loris's functionality, process flows, and how each feature supports the goal of building compounding organizational knowledge.

---

## Table of Contents

1. [The Core Problem & Solution](#the-core-problem--solution)
2. [System Architecture Overview](#system-architecture-overview)
3. [The Question Lifecycle](#the-question-lifecycle)
4. [Progressive Automation (The Flywheel)](#progressive-automation-the-flywheel)
5. [Knowledge Management](#knowledge-management)
6. [Gap Analysis (AI-Assisted Expertise)](#gap-analysis-ai-assisted-expertise)
7. [Sub-Domain Routing & Expert Assignment](#sub-domain-routing--expert-assignment)
8. [Departments & Organization Structure](#departments--organization-structure)
9. [Good Until Date (GUD) System](#good-until-date-gud-system)
10. [Turbo Mode (User-Controlled Speed)](#turbo-mode-user-controlled-speed)
11. [MoltenLoris (Slack Integration)](#moltenloris-slack-integration)
12. [Analytics & Insights](#analytics--insights)
13. [User Stories by Scale](#user-stories-by-scale)
14. [Privacy & AI Provider Options](#privacy--ai-provider-options)

---

## The Core Problem & Solution

### The Problem

Organizations suffer from knowledge fragmentation:

| Symptom | Impact |
|---------|--------|
| "Ask Sarah, she knows" | Sarah answers the same question 50+ times |
| Tribal knowledge | Critical info lives in one person's head |
| Expert departure | Knowledge walks out the door |
| Document overload | Search returns 47 docs, not answers |
| Stale information | Outdated answers cause mistakes |

### The Solution

Open Loris transforms Q&A from a **repetitive burden** into a **compounding asset**:

```
Traditional Approach:
  Question → Expert answers → Answer forgotten → Same question asked again

Open Loris Approach:
  Question → Expert answers → Automation rule created → Similar questions auto-answered forever
```

**Key insight**: Every answered question is a candidate for automation. The system gets smarter with use, not dumber with staff turnover.

---

## System Architecture Overview

### Three-Tier Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React SPA with role-based dashboards                       │
│  • Business Users: Ask questions, view answers              │
│  • Domain Experts: Queue, knowledge management, analytics   │
│  • Admins: Users, sub-domains, settings, MoltenLoris        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  FastAPI with async SQLAlchemy                              │
│  Services: Auth, Questions, Automation, Knowledge,          │
│           Documents, Analytics, Notifications, Scheduling   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA TIER                              │
│  PostgreSQL + pgvector (semantic search)                    │
│  Redis (caching)                                            │
│  Ollama (local AI) or Cloud AI providers                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Data Models

| Model | Purpose |
|-------|---------|
| `User` | Accounts with roles (business_user, domain_expert, admin) |
| `Organization` | Multi-tenant support with settings |
| `Question` | Full lifecycle tracking with status, priority, metadata |
| `Answer` | Expert responses with source tracking and citations |
| `AutomationRule` | Canonical Q&A pairs that trigger auto-answers |
| `WisdomFact` | Knowledge base entries with tiers and embeddings |
| `KnowledgeDocument` | Uploaded documents with parsing and extraction |
| `SubDomain` | Topic areas for routing (Contracts, HR, IT, etc.) |
| `Notification` | In-app alerts for workflow events |

---

## The Question Lifecycle

### Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         USER SUBMITS QUESTION                             │
│  • Enters question text (min 5 words)                                    │
│  • Optionally selects sub-domain (or AI classifies)                      │
│  • Optionally selects department                                         │
│  • Optionally enables Turbo Mode with confidence threshold               │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      AUTOMATION CHECK (Step 1)                            │
│  System searches all active AutomationRules:                             │
│  1. Generate embedding for question text                                 │
│  2. Compare against rule embeddings using cosine similarity              │
│  3. If similarity >= rule.threshold (default 0.85): MATCH               │
└──────────────────────────────────────────────────────────────────────────┘
                          │                    │
                    MATCH FOUND           NO MATCH
                          │                    │
                          ▼                    ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────────┐
│      AUTO-ANSWER DELIVERED      │  │      TURBO MODE CHECK (Step 2)      │
│  Status: AUTO_ANSWERED          │  │  If user enabled Turbo Mode:        │
│  • Answer from matched rule     │  │  1. Search knowledge base           │
│  • User notified                │  │  2. Calculate confidence score      │
│  • Metrics tracked              │  │  3. If confidence >= threshold:     │
│                                 │  │     deliver AI-generated answer     │
│  User can:                      │  │                                     │
│  • Accept → RESOLVED            │  │  Confidence formula:                │
│  • Reject → EXPERT_QUEUE        │  │  40% fact relevance +               │
└─────────────────────────────────┘  │  30% coverage completeness +        │
                                     │  30% answer coherence               │
                                     └─────────────────────────────────────┘
                                               │
                                    ┌──────────┴──────────┐
                               TURBO ANSWERED         NO TURBO
                                    │                     │
                                    ▼                     ▼
                     ┌─────────────────────┐  ┌─────────────────────────────┐
                     │  TURBO ANSWER       │  │     GAP ANALYSIS (Step 3)   │
                     │  Status: ANSWERED   │  │  1. Search relevant facts   │
                     │  Source: TURBO      │  │  2. AI analyzes coverage    │
                     │                     │  │  3. Identifies gaps         │
                     │  User can:          │  │  4. Proposes draft answer   │
                     │  • Accept → RESOLVED│  │  5. Stores in question.     │
                     │  • Request human    │  │     gap_analysis field      │
                     └─────────────────────┘  └─────────────────────────────┘
                                                          │
                                                          ▼
                                     ┌─────────────────────────────────────┐
                                     │         EXPERT QUEUE (Step 4)       │
                                     │  Status: EXPERT_QUEUE               │
                                     │  • Routed to sub-domain experts     │
                                     │  • Priority assigned (low/normal/   │
                                     │    high/urgent)                     │
                                     │  • SLA clock starts                 │
                                     │  • Experts notified                 │
                                     └─────────────────────────────────────┘
                                                          │
                                                          ▼
                                     ┌─────────────────────────────────────┐
                                     │       EXPERT CLAIMS QUESTION        │
                                     │  Status: IN_PROGRESS                │
                                     │  • Expert sees gap analysis         │
                                     │  • Pre-populated draft answer       │
                                     │  • Relevant facts highlighted       │
                                     │  • Expert refines and submits       │
                                     └─────────────────────────────────────┘
                                                          │
                                                          ▼
                                     ┌─────────────────────────────────────┐
                                     │        ANSWER DELIVERED             │
                                     │  Status: ANSWERED                   │
                                     │  • User notified                    │
                                     │  • User reviews answer              │
                                     │  • User provides rating (1-5)       │
                                     │  Status: RESOLVED                   │
                                     └─────────────────────────────────────┘
                                                          │
                                                          ▼
                                     ┌─────────────────────────────────────┐
                                     │    EXPERT CREATES AUTOMATION RULE   │
                                     │  (Optional but powerful)            │
                                     │  • One-click from answered question │
                                     │  • Sets canonical Q&A pair          │
                                     │  • Configures similarity threshold  │
                                     │  • Sets Good Until Date             │
                                     │  • Future similar questions →       │
                                     │    auto-answered instantly          │
                                     └─────────────────────────────────────┘
```

### Status Transitions

| From | To | Trigger |
|------|-----|---------|
| SUBMITTED | AUTO_ANSWERED | Automation rule matched |
| SUBMITTED | ANSWERED | Turbo mode confident answer |
| SUBMITTED | EXPERT_QUEUE | No match, no turbo, or low confidence |
| AUTO_ANSWERED | RESOLVED | User accepts auto-answer |
| AUTO_ANSWERED | EXPERT_QUEUE | User rejects, requests human |
| EXPERT_QUEUE | IN_PROGRESS | Expert claims question |
| IN_PROGRESS | ANSWERED | Expert submits answer |
| ANSWERED | RESOLVED | User provides feedback |

---

## Progressive Automation (The Flywheel)

### How It Works

The automation system uses **semantic similarity** to match incoming questions against a library of expert-created rules.

#### Step 1: Expert Creates Rule

After answering a question, the expert can click "Create Automation Rule":

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTOMATION RULE                           │
├─────────────────────────────────────────────────────────────┤
│  Canonical Question: "What are the office hours?"           │
│  Canonical Answer:   "Our office hours are Monday through   │
│                      Friday, 9 AM to 5 PM. For emergencies  │
│                      outside these hours, please contact    │
│                      the on-call support line."             │
│  Similarity Threshold: 0.85 (85%)                           │
│  Good Until Date: 2025-06-30                                │
│  Created By: expert@company.com                             │
└─────────────────────────────────────────────────────────────┘
```

#### Step 2: Embedding Generated

When the rule is created, the system:
1. Sends canonical question to embedding model (nomic-embed-text)
2. Receives 768-dimensional vector
3. Stores vector in `AutomationRuleEmbedding` table

#### Step 3: Matching on New Questions

When a new question arrives:
1. Generate embedding for new question
2. Calculate cosine similarity against all active rules
3. If any rule exceeds its threshold → deliver that rule's answer

```python
# Simplified matching logic
def check_automation(question_text: str) -> AutomationRule | None:
    question_embedding = generate_embedding(question_text)

    for rule in active_rules:
        similarity = cosine_similarity(question_embedding, rule.embedding)
        if similarity >= rule.similarity_threshold:
            return rule

    return None
```

#### Step 4: Metrics Tracked

Every automation interaction is logged:

| Metric | Description |
|--------|-------------|
| `times_triggered` | How many times this rule matched a question |
| `times_accepted` | How many users accepted the auto-answer |
| `times_rejected` | How many users requested human review |
| `acceptance_rate` | accepted / triggered (quality indicator) |

### The Compounding Effect

```
Month 1:
  • 100 questions asked
  • 100 answered by experts
  • 10 automation rules created
  • 0% auto-answered

Month 3:
  • 300 questions asked
  • 75 answered by experts
  • 30 automation rules exist
  • 25% auto-answered (75 questions)

Month 6:
  • 600 questions asked
  • 300 answered by experts
  • 60 automation rules exist
  • 50% auto-answered (300 questions)

Month 12:
  • 1200 questions asked
  • 360 answered by experts
  • 100 automation rules exist
  • 70% auto-answered (840 questions)
```

**Key insight**: Expert workload decreases over time while answer quality improves through refinement.

---

## Knowledge Management

### Knowledge Facts (WisdomFacts)

The knowledge base stores discrete, searchable facts that power gap analysis and Turbo Mode.

#### Tier System

| Tier | Name | Description | Source |
|------|------|-------------|--------|
| `tier_0a` | Authoritative | Official policy, verified sources | Documents, manual entry |
| `tier_0b` | Expert-validated | Expert confirmed accuracy | Expert review |
| `tier_0c` | AI-generated | Extracted by AI, not yet validated | Document extraction |
| `pending` | Awaiting review | Newly added, needs triage | Any source |
| `archived` | Deprecated | No longer current | Manual archival |

#### Fact Lifecycle

```
Document uploaded
        │
        ▼
AI extracts facts → Status: PENDING (tier_0c)
        │
        ▼
Expert reviews → Approves → Status: ACTIVE (tier_0b)
        │              │
        │              └→ Rejects → Status: ARCHIVED
        │
        ▼
Admin verifies against policy → Status: ACTIVE (tier_0a)
```

### Document Management

Open Loris can ingest documents and extract knowledge automatically.

#### Supported Formats
- PDF (via pdfplumber)
- DOCX (via python-docx)
- TXT (plain text)

#### Extraction Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPLOAD                           │
│  • User uploads file with metadata                          │
│  • Sets department, category, GUD date                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PARSING PHASE                             │
│  Status: PARSING                                            │
│  • Extract text from document                               │
│  • Split into chunks (semantic boundaries)                  │
│  • Generate embeddings for each chunk                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   EXTRACTION PHASE                           │
│  Status: EXTRACTING                                         │
│  • AI analyzes chunks for discrete facts                    │
│  • Creates ExtractedFactCandidate for each                  │
│  • Assigns confidence scores                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXPERT REVIEW                             │
│  Status: READY                                              │
│  • Expert sees candidate facts                              │
│  • Approves → Creates WisdomFact (tier_0c)                  │
│  • Rejects → Discarded with reason                          │
│  • Edits → Modified then approved                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Gap Analysis (AI-Assisted Expertise)

### What It Does

When a question enters the expert queue, the system prepares an "expert brief":

1. **Searches** the knowledge base for relevant facts
2. **Analyzes** what aspects of the question are covered
3. **Identifies** gaps where no knowledge exists
4. **Proposes** a draft answer the expert can refine

### Gap Analysis Output

```json
{
  "question": "Can contractors work remotely on Fridays?",
  "relevant_facts": [
    {
      "id": "fact-123",
      "content": "Remote work is allowed with manager approval.",
      "tier": "tier_0b",
      "relevance_score": 0.87
    },
    {
      "id": "fact-456",
      "content": "Contractors must follow the same attendance policies as employees.",
      "tier": "tier_0a",
      "relevance_score": 0.72
    }
  ],
  "coverage_assessment": {
    "covered": ["Remote work policy exists", "Contractor policy exists"],
    "gaps": ["No specific contractor + remote work combination policy found",
             "Friday-specific policies not found"]
  },
  "proposed_answer": "Based on our policies, remote work requires manager approval, and contractors follow the same attendance policies as employees. However, I don't see a specific policy addressing Friday remote work for contractors. Let me verify with HR and provide a definitive answer.",
  "confidence": 0.65
}
```

### How Experts Use It

The expert answer page shows:
- The gap analysis summary
- Relevant facts with citations
- Pre-populated answer text
- Ability to edit before sending

**Key insight**: This isn't AI replacing experts—it's AI doing the research so experts can focus on judgment and validation.

---

## Sub-Domain Routing & Expert Assignment

### Purpose

As organizations grow, questions span multiple areas of expertise. Sub-domain routing ensures questions reach the right experts.

### Setup Flow

```
┌─────────────────────────────────────────────────────────────┐
│              ADMIN CREATES SUB-DOMAINS                       │
│  Examples: Contracts, Employment Law, Benefits, IT Support   │
│  Each has: name, description, SLA hours                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ADMIN ASSIGNS EXPERTS                           │
│  • Expert A → Contracts, Employment Law                      │
│  • Expert B → Benefits, IT Support                          │
│  • Expert C → All sub-domains (generalist)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              QUESTIONS ROUTED AUTOMATICALLY                  │
│  User submits question:                                      │
│  • User selects sub-domain manually, OR                      │
│  • AI classifies based on question content                   │
│  • Question appears in assigned experts' queues              │
└─────────────────────────────────────────────────────────────┘
```

### AI Classification

When a user selects "Not sure — let Open Loris classify it":

1. System analyzes question text
2. Compares against sub-domain descriptions
3. Assigns to best-matching sub-domain
4. Sets `ai_classified_subdomain = true` flag

### Reassignment Workflow

If an expert receives a misrouted question:

```
Expert clicks "Request Reassignment"
        │
        ▼
Selects target sub-domain + provides reason
        │
        ▼
Admin sees pending reassignment request
        │
        ▼
Admin approves → Question moves to new sub-domain
   OR
Admin rejects → Question stays, expert notified
```

### SLA Monitoring

Each sub-domain has configurable SLA hours:
- System tracks time from submission to first response
- Notifications sent when SLA breach is imminent
- Analytics show SLA compliance by sub-domain

---

## Departments & Organization Structure

### Purpose

Departments organize users and content by business unit, independent of sub-domains (expertise areas).

### Configuration

Admins configure departments in Organization Settings:

```json
{
  "departments": ["Engineering", "Sales", "Marketing", "Finance", "HR", "Legal"],
  "require_department": true
}
```

### Usage

| Feature | How Departments Are Used |
|---------|-------------------------|
| Questions | User selects their department when asking |
| Documents | Documents tagged by owning department |
| Analytics | Filter metrics by department |
| Routing | Optional: route to experts by department |

### Departments vs Sub-Domains

| Aspect | Departments | Sub-Domains |
|--------|-------------|-------------|
| Purpose | Organizational structure | Expertise areas |
| Who uses | All users | Experts |
| Example | "Sales", "Engineering" | "Contracts", "IT Support" |
| Routing | Optional filter | Primary routing mechanism |

---

## Good Until Date (GUD) System

### The Problem It Solves

Knowledge goes stale:
- Policies change annually
- Tax rates update quarterly
- Software versions change monthly
- Personnel directories change weekly

Stale answers erode trust and cause mistakes.

### How GUD Works

Every piece of knowledge has an expiration date:

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTOMATION RULE                           │
│  Question: "What's the PTO policy?"                         │
│  Answer: "Employees receive 15 days PTO annually..."        │
│  Good Until Date: 2025-01-01 (next policy review)           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE FACT                            │
│  Content: "Sales tax rate in California is 7.25%"           │
│  Good Until Date: 2025-04-01 (next quarter)                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT                                  │
│  Name: "Employee Handbook 2024"                             │
│  Good Until Date: 2025-01-01 (annual update)                │
└─────────────────────────────────────────────────────────────┘
```

### Automated Enforcement

The system runs daily GUD checks (2 AM via APScheduler):

```
┌─────────────────────────────────────────────────────────────┐
│                30 DAYS BEFORE EXPIRY                         │
│  • Warning notification to relevant experts                  │
│  • Item flagged in dashboard                                 │
│  • "Expiring Soon" list in analytics                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 7 DAYS BEFORE EXPIRY                         │
│  • Urgent notification to experts                            │
│  • Item highlighted in red                                   │
│  • Reminder to review and extend or update                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXPIRY DATE                               │
│  • Item automatically DEACTIVATED                            │
│  • No longer used for automation/search                      │
│  • Notification: "Item expired and deactivated"              │
│  • Can be reactivated after review/update                    │
└─────────────────────────────────────────────────────────────┘
```

### Renewal Flow

Experts can extend GUD dates:
1. Review item for accuracy
2. Update content if needed
3. Set new GUD date
4. Item remains active

---

## Turbo Mode (User-Controlled Speed)

### Purpose

Some questions need instant answers; others need expert certainty. Turbo Mode lets users choose.

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                USER ENABLES TURBO MODE                       │
│  • Selects confidence threshold: 50% / 75% / 90%            │
│  • Higher threshold = more certain but fewer instant answers │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SYSTEM PROCESSES QUESTION                       │
│  1. Check automation rules first (always)                    │
│  2. If no rule match, search knowledge base                  │
│  3. Calculate confidence score                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CONFIDENCE CALCULATION                          │
│  Score = 40% × Fact Relevance                               │
│        + 30% × Coverage Completeness                         │
│        + 30% × Answer Coherence                              │
│                                                              │
│  Example: 0.85 relevance, 0.70 coverage, 0.90 coherence     │
│  Score = (0.40 × 0.85) + (0.30 × 0.70) + (0.30 × 0.90)      │
│        = 0.34 + 0.21 + 0.27 = 0.82 (82%)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
            SCORE >= THRESHOLD    SCORE < THRESHOLD
                    │                     │
                    ▼                     ▼
┌───────────────────────────┐  ┌─────────────────────────────┐
│    TURBO ANSWER           │  │    EXPERT QUEUE             │
│  • Instant AI answer      │  │  • Routes to experts        │
│  • Shows confidence %     │  │  • User notified            │
│  • Shows source facts     │  │  • Gap analysis prepared    │
│  • User can still request │  │                             │
│    human review           │  │                             │
└───────────────────────────┘  └─────────────────────────────┘
```

### Threshold Guidelines

| Threshold | Best For |
|-----------|----------|
| 50% | Quick reference, low-stakes questions |
| 75% | Balanced speed vs certainty (default) |
| 90% | Important decisions, policy questions |

---

## MoltenLoris (Slack Integration)

### Purpose

Meet people where they already work. MoltenLoris monitors Slack channels and answers questions using your Open Loris knowledge base.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SLACK WORKSPACE                         │
│  #general, #hr-questions, #it-help, etc.                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MOLTENLORIS AGENT                         │
│  (MCP Server running alongside Open Loris)                   │
│  • Monitors configured channels                              │
│  • Detects questions (? or question patterns)                │
│  • Queries Open Loris knowledge base                         │
│  • Posts answers with confidence + citations                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    OPEN LORIS BACKEND                        │
│  • Receives question via API                                 │
│  • Searches knowledge base                                   │
│  • Returns answer with sources                               │
└─────────────────────────────────────────────────────────────┘
```

### Behavior

| Confidence | Action |
|------------|--------|
| High (>80%) | Posts answer directly in channel |
| Medium (50-80%) | Posts answer with "I'm not 100% sure" caveat |
| Low (<50%) | Suggests asking in Open Loris for expert review |

### Expert Correction

When MoltenLoris gets something wrong:
1. Expert reacts with ❌ or replies with correction
2. Correction logged in activity tracking
3. Optionally creates new knowledge fact from correction
4. MoltenLoris learns from corrections

---

## Analytics & Insights

### Overview Dashboard

| Metric | What It Shows |
|--------|--------------|
| Total Questions | Volume over selected period |
| Automation Rate | % answered without expert |
| Avg Response Time | Time to first answer |
| Satisfaction Score | Average user rating (1-5) |

### Question Trends

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY VOLUME CHART                        │
│  Shows question volume over time                             │
│  Helps identify busy periods, staffing needs                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    STATUS DISTRIBUTION                       │
│  Pie chart: Resolved, Answered, In Progress, Expert Queue    │
│  Helps identify bottlenecks                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SUB-DOMAIN BREAKDOWN                      │
│  Which topics get the most questions?                        │
│  Helps prioritize knowledge building                         │
└─────────────────────────────────────────────────────────────┘
```

### Automation Performance

| Metric | Purpose |
|--------|---------|
| Rules by Acceptance Rate | Which rules work well vs need tuning |
| Trigger Trend | Are auto-answers increasing over time? |
| Rejection Reasons | Why do users reject auto-answers? |

### Knowledge Coverage

| Metric | Purpose |
|--------|---------|
| Facts by Tier | Knowledge quality distribution |
| Expiring Soon | Items needing review |
| Usage Frequency | Which facts are most cited |
| Gap Frequency | Common questions with no matching knowledge |

### Expert Performance

| Metric | Purpose |
|--------|---------|
| Questions Answered | Workload distribution |
| Avg Response Time | Speed of service |
| Satisfaction Ratings | Quality of answers |
| Rules Created | Contribution to automation |

---

## User Stories by Scale

### Individual User: Personal Knowledge System

**Persona**: Alex, a consultant who accumulates knowledge from projects

**Setup**:
- Single-user Open Loris instance
- Uploads project documents, notes, bookmarks
- Creates facts from learnings

**Workflow**:
```
Alex uploads project retrospective PDF
        │
        ▼
System extracts facts: "Client X prefers weekly status reports"
        │
        ▼
6 months later, Alex asks: "What format did Client X want for reports?"
        │
        ▼
Open Loris: "Client X prefers weekly status reports (Source: Project X Retro)"
```

**Value**: "A second brain that actually retrieves"

---

### Small Business: Shared Knowledge Hub

**Persona**: 20-person startup with no dedicated HR/IT/Legal

**Setup**:
- All employees are both askers and potential answerers
- No formal sub-domains—everyone shares everything
- Departments match team structure (Engineering, Sales, Ops)

**Workflow**:
```
New hire asks: "How do I expense a client dinner?"
        │
        ▼
No automation rule exists → Goes to queue
        │
        ▼
Office manager (wearing Ops hat) answers with policy
        │
        ▼
Creates automation rule → Next person gets instant answer
```

**Value**:
- Tribal knowledge captured before people forget
- No single point of failure
- Onboarding accelerates over time

---

### Growing Company: Departmental Experts

**Persona**: 200-person company with specialized teams

**Setup**:
- Sub-domains: HR, Legal, IT, Finance, Facilities
- Dedicated experts in each area
- Departments: Engineering, Product, Sales, Marketing, etc.

**Workflow**:
```
Engineer asks: "Is our software license compliant for commercial use?"
        │
        ▼
AI classifies → Legal sub-domain
        │
        ▼
Legal expert sees in queue, answers with citation to license terms
        │
        ▼
Creates automation rule with GUD = license renewal date
```

**Value**:
- Experts focus on complex questions
- Routine questions automated
- Compliance maintained with GUD tracking

---

### Enterprise: Intake & Triage System

**Persona**: 5000-person enterprise with global operations

**Setup**:
- Multiple sub-domains per department
- Regional variations (US Policy, EU Policy, APAC Policy)
- Integration with Slack via MoltenLoris
- Strict GUD enforcement for compliance

**Workflow**:
```
Employee in Germany asks in #hr-questions: "What's the parental leave policy?"
        │
        ▼
MoltenLoris detects question
        │
        ▼
Queries Open Loris → Finds EU-specific policy
        │
        ▼
Posts answer in Slack with citation and confidence
        │
        ▼
If wrong region detected → Employee corrects → Knowledge updated
```

**Value**:
- Consistent answers across global workforce
- Compliance documentation automatic
- Reduced ticket volume for HR/IT help desks
- Audit trail of what was communicated when

---

### Compliance Use Case: Living Policy Database

**Scenario**: Financial services firm with regulatory requirements

**Setup**:
- All policies uploaded as documents
- Facts extracted with regulatory citations
- GUD dates aligned with review cycles
- Automation rules for common compliance questions

**Workflow**:
```
Quarterly:
  • GUD system flags expiring policies
  • Compliance team reviews/updates
  • New facts extracted from updated docs
  • Automation rules updated

Daily:
  • Employees ask compliance questions
  • Get instant, current answers
  • All interactions logged
  • Audit trail maintained
```

**Value**:
- Regulators can see: "What did employees know, and when?"
- Policies always current (GUD enforcement)
- Reduced compliance training burden
- Consistent messaging across organization

---

## Privacy & AI Provider Options

### The Privacy Spectrum

| Option | Data Location | Use Case |
|--------|--------------|----------|
| Ollama Local | Your servers only | Maximum privacy, regulated industries |
| Ollama Cloud | Ollama infrastructure | Good privacy, no API keys needed |
| Anthropic Claude | Third-party API | Best quality, data sent externally |
| AWS Bedrock | Your AWS account | Enterprise, data in your VPC |
| Azure OpenAI | Your Azure tenant | Enterprise, data in your tenant |

### Configuration

Set in `.env`:
```bash
# Maximum privacy
AI_PROVIDER=local_ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Best quality
AI_PROVIDER=cloud_anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Enterprise (AWS)
AI_PROVIDER=cloud_bedrock
AWS_REGION=us-east-1
```

### What Data Goes to AI?

| Operation | Data Sent |
|-----------|-----------|
| Embedding Generation | Question text, fact content |
| Gap Analysis | Question + relevant facts |
| Turbo Answer | Question + knowledge context |
| Fact Extraction | Document chunks |

**Note**: User PII, credentials, and internal IDs are never sent to AI providers.

---

## Summary: How Open Loris Delivers on Its Promises

| Claim | How It Works |
|-------|--------------|
| "Experts answer once" | Automation rules capture expert answers |
| "Similar questions auto-answered" | Semantic matching with configurable thresholds |
| "Knowledge compounds" | Every answer can become automation; metrics prove growth |
| "AI assists, doesn't replace" | Gap analysis prepares drafts; experts validate |
| "Knowledge tiers" | 0A/0B/0C hierarchy with validation workflow |
| "Stale content expires" | GUD system with 30/7/0 day notifications |
| "Privacy-first" | Local Ollama or your own cloud tenants |
| "Works where you work" | MoltenLoris brings answers to Slack |

---

## Getting Started

1. **Deploy**: `docker-compose up -d`
2. **Login**: admin@loris.local / Password123
3. **Create sub-domains**: Define your expertise areas
4. **Assign experts**: Map people to sub-domains
5. **Upload documents**: Seed your knowledge base
6. **Ask questions**: Start the flywheel
7. **Create rules**: Automate common answers
8. **Watch it compound**: Analytics show growth over time

---

*Open Loris: Slow is smooth, smooth is fast.*
