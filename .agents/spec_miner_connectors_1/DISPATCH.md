## 2026-09-05T12:58:30Z

You are the Connector Architecture Spec Miner for MorphoMesh Phase 2: Open-Source Integration Hub.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_connectors_1
Project root: /Users/duongnad/Documents/tool/MorphoMesh

MANDATORY FIRST STEP: Read /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md.

Task:
Mine and specify the architectural design, class structures, Pydantic v2 schemas, and interaction flows for R2 (`src/morphomesh/connectors/`) and R3 (`tests/test_connectors.py`, `examples/open_source_pipeline_demo.py`):

1. **Connector Framework Architecture**:
   - `src/morphomesh/connectors/registry.py`:
     * `BaseConnector` abstract base class: `initialize()`, `health_check() -> HealthStatus`, `check_dependencies() -> DependencyStatus`, `execute(...)`, `close()`.
     * `ConnectorRegistry`: automatic registration, discovery, health status monitoring.
     * `CircuitBreaker`: Failure count threshold, reset timeout, states (CLOSED, OPEN, HALF_OPEN), automatic trip and recovery, fallback handler registration.
   - `src/morphomesh/connectors/trellis_connector.py`:
     * Pydantic v2 schemas: `TrellisInput`, `TrellisOutput`, `TrellisConfig`, `PBRTextureMaps`.
     * Local/Remote execution modes, latent/GLB extraction, PBR maps conversion.
   - `src/morphomesh/connectors/animals3d_connector.py`:
     * Pydantic v2 schemas: `SMALParams`, `AnimalPoseInput`, `Landmark3D`, `RigifyMappingConfig`.
     * SMAL joint landmark extraction, coordinate transformation matrix (PyTorch/OpenCV to Blender coordinate system [X, Y, Z] -> [X, -Z, Y]), Blender Rigify quadruped mapping.
   - `src/morphomesh/connectors/anycreature_connector.py`:
     * Pydantic v2 schemas: `CreaturePromptSpec`, `BodyGraph`, `BodyPart`, `LimbSpec`, `AnimationBinding`.
     * Prompt parsing to anyCreature JSON specification, procedural mesh & animation clips import.
   - `src/morphomesh/connectors/meshanything_connector.py`:
     * Pydantic v2 schemas: `MeshAnythingInput`, `RetopologyConfig`, `MeshAnythingOutput`.
     * Loading dense meshes, retopology coordination to quad mesh under 1600 faces.
   - `src/morphomesh/connectors/hunyuan_connector.py`:
     * Pydantic v2 schemas: `HunyuanInput`, `HunyuanConfig`, `HunyuanOutput`.
     * Remote API communication with Hunyuan3D-2.1 backend for high-res mesh & PBR textures.

2. **Integration Architecture**:
   - How `InferenceAdapter` exposes connectors as seamless backends.
   - How FastMCP tools in `server.py` expose connector capabilities.

3. **Testing & Demo Architecture**:
   - `tests/test_connectors.py`: 100% offline/mock test suite testing each connector, JSON spec structure, SMAL transformation matrix, PBR texture pipeline, circuit breaker & fallback.
   - `examples/open_source_pipeline_demo.py`: Complete runnable script demonstrating end-to-end integration.

Constraints:
- You are a read-only spec miner. Write only to your directory: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_connectors_1/`.
- Deliverables:
  * Comprehensive architectural report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_connectors_1/report.md`
  * Standard `handoff.md`.
- Send message back to parent when done.
