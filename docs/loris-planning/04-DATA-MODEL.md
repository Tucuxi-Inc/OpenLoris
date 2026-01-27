# Loris: Data Model Specification

## Document Overview
**Version:** 0.1.0 (Draft)
**Last Updated:** January 2026

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LORIS DATA MODEL (HIGH LEVEL)                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐               │
│  │  Organization   │────────<│      User       │>────────│   UserSession   │               │
│  └─────────────────┘    1:N  └────────┬────────┘   1:N   └─────────────────┘               │
│                                       │                                                     │
│                         ┌─────────────┼─────────────┐                                       │
│                         │             │             │                                       │
│                        1:N           1:N           1:N                                      │
│                         │             │             │                                       │
│                         ▼             ▼             ▼                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                             │
│  │    Question     │  │    Answer       │  │  Notification   │                             │
│  │   (asked_by)    │  │  (created_by)   │  │                 │                             │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────┘                             │
│           │                    │                                                            │
│          1:N                  1:1                                                           │
│           │                    │                                                            │
│           ▼                    │                                                            │
│  ┌─────────────────┐          │                                                            │
│  │QuestionMessage  │          │                                                            │
│  │ (clarifications)│          │                                                            │
│  └─────────────────┘          │                                                            │
│           │                    │                                                            │
│           └────────────────────┘                                                            │
│                    │                                                                        │
│                   N:M                                                                       │
│                    │                                                                        │
│                    ▼                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐                       │
│  │                     KNOWLEDGE LAYER                              │                       │
│  │                                                                  │                       │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │                       │
│  │  │ WisdomFact      │  │KnowledgeDocument│  │ WisdomCategory  │  │                       │
│  │  │                 │  │                 │  │                 │  │                       │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────────┘  │                       │
│  │           │                    │                                 │                       │
│  │          1:1                  1:N                                │                       │
│  │           │                    │                                 │                       │
│  │           ▼                    ▼                                 │                       │
│  │  ┌─────────────────┐  ┌─────────────────┐                       │                       │
│  │  │ WisdomEmbedding │  │ DocumentChunk   │                       │                       │
│  │  └─────────────────┘  └─────────────────┘                       │                       │
│  │                                                                  │                       │
│  └──────────────────────────────────────────────────────────────────┘                       │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐                       │
│  │                     AUTOMATION LAYER                             │                       │
│  │                                                                  │                       │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │                       │
│  │  │ AutomationRule  │──│RuleEmbedding    │  │ AutomationLog   │  │                       │
│  │  │                 │  │                 │  │                 │  │                       │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │                       │
│  │                                                                  │                       │
│  └──────────────────────────────────────────────────────────────────┘                       │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐                       │
│  │                     BILLING LAYER (from CounselScope)           │                       │
│  │                                                                  │                       │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │                       │
│  │  │    LawFirm      │  │  BillingRate    │  │ CounselInvoice  │  │                       │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │                       │
│  │                                                                  │                       │
│  └──────────────────────────────────────────────────────────────────┘                       │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Models

### 1. Organization

Multi-tenant support for different companies/departments.

```python
class Organization(Base):
    __tablename__ = "organizations"

    id: UUID                        # Primary key
    name: str                       # Organization name
    slug: str                       # URL-safe identifier (unique)
    domain: str | None              # Email domain for auto-assignment
    settings: JSON                  # Organization-specific settings

    # Branding
    logo_url: str | None            # Custom logo
    primary_color: str | None       # Brand color

    # Limits
    max_users: int | None           # User limit (null = unlimited)
    max_questions_per_month: int | None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Relationships
    users: List[User]
    questions: List[Question]
    knowledge_documents: List[KnowledgeDocument]
    automation_rules: List[AutomationRule]
```

### 2. User

Enhanced user model with role-based access.

```python
class UserRole(str, Enum):
    BUSINESS_USER = "business_user"     # Can ask questions, view own history
    DOMAIN_EXPERT = "domain_expert"     # Can answer, manage knowledge, automate
    ADMIN = "admin"                     # Full access including user management

class User(Base):
    __tablename__ = "users"

    id: UUID                        # Primary key
    organization_id: UUID           # FK to Organization

    # Identity
    email: str                      # Unique within org
    name: str                       # Display name
    avatar_url: str | None          # Profile picture

    # Authentication
    hashed_password: str            # bcrypt hash

    # Role & Status
    role: UserRole                  # business_user, domain_expert, admin
    is_active: bool = True          # Account enabled
    is_verified: bool = False       # Email verified

    # Metadata
    department: str | None          # e.g., "Marketing", "Engineering"
    title: str | None               # Job title

    # Preferences
    notification_preferences: JSON  # {email: bool, in_app: bool, ...}

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    # Relationships
    organization: Organization
    questions_asked: List[Question]         # Questions this user asked
    answers_given: List[Answer]             # Answers this expert provided
    automation_rules: List[AutomationRule]  # Rules this expert created
    notifications: List[Notification]
```

### 3. UserSession

Session management for security.

```python
class UserSession(Base):
    __tablename__ = "user_sessions"

    id: UUID                        # Primary key
    user_id: UUID                   # FK to User

    refresh_token_hash: str         # Hashed refresh token
    device_info: str | None         # User agent, device type
    ip_address: str | None          # Last known IP

    is_active: bool = True          # Can be revoked

    created_at: datetime
    expires_at: datetime
    last_used_at: datetime
```

---

## Question & Answer Models

### 4. Question

Core model for tracking questions through their lifecycle.

```python
class QuestionStatus(str, Enum):
    SUBMITTED = "submitted"             # Just received
    PROCESSING = "processing"           # Checking for automation
    AUTO_ANSWERED = "auto_answered"     # Automated answer delivered
    HUMAN_REQUESTED = "human_requested" # User rejected auto-answer
    EXPERT_QUEUE = "expert_queue"       # Waiting for expert
    IN_PROGRESS = "in_progress"         # Expert working on it
    NEEDS_CLARIFICATION = "needs_clarification"
    ANSWERED = "answered"               # Expert answered
    RESOLVED = "resolved"               # User confirmed satisfied
    CLOSED = "closed"                   # Closed without resolution

class QuestionPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class Question(Base):
    __tablename__ = "questions"

    id: UUID                        # Primary key
    organization_id: UUID           # FK to Organization
    asked_by_id: UUID               # FK to User (business user)

    # Question Content
    original_text: str              # Original question text
    category: str | None            # Topic category
    tags: List[str]                 # Additional tags

    # File attachments
    attachments: JSON               # [{filename, url, type}, ...]

    # Status & Priority
    status: QuestionStatus
    priority: QuestionPriority = QuestionPriority.NORMAL

    # Assignment
    assigned_to_id: UUID | None     # FK to User (expert)

    # Automation tracking
    automation_rule_id: UUID | None # If auto-answered, which rule
    auto_answer_accepted: bool | None  # True = accepted, False = rejected, None = pending
    rejection_reason: str | None    # Why user requested human review

    # Gap Analysis Results (stored for expert view)
    gap_analysis: JSON | None       # {relevant_knowledge, gaps, proposed_answer, ...}

    # Metrics
    response_time_seconds: int | None  # Time to first answer
    resolution_time_seconds: int | None # Time to resolved status
    satisfaction_rating: int | None     # 1-5 rating from user

    # Timestamps
    created_at: datetime
    updated_at: datetime
    first_response_at: datetime | None
    resolved_at: datetime | None

    # Relationships
    organization: Organization
    asked_by: User
    assigned_to: User | None
    automation_rule: AutomationRule | None
    messages: List[QuestionMessage]
    answer: Answer | None
    knowledge_used: List[QuestionKnowledge]
```

### 5. QuestionMessage

For back-and-forth clarifications.

```python
class MessageType(str, Enum):
    QUESTION = "question"           # Original or follow-up question
    CLARIFICATION_REQUEST = "clarification_request"  # Expert asks for more info
    CLARIFICATION_RESPONSE = "clarification_response"  # User provides info
    SYSTEM = "system"               # System-generated message

class QuestionMessage(Base):
    __tablename__ = "question_messages"

    id: UUID                        # Primary key
    question_id: UUID               # FK to Question
    user_id: UUID                   # FK to User (who sent)

    message_type: MessageType
    content: str                    # Message text
    attachments: JSON               # [{filename, url, type}, ...]

    created_at: datetime

    # Relationships
    question: Question
    user: User
```

### 6. Answer

Expert's answer to a question.

```python
class AnswerSource(str, Enum):
    EXPERT = "expert"               # Human expert wrote it
    AI_APPROVED = "ai_approved"     # AI proposed, expert approved as-is
    AI_EDITED = "ai_edited"         # AI proposed, expert edited
    AUTOMATION = "automation"       # Delivered by automation rule

class Answer(Base):
    __tablename__ = "answers"

    id: UUID                        # Primary key
    question_id: UUID               # FK to Question (unique)
    created_by_id: UUID             # FK to User (expert or system)

    # Answer Content
    content: str                    # Rich text answer
    source: AnswerSource            # How this answer was created

    # If AI-assisted
    original_ai_proposal: str | None   # What AI originally proposed

    # Knowledge Citations
    cited_knowledge: JSON           # [{fact_id, document_id, excerpt}, ...]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None   # When user saw it

    # Relationships
    question: Question
    created_by: User
```

### 7. QuestionKnowledge (Junction Table)

Tracks which knowledge facts were relevant to a question.

```python
class QuestionKnowledge(Base):
    __tablename__ = "question_knowledge"

    id: UUID                        # Primary key
    question_id: UUID               # FK to Question
    wisdom_fact_id: UUID            # FK to WisdomFact

    relevance_score: float          # 0-1 semantic similarity
    was_cited: bool = False         # Actually used in answer
    was_helpful: bool | None        # Expert feedback

    created_at: datetime
```

---

## Automation Models

### 8. AutomationRule

Defines when to auto-answer similar questions.

```python
class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: UUID                        # Primary key
    organization_id: UUID           # FK to Organization
    created_by_id: UUID             # FK to User (expert who created)

    # Rule Definition
    name: str                       # Human-readable name
    description: str | None         # Why this rule exists

    # Source question & answer
    source_question_id: UUID | None # FK to Question (origin of rule)
    canonical_question: str         # The "template" question
    canonical_answer: str           # The automated answer to deliver

    # Matching Configuration
    similarity_threshold: float = 0.85  # Min cosine similarity to match
    category_filter: str | None     # Only match questions in this category
    exclude_keywords: List[str]     # Don't match if these words present

    # Status
    is_enabled: bool = True         # Active or paused
    requires_approval: bool = False # If true, just suggest don't auto-send

    # Metrics
    times_triggered: int = 0        # How many times matched
    times_accepted: int = 0         # User accepted auto-answer
    times_rejected: int = 0         # User requested human review

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_triggered_at: datetime | None

    # Relationships
    organization: Organization
    created_by: User
    source_question: Question | None
    embedding: AutomationRuleEmbedding
    logs: List[AutomationLog]
```

### 9. AutomationRuleEmbedding

Vector embedding for the canonical question.

```python
class AutomationRuleEmbedding(Base):
    __tablename__ = "automation_rule_embeddings"

    id: UUID                        # Primary key
    rule_id: UUID                   # FK to AutomationRule (unique)

    # Vector (pgvector)
    embedding: Vector(384)          # sentence-transformer embedding

    # Metadata
    model_name: str                 # Which model generated this
    generated_at: datetime

    # Relationship
    rule: AutomationRule
```

### 10. AutomationLog

Audit trail of automation events.

```python
class AutomationLogAction(str, Enum):
    MATCHED = "matched"             # Rule matched a question
    DELIVERED = "delivered"         # Auto-answer was shown to user
    ACCEPTED = "accepted"           # User accepted
    REJECTED = "rejected"           # User requested human review
    SKIPPED = "skipped"             # Matched but didn't deliver (below threshold)

class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id: UUID                        # Primary key
    rule_id: UUID                   # FK to AutomationRule
    question_id: UUID               # FK to Question

    action: AutomationLogAction
    similarity_score: float         # Actual similarity that triggered

    user_feedback: str | None       # If rejected, why

    created_at: datetime

    # Relationships
    rule: AutomationRule
    question: Question
```

---

## Knowledge Models (From CounselScope)

### 11. WisdomFact

Validated knowledge facts.

```python
class WisdomTier(str, Enum):
    TIER_0A = "0A"      # >95% confidence, expert validated
    TIER_0B = "0B"      # 85-95% confidence, validated
    TIER_0C = "0C"      # <85% confidence, needs review
    PENDING = "PENDING" # Newly extracted
    ARCHIVED = "ARCHIVED" # Outdated

class WisdomFact(Base):
    __tablename__ = "wisdom_facts"

    id: UUID                        # Primary key
    organization_id: UUID           # FK to Organization

    # Content
    domain: str                     # e.g., "Legal", "HR", "IT"
    category: str                   # Sub-category
    content: str                    # The actual fact/knowledge

    # Source tracking
    source_document_id: UUID | None # FK to KnowledgeDocument
    source_answer_id: UUID | None   # FK to Answer (if from Q&A)

    # Quality
    tier: WisdomTier
    confidence_score: float         # 0-1
    importance: int                 # 1-10

    # Expiration
    good_until_date: date | None    # When this expires
    is_perpetual: bool = False      # Never expires
    contact_person_id: UUID | None  # Who to contact if expired

    # Timestamps
    created_at: datetime
    updated_at: datetime
    validated_at: datetime | None
    validated_by_id: UUID | None    # FK to User

    # Relationships
    organization: Organization
    source_document: KnowledgeDocument | None
    source_answer: Answer | None
    validated_by: User | None
    embedding: WisdomEmbedding
```

### 12. WisdomEmbedding

Vector embedding for semantic search.

```python
class WisdomEmbedding(Base):
    __tablename__ = "wisdom_embeddings"

    id: UUID                        # Primary key
    wisdom_fact_id: UUID            # FK to WisdomFact (unique)

    embedding: Vector(384)          # sentence-transformer embedding
    model_name: str                 # Model used

    generated_at: datetime

    # Relationship
    wisdom_fact: WisdomFact
```

### 13. KnowledgeDocument

Source documents uploaded by experts.

```python
class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    ERROR = "error"

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: UUID                        # Primary key
    organization_id: UUID           # FK to Organization
    uploaded_by_id: UUID            # FK to User

    # File info
    filename: str
    file_type: str                  # pdf, docx, txt, md
    file_size: int                  # bytes
    storage_url: str                # Where file is stored

    # Metadata
    title: str | None
    description: str | None
    department: str | None
    tags: List[str]

    # Processing status
    status: DocumentStatus
    error_message: str | None

    # Content stats
    page_count: int | None
    word_count: int | None

    # Expiration
    good_until_date: date | None
    is_perpetual: bool = False
    contact_person_id: UUID | None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    parsed_at: datetime | None

    # Relationships
    organization: Organization
    uploaded_by: User
    chunks: List[DocumentChunk]
    extracted_facts: List[WisdomFact]
```

### 14. DocumentChunk

Parsed sections of documents.

```python
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: UUID                        # Primary key
    document_id: UUID               # FK to KnowledgeDocument

    content: str                    # Chunk text
    chunk_index: int                # Order in document
    page_number: int | None         # Source page

    # For retrieval
    embedding: Vector(384) | None   # Optional pre-computed embedding

    created_at: datetime

    # Relationships
    document: KnowledgeDocument
```

---

## Notification Models

### 15. Notification

In-app and email notifications.

```python
class NotificationType(str, Enum):
    QUESTION_SUBMITTED = "question_submitted"
    QUESTION_ANSWERED = "question_answered"
    QUESTION_AUTO_ANSWERED = "question_auto_answered"
    QUESTION_NEEDS_CLARIFICATION = "question_needs_clarification"
    QUESTION_HUMAN_REQUESTED = "question_human_requested"
    QUESTION_SLA_WARNING = "question_sla_warning"
    AUTOMATION_TRIGGERED = "automation_triggered"
    KNOWLEDGE_EXPIRED = "knowledge_expired"
    SYSTEM_ANNOUNCEMENT = "system_announcement"

class Notification(Base):
    __tablename__ = "notifications"

    id: UUID                        # Primary key
    user_id: UUID                   # FK to User (recipient)

    notification_type: NotificationType
    title: str                      # Short headline
    message: str                    # Full message

    # Related entities
    question_id: UUID | None        # FK to Question
    answer_id: UUID | None          # FK to Answer

    # Delivery status
    is_read: bool = False
    read_at: datetime | None

    # Email delivery
    email_sent: bool = False
    email_sent_at: datetime | None

    created_at: datetime

    # Relationships
    user: User
    question: Question | None
    answer: Answer | None
```

---

## Analytics Models

### 16. DailyMetrics

Pre-aggregated daily statistics for fast dashboard queries.

```python
class DailyMetrics(Base):
    __tablename__ = "daily_metrics"

    id: UUID                        # Primary key
    organization_id: UUID           # FK to Organization
    metric_date: date               # Which day

    # Volume
    questions_submitted: int
    questions_auto_answered: int
    questions_expert_answered: int
    questions_resolved: int

    # Automation
    automation_triggers: int
    automation_accepts: int
    automation_rejects: int

    # Response time (seconds)
    avg_response_time: int | None
    min_response_time: int | None
    max_response_time: int | None

    # Satisfaction
    avg_satisfaction: float | None
    satisfaction_responses: int

    # Expert workload
    unique_experts_active: int

    # Knowledge
    knowledge_facts_created: int
    automation_rules_created: int

    created_at: datetime

    # Index on (organization_id, metric_date) for fast queries
```

---

## Billing Models (From CounselScope)

Retained for cost savings analysis:

### 17. LawFirm
### 18. BillingRate
### 19. ActivityTimeEstimate
### 20. CounselInvoice
### 21. InvoiceLineItem

*See CounselScope documentation for details on these models. They remain unchanged.*

---

## Database Indexes

### Performance Indexes

```sql
-- Questions
CREATE INDEX idx_questions_org_status ON questions(organization_id, status);
CREATE INDEX idx_questions_asked_by ON questions(asked_by_id, created_at DESC);
CREATE INDEX idx_questions_assigned_to ON questions(assigned_to_id, status);
CREATE INDEX idx_questions_created_at ON questions(created_at DESC);

-- Automation Rules (with vector similarity)
CREATE INDEX idx_automation_rules_org_enabled ON automation_rules(organization_id, is_enabled);
-- pgvector index for semantic search
CREATE INDEX idx_automation_embeddings_vector ON automation_rule_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Knowledge (with vector similarity)
CREATE INDEX idx_wisdom_facts_org_tier ON wisdom_facts(organization_id, tier);
CREATE INDEX idx_wisdom_embeddings_vector ON wisdom_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Notifications
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);

-- Analytics
CREATE INDEX idx_daily_metrics_org_date ON daily_metrics(organization_id, metric_date DESC);

-- Sessions
CREATE INDEX idx_user_sessions_user_active ON user_sessions(user_id, is_active);
```

---

## Migration Strategy

### Phase 1: Schema Additions

```sql
-- Add new tables
CREATE TABLE automation_rules (...);
CREATE TABLE automation_rule_embeddings (...);
CREATE TABLE automation_logs (...);
CREATE TABLE notifications (...);
CREATE TABLE question_messages (...);
CREATE TABLE question_knowledge (...);
CREATE TABLE daily_metrics (...);

-- Modify existing tables
ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'business_user';
ALTER TABLE users ADD COLUMN notification_preferences JSONB;

-- Rename/repurpose conversations → questions
-- (May need data migration script)
```

### Phase 2: Data Migration

```python
# Migrate existing conversation data to new question format
# Map conversation_messages to question_messages
# Extract any automated response patterns for automation_rules
```

### Phase 3: Index Creation

```sql
-- Create all performance indexes
-- Create vector indexes for pgvector
```

---

## Seeding Requirements

### Development Seed Data

| Entity | Count | Notes |
|--------|-------|-------|
| Organizations | 2 | "Demo Corp", "Test Inc" |
| Users | 10 | Mix of roles |
| Questions | 50 | Various statuses |
| Answers | 40 | |
| Automation Rules | 10 | Sample rules |
| WisdomFacts | 200 | From CounselScope |
| KnowledgeDocuments | 20 | From CounselScope |

### Production Initial Data

| Entity | Count | Notes |
|--------|-------|-------|
| Organizations | 1 | Customer org |
| Users | 1 | Admin user |
| System Settings | Default | |

---

*This data model will be refined during implementation.*
