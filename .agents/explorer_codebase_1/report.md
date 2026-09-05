# MorphoMesh Phase 2: Codebase Survey & Architectural Integration Report
**Document ID**: `MM-SURVEY-P2-001`  
**Agent**: `explorer_codebase_1` (Codebase Surveyor)  
**Date**: 2026-09-05  
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_codebase_1`  
**Target Scope**: Open-Source Integration Hub (TRELLIS.2, 3DAnimals/SMAL, anyCreature, MeshAnything V2, Hunyuan3D-2.1)  

---

## 1. Executive Summary

MorphoMesh Phase 1 established an exceptionally robust, production-grade foundation comprising:
1. **Authoritative Architecture & Protocol Specifications** (`docs/ARCHITECTURE.md`, `docs/MCP_SPECIFICATION.md`, `docs/RESEARCH_BENCHMARK.md`, `docs/ROADMAP.md`).
2. **FastMCP Server** (`src/morphomesh/server.py`) exposing 7 canonical Model Context Protocol tools conforming to MCP 2024-11-05.
3. **Dual-Mode Blender Bridge** (`src/morphomesh/blender_bridge.py`) with interactive localhost TCP socket (port 9876), headless CLI fallback (`blender -b -P`), and two-tier AST static analysis code validation (`BpyCodeValidator`).
4. **AI Inference Adapter Tier** (`src/morphomesh/inference_adapter.py`) featuring zero-VRAM procedural mesh synthesis (`MeshGeometry`), genuine PBR texture generation (PIL/NumPy), circuit breaker fault recovery, and cloud stubs.
5. **Pytest Test Suite** (148 tests passing in 1.18s across schema validation, AST security, inference adapter, blender bridge IPC, and end-to-end in-memory client session runs).

Phase 2 focuses on creating the **Open-Source Integration Hub**:
- Publishing the Engineering Playbook & Licensing Governance (`docs/OPEN_SOURCE_INTEGRATION_PLAYBOOK.md`).
- Developing production-ready connectors in `src/morphomesh/connectors/`:
  - `trellis_connector.py` (Microsoft TRELLIS.2)
  - `animals3d_connector.py` (3DAnimals / SMAL)
  - `anycreature_connector.py` (anyCreature procedural engine)
  - `meshanything_connector.py` (MeshAnything V2 autoregressive retopology)
  - `hunyuan_connector.py` (Tencent Hunyuan3D-2.1)
  - `registry.py` (Dynamic registration, health checks, dependency checks, circuit breaker & fallback)
- Seamlessly integrating these connectors into `InferenceAdapter` and existing FastMCP tools without breaking existing tests.
- Delivering a comprehensive test suite `tests/test_connectors.py` and demonstration script `examples/open_source_pipeline_demo.py`.

---

## 2. Existing Codebase Deep-Dive & Topology Map

### 2.1 Package Configuration & Python Environment (`pyproject.toml`)
- **Python Version**: `>=3.11` (Runtime tested on Python 3.11.14 on macOS Darwin ARM64).
- **Core Dependencies**:
  - `mcp>=1.2.0` (FastMCP 1.28.1+ compatible, using `from mcp.server.fastmcp import FastMCP, Context, Image`).
  - `pydantic>=2.0.0` (Pydantic v2 syntax: `model_config = ConfigDict(...)`, `@field_validator`, `model_dump()`).
  - `pillow>=10.0.0` (RGBA procedural rasterization and texture generation).
  - `numpy>=1.24.0` (Mesh manipulation and PBR map array arithmetic).
  - `pytest>=7.0.0` and `pytest-asyncio>=0.21.0` (`asyncio_mode = "auto"`, `pythonpath = ["src"]`, `--ignore=tests/m1_stress_harness`).
- **CLI Entrypoints**:
  - `morphomesh = morphomesh.main:main`
  - `morphomesh-server = morphomesh.main:main`

### 2.2 Data Models & Error Taxonomy (`src/morphomesh/models.py`)
- **Error Codes Matrix**: JSON-RPC 2.0 standard codes (`-32700` to `-32602`) and domain-specific negative codes (`ERR_IMAGE_NOT_FOUND = -32001`, `ERR_BACKEND_UNAVAILABLE = -32002`, `ERR_VRAM_EXHAUSTED = -32003`, `ERR_REMESH_FAILED = -32004`, `ERR_SKINNING_HEAT_FAILURE = -32005`, `ERR_SCRIPT_SECURITY_VIOLATION = -32006`, `ERR_TIMEOUT = -32007`, `ERR_BLENDER_UNAVAILABLE = -32008`, `ERR_INFERENCE_FAILED = -32019`, etc.).
- **Enums**:
  - `CreatureType`: `QUADRUPED`, `BIPED`, `WINGED`, `AQUATIC`, `SERPENTINE`, `HYBRID`, `CUSTOM`, `WINGED_QUADRUPED`, `BIRD`, `SPIDER_ARTHROPOD`, `FISH_AQUATIC`, `CUSTOM_AUTO`.
  - `RetopoMethod`: `QUADRIFLOW`, `DECIMATE`, `VOXEL_REMESH`, `MESHANYTHING_V2`, `MOCK`. *(Notice `MESHANYTHING_V2` is already defined in models.py!)*
  - `RigType`: `BASIC_FK`, `RIGIFY_CREATURE`, `GAME_ENGINE_ROOT`, `DEFORM_ONLY`.
  - `SkinningMethod`: `AUTOMATIC_WEIGHTS`, `VOXEL_HEAT_DIFFUSE`, `GEODESIC_VOXEL`.
- **Authoritative Tool Schemas**:
  - `GenerateConceptInput` / `GenerateConceptOutput`
  - `Create3DAssetInput` / `Create3DAssetOutput` (`model_backend` defaults to `"mock"`)
  - `OptimizeTopologyInput` / `OptimizeTopologyOutput` (`method` defaults to `"quadriflow"`)
  - `AutoRigInput` / `AutoRigOutput` (`rig_type` defaults to `"rigify_creature"`)
  - `BlenderExecuteInput` / `BlenderExecuteOutput`
  - `SceneStatusInput` / `SceneStatusOutput`
  - `RenderPreviewInput` / `RenderPreviewOutput`

### 2.3 FastMCP Server (`src/morphomesh/server.py`)
- **Instance**: `mcp = FastMCP(name="MorphoMeshServer", ...)`
- **Global Objects**:
  - `inference_adapter = get_inference_adapter(mode=_backend_mode, cache_dir=_storage_dir)`
  - `blender_bridge = BlenderBridge(host=..., port=..., blender_bin_path=...)`
- **Exposed Tools**:
  1. `morphomesh_generate_concept` -> `inference_adapter.generate_concept(req)`
  2. `morphomesh_create_3d_asset` -> `inference_adapter.generate_3d_asset(req)`
  3. `morphomesh_optimize_topology` -> `blender_bridge.optimize_topology(...)`
  4. `morphomesh_auto_rig` -> `blender_bridge.create_armature(...)`
  5. `morphomesh_blender_execute` -> `blender_bridge.execute_custom_script(...)`
  6. `morphomesh_get_scene_status` -> `blender_bridge.get_scene_status(...)`
  7. `morphomesh_render_preview` -> `blender_bridge.render_preview(...)`
- **CRITICAL ARCHITECTURAL CONSTRAINT (Discovered in Test Suite)**:
  - In `tests/test_tools_schema.py`:
    ```python
    EXPECTED_TOOL_NAMES = {
        "morphomesh_generate_concept",
        "morphomesh_create_3d_asset",
        "morphomesh_optimize_topology",
        "morphomesh_auto_rig",
        "morphomesh_blender_execute",
        "morphomesh_get_scene_status",
        "morphomesh_render_preview",
    }
    assert registered_names == EXPECTED_TOOL_NAMES
    assert len(tools) == 7
    ```
  - In `tests/test_e2e_offline.py`:
    ```python
    assert len(tool_names) == 7
    ```
  - **Implication**: Registering new tools directly onto `mcp` via `@mcp.tool` in `server.py` will violate `len(tools) == 7` and break existing regression tests. Connector capabilities must therefore be seamlessly integrated into the **existing 7 canonical tools** (via parameter routing like `model_backend`, `method`, `rig_type`), or exposed via modular helper functions / inspection properties.

### 2.4 Inference Adapter Tier (`src/morphomesh/inference_adapter.py`)
- `BaseInferenceAdapter(ABC)`: Defines `generate_concept(...)` and `generate_3d_asset(...)`.
- `MeshGeometry`: Clean, custom in-memory mesh container that can construct primitives (boxes, cylinders, spheres, quads) and export directly to Wavefront `.obj` or standard binary `.glb` containers with valid glTF 2.0 chunk formatting (JSON + BIN buffers aligned to 4-byte boundaries).
- `MockInferenceAdapter`: Generates realistic procedural creature archetypes (quadrupeds, bipeds, winged creatures, primitives) and generates 4 genuine PBR texture maps (Albedo, Tangent Normal, Roughness, Metallic) with NumPy and PIL.
- `CircuitBreaker`: Implements `CLOSED`, `OPEN`, `HALF_OPEN` states with `failure_threshold` and `recovery_timeout`.
- `ReplicateInferenceAdapter` & `HuggingFaceInferenceAdapter`: Cloud wrappers that currently stub and fallback to `MockInferenceAdapter`.
- `get_inference_adapter(mode, **kwargs)`: Factory returning configured adapter instance.

### 2.5 Blender Bridge (`src/morphomesh/blender_bridge.py`)
- `BpyCodeValidator(ast.NodeVisitor)`: Two-tier AST static security analyzer blocking unsafe modules (`os`, `sys`, `subprocess`, `socket`, `ctypes`, etc.), forbidden built-ins (`eval`, `exec`, `open`, `__import__`), and dunder attributes (`__subclasses__`, `__dict__`, etc.).
- `BlenderBridge`:
  - Interactive mode: Connects to localhost TCP socket (`127.0.0.1:9876`), sends JSON-RPC 2.0 requests.
  - Headless fallback: Generates a self-contained Python script embedding parameter JSON, executes `blender -b -P <script>`, and parses response from sentinel tokens (`MORPHOMESH_START_JSON` / `MORPHOMESH_END_JSON`).
  - High-level methods: `ping()`, `get_scene_status()`, `execute_custom_script()`, `optimize_topology()`, `create_armature()`, `render_preview()`.

### 2.6 Blender Addon (`blender_addon/morphomesh/`)
- Packaged as a standard Blender addon with `listener.py` (TCP server running on a background thread and synchronized with Blender's main thread via `bpy.app.timers`) and `operators.py` (QuadriFlow remeshing, Rigify armature generation, studio preview camera).

### 2.7 Existing Test Architecture (`tests/`)
- Current status: **148 passed in 1.18s**.
- Fixtures in `tests/conftest.py`:
  - `temp_storage_dir`: Isolated temporary directory with monkeypatched `MORPHOMESH_STORAGE_DIR`, `_storage_dir`, and `inference_adapter`.
  - `sample_concept_image` & `sample_rgba_image`: Valid test images.
  - `sample_mesh_glb` & `sample_mesh_obj`: Valid test meshes.
  - `mock_adapter`: Isolated `MockInferenceAdapter`.
  - `mock_blender_bridge`: Isolated `BlenderBridge`.
  - `mcp_session_factory`: Async context manager creating authentic in-memory ClientSession (`create_connected_server_and_client_session(mcp._mcp_server)`).

---

## 3. Exact Extension Points for `src/morphomesh/connectors/`

### 3.1 Proposed Package Directory Structure
```
src/morphomesh/connectors/
├── __init__.py                # Package exports, registry accessor
├── base.py                    # BaseConnector abstract base class & Common Models
├── registry.py                # ConnectorRegistry, health check, circuit breaker & fallback
├── trellis_connector.py       # Microsoft TRELLIS.2 Connector
├── animals3d_connector.py     # 3DAnimals / SMAL Connector
├── anycreature_connector.py   # anyCreature Procedural Engine Connector
├── meshanything_connector.py  # MeshAnything V2 Retopology Connector
└── hunyuan_connector.py       # Tencent Hunyuan3D-2.1 Connector
```
*(Note: `base.py` can either be a separate file or included inside `registry.py`. Keeping a clean `base.py` or having `BaseConnector` in `registry.py` ensures modularity.)*

### 3.2 Detailed Design of Each Connector

#### 1. `BaseConnector` & Common Data Structures (`base.py` / `registry.py`)
- **Abstract Base Class**:
  ```python
  class BaseConnector(ABC):
      name: str
      version: str
      stage: int  # 1: Concept, 2: 3D Asset, 3: Retopo, 4: Rigging
      description: str

      @abstractmethod
      def health_check(self) -> HealthCheckResult:
          """Probe dependencies, local/remote service availability, and latency."""
          pass

      @abstractmethod
      def is_available(self) -> bool:
          """Quick boolean availability flag."""
          pass
  ```
- **Pydantic v2 Models**:
  - `HealthCheckResult`: `status` (`"healthy"`, `"degraded"`, `"unavailable"`), `latency_ms: float`, `message: str`, `circuit_state: str`, `dependencies_met: bool`.
  - `ConnectorMetadata`: Information for registry introspection.

#### 2. `trellis_connector.py` (Microsoft TRELLIS / TRELLIS.2)
- **Role**: Stage 2 (Single-Image to 3D Generation).
- **Core Functionality**:
  - Handles O-Voxel representations, dense geometric latent decoding, and structured GLB extraction.
  - Extracts and formats 4 PBR texture channels (Albedo, Normal, Roughness, Metallic).
  - Dual Execution Mode:
    - *Local/Remote HTTP/Gradio API client*: Connects to remote TRELLIS.2 backend (FastAPI / Gradio / ComfyUI).
    - *Offline/Mock Mode*: Synthesizes deterministic high-fidelity mesh and procedural PBR maps for zero-VRAM execution.
  - Outputs `Create3DAssetOutput` compatible metadata.

#### 3. `animals3d_connector.py` (3DAnimals / MagicPony / SMAL)
- **Role**: Stage 4 (Skeleton & Rigging Automation) / Parametric Animal Anatomy.
- **Core Functionality**:
  - Parses 3D quadruped/animal joint landmarks ($J \in \mathbb{R}^{K \times 3}$) from SMAL parametric shape/pose models.
  - Converts SMAL joint positions, bone hierarchy, and vertex blend weights ($\mathcal{W} \in \mathbb{R}^{N \times K}$) into standard Blender Rigify creature armature conventions.
  - Transforms coordinate spaces: SMAL (Y-up or Z-forward) to Blender convention (Z-up, -Y-forward).
  - Provides metarig specification for quadruped archetypes (canine, feline, equine, bovine).

#### 4. `anycreature_connector.py` (anyCreature Procedural Engine)
- **Role**: Stage 1/2/4 (Procedural Creature Generation & Rigging).
- **Core Functionality**:
  - Ingests natural language prompt and decomposes it into structured `AnyCreatureSpec` JSON:
    - Body parts specification (torso, head, limbs, wings, tails, appendages).
    - Morphological parameters (scales, dimensions, attachment points).
    - Animation clip assignments (idle, walk, run, fly).
  - Translates structured JSON specification into modular procedural 3D meshes and rigging hierarchy.
  - Validates against Pydantic v2 schema ensuring non-manifold integrity.

#### 5. `meshanything_connector.py` (MeshAnything V2)
- **Role**: Stage 3 (Topology Optimization & Retopology).
- **Core Functionality**:
  - Ingests raw, dense triangular mesh from 3D AI generators (TRELLIS / Hunyuan).
  - Coordinates autoregressive sequence retopology model to generate artist-like, quad-dominant mesh adhering to polygon budget:
    - Target: strictly $< 1600$ faces for game-ready low-poly assets, or configurable target poly count ($500 \le N \le 50,000$).
    - Preserves sharp creased feature edges and computes UV projection mapping.
  - Fallback logic: If remote MeshAnything service is offline, seamlessly routes to Blender QuadriFlow or Decimate modifier.

#### 6. `hunyuan_connector.py` (Tencent Hunyuan3D-2.1)
- **Role**: Stage 2 (High-Fidelity 3D Mesh & PBR Texture Generation).
- **Core Functionality**:
  - Connects to containerized Hunyuan3D-2.1 service (via HTTP REST API / Gradio).
  - Handles image upload, background removal, 3D shape reconstruction, and multi-view texture baking.
  - Manages asynchronous job polling / task queuing with timeout protection.
  - Offline/Mock Mode: Procedural generation with photorealistic attribute simulation.

#### 7. `registry.py` (Dynamic Registry & Resilient Orchestrator)
- **Singleton `ConnectorRegistry`**:
  - Auto-discovers and registers the 5 connectors upon module initialization.
  - Maintains individual `CircuitBreaker` instances per connector.
  - `health_check(name: str) -> HealthCheckResult` and `health_check_all() -> Dict[str, HealthCheckResult]`.
  - `execute_with_fallback(primary_name, fallback_fn, *args, **kwargs)`: Attempts execution via primary connector; if circuit breaker is OPEN or connector fails, executes fallback and records metrics.
  - Provides thread-safe connector lookup and registration.

---

## 4. Refactoring & Enhancement Strategy for `InferenceAdapter`

### 4.1 Current Implementation State
- `BaseInferenceAdapter` specifies:
  - `generate_concept(request: GenerateConceptInput) -> GenerateConceptOutput`
  - `generate_3d_asset(request: Create3DAssetInput) -> Create3DAssetOutput`
- `MockInferenceAdapter` implements procedural generation.
- `ReplicateInferenceAdapter` and `HuggingFaceInferenceAdapter` are stubs that fall back to `MockInferenceAdapter`.
- `get_inference_adapter(mode: str)` returns one adapter instance based on string flag (`"mock"`, `"replicate"`, `"huggingface"`).

### 4.2 Seamless Integration Architecture
Rather than discarding the existing clean `InferenceAdapter`, it should be enhanced into a **Unified Dispatcher**:
1. **Registry Integration**:
   `InferenceAdapter` (or an `OpenSourceInferenceAdapter` subclass / enhanced `InferenceAdapter`) holds a reference to `ConnectorRegistry`.
2. **Dynamic Backend Routing in `generate_3d_asset`**:
   - Inspect `request.model_backend`:
     - `"trellis"` / `"trellis2"` -> Dispatch to `trellis_connector`.
     - `"hunyuan"` / `"hunyuan3d_2"` / `"hunyuan3d_2.1"` -> Dispatch to `hunyuan_connector`.
     - `"anycreature"` -> Dispatch to `anycreature_connector`.
     - `"mock"` / default -> Dispatch to `MockInferenceAdapter`.
3. **Resilient Circuit Breaker & Fallback Chain**:
   ```
   Request (model_backend="trellis")
          │
          ▼
   ConnectorRegistry.get("trellis")
          │
          ├──> [Circuit Breaker Check]
          │       │
          │       ├── OPEN / Degraded ───────────────┐
          │       │                                  │
          │       └── CLOSED / Healthy               │
          │               │                          │
          │               ▼                          ▼
          │       Execute Trellis API       [Fallback to Mock]
          │               │                          │
          │         Success? ─── No ─────────────────┘
          │               │
          │              Yes
          ▼               ▼
   Create3DAssetOutput (with backend_used="trellis" or "mock")
   ```
4. **Topology & Rigging Bridge Hooks**:
   - `InferenceAdapter` can provide helper methods `optimize_topology_with_connector(req)` and `rig_with_smal(req)` that interact with `meshanything_connector` and `animals3d_connector`.
5. **Backwards Compatibility**:
   - Calling `get_inference_adapter("mock")` continues to return a functional adapter producing identical outputs to Phase 1.
   - All 148 existing tests continue to pass without alteration.

---

## 5. FastMCP Server Extension Strategy (`src/morphomesh/server.py`)

### 5.1 The 7-Tool Invariance Requirement
As noted in Section 2.3, the test suite strictly enforces that the FastMCP server exposes **exactly 7 tools**:
```python
# tests/test_tools_schema.py:65
assert len(tools) == 7
# tests/test_e2e_offline.py:52
assert len(tool_names) == 7
```
This means we **must not** add `@mcp.tool` for new standalone tools in `server.py` unless the test definitions are explicitly permitted to be updated. The superior, elegant architectural pattern is to **route connector functionality through the existing 7 tools**:

### 5.2 Seamless Tool Parameter Mapping

| Canonical MCP Tool | Connector Extension Point | Parameter & Behavior |
|---|---|---|
| `morphomesh_create_3d_asset` | `trellis_connector`<br>`hunyuan_connector`<br>`anycreature_connector` | Accepts `model_backend="trellis"`, `"hunyuan3d_2"`, `"anycreature"`, `"mock"`. When specified, routes to the corresponding connector via `InferenceAdapter`. Returns enriched `Create3DAssetOutput` with `backend_used` and metadata. |
| `morphomesh_optimize_topology` | `meshanything_connector` | Accepts `method="meshanything_v2"` (already in `RetopoMethod` enum!). When selected, invokes `meshanything_connector` for neural autoregressive retopology before/alongside Blender mesh import. |
| `morphomesh_auto_rig` | `animals3d_connector` | Accepts `rig_type="smal_animals3d"` or `creature_type="quadruped"`. Connects to `animals3d_connector` to compute SMAL joint positions and blend weights, forwarding to `BlenderBridge.create_armature`. |
| `morphomesh_generate_concept` | `anycreature_connector` | When procedural synthesis is requested, leverages `anycreature_connector` prompt parsing to populate enhanced anatomical specifications. |
| `morphomesh_get_scene_status` | `registry.py` | Can optionally include connector health statuses in diagnostic response without modifying schema invariants. |

This provides 100% feature coverage for Phase 2 while preserving 100% backward compatibility and 0 test breakage.

---

## 6. Test Suite Design (`tests/test_connectors.py`)

### 6.1 Requirements & Principles
- **100% Offline / Zero Network**: No real outbound HTTP/socket calls to external hosts during `pytest`.
- **Pure Python Mocks & Stubs**: Fast execution ($< 2$ seconds total runtime for test suite).
- **Comprehensive Coverage**:
  - Independent unit tests for all 5 connectors.
  - Unit tests for `ConnectorRegistry` (registration, health checks, circuit breaker transitions, fallbacks).
  - Integration tests verifying `InferenceAdapter` correctly routes to connectors and respects circuit breaker states.
  - End-to-end simulated pipeline test running all 5 stages using connectors.

### 6.2 Proposed Test Structure & Test Cases

```python
# tests/test_connectors.py

# 1. Registry & Circuit Breaker Tests
class TestConnectorRegistry:
    def test_auto_registration_all_five_connectors():
        """Verify registry contains trellis, animals3d, anycreature, meshanything, hunyuan."""
    def test_health_check_all():
        """Verify health check returns structured status for all connectors."""
    def test_circuit_breaker_transitions():
        """Verify transition CLOSED -> OPEN after threshold failures, and fallback execution."""
    def test_execute_with_fallback():
        """Verify successful primary execution and graceful fallback on primary error."""

# 2. TRELLIS Connector Tests
class TestTrellisConnector:
    def test_offline_mesh_generation():
        """Verify offline generation yields valid GLB and 4 PBR texture paths."""
    def test_pbr_texture_map_extraction():
        """Verify Albedo, Normal, Roughness, Metallic are synthesized and valid PNGs."""
    def test_api_mock_response_parsing():
        """Verify parsing of simulated remote TRELLIS REST API payload."""

# 3. 3DAnimals / SMAL Connector Tests
class TestAnimals3DConnector:
    def test_smal_landmark_extraction():
        """Verify extraction of standard 35+ animal joint landmarks."""
    def test_coordinate_space_transformation():
        """Verify conversion from SMAL coordinate frame to Blender Z-up."""
    def test_rigify_armature_mapping():
        """Verify generation of Rigify-compatible bone hierarchy and bone weights."""

# 4. anyCreature Connector Tests
class TestAnyCreatureConnector:
    def test_prompt_to_json_specification():
        """Verify NLP decomposition into structured AnyCreatureSpec JSON."""
    def test_procedural_assembly_mesh():
        """Verify building procedural geometry from body parts spec."""
    def test_animation_clip_mapping():
        """Verify procedural animation action mapping (idle, walk, gallop)."""

# 5. MeshAnything V2 Connector Tests
class TestMeshAnythingConnector:
    def test_dense_mesh_retopology():
        """Verify dense mesh is retopologized into quad-dominant mesh < 1600 faces."""
    def test_poly_budget_enforcement():
        """Verify face count constraints (target_poly_count)."""
    def test_fallback_to_quadriflow():
        """Verify fallback to QuadriFlow when service unavailable."""

# 6. Hunyuan3D-2.1 Connector Tests
class TestHunyuanConnector:
    def test_high_fidelity_mesh_generation():
        """Verify high-res mesh synthesis and texture mapping."""
    def test_mock_container_client():
        """Verify simulated containerized HTTP endpoint communication."""

# 7. InferenceAdapter Integration Tests
class TestInferenceAdapterConnectorIntegration:
    def test_adapter_backend_routing_trellis():
        """Verify create_3d_asset with backend='trellis' invokes TrellisConnector."""
    def test_adapter_backend_routing_hunyuan():
        """Verify create_3d_asset with backend='hunyuan' invokes HunyuanConnector."""
    def test_adapter_graceful_fallback():
        """Verify adapter falls back to MockInferenceAdapter when connector fails."""
```

### 6.3 Verification Method
- Run command: `pytest -v tests/test_connectors.py`
- Run full suite: `pytest -v tests/`
- Ensure 0 errors, 0 failures, 100% exit code 0.

---

## 7. Example Demo Script Design (`examples/open_source_pipeline_demo.py`)

ORIGINAL_REQUEST.md requires:
`examples/open_source_pipeline_demo.py` demonstrating the seamless integration pipeline from concept to rigged creature in Blender.
- Script should:
  1. Initialize `ConnectorRegistry` and perform health checks.
  2. Parse a creature prompt (e.g. "Shadow Chimera with bat wings and leonine body") via `AnyCreatureConnector`.
  3. Synthesize 3D geometry and PBR textures via `TrellisConnector` / `HunyuanConnector`.
  4. Perform quad retopology via `MeshAnythingConnector` targeting `< 1600` faces.
  5. Map anatomical joints and bone weights via `Animals3DConnector` to standard Blender Rigify hierarchy.
  6. Execute in standalone offline mode (no network required) and report step-by-step metrics and file outputs.

---

## 8. Summary of Findings & Actionable Recommendations

| Area | Current State | Recommendation for Phase 2 Implementation |
|---|---|---|
| **Package Layout** | `src/morphomesh/` has `server.py`, `inference_adapter.py`, `blender_bridge.py`, `models.py`. | Create directory `src/morphomesh/connectors/` with `__init__.py`, `registry.py`, `trellis_connector.py`, `animals3d_connector.py`, `anycreature_connector.py`, `meshanything_connector.py`, `hunyuan_connector.py`. |
| **InferenceAdapter** | Supports `"mock"`, `"replicate"`, `"huggingface"`. | Refactor/enhance `InferenceAdapter` to delegate to `ConnectorRegistry` for backends `"trellis"`, `"hunyuan3d_2"`, `"anycreature"`, with circuit breaker fallback to `MockInferenceAdapter`. |
| **FastMCP Tools** | 7 canonical tools registered; regression tests assert `len(tools) == 7`. | **Do not add new `@mcp.tool` decorators**. Route connector features through existing parameters (`model_backend`, `method`, `rig_type`) to protect regression tests. |
| **Pydantic v2 Models** | `models.py` has `RetopoMethod.MESHANYTHING_V2` already defined. | Add connector configuration and health check models, SMAL landmark models, and anyCreature JSON specification models in `src/morphomesh/models.py` or `src/morphomesh/connectors/base.py`. |
| **Tests** | 148 tests passing in `tests/`. | Add `tests/test_connectors.py` with zero network calls, comprehensive unit and integration coverage. |
| **Demo** | No `examples/` directory yet. | Create `examples/open_source_pipeline_demo.py` showcasing the full 5-stage open-source pipeline. |

This provides a complete, unambiguous architectural blueprint ready for immediate milestone execution.
