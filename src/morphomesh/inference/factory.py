"""
MorphoMesh: Inference Adapter Pluggable Factory.
"""
from __future__ import annotations

from typing import Any

from .base import BaseInferenceAdapter
from .huggingface import HuggingFaceInferenceAdapter
from .mock import InferenceAdapter
from .replicate import ReplicateInferenceAdapter


def get_inference_adapter(mode: str = "mock", **kwargs: Any) -> BaseInferenceAdapter:
    """Pluggable factory instantiating configured inference adapter."""
    m = mode.lower()
    if m in ("mock", "production", "connectors", "unified", "default"):
        return InferenceAdapter(**kwargs)
    elif m == "replicate":
        return ReplicateInferenceAdapter(**kwargs)
    elif m in ("huggingface", "hf"):
        return HuggingFaceInferenceAdapter(**kwargs)
    else:
        return InferenceAdapter(**kwargs)




__all__ = [
    "get_inference_adapter",
]
