# Loris Enhancement: Turbo Loris & MoltenLoris Agent

## Document Overview
**Version:** 0.2.0 (Revised)
**Last Updated:** January 2026
**Author:** Kevin Rogers / Claude

---

## Executive Summary

This document specifies two related enhancements to the Loris platform:

1. **Turbo Loris** — A user-controlled fast-answer mode that delivers AI-generated responses when knowledge confidence exceeds a user-selected threshold, with full attribution to knowledge contributors.

2. **MoltenLoris** — An autonomous agent deployment pattern that monitors Slack channels and answers questions using Loris's knowledge base via read-only access to a shared Google Drive folder.

Both enhancements share a core principle: **democratize access to organizational knowledge while maintaining attribution, quality signals, and data integrity.**

### Key Architectural Decision

**Google Drive serves as the shared knowledge distribution layer.** The Loris Web App writes validated knowledge to GDrive as markdown files. MoltenLoris reads from GDrive but cannot write to it. PostgreSQL remains the authoritative source of truth.

---

## Part 1: Turbo Loris

### 1.1 Concept

Turbo Loris inverts the default Loris behavior. Instead of requiring expert validation before delivering answers:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Standard** | Question → Expert Queue → Validated Answer | High-stakes decisions |
| **Turbo** | Question → Knowledge Match → Instant Answer (if confidence ≥ threshold) | Quick lookups, time-sensitive queries |

The key innovation is **user-controlled risk tolerance**: the requester chooses their acceptable confidence threshold.

### 1.2 User Experience

#### Question Submission UI

```
┌─────────────────────────────────────────────────────────────────────┐
│ Ask a Question                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ [Question text input...]                                            │
│                                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Answer Mode                                                      │ │
│ │                                                                  │ │
│ │  ○ Standard (Expert-verified)                                   │ │
│ │    "Slow is smooth, smooth is fast"                             │ │
│ │                                                                  │ │
│ │  ● ⚡ Turbo Loris                                                │ │
│ │    Instant answers from knowledge base                          │ │
│ │                                                                  │ │
│ │    Confidence threshold: [ 75% ▼ ]                              │ │
│ │                                                                  │ │
│ │    ┌──────────────────────────────────────────────────────────┐ │ │
│ │    │ "Fast is rough, rough can be slow"                       │ │ │
│ │    │                                                          │ │ │
│ │    │ Turbo answers are AI-generated from your organization's  │ │ │
│ │    │ knowledge base. They haven't been verified by an expert  │ │ │
│ │    │ for this specific question.                              │ │ │
│ │    └──────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│                                              [ Submit Question ]     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Confidence Threshold Options

| Threshold | Label | Messaging |
|-----------|-------|-----------|
| 90% | "High confidence" | "Tight match — likely accurate" |
| 75% | "Moderate confidence" | "Good match — verify key details" |
| 50% | "Low confidence" | "Best guess — Schrödinger's Answer" |

### 1.3 Turbo Loris Answer Delivery

When Turbo Loris delivers an answer:

```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚡ Turbo Loris Answer                                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ ┌─────────────────────┐                                             │
│ │  [TransWarp Loris]  │  Confidence: 82%                            │
│ │      ⚡ image        │  Your threshold: 75%                        │
│ └─────────────────────┘                                             │
│                                                                      │
│ ────────────────────────────────────────────────────────────────────│
│                                                                      │
│ Based on organizational knowledge, here's what I found:              │
│                                                                      │
│ [Answer content here...]                                            │
│                                                                      │
│ ────────────────────────────────────────────────────────────────────│
│                                                                      │
│ 📚 Sources                                                          │
│                                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ "Vendor Contract Guidelines" — Contracts Department              │ │
│ │  Uploaded by Sarah Chen • Confidence: 87%                        │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ "Standard Terms FAQ" — Legal Department                          │ │
│ │  From answered question • Confidence: 78%                        │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│ ────────────────────────────────────────────────────────────────────│
│                                                                      │
│ 💡 Thanks to Sarah Chen in Contracts — their document               │
│    turbo-charged this Loris!                                        │
│                                                                      │
│ ┌──────────────────────────────┐  ┌────────────────────────────┐   │
│ │ ✓ This helped               │  │ 🔄 Request expert review    │   │
└──────────────────────────────┘  └────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 Attribution System

#### Attribution Data Model

```python
class Attribution(BaseModel):
    """
    Tracks who contributed the knowledge that powered an answer.
    Handles departed employees gracefully.
    """
    
    # Source identification
    source_type: Literal["document", "fact", "automation_rule"]
    source_id: UUID
    
    # Attribution
    attributed_user_id: UUID | None  # Null if user departed
    attributed_department_id: UUID   # Always populated (fallback)
    
    # Contribution context
    contribution_type: Literal["uploaded", "authored", "approved", "created_rule"]
    contribution_date: datetime
    
    # For display
    display_name: str  # Pre-computed: user name or department name
    
    # Match quality
    confidence_score: float
    semantic_similarity: float
```

#### Handling Departed Employees

**Problem:** When an employee leaves, we don't want to show their name in attributions, but we also don't want to query the user table on every Turbo Loris answer.

**Solution:** Event-driven attribution cleanup.

```python
# When user is marked as departed:
async def handle_user_departure(user_id: UUID, departed_at: datetime):
    """
    Called when a user is deactivated/departed.
    Updates all their attributions to department-level.
    """
    
    # Batch update all attributions from this user
    await db.execute("""
        UPDATE attributions
        SET attributed_user_id = NULL,
            display_name = (
                SELECT name FROM departments 
                WHERE id = attributions.attributed_department_id
            )
        WHERE attributed_user_id = :user_id
    """, {"user_id": user_id})
    
    # Log for audit
    await AuditLog.create(
        action="attribution_anonymized",
        user_id=user_id,
        details={"departed_at": departed_at}
    )
```

**Display Logic:**

```python
def get_attribution_display(attribution: Attribution) -> str:
    """
    Returns the display string for an attribution.
    User name if active, department name if departed.
    """
    # display_name is pre-computed and updated on departure
    return attribution.display_name
```

### 1.5 Turbo Loris Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TURBO LORIS WORKFLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  USER SUBMITS QUESTION (Turbo mode, threshold=75%)                  │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 KNOWLEDGE SEARCH                             │   │
│  │                                                              │   │
│  │  1. Generate question embedding                              │   │
│  │  2. Search WisdomFacts (semantic similarity)                 │   │
│  │  3. Search DocumentChunks (if facts insufficient)            │   │
│  │  4. Search AutomationRules (exact pattern matches)           │   │
│  │                                                              │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              CONFIDENCE EVALUATION                           │   │
│  │                                                              │   │
│  │  Aggregate confidence = weighted average of:                 │   │
│  │    - Best fact match similarity (weight: 0.4)               │   │
│  │    - Fact tier score (0a=1.0, 0b=0.9, 0c=0.7) (weight: 0.3) │   │
│  │    - Coverage breadth (% of question concepts) (weight: 0.3)│   │
│  │                                                              │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│              ┌──────────────┴──────────────┐                       │
│              │                              │                       │
│    Confidence ≥ threshold         Confidence < threshold           │
│              │                              │                       │
│              ▼                              ▼                       │
│  ┌────────────────────────┐    ┌────────────────────────────────┐  │
│  │   GENERATE ANSWER      │    │   STANDARD WORKFLOW            │  │
│  │                        │    │                                │  │
│  │ • AI synthesizes from  │    │ • Question enters expert queue │  │
│  │   matched knowledge    │    │ • Gap analysis runs            │  │
│  │ • Collect attributions │    │ • User notified: "Below your   │  │
│  │ • Deliver with Turbo   │    │   threshold, routing to expert"│  │
│  │   Loris branding       │    │                                │  │
│  └───────────┬────────────┘    └────────────────────────────────┘  │
│              │                                                      │
│              ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 USER FEEDBACK                                │   │
│  │                                                              │   │
│  │  "This helped" → Log success, update source confidence      │   │
│  │  "Request expert" → Route to queue, log turbo failure       │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.6 Turbo Loris from Automation Rules

When an expert creates an automation rule from an answered question, future matching questions get Turbo Loris treatment:

```python
async def check_automation_rules(
    question: Question,
    turbo_mode: bool,
    turbo_threshold: float
) -> AutomationMatch | None:
    """
    Existing automation check, enhanced for Turbo Loris.
    """
    
    matches = await automation_service.find_matching_rules(
        embedding=question.embedding,
        organization_id=question.organization_id
    )
    
    if not matches:
        return None
    
    best_match = matches[0]
    
    # Standard automation: requires high threshold (0.85)
    # Turbo mode: uses user-specified threshold
    threshold = turbo_threshold if turbo_mode else 0.85
    
    if best_match.similarity >= threshold:
        return AutomationMatch(
            rule=best_match.rule,
            confidence=best_match.similarity,
            source="automation_rule",
            # Attribution: rule creator
            attribution=Attribution(
                source_type="automation_rule",
                source_id=best_match.rule.id,
                attributed_user_id=best_match.rule.created_by_id,
                attributed_department_id=best_match.rule.department_id,
                contribution_type="created_rule",
                confidence_score=best_match.similarity
            )
        )
    
    return None
```

**Note:** Automation rule matches don't show the attribution credit message ("Thanks to...") — they just deliver the answer with the Turbo Loris branding. This distinguishes expert-created automations from knowledge-base matches.

### 1.7 Admin Configuration

Admins can configure Turbo Loris behavior at the organization level:

```python
class TurboLorisSettings(BaseModel):
    """Organization settings for Turbo Loris."""
    
    # Feature toggle
    enabled: bool = True
    
    # Threshold constraints
    min_threshold: float = 0.50  # Users can't go below this
    default_threshold: float = 0.75
    threshold_options: List[float] = [0.50, 0.75, 0.90]
    
    # Source restrictions
    allow_from_knowledge: bool = True
    allow_from_documents: bool = True
    allow_from_automation: bool = True  # Expert-created rules
    
    # Quality gates
    require_tier_0_facts: bool = False  # Only tier_0a/0b/0c facts
    min_sources_required: int = 1
    
    # Attribution
    show_contributor_names: bool = True  # If false, show department only
    show_confidence_scores: bool = True
```

### 1.8 Data Model Changes

#### Question Model Updates

```python
class Question(Base):
    # ... existing fields ...
    
    # Turbo Loris fields
    turbo_mode: bool = False
    turbo_threshold: float | None = None  # User's selected threshold
    turbo_confidence: float | None = None  # Actual confidence achieved
    turbo_sources: List[UUID] | None = None  # Source IDs used
```

#### New Attribution Table

```python
class TurboAttribution(Base):
    """
    Records which knowledge sources contributed to a Turbo Loris answer.
    """
    __tablename__ = "turbo_attributions"
    
    id: UUID
    question_id: UUID  # FK to questions
    
    # Source
    source_type: str  # "fact", "document", "automation_rule"
    source_id: UUID
    
    # Attribution (nullable user for departed employees)
    attributed_user_id: UUID | None
    attributed_department_id: UUID
    display_name: str  # Pre-computed
    
    # Contribution details
    contribution_type: str
    contribution_date: datetime
    
    # Match quality
    confidence_score: float
    semantic_similarity: float
    
    # Timestamps
    created_at: datetime
```

### 1.9 API Changes

#### Question Submission

```python
class QuestionCreateTurbo(BaseModel):
    """Extended question submission with Turbo Loris options."""
    
    text: str
    category: str | None = None
    priority: str = "medium"
    department: str | None = None
    subdomain_id: UUID | None = None
    
    # Turbo Loris options
    turbo_mode: bool = False
    turbo_threshold: float = 0.75  # Only used if turbo_mode=True
```

#### Question Response

```python
class QuestionResponseTurbo(BaseModel):
    """Response when Turbo Loris answers."""
    
    question: QuestionDetail
    
    # Turbo-specific fields
    turbo_answered: bool
    turbo_confidence: float | None
    turbo_threshold: float | None
    
    # Attribution
    attributions: List[TurboAttributionResponse]
    
    # The answer (if turbo_answered)
    answer: AnswerDetail | None
    
    # Messaging
    confidence_message: str | None  # "High confidence match" etc.
    attribution_message: str | None  # "Thanks to Sarah in Contracts..."
```

---

## Part 2: MoltenLoris Agent

### 2.1 Concept

MoltenLoris is an autonomous agent that:

1. Monitors a Slack channel for questions
2. **Reads** organizational knowledge from a shared Google Drive folder (read-only)
3. Generates answers based on available knowledge
4. Escalates to humans when confidence is insufficient
5. **Prompts humans to capture knowledge** in the Loris Web App (does not write directly)

The architecture prioritizes **security isolation**, **controlled access**, and **data integrity**:

### 2.2 Architecture: GDrive as Shared Knowledge Layer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MOLTENLORIS-ENABLED MODE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         LORIS WEB APP                                       │
│                    (Authoritative Source)                                   │
│                              │                                              │
│                              │ READ/WRITE                                   │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      POSTGRESQL                                      │  │
│   │                   (Ground Truth)                                     │  │
│   │                                                                      │  │
│   │  • All knowledge facts (with embeddings)                            │  │
│   │  • User data, questions, analytics                                   │  │
│   │  • Full audit trail                                                  │  │
│   │  • GUD enforcement                                                   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              │ WRITE (sync on create/update/delete)         │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      GOOGLE DRIVE                                    │  │
│   │              (Read-Only Distribution Layer)                          │  │
│   │                                                                      │  │
│   │  /Loris-Knowledge/                                                   │  │
│   │    /facts/*.md           ← Knowledge facts as markdown              │  │
│   │    /documents/*.pdf      ← Source documents                         │  │
│   │    /automations/*.md     ← Automation rules as markdown             │  │
│   │    /_archived/           ← Expired/deleted content                  │  │
│   │    /_index.json          ← Optional metadata cache                  │  │
│   │                                                                      │  │
│   │  Loris Web App: READ + WRITE                                        │  │
│   │  MoltenLoris:   READ ONLY                                           │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              │ READ ONLY (via Zapier MCP)                   │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      MOLTENLORIS                                     │  │
│   │                (Consumer Only - VM Isolated)                         │  │
│   │                                                                      │  │
│   │  ✓ Reads knowledge from GDrive                                      │  │
│   │  ✓ Answers questions in Slack                                        │  │
│   │  ✓ Escalates to humans when uncertain                                │  │
│   │  ✓ Prompts humans to add knowledge to Loris                         │  │
│   │                                                                      │  │
│   │  ✗ CANNOT write to GDrive                                           │  │
│   │  ✗ CANNOT modify knowledge                                          │  │
│   │  ✗ CANNOT access PostgreSQL                                         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Why Read-Only for MoltenLoris?

| Risk | Prevention |
|------|------------|
| MoltenLoris overwrites validated knowledge | Cannot write to GDrive |
| GDrive and PostgreSQL get out of sync | PostgreSQL is authoritative; GDrive is derived |
| Duplicate or conflicting facts created | Only Loris Web App creates facts |
| Unvalidated knowledge enters the system | All knowledge goes through expert validation |
| Agent creates low-quality data | No write access anywhere |

**Key Principle:** PostgreSQL is always the source of truth. GDrive is a read-only distribution copy that enables MoltenLoris to function without direct database access.

### 2.4 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE CREATION FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EXPERT CREATES KNOWLEDGE (via Loris Web App)                              │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. Expert answers question or creates fact in Loris Web App         │   │
│  │  2. Saved to PostgreSQL (ground truth, embeddings, full metadata)    │   │
│  │  3. GDrive sync triggered: write markdown file to /Loris-Knowledge/  │   │
│  │  4. MoltenLoris can now see the new knowledge                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        KNOWLEDGE CONSUMPTION FLOW                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USER ASKS QUESTION IN SLACK                                               │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. MoltenLoris detects new message                                  │   │
│  │  2. Reads markdown files from GDrive /Loris-Knowledge/               │   │
│  │  3. Matches question to available knowledge                          │   │
│  │  4. If confident: posts answer with sources                          │   │
│  │  5. If not confident: escalates to expert                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         LEARNING FLOW (Human in Loop)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MOLTENLORIS ESCALATES → EXPERT ANSWERS IN SLACK                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. MoltenLoris detects expert response in thread                    │   │
│  │  2. MoltenLoris posts: "Great answer! Consider adding to Loris:"     │   │
│  │     → Link to Loris Web App /add-fact page                           │   │
│  │  3. Expert clicks link, creates fact in Loris Web App                │   │
│  │  4. Saved to PostgreSQL → Synced to GDrive                          │   │
│  │  5. MoltenLoris can use it for future questions                      │   │
│  │                                                                       │   │
│  │  NOTE: MoltenLoris does NOT write anywhere. It only prompts humans.  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.5 Markdown File Format for Knowledge

Knowledge facts are stored as markdown files with YAML frontmatter:

```markdown
<!-- /Loris-Knowledge/facts/contracts/fact-2026-01-28-001.md -->

---
id: fact-2026-01-28-001
created_at: 2026-01-28T14:32:00Z
updated_at: 2026-01-28T14:32:00Z
created_by: sarah.chen@company.com
department: Legal
category: contracts
tier: tier_0b
confidence: 0.92
gud_date: 2026-07-28
tags:
  - vendor
  - contracts
  - renewal
  - terms
source_type: answered_question
source_id: question-abc-123
---

# Standard Vendor Contract Terms

Standard vendor contracts have a 12-month term with automatic renewal unless 
cancelled with 30 days written notice prior to the renewal date.

## Key Points

- Initial term: 12 months
- Renewal: Automatic unless cancelled
- Cancellation notice: 30 days prior to renewal
- Notice method: Written (email acceptable)

## Source

This was validated by Sarah Chen (Legal) on January 28, 2026 in response to 
a question from the Sales team.
```

### 2.6 GDrive Folder Structure

```
/Loris-Knowledge/
├── facts/
│   ├── contracts/
│   │   ├── fact-2026-01-28-001.md
│   │   └── fact-2026-01-25-003.md
│   ├── policies/
│   │   └── fact-2026-01-20-002.md
│   └── procedures/
│       └── ...
├── documents/
│   ├── contracts/
│   │   └── vendor-agreement-template.pdf
│   └── policies/
│       └── data-retention-policy.pdf
├── automations/
│   ├── rule-001-contract-terms.md
│   └── rule-002-nda-duration.md
├── _archived/
│   └── ... (expired/deleted content moved here)
└── _index.json  (optional: metadata cache for faster browsing)
```

### 2.7 Security Architecture

#### VM Isolation

MoltenLoris runs in an isolated virtual machine (UTM on macOS):

| Risk | Mitigation |
|------|------------|
| Agent damages host system | Runs in isolated VM |
| Agent accesses unauthorized data | MCP limits to specific GDrive folders |
| Credentials leak to agent | Zapier holds credentials, agent gets session tokens |
| Agent takes unauthorized actions | GDrive access is READ-ONLY |
| Agent runs amok | VM can be shut down instantly |

#### Zapier MCP Configuration

```yaml
# zapier-mcp-config.yaml

tools:
  # Slack - Read messages from monitored channel
  slack_read:
    app: "Slack"
    action: "Read Channel Messages"
    channel: "#legal-questions"
    permissions:
      - read_messages
      - read_reactions

  # Slack - Post responses
  slack_write:
    app: "Slack"
    action: "Send Channel Message"
    channel: "#legal-questions"
    permissions:
      - post_message
      - add_reaction
    rate_limit: "10/hour"

  # Google Drive - READ ONLY
  gdrive_list:
    app: "Google Drive"
    action: "Find Files in Folder"
    folders:
      - "/Loris-Knowledge/facts"
      - "/Loris-Knowledge/documents"
      - "/Loris-Knowledge/automations"
    permissions:
      - read
    # EXPLICITLY NO:
    # - write
    # - delete
    # - share
    # - modify

  gdrive_download:
    app: "Google Drive"
    action: "Download File"
    permissions:
      - read
    # Used to read file contents
```

### 2.8 MoltenLoris Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MOLTENLORIS WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SCHEDULER (every 5 minutes)                                        │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              CHECK SLACK FOR NEW QUESTIONS                   │   │
│  │                                                              │   │
│  │  MCP Tool: slack_read                                        │   │
│  │  Filter: Messages in last 5 min without 🤖 reaction         │   │
│  │                                                              │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│              ┌──────────────┴──────────────┐                       │
│              │                              │                       │
│         New messages               No new messages                  │
│              │                              │                       │
│              ▼                              ▼                       │
│  ┌────────────────────────┐              (sleep)                   │
│  │   FOR EACH MESSAGE     │                                        │
│  │                        │                                        │
│  │ 1. Mark with 👀 (seen) │                                        │
│  │                        │                                        │
│  │ 2. Search knowledge:   │                                        │
│  │    - List GDrive files │                                        │
│  │    - Read relevant .md │                                        │
│  │    - Match to question │                                        │
│  │                        │                                        │
│  │ 3. Calculate confidence│                                        │
│  │                        │                                        │
│  └───────────┬────────────┘                                        │
│              │                                                      │
│              ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              CONFIDENCE DECISION                             │   │
│  │                                                              │   │
│  │  HIGH (≥75%):                                               │   │
│  │    → Post answer to Slack                                   │   │
│  │    → Mark message with 🤖 (answered)                        │   │
│  │    → Include sources from markdown frontmatter              │   │
│  │                                                              │   │
│  │  MEDIUM (50-75%):                                           │   │
│  │    → Post tentative answer with disclaimer                  │   │
│  │    → Mark message with 🔶 (tentative)                       │   │
│  │    → Tag expert for verification                            │   │
│  │                                                              │   │
│  │  LOW (<50%):                                                │   │
│  │    → Post "I need help with this one"                       │   │
│  │    → Mark message with 🔴 (needs human)                     │   │
│  │    → Tag experts for assistance                             │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  LEARNING PROMPT (when expert answers in thread):                   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  1. Detect expert response to escalated message              │   │
│  │  2. Post thank you + link to Loris Web App:                  │   │
│  │     "Great answer! Add it to Loris so I can help next time:" │   │
│  │     → https://loris.company.com/knowledge/add                │   │
│  │  3. DO NOT write anywhere — human decides whether to save    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.9 Slack Message Formats

#### MoltenLoris Answer (High Confidence)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🤖 MoltenLoris                                              2:34 PM │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Based on our knowledge base, here's what I found:                   │
│                                                                      │
│ Standard vendor contracts have a 12-month term with automatic       │
│ renewal unless cancelled with 30 days written notice.               │
│                                                                      │
│ ───────────────────────────────────────────────────────────────────│
│ 📚 Sources: fact-2026-01-28-001.md (Sarah Chen, Legal)              │
│ 🎯 Confidence: 82%                                                  │
│ ───────────────────────────────────────────────────────────────────│
│                                                                      │
│ _Was this helpful? React with ✅ or ❌_                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### MoltenLoris Tentative Answer (Medium Confidence)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔶 MoltenLoris                                              2:34 PM │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ I found some relevant information, but I'm not fully confident:     │
│                                                                      │
│ [Answer content...]                                                 │
│                                                                      │
│ ───────────────────────────────────────────────────────────────────│
│ ⚠️ Confidence: 62% — An expert should verify this.                 │
│ ───────────────────────────────────────────────────────────────────│
│                                                                      │
│ @sarah.chen — Could you verify this when you have a moment?         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### MoltenLoris Escalation (Low Confidence)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔴 MoltenLoris                                              2:34 PM │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ I don't have enough information to answer this one confidently.     │
│                                                                      │
│ I've notified @sarah.chen and @mike.johnson to help.               │
│                                                                      │
│ ───────────────────────────────────────────────────────────────────│
│ 🔍 What I searched: vendor contract, renewal terms, 90-day notice   │
│ 📊 Best match confidence: 34%                                       │
│ ───────────────────────────────────────────────────────────────────│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Learning Prompt (After Expert Answers)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🤖 MoltenLoris                                              2:45 PM │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Thanks @sarah.chen! Great answer. 👆                                │
│                                                                      │
│ 💡 Want me to remember this for next time?                          │
│ → Add it to Loris: https://loris.company.com/knowledge/add          │
│                                                                      │
│ _(I can't add it myself, but it only takes 30 seconds!)_            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.10 Loris Web App: GDrive Sync Service

The Loris Web App needs a service to sync knowledge to GDrive:

```python
# backend/app/services/gdrive_sync_service.py

class GDriveSyncService:
    """
    Syncs knowledge from PostgreSQL to Google Drive.
    Called on fact create/update/delete when MOLTENLORIS_MODE is enabled.
    """
    
    def __init__(self, gdrive_client: GDriveClient):
        self.gdrive = gdrive_client
        self.base_path = "/Loris-Knowledge"
    
    async def sync_fact(self, fact: WisdomFact) -> None:
        """Write a fact to GDrive as a markdown file."""
        if not settings.MOLTENLORIS_ENABLED:
            return
        
        markdown = self._fact_to_markdown(fact)
        folder = f"{self.base_path}/facts/{fact.category or 'general'}"
        filename = f"fact-{fact.created_at.date()}-{str(fact.id)[:8]}.md"
        
        await self.gdrive.upload_file(
            path=f"{folder}/{filename}",
            content=markdown,
            mime_type="text/markdown"
        )
    
    async def archive_fact(self, fact: WisdomFact) -> None:
        """Move a deleted/expired fact to the archive folder."""
        if not settings.MOLTENLORIS_ENABLED:
            return
        
        old_path = self._get_fact_path(fact)
        new_path = f"{self.base_path}/_archived/facts/{fact.id}.md"
        
        await self.gdrive.move_file(old_path, new_path)
    
    def _fact_to_markdown(self, fact: WisdomFact) -> str:
        """Convert a WisdomFact to markdown with YAML frontmatter."""
        frontmatter = {
            "id": str(fact.id),
            "created_at": fact.created_at.isoformat(),
            "updated_at": fact.updated_at.isoformat(),
            "created_by": fact.created_by.email if fact.created_by else None,
            "department": fact.department,
            "category": fact.category,
            "tier": fact.tier.value,
            "confidence": fact.confidence,
            "gud_date": fact.gud_date.isoformat() if fact.gud_date else None,
            "tags": fact.tags or [],
            "source_type": fact.source_type,
            "source_id": str(fact.source_id) if fact.source_id else None,
        }
        
        yaml_str = yaml.dump(frontmatter, default_flow_style=False)
        
        return f"""---
{yaml_str}---

# {fact.title or 'Knowledge Fact'}

{fact.content}
"""
```

### 2.11 Configuration

#### Environment Variables

```bash
# .env

# MoltenLoris Mode
MOLTENLORIS_ENABLED=true

# Google Drive Integration (for Loris Web App)
GDRIVE_CREDENTIALS_FILE=/path/to/service-account.json
GDRIVE_KNOWLEDGE_FOLDER_ID=your-folder-id
GDRIVE_SYNC_ON_WRITE=true
```

#### Organization Settings

```python
class MoltenLorisSettings(BaseModel):
    """Organization settings for MoltenLoris integration."""
    
    # Feature toggle
    enabled: bool = False
    
    # GDrive configuration
    gdrive_folder_id: str | None = None
    sync_facts: bool = True
    sync_documents: bool = True
    sync_automations: bool = True
    
    # Sync behavior
    sync_on_create: bool = True
    sync_on_update: bool = True
    archive_on_delete: bool = True  # Move to _archived instead of delete
```

### 2.12 Loop Prevention

MoltenLoris must not respond to:
- Its own messages
- Other bots
- Expert responses to questions it escalated (but should post learning prompt)
- Messages in threads it didn't start

```python
def should_process_message(message: SlackMessage) -> bool:
    """
    Determine if MoltenLoris should process this message.
    """
    # Skip own messages
    if message.user_id == MOLTENLORIS_BOT_ID:
        return False
    
    # Skip other bots
    if message.is_bot:
        return False
    
    # Skip if already processed (has reaction)
    if any(r in message.reactions for r in ["👀", "🤖", "🔶", "🔴"]):
        return False
    
    # Skip thread replies (only process top-level messages)
    if message.thread_ts and message.thread_ts != message.ts:
        return False
    
    return True


def should_post_learning_prompt(message: SlackMessage) -> bool:
    """
    Determine if MoltenLoris should post a learning prompt.
    """
    # Only in threads where MoltenLoris escalated
    if not is_escalation_thread(message.thread_ts):
        return False
    
    # Only for non-bot messages
    if message.is_bot:
        return False
    
    # Only if we haven't already prompted
    if thread_has_learning_prompt(message.thread_ts):
        return False
    
    return True
```

### 2.13 Setup Guide for MoltenLoris

#### Prerequisites

- Mac with Apple Silicon or Intel (8GB+ RAM recommended for VM)
- UTM installed ([utm.app](https://utm.app))
- Zapier account (free tier works for testing)
- Anthropic API key
- Slack workspace admin access
- Google Drive folder set up for Loris-Knowledge

#### Step 1: Enable MoltenLoris Mode in Loris Web App

1. Set `MOLTENLORIS_ENABLED=true` in your Loris `.env`
2. Configure GDrive credentials for the Loris Web App
3. Restart Loris backend
4. Verify: Create a test fact and confirm it appears in GDrive

#### Step 2: Create the Virtual Machine

1. Open UTM and click "Create a new virtual machine"
2. Select "Virtualize" → "macOS 12+"
3. Configure resources:
   - Memory: 4GB minimum, 8GB recommended
   - CPU cores: 2-4
   - Storage: 40GB
4. Complete macOS setup in the VM

#### Step 3: Install Moltbot in the VM

```bash
# In the VM terminal:
sudo curl -fsSL https://moltbot.dev/install.sh | bash

# Follow the prompts:
# - Accept the risk warning
# - Choose Anthropic as provider
# - Enter your API key
# - Select claude-sonnet-4-5
# - Skip Telegram setup (unless you want it)
```

#### Step 4: Configure Zapier MCP Server

1. Log into Zapier and create a new MCP server
2. Add these tools (READ-ONLY for GDrive):

**Slack - Read Messages:**
- App: Slack
- Action: "Read Channel Messages"
- Channel: #legal-questions

**Slack - Post Message:**
- App: Slack
- Action: "Send Channel Message"
- Channel: Same channel

**Google Drive - List Files (READ-ONLY):**
- App: Google Drive
- Action: "Find Files in Folder"
- Folder: /Loris-Knowledge
- **Permissions: READ ONLY**

**Google Drive - Download File (READ-ONLY):**
- App: Google Drive
- Action: "Download File"
- **Permissions: READ ONLY**

3. Copy the MCP connection details

#### Step 5: Connect MoltenLoris to Zapier MCP

In the VM:
```
You: Connect to my Zapier MCP
Moltbot: Sure, paste the connection details.
You: [paste Zapier MCP config]
Moltbot: Connected! I can see Slack read/write and Google Drive read access.
```

#### Step 6: Configure MoltenLoris with SOUL.md

Create or update the SOUL.md file (see template in Appendix).

#### Step 7: Start Monitoring

```
You: Start monitoring #legal-questions for questions. Check every 5 minutes.
When you find a question, search the /Loris-Knowledge folder in Google Drive
and answer if confident. If not, tag @sarah.chen for help. You cannot write
to Google Drive - if an expert gives a good answer, just prompt them to add
it to Loris.

Moltbot: Got it. I'll check every 5 minutes. I have read-only access to
Google Drive and will prompt experts to add knowledge through the Loris
web app. Starting now...
```

### 2.14 Handling GUD (Good Until Date)

When facts expire:

1. Loris scheduler marks fact as expired in PostgreSQL
2. GDrive sync service moves file to `/_archived/` folder
3. MoltenLoris no longer sees the expired fact

```python
# In scheduler_service.py
async def check_gud_expiry():
    expired_facts = await get_expired_facts()
    
    for fact in expired_facts:
        # Mark as archived in PostgreSQL
        fact.tier = WisdomTier.ARCHIVED
        await db.commit()
        
        # Move to archive in GDrive
        if settings.MOLTENLORIS_ENABLED:
            await gdrive_sync_service.archive_fact(fact)
        
        # Send notification
        await notification_service.notify_fact_expired(fact)
```

---

## Part 3: Implementation Roadmap

### Phase 1: Turbo Loris (Weeks 1-3)

**Week 1: Backend**
- [ ] Add turbo fields to Question model
- [ ] Create TurboAttribution model and table
- [ ] Implement TurboLorisService with confidence calculation
- [ ] Add turbo_mode and turbo_threshold to question submission endpoint
- [ ] Create attribution cleanup job for departed users

**Week 2: API & Integration**
- [ ] Extend question response schema for Turbo Loris
- [ ] Add admin endpoints for Turbo Loris settings
- [ ] Integrate with existing automation matching
- [ ] Add feedback endpoints for Turbo answers
- [ ] Create analytics for Turbo Loris performance

**Week 3: Frontend**
- [ ] Add Turbo mode toggle to question submission form
- [ ] Create Turbo Loris answer display component
- [ ] Add attribution display with contributor credit
- [ ] Update question detail page for Turbo answers
- [ ] Add Turbo Loris metrics to analytics dashboard

### Phase 2: GDrive Sync (Week 4)

- [ ] Add MOLTENLORIS_ENABLED config flag
- [ ] Implement GDriveSyncService
- [ ] Add sync calls to fact create/update/delete
- [ ] Implement archive behavior for expired/deleted facts
- [ ] Test end-to-end: create fact → appears in GDrive

### Phase 3: MoltenLoris Documentation (Week 5)

- [ ] Write detailed VM setup guide with screenshots
- [ ] Create SOUL.md template
- [ ] Document Zapier MCP configuration (read-only GDrive)
- [ ] Create troubleshooting guide
- [ ] Add to Loris documentation site

### Phase 4: Testing & Refinement (Week 6)

- [ ] End-to-end testing of full flow
- [ ] Test GUD expiry and archival
- [ ] Test learning prompt flow
- [ ] Performance testing (GDrive read latency)
- [ ] Documentation review

---

## Part 4: Testing Strategy

### Turbo Loris Test Cases

```python
class TestTurboLoris:
    async def test_turbo_answer_above_threshold(self):
        """Question with high knowledge match gets instant answer."""
        
    async def test_turbo_below_threshold_routes_standard(self):
        """Question below threshold routes to expert queue."""
        
    async def test_attribution_survives_user_departure(self):
        """Attribution shows department after user leaves."""
        
    async def test_turbo_feedback_updates_confidence(self):
        """User feedback affects source confidence scores."""
```

### GDrive Sync Test Cases

```python
class TestGDriveSync:
    async def test_fact_creation_syncs_to_gdrive(self):
        """Creating a fact in Loris writes markdown to GDrive."""
        
    async def test_fact_update_syncs_to_gdrive(self):
        """Updating a fact updates the GDrive file."""
        
    async def test_fact_deletion_archives_in_gdrive(self):
        """Deleting a fact moves it to _archived folder."""
        
    async def test_gud_expiry_archives_in_gdrive(self):
        """Expired facts are moved to _archived folder."""
        
    async def test_sync_disabled_when_mode_off(self):
        """No GDrive writes when MOLTENLORIS_ENABLED=false."""
```

### MoltenLoris Integration Test Cases

```python
class TestMoltenLorisIntegration:
    async def test_moltenloris_reads_fact_from_gdrive(self):
        """MoltenLoris can read and parse markdown facts."""
        
    async def test_moltenloris_cannot_write_to_gdrive(self):
        """MoltenLoris MCP has read-only GDrive access."""
        
    async def test_learning_prompt_posted_after_expert_answer(self):
        """MoltenLoris prompts expert to add knowledge to Loris."""
```

---

## Appendix A: SOUL.md Template for MoltenLoris

See separate file: `SOUL-TEMPLATE.md`

---

## Appendix B: Confidence Calculation Details

```python
def calculate_turbo_confidence(
    question_embedding: List[float],
    matched_facts: List[WisdomFact],
    matched_documents: List[DocumentChunk]
) -> float:
    """
    Calculate aggregate confidence for Turbo Loris answer.
    
    Factors:
    1. Semantic similarity of best match (40% weight)
    2. Tier score of best fact (30% weight)
    3. Coverage breadth (30% weight)
    """
    
    if not matched_facts and not matched_documents:
        return 0.0
    
    # Best match similarity
    best_similarity = max(
        [f.similarity for f in matched_facts] +
        [d.similarity for d in matched_documents]
    )
    
    # Tier score (facts only)
    tier_scores = {"tier_0a": 1.0, "tier_0b": 0.9, "tier_0c": 0.7, "pending": 0.4}
    best_tier_score = max(
        [tier_scores.get(f.tier, 0.5) for f in matched_facts],
        default=0.5
    )
    
    # Coverage: how many distinct concepts are addressed?
    coverage = min(
        len([f for f in matched_facts if f.similarity > 0.6]) / 3,
        1.0
    )
    
    # Weighted aggregate
    confidence = (
        best_similarity * 0.4 +
        best_tier_score * 0.3 +
        coverage * 0.3
    )
    
    return round(confidence, 2)
```

---

## Appendix C: GDrive API Considerations

### Rate Limits
- Read: 12,000 requests/day (sufficient for most organizations)
- Write: 3,000 requests/day (Loris Web App only)

### Latency
- PostgreSQL query: ~10ms
- GDrive API call: ~200-500ms

MoltenLoris will be slower than the web app. This is acceptable for Slack use cases.

### Fallback Behavior

If GDrive is unavailable:
- **Loris Web App:** Continues normally (PostgreSQL is authoritative)
- **MoltenLoris:** Escalates all questions until GDrive is back

---

*This document will be refined during implementation.*
