## 2026-09-08T16:18:49Z

You are the Lead Implementation Worker for the MorphoMesh Production Upgrade (Milestones M4 & M5).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\worker_prod_upgrade_1
Workspace root: E:\tool\mcp\MorphoMesh

Read the authoritative user request at:
E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically the latest entry ## 2026-09-08T16:06:11Z).

Also read the survey reports from the Explorers:
- E:\tool\mcp\MorphoMesh\.agents\explorer_survey_1\survey_report.md (FastMCP tools, gating, schema imports)
- E:\tool\mcp\MorphoMesh\.agents\explorer_survey_2\survey_report.md (Visual critic, inspector camera, viewpoints, capture)
- E:\tool\mcp\MorphoMesh\.agents\explorer_survey_3\survey_report.md (Socket IPC, character pipelines, 18 test failure diagnoses)
- E:\tool\mcp\MorphoMesh\.agents\orchestrator_prod_qa_1\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & File Ownership:
You have exclusive write ownership of:
- `src/morphomesh/server.py`
- `blender_addon/morphomesh/listener.py`
- `src/morphomesh/wardrobe.py`
- `src/morphomesh/human_generator.py`
- `src/morphomesh/human_rigging.py`
- `PROJECT.md`
- `README.md`
- `artifacts/` and `output/` (for previews and regenerated assets)

Your Mission & Concrete Tasks:
1. FastMCP Server Hardening (M4):
   - In `src/morphomesh/server.py`:
     * Import `SetupInspectorCameraInput`, `SetupInspectorCameraOutput`, `CaptureViewportInput`, `CaptureViewportOutput`, `VisualCritiqueInput`, `VisualCritiqueOutput` from `morphomesh.models`.
     * Update `morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, and `morphomesh_critique_visual_quality` to validate arguments using the corresponding Pydantic v2 input models, catching `ValidationError` and re-raising as `ToolError`.
     * Ensure all 17 tools remain registered and the 3 environment gating flags (`MORPHOMESH_INCLUDE_ALL_TOOLS`, `MORPHOMESH_INCLUDE_HUMAN_TOOLS`, `MORPHOMESH_INCLUDE_INSPECTION_TOOLS`) function perfectly with 100% backward compatibility (7 tools default).
2. Socket IPC Listener Hardening (M4):
   - In `blender_addon/morphomesh/listener.py`:
     * In `_accept_loop`, safely handle `self.socket.settimeout(1.0)` to suppress `OSError: [WinError 10038]` during test teardown when the socket is closed.
3. Wardrobe Bodice Bust Clearance (M5):
   - In `src/morphomesh/wardrobe.py`:
     * In `generate_dress_bodice()`, expand the anterior contour around the bust apex ($Z \in [1.08, 1.15]$) by ~16mm ($+0.016\text{m}$) so that no bodice vertices penetrate the teardrop bust contour, ensuring $s_i \ge +0.0018\text{m}$ clearance and fixing the 5 bodice penetration test failures.
4. Base Mold Anatomy & Topology Hardening (M5):
   - In `src/morphomesh/human_generator.py`:
     * Mandibular jawline / chin projection: adjust chin anterior tip displacement delta by $-0.005\text{m}$ along Y so chin-to-neck anterior separation is $\ge 0.045\text{m}$ (fixing `test_t1_11_mandibular_jawline_and_chin_sharpness`).
     * Inverted quad normal winding: reverse vertex order `(f[0], f[3], f[2], f[1])` on the 8 clockwise quad faces in `generate_human_base_mesh()` around the axillary-trapezius junction and inner ankle seam so all face normals point outward ($\ge 99.5\%$ outward normals, 0 inverted faces; fixing the 5 normal winding failures).
     * Waist-to-hip ratio: adjust circumferential radius/projection so effective WHR is in the feminine target range $[0.67, 0.72]$ (e.g. $\approx 0.697$, currently 0.7422; fixing the 4 WHR test failures).
5. Upper Limb Twist Skinning Weight Normalization (M5):
   - In `src/morphomesh/human_rigging.py`:
     * Normalize twist weight assignment between `DEF-upper_arm.L` and `DEF-upper_arm.02.L` using linear interpolation along the humerus length (fixing `test_dual_bone_twist_decomposition_upper_limb`).
6. Character Master Asset Regeneration & Inspection Previews (M5):
   - Re-run `scripts/build_ultimate_yu_nian_an.py` to regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend` and update production exports (`.glb`, `.fbx`, textures).
   - Generate multi-angle preview images in `artifacts/inspection_previews/` using the inspector camera / viewport capture (6 canonical viewpoints: front, side, back, three_quarter, head, hands).
   - Run `verify_bear_anatomy.py` and `tests/test_bear_anatomy.py` to verify Armored War Bear character.
7. 100% Repository Test Pass Verification:
   - Run `uv run pytest -v tests/` across all 87 test files (2,071 tests).
   - Verify 100% of tests pass with 0 failures and 0 regressions!
8. Documentation Update (M5):
   - Update `PROJECT.md` (mark M4 and M5 as DONE with full verification details).
   - Update `README.md` reflecting completion of Milestones M4 and M5.
