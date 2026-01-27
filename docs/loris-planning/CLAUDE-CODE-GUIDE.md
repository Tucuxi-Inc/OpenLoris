# Loris: Claude Code Implementation Guide

## Purpose

This document provides detailed instructions for Claude Code (or any AI assistant) working on the Loris project. It covers project context, design aesthetics, implementation patterns, and guidance for making consistent decisions.

---

## Project Context

**Loris** transforms CounselScope into an intelligent Q&A platform. The core concept:

```
Traditional Search (Glean):     User asks → Gets links → Sifts through results
Loris ("Glean+"):               User asks → Gets answer → Done
```

### Key Files to Read First

Before making changes, read these in order:

1. `docs/loris-planning/README.md` - Project overview
2. `docs/loris-planning/01-PROJECT-VISION.md` - What we're building
3. `docs/loris-planning/03-SYSTEM-ARCHITECTURE.md` - Technical approach
4. `docs/loris-planning/08-MIGRATION-STRATEGY.md` - Implementation phases

### Existing Codebase to Understand

The project builds on CounselScope. Key areas to explore:

```
backend/
├── app/
│   ├── services/ai_provider_service.py    # Multi-provider AI (RETAIN)
│   ├── services/document_ingestion_service.py  # Doc processing (RETAIN)
│   ├── models/wisdom.py                   # Knowledge facts (RETAIN + extend)
│   ├── models/documents.py                # Document models (RETAIN)
│   └── models/billing.py                  # Billing intelligence (RETAIN)

frontend/
├── src/
│   ├── components/ui/                     # Base components (RETAIN + restyle)
│   └── components/KnowledgeManagement.tsx # Reference for patterns
```

---

## Design System: Tufte-Inspired Aesthetic

The visual design follows Edward Tufte's principles of information design, creating a scientific illustration aesthetic that complements the Loris imagery.

### Core Principles

1. **Maximize data-ink ratio** - Every visual element should convey information
2. **Minimize chartjunk** - No decorative elements that don't serve a purpose
3. **Use small multiples** - Repeat simple designs for comparison
4. **Typography carries the design** - Let beautiful type do the work

### Color Palette

```css
:root {
  /* Backgrounds */
  --bg-primary: #FFFEF8;        /* Cream/off-white - main background */
  --bg-secondary: #FAF9F6;      /* Slightly darker cream - cards */
  --bg-tertiary: #F5F4F0;       /* Warm gray - hover states */

  /* Text */
  --text-primary: #1A1A1A;      /* Near-black - body text */
  --text-secondary: #4A4A4A;    /* Dark gray - secondary text */
  --text-tertiary: #6B6B6B;     /* Medium gray - captions, hints */
  --text-muted: #8B8B8B;        /* Light gray - disabled, timestamps */

  /* Ink colors (for emphasis, sparingly) */
  --ink-accent: #8B5A2B;        /* Loris brown - links, primary actions */
  --ink-success: #2E5E4E;       /* Forest green - success states */
  --ink-warning: #8B6914;       /* Ochre - warnings */
  --ink-error: #8B2E2E;         /* Burgundy - errors */

  /* Rules and borders */
  --rule-light: #E5E4E0;        /* Light hairline rules */
  --rule-medium: #C5C4C0;       /* Medium rules */
  --rule-dark: #1A1A1A;         /* Dark rules for emphasis */
}
```

### What NOT to Use

```css
/* NEVER use these: */

/* No neon/bright colors */
--bad: #00D4FF;    /* No cyan */
--bad: #FF6B6B;    /* No bright red */
--bad: #00FF00;    /* No green glow */

/* No glowing effects */
box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);  /* NO */
text-shadow: 0 0 10px #fff;                     /* NO */

/* No gradients */
background: linear-gradient(...);               /* NO */

/* No rounded pill shapes */
border-radius: 100px;                           /* NO - use subtle rounding */
```

### Typography

```css
/* Primary typeface - Serif for body and headings */
--font-serif: 'Georgia', 'Times New Roman', Times, serif;

/* Secondary typeface - for code, data, labels */
--font-mono: 'IBM Plex Mono', 'Menlo', monospace;

/* Type scale */
--text-xs: 0.75rem;     /* 12px - captions */
--text-sm: 0.875rem;    /* 14px - small text */
--text-base: 1rem;      /* 16px - body */
--text-lg: 1.125rem;    /* 18px - lead text */
--text-xl: 1.25rem;     /* 20px - h4 */
--text-2xl: 1.5rem;     /* 24px - h3 */
--text-3xl: 1.875rem;   /* 30px - h2 */
--text-4xl: 2.25rem;    /* 36px - h1 */

/* Line heights */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;

/* Letter spacing */
--tracking-tight: -0.02em;  /* Headings */
--tracking-normal: 0;       /* Body */
--tracking-wide: 0.02em;    /* All caps labels */
```

### Component Patterns

#### Buttons

```css
/* Primary button - understated, not shouty */
.btn-primary {
  font-family: var(--font-serif);
  font-size: var(--text-sm);
  font-weight: 500;
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;

  color: var(--bg-primary);
  background: var(--text-primary);

  padding: 0.625rem 1.25rem;
  border: 1px solid var(--text-primary);
  border-radius: 2px;  /* Subtle, not pill-shaped */

  transition: background 0.15s ease;
}

.btn-primary:hover {
  background: var(--text-secondary);
}

/* Secondary button - outline style */
.btn-secondary {
  color: var(--text-primary);
  background: transparent;
  border: 1px solid var(--rule-medium);
}
```

#### Cards

```css
/* Card - subtle, paper-like */
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--rule-light);
  border-radius: 2px;
  padding: 1.5rem;

  /* No shadow - flat, printed appearance */
  box-shadow: none;
}

/* Card with emphasis */
.card-elevated {
  border-left: 3px solid var(--ink-accent);
}
```

#### Hairline Rules

```css
/* Horizontal rule - thin, understated */
hr, .rule {
  border: none;
  border-top: 1px solid var(--rule-light);
  margin: 1.5rem 0;
}

/* Section divider - slightly heavier */
.rule-section {
  border-top: 1px solid var(--rule-medium);
}

/* Strong divider */
.rule-strong {
  border-top: 2px solid var(--text-primary);
}
```

#### Status Indicators

```css
/* Status - small, typographic, not badges */
.status {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.status-pending {
  color: var(--ink-warning);
}

.status-complete {
  color: var(--ink-success);
}

.status-error {
  color: var(--ink-error);
}

/* If you must use a background, keep it subtle */
.status-badge {
  background: var(--bg-tertiary);
  padding: 0.25rem 0.5rem;
  border-radius: 2px;
}
```

#### Forms

```css
/* Input - clean, minimal */
.input {
  font-family: var(--font-serif);
  font-size: var(--text-base);

  background: var(--bg-primary);
  border: 1px solid var(--rule-medium);
  border-radius: 2px;
  padding: 0.75rem 1rem;

  transition: border-color 0.15s ease;
}

.input:focus {
  outline: none;
  border-color: var(--text-primary);
}

/* Label */
.label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}
```

### The Loris Images

The Loris illustrations should be displayed as **scientific illustrations** - think field guide or natural history book.

```css
/* Loris image container */
.loris-illustration {
  /* Let the illustration breathe */
  padding: 1rem;

  /* Optional: subtle caption styling */
  text-align: center;
}

.loris-illustration img {
  /* Clean presentation */
  max-width: 120px;
  height: auto;

  /* No effects */
  filter: none;
  box-shadow: none;
}

/* Caption below illustration */
.loris-caption {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: 0.5rem;
}
```

#### Loris Variants Usage

| Variant | When to Use | Caption Example |
|---------|-------------|-----------------|
| Standard Loris | Welcome, general UI | "Legal Loris" |
| TransWarp Loris | Automated instant answer | "Automated response" |
| Research Loris | Question in expert queue | "Being researched" |
| Thinking Loris | Processing state | "Consulting the archives..." |
| Expert Loris | Human is reviewing | "Expert review" |
| Celebration Loris | Successfully resolved | "Resolved" |

### Layout Principles

```css
/* Maximum content width - readable line length */
.content-width {
  max-width: 65ch;  /* ~65 characters per line */
}

/* Wider for dashboards/data */
.dashboard-width {
  max-width: 1200px;
}

/* Generous margins - let content breathe */
.page {
  padding: 2rem 3rem;
}

/* Consistent spacing scale */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

### Data Display

```css
/* Tables - Tufte style */
.table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-serif);
}

.table th {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  text-align: left;

  padding: 0.75rem 1rem;
  border-bottom: 2px solid var(--text-primary);
}

.table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--rule-light);
}

/* Numbers in tables - right align, monospace */
.table td.numeric {
  font-family: var(--font-mono);
  text-align: right;
}
```

```css
/* Metrics/KPIs - simple, typographic */
.metric {
  text-align: center;
}

.metric-value {
  font-family: var(--font-serif);
  font-size: var(--text-4xl);
  font-weight: 400;
  color: var(--text-primary);
  line-height: 1;
}

.metric-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--text-tertiary);
  margin-top: 0.5rem;
}

.metric-change {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--ink-success);
}
```

---

## Implementation Patterns

### File Structure Convention

```
frontend/src/
├── components/
│   ├── ui/                    # Base design system components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Table.tsx
│   │   └── Typography.tsx     # H1, H2, P, Caption, etc.
│   ├── loris/
│   │   ├── LorisIllustration.tsx
│   │   └── loris-images/      # Loris image assets
│   ├── questions/
│   │   ├── QuestionCard.tsx
│   │   ├── QuestionForm.tsx
│   │   └── AnswerDisplay.tsx
│   └── expert/
│       ├── QueueItem.tsx
│       ├── GapAnalysis.tsx
│       └── AnswerComposer.tsx
├── pages/
│   ├── user/
│   │   ├── Dashboard.tsx
│   │   └── QuestionDetail.tsx
│   └── expert/
│       ├── Queue.tsx
│       └── ReviewQuestion.tsx
├── styles/
│   ├── globals.css            # CSS custom properties, base styles
│   └── tufte.css              # Tufte-specific utilities
└── lib/
    └── api/                   # API client functions
```

### Component Example

```tsx
// components/questions/QuestionCard.tsx

import { Card } from '@/components/ui/Card';
import { LorisIllustration } from '@/components/loris/LorisIllustration';

interface QuestionCardProps {
  question: Question;
  onClick?: () => void;
}

export function QuestionCard({ question, onClick }: QuestionCardProps) {
  return (
    <Card
      className={question.hasUnreadAnswer ? 'card-elevated' : ''}
      onClick={onClick}
    >
      {/* Status line - small, typographic */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`status status-${question.status}`}>
          {question.status === 'auto_answered' ? 'Automated' : question.status}
        </span>
        <span className="text-muted">·</span>
        <time className="text-muted text-sm">
          {formatRelativeTime(question.createdAt)}
        </time>
      </div>

      {/* Question text - prominent, readable */}
      <p className="font-serif text-lg leading-relaxed">
        {question.text}
      </p>

      {/* Footer with subtle rule */}
      <hr className="rule my-4" />

      <div className="flex items-center justify-between">
        <span className="text-secondary text-sm">
          {question.category}
        </span>
        <button className="btn-link">
          View →
        </button>
      </div>
    </Card>
  );
}
```

### API Integration Pattern

```typescript
// lib/api/questions.ts

import { apiClient } from './client';

export const questionsApi = {
  async submit(data: QuestionSubmit): Promise<QuestionResult> {
    return apiClient.post('/questions', data);
  },

  async list(filters?: QuestionFilters): Promise<PaginatedList<Question>> {
    return apiClient.get('/questions', { params: filters });
  },

  async get(id: string): Promise<QuestionDetail> {
    return apiClient.get(`/questions/${id}`);
  },

  async submitFeedback(id: string, feedback: Feedback): Promise<void> {
    return apiClient.post(`/questions/${id}/feedback`, feedback);
  },
};
```

### Backend Service Pattern

```python
# backend/app/services/questions_service.py

from app.models.questions import Question, QuestionStatus
from app.services.automation_service import AutomationService
from app.services.gap_analysis_service import GapAnalysisService

class QuestionsService:
    def __init__(
        self,
        db: AsyncSession,
        automation_service: AutomationService,
        gap_analysis_service: GapAnalysisService,
        embedding_service: EmbeddingService,
    ):
        self.db = db
        self.automation = automation_service
        self.gap_analysis = gap_analysis_service
        self.embedding = embedding_service

    async def submit_question(
        self,
        user_id: UUID,
        text: str,
        category: str | None = None,
    ) -> QuestionSubmitResult:
        """
        Submit a new question.

        Flow:
        1. Create question record
        2. Generate embedding
        3. Check for automation match
        4. If match >= threshold: deliver auto-answer
        5. If no match: run gap analysis and queue for expert
        """
        # Create question
        question = Question(
            asked_by_id=user_id,
            original_text=text,
            category=category,
            status=QuestionStatus.PROCESSING,
        )
        self.db.add(question)
        await self.db.flush()

        # Generate embedding
        embedding = await self.embedding.generate(text)

        # Check automation
        match = await self.automation.find_match(
            embedding=embedding,
            organization_id=question.organization_id,
            category=category,
        )

        if match and match.similarity >= match.rule.similarity_threshold:
            return await self._deliver_auto_answer(question, match)

        # No automation - queue for expert with gap analysis
        gap_analysis = await self.gap_analysis.analyze(question, embedding)
        question.gap_analysis = gap_analysis.dict()
        question.status = QuestionStatus.EXPERT_QUEUE
        await self.db.commit()

        return QuestionSubmitResult(
            question=question,
            auto_answered=False,
            message="Your question has been submitted to our experts.",
        )
```

---

## Common Tasks

### Adding a New Page

1. Create page component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Use existing UI components from `frontend/src/components/ui/`
4. Follow Tufte aesthetic guidelines

### Adding a New API Endpoint

1. Create/update Pydantic schemas in `backend/app/schemas/`
2. Create/update service methods in `backend/app/services/`
3. Add endpoint in `backend/app/api/v1/`
4. Register router in `backend/app/main.py`
5. Add API client function in `frontend/src/lib/api/`

### Adding a Database Model

1. Create model in `backend/app/models/`
2. Create Alembic migration: `alembic revision --autogenerate -m "description"`
3. Review and edit migration file
4. Apply: `alembic upgrade head`

### Working with Loris Images

Images are stored in `frontend/src/components/loris/loris-images/`. Use the `LorisIllustration` component:

```tsx
<LorisIllustration
  variant="transwarp"
  size="medium"
  caption="Automated response"
/>
```

---

## Testing Guidance

### What to Test

- **Services**: Unit tests for business logic
- **API**: Integration tests for endpoints
- **Components**: Basic render tests, interaction tests for forms
- **E2E**: Critical user journeys (submit question, receive answer)

### Test File Location

```
backend/tests/
├── unit/
│   └── services/
│       └── test_questions_service.py
└── integration/
    └── api/
        └── test_questions_endpoints.py

frontend/src/
└── __tests__/
    ├── components/
    └── pages/
```

---

## Questions to Ask When Uncertain

1. **"Does this add information or just decoration?"** → If decoration, remove it
2. **"Could this be simpler?"** → Probably yes
3. **"Does this match the Tufte aesthetic?"** → Cream background, serif type, hairline rules
4. **"Is this retained from CounselScope?"** → Check the retain/create list in migration doc
5. **"Does the user need to see this?"** → If not, don't show it

---

## Checklist Before Committing

- [ ] Follows Tufte aesthetic (no neon, no gradients, no glowing)
- [ ] Uses serif fonts for content, monospace for labels/code
- [ ] Cream/off-white backgrounds, dark text
- [ ] Buttons are understated, not shouty
- [ ] Status indicators are typographic, not colorful badges
- [ ] Loris images displayed as illustrations, not icons
- [ ] Code follows existing patterns in codebase
- [ ] New endpoints have schemas and error handling
- [ ] Changes documented in relevant planning docs if scope changes

---

*This guide should be updated as patterns evolve during implementation.*
