# Dispatch Instructions - explorer_remediation_m4_6_3

**Agent ID**: explorer_remediation_m4_6_3
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

## Assignment: Cranial Apex Glare Elimination, Hair Shading & Card Silhouette
Investigate and formulate an exact, verified technical plan for hair material and cranial lighting aesthetics:
1. **Cranial Apex White Crescent Glare**:
   - Reviewer 2 identified that the 750W rim light (`Light_Rim_HairLight`) reflecting off `Coat Weight = 0.50` and `Coat Roughness = 0.06` on `Mat_Human_Hair` at Polygon 522 (cranial apex, $Z \approx 1.642\text{m}$) bounces directly into `Camera_Portrait_85mm`, producing a glaring white crescent dome highlight.
   - Investigate how to eliminate this glare:
     * Reduce clearcoat on scalp polygons / hair ribbons (`Coat Weight <= 0.15`, `Coat Roughness >= 0.25`, or dedicated scalp material).
     * Extend or adjust `Hair_Scalp_Crown` ribbons over the cranial apex to diffuse and break up direct specular reflection.
     * Tune rim light angle/power or shader specular response.
2. **Hair Ribbons Silky East Asian Sheen vs Plastic Tape**:
   - Ensure hair ribbons render as deep silky jet-black East Asian hair with an organic anisotropic angel-ring highlight rather than mirror-like glossy plastic tape.
3. **Bangs Silhouette Curvature**:
   - Soften lateral bangs geometry so ribbons curve naturally around the forehead contour instead of projecting as sharp 90-degree square cardboard box corners.
4. Write your findings and recommended plan in `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_3\handoff.md` and message orchestrator_human_1.
