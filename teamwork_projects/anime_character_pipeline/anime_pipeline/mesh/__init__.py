"""
Anime Character Pipeline: Mesh Synthesis & Anatomy Topology (Milestone 1).

Provides:
- AnimeMeshConfig: Parameter configuration for modular anime character mesh synthesis.
- AnimeSubMesh: Discrete sub-mesh representation with quad topology and boundary metadata.
- AnimeModelResult: Complete model container for 7 modular sub-meshes with multi-format export.
- AnimeMeshGenerator: 7-component modular mesh generator.
- TopologyValidator: 100% 2-manifold quad topology and defect auditor.
- HingeLoopValidator: Multi-loop concentric deformation zone auditor.
- NormalHarmonizer: Seam normal harmonizer for seamless cel-shading.
- TopologyCleaner: Mesh repair and quad capping utilities.
"""

from .generator import (
    AnimeMeshConfig,
    AnimeMeshGenerator,
    AnimeModelResult,
    AnimeSubMesh,
)
from .topology_cleaner import (
    HingeLoopValidator,
    NormalHarmonizer,
    TopologyCleaner,
    TopologyReport,
    TopologyValidator,
)

__all__ = [
    "AnimeMeshConfig",
    "AnimeSubMesh",
    "AnimeModelResult",
    "AnimeMeshGenerator",
    "TopologyReport",
    "TopologyValidator",
    "HingeLoopValidator",
    "NormalHarmonizer",
    "TopologyCleaner",
]
