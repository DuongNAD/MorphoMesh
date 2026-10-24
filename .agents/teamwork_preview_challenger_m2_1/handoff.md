# Milestone 2 Adversarial Stress Test & Verification Report: FastMCP Tool Registrations, Schemas, and Dynamic Gating

**Agent**: `teamwork_preview_challenger_m2_1`  
**Milestone**: Milestone 2 (M2)  
**Parent Orchestrator**: `78d0042b-63cb-483e-9623-ab80bdbef35e`  
**Date**: 2026-09-09T05:41:00Z  
**Verdict**: **REJECT**

---

## 1. Observation

### 1.1 Direct Observation of Critical Regression in `mcp.call_tool()`
During empirical evaluation of FastMCP tool execution via `mcp.call_tool()`, **9 out of 19 tools crashed immediately** with unhandled `ValueError` wrapped inside `ToolError`:

```text
mcp.server.fastmcp.exceptions.ToolError: Error executing tool <tool_name>: Context is not available outside of a request
```

#### Affected Tools Breakdown:
| Subsystem | Tool Name | Direct Call via `mcp.call_tool()` | Root Cause |
|---|---|---|---|
| **Creature (7)** | `morphomesh_generate_concept` | **FAILED** | Unprotected `await ctx.info(...)` at `creature.py:81` |
| **Creature (7)** | `morphomesh_create_3d_asset` | **FAILED** | Unprotected `await ctx.info(...)` at `creature.py:147` |
| **Creature (7)** | `morphomesh_optimize_topology` | **FAILED** | Unprotected `await ctx.info(...)` at `creature.py:214` |
| **Creature (7)** | `morphomesh_auto_rig` | **FAILED** | Unprotected `await ctx.info(...)` at `creature.py:307` |
| **Creature (7)** | `morphomesh_blender_execute` | **FAILED** | Unprotected `await ctx.info(...)` at `creature.py:465` |
| **Creature (7)** | `morphomesh_get_scene_status` | **FAILED** | Unprotected `await ctx.info(...)` at `creature.py:505` |
| **Creature (7)** | `morphomesh_render_preview` | **FAILED** | Unprotected `await ctx.info(...)` at `creature.py:547` |
| **Animation (2)** | `morphomesh_animate_asset` | **FAILED** | Unprotected `await ctx.info(...)` at `animation.py:51` |
| **Animation (2)** | `morphomesh_list_animations` | **FAILED** | Unprotected `await ctx.info(...)` at `animation.py:122` |
| **Human (7)** | `morphomesh_create_human_asset` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`human.py:66`) |
| **Human (7)** | `morphomesh_auto_rig_human` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`human.py:165`) |
| **Human (7)** | `morphomesh_setup_human_materials` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`human.py:227`) |
| **Human (7)** | `morphomesh_groom_human` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`human.py:292`) |
| **Human (7)** | `morphomesh_dress_human` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`human.py:362`) |
| **Human (7)** | `morphomesh_assemble_master_character` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`human.py:436`) |
| **Human (7)** | `morphomesh_export_production_character`| **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`human.py:488`) |
| **Inspection (3)**| `morphomesh_setup_inspector_camera_rig`| **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`inspection.py:76`) |
| **Inspection (3)**| `morphomesh_capture_viewport` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`inspection.py:183`) |
| **Inspection (3)**| `morphomesh_critique_visual_quality` | **PASSED** | Correctly uses `_safe_ctx_info(ctx, ...)` (`inspection.py:284`) |

### 1.2 Exact Verbatim Exception Traceback
Executing `await mcp.call_tool("morphomesh_generate_concept", {"prompt": "A mechanical direwolf"})`:
```text
Traceback (most recent call last):
  File "E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages\mcp\server\fastmcp\tools\base.py", line 101, in run
    result = await self.fn_metadata.call_fn_with_arg_validation(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages\mcp\server\fastmcp\utilities\func_metadata.py", line 113, in call_fn_with_arg_validation
    return await fn(**arguments_parsed_dict)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\tool\mcp\MorphoMesh\src\morphomesh\tools\creature.py", line 81, in morphomesh_generate_concept
    await ctx.info("Initializing Stage 1: 2D Concept Synthesis...")
  File "E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages\mcp\server\fastmcp\server.py", line 1358, in info
    await self.log("info", message, **extra)
  File "E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages\mcp\server\fastmcp\server.py", line 1290, in log
    await self.request_context.session.send_log_message(
          ^^^^^^^^^^^^^^^^^^^^
  File "E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages\mcp\server\fastmcp\server.py", line 1170, in request_context
    raise ValueError("Context is not available outside of a request")
ValueError: Context is not available outside of a request

During handling of the above exception, another exception occurred:

mcp.server.fastmcp.exceptions.ToolError: Error executing tool morphomesh_generate_concept: Context is not available outside of a request
```

### 1.3 Unprotected Context Call Locations in Source Code
In `src/morphomesh/tools/creature.py`:
- Line 81, 82, 102, 103: `await ctx.info(...)`, `await ctx.report_progress(...)`
- Line 147, 148, 169, 170: `await ctx.info(...)`, `await ctx.report_progress(...)`
- Line 214, 215, 242, 243, 259, 260: `await ctx.info(...)`, `await ctx.report_progress(...)`
- Line 307, 308, 314, 315, 349, 350, 400, 401, 432, 433: `await ctx.info(...)`, `await ctx.report_progress(...)`
- Line 465: `await ctx.info(...)`
- Line 505: `await ctx.info(...)`
- Line 547, 548, 574, 575: `await ctx.info(...)`, `await ctx.report_progress(...)`

In `src/morphomesh/tools/animation.py`:
- Line 51, 52: `await ctx.info(...)`, `await ctx.report_progress(...)`
- Line 93, 94: `await ctx.report_progress(...)`, `await ctx.info(...)`
- Line 122: `await ctx.info(...)`

### 1.4 Baseline & Matrix State Verification (PASSED)
1. **Gating Matrix Truth Table**: Verified across all 8 configurations:
   - Clean / Default: 7 tools (`CREATURE_TOOL_NAMES`)
   - `MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1`: 9 tools (`CREATURE_TOOL_NAMES | ANIMATION_TOOL_NAMES`)
   - `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1`: 10 tools (`CREATURE_TOOL_NAMES | INSPECTION_TOOL_NAMES`)
   - `MORPHOMESH_INCLUDE_HUMAN_TOOLS=1`: 14 tools (`CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES`)
   - `MORPHOMESH_INCLUDE_HUMAN_TOOLS=1` & `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1`: 17 tools (`ALL_TOOL_NAMES`)
   - `MORPHOMESH_INCLUDE_ALL_TOOLS=1`: 17 tools (`ALL_TOOL_NAMES`)
   - `MORPHOMESH_INCLUDE_ALL_TOOLS=1` & `MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1`: 19 tools (`ALL_19_TOOL_NAMES`)
   - All 4 environment flags enabled: exactly 19 tools.
2. **Low-Level JSON-RPC ListToolsRequest Handling**:
   - `mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]` returns `ServerResult(root=ListToolsResult(tools=[...]))`.
   - Exact 1:1 parity with `await mcp.list_tools()` across all states.
   - Zero schema drift across all 19 tools (valid `properties`, `type: object`, docstrings > 20 chars).
3. **Pydantic Validation Error Handling**:
   - Tested 15 adversarial payloads (missing required fields, negative integers, string-for-int, out-of-range bounds).
   - FastMCP and Pydantic schemas catch all invalid payloads and raise `ToolError` with informative descriptions.
4. **Dynamic Runtime State Transitions**:
   - Rapid toggling of environment flags without caching leakage or cross-contamination.
   - Calling an unknown tool (`morphomesh_unknown_nonexistent_tool`) correctly raises `ToolError("Unknown tool: ...")`.

---

## 2. Logic Chain

1. **Mission Requirement Invalidation**:
   - Mission deliverable #1 explicitly requires: *"Test all 19 tools through `mcp.call_tool()` under gated and ungated configurations (verify tools hidden from `list_tools()` remain callable)."*
   - Direct empirical execution proves that 9 out of 19 tools cannot be called via `mcp.call_tool()` in either gated or ungated mode.
2. **Incomplete Architectural Migration**:
   - The worker correctly designed `src/morphomesh/tools/base.py` containing `_safe_ctx_info` and `_safe_ctx_progress` to swallow `ValueError` when `ctx` is outside of an active JSON-RPC request.
   - The worker successfully integrated `_safe_ctx_info` and `_safe_ctx_progress` into `src/morphomesh/tools/human.py` and `src/morphomesh/tools/inspection.py`.
   - However, the worker omitted this migration in `src/morphomesh/tools/creature.py` and `src/morphomesh/tools/animation.py`, leaving raw `await ctx.info(...)` and `await ctx.report_progress(...)` calls.
3. **FastMCP Execution Semantics**:
   - Whenever any tool whose signature includes `ctx: Optional[Context] = None` is executed via `mcp.call_tool()`, FastMCP automatically instantiates a default `Context(request_context=None)`.
   - Because `ctx` is not None, `if ctx:` evaluates to `True`.
   - Calling `.info()` or `.report_progress()` on this unbound context unconditionally raises `ValueError("Context is not available outside of a request")`.
   - In `creature.py`, these calls occur outside the main `try...except` block, bubbling up to FastMCP's tool runner which wraps it in `ToolError`.
   - In `animation.py`, it is caught by `except Exception` and re-raised as `ToolError("Unexpected Tool Failure...")`.
4. **Validation Masking**:
   - Because the context crash occurs before domain validation models are evaluated, domain validation never executes for invalid creature or animation inputs.
5. **Architectural Viability Proved**:
   - When `Context.info` and `Context.report_progress` are safely wrapped to ignore missing request contexts (as demonstrated in `tests/test_challenger_m2_1_fastmcp_stress.py::TestToolCallabilityEmpiricalChallenge::test_all_tools_succeed_under_safe_context_patch`), **all 19 tools pass 100% without error**.

---

## 3. Caveats

- **Existing Tests Missed This Bug**: Pre-existing tests in `tests/test_tools_schema.py` tested tool functions via direct Python imports (`await morphomesh_generate_concept(..., ctx=None)`), explicitly passing `ctx=None`, which bypassed the `if ctx:` branch. Only testing via `mcp.call_tool()` exposed the regression.
- **Scope of Rejection**: This rejection is strictly scoped to the context handling bug in `src/morphomesh/tools/creature.py` and `src/morphomesh/tools/animation.py`. The modular decomposition layout, facade re-exports, AST validator, socket protocol, low-level JSON-RPC handler, and gating matrix logic are all sound and verified.

---

## 4. Conclusion

**Verdict: REJECT**

The Milestone 2 implementation cannot be confirmed as correct until the 9 creature and animation tools are remediated to use `_safe_ctx_info` and `_safe_ctx_progress`.

### Actionable Remediation Required:
1. In `src/morphomesh/tools/creature.py`:
   - Import `_safe_ctx_info, _safe_ctx_progress` from `morphomesh.tools.base`.
   - Replace all 26 occurrences of raw `await ctx.info(...)` and `await ctx.report_progress(...)` with `await _safe_ctx_info(ctx, ...)` and `await _safe_ctx_progress(ctx, ...)`.
2. In `src/morphomesh/tools/animation.py`:
   - Import `_safe_ctx_info, _safe_ctx_progress` from `morphomesh.tools.base`.
   - Replace all 5 occurrences of raw `await ctx.info(...)` and `await ctx.report_progress(...)` with `await _safe_ctx_info(ctx, ...)` and `await _safe_ctx_progress(ctx, ...)`.
3. Re-run `uv run pytest tests/test_challenger_m2_1_fastmcp_stress.py` to confirm that all 19 tools succeed under `mcp.call_tool()`.

---

## 5. Verification Method

To independently reproduce the empirical failure and verify the adversarial challenge:

1. **Run the dedicated adversarial stress test suite**:
   ```powershell
   uv run pytest tests/test_challenger_m2_1_fastmcp_stress.py -v
   ```
   *Expected result*: 29 passed (including explicit bug reproduction tests `test_reproduce_raw_context_failure_on_creature_tools` and patched verification `test_all_tools_succeed_under_safe_context_patch`).

2. **Empirically reproduce the unhandled context failure in a single command**:
   ```powershell
   uv run python -c "
   import asyncio
   from morphomesh.server import mcp
   async def reproduce():
       try:
           await mcp.call_tool('morphomesh_generate_concept', {'prompt': 'A ferocious direwolf'})
           print('UNEXPECTED SUCCESS')
       except Exception as e:
           print('CONFIRMED REGRESSION:', type(e), e)
   asyncio.run(reproduce())
   "
   ```
   *Output observed*:
   `CONFIRMED REGRESSION: <class 'mcp.server.fastmcp.exceptions.ToolError'> Error executing tool morphomesh_generate_concept: Context is not available outside of a request`

3. **Verify against human tools to observe passing contrast**:
   ```powershell
   uv run python -c "
   import asyncio
   from morphomesh.server import mcp
   async def test_human():
       res = await mcp.call_tool('morphomesh_create_human_asset', {'character_name': 'Yu_Nian_An'})
       print('HUMAN TOOL SUCCESS:', res[0][0].text[:60])
   asyncio.run(test_human())
   "
   ```
   *Output observed*:
   `HUMAN TOOL SUCCESS: {"status": "success", "asset_id": "human-...`
