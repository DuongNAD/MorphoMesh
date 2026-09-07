# Dispatch Instructions - reviewer_human_m4_iter6_2

**Agent ID**: reviewer_human_m4_iter6_2
**Archetype**: teamwork_preview_reviewer
**Parent**: orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7)
**Date**: 2026-09-07T05:21:00+07:00

## Mandatory Reading (Read FIRST)
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. Reviewer 2 Iteration 5 Report: E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter5_2\handoff.md (Your previous report)
5. Worker M4 Iteration 6 Handoff: E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter6\handoff.md
6. Reference Turnaround Art: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg

## Assignment: Aesthetic Likeness, Lips, Eyes, Bangs & Shading Review
Review Milestone 4 Iteration 6 remediations against all 4 defects flagged in Iteration 5:
1. **Mouth & Lip Likeness**:
   - Inspect `output/yu_nian_an/master_portrait_clean.png` and `output/yu_nian_an/Yu_Nian_An_Master.blend`.
   - Confirm body mesh polygons 377 and 378 are reset to `slot_skin` (flat 25mm x 33mm pink rectangle sticker completely eradicated).
   - Confirm dedicated pure-quad `Mesh_Lips` (50 pure quads, 66 verts) displays authentic anime lip features: delicate cupid's bow, dark oral fissure slit (`Mat_Human_Oral_Slit`), and pillowed soft rose vermilion (`Mat_Human_Lips`).
2. **Forehead Bangs Coverage & Silhouette**:
   - Confirm vector math fix in `src/morphomesh/human_grooming.py`: measure actual quad X-widths in `Hair_Hime_Bangs` (must be ~7.5mm, NOT 2.25mm).
   - Confirm adjacent ribbon overlap (>= 1.0mm) across all 36 splines: verify 0 comb barcode gaps exposing forehead skin.
   - Confirm lateral roots and tips curve backward along the temple profile, eliminating the 80mm overhang and 90-degree square cardboard visor.
3. **Eyelids & Eye Optics**:
   - Confirm almond eyelids have a prominent upper eyeliner band (`Mat_Human_Eyeliner`) and flush lower cheek margin (0 puffy eye-bag shelf).
   - Confirm eye spheres have forward planar UV coordinates and display high-contrast pupil, slate-grey iris, dark limbal ring, and white sclera through the cornea.
4. **Cranial Apex Glare & Hair Sheen**:
   - Confirm white crescent glare on cranial apex is eliminated (matte `Mat_Human_Scalp` on 73 scalp polys, `Mat_Human_Hair` coat weight 0.08, rim light 450W).
   - Confirm silky East Asian anisotropic hair sheen.
5. Deliver your verdict (APPROVE or REQUEST_CHANGES) in `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_2\handoff.md` and message orchestrator_human_1.
