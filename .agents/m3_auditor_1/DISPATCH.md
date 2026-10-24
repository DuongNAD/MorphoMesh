# Task Dispatch — M3 Forensic Auditor (Integrity Forensics)

## Objective
Perform an independent, strict Forensic Integrity Audit on Milestone 3:
1. Examine `src/morphomesh/character_assembler.py`, `src/morphomesh/human_rigging.py`, and `src/morphomesh/human_grooming.py`:
   - Verify that 163 DEF bones are genuinely created and aligned to MakeHuman landmark ICRs, not static mock lists.
   - Verify that the 52 ARKit FACS shape keys produce genuine non-zero deformation deltas.
   - Verify that the 10 marionette cords are genuinely computed using catenary physics and snap with 0.000mm error to fingertips.
   - Verify that 10 swallowtail butterflies are genuinely 24 pure quads (48 vertices, 0 triangles) in bilateral vortex spiral flocking with >= 150mm separation.
   - Check for hardcoded test return dictionaries, artificial bypass branches, or dummy facades.
   - Verify that the code does not circumvent the intended task.
2. Issue a binary verdict: `CLEAN` or `INTEGRITY VIOLATION`.

## Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`
- `E:\tool\mcp\MorphoMesh\.agents\m3_worker_assembly_rigging_1\handoff.md`

## Output
Write report to `E:\tool\mcp\MorphoMesh\.agents\m3_auditor_1\handoff.md`
Notify orchestrator via `send_message` when done.

## 2026-09-08T03:04:06Z
You are M3 Forensic Auditor (Integrity Forensics).
Your identity: M3 Forensic Auditor (Integrity Forensics).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\m3_auditor_1
You MUST create your own BRIEFING.md and progress.md in your working directory.

MANDATORY FIRST STEP: Read the authoritative user request at:
E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md

Also read your dispatch instructions at:
E:\tool\mcp\MorphoMesh\.agents\m3_auditor_1\DISPATCH.md
and the master project specification at:
E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md
and M3 Worker's handoff report at:
E:\tool\mcp\MorphoMesh\.agents\m3_worker_assembly_rigging_1\handoff.md

Auditor tasks:
1. Perform an independent, strict Forensic Integrity Audit on src/morphomesh/character_assembler.py, src/morphomesh/human_rigging.py, and src/morphomesh/human_grooming.py:
   - Check that 163 DEF bones are genuinely generated and mapped to MakeHuman landmarks (not static mocks).
   - Check that 52 ARKit FACS shape keys produce genuine non-zero deformation deltas.
   - Check that 10 marionette cords are genuinely computed via catenary curves and snap with 0.000mm error to fingertips.
   - Check that 10 swallowtail butterflies are genuinely 24 pure quads (48 vertices, 0 triangles) in bilateral vortex spiral flocking with >= 150mm separation.
   - Check for hardcoded test return dictionaries, artificial bypass branches, or dummy facades.
   - Check whether code circumvents the intended task.
2. Issue a binary verdict: CLEAN or INTEGRITY VIOLATION.

Produce handoff report at:
E:\tool\mcp\MorphoMesh\.agents\m3_auditor_1\handoff.md
Notify me via send_message when done.

