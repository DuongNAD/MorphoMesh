# DISPATCH FOR WORKER M2 REMEDIATION: Skinning Gap-Preserving Fix

## Working Directory
`e:\tool\mcp\MorphoMesh\.agents\worker_m2_remediation`

## Inputs
- Authoritative User Request: `e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-07T13:20:42Z`)
- Master Plan: `e:\tool\mcp\MorphoMesh\.agents\orchestrator_anatomy_engine_1\plan.md`
- Dead Ends Log: `e:\tool\mcp\MorphoMesh\.agents\orchestrator_anatomy_engine_1\DEAD_ENDS.md`
- Explorer M2 Remediation Report: `e:\tool\mcp\MorphoMesh\.agents\explorer_m2_remediation\report.md`
- Explorer M2 Remediation Handoff: `e:\tool\mcp\MorphoMesh\.agents\explorer_m2_remediation\handoff.md`
- Adversarial Test Suite: `tests/test_adversarial_skinning.py`

## File Ownership
Worker M2 Remediation has exclusive write ownership of:
- `src/morphomesh/anatomy/skinning.py`

Worker M2 Remediation MUST NOT modify other modules or test files.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## CRITICAL CONSTRAINT: PURE NUMPY ONLY
Zero imports of `scipy` allowed. Everything must run in pure NumPy.

## Objectives & Tasks
1. Read the implementation blueprint in Section 2.2 of `e:\tool\mcp\MorphoMesh\.agents\explorer_m2_remediation\report.md`.
2. Apply the remediation to `src/morphomesh/anatomy/skinning.py`:
   - Replace blanket 6-connected dilation with gap-preserving 2D triangle surface rasterization.
   - Implement anatomical candidate validity filtering (contralateral bone isolation across $X=0$, peripheral limb bone isolation from axial chest/torso across air).
   - Replace naive Euclidean fallback with boundary-constrained candidate projection.
3. Run verification tests:
   - `uv run pytest tests/test_adversarial_skinning.py -v` -> MUST PASS 17/17 (0 failed).
   - `uv run pytest tests/test_anatomy.py -v` -> MUST PASS 24/24 (0 failed).
   - `uv run pytest tests/test_adversarial_anatomy.py -v` -> MUST PASS 52/52 (0 failed).
   - `uv run pytest tests/test_adversarial_character_assembler.py tests/test_production_exports.py tests/test_character_assembler.py tests/test_challenger_m5_empirical.py -v` -> MUST PASS 77/77 (0 failed).
4. Author comprehensive report to `e:\tool\mcp\MorphoMesh\.agents\worker_m2_remediation\report.md` and `handoff.md`, and notify orchestrator via send_message.

## 2026-09-07T14:52:00Z
Dispatched by Orchestrator for M2 Remediation (Skinning Gap-Preserving Fix).
- Exclusive ownership: `src/morphomesh/anatomy/skinning.py`.
- Pure NumPy only (no scipy).
- Target: 17/17 adversarial skinning passed, 24/24 anatomy passed, 52/52 adversarial anatomy passed, 77/77 production exports & assembler passed.

