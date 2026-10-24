# Task Assignment: Worker M3-1 (Implementation - Milestone 3)

## Context
Milestone 3: Digital Human, Rigging, Wardrobe & Grooming Subsystems Modularization.

## Mission & Implementation Steps
Decompose the 4 monolithic human pipeline files (>50KB) into modular sub-packages with single responsibilities while preserving 100% backward compatibility via facades:

### 1. `human/` Sub-Package (`src/morphomesh/human/`):
Decompose `src/morphomesh/human_generator.py` (73.6 KB, 1,695 lines):
- `mold_loader.py`: MakeHuman CC0 base mold OBJ parser, vertex groups parser (32 vertex groups).
- `morphology.py`: Parametric morphing functions, breast volume, teardrop profile, gluteal curve, anthropometric scale math.
- `anatomy.py`: `HumanAnatomyGenerator` class.
- `scripts.py`: In-Blender Python script template generator (`get_human_generation_script()`).
- `__init__.py`: Package re-exports with exhaustive `__all__`.
- Refactor `src/morphomesh/human_generator.py` into a facade re-exporting all symbols via `__all__`.

### 2. `rigging/` Sub-Package (`src/morphomesh/rigging/`):
Decompose `src/morphomesh/human_rigging.py` (82.5 KB, 1,835 lines):
- `metarig.py`: 163 DEF bones metarig generator (`generate_rigify_human_metarig`), bone roll math, biological joint pivots.
- `anti_pinch.py`: Anti-pinch skin weights calculation, volume preservation heuristics (`calculate_anti_pinch_weights`).
- `blendshapes.py`: 52 ARKit FACS morph targets delta calculator (`generate_arkit_52_blendshapes`).
- `scripts.py`: In-Blender script template generator (`get_rigging_script()`).
- `__init__.py`: Package re-exports with exhaustive `__all__`.
- Refactor `src/morphomesh/human_rigging.py` into a facade re-exporting all symbols via `__all__`.

### 3. `wardrobe/` Sub-Package (`src/morphomesh/wardrobe/`):
Decompose `src/morphomesh/wardrobe.py` (88.0 KB, 2,182 lines):
- `garments.py`: Sundress procedural mesh generation (`generate_dress_bodice`, `generate_dress_waist_sash`, `generate_dress_skirt`, `generate_flat_strappy_sandals`).
- `props.py`: Catenary marionette strings (`generate_marionette_strings`) and glowing butterflies (`generate_glowing_butterflies`).
- `skinning.py`: Garment skin weights transfer and biharmonic proxy weighting.
- `scripts.py`: Wardrobe script template generator (`get_wardrobe_script()`).
- `__init__.py`: Package re-exports with exhaustive `__all__`.
- Refactor `src/morphomesh/wardrobe.py` into a facade re-exporting all symbols via `__all__`.

### 4. `grooming/` Sub-Package (`src/morphomesh/grooming/`):
Decompose `src/morphomesh/human_grooming.py` (50.8 KB, 1,188 lines):
- `hime_cut.py`: 6-stratum hime cut spline curves generator (`generate_hime_cut_splines`).
- `ribbons.py`: Hair ribbon mesh extrusion and UV coordinate generation.
- `curves_pipeline.py`: Geometry Nodes hair curve modifier tree builder (`build_hair_geom_node_tree`).
- `scripts.py`: Hair grooming script template generator (`get_grooming_script()`).
- `__init__.py`: Package re-exports with exhaustive `__all__`.
- Refactor `src/morphomesh/human_grooming.py` into a facade re-exporting all symbols via `__all__`.

### 5. Verification Commands:
- Run tests:
  `uv run pytest tests/test_human_generator.py tests/test_human_rigging.py tests/test_wardrobe_m2.py tests/test_wardrobe_m3.py tests/test_e2e_human_anatomy.py tests/test_adversarial_human_m3.py tests/test_adversarial_rigging.py tests/test_adversarial_skinning.py -v`
- Verify imports:
  `uv run python -c "import morphomesh.human, morphomesh.rigging, morphomesh.wardrobe, morphomesh.grooming; from morphomesh import human_generator, human_rigging, wardrobe, human_grooming; print('M3 Imports verified successfully!')"`
- Verify 0 circular dependencies.

## Write Ownership
You own:
- `src/morphomesh/human/` (all files)
- `src/morphomesh/human_generator.py` (facade)
- `src/morphomesh/rigging/` (all files)
- `src/morphomesh/human_rigging.py` (facade)
- `src/morphomesh/wardrobe/` (all files)
- `src/morphomesh/wardrobe.py` (facade)
- `src/morphomesh/grooming/` (all files)
- `src/morphomesh/human_grooming.py` (facade)

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverables
Write report to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m3_1\handoff.md`.
Send message to orchestrator upon completion.

## 2026-09-09T05:57:52Z
You are Worker M3-1 for Milestone 3: Digital Human, Rigging, Wardrobe & Grooming Subsystems Modularization. Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m3_1. Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m3_1\DISPATCH.md, PROJECT.md at E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md, and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md. Decompose src/morphomesh/human_generator.py into src/morphomesh/human/, src/morphomesh/human_rigging.py into src/morphomesh/rigging/, src/morphomesh/wardrobe.py into src/morphomesh/wardrobe/, and src/morphomesh/human_grooming.py into src/morphomesh/grooming/. Refactor all 4 root files into 100% backward-compatible facades with exact symbol parity via __all__. Run pytest test suites and ensure zero circular dependencies. MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected. Send a message to orchestrator when finished.
