"""
MCP Client for Loris Web App.

Connects to Zapier MCP server via JSON-RPC 2.0 to:
- Read Slack messages (monitoring expert answers to MoltenLoris)
- Write files to Google Drive (publishing knowledge)

This enables the air gap architecture: Loris and MoltenLoris never
communicate directly - only through Slack (observed) and GDrive (shared files).
"""

import httpx
import json
from typing import Any, Optional, List, Dict
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for Zapier MCP server communication via JSON-RPC 2.0."""

    def __init__(self, mcp_url: Optional[str] = None):
        self.mcp_url = mcp_url or settings.MCP_SERVER_URL
        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0

    @property
    def is_configured(self) -> bool:
        """Check if MCP is configured."""
        return bool(self.mcp_url)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
        return self._client

    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id

    async def call_tool(
        self,
        tool_name: str,
        instructions: str,
        output_hint: str = "all relevant data",
        **params
    ) -> Dict[str, Any]:
        """
        Call an MCP tool via JSON-RPC.

        Args:
            tool_name: Name of the MCP tool to call
            instructions: Natural language instructions for the tool
            output_hint: Description of what data to extract from results
            **params: Additional parameters for the tool

        Returns:
            Tool response dict with results
        """
        if not self.is_configured:
            raise RuntimeError("MCP server not configured - set MCP_SERVER_URL")

        client = await self._get_client()

        # Build JSON-RPC request
        arguments = {
            "instructions": instructions,
            "output_hint": output_hint,
            **params
        }

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": self._next_id()
        }

        try:
            response = await client.post(self.mcp_url, json=payload)
            response.raise_for_status()

            # Parse SSE response
            text = response.text
            if text.startswith("event:"):
                # Extract JSON from SSE format
                for line in text.split("\n"):
                    if line.startswith("data:"):
                        json_str = line[5:].strip()
                        result = json.loads(json_str)
                        return self._parse_result(result)

            # Direct JSON response
            return self._parse_result(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(f"MCP tool call failed: {tool_name} - {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"MCP tool call error: {tool_name} - {e}")
            raise

    def _parse_result(self, response: Dict) -> Dict[str, Any]:
        """Parse JSON-RPC response."""
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        result = response.get("result", {})
        content = result.get("content", [])

        # Extract text content and parse inner JSON
        for item in content:
            if item.get("type") == "text":
                try:
                    inner = json.loads(item.get("text", "{}"))
                    return inner
                except json.JSONDecodeError:
                    return {"text": item.get("text")}

        return result

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools."""
        if not self.is_configured:
            return []

        client = await self._get_client()

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": self._next_id()
        }

        try:
            response = await client.post(self.mcp_url, json=payload)
            text = response.text

            if text.startswith("event:"):
                for line in text.split("\n"):
                    if line.startswith("data:"):
                        result = json.loads(line[5:].strip())
                        return result.get("result", {}).get("tools", [])

            return response.json().get("result", {}).get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            return []

    # --- Google Docs Tools ---

    async def gdrive_create_document(
        self,
        title: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Create a new document in the Loris-Knowledge folder.

        Args:
            title: Document name (e.g., "Contracts-Vendor-Agreements")
            content: Document content (markdown)

        Returns:
            Dict with url and title of created document
        """
        logger.info(f"Creating GDrive document: {title} (content length: {len(content)})")
        result = await self.call_tool(
            "google_docs_create_document_from_text",
            instructions=f"Create a knowledge document named {title} in the Loris-Knowledge folder",
            output_hint="document URL and title",
            title=title,
            file=content
        )
        logger.info(f"GDrive create result for '{title}': {result}")
        return result

    async def gdrive_append_to_document(
        self,
        document_name: str,
        text: str,
        newline: bool = True
    ) -> Dict[str, Any]:
        """
        Append text to an existing document.

        Args:
            document_name: Name of the document
            text: Text to append
            newline: Whether to add on new line

        Returns:
            Result of append operation
        """
        return await self.call_tool(
            "google_docs_append_text_to_document",
            instructions=f"Append text to the document named {document_name}",
            output_hint="success confirmation",
            file=document_name,
            text=text,
            newline="Yes" if newline else "No"
        )

    async def gdrive_update_document(
        self,
        document_name: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Update an existing document by replacing its content.

        Since Google Docs append doesn't truly replace content, we:
        1. Try to find the existing document
        2. If it exists, delete it (by creating with same name - GDrive allows duplicates)
        3. Create new document with the content

        For simplicity, we just create the document. Google Drive handles
        documents by name, and MoltenLoris will use the most recent version.

        Args:
            document_name: Name of the document to update
            content: New content for the document

        Returns:
            Result of create operation
        """
        # Check if document exists for logging
        try:
            existing = await self.gdrive_find_document(document_name)
            doc_exists = existing and (existing.get("results") or existing.get("url") or existing.get("title"))
            if doc_exists:
                logger.info(f"Document '{document_name}' exists, creating updated version")
            else:
                logger.info(f"Document '{document_name}' not found, creating new")
        except Exception as e:
            logger.warning(f"Could not check if document exists: {e}")
            doc_exists = False

        # Create/update the document
        # Note: This may create a duplicate if one exists, but GDrive search
        # will find the most recent one with matching name
        result = await self.gdrive_create_document(
            title=document_name,
            content=content
        )

        logger.info(f"Created/updated document '{document_name}': {result}")
        return result

    async def gdrive_find_document(
        self,
        title: str
    ) -> Dict[str, Any]:
        """
        Find a document by name in the Loris-Knowledge folder.

        Args:
            title: Document name to search for

        Returns:
            Document metadata if found
        """
        return await self.call_tool(
            "google_docs_find_a_document",
            instructions=f"Find the document named {title} in the Loris-Knowledge folder",
            output_hint="document URL, title, and id",
            title=title
        )

    async def gdrive_list_folder(self) -> List[Dict[str, Any]]:
        """
        List all documents in the Loris-Knowledge folder.

        Returns:
            List of documents with title, url, and id
        """
        result = await self.call_tool(
            "google_docs_find_a_document",
            instructions="List all documents in the Loris-Knowledge folder. Return all files found.",
            output_hint="list of all documents: title, url, id for each file",
            title="*"
        )

        # Normalize to list
        files = result.get("results", [])
        if isinstance(files, dict):
            files = [files] if files else []
        return files if isinstance(files, list) else []

    # --- Slack Tools ---

    async def slack_get_thread_messages(
        self,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve messages from the moltenloris Slack channel.

        Args:
            thread_ts: Optional thread timestamp (uses default if not provided)

        Returns:
            Dict with messages
        """
        params = {}
        if thread_ts:
            params["threadTs"] = thread_ts

        return await self.call_tool(
            "slack_retrieve_thread_messages",
            instructions="Get messages from the moltenloris channel thread",
            output_hint="message text, user names, timestamps",
            **params
        )

    async def slack_scan_recent_messages(
        self,
        minutes_back: int = 10,
        channel: str = "moltenloris"
    ) -> Dict[str, Any]:
        """
        Scan for recent messages in a Slack channel.

        Uses a time window to find messages from the last N minutes.

        Args:
            minutes_back: How many minutes back to scan (default 10)
            channel: Channel name to scan

        Returns:
            Dict with recent messages, including any expert answers to escalations
        """
        from datetime import datetime, timezone, timedelta

        # Calculate timestamp for N minutes ago
        since_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_back)
        since_ts = since_time.timestamp()

        instructions = (
            f"Get messages from the {channel} channel from the last {minutes_back} minutes "
            f"(since Unix timestamp {since_ts:.6f}). "
            f"Look for threads where MoltenLoris asked a question or escalated something "
            f"and a human expert replied. Return the original question and the expert's answer. "
            f"Focus on substantive expert responses, not just acknowledgments."
        )

        return await self.call_tool(
            "slack_retrieve_thread_messages",
            instructions=instructions,
            output_hint="For each Q&A found: original_question, expert_answer, expert_name, thread_timestamp, answer_timestamp"
        )

    async def slack_read_channel(
        self,
        channel: str,
        since: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Read messages from a Slack channel since a given time.

        Args:
            channel: Channel name
            since: ISO timestamp to start from
            limit: Max messages to retrieve

        Returns:
            List of message dicts
        """
        from datetime import datetime

        # Parse the since timestamp and convert to Unix
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            since_ts = since_dt.timestamp()
        except:
            since_ts = datetime.now().timestamp() - 86400  # Default to 24h ago

        instructions = (
            f"Get recent messages from the {channel} channel since Unix timestamp {since_ts:.6f}. "
            f"Look for bot messages from MoltenLoris that indicate escalations or questions "
            f"that need expert help. Return up to {limit} messages."
        )

        result = await self.call_tool(
            "slack_retrieve_thread_messages",
            instructions=instructions,
            output_hint="message text, sender, timestamp, thread_ts, bot_id, reactions"
        )

        # Normalize to list
        messages = result.get("messages", result.get("results", []))
        if isinstance(messages, dict):
            messages = [messages] if messages else []
        return messages if isinstance(messages, list) else []

    async def slack_read_thread(
        self,
        channel: str,
        thread_ts: str
    ) -> List[Dict[str, Any]]:
        """
        Read all messages in a specific thread.

        Args:
            channel: Channel name
            thread_ts: Thread timestamp (parent message ts)

        Returns:
            List of messages in the thread
        """
        instructions = (
            f"Get all messages from the thread with timestamp {thread_ts} "
            f"in the {channel} channel. Include the original message and all replies."
        )

        result = await self.call_tool(
            "slack_retrieve_thread_messages",
            instructions=instructions,
            output_hint="All messages in thread: text, sender name, timestamp, is_bot",
            threadTs=thread_ts
        )

        # Normalize to list
        messages = result.get("messages", result.get("results", []))
        if isinstance(messages, dict):
            messages = [messages] if messages else []
        return messages if isinstance(messages, list) else []

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """Get or create MCP client singleton."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def close_mcp_client():
    """Close the MCP client singleton."""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None
