"""
Slack Monitor Service.

Monitors configured Slack channels for:
1. MoltenLoris escalations (questions it couldn't answer)
2. Expert responses to those escalations
3. Captures Q&A pairs for knowledge base enrichment

This is read-only monitoring - Loris Web App observes what happens
in Slack but doesn't post messages itself.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mcp_client import get_mcp_client
from app.models.slack_capture import SlackCapture, SlackCaptureStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


class SlackMonitorService:
    """Service to monitor Slack for expert answers to MoltenLoris escalations."""

    def __init__(self, db: AsyncSession, organization_id: UUID):
        self.db = db
        self.organization_id = organization_id

    async def scan_for_expert_answers(
        self,
        since: Optional[datetime] = None,
        channels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scan monitored channels for expert answers to MoltenLoris escalations.

        Looks for threads where:
        1. MoltenLoris posted an escalation (has specific patterns or reactions)
        2. A human expert replied with an answer

        Args:
            since: Only look at messages after this timestamp
            channels: Specific channels to scan (defaults to configured channels)

        Returns:
            List of Q&A candidate dicts
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)

        channels_to_scan = channels or settings.slack_channels_list
        if not channels_to_scan:
            logger.warning("No Slack channels configured for monitoring")
            return []

        mcp = await get_mcp_client()
        if not mcp.is_configured:
            logger.warning("MCP client not configured, cannot scan Slack")
            return []

        candidates = []

        for channel in channels_to_scan:
            try:
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
                    thread_ts = msg.get("ts") or msg.get("thread_ts")
                    if not thread_ts:
                        continue

                    thread = await mcp.slack_read_thread(
                        channel=channel,
                        thread_ts=thread_ts
                    )

                    # Look for expert response
                    expert_answer = self._find_expert_answer(thread)
                    if expert_answer:
                        original_question = self._extract_original_question(msg, thread)
                        candidates.append({
                            "question": original_question,
                            "answer": expert_answer["text"],
                            "expert_name": expert_answer.get("user_name", "Unknown Expert"),
                            "expert_slack_id": expert_answer.get("user"),
                            "channel": channel,
                            "thread_ts": thread_ts,
                            "message_ts": expert_answer.get("ts", ""),
                            "question_timestamp": msg.get("ts"),
                            "answer_timestamp": expert_answer.get("ts"),
                        })

            except Exception as e:
                logger.error(f"Error scanning channel {channel}: {e}")
                continue

        return candidates

    def _is_moltenloris_escalation(self, message: Dict[str, Any]) -> bool:
        """
        Check if a message is a MoltenLoris escalation.

        Escalations are identified by:
        - Red circle (🔴) reaction
        - Bot message with escalation keywords
        - Specific message patterns
        """
        # Check for 🔴 reaction
        reactions = message.get("reactions", [])
        has_red_circle = any(
            r.get("name") in ["red_circle", "rotating_light", "warning"]
            for r in reactions
        )

        if has_red_circle:
            return True

        # Check if from a bot (MoltenLoris)
        is_bot = message.get("bot_id") is not None or message.get("subtype") == "bot_message"

        # Check for escalation text patterns
        text = (message.get("text") or "").lower()
        escalation_phrases = [
            "don't have enough information",
            "i'm not confident",
            "need expert help",
            "escalating to",
            "notifying an expert",
            "can someone help",
            "need help with this",
            "couldn't find an answer",
            "outside my knowledge",
        ]
        is_escalation_text = any(phrase in text for phrase in escalation_phrases)

        return is_bot and is_escalation_text

    def _find_expert_answer(self, thread: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the first substantive non-bot response in a thread.

        Returns the expert's answer message if found.
        """
        for msg in thread[1:]:  # Skip first message (the escalation)
            # Skip bot messages
            if msg.get("bot_id") is not None or msg.get("subtype") == "bot_message":
                continue

            # Skip very short messages (likely reactions or acknowledgments)
            text = msg.get("text", "")
            if len(text.strip()) < 20:
                continue

            # Skip messages that are just questions
            if text.strip().endswith("?") and len(text) < 100:
                continue

            return msg

        return None

    def _extract_original_question(
        self,
        escalation_msg: Dict[str, Any],
        thread: List[Dict[str, Any]]
    ) -> str:
        """
        Extract the original user question from the escalation context.

        The question might be:
        - Quoted in MoltenLoris's escalation message
        - The parent message if this is a thread
        - In a "forwarded from" block
        """
        escalation_text = escalation_msg.get("text", "")

        # Try to find quoted text (Slack uses > for quotes)
        lines = escalation_text.split("\n")
        quoted_lines = [line[1:].strip() for line in lines if line.startswith(">")]
        if quoted_lines:
            return " ".join(quoted_lines)

        # Look for the first non-bot message before the escalation
        escalation_ts = escalation_msg.get("ts", "")
        for msg in thread:
            msg_ts = msg.get("ts", "")
            if msg.get("bot_id") is None and msg_ts < escalation_ts:
                return msg.get("text", "")

        # Fallback: extract from escalation message
        # Remove common prefixes
        for prefix in ["escalating:", "question:", "user asked:", "need help with:"]:
            if prefix in escalation_text.lower():
                idx = escalation_text.lower().index(prefix) + len(prefix)
                return escalation_text[idx:].strip()

        return escalation_text

    async def create_captures(
        self,
        qa_pairs: List[Dict[str, Any]]
    ) -> List[SlackCapture]:
        """
        Create SlackCapture records from Q&A pairs for expert review.

        Deduplicates against existing captures by thread_ts.

        Args:
            qa_pairs: List of Q&A dicts from scan_for_expert_answers

        Returns:
            List of created SlackCapture records
        """
        created = []

        for qa in qa_pairs:
            # Check for existing capture with same thread
            existing = await self.db.execute(
                select(SlackCapture).where(
                    and_(
                        SlackCapture.organization_id == self.organization_id,
                        SlackCapture.channel == qa["channel"],
                        SlackCapture.thread_ts == qa["thread_ts"]
                    )
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Skipping duplicate capture for thread {qa['thread_ts']}")
                continue

            capture = SlackCapture(
                organization_id=self.organization_id,
                channel=qa["channel"],
                thread_ts=qa["thread_ts"],
                message_ts=qa.get("message_ts", qa["thread_ts"]),
                original_question=qa["question"],
                expert_answer=qa["answer"],
                expert_name=qa["expert_name"],
                expert_slack_id=qa.get("expert_slack_id"),
                confidence_score=0.8,  # High confidence since expert answered
                status=SlackCaptureStatus.PENDING,
                extra_data={
                    "question_timestamp": qa.get("question_timestamp"),
                    "answer_timestamp": qa.get("answer_timestamp"),
                    "captured_at": datetime.now(timezone.utc).isoformat()
                }
            )
            self.db.add(capture)
            created.append(capture)

        if created:
            await self.db.commit()
            logger.info(f"Created {len(created)} new Slack captures")

        return created

    async def get_pending_captures(
        self,
        limit: int = 50
    ) -> List[SlackCapture]:
        """Get pending Slack captures for expert review."""
        result = await self.db.execute(
            select(SlackCapture)
            .where(
                and_(
                    SlackCapture.organization_id == self.organization_id,
                    SlackCapture.status == SlackCaptureStatus.PENDING
                )
            )
            .order_by(SlackCapture.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def approve_capture(
        self,
        capture_id: UUID,
        reviewer_id: UUID,
        notes: Optional[str] = None,
        category: Optional[str] = None
    ) -> SlackCapture:
        """
        Approve a Slack capture and optionally create a WisdomFact.

        The actual fact creation is handled separately to allow
        for more control over the fact content.
        """
        result = await self.db.execute(
            select(SlackCapture).where(SlackCapture.id == capture_id)
        )
        capture = result.scalar_one_or_none()
        if not capture:
            raise ValueError(f"Capture not found: {capture_id}")

        capture.status = SlackCaptureStatus.APPROVED
        capture.reviewed_by_id = reviewer_id
        capture.reviewed_at = datetime.now(timezone.utc)
        capture.review_notes = notes
        if category:
            capture.suggested_category = category

        await self.db.commit()
        return capture

    async def reject_capture(
        self,
        capture_id: UUID,
        reviewer_id: UUID,
        reason: str
    ) -> SlackCapture:
        """Reject a Slack capture."""
        result = await self.db.execute(
            select(SlackCapture).where(SlackCapture.id == capture_id)
        )
        capture = result.scalar_one_or_none()
        if not capture:
            raise ValueError(f"Capture not found: {capture_id}")

        capture.status = SlackCaptureStatus.REJECTED
        capture.reviewed_by_id = reviewer_id
        capture.reviewed_at = datetime.now(timezone.utc)
        capture.review_notes = reason

        await self.db.commit()
        return capture
