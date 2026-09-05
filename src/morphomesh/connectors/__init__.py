"""
MorphoMesh: Open-Source Connectors Integration Hub.

Exports unified adapter connectors bridging leading open-source foundation models
into the MorphoMesh MCP ecosystem:
  - Microsoft TRELLIS.2 (trellis_connector)
  - 3DAnimals / SMAL (animals3d_connector)
  - anyCreature Engine (anycreature_connector)
  - MeshAnything V2 (meshanything_connector)
  - Tencent Hunyuan3D-2.1 (hunyuan_connector)
"""

from __future__ import annotations

from morphomesh.connectors.base import (
    BaseConnector,
    CircuitBreakerState,
    ConnectorStatus,
    DependencyCheckResult,
    DependencyStatus,
    HealthCheckResult,
    HealthStatus,
    PBRTextureMaps,
)
from morphomesh.connectors.registry import (
    CircuitBreaker,
    ConnectorRegistry,
    get_connector_registry,
)
from morphomesh.connectors.trellis_connector import (
    TrellisConfig,
    TrellisConnector,
    TrellisInput,
    TrellisOutput,
)
from morphomesh.connectors.animals3d_connector import (
    RX_90_SMAL_TO_BLENDER,
    SMAL_TO_RIGIFY_WOLF,
    AnimalPoseInput,
    Animals3DConnector,
    Animals3DOutput,
    Landmark3D,
    RigifyMappingConfig,
    RigifyMappingOutput,
    SMALParams,
    transform_smal_to_blender,
)
from morphomesh.connectors.anycreature_connector import (
    AnimationBinding,
    AnyCreatureConnector,
    AnyCreatureOutput,
    BodyGraph,
    BodyPart,
    CreaturePromptSpec,
    LimbSpec,
)
from morphomesh.connectors.meshanything_connector import (
    MeshAnythingConnector,
    MeshAnythingInput,
    MeshAnythingOutput,
    RetopologyConfig,
)
from morphomesh.connectors.hunyuan_connector import (
    HunyuanConfig,
    HunyuanConnector,
    HunyuanInput,
    HunyuanOutput,
)

__all__ = [
    # Base Framework & Schemas
    "BaseConnector",
    "CircuitBreaker",
    "CircuitBreakerState",
    "ConnectorRegistry",
    "ConnectorStatus",
    "DependencyCheckResult",
    "DependencyStatus",
    "HealthCheckResult",
    "HealthStatus",
    "PBRTextureMaps",
    "get_connector_registry",
    # TRELLIS
    "TrellisConfig",
    "TrellisConnector",
    "TrellisInput",
    "TrellisOutput",
    # 3DAnimals / SMAL
    "AnimalPoseInput",
    "Animals3DConnector",
    "Animals3DOutput",
    "Landmark3D",
    "RX_90_SMAL_TO_BLENDER",
    "RigifyMappingConfig",
    "RigifyMappingOutput",
    "SMALParams",
    "SMAL_TO_RIGIFY_WOLF",
    "transform_smal_to_blender",
    # anyCreature
    "AnimationBinding",
    "AnyCreatureConnector",
    "AnyCreatureOutput",
    "BodyGraph",
    "BodyPart",
    "CreaturePromptSpec",
    "LimbSpec",
    # MeshAnything V2
    "MeshAnythingConnector",
    "MeshAnythingInput",
    "MeshAnythingOutput",
    "RetopologyConfig",
    # Tencent Hunyuan3D
    "HunyuanConfig",
    "HunyuanConnector",
    "HunyuanInput",
    "HunyuanOutput",
]
