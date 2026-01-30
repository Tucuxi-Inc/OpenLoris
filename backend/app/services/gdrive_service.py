"""
Google Drive service via Zapier MCP.

Provides read/write access to GDrive for knowledge synchronization.
The Loris Web App has read/write access; MoltenLoris has read-only access.
"""

import logging
import httpx
import yaml
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.wisdom import WisdomFact, WisdomTier

logger = logging.getLogger(__name__)


class GDriveService:
    """Google Drive operations via Zapier MCP."""

    def __init__(self, mcp_url: str, timeout: float = 30.0):
        """
        Initialize GDrive service.

        Args:
            mcp_url: Zapier MCP webhook URL
            timeout: Request timeout in seconds
        """
        self.mcp_url = mcp_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a request to the Zapier MCP.

        Args:
            action: The MCP action to perform
            params: Action parameters

        Returns:
            Response data from MCP
        """
        payload = {
            "action": action,
            "params": params or {},
        }

        try:
            response = await self.client.post(
                self.mcp_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GDrive MCP request failed: {e.response.status_code} - {e.response.text}")
            raise GDriveError(f"MCP request failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"GDrive MCP connection error: {e}")
            raise GDriveError(f"Connection error: {str(e)}")

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to GDrive via Zapier MCP.

        Returns:
            Connection status and details
        """
        try:
            result = await self._make_request("test_connection")
            return {
                "connected": True,
                "message": "Connection successful",
                "details": result,
            }
        except GDriveError as e:
            return {
                "connected": False,
                "message": str(e),
                "details": None,
            }

    async def list_folders(self, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available GDrive folders.

        Args:
            parent_id: Optional parent folder ID to list children

        Returns:
            List of folder metadata
        """
        params = {}
        if parent_id:
            params["parent_id"] = parent_id

        result = await self._make_request("list_folders", params)
        return result.get("folders", [])

    async def list_files(
        self,
        folder_id: str,
        file_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List files in a GDrive folder.

        Args:
            folder_id: Folder ID to list files from
            file_type: Optional filter by file type (e.g., "markdown")

        Returns:
            List of file metadata
        """
        params = {"folder_id": folder_id}
        if file_type:
            params["file_type"] = file_type

        result = await self._make_request("list_files", params)
        return result.get("files", [])

    async def read_file(self, file_id: str) -> str:
        """
        Read file content from GDrive.

        Args:
            file_id: File ID to read

        Returns:
            File content as string
        """
        result = await self._make_request("read_file", {"file_id": file_id})
        return result.get("content", "")

    async def write_file(
        self,
        folder_id: str,
        filename: str,
        content: str,
        mime_type: str = "text/markdown",
    ) -> Dict[str, Any]:
        """
        Write/update file in GDrive.

        Args:
            folder_id: Target folder ID
            filename: Name of the file
            content: File content
            mime_type: MIME type of the file

        Returns:
            Created/updated file metadata
        """
        result = await self._make_request(
            "write_file",
            {
                "folder_id": folder_id,
                "filename": filename,
                "content": content,
                "mime_type": mime_type,
            },
        )
        return result

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from GDrive.

        Args:
            file_id: File ID to delete

        Returns:
            True if successful
        """
        result = await self._make_request("delete_file", {"file_id": file_id})
        return result.get("success", False)


class GDriveError(Exception):
    """Exception raised for GDrive operations."""
    pass


# ── Knowledge Sync Functions ─────────────────────────────────────────


def fact_to_markdown(fact: WisdomFact, creator_email: Optional[str] = None) -> str:
    """
    Convert a WisdomFact to markdown with YAML frontmatter.

    Args:
        fact: The WisdomFact to convert
        creator_email: Email of the fact creator

    Returns:
        Markdown string with YAML frontmatter
    """
    # Build frontmatter
    frontmatter = {
        "id": str(fact.id),
        "loris_id": str(fact.id),
        "created_at": fact.created_at.isoformat() if fact.created_at else None,
        "updated_at": fact.updated_at.isoformat() if fact.updated_at else None,
        "created_by": creator_email or "unknown",
        "category": fact.category or "",
        "domain": fact.domain or "",
        "tier": fact.tier.value if fact.tier else "pending",
        "confidence": fact.confidence_score or 0.0,
        "importance": fact.importance or 5,
        "gud_date": fact.gud_date.isoformat() if fact.gud_date else None,
        "tags": fact.tags or [],
        "loris_sync": True,
    }

    # Remove None values
    frontmatter = {k: v for k, v in frontmatter.items() if v is not None}

    # Build markdown
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

    # Use content as both title and body (facts are typically single statements)
    title = fact.content[:80] + "..." if len(fact.content) > 80 else fact.content
    body = fact.content

    return f"---\n{yaml_str}---\n\n# {title}\n\n{body}\n"


def markdown_to_fact_data(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse markdown with YAML frontmatter into fact data.

    Args:
        content: Markdown content with YAML frontmatter

    Returns:
        Dict with fact data, or None if parsing fails
    """
    try:
        # Split frontmatter from content
        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        frontmatter_str = parts[1].strip()
        body = parts[2].strip()

        # Parse YAML frontmatter
        frontmatter = yaml.safe_load(frontmatter_str)
        if not frontmatter:
            return None

        # Extract the actual content (skip the title line if present)
        lines = body.split("\n")
        content_lines = []
        skip_title = True
        for line in lines:
            if skip_title and line.startswith("# "):
                skip_title = False
                continue
            content_lines.append(line)

        fact_content = "\n".join(content_lines).strip()

        # If no content after title, use the full body
        if not fact_content:
            fact_content = body

        return {
            "loris_id": frontmatter.get("loris_id") or frontmatter.get("id"),
            "content": fact_content,
            "category": frontmatter.get("category"),
            "domain": frontmatter.get("domain"),
            "tier": frontmatter.get("tier", "pending"),
            "confidence": frontmatter.get("confidence", 0.0),
            "importance": frontmatter.get("importance", 5),
            "gud_date": frontmatter.get("gud_date"),
            "tags": frontmatter.get("tags", []),
            "created_by": frontmatter.get("created_by"),
        }
    except Exception as e:
        logger.error(f"Failed to parse markdown: {e}")
        return None


async def sync_knowledge_to_drive(
    org_id: UUID,
    db: AsyncSession,
    gdrive: GDriveService,
    folder_id: str,
) -> Dict[str, Any]:
    """
    Export WisdomFacts to GDrive as markdown files.

    Args:
        org_id: Organization ID
        db: Database session
        gdrive: GDrive service instance
        folder_id: Target GDrive folder ID

    Returns:
        Sync results (exported count, errors, etc.)
    """
    from app.models.user import User

    # Get all active facts for the organization
    result = await db.execute(
        select(WisdomFact)
        .where(WisdomFact.organization_id == org_id)
        .where(WisdomFact.tier != WisdomTier.ARCHIVED)
    )
    facts = result.scalars().all()

    exported = 0
    errors = []

    for fact in facts:
        try:
            # Get creator email
            creator_email = None
            if fact.created_by:
                user_result = await db.execute(
                    select(User).where(User.id == fact.created_by)
                )
                creator = user_result.scalar_one_or_none()
                if creator:
                    creator_email = creator.email

            # Convert to markdown
            markdown = fact_to_markdown(fact, creator_email)

            # Generate filename from ID
            filename = f"fact-{str(fact.id)[:8]}.md"

            # Write to GDrive
            await gdrive.write_file(folder_id, filename, markdown)
            exported += 1

        except Exception as e:
            logger.error(f"Failed to export fact {fact.id}: {e}")
            errors.append({"fact_id": str(fact.id), "error": str(e)})

    return {
        "exported": exported,
        "total": len(facts),
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def import_from_drive(
    org_id: UUID,
    db: AsyncSession,
    gdrive: GDriveService,
    folder_id: str,
    created_by: UUID,
) -> Dict[str, Any]:
    """
    Import markdown files from GDrive as WisdomFacts.

    Only imports files that don't already exist in the database.

    Args:
        org_id: Organization ID
        db: Database session
        gdrive: GDrive service instance
        folder_id: Source GDrive folder ID
        created_by: User ID to attribute imported facts to

    Returns:
        Import results (imported count, skipped, errors, etc.)
    """
    # List markdown files in folder
    files = await gdrive.list_files(folder_id, file_type="markdown")

    imported = 0
    skipped = 0
    errors = []

    for file_info in files:
        try:
            file_id = file_info.get("id")
            if not file_id:
                continue

            # Read file content
            content = await gdrive.read_file(file_id)
            if not content:
                continue

            # Parse markdown
            fact_data = markdown_to_fact_data(content)
            if not fact_data:
                errors.append({
                    "file": file_info.get("name", file_id),
                    "error": "Failed to parse markdown",
                })
                continue

            # Check if fact already exists (by loris_id)
            loris_id = fact_data.get("loris_id")
            if loris_id:
                existing = await db.execute(
                    select(WisdomFact).where(WisdomFact.id == loris_id)
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

            # Create new fact
            tier_str = fact_data.get("tier", "pending")
            try:
                tier = WisdomTier(tier_str)
            except ValueError:
                tier = WisdomTier.PENDING

            gud_date = None
            if fact_data.get("gud_date"):
                try:
                    gud_date = datetime.fromisoformat(fact_data["gud_date"]).date()
                except (ValueError, TypeError):
                    pass

            new_fact = WisdomFact(
                organization_id=org_id,
                content=fact_data["content"],
                category=fact_data.get("category"),
                domain=fact_data.get("domain"),
                tier=tier,
                confidence_score=fact_data.get("confidence", 0.0),
                importance=fact_data.get("importance", 5),
                gud_date=gud_date,
                tags=fact_data.get("tags", []),
                created_by=created_by,
                source="gdrive_import",
            )

            db.add(new_fact)
            imported += 1

        except Exception as e:
            logger.error(f"Failed to import file {file_info.get('name', 'unknown')}: {e}")
            errors.append({
                "file": file_info.get("name", "unknown"),
                "error": str(e),
            })

    await db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "total_files": len(files),
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Factory Function ─────────────────────────────────────────────────


async def get_gdrive_service(org: Organization) -> Optional[GDriveService]:
    """
    Get a GDrive service instance for an organization.

    Args:
        org: Organization with GDrive settings

    Returns:
        GDriveService instance, or None if not configured
    """
    settings = org.settings or {}
    gdrive_settings = settings.get("gdrive", {})

    if not gdrive_settings.get("enabled"):
        return None

    mcp_url = gdrive_settings.get("zapier_mcp_url")
    if not mcp_url:
        return None

    return GDriveService(mcp_url)
