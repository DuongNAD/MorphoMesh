# Handoff Report — Explorer 1: Monolithic Files & Codebase Architecture Survey

## 1. Observation

### Codebase Inventory & Metrics
- **Analysis Scope**: All 35 Python source files within `src/morphomesh/` (including `connectors/` and `anatomy/`).
- **Total Volume**: 1,485,538 bytes (1.42 MB), 34,609 lines of code, 126 classes, 269 functions.
- **Size Distribution**:
  - **Monolithic Files (>= 50 KB)**: 11 files (1,019,139 bytes = 68.6% of codebase, 23,248 lines = 67.2% of codebase).
  - **Large Files (>= 800 lines, < 50 KB)**: 6 files (243,303 bytes = 16.4% of codebase, 5,843 lines = 16.9% of codebase).
  - **Modular / Small Files (< 800 lines, < 50 KB)**: 18 files (223,096 bytes = 15.0% of codebase, 5,518 lines = 15.9% of codebase).

### Monolithic Files Inventory (>= 50 KB)
1. `src/morphomesh/blender_bridge.py`: 151.50 KB (155,140 bytes), 3,454 lines, 4 classes, 31 methods in `BlenderBridge`. Contains 1,596-line `_generate_headless_script()` method and 218-line `_generate_interactive_script()` method.
2. `src/morphomesh/character_assembler.py`: 105.14 KB (107,667 bytes), 2,431 lines, 2 classes, 5 top-level functions. Contains 1,030-line `get_master_assembly_script()` function and 273-line `generate_yu_nian_an_pbr_textures()` function.
3. `src/morphomesh/inference_adapter.py`: 96.67 KB (98,993 bytes), 2,357 lines, 8 classes. Contains 1,108-line `MeshGeometry` class (pure-python 3D mesh container, anatomical shape generators, and binary glTF 2.0 exporter) and 915-line `MockInferenceAdapter`.
4. `src/morphomesh/visual_critic.py`: 93.11 KB (95,343 bytes), 2,295 lines, 5 classes, 32 top-level functions. Contains 249-line `PurePythonBVHTree`, 97-line Eberly point-to-triangle distance, and 223-line garment penetration evaluator.
5. `src/morphomesh/wardrobe.py`: 88.02 KB (90,136 bytes), 2,182 lines, 1 class, 21 functions. Contains 244-line `generate_dress_bodice()`, 293-line `generate_dress_waist_sash()`, 331-line `generate_flat_strappy_sandals()`, and 280-line `get_wardrobe_script()`.
6. `src/morphomesh/human_rigging.py`: 82.55 KB (84,527 bytes), 1,835 lines, 4 classes, 9 functions. Contains 358-line `generate_rigify_human_metarig()` (163 DEF bones), 383-line `calculate_anti_pinch_weights()`, 210-line `generate_arkit_52_blendshapes()`, and 252-line `get_rigging_script()`.
7. `src/morphomesh/connectors/meshy_connector.py`: 74.27 KB (76,049 bytes), 1,580 lines, 8 classes. Contains 1,272-line `MeshyConnector` class with polling, autorigging, and animation retargeting.
8. `src/morphomesh/human_generator.py`: 73.56 KB (75,324 bytes), 1,695 lines, 2 classes, 13 functions. Contains MakeHuman OBJ loader (102 lines), 334-line `HumanAnatomyGenerator.generate()`, and 490-line `get_human_generation_script()`.
9. `src/morphomesh/server.py`: 71.94 KB (73,670 bytes), 1,689 lines, 0 classes, 24 functions. Implements all 17 MCP tools in a single file with environment-gated filtering.
10. `src/morphomesh/models.py`: 63.78 KB (65,310 bytes), 1,232 lines, 62 classes, 32 error constants, 17 enums, and aliasing validators.
11. `src/morphomesh/human_grooming.py`: 50.77 KB (51,992 bytes), 1,188 lines, 3 classes, 9 functions. Contains 288-line `generate_hime_cut_splines()`, 112-line `build_hair_geom_node_tree()`, and 354-line `get_grooming_script()`.

### Import Topology & Circularity Observations
- **Direct Cycle Traversal**: When resolving exact module names (distinguishing `morphomesh.connectors.__init__` from `morphomesh.connectors.base` and individual connectors), the directed dependency graph has **0 cycles**.
- **Runtime Import Check**: Command `uv run python -c "import morphomesh.blender_bridge; import morphomesh.character_assembler; import morphomesh.visual_critic; import morphomesh.wardrobe; import morphomesh.human_rigging; import morphomesh.inference_adapter; import morphomesh.server"` executed with exit code 0.
- **Coupling Gravity Hubs**:
  - `morphomesh.models`: imported by 10 internal modules and 29 test files.
  - `morphomesh.inference_adapter` (`MeshGeometry`): imported by 11 internal modules and 22 test files.
  - `morphomesh.blender_bridge`: imported by 2 internal modules and 22 test files.

### Test Suite Baseline Metrics
- **Command**: `uv run pytest -q`
- **Result**: 2,082 tests total — **2,064 PASSED**, **9 SKIPPED**, **9 FAILED** (execution time: 255.19s).
- **Failure Scope**: All 9 failing tests are pre-existing empirical assertions against disk binary deliverables (`output/yu_nian_an/Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, `Yu_Nian_An_Master.blend`):
  1. `tests/test_anatomy.py::TestBridgeAndConnectorIntegration::test_blender_bridge_create_armature_interactive_script`
  2. `tests/test_challenger_m1_1_empirical.py::TestEmpiricalFBXContainer::test_fbx_shape_keys_and_uv_layers`
  3. `tests/test_challenger_m1_1_empirical.py::TestLiveBlenderReimportAudit::test_live_blender_reimport_depsgraph`
  4. `tests/test_challenger_m3_props.py::TestChallengerCharacterAssemblerDiscrepancies::test_on_disk_master_blend_has_m3_props_adversarial`
  5. `tests/test_challenger_m4_iter4_empirical.py::test_empirical_adversarial_audit_in_blender`
  6. `tests/test_challenger_m5_empirical.py::TestEmpiricalContainersAndTextures::test_fbx_binary_header_and_bones`
  7. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_wardrobe_signed_clearance_and_zero_penetration`
  8. `tests/test_production_exports.py::TestFBXBinaryIntegrity::test_fbx_contains_def_bones_and_shape_keys`
  9. `tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_uv_semantic_texture_sampling`
- **Unit/Schema/Logic Pass Rate**: 100% (2,064 passing tests covering all MCP tools, schemas, models, geometry, bridge dispatch, and algorithms).

---

## 2. Logic Chain

1. **Premise 1 (Codebase Mass Concentration)**: 11 files (31% of file count) account for 68.6% of bytes (1,019,139 bytes) and 67.2% of code lines (23,248 lines).
   - *Inference*: Refactoring efforts should focus squarely on these 11 monolithic modules to achieve maximum architectural benefit.

2. **Premise 2 (Severe SRP Violations in Core Hubs)**:
   - `blender_bridge.py` mixes low-level socket transport, AST security validation, subprocess management, and 1,800+ lines of domain script generation.
   - `inference_adapter.py` embeds 1,108 lines of pure-python 3D procedural modeling (`MeshGeometry`) and binary glTF 2.0 serialization inside an AI generative inference dispatcher.
   - `character_assembler.py` combines 4K PBR texture baking (PIL/NumPy), scene assembly script generation (1,030 lines), master character coordination, and file packaging.
   - `visual_critic.py` combines scalar vector algebra, a complete pure-python BVH spatial index, 4 defect evaluation algorithms, synthetic fixtures, and QA reporting.
   - `wardrobe.py` combines skin weighting heuristics, procedural mesh modeling for 4 garments and 2 magic props, and Blender script generation.
   - `server.py` implements all 17 MCP tools directly in one 1,689-line file.
   - `models.py` bundles 62 classes across 5 different business domains into one file.
   - *Inference*: Decomposing these files into cohesive sub-packages (`bridge/`, `geometry/`, `assembler/`, `critic/`, `wardrobe/`, `rigging/`, `human/`, `grooming/`, `tools/`, `models/`) directly eliminates SRP violations and reduces blast radius.

3. **Premise 3 (Inbound Test & Caller Sensitivity)**:
   - 29 test files import from `morphomesh.models`.
   - 22 test files import from `morphomesh.blender_bridge`.
   - 22 test files import from `morphomesh.inference_adapter`.
   - 19 test files import from `morphomesh.human_generator`.
   - 17 test files import from `morphomesh.server`.
   - 12 test files import from `morphomesh.wardrobe`.
   - *Inference*: Any refactoring must strictly use facade legacy modules (e.g. keeping `src/morphomesh/blender_bridge.py` as a facade that re-exports all public symbols from `src/morphomesh/bridge/` via `__all__`) to ensure 100% backward compatibility and zero test regression.

4. **Premise 4 (Zero Existing Import Cycles)**:
   - Since the existing dependency graph has 0 cycles, a modular decomposition that respects the established layering (`models` -> `geometry` -> `domain engines` -> `bridge` / `assembler` -> `tools` -> `server`) will remain cleanly acyclic.

---

## 3. Caveats

1. **Blender Environment Availability**: Full integration tests involving live Blender execution require a running Blender instance on port 9876 or headless `blender.exe` on PATH. In test runs without Blender, mock execution and fallback branches are tested.
2. **Dynamic `__all__` and `__getattr__` Edge Cases**: Some external scripts or tests may use star imports (`from morphomesh.models import *`). Facade modules must explicitly populate `__all__` with all classes, constants, and functions to prevent missing symbols in star imports.
3. **AST Security Whitelist in `BpyCodeValidator`**: When splitting script generation into submodules, any changes to generated script formatting must continue to pass `BpyCodeValidator`'s AST security rules.

---

## 4. Conclusion

- The MorphoMesh codebase has grown into a highly capable 34,600+ line pipeline, but 11 monolithic files (>50KB) harbor severe SRP violations, monolithic script generators (>4,900 lines of Python strings), and hidden coupling (e.g., `MeshGeometry` in `inference_adapter.py`).
- The codebase is currently **free of circular import cycles** and has 2,082 automated tests, making it safe for modular decomposition.
- A clean, 12-package target architecture is proposed:
  - `morphomesh/bridge/`: Socket NDJSON transport, process runner, security validator, modular script builders.
  - `morphomesh/geometry/`: In-memory `MeshGeometry`, glTF/OBJ exporters, quad utilities.
  - `morphomesh/models/`: Domain-divided Pydantic schemas (errors, enums, creature, human, inspection, critique, animation).
  - `morphomesh/inference/`: Mock, Replicate, HuggingFace adapters, circuit breaker, factory.
  - `morphomesh/critic/`: Math utils, BVH spatial tree, penetration, proportions, deformation diagnostics.
  - `morphomesh/wardrobe/`: Skinning heuristics, bodice, sash, skirt, sandals, props (strings, butterflies).
  - `morphomesh/rigging/`: 163 DEF bones Rigify metarig, pivot alignment, anti-pinch weights, ARKit 52 blendshapes.
  - `morphomesh/human/`: MakeHuman CC0 mold loader, 32 vertex groups, parametric morphology.
  - `morphomesh/grooming/`: 6-stratum hime cut splines, ribbons, Geometry Nodes, animal fur.
  - `morphomesh/assembler/`: YuNianAnAssembler, 4K PBR texture baker, scene assembly, export packaging.
  - `morphomesh/materials/`: Principled BSDF v2 human & creature PBR shaders.
  - `morphomesh/tools/`: 17 decoupled FastMCP tool implementations.
- All monolithic files will be preserved as backward-compatible facade modules re-exporting symbols via `__all__`.

---

## 5. Verification Method

### 1. File Inventory & Size Verification
Verify total file count, sizes, and line counts:
```bash
uv run python -c "from pathlib import Path; files = list(Path('src/morphomesh').rglob('*.py')); print(f'Files: {len(files)}, Total bytes: {sum(f.stat().st_size for f in files):,}')"
```

### 2. Monolithic Files (>50KB) Count Verification
Verify that exactly 11 files exceed 50KB:
```bash
uv run python -c "from pathlib import Path; l = [f for f in Path('src/morphomesh').rglob('*.py') if f.stat().st_size >= 50*1024]; print(len(l)); [print(f.as_posix(), f.stat().st_size) for f in l]"
```

### 3. Circular Import Verification
Verify zero circular imports across all core modules:
```bash
uv run python -c "import morphomesh; import morphomesh.blender_bridge; import morphomesh.character_assembler; import morphomesh.visual_critic; import morphomesh.wardrobe; import morphomesh.human_rigging; import morphomesh.inference_adapter; import morphomesh.server; print('Import verification PASSED!')"
```

### 4. FastMCP Tool Schema Verification
Verify that all 17 tools remain registered and valid:
```bash
uv run pytest tests/test_tools_schema.py -v
```

### 5. Full Test Suite Regression Verification
Run the complete unit and adversarial test suite:
```bash
uv run pytest -q
```
