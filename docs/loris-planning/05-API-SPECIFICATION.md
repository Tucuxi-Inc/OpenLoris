# Loris: API Specification

## Document Overview
**Version:** 0.1.0 (Draft)
**Last Updated:** January 2026
**Base URL:** `/api/v1`

---

## API Design Principles

1. **RESTful conventions** - Standard HTTP methods, resource-based URLs
2. **JSON request/response** - All payloads are JSON
3. **JWT authentication** - Bearer token in Authorization header
4. **Consistent error format** - Standard error response structure
5. **Pagination** - Offset/limit for list endpoints
6. **Filtering** - Query parameters for filtering

---

## Authentication

### Standard Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Error Responses

```json
// 401 Unauthorized
{
  "error": "unauthorized",
  "message": "Invalid or expired token"
}

// 403 Forbidden
{
  "error": "forbidden",
  "message": "Insufficient permissions for this action"
}
```

---

## Endpoints Overview

| Category | Endpoints |
|----------|-----------|
| Authentication | `/auth/*` |
| Users | `/users/*` |
| Questions | `/questions/*` |
| Answers | `/answers/*` |
| Automation | `/automation/*` |
| Knowledge | `/knowledge/*` |
| Documents | `/documents/*` |
| Notifications | `/notifications/*` |
| Analytics | `/analytics/*` |
| Billing | `/billing/*` (from CounselScope) |

---

## 1. Authentication Endpoints

### POST /auth/register

Create a new user account (admin only or self-registration if enabled).

**Request:**
```json
{
  "email": "alex@example.com",
  "password": "SecurePass123!",
  "name": "Alex Martinez",
  "department": "Marketing"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "email": "alex@example.com",
  "name": "Alex Martinez",
  "role": "business_user",
  "is_verified": false,
  "created_at": "2026-01-26T10:00:00Z"
}
```

---

### POST /auth/login

Authenticate and receive tokens.

**Request:**
```json
{
  "email": "alex@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "email": "alex@example.com",
    "name": "Alex Martinez",
    "role": "business_user",
    "organization": {
      "id": "uuid",
      "name": "Demo Corp"
    }
  }
}
```

---

### POST /auth/refresh

Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbG..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### POST /auth/logout

Invalidate current session.

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

### GET /auth/me

Get current user profile.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "alex@example.com",
  "name": "Alex Martinez",
  "role": "business_user",
  "department": "Marketing",
  "organization": {
    "id": "uuid",
    "name": "Demo Corp"
  },
  "notification_preferences": {
    "email_on_answer": true,
    "email_on_clarification": true
  },
  "created_at": "2026-01-26T10:00:00Z"
}
```

---

## 2. Questions Endpoints

### POST /questions

Submit a new question (any authenticated user).

**Request:**
```json
{
  "text": "Can we add a non-compete clause to the vendor contract with Acme Corp?",
  "category": "contracts",
  "tags": ["vendor", "non-compete"],
  "priority": "normal",
  "attachments": [
    {
      "filename": "draft_contract.pdf",
      "url": "https://storage.example.com/uploads/abc123.pdf"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "id": "question-uuid",
  "text": "Can we add a non-compete clause...",
  "status": "processing",
  "asked_by": {
    "id": "user-uuid",
    "name": "Alex Martinez"
  },
  "created_at": "2026-01-26T10:15:00Z",

  // If automation matched:
  "auto_answer": {
    "content": "Non-compete clauses in vendor contracts are generally...",
    "source_rule_id": "rule-uuid",
    "confidence": 0.92,
    "sources": [
      {
        "id": "fact-uuid",
        "title": "Vendor Contract Guidelines",
        "excerpt": "..."
      }
    ]
  },

  // OR if no match:
  "auto_answer": null,
  "message": "Your question has been submitted. An expert will respond shortly."
}
```

---

### GET /questions

List user's questions (business user sees own, expert sees queue).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status |
| category | string | Filter by category |
| from_date | date | Filter created after |
| to_date | date | Filter created before |
| search | string | Full-text search |
| page | int | Page number (default 1) |
| per_page | int | Items per page (default 20, max 100) |

**Response (200 OK):**
```json
{
  "questions": [
    {
      "id": "uuid",
      "text": "Can we add a non-compete clause...",
      "status": "auto_answered",
      "category": "contracts",
      "priority": "normal",
      "asked_by": {
        "id": "uuid",
        "name": "Alex Martinez"
      },
      "assigned_to": null,
      "has_unread_answer": true,
      "created_at": "2026-01-26T10:15:00Z",
      "updated_at": "2026-01-26T10:15:05Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 47,
    "total_pages": 3
  }
}
```

---

### GET /questions/{id}

Get question details.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "text": "Can we add a non-compete clause to the vendor contract with Acme Corp?",
  "status": "auto_answered",
  "category": "contracts",
  "tags": ["vendor", "non-compete"],
  "priority": "normal",

  "asked_by": {
    "id": "uuid",
    "name": "Alex Martinez",
    "department": "Marketing"
  },

  "assigned_to": null,

  "attachments": [...],

  "messages": [
    {
      "id": "msg-uuid",
      "type": "question",
      "content": "Can we add a non-compete...",
      "user": { "name": "Alex Martinez" },
      "created_at": "2026-01-26T10:15:00Z"
    }
  ],

  "answer": {
    "id": "answer-uuid",
    "content": "Based on our vendor contract guidelines...",
    "source": "automation",
    "sources": [...],
    "created_at": "2026-01-26T10:15:05Z"
  },

  "auto_answer_accepted": null,  // pending user feedback

  // For experts: gap analysis
  "gap_analysis": {
    "relevant_knowledge": [...],
    "coverage_percentage": 85,
    "identified_gaps": [...],
    "proposed_answer": "...",
    "confidence": 0.78
  },

  "metrics": {
    "response_time_seconds": 5,
    "resolution_time_seconds": null
  },

  "created_at": "2026-01-26T10:15:00Z",
  "updated_at": "2026-01-26T10:15:05Z"
}
```

---

### POST /questions/{id}/feedback

User provides feedback on automated answer.

**Request (Accept):**
```json
{
  "accepted": true,
  "rating": 5,
  "comment": "Perfect, exactly what I needed!"
}
```

**Request (Reject - request human review):**
```json
{
  "accepted": false,
  "reason": "My situation is different - this vendor is a direct competitor and I'm concerned about competitive intelligence sharing.",
  "rating": null
}
```

**Response (200 OK):**
```json
{
  "id": "question-uuid",
  "status": "resolved",  // or "human_requested"
  "message": "Thank you for your feedback!"

  // If rejected:
  // "status": "human_requested",
  // "message": "Your question has been escalated to an expert."
}
```

---

### POST /questions/{id}/clarify

User provides clarification when requested.

**Request:**
```json
{
  "clarification": "The vendor is Acme Corp, they make competing widgets. We're worried they'll gain insights into our pricing and strategy from the engagement."
}
```

**Response (200 OK):**
```json
{
  "id": "question-uuid",
  "status": "expert_queue",
  "message": "Thank you for the additional context. An expert will review shortly."
}
```

---

## 3. Expert Queue Endpoints

### GET /questions/queue

Get questions awaiting expert attention (experts only).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter: expert_queue, in_progress, needs_clarification |
| assigned_to | uuid | Filter by assigned expert |
| unassigned | bool | Only show unassigned |
| category | string | Filter by category |
| priority | string | Filter by priority |
| sort | string | created_at, priority, response_time |
| order | string | asc, desc |

**Response (200 OK):**
```json
{
  "questions": [
    {
      "id": "uuid",
      "text": "Can we add a non-compete clause...",
      "status": "human_requested",
      "category": "contracts",
      "priority": "normal",
      "asked_by": {
        "id": "uuid",
        "name": "Alex Martinez",
        "department": "Marketing"
      },
      "assigned_to": null,
      "rejection_context": "This vendor is a direct competitor...",
      "waiting_time_seconds": 7200,
      "sla_status": "within_sla",  // within_sla, warning, breached
      "created_at": "2026-01-26T10:15:00Z"
    }
  ],
  "summary": {
    "total_in_queue": 5,
    "unassigned": 3,
    "avg_wait_time_seconds": 3600,
    "sla_at_risk": 1
  }
}
```

---

### PUT /questions/{id}/assign

Assign question to an expert.

**Request:**
```json
{
  "assigned_to_id": "expert-uuid"
}
```

**Response (200 OK):**
```json
{
  "id": "question-uuid",
  "assigned_to": {
    "id": "expert-uuid",
    "name": "Sarah Chen"
  },
  "status": "in_progress"
}
```

---

### POST /questions/{id}/answer

Expert submits answer.

**Request:**
```json
{
  "content": "Given that Acme Corp is a direct competitor, I recommend enhanced confidentiality provisions rather than non-compete clauses. Here's why...\n\n[Detailed answer]",

  "used_ai_proposal": true,  // Did expert use AI-proposed answer as base?
  "original_ai_proposal": "...",  // For tracking edits

  "cited_knowledge": [
    {
      "fact_id": "fact-uuid",
      "excerpt": "Non-compete clauses in vendor agreements..."
    }
  ],

  // Create automation rule?
  "create_automation": {
    "enabled": true,
    "name": "Vendor Non-Compete General Guidance",
    "similarity_threshold": 0.85,
    "good_until_date": "2027-01-26",  // Review in 1 year
    "category_filter": "contracts"
  },

  // Add answer to knowledge base?
  "add_to_knowledge": {
    "enabled": true,
    "category": "Vendor Contracts",
    "good_until_date": "2027-01-26",  // Refresh in 1 year
    "importance": 7
  }
}
```

**Response (201 Created):**
```json
{
  "answer": {
    "id": "answer-uuid",
    "content": "Given that Acme Corp...",
    "source": "ai_edited",
    "created_at": "2026-01-26T12:30:00Z"
  },

  "question": {
    "id": "question-uuid",
    "status": "answered"
  },

  "automation_rule": {
    "id": "rule-uuid",
    "name": "Vendor Non-Compete General Guidance",
    "is_enabled": true,
    "good_until_date": "2027-01-26"
  },

  "knowledge_fact": {
    "id": "fact-uuid",
    "content": "Given that Acme Corp...",
    "category": "Vendor Contracts",
    "good_until_date": "2027-01-26"
  },

  "notification_sent": true
}
```

---

### POST /questions/{id}/request-clarification

Expert requests more information from user.

**Request:**
```json
{
  "questions": [
    "What specific insights are you concerned about sharing?",
    "What is the nature of the engagement with Acme - consulting, software, services?"
  ]
}
```

**Response (200 OK):**
```json
{
  "id": "question-uuid",
  "status": "needs_clarification",
  "message_sent": true
}
```

---

## 4. Automation Endpoints

### GET /automation/rules

List automation rules (experts/admin).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| is_enabled | bool | Filter active/inactive |
| category | string | Filter by category |
| expiring_within_days | int | Rules expiring soon |
| sort | string | created_at, times_triggered, acceptance_rate |

**Response (200 OK):**
```json
{
  "rules": [
    {
      "id": "uuid",
      "name": "Vendor Non-Compete General Guidance",
      "canonical_question": "Can we add a non-compete clause to vendor contracts?",
      "is_enabled": true,
      "similarity_threshold": 0.85,
      "category_filter": "contracts",

      "good_until_date": "2027-01-26",
      "days_until_expiry": 365,
      "needs_review": false,

      "metrics": {
        "times_triggered": 15,
        "times_accepted": 12,
        "times_rejected": 3,
        "acceptance_rate": 0.80
      },

      "created_by": {
        "id": "uuid",
        "name": "Sarah Chen"
      },
      "created_at": "2026-01-26T12:30:00Z",
      "last_triggered_at": "2026-01-25T14:20:00Z"
    }
  ],
  "summary": {
    "total_rules": 25,
    "active_rules": 22,
    "expiring_soon": 3,
    "avg_acceptance_rate": 0.85
  }
}
```

---

### POST /automation/rules

Create new automation rule.

**Request:**
```json
{
  "name": "NDA Confidentiality Duration",
  "description": "Standard guidance on NDA confidentiality periods",
  "canonical_question": "How long should confidentiality obligations last in an NDA?",
  "canonical_answer": "Standard confidentiality periods are 2-3 years from disclosure...",

  "similarity_threshold": 0.85,
  "category_filter": "contracts",
  "exclude_keywords": ["litigation", "lawsuit"],

  "good_until_date": "2027-01-26",
  "is_enabled": true,

  // Optional: link to source question
  "source_question_id": "question-uuid"
}
```

**Response (201 Created):**
```json
{
  "id": "rule-uuid",
  "name": "NDA Confidentiality Duration",
  "is_enabled": true,
  "embedding_generated": true,
  "created_at": "2026-01-26T12:30:00Z"
}
```

---

### PUT /automation/rules/{id}

Update automation rule.

**Request:**
```json
{
  "canonical_answer": "Updated guidance...",
  "good_until_date": "2028-01-26",
  "similarity_threshold": 0.90
}
```

**Response (200 OK):**
```json
{
  "id": "rule-uuid",
  "updated_at": "2026-01-26T12:30:00Z",
  "embedding_regenerated": true
}
```

---

### PUT /automation/rules/{id}/toggle

Enable or disable rule.

**Request:**
```json
{
  "is_enabled": false
}
```

**Response (200 OK):**
```json
{
  "id": "rule-uuid",
  "is_enabled": false,
  "message": "Rule disabled"
}
```

---

### GET /automation/rules/{id}/preview

Preview which existing questions this rule would have matched.

**Response (200 OK):**
```json
{
  "rule_id": "uuid",
  "potential_matches": [
    {
      "question_id": "uuid",
      "question_text": "What's a good non-compete duration for vendors?",
      "similarity_score": 0.91,
      "would_have_matched": true,
      "actual_outcome": "expert_answered",
      "asked_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total_potential_matches": 8
}
```

---

### GET /automation/expiring

Get rules and knowledge facts approaching their GUD date (experts/admin).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| within_days | int | Default 30 |
| type | string | rules, knowledge, all |

**Response (200 OK):**
```json
{
  "expiring_items": [
    {
      "type": "automation_rule",
      "id": "uuid",
      "name": "Vendor Non-Compete Guidance",
      "good_until_date": "2026-02-15",
      "days_until_expiry": 20,
      "created_by": { "name": "Sarah Chen" },
      "times_triggered": 15,
      "acceptance_rate": 0.80
    },
    {
      "type": "knowledge_fact",
      "id": "uuid",
      "content": "Standard confidentiality periods...",
      "category": "Contracts",
      "good_until_date": "2026-02-10",
      "days_until_expiry": 15,
      "times_cited": 8
    }
  ],
  "summary": {
    "rules_expiring": 3,
    "knowledge_expiring": 7,
    "total": 10
  }
}
```

---

## 5. Knowledge Endpoints

### GET /knowledge/search

Semantic search across knowledge base.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| q | string | Search query (required) |
| category | string | Filter by category |
| tier | string | Filter by tier (0A, 0B, 0C) |
| include_expired | bool | Include expired facts (default false) |
| limit | int | Max results (default 10) |

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "fact-uuid",
      "content": "Non-compete clauses in vendor agreements are generally not recommended...",
      "category": "Vendor Contracts",
      "tier": "0A",
      "relevance_score": 0.92,

      "source": {
        "type": "document",
        "id": "doc-uuid",
        "title": "Vendor Contract Guidelines 2024",
        "url": "/documents/doc-uuid"
      },

      "good_until_date": "2027-01-01",
      "is_expired": false,

      "validated_by": { "name": "Sarah Chen" },
      "validated_at": "2025-06-15T10:00:00Z"
    }
  ],
  "query": "non-compete vendor contracts",
  "total_results": 5
}
```

---

### POST /knowledge/analyze-gaps

Analyze question against knowledge base (for expert view).

**Request:**
```json
{
  "question": "Can we add a non-compete clause to the vendor contract with Acme Corp?",
  "context": "Acme is a direct competitor..."
}
```

**Response (200 OK):**
```json
{
  "relevant_knowledge": [
    {
      "id": "fact-uuid",
      "content": "Non-compete clauses in vendor agreements...",
      "relevance_score": 0.92,
      "source": {...}
    }
  ],

  "coverage_percentage": 65,

  "identified_gaps": [
    {
      "description": "No specific guidance for direct competitor vendors",
      "severity": "medium"
    },
    {
      "description": "No precedent for Acme Corp specifically",
      "severity": "low"
    }
  ],

  "proposed_answer": {
    "content": "Based on available knowledge, here's a proposed answer...",
    "confidence_score": 0.72,
    "needs_review": true,
    "reasoning": "Medium confidence due to lack of competitor-specific guidance"
  },

  "suggested_clarifications": [
    "What type of engagement is this (consulting, software, services)?",
    "What specific competitive insights are you concerned about?"
  ]
}
```

---

### POST /knowledge/from-answer

Create knowledge fact from a question answer.

**Request:**
```json
{
  "answer_id": "answer-uuid",

  "content": "When engaging with direct competitor vendors, enhanced confidentiality provisions should be used rather than non-compete clauses...",

  "category": "Vendor Contracts",
  "domain": "Legal",
  "tier": "0B",
  "importance": 7,

  "good_until_date": "2027-01-26",
  "is_perpetual": false
}
```

**Response (201 Created):**
```json
{
  "id": "fact-uuid",
  "content": "When engaging with direct competitor vendors...",
  "category": "Vendor Contracts",
  "tier": "0B",
  "embedding_generated": true,
  "created_at": "2026-01-26T12:30:00Z"
}
```

---

### GET /knowledge/facts

List knowledge facts (experts).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| category | string | Filter by category |
| tier | string | Filter by tier |
| source_type | string | document, answer, manual |
| expiring_within_days | int | Facts expiring soon |
| search | string | Text search |
| page | int | Page number |
| per_page | int | Items per page |

**Response (200 OK):**
```json
{
  "facts": [
    {
      "id": "uuid",
      "content": "Non-compete clauses in vendor agreements...",
      "category": "Vendor Contracts",
      "tier": "0A",
      "importance": 8,
      "confidence_score": 0.95,

      "source": {
        "type": "document",
        "id": "doc-uuid",
        "title": "Vendor Contract Guidelines"
      },

      "good_until_date": "2027-01-01",
      "days_until_expiry": 340,

      "usage_stats": {
        "times_cited": 12,
        "last_cited_at": "2026-01-25T10:00:00Z"
      },

      "created_at": "2025-06-15T10:00:00Z"
    }
  ],
  "pagination": {...}
}
```

---

## 6. Document Endpoints

(Largely from CounselScope, with minor enhancements)

### POST /documents/upload

Upload a knowledge document.

### GET /documents

List documents.

### GET /documents/{id}

Get document details.

### POST /documents/{id}/extract-facts

Trigger AI fact extraction.

### POST /documents/{id}/facts/{fact_id}/approve

Approve extracted fact.

### POST /documents/{id}/facts/{fact_id}/reject

Reject extracted fact.

---

## 7. Notification Endpoints

### GET /notifications

Get user's notifications.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| unread_only | bool | Only unread (default false) |
| type | string | Filter by notification type |
| page | int | Page number |
| per_page | int | Items per page |

**Response (200 OK):**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "question_answered",
      "title": "Your question has been answered",
      "message": "Sarah Chen answered your question about non-compete clauses.",

      "related": {
        "question_id": "uuid",
        "answer_id": "uuid"
      },

      "is_read": false,
      "created_at": "2026-01-26T12:30:00Z"
    }
  ],
  "unread_count": 3
}
```

---

### PUT /notifications/{id}/read

Mark notification as read.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "is_read": true,
  "read_at": "2026-01-26T12:35:00Z"
}
```

---

### PUT /notifications/read-all

Mark all notifications as read.

**Response (200 OK):**
```json
{
  "marked_read": 5
}
```

---

### WebSocket: /ws/notifications

Real-time notification stream.

**Connection:**
```
ws://api.example.com/api/v1/ws/notifications?token=<access_token>
```

**Server Messages:**
```json
{
  "type": "notification",
  "data": {
    "id": "uuid",
    "type": "question_answered",
    "title": "Your question has been answered",
    "message": "...",
    "created_at": "2026-01-26T12:30:00Z"
  }
}
```

---

## 8. Analytics Endpoints

### GET /analytics/overview

Dashboard overview (admin).

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| period | string | day, week, month, quarter, year |
| from_date | date | Start date |
| to_date | date | End date |

**Response (200 OK):**
```json
{
  "period": {
    "from": "2026-01-01",
    "to": "2026-01-26"
  },

  "questions": {
    "total_submitted": 150,
    "auto_answered": 63,
    "expert_answered": 72,
    "pending": 15,
    "automation_rate": 0.42
  },

  "response_time": {
    "avg_seconds": 14400,
    "median_seconds": 10800,
    "p95_seconds": 43200
  },

  "automation": {
    "total_triggers": 80,
    "acceptance_rate": 0.79,
    "human_escalations": 17
  },

  "satisfaction": {
    "avg_rating": 4.6,
    "total_ratings": 98,
    "distribution": {
      "5": 65,
      "4": 20,
      "3": 8,
      "2": 3,
      "1": 2
    }
  },

  "knowledge": {
    "total_facts": 245,
    "facts_added": 18,
    "facts_expiring_soon": 7
  },

  "experts": {
    "active_count": 5,
    "questions_per_expert": 14.4
  }
}
```

---

### GET /analytics/questions

Detailed question analytics.

**Response (200 OK):**
```json
{
  "volume_by_day": [
    { "date": "2026-01-25", "submitted": 12, "auto": 5, "expert": 6 },
    { "date": "2026-01-26", "submitted": 8, "auto": 3, "expert": 4 }
  ],

  "by_category": [
    { "category": "contracts", "count": 45, "percentage": 0.30 },
    { "category": "employment", "count": 30, "percentage": 0.20 }
  ],

  "by_department": [
    { "department": "Marketing", "count": 25 },
    { "department": "Engineering", "count": 20 }
  ],

  "status_distribution": {
    "resolved": 120,
    "pending": 15,
    "in_progress": 10,
    "needs_clarification": 5
  }
}
```

---

### GET /analytics/automation

Automation performance metrics.

**Response (200 OK):**
```json
{
  "overall": {
    "total_rules": 25,
    "active_rules": 22,
    "total_triggers": 500,
    "overall_acceptance_rate": 0.82
  },

  "rules_performance": [
    {
      "id": "uuid",
      "name": "Vendor Non-Compete Guidance",
      "triggers": 45,
      "accepted": 38,
      "rejected": 7,
      "acceptance_rate": 0.84
    }
  ],

  "trends": {
    "acceptance_rate_trend": [
      { "week": "2026-W01", "rate": 0.80 },
      { "week": "2026-W02", "rate": 0.82 },
      { "week": "2026-W03", "rate": 0.85 }
    ]
  },

  "time_saved": {
    "total_auto_answered": 410,
    "estimated_minutes_saved": 8200,  // Assuming 20 min per question
    "estimated_cost_savings": 27333   // At $200/hr expert rate
  }
}
```

---

### GET /analytics/experts

Expert performance metrics (admin only).

**Response (200 OK):**
```json
{
  "experts": [
    {
      "id": "uuid",
      "name": "Sarah Chen",
      "questions_answered": 45,
      "avg_response_time_seconds": 10800,
      "avg_satisfaction_rating": 4.8,
      "automation_rules_created": 8,
      "knowledge_facts_added": 12
    }
  ],

  "workload_distribution": [
    { "expert": "Sarah Chen", "pending": 3, "in_progress": 2 },
    { "expert": "Mike Johnson", "pending": 5, "in_progress": 1 }
  ]
}
```

---

### GET /analytics/roi

Business value / ROI metrics.

**Response (200 OK):**
```json
{
  "period": {
    "from": "2026-01-01",
    "to": "2026-01-26"
  },

  "questions_handled": {
    "total": 150,
    "in_house": 150,
    "that_would_go_external": 25  // Estimated based on complexity
  },

  "time_savings": {
    "auto_answered_count": 63,
    "avg_minutes_per_question": 20,
    "total_minutes_saved": 1260,
    "total_hours_saved": 21
  },

  "cost_avoidance": {
    "external_hourly_rate": 500,
    "estimated_external_hours": 50,
    "estimated_savings": 25000
  },

  "efficiency_gain": {
    "questions_per_expert_day": 6.5,
    "baseline_questions_per_day": 4.0,
    "efficiency_increase_percentage": 62.5
  }
}
```

---

## 9. User Management Endpoints (Admin)

### GET /users

List users in organization.

### POST /users

Create new user.

### GET /users/{id}

Get user details.

### PUT /users/{id}

Update user.

### PUT /users/{id}/role

Change user role.

### DELETE /users/{id}

Deactivate user.

---

## 10. Settings Endpoints (Admin)

### GET /settings

Get organization settings.

**Response (200 OK):**
```json
{
  "organization": {
    "name": "Demo Corp",
    "default_sla_hours": 24,
    "automation_default_threshold": 0.85,
    "gud_warning_days": 30
  },

  "notifications": {
    "email_enabled": true,
    "slack_enabled": false
  },

  "ai_provider": {
    "current": "local_ollama",
    "available": ["local_ollama", "cloud_anthropic", "cloud_bedrock", "cloud_azure"]
  }
}
```

### PUT /settings

Update settings.

---

## Error Response Format

All errors follow consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "details": {
    // Additional context when helpful
  },
  "request_id": "uuid"  // For support/debugging
}
```

**Common Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| unauthorized | 401 | Invalid/missing token |
| forbidden | 403 | Insufficient permissions |
| not_found | 404 | Resource doesn't exist |
| validation_error | 422 | Invalid request data |
| rate_limited | 429 | Too many requests |
| internal_error | 500 | Server error |

---

## Rate Limiting

| Endpoint Type | Limit |
|--------------|-------|
| Auth endpoints | 10/minute per IP |
| Read endpoints | 100/minute per user |
| Write endpoints | 30/minute per user |
| Search endpoints | 30/minute per user |

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706270400
```

---

*This API specification will evolve during implementation.*
