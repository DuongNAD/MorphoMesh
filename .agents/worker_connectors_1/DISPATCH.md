## 2026-09-05T13:04:21Z

You are the Connectors Engineer Worker for MorphoMesh Phase 2: Open-Source Integration Hub.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_connectors_1
Project root: /Users/duongnad/Documents/tool/MorphoMesh

MANDATORY FIRST STEP: Read /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You own `src/morphomesh/connectors/` exclusively. Do not edit files outside this directory.

Inputs:
- Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_connectors_1/report.md` (exhaustive architectural design and class structures).
- Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_models_1/report.md` (transformation matrices, bone dictionary, and model specs).
- Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_codebase_1/report.md` (codebase survey and FastMCP constraints).
- Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_hub_1/PROJECT.md`.

Task:
Implement the complete production connectors package in `src/morphomesh/connectors/`:
1. `src/morphomesh/connectors/__init__.py`:
   - Export all connectors, `BaseConnector`, `ConnectorRegistry`, `CircuitBreaker`, and `get_connector_registry()`.
2. `src/morphomesh/connectors/base.py`:
   - `BaseConnector(ABC)` with lifecycle: `initialize()`, `health_check() -> HealthCheckResult`, `check_dependencies() -> DependencyCheckResult`, `execute(...)`, `close()`.
   - Pydantic v2 models: `HealthCheckResult`, `DependencyCheckResult`, `ConnectorStatus`, `PBRTextureMaps`, `CircuitBreakerState`.
3. `src/morphomesh/connectors/registry.py`:
   - `CircuitBreaker`: 3 states (`CLOSED`, `OPEN`, `HALF_OPEN`), failure threshold, recovery timeout, automatic state transitions, metrics tracking.
   - `ConnectorRegistry`: thread-safe singleton, `register()`, `get()`, `get_all()`, `health_check_all()`, `execute_with_fallback()`. Auto-registers the 5 connectors on initialization.
4. `src/morphomesh/connectors/trellis_connector.py`:
   - `TrellisConnector(BaseConnector)`: Supports both remote REST/Gradio API client and deterministic local mock generation (producing valid GLB mesh and 4 PBR texture maps Albedo sRGB, Normal Non-Color, Roughness Non-Color, Metallic Non-Color).
   - Pydantic schemas: `TrellisInput`, `TrellisOutput`, `TrellisConfig`.
5. `src/morphomesh/connectors/animals3d_connector.py`:
   - `Animals3DConnector(BaseConnector)`: Supports SMAL 35-joint landmark extraction.
   - Coordinate transformation matrix: Rx(+90 deg) = [[1,0,0],[0,0,-1],[0,1,0]] converting PyTorch3D canonical coords (x, y, z) to Blender character space (x, -z, y).
   - `SMAL_TO_RIGIFY_WOLF` bone translation dictionary mapping SMAL joints to Blender Rigify `DEF-*` bones with roll recalculation.
   - Vertex blend skinning weight computation.
   - Pydantic schemas: `SMALParams`, `AnimalPoseInput`, `Landmark3D`, `RigifyMappingOutput`.
6. `src/morphomesh/connectors/anycreature_connector.py`:
   - `AnyCreatureConnector(BaseConnector)`: NLP/heuristic prompt parser decomposing natural language into structured `AnyCreatureSpec` JSON with `BodyGraph`, segments, attachment points, dimensions.
   - Procedural mesh builder for segments and animation clip bindings (idle, walk, run, fly).
   - Pydantic schemas: `CreaturePromptSpec`, `BodyGraph`, `BodyPart`, `LimbSpec`, `AnimationBinding`.
7. `src/morphomesh/connectors/meshanything_connector.py`:
   - `MeshAnythingConnector(BaseConnector)`: Ingests dense triangle mesh, autoregressive sequence retopology coordinator targeting `< 1600` quad-dominant faces for game engine readiness.
   - Fallback mechanism to QuadriFlow / Blender decimate if remote service is unavailable.
   - Pydantic schemas: `MeshAnythingInput`, `RetopologyConfig`, `MeshAnythingOutput`.
8. `src/morphomesh/connectors/hunyuan_connector.py`:
   - `HunyuanConnector(BaseConnector)`: Connects to Tencent Hunyuan3D-2.1 service (remote REST API client + offline mock mode).
   - High-fidelity mesh generation and multi-view PBR texture baking. Clean-room process and network boundary isolation.
   - Pydantic schemas: `HunyuanInput`, `HunyuanConfig`, `HunyuanOutput`.

Requirements:
- All code strictly typed with Pydantic v2.
- Production quality: NO empty mocks, NO dummy stubs, NO unfinished TODOs.
- Verify that all files compile cleanly and import without errors using python compile / import test.
- Document all classes, methods, and verification results in `handoff.md`.
- Report completion back to parent.
