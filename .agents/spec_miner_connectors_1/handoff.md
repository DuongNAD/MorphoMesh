# Handoff Report: Connector Architecture Specification Mining (R2 & R3)

**Agent**: Connector Architecture Spec Miner (`spec_miner_connectors_1`)  
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_connectors_1`  
**Target Milestone**: Phase 2 Open-Source Integration Hub (R2 & R3)  
**Date**: 2026-09-05  

---

## 1. Observation

1. **User Request & Requirements**:
   - `ORIGINAL_REQUEST.md:73-122` specifies Phase 2 requirements for MorphoMesh: R2 defines the production open-source connectors package `src/morphomesh/connectors/` (`trellis_connector.py`, `animals3d_connector.py`, `anycreature_connector.py`, `meshanything_connector.py`, `hunyuan_connector.py`, `registry.py`) and R3 defines automated tests (`tests/test_connectors.py`) and an executable pipeline demo (`examples/open_source_pipeline_demo.py`).
2. **Current Codebase State**:
   - `src/morphomesh/models.py:1-407`: Defines authoritative Pydantic v2 schemas for MCP tools (`GenerateConceptInput`, `Create3DAssetInput`, `OptimizeTopologyInput`, `AutoRigInput`, etc.) and error codes (`ERR_BACKEND_UNAVAILABLE = -32002`, `ERR_INFERENCE_FAILED = -32019`, `ERR_REMESH_FAILED = -32004`).
   - `src/morphomesh/inference_adapter.py:45-58`: Defines `BaseInferenceAdapter` abstract interface with `generate_concept()` and `generate_3d_asset()`. Lines 650-676 define a basic `CircuitBreaker`, lines 678-736 define `ReplicateInferenceAdapter` and `HuggingFaceInferenceAdapter`, and lines 742-753 define `get_inference_adapter()`.
   - `src/morphomesh/blender_bridge.py:937-982`: Implements `optimize_topology()` and `create_armature()` delegating commands to the Blender IPC server.
   - `src/morphomesh/server.py:45-180`: FastMCP server exposing 7 MCP tools, backed by `inference_adapter` and `blender_bridge`.
   - `tests/`: 148 automated unit and e2e tests currently pass with exit code 0 (`pytest -v tests/` took 1.12s).
   - `src/morphomesh/connectors/`: Does not yet exist; needs to be architected from scratch.
3. **Domain & Scientific References**:
   - `docs/RESEARCH_BENCHMARK.md:1202-1251`: Contains the verified 35-joint translation dictionary `SMAL_TO_RIGIFY_WOLF` mapping SMAL parametric joints to Blender Rigify `DEF-*` deformation bones.
   - `docs/RESEARCH_BENCHMARK.md:740-756`: Details MeshAnything V2 Adjacent Mesh Tokenization (AMT) and face budget controllability ($N \le 1600$).
   - `docs/RESEARCH_BENCHMARK.md:520-530`: Details Microsoft TRELLIS.2 4B O-Voxel representations and 4-channel PBR texture extraction.
   - `docs/RESEARCH_BENCHMARK.md:573-580`: Details Tencent Hunyuan3D-2.1 and territorial exclusion licensing governance requiring process & network boundary isolation.
   - `docs/ARCHITECTURE.md:250-258`: Confirms `nvdiffrast`, `spconv`, and `flash-attn` are unsupported on native macOS Darwin ARM64, mandating remote GPU microservice execution or deterministic local mock fallbacks.

---

## 2. Logic Chain

1. **Connector Framework Contract** (supported by Obs 1, Obs 2):
   Because MorphoMesh integrates 5 disparate open-source models across different compute environments (local MPS/CPU, remote Linux CUDA nodes, containerized REST APIs, mock tests), a standardized abstract base class (`BaseConnector`) is necessary. Enforcing lifecycle methods (`initialize`, `health_check`, `check_dependencies`, `execute`, `close`) guarantees uniform management, telemetry, and error handling.
2. **Resilience via CircuitBreaker & Dynamic Registry** (supported by Obs 1, Obs 2):
   Because external cloud APIs (Replicate, Hugging Face, custom GPU endpoints) can experience network latency, timeouts, or quota limits, a formal 3-state `CircuitBreaker` (`CLOSED`, `OPEN`, `HALF_OPEN`) with threshold-based tripping and automatic recovery is essential. Integrating a fallback handler registration mechanism ensures that when remote services fail or breaker opens, execution falls back instantly to local solvers (such as Blender QuadriFlow for retopology or MockInferenceAdapter for 3D generation) without interrupting agent workflows.
3. **Domain-Specific Connector Design** (supported by Obs 1, Obs 3):
   - **TRELLIS**: Must support O-Voxel latents, GLB extraction, and 4-channel PBR texture maps (`albedo`, `normal`, `roughness`, `metallic`) with color space tagging (`sRGB` vs `Non-Color`).
   - **3DAnimals / SMAL**: Requires coordinate system transformation ($[X, Y, Z] \to [X, -Z, Y]$) from PyTorch3D/OpenCV to Blender, 35-joint landmark extraction, and binding to Rigify Wolf via `SMAL_TO_RIGIFY_WOLF` with bone roll recalculation (`align_roll`).
   - **anyCreature**: Requires a natural language heuristic parser compiling prompts into modular `BodyGraph` specifications, procedural mesh lofting, and diagonal quadruped gait binding.
   - **MeshAnything V2**: Requires face count constraint enforcement ($N \le 1600$ faces for game readiness), quad ratio verification ($\ge 90\%$), and automatic fallback to QuadriFlow when remote `nvdiffrast` is unavailable.
   - **Hunyuan3D-2.1**: Requires two-stage REST communication (DiT geometry + Paint-PBR) and clean-room network boundary isolation to ensure licensing compliance.
4. **Integration & Testability** (supported by Obs 1, Obs 2):
   - Wrapping connectors inside `ConnectorInferenceAdapter` allows zero-friction integration into `src/morphomesh/inference_adapter.py` and `server.py`.
   - Creating a dedicated, 100% offline mock test harness (`tests/test_connectors.py`) ensures that CI/CD and developer machines without GPUs can test 100% of schema validation, mathematical transformations, circuit breaker state machines, and fallback mechanisms in <2 seconds.
   - Providing `examples/open_source_pipeline_demo.py` offers a complete runnable demonstration of all 5 connectors functioning cohesively.

---

## 3. Caveats

- **Live GPU Dependencies**: Native local execution of TRELLIS.2 (`spconv`), Hunyuan3D-2.1 (`flash-attn`), and MeshAnything V2 (`nvdiffrast`) requires NVIDIA Linux CUDA environments. On macOS development machines, these connectors operate in `remote` mode (delegating to cloud REST endpoints) or `mock` mode (generating deterministic procedural meshes and PBR maps).
- **Blender Version Alignment**: Blender Rigify wolf metarig bone names were verified against Blender 5.2.1 LTS. Older Blender versions (<4.0) may use slightly different bone naming conventions.
- **Licensing Boundary**: While the connectors provide clean Python interfaces, users deploying Hunyuan3D-2.1 models commercially in the EU/UK/KR must independently secure licensing from Tencent as specified in the playbook.

---

## 4. Conclusion

The architectural design, class structures, Pydantic v2 schemas, mathematical transformation matrices, and interaction flows for R2 (`src/morphomesh/connectors/`) and R3 (`tests/test_connectors.py`, `examples/open_source_pipeline_demo.py`) have been fully specified and documented in `report.md`.

All deliverables requested by the orchestrator are fulfilled:
1. `BaseConnector`, `ConnectorRegistry`, and `CircuitBreaker` specifications with exact method signatures and Pydantic schemas.
2. Complete specifications for `trellis_connector.py`, `animals3d_connector.py`, `anycreature_connector.py`, `meshanything_connector.py`, and `hunyuan_connector.py`.
3. Mathematical specification of the coordinate transformation matrix ($[X, Y, Z] \to [X, -Z, Y]$) and the 35-joint `SMAL_TO_RIGIFY_WOLF` dictionary.
4. Integration strategy into `InferenceAdapter` and FastMCP tools.
5. Exhaustive test matrix for `tests/test_connectors.py` and demo script workflow for `examples/open_source_pipeline_demo.py`.
6. A comprehensive 11-task implementation roadmap for worker agents.

---

## 5. Verification Method

To independently verify this specification:
1. Inspect the detailed report:
   ```bash
   cat /Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_connectors_1/report.md
   ```
2. Verify existing test baseline passes cleanly:
   ```bash
   pytest -v tests/
   ```
3. When worker agents implement the connectors based on this specification, verify the implementation with:
   ```bash
   pytest -v tests/test_connectors.py
   python examples/open_source_pipeline_demo.py
   pytest -v tests/
   ```
   **Invalidation Conditions**:
   - Any test failure in `tests/test_connectors.py` or existing tests.
   - Any external network request executed during unit tests.
   - Coordinate transformation matrix yielding incorrect Blender axes.
   - MeshAnything V2 output failing to satisfy the $\le 1600$ face count budget.
