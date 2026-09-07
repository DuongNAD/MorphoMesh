# Task Assignment: Milestone 4 Iteration 7 Victory Remediation Worker

## Agent Identity
- Agent: `worker_human_m4_iter7`
- Archetype: `teamwork_preview_worker`
- Parent: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)
- Working Directory: `E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter7`

## Mandatory Reading
1. `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md`
2. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md`
3. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md`
4. Reviewer 2 Iteration 6 Report: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_2\handoff.md`
5. Challenger 1 Iteration 6 Report: `E:\tool\mcp\MorphoMesh\.agents\challenger_human_m4_iter6_1\handoff.md`
6. Auditor Iteration 6 Report: `E:\tool\mcp\MorphoMesh\.agents\auditor_human_m4_iter6_1\handoff.md`
7. Reference Turnaround Art: `C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You have exclusive write ownership of:
- `src/morphomesh/character_assembler.py`
- `tests/test_character_assembler.py`
- `output/yu_nian_an/` (Master blend, renders, verification images)
- `E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter7\`

Do NOT alter base mesh vertex coordinates or topology in `human_generator.py` (2,036 pure quads, 2,144 vertices).

## Technical Remediation Tasks

### 1. Advance `Mesh_Lips` Forward in Y (Eliminate 78.8% Submersion)
- Location: `src/morphomesh/character_assembler.py` in `create_delicate_anime_lips_mesh()`.
- Problem: The anterior facial skin surface at mouth level is $Y = -0.1238\text{m}$. Setting `center_y = -0.1169 * s` placed `Mesh_Lips` 6.9mm behind the skin, submerging 52 of 66 vertices (78.8%) inside the skull.
- Fix: Set `center_y = -0.1245 * s` (or calibrate so all 66 vertices have signed normal clearance $+0.3\text{mm}$ to $+1.5\text{mm}$ in front of the facial skin, with 0 penetrations).
- Verification: In Blender depsgraph, verify `Mesh_Lips` signed distance to `Yu_Nian_An_Body` has 0 penetrating vertices (min signed clearance >= +0.1mm, avg ~ +0.6mm). Cupid's bow, oral fissure, and pillowed lower vermilion must be beautifully visible in portrait renders.

### 2. Fix Material Slot Wipe in `Mesh_Lips` and `Mesh_Eyelid_*`
- Location: `src/morphomesh/character_assembler.py` lines ~705-715.
- Problem: Calling `e_obj.data.materials.clear()` in line 705 resets all polygon `material_index` attributes to 0 in Blender Python, wiping out `Mat_Human_Oral_Slit` on `Mesh_Lips` (100% assigned to slot 0) and `Mat_Human_Skin_SSS` on lower eyelids.
- Fix: After appending material slots (or without clearing), re-assign the polygon material indices:
  * For `Mesh_Lips`: row $r=2$ quads (columns $1 \le c \le n\_cols - 2$) get `material_index = 1` (`Mat_Human_Oral_Slit`); all other quads get `material_index = 0` (`Mat_Human_Lips`).
  * For `Mesh_Eyelid_*`: row 0 quads get `material_index = 0` (`Mat_Human_Eyeliner`); row 1 quads get `material_index = 1` (`Mat_Human_Skin_SSS`).
- Verification: In Blender asset, verify `Mesh_Lips` polygon material distribution contains both slot 0 (`Mat_Human_Lips`) and slot 1 (`Mat_Human_Oral_Slit`), and eyelids contain both slot 0 and slot 1.

### 3. Add Armature Modifier and `DEF-head` Vertex Group to Eye Spheres and Hair Layers
- Location: `src/morphomesh/character_assembler.py` lines ~725-735.
- Problem: `eye_left_cornea`, `eye_right_cornea`, `eye_left_iris`, `eye_right_iris`, and the 6 hair layer objects were parented only via object parenting without Armature modifiers. When `DEF-head` rotates 30°, they remained stationary at 0.00mm displacement, shearing out of the head by 54.42mm.
- Fix: Include all 4 eye spheres and all 6 hair layers (`Hair_Hime_Bangs`, `Hair_Eyebrows`, `Hair_Eyelashes`, `Hair_Scalp_Crown`, `Hair_Hime_Sidelocks`, `Hair_Back_Cascade`) in the Armature modifier binding loop with vertex group `DEF-head` (weight = 1.0):
  ```python
  rigged_facial_objects = [
      eyelid_left, eyelid_right, lip_mesh,
      eye_left_cornea, eye_right_cornea,
      eye_left_iris, eye_right_iris,
      *hair_objects
  ]
  for obj in rigged_facial_objects:
      if obj:
          vg_head = obj.vertex_groups.get("DEF-head") or obj.vertex_groups.new(name="DEF-head")
          vg_head.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
          arm_mod = obj.modifiers.get("Armature") or obj.modifiers.new("Armature", 'ARMATURE')
          arm_mod.object = arm_obj
          arm_mod.use_deform_preserve_volume = True
  ```
- Verification: Rotate `DEF-head` pose bone by 30° in evaluated depsgraph; verify eye spheres, eyelids, lips, and hair layers deform identically with 0.00mm shear detachment.

### 4. Regenerate Master Asset & Beauty Renders
- Regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend`.
- Re-render:
  * `output/yu_nian_an/master_portrait_clean.png` (85mm portrait camera: verify visible delicate rose lips with dark oral slit, framed almond eyes, full bangs, 0 cranial glare).
  * `output/yu_nian_an/master_fullbody_clean.png` (50mm camera: full body, sash, dress clearance, finger cords, mid-air butterflies).
  * Render close-up face plate `audit_face_closeup.png` to certify lips and eyes.

### 5. Testing & Handoff
- Run `pytest tests/test_character_assembler.py tests/test_human_grooming.py -v`
- Run full regression test suite `pytest tests/` (verify 100% pass rate).
- Deliver your handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter7\handoff.md` and message orchestrator_human_1.

## 2026-09-06T22:29:15Z
Received dispatch from orchestrator_human_1 (fa73b7ae-2239-4440-89d0-f3a69497b7b7).
Tasks:
1. Mesh_Lips Positioning (center_y = -0.1245 * s)
2. Fix Material Slot Index Wipe
3. Armature Modifiers on Eye Spheres & Hair Layers
4. Regenerate Master Asset & Re-Render
5. Full regression testing & handoff

## 2026-09-06T22:39:32Z
Status checkpoint from orchestrator_human_1 (fa73b7ae-2239-4440-89d0-f3a69497b7b7):
Observed assemble_and_render.py and audit_face_closeup.png generated. Requested status update and handoff.md once tests pass.
