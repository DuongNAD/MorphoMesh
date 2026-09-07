# BRIEFING — 2026-09-07T07:08:00Z

## Mission
Investigate and blueprint offline bridge resilience and fallback handling in `src/morphomesh/server.py` and `src/morphomesh/blender_bridge.py` for Milestone 4.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: e:\tool\mcp\MorphoMesh\.agents\explorer_m4_iter2_2
- Original parent: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
- Milestone: Milestone 4 (Iteration 2 - Offline Bridge Resilience & Fallback)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Inspect lines 1176–1216 in `src/morphomesh/server.py` (`morphomesh_capture_viewport`)
- Inspect lines 1125–1141 in `src/morphomesh/server.py` (`morphomesh_setup_inspector_camera_rig`)
- Inspect `tests/test_adversarial_error_injection_m4.py::TestOfflineBridgeResilience`
- Inspect `ORIGINAL_REQUEST.md`, `PROJECT.md`, `GATE_STATUS.md`, `challenger_m4_insp_2/handoff.md`

## Current Parent
- Conversation ID: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
- Updated: 2026-09-07T07:08:00Z

## Investigation State
- **Explored paths**:
  * `tests/test_adversarial_error_injection_m4.py::TestOfflineBridgeResilience`
  * `tests/test_fastmcp_inspection_tools.py`
  * `tests/test_bridge_socket_parity.py`
  * `tests/test_adversarial_viewport_capture.py`
  * `src/morphomesh/server.py` (lines 1090–1290)
  * `src/morphomesh/blender_bridge.py` (lines 430–650, 2120–2160, 2465–2640)
  * `src/morphomesh/camera_rig.py` (lines 20–50, 810–920)
  * `src/morphomesh/visual_critic.py` (lines 1–60, 2090–2240)
- **Key findings**:
  1. `test_capture_viewport_offline_produces_fallback_png` and `test_setup_camera_rig_offline_returns_mock_metadata` patch `blender_bridge.is_interactive_connected=False` and `blender_bridge.blender_bin_path=None`.
  2. In `blender_bridge.py`, `execute` attempts headless execution via `run_headless_script`, raising `MorphoMeshException(code="ERR_BLENDER_UNAVAILABLE")`.
  3. In `server.py`, lines 1136 and 1211 catch `MorphoMeshException` and immediately raise `ToolError`, aborting execution before `FALLBACK_PNG_BYTES` or mock metadata can be returned.
  4. In `test_fastmcp_inspection_tools.py`, line 415 (`test_bridge_exception_mapping`) asserts that non-offline exceptions like `ERR_CAMERA_FAILED` must STILL raise `ToolError` with `[ERR_CAMERA_FAILED]`. Indiscriminate exception catching would fail this regression test!
  5. The camera rig calculation function `morphomesh.camera_rig.setup_inspector_camera` already executes in pure Python without `bpy` and produces complete camera metadata (`camera_location`, `location`, `rotation_euler`, `target_center`, `framing_distance`, `bounding_box`).
  6. Writing `FALLBACK_PNG_BYTES` (70-byte valid transparent 1x1 PNG) to `output_path` (creating parent directories if needed) and encoding to ASCII base64 satisfies all disk and return value assertions.
- **Unexplored areas**: None for offline bridge resilience.

## Key Decisions Made
- Architected a two-layer defense-in-depth offline fallback:
  1. Layer 1 (Bridge Client in `blender_bridge.py`): Add try/except block around `execute` in `setup_inspector_camera`, `capture_viewport`, and `critique_visual_quality` triggering fallback when offline.
  2. Layer 2 (FastMCP Tool in `server.py`): Add offline condition checks (`e.code in ("ERR_BLENDER_UNAVAILABLE", "ERR_BRIDGE_CONNECTION")` or `ConnectionError`/`TimeoutError`/`OSError`) in exception handlers to return compliant fallback dictionaries while allowing domain exceptions like `ERR_CAMERA_FAILED` to raise `ToolError`.

## Artifact Index
- `progress.md` — Progress tracker and liveness heartbeat
- `handoff.md` — Comprehensive 5-component handoff report for Worker M4
