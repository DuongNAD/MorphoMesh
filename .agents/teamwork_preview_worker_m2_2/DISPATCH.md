# Task Assignment: Worker M2-2 (Milestone 2 Iteration 2 Remediation)

## Context
Milestone 2: Blender Socket Bridge & FastMCP Tools Subsystems Modularization — Remediation of Challenger M2-1 Finding.

## Mission
Fix the `mcp.call_tool()` context failure identified by Challenger M2-1:
1. In `src/morphomesh/tools/creature.py`:
   - Import `_safe_ctx_info` and `_safe_ctx_progress` from `morphomesh.tools.base`.
   - Replace all unshielded `await ctx.info(...)` with `await _safe_ctx_info(ctx, ...)`.
   - Replace all unshielded `await ctx.report_progress(...)` with `await _safe_ctx_progress(ctx, ...)`.
2. In `src/morphomesh/tools/animation.py`:
   - Import `_safe_ctx_info` and `_safe_ctx_progress` from `morphomesh.tools.base`.
   - Replace all unshielded `await ctx.info(...)` and `await ctx.report_progress(...)` with `await _safe_ctx_info(ctx, ...)` and `await _safe_ctx_progress(ctx, ...)`.
3. Verification:
   - Run `uv run pytest tests/test_challenger_m2_1_fastmcp_stress.py -v` (must pass 100%).
   - Run `uv run pytest tests/test_tools_schema.py tests/test_adversarial_m4_gating.py tests/test_blender_bridge.py tests/test_bridge_socket_parity.py -v`.
   - Run smoke check to ensure all 19 tools can be invoked via `mcp.call_tool()` without `ValueError: Context is not available outside of a request`.

## Write Ownership
You own:
- `src/morphomesh/tools/creature.py`
- `src/morphomesh/tools/animation.py`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverables
Write report to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m2_2\handoff.md`.
Send message to orchestrator upon completion.
