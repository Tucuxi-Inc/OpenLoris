# Phase 9c & 11: Google Drive via Zapier MCP + MoltenLoris Foundation

## Status: Planning

**Phase 9a** (AI Provider Configuration): COMPLETE
**Phase 9b** (AI Provider Frontend UI): COMPLETE
**Phase 10** (LorisAvatar Component): COMPLETE

---

## Phase 9c: Google Drive Integration via Zapier MCP

### Design Decision: Zapier MCP vs Direct OAuth

We're using Zapier MCP for Google Drive integration rather than building direct OAuth. This provides:

1. **Simplified authentication** - Zapier handles all Google OAuth, token refresh, etc.
2. **Single configuration point** - Admin configures Zapier connection once
3. **Unified access pattern** - Both Loris Web App and MoltenLoris use the same MCP interface
4. **Audit trail** - All operations logged in Zapier
5. **Security isolation** - Loris never touches Google credentials directly

### Architecture

```
Business User → Loris Web App → Zapier MCP → Google Drive
                     ↑
MoltenLoris ─────────┘
```

### Implementation

#### Backend: `backend/app/services/gdrive_service.py`

```python
class GDriveService:
    """Google Drive operations via Zapier MCP"""

    async def list_folders(self, org_id: str) -> list[dict]:
        """List available GDrive folders via Zapier"""

    async def read_file(self, file_id: str) -> str:
        """Read file content via Zapier"""

    async def write_file(self, folder_id: str, filename: str, content: str) -> dict:
        """Write/update file via Zapier"""

    async def sync_knowledge_to_drive(self, org_id: str, db: AsyncSession):
        """Export WisdomFacts as markdown files to GDrive"""

    async def import_from_drive(self, folder_id: str, db: AsyncSession):
        """Import markdown files with YAML frontmatter as WisdomFacts"""
```

#### Backend: `backend/app/api/v1/gdrive.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/gdrive/status | Check connection status |
| GET | /api/v1/gdrive/folders | List available folders |
| POST | /api/v1/gdrive/sync | Trigger sync (export facts to GDrive) |
| POST | /api/v1/gdrive/import | Import facts from GDrive folder |
| GET | /api/v1/gdrive/files | List files in configured folder |

#### Frontend: Settings UI

Add to `frontend/src/pages/admin/OrgSettingsPage.tsx`:

```tsx
// GDrive/Zapier MCP Settings panel
<GDriveSettingsPanel />
```

**`frontend/src/components/settings/GDriveSettings.tsx`:**

- Zapier MCP URL input field
- Test Connection button
- Folder selector (after connection test succeeds)
- Sync direction toggle: Export only / Import only / Bidirectional
- Last sync timestamp display
- Manual Sync button

#### Org Settings Schema Update

```python
# backend/app/models/organizations.py - settings JSONB
{
    "gdrive": {
        "zapier_mcp_url": "https://...",
        "folder_id": "...",
        "sync_direction": "export",  # export | import | bidirectional
        "last_sync_at": "2026-01-29T...",
        "enabled": true
    }
}
```

### File Format for GDrive Sync

Knowledge facts exported to GDrive use markdown with YAML frontmatter:

```markdown
---
id: fact-2026-01-28-001
created_by: sarah.chen@company.com
department: Legal
category: contracts
tier: tier_0b
confidence: 0.92
gud_date: 2026-07-28
tags: [vendor, contracts, renewal]
loris_sync: true
---

# Fact Title

Fact content here...
```

This format is compatible with MoltenLoris's READ-ONLY consumption.

---

## Phase 11: MoltenLoris Foundation

### Overview

MoltenLoris is an autonomous Slack-monitoring Claude Desktop agent that:
1. Watches configured Slack channels for questions
2. Searches the knowledge base (via GDrive read-only access)
3. Provides answers with confidence levels
4. Escalates to human experts when uncertain
5. Prompts humans to save new knowledge (cannot write itself)

### Architecture

```
Slack Channel → Claude Desktop (MoltenLoris) → Zapier MCP (read-only) → GDrive
                           ↓
                    Escalation → Expert notification
```

### Key Constraint: READ-ONLY

MoltenLoris has READ-ONLY access to the knowledge base. It CANNOT:
- Create new knowledge files
- Edit existing knowledge files
- Write to the Loris database

When an expert provides a good answer, MoltenLoris:
1. Thanks them
2. Provides a link to the Loris Web App where they can add the knowledge
3. Encourages them to save it so MoltenLoris can help next time

### SOUL Configuration

The SOUL-TEMPLATE.md defines MoltenLoris's behavior:
- Communication style and formatting
- Confidence thresholds (≥75% auto-answer, 50-74% tentative, <50% escalate)
- Response templates
- Behavior rules (what to always/never do)
- Rate limits and constraints

### Phase 11a: MoltenLoris Backend Support

Add to Loris Web App backend:

1. **MoltenLoris Settings** in org settings:
   - Enabled toggle
   - Slack channel configuration (store channel ID, not secrets)
   - Expert handles for escalation
   - Confidence thresholds (configurable per org)

2. **API endpoints for MoltenLoris**:
   - `GET /api/v1/moltenloris/config` - Get org's MoltenLoris config
   - `GET /api/v1/moltenloris/knowledge` - Search knowledge (read-only)
   - `POST /api/v1/moltenloris/log` - Log MoltenLoris activity (optional)

### Phase 11b: MoltenLoris Settings UI

Add to frontend:

1. **MoltenLoris page** - currently shows "Coming Soon"
2. Update to show:
   - Enable/disable toggle
   - Configuration panel (channel, experts, thresholds)
   - Activity log viewer
   - Quick stats (questions answered, escalated, learned)

### Phase 11c: SOUL File Generation

The Loris Web App can generate/update the SOUL configuration file:

1. Admin configures MoltenLoris settings in UI
2. Backend generates SOUL.md from template + org settings
3. SOUL.md exported to GDrive folder
4. MoltenLoris (Claude Desktop) reads SOUL.md on startup

---

## Implementation Order

### Phase 9c: GDrive via Zapier (4-6 hours)
1. Create `gdrive_service.py` with Zapier MCP client
2. Create `api/v1/gdrive.py` endpoints
3. Update org settings schema for GDrive config
4. Create `GDriveSettings.tsx` component
5. Integrate into OrgSettingsPage
6. Test sync flow

### Phase 11a: MoltenLoris Backend (2-3 hours)
1. Add MoltenLoris config to org settings schema
2. Create `api/v1/moltenloris.py` endpoints
3. Create `moltenloris_service.py` for knowledge search

### Phase 11b: MoltenLoris Frontend (2-3 hours)
1. Update MoltenLorisPage with settings UI
2. Add configuration panel component
3. Add activity log viewer (if logging enabled)

### Phase 11c: SOUL Generation (1-2 hours)
1. Create SOUL template renderer
2. Add "Generate SOUL" button to MoltenLoris settings
3. Export to GDrive

---

## Files Summary

**New backend files:**
- `backend/app/services/gdrive_service.py`
- `backend/app/api/v1/gdrive.py`
- `backend/app/api/v1/moltenloris.py`
- `backend/app/services/moltenloris_service.py`

**New frontend files:**
- `frontend/src/components/settings/GDriveSettings.tsx`
- `frontend/src/components/settings/MoltenLorisSettings.tsx`

**Modified files:**
- `backend/app/main.py` (register new routers)
- `frontend/src/pages/admin/OrgSettingsPage.tsx` (add GDrive panel)
- `frontend/src/pages/MoltenLorisPage.tsx` (replace "Coming Soon" with settings)
- `docs/loris-planning/SOUL-TEMPLATE.md` (reference only, already exists)
