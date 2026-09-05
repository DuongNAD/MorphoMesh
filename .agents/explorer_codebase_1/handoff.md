# Handoff Report: Codebase Survey for Phase 2 Open-Source Integration Hub

**Agent**: `explorer_codebase_1` (Codebase Surveyor)  
**Recipient**: `parent` (`419e2607-121e-4267-b352-b2449fff6c92` / Project Orchestrator)  
**Date**: 2026-09-05  
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_codebase_1`  
**Target File**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_codebase_1/report.md`  

---

## 1. Observation

1. **Test Suite Baseline & Tool Invariance Constraint**:
   - Running `pytest -v` from `/Users/duongnad/Documents/tool/MorphoMesh` passed **148 tests in 1.18s** (exit code 0).
   - In `tests/test_tools_schema.py:42-50, 58-65`:
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
     tools = await mcp.list_tools()
     registered_names = {t.name for t in tools}
     assert registered_names == EXPECTED_TOOL_NAMES
     assert len(tools) == 7
     ```
   - In `tests/test_e2e_offline.py:47-52`:
     ```python
     tools_response = await mcp_client.list_tools()
     tool_names = [t.name for t in tools_response.tools]
     assert len(tool_names) == 7
     ```
   - **Direct Fact**: Adding a new `@mcp.tool` decorator to `server.py` will cause `len(tools) == 8` and instantly fail existing regression tests in `test_tools_schema.py` and `test_e2e_offline.py`.

2. **Current Module Structure in `src/morphomesh/`**:
   - `server.py`: Defines FastMCP instance `mcp`, instantiates global `inference_adapter` via `get_inference_adapter(mode=_backend_mode, cache_dir=_storage_dir)` and `blender_bridge = BlenderBridge(...)`. Exposes the 7 tools.
   - `inference_adapter.py`: Implements `BaseInferenceAdapter(ABC)`, `MeshGeometry` (procedural mesh with Wavefront `.obj` and standard binary `.glb` container export), `MockInferenceAdapter` (procedural quadruped, biped, winged, primitive generation with genuine PBR PIL/NumPy textures), `CircuitBreaker`, `ReplicateInferenceAdapter`, and `HuggingFaceInferenceAdapter`.
   - `blender_bridge.py`: Implements dual-mode IPC (TCP socket at `127.0.0.1:9876` and headless `blender -b -P` runner with `MORPHOMESH_START_JSON`/`MORPHOMESH_END_JSON` sentinels) and 2-tier AST static security analysis (`BpyCodeValidator`).
   - `models.py`: Authoritative Pydantic v2 schemas. Notice line 127: `RetopoMethod.MESHANYTHING_V2 = "meshanything_v2"` already exists! Tool parameters already support `model_backend: str = "mock"` in `Create3DAssetInput`, `method: Union[RetopoMethod, str] = RetopoMethod.QUADRIFLOW` in `OptimizeTopologyInput`, and `rig_type: Union[RigType, str] = RigType.RIGIFY_CREATURE` in `AutoRigInput`.

3. **Dependencies & Test Configuration**:
   - `pyproject.toml:26-33`: Requires `mcp>=1.2.0`, `pydantic>=2.0.0`, `pillow>=10.0.0`, `numpy>=1.24.0`, `pytest>=7.0.0`, `pytest-asyncio>=0.21.0`.
   - `pyproject.toml:48-56`: `testpaths = ["tests"]`, `norecursedirs = ["m1_stress_harness"]`, `addopts = "--ignore=tests/m1_stress_harness"`, `asyncio_mode = "auto"`, `pythonpath = ["src"]`.

---

## 2. Logic Chain

1. **Extension Points Placement**:
   - Creating `src/morphomesh/connectors/` is entirely non-destructive to existing imports.
   - Files required by `ORIGINAL_REQUEST.md`: `__init__.py`, `registry.py`, `trellis_connector.py`, `animals3d_connector.py`, `anycreature_connector.py`, `meshanything_connector.py`, `hunyuan_connector.py`.
   - `registry.py` should house `BaseConnector(ABC)` and `ConnectorRegistry` to centralize discovery, health checking, dependency inspection, and circuit breakers.

2. **InferenceAdapter Refactoring & Integration**:
   - In `src/morphomesh/inference_adapter.py`, `BaseInferenceAdapter` currently routes requests solely through `MockInferenceAdapter`, `ReplicateInferenceAdapter`, or `HuggingFaceInferenceAdapter`.
   - Refactoring `InferenceAdapter` to connect to `ConnectorRegistry` allows `generate_3d_asset(req)` to dispatch dynamically:
     - If `req.model_backend == "trellis"`, dispatch to `TrellisConnector`.
     - If `req.model_backend in ("hunyuan", "hunyuan3d_2", "hunyuan3d_2.1")`, dispatch to `HunyuanConnector`.
     - If `req.model_backend == "anycreature"`, dispatch to `AnyCreatureConnector`.
     - If circuit breaker is OPEN, connection fails, or mode is `"mock"`, gracefully fall back to `MockInferenceAdapter`.
   - This keeps `MockInferenceAdapter` as the zero-VRAM offline bedrock while providing seamless production connectors.

3. **FastMCP Integration Strategy without Breaking Tests**:
   - Since `test_all_seven_tools_registered` strictly asserts `len(tools) == 7`, new `@mcp.tool` decorators must NOT be registered on `server.py`'s `mcp`.
   - Instead, the 5 connectors map directly onto the 7 existing tools:
     - `morphomesh_create_3d_asset`: `model_backend` accepts `"trellis"`, `"hunyuan3d_2"`, `"anycreature"`.
     - `morphomesh_optimize_topology`: `method` accepts `"meshanything_v2"`.
     - `morphomesh_auto_rig`: `rig_type` / `creature_type` connects to `animals3d_connector` for SMAL joint landmarks.
     - `morphomesh_generate_concept`: supports enhanced prompt decomposition via `anycreature_connector`.
   - This satisfies all Phase 2 connector exposure requirements while maintaining 100% test compatibility.

4. **Test Suite `tests/test_connectors.py` Design**:
   - Must follow offline isolation (no live external API calls).
   - Uses `tmp_path`, `monkeypatch`, and mock fixtures from `conftest.py`.
   - Covers: unit tests for all 5 connectors, `ConnectorRegistry` operations, Circuit Breaker transitions, fallback execution, and `InferenceAdapter` backend routing.

---

## 3. Caveats

1. **Blender Headless Environment**: In local test environments without Blender installed, `BlenderBridge` uses simulated offline responses or AST validation checks. All connector unit tests should similarly be mock-safe and independent of Blender binary presence.
2. **Network Calls**: Connectors must implement both local/mock mode and remote client mode so CI/pytest can run in strict offline mode without API keys or live endpoints.

---

## 4. Conclusion

The MorphoMesh architecture is clean, modular, and ready for Phase 2:
- `src/morphomesh/connectors/` can be dropped in cleanly with 7 files (`__init__.py`, `registry.py`, 5 connectors).
- `InferenceAdapter` will act as a unified dispatcher delegating to `ConnectorRegistry` with fallback to `MockInferenceAdapter`.
- `server.py` exposes connector capabilities via parameter routing in `morphomesh_create_3d_asset`, `morphomesh_optimize_topology`, and `morphomesh_auto_rig`, preserving the 7-tool FastMCP invariance.
- `tests/test_connectors.py` will test all 5 connectors, registry, circuit breakers, and fallbacks in offline mode, ensuring all 148 existing tests + new connector tests pass with exit code 0.
- Full architectural details and specifications are recorded in `report.md`.

---

## 5. Verification Method

To independently verify these survey findings:
1. Verify existing test suite:
   ```bash
   pytest -v
   ```
   (Confirms 148 passed in ~1.18s).
2. Verify tool count assertion in `tests/test_tools_schema.py:65` and `tests/test_e2e_offline.py:52`:
   ```bash
   rg -n "assert len\(tools" tests/
   rg -n "EXPECTED_TOOL_NAMES" tests/
   ```
3. Inspect the comprehensive survey report:
   ```bash
   cat /Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_codebase_1/report.md
   ```
