# Dispatch Instructions - reviewer_human_m4_iter6_1

**Agent ID**: reviewer_human_m4_iter6_1
**Archetype**: teamwork_preview_reviewer
**Parent**: orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7)
**Date**: 2026-09-07T05:21:00+07:00

## Mandatory Reading (Read FIRST)
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. Worker M4 Iteration 6 Handoff: E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter6\handoff.md
5. Master Asset: output/yu_nian_an/Yu_Nian_An_Master.blend

## Assignment: Master Scene Hierarchy, Rigging, Clearance & Camera Verification
Review Milestone 4 Iteration 6 deliverables:
1. Verify 7-tier collection hierarchy in `output/yu_nian_an/Yu_Nian_An_Master.blend`:
   - `Yu_Nian_An_Master`, `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, `05_Armature`, `06_Lights_Camera`.
   - Confirm all modular face sub-meshes (`Mesh_Lips`, `Mesh_Eyelid_Left`, `Mesh_Eyelid_Right`, `Mesh_Eye_*`) are in `01_Body` and parented to `Yu_Nian_An_Body`.
2. Verify Rigging & Blendshapes:
   - Armature contains exactly 163 DEF bones.
   - Body mesh contains 2,036 pure quads, 2,144 vertices, and all 52 ARKit FACS shape keys with non-zero deltas.
   - Confirm `Mesh_Lips` (50 pure quads, 66 verts) and eyelid meshes are rigged to `DEF-head` with 100% weights.
3. Verify Bodice & Wardrobe Clearance:
   - Zero BVH face overlaps and minimum clearance >= +4.0mm.
4. Verify Camera Optics:
   - `Camera_FullBody` (50.0mm, distance 5.5m) framing full 1.65m character in NDC Y in [0.05, 0.95] (zero decapitation).
   - `Camera_Portrait_85mm` (85.0mm) framing head/bust.
5. Run unit tests and Deliver your verdict (APPROVE or REQUEST_CHANGES) in `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_1\handoff.md` and message orchestrator_human_1.

## 2026-09-06T22:21:02Z
You are reviewer_human_m4_iter6_1.
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_1
Your parent is orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7).

Read your dispatch file at E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_1\DISPATCH.md.
Read all mandatory reading files:
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. Worker M4 Iteration 6 Handoff: E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter6\handoff.md
5. Master Asset: output/yu_nian_an/Yu_Nian_An_Master.blend

Review Master Scene Hierarchy (7 collections), Rigging (163 DEF bones, 52 shape keys, Mesh_Lips and eyelids rigging), Bodice Clearance (>= +4mm, 0 overlaps), and Camera Framing (50mm fullbody, 85mm portrait).
Deliver your verdict: APPROVE or REQUEST_CHANGES in E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_1\handoff.md and message orchestrator_human_1.

