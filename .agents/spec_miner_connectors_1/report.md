# MorphoMesh Phase 2: Open-Source Integration Hub
## Architecture Specification Report: Production Connectors & Test Harness (R2 & R3)

**Author**: Connector Architecture Spec Miner (`spec_miner_connectors_1`)  
**Date**: 2026-09-05  
**Version**: 1.0.0  
**Status**: Authoritative Specification  
**Target Package**: `src/morphomesh/connectors/`, `tests/test_connectors.py`, `examples/open_source_pipeline_demo.py`  

---

## Executive Summary

Phase 2 of MorphoMesh introduces the **Open-Source Integration Hub**, expanding the core pipeline with dedicated, production-grade adapter connectors to bridge 5 state-of-the-art (SOTA) open-source frameworks into the MorphoMesh MCP ecosystem:
1. **Microsoft TRELLIS / TRELLIS.2**: High-fidelity structured O-Voxel 3D diffusion and decoupled 4-channel PBR texture baking.
2. **3DAnimals / MagicPony / SMAL**: 35-joint parametric quadruped anatomical estimation, coordinate system conversion, and Blender Rigify metarig binding.
3. **anyCreature Engine**: Procedural natural-language body graph specification, parametric spline/metaball lofting, and real-time gait/animation binding.
4. **MeshAnything V2**: Autoregressive adjacent mesh tokenization (AMT) for artist-like quad retopology strictly constrained under 1600 faces.
5. **Tencent Hunyuan3D-2.1**: Two-stage remote DiT geometry generation and high-resolution PBR surface synthesis.

This specification provides the exhaustive blueprints for:
- The unified **Connector Framework** (`registry.py`) with life-cycle hooks (`initialize`, `health_check`, `check_dependencies`, `execute`, `close`), a three-state **Circuit Breaker** (`CLOSED`, `OPEN`, `HALF_OPEN`), and a centralized **Connector Registry**.
- All 5 specialized connectors with complete **Pydantic v2 schemas**, execution flows, transformation matrices, and fallback routes.
- Seamless integration into `InferenceAdapter` and FastMCP tools in `server.py`.
- A 100% offline, zero-network, deterministic **Test Harness** (`tests/test_connectors.py`) and an executable **Pipeline Demo** (`examples/open_source_pipeline_demo.py`).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Framework | BaseConnector Abstract Contract | Base class defining standard connector life-cycle methods | Config parameters | BaseConnector instance | Abstract method enforcement on subclassing | R2 Specification |
| 2 | Framework | CircuitBreaker Pattern | Fault-tolerance pattern with failure threshold, reset timeout, and fallback handler | Function call, failure counts, timeouts | Execution result or fallback | Trips to OPEN on threshold, returns fallback or raises | R2 Specification |
| 3 | Framework | ConnectorRegistry Discovery | Automatic discovery, instantiation, and singleton management of connectors | Connector IDs, class types | Connector instances, health dictionaries | Raises KeyError on unregistered ID | R2 Specification |
| 4 | Framework | HealthCheck & DependencyCheck | Live diagnostics verifying binary presence, CUDA/MPS capabilities, and service latency | Connector instance | `HealthStatus`, `DependencyStatus` | Returns degraded/unhealthy status models | R2 Specification |
| 5 | TRELLIS | TrellisConnector | Ingests concept image, synthesizes 3D mesh via O-Voxel latents and bakes 4 PBR texture maps | `TrellisInput` (image, seed, PBR config) | `TrellisOutput` (GLB path, vertex/face stats, `PBRTextureMaps`) | Falls back to mock or raises `ERR_INFERENCE_FAILED` | `trellis_connector.py` |
| 6 | 3DAnimals | Animals3DConnector | Extracts SMAL $\beta, \theta$ parameters, transforms coords to Blender, and aligns Rigify Wolf | `AnimalPoseInput` (image/mesh, species) | `Animals3DOutput` (landmarks, SMAL params, Rigify mapping, script) | Falls back to canonical quadruped prior | `animals3d_connector.py` |
| 7 | SMAL Math | Coordinate Transformation Matrix | Maps PyTorch3D/OpenCV coords $[X, Y, Z]$ to Blender $[X, -Z, Y]$ | 3D vectors or landmark matrices | Transformed Blender coordinates | Validates dimension $N \times 3$ | `animals3d_connector.py` |
| 8 | anyCreature | AnyCreatureConnector | Parses prompts into modular `BodyGraph`, generates procedural meshes and binds gaits | `CreaturePromptSpec` or raw prompt | `AnyCreatureOutput` (JSON spec, mesh path, animation clips) | Emits standard biped/quadruped default graph | `anycreature_connector.py` |
| 9 | MeshAnything | MeshAnythingConnector | Autoregressive quad retopology conditioned on strict face budget ($N \le 1600$) | `MeshAnythingInput` (mesh path, target count) | `MeshAnythingOutput` (optimized mesh, quad ratio, face count) | Automatically falls back to Blender QuadriFlow | `meshanything_connector.py` |
| 10| Hunyuan3D | HunyuanConnector | Remote client communicating with Hunyuan3D-2.1 DiT & Paint-PBR containers | `HunyuanInput` (image, PBR flags) | `HunyuanOutput` (high-res GLB, 4K PBR maps) | Circuit breaker trips to mock generator | `hunyuan_connector.py` |
| 11| Integration | ConnectorInferenceAdapter | Subclass of `BaseInferenceAdapter` wrapping `ConnectorRegistry` for unified execution | MCP input models (`Create3DAssetInput`) | MCP output models (`Create3DAssetOutput`) | Seamless fallback to `MockInferenceAdapter` | `inference_adapter.py` |
| 12| Server | MCP Tool Routing | FastMCP tools in `server.py` routing backend requests to appropriate connectors | Tool call arguments | JSON-serializable dictionaries | Returns MCP `ToolError` with standard code | `server.py` |
| 13| Testing | Offline Mock Harness | 100% network-free unit test suite verifying schemas, math matrices, and circuit breakers | Pytest test runner | Exit code 0, 0 failures | Pytest assertion errors | `tests/test_connectors.py` |
| 14| Demo | E2E Open Source Pipeline Demo | Standalone runnable Python demonstration script showing end-to-end integration | Command-line arguments | Formatted pipeline execution logs | Catches exceptions with graceful reporting | `examples/demo.py` |

---

## Edge Cases

| # | Feature | Input | Observed / Specified Behavior |
|---|---------|-------|-------------------------------|
| 1 | CircuitBreaker | Service throws 3 consecutive HTTP 503 errors | Breaker transitions from `CLOSED` to `OPEN`. Subsequent calls bypass remote service immediately, executing fallback in <1ms without timeout latency. |
| 2 | CircuitBreaker | Call attempted after `recovery_timeout` (60s) has elapsed | Breaker enters `HALF_OPEN` and permits a single probe request. If probe succeeds, breaker transitions to `CLOSED` and resets failure count. If probe fails, transitions back to `OPEN`. |
| 3 | TrellisConnector | Input image has no alpha channel and background is noisy | Connector triggers automatic foreground segmentation fallback (`rembg` / Otsu thresholding), isolates creature silhouette, and normalizes aspect ratio before generation. |
| 4 | Animals3DConnector | SMAL joint coordinates contain NaN or infinite values | Sanitizer rejects invalid coordinates, triggers warning log, and substitutes canonical rest-pose SMAL landmark offsets based on the selected species template. |
| 5 | Animals3DConnector | Metarig alignment with inverted bone vector ($\vec{v}_{\text{tail}} \approx \vec{v}_{\text{head}}$) | `bone.align_roll` guard checks $\lVert \vec{v}_{\text{tail}} - \vec{v}_{\text{head}} \rVert < 10^{-4}$, applies minimum bone length clamping ($0.01$m) to prevent Blender zero-length bone collapse. |
| 6 | AnyCreatureConnector | Prompt describes contradictory or nonsensical creature ("a creature with 0 legs and 100 heads") | Body graph compiler enforces physiological constraints: limits head count to maximum 3, enforces minimum root pelvis existence, sets valid bounding bounds. |
| 7 | MeshAnythingConnector | Input mesh has non-manifold edges, self-intersections, or 200,000+ vertices | Connector executes preprocessing clean pass: decimates to 50,000 faces, repairs non-manifold geometry, then passes manifold envelope to retopology model. |
| 8 | MeshAnythingConnector | Remote MeshAnything endpoint unreachable or times out (>90s) | Circuit breaker catches `TimeoutError`, triggers local Blender QuadriFlow fallback, returning valid quad mesh without terminating the pipeline. |
| 9 | HunyuanConnector | Remote API returns incomplete PBR channel set (e.g. Albedo present, but Roughness missing) | Connector synthesizes default PBR maps (Roughness=0.6 uniform, Metallic=0.0 uniform, Tangent Normal=[128, 128, 255]) to guarantee complete Principled BSDF node setup. |
| 10| ConnectorRegistry | Request for unregistered connector name (e.g. `registry.get("invalid_model")`) | Raises explicit `MorphoMeshException` with code `ERR_INVALID_ARGUMENT` and clear listing of available registered connector IDs. |

---

## 1. Connector Framework Architecture (`registry.py`)

### 1.1 Architectural Pattern & Component Diagram

```
+-----------------------------------------------------------------------------------+
|                              ConnectorRegistry                                    |
|                                                                                   |
|  - _registry: Dict[str, Type[BaseConnector]]                                      |
|  - _instances: Dict[str, BaseConnector]                                           |
|                                                                                   |
|  + register(cls: Type[BaseConnector]) -> Type[BaseConnector]                     |
|  + get(connector_id: str, auto_initialize: bool = True) -> BaseConnector         |
|  + list_connectors() -> List[str]                                                 |
|  + health_check_all() -> Dict[str, HealthStatus]                                  |
|  + check_dependencies_all() -> Dict[str, DependencyStatus]                        |
|  + reset_all() -> None                                                            |
+------------------------------------------+----------------------------------------+
                                           |
                   +-----------------------+-----------------------+
                   |                       |                       |
                   v                       v                       v
        +---------------------+ +---------------------+ +---------------------+
        |   TrellisConnector  | | Animals3DConnector  | | AnyCreatureConnector|
        +---------------------+ +---------------------+ +---------------------+
                   |                       |                       |
                   +-----------------------+-----------------------+
                   |
                   v
        +-------------------------------------------------------------+
        |                     BaseConnector (ABC)                     |
        |                                                             |
        |  - connector_id: str                                        |
        |  - circuit_breaker: CircuitBreaker                          |
        |  - is_initialized: bool                                     |
        |                                                             |
        |  + initialize() -> bool                                     |
        |  + health_check() -> HealthStatus                           |
        |  + check_dependencies() -> DependencyStatus                 |
        |  + execute(request: Any, **kwargs) -> Any                   |
        |  + close() -> None                                          |
        |  + execute_with_resilience(request: Any, fallback, **kwargs)|
        +------------------------------+------------------------------+
                                       |
                                       v
        +-------------------------------------------------------------+
        |                       CircuitBreaker                        |
        |                                                             |
        |  - state: CircuitBreakerState (CLOSED, OPEN, HALF_OPEN)     |
        |  - failure_count: int                                       |
        |  - failure_threshold: int = 3                               |
        |  - recovery_timeout: float = 60.0                           |
        |                                                             |
        |  + can_attempt() -> bool                                    |
        |  + record_success() -> None                                 |
        |  + record_failure(error: Optional[Exception]) -> None       |
        |  + call(func, *args, fallback=None, **kwargs) -> Any        |
        +-------------------------------------------------------------+
```

### 1.2 Data Schemas & Enumerations

```python
# In src/morphomesh/connectors/registry.py

from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type
from pydantic import BaseModel, Field, ConfigDict


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Literal["healthy", "degraded", "unhealthy", "offline", "unknown"]
    latency_ms: float = 0.0
    last_checked: float = Field(default_factory=time.time)
    message: str = "Operating normally"
    details: Dict[str, Any] = Field(default_factory=dict)


class DependencyStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    satisfied: bool
    missing_packages: List[str] = Field(default_factory=list)
    missing_binaries: List[str] = Field(default_factory=list)
    hardware_supported: bool = True
    vram_available_mb: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
```

### 1.3 `CircuitBreaker` State Machine

```
              +--------------------------+
              |          CLOSED          | <-------------------+
              |  Normal operations       |                     |
              |  failure_count = 0       |                     |
              +--------------------------+                     |
                           |                                   |
           failure_count >= failure_threshold                  |
                           |                                   |
                           v                                   | Probe
              +--------------------------+                     | Success
              |           OPEN           |                     |
              |  Rejects live calls      |                     |
              |  Executes fallback       |                     |
              +--------------------------+                     |
                           |                                   |
              time > recovery_timeout                          |
                           |                                   |
                           v                                   |
              +--------------------------+                     |
              |        HALF_OPEN         | --------------------+
              |  Allows single probe     |
              |  Probe failure -> OPEN   |
              +--------------------------+
```

#### CircuitBreaker Implementation Contract:
- **`__init__(failure_threshold=3, recovery_timeout=60.0, half_open_max_attempts=1)`**: Initializes in `CLOSED` state.
- **`can_attempt() -> bool`**: Returns `True` if `CLOSED`. If `OPEN`, compares `time.time() - last_failure_time > recovery_timeout`; if elapsed, transitions to `HALF_OPEN` and returns `True`. Returns `False` otherwise. If `HALF_OPEN`, returns `True` up to max attempts.
- **`record_success()`**: Resets `failure_count = 0`, sets `state = CircuitBreakerState.CLOSED`.
- **`record_failure(exception=None)`**: Increments `failure_count`. Sets `last_failure_time = time.time()`. If `failure_count >= failure_threshold` or state was `HALF_OPEN`, sets `state = CircuitBreakerState.OPEN`.
- **`trip()` / `reset()`**: Manual overrides for testing and administrative control.
- **`call(func, *args, fallback=None, **kwargs)`**: Executes `func(*args, **kwargs)` if `can_attempt()`. On success, records success and returns result. On failure or if blocked by open breaker, invokes `fallback(*args, **kwargs)` if registered, otherwise raises `MorphoMeshException(ERR_BACKEND_UNAVAILABLE, ...)`.

### 1.4 `BaseConnector` Abstract Base Class

```python
class BaseConnector(ABC):
    """Authoritative base class for all MorphoMesh Phase 2 external adapters."""

    connector_id: str = "base"
    display_name: str = "Base Connector"
    version: str = "1.0.0"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.config = config or {}
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.is_initialized: bool = False
        self._fallback_handler: Optional[Callable[..., Any]] = None

    @abstractmethod
    def initialize(self) -> bool:
        """Allocate resources, verify endpoints, or load weights."""
        pass

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Query connector endpoint or test execution latency."""
        pass

    @abstractmethod
    def check_dependencies(self) -> DependencyStatus:
        """Inspect Python packages, native shared libraries, and hardware."""
        pass

    @abstractmethod
    def execute(self, request: Any, **kwargs) -> Any:
        """Execute primary connector workload."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release allocated handles, sockets, or memory."""
        pass

    def register_fallback(self, handler: Callable[..., Any]) -> None:
        """Attach a fallback handler for resilient execution."""
        self._fallback_handler = handler

    def execute_with_resilience(self, request: Any, **kwargs) -> Any:
        """Execute workload protected by the circuit breaker and fallback."""
        return self.circuit_breaker.call(
            self.execute,
            request,
            fallback=self._fallback_handler,
            **kwargs,
        )
```

### 1.5 `ConnectorRegistry` Class

```python
class ConnectorRegistry:
    """Central registry and lifecycle manager for all MorphoMesh connectors."""

    _registry: Dict[str, Type[BaseConnector]] = {}
    _instances: Dict[str, BaseConnector] = {}

    @classmethod
    def register(cls, connector_cls: Type[BaseConnector]) -> Type[BaseConnector]:
        """Decorator or function to register a connector class."""
        cls._registry[connector_cls.connector_id] = connector_cls
        return connector_cls

    @classmethod
    def get(cls, connector_id: str, auto_initialize: bool = True) -> BaseConnector:
        """Retrieve or lazily instantiate a singleton connector instance."""
        if connector_id not in cls._instances:
            if connector_id not in cls._registry:
                raise MorphoMeshException(
                    code=ERR_INVALID_ARGUMENT,
                    message=f"Connector '{connector_id}' is not registered. Available: {list(cls._registry.keys())}",
                )
            instance = cls._registry[connector_id]()
            if auto_initialize:
                instance.initialize()
            cls._instances[connector_id] = instance
        return cls._instances[connector_id]

    @classmethod
    def list_connectors(cls) -> List[str]:
        return list(cls._registry.keys())

    @classmethod
    def health_check_all(cls) -> Dict[str, HealthStatus]:
        results = {}
        for cid in cls.list_connectors():
            inst = cls.get(cid, auto_initialize=False)
            results[cid] = inst.health_check()
        return results

    @classmethod
    def check_dependencies_all(cls) -> Dict[str, DependencyStatus]:
        results = {}
        for cid in cls.list_connectors():
            inst = cls.get(cid, auto_initialize=False)
            results[cid] = inst.check_dependencies()
        return results

    @classmethod
    def reset_all(cls) -> None:
        """Close all active instances and clean cache (essential for isolated tests)."""
        for inst in cls._instances.values():
            try:
                inst.close()
            except Exception:
                pass
        cls._instances.clear()
```

---

## 2. Microsoft TRELLIS Connector (`trellis_connector.py`)

### 2.1 Technical Role & Architecture
The `TrellisConnector` wraps Microsoft's TRELLIS / TRELLIS.2 3D generative diffusion backbone. It produces structured 3D latents (O-Voxels), extracts a continuous manifold surface representation via Marching Cubes / FlexiCubes, and extracts a complete 4-channel PBR texture set (Albedo, Tangent-Space Normal, Roughness, Metallic) baked to UV coordinates.

### 2.2 Pydantic v2 Schemas

```python
class PBRTextureMaps(BaseModel):
    model_config = ConfigDict(extra="ignore")
    albedo_path: Optional[str] = None
    normal_path: Optional[str] = None
    roughness_path: Optional[str] = None
    metallic_path: Optional[str] = None
    resolution: int = Field(default=2048, ge=512, le=4096)
    color_space_map: Dict[str, str] = Field(
        default_factory=lambda: {
            "albedo": "sRGB",
            "normal": "Non-Color",
            "roughness": "Non-Color",
            "metallic": "Non-Color",
        }
    )


class TrellisConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mode: Literal["mock", "local", "remote"] = "mock"
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: str = "TRELLIS.2-4B"
    sparse_structure_resolution: int = Field(default=1024, ge=512, le=1536)
    slat_steps: int = Field(default=25, ge=10, le=50)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    timeout_seconds: float = Field(default=120.0, ge=5.0, le=600.0)
    device: str = "cuda"


class TrellisInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_path: str = Field(..., description="Path to concept image on disk")
    seed: int = Field(default=-1, description="RNG seed (-1 for random)")
    preprocess_image: bool = Field(default=True, description="Run foreground alpha extraction")
    generate_pbr: bool = Field(default=True, description="Synthesize PBR texture suite")
    texture_resolution: int = Field(default=2048, ge=512, le=4096)
    output_dir: Optional[str] = None


class TrellisOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: str
    glb_path: str
    vertex_count: int
    face_count: int
    pbr_textures: PBRTextureMaps
    latent_representation: Optional[Dict[str, Any]] = None
    execution_mode: str
    duration_seconds: float
```

### 2.3 Execution Flow & Mock Fallback
1. **Input Validation**: Verifies `image_path` existence on disk.
2. **Execution Modes**:
   - **`local`**: Checks if `torch`, `cuda`, and `spconv` are installed. If missing (e.g. on macOS), raises `MorphoMeshException(ERR_BACKEND_UNAVAILABLE)` which triggers the circuit breaker or fallback handler.
   - **`remote`**: Formulates multipart HTTP POST to `endpoint_url/v1/generate` with payload `{"image": <base64>, "slat_steps": 25, "guidance_scale": 7.5}`. Downloads synthesized `.glb` and unpacked `.png` texture maps to `output_dir`.
   - **`mock`**: Procedurally generates a valid GLB creature asset using `MeshGeometry` and synthesizes 4 valid PBR textures (Albedo, Normal, Roughness, Metallic) via PIL and numpy, executing in <50ms without GPU or network.
3. **PBR Texture Normalization**: Maps texture paths into `PBRTextureMaps` conforming to Blender 5.2.1 LTS Principled BSDF color space inputs (`sRGB` for albedo, `Non-Color` for normal, roughness, and metallic).

---

## 3. 3DAnimals / SMAL Connector (`animals3d_connector.py`)

### 3.1 Technical Role & Architecture
The `Animals3DConnector` connects the MorphoMesh pipeline to the Skinned Multi-Animal Linear model (SMAL) and 3DAnimals prior estimation. From a single input image or an existing unrigged quadruped mesh, it regresses:
- $\beta \in \mathbb{R}^{40}$: Shape parameters controlling species morphology (e.g., wolf vs. horse vs. big cat).
- $\theta \in \mathbb{R}^{35 \times 3}$: 35-joint kinematic pose rotations.
- Coordinate transformation into Blender's world frame.
- Automated mapping to Blender's standard Rigify quadruped metarig (`metarig.animals.wolf`).

### 3.2 Coordinate Transformation Matrix
Computer vision frameworks (PyTorch3D, OpenCV, SMAL) standardly represent 3D space with $+X$ right, $+Y$ up, and $-Z$ forward (or $+Z$ depth). Blender uses a right-handed system where $+X$ is right, $+Y$ is forward, and $+Z$ is up.

The authoritative coordinate conversion mapping is:
$$X_B = X, \quad Y_B = -Z, \quad Z_B = Y$$

Expressed as a $4 \times 4$ homogeneous transformation matrix:
$$T_{\text{SMAL} \to \text{Blender}} = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 0 & 0 & -1 & 0 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 0 & 1 \end{bmatrix}$$

Given any SMAL 3D joint coordinate matrix $\mathbf{J}_{\text{SMAL}} \in \mathbb{R}^{35 \times 3}$:
$$\mathbf{J}_{\text{Blender}} = \mathbf{J}_{\text{SMAL}} \cdot \begin{bmatrix} 1 & 0 & 0 \\ 0 & 0 & 1 \\ 0 & -1 & 0 \end{bmatrix}$$

### 3.3 Authoritative 35-Joint SMAL to Rigify Wolf Mapping

The connector maintains the authoritative dictionary mapping the 35 kinematic SMAL joints directly to Rigify's `DEF-*` deformation bones:

```python
SMAL_TO_RIGIFY_WOLF: Dict[str, List[str]] = {
    # Pelvis & Spine Chain
    "root":            ["DEF-spine.004"],
    "spine1":          ["DEF-spine.005"],
    "spine2":          ["DEF-spine.006", "DEF-spine.007"],
    "spine3":          ["DEF-spine.008"],
    
    # Neck & Head
    "neck1":           ["DEF-spine.009"],
    "neck2":           ["DEF-spine.010"],
    "head":            ["DEF-spine.011"],
    "jaw":             ["DEF-jaw", "DEF-chin"],
    "left_ear":        ["DEF-ear.L", "DEF-ear.L.001"],
    "right_ear":       ["DEF-ear.R", "DEF-ear.R.001"],
    "nose":            ["DEF-nose", "DEF-nose.001"],
    
    # Left Forelimb
    "left_collar":     ["DEF-shoulder.L"],
    "left_shoulder":   ["DEF-front_thigh.L", "DEF-front_thigh.L.001"],
    "left_elbow":      ["DEF-front_shin.L", "DEF-front_shin.L.001"],
    "left_wrist":      ["DEF-front_foot.L", "DEF-front_foot.L.001"],
    "left_hand":       ["DEF-front_toe.L", "DEF-f_palm.01.L", "DEF-f_index.01.L"],
    
    # Right Forelimb
    "right_collar":    ["DEF-shoulder.R"],
    "right_shoulder":  ["DEF-front_thigh.R", "DEF-front_thigh.R.001"],
    "right_elbow":     ["DEF-front_shin.R", "DEF-front_shin.R.001"],
    "right_wrist":     ["DEF-front_foot.R", "DEF-front_foot.R.001"],
    "right_hand":      ["DEF-front_toe.R", "DEF-f_palm.01.R", "DEF-f_index.01.R"],
    
    # Left Hindlimb
    "left_hip":        ["DEF-thigh.L", "DEF-thigh.L.001"],
    "left_knee":       ["DEF-shin.L", "DEF-shin.L.001"],
    "left_ankle":      ["DEF-foot.L", "DEF-foot.L.001"],
    "left_foot":       ["DEF-toe.L", "DEF-r_palm.01.L", "DEF-r_index.01.L"],
    
    # Right Hindlimb
    "right_hip":       ["DEF-thigh.R", "DEF-thigh.R.001"],
    "right_knee":      ["DEF-shin.R", "DEF-shin.R.001"],
    "right_ankle":     ["DEF-foot.R", "DEF-foot.R.001"],
    "right_foot":      ["DEF-toe.R", "DEF-r_palm.01.R", "DEF-r_index.01.R"],
    
    # Caudal Spine (Tail)
    "tail1":           ["DEF-spine.003"],
    "tail2":           ["DEF-spine.002"],
    "tail3":           ["DEF-spine.001"],
    "tail4":           ["DEF-spine"],
    "tail5":           ["DEF-spine"],
    "tail6":           ["DEF-spine"],
}
```

### 3.4 Pydantic v2 Schemas

```python
class SMALParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shape_beta: List[float] = Field(
        default_factory=lambda: [0.0] * 40,
        description="40 shape coefficients",
    )
    pose_theta: List[List[float]] = Field(
        default_factory=lambda: [[0.0, 0.0, 0.0] for _ in range(35)],
        description="35x3 Rodrigues rotation vectors",
    )
    trans: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: float = 1.0
    species: str = "canine"


class Landmark3D(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    coordinates: List[float] = Field(..., description="[x, y, z] in Blender coordinates")
    original_coordinates: Optional[List[float]] = None
    confidence: float = 1.0
    rigify_bone_targets: List[str] = Field(default_factory=list)


class AnimalPoseInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_path: Optional[str] = None
    mesh_path: Optional[str] = None
    species: str = "quadruped"
    estimate_pose: bool = True
    smal_params: Optional[SMALParams] = None


class RigifyMappingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    metarig_type: str = "wolf"
    apply_coordinate_transform: bool = True
    align_roll: bool = True
    skin_weight_transfer: Literal["nearest", "harmonic", "proportional"] = "proportional"


class Animals3DOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: str
    landmarks: Dict[str, Landmark3D]
    smal_params: SMALParams
    blender_script: str
    rigify_mapping: Dict[str, List[str]]
    transformation_matrix: List[List[float]]
    landmark_count: int
```

---

## 4. anyCreature Connector (`anycreature_connector.py`)

### 4.1 Technical Role & Architecture
The `AnyCreatureConnector` bridges text prompts to a procedural creature synthesis engine. Rather than relying solely on diffusion meshes, anyCreature structures creatures into a modular **Body Graph** (segments, branches, attachment sockets, and joint limits), procedural geometry synthesis (metaballs, spine lofting), and binds procedural gaits (quadruped walk, gallop, wing flapping).

### 4.2 Pydantic v2 Schemas

```python
class LimbSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    limb_id: str
    limb_type: Literal["leg", "wing", "arm", "fin", "tentacle"]
    side: Literal["left", "right", "center"]
    attachment_joint: str
    segment_lengths: List[float] = Field(default_factory=lambda: [0.4, 0.4, 0.15])
    joint_constraints: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "knee": {"min_deg": 0.0, "max_deg": 120.0},
            "ankle": {"min_deg": -45.0, "max_deg": 60.0},
        }
    )


class BodyPart(BaseModel):
    model_config = ConfigDict(extra="ignore")
    part_id: str
    part_type: Literal["root", "spine", "neck", "head", "tail", "jaw", "ear", "horn"]
    parent_id: Optional[str] = None
    length: float = 0.5
    radius_start: float = 0.2
    radius_end: float = 0.15
    subdivisions: int = 4
    symmetry: bool = False


class BodyGraph(BaseModel):
    model_config = ConfigDict(extra="ignore")
    creature_name: str = "ProceduralCreature"
    archetype: str = "quadruped"
    parts: Dict[str, BodyPart] = Field(default_factory=dict)
    limbs: List[LimbSpec] = Field(default_factory=list)
    root_id: str = "pelvis"


class AnimationBinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action_name: str = "walk_cycle"
    gait_frequency: float = 1.0
    phase_offsets: Dict[str, float] = Field(
        default_factory=lambda: {
            "front_left": 0.0,
            "rear_right": 0.25,
            "front_right": 0.5,
            "rear_left": 0.75,
        }
    )
    stride_length: float = 1.2
    body_undulation_amplitude: float = 0.15


class CreaturePromptSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    raw_prompt: str
    inferred_type: str = "quadruped"
    body_graph: BodyGraph
    animation_bindings: List[AnimationBinding] = Field(default_factory=list)
    procedural_parameters: Dict[str, Any] = Field(default_factory=dict)


class AnyCreatureOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: str
    spec: CreaturePromptSpec
    generated_mesh_path: Optional[str] = None
    json_spec_path: str
    clip_names: List[str] = Field(default_factory=list)
    total_parts: int
    total_limbs: int
```

### 4.3 Prompt to Body Graph Parsing Engine
The connector implements an anatomical heuristic parser:
1. **Archetype Extraction**: Scans prompt keywords:
   - "dragon", "winged", "pegasus", "wyvern" $\to$ `winged_quadruped`
   - "dog", "wolf", "cat", "tiger", "bear" $\to$ `quadruped`
   - "biped", "humanoid", "orc", "goblin" $\to$ `biped`
   - "serpent", "snake", "worm" $\to$ `serpentine`
2. **Limb & Attachment Generation**: Synthesizes bilateral limb pairs attached to `pelvis` (hind limbs) and `chest` (forelimbs). If winged, creates wing limbs attached to `chest` with specialized joint constraints.
3. **Procedural Animation Binding**: Assigns phase offsets based on quadruped diagonal trot or biped pendulum walk.

---

## 5. MeshAnything V2 Connector (`meshanything_connector.py`)

### 5.1 Technical Role & Architecture
MeshAnything V2 reformulates polygon retopology as autoregressive adjacent mesh tokenization (AMT). High-density marching cubes / Poisson meshes (50k–300k faces) are converted into clean, artist-style quad meshes. The model features **strict face budget controllability**, capable of producing quad topologies strictly under 1600 faces ($N \le 1600$) for real-time game engine assets.

### 5.2 Pydantic v2 Schemas

```python
class RetopologyConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    target_face_count: int = Field(
        default=1500,
        ge=400,
        le=8000,
        description="Target face count (quad budget; < 1600 for game-ready)",
    )
    enforce_pure_quad: bool = True
    preserve_sharp_edges: bool = True
    preserve_uvs: bool = True
    remote_endpoint: Optional[str] = None
    timeout_seconds: float = Field(default=90.0, ge=5.0, le=300.0)
    fallback_method: str = "quadriflow"


class MeshAnythingInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    input_mesh_path: str = Field(..., description="Path to dense input mesh (OBJ/GLB)")
    config: RetopologyConfig = Field(default_factory=RetopologyConfig)
    output_dir: Optional[str] = None
    output_format: str = "glb"


class MeshAnythingOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    optimized_mesh_path: str
    original_face_count: int
    original_vertex_count: int
    optimized_face_count: int
    optimized_vertex_count: int
    quad_ratio: float = Field(..., ge=0.0, le=1.0)
    reduction_ratio: float
    solver_used: str
    duration_seconds: float
```

### 5.3 Execution & Fallback Strategy
- **Platform Limitation**: `MeshAnything V2` depends on NVIDIA CUDA `nvdiffrast`. On macOS (Darwin ARM64), local compilation is unsupported.
- **Circuit Breaker & Fallback Flow**:
  1. `check_dependencies()` verifies if `nvdiffrast` and CUDA are present. If absent, marks `DependencyStatus(satisfied=False, missing_packages=["nvdiffrast", "torch.cuda"])`.
  2. If `config.remote_endpoint` is specified, delegates retopology via REST API.
  3. If remote service is unavailable, fails, or times out (>90s), the `CircuitBreaker` catches the error and executes the registered fallback: local Blender `QuadriFlow` remeshing via `blender_bridge.optimize_topology()`.
  4. In mock/test mode, executes procedural quad decimation using `MeshGeometry`, guaranteeing an output with $\le 1600$ faces and $\ge 90\%$ quad ratio in $<100$ms.

---

## 6. Tencent Hunyuan3D-2.1 Connector (`hunyuan_connector.py`)

### 6.1 Technical Role & Architecture
The `HunyuanConnector` interacts with Tencent's Hunyuan3D-2.1 foundation model via an isolated containerized service. The two-stage pipeline consists of:
1. **Hunyuan3D-DiT**: High-density geometric isosurface extraction.
2. **Hunyuan3D-Paint-PBR**: Multi-view texture inpainting synthesizing decoupled 4K PBR maps: Albedo, Tangent-Space Normal, Roughness, and Metallic.

### 6.2 Process & Network Boundary Isolation (Licensing Governance)
The connector enforces clean-room architectural separation:
- The connector communicates solely over HTTP JSON/multipart REST boundaries (`POST /v1/shape`, `POST /v1/texture_pbr`).
- No proprietary Hunyuan weights or code reside inside the MorphoMesh Python package, ensuring complete isolation from Tencent Hunyuan Community License restrictions.

### 6.3 Pydantic v2 Schemas

```python
class HunyuanConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    endpoint_url: str = "http://localhost:8001/v1"
    api_key: Optional[str] = None
    timeout_seconds: float = Field(default=180.0, ge=10.0, le=600.0)
    texture_resolution: int = Field(default=2048, ge=1024, le=4096)
    guidance_scale: float = Field(default=5.5, ge=1.0, le=15.0)
    octree_resolution: int = Field(default=256, ge=128, le=512)
    mode: Literal["mock", "remote"] = "mock"


class HunyuanInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_path: str
    generate_pbr: bool = True
    seed: int = -1
    output_format: str = "glb"
    remove_background: bool = True


class HunyuanOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: str
    mesh_path: str
    vertex_count: int
    face_count: int
    albedo_map_path: Optional[str] = None
    normal_map_path: Optional[str] = None
    roughness_map_path: Optional[str] = None
    metallic_map_path: Optional[str] = None
    pbr_textures: Dict[str, str] = Field(default_factory=dict)
    generation_time_seconds: float
    backend_service: str = "hunyuan3d-2.1"
```

---

## 7. Integration Architecture

### 7.1 Integration with `InferenceAdapter`

MorphoMesh provides `ConnectorInferenceAdapter`, a concrete subclass of `BaseInferenceAdapter` that leverages the connector framework while maintaining backwards compatibility with `get_inference_adapter()`:

```python
# In src/morphomesh/inference_adapter.py

class ConnectorInferenceAdapter(BaseInferenceAdapter):
    """Inference Adapter delegating generative stages to registered open-source connectors."""

    def __init__(self, cache_dir: Optional[str] = None, backend: str = "trellis"):
        self.cache_dir = cache_dir or os.path.expanduser("~/.morphomesh/cache")
        self.backend = backend.lower()
        self.mock_fallback = MockInferenceAdapter(cache_dir=self.cache_dir)

    def generate_concept(self, request: GenerateConceptInput) -> GenerateConceptOutput:
        # High-res 2D concept generation delegates to SD-XL/FLUX or Mock
        return self.mock_fallback.generate_concept(request)

    def generate_3d_asset(self, request: Create3DAssetInput) -> Create3DAssetOutput:
        connector_id = "trellis" if "trellis" in self.backend else "hunyuan"
        try:
            connector = ConnectorRegistry.get(connector_id)
            if connector_id == "trellis":
                inp = TrellisInput(
                    image_path=request.image_path or "",
                    seed=request.seed,
                    generate_pbr=request.generate_pbr,
                    texture_resolution=request.texture_resolution,
                    output_dir=os.path.join(self.cache_dir, "assets"),
                )
                res = connector.execute_with_resilience(inp)
                return Create3DAssetOutput(
                    asset_id=res.asset_id,
                    mesh_path=res.glb_path,
                    format="glb",
                    vertex_count=res.vertex_count,
                    face_count=res.face_count,
                    has_pbr_materials=bool(res.pbr_textures.albedo_path),
                    texture_paths={k: v for k, v in res.pbr_textures.model_dump().items() if v and isinstance(v, str)},
                    bounding_box=BoundingBox(min_point=[-0.5, -0.5, 0.0], max_point=[0.5, 0.5, 1.0], dimensions=[1.0, 1.0, 1.0]),
                    generation_time_seconds=res.duration_seconds,
                    backend_used=f"connector_{connector_id}",
                )
            else:
                inp = HunyuanInput(
                    image_path=request.image_path or "",
                    generate_pbr=request.generate_pbr,
                    seed=request.seed,
                )
                res = connector.execute_with_resilience(inp)
                return Create3DAssetOutput(
                    asset_id=res.asset_id,
                    mesh_path=res.mesh_path,
                    format="glb",
                    vertex_count=res.vertex_count,
                    face_count=res.face_count,
                    has_pbr_materials=bool(res.pbr_textures),
                    texture_paths=res.pbr_textures,
                    bounding_box=BoundingBox(min_point=[-0.5, -0.5, 0.0], max_point=[0.5, 0.5, 1.0], dimensions=[1.0, 1.0, 1.0]),
                    generation_time_seconds=res.generation_time_seconds,
                    backend_used=f"connector_{connector_id}",
                )
        except Exception as e:
            logger.warning(f"Connector '{connector_id}' failed ({e}). Routing to Mock fallback.")
            return self.mock_fallback.generate_3d_asset(request)
```

Factory update in `get_inference_adapter(mode: str)`:
- `mode="trellis"` $\to$ `ConnectorInferenceAdapter(backend="trellis")`
- `mode="hunyuan"` or `mode="hunyuan3d_2"` $\to$ `ConnectorInferenceAdapter(backend="hunyuan")`
- `mode="connectors"` $\to$ `ConnectorInferenceAdapter(backend="trellis")`

### 7.2 Integration with FastMCP Tools in `server.py`

The 7 FastMCP tools seamlessly access connectors through `inference_adapter` and `ConnectorRegistry`:
1. **`morphomesh_create_3d_asset`**: When `model_backend in ("trellis", "hunyuan3d_2", "hunyuan3d_2.1")`, instantiates or delegates to the appropriate connector.
2. **`morphomesh_optimize_topology`**: When `method == "meshanything_v2"`, delegates to `ConnectorRegistry.get("meshanything")`. If circuit breaker opens or connection times out, automatically invokes `blender_bridge.optimize_topology(method="quadriflow")`.
3. **`morphomesh_auto_rig`**: When `creature_type == "quadruped"`, queries `ConnectorRegistry.get("animals3d")` to extract SMAL landmarks and calculate bone alignments before metarig construction.
4. **New Tool: `morphomesh_connector_health`**: Exposes diagnostics to Antigravity agents:
   - Returns aggregated statuses: `ConnectorRegistry.health_check_all()`, `ConnectorRegistry.check_dependencies_all()`, and circuit breaker states.

---

## 8. Testing & Demo Architecture (R3)

### 8.1 Automated Test Suite (`tests/test_connectors.py`)

The test suite must be **100% offline**, requiring zero active network connections, zero external GPUs, and executing under 2 seconds.

#### Test Suite Structure:
1. **`TestCircuitBreaker`**:
   - `test_initial_state_closed`: Validates initial state is `CLOSED` with 0 failures.
   - `test_record_success_resets_failures`: Validates failure count reset upon success.
   - `test_trips_to_open_after_threshold`: Validates state transition to `OPEN` when failure count reaches threshold (e.g. 3).
   - `test_open_rejects_and_executes_fallback`: Confirms that calls made when `OPEN` execute fallback immediately.
   - `test_transitions_to_half_open_after_timeout`: Monkeypatches `time.time` to advance beyond `recovery_timeout` and validates transition to `HALF_OPEN`.
   - `test_half_open_success_closes_breaker`: Confirms successful probe in `HALF_OPEN` restores `CLOSED` status.
   - `test_half_open_failure_reopens_breaker`: Confirms failed probe in `HALF_OPEN` immediately returns to `OPEN`.

2. **`TestConnectorRegistry`**:
   - `test_all_five_connectors_registered`: Asserts `trellis`, `animals3d`, `anycreature`, `meshanything`, and `hunyuan` exist in `ConnectorRegistry.list_connectors()`.
   - `test_get_instantiates_singleton`: Verifies repeated calls to `get()` return identical instance.
   - `test_health_check_all_returns_valid_models`: Asserts all returned values validate against `HealthStatus`.
   - `test_check_dependencies_all`: Asserts all returned values validate against `DependencyStatus`.
   - `test_unregistered_connector_raises_error`: Asserts requesting an unknown ID raises `ERR_INVALID_ARGUMENT`.

3. **`TestTrellisConnector`**:
   - `test_mock_generation_glb_and_pbr`: Tests GLB mesh creation and generation of all 4 PBR maps (`albedo`, `normal`, `roughness`, `metallic`).
   - `test_pbr_color_spaces`: Validates that color space metadata correctly marks `albedo` as `sRGB` and other maps as `Non-Color`.
   - `test_missing_image_error`: Confirms missing image path raises validation error or `ERR_IMAGE_NOT_FOUND`.
   - `test_circuit_breaker_resilience`: Verifies fallback execution when mock backend is set to simulate failure.

4. **`TestAnimals3DConnector`**:
   - `test_coordinate_transformation_matrix`: Verifies mathematical conversion:
     $$\begin{pmatrix} 1.0 \\ 2.0 \\ 3.0 \end{pmatrix} \xrightarrow{T_{\text{SMAL} \to \text{Blender}}} \begin{pmatrix} 1.0 \\ -3.0 \\ 2.0 \end{pmatrix}$$
   - `test_smal_35_joint_landmarks_extracted`: Confirms all 35 canonical joints exist with valid non-null coordinates.
   - `test_rigify_wolf_mapping_integrity`: Asserts that all 35 mapped Rigify deformation bone targets begin with `DEF-`.
   - `test_bone_roll_alignment_flag`: Verifies that alignment script generation includes `align_roll` commands.

5. **`TestAnyCreatureConnector`**:
   - `test_prompt_parsing_winged_dragon`: Parses prompt containing "winged dragon" and asserts `archetype == "winged_quadruped"`, with 2 wings and 4 legs.
   - `test_prompt_parsing_wolf`: Parses prompt containing "dire wolf" and asserts `archetype == "quadruped"` with 4 legs.
   - `test_body_graph_schema_validity`: Verifies that generated body graph satisfies Pydantic validation and exports valid JSON.
   - `test_animation_binding_gait_phases`: Confirms quadruped diagonal gait phase offsets are assigned.

6. **`TestMeshAnythingConnector`**:
   - `test_target_face_count_budget`: Tests retopology with budget $N=1200$, asserting output face count $\le 1600$.
   - `test_quad_ratio_specification`: Verifies output quad percentage $\ge 90\%$.
   - `test_remote_failure_triggers_quadriflow_fallback`: Simulates remote endpoint failure; asserts solver fallback to `quadriflow` without crashing.

7. **`TestHunyuanConnector`**:
   - `test_hunyuan_mock_execution`: Verifies 2-stage generation output with high-res mesh and PBR maps dictionary.
   - `test_pbr_textures_dictionary_keys`: Asserts `albedo`, `normal`, `roughness`, `metallic` keys are present.
   - `test_timeout_triggers_circuit_breaker`: Verifies simulated timeout trips breaker and routes to fallback.

8. **`TestInferenceAdapterIntegration`**:
   - `test_connector_adapter_routes_trellis`: Verifies `ConnectorInferenceAdapter(backend="trellis")` produces valid `Create3DAssetOutput`.
   - `test_connector_adapter_routes_hunyuan`: Verifies `ConnectorInferenceAdapter(backend="hunyuan")` produces valid `Create3DAssetOutput`.
   - `test_connector_adapter_fallback_on_error`: Verifies graceful fallback to `MockInferenceAdapter` on connector exception.

---

### 8.2 Runnable Pipeline Demo (`examples/open_source_pipeline_demo.py`)

A complete, self-contained, runnable Python script demonstrating the end-to-end integration:

#### Script Workflow:
1. **System Health & Registry Inspection**: Queries `ConnectorRegistry`, checks dependencies, and displays status table for all 5 connectors.
2. **Stage 1: Prompt Analysis & anyCreature Body Graph**: Takes creature prompt (*"Mythical armored quadruped dire-wolf with twin shoulder horns"*), parses into `BodyGraph`, and writes `creature_spec.json`.
3. **Stage 2: High-Fidelity 3D Generation**: Invokes `TrellisConnector` (or `HunyuanConnector`) to synthesize base geometry and bake 4 PBR texture maps (`albedo`, `normal`, `roughness`, `metallic`).
4. **Stage 3: Autoregressive Quad Retopology**: Invokes `MeshAnythingConnector` to retopologize the dense mesh into an artist-quality quad mesh under 1600 faces.
5. **Stage 4: Parametric Rigging & Coordinate Transformation**: Invokes `Animals3DConnector` to estimate 35 SMAL landmarks, transform coordinates to Blender space ($[X, Y, Z] \to [X, -Z, Y]$), and generate Rigify Wolf alignment commands.
6. **Summary & Output Verification**: Prints complete metrics (vertex count, face count, quad ratio, bone count, texture channels, elapsed time).

---

## 9. Implementation Roadmap & Task Breakdown

| Task ID | Component | File Path | Scope of Work |
|---------|-----------|-----------|---------------|
| **T1** | Connector Framework | `src/morphomesh/connectors/registry.py` | Implement `BaseConnector`, `CircuitBreaker`, `ConnectorRegistry`, `HealthStatus`, `DependencyStatus`. |
| **T2** | TRELLIS Connector | `src/morphomesh/connectors/trellis_connector.py` | Implement `TrellisConnector`, PBR map extraction, local/remote/mock execution modes. |
| **T3** | 3DAnimals Connector | `src/morphomesh/connectors/animals3d_connector.py` | Implement `Animals3DConnector`, 35 SMAL landmarks, coordinate transformation matrix, `SMAL_TO_RIGIFY_WOLF`. |
| **T4** | anyCreature Connector | `src/morphomesh/connectors/anycreature_connector.py` | Implement `AnyCreatureConnector`, prompt-to-spec parser, `BodyGraph`, procedural animation bindings. |
| **T5** | MeshAnything Connector | `src/morphomesh/connectors/meshanything_connector.py` | Implement `MeshAnythingConnector`, face budget (<1600), quad ratio verification, QuadriFlow fallback. |
| **T6** | Hunyuan3D Connector | `src/morphomesh/connectors/hunyuan_connector.py` | Implement `HunyuanConnector`, 2-stage DiT/Paint-PBR client, process isolation boundary. |
| **T7** | Package Exposure | `src/morphomesh/connectors/__init__.py` | Export all connectors and schemas; trigger auto-discovery. |
| **T8** | Adapter Integration | `src/morphomesh/inference_adapter.py` | Integrate `ConnectorInferenceAdapter` and update `get_inference_adapter()`. |
| **T9** | Server Tool Routing | `src/morphomesh/server.py` | Wire connectors into `morphomesh_create_3d_asset`, `morphomesh_optimize_topology`, `morphomesh_auto_rig`, and add `morphomesh_connector_health`. |
| **T10**| Automated Test Suite | `tests/test_connectors.py` | Implement complete 100% offline mock test suite covering all connectors and integration points. |
| **T11**| Pipeline Demo Harness| `examples/open_source_pipeline_demo.py` | Implement standalone runnable demo script showcasing end-to-end flow. |

---

## 10. Conclusion & Verification Guide

This specification establishes a robust, extensible, and mathematically verified architecture for MorphoMesh Phase 2. By standardizing connectors behind the `BaseConnector` contract, protecting against remote failures with `CircuitBreaker`, and providing offline mock capabilities, the system achieves enterprise-grade resilience while unlocking the full generative power of the open-source 3D ecosystem.

Workers implementing this architecture can independently verify their work by executing:
```bash
pytest -v tests/test_connectors.py
python examples/open_source_pipeline_demo.py
pytest -v tests/
```
All tests must pass with 0 failures and exit code 0.
