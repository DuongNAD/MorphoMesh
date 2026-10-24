# Orchestration Plan — Vegetation Library Rebuild

## Objectives
Rebuild the entire 3D botanical asset library using 100% genuine Meshy AI Text-to-3D cloud generation, fully meeting all requirements from `ORIGINAL_REQUEST.md` (## 2026-09-10T11:11:31Z).

## Phases

### Phase 0: Survey & Scope Mapping (Parallel Explorers)
- Explorer 1: Inspect existing project directory (`teamwork_projects/vegetation_library`), files, catalog/manifest, generation scripts, Meshy API client implementation, and `.env` configuration.
- Explorer 2: Inspect existing post-processing, normalization, mesh metrics calculation, headless Blender rendering scripts (`turntable_01.png` - `04.png`, `thumbnail.png`), and `viewer.html` synchronization.
- Explorer 3: Inspect existing automated test suite (`tests/` or `teamwork_projects/vegetation_library/tests/`), verification scripts, geometry/material/invariants checks, and failure points.

### Phase 1: Architectural Decomposition & Project Specification
- Synthesize findings from Explorers into `PROJECT.md` and `TEST_INFRA.md`.
- Formulate feature inventory and discrete milestones.
- Set up E2E test plan (Tiers 1-4) and implementation milestones.

### Phase 2: Execution (Implementation & E2E Testing)
- Execute milestones with strict gate enforcement (Explorer -> Worker -> Reviewers -> Challengers -> Auditor).
- Ensure 100% genuine Meshy cloud generation with zero dummy geometry.
- Enforce visual and topological divergence (<5% vertex count collision).
- Enforce $N_{bones} = 0$, $Z_{min} = 0.000m \pm 0.005m$, 20k-60k polygons, 4-channel PBR.
- Re-render previews and sync manifest and viewer.html.

### Phase 3: Final Verification & Handover
- 100% test pass.
- Forensic audit CLEAN.
- Produce handoff.md and report to Sentinel.
