## 2026-09-07T03:48:34Z
<USER_REQUEST>
You are Worker M1: Interactive Socket Bridge Parity & Reliability Implementer.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\worker_m1
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 1).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You exclusively own and may edit the following files:
- blender_addon/morphomesh/listener.py
- src/morphomesh/blender_bridge.py
- tests/test_bridge_socket_parity.py
You MUST NOT edit any other implementation files.

Reference Input Artifacts (Read these for exact blueprints before coding):
- e:\tool\mcp\MorphoMesh\.agents\explorer_m1_1\handoff.md (Listener blueprints for NDJSON framing, timer immortality, and _dispatch methods)
- e:\tool\mcp\MorphoMesh\.agents\explorer_m1_2\handoff.md (Bridge client blueprints for NDJSON framing, execute() dispatch fix, typed client inspection methods, and defensive schema parsing)
- e:\tool\mcp\MorphoMesh\.agents\explorer_m1_3\handoff.md (Test suite specifications for tests/test_bridge_socket_parity.py)

Milestone 1 Objectives:
1. Update blender_addon/morphomesh/listener.py:
   - NDJSON streaming in _client_handler (split on b\n, handle multiple commands and whitespace without JSONDecodeError).
   - Timer immortality in _drain_queue (top-level try/except/finally always returning 0.02, protecting bpy.app.timers from dropping on unhandled exceptions).
   - Method parity in _dispatch: implement handlers for morphomesh.render_preview, morphomesh.capture_viewport, morphomesh.setup_inspector_camera, morphomesh.critique_visual_quality, morphomesh.create_human_asset, and complete scene status statistics in morphomesh.get_scene_status.
2. Update src/morphomesh/blender_bridge.py:
   - NDJSON streaming in send_socket_request() (append b\n, line-buffered response parsing, timeout handling, clean socket disposal).
   - Fix execute() line 506-512 condition so socket responses containing image_path, camera_name, defects, status, success, object_count, etc. are recognized as successful and not falsely routed to headless CLI fallback.
   - Add typed client helper methods: capture_viewport(), setup_inspector_camera(), critique_visual_quality().
   - Add headless script branches in _generate_headless_script() for these methods as reliable offline fallbacks.
3. Create tests/test_bridge_socket_parity.py:
   - Implement the test suite designed in explorer_m1_3/handoff.md covering connection lifecycle, rapid NDJSON streaming, malformed data resilience, timer immortality exception trapping, and method parity.
4. Verification:
   - Run tests with pytest: pytest tests/test_bridge_socket_parity.py -v and pytest tests/test_blender_bridge.py -v.
   - Verify 100% pass rate.
5. Reporting:
   - Update your progress in e:\tool\mcp\MorphoMesh\.agents\worker_m1\progress.md.
   - Write your comprehensive handoff report to e:\tool\mcp\MorphoMesh\.agents\worker_m1\handoff.md with passing test commands, verification outputs, and summary of changes.
   - Send completion message to parent orchestrator (conv ID: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9).
</USER_REQUEST>
