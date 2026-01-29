# Claude Code Instructions: Turbo Loris & MoltenLoris Implementation (v2)

**Date:** January 28, 2026
**Project:** Loris
**Prepared by:** Kevin Rogers / Claude

---

## Overview

This document provides instructions for Claude Code to implement two new features for Loris:

1. **Turbo Loris** — User-controlled fast-answer mode with knowledge-based instant responses
2. **MoltenLoris** — Autonomous Slack-monitoring agent with read-only GDrive access

### Key Architectural Decision

**Google Drive serves as the shared knowledge distribution layer:**
- Loris Web App: READ + WRITE to PostgreSQL (ground truth) and GDrive (distribution)
- MoltenLoris: READ ONLY from GDrive (cannot modify knowledge)

This ensures data integrity while enabling MoltenLoris to access organizational knowledge.

---

## Step 1: Update Project Documentation

### 1.1 Add Planning Document

Copy `09-TURBO-AND-MOLTEN-LORIS.md` to the planning docs folder:

```bash
cp 09-TURBO-AND-MOLTEN-LORIS.md docs/loris-planning/
```

**Read this document completely before writing any code.**

### 1.2 Update CLAUDE.md

Append the contents of `CLAUDE-ADDITIONS-TURBO-MOLTEN.md` to the existing `CLAUDE.md` file.

### 1.3 Update Implementation Status Table

In `CLAUDE.md`, update the implementation status table:

```markdown
| Phase 8: Turbo Loris | NOT STARTED | User-controlled fast-answer mode, attribution system |
| Phase 9: GDrive Sync | NOT STARTED | Sync knowledge to GDrive for MoltenLoris |
| Phase 10: MoltenLoris Docs | NOT STARTED | Setup guide, SOUL.md template |
```

### 1.4 Add Documentation Files

Create these files:
- `docs/moltenloris/SOUL-TEMPLATE.md`
- `docs/moltenloris/SETUP-GUIDE.md`

---

## Step 2: Implement Turbo Loris Backend

### 2.1 Database Schema Changes

Run these migrations manually:

```sql
-- Add turbo fields to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_mode BOOLEAN DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_threshold FLOAT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_confidence FLOAT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_sources UUID[];

-- Add enum value for question status
ALTER TYPE questionstatus ADD VALUE IF NOT EXISTS 'turbo_answered';

-- Create turbo_attributions table
CREATE TABLE IF NOT EXISTS turbo_attributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    attributed_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    attributed_department_id UUID NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    contribution_type VARCHAR(50) NOT NULL,
    contribution_date TIMESTAMP NOT NULL,
    confidence_score FLOAT NOT NULL,
    semantic_similarity FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_turbo_attr_question ON turbo_attributions(question_id);
CREATE INDEX IF NOT EXISTS idx_turbo_attr_source ON turbo_attributions(source_type, source_id);
```

### 2.2 Create TurboAttribution Model

Create `backend/app/models/turbo.py`:

```python
from datetime import datetime
from uuid import UUID
from sqlalchemy import ForeignKey, String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class TurboAttribution(Base, UUIDMixin, TimestampMixin):
    """Records knowledge sources that contributed to a Turbo Loris answer."""
    __tablename__ = "turbo_attributions"
    
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[UUID]
    attributed_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    attributed_department_id: Mapped[UUID]
    display_name: Mapped[str] = mapped_column(String(255))
    contribution_type: Mapped[str] = mapped_column(String(50))
    contribution_date: Mapped[datetime] = mapped_column(DateTime)
    confidence_score: Mapped[float] = mapped_column(Float)
    semantic_similarity: Mapped[float] = mapped_column(Float)
    
    # Relationships
    question = relationship("Question", back_populates="turbo_attributions")
```

**Remember to:**
1. Add `TurboAttribution` to `backend/app/models/__init__.py`
2. Add `turbo_attributions` relationship to the Question model

### 2.3 Update Question Model

In `backend/app/models/questions.py`:

```python
from sqlalchemy import Boolean, Float, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID

class QuestionStatus(str, Enum):
    # ... existing values ...
    TURBO_ANSWERED = "turbo_answered"

class Question(Base, UUIDMixin, TimestampMixin):
    # ... existing fields ...
    
    # Turbo Loris fields
    turbo_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    turbo_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    turbo_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    turbo_sources: Mapped[list | None] = mapped_column(ARRAY(PGUUID), nullable=True)
    
    # Relationships
    turbo_attributions = relationship(
        "TurboAttribution", 
        back_populates="question", 
        cascade="all, delete-orphan"
    )
```

### 2.4 Create Turbo Service

Create `backend/app/services/turbo_service.py` with these key methods:

- `attempt_turbo_answer(question, threshold) -> (success, confidence, answer, attributions)`
- `_calculate_confidence(matched_facts) -> float`
- `_generate_answer(question_text, matched_facts) -> str`
- `_create_attributions(question_id, sources) -> List[TurboAttribution]`
- `handle_user_departure(user_id) -> int`

See the planning document for full implementation details.

### 2.5 Update Question Submission Endpoint

In `backend/app/api/v1/questions.py`:

```python
class QuestionCreate(BaseModel):
    # ... existing fields ...
    turbo_mode: bool = False
    turbo_threshold: float = 0.75

@router.post("/")
async def create_question(...):
    # ... existing validation ...
    
    # Create question with turbo fields
    question = Question(
        text=request.text,
        turbo_mode=request.turbo_mode,
        turbo_threshold=request.turbo_threshold if request.turbo_mode else None,
        # ... other fields ...
    )
    
    # If Turbo mode, attempt fast answer
    if request.turbo_mode:
        turbo_service = TurboService(db)
        success, confidence, answer_text, attributions = \
            await turbo_service.attempt_turbo_answer(question, request.turbo_threshold)
        
        if success:
            # Create answer, update status, return with attributions
            ...
    
    # ... rest of existing logic ...
```

---

## Step 3: Implement GDrive Sync Service

This enables MoltenLoris to access knowledge without direct database access.

### 3.1 Add Configuration

In `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # MoltenLoris / GDrive Sync
    MOLTENLORIS_ENABLED: bool = False
    GDRIVE_CREDENTIALS_FILE: str | None = None
    GDRIVE_KNOWLEDGE_FOLDER_ID: str | None = None
```

In `.env.example`:

```bash
# MoltenLoris Mode
MOLTENLORIS_ENABLED=false
GDRIVE_CREDENTIALS_FILE=/path/to/service-account.json
GDRIVE_KNOWLEDGE_FOLDER_ID=your-folder-id
```

### 3.2 Create GDrive Client

Create `backend/app/services/gdrive_client.py`:

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


class GDriveClient:
    """Google Drive API client for syncing knowledge files."""
    
    def __init__(self, credentials_file: str, folder_id: str):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        self.service = build('drive', 'v3', credentials=credentials)
        self.folder_id = folder_id
    
    async def upload_file(self, path: str, content: str, mime_type: str = "text/markdown"):
        """Upload or update a file in GDrive."""
        # Implementation details...
    
    async def move_file(self, old_path: str, new_path: str):
        """Move a file (for archiving)."""
        # Implementation details...
    
    async def delete_file(self, path: str):
        """Delete a file."""
        # Implementation details...
```

### 3.3 Create GDrive Sync Service

Create `backend/app/services/gdrive_sync_service.py`:

```python
import yaml
from app.models.wisdom import WisdomFact
from app.services.gdrive_client import GDriveClient
from app.core.config import settings


class GDriveSyncService:
    """
    Syncs knowledge from PostgreSQL to Google Drive.
    Called on fact create/update/delete when MOLTENLORIS_ENABLED is True.
    """
    
    def __init__(self):
        if settings.MOLTENLORIS_ENABLED:
            self.gdrive = GDriveClient(
                settings.GDRIVE_CREDENTIALS_FILE,
                settings.GDRIVE_KNOWLEDGE_FOLDER_ID
            )
        else:
            self.gdrive = None
    
    async def sync_fact(self, fact: WisdomFact) -> None:
        """Write a fact to GDrive as a markdown file."""
        if not settings.MOLTENLORIS_ENABLED or not self.gdrive:
            return
        
        markdown = self._fact_to_markdown(fact)
        folder = f"facts/{fact.category or 'general'}"
        filename = f"fact-{fact.created_at.date()}-{str(fact.id)[:8]}.md"
        
        await self.gdrive.upload_file(
            path=f"{folder}/{filename}",
            content=markdown
        )
    
    async def archive_fact(self, fact: WisdomFact) -> None:
        """Move a deleted/expired fact to the _archived folder."""
        if not settings.MOLTENLORIS_ENABLED or not self.gdrive:
            return
        
        old_path = self._get_fact_path(fact)
        new_path = f"_archived/facts/{fact.id}.md"
        
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
            "tier": fact.tier.value if fact.tier else None,
            "confidence": fact.confidence,
            "gud_date": fact.gud_date.isoformat() if fact.gud_date else None,
            "tags": fact.tags or [],
        }
        
        yaml_str = yaml.dump(frontmatter, default_flow_style=False)
        
        return f"""---
{yaml_str}---

# {getattr(fact, 'title', 'Knowledge Fact') or 'Knowledge Fact'}

{fact.content}
"""
    
    def _get_fact_path(self, fact: WisdomFact) -> str:
        """Get the GDrive path for a fact."""
        folder = f"facts/{fact.category or 'general'}"
        filename = f"fact-{fact.created_at.date()}-{str(fact.id)[:8]}.md"
        return f"{folder}/{filename}"
```

### 3.4 Integrate Sync into Knowledge Service

In `backend/app/services/knowledge_service.py`:

```python
from app.services.gdrive_sync_service import GDriveSyncService

class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gdrive_sync = GDriveSyncService()
    
    async def create_fact(self, fact_data: dict, user: User) -> WisdomFact:
        # ... existing creation logic ...
        
        await self.db.commit()
        
        # Sync to GDrive for MoltenLoris
        await self.gdrive_sync.sync_fact(fact)
        
        return fact
    
    async def update_fact(self, fact_id: UUID, fact_data: dict) -> WisdomFact:
        # ... existing update logic ...
        
        await self.db.commit()
        
        # Sync updated fact to GDrive
        await self.gdrive_sync.sync_fact(fact)
        
        return fact
    
    async def archive_fact(self, fact_id: UUID) -> None:
        # ... existing archive logic ...
        
        # Move to archive in GDrive
        await self.gdrive_sync.archive_fact(fact)
```

### 3.5 Integrate with GUD Scheduler

In `backend/app/services/scheduler_service.py`:

```python
from app.services.gdrive_sync_service import GDriveSyncService

async def check_gud_expiry():
    gdrive_sync = GDriveSyncService()
    expired_facts = await get_expired_facts()
    
    for fact in expired_facts:
        # Mark as archived in PostgreSQL
        fact.tier = WisdomTier.ARCHIVED
        await db.commit()
        
        # Move to archive in GDrive
        await gdrive_sync.archive_fact(fact)
        
        # Send notification
        await notification_service.notify_fact_expired(fact)
```

---

## Step 4: Implement Turbo Loris Frontend

### 4.1 Update Question Submission Form

In the question submission page, add Turbo mode toggle:

```tsx
const [turboMode, setTurboMode] = useState(false);
const [turboThreshold, setTurboThreshold] = useState(0.75);

// In form JSX:
<div className="answer-mode-section">
  <label className="flex items-center gap-2">
    <input
      type="radio"
      name="answerMode"
      checked={!turboMode}
      onChange={() => setTurboMode(false)}
    />
    <span>Standard (Expert-verified)</span>
  </label>
  <p className="text-sm text-gray-500 ml-6">"Slow is smooth, smooth is fast"</p>
  
  <label className="flex items-center gap-2 mt-3">
    <input
      type="radio"
      name="answerMode"
      checked={turboMode}
      onChange={() => setTurboMode(true)}
    />
    <span className="font-medium">⚡ Turbo Loris</span>
  </label>
  
  {turboMode && (
    <div className="ml-6 mt-2 p-3 bg-amber-50 rounded">
      <label className="text-sm font-medium">Confidence threshold:</label>
      <select
        value={turboThreshold}
        onChange={(e) => setTurboThreshold(parseFloat(e.target.value))}
        className="ml-2 border rounded px-2 py-1"
      >
        <option value={0.90}>90% - High confidence</option>
        <option value={0.75}>75% - Moderate confidence</option>
        <option value={0.50}>50% - Best guess</option>
      </select>
      <p className="text-sm text-gray-600 mt-2 italic">
        "Fast is rough, rough can be slow"
      </p>
    </div>
  )}
</div>
```

### 4.2 Create TurboAnswerCard Component

Create `frontend/src/components/TurboAnswerCard.tsx`:

```tsx
interface TurboAnswerCardProps {
  answer: string;
  confidence: number;
  threshold: number;
  attributions: TurboAttribution[];
  onHelpful: () => void;
  onRequestExpert: () => void;
}

export function TurboAnswerCard({ 
  answer, 
  confidence, 
  threshold, 
  attributions,
  onHelpful,
  onRequestExpert
}: TurboAnswerCardProps) {
  const topContributor = attributions[0];
  
  return (
    <div className="border rounded-lg p-6 bg-amber-50">
      <div className="flex items-center gap-4 mb-4">
        <img 
          src="/loris-images/TransWarp_Loris.png" 
          alt="Turbo Loris" 
          className="w-16 h-16"
        />
        <div>
          <h3 className="font-bold text-lg">⚡ Turbo Loris Answer</h3>
          <p className="text-sm text-gray-600">
            Confidence: {Math.round(confidence * 100)}% 
            (your threshold: {Math.round(threshold * 100)}%)
          </p>
        </div>
      </div>
      
      <div className="prose mb-4">{answer}</div>
      
      <div className="border-t pt-4">
        <h4 className="font-semibold text-sm mb-2">📚 Sources</h4>
        {attributions.map((attr) => (
          <div key={attr.id} className="text-sm text-gray-600 mb-1">
            {attr.source_type} — {attr.display_name}
            <span className="text-gray-400 ml-2">
              ({Math.round(attr.confidence_score * 100)}% match)
            </span>
          </div>
        ))}
      </div>
      
      {topContributor && (
        <div className="mt-4 p-3 bg-amber-100 rounded text-sm">
          💡 Thanks to <strong>{topContributor.display_name}</strong> — 
          their knowledge turbo-charged this Loris!
        </div>
      )}
      
      <div className="flex gap-4 mt-4">
        <button onClick={onHelpful} className="btn-secondary">
          ✓ This helped
        </button>
        <button onClick={onRequestExpert} className="btn-outline">
          🔄 Request expert review
        </button>
      </div>
    </div>
  );
}
```

### 4.3 Update API Client Types

In `frontend/src/lib/api/questions.ts`:

```typescript
export interface QuestionCreate {
  text: string;
  category?: string;
  priority?: string;
  department?: string;
  subdomain_id?: string;
  turbo_mode?: boolean;
  turbo_threshold?: number;
}

export interface TurboAttribution {
  id: string;
  source_type: string;
  source_id: string;
  display_name: string;
  contribution_type: string;
  confidence_score: number;
  semantic_similarity: number;
}

export interface QuestionResponse {
  question: Question;
  turbo_answered?: boolean;
  turbo_confidence?: number;
  turbo_threshold?: number;
  attributions?: TurboAttribution[];
  answer?: Answer;
}
```

---

## Step 5: Create MoltenLoris Documentation

### 5.1 Create SOUL.md Template

Create `docs/moltenloris/SOUL-TEMPLATE.md` with the full template (see separate file).

Key sections:
- Identity and communication style
- Channel configuration (Slack read/write)
- Knowledge sources (GDrive READ-ONLY)
- Confidence thresholds and actions
- Response templates
- Behavior rules (including "cannot write to GDrive")
- Learning prompt behavior

### 5.2 Create Setup Guide

Create `docs/moltenloris/SETUP-GUIDE.md` with:

1. Prerequisites
2. Enable MoltenLoris Mode in Loris Web App
3. Create UTM Virtual Machine
4. Install Moltbot in VM
5. Configure Zapier MCP (READ-ONLY GDrive)
6. Connect MoltenLoris to Zapier
7. Configure SOUL.md
8. Start monitoring
9. Verify operation
10. Troubleshooting

---

## Step 6: Testing

### 6.1 Turbo Loris Backend Tests

```bash
BASE="http://localhost:8005/api/v1"

# Login as expert
EXPERT_TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -d "username=bob@loris.dev&password=Test1234!" | jq -r '.access_token')

# Create a knowledge fact
curl -s -X POST "$BASE/knowledge/facts" \
  -H "Authorization: Bearer $EXPERT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Standard vendor contracts have a 12-month term.",
    "category": "contracts",
    "tier": "tier_0b"
  }'

# Login as user
USER_TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -d "username=carol@loris.dev&password=Test1234!" | jq -r '.access_token')

# Submit Turbo question
curl -s -X POST "$BASE/questions/" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is the standard term for vendor contracts?",
    "turbo_mode": true,
    "turbo_threshold": 0.75
  }' | jq

# Expected: turbo_answered=true, attributions populated
```

### 6.2 GDrive Sync Tests

```bash
# Enable MoltenLoris mode (in .env)
MOLTENLORIS_ENABLED=true

# Restart backend
docker-compose restart backend

# Create a fact
curl -s -X POST "$BASE/knowledge/facts" \
  -H "Authorization: Bearer $EXPERT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test fact for GDrive sync.",
    "category": "test"
  }'

# Verify: Check GDrive /Loris-Knowledge/facts/test/ for new .md file
```

---

## Step 7: Final Checklist

### Backend
- [ ] Run SQL migrations for turbo_attributions table
- [ ] Add enum value `turbo_answered` to QuestionStatus
- [ ] Add `TurboAttribution` model to models/__init__.py
- [ ] Update Question model with turbo fields and relationship
- [ ] Create TurboService
- [ ] Update question creation endpoint for Turbo mode
- [ ] Add GDrive config to Settings
- [ ] Create GDriveClient
- [ ] Create GDriveSyncService
- [ ] Integrate sync into KnowledgeService
- [ ] Integrate sync into scheduler (GUD expiry)
- [ ] Rebuild backend: `docker-compose up -d --build backend`

### Frontend
- [ ] Add Turbo mode toggle to question submission form
- [ ] Create TurboAnswerCard component
- [ ] Update QuestionDetailPage for Turbo answers
- [ ] Update API client types
- [ ] Restart frontend: `docker-compose restart frontend`

### Documentation
- [ ] Copy planning doc to docs/loris-planning/
- [ ] Append additions to CLAUDE.md
- [ ] Create docs/moltenloris/SOUL-TEMPLATE.md
- [ ] Create docs/moltenloris/SETUP-GUIDE.md
- [ ] Update README.md

### Testing
- [ ] Test Turbo answer flow
- [ ] Test attribution display
- [ ] Test GDrive sync on fact create
- [ ] Test GDrive sync on fact update
- [ ] Test GDrive archive on fact delete/expire
- [ ] Verify MoltenLoris can read from GDrive (manual test)

---

## Key Reminders

1. **PostgreSQL is always the source of truth** — GDrive is a derived copy for MoltenLoris
2. **MoltenLoris has READ-ONLY access** — It cannot modify GDrive or any knowledge
3. **Learning requires human action** — MoltenLoris prompts experts to add knowledge via Loris Web App
4. **Departed employee handling** — Batch update attributions when user is deactivated
5. **GDrive sync is optional** — Only enabled when `MOLTENLORIS_ENABLED=true`
