"""
Configurable AI Provider Service - supports multiple AI backends for data privacy.

Supports:
- LOCAL: Ollama (local or Ollama cloud models) - encrypted, no prompt/output logging
- CLOUD_ANTHROPIC: Anthropic Claude API - direct cloud access
- CLOUD_BEDROCK: AWS Bedrock (Claude) - data stays in your AWS account
- CLOUD_AZURE: Azure OpenAI - data stays in your Azure account

Enterprise users can keep all confidential/privileged information local or within
controlled cloud environments where data is not shared with third parties.

Configuration Priority:
1. Organization settings (stored in DB, encrypted API keys)
2. Environment variables (.env file)
3. Default values

Ollama cloud models (e.g. qwen3-vl:235b-cloud, gpt-oss:120b-cloud) offer a good
middle ground: traffic to Ollama is encrypted and they don't store prompts/outputs,
but the models run on Ollama's infrastructure so they work on any machine regardless
of local GPU capacity.
"""

import logging
import json
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass
import httpx

from app.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from uuid import UUID

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    LOCAL_OLLAMA = "local_ollama"
    CLOUD_ANTHROPIC = "cloud_anthropic"
    CLOUD_BEDROCK = "cloud_bedrock"
    CLOUD_AZURE = "cloud_azure"


@dataclass
class AIConfig:
    """Configuration for AI provider."""
    provider: AIProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    region: Optional[str] = None  # For AWS Bedrock
    azure_endpoint: Optional[str] = None  # For Azure OpenAI
    azure_deployment: Optional[str] = None  # For Azure OpenAI
    fallback_model: Optional[str] = None  # Fallback model for Ollama
    max_tokens: int = 4096
    temperature: float = 0.7
    log_prompts: bool = False
    log_responses: bool = False


class AIProviderService:
    """
    Unified AI provider service supporting multiple backends.

    Data Privacy:
    - LOCAL_OLLAMA: All data stays on your servers, no external calls
    - CLOUD_BEDROCK: Data stays in your AWS VPC, not shared with Anthropic
    - CLOUD_AZURE: Data stays in your Azure tenant
    - CLOUD_ANTHROPIC: Data sent to Anthropic (may not be suitable for privileged info)
    """

    def __init__(self, config: Optional[AIConfig] = None):
        """Initialize with configuration or load from settings."""
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_settings()

        self._client = None
        logger.info(f"AI Provider initialized: {self.config.provider.value} with model {self.config.model}")

    @classmethod
    async def for_organization(
        cls,
        organization_id: "UUID",
        db: "AsyncSession"
    ) -> "AIProviderService":
        """
        Get an AI provider service configured for a specific organization.

        Loads settings from the organization's stored configuration,
        falling back to environment variables for missing values.

        Args:
            organization_id: The organization's UUID
            db: Database session

        Returns:
            AIProviderService configured for the organization
        """
        from sqlalchemy import select
        from app.models.organization import Organization
        from app.core.encryption import decrypt_value

        result = await db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            logger.warning(f"Organization {organization_id} not found, using default config")
            return cls()

        org_settings = org.settings or {}
        ai_settings = org_settings.get("ai_provider", {})

        if not ai_settings:
            # No org-specific settings, use defaults
            return cls()

        # Build config from org settings with env fallbacks
        provider_str = ai_settings.get("provider", getattr(settings, 'AI_PROVIDER', 'local_ollama'))

        try:
            provider = AIProvider(provider_str)
        except ValueError:
            logger.warning(f"Unknown AI provider '{provider_str}', defaulting to local_ollama")
            provider = AIProvider.LOCAL_OLLAMA

        # Get model
        model = ai_settings.get("model")
        if not model:
            model = cls._get_default_model_static(provider)

        # Decrypt API keys
        anthropic_key = None
        azure_key = None

        if ai_settings.get("anthropic_api_key_encrypted"):
            try:
                anthropic_key = decrypt_value(ai_settings["anthropic_api_key_encrypted"])
            except ValueError:
                logger.warning("Failed to decrypt Anthropic API key for org")

        if ai_settings.get("azure_api_key_encrypted"):
            try:
                azure_key = decrypt_value(ai_settings["azure_api_key_encrypted"])
            except ValueError:
                logger.warning("Failed to decrypt Azure API key for org")

        # Fall back to env vars if org doesn't have keys set
        if provider == AIProvider.CLOUD_ANTHROPIC and not anthropic_key:
            anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', None)

        if provider == AIProvider.CLOUD_AZURE and not azure_key:
            azure_key = getattr(settings, 'AZURE_OPENAI_KEY', None)

        # Build config
        config = AIConfig(
            provider=provider,
            model=model,
            api_key=anthropic_key,
            base_url=ai_settings.get("ollama_url") or getattr(settings, 'OLLAMA_URL', 'http://host.docker.internal:11434'),
            region=ai_settings.get("aws_region") or getattr(settings, 'AWS_REGION', 'us-east-1'),
            azure_endpoint=ai_settings.get("azure_endpoint") or getattr(settings, 'AZURE_OPENAI_ENDPOINT', None),
            azure_deployment=ai_settings.get("azure_deployment") or getattr(settings, 'AZURE_OPENAI_DEPLOYMENT', None),
            fallback_model=ai_settings.get("ollama_fallback_model") or getattr(settings, 'OLLAMA_FALLBACK_MODEL', None),
            max_tokens=ai_settings.get("max_tokens", getattr(settings, 'AI_MAX_TOKENS', 4096)),
            temperature=ai_settings.get("temperature", getattr(settings, 'AI_TEMPERATURE', 0.7)),
            log_prompts=getattr(settings, 'AI_LOG_PROMPTS', False),
            log_responses=getattr(settings, 'AI_LOG_RESPONSES', False),
        )

        # For Azure, set the API key in a way we can access it
        if provider == AIProvider.CLOUD_AZURE:
            config.api_key = azure_key

        return cls(config)

    @staticmethod
    def _get_default_model_static(provider: AIProvider) -> str:
        """Get default model for each provider (static version)."""
        defaults = {
            AIProvider.LOCAL_OLLAMA: "qwen3-vl:235b-cloud",
            AIProvider.CLOUD_ANTHROPIC: "claude-sonnet-4-20250514",
            AIProvider.CLOUD_BEDROCK: "anthropic.claude-3-sonnet-20240229-v1:0",
            AIProvider.CLOUD_AZURE: "gpt-4"
        }
        return defaults.get(provider, "qwen3-vl:235b-cloud")

    def _load_config_from_settings(self) -> AIConfig:
        """Load AI configuration from application settings (environment variables)."""
        provider_str = getattr(settings, 'AI_PROVIDER', 'local_ollama')

        try:
            provider = AIProvider(provider_str)
        except ValueError:
            logger.warning(f"Unknown AI provider '{provider_str}', defaulting to local_ollama")
            provider = AIProvider.LOCAL_OLLAMA

        # Get model - prefer AI_MODEL, then provider-specific setting, then default
        model = getattr(settings, 'AI_MODEL', None)
        if not model and provider == AIProvider.LOCAL_OLLAMA:
            model = getattr(settings, 'OLLAMA_MODEL', None)
        if not model:
            model = self._get_default_model(provider)

        return AIConfig(
            provider=provider,
            model=model,
            api_key=getattr(settings, 'ANTHROPIC_API_KEY', None),
            base_url=getattr(settings, 'AI_BASE_URL', None) or getattr(settings, 'OLLAMA_URL', 'http://localhost:11434'),
            region=getattr(settings, 'AWS_REGION', 'us-east-1'),
            azure_endpoint=getattr(settings, 'AZURE_OPENAI_ENDPOINT', None),
            azure_deployment=getattr(settings, 'AZURE_OPENAI_DEPLOYMENT', None),
            fallback_model=getattr(settings, 'OLLAMA_FALLBACK_MODEL', None),
            max_tokens=getattr(settings, 'AI_MAX_TOKENS', 4096),
            temperature=getattr(settings, 'AI_TEMPERATURE', 0.7),
            log_prompts=getattr(settings, 'AI_LOG_PROMPTS', False),
            log_responses=getattr(settings, 'AI_LOG_RESPONSES', False)
        )

    def _get_default_model(self, provider: AIProvider) -> str:
        """Get default model for each provider."""
        return self._get_default_model_static(provider)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None
    ) -> str:
        """
        Generate a response from the AI model.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            max_tokens: Override default max tokens
            temperature: Override default temperature
            stop_sequences: Optional stop sequences

        Returns:
            Generated text response
        """
        if self.config.log_prompts:
            logger.debug(f"AI Prompt: {prompt[:200]}...")

        try:
            if self.config.provider == AIProvider.LOCAL_OLLAMA:
                response = await self._generate_ollama(prompt, system_prompt, max_tokens, temperature)
            elif self.config.provider == AIProvider.CLOUD_ANTHROPIC:
                response = await self._generate_anthropic(prompt, system_prompt, max_tokens, temperature, stop_sequences)
            elif self.config.provider == AIProvider.CLOUD_BEDROCK:
                response = await self._generate_bedrock(prompt, system_prompt, max_tokens, temperature, stop_sequences)
            elif self.config.provider == AIProvider.CLOUD_AZURE:
                response = await self._generate_azure(prompt, system_prompt, max_tokens, temperature)
            else:
                raise ValueError(f"Unsupported AI provider: {self.config.provider}")

            if self.config.log_responses:
                logger.debug(f"AI Response: {response[:200]}...")

            return response

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            raise

    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float]
    ) -> str:
        """Generate using Ollama server (local or cloud models).

        Tries the configured primary model first, then falls back to
        the fallback model if the primary is unavailable.
        """
        base_url = self.config.base_url or "http://localhost:11434"

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        models_to_try = [self.config.model]
        # Use config fallback first, then env fallback
        fallback = self.config.fallback_model or getattr(settings, 'OLLAMA_FALLBACK_MODEL', None)
        if fallback and fallback != self.config.model:
            models_to_try.append(fallback)

        last_error = None
        for model in models_to_try:
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens or self.config.max_tokens,
                    "temperature": temperature if temperature is not None else self.config.temperature
                }
            }
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(f"{base_url}/api/generate", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    result = data.get("response", "")
                    if model != self.config.model:
                        logger.info(f"Used fallback Ollama model: {model}")
                    return result
            except Exception as e:
                logger.warning(f"Ollama model '{model}' failed: {e}")
                last_error = e

        raise last_error or RuntimeError("All Ollama models failed")

    @staticmethod
    async def list_ollama_models(ollama_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """List models available on the connected Ollama instance."""
        url = ollama_url or getattr(settings, 'OLLAMA_URL', 'http://host.docker.internal:11434')
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        stop_sequences: Optional[List[str]]
    ) -> str:
        """Generate using Anthropic Claude API directly."""
        if not self.config.api_key:
            raise ValueError("API key required for cloud_anthropic provider")

        headers = {
            "anthropic-version": "2024-10-22",
            "x-api-key": self.config.api_key,
            "content-type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            payload["system"] = system_prompt
        if temperature is not None:
            payload["temperature"] = temperature
        if stop_sequences:
            payload["stop_sequences"] = stop_sequences

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "")
            return ""

    async def _generate_bedrock(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        stop_sequences: Optional[List[str]]
    ) -> str:
        """Generate using AWS Bedrock (Claude models)."""
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError("boto3 required for AWS Bedrock. Install with: pip install boto3")

        config = Config(
            region_name=self.config.region or "us-east-1",
            retries={'max_attempts': 3}
        )

        bedrock = boto3.client('bedrock-runtime', config=config)

        messages = [{"role": "user", "content": prompt}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": messages
        }

        if system_prompt:
            body["system"] = system_prompt
        if temperature is not None:
            body["temperature"] = temperature
        if stop_sequences:
            body["stop_sequences"] = stop_sequences

        response = bedrock.invoke_model(
            modelId=self.config.model,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response['body'].read())
        content = response_body.get("content", [])

        if content and isinstance(content, list):
            return content[0].get("text", "")
        return ""

    async def _generate_azure(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float]
    ) -> str:
        """Generate using Azure OpenAI."""
        # Use config values first, fall back to env vars
        azure_endpoint = self.config.azure_endpoint or getattr(settings, 'AZURE_OPENAI_ENDPOINT', None)
        azure_key = self.config.api_key or getattr(settings, 'AZURE_OPENAI_KEY', None)
        deployment_name = self.config.azure_deployment or getattr(settings, 'AZURE_OPENAI_DEPLOYMENT', self.config.model)

        if not azure_endpoint or not azure_key:
            raise ValueError("Azure endpoint and API key required for cloud_azure provider")

        headers = {
            "api-key": azure_key,
            "content-type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature
        }

        url = f"{azure_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2024-02-15-preview"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

    async def generate_turbo_answer(
        self,
        question: str,
        knowledge_facts: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Generate a Turbo Loris answer based on matched knowledge facts.
        Returns the answer text or None if generation fails.
        """
        if not knowledge_facts:
            return None

        system_prompt = """You are Turbo Loris, an AI assistant that provides fast, accurate answers
based on validated knowledge. Your answers should be:
- Concise but complete
- Based directly on the provided knowledge
- Honest about any limitations or caveats
- Professional and helpful

IMPORTANT: Only answer based on the knowledge provided. If the knowledge is insufficient,
say so rather than making things up."""

        knowledge_summary = "\n".join([
            f"• [{k.get('tier', 'unknown')}] {k.get('content', '')[:500]}"
            for k in knowledge_facts[:5]  # Top 5 most relevant
        ])

        prompt = f"""Based on the following validated knowledge, answer this question:

QUESTION:
{question}

KNOWLEDGE BASE:
{knowledge_summary}

Provide a clear, direct answer. If the knowledge doesn't fully cover the question,
indicate what additional expert consultation might be needed."""

        try:
            response = await self.generate(
                prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more consistent answers
                max_tokens=1024,
            )
            return response.strip() if response else None
        except Exception as e:
            logger.error(f"Turbo answer generation failed: {e}")
            return None

    async def analyze_gaps(
        self,
        question: str,
        knowledge_facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a question against the knowledge base to identify gaps.

        Returns:
        - relevant_knowledge: Facts that apply to this question
        - coverage_percentage: How much of the question is covered
        - identified_gaps: What's missing
        - proposed_answer: AI-generated answer draft
        - confidence_score: How confident the AI is
        """
        system_prompt = """You are a knowledge analysis expert helping domain experts answer questions.
Your task is to analyze what knowledge is relevant, what gaps exist, and propose an answer.

Be thorough but concise. Focus on actionable insights for the expert."""

        knowledge_summary = "\n".join([
            f"- {k.get('content', k.get('fact_text', 'Unknown'))[:300]}"
            for k in knowledge_facts[:10]
        ]) if knowledge_facts else "No relevant knowledge found."

        prompt = f"""QUESTION:
{question}

AVAILABLE KNOWLEDGE:
{knowledge_summary}

Analyze and return JSON:
{{
  "relevant_knowledge": ["fact1", "fact2"],
  "coverage_percentage": 0-100,
  "identified_gaps": ["gap1", "gap2"],
  "proposed_answer": "Draft answer text",
  "confidence_score": 0.0-1.0,
  "suggested_clarifications": ["clarification1"]
}}

Return ONLY valid JSON."""

        try:
            response = await self.generate(prompt, system_prompt=system_prompt, temperature=0.3)

            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI gap analysis response: {e}")
            return {
                "relevant_knowledge": [],
                "coverage_percentage": 0,
                "identified_gaps": ["Unable to analyze"],
                "proposed_answer": "",
                "confidence_score": 0.0,
                "suggested_clarifications": []
            }

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current AI provider configuration."""
        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "data_locality": self._get_data_locality(),
            "privacy_level": self._get_privacy_level(),
            "max_tokens": self.config.max_tokens
        }

    def _get_data_locality(self) -> str:
        """Get data locality description for the current provider."""
        if self.config.provider == AIProvider.LOCAL_OLLAMA:
            if self.config.model.endswith("-cloud"):
                return "Ollama cloud (encrypted, no prompt/output storage)"
            return "on-premise (data never leaves your servers)"
        localities = {
            AIProvider.CLOUD_BEDROCK: "AWS account (data stays in your VPC)",
            AIProvider.CLOUD_AZURE: "Azure tenant (data stays in your subscription)",
            AIProvider.CLOUD_ANTHROPIC: "Anthropic cloud (data sent to third party)"
        }
        return localities.get(self.config.provider, "unknown")

    def _get_privacy_level(self) -> str:
        """Get privacy level for the current provider."""
        if self.config.provider == AIProvider.LOCAL_OLLAMA:
            if self.config.model.endswith("-cloud"):
                return "high (encrypted, no prompt/output retention)"
            return "maximum (fully on-premise)"
        levels = {
            AIProvider.CLOUD_BEDROCK: "high (your AWS account only)",
            AIProvider.CLOUD_AZURE: "high (your Azure tenant only)",
            AIProvider.CLOUD_ANTHROPIC: "standard (third-party processing)"
        }
        return levels.get(self.config.provider, "unknown")


# Global service instance - configured from settings (env vars)
# For org-specific config, use AIProviderService.for_organization()
ai_provider_service = AIProviderService()
