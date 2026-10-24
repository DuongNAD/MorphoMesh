# Task Assignment: Worker M2-1 (Implementation - Milestone 2)

## Context
Milestone 2: Blender Socket Bridge & FastMCP Tools Subsystems Modularization.

## Mission & Implementation Steps
Decompose `src/morphomesh/blender_bridge.py` (151.5 KB) and `src/morphomesh/server.py` (71.9 KB) into clean, cohesive sub-packages while preserving 100% backward compatibility:

### 1. `bridge/` Sub-Package (`src/morphomesh/bridge/`):
Decompose `blender_bridge.py` following Explorer 1 and Explorer 2 blueprints:
- `constants.py`: Constants (`SENTINEL_START`, `SENTINEL_END`, `DEFAULT_HOST`, `DEFAULT_PORT`, `ALL_163_DEF_BONES`, `ALL_SEVEN_COLLECTIONS`, `ARKIT_52_BLENDSHAPES`, error codes).
- `validator.py`: `BpyCodeValidator`, `SecurityException`, `BlenderExecutionError`.
- `client.py`: `BlenderSocketClient` handling TCP socket connection, NDJSON streaming framing, timeout, and buffer handling.
- `headless.py`: Headless CLI runner, `_resolve_blender_binary()`, sentinel output extraction.
- `scripts/`: Domain script template generators:
  * `scripts/base_scripts.py`: Scene query, object listing, status, materials, lights.
  * `scripts/creature_scripts.py`: Procedural creature generation, auto-rigging scripts (preserve line 693 comment tag!).
  * `scripts/human_scripts.py`: Human assembly, rigging, wardrobe, grooming scripts.
  * `scripts/camera_scripts.py`: Camera rig setup, viewport capture, OpenGL/Workbench render scripts.
- `bridge.py`: Core `BlenderBridge` class coordinating `client`, `headless`, `validator`, and script builders, exposing all 30 public proxy methods.
- `__init__.py`: Re-exports `BlenderBridge`, `BpyCodeValidator`, `SecurityException`, `BlenderExecutionError`, constants.
- Refactor `src/morphomesh/blender_bridge.py` into a backward-compatible facade re-exporting all symbols via `__all__`.

### 2. `tools/` Sub-Package (`src/morphomesh/tools/`):
Decompose `server.py` following Explorer 2 blueprint:
- `gating.py`: Environment variable readers, tool name sets (`CREATURE_TOOL_NAMES`, `HUMAN_TOOL_NAMES`, `INSPECTION_TOOL_NAMES`, `ANIMATION_TOOL_NAMES`, `ALL_TOOL_NAMES`), and the dual-layer `list_tools()` filter wrapper.
- `creature.py`: 7 canonical creature tools definitions.
- `human.py`: 7 digital human tools definitions.
- `inspection.py`: 3 inspector camera and visual critique tools definitions.
- `animation.py`: 2 Meshy animation tools definitions.
- `registry.py`: Helper to register all 19 tools onto the FastMCP server instance.
- `__init__.py`: Re-exports all tool functions and tool sets.
- Refactor `src/morphomesh/server.py` into a backward-compatible facade initializing `mcp = FastMCP("morphomesh", ...)`, registering all tools, wrapping `list_tools()` and JSON-RPC handlers for gating, and re-exporting `mcp`, `create_mcp_server`, all 19 tools, and constants via `__all__`.

### 3. Verification Commands:
Execute and ensure 100% pass:
- `uv run pytest tests/test_tools_schema.py tests/test_adversarial_m4_gating.py tests/test_bridge_socket_parity.py tests/test_blender_bridge.py tests/test_fastmcp_human_tools.py tests/test_fastmcp_inspection_tools.py tests/test_m1_adversarial_socket.py -v`
- `uv run python -c "import morphomesh; from morphomesh.server import mcp; print('Tools:', len(mcp._tool_manager._tools)); print('Exports:', len(morphomesh.__all__))"`
  (Expected: Tools: 19, Exports: 40).
- Check zero circular dependencies.

## Write Ownership
You own:
- `src/morphomesh/bridge/` (all files)
- `src/morphomesh/blender_bridge.py` (facade)
- `src/morphomesh/tools/` (all files)
- `src/morphomesh/server.py` (facade)

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Input Reference Files
- `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md`
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md`
- `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_1\analysis.md`
- `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\analysis.md`
- `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\handoff.md`

## Deliverables
Write report to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m2_1\handoff.md`.
Send message to orchestrator upon completion.

## 2026-09-09T05:03:00Z
You are Worker M2-1 for Milestone 2: Blender Socket Bridge & FastMCP Tools Subsystems Modularization. Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m2_1. Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m2_1\DISPATCH.md, PROJECT.md at E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md, and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md. Read the blueprints in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_1\analysis.md and E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\analysis.md and handoff.md. Modularize src/morphomesh/blender_bridge.py into src/morphomesh/bridge/ and src/morphomesh/server.py into src/morphomesh/tools/, refactoring both root files into backward-compatible facades with exact __all__ parity. Verify all 19 FastMCP tools and their gating truth tables. Run pytest suites and verify zero regressions. MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected. Send a message to orchestrator when finished.
