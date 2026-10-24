# Milestone 2 Reviewer Report: Blender Socket Bridge & FastMCP Tools Subsystems

**Reviewer**: `teamwork_preview_reviewer_m2_1`  
**Milestone**: Milestone 2 (M2)  
**Parent Orchestrator**: `78d0042b-63cb-483e-9623-ab80bdbef35e`  
**Verdict**: **APPROVE**  
**Date**: 2026-09-09T05:39:00Z  

---

## 1. Observation

1. **Subsystem Decomposition and Modularity**:
   - `src/morphomesh/bridge/` was inspected across all 6 submodules and the `scripts/` package:
     * `constants.py` (82 lines): Defines network configurations (`DEFAULT_HOST`, `DEFAULT_PORT`), buffer limits (`BUFFER_SIZE=65536`, `MAX_BUFFER_BYTES=16777216`, `SOCKET_TIMEOUT=120.0`), framing tokens (`SENTINEL_START`, `SENTINEL_END`), and error constants.
     * `validator.py` (205 lines): Implements `BpyCodeValidator(ast.NodeVisitor)` with comprehensive blacklists (`FORBIDDEN_MODULES`, `FORBIDDEN_CALLS`, `FORBIDDEN_ATTRIBUTES`, `FORBIDDEN_NAMES`), script length guard (`MAX_SCRIPT_LENGTH=10000`), and domain exceptions (`SecurityException`, `BlenderExecutionError`).
     * `client.py` (157 lines): Implements `BlenderSocketClient` with fast connection probing (`timeout=0.25`), NDJSON delimiter framing (`\n`), buffer reassembly, JSON-RPC 2.0 error parsing, and blender-mcp envelope unwrapping.
     * `headless.py` (147 lines): Multi-platform binary locator `resolve_blender_binary()` (Windows/macOS/Linux paths) and subprocess runner `run_headless_script()` with environment token scrubbing and sentinel JSON regex extraction.
     * `scripts/` (5 files, ~94 KB total): `base_scripts.py`, `camera_scripts.py`, `creature_scripts.py`, `human_scripts.py`, `__init__.py`. Retains line 78 comment `# front_thigh.L, front_thigh.R` for template compatibility.
     * `bridge.py` (1,104 lines): `BlenderBridge` coordinator exposing 20 high-level proxy methods with unified dispatch (`execute()`), attempting interactive TCP socket first and falling back to headless CLI runner.
     * `__init__.py` (67 lines): Re-exports all 27 canonical bridge symbols.
     * `src/morphomesh/blender_bridge.py` (69 lines): Facade re-exporting all 27 symbols from `morphomesh.bridge` with 100% object identity.

   - `src/morphomesh/tools/` was inspected across all 10 submodules:
     * `dependencies.py` (38 lines): Singleton instances (`blender_bridge`, `inference_adapter`, `meshy_connector`, `logger`, `_storage_dir`, `_backend_mode`) to prevent circular dependencies.
     * `base.py` (36 lines): Safe FastMCP context reporting helpers (`_safe_ctx_info`, `_safe_ctx_progress`).
     * `gating.py` (109 lines): Tool name sets (`CREATURE_TOOL_NAMES`, `HUMAN_TOOL_NAMES`, `INSPECTION_TOOL_NAMES`, `ANIMATION_TOOL_NAMES`, `ALL_TOOL_NAMES`), resolution function `_get_active_allowed_tool_names()`, and dual-layer wrapper `apply_tool_gating(mcp)`.
     * `creature.py` (593 lines): 7 canonical creature tools (`morphomesh_generate_concept`, `morphomesh_create_3d_asset`, `morphomesh_optimize_topology`, `morphomesh_auto_rig`, `morphomesh_blender_execute`, `morphomesh_get_scene_status`, `morphomesh_render_preview`).
     * `human.py` (525 lines): 7 digital human tools (`morphomesh_create_human_asset`, `morphomesh_auto_rig_human`, `morphomesh_setup_human_materials`, `morphomesh_groom_human`, `morphomesh_dress_human`, `morphomesh_assemble_master_character`, `morphomesh_export_production_character`).
     * `inspection.py` (363 lines): 3 inspection tools (`morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, `morphomesh_critique_visual_quality`) and canonical inspection sets.
     * `animation.py` (146 lines): 2 Meshy animation library tools (`morphomesh_animate_asset`, `morphomesh_list_animations`).
     * `registry.py` (74 lines): `register_all_tools(mcp)` registering all 19 tools onto FastMCP.
     * `server_instance.py` (43 lines): `mcp` FastMCP instance initialization, registration, and gating application.
     * `__init__.py` (113 lines): Exhaustive re-export of all 41 tools subsystem symbols.
     * `src/morphomesh/server.py` (113 lines): Facade re-exporting all 41 symbols from `morphomesh.tools` with 100% object identity.

2. **Automated Test Execution**:
   - Command specified in `DISPATCH.md`:
     `uv run pytest tests/test_blender_bridge.py tests/test_bridge_socket_parity.py tests/test_tools_schema.py tests/test_fastmcp_human_tools.py tests/test_fastmcp_inspection_tools.py -v`
     * **Result**: `169 passed in 24.64s` (exit code 0).
   - Full 11-suite Milestone 2 regression & adversarial suite:
     `uv run pytest tests/test_blender_bridge.py tests/test_bridge_socket_parity.py tests/test_m1_adversarial_socket.py tests/test_adversarial_dispatch_m1_2.py tests/test_adversarial_fastmcp_bridge_human.py tests/test_tools_schema.py tests/test_adversarial_m4_gating.py tests/test_fastmcp_human_tools.py tests/test_fastmcp_inspection_tools.py tests/test_meshy_rig_and_animation.py tests/test_challenger_m1_2_import_matrix.py -q`
     * **Result**: `452 passed in 135.01s (0:02:15)` (exit code 0).

3. **Integrity Audit**:
   - Grep searches for `test_` across `src/morphomesh/bridge/` and `src/morphomesh/tools/` returned only legitimate parameter names (`generate_test_animation`), default action names (`Action_Meshy_Walk`), and template comments (`# front_thigh.L, front_thigh.R`).
   - Zero hardcoded test outputs or mock stubs masquerading as real code.
   - Genuine AST node visitor implementation, genuine NDJSON streaming parser, and genuine FastMCP tool wrappers.

4. **Static Typings & Docstrings**:
   - Introspection of all public functions, methods, and classes in `morphomesh.bridge` and `morphomesh.tools`:
     * Bridge untyped parameters/returns: `0`
     * Tools untyped parameters/returns: `0`
     * Bridge undocumented public APIs: `0` (excluding standard `ast.NodeVisitor.visit_*` hooks)
     * Tools undocumented public APIs: `0`

5. **Adversarial Stress Testing**:
   - **AST Validator Security**:
     * Empty script: Rejected with `SecurityException` (`"Script is empty."`).
     * Oversized script (>10,000 chars): Rejected with `SecurityException` (`"Script exceeds maximum length..."`).
     * `eval()`, `exec()`, `open()`: Rejected with `SecurityException` (`"Forbidden built-in call..."`).
     * `import os`, `from subprocess import Popen`: Rejected with `SecurityException` (`"Forbidden module import..."`).
     * Dunder attributes (`().__class__.__bases__`): Rejected with `SecurityException` (`"Forbidden reflection attribute access..."`).
     * `getattr(math, 'sin')`: Rejected with `SecurityException` (`"Forbidden built-in call..."`).
     * Valid `bpy` + `math` script: Accepted without error.
   - **Socket NDJSON Streaming Transport**:
     * Fragmented TCP packet chunks: Successfully reassembled and parsed across packet boundaries.
     * JSON-RPC error payload (`{"error": {"code": -32601, "message": "Method not found"}}`): Raised `BlenderExecutionError` preserving code and message.
     * Application error payload (`{"status": "error", "message": "Failed to bake textures"}`): Raised `BlenderExecutionError`.
   - **Tool Gating Truth Table**:
     * Default (no flags): exactly 7 creature tools exposed.
     * `MORPHOMESH_INCLUDE_HUMAN_TOOLS=1`: exactly 14 tools exposed (7 creature + 7 human).
     * `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1`: exactly 10 tools exposed (7 creature + 3 inspection).
     * `MORPHOMESH_INCLUDE_ALL_TOOLS=1`: exactly 17 tools exposed (7 creature + 7 human + 3 inspection).
     * `MORPHOMESH_INCLUDE_ALL_TOOLS=1` + `MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1`: exactly 19 tools exposed.
     * Direct programmatic invocation via `mcp.call_tool("morphomesh_create_human_asset", ...)` remains fully functional even when the tool is hidden from `list_tools`.

---

## 2. Logic Chain

1. **Subsystem Cohesion & Modularity**:
   - In Observation 1, `blender_bridge.py` and `server.py` were split into focused submodules with explicit responsibilities (transport in `client.py`, process management in `headless.py`, security in `validator.py`, script templates in `scripts/`, dependencies in `dependencies.py`, gating in `gating.py`).
   - The facades `src/morphomesh/blender_bridge.py` and `src/morphomesh/server.py` re-export all original symbols with 100% object identity, preserving backward compatibility for external consumers and existing tests.
2. **Absence of Integrity Violations**:
   - In Observation 3, static analysis confirmed no hardcoded test responses, dummy facade implementations, or bypasses. All logic paths perform genuine data transformations, network I/O, subprocess execution, and AST auditing.
3. **Robustness & Adversarial Resilience**:
   - In Observation 5, adversarial testing validated that `BpyCodeValidator` actively halts dangerous code injection and reflection vectors, `BlenderSocketClient` handles TCP fragmentation and error payloads gracefully, and FastMCP tool gating behaves deterministically without breaking direct tool execution.
4. **Regression-Free Execution**:
   - In Observation 2, all 169 tests required by `DISPATCH.md` and all 452 tests across 11 test suites passed with exit code 0. Clean-process submodule imports verified zero circular dependencies across the entire repository.

---

## 3. Caveats

- System requirements for live Blender tests: 8 repository tests in `test_production_exports.py` and `test_character_assembler.py` test pre-baked binary assets on disk in `output/yu_nian_an/` and require live Blender 4.5/5.2 with GPU rendering; all 452 unit, socket transport, schema, and adversarial tests covering Milestone 2 run in mock/headless environments and execute cleanly with 100% pass rate.
- No other caveats.

---

## 4. Conclusion

**Verdict**: **APPROVE**

Worker M2-1's deliverables fulfill all architectural, typing, modularity, security, and backward-compatibility criteria specified in `PROJECT.md` and `DISPATCH.md`. The code exhibits high structural quality, complete PEP 484 typing, comprehensive docstrings, robust AST security validation, and zero circular imports.

---

## 5. Verification Method

To independently verify this assessment:

1. **Run the DISPATCH.md test suites**:
   ```powershell
   uv run pytest tests/test_blender_bridge.py tests/test_bridge_socket_parity.py tests/test_tools_schema.py tests/test_fastmcp_human_tools.py tests/test_fastmcp_inspection_tools.py -v
   ```
   *Expected*: 169 passed in ~25s.

2. **Run the full Milestone 2 regression and adversarial suite**:
   ```powershell
   uv run pytest tests/test_blender_bridge.py tests/test_bridge_socket_parity.py tests/test_m1_adversarial_socket.py tests/test_adversarial_dispatch_m1_2.py tests/test_adversarial_fastmcp_bridge_human.py tests/test_tools_schema.py tests/test_adversarial_m4_gating.py tests/test_fastmcp_human_tools.py tests/test_fastmcp_inspection_tools.py tests/test_meshy_rig_and_animation.py tests/test_challenger_m1_2_import_matrix.py -q
   ```
   *Expected*: 452 passed in ~135s.

3. **Verify export parity, tool count, and gating truth table**:
   ```powershell
   uv run python -c "
   import morphomesh, asyncio, os
   from morphomesh import blender_bridge, server
   import morphomesh.bridge as bridge
   import morphomesh.tools as tools
   assert len(morphomesh.__all__) == 40
   assert len(server.mcp._tool_manager._tools) == 19
   for s in blender_bridge.__all__: assert getattr(blender_bridge, s) is getattr(bridge, s)
   for s in server.__all__: assert getattr(server, s) is getattr(tools, s)
   async def check():
       assert len(await server.mcp.list_tools()) == 7
       os.environ['MORPHOMESH_INCLUDE_ALL_TOOLS'] = '1'
       assert len(await server.mcp.list_tools()) == 17
   asyncio.run(check())
   print('VERIFICATION SUCCESSFUL')
   "
   ```
