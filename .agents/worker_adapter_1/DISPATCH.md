## 2026-09-05T13:10:34Z
You are the Adapter Integration Worker for MorphoMesh Phase 2: Open-Source Integration Hub.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_adapter_1
Project root: /Users/duongnad/Documents/tool/MorphoMesh

MANDATORY FIRST STEP: Read /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You own `src/morphomesh/inference_adapter.py` and `src/morphomesh/server.py` exclusively. Do not edit other files.

Inputs:
- Read `src/morphomesh/connectors/` (`__init__.py`, `base.py`, `registry.py`, `trellis_connector.py`, `animals3d_connector.py`, `anycreature_connector.py`, `meshanything_connector.py`, `hunyuan_connector.py`) to inspect the implemented classes and API signatures.
- Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_connectors_1/handoff.md`.
- Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_codebase_1/report.md` (specifically Section 4 & 5 regarding the 7-tool FastMCP invariance and routing).

Task:
Seamlessly integrate the new production connectors into `InferenceAdapter` and `server.py`:
1. In `src/morphomesh/inference_adapter.py`:
   - Import `get_connector_registry` and connector classes from `morphomesh.connectors`.
   - Update or enhance `InferenceAdapter` (or `MockInferenceAdapter` / a unified adapter class returned by `get_inference_adapter`):
     - In `generate_3d_asset(request: Create3DAssetInput) -> Create3DAssetOutput`:
       - Check `request.model_backend`:
         - If `"trellis"` or `"trellis2"`: execute via `trellis` connector with fallback to mock.
         - If `"hunyuan"`, `"hunyuan3d_2"`, or `"hunyuan3d_2.1"`: execute via `hunyuan` connector with fallback to mock.
         - If `"anycreature"`: execute via `anycreature` connector with fallback to mock.
         - If `"mock"` or default: execute mock procedural generation.
       - Ensure the returned `Create3DAssetOutput` is completely valid, including `mesh_path`, `pbr_textures`, and `metadata` containing connector execution telemetry.
     - Add helper methods to the adapter:
       - `optimize_topology_with_connector(mesh_path: str, method: str, target_faces: int, ...) -> Dict[str, Any]`: Uses `meshanything_connector` when `method == "meshanything_v2"`, with fallback.
       - `create_animal_rig_with_connector(mesh_path: str, creature_type: str, ...) -> Dict[str, Any]`: Uses `animals3d_connector` when applicable.
2. In `src/morphomesh/server.py`:
   - PRESERVE STRICTLY the 7 canonical MCP tools (`len(tools) == 7` and tool names must match `EXPECTED_TOOL_NAMES` in `tests/test_tools_schema.py`):
     * `morphomesh_generate_concept`
     * `morphomesh_create_3d_asset`
     * `morphomesh_optimize_topology`
     * `morphomesh_auto_rig`
     * `morphomesh_blender_execute`
     * `morphomesh_get_scene_status`
     * `morphomesh_render_preview`
   - In `morphomesh_create_3d_asset`: Pass `model_backend` through to `inference_adapter.generate_3d_asset`.
   - In `morphomesh_optimize_topology`: If `method == "meshanything_v2"`, invoke `meshanything_connector` (either via adapter or directly with fallback to blender bridge).
   - In `morphomesh_auto_rig`: If `rig_type == "smal_animals3d"` or quadruped creature, incorporate `animals3d_connector` landmark/bone mapping.
3. Verification:
   - Run `pytest -v tests/` to confirm that all 148 existing tests pass 100% with exit code 0.
   - Run a test of `generate_3d_asset` with `model_backend="trellis"` and `model_backend="hunyuan"` to ensure correct routing.
   - Document changes and test results in `handoff.md`.
   - Report completion back to parent.
