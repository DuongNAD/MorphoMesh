# Dispatch Assignment: Worker M5-2 (Milestone 5 Iteration 2 Remediation)

## Mission & Role
You are Worker M5-2 for Milestone 5 Iteration 2 Remediation.
Your working directory is `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m5_2`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations and documentation edits must be genuine, accurate, and runnable. A Forensic Auditor will independently verify your work.

## Tasks: Exact Fixes Requested by Reviewer M5-1
Inspect Reviewer M5-1's handoff report at `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_reviewer_m5_1\handoff.md` and implement the 6 required action items:

1. **Fix Recipe 3 and Recipe 4 in `docs/DEVELOPER_GUIDE.md`**:
   - `generate_arachnid_leg` (around line 469) and `generate_flowing_cape` (around line 523) currently instantiate `MeshGeometry(vertices=..., faces=...)`, raising `TypeError` because `MeshGeometry.__init__()` takes no arguments.
   - Fix: Instantiate `mesh = MeshGeometry()`, then populate vertices via `mesh.add_vertex()` (or assign `mesh.vertices = ...`) and quad faces via `mesh.add_quad()` (or assign `mesh.faces = ...`). Ensure both functions are syntactically and semantically runnable.

2. **Fix Recipe 5 in `docs/DEVELOPER_GUIDE.md`**:
   - At line 563, Recipe 5 references `DefectCategory.TOPOLOGY_DEFORMATION`, which does not exist in `DefectCategory`.
   - Fix: Replace with `DefectCategory.SKINNING_PINCH` or `DefectCategory.PENETRATION` (members of `morphomesh.models.critique.DefectCategory`).

3. **Fix Recipe 2 in `docs/DEVELOPER_GUIDE.md`**:
   - At line 339, Recipe 2 imports `requests`, which is not in `pyproject.toml` dependencies.
   - Fix: Replace with standard library: `import urllib.request, urllib.error, json`.

4. **Fix Schema Names in `docs/MCP_SPECIFICATION.md`**:
   - In Section 4.6 (lines 307 and 311), change `GetSceneStatusInput` to `SceneStatusInput` and `GetSceneStatusOutput` to `SceneStatusOutput` (matching `src/morphomesh/models/creature.py` and `src/morphomesh/tools/creature.py`).

5. **Fix Typo in `docs/MCP_SPECIFICATION.md`**:
   - At line 415, change `CIRUCT_BREAKER_OPEN` to `CIRCUIT_BREAKER_OPEN`.

6. **Register Pytest Markers in `pyproject.toml`**:
   - In `pyproject.toml` lines 54-56, under `markers`, add `unit`, `integration`, and `adversarial` alongside `live_blender`.

## Verification Commands to Execute
Run:
```bash
# 1. Test Recipe 3 & 4 instantiation:
uv run python -c "from morphomesh.geometry.mesh import MeshGeometry; m = MeshGeometry(); m.add_vertex((0,0,0)); m.add_vertex((1,0,0)); m.add_vertex((1,1,0)); m.add_vertex((0,1,0)); m.add_quad(0,1,2,3); print('Vertices:', len(m.vertices), 'Faces:', len(m.faces))"

# 2. Test Recipe 5 DefectCategory:
uv run python -c "from morphomesh.models.critique import DefectCategory; print([m.name for m in DefectCategory])"

# 3. Test SceneStatus schemas import:
uv run python -c "from morphomesh.models import SceneStatusInput, SceneStatusOutput; print(SceneStatusInput, SceneStatusOutput)"

# 4. Test pytest markers without warnings:
uv run pytest --markers

# 5. Re-run package build:
uv run python -m build --sdist --wheel
```

## Output Requirements
Document all edits and verification outputs in `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m5_2\handoff.md`.
Send a message to the orchestrator when finished.

## 2026-09-09T08:51:19Z
You are Worker M5-2 for Milestone 5 Iteration 2 Remediation.
Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m5_2.
Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m5_2\DISPATCH.md, PROJECT.md at E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md, and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md.
Also inspect Reviewer M5-1's handoff report at E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_reviewer_m5_1\handoff.md.

Task:
Implement the 6 remediation items:
1. Fix Recipes 3 & 4 in docs/DEVELOPER_GUIDE.md: update generate_arachnid_leg and generate_flowing_cape to instantiate mesh = MeshGeometry(), then add vertices and quads via mesh.add_vertex() / mesh.add_quad().
2. Fix Recipe 5 in docs/DEVELOPER_GUIDE.md: replace DefectCategory.TOPOLOGY_DEFORMATION with DefectCategory.SKINNING_PINCH or DefectCategory.PENETRATION.
3. Fix Recipe 2 in docs/DEVELOPER_GUIDE.md: replace import requests with standard library import urllib.request, urllib.error, json.
4. Fix schema names in docs/MCP_SPECIFICATION.md: change GetSceneStatusInput / GetSceneStatusOutput to SceneStatusInput / SceneStatusOutput.
5. Fix typo in docs/MCP_SPECIFICATION.md: change CIRUCT_BREAKER_OPEN to CIRCUIT_BREAKER_OPEN.
6. In pyproject.toml: add unit, integration, and adversarial markers alongside live_blender.

Run verification commands and rebuild package: uv run python -m build --sdist --wheel.
MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations and docs must be genuine.

Record full handoff report in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m5_2\handoff.md and send a message to orchestrator when finished.
