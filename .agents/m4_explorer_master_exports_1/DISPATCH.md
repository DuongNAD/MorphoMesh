# Task Dispatch — M4 Explorer 3 (Production Master Deliverables & Quality Verification Strategy)

## Objective
Formulate the exact technical implementation strategy for Feature 18 (Strict Quality Verification) and Feature 20 (Multi-Format Production Master Deliverables):
1. Master Export Pipeline (`scripts/build_ultimate_yu_nian_an.py`):
   - `output/yu_nian_an/Yu_Nian_An_Master.blend`: Complete 7-tier collection hierarchy, packed textures, rigged with 163 DEF bones, 52 ARKit FACS shape keys.
   - `output/yu_nian_an/Yu_Nian_An.glb`: glTF 2.0 binary with embedded 4K PBR textures, 163 DEF skeletal hierarchy, `extras.targetNames` with all 52 ARKit blendshapes, `TEXCOORD_0` on all primitives.
   - `output/yu_nian_an/Yu_Nian_An.fbx`: FBX binary containing complete 163 DEF armature, bind pose, materials, and blendshapes.
   - 9 uncompressed 4K PBR texture maps in `output/yu_nian_an/textures/` (Skin Albedo, Normal, Roughness; Dress Albedo, Normal, Sheen; Sash Albedo, Metallic, Roughness).
2. Automated Quality Verification Script (`scripts/verify_ultimate_yu_nian_an.py` or similar):
   - 0 signed distance penetrations between wardrobe and body mesh ($s_i \ge -0.0005$m).
   - 100% outward normals ($c_x n_x + c_y n_y > 0$).
   - 100% quads in all deforming joints.
   - 0 detached marionette string endpoints (snapping error < 0.001mm).
3. Evaluate compatibility with existing tests in `tests/test_production_exports.py` and `tests/test_challenger_m5_empirical.py`.

## Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`

## Output
Write report to `E:\tool\mcp\MorphoMesh\.agents\m4_explorer_master_exports_1\handoff.md`
Notify orchestrator via `send_message` when done.
