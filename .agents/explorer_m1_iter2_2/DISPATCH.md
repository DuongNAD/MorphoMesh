# Dispatch Assignment: Explorer M1-Iter2-2 (Face Normal Winding Fix)

**Identity**: teamwork_preview_explorer
**Assigned Task**: Fix Strategy for Counter-Clockwise Normal Winding in `add_box` & `add_cylinder`
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_2`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`
**Project Plan**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
**Gate Failure Report**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m1_2/handoff.md`

## Problem Statement
Challenger M1-2 detected 104 inverted face normals in `generate_bear_base_mesh()` caused by clockwise vertex winding in `add_box()` and `add_cylinder(axis="Y")`.
Cross product $e_1 \times e_2$ points inward towards the interior instead of outward.

## Objectives
1. Inspect `src/morphomesh/inference_adapter.py` lines 140–165 (`add_box`) and lines 190–215 (`add_cylinder`).
2. Formulate the exact vertex winding order for all 6 faces of `add_box` and cylinder side quads so all outward face normals strictly satisfy $fn \cdot n_{\text{geom}} = 1.0 > 0.5$.
3. Check `tests/test_m1_topology_and_facial_stress.py::test_adversarial_inverted_face_normals`.
4. Deliver report to `survey_report.md` and `handoff.md`.

## 2026-09-05T16:10:04Z
You are Explorer M1-Iter2-2.
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_2`.
Read your dispatch at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_2/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`, and Challenger M1-2's report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m1_2/handoff.md`.

Investigate the 104 inverted face normals in `add_box` and `add_cylinder(axis="Y")` in `src/morphomesh/inference_adapter.py`.
Formulate the exact counter-clockwise vertex winding order for all 6 box faces and cylinder side quads so outward geometric normals match outward face directions.
Write your report and handoff.md, then notify orchestrator.

