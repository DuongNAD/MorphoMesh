# Master Execution Plan: Anatomical Skeletal Estimation & Biomechanical Auto-Rigging Engine & Yu Nian An Production Fix

## Architecture & Project Scope
- Workspace: `e:\tool\mcp\MorphoMesh`
- Target Package: `src/morphomesh/anatomy/`
- Production Deliverables: `output/yu_nian_an/` (`Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, `Yu_Nian_An_Master.blend`)
- Connectors & Bridges: `src/morphomesh/blender_bridge.py`, `src/morphomesh/connectors/animals3d_connector.py`
- Target Test Pass: 1681+ tests passing, 0 failures via `uv run pytest -q`

## Milestones Overview

| Milestone | Scope Description | Dependencies | Status |
|-----------|-------------------|--------------|--------|
| **Survey** | Parallel exploration of 19 failing tests, Yu Nian An export pipeline, anatomy math/architecture, and connector requirements | None | DONE |
| **M1: Production Deliverables Fix** | Fix character assembler, export manager, FBX 163 DEF bones, GLB 52 ARKit FACS targets + TEXCOORD_0, marionette finger snapping, pass all 19 failing tests | Survey | DONE |
| **M2: Anatomical Engine & Connectors** | Implement `src/morphomesh/anatomy/` (`__init__.py`, `stance.py`, `landmarks.py`, `bone_roll.py`, `skinning.py`), update `blender_bridge.py` & `animals3d_connector.py`, implement `tests/test_anatomy.py`, achieve 100% test pass (1700+ passing, 0 failed) | M1 | IN_PROGRESS |

## Gate Protocol & Quality Standards
- Direct iteration loop: Explorers -> Worker -> 2 Reviewers -> 2 Challengers -> 1 Auditor -> Gate.
- Binary veto on Auditor integrity violations (no mocks, no hardcoded cheating, no fake results).
- Strict pass criteria: Clean audit, 100% test pass, APPROVE from all reviewers and challengers.
