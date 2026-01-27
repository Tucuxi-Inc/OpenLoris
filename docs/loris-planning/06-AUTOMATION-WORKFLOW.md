# Loris: Automation Workflow & Gap Analysis System

## Document Overview
**Version:** 0.1.0 (Draft)
**Last Updated:** January 2026

---

## The "Glean+" Philosophy

Loris differs from enterprise search tools like Glean in a fundamental way:

| Aspect | Traditional Search (Glean) | Loris (Glean+) |
|--------|---------------------------|----------------|
| **Output** | Links to documents | Curated answer |
| **User effort** | Sift through results | Read answer, done |
| **Quality control** | None | Human-validated |
| **Learning** | None | Compounding knowledge |
| **Freshness** | Index-based | GUD-managed |

**Key principle:** Users don't want search results - they want answers. Loris provides answers, validated by domain experts, that improve over time.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LORIS ANSWER DELIVERY SYSTEM                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USER ASKS QUESTION                                                         │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AUTOMATION ENGINE                                 │   │
│  │                                                                       │   │
│  │   Question ──► Embedding ──► Match Automation Rules                  │   │
│  │                                    │                                 │   │
│  │                     ┌──────────────┼──────────────┐                  │   │
│  │                     │              │              │                  │   │
│  │                  MATCH          NO MATCH      LOW CONFIDENCE         │   │
│  │                (≥ 0.85)                        (0.70-0.85)           │   │
│  │                     │              │              │                  │   │
│  │                     ▼              │              │                  │   │
│  │              ┌────────────┐        │        ┌─────────────┐          │   │
│  │              │ TransWarp  │        │        │ Suggest to  │          │   │
│  │              │   Answer   │        │        │   Expert    │          │   │
│  │              └─────┬──────┘        │        └──────┬──────┘          │   │
│  │                    │               │               │                  │   │
│  └────────────────────│───────────────│───────────────│──────────────────┘   │
│                       │               │               │                      │
│         ┌─────────────┘               │               │                      │
│         │                             │               │                      │
│         ▼                             ▼               ▼                      │
│  ┌─────────────┐              ┌─────────────────────────────┐               │
│  │   USER      │              │      EXPERT QUEUE           │               │
│  │   ACCEPTS   │              │                             │               │
│  │   OR        │              │  ┌───────────────────────┐  │               │
│  │   REJECTS   │              │  │   GAP ANALYSIS        │  │               │
│  └──────┬──────┘              │  │                       │  │               │
│         │                     │  │ • Relevant knowledge  │  │               │
│    ┌────┴────┐                │  │ • Coverage %          │  │               │
│    │         │                │  │ • Identified gaps     │  │               │
│    ▼         ▼                │  │ • Proposed answer     │  │               │
│ RESOLVED  ESCALATE            │  │ • Clarifications      │  │               │
│            TO EXPERT          │  └───────────────────────┘  │               │
│               │               │                             │               │
│               └───────────────┤  Expert reviews & answers   │               │
│                               │                             │               │
│                               └──────────────┬──────────────┘               │
│                                              │                              │
│                                              ▼                              │
│                               ┌──────────────────────────────┐              │
│                               │  ANSWER + KNOWLEDGE UPDATE   │              │
│                               │                              │              │
│                               │  • Send answer to user       │              │
│                               │  • Create automation rule?   │              │
│                               │  • Add to knowledge base?    │              │
│                               └──────────────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Automation Engine

### 1.1 When a Question Arrives

```python
# Pseudocode for question processing

async def process_question(question: Question) -> QuestionResult:
    """
    Main entry point when a question is submitted.
    Determines if we can auto-answer or need expert review.
    """

    # Step 1: Generate embedding for the question
    question_embedding = await embedding_service.generate(question.text)

    # Step 2: Search for matching automation rules
    matches = await automation_service.find_matching_rules(
        embedding=question_embedding,
        organization_id=question.organization_id,
        category=question.category  # Optional filter
    )

    # Step 3: Evaluate matches
    if matches and matches[0].similarity >= 0.85:
        # High confidence match - auto-answer
        return await deliver_auto_answer(question, matches[0])

    elif matches and matches[0].similarity >= 0.70:
        # Medium confidence - suggest to expert but queue anyway
        return await queue_with_suggestion(question, matches[0])

    else:
        # No match - full expert review needed
        return await queue_for_expert(question)
```

### 1.2 Automation Rule Matching

```python
async def find_matching_rules(
    embedding: List[float],
    organization_id: UUID,
    category: str | None = None
) -> List[RuleMatch]:
    """
    Find automation rules that match the question semantically.
    Uses pgvector for efficient similarity search.
    """

    # Build query with filters
    query = """
        SELECT
            ar.id,
            ar.name,
            ar.canonical_question,
            ar.canonical_answer,
            ar.similarity_threshold,
            ar.exclude_keywords,
            ar.good_until_date,
            1 - (are.embedding <=> $1) as similarity
        FROM automation_rules ar
        JOIN automation_rule_embeddings are ON ar.id = are.rule_id
        WHERE ar.organization_id = $2
          AND ar.is_enabled = true
          AND (ar.good_until_date IS NULL OR ar.good_until_date > CURRENT_DATE)
          AND ($3 IS NULL OR ar.category_filter IS NULL OR ar.category_filter = $3)
        ORDER BY similarity DESC
        LIMIT 5
    """

    results = await db.fetch(query, embedding, organization_id, category)

    # Filter by exclude keywords and threshold
    matches = []
    for row in results:
        # Check exclude keywords
        if row.exclude_keywords:
            if any(kw.lower() in question.text.lower() for kw in row.exclude_keywords):
                continue

        # Check meets threshold
        if row.similarity >= row.similarity_threshold:
            matches.append(RuleMatch(
                rule_id=row.id,
                similarity=row.similarity,
                canonical_answer=row.canonical_answer,
                # ...
            ))

    return matches
```

### 1.3 Delivering Auto-Answers

```python
async def deliver_auto_answer(question: Question, match: RuleMatch) -> QuestionResult:
    """
    Deliver an automated answer using TransWarp Loris.
    """

    # Create answer record
    answer = await Answer.create(
        question_id=question.id,
        content=match.canonical_answer,
        source=AnswerSource.AUTOMATION,
        automation_rule_id=match.rule_id
    )

    # Update question status
    question.status = QuestionStatus.AUTO_ANSWERED
    question.automation_rule_id = match.rule_id
    await question.save()

    # Log automation event
    await AutomationLog.create(
        rule_id=match.rule_id,
        question_id=question.id,
        action=AutomationLogAction.DELIVERED,
        similarity_score=match.similarity
    )

    # Update rule metrics
    await automation_service.increment_trigger_count(match.rule_id)

    return QuestionResult(
        status="auto_answered",
        answer=answer,
        loris_type="transwarp",  # For UI to show TransWarp Loris image
        message="Here's what I found in our knowledge base!"
    )
```

### 1.4 Handling User Feedback on Auto-Answers

```python
async def handle_auto_answer_feedback(
    question_id: UUID,
    accepted: bool,
    rejection_reason: str | None = None
) -> None:
    """
    Process user's response to an automated answer.
    """

    question = await Question.get(question_id)

    if accepted:
        # User accepted the auto-answer
        question.status = QuestionStatus.RESOLVED
        question.auto_answer_accepted = True
        question.resolved_at = datetime.utcnow()
        await question.save()

        # Update automation metrics
        await AutomationLog.create(
            rule_id=question.automation_rule_id,
            question_id=question.id,
            action=AutomationLogAction.ACCEPTED
        )
        await automation_service.increment_accept_count(question.automation_rule_id)

    else:
        # User rejected - escalate to expert
        question.status = QuestionStatus.HUMAN_REQUESTED
        question.auto_answer_accepted = False
        question.rejection_reason = rejection_reason
        await question.save()

        # Log rejection
        await AutomationLog.create(
            rule_id=question.automation_rule_id,
            question_id=question.id,
            action=AutomationLogAction.REJECTED,
            user_feedback=rejection_reason
        )
        await automation_service.increment_reject_count(question.automation_rule_id)

        # Run gap analysis for expert
        await run_gap_analysis(question)

        # Notify experts
        await notification_service.notify_expert_queue(
            question=question,
            note="User requested human review of automated answer"
        )
```

---

## Part 2: Gap Analysis Engine

### 2.1 What Gap Analysis Does

When a question can't be auto-answered (or the auto-answer was rejected), the Gap Analysis Engine:

1. **Searches the knowledge base** for relevant information
2. **Calculates coverage** - what percentage of the question can be answered
3. **Identifies gaps** - what information is missing
4. **Proposes an answer** - best attempt based on available knowledge
5. **Suggests clarifications** - questions that would help fill gaps

### 2.2 Gap Analysis Workflow

```python
async def run_gap_analysis(question: Question) -> GapAnalysisResult:
    """
    Analyze a question against the knowledge base to support expert review.
    """

    # Step 1: Generate question embedding
    question_embedding = await embedding_service.generate(question.text)

    # Step 2: Search knowledge base
    relevant_facts = await knowledge_service.semantic_search(
        embedding=question_embedding,
        organization_id=question.organization_id,
        limit=10,
        include_expired=False  # Only fresh knowledge
    )

    # Step 3: Use AI to analyze gaps
    analysis = await ai_provider.analyze_gaps(
        question=question.text,
        context=question.rejection_reason,  # If user provided context
        relevant_knowledge=relevant_facts,
        organization_context=question.organization.settings
    )

    # Step 4: Store analysis with question
    question.gap_analysis = {
        "relevant_knowledge": [
            {
                "id": str(fact.id),
                "content": fact.content,
                "relevance_score": fact.relevance_score,
                "source": fact.source_info
            }
            for fact in relevant_facts
        ],
        "coverage_percentage": analysis.coverage_percentage,
        "identified_gaps": analysis.gaps,
        "proposed_answer": analysis.proposed_answer,
        "confidence_score": analysis.confidence,
        "suggested_clarifications": analysis.clarifications
    }
    await question.save()

    return analysis
```

### 2.3 AI Analysis Prompt

```python
GAP_ANALYSIS_PROMPT = """
You are analyzing a question against a knowledge base to help a domain expert
formulate an answer.

QUESTION:
{question}

{context_section}

RELEVANT KNOWLEDGE FROM OUR DATABASE:
{knowledge_items}

Please analyze and provide:

1. COVERAGE ASSESSMENT
   - What percentage of this question can be answered with the provided knowledge?
   - Score from 0-100%

2. IDENTIFIED GAPS
   - What specific information is missing that would be needed for a complete answer?
   - List each gap with severity (high/medium/low)

3. PROPOSED ANSWER
   - Based on available knowledge, draft the best possible answer
   - Note any caveats or areas where you're less confident
   - Include citations to the knowledge items used

4. SUGGESTED CLARIFICATIONS
   - What additional questions would help provide a better answer?
   - These would be asked of the person who submitted the question

Respond in JSON format:
{{
  "coverage_percentage": <0-100>,
  "gaps": [
    {{"description": "...", "severity": "high|medium|low"}}
  ],
  "proposed_answer": {{
    "content": "...",
    "confidence": <0-1>,
    "citations": [<fact_ids>]
  }},
  "clarifications": ["question 1", "question 2"]
}}
"""
```

### 2.4 What Experts See

When an expert opens a question from the queue, they see:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ QUESTION FROM: Alex Martinez (Marketing)                                    │
│ Submitted: 2 hours ago | Status: In Expert Queue                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ORIGINAL QUESTION:                                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ "Can we add a non-compete clause to the vendor contract with            │ │
│ │ Acme Corp?"                                                             │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ USER CONTEXT (why they requested human review):                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ "This vendor is a direct competitor to our main product line. I'm       │ │
│ │ worried they'll gain insights into our pricing and strategy."           │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ KNOWLEDGE BASE ANALYSIS                                    Coverage: 65%   │
│                                                                             │
│ ✅ RELEVANT KNOWLEDGE FOUND:                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 1. Vendor Contract Guidelines (2024)              Relevance: 92%        │ │
│ │    "Non-compete clauses in vendor agreements are generally not          │ │
│ │    recommended as they reduce business flexibility..."                  │ │
│ │    [View Full Document]                                                 │ │
│ │                                                                         │ │
│ │ 2. Competitive Vendor Policy                      Relevance: 88%        │ │
│ │    "When engaging vendors who are competitors, additional protections   │ │
│ │    including enhanced confidentiality provisions..."                    │ │
│ │    [View Full Document]                                                 │ │
│ │                                                                         │ │
│ │ 3. Previous Q&A (Oct 15, 2025)                   Relevance: 75%        │ │
│ │    Non-solicitation vs. Non-compete guidance                           │ │
│ │    [View Previous Answer]                                              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ⚠️ IDENTIFIED GAPS:                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ • No specific guidance for direct competitor vendors       [MEDIUM]     │ │
│ │ • No precedent for protecting competitive intelligence     [HIGH]       │ │
│ │ • Unknown: type of engagement (software, services, etc.)   [LOW]        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ 🤖 AI-PROPOSED ANSWER (Confidence: 72%):                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Based on our vendor contract guidelines, non-compete clauses are        │ │
│ │ generally not recommended. However, given that Acme Corp is a direct   │ │
│ │ competitor, I recommend:                                                │ │
│ │                                                                         │ │
│ │ 1. Enhanced confidentiality provisions specifically covering...         │ │
│ │ 2. Information barrier requirements...                                  │ │
│ │ 3. Right to audit compliance...                                         │ │
│ │                                                                         │ │
│ │ [Edit This] [Use As-Is]                                                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ EXPERT ACTIONS:                                                            │
│                                                                             │
│ [👍 Approve & Send]  [✏️ Edit & Send]  [❓ Ask Clarification]  [🔗 Assign]  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Knowledge Compounding

Every validated answer can become knowledge. This is how Loris "learns" and improves.

### 3.1 The Compounding Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KNOWLEDGE COMPOUNDING LOOP                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Question ──► Expert Answer ──► Add to Knowledge? ──► YES ──┐              │
│                                        │                     │              │
│                                        NO                    ▼              │
│                                        │         ┌───────────────────┐      │
│                                        │         │  New WisdomFact   │      │
│                                        │         │  with GUD date    │      │
│                                        │         └─────────┬─────────┘      │
│                                        │                   │                │
│                                        │                   ▼                │
│                                        │         ┌───────────────────┐      │
│                                        │         │  Generate         │      │
│                                        │         │  Embedding        │      │
│                                        │         └─────────┬─────────┘      │
│                                        │                   │                │
│                                        │                   ▼                │
│                                        │         ┌───────────────────┐      │
│                                        │         │  Available for    │      │
│                                        │         │  Future Searches  │      │
│                                        │         └─────────┬─────────┘      │
│                                        │                   │                │
│                                        ▼                   │                │
│                                ┌───────────────┐           │                │
│                                │   Done        │           │                │
│                                └───────────────┘           │                │
│                                        ▲                   │                │
│                                        │                   │                │
│  Create Automation Rule? ──► YES ──────│───────────────────┤                │
│           │                            │                   │                │
│           NO                           │                   │                │
│           │                            │                   ▼                │
│           └────────────────────────────┤      ┌───────────────────┐        │
│                                        │      │ New Automation    │        │
│                                        │      │ Rule with GUD     │        │
│                                        │      └─────────┬─────────┘        │
│                                        │                │                  │
│                                        │                ▼                  │
│                                        │      ┌───────────────────┐        │
│                                        │      │ Similar Future    │        │
│                                        │      │ Questions Auto-   │        │
│                                        │      │ Answered          │        │
│                                        │      └───────────────────┘        │
│                                        │                                    │
│                                        └────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Creating Knowledge from Answers

```python
async def create_knowledge_from_answer(
    answer: Answer,
    config: KnowledgeCreationConfig
) -> WisdomFact:
    """
    Convert an expert's answer into a reusable knowledge fact.
    """

    fact = await WisdomFact.create(
        organization_id=answer.question.organization_id,

        # Content
        content=config.content or answer.content,
        domain=config.domain or "Legal",  # Default for Legal Loris
        category=config.category,

        # Source tracking
        source_answer_id=answer.id,

        # Quality settings
        tier=WisdomTier.TIER_0B,  # Expert-validated
        confidence_score=0.90,
        importance=config.importance or 5,

        # Freshness management (GUD)
        good_until_date=config.good_until_date,
        is_perpetual=config.is_perpetual,
        contact_person_id=answer.created_by_id,

        # Validation
        validated_at=datetime.utcnow(),
        validated_by_id=answer.created_by_id
    )

    # Generate embedding for semantic search
    embedding = await embedding_service.generate(fact.content)
    await WisdomEmbedding.create(
        wisdom_fact_id=fact.id,
        embedding=embedding,
        model_name=embedding_service.model_name
    )

    return fact
```

### 3.3 Creating Automation Rules from Answers

```python
async def create_automation_from_answer(
    answer: Answer,
    config: AutomationCreationConfig
) -> AutomationRule:
    """
    Create an automation rule so similar future questions get auto-answered.
    """

    question = answer.question

    rule = await AutomationRule.create(
        organization_id=question.organization_id,
        created_by_id=answer.created_by_id,

        # Rule definition
        name=config.name,
        description=config.description,
        source_question_id=question.id,

        # The template Q&A
        canonical_question=question.original_text,
        canonical_answer=answer.content,

        # Matching configuration
        similarity_threshold=config.similarity_threshold or 0.85,
        category_filter=config.category_filter,
        exclude_keywords=config.exclude_keywords or [],

        # Freshness management (GUD)
        good_until_date=config.good_until_date,

        # Enable immediately
        is_enabled=True
    )

    # Generate embedding for the canonical question
    embedding = await embedding_service.generate(rule.canonical_question)
    await AutomationRuleEmbedding.create(
        rule_id=rule.id,
        embedding=embedding,
        model_name=embedding_service.model_name
    )

    return rule
```

---

## Part 4: Good Until Date (GUD) Management

GUD dates are critical for maintaining knowledge freshness and ensuring automated answers don't go stale.

### 4.1 Where GUD Applies

| Entity | GUD Purpose | Default |
|--------|-------------|---------|
| **KnowledgeDocument** | When to re-review source document | 1 year |
| **WisdomFact** | When knowledge may be outdated | 1 year |
| **AutomationRule** | When to verify auto-answer is still correct | 6 months |

### 4.2 GUD Enforcement Logic

```python
# For knowledge search
async def semantic_search(
    embedding: List[float],
    organization_id: UUID,
    include_expired: bool = False  # Usually False!
) -> List[WisdomFact]:
    """
    Search knowledge base, optionally filtering out expired facts.
    """

    filters = [
        WisdomFact.organization_id == organization_id,
        WisdomFact.tier.in_([WisdomTier.TIER_0A, WisdomTier.TIER_0B])
    ]

    if not include_expired:
        filters.append(
            or_(
                WisdomFact.is_perpetual == True,
                WisdomFact.good_until_date == None,
                WisdomFact.good_until_date > date.today()
            )
        )

    # ... execute search with filters


# For automation matching
async def find_matching_rules(
    embedding: List[float],
    organization_id: UUID,
) -> List[RuleMatch]:
    """
    Only match rules that haven't expired.
    """

    query = """
        SELECT ...
        FROM automation_rules ar
        WHERE ar.is_enabled = true
          AND (ar.good_until_date IS NULL OR ar.good_until_date > CURRENT_DATE)
        ...
    """
```

### 4.3 GUD Expiration Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GUD EXPIRATION HANDLING                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DAILY JOB: Check for expiring items                                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ SELECT * FROM automation_rules                                       │   │
│  │ WHERE good_until_date BETWEEN today AND today + 30 days              │   │
│  │ AND is_enabled = true                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│                          │                                                  │
│                          ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  30 days before expiry:                                              │   │
│  │  • Send reminder to rule creator                                     │   │
│  │  • Add to "Expiring Soon" dashboard                                  │   │
│  │                                                                       │   │
│  │  7 days before expiry:                                               │   │
│  │  • Send urgent reminder                                              │   │
│  │  • Highlight in expert dashboard                                     │   │
│  │                                                                       │   │
│  │  On expiry:                                                          │   │
│  │  • Rule stops matching new questions                                 │   │
│  │  • Still visible in dashboard as "Expired"                           │   │
│  │  • Expert can: Renew (extend GUD), Archive, or Edit & Renew          │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.4 GUD Renewal Interface

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXPIRING SOON                                                    [View All] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ⚠️ AUTOMATION RULES                                                         │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Vendor Non-Compete Guidance                           Expires in 15 days │ │
│ │ Created by: Sarah Chen on Jan 26, 2025                                  │ │
│ │ Triggered: 45 times | Acceptance: 84%                                   │ │
│ │                                                                         │ │
│ │ [Review & Renew]  [Edit & Renew]  [Archive]                             │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ NDA Confidentiality Duration                          Expires in 22 days │ │
│ │ Created by: Mike Johnson on Mar 10, 2025                                │ │
│ │ Triggered: 28 times | Acceptance: 92%                                   │ │
│ │                                                                         │ │
│ │ [Review & Renew]  [Edit & Renew]  [Archive]                             │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ⚠️ KNOWLEDGE FACTS                                                          │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ "Standard confidentiality periods are 2-3 years..."   Expires in 8 days │ │
│ │ Category: Contracts | Cited: 12 times                                   │ │
│ │ Source: Previous Q&A                                                    │ │
│ │                                                                         │ │
│ │ [Verify & Renew]  [Edit & Renew]  [Archive]                             │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Loris Visual States

Different Loris images communicate the system state to users:

### 5.1 User-Facing Loris States

| State | Loris Type | When Shown |
|-------|------------|------------|
| Question received | Standard Loris | After submission, before processing |
| Processing | Thinking Loris | While checking automation |
| Auto-answered | **TransWarp Loris** | Instant answer from automation |
| In queue | Research Loris | Waiting for expert |
| Expert reviewing | Expert Loris | Expert has claimed question |
| Need more info | Confused Loris | Clarification requested |
| Answered | Happy Loris | Human answer delivered |
| Resolved | Celebration Loris | User confirmed satisfaction |

### 5.2 Implementation

```typescript
// Frontend component
function LorisIndicator({ status }: { status: QuestionStatus }) {
  const lorisConfig = {
    submitted: { image: '/loris/standard.png', label: 'Question received!' },
    processing: { image: '/loris/thinking.gif', label: 'Checking our knowledge...' },
    auto_answered: { image: '/loris/transwarp.png', label: 'Found it!' },
    expert_queue: { image: '/loris/research.png', label: 'Researching...' },
    in_progress: { image: '/loris/expert.png', label: 'Expert reviewing...' },
    needs_clarification: { image: '/loris/confused.png', label: 'Need more info' },
    answered: { image: '/loris/happy.png', label: 'Here\'s your answer!' },
    resolved: { image: '/loris/celebration.png', label: 'Glad I could help!' },
  };

  const config = lorisConfig[status] || lorisConfig.submitted;

  return (
    <div className="loris-indicator">
      <img src={config.image} alt={config.label} />
      <span>{config.label}</span>
    </div>
  );
}
```

---

## Part 6: Metrics & Analytics

### 6.1 Key Automation Metrics

```python
class AutomationMetrics(BaseModel):
    """Metrics tracked for automation performance."""

    # Volume
    total_questions: int
    auto_answered: int
    expert_answered: int
    automation_rate: float  # auto_answered / total_questions

    # Quality
    auto_acceptance_rate: float  # accepted / (accepted + rejected)
    human_escalation_rate: float  # rejected / auto_answered

    # Per-rule performance
    rules_performance: List[RuleMetrics]

    # Time savings
    estimated_time_saved_minutes: int  # auto_answered * avg_expert_time
    estimated_cost_saved: float  # time_saved * hourly_rate


class RuleMetrics(BaseModel):
    """Per-rule performance metrics."""

    rule_id: UUID
    rule_name: str
    times_triggered: int
    times_accepted: int
    times_rejected: int
    acceptance_rate: float
    last_triggered_at: datetime | None
    days_until_expiry: int | None
```

### 6.2 Gap Analysis Quality Metrics

```python
class GapAnalysisMetrics(BaseModel):
    """Track how well gap analysis serves experts."""

    # Proposal quality
    proposals_used_as_is: int  # Expert approved without edit
    proposals_edited: int  # Expert modified
    proposals_discarded: int  # Expert wrote from scratch

    proposal_acceptance_rate: float  # used_as_is / total

    # Coverage accuracy
    avg_predicted_coverage: float  # What we said we'd cover
    avg_actual_relevance: float  # Expert rating of knowledge relevance

    # Gap identification
    gaps_addressed_in_answer: float  # % of identified gaps expert addressed
```

---

## Part 7: Configuration Options

### 7.1 Organization-Level Settings

```python
class AutomationSettings(BaseModel):
    """Organization settings for automation behavior."""

    # Matching thresholds
    auto_answer_threshold: float = 0.85  # Above this, auto-answer
    suggest_threshold: float = 0.70  # Above this, suggest to expert

    # GUD defaults
    default_rule_gud_days: int = 180  # 6 months
    default_knowledge_gud_days: int = 365  # 1 year
    gud_warning_days: int = 30  # Warn this many days before expiry

    # Behavior
    require_expert_approval_for_rules: bool = False
    auto_create_knowledge_from_answers: bool = True
    allow_users_to_escalate: bool = True

    # Quality controls
    min_acceptance_rate_to_keep_enabled: float = 0.60  # Disable rule below this
    max_rejections_before_review: int = 5  # Flag rule after this many rejections
```

### 7.2 Per-Rule Configuration

```python
class AutomationRuleConfig(BaseModel):
    """Per-rule configuration options."""

    similarity_threshold: float = 0.85
    category_filter: str | None = None
    exclude_keywords: List[str] = []

    # GUD
    good_until_date: date | None = None

    # Behavior
    requires_approval: bool = False  # If true, suggest but don't auto-send
    max_daily_triggers: int | None = None  # Rate limit

    # Notifications
    notify_on_rejection: bool = True
    notify_on_threshold_breach: bool = True
```

---

## Summary

The Loris automation and gap analysis system provides:

1. **Intelligent automation** - Semantic matching delivers instant answers when confident
2. **Expert empowerment** - Gap analysis helps experts answer faster with relevant context
3. **Knowledge compounding** - Every answer can become reusable knowledge
4. **Freshness management** - GUD dates ensure nothing goes stale
5. **Quality feedback loop** - Metrics drive continuous improvement
6. **User trust** - Always an option to escalate to a human

This is what makes Loris "Glean+" - not just search, but curated, validated, improving answers.

---

*This document will be refined during implementation.*
