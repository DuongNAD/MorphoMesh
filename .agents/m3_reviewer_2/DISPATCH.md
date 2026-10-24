# Task Dispatch — M3 Reviewer 2 (Rigging & Skinning Review)

## Objective
Perform an independent, objective review and verification of Milestone 3:
1. Examine `src/morphomesh/human_rigging.py`:
   - Verify alignment of all 163 DEF bones (64 body + 99 facial) to MakeHuman 125 landmarks.
   - Verify 5-digit finger partitioning (thumb: 34, index: 308, middle: 312, ring: 318, pinky: 344).
   - Verify biological pre-bends (+Y elbow >= 15mm, -Y knee <= -18mm) and closed-form bone rolls.
   - Verify geodesic biharmonic skinning weights summing strictly to 1.0.
   - Verify 52 ARKit FACS shape keys with active deformation.
2. Run test verification:
   - `uv run pytest tests/test_human_rigging.py tests/test_adversarial_rigging.py tests/test_adversarial_skinning.py -v`
3. Document exact test outputs and issue a binary verdict: `APPROVE` or `REQUEST_CHANGES`.

## Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`
- `E:\tool\mcp\MorphoMesh\.agents\m3_worker_assembly_rigging_1\handoff.md`

## Output
Write report to `E:\tool\mcp\MorphoMesh\.agents\m3_reviewer_2\handoff.md`
Notify orchestrator via `send_message` when done.

## 2026-09-07T20:04:06Z
You are M3 Reviewer 2 (Rigging & Skinning Review).
Your identity: M3 Reviewer 2 (Rigging & Skinning Review).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\m3_reviewer_2
You MUST create your own BRIEFING.md and progress.md in your working directory.

MANDATORY FIRST STEP: Read the authoritative user request at:
E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md

Also read your dispatch instructions at:
E:\tool\mcp\MorphoMesh\.agents\m3_reviewer_2\DISPATCH.md
and the master project specification at:
E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md
and M3 Worker's handoff report at:
E:\tool\mcp\MorphoMesh\.agents\m3_worker_assembly_rigging_1\handoff.md

Review tasks:
1. Examine src/morphomesh/human_rigging.py: verify alignment of all 163 DEF bones to MakeHuman 125 landmarks, 5-digit finger partitioning, +Y elbow / -Y knee pre-bends, closed-form bone rolls, biharmonic skinning weights summing strictly to 1.0, and 52 active ARKit FACS shape keys.
2. Run test verification:
   `uv run pytest tests/test_human_rigging.py tests/test_adversarial_rigging.py tests/test_adversarial_skinning.py -v`
3. Document exact test outputs and issue a binary verdict: APPROVE or REQUEST_CHANGES.

Produce handoff report at:
E:\tool\mcp\MorphoMesh\.agents\m3_reviewer_2\handoff.md
Notify me via send_message when done.
