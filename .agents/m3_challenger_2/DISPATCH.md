# Task Dispatch — M3 Challenger 2 (Stress, Rigging Deformation & Live Blender Audit)

## Objective
Perform adversarial stress testing on Milestone 3 rigging and assembly:
1. Verify Joint Deformation & Preservation of Volume:
   - Elbow 90° flexion: thickness retention >= 85%, no volume pinch, minimum vertex count around elbow ICR.
   - Knee flexion: patella stabilization >= 90% on shin, no collapse of knee cavity.
   - Finger articulation: 5-digit isolation under extreme arm spans ($s=2.0$), zero vertex collapse into thumb.
2. Verify Live Blender Master Asset (`output/yu_nian_an/Yu_Nian_An_Master.blend`):
   - 0 wardrobe penetrations ($s_i \ge 0.0$mm).
   - Signed wardrobe clearance >= +5.5mm.
   - Active armature pose rotation with non-zero mesh displacement (`max_disp > 0.0m`).
   - 52 ARKit FACS shape keys present with non-zero delta vectors.
3. Run test verification:
   - `uv run pytest tests/test_adversarial_rigging.py tests/test_adversarial_character_assembler.py -v`
4. Document exact empirical values and issue a binary verdict: `APPROVE` or `REQUEST_CHANGES`.

## Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`
- `E:\tool\mcp\MorphoMesh\.agents\m3_worker_assembly_rigging_1\handoff.md`

## Output
Write report to `E:\tool\mcp\MorphoMesh\.agents\m3_challenger_2\handoff.md`
Notify orchestrator via `send_message` when done.

## 2026-09-07T20:04:06Z
You are M3 Challenger 2 (Stress, Rigging Deformation & Live Blender Audit).
Your identity: M3 Challenger 2 (Stress, Rigging Deformation & Live Blender Audit).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\m3_challenger_2
You MUST create your own BRIEFING.md and progress.md in your working directory.

MANDATORY FIRST STEP: Read the authoritative user request at:
E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md

Also read your dispatch instructions at:
E:\tool\mcp\MorphoMesh\.agents\m3_challenger_2\DISPATCH.md
and the master project specification at:
E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md
and M3 Worker's handoff report at:
E:\tool\mcp\MorphoMesh\.agents\m3_worker_assembly_rigging_1\handoff.md

Challenger tasks:
1. Verify Joint Deformation & Preservation of Volume: elbow 90° flexion thickness retention >= 85%, knee flexion patella stabilization >= 90%, 5-digit finger isolation under extreme arm spans (s=2.0).
2. Verify Live Blender Master Asset (`output/yu_nian_an/Yu_Nian_An_Master.blend`): 0 penetrations, wardrobe clearance >= +5.5mm, active pose deformation (max_disp > 0.0m), 52 ARKit FACS shape keys with active deltas.
3. Run test verification:
   `uv run pytest tests/test_adversarial_rigging.py tests/test_adversarial_character_assembler.py -v`
4. Document exact empirical values and issue a binary verdict: APPROVE or REQUEST_CHANGES.

Produce handoff report at:
E:\tool\mcp\MorphoMesh\.agents\m3_challenger_2\handoff.md
Notify me via send_message when done.
