# Comprehensive Analysis & Modularization Plan: Geometry & Inference Subsystems

**Author**: Explorer M1-2  
**Milestone**: Milestone 1: Models, Geometry & Inference Subsystems Modularization  
**Target Source**: `src/morphomesh/inference_adapter.py` (2,358 lines, 98,993 bytes / 96.7 KB)  
**Deliverables**:
- Sub-package `src/morphomesh/geometry/`
- Sub-package `src/morphomesh/inference/`
- Backward-compatible facade `src/morphomesh/inference_adapter.py`

---

## 1. Executive Summary & Problem Boundary

### 1.1 Current Architecture & Deficiencies
`src/morphomesh/inference_adapter.py` is currently the third largest source module in the MorphoMesh codebase (98.9 KB, 2,358 lines). It violates the Single Responsibility Principle (SRP) by combining five fundamentally disparate technical concerns in one monolithic file:
1. **In-Memory 3D Geometric Mesh Topology**: `MeshGeometry` (lines 101–1210, 1,109 lines) storing vertex positions, normals, UV coordinates, triangular/quad faces, and vertex groups.
2. **Binary Buffer Serialization & Exporters**: Wavefront OBJ formatting (lines 1045–1063) and glTF 2.0 binary container (`.glb`) generation with byte alignment, chunk padding, bufferViews, and accessors (lines 1064–1209).
3. **Procedural Biological & Anatomical Synthesis**: Mathematical curves, splayed keratin claws, plantigrade paws, calcaneus heels, articulated ursine cranium/snout/nares, and muscular torso primitives (lines 471–1018).
4. **AI Inference & Foundation Model Connectors**: Abstract base contracts, circuit breaker state machine, cloud API endpoints (Replicate, HuggingFace), multi-connector dispatch (Trellis, Hunyuan, anyCreature, Tripo, Meshy), and offline PIL/numpy PBR texture map baking (lines 1211–2321).
5. **Pluggable Factory Dispatch**: Dynamic instantiation based on execution environment and backend mode strings (lines 2323–2334).

### 1.2 Impact on Coupling and Circular Dependencies
Prior to modularization, foundation model connectors in `src/morphomesh/connectors/` (such as `trellis_connector.py`, `hunyuan_connector.py`, `anycreature_connector.py`, `tripo_connector.py`, `meshy_connector.py`, `meshanything_connector.py`) had to import `MeshGeometry` from `morphomesh.inference_adapter`. Concurrently, `inference_adapter.py` imported these connectors at line 1219 to orchestrate them inside `MockInferenceAdapter`. This created an undesirable bidirectional dependency between connectors and inference adapters.

Extracting `MeshGeometry` into a dedicated leaf subsystem (`src/morphomesh/geometry/`) eliminates this coupling completely.

---

## 2. Target Architecture Overview

```
src/morphomesh/
├── geometry/                    # [NEW] Geometry Subsystem (Leaf package)
│   ├── __init__.py              # Public exports: MeshGeometry, exporters, primitives, quad_utils
│   ├── mesh.py                  # MeshGeometry class (vertex/face container, bounding box)
│   ├── exporters.py             # Binary glTF 2.0 (GLB) and Wavefront OBJ serializers
│   ├── primitives.py            # GeometryPrimitivesMixin (box, cylinder, claw, paw, head, torso)
│   └── quad_utils.py            # Quad dominance metrics, quad capping, quad ellipsoid helpers
├── inference/                   # [NEW] Inference Subsystem
│   ├── __init__.py              # Public exports: all adapter classes, circuit breaker, factory
│   ├── base.py                  # BaseInferenceAdapter, EnhancedCreate3DAssetOutput, CircuitBreaker
│   ├── mock.py                  # MockInferenceAdapter, InferenceAdapter (PIL/numpy & connector dispatch)
│   ├── replicate.py             # ReplicateInferenceAdapter (REST API + CircuitBreaker)
│   ├── huggingface.py           # HuggingFaceInferenceAdapter (Serverless API + CircuitBreaker)
│   └── factory.py               # get_inference_adapter() pluggable factory
└── inference_adapter.py         # [FACADE] 100% backward-compatible re-export module (<80 lines)
```

### Dependency DAG (Strictly Acyclic):
```
morphomesh.models
       │
       ├──► morphomesh.geometry (mesh, primitives, exporters, quad_utils)
       │         │
       │         ├──► morphomesh.connectors
       │         │           │
       ▼         ▼           ▼
morphomesh.inference.base ──► morphomesh.inference.mock ──► morphomesh.inference.replicate
                                        │               ──► morphomesh.inference.huggingface
                                        ▼                                │
                              morphomesh.inference.factory ◄─────────────┘
                                        │
                                        ▼
                              morphomesh.inference (package __init__)
                                        │
                                        ▼
                              morphomesh.inference_adapter (backward-compatible facade)
```

---

## 3. Subsystem 1: Geometry Decomposition Plan (`src/morphomesh/geometry/`)

### 3.1 `src/morphomesh/geometry/mesh.py`
**Responsibility**: In-memory mesh container maintaining vertex lists, normals, UVs, triangle faces, and named vertex groups.
**Inheritance**: Inherits `GeometryPrimitivesMixin` from `morphomesh.geometry.primitives` to ensure all procedural geometry creation methods are directly accessible on `MeshGeometry` instances.
**Delegation**: Delegates `export_obj` and `export_glb` to `morphomesh.geometry.exporters`.

**Key Methods & Signatures**:
```python
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union
from morphomesh.models import BoundingBox
from morphomesh.geometry.exporters import export_glb, export_obj
from morphomesh.geometry.primitives import GeometryPrimitivesMixin

class MeshGeometry(GeometryPrimitivesMixin):
    """In-memory 3D mesh container supporting procedural generation and GLB/OBJ export."""

    def __init__(self) -> None:
        self.vertices: List[Tuple[float, float, float]] = []
        self.normals: List[Tuple[float, float, float]] = []
        self.uvs: List[Tuple[float, float]] = []
        self.faces: List[Tuple[int, int, int]] = []
        self.vertex_groups: Dict[str, List[int]] = {}

    def add_vertex(
        self,
        pos: Tuple[float, float, float],
        normal: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        uv: Tuple[float, float] = (0.0, 0.0),
    ) -> int: ...

    def add_triangle(self, i0: int, i1: int, i2: int) -> None: ...

    def add_quad(self, i0: int, i1: int, i2: int, i3: int) -> None: ...

    def add_to_vertex_group(self, group_name: str, vertex_indices: Union[int, List[int]]) -> None: ...

    def compute_bounding_box(self) -> BoundingBox: ...

    def export_obj(self, filepath: str) -> None:
        """Export geometry to standard Wavefront .obj file."""
        export_obj(self, filepath)

    def export_glb(self, filepath: str) -> None:
        """Export geometry to standard binary glTF 2.0 (.glb) container."""
        export_glb(self, filepath)
```

### 3.2 `src/morphomesh/geometry/exporters.py`
**Responsibility**: Binary packing and text serialization of 3D geometry.
**Extracted Code**: Lines 1045–1209 of `inference_adapter.py`.
**Key Functions**:
```python
def export_obj(mesh: MeshGeometry, filepath: str) -> None:
    """Export geometry to standard Wavefront .obj file with 1-indexed vertex, normal, UV faces."""
    ...

def export_glb(mesh: MeshGeometry, filepath: str) -> None:
    """
    Export geometry to standard binary glTF 2.0 (.glb) container.
    Constructs 12-byte header (glTF magic, version 2, total length),
    Chunk 0 (JSON metadata with POSITION, NORMAL, TEXCOORD_0 accessors and bufferViews),
    and Chunk 1 (BIN buffer with 4-byte aligned packed float32 and uint16/uint32 indices).
    """
    ...

def pad_4(b: bytes) -> bytes:
    """Pads binary buffer with null bytes to align to a 4-byte boundary."""
    ...
```

### 3.3 `src/morphomesh/geometry/primitives.py`
**Responsibility**: Procedural mathematical primitives and biological/anatomical geometry synthesis.
**Extracted Code**: Lines 131–1018 of `inference_adapter.py`.
**Structure**: `class GeometryPrimitivesMixin` containing:
1. **Basic Geometric Primitives**:
   - `add_box(self, center: Tuple[float, float, float], size: Tuple[float, float, float]) -> None` (6 faces, 24 vertices, 12 triangles, outward normals).
   - `add_cylinder(self, base_center: Tuple[float, float, float], radius: float, height: float, segments: int = 12, axis: str = "Z", cap_ends: bool = False, cap_bottom: Optional[bool] = None, cap_top: Optional[bool] = None) -> None`
   - `add_sphere(self, center: Tuple[float, float, float], radius: float, rings: int = 12, sectors: int = 16) -> None`
   - `add_ellipsoid(self, center: Tuple[float, float, float], radii: Tuple[float, float, float], rings: int = 8, sectors: int = 12) -> List[int]`
   - `add_cone(self, base_center: Tuple[float, float, float], apex: Tuple[float, float, float], base_radius: float, segments: int = 8) -> List[int]`
2. **Biological & Anatomical Procedural Primitives**:
   - `add_curved_claw(self, base_pos: Tuple[float, float, float], forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0), downward_dir: Tuple[float, float, float] = (0.0, 0.0, -1.0), length: float = 0.12, base_radius: float = 0.025, curve_factor: float = 0.45, segments: int = 6, radial_segments: int = 8, splay_dir: Optional[Tuple[float, float, float]] = None, splay_factor: float = 0.0) -> List[int]`
   - `add_plantigrade_paw(self, heel_pos: Tuple[float, float, float], forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0), is_front: bool = False, scale: float = 1.0) -> Dict[str, List[int]]`
   - `add_articulated_head(self, head_center: Tuple[float, float, float], forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0), scale: float = 1.0) -> Dict[str, List[int]]`
   - `add_anatomical_torso(self, center: Tuple[float, float, float], forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0), scale: float = 1.0) -> Dict[str, List[int]]`

### 3.4 `src/morphomesh/geometry/quad_utils.py`
**Responsibility**: Quad mesh topology metrics and quad capping utilities consolidated from `human_generator.py` and test harnesses.
**Key Functions**:
```python
def compute_quad_metrics(mesh: MeshGeometry) -> Tuple[int, int, float]:
    """
    Computes quad dominance ratio from mesh faces.
    Identifies pairs of triangles representing quad faces and returns (quad_count, tri_count, quad_ratio).
    """
    ...

def add_quad_cap(mesh: MeshGeometry, ring_indices: List[int], flip_normal: bool = False) -> None:
    """Caps an even-sided circular ring of N vertices with pure quad strips ((N-2)//2 quads)."""
    ...

def add_quad_ellipsoid(
    mesh: MeshGeometry,
    center: Tuple[float, float, float],
    radii: Tuple[float, float, float],
    rings: int = 4,
    sectors: int = 8,
    flip_normals: bool = False,
) -> List[int]:
    """Synthesizes quad-dominant 3D ellipsoid with quad strips between latitude rings."""
    ...
```

### 3.5 `src/morphomesh/geometry/__init__.py`
**Exports**:
```python
from morphomesh.geometry.exporters import export_glb, export_obj
from morphomesh.geometry.mesh import MeshGeometry
from morphomesh.geometry.primitives import GeometryPrimitivesMixin
from morphomesh.geometry.quad_utils import add_quad_cap, add_quad_ellipsoid, compute_quad_metrics

__all__ = [
    "MeshGeometry",
    "GeometryPrimitivesMixin",
    "export_obj",
    "export_glb",
    "compute_quad_metrics",
    "add_quad_cap",
    "add_quad_ellipsoid",
]
```

---

## 4. Subsystem 2: Inference Decomposition Plan (`src/morphomesh/inference/`)

### 4.1 `src/morphomesh/inference/base.py`
**Responsibility**: Abstract contracts, circuit breaker state machine, and enhanced asset telemetry schema.
**Extracted Code**: Lines 58–95, 1282–1295, 2217–2247 of `inference_adapter.py`.
**Key Classes**:
1. `BaseInferenceAdapter(ABC)`:
   - `generate_concept(request: GenerateConceptInput) -> GenerateConceptOutput` (abstract)
   - `generate_3d_asset(request: Create3DAssetInput) -> Create3DAssetOutput` (abstract)
   - `optimize_topology_with_connector(mesh_path: str, method: str = "meshanything_v2", target_faces: int = 1500, **kwargs: Any) -> Dict[str, Any]`
   - `create_animal_rig_with_connector(mesh_path: Optional[str] = None, creature_type: str = "quadruped", species: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]`
   - `get_connector_status() -> Dict[str, Any]`
2. `EnhancedCreate3DAssetOutput(Create3DAssetOutput)`:
   - Pydantic v2 model holding `pbr_textures`, `connector_telemetry`, `source_connector`, `execution_time_seconds`.
3. `CircuitBreaker`:
   - In-memory circuit breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) tracking consecutive failures and recovery timeout.

### 4.2 `src/morphomesh/inference/mock.py`
**Responsibility**: Zero-VRAM offline procedural synthesis, Gemini API concept generation with PIL/numpy fallback, open-source connector routing, and PBR texture map baking.
**Extracted Code**: Lines 1296–2216 and 2312–2321 of `inference_adapter.py`.
**Key Classes**:
1. `MockInferenceAdapter(BaseInferenceAdapter)`:
   - `generate_concept`: Dispatches to `_generate_concept_via_gemini` or `_generate_concept_mock`.
   - `generate_turnaround_sheet`, `synthesize_textures_with_gemini`.
   - `generate_3d_asset`: Dispatches to connectors (`_generate_via_trellis`, `_generate_via_hunyuan`, `_generate_via_anycreature`, `_generate_via_tripo`, `_generate_via_meshy`) or `_generate_3d_asset_mock`.
   - `_generate_3d_asset_mock`: Builds procedural creature via `MeshGeometry()` and exports `.glb`/`.obj`.
   - `_synthesize_pbr_textures`: Synthesizes Albedo (RGB), Normal (tangent-space RGB), Roughness (grayscale L), and Metallic (grayscale L) PNG maps.
   - `optimize_topology_with_connector` and `_fallback_retopology`.
   - `create_animal_rig_with_connector` and `_fallback_animal_rig`.
   - `get_connector_status`.
2. `InferenceAdapter(MockInferenceAdapter)`:
   - Production unified adapter alias orchestrating connectors with procedural fallback.

### 4.3 `src/morphomesh/inference/replicate.py`
**Responsibility**: Replicate cloud API adapter with CircuitBreaker resilience and MockInferenceAdapter fallback.
**Extracted Code**: Lines 2248–2280 of `inference_adapter.py`.
**Class**: `ReplicateInferenceAdapter(BaseInferenceAdapter)`

### 4.4 `src/morphomesh/inference/huggingface.py`
**Responsibility**: Hugging Face Serverless API adapter with CircuitBreaker resilience and MockInferenceAdapter fallback.
**Extracted Code**: Lines 2281–2311 of `inference_adapter.py`.
**Class**: `HuggingFaceInferenceAdapter(BaseInferenceAdapter)`

### 4.5 `src/morphomesh/inference/factory.py`
**Responsibility**: Dynamic instantiation of inference adapter by backend mode name.
**Extracted Code**: Lines 2323–2334 of `inference_adapter.py`.
**Function**:
```python
def get_inference_adapter(mode: str = "mock", **kwargs: Any) -> BaseInferenceAdapter:
    """
    Pluggable factory instantiating configured inference adapter.
    Modes:
      - 'mock', 'production', 'connectors', 'unified', 'default' -> InferenceAdapter
      - 'replicate' -> ReplicateInferenceAdapter
      - 'huggingface', 'hf' -> HuggingFaceInferenceAdapter
      - fallback -> InferenceAdapter
    """
```

### 4.6 `src/morphomesh/inference/__init__.py`
**Exports**:
```python
from morphomesh.inference.base import (
    BaseInferenceAdapter,
    CircuitBreaker,
    EnhancedCreate3DAssetOutput,
)
from morphomesh.inference.factory import get_inference_adapter
from morphomesh.inference.huggingface import HuggingFaceInferenceAdapter
from morphomesh.inference.mock import InferenceAdapter, MockInferenceAdapter
from morphomesh.inference.replicate import ReplicateInferenceAdapter

__all__ = [
    "BaseInferenceAdapter",
    "CircuitBreaker",
    "EnhancedCreate3DAssetOutput",
    "MockInferenceAdapter",
    "InferenceAdapter",
    "ReplicateInferenceAdapter",
    "HuggingFaceInferenceAdapter",
    "get_inference_adapter",
]
```

---

## 5. Backward-Compatible Facade: `src/morphomesh/inference_adapter.py`

To guarantee 100% backward compatibility across all 23 test suites and 15 internal modules without modifying any existing callers, `src/morphomesh/inference_adapter.py` will become a clean facade re-exporting:
1. `MeshGeometry` from `morphomesh.geometry`
2. All inference classes and factory from `morphomesh.inference`
3. All connector classes from `morphomesh.connectors`

### Facade Code Blueprint:
```python
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

# Re-export Connectors (Preserving connector symbols previously in inference_adapter.__all__)
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
    "BaseInferenceAdapter",
    "MeshGeometry",
    "MockInferenceAdapter",
    "InferenceAdapter",
    "EnhancedCreate3DAssetOutput",
    "CircuitBreaker",
    "ReplicateInferenceAdapter",
    "HuggingFaceInferenceAdapter",
    "get_inference_adapter",
    "get_connector_registry",
    "TrellisConnector",
    "HunyuanConnector",
    "AnyCreatureConnector",
    "MeshAnythingConnector",
    "Animals3DConnector",
    "GeminiImageConnector",
    "TripoConnector",
    "MeshyConnector",
]
```

---

## 6. Comprehensive Caller & Test Invariance Matrix

Every caller in the repository has been audited and cataloged below to ensure absolute import and behavioral invariance:

| # | File Path | Imported Symbols | Verification Criterion |
|---|---|---|---|
| 1 | `tests/test_inference_adapter.py` | `CircuitBreaker`, `HuggingFaceInferenceAdapter`, `MeshGeometry`, `MockInferenceAdapter`, `ReplicateInferenceAdapter`, `get_inference_adapter` | 28 unit tests pass identically |
| 2 | `tests/test_connectors.py` | `EnhancedCreate3DAssetOutput`, `MeshGeometry`, `get_inference_adapter` | Connector telemetry & geometry pass |
| 3 | `tests/test_gemini_image_connector.py` | `InferenceAdapter`, `MockInferenceAdapter`, `get_inference_adapter` | Gemini prompt enhancement passes |
| 4 | `tests/test_tripo_connector.py` | `EnhancedCreate3DAssetOutput`, `MeshGeometry`, `get_inference_adapter` | Tripo GLB metrics parsing passes |
| 5 | `tests/test_meshy_connector.py` | `EnhancedCreate3DAssetOutput`, `MeshGeometry`, `get_inference_adapter` | Meshy polling & task tasks pass |
| 6 | `tests/test_anatomy_generator.py` | `MeshGeometry`, `MockInferenceAdapter` | Claws, plantigrade paws, head, torso pass |
| 7 | `tests/test_m1_claw_and_paw_stress.py` | `MeshGeometry` | 10,000 randomized claw orientations pass |
| 8 | `tests/test_m1_challenger_1_anatomy_contours.py` | `MeshGeometry` | Teardrop bust, IMF depth, WHR pass |
| 9 | `tests/test_m1_challenger_2_stress.py` | `MeshGeometry` | Quad dominance & exact metrics pass |
| 10 | `tests/test_m1_anatomical_base_mold.py` | `MeshGeometry` | Base mold loading and topology pass |
| 11 | `tests/test_empiric_m1_anatomy.py` | `MeshGeometry` | Manifoldness & edge incidence pass |
| 12 | `tests/test_adversarial_human_generator.py` | `MeshGeometry` | Zero degenerate face checks pass |
| 13 | `tests/test_adversarial_human_m3.py` | `MeshGeometry` | Wardrobe mesh analysis passes |
| 14 | `tests/test_challenger_m2_sash.py` | `MeshGeometry` | Sash & bow clearance pass |
| 15 | `tests/test_challenger_m2_empirical.py` | `MeshGeometry` | Empirical cloth penetration tests pass |
| 16 | `tests/test_challenger_m2_adversarial_cloth.py` | `MeshGeometry` | Cloth fold curvature checks pass |
| 17 | `tests/test_wardrobe_m2.py` | `MeshGeometry` | Garments & sandals pass |
| 18 | `tests/test_e2e_human_anatomy.py` | `MeshGeometry` | End-to-end human assembly passes |
| 19 | `tests/run_m1_challenger_2_audit.py` | `MeshGeometry` | Quad metrics audit script passes |
| 20 | `tests/test_materials_and_armor.py` | `MeshGeometry` | Armor mounting indices pass |
| 21 | `tests/test_m3_adversarial_materials_and_armor.py` | `MeshGeometry` | PBR material assignment passes |
| 22 | `tests/test_m4_adversarial_geometry_stress.py` | `MeshGeometry` | Multi-resolution stress testing passes |
| 23 | `tests/conftest.py` | `MeshGeometry`, `MockInferenceAdapter` | Shared test fixtures & temp storage pass |
| 24 | `src/morphomesh/__init__.py` | `BaseInferenceAdapter`, `MockInferenceAdapter`, `ReplicateInferenceAdapter`, `HuggingFaceInferenceAdapter`, `get_inference_adapter` | Top-level package re-exports pass |
| 25 | `src/morphomesh/server.py` | `BaseInferenceAdapter`, `get_inference_adapter` | MCP server tool registrations pass |
| 26 | `src/morphomesh/creature_generator.py` | `MeshGeometry` | Procedural creature mesh creation passes |
| 27 | `src/morphomesh/human_generator.py` | `MeshGeometry` | Digital human mesh synthesis passes |
| 28 | `src/morphomesh/human_rigging.py` | `MeshGeometry` | 163 DEF bone binding passes |
| 29 | `src/morphomesh/human_grooming.py` | `MeshGeometry` | Spline & ribbon hair curves pass |
| 30 | `src/morphomesh/wardrobe.py` | `MeshGeometry` | Procedural clothing meshes pass |
| 31 | `src/morphomesh/character_assembler.py` | `MeshGeometry` | YuNianAn character assembly passes |
| 32 | `src/morphomesh/armor.py` | `MeshGeometry` | Procedural armor plating passes |
| 33 | `src/morphomesh/connectors/*.py` (6 files) | `MeshGeometry` | Foundation model 3D inputs/outputs pass |

---

## 7. Step-by-Step Implementation Sequence

The implementer (worker) should execute the refactoring in this exact sequence:

1. **Create Sub-package Directories**:
   - `mkdir src/morphomesh/geometry`
   - `mkdir src/morphomesh/inference`

2. **Populate Geometry Subsystem**:
   - Create `src/morphomesh/geometry/exporters.py` (OBJ and GLB binary writers).
   - Create `src/morphomesh/geometry/primitives.py` (`GeometryPrimitivesMixin` with box, cylinder, sphere, ellipsoid, cone, claw, paw, head, torso).
   - Create `src/morphomesh/geometry/quad_utils.py` (`compute_quad_metrics`, `add_quad_cap`, `add_quad_ellipsoid`).
   - Create `src/morphomesh/geometry/mesh.py` (`MeshGeometry` class inheriting mixin and delegating exports).
   - Create `src/morphomesh/geometry/__init__.py` (clean re-exports).
   - *Verification*: `python -c "from morphomesh.geometry import MeshGeometry; g = MeshGeometry(); g.add_box((0,0,0), (1,1,1)); print(len(g.vertices))"`

3. **Populate Inference Subsystem**:
   - Create `src/morphomesh/inference/base.py` (`BaseInferenceAdapter`, `EnhancedCreate3DAssetOutput`, `CircuitBreaker`).
   - Create `src/morphomesh/inference/mock.py` (`MockInferenceAdapter` with connector routing + PIL PBR synthesis, `InferenceAdapter`).
   - Create `src/morphomesh/inference/replicate.py` (`ReplicateInferenceAdapter`).
   - Create `src/morphomesh/inference/huggingface.py` (`HuggingFaceInferenceAdapter`).
   - Create `src/morphomesh/inference/factory.py` (`get_inference_adapter`).
   - Create `src/morphomesh/inference/__init__.py` (clean re-exports).
   - *Verification*: `python -c "from morphomesh.inference import get_inference_adapter; a = get_inference_adapter('mock'); print(type(a))"`

4. **Refactor Facade Module**:
   - Replace `src/morphomesh/inference_adapter.py` with the backward-compatible facade re-exporting `MeshGeometry`, all adapter symbols, and connector symbols.
   - *Verification*: `python -c "from morphomesh.inference_adapter import MeshGeometry, MockInferenceAdapter, get_inference_adapter; print('Facade OK')"`

5. **Run Comprehensive Verification Test Suite**:
   - Run `pytest tests/test_inference_adapter.py` (must pass 28/28).
   - Run `pytest tests/test_connectors.py tests/test_gemini_image_connector.py tests/test_tripo_connector.py tests/test_meshy_connector.py` (must pass 189/189).
   - Run `pytest tests/test_anatomy_generator.py tests/test_m1_claw_and_paw_stress.py` (must pass 39/39).
   - Run `pytest tests/test_wardrobe_m2.py tests/test_materials_and_armor.py` (must pass 37/37).
