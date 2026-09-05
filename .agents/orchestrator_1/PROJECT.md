# Project: MorphoMesh

## Architecture
MorphoMesh is an automated AI creature generation pipeline and Model Context Protocol (MCP) server connecting Google Antigravity 2.0 with Blender. It operates on a **Hybrid Architecture**:
1. **Client & Coordination Layer**: Runs locally on macOS Apple Silicon, hosting the Python FastMCP server communicating over stdio with Antigravity 2.0.
2. **Blender Communication Layer**: Dual-mode bridge:
   - Interactive Mode: Localhost TCP socket (`127.0.0.1:9876`) integrated into Blender 5.2.1 LTS via `bpy.app.timers` non-blocking message queue.
   - Headless / CI Mode: Command-line invocation (`blender --background --python`) with sentinel JSON serialization (`MORPHOMESH_START_JSON` ... `MORPHOMESH_END_JSON`).
   - Security: AST static analysis intercepting forbidden modules (`os`, `sys`, `subprocess`) and builtins (`eval`, `exec`, `open`).
3. **AI Inference Layer (`inference_adapter.py`)**:
   - `MockInferenceAdapter`: Deterministic procedural creature mesh & PBR texture generation for local offline testing (0 VRAM, 0 API cost, 100% testable).
   - `ReplicateInferenceAdapter` & `HuggingFaceInferenceAdapter`: Remote cloud GPU endpoints for heavy 3D diffusion models (TRELLIS.2 4B, Hunyuan3D 2.1, FLUX).
   - Local Fallback: Native Blender QuadriFlow remeshing and Rigify armature binding.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | SOTA Models Matrix | Detailed benchmark table of >=20 models (33 variants) across Articulated Animals, General 3D, and Retopology/Rigging | M1 | ORIGINAL_REQUEST §R1 |
| F2 | Model Feasibility Analysis | Evaluation of License, VRAM/Hardware, Geometry fidelity, PBR, Rigging status, and Local vs Cloud deployment | M1 | ORIGINAL_REQUEST §R1 |
| F3 | 3 Use-Case Recommendations | Optimal model/tool pipeline architectures for Fantasy Creatures, Realistic Animals, and Game-Ready Assets | M1 | ORIGINAL_REQUEST §R1 |
| F4 | Hybrid Architecture Design | macOS Apple Silicon client + Remote Cloud GPU inference + Local Blender bridge architecture | M2 | ORIGINAL_REQUEST §R2 |
| F5 | Blender Bridge Specification | Dual-mode socket IPC (`127.0.0.1:9876`) and headless CLI fallback with AST security validation | M2 | ORIGINAL_REQUEST §R2 |
| F6 | 5-Stage Dataflow Specification | Comprehensive dataflow with Mermaid diagrams: Prompt -> 3D Asset -> Retopology -> Rigging -> Scene Assembly | M2 | ORIGINAL_REQUEST §R2 |
| F7 | MCP 7-Tool Specification | Full parameter schemas, return types, error codes, and JSON payloads for all 7 tools | M3 | ORIGINAL_REQUEST §R3 |
| F8 | Project Roadmap | Phase 1 PoC to production roadmap covering milestones, dependencies, and rollout | M3 | ORIGINAL_REQUEST §R3 |
| F9 | FastMCP Server Implementation | Python MCP server (`src/morphomesh/server.py` & `main.py`) exposing all 7 tools via FastMCP | M4 | ORIGINAL_REQUEST §R4 |
| F10 | Inference Adapter Module | `src/morphomesh/inference_adapter.py` supporting Mock/Offline mode and remote cloud endpoints | M4 | ORIGINAL_REQUEST §R4 |
| F11 | Blender Bridge Module | `src/morphomesh/blender_bridge.py` bidirectional client, headless runner, and AST safety filter | M4 | ORIGINAL_REQUEST §R4 |
| F12 | Blender Addon Template | `blender_addon/morphomesh/` addon package running socket listener in Blender UI | M4 | ORIGINAL_REQUEST §R4 |
| F13 | Documentation & Setup Guide | `README.md` and `SETUP_GUIDE.md` with complete setup, CLI execution, and Blender integration steps | M4 | ORIGINAL_REQUEST §R4 |
| F14 | Tool Schema Test Suite | `tests/test_tools_schema.py` validating parameters, schema boundaries, and registration | M5 | ORIGINAL_REQUEST §R4 |
| F15 | Inference Adapter Test Suite | `tests/test_inference_adapter.py` testing mock generation, procedural geometry, textures, and retopo | M5 | ORIGINAL_REQUEST §R4 |
| F16 | Blender Bridge Test Suite | `tests/test_blender_bridge.py` testing serialization, command parsing, and AST security rejection | M5 | ORIGINAL_REQUEST §R4 |
| F17 | E2E Offline Test Suite | `tests/test_e2e_offline.py` verifying full 5-stage pipeline in offline mode with 0 exit code | M5 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Research & Benchmark Docs | Generate `docs/RESEARCH_BENCHMARK.md` with full matrix and use-case roadmaps | None | DONE |
| M2 | System Architecture & Pipeline | Generate `docs/ARCHITECTURE.md` with hybrid design, 5-stage dataflow, and Mermaid diagrams | M1 | DONE |
| M3 | MCP Specification & Roadmap | Generate `docs/MCP_SPECIFICATION.md` and `docs/ROADMAP.md` | M2 | DONE |
| M4 | Runnable PoC Implementation | Build `src/morphomesh/`, `blender_addon/`, `README.md`, and `SETUP_GUIDE.md` | M2, M3 | DONE |
| M5 | Test Suite & Verification | Implement `tests/`, run `pytest -v tests/`, E2E test pass, forensic audit | M4 | DONE |

## Interface Contracts

### MCP Client (Antigravity 2.0) ↔ MorphoMesh FastMCP Server
- Transport: `stdio` (default) or `sse` (optional HTTP).
- Serialization: JSON-RPC 2.0 messages defined by MCP Specification 2024-11-05.
- Tools exposed:
  1. `morphomesh_generate_concept(prompt: str, creature_type: str, style: str, view_angles: list[str]) -> ConceptResult`
  2. `morphomesh_create_3d_asset(concept_image_path: str, creature_name: str, quality_tier: str, generate_pbr: bool) -> AssetResult`
  3. `morphomesh_optimize_topology(input_mesh_path: str, target_polycount: int, topology_type: str, preserve_features: bool) -> RetopoResult`
  4. `morphomesh_auto_rig(mesh_path: str, creature_type: str, rig_type: str, skinning_method: str) -> RigResult`
  5. `morphomesh_blender_execute(script_code: str, parameters: dict, timeout_seconds: float) -> BlenderExecResult`
  6. `morphomesh_get_scene_status(include_meshes: bool, include_armatures: bool) -> SceneStatusResult`
  7. `morphomesh_render_preview(camera_angle: str, resolution: list[int], engine: str, samples: int) -> PreviewResult`

### MorphoMesh Server ↔ Blender Bridge (`blender_bridge.py`)
- Socket: Localhost TCP `127.0.0.1:9876`.
- Message framing: Length-prefixed or newline-delimited JSON payload:
  `{"id": str, "action": str, "payload": dict, "script": str}`.
- Response payload:
  `{"id": str, "success": bool, "data": dict, "error": str | null}`.
- Headless execution fallback:
  `blender --background --python <generated_script.py>`
  Output wrapped in sentinel tokens:
  `MORPHOMESH_START_JSON\n{...}\nMORPHOMESH_END_JSON`.

### MorphoMesh Server ↔ Inference Adapter (`inference_adapter.py`)
- Base Class: `BaseInferenceAdapter(ABC)`
  - `generate_concept(prompt, options) -> ConceptArtifact`
  - `create_3d_asset(image_path, options) -> MeshArtifact`
  - `optimize_topology(mesh_path, options) -> MeshArtifact`
  - `auto_rig(mesh_path, options) -> RigArtifact`
- Implementations: `MockInferenceAdapter`, `ReplicateInferenceAdapter`, `HuggingFaceInferenceAdapter`.

## Code Layout
```
/Users/duongnad/Documents/tool/MorphoMesh/
├── docs/
│   ├── RESEARCH_BENCHMARK.md      # Milestone M1 [DONE]
│   ├── ARCHITECTURE.md            # Milestone M2 [DONE]
│   ├── MCP_SPECIFICATION.md       # Milestone M3 [DONE]
│   └── ROADMAP.md                 # Milestone M3 [DONE]
├── src/
│   └── morphomesh/
│       ├── __init__.py            # Package root & version [DONE]
│       ├── main.py                # CLI entrypoint [DONE]
│       ├── server.py              # FastMCP server setup and tool registrations [DONE]
│       ├── models.py              # Pydantic schemas, enums, error types [DONE]
│       ├── blender_bridge.py      # Socket client & headless bpy runner with AST security [DONE]
│       └── inference_adapter.py   # Mock & Remote AI inference adapters [DONE]
├── blender_addon/
│   └── morphomesh/
│       ├── __init__.py            # Blender addon bl_info, registration & timer server [DONE]
│       ├── listener.py            # Async socket listener with bpy.app.timers [DONE]
│       ├── operators.py           # Creature generation & rigify operators [DONE]
│       └── package_addon.py       # Addon zip packaging script [DONE]
├── tests/
│   ├── __init__.py                # Package root [DONE]
│   ├── conftest.py                # Shared temporary storage & fixtures [DONE]
│   ├── test_tools_schema.py       # 31 tool schema & argument validation tests [DONE]
│   ├── test_inference_adapter.py  # 28 mock inference adapter unit tests [DONE]
│   ├── test_blender_bridge.py     # 79 IPC serialization & AST security tests [DONE]
│   └── test_e2e_offline.py        # 10 end-to-end offline pipeline tests [DONE]
├── README.md                      # Project overview, installation, testing guide [DONE]
├── SETUP_GUIDE.md                 # Detailed Blender 5.2.1 LTS integration & config [DONE]
├── pyproject.toml                 # Package definition, dependencies, pytest config [DONE]
└── ORIGINAL_REQUEST.md            # Authoritative user requirements
```
