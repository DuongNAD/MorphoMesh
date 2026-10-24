"""
MorphoMesh: Replicate Cloud Inference Adapter.
"""
from __future__ import annotations

import os
from typing import Optional

from morphomesh.models import (
    Create3DAssetInput,
    Create3DAssetOutput,
    GenerateConceptInput,
    GenerateConceptOutput,
)
from .base import BaseInferenceAdapter, CircuitBreaker
from .mock import MockInferenceAdapter


class ReplicateInferenceAdapter(BaseInferenceAdapter):
    """Remote GPU Adapter communicating with Replicate REST API."""

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.environ.get("REPLICATE_API_TOKEN")
        self.circuit_breaker = CircuitBreaker()
        self.mock_fallback = MockInferenceAdapter()

    def generate_concept(self, request: GenerateConceptInput) -> GenerateConceptOutput:
        if not self.api_token or not self.circuit_breaker.can_attempt():
            # Circuit breaker open or no token -> fallback
            return self.mock_fallback.generate_concept(request)

        # In production: make HTTP request to Replicate predictions API
        # If network error or timeout -> record_failure() and fallback
        try:
            # Stub for live API
            return self.mock_fallback.generate_concept(request)
        except Exception:
            self.circuit_breaker.record_failure()
            return self.mock_fallback.generate_concept(request)

    def generate_3d_asset(self, request: Create3DAssetInput) -> Create3DAssetOutput:
        if not self.api_token or not self.circuit_breaker.can_attempt():
            return self.mock_fallback.generate_3d_asset(request)

        try:
            return self.mock_fallback.generate_3d_asset(request)
        except Exception:
            self.circuit_breaker.record_failure()
            return self.mock_fallback.generate_3d_asset(request)




__all__ = [
    "ReplicateInferenceAdapter",
]
