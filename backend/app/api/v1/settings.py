"""
Settings API - AI provider configuration and Ollama model management.

Domain experts and admins can view and manage AI provider settings,
including listing available Ollama models on the connected instance.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.v1.auth import get_current_active_expert
from app.models.user import User
from app.services.ai_provider_service import AIProviderService, ai_provider_service

router = APIRouter()


class AIProviderInfoResponse(BaseModel):
    provider: str
    model: str
    data_locality: str
    privacy_level: str
    max_tokens: int


class OllamaModelResponse(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None
    digest: str | None = None


@router.get("/ai-provider", response_model=AIProviderInfoResponse)
async def get_ai_provider_info(
    current_user: User = Depends(get_current_active_expert),
):
    """Get current AI provider configuration. Expert-only."""
    info = ai_provider_service.get_provider_info()
    return AIProviderInfoResponse(**info)


@router.get("/ollama-models", response_model=List[OllamaModelResponse])
async def list_ollama_models(
    current_user: User = Depends(get_current_active_expert),
):
    """List models available on the connected Ollama instance. Expert-only."""
    models = await AIProviderService.list_ollama_models()
    return [
        OllamaModelResponse(
            name=m.get("name", m.get("model", "unknown")),
            size=m.get("size"),
            modified_at=m.get("modified_at"),
            digest=m.get("digest"),
        )
        for m in models
    ]
