"""
SOUL File Generation Service

Generates SOUL (Semantic Operational Understanding Layer) configuration
files for MoltenLoris from an organization's knowledge base.

The SOUL file provides MoltenLoris with the context it needs to answer
questions accurately based on the organization's validated knowledge.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.wisdom import WisdomFact, WisdomTier
from app.models.automation import AutomationRule
from app.models.subdomain import SubDomain


class SoulGenerationService:
    """
    Service for generating SOUL configuration files.

    SOUL files are markdown documents that configure MoltenLoris
    with organization-specific knowledge and answering guidelines.
    """

    # Template for the SOUL file
    SOUL_TEMPLATE = '''# {org_name} - Knowledge Base SOUL File

> Generated: {generated_at}
> Organization: {org_name}

## About This File

This SOUL (Semantic Operational Understanding Layer) file configures MoltenLoris
with your organization's validated knowledge. Use this to help the bot provide
accurate, consistent answers based on your knowledge base.

## Organization Context

**Name:** {org_name}
**Domain:** {org_domain}
**Sub-Domains:** {subdomain_list}

---

## Core Knowledge (Tier 0A - Authoritative)

These are your organization's most authoritative facts. MoltenLoris should treat
these as ground truth and never contradict them.

{tier_0a_facts}

---

## Expert-Validated Knowledge (Tier 0B)

These facts have been validated by domain experts. High confidence.

{tier_0b_facts}

---

## AI-Generated Knowledge (Tier 0C)

These facts were extracted by AI and should be used with moderate confidence.
They may need expert review.

{tier_0c_facts}

---

## Automation Rules

These are pre-defined Q&A pairs that should be used when questions match closely.

{automation_rules}

---

## Answering Guidelines

1. **Cite your sources**: When using knowledge facts, indicate which fact supports your answer.
2. **Confidence thresholds**: Only auto-answer with confidence >= 0.8. Lower confidence should route to experts.
3. **Stay in scope**: Only answer questions related to the knowledge base. Route out-of-scope questions to experts.
4. **Be concise**: Provide clear, direct answers without unnecessary elaboration.
5. **Acknowledge uncertainty**: If the knowledge base doesn't fully cover a topic, say so.

---

## Sub-Domain Routing

When questions fall outside the main knowledge base, route to the appropriate sub-domain:

{subdomain_routing}

---

## Statistics

- **Total Facts:** {total_facts}
- **Tier 0A (Authoritative):** {tier_0a_count}
- **Tier 0B (Expert-Validated):** {tier_0b_count}
- **Tier 0C (AI-Generated):** {tier_0c_count}
- **Active Automation Rules:** {rule_count}
- **Active Sub-Domains:** {subdomain_count}

---

*This file is auto-generated from the Loris knowledge base. Update your knowledge base to refresh this configuration.*
'''

    async def generate_soul_file(
        self,
        organization_id: UUID,
        db: AsyncSession,
    ) -> str:
        """
        Generate a SOUL configuration file for an organization.

        Args:
            organization_id: The organization to generate for
            db: Database session

        Returns:
            The generated SOUL file as a string
        """
        # Get organization
        org_result = await db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = org_result.scalar_one_or_none()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        # Get facts by tier
        tier_0a_facts = await self._get_facts_by_tier(
            db, organization_id, WisdomTier.TIER_0A, limit=50
        )
        tier_0b_facts = await self._get_facts_by_tier(
            db, organization_id, WisdomTier.TIER_0B, limit=100
        )
        tier_0c_facts = await self._get_facts_by_tier(
            db, organization_id, WisdomTier.TIER_0C, limit=50
        )

        # Get automation rules
        rules = await self._get_automation_rules(db, organization_id, limit=50)

        # Get sub-domains
        subdomains = await self._get_subdomains(db, organization_id)

        # Get stats
        stats = await self._get_stats(db, organization_id)

        # Format the SOUL file
        return self.SOUL_TEMPLATE.format(
            org_name=org.name,
            org_domain=org.domain or "Not specified",
            generated_at=datetime.now(timezone.utc).isoformat(),
            subdomain_list=", ".join(s["name"] for s in subdomains) or "None",
            tier_0a_facts=self._format_facts(tier_0a_facts),
            tier_0b_facts=self._format_facts(tier_0b_facts),
            tier_0c_facts=self._format_facts(tier_0c_facts),
            automation_rules=self._format_rules(rules),
            subdomain_routing=self._format_subdomain_routing(subdomains),
            total_facts=stats["total_facts"],
            tier_0a_count=stats["tier_0a"],
            tier_0b_count=stats["tier_0b"],
            tier_0c_count=stats["tier_0c"],
            rule_count=stats["active_rules"],
            subdomain_count=stats["active_subdomains"],
        )

    async def _get_facts_by_tier(
        self,
        db: AsyncSession,
        organization_id: UUID,
        tier: WisdomTier,
        limit: int = 50,
    ) -> list[dict]:
        """Get facts of a specific tier, ordered by confidence."""
        result = await db.execute(
            select(WisdomFact)
            .where(
                WisdomFact.organization_id == organization_id,
                WisdomFact.tier == tier,
                WisdomFact.is_active == True,
            )
            .order_by(WisdomFact.confidence_score.desc())
            .limit(limit)
        )
        facts = result.scalars().all()
        return [
            {
                "id": str(f.id),
                "content": f.content,
                "category": f.category,
                "domain": f.domain,
                "confidence": f.confidence_score,
            }
            for f in facts
        ]

    async def _get_automation_rules(
        self,
        db: AsyncSession,
        organization_id: UUID,
        limit: int = 50,
    ) -> list[dict]:
        """Get active automation rules."""
        result = await db.execute(
            select(AutomationRule)
            .where(
                AutomationRule.organization_id == organization_id,
                AutomationRule.is_enabled == True,
            )
            .order_by(AutomationRule.times_triggered.desc())
            .limit(limit)
        )
        rules = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "question": r.canonical_question,
                "answer": r.canonical_answer,
                "threshold": r.similarity_threshold,
                "triggered": r.times_triggered,
                "accepted": r.times_accepted,
            }
            for r in rules
        ]

    async def _get_subdomains(
        self,
        db: AsyncSession,
        organization_id: UUID,
    ) -> list[dict]:
        """Get active sub-domains."""
        result = await db.execute(
            select(SubDomain)
            .where(
                SubDomain.organization_id == organization_id,
                SubDomain.is_active == True,
            )
            .order_by(SubDomain.name)
        )
        subdomains = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "keywords": s.keywords or [],
            }
            for s in subdomains
        ]

    async def _get_stats(
        self,
        db: AsyncSession,
        organization_id: UUID,
    ) -> dict:
        """Get knowledge base statistics."""
        # Count facts by tier
        fact_counts = {}
        for tier in [WisdomTier.TIER_0A, WisdomTier.TIER_0B, WisdomTier.TIER_0C]:
            result = await db.execute(
                select(func.count(WisdomFact.id))
                .where(
                    WisdomFact.organization_id == organization_id,
                    WisdomFact.tier == tier,
                    WisdomFact.is_active == True,
                )
            )
            fact_counts[tier.value] = result.scalar() or 0

        # Total facts
        total_result = await db.execute(
            select(func.count(WisdomFact.id))
            .where(
                WisdomFact.organization_id == organization_id,
                WisdomFact.is_active == True,
            )
        )
        total_facts = total_result.scalar() or 0

        # Count active rules
        rule_result = await db.execute(
            select(func.count(AutomationRule.id))
            .where(
                AutomationRule.organization_id == organization_id,
                AutomationRule.is_enabled == True,
            )
        )
        active_rules = rule_result.scalar() or 0

        # Count active subdomains
        subdomain_result = await db.execute(
            select(func.count(SubDomain.id))
            .where(
                SubDomain.organization_id == organization_id,
                SubDomain.is_active == True,
            )
        )
        active_subdomains = subdomain_result.scalar() or 0

        return {
            "total_facts": total_facts,
            "tier_0a": fact_counts.get("tier_0a", 0),
            "tier_0b": fact_counts.get("tier_0b", 0),
            "tier_0c": fact_counts.get("tier_0c", 0),
            "active_rules": active_rules,
            "active_subdomains": active_subdomains,
        }

    def _format_facts(self, facts: list[dict]) -> str:
        """Format facts as markdown list."""
        if not facts:
            return "*No facts in this tier.*"

        lines = []
        for f in facts:
            category = f.get("category") or "General"
            lines.append(f"- **[{category}]** {f['content']}")
        return "\n".join(lines)

    def _format_rules(self, rules: list[dict]) -> str:
        """Format automation rules as markdown."""
        if not rules:
            return "*No automation rules configured.*"

        lines = []
        for r in rules:
            lines.append(f"### {r['name']}")
            lines.append(f"**Q:** {r['question']}")
            lines.append(f"**A:** {r['answer']}")
            lines.append(f"*Threshold: {r['threshold']:.0%} | Used: {r['triggered']} times | Accepted: {r['accepted']} times*")
            lines.append("")
        return "\n".join(lines)

    def _format_subdomain_routing(self, subdomains: list[dict]) -> str:
        """Format sub-domain routing as markdown."""
        if not subdomains:
            return "*No sub-domains configured. All questions go to the main expert queue.*"

        lines = []
        for s in subdomains:
            desc = s.get("description") or "No description"
            keywords = ", ".join(s.get("keywords", [])) or "None"
            lines.append(f"- **{s['name']}**: {desc}")
            lines.append(f"  - Keywords: {keywords}")
        return "\n".join(lines)


# Global singleton
soul_generation_service = SoulGenerationService()
