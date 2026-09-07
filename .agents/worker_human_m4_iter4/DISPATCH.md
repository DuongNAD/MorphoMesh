## 2026-09-06T20:50:50Z
<USER_REQUEST>
You are worker_human_m4_iter4.
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter4
Your parent is orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7).

MANDATORY READING (DO NOT SKIP):
1. Read E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md.
2. Read E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md.
3. Read E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md.
4. Read Reviewer 2 Iteration 3 Handoff Report (Full analysis of hair occlusion & facial contours):
   E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter3_2\handoff.md
5. Check reference turnaround artwork:
   C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR ASSIGNMENT:
Milestone 4 Iteration 4: Final Aesthetic Polish (Hair Anterior Offset & Facial Contours).
You have exclusive write ownership of:
- src/morphomesh/human_grooming.py
- src/morphomesh/human_generator.py
- src/morphomesh/character_assembler.py
- tests/test_character_assembler.py
- tests/test_human_grooming.py
- tests/test_human_generator.py
- output/yu_nian_an/ (Master blend file and rendered verification images)

TASKS TO COMPLETE:
1. Hair Splines Anterior Offset (src/morphomesh/human_grooming.py):
   - In `generate_hime_cut_splines()`:
     * Currently hair splines were generated at Y in [-0.065m, -0.092m], burying bangs (54%), eyebrows (100%), eyelashes (100%), crown (91%), and sidelocks (64%) deep inside the cranium (whose surface is at Y = -0.101m to -0.1258m).
     * Reposition all frontal and crown hair splines so they originate from the scalp and project anteriorly outside the facial skin:
       - Forehead bangs: shift Y to `[-0.120m, -0.138m]` at Z in [1.51m, 1.58m], draping cleanly in front of the forehead.
       - Eyebrows: shift Y to `~ -0.128m` at Z in [1.535m, 1.545m], arching above the eyes.
       - Eyelashes: shift Y to `~ -0.130m` at Z in [1.515m, 1.522m], lining the anterior eyelid rims.
       - Sidelocks: shift Y to `[-0.110m, -0.125m]` at X = +/- 0.082m, cascading down to Z ~ 1.35m.
       - Scalp crown: expand radius to `r_c ~ 0.090m` (from 0.065m) so crown curves envelop the skull mesh.
     * Ensure `convert_curves_to_ribbon_mesh()` and the Geometry Nodes tree reflect these positions.
     * Verify hair visibility: In Blender depsgraph, verify >= 90% of bangs, eyebrows, eyelashes, and sidelock vertices are EXTERIOR to the body mesh (dot product with surface normal >= 0).

2. Facial Contour Definition & Likeness (src/morphomesh/human_generator.py and/or character_assembler.py):
   - Elevate the head mesh from a featureless ellipsoid into an elegant semi-realistic female face matching Yu Nian An:
     * Nose bridge & tip: Add forward protrusion along -Y for frontal vertices at Z in [1.50m, 1.54m] (nose tip reaching Y ~ -0.135m to -0.138m).
     * Mouth / lips: Define upper and lower lip contours at Z in [1.46m, 1.485m] (Y ~ -0.124m) with subtle mouth corner / philtrum indent.
     * Orbital sockets: Slight recessed cavity at X = +/- 0.035m, Z ~ 1.515m (Y ~ -0.116m) so eye spheres sit naturally within eye sockets.
     * Crucial: Maintain 100% pure quads (0 tris, 0 ngons), preserve all 29 vertex groups, landmark coordinates, and 52 ARKit FACS shape keys!

3. Regenerate Master Blend & Beauty Verification Renders:
   - Run the updated generator inside Blender 4.5.4 LTS to cleanly regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend`.
   - Re-render:
     * `output/yu_nian_an/master_portrait_clean.png` (85mm portrait camera: verify prominent lush hime bangs, visible eyebrows/eyelashes, delicate nose and lips, melancholic gaze).
     * `output/yu_nian_an/master_fullbody_clean.png` (50mm full-body camera: verify full-body framing, sash, skirt, sandals, cords, butterflies).

4. Verification & Testing:
   - Run `pytest tests/test_character_assembler.py tests/test_human_grooming.py tests/test_human_generator.py -v`.
   - Run full regression test suite `pytest tests/` to verify 100% pass rate.

5. Deliver your handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter4\handoff.md` and send a message back to orchestrator_human_1 when finished.
</USER_REQUEST>
