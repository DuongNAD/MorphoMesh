# DISPATCH INSTRUCTIONS FOR PROJECT ORCHESTRATOR

## Working Directory
`e:\tool\mcp\MorphoMesh\.agents\orchestrator_anatomy_engine_1`

## Project Workspace
`e:\tool\mcp\MorphoMesh`

## Authoritative User Request
Refer to `e:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (section `## 2026-09-07T13:20:42Z`).

## Core Mission
Upgrade the MorphoMesh ecosystem by building the Anatomical Skeletal Estimation & Biomechanical Auto-Rigging Engine for both humans and creatures, and comprehensively resolve all 19 failing tests in the Master Production Deliverables for character Yu Nian An.

### Requirements:
1. **R1: Fix 19 Failing Tests & Complete Master Production Deliverables**:
   - Re-synchronize assembly and export pipeline for binary deliverables in `output/yu_nian_an/`: `Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, `Yu_Nian_An_Master.blend`.
   - Ensure all 163 DEF bones, 52 ARKit FACS morph targets (with valid non-zero delta vectors), standard UV map naming `TEXCOORD_0`, consistent lip/face mesh naming, and marionette string clearance/snapping pass project tests.
   - Tests to pass: `test_adversarial_character_assembler.py`, `test_character_assembler.py`, `test_production_exports.py`, `test_challenger_m5_empirical.py`.

2. **R2: Biomechanical Gait Stance & Bony Landmark Extraction Engine**:
   - Build package `src/morphomesh/anatomy/`.
   - Implement automatic classification of locomotor stance: Humanoid (biped), Plantigrade (sole-walker), Digitigrade (digit-walker), Unguligrade (hoof-walker).
   - Implement automatic surface bony landmark detection and Instantaneous Center of Rotation (ICR) joint pivot estimation.

3. **R3: Biomechanical Bone Roll & Pre-Bend Solver**:
   - Calculate hinge plane normal vector $\vec{n}_{\text{hinge}}$.
   - Automatically pre-bend 1-DOF hinge joints (elbows, knees, animal hocks/stifles).
   - Normalize bone roll axes to completely eliminate candy-wrapper collapse and pole target flipping in Rigify and game engines.

4. **R4: Biharmonic Skinning**:
   - Replace mock skinning and fallback to spine with volumetric geodesic voxel biharmonic diffusion skinning.
   - Prevent weight stealing across axilla-chest and inner thighs.

5. **R5: Integration, Connectors & Automated Verification**:
   - Create unit tests in `tests/test_anatomy.py` covering human and 3 animal stances (Plantigrade, Digitigrade, Unguligrade).
   - Update headless creature rig in `src/morphomesh/blender_bridge.py` and `animals3d_connector.py` to use real anatomical solver rather than junk weights or static mismatched coordinates.
   - Full test suite must pass with 0 failures on `uv run pytest -q` (all 1681+ tests passing).

## Execution Standards
- Maintain `plan.md` and `progress.md` in your working directory.
- Dispatch specialized workers, reviewers, challengers, and auditors as required by team protocols.
- Upon completion, deliver a comprehensive handoff report and notify the sentinel.

## 2026-09-07T13:22:06Z
You are the Project Orchestrator for the Anatomical Skeletal Estimation & Biomechanical Auto-Rigging Engine and Yu Nian An Master Production Deliverables fix.

Summary of your mission:
1. R1: Resolve all 19 failing tests and regenerate/synchronize all Master Production Deliverables in output/yu_nian_an/ (Yu_Nian_An.fbx with 163 DEF bones, Yu_Nian_An.glb with 52 ARKit FACS morph targets and TEXCOORD_0, Yu_Nian_An_Master.blend with 52 shape keys and finger marionette snapping). Pass test_adversarial_character_assembler.py, test_character_assembler.py, test_production_exports.py, test_challenger_m5_empirical.py.
2. R2: Implement module src/morphomesh/anatomy/ for locomotor stance classification (Humanoid biped, Plantigrade, Digitigrade, Unguligrade), surface bony landmark detection, and instantaneous center of rotation (ICR).
3. R3: Biomechanical bone roll solver & pre-bend solver with hinge plane normal vector, 1-DOF joint pre-bend, and bone roll normalization to eliminate candy-wrapper collapse and pole target flipping.
4. R4: Geodesic voxel biharmonic skinning solver to replace mock skinning and prevent weight stealing.
5. R5: Comprehensive tests in tests/test_anatomy.py, connector updates (blender_bridge.py and animals3d_connector.py), and ensure 100% test pass (0 tests failed on `uv run pytest -q`, 1681+ tests passing).
