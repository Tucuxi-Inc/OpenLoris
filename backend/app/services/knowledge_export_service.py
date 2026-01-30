"""
Knowledge Export Service.

Exports approved knowledge from Loris to Google Drive for MoltenLoris consumption.
Knowledge is exported as markdown files following the Loris Knowledge File Format
Specification (v1.0) with YAML frontmatter and hidden metadata.

This is write-only to GDrive - MoltenLoris reads from GDrive via a separate MCP server.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mcp_client import get_mcp_client
from app.models.wisdom import WisdomFact, WisdomTier
from app.models.automation import AutomationRule
from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeExportService:
    """Service to export knowledge to Google Drive for MoltenLoris."""

    def __init__(self, db: AsyncSession, organization_id: UUID):
        self.db = db
        self.organization_id = organization_id

    async def is_gdrive_sync_enabled(self) -> bool:
        """Check if GDrive sync is enabled for this organization."""
        from app.models.organization import Organization

        result = await self.db.execute(
            select(Organization).where(Organization.id == self.organization_id)
        )
        org = result.scalar_one_or_none()
        if not org:
            return False

        settings = org.settings or {}
        # GDrive settings are stored at org.settings["gdrive"]
        gdrive_settings = settings.get("gdrive", {})
        return gdrive_settings.get("enabled", False)

    async def export_category(
        self,
        category: str,
        subcategory: str = "General",
        subdomain_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Export all approved knowledge for a category to Google Drive.

        Creates/updates a markdown file in the Loris-Knowledge folder
        following the Loris Knowledge File Format Specification.

        Args:
            category: Knowledge category to export
            subcategory: Subcategory (default "General")
            subdomain_id: Optional subdomain filter

        Returns:
            Export result with status and metadata
        """
        # Fetch approved facts for this category
        query = select(WisdomFact).where(
            and_(
                WisdomFact.organization_id == self.organization_id,
                WisdomFact.category == category,
                WisdomFact.tier.in_([
                    WisdomTier.TIER_0A,
                    WisdomTier.TIER_0B,
                    WisdomTier.TIER_0C
                ]),
                WisdomFact.is_active == True
            )
        )
        if subdomain_id:
            query = query.where(WisdomFact.subdomain_id == subdomain_id)

        result = await self.db.execute(query)
        facts = list(result.scalars().all())

        # Fetch automation rules for FAQ
        rule_query = select(AutomationRule).where(
            and_(
                AutomationRule.organization_id == self.organization_id,
                AutomationRule.is_enabled == True
            )
        )
        rule_result = await self.db.execute(rule_query)
        rules = list(rule_result.scalars().all())

        if not facts and not rules:
            return {
                "status": "no_content",
                "category": category,
                "fact_count": 0,
                "rule_count": 0
            }

        # Generate content in Loris format
        content = self._generate_knowledge_file(
            category=category,
            subcategory=subcategory,
            facts=facts,
            qa_pairs=rules,
            subdomain_id=subdomain_id
        )

        # Generate filename
        filename = self._generate_filename(category, subcategory)

        # Check if GDrive sync is enabled
        if not await self.is_gdrive_sync_enabled():
            return {
                "status": "skipped",
                "category": category,
                "message": "GDrive sync is not enabled"
            }

        # Write to Google Drive via MCP
        mcp = await get_mcp_client()
        if not mcp.is_configured:
            return {
                "status": "error",
                "category": category,
                "message": "MCP client not configured"
            }

        try:
            file_result = await mcp.gdrive_create_document(
                title=filename,
                content=content
            )

            return {
                "status": "exported",
                "category": category,
                "subcategory": subcategory,
                "fact_count": len(facts),
                "rule_count": len(rules),
                "filename": filename,
                "gdrive_url": file_result.get("results", {}).get("url"),
            }
        except Exception as e:
            logger.error(f"Failed to export category {category}: {e}")
            return {
                "status": "error",
                "category": category,
                "message": str(e)
            }

    async def export_all_knowledge(self) -> List[Dict[str, Any]]:
        """
        Export all approved knowledge categories to Google Drive.

        Returns:
            List of export results for each category
        """
        # Get distinct categories
        result = await self.db.execute(
            select(WisdomFact.category)
            .where(
                and_(
                    WisdomFact.organization_id == self.organization_id,
                    WisdomFact.is_active == True,
                    WisdomFact.tier.in_([
                        WisdomTier.TIER_0A,
                        WisdomTier.TIER_0B,
                        WisdomTier.TIER_0C
                    ])
                )
            )
            .distinct()
        )
        categories = [row[0] for row in result.fetchall() if row[0]]

        results = []

        # Export each category
        for category in categories:
            result = await self.export_category(category)
            results.append(result)

        # Also export FAQ if no categories but rules exist
        if not categories:
            faq_result = await self._export_faq_only()
            if faq_result.get("status") == "exported":
                results.append(faq_result)

        # Update the inventory/index file for MoltenLoris
        await self._update_knowledge_index(results)

        return results

    async def _export_faq_only(self) -> Dict[str, Any]:
        """Export automation rules as a standalone FAQ document."""
        result = await self.db.execute(
            select(AutomationRule).where(
                and_(
                    AutomationRule.organization_id == self.organization_id,
                    AutomationRule.is_enabled == True
                )
            )
        )
        rules = list(result.scalars().all())

        if not rules:
            return {"status": "no_rules", "category": "FAQ", "rule_count": 0}

        content = self._generate_knowledge_file(
            category="FAQ",
            subcategory="General",
            facts=[],
            qa_pairs=rules
        )

        # Check if GDrive sync is enabled
        if not await self.is_gdrive_sync_enabled():
            return {"status": "skipped", "message": "GDrive sync not enabled"}

        mcp = await get_mcp_client()
        if not mcp.is_configured:
            return {"status": "error", "message": "MCP not configured"}

        try:
            file_result = await mcp.gdrive_create_document(
                title="FAQ-General",
                content=content
            )
            return {
                "status": "exported",
                "category": "FAQ",
                "rule_count": len(rules),
                "filename": "FAQ-General",
                "gdrive_url": file_result.get("results", {}).get("url")
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _generate_knowledge_file(
        self,
        category: str,
        subcategory: str,
        facts: List[WisdomFact],
        qa_pairs: List[AutomationRule],
        subdomain_id: Optional[UUID] = None
    ) -> str:
        """
        Generate a knowledge file in Loris format.

        Follows the Loris Knowledge File Format Specification v1.0.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        now_human = now.strftime('%B %d, %Y at %I:%M %p UTC')

        # Separate facts by tier
        tier_0a = [f for f in facts if f.tier == WisdomTier.TIER_0A]
        tier_0b = [f for f in facts if f.tier == WisdomTier.TIER_0B]
        tier_0c = [f for f in facts if f.tier == WisdomTier.TIER_0C]

        # Build content sections (will calculate checksum after)
        sections = []

        # Header block
        sections.append(f"# {category}: {subcategory}")
        sections.append("")
        sections.append(f"> **Last Updated:** {now_human}")
        sections.append("> **Source:** Loris Knowledge Base")
        sections.append("> **Confidence Level:** This document contains verified organizational knowledge.")
        sections.append("")
        sections.append("---")
        sections.append("")

        # Quick Facts (Tier 0a and 0b)
        sections.append("## Quick Facts")
        sections.append("")
        quick_facts = tier_0a + tier_0b
        if quick_facts:
            for fact in quick_facts[:20]:  # Limit to 20 quick facts
                content = fact.content.replace("\n", " ").strip()
                if len(content) > 150:
                    content = content[:147] + "..."
                sections.append(f"- {content}")
        else:
            sections.append("_No quick facts available for this category._")
        sections.append("")
        sections.append("---")
        sections.append("")

        # Detailed Knowledge (Tier 0c and longer content)
        sections.append("## Detailed Knowledge")
        sections.append("")
        if tier_0c:
            for fact in tier_0c:
                sections.append(fact.content)
                if fact.source:
                    sections.append(f"_Source: {fact.source}_")
                sections.append("")
        else:
            sections.append("_See Quick Facts above for available knowledge._")
        sections.append("")
        sections.append("---")
        sections.append("")

        # FAQ Section
        sections.append("## Frequently Asked Questions")
        sections.append("")
        if qa_pairs:
            for rule in qa_pairs:
                sections.append(f"**Q: {rule.canonical_question}**")
                sections.append("")
                sections.append(f"A: {rule.canonical_answer}")
                sections.append("")
                sections.append(f"_Source: Automation Rule | Confidence: {int(rule.similarity_threshold * 100)}%_")
                sections.append("")
                sections.append("---")
                sections.append("")
        else:
            sections.append("_No FAQs available for this category._")
            sections.append("")
            sections.append("---")
            sections.append("")

        # Related Topics (placeholder)
        sections.append("## Related Topics")
        sections.append("")
        sections.append("_Related knowledge files will be linked here as they are created._")
        sections.append("")
        sections.append("---")
        sections.append("")

        # Build content body (for checksum calculation)
        content_body = "\n".join(sections)

        # Calculate checksum
        checksum = hashlib.md5(content_body.encode()).hexdigest()[:24]

        # Build frontmatter
        frontmatter_lines = [
            "---",
            "loris_version: 1.0",
            f'category: "{category}"',
            f'subcategory: "{subcategory}"',
            f'organization_id: "{self.organization_id}"',
            f'subdomain_id: "{subdomain_id or ""}"',
            f'exported_at: "{now_iso}"',
            'exported_by: "loris-web-app"',
            f"fact_count: {len(facts)}",
            f"qa_count: {len(qa_pairs)}",
            f"rule_count: {len(qa_pairs)}",
            f'checksum: "{checksum}"',
            "---",
            ""
        ]

        # Build hidden metadata
        metadata = {
            "facts": [
                {
                    "id": str(f.id),
                    "content": f.content[:200],
                    "tier": f.tier.value if hasattr(f.tier, 'value') else str(f.tier),
                    "confidence": getattr(f, 'confidence', 0.9),
                    "category": f.category,
                    "created_at": f.created_at.isoformat() if f.created_at else None
                }
                for f in facts
            ],
            "qa_pairs": [
                {
                    "id": str(r.id),
                    "question_pattern": r.canonical_question[:100],
                    "confidence": r.similarity_threshold,
                    "times_used": r.times_triggered
                }
                for r in qa_pairs
            ]
        }

        metadata_section = [
            "<!-- LORIS_METADATA_START",
            json.dumps(metadata, indent=2),
            "LORIS_METADATA_END -->"
        ]

        # Combine all parts
        full_content = "\n".join(frontmatter_lines) + content_body + "\n".join(metadata_section)

        return full_content

    def _generate_filename(self, category: str, subcategory: str) -> str:
        """Generate filename following naming convention."""
        # Sanitize and format
        cat = category.replace(" ", "-").replace("_", "-").title()
        sub = subcategory.replace(" ", "-").replace("_", "-").title()

        # Remove double dashes
        cat = "-".join(filter(None, cat.split("-")))
        sub = "-".join(filter(None, sub.split("-")))

        if sub.lower() == "general":
            return f"{cat}"
        return f"{cat}-{sub}"

    async def _update_knowledge_index(self, export_results: List[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Update the Loris-Knowledge-Index file by scanning the actual folder contents.

        Scans the Google Drive folder to find all files and builds a complete index.
        This ensures the index reflects what's actually in the folder, including
        manually added files like skills documents.

        Args:
            export_results: Optional results from recent export operations (for metadata)

        Returns:
            Result of index file update, or None if failed
        """
        # Check if GDrive sync is enabled
        if not await self.is_gdrive_sync_enabled():
            logger.info("GDrive sync not enabled, skipping index update")
            return None

        mcp = await get_mcp_client()
        if not mcp.is_configured:
            return None

        now = datetime.now(timezone.utc)
        now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        now_human = now.strftime('%B %d, %Y at %I:%M %p UTC')

        # Scan the folder to get all files
        try:
            all_files = await mcp.gdrive_list_folder()
        except Exception as e:
            logger.error(f"Failed to scan GDrive folder: {e}")
            all_files = []

        # Build export results lookup for metadata
        export_lookup = {}
        if export_results:
            for r in export_results:
                if r.get("status") == "exported":
                    export_lookup[r.get("filename", "")] = r

        # Get documents from database for GUD info
        from app.models.documents import KnowledgeDocument
        doc_result = await self.db.execute(
            select(KnowledgeDocument).where(
                and_(
                    KnowledgeDocument.organization_id == self.organization_id,
                    KnowledgeDocument.is_active == True
                )
            )
        )
        db_documents = {d.title or d.original_filename: d for d in doc_result.scalars().all()}

        # Categorize files
        index_files = []
        knowledge_files = []
        skills_files = []
        document_files = []
        other_files = []

        for f in all_files:
            title = f.get("title", "")
            if title.startswith("_"):
                index_files.append(f)
            elif title.startswith("DOC-"):
                document_files.append(f)
            elif "SKILL" in title.upper() or title.endswith(".md"):
                skills_files.append(f)
            elif title in export_lookup or title == "Accumulated_Wisdom" or title == "FAQ-General":
                knowledge_files.append(f)
            else:
                other_files.append(f)

        # Build the index content
        lines = [
            "---",
            "loris_version: 1.0",
            "document_type: index",
            f'updated_at: "{now_iso}"',
            f"total_files: {len(all_files)}",
            "---",
            "",
            "# Loris Knowledge Index",
            "",
            f"> **Last Updated:** {now_human}",
            f"> **Total Files:** {len(all_files)}",
            "> **Purpose:** Complete directory of all files in the Loris-Knowledge folder.",
            "",
            "---",
            "",
        ]

        # Knowledge Files Section
        lines.append("## Knowledge Files")
        lines.append("")
        if knowledge_files:
            for f in knowledge_files:
                title = f.get("title", "Unknown")
                url = f.get("url", "")
                meta = export_lookup.get(title, {})

                lines.append(f"### {title}")
                lines.append("")
                if meta:
                    lines.append(f"- **Category:** {meta.get('category', 'General')}")
                    lines.append(f"- **Facts:** {meta.get('fact_count', 0)}")
                    lines.append(f"- **FAQ Entries:** {meta.get('rule_count', 0)}")
                lines.append(f"- **URL:** {url}")
                lines.append("")
        else:
            lines.append("_No knowledge files exported yet._")
            lines.append("")

        # Source Documents Section
        lines.append("---")
        lines.append("")
        lines.append("## Source Documents")
        lines.append("")
        lines.append("Documents uploaded to Loris for knowledge extraction.")
        lines.append("")
        if document_files:
            for f in document_files:
                title = f.get("title", "Unknown")
                url = f.get("url", "")
                # Try to find GUD from database
                doc_name = title.replace("DOC-", "")
                db_doc = db_documents.get(doc_name)
                gud_str = "Unknown"
                if db_doc:
                    if db_doc.is_perpetual:
                        gud_str = "Perpetual"
                    elif db_doc.good_until_date:
                        gud_str = db_doc.good_until_date.isoformat()
                lines.append(f"- **{title}**")
                lines.append(f"  - GUD: {gud_str}")
                lines.append(f"  - URL: {url}")
                lines.append("")
        else:
            lines.append("_No source documents uploaded._")
            lines.append("")

        # Skills Files Section
        lines.append("---")
        lines.append("")
        lines.append("## Skills & Reference Files")
        lines.append("")
        if skills_files:
            for f in skills_files:
                title = f.get("title", "Unknown")
                url = f.get("url", "")
                lines.append(f"- **{title}** — {url}")
        else:
            lines.append("_No skills files found._")
        lines.append("")

        # Other Files Section
        if other_files:
            lines.append("---")
            lines.append("")
            lines.append("## Other Files")
            lines.append("")
            for f in other_files:
                title = f.get("title", "Unknown")
                url = f.get("url", "")
                lines.append(f"- **{title}** — {url}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## How to Use",
            "",
            "1. **Knowledge Files** contain Quick Facts, Detailed Knowledge, and FAQs by category",
            "2. **Skills Files** contain reasoning skills and capabilities",
            "3. Check the `updated_at` timestamp in each file's frontmatter for freshness",
            "4. This index is automatically updated when knowledge is exported",
            "",
            "---",
            "",
            f"_Index generated by Loris Web App on {now_human}_",
        ])

        content = "\n".join(lines)

        try:
            result = await mcp.gdrive_update_document(
                document_name="_Loris-Knowledge-Index",
                content=content
            )
            logger.info(f"Updated knowledge index with {len(all_files)} files")
            return result
        except Exception as e:
            logger.error(f"Failed to update knowledge index: {e}")
            return None

    async def refresh_knowledge_index(self) -> Optional[Dict[str, Any]]:
        """
        Manually refresh the knowledge index by scanning the folder.

        Call this to update the index without exporting knowledge.

        Returns:
            Result of index file update, or None if failed
        """
        return await self._update_knowledge_index()

    async def get_export_status(self) -> Dict[str, Any]:
        """Get current export status and statistics."""
        # Count facts by category
        result = await self.db.execute(
            select(WisdomFact.category)
            .where(
                and_(
                    WisdomFact.organization_id == self.organization_id,
                    WisdomFact.is_active == True,
                    WisdomFact.tier.in_([
                        WisdomTier.TIER_0A,
                        WisdomTier.TIER_0B,
                        WisdomTier.TIER_0C
                    ])
                )
            )
        )
        facts = result.fetchall()

        # Count by category
        category_counts: Dict[str, int] = {}
        for row in facts:
            cat = row[0] or "uncategorized"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Count automation rules
        rule_result = await self.db.execute(
            select(AutomationRule).where(
                and_(
                    AutomationRule.organization_id == self.organization_id,
                    AutomationRule.is_enabled == True
                )
            )
        )
        rules = list(rule_result.scalars().all())

        return {
            "total_facts": len(facts),
            "categories": category_counts,
            "automation_rules": len(rules),
            "gdrive_folder": settings.GDRIVE_KNOWLEDGE_FOLDER_PATH,
            "mcp_configured": bool(settings.MCP_SERVER_URL),
        }

    async def upload_document_to_gdrive(
        self,
        document_title: str,
        document_content: str,
        good_until_date: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a document to Google Drive for MoltenLoris to access.

        Args:
            document_title: Title for the document (will be used as filename)
            document_content: The document content to upload
            good_until_date: Optional GUD date string
            domain: Optional domain/category

        Returns:
            Upload result with URL, or None if failed
        """
        # Check if GDrive sync is enabled
        if not await self.is_gdrive_sync_enabled():
            logger.info("GDrive sync not enabled, skipping document upload")
            return None

        mcp = await get_mcp_client()
        if not mcp.is_configured:
            logger.warning("MCP not configured, skipping GDrive upload")
            return None

        # Sanitize title for filename
        safe_title = document_title.replace(" ", "-").replace("/", "-")
        safe_title = "".join(c for c in safe_title if c.isalnum() or c in "-_.")

        try:
            result = await mcp.gdrive_create_document(
                title=safe_title,
                content=document_content
            )
            logger.info(f"Uploaded document to GDrive: {safe_title}")

            # Update the index to include this document
            await self._update_knowledge_index()

            return result
        except Exception as e:
            logger.error(f"Failed to upload document to GDrive: {e}")
            return None

    async def sync_document_to_gdrive(
        self,
        doc_id: UUID,
        doc_title: str,
        doc_content: str,
        good_until_date: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Sync a Loris document to Google Drive.

        Called after document parsing is complete.

        Args:
            doc_id: Document ID in Loris
            doc_title: Document title
            doc_content: Parsed document content
            good_until_date: GUD date string
            domain: Document domain

        Returns:
            Upload result or None
        """
        # Check if GDrive sync is enabled
        if not await self.is_gdrive_sync_enabled():
            logger.info("GDrive sync not enabled, skipping document sync")
            return None

        mcp = await get_mcp_client()
        if not mcp.is_configured:
            return None

        now = datetime.now(timezone.utc)
        now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Build document with frontmatter
        lines = [
            "---",
            "loris_version: 1.0",
            "document_type: source_document",
            f'document_id: "{doc_id}"',
            f'title: "{doc_title}"',
            f'domain: "{domain or "General"}"',
            f'good_until_date: "{good_until_date or ""}"',
            f'synced_at: "{now_iso}"',
            "source: loris_web_app",
            "---",
            "",
            f"# {doc_title}",
            "",
            doc_content
        ]

        content = "\n".join(lines)
        safe_title = doc_title.replace(" ", "-").replace("/", "-")[:50]

        try:
            result = await mcp.gdrive_create_document(
                title=f"DOC-{safe_title}",
                content=content
            )
            logger.info(f"Synced document {doc_id} to GDrive")
            return result
        except Exception as e:
            logger.error(f"Failed to sync document to GDrive: {e}")
            return None

    async def export_accumulated_wisdom(self) -> Optional[Dict[str, Any]]:
        """
        Export all expert-approved WisdomFacts to an Accumulated_Wisdom file.

        This file contains knowledge that has been validated by experts,
        either from document extraction or from expert answers.

        Returns:
            Export result or None
        """
        from app.models.documents import KnowledgeDocument

        # Check if GDrive sync is enabled
        if not await self.is_gdrive_sync_enabled():
            logger.info("GDrive sync not enabled, skipping accumulated wisdom export")
            return {"status": "skipped", "message": "GDrive sync not enabled"}

        mcp = await get_mcp_client()
        if not mcp.is_configured:
            return None

        # Get all approved facts (tier 0a, 0b, 0c)
        result = await self.db.execute(
            select(WisdomFact).where(
                and_(
                    WisdomFact.organization_id == self.organization_id,
                    WisdomFact.is_active == True,
                    WisdomFact.tier.in_([
                        WisdomTier.TIER_0A,
                        WisdomTier.TIER_0B,
                        WisdomTier.TIER_0C
                    ])
                )
            ).order_by(WisdomFact.created_at.desc())
        )
        facts = list(result.scalars().all())

        if not facts:
            return {"status": "no_content", "fact_count": 0}

        now = datetime.now(timezone.utc)
        now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        now_human = now.strftime('%B %d, %Y at %I:%M %p UTC')

        # Build the Accumulated Wisdom file
        lines = [
            "---",
            "loris_version: 1.0",
            "document_type: accumulated_wisdom",
            f'organization_id: "{self.organization_id}"',
            f'exported_at: "{now_iso}"',
            f"fact_count: {len(facts)}",
            "---",
            "",
            "# Accumulated Wisdom",
            "",
            f"> **Last Updated:** {now_human}",
            f"> **Total Facts:** {len(facts)}",
            "> **Source:** Expert-validated knowledge from Loris",
            "",
            "---",
            "",
        ]

        # Group by tier
        tier_0a = [f for f in facts if f.tier == WisdomTier.TIER_0A]
        tier_0b = [f for f in facts if f.tier == WisdomTier.TIER_0B]
        tier_0c = [f for f in facts if f.tier == WisdomTier.TIER_0C]

        # Authoritative Knowledge (Tier 0A)
        lines.append("## Authoritative Knowledge")
        lines.append("")
        if tier_0a:
            for fact in tier_0a:
                gud_str = fact.good_until_date.isoformat() if fact.good_until_date else "Perpetual"
                lines.append(f"### {fact.summary or fact.content[:50]}...")
                lines.append("")
                lines.append(fact.content)
                lines.append("")
                lines.append(f"_Domain: {fact.domain or 'General'} | GUD: {gud_str}_")
                lines.append("")
        else:
            lines.append("_No authoritative knowledge entries._")
            lines.append("")

        # Expert-Validated (Tier 0B)
        lines.append("---")
        lines.append("")
        lines.append("## Expert-Validated Knowledge")
        lines.append("")
        if tier_0b:
            for fact in tier_0b:
                gud_str = fact.good_until_date.isoformat() if fact.good_until_date else "Perpetual"
                lines.append(f"- **{fact.content[:150]}{'...' if len(fact.content) > 150 else ''}**")
                lines.append(f"  - _Domain: {fact.domain or 'General'} | GUD: {gud_str}_")
                lines.append("")
        else:
            lines.append("_No expert-validated entries._")
            lines.append("")

        # AI-Generated/Extracted (Tier 0C)
        lines.append("---")
        lines.append("")
        lines.append("## Extracted Knowledge")
        lines.append("")
        if tier_0c:
            for fact in tier_0c:
                gud_str = fact.good_until_date.isoformat() if fact.good_until_date else "Perpetual"
                lines.append(f"- {fact.content[:200]}{'...' if len(fact.content) > 200 else ''}")
                lines.append(f"  - _GUD: {gud_str}_")
                lines.append("")
        else:
            lines.append("_No extracted knowledge entries._")
            lines.append("")

        lines.extend([
            "---",
            "",
            f"_Generated by Loris Web App on {now_human}_",
        ])

        content = "\n".join(lines)

        try:
            result = await mcp.gdrive_update_document(
                document_name="Accumulated_Wisdom",
                content=content
            )
            logger.info(f"Exported {len(facts)} facts to Accumulated_Wisdom - raw result: {result}")

            # Extract URL from various possible response formats
            url = None
            if result:
                # Try different paths where URL might be
                url = (
                    result.get("results", {}).get("url") or
                    result.get("url") or
                    result.get("results", {}).get("documentUrl") or
                    result.get("documentUrl")
                )

            return {
                "status": "exported",
                "fact_count": len(facts),
                "url": url,
                "raw_result": result  # Include for debugging
            }
        except Exception as e:
            logger.error(f"Failed to export accumulated wisdom: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
