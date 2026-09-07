# Dispatch Instructions - auditor_human_m4_iter6_1

**Agent ID**: auditor_human_m4_iter6_1
**Archetype**: teamwork_preview_auditor
**Parent**: orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7)
**Date**: 2026-09-07T05:21:00+07:00

## Mandatory Reading (Read FIRST)
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. Reviewer 2 Iteration 5 Report: E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter5_2\handoff.md
5. Worker M4 Iteration 6 Handoff: E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter6\handoff.md
6. Master Asset: output/yu_nian_an/Yu_Nian_An_Master.blend

## Assignment: Forensic Integrity Re-Audit of Milestone 4 Iteration 6
Perform a rigorous forensic integrity audit across all modified code and generated assets:
1. Inspect git diff / changes in:
   - `src/morphomesh/human_grooming.py`
   - `src/morphomesh/character_assembler.py`
   - `src/morphomesh/human_materials.py`
   - `output/yu_nian_an/Yu_Nian_An_Master.blend`
   - `output/yu_nian_an/master_portrait_clean.png`
   - `output/yu_nian_an/master_fullbody_clean.png`
2. Forensic Integrity Verifications:
   - Verify that `Mesh_Lips` is genuinely procedural geometry (50 pure quads, 66 verts) and not a facade mock.
   - Verify that body mesh polygons 377 and 378 are genuinely reset to `slot_skin`, and body topology remains exactly 2,036 pure quads (0 tris, 0 ngons) with 2,144 vertices.
   - Verify that all 52 ARKit FACS shape keys remain functional with non-zero deltas.
   - Verify that bangs ribbon width math in `human_grooming.py` genuinely computes invariant 7.5mm ribbons without cheat metric overrides.
   - Verify that eye spheres have real forward planar UV maps and multi-stop ColorRamp shader nodes.
   - Verify that 73 scalp polygons have real matte `Mat_Human_Scalp` without specular crescent artifacts.
   - Verify zero cheat metrics, zero hardcoded test overrides, zero dummy assertions.
3. Run full regression test suite:
   - `pytest tests/ -v` (confirm 100% genuine pass rate).
4. Deliver your BINARY verdict (CLEAN or INTEGRITY VIOLATION) in `E:\tool\mcp\MorphoMesh\.agents\auditor_human_m4_iter6_1\handoff.md` and message orchestrator_human_1.
