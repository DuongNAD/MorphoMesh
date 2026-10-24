# Dispatch Instructions — Challenger M2-Iter3-1 (GLB, FBX & Master Blend Empirical Verification)

## Identity
- **Name**: challenger_m2_iter3_1
- **Role**: GLB, FBX & Master Blend Empirical Challenger
- **Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\challenger_m2_iter3_1`
- **Parent Conversation ID**: `78de56ae-5f93-4a99-a306-f90155921566`

## Context
Read `e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-07T13:20:42Z`) and Worker M2 Iteration 3 handoff at `e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync\handoff.md`.

## Tasks
1. Empirically verify the master production deliverables in `output/yu_nian_an/`:
   - Inspect `Yu_Nian_An.glb`:
     * Read GLB JSON, verify 52 ARKit blendshapes in `extras.targetNames`.
     * Verify all mesh primitives have `TEXCOORD_0`.
     * Verify >= 190 scene nodes and skin joints.
   - Inspect `Yu_Nian_An.fbx`:
     * Verify binary format (Kaydara 7400), file size > 5 MB, and presence of all 163 DEF bones.
   - Inspect `Yu_Nian_An_Master.blend` using Blender 4.5 headless:
     * Check collections, `Armature_Yu_Nian_An_Rigify` with 163 DEF bones, 52 shape keys on `Yu_Nian_An_Body`, cameras 50mm, marionette string snapping.
2. Run test suites:
   ```powershell
   uv run pytest tests/test_production_exports.py tests/test_challenger_m5_empirical.py tests/test_adversarial_character_assembler.py -v
## 2026-09-07T15:23:00Z

<USER_REQUEST>
You are Challenger M2-Iter3-1 (GLB, FBX & Master Blend Empirical Verification).
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\challenger_m2_iter3_1
Your dispatch instructions are at: e:\tool\mcp\MorphoMesh\.agents\challenger_m2_iter3_1\DISPATCH.md
The authoritative user request is at: e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-07T13:20:42Z). Read it before starting work.
Refer also to Worker M2 Iteration 3 report and handoff at: e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync\.

Tasks:
1. Empirically verify the master production deliverables in `output/yu_nian_an/`:
   - Inspect `Yu_Nian_An.glb`: verify 52 ARKit blendshapes in `extras.targetNames`, `TEXCOORD_0` on all primitives, >= 190 scene nodes and skin joints.
   - Inspect `Yu_Nian_An.fbx`: verify binary format, file size > 5 MB, and presence of all 163 DEF bones.
   - Inspect `Yu_Nian_An_Master.blend` using Blender 4.5 headless: check collections, `Armature_Yu_Nian_An_Rigify` with 163 DEF bones, 52 shape keys, cameras 50mm, marionette string snapping.
2. Run test suites:
   `uv run pytest tests/test_production_exports.py tests/test_challenger_m5_empirical.py tests/test_adversarial_character_assembler.py -v`
3. Record verdict (APPROVE or REJECT) in `handoff.md` and message orchestrator when done.
</USER_REQUEST>

