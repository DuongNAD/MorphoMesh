# Dispatch Instructions - explorer_remediation_m4_6_1

**Agent ID**: explorer_remediation_m4_6_1
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

## Assignment: Bangs Ribbon Width Vector Math & Forehead Gap Elimination
Investigate and formulate an exact, mathematically verified code fix for the bangs ribbon generation in `src/morphomesh/human_grooming.py`:
1. **Mathematical Defect in `convert_curves_to_ribbon_mesh` (lines 373-396)**:
   - Reviewer 2 proved: dividing side vector $(sx, sy)$ by 3D spline length $dlen = \sqrt{dx^2 + dy^2 + dz^2}$ scales the horizontal ribbon width down by $dy/dlen \approx 0.35$ for vertical bangs ($dz \approx -0.108\text{m}, dy \approx -0.040\text{m}$).
   - A requested 7.0mm ribbon shrinks to an average quad width of only 2.25mm, leaving 3.52mm empty gaps (61% open space) between 5.77mm-spaced splines!
2. **Formulate Exact Mathematical Formulation**:
   - Determine how to construct a true horizontal or binormal vector orthogonal to the spline tangent and normal, ensuring ribbons achieve their full 7.0mm - 8.0mm width across $X$ regardless of spline steepness $dz$.
   - Calculate exact strand density / count (e.g. 32-36 splines across $X \in [-0.078\text{m}, +0.078\text{m}]$) and geometric overlap ($\ge 1.0\text{mm}$) to guarantee 100% continuous curtain coverage with zero gaps.
   - Design gentle curvature for lateral bangs edges so they curve softly backwards/downwards into the temples rather than forming a rigid 90-degree square cardboard box visor.
3. Write your findings and recommended implementation plan in `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_1\handoff.md` and message orchestrator_human_1.
