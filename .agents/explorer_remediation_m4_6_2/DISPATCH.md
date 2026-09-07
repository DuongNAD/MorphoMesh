# Dispatch Instructions - explorer_remediation_m4_6_2

**Agent ID**: explorer_remediation_m4_6_2
**Archetype**: teamwork_preview_explorer
**Parent**: orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7)
**Date**: 2026-09-07T04:57:00+07:00

## Mandatory Reading (Read FIRST)
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter5_2\handoff.md (Reviewer 2 Iteration 5 Full Evidence Report)
5. E:\tool\mcp\MorphoMesh\.agents\auditor_human_m4_iter5_1\handoff.md
6. Reference Turnaround Art: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg

## Assignment: Anime Lip/Mouth Definition & Eye/Eyelid Framing
Investigate and formulate an exact, verified technical plan for authentic facial feature remediation matching Yu Nian An's aesthetic:
1. **Delicate Anime Mouth / Lip Remediation**:
   - Reviewer 2 showed that assigning `Mat_Human_Lips` to 2 coarse base mesh quads (377, 378) created a flat 25mm x 33mm pink rectangular sticker slapped onto the lower face.
   - Investigate how to achieve an authentic delicate anime mouth matching `media_1788716034772.jpg`:
     * Option A: Dedicated procedural curved lip / oral fissure mesh (`Mesh_Lips` or `Mesh_Mouth_Fissure`) parented to head and bound to `DEF-head`, with upper lip cupid's bow, dark oral commissure slit, and soft rose lower lip vermilion.
     * Option B: Refine the vertex weighting / shader blending / vertex color or procedural displacement in `human_generator.py` and `character_assembler.py` while preserving 100% pure quads (2,036 quads on body mesh) and all 52 ARKit FACS shape keys.
2. **Almond Eyelids & Eye Optics Remediation**:
   - Currently `Mesh_Eyelid_Left` and `Mesh_Eyelid_Right` form a swollen, polygonal lower eyelid pouch with uniform skin SSS, and eye spheres appear as lifeless grey marbles.
   - Formulate exact geometry / shader fixes:
     * Add a dark eyeliner / superior lash margin material (deep charcoal/black) along the upper palpebral border.
     * Smoothly blend the lower eyelid margin into the infraorbital cheek to eliminate the puffy eye bag shelf.
     * Ensure `Mat_Human_Eye_Inner_Iris` displays high-contrast dark pupil and slate-grey iris pattern visible through the refractive cornea.
3. Write your findings and recommended plan in `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_2\handoff.md` and message orchestrator_human_1.
