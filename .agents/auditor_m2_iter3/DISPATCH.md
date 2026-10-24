# Dispatch Instructions — Forensic Auditor M2 Iteration 3 (Integrity Verification)

## Identity
- **Name**: auditor_m2_iter3
- **Role**: Forensic Auditor
- **Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\auditor_m2_iter3`
- **Parent Conversation ID**: `78de56ae-5f93-4a99-a306-f90155921566`

## Context
Read `e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-07T13:20:42Z`) and Worker M2 Iteration 3 handoff at `e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync\handoff.md`.

## Tasks
1. Perform forensic integrity audit on all changes made by Worker M2 Iteration 3:
   - Check git diff on `scripts/test_beauty_recreation.py` and `src/morphomesh/character_assembler.py`.
   - Verify `src/morphomesh/anatomy/` was not modified (clean git diff / frozen).
   - Check for cheating/circumvention: zero hardcoded test coordinates, zero mock facades, genuine BVH signed distance computation.
2. Inspect production binary assets in `output/yu_nian_an/`:
   - `Yu_Nian_An_Master.blend` (file size > 5 MB)
   - `Yu_Nian_An.fbx` (file size > 5 MB)
   - `Yu_Nian_An.glb` (file size > 2 MB)
3. Run independent tests:
   ```powershell
   uv run pytest tests/test_production_exports.py tests/test_character_assembler.py -v
   uv run pytest tests/test_adversarial_skinning.py -v
   ```
4. Record verdict (CLEAN or INTEGRITY VIOLATION) in `handoff.md` and message orchestrator when done.
