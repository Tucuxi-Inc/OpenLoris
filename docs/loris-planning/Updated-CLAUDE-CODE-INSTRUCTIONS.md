# Claude Code Instructions: Turbo Loris & MoltenLoris Integration

**Date:** January 28, 2026
**Project:** Loris
**Prepared by:** Kevin Keller / Claude

---

## Overview

This document provides instructions for Claude Code to implement two features:

1. **Turbo Loris** — User-controlled fast-answer mode with knowledge-based instant responses
2. **MoltenLoris Integration** — Sync knowledge to Google Drive + monitor Slack for expert answers

**Architecture Note:** MoltenLoris (the VM agent) and Loris Web App communicate indirectly:
- **Slack**: MoltenLoris writes answers → Loris reads expert responses
- **Google Drive**: Loris writes knowledge files → MoltenLoris reads them

They never communicate directly. This is the air gap.

---

## Step 1: Update Project Documentation

### 1.1 Add Planning Document

Copy `09-TURBO-AND-MOLTEN-LORIS.md` to the planning docs folder:

```bash
cp docs/loris-planning/09-TURBO-AND-MOLTEN-LORIS.md docs/loris-planning/
```

### 1.2 Update CLAUDE.md

Append the contents of `CLAUDE-ADDITIONS-TURBO-MOLTEN.md` to the existing `CLAUDE.md` file.

### 1.3 Update Implementation Status Table

In `CLAUDE.md`, update the implementation status table:

```markdown
| Phase 8: Turbo Loris | NOT STARTED | User-controlled fast-answer mode, attribution system |
| Phase 9: MoltenLoris Sync | NOT STARTED | Slack monitoring + Google Drive knowledge export |
```

---

## Step 2: Environment Configuration

### 2.1 MCP Server Configuration

The Loris Web App needs access to two MCP tools. Add these environment variables:

```bash
# .env

# MCP Server Configuration
MCP_SERVER_URL=https://[your-zapier-mcp-url]
MCP_API_TOKEN=[your-mcp-token]

# Google Drive - Loris Knowledge Folder
GDRIVE_KNOWLEDGE_FOLDER_ID=[folder-id-for-Loris-Knowledge]
GDRIVE_KNOWLEDGE_FOLDER_PATH=/Loris-Knowledge

# Slack - Channels to monitor for expert answers
SLACK_MONITOR_CHANNELS=#legal-questions,#hr-questions,#it-questions
```

### 2.2 Config Class Updates

In `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # MCP Integration
    MCP_SERVER_URL: str | None = None
    MCP_API_TOKEN: str | None = None
    
    # Google Drive Knowledge Sync
    GDRIVE_KNOWLEDGE_FOLDER_ID: str | None = None
    GDRIVE_KNOWLEDGE_FOLDER_PATH: str = "/Loris-Knowledge"
    
    # Slack Monitoring
    SLACK_MONITOR_CHANNELS: str = ""  # Comma-separated
    
    @property
    def slack_channels_list(self) -> list[str]:
        if not self.SLACK_MONITOR_CHANNELS:
            return []
        return [c.strip() for c in self.SLACK_MONITOR_CHANNELS.split(",")]
```

---

## Step 3: Implement Turbo Loris Backend

*(Same as before — see full schema and service implementation)*

### 3.1 Database Schema Changes

```sql
-- Add turbo fields to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_mode BOOLEAN DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_threshold FLOAT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_confidence FLOAT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_sources UUID[];

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

### 3.2 Models

Create `backend/app/models/turbo.py` — See full implementation in planning doc.

### 3.3 Service

Create `backend/app/services/turbo_service.py` — See full implementation in planning doc.

### 3.4 API Updates

Update `backend/app/api/v1/questions.py` to support `turbo_mode` and `turbo_threshold` parameters.

---

## Step 4: Implement MoltenLoris Integration

This is the NEW architecture — no direct API between MoltenLoris and Loris.

### 4.1 Create MCP Client Service

Create `backend/app/services/mcp_client.py`:

```python
"""
MCP Client for Loris Web App.

Connects to Zapier MCP server to:
- Read Slack messages (monitoring expert answers)
- Write files to Google Drive (publishing knowledge)
"""

import httpx
from typing import Any
from app.core.config import settings


class MCPClient:
    """Client for MCP server communication."""
    
    def __init__(self):
        self.base_url = settings.MCP_SERVER_URL
        self.token = settings.MCP_API_TOKEN
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30.0
        )
    
    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> dict:
        """Call an MCP tool."""
        response = await self.client.post(
            "/tools/call",
            json={
                "tool": tool_name,
                "parameters": params
            }
        )
        response.raise_for_status()
        return response.json()
    
    # --- Slack Tools (Read-Only) ---
    
    async def slack_read_channel(
        self, 
        channel: str, 
        since: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Read messages from a Slack channel.
        
        Args:
            channel: Channel name (e.g., "#legal-questions")
            since: ISO timestamp to fetch messages after
            limit: Max messages to return
        
        Returns:
            List of message objects with thread info
        """
        result = await self.call_tool("slack_read_channel", {
            "channel": channel,
            "since": since,
            "limit": limit
        })
        return result.get("messages", [])
    
    async def slack_read_thread(self, channel: str, thread_ts: str) -> list[dict]:
        """Read all messages in a Slack thread."""
        result = await self.call_tool("slack_read_thread", {
            "channel": channel,
            "thread_ts": thread_ts
        })
        return result.get("messages", [])
    
    # --- Google Drive Tools (Write-Only to Loris-Knowledge) ---
    
    async def gdrive_write_file(
        self,
        filename: str,
        content: str,
        subfolder: str | None = None
    ) -> dict:
        """
        Write/update a file in the Loris-Knowledge folder.
        
        Args:
            filename: Name of the file (e.g., "NDA-Guidelines.md")
            content: File content (markdown)
            subfolder: Optional subfolder within Loris-Knowledge
        
        Returns:
            File metadata (id, url, etc.)
        """
        folder_path = settings.GDRIVE_KNOWLEDGE_FOLDER_PATH
        if subfolder:
            folder_path = f"{folder_path}/{subfolder}"
        
        result = await self.call_tool("gdrive_write_file", {
            "folder_id": settings.GDRIVE_KNOWLEDGE_FOLDER_ID,
            "folder_path": folder_path,
            "filename": filename,
            "content": content,
            "mime_type": "text/markdown"
        })
        return result
    
    async def gdrive_list_files(self, subfolder: str | None = None) -> list[dict]:
        """List files in the Loris-Knowledge folder."""
        folder_path = settings.GDRIVE_KNOWLEDGE_FOLDER_PATH
        if subfolder:
            folder_path = f"{folder_path}/{subfolder}"
        
        result = await self.call_tool("gdrive_list_files", {
            "folder_id": settings.GDRIVE_KNOWLEDGE_FOLDER_ID,
            "folder_path": folder_path
        })
        return result.get("files", [])
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_mcp_client: MCPClient | None = None

async def get_mcp_client() -> MCPClient:
    """Get or create MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
```

### 4.2 Create Slack Monitor Service

Create `backend/app/services/slack_monitor_service.py`:

```python
"""
Slack Monitor Service.

Monitors configured Slack channels for:
1. MoltenLoris escalations (🔴 reactions)
2. Expert responses to escalations
3. Captures Q&A pairs for knowledge base
"""

import re
from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mcp_client import get_mcp_client
from app.models.documents import ExtractedFactCandidate
from app.core.config import settings


class SlackMonitorService:
    """Service to monitor Slack for expert answers to MoltenLoris escalations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def scan_for_expert_answers(
        self,
        since: datetime | None = None
    ) -> List[dict]:
        """
        Scan monitored channels for expert answers.
        
        Looks for threads where:
        1. MoltenLoris posted an escalation (has 🔴 reaction)
        2. An expert (non-bot) replied
        
        Returns list of Q&A candidates.
        """
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)
        
        mcp = await get_mcp_client()
        candidates = []
        
        for channel in settings.slack_channels_list:
            messages = await mcp.slack_read_channel(
                channel=channel,
                since=since.isoformat(),
                limit=100
            )
            
            # Find MoltenLoris escalations
            for msg in messages:
                if not self._is_moltenloris_escalation(msg):
                    continue
                
                # Get the thread
                thread = await mcp.slack_read_thread(
                    channel=channel,
                    thread_ts=msg["ts"]
                )
                
                # Look for expert response
                expert_answer = self._find_expert_answer(thread)
                if expert_answer:
                    original_question = self._extract_original_question(msg, thread)
                    candidates.append({
                        "question": original_question,
                        "answer": expert_answer["text"],
                        "expert_name": expert_answer["user_name"],
                        "channel": channel,
                        "thread_ts": msg["ts"],
                        "timestamp": expert_answer["ts"]
                    })
        
        return candidates
    
    def _is_moltenloris_escalation(self, message: dict) -> bool:
        """Check if message is a MoltenLoris escalation."""
        # Check for 🔴 reaction
        reactions = message.get("reactions", [])
        has_red_circle = any(r["name"] == "red_circle" for r in reactions)
        
        # Check if from MoltenLoris (bot)
        is_bot = message.get("bot_id") is not None
        
        # Check for escalation text patterns
        text = message.get("text", "").lower()
        is_escalation = any(phrase in text for phrase in [
            "don't have enough information",
            "notifying",
            "need help with this"
        ])
        
        return has_red_circle or (is_bot and is_escalation)
    
    def _find_expert_answer(self, thread: List[dict]) -> dict | None:
        """Find the first non-bot response in a thread."""
        for msg in thread[1:]:  # Skip first message (the escalation)
            if msg.get("bot_id") is None and msg.get("text"):
                return msg
        return None
    
    def _extract_original_question(
        self,
        escalation_msg: dict,
        thread: List[dict]
    ) -> str:
        """Extract the original user question from the thread."""
        # The original question is usually quoted in MoltenLoris's escalation
        # or is the parent message if this is a thread reply
        
        # Try to find quoted text
        text = escalation_msg.get("text", "")
        
        # Look for the first non-bot message before the escalation
        for msg in thread:
            if msg.get("bot_id") is None and msg["ts"] < escalation_msg["ts"]:
                return msg.get("text", "")
        
        # Fallback: try to extract from escalation message
        # MoltenLoris might quote the question
        return text
    
    async def create_fact_candidates(
        self,
        qa_pairs: List[dict]
    ) -> List[ExtractedFactCandidate]:
        """Create fact candidates from Q&A pairs for expert review."""
        candidates = []
        
        for qa in qa_pairs:
            candidate = ExtractedFactCandidate(
                content=f"Q: {qa['question']}\n\nA: {qa['answer']}",
                source_type="slack_moltenloris",
                source_identifier=f"{qa['channel']}/{qa['thread_ts']}",
                status="pending",
                confidence_score=0.8,  # High confidence since expert answered
                metadata={
                    "question": qa["question"],
                    "answer": qa["answer"],
                    "expert_name": qa["expert_name"],
                    "channel": qa["channel"],
                    "thread_ts": qa["thread_ts"],
                    "captured_at": datetime.utcnow().isoformat()
                }
            )
            self.db.add(candidate)
            candidates.append(candidate)
        
        await self.db.commit()
        return candidates
```

### 4.3 Create Knowledge Export Service

Create `backend/app/services/knowledge_export_service.py`:

```python
"""
Knowledge Export Service.

Exports approved knowledge to Google Drive for MoltenLoris consumption.
"""

from datetime import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mcp_client import get_mcp_client
from app.models.wisdom import WisdomFact
from app.models.automation import AutomationRule


class KnowledgeExportService:
    """Service to export knowledge to Google Drive."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def export_category_knowledge(
        self,
        category: str,
        subdomain_id: str | None = None
    ) -> dict:
        """
        Export all approved knowledge for a category to Google Drive.
        
        Creates/updates a markdown file in Loris-Knowledge folder.
        """
        # Fetch approved facts for this category
        query = select(WisdomFact).where(
            WisdomFact.category == category,
            WisdomFact.tier.in_(["tier_0a", "tier_0b", "tier_0c"])
        )
        if subdomain_id:
            query = query.where(WisdomFact.subdomain_id == subdomain_id)
        
        result = await self.db.execute(query)
        facts = result.scalars().all()
        
        if not facts:
            return {"status": "no_facts", "category": category}
        
        # Generate markdown content
        content = self._generate_markdown(category, facts)
        
        # Write to Google Drive
        mcp = await get_mcp_client()
        filename = f"{self._sanitize_filename(category)}.md"
        
        file_result = await mcp.gdrive_write_file(
            filename=filename,
            content=content,
            subfolder=None  # Root of Loris-Knowledge
        )
        
        return {
            "status": "exported",
            "category": category,
            "fact_count": len(facts),
            "filename": filename,
            "gdrive_url": file_result.get("url")
        }
    
    async def export_all_knowledge(self) -> List[dict]:
        """Export all categories to Google Drive."""
        # Get distinct categories
        result = await self.db.execute(
            select(WisdomFact.category).distinct()
        )
        categories = [row[0] for row in result.fetchall() if row[0]]
        
        results = []
        for category in categories:
            result = await self.export_category_knowledge(category)
            results.append(result)
        
        # Also export automation rules as FAQ
        await self._export_automation_rules()
        
        return results
    
    async def _export_automation_rules(self) -> dict:
        """Export automation rules as a FAQ document."""
        result = await self.db.execute(
            select(AutomationRule).where(AutomationRule.is_active == True)
        )
        rules = result.scalars().all()
        
        if not rules:
            return {"status": "no_rules"}
        
        content = self._generate_faq_markdown(rules)
        
        mcp = await get_mcp_client()
        file_result = await mcp.gdrive_write_file(
            filename="FAQ-Automation-Rules.md",
            content=content
        )
        
        return {
            "status": "exported",
            "rule_count": len(rules),
            "gdrive_url": file_result.get("url")
        }
    
    def _generate_markdown(self, category: str, facts: List[WisdomFact]) -> str:
        """Generate markdown content from facts."""
        lines = [
            f"# {category.replace('_', ' ').title()}",
            "",
            f"*Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
            f"*Source: Loris Knowledge Base*",
            "",
            "---",
            ""
        ]
        
        # Group by tier
        tier_0a = [f for f in facts if f.tier == "tier_0a"]
        tier_0b = [f for f in facts if f.tier == "tier_0b"]
        tier_0c = [f for f in facts if f.tier == "tier_0c"]
        
        if tier_0a:
            lines.append("## Core Knowledge (Highest Confidence)")
            lines.append("")
            for fact in tier_0a:
                lines.append(f"- {fact.content}")
            lines.append("")
        
        if tier_0b:
            lines.append("## Established Knowledge")
            lines.append("")
            for fact in tier_0b:
                lines.append(f"- {fact.content}")
            lines.append("")
        
        if tier_0c:
            lines.append("## Working Knowledge")
            lines.append("")
            for fact in tier_0c:
                lines.append(f"- {fact.content}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_faq_markdown(self, rules: List[AutomationRule]) -> str:
        """Generate FAQ markdown from automation rules."""
        lines = [
            "# Frequently Asked Questions",
            "",
            f"*Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
            f"*Source: Loris Automation Rules*",
            "",
            "---",
            ""
        ]
        
        for rule in rules:
            lines.append(f"**Q: {rule.trigger_pattern}**")
            lines.append("")
            lines.append(f"A: {rule.response_template}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize category name for use as filename."""
        return name.replace(" ", "-").replace("/", "-").replace("_", "-").title()
```

### 4.4 Create Background Jobs

Create `backend/app/jobs/molten_sync_jobs.py`:

```python
"""
Background jobs for MoltenLoris sync.

These run on a schedule to:
1. Monitor Slack for expert answers
2. Export updated knowledge to Google Drive
"""

import asyncio
from datetime import datetime, timedelta
from app.core.database import async_session_maker
from app.services.slack_monitor_service import SlackMonitorService
from app.services.knowledge_export_service import KnowledgeExportService
import logging

logger = logging.getLogger(__name__)


async def scan_slack_for_answers():
    """
    Scan Slack channels for expert answers to MoltenLoris escalations.
    Run every 15 minutes.
    """
    async with async_session_maker() as db:
        try:
            service = SlackMonitorService(db)
            
            # Look back 1 hour (overlap to catch any missed)
            since = datetime.utcnow() - timedelta(hours=1)
            
            qa_pairs = await service.scan_for_expert_answers(since=since)
            
            if qa_pairs:
                candidates = await service.create_fact_candidates(qa_pairs)
                logger.info(f"Created {len(candidates)} fact candidates from Slack")
            
        except Exception as e:
            logger.error(f"Error scanning Slack: {e}")


async def export_knowledge_to_gdrive():
    """
    Export all approved knowledge to Google Drive.
    Run every hour or when knowledge changes.
    """
    async with async_session_maker() as db:
        try:
            service = KnowledgeExportService(db)
            results = await service.export_all_knowledge()
            
            exported = [r for r in results if r.get("status") == "exported"]
            logger.info(f"Exported {len(exported)} knowledge files to Google Drive")
            
        except Exception as e:
            logger.error(f"Error exporting to Google Drive: {e}")


# Schedule configuration (for use with APScheduler or similar)
JOB_SCHEDULE = {
    "scan_slack_for_answers": {
        "func": scan_slack_for_answers,
        "trigger": "interval",
        "minutes": 15
    },
    "export_knowledge_to_gdrive": {
        "func": export_knowledge_to_gdrive,
        "trigger": "interval",
        "hours": 1
    }
}
```

### 4.5 Add API Endpoints for Manual Triggers

Create `backend/app/api/v1/molten_sync.py`:

```python
"""
MoltenLoris Sync API endpoints.

Manual triggers for sync operations (for testing and admin use).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_admin_user
from app.services.slack_monitor_service import SlackMonitorService
from app.services.knowledge_export_service import KnowledgeExportService
from app.models.user import User


router = APIRouter(prefix="/molten-sync", tags=["MoltenLoris Sync"])


@router.post("/scan-slack")
async def trigger_slack_scan(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger Slack scan for expert answers."""
    service = SlackMonitorService(db)
    qa_pairs = await service.scan_for_expert_answers()
    
    if qa_pairs:
        candidates = await service.create_fact_candidates(qa_pairs)
        return {
            "status": "success",
            "qa_pairs_found": len(qa_pairs),
            "candidates_created": len(candidates)
        }
    
    return {"status": "success", "qa_pairs_found": 0}


@router.post("/export-knowledge")
async def trigger_knowledge_export(
    category: str | None = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger knowledge export to Google Drive."""
    service = KnowledgeExportService(db)
    
    if category:
        result = await service.export_category_knowledge(category)
        return result
    else:
        results = await service.export_all_knowledge()
        return {
            "status": "success",
            "exports": results
        }


@router.get("/status")
async def get_sync_status(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get MoltenLoris sync status and configuration."""
    from app.core.config import settings
    
    return {
        "mcp_configured": bool(settings.MCP_SERVER_URL),
        "gdrive_folder": settings.GDRIVE_KNOWLEDGE_FOLDER_PATH,
        "slack_channels": settings.slack_channels_list,
        "status": "ready" if settings.MCP_SERVER_URL else "not_configured"
    }
```

### 4.6 Register Router

In `backend/app/main.py`:

```python
from app.api.v1 import molten_sync

app.include_router(molten_sync.router, prefix="/api/v1")
```

---

## Step 5: Frontend Updates

### 5.1 Expert Review UI for Slack Captures

When experts review fact candidates, show the Slack source context.

In the fact candidate review component, add:

```tsx
{candidate.source_type === 'slack_moltenloris' && (
  <div className="bg-purple-50 border border-purple-200 rounded p-4 mb-4">
    <h4 className="font-semibold text-purple-800 mb-2">
      📱 Captured from Slack
    </h4>
    <p className="text-sm text-gray-600 mb-2">
      Expert <strong>{candidate.metadata?.expert_name}</strong> answered 
      this in <strong>{candidate.metadata?.channel}</strong>
    </p>
    <div className="bg-white rounded p-3 text-sm">
      <p className="font-medium">Question:</p>
      <p className="text-gray-700 mb-2">{candidate.metadata?.question}</p>
      <p className="font-medium">Answer:</p>
      <p className="text-gray-700">{candidate.metadata?.answer}</p>
    </div>
  </div>
)}
```

### 5.2 Admin Settings for MoltenLoris Sync

Add a settings page section for MoltenLoris configuration status:

```tsx
// In admin settings page
const MoltenLorisStatus = () => {
  const { data: status } = useQuery(['molten-status'], getMoltenSyncStatus);
  
  return (
    <div className="border rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">MoltenLoris Integration</h3>
      
      <div className="space-y-3">
        <div className="flex justify-between">
          <span>MCP Server</span>
          <span className={status?.mcp_configured ? 'text-green-600' : 'text-red-600'}>
            {status?.mcp_configured ? '✓ Connected' : '✗ Not configured'}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span>Google Drive Folder</span>
          <span className="text-gray-600">{status?.gdrive_folder || 'Not set'}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Slack Channels</span>
          <span className="text-gray-600">
            {status?.slack_channels?.join(', ') || 'None configured'}
          </span>
        </div>
      </div>
      
      <div className="mt-4 flex gap-2">
        <button 
          onClick={() => triggerSlackScan()}
          className="btn-secondary text-sm"
        >
          Scan Slack Now
        </button>
        <button 
          onClick={() => triggerKnowledgeExport()}
          className="btn-secondary text-sm"
        >
          Export to Drive
        </button>
      </div>
    </div>
  );
};
```

---

## Step 6: Testing

### 6.1 Test MCP Connection

```bash
# Check sync status
curl -s "$BASE/api/v1/molten-sync/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

### 6.2 Test Slack Scan

```bash
# Trigger manual scan
curl -s -X POST "$BASE/api/v1/molten-sync/scan-slack" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

### 6.3 Test Knowledge Export

```bash
# Export all knowledge
curl -s -X POST "$BASE/api/v1/molten-sync/export-knowledge" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Export single category
curl -s -X POST "$BASE/api/v1/molten-sync/export-knowledge?category=contracts" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

### 6.4 End-to-End Test

1. Create a fact in Loris Web App (category: "contracts")
2. Approve the fact (tier_0b)
3. Trigger knowledge export
4. Verify file appears in Google Drive `/Loris-Knowledge/Contracts.md`
5. (Later) Verify MoltenLoris can read and answer questions from this file

---

## Step 7: Final Checklist

### Backend
- [ ] Add MCP config to settings
- [ ] Create MCPClient service
- [ ] Create SlackMonitorService
- [ ] Create KnowledgeExportService
- [ ] Create background jobs
- [ ] Create molten_sync router
- [ ] Register router in main.py
- [ ] Set up job scheduler (APScheduler or cron)

### Frontend
- [ ] Add Slack capture display to fact review
- [ ] Add MoltenLoris status to admin settings
- [ ] Add manual trigger buttons

### Configuration
- [ ] Set MCP_SERVER_URL in .env
- [ ] Set MCP_API_TOKEN in .env
- [ ] Set GDRIVE_KNOWLEDGE_FOLDER_ID in .env
- [ ] Set SLACK_MONITOR_CHANNELS in .env

### Documentation
- [ ] Update CLAUDE.md with Phase 9 details
- [ ] Create MoltenLoris setup guide for end users

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                         SLACK                                    │
│                                                                  │
│  User asks question                                             │
│       ↓                                                         │
│  MoltenLoris answers (or escalates)                             │
│       ↓                                                         │
│  Expert responds (if escalated)                                 │
│                                                                  │
└──────────┬──────────────────────────────────────┬───────────────┘
           │                                      │
      READ/WRITE                             READ-ONLY
      (MoltenLoris)                          (Loris Web App)
           │                                      │
           │                                      ▼
           │                          ┌───────────────────────┐
           │                          │   LORIS WEB APP       │
           │                          │                       │
           │                          │ • Reads expert answers│
           │                          │ • Creates fact        │
           │                          │   candidates          │
           │                          │ • Exports approved    │
           │                          │   knowledge           │
           │                          └───────────┬───────────┘
           │                                      │
           │                                 WRITE-ONLY
           │                                      │
           ▼                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GOOGLE DRIVE                                │
│                    /Loris-Knowledge/                            │
│                                                                  │
│  Contracts.md ←──────────────────────────── Loris writes        │
│  NDA-Guidelines.md                                              │
│  FAQ-Automation-Rules.md                                        │
│       │                                                         │
│       └──────────────────────────────────→ MoltenLoris reads    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**The air gap is maintained:** MoltenLoris and Loris Web App never communicate directly. All sync happens through Slack (observed behavior) and Google Drive (shared files).
