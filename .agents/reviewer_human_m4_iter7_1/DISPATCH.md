# Dispatch: reviewer_human_m4_iter7_1 (Master Scene Architecture & Rigging Reviewer)

## Agent Identity
- Agent: `reviewer_human_m4_iter7_1`
- Archetype: `teamwork_preview_reviewer`
- Parent: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)
- Working Directory: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter7_1`

## Mandatory Reading
1. `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md`
2. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md`
3. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md`
4. Worker Iteration 7 Handoff: `E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter7\handoff.md`
5. Master Asset: `E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend`

## Your Review Assignment
Review Milestone 4 Iteration 7 deliverables focusing on Master Scene Architecture, Rigging, and Component Integration:
1. **Scene Hierarchy & Collections**:
   - Confirm exactly 7 collections: `Yu_Nian_An_Master`, `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, `05_Armature`, `06_Lights_Camera`.
   - Confirm all required mesh objects, materials with fake users, 163 DEF bones, and 52 ARKit FACS keys.
2. **Armature Modifiers & Head Kinematics**:
   - Verify that all 4 eye spheres (`Mesh_Eye_*`) and all 6 hair layers (`Hair_*`) possess an `Armature` modifier pointing to `Armature_Yu_Nian_An_Rigify` with vertex group `DEF-head` (weight = 1.0) and `use_deform_preserve_volume = True`.
   - Confirm that under 30° `DEF-head` rotation in evaluated depsgraph, all facial components, eye spheres, and hair layers deform seamlessly with 0.00mm separation shear.
3. **Camera Optics & Bodice Clearance**:
   - `Camera_FullBody` (50.0mm lens, distance 5.5m): character fits vertically in NDC Y `[0.05, 0.95]`.
   - `Camera_Portrait_85mm` (85.0mm lens): head and bust framing.
   - Bodice signed clearance >= +4.0mm with 0 BVH face overlaps.
4. **Testing**:
   - Run `pytest tests/test_character_assembler.py tests/test_human_grooming.py -v`.
5. **Deliver Verdict**:
    - Write your verdict (`APPROVE` or `REQUEST_CHANGES`) with full rationale in `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter7_1\handoff.md` and message orchestrator_human_1.

## 2026-09-06T22:41:10Z
Received dispatch request:
You are reviewer_human_m4_iter7_1.
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter7_1
Your parent is orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7).
Review Master Scene Architecture (7 collections), Armature Modifiers on Eye Spheres & Hair Layers, 30° head bone deformation kinematics (0.00mm shear detachment), Bodice Clearance (>= +4mm, 0 overlaps), and Camera Framing (50mm fullbody, 85mm portrait).
Deliver your verdict: APPROVE or REQUEST_CHANGES in E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter7_1\handoff.md and message orchestrator_human_1.
