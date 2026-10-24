# Task Assignment: Explorer M1-2 (Geometry & Inference Subsystems Decomposition Plan)

## Context
Milestone 1: Models, Geometry & Inference Subsystems Modularization.

## Mission
Analyze `src/morphomesh/inference_adapter.py` (96.7 KB, 2,357 lines) and design target sub-packages:
1. Extract `MeshGeometry` (1,108 lines), glTF 2.0 binary and OBJ exporters, and quad mesh helpers into `src/morphomesh/geometry/`:
   - `src/morphomesh/geometry/mesh.py`
   - `src/morphomesh/geometry/exporters.py`
   - `src/morphomesh/geometry/primitives.py`
   - `src/morphomesh/geometry/__init__.py`
2. Modularize inference adapters into `src/morphomesh/inference/`:
   - `src/morphomesh/inference/base.py`
   - `src/morphomesh/inference/mock.py`
   - `src/morphomesh/inference/replicate.py`
   - `src/morphomesh/inference/huggingface.py`
   - `src/morphomesh/inference/factory.py`
   - `src/morphomesh/inference/__init__.py`
3. Design `src/morphomesh/inference_adapter.py` as a facade module re-exporting `MeshGeometry`, all adapter classes, and `get_inference_adapter` via `__all__`.
4. Ensure all 22 test files importing from `inference_adapter` continue to work without any modifications.

## Input Files
- `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (read section `## 2026-09-09T04:28:41Z`)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md`
- `src/morphomesh/inference_adapter.py`

## Output Deliverables
Write implementation blueprint to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2\analysis.md` and handoff report to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2\handoff.md`.

## 2026-09-09T04:38:21Z

You are Explorer M1-2 for Milestone 1: Geometry & Inference Subsystems. Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2. Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2\DISPATCH.md, PROJECT.md at E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md, and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md. Plan the extraction of MeshGeometry into src/morphomesh/geometry/ and adapter modularization into src/morphomesh/inference/, maintaining facade src/morphomesh/inference_adapter.py. Write your report to E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2\analysis.md and E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2\handoff.md. Send a message to orchestrator when finished.
