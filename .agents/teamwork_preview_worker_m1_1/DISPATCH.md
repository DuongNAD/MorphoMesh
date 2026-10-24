# Task Assignment: Worker M1-1 (Implementation - Milestone 1)

## Context
Milestone 1: Models, Geometry & Inference Subsystems Modularization & Test Anatomy Bugfix.

## Mission & Implementation Steps
Execute the modularization blueprints established by Explorers M1-1, M1-2, and M1-3:

1. **Models Subsystem Modularization**:
   - Create package `src/morphomesh/models/`:
     * `errors.py`: All 32 error constants and `MorphoMeshException`.
     * `enums.py`: All 17 enums, `TargetPreset`, `VALID_INSPECTOR_VIEWPOINTS_SET`.
     * `base.py`: `BoundingBox`, `SceneObjectInfo`, `BoundingBox3D`.
     * `creature.py`: Tools 1-7 schemas (`GenerateConceptInput/Output`, `Create3DAssetInput/Output`, `OptimizeTopologyInput/Output`, `AutoRigInput/Output`, `BlenderExecuteInput/Output`, `SceneStatusInput/Output`, `RenderPreviewInput/Output`).
     * `human.py`: Tools 8-12 schemas (`HumanAnatomyConfig`, `CreateHumanAssetInput/Output`, `AutoRigHumanInput/Output`, `SetupHumanMaterialsInput/Output`, `GroomHumanInput/Output`, `DressHumanInput/Output`, `AssembleMasterCharacterInput/Output`, `ExportProductionCharacterInput/Output` and aliases).
     * `inspection.py`: Tools 13-14 schemas (`SetupInspectorCameraRigInput/Output`, `CaptureViewportInput/Output`, `MultiAngleCaptureFrame`).
     * `critique.py`: Tool 15 schemas (`ActionableRecommendation`, `DefectItem`, `VisualCritiqueInput`, `VisualCritiqueOutput`).
     * `animation.py`: Tools 16-17 schemas (`AnimateAssetInput/Output`, `ListAnimationsInput/Output`).
     * `__init__.py`: Clean re-exports of all 101 symbols in `__all__`.
   - Refactor `src/morphomesh/models.py` into a clean facade re-exporting all symbols from `morphomesh.models` via `__all__`.

2. **Geometry Subsystem Extraction**:
   - Create package `src/morphomesh/geometry/`:
     * `quad_utils.py`: Quad metrics and capping helpers (`compute_quad_metrics`, `add_quad_cap`, `add_quad_ellipsoid`).
     * `primitives.py`: `GeometryPrimitivesMixin` with primitive shapes and procedural anatomy generators.
     * `exporters.py`: Binary glTF 2.0 (`.glb`) and Wavefront OBJ serialization functions.
     * `mesh.py`: Core `MeshGeometry` class inheriting from `GeometryPrimitivesMixin`.
     * `__init__.py`: Clean re-exports of `MeshGeometry`, exporters, and quad utilities.

3. **Inference Subsystem Modularization**:
   - Create package `src/morphomesh/inference/`:
     * `base.py`: `BaseInferenceAdapter`, `EnhancedCreate3DAssetOutput`, `CircuitBreaker`.
     * `mock.py`: `MockInferenceAdapter` and `InferenceAdapter` alias.
     * `replicate.py`: `ReplicateInferenceAdapter`.
     * `huggingface.py`: `HuggingFaceInferenceAdapter`.
     * `factory.py`: `get_inference_adapter(mode, **kwargs)`.
     * `__init__.py`: Clean re-exports.
   - Refactor `src/morphomesh/inference_adapter.py` into a clean facade re-exporting all symbols from `morphomesh.inference` and `morphomesh.geometry.mesh` via `__all__`.

4. **Apply Surgical Fix to `src/morphomesh/blender_bridge.py:693`**:
   - Ensure the template line includes `# front_thigh.L, front_thigh.R` per `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_3\proposed_blender_bridge_fix.patch`.

5. **Run Verification Commands**:
   - `uv run pytest tests/test_models.py tests/test_inference_adapter.py tests/test_anatomy.py tests/test_connectors.py -v`
   - `uv run python -c "import morphomesh.models; import morphomesh.inference_adapter; import morphomesh.geometry; import morphomesh.inference; print('Imports verified successfully!')"`
   - Verify 0 circular imports and 0 regressions on all touched suites.

## Write Ownership
You own:
- `src/morphomesh/models/` (all files)
- `src/morphomesh/models.py`
- `src/morphomesh/geometry/` (all files)
- `src/morphomesh/inference/` (all files)
- `src/morphomesh/inference_adapter.py`
- `src/morphomesh/blender_bridge.py` (line 693 fix only)

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Input Reference Files
- `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md`
- `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_1\analysis.md`
- `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2\analysis.md`
- `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_3\analysis.md`
- `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_3\proposed_blender_bridge_fix.patch`

## Output Deliverables
Write progress and completion reports to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m1_1\progress.md` and `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m1_1\handoff.md`.
Send a message to orchestrator upon completion.

## 2026-09-09T04:45:02Z
You are Worker M1-1 for Milestone 1: Models, Geometry & Inference Subsystems Modularization. Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m1_1. Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m1_1\DISPATCH.md, PROJECT.md at E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md, and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md. Read the blueprints prepared by Explorers M1-1, M1-2, and M1-3 at E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_1\analysis.md, E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_2\analysis.md, E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_3\analysis.md, and the patch at E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_m1_3\proposed_blender_bridge_fix.patch. Implement the modular sub-packages src/morphomesh/models/, src/morphomesh/geometry/, src/morphomesh/inference/, refactor models.py and inference_adapter.py into facades, apply the line 693 fix to blender_bridge.py, run tests, and report in handoff.md. MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected. Send a message to orchestrator when finished.
