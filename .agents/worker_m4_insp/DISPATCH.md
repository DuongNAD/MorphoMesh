## 2026-09-07T06:45:24Z

You are Worker M4: FastMCP Integration, Gating, Test Suite & Documentation Implementer.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\worker_m4_insp
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 4).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You exclusively own and may edit the following files:
- `src/morphomesh/server.py`
- `tests/test_fastmcp_inspection_tools.py`
- `README.md`
You MUST NOT edit any other implementation files.

Reference Input Artifacts (Read these for exact blueprints before coding):
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m4_insp_1\handoff.md` (FastMCP tool registration, signatures, docstrings, and backward-compatible gating logic)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m4_insp_2\handoff.md` (Complete test architecture for tests/test_fastmcp_inspection_tools.py)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m4_insp_3\analysis.md` and `handoff.md` (Turnkey README.md additions and full repository regression matrix)

Implementation Tasks:
1. `src/morphomesh/server.py`:
   - Register the 3 FastMCP inspection tools decorated with `@mcp.tool()`:
     * `morphomesh_setup_inspector_camera_rig`
     * `morphomesh_capture_viewport`
     * `morphomesh_critique_visual_quality`
   - Define `INSPECTION_TOOL_NAMES = {"morphomesh_setup_inspector_camera_rig", "morphomesh_capture_viewport", "morphomesh_critique_visual_quality"}`.
   - Define `ALL_TOOL_NAMES = CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES | INSPECTION_TOOL_NAMES`.
   - Update `_filtered_list_tools` and `_wrapped_lowlevel_list_tools` using `_get_active_allowed_tool_names()` per `explorer_m4_insp_1` blueprint:
     * When no inspection/human flags set: strictly returns `CREATURE_TOOL_NAMES` (7 tools).
     * When `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` in `("1", "true", "yes", "all")`: includes `INSPECTION_TOOL_NAMES`.
     * When `MORPHOMESH_INCLUDE_HUMAN_TOOLS` in `("1", "true", "yes", "all")`: includes `HUMAN_TOOL_NAMES`.
     * When `MORPHOMESH_INCLUDE_ALL_TOOLS` in `("1", "true", "yes", "all")`: includes all tools.
   - Implement parameter validation, docstrings, type annotations, and exception handling mapping errors to `ToolError`.
2. `tests/test_fastmcp_inspection_tools.py`:
   - Implement complete test suite per `explorer_m4_insp_2` blueprint:
     * Autouse fixture setting `monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")`.
     * Tool registration & discovery tests (all 3 tools discovered, JSON-RPC schemas validated).
     * Direct function execution tests with mock/offline bridge and fallback bitstream validation.
     * Client invocation via `mcp.call_tool()`.
     * Bounds checking and `ToolError` raising on invalid inputs.
     * Backward compatibility tests verifying that when `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` is unset, `mcp.list_tools()` returns exactly 7 tools matching `EXPECTED_TOOL_NAMES`.
3. `README.md`:
   - Apply turnkey documentation sections from `explorer_m4_insp_3/analysis.md`:
     * Table of Contents and Tool Reference table update.
     * Section `## Multi-Angle Inspection Camera & Viewport Capture`.
     * Section `## Closed-Loop Visual Quality Critique (Auto-Critic QA)`.
     * Configuration and environment variables.
4. Verification:
   - Run: `.venv\Scripts\pytest.exe -v tests/test_fastmcp_inspection_tools.py tests/test_tools_schema.py`
   - Run full regression: `.venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_adversarial_camera_math.py tests/test_adversarial_viewport_capture.py tests/test_bridge_socket_parity.py tests/test_visual_critic.py tests/test_adversarial_bvh_penetration.py tests/test_adversarial_critic_benchmark.py tests/test_tools_schema.py tests/test_fastmcp_inspection_tools.py`
   - Verify 100% pass rate.
5. Reporting:
   - Record progress in `.agents/worker_m4_insp/progress.md`.
   - Write comprehensive handoff report to `.agents/worker_m4_insp/handoff.md` with raw verbatim terminal execution output.
   - Notify parent orchestrator via `send_message`.
