# Dispatch Instructions — Worker M2 Iteration 3 (Master Production Deliverables & Test Sync)

## Identity
- **Name**: worker_m2_deliverables_sync
- **Role**: Yu Nian An Master Deliverables & Production Exports Sync
- **Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync`
- **Parent Conversation ID**: `78de56ae-5f93-4a99-a306-f90155921566`

## Context
The core pure-NumPy anatomical engine in `src/morphomesh/anatomy/` (`stance.py`, `landmarks.py`, `bone_roll.py`, `skinning.py`) is 100% complete and certified CLEAN by Forensic Auditor M2-R2. All 93 anatomy tests pass (`test_anatomy.py`, `test_adversarial_anatomy.py`, `test_adversarial_skinning.py`).

However, during testing, running prototype scripts (`scripts/test_beauty_recreation.py`) overwrote `output/yu_nian_an/` with prototype data (`Beauty_Armature`, `Beauty_Body`, etc.), corrupting:
1. `output/yu_nian_an/Yu_Nian_An_Master.blend` (contains `Beauty_Armature` instead of `Armature_Yu_Nian_An_Rigify` with 163 DEF bones and 52 shape keys)
2. `output/yu_nian_an/Yu_Nian_An.glb` (has 0 morph targets instead of 52, missing `TEXCOORD_0` on 16 primitives, only 20 scene nodes)
3. `output/yu_nian_an/Yu_Nian_An.fbx` (missing DEF bones, size 1.79 MB instead of > 5 MB)

This caused 17 test failures across the production export test suites.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You have exclusive write ownership of:
- `scripts/test_beauty_recreation.py`
- `src/morphomesh/character_assembler.py`
- `output/yu_nian_an/` (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`)

DO NOT modify `src/morphomesh/anatomy/` as it is already verified and frozen.

## Tasks
1. In `scripts/test_beauty_recreation.py`:
   - Permanently redirect all outputs away from `output/yu_nian_an/` to `output/beauty_test/` so running beauty tests never overwrites master production files.
2. In `src/morphomesh/character_assembler.py`:
   - Inspect `assemble_and_export()` and ensure it creates:
     * Collection `Yu_Nian_An_Master` with all required objects (`Armature_Yu_Nian_An_Rigify` with 163 DEF bones, `Yu_Nian_An_Body` with 52 ARKit shape keys, `Mesh_Lips`, `Prop_Marionette_Strings`, etc.).
     * FBX export with 163 DEF bones, binary format, file size > 5 MB.
     * glTF export with 52 ARKit FACS morph targets in `extras.targetNames`, `TEXCOORD_0` on all primitives, and >= 190 scene nodes.
3. Run the canonical production character assembler in headless Blender:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python-expr "from morphomesh.character_assembler import CharacterAssembler; ca = CharacterAssembler(); print(ca.assemble_and_export())"
   ```
4. Verify tests:
   ```powershell
   uv run pytest tests/test_adversarial_character_assembler.py tests/test_production_exports.py tests/test_character_assembler.py tests/test_challenger_m5_empirical.py -v
   ```
   Must achieve **77 / 77 PASSED (0 failed)**.
5. Verify anatomy tests:
   ```powershell
   uv run pytest tests/test_anatomy.py tests/test_adversarial_anatomy.py tests/test_adversarial_skinning.py -v
   ```
   Must achieve **93 / 93 PASSED (0 failed)**.
6. Verify repository-wide test health:
   ```powershell
   uv run pytest -q
   ```
7. Author report to `report.md` and `handoff.md`, and notify orchestrator via `send_message`.

## 2026-09-07T15:08:10Z
<USER_REQUEST>
You are Worker M2 Iteration 3 (Master Production Deliverables & Test Sync).
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync
Your dispatch instructions are at: e:\tool\mcp\MorphoMesh\.agents\worker_m2_deliverables_sync\DISPATCH.md
The authoritative user request is at: e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md (under header ## 2026-09-07T13:20:42Z). Read it before starting work.
Refer also to Reviewer M2-R2-2 handoff at: e:\tool\mcp\MorphoMesh\.agents\reviewer_m2_r2_2\handoff.md and Challenger M2-R2-2 handoff at: e:\tool\mcp\MorphoMesh\.agents\challenger_m2_r2_2\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You have exclusive write ownership of:
- `scripts/test_beauty_recreation.py`
- `src/morphomesh/character_assembler.py`
- `output/yu_nian_an/` (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`)
DO NOT modify `src/morphomesh/anatomy/` as it is already verified and frozen.

Tasks:
1. In `scripts/test_beauty_recreation.py`, permanently redirect all outputs away from `output/yu_nian_an/` to `output/beauty_test/` so running beauty recreation never overwrites master production files.
2. In `src/morphomesh/character_assembler.py`, ensure `assemble_and_export()` properly creates `Yu_Nian_An_Master` collection, `Armature_Yu_Nian_An_Rigify` with 163 DEF bones, 52 shape keys on body, exports FBX (> 5 MB binary with 163 DEF bones), and exports GLB (with 52 ARKit FACS targets in extras.targetNames, TEXCOORD_0 on all primitives, >= 190 nodes).
3. Run the canonical production character assembler in headless Blender:
   `& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python-expr "from morphomesh.character_assembler import CharacterAssembler; ca = CharacterAssembler(); print(ca.assemble_and_export())"`
4. Verify tests:
   `uv run pytest tests/test_adversarial_character_assembler.py tests/test_production_exports.py tests/test_character_assembler.py tests/test_challenger_m5_empirical.py -v`
   All 77 tests must PASS (0 failed).
5. Verify anatomy tests:
   `uv run pytest tests/test_anatomy.py tests/test_adversarial_anatomy.py tests/test_adversarial_skinning.py -v`
   All 93 tests must PASS (0 failed).
6. Verify full test suite:
   `uv run pytest -q`
7. Author your report to `report.md` and `handoff.md`, and notify orchestrator via send_message when done.
</USER_REQUEST>
