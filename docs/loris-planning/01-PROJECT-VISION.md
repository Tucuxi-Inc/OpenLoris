# Loris: Intelligent Domain Expert Q&A Platform

## Project Vision Document
**Version:** 0.1.0 (Draft)
**Last Updated:** January 2026
**Status:** Planning Phase

---

## Executive Summary

**Loris** is an intelligent question-and-answer platform that bridges the gap between business users seeking domain expertise and subject matter experts (SMEs) who hold institutional knowledge. The platform leverages AI to automate routine Q&A while ensuring complex or novel questions receive proper human expert attention.

The first implementation, **Legal Loris**, focuses on legal departments, enabling employees to get answers to legal questions efficiently while tracking response times, automating common queries, and measuring the value delivered by the legal team.

---

## The Problem

Organizations face a persistent challenge: **institutional knowledge is siloed in experts' heads**.

1. **Business users** repeatedly ask the same questions that have been answered before
2. **Domain experts** spend significant time answering routine questions instead of high-value work
3. **No tracking** exists for questions asked, time to response, or patterns in inquiries
4. **Knowledge decay** - answers given in email or Slack are lost and never reused
5. **No visibility** into the volume and types of questions being asked
6. **Inconsistent answers** when different experts respond differently to similar questions

---

## The Solution: Loris

Loris creates a **structured, intelligent Q&A workflow** with:

### For Business Users (Question Askers)
- Simple chat-like interface to ask questions
- Dashboard showing all past questions and their status
- Notification when answers are ready
- Ability to indicate if an automated answer doesn't quite fit their situation
- Searchable history of Q&A for self-service

### For Domain Experts (Knowledge Owners)
- Upload and manage existing FAQs, documents, and knowledge
- Connect to document repositories (Google Drive, OneDrive, SharePoint)
- Review incoming questions with AI-proposed answers
- Approve, edit, or request clarification
- Elect to automate answers for similar future questions
- Track metrics on question volume, response time, and automation rate

### For Organizations (Leadership)
- Visibility into question volume and patterns
- Metrics on expert time spent answering questions
- Cost savings analysis from automation
- Knowledge gap identification
- Response time SLAs and tracking

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BUSINESS USER FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. User asks question via chat interface                                   │
│                          ↓                                                  │
│  2. System searches existing knowledge base                                 │
│                          ↓                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    AUTOMATION CHECK                                   │  │
│  │                                                                       │  │
│  │  Is there an approved automated answer for this or similar question? │  │
│  │                                                                       │  │
│  │     YES → Deliver TransWarp Loris answer immediately                  │  │
│  │           User can: ✓ Accept  OR  ⚑ Request Human Review              │  │
│  │                                                                       │  │
│  │     NO  → Continue to expert queue                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                          ↓                                                  │
│  3. Question enters Expert Queue with AI analysis:                          │
│     • What we already know (with source links)                              │
│     • Knowledge gaps identified                                             │
│     • Proposed answer or proposed clarifying questions                      │
│                          ↓                                                  │
│  4. User sees "Researching..." with Research Loris image                    │
│     Question tracked for response time                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          DOMAIN EXPERT FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Expert sees question in queue with AI analysis                          │
│                          ↓                                                  │
│  2. Reviews:                                                                │
│     • Original question                                                     │
│     • Relevant existing knowledge (with source links)                       │
│     • Identified gaps                                                       │
│     • AI-proposed answer                                                    │
│                          ↓                                                  │
│  3. Expert action options:                                                  │
│                                                                             │
│     [👍 Approve Proposed]  - Send AI answer as-is                           │
│     [✏️ Edit & Send]       - Modify answer, then send                       │
│     [❓ Ask Clarification] - Request more info from user                    │
│     [🔗 Assign/Escalate]   - Route to another expert                        │
│                          ↓                                                  │
│  4. After answering, expert can:                                            │
│                                                                             │
│     [🤖 Automate This]     - Future similar questions get this answer       │
│     [📝 Add to Knowledge]  - Save as new knowledge fact                     │
│     [✓ Done]               - Complete without automation                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## User Acceptance of Automated Answers

When a user receives an automated (TransWarp Loris) answer:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  [TransWarp Loris Image]                                                    │
│                                                                             │
│  "Based on our knowledge base, here's what I found:"                        │
│                                                                             │
│  [Answer content with source citations]                                     │
│                                                                             │
│  ────────────────────────────────────────────────────────────────────────   │
│                                                                             │
│  Was this helpful?                                                          │
│                                                                             │
│  [✓ Yes, this answers my question]                                          │
│                                                                             │
│  [⚑ My situation is different - request human review]                       │
│     └─→ Opens text field: "Please explain how your situation differs..."    │
│         └─→ Question re-enters expert queue with user's clarification       │
│             AND the automated answer that didn't quite fit                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Differentiators

### 1. **Gap Analysis Engine**
Unlike simple FAQ matching, Loris performs intelligent gap analysis:
- Identifies what portion of the question is already answered in existing knowledge
- Highlights specific gaps that need expert input
- Suggests clarifying questions when the original query is ambiguous

### 2. **Progressive Automation**
- Starts with 0% automation
- Each answered question can become an automated response
- Experts control what gets automated
- Users can always request human review

### 3. **Full Audit Trail**
- Every question tracked from submission to resolution
- Source citations for all answers
- Response time metrics
- Automation acceptance rates

### 4. **Visual Personality**
Different Loris characters communicate system state:
- **Standard Loris** - Initial question submission
- **TransWarp Loris** - Automated instant answer
- **Research Loris** - Question in expert queue
- **Thinking Loris** - Processing/analyzing
- **Expert Loris** - Human expert reviewing
- **Celebration Loris** - Question resolved

---

## Legal Loris: First Implementation

### Domain-Specific Features

**Inherited from CounselScope:**
- Outside counsel bill upload and analysis
- Cost savings estimation (in-house vs. external)
- Legal practice area categorization
- Attorney billing rate benchmarks

**New for Legal Loris:**
- Track time savings from automated legal answers
- Identify questions that frequently need external counsel
- Legal-specific knowledge taxonomy
- Matter/project association for questions

### Target Users

**Business Users:**
- Employees with legal questions
- Business unit leaders
- Project managers
- Procurement teams
- HR representatives

**Domain Experts:**
- General Counsel
- In-house attorneys
- Legal operations
- Paralegals
- Contract managers

---

## Success Metrics

### Efficiency Metrics
| Metric | Target |
|--------|--------|
| Average response time | < 4 hours |
| Automation rate | > 40% within 6 months |
| Automated answer acceptance | > 85% |
| Questions per expert per day | Reduced by 30% |

### Quality Metrics
| Metric | Target |
|--------|--------|
| User satisfaction (resolved) | > 4.5/5 |
| Answer accuracy (spot-check) | > 95% |
| Knowledge reuse rate | > 60% |

### Business Value Metrics
| Metric | Target |
|--------|--------|
| Expert time saved | Track hours/week |
| Cost avoidance (vs. external) | Track $ value |
| Questions diverted from email/Slack | > 80% |

---

## Technical Foundation

### Leveraging CounselScope

Loris will be built on CounselScope's proven infrastructure:

| Component | CounselScope Capability | Loris Usage |
|-----------|------------------------|-------------|
| Knowledge Management | Document upload, parsing, fact extraction | Core knowledge base |
| Semantic Search | pgvector embeddings | Question-to-knowledge matching |
| AI Provider Abstraction | Multi-provider (Ollama, Anthropic, Bedrock, Azure) | Gap analysis, answer generation |
| Billing Intelligence | Rate management, cost projection | Cost savings analysis |
| Database | PostgreSQL with async SQLAlchemy | Data persistence |
| Frontend | React + TypeScript + Tailwind | User interface foundation |

### New Components Required

| Component | Purpose |
|-----------|---------|
| User Authentication | Business user vs. expert accounts |
| Question Queue System | Track questions through lifecycle |
| Notification Service | Alert users when answers ready |
| Automation Engine | Match questions to automated answers |
| Dashboard System | User-specific views of their questions |
| External Integrations | Google Drive, OneDrive, SharePoint |
| Analytics Dashboard | Metrics and reporting |

---

## Phased Rollout

### Phase 1: Foundation (MVP)
- Two-tier user system (business user, domain expert)
- Question submission interface
- Expert review queue
- Basic knowledge search
- Manual answer approval
- Simple dashboard

### Phase 2: Intelligence
- Gap analysis engine
- AI-proposed answers
- Answer automation with expert approval
- Semantic question matching
- User feedback on automated answers

### Phase 3: Integration
- External repository connections (Google Drive, OneDrive)
- Notification system (email, Slack)
- Calendar integration for response time tracking
- SSO/SAML authentication

### Phase 4: Analytics & Optimization
- Full analytics dashboard
- Cost savings reporting
- Knowledge effectiveness metrics
- Recommendation engine for automation candidates

---

## Open Questions

1. **Multi-domain support**: Should v1 support multiple domains (Legal, IT, HR) or just Legal?
   - *Recommendation:* Focus on Legal for v1, design architecture for multi-domain

2. **Expert routing**: How are questions routed to specific experts?
   - *Options:* Round-robin, topic-based, skill-based, first-available

3. **SLA enforcement**: Should there be hard SLAs with escalation?
   - *Recommendation:* Soft SLAs with visibility, hard escalation in v2

4. **Guest access**: Can external users (vendors, contractors) ask questions?
   - *Recommendation:* Internal only for v1

5. **Mobile experience**: Native app or responsive web?
   - *Recommendation:* Responsive web for v1

---

## Appendix: Loris Visual Identity

The Loris (slow loris) was chosen as the mascot because:
- Slow lorises are known for being methodical and thorough
- The "TransWarp Loris" with speed lines represents automation making slow things fast
- The cute appearance makes the system feel approachable
- Different Loris variants can communicate system state visually

### Planned Loris Variants
- Standard/Friendly Loris - Welcome, general UI
- TransWarp Loris - Automated instant answers
- Research Loris - In expert queue, being researched
- Thinking Loris - Processing animation
- Expert Loris - Human expert is reviewing
- Celebration Loris - Successfully resolved
- Confused Loris - Need more information
- Alert Loris - Time-sensitive or urgent

---

*This document will be updated as requirements are refined.*
