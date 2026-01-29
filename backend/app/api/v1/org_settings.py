"""
Organization settings API — manage departments, AI provider config, and other org settings.
Settings are stored in the Organization.settings JSONB field.
API keys are encrypted before storage.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.encryption import encrypt_value, decrypt_value, mask_api_key, is_key_set
from app.api.v1.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.organization import Organization

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class TurboLorisSettings(BaseModel):
    enabled: bool = True
    min_threshold: float = 0.50
    default_threshold: float = 0.75
    threshold_options: List[float] = [0.50, 0.75, 0.90]


class AIProviderResponse(BaseModel):
    """AI provider configuration response (keys masked)."""
    provider: str = "local_ollama"
    model: str = ""

    # Ollama settings
    ollama_url: Optional[str] = None
    ollama_fallback_model: Optional[str] = None

    # Cloud provider settings (keys masked for security)
    anthropic_api_key_set: bool = False
    anthropic_api_key_masked: str = ""

    azure_endpoint: Optional[str] = None
    azure_api_key_set: bool = False
    azure_api_key_masked: str = ""
    azure_deployment: Optional[str] = None

    aws_region: Optional[str] = None

    # Advanced settings
    max_tokens: int = 4096
    temperature: float = 0.7

    # Computed privacy info
    data_locality: str = ""
    privacy_level: str = ""


class AIProviderUpdate(BaseModel):
    """AI provider configuration update request."""
    provider: Optional[str] = Field(
        None,
        description="Provider: local_ollama, cloud_anthropic, cloud_bedrock, cloud_azure"
    )
    model: Optional[str] = None

    # Ollama settings
    ollama_url: Optional[str] = None
    ollama_fallback_model: Optional[str] = None

    # Cloud provider settings (plaintext, will be encrypted)
    anthropic_api_key: Optional[str] = Field(None, description="Set to update, omit to keep existing")

    azure_endpoint: Optional[str] = None
    azure_api_key: Optional[str] = Field(None, description="Set to update, omit to keep existing")
    azure_deployment: Optional[str] = None

    aws_region: Optional[str] = None

    # Advanced settings
    max_tokens: Optional[int] = Field(None, ge=100, le=32000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class AIProviderTestResult(BaseModel):
    """Result of AI provider connection test."""
    success: bool
    message: str
    provider: str
    model: str
    response_preview: Optional[str] = None


class OllamaModelInfo(BaseModel):
    """Information about an available Ollama model."""
    name: str
    size: Optional[int] = None
    modified_at: Optional[str] = None


class OrgSettingsResponse(BaseModel):
    departments: List[str]
    require_department: bool
    turbo_loris: TurboLorisSettings

    class Config:
        from_attributes = True


class TurboLorisSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    min_threshold: Optional[float] = None
    default_threshold: Optional[float] = None
    threshold_options: Optional[List[float]] = None


class OrgSettingsUpdate(BaseModel):
    departments: Optional[List[str]] = None
    require_department: Optional[bool] = None
    turbo_loris: Optional[TurboLorisSettingsUpdate] = None


# ── Helper Functions ─────────────────────────────────────────────────

def _get_data_locality(provider: str, model: str = "") -> str:
    """Get data locality description for a provider."""
    if provider == "local_ollama":
        if model.endswith("-cloud"):
            return "Ollama cloud (encrypted, no prompt/output storage)"
        return "On-premise (data never leaves your servers)"
    localities = {
        "cloud_bedrock": "AWS account (data stays in your VPC)",
        "cloud_azure": "Azure tenant (data stays in your subscription)",
        "cloud_anthropic": "Anthropic cloud (data sent to third party)"
    }
    return localities.get(provider, "Unknown")


def _get_privacy_level(provider: str, model: str = "") -> str:
    """Get privacy level for a provider."""
    if provider == "local_ollama":
        if model.endswith("-cloud"):
            return "High (encrypted, no prompt/output retention)"
        return "Maximum (fully on-premise)"
    levels = {
        "cloud_bedrock": "High (your AWS account only)",
        "cloud_azure": "High (your Azure tenant only)",
        "cloud_anthropic": "Standard (third-party processing)"
    }
    return levels.get(provider, "Unknown")


def _build_ai_provider_response(ai_settings: dict) -> AIProviderResponse:
    """Build AI provider response from stored settings."""
    provider = ai_settings.get("provider", "local_ollama")
    model = ai_settings.get("model", "")

    # Decrypt and mask API keys for display
    anthropic_key_encrypted = ai_settings.get("anthropic_api_key_encrypted", "")
    azure_key_encrypted = ai_settings.get("azure_api_key_encrypted", "")

    anthropic_key_decrypted = ""
    azure_key_decrypted = ""

    if anthropic_key_encrypted:
        try:
            anthropic_key_decrypted = decrypt_value(anthropic_key_encrypted)
        except ValueError:
            logger.warning("Failed to decrypt Anthropic API key")

    if azure_key_encrypted:
        try:
            azure_key_decrypted = decrypt_value(azure_key_encrypted)
        except ValueError:
            logger.warning("Failed to decrypt Azure API key")

    return AIProviderResponse(
        provider=provider,
        model=model,
        ollama_url=ai_settings.get("ollama_url"),
        ollama_fallback_model=ai_settings.get("ollama_fallback_model"),
        anthropic_api_key_set=is_key_set(anthropic_key_encrypted),
        anthropic_api_key_masked=mask_api_key(anthropic_key_decrypted),
        azure_endpoint=ai_settings.get("azure_endpoint"),
        azure_api_key_set=is_key_set(azure_key_encrypted),
        azure_api_key_masked=mask_api_key(azure_key_decrypted),
        azure_deployment=ai_settings.get("azure_deployment"),
        aws_region=ai_settings.get("aws_region"),
        max_tokens=ai_settings.get("max_tokens", 4096),
        temperature=ai_settings.get("temperature", 0.7),
        data_locality=_get_data_locality(provider, model),
        privacy_level=_get_privacy_level(provider, model),
    )


# ── General Settings Endpoints ───────────────────────────────────────

@router.get("/settings", response_model=OrgSettingsResponse)
async def get_org_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization settings. Any authenticated user can read."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = org.settings or {}

    # Default Turbo Loris settings
    turbo_settings = settings.get("turbo_loris", {})
    turbo_loris = TurboLorisSettings(
        enabled=turbo_settings.get("enabled", True),
        min_threshold=turbo_settings.get("min_threshold", 0.50),
        default_threshold=turbo_settings.get("default_threshold", 0.75),
        threshold_options=turbo_settings.get("threshold_options", [0.50, 0.75, 0.90]),
    )

    return OrgSettingsResponse(
        departments=settings.get("departments", []),
        require_department=settings.get("require_department", False),
        turbo_loris=turbo_loris,
    )


@router.put("/settings", response_model=OrgSettingsResponse)
async def update_org_settings(
    data: OrgSettingsUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update organization settings. Admin-only."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = dict(org.settings or {})

    if data.departments is not None:
        settings["departments"] = data.departments
    if data.require_department is not None:
        settings["require_department"] = data.require_department

    # Update Turbo Loris settings
    if data.turbo_loris is not None:
        turbo_settings = settings.get("turbo_loris", {})
        if data.turbo_loris.enabled is not None:
            turbo_settings["enabled"] = data.turbo_loris.enabled
        if data.turbo_loris.min_threshold is not None:
            turbo_settings["min_threshold"] = data.turbo_loris.min_threshold
        if data.turbo_loris.default_threshold is not None:
            turbo_settings["default_threshold"] = data.turbo_loris.default_threshold
        if data.turbo_loris.threshold_options is not None:
            turbo_settings["threshold_options"] = data.turbo_loris.threshold_options
        settings["turbo_loris"] = turbo_settings

    org.settings = settings
    await db.commit()
    await db.refresh(org)

    # Build Turbo Loris response
    turbo_settings = settings.get("turbo_loris", {})
    turbo_loris = TurboLorisSettings(
        enabled=turbo_settings.get("enabled", True),
        min_threshold=turbo_settings.get("min_threshold", 0.50),
        default_threshold=turbo_settings.get("default_threshold", 0.75),
        threshold_options=turbo_settings.get("threshold_options", [0.50, 0.75, 0.90]),
    )

    return OrgSettingsResponse(
        departments=settings.get("departments", []),
        require_department=settings.get("require_department", False),
        turbo_loris=turbo_loris,
    )


# ── AI Provider Endpoints ────────────────────────────────────────────

@router.get("/ai-provider", response_model=AIProviderResponse)
async def get_ai_provider_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI provider configuration. Any authenticated user can read.
    API keys are masked for security.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = org.settings or {}
    ai_settings = settings.get("ai_provider", {})

    return _build_ai_provider_response(ai_settings)


@router.put("/ai-provider", response_model=AIProviderResponse)
async def update_ai_provider_settings(
    data: AIProviderUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update AI provider configuration. Admin-only.
    API keys are encrypted before storage.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = dict(org.settings or {})
    ai_settings = dict(settings.get("ai_provider", {}))

    # Update provider and model
    if data.provider is not None:
        valid_providers = ["local_ollama", "cloud_anthropic", "cloud_bedrock", "cloud_azure"]
        if data.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        ai_settings["provider"] = data.provider

    if data.model is not None:
        ai_settings["model"] = data.model

    # Update Ollama settings
    if data.ollama_url is not None:
        ai_settings["ollama_url"] = data.ollama_url
    if data.ollama_fallback_model is not None:
        ai_settings["ollama_fallback_model"] = data.ollama_fallback_model

    # Update Anthropic settings (encrypt API key)
    if data.anthropic_api_key is not None:
        if data.anthropic_api_key.strip():
            ai_settings["anthropic_api_key_encrypted"] = encrypt_value(data.anthropic_api_key)
        else:
            # Empty string clears the key
            ai_settings["anthropic_api_key_encrypted"] = ""

    # Update Azure settings (encrypt API key)
    if data.azure_endpoint is not None:
        ai_settings["azure_endpoint"] = data.azure_endpoint
    if data.azure_api_key is not None:
        if data.azure_api_key.strip():
            ai_settings["azure_api_key_encrypted"] = encrypt_value(data.azure_api_key)
        else:
            ai_settings["azure_api_key_encrypted"] = ""
    if data.azure_deployment is not None:
        ai_settings["azure_deployment"] = data.azure_deployment

    # Update AWS settings
    if data.aws_region is not None:
        ai_settings["aws_region"] = data.aws_region

    # Update advanced settings
    if data.max_tokens is not None:
        ai_settings["max_tokens"] = data.max_tokens
    if data.temperature is not None:
        ai_settings["temperature"] = data.temperature

    settings["ai_provider"] = ai_settings
    org.settings = settings
    await db.commit()
    await db.refresh(org)

    logger.info(f"AI provider settings updated by user {current_user.email} for org {org.id}")

    return _build_ai_provider_response(ai_settings)


@router.post("/ai-provider/test", response_model=AIProviderTestResult)
async def test_ai_provider_connection(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Test the AI provider connection with a simple prompt.
    Admin-only.
    """
    from app.services.ai_provider_service import AIProviderService, AIConfig, AIProvider

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = org.settings or {}
    ai_settings = settings.get("ai_provider", {})

    # Build config from org settings
    provider_str = ai_settings.get("provider", "local_ollama")
    try:
        provider = AIProvider(provider_str)
    except ValueError:
        return AIProviderTestResult(
            success=False,
            message=f"Invalid provider: {provider_str}",
            provider=provider_str,
            model="",
        )

    # Get API keys (decrypt if needed)
    anthropic_key = ""
    azure_key = ""

    if ai_settings.get("anthropic_api_key_encrypted"):
        try:
            anthropic_key = decrypt_value(ai_settings["anthropic_api_key_encrypted"])
        except ValueError:
            pass

    if ai_settings.get("azure_api_key_encrypted"):
        try:
            azure_key = decrypt_value(ai_settings["azure_api_key_encrypted"])
        except ValueError:
            pass

    model = ai_settings.get("model", "")

    # Build config
    config = AIConfig(
        provider=provider,
        model=model or AIProviderService(None)._get_default_model(provider),
        api_key=anthropic_key,
        base_url=ai_settings.get("ollama_url"),
        region=ai_settings.get("aws_region"),
        max_tokens=ai_settings.get("max_tokens", 4096),
        temperature=ai_settings.get("temperature", 0.7),
    )

    # Test with a simple prompt
    try:
        service = AIProviderService(config)
        response = await service.generate(
            "Say 'Hello from Loris!' in exactly those words.",
            max_tokens=50,
            temperature=0.1,
        )

        return AIProviderTestResult(
            success=True,
            message="Connection successful",
            provider=provider_str,
            model=config.model,
            response_preview=response[:100] if response else None,
        )
    except Exception as e:
        logger.error(f"AI provider test failed: {e}")
        return AIProviderTestResult(
            success=False,
            message=str(e),
            provider=provider_str,
            model=config.model,
        )


@router.get("/ai-provider/models", response_model=List[OllamaModelInfo])
async def list_available_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List available models for the current AI provider.
    Currently only supports listing Ollama models.
    """
    from app.services.ai_provider_service import AIProviderService

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = org.settings or {}
    ai_settings = settings.get("ai_provider", {})
    provider = ai_settings.get("provider", "local_ollama")

    if provider != "local_ollama":
        # For cloud providers, return common model options
        if provider == "cloud_anthropic":
            return [
                OllamaModelInfo(name="claude-sonnet-4-20250514"),
                OllamaModelInfo(name="claude-opus-4-20250514"),
                OllamaModelInfo(name="claude-3-5-sonnet-20241022"),
                OllamaModelInfo(name="claude-3-5-haiku-20241022"),
            ]
        elif provider == "cloud_bedrock":
            return [
                OllamaModelInfo(name="anthropic.claude-3-sonnet-20240229-v1:0"),
                OllamaModelInfo(name="anthropic.claude-3-haiku-20240307-v1:0"),
                OllamaModelInfo(name="anthropic.claude-3-opus-20240229-v1:0"),
            ]
        elif provider == "cloud_azure":
            return [
                OllamaModelInfo(name="gpt-4"),
                OllamaModelInfo(name="gpt-4-turbo"),
                OllamaModelInfo(name="gpt-35-turbo"),
            ]
        return []

    # For Ollama, query the server
    models = await AIProviderService.list_ollama_models()
    return [
        OllamaModelInfo(
            name=m.get("name", m.get("model", "unknown")),
            size=m.get("size"),
            modified_at=m.get("modified_at"),
        )
        for m in models
    ]
