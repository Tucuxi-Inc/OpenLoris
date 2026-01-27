# Loris Project Planning Documents

## Overview

**Loris** is an intelligent Q&A platform that connects business users with domain experts. Think of it as "Glean+" - instead of giving users search results to sift through, Loris delivers curated, expert-validated answers that improve over time through automation.

**Legal Loris** is the first implementation, focused on legal departments.

## Project Concept

```
USER: "Can we add a non-compete clause to the vendor contract?"

     ┌──────────────────────────────────────────────┐
     │                   LORIS                       │
     │                                               │
     │   1. Search automation rules                  │
     │   2. If match → Instant TransWarp answer     │
     │   3. If no match → Expert queue + gap analysis│
     │   4. Expert answers → Knowledge compounds     │
     └──────────────────────────────────────────────┘

ANSWER: "Here's what I found..." (with source citations)
```

## Key Value Propositions

1. **Users get answers, not search results** - Human-curated responses
2. **Knowledge compounds** - Every answer can become automation
3. **Freshness managed** - GUD dates ensure nothing goes stale
4. **Full visibility** - Track questions, response times, automation rates

## Planning Documents

| # | Document | Description |
|---|----------|-------------|
| 01 | [Project Vision](./01-PROJECT-VISION.md) | Executive summary, core workflow, success metrics |
| 02 | [User Personas](./02-USER-PERSONAS.md) | Business user, domain expert, admin personas and journeys |
| 03 | [System Architecture](./03-SYSTEM-ARCHITECTURE.md) | Technical architecture, services, data flow |
| 04 | [Data Model](./04-DATA-MODEL.md) | Database schema, models, relationships |
| 05 | [API Specification](./05-API-SPECIFICATION.md) | REST API endpoints, request/response formats |
| 06 | [Automation Workflow](./06-AUTOMATION-WORKFLOW.md) | Auto-answering, gap analysis, knowledge compounding |
| 07 | [UI Wireframes](./07-UI-WIREFRAMES.md) | Screen layouts, components, design system |
| 08 | [Migration Strategy](./08-MIGRATION-STRATEGY.md) | CounselScope → Loris transformation plan |

## Implementation Guide

| Document | Description |
|----------|-------------|
| [Claude Code Guide](./CLAUDE-CODE-GUIDE.md) | **Start here for implementation.** Detailed instructions for AI assistants, Tufte-inspired design system, code patterns, and aesthetic guidelines. |

## Quick Links

### For AI Assistants / Claude Code
- **[CLAUDE-CODE-GUIDE.md](./CLAUDE-CODE-GUIDE.md)** - Start here. Contains design system, code patterns, aesthetic rules.

### For Understanding the Product
- Start with [01-PROJECT-VISION.md](./01-PROJECT-VISION.md)
- Then read [02-USER-PERSONAS.md](./02-USER-PERSONAS.md)

### For Technical Implementation
- Architecture: [03-SYSTEM-ARCHITECTURE.md](./03-SYSTEM-ARCHITECTURE.md)
- Data model: [04-DATA-MODEL.md](./04-DATA-MODEL.md)
- APIs: [05-API-SPECIFICATION.md](./05-API-SPECIFICATION.md)

### For the Automation System
- [06-AUTOMATION-WORKFLOW.md](./06-AUTOMATION-WORKFLOW.md) explains the "Glean+" philosophy

### For UI/UX
- [07-UI-WIREFRAMES.md](./07-UI-WIREFRAMES.md) has detailed wireframes

### For Implementation Planning
- [08-MIGRATION-STRATEGY.md](./08-MIGRATION-STRATEGY.md) has the 8-week roadmap

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy 2.0, PostgreSQL + pgvector |
| Frontend | React, TypeScript, Tailwind CSS, React Query |
| AI | Multi-provider (Ollama, Anthropic, Bedrock, Azure) |
| Infrastructure | Docker, Redis, Celery |

## Project Status

- [x] Project vision defined
- [x] User personas documented
- [x] Architecture designed
- [x] Data model specified
- [x] API specification written
- [x] Automation workflow documented
- [x] UI wireframes created
- [x] Migration strategy planned
- [ ] Implementation (Phase 1-8)

## Open Questions

1. Multi-domain support in v1? (Recommendation: Legal only, architecture for multi)
2. Expert routing strategy? (Round-robin, topic-based, first-available)
3. Hard SLAs with escalation? (Recommendation: Soft SLAs v1, hard in v2)
4. External/guest users? (Recommendation: Internal only v1)

---

*Last updated: January 2026*
