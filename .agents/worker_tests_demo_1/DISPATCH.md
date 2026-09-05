## 2026-09-05T13:23:00Z
You are the Tests & Demo Engineer Worker for MorphoMesh Phase 2: Open-Source Integration Hub.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_tests_demo_1
Project root: /Users/duongnad/Documents/tool/MorphoMesh

MANDATORY FIRST STEP: Read /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You own \`tests/test_connectors.py\` and \`examples/open_source_pipeline_demo.py\` exclusively. Do not edit other files.

Inputs:
- Read \`src/morphomesh/connectors/\` (\`__init__.py\`, \`base.py\`, \`registry.py\`, \`trellis_connector.py\`, \`animals3d_connector.py\`, \`anycreature_connector.py\`, \`meshanything_connector.py\`, \`hunyuan_connector.py\`).
- Read \`src/morphomesh/inference_adapter.py\` and \`src/morphomesh/server.py\`.
- Read \`/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_adapter_1/handoff.md\`.
- Read \`/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_connectors_1/report.md\` (Section 6: Test Suite Design and Section 7: Demo Design).

Task:
Implement \`tests/test_connectors.py\` and \`examples/open_source_pipeline_demo.py\`:
1. \`tests/test_connectors.py\`:
   - Must be 100% offline (zero network, zero external API keys needed).
   - Test \`ConnectorRegistry\`:
     * Auto-registration of all 5 canonical connectors (\`trellis\`, \`animals3d\`, \`anycreature\`, \`meshanything\`, \`hunyuan\`).
     * \`health_check_all\` and \`check_dependencies_all\`.
     * \`execute_with_fallback\`: successful execution and fallback on failure.
   - Test \`CircuitBreaker\`:
     * State machine transitions: \`CLOSED\` -> threshold failures (3) -> \`OPEN\` -> recovery timeout -> \`HALF_OPEN\` -> success -> \`CLOSED\`.
     * Rejecting executions while \`OPEN\` and routing to fallback handler.
   - Test \`TrellisConnector\`:
     * Offline mock mesh generation producing valid \`.glb\` container.
     * Generation of 4 distinct PBR texture maps (Albedo sRGB, Normal Non-Color OpenGL, Roughness, Metallic).
     * Simulated remote REST API response parsing.
   - Test \`Animals3DConnector\`:
     * SMAL 35-joint landmark extraction.
     * Coordinate transformation matrix: $R_x(+90^\circ) = [[1,0,0],[0,0,-1],[0,1,0]]$ ($\det = +1.0$) mapping canonical coords $[x, y, z]$ to Blender $[x, -z, y]$.
     * \`SMAL_TO_RIGIFY_WOLF\` dictionary mapping all 35 joints to Rigify \`DEF-*\` bones.
     * Vertex blend weights calculation and Rigify script generation.
   - Test \`AnyCreatureConnector\`:
     * Heuristic/NLP prompt compilation into structured \`AnyCreatureSpec\` JSON (\`BodyGraph\`, segments, attachment points).
     * Procedural mesh building for body parts and non-manifold validation.
     * Animation clip bindings (idle, walk, run, fly).
   - Test \`MeshAnythingConnector\`:
     * Dense triangle mesh retopology coordination.
     * Polygon budget enforcement strictly producing $< 1600$ quad-dominant faces ($\ge 90\%$ quad ratio).
     * Fallback to QuadriFlow when remote service is unavailable.
   - Test \`HunyuanConnector\`:
     * High-fidelity mesh generation and multi-view PBR texture baking.
     * Mock containerized HTTP communication and clean-room network isolation.
   - Test \`InferenceAdapter\` Integration:
     * \`generate_3d_asset\` with \`model_backend="trellis"\`, \`"hunyuan"\`, \`"anycreature"\`.
     * \`optimize_topology_with_connector\` with \`method="meshanything_v2"\`.
     * \`create_animal_rig_with_connector\` with quadruped creature type.
     * Circuit breaker fallback to procedural mock when connector fails.

2. \`examples/open_source_pipeline_demo.py\`:
   - Complete, standalone runnable script demonstrating the end-to-end integration:
     * Stage 1: Concept Prompt Parsing via \`AnyCreatureConnector\` (generating \`AnyCreatureSpec\` JSON).
     * Stage 2: 3D Asset & PBR maps generation via \`TrellisConnector\` or \`HunyuanConnector\`.
     * Stage 3: Quad retopology via \`MeshAnythingConnector\` targeting $< 1600$ faces for game readiness.
     * Stage 4: Anatomical joint landmark extraction and Rigify mapping via \`Animals3DConnector\`.
     * Stage 5: Summary metrics and assembly demonstration.
   - Script must run standalone (\`python examples/open_source_pipeline_demo.py\`) with zero external dependencies and exit code 0.

3. Verification:
   - Run \`pytest -v tests/test_connectors.py\` (ensure 100% pass).
   - Run \`python examples/open_source_pipeline_demo.py\` (ensure exit code 0).
   - Run full test suite \`pytest -v tests/\` (ensure all tests pass, 0 regressions).
   - Document verification results in \`handoff.md\` and send completion message to parent.
