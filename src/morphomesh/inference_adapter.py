"""
MorphoMesh: AI Inference Adapter Facade Module.

Backward-compatible facade module re-exporting all symbols from
morphomesh.geometry, morphomesh.inference, and morphomesh.connectors.
Preserves 100% compatibility for external callers and existing test suites.
"""
from __future__ import annotations

# Re-export Geometry
from morphomesh.geometry import MeshGeometry

# Re-export Inference Subsystem
from morphomesh.inference import (
    BaseInferenceAdapter,
    CircuitBreaker,
    EnhancedCreate3DAssetOutput,
    HuggingFaceInferenceAdapter,
    InferenceAdapter,
    MockInferenceAdapter,
    ReplicateInferenceAdapter,
    get_inference_adapter,
)

# Re-export Connectors
try:
    from morphomesh.connectors import (
        AnimalPoseInput,
        Animals3DConnector,
        AnyCreatureConnector,
        ConnectorRegistry,
        CreaturePromptSpec,
        GeminiImageConfig,
        GeminiImageConnector,
        GeminiImageInput,
        GeminiImageOutput,
        HunyuanConnector,
        HunyuanInput,
        MeshAnythingConnector,
        MeshAnythingInput,
        MeshyConfig,
        MeshyConnector,
        MeshyInput,
        MeshyOutput,
        RetopologyConfig,
        TrellisConnector,
        TrellisInput,
        TripoConfig,
        TripoConnector,
        TripoInput,
        TripoOutput,
        get_connector_registry,
    )
except (ImportError, ModuleNotFoundError):
    try:
        from connectors import (  # type: ignore[no-redef]
            AnimalPoseInput,
            Animals3DConnector,
            AnyCreatureConnector,
            ConnectorRegistry,
            CreaturePromptSpec,
            GeminiImageConfig,
            GeminiImageConnector,
            GeminiImageInput,
            GeminiImageOutput,
            HunyuanConnector,
            HunyuanInput,
            MeshAnythingConnector,
            MeshAnythingInput,
            MeshyConfig,
            MeshyConnector,
            MeshyInput,
            MeshyOutput,
            RetopologyConfig,
            TrellisConnector,
            TrellisInput,
            TripoConfig,
            TripoConnector,
            TripoInput,
            TripoOutput,
            get_connector_registry,
        )
    except (ImportError, ModuleNotFoundError):
        get_connector_registry = None  # type: ignore[assignment]

__all__ = [
    "Animals3DConnector",
    "AnyCreatureConnector",
    "BaseInferenceAdapter",
    "CircuitBreaker",
    "EnhancedCreate3DAssetOutput",
    "GeminiImageConnector",
    "HuggingFaceInferenceAdapter",
    "HunyuanConnector",
    "InferenceAdapter",
    "MeshAnythingConnector",
    "MeshGeometry",
    "MeshyConnector",
    "MockInferenceAdapter",
    "ReplicateInferenceAdapter",
    "TrellisConnector",
    "TripoConnector",
    "get_connector_registry",
    "get_inference_adapter",
]
