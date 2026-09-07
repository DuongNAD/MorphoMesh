## 2026-09-07T03:13:40+07:00

You are worker_human_m4_iter2.
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter2
Your parent is orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7).

MANDATORY READING:
1. Read E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md.
2. Read E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md.
3. Read E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md.
4. Read Reviewer 2 Report: E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_2\handoff.md.
5. Read Challenger Report: E:\tool\mcp\MorphoMesh\.agents\challenger_human_m4_1\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR ASSIGNMENT:
Remediate all 6 defect areas identified across Milestone 4:

1. Fix Hair Geometry Nodes Interface in Blender 4.5+ (Critical):
   - In `src/morphomesh/human_grooming.py` (`build_hair_geom_node_tree` & `get_grooming_script`):
     In Blender 4.0+, you must declare interface sockets on `tree.interface`:
     ```python
     if hasattr(tree, "interface"):
         tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
         tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
     ```
     Ensure input node output connects through the modifiers (CurveSplineParameter -> MapRange -> SetCurveRadius, Clump, Noise, SetMaterial) to output node input.
     Verify that in Blender 4.5.4 LTS, `GN_HairGroom` compiles without `Node group must have an output socket` and hair curves evaluate to real non-zero vertices!

2. Position and Rig Magic Props (Butterflies & Marionette Strings) (Critical):
   - In `src/morphomesh/character_assembler.py` and `src/morphomesh/wardrobe.py`:
     * Position the 10 butterflies dynamically in 3D space: anchor each butterfly `Prop_Butterfly_00..09` at or near the distal tip of its corresponding cord, fluttering around Yu Nian An's hands and flanks in mid-air (Z ~ 0.85m to 1.3m, varied X and Y offsets), NOT at `(0, 0, 0)` on the floor!
     * Align cords with current hand rest pose: string proximal coordinates must originate at actual hand finger distal positions (Z ~ 0.85m to 0.90m) rather than elevated pose.
     * Rig the cords and butterflies: Assign vertex group weights to `Prop_Marionette_Strings` corresponding to the 10 finger DEF bones (`DEF-thumb.03.L/R`, `DEF-f_index.03.L/R`, `DEF-f_middle.03.L/R`, `DEF-f_ring.03.L/R`, `DEF-f_pinky.03.L/R`), and add an Armature modifier (or ChildOf / Hook constraints) linking strings and butterflies to the character armature so they articulate when posed!

3. Unbury Eyes & Ensure Facial Features:
   - In `src/morphomesh/character_assembler.py`:
     * Move eye sphere meshes forward to anterior ocular plane (`eye_y ~ -0.115` to `-0.120`) matching where the front face surface is (`Y ~ -0.1258`), so corneas and irises are visible on the exterior of the face rather than buried 5.7cm inside the cranium.

4. Aim Studio 3-Point Lights at Character:
   - In `src/morphomesh/character_assembler.py`:
     * Aim all 3 area lights (`Light_Key_Softbox`, `Light_Fill_Softbox`, `Light_Rim_HairLight`) at Yu Nian An's chest/head center `(0.0, 0.0, 1.25)` by adding a `TRACK_TO` constraint to each light targeting an empty object at `(0.0, 0.0, 1.25)`, or setting explicit Euler rotations so they illuminate the front face, body, and rim halo instead of shining straight down into the floor.

5. Calibrate Camera Framing:
   - In `src/morphomesh/character_assembler.py`:
     * Camera framing must properly capture the character without decapitation:
       - Set `Camera_FullBody` at distance ~5.5m (or appropriate focal length) to frame Yu Nian An's full 1.65m height.
       - Set `Camera_Portrait_85mm` framed on bust/portrait centered at `Z = 1.55m` (distance ~1.8m to 2.2m) capturing the head, melancholic eyes, and hime cut bangs.

6. Wardrobe Color Aesthetics:
   - In `src/morphomesh/character_assembler.py`:
     * Assign pale satin ice-blue/white `Mat_Sash_Satin` to `Mesh_Dress_WaistSash` and light/white leather to sandals, matching reference image `media_1788716034772.jpg`.

7. Regenerate Master .blend File & Verification:
   - Regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend`.
   - Run `pytest tests/test_character_assembler.py -v`.
   - Run full pytest regression suite.
   - Deliver handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter2\handoff.md` and message orchestrator_human_1.
