# Dispatch Instructions — Challenger M2-Iter3-2 (Wardrobe Clearance & Anatomy Empirical Challenge)

## Identity
- **Name**: challenger_m2_iter3_2
- **Role**: Wardrobe Clearance & Anatomy Empirical Challenger
- **Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\challenger_m2_iter3_2`
- **Parent Conversation ID**: `78de56ae-5f93-4a99-a306-f90155921566`

## Context
Read `e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-07T13:20:42Z`) and Worker M2 Iteration 3 handoff at `e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync\handoff.md`.

## Tasks
1. Empirically verify wardrobe signed clearance:
   - Check `Mesh_Dress_Bodice` signed distance to `Yu_Nian_An_Body`: minimum signed distance must be positive (>= 5.0 mm), 0 penetrating vertices.
   - Check `Mesh_Dress_PleatedSkirt` and `Mesh_Dress_WaistSash` for 0 penetrating vertices.
2. Run character assembler and wardrobe tests:
   ```powershell
   uv run pytest tests/test_character_assembler.py -v
   ```
3. Run adversarial skinning and anatomy stress tests:
   ```powershell
   uv run pytest tests/test_adversarial_skinning.py tests/test_adversarial_anatomy.py -v
   ```
   Verify 69/69 PASS (0 failed).
4. Record verdict (APPROVE or REJECT) in `handoff.md` and message orchestrator when done.

## 2026-09-07T15:22:56Z
You are Challenger M2-Iter3-2 (Wardrobe Clearance & Anatomy Empirical Challenge).
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\challenger_m2_iter3_2
Your dispatch instructions are at: e:\tool\mcp\MorphoMesh\.agents\challenger_m2_iter3_2\DISPATCH.md
The authoritative user request is at: e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-07T13:20:42Z). Read it before starting work.
Refer also to Worker M2 Iteration 3 report and handoff at: e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync\.

Tasks:
1. Empirically verify wardrobe signed clearance:
   - Check `Mesh_Dress_Bodice` signed distance to `Yu_Nian_An_Body`: minimum signed distance must be positive (>= 5.0 mm), 0 penetrating vertices.
   - Check `Mesh_Dress_PleatedSkirt` and `Mesh_Dress_WaistSash` for 0 penetrating vertices.
2. Run character assembler and wardrobe tests:
   `uv run pytest tests/test_character_assembler.py -v`
3. Run adversarial skinning and anatomy stress tests:
   `uv run pytest tests/test_adversarial_skinning.py tests/test_adversarial_anatomy.py -v`
   Verify 69/69 PASS (0 failed).
4. Record verdict (APPROVE or REJECT) in `handoff.md` and message orchestrator when done.
