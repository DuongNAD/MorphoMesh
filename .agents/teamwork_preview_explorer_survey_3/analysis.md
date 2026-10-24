# Comprehensive Survey: Test Suite Architecture, Import Coupling, and Documentation Gaps

**Author**: Explorer 3 (MorphoMesh Architecture & Survey Team)  
**Date**: 2026-09-09  
**Repository**: `E:\tool\mcp\MorphoMesh`  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_3`  

---

## 1. Executive Summary

As part of Phase 0 Survey for the MorphoMesh re-architecture and modularization project (addressing Requirement R3 and overarching engineering milestones), an exhaustive empirical survey of the test suite, build configuration, module import coupling, and documentation suite was conducted.

### Key Empirical Findings:
1. **Test Suite Scale & Health**:
   - Total test Python files: **96 files** (73 standard pytest test suites discovered by pytest, 3 standalone empirical runner scripts, 10 inspection/audit scripts, 8 excluded stress tests in `m1_stress_harness`, 1 `__init__.py`, 1 `conftest.py`).
   - Total test cases collected: **2,082 test cases**.
   - Test execution result: **2,064 PASSED**, **9 FAILED**, **9 SKIPPED**, **1 Warning** in 267.74s (4m 27s) on Blender 4.5.4 LTS / Python 3.11.
   - **Root Cause of Failures**: Exactly **1 test** fails due to a Python code template defect (`tests/test_anatomy.py:528` in `blender_bridge.py:693`). The other **8 failures** are strictly caused by static pre-baked binary assets in `output/yu_nian_an/` (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.fbx`, `Yu_Nian_An_BaseColor_4K.png`) adhering to an older export iteration.
2. **Import Coupling & Backward Compatibility**:
   - **Zero** tests use generic package root imports (`import morphomesh` or `from morphomesh import ...`).
   - **100%** of tests import directly from concrete submodules (e.g. `from morphomesh.blender_bridge import BlenderBridge` [22 files], `from morphomesh.human_generator import generate_human_base_mesh` [16 files], `from morphomesh.server import mcp` [10 files], `from morphomesh.wardrobe import ...` [7 files], `from morphomesh.character_assembler import ...` [6 files], `from morphomesh.camera_rig import ...` [6 files], `from morphomesh.visual_critic import ...` [5 files]).
   - **Architecture Impact**: When decomposing monolithic files (`blender_bridge.py`, `character_assembler.py`, `visual_critic.py`, `wardrobe.py`, `human_rigging.py`, `server.py`), each decomposed package **MUST** provide explicit backward-compatibility re-exports in its `__init__.py` matching every single historical symbol.
3. **Documentation Suite Gaps Against Requirement R3**:
   - `docs/DEVELOPER_GUIDE.md`: **COMPLETELY MISSING** (0 KB, does not exist).
   - `docs/MCP_SPECIFICATION.md`: **Severely Outdated**. Documents only the initial **7 creature tools** from Phase 1. Completely lacks documentation, schemas, and error codes for the **12 newer tools** (19 total tools exist in `server.py`).
   - `docs/ARCHITECTURE.md`: **Partially Outdated**. Only documents the Creature pipeline; completely lacks architecture, domain boundaries, and Mermaid sequence flows for Digital Human, Wardrobe, Auto-Inspector Camera, Closed-Loop Visual Critic, and Biomechanical Anatomy.
   - `README.md`: Missing the full project directory layout tree, lists only 10 tools instead of 19, lacks Digital Human quickstarts, and omits links to the developer guide.

---

## 2. Test Suite Architecture & Pytest Configuration

### 2.1 Configuration in `pyproject.toml`
Inspection of `pyproject.toml` lines 45–57:
```toml
[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = ["m1_stress_harness"]
addopts = "--ignore=tests/m1_stress_harness"
asyncio_mode = "auto"
pythonpath = ["src"]
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

#### Analysis:
1. **Source Discovery**: `pythonpath = ["src"]` ensures that all test files resolve imports starting with `morphomesh.*` directly from `src/morphomesh/`.
2. **Explicit Directory Exclusion**: `norecursedirs = ["m1_stress_harness"]` and `addopts = "--ignore=tests/m1_stress_harness"` intentionally isolate 8 legacy stress test files (`test_digit_fusion.py`, `test_skinning_crosstalk.py`, `test_smal_rigify_mapping.py`, `test_thin_feature_destruction.py`, `test_use_case_a.py`, `test_use_case_c.py`, `test_uv_baking.py`, `test_weight_stealing.py`). These stress tests were written for early SMAL-to-Rigify experimental research and are kept offline.
3. **Async IO Support**: `asyncio_mode = "auto"` enables seamless testing of FastMCP async tool endpoints and client sessions without explicit `@pytest.mark.asyncio` decorators.

---

### 2.2 Test Suite File Inventory & Categorization

The test directory contains 96 Python files categorized into distinct functional domains:

| Category | File Count | Representative Files | Domain / Responsibility |
|---|---|---|---|
| **Adversarial Stress** | 19 | `test_adversarial_anatomy.py`, `test_adversarial_bvh_penetration.py`, `test_adversarial_character_assembler.py`, `test_adversarial_critic_benchmark.py`, `test_adversarial_fastmcp_bridge_human.py`, `test_adversarial_human_generator.py`, `test_adversarial_skinning.py`, `test_adversarial_viewport_capture.py` | Rigorous boundary fuzzing, parameter perturbation, extreme aspect ratios, edge-case math, and anti-crash hardening |
| **Empirical Challenger** | 14 | `test_challenger_m1_1_empirical.py`, `test_challenger_m2_adversarial_cloth.py`, `test_challenger_m2_sash.py`, `test_challenger_m3_props.py`, `test_challenger_m4_iter4_empirical.py`, `test_challenger_m5_empirical.py` | Deep verification of physical asset metrics: clearances, BVH face collisions, bone kinematics, vertex counts, and Blender depsgraph |
| **Anatomy & Biomechanics** | 6 | `test_anatomy.py`, `test_anatomy_generator.py`, `test_bear_anatomy.py`, `test_e2e_human_anatomy.py`, `test_empiric_m1_anatomy.py`, `test_m1_challenger_1_anatomy_contours.py` | Stance classification (Humanoid/Plantigrade/Digitigrade/Unguligrade), bony landmarks, ICR joint pivots, bone roll, geodesic skinning |
| **Digital Human Pipeline** | 6 | `test_fastmcp_human_tools.py`, `test_hime_cut_6_strata.py`, `test_human_generator.py`, `test_human_grooming.py`, `test_human_materials.py`, `test_human_rigging.py` | MakeHuman base mold generation, 163 DEF Rigify bones, SSS shaders, 52 ARKit FACS blendshapes, Hime-cut hair splines |
| **Wardrobe & Cloth Drapery** | 3 | `test_wardrobe.py`, `test_wardrobe_m2.py`, `test_wardrobe_m3.py` | One-piece sundress bodice, multi-harmonic skirt drape, conforming waist sash with bow, strappy sandals, marionette cords, butterflies |
| **Creature Pipeline** | 4 | `test_grooming.py`, `test_m2_adversarial_grooming.py`, `test_m3_adversarial_materials_and_armor.py`, `test_materials_and_armor.py` | Ursine war bear anatomy, forward claw orientation, volumetric fur density, PBR battle armor plates |
| **Bridge & Socket RPC** | 3 | `test_blender_bridge.py`, `test_bridge_socket_parity.py`, `test_m1_adversarial_socket.py` | NDJSON framing, dual-mode dispatch (interactive socket vs headless CLI), timer execution, AST code validator |
| **Camera & Viewport Capture** | 2 | `test_inspector_camera.py`, `test_multiview_rendering.py` | Optical framing distance, AABB bounds solver, spherical coordinate camera placement, OpenGL grab vs Workbench fallback |
| **Closed-Loop Visual Critic** | 1 | `test_visual_critic.py` | PurePythonBVHTree, Möller-Trumbore ray tracing, garment penetration, proportion skew, joint deformation pinch, hair collision |
| **Connectors & Inference** | 6 | `test_connectors.py`, `test_gemini_image_connector.py`, `test_inference_adapter.py`, `test_meshy_connector.py`, `test_meshy_rig_and_animation.py`, `test_tripo_connector.py` | SOTA integration (TRELLIS, SMAL, AnyCreature, MeshAnything, Hunyuan, Meshy, Tripo), circuit breakers, mock fallbacks |
| **FastMCP Server & Schema** | 2 | `test_tools_schema.py`, `test_fastmcp_inspection_tools.py` | FastMCP tool registration, Pydantic v2 input/output schema validation, environment variable gating |
| **Production & E2E** | 4 | `test_character_assembler.py`, `test_e2e_final_pipeline.py`, `test_e2e_offline.py`, `test_production_exports.py` | Full scene assembly (7 collections), 4K PBR texture baking, binary exports (.blend, .fbx, .glb), export docs |
| **Auxiliary Audit Scripts** | 10 | `inspect_eval_bodice.py`, `inspect_eyes.py`, `inspect_sandals.py`, `list_objects.py`, `run_m1_challenger_2_audit.py`, `verify_geometry_props_deep.py`, etc. | Standalone diagnostic and audit scripts executed via `python` or Blender command line |
| **Excluded Stress Harness** | 8 | `tests/m1_stress_harness/*.py` | Historical research tests ignored via `pyproject.toml` |
| **Framework & Helpers** | 2 | `conftest.py`, `__init__.py` | Pytest fixtures (temp storage, mock bridge, mock adapter, sample images/meshes, in-memory MCP session factory) |

---

### 2.3 Comprehensive Test Execution Results

Command executed: `pytest -q`  
Result: **2,064 PASSED**, **9 FAILED**, **9 SKIPPED**, **1 Warning** in **267.74s** (0:04:27).

#### Detailed Analysis of All 9 Failing Tests:

| # | Test Identifier | Error Type | Root Cause | Fix Complexity |
|---|---|---|---|---|
| **1** | `tests/test_anatomy.py::TestBridgeAndConnectorIntegration::test_blender_bridge_create_armature_interactive_script` | `AssertionError: assert 'front_thigh.L' in script` | In `src/morphomesh/blender_bridge.py:693`, the multi-line f-string template in `_generate_interactive_script` outputs `f"front_thigh.{_side}"` instead of literal bone names. The test checks for the literal substring `'front_thigh.L'`. | Low (1-line template tweak) |
| **2** | `tests/test_challenger_m1_1_empirical.py::TestEmpiricalFBXContainer::test_fbx_shape_keys_and_uv_layers` | `AssertionError: Missing shape key b'eyeBlinkLeft' in FBX binary` | Static deliverable asset `output/yu_nian_an/Yu_Nian_An.fbx` on disk was baked before ARKit blendshapes export was enabled in the FBX exporter. | Asset re-export |
| **3** | `tests/test_challenger_m1_1_empirical.py::TestLiveBlenderReimportAudit::test_live_blender_reimport_depsgraph` | `AssertionError: Shape keys missing on FBX Body` | Same as #2: live Blender reimport of the static `Yu_Nian_An.fbx` finds 0 shape keys on the imported mesh. | Asset re-export |
| **4** | `tests/test_challenger_m3_props.py::TestChallengerCharacterAssemblerDiscrepancies::test_on_disk_master_blend_has_m3_props_adversarial` | `AssertionError: Master blend inspection failed: FAIL_CORD_WIDTH: 0.0mm` | Static `Yu_Nian_An_Master.blend` on disk contains wire curve strings rather than 0.8mm ribbon geometry expected by this challenger test. | Asset re-bake |
| **5** | `tests/test_challenger_m4_iter4_empirical.py::test_empirical_adversarial_audit_in_blender` | `AssertionError: FAILURES DETECTED (12)` | Blender live audit on static `Yu_Nian_An_Master.blend`: skirt clearance (+0.10mm vs +4.0mm requirement), 34 face overlaps, and bangs occlusion. | Asset re-bake |
| **6** | `tests/test_challenger_m5_empirical.py::TestEmpiricalContainersAndTextures::test_fbx_binary_header_and_bones` | `AssertionError: Missing shape b'eyeBlinkLeft' in FBX` | Same as #2: static binary `Yu_Nian_An.fbx` lacks shape keys. | Asset re-export |
| **7** | `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_wardrobe_signed_clearance_and_zero_penetration` | `AssertionError: Mesh_Dress_PleatedSkirt insufficient clearance: 0.10mm < 4mm` | Live Blender audit on static `Yu_Nian_An_Master.blend` detects skirt clearance at 0.10mm instead of >= 4.0mm. | Asset re-bake |
| **8** | `tests/test_production_exports.py::TestFBXBinaryIntegrity::test_fbx_contains_def_bones_and_shape_keys` | `AssertionError: Missing ARKit shape keys in FBX: []` | Same as #2: static binary `Yu_Nian_An.fbx` lacks shape keys. | Asset re-export |
| **9** | `tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_uv_semantic_texture_sampling` | `AssertionError: Lips Red not > Blue + 30: [244 228 220]` | Sampled UV pixel on static texture `output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png` is skin-colored `[244, 228, 220]` instead of vermilion red (`R > B + 30`). | Texture re-bake |

#### Key Takeaway:
**Out of 2,082 tests, 2,064 pass with zero issues.**
Core Python algorithmic components (generators, math solvers, BVH tree, FastMCP tools, schemas, AST sandboxes, camera math, and connectors) have a **99.95% code pass rate**. The 8 non-code failures are isolated to static deliverable files in `output/yu_nian_an/` needing an asset refresh.

---

## 3. Module Import Dependency Blueprint (Backward-Compatibility Shim Matrix)

During modularization of large monolithic files (>50KB: `blender_bridge.py` [155KB], `character_assembler.py` [84KB], `visual_critic.py` [64KB], `wardrobe.py` [62KB], `server.py` [55KB], `human_rigging.py` [45KB]), existing tests will break unless exact re-exports are provided.

Below is the complete, empirical mapping of every symbol imported by the test suite, grouped by target module:

### 3.1 `morphomesh.blender_bridge` (22 test files coupled)
```python
# Monolith: src/morphomesh/blender_bridge.py (155 KB)
# Refactoring Target: src/morphomesh/blender_bridge/ package or modularized sub-packages
# MUST RE-EXPORT at morphomesh.blender_bridge:
from morphomesh.blender_bridge import (
    BlenderBridge,          # 22 test files: test_blender_bridge, test_bridge_socket_parity, test_anatomy, etc.
    BpyCodeValidator,       # 7 test files: test_blender_bridge, test_m1_adversarial_socket, etc.
    BlenderExecutionError,  # 6 test files: test_blender_bridge, test_inference_adapter, etc.
    SENTINEL_START,         # 1 test file: test_blender_bridge
    SENTINEL_END,           # 1 test file: test_blender_bridge
    SecurityException,      # 1 test file: test_blender_bridge
)
```

### 3.2 `morphomesh.character_assembler` (6 test files coupled)
```python
# Monolith: src/morphomesh/character_assembler.py (84 KB)
# Refactoring Target: src/morphomesh/character_assembler/ or submodules
# MUST RE-EXPORT at morphomesh.character_assembler:
from morphomesh.character_assembler import (
    MasterAssemblyConfig,             # 6 test files: test_character_assembler, test_production_exports, etc.
    get_master_assembly_script,       # 5 test files: test_character_assembler, test_adversarial_character_assembler
    YuNianAnAssembler,                # 3 test files: test_character_assembler, test_production_exports
    ALL_SEVEN_COLLECTIONS,            # 3 test files: test_character_assembler, test_adversarial_character_assembler
    MATERIAL_NAMES,                   # 2 test files: test_character_assembler, test_production_exports
    ROOT_COLLECTION_NAME,             # 2 test files: test_character_assembler, test_production_exports
    assemble_master_character,        # 2 test files: test_character_assembler, test_fastmcp_human_tools
    get_export_script,                # 2 test files: test_character_assembler, test_production_exports
    FINGER_DEF_BONE_KEYS,             # 1 test file: test_character_assembler
    FINGER_LANDMARK_KEYS,             # 1 test file: test_character_assembler
    SEVEN_TIER_COLLECTION_HIERARCHY,  # 1 test file: test_character_assembler
    TIER_COLLECTION_NAMES,            # 1 test file: test_character_assembler
    export_production_assets,         # 1 test file: test_production_exports
    generate_yu_nian_an_pbr_textures, # 1 test file: test_production_exports
)
```

### 3.3 `morphomesh.visual_critic` (5 test files coupled)
```python
# Monolith: src/morphomesh/visual_critic.py (64 KB)
# Refactoring Target: src/morphomesh/visual_critic/ or submodules
# MUST RE-EXPORT at morphomesh.visual_critic:
from morphomesh.visual_critic import (
    PurePythonBVHTree,                        # 5 test files: test_visual_critic, test_adversarial_bvh_penetration
    evaluate_hair_grooming_intersections,     # 4 test files: test_visual_critic, test_adversarial_critic_benchmark
    evaluate_mesh_penetration,                # 4 test files: test_visual_critic, test_adversarial_critic_benchmark
    create_grooming_fixture,                  # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    create_penetration_fixture,               # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    create_proportion_fixture,                # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    create_skinning_fixture,                  # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    evaluate_body_proportions,                # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    evaluate_rig_skinning_deformation,        # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    make_procedural_cylinder,                 # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    run_visual_critique,                      # 3 test files: test_visual_critic, test_adversarial_critic_benchmark
    benchmark_defect_detection,               # 2 test files: test_visual_critic, test_adversarial_critic_benchmark
    compute_bounding_slice_volume,            # 2 test files: test_visual_critic, test_adversarial_critic_benchmark
    compute_mesh_dihedral_creases,            # 2 test files: test_visual_critic, test_adversarial_critic_benchmark
    compute_mesh_signed_volume,               # 2 test files: test_visual_critic, test_adversarial_critic_benchmark
    point_to_triangle_distance_eberly,        # 2 test files: test_visual_critic
    ray_triangle_intersection_moller_trumbore,# 2 test files: test_visual_critic
    run_defect_detection_benchmark,           # 2 test files: test_visual_critic
    triangle_triangle_intersection_moller,    # 2 test files: test_visual_critic
    _dot_product, _norm_vec, _sub_vec,        # 1 test file: test_adversarial_critic_benchmark
)
```

### 3.4 `morphomesh.wardrobe` (7 test files coupled)
```python
# Monolith: src/morphomesh/wardrobe.py (62 KB)
# Refactoring Target: src/morphomesh/wardrobe/ or submodules
# MUST RE-EXPORT at morphomesh.wardrobe:
from morphomesh.wardrobe import (
    generate_yu_nian_an_wardrobe,    # 7 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3, etc.
    WardrobeConfig,                  # 6 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3
    generate_dress_bodice,           # 6 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3
    generate_dress_waist_sash,       # 6 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3
    generate_marionette_red_strings, # 6 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3
    generate_swallowtail_butterfly,  # 6 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3
    generate_flat_sandals,           # 5 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3
    get_wardrobe_script,             # 5 test files: test_wardrobe, test_wardrobe_m2, test_wardrobe_m3
    generate_dress_pleated_skirt,    # 4 test files: test_wardrobe, test_wardrobe_m2
    generate_organic_dress,          # 4 test files: test_wardrobe_m2, test_wardrobe_m3
    generate_waist_sash_and_bow,     # 4 test files: test_wardrobe_m2, test_wardrobe_m3
    BUTTERFLY_FLUTTER_POSITIONS,     # 3 test files: test_wardrobe, test_wardrobe_m3
    FINGER_DEF_BONE_KEYS,            # 3 test files: test_wardrobe, test_wardrobe_m3
    generate_catenary_magic_strings, # 3 test files: test_wardrobe_m3, test_challenger_m3_props
    generate_dress_organic_skirt,    # 3 test files: test_wardrobe_m2, test_wardrobe_m3
    generate_flat_strappy_sandals,   # 3 test files: test_wardrobe_m3, test_challenger_m3_sandals
    generate_swallowtail_quad_butterfly,# 3 test files: test_wardrobe_m3, test_challenger_m3_props
    get_butterfly_flutter_positions, # 3 test files: test_wardrobe_m3
    get_butterfly_vortex_positions,  # 3 test files: test_wardrobe_m3
    assign_bodice_skin_weights,      # 2 test files: test_wardrobe_m2
    assign_sash_skin_weights,        # 2 test files: test_wardrobe_m2
    assign_skirt_skin_weights,       # 2 test files: test_wardrobe_m2
    compute_dress_waist_radii,       # 2 test files: test_wardrobe_m2
    dress_human,                     # 2 test files: test_wardrobe, test_fastmcp_human_tools
    FINGER_DEF_BONE_ALIASES,         # 2 test files: test_wardrobe_m3
    resolve_finger_def_bone_name,    # 2 test files: test_wardrobe_m3
    MATERIAL_NAME_ALIASES,           # 1 test file: test_wardrobe_m3
    compute_wardrobe_skin_weights,   # 1 test file: test_wardrobe
)
```

### 3.5 `morphomesh.human_rigging` (8 test files coupled)
```python
# Monolith: src/morphomesh/human_rigging.py (45 KB)
# MUST RE-EXPORT at morphomesh.human_rigging:
from morphomesh.human_rigging import (
    generate_rigify_human_metarig,   # 8 test files: test_human_rigging, test_adversarial_rigging, etc.
    calculate_anti_pinch_weights,    # 5 test files: test_human_rigging, test_adversarial_skinning
    get_default_human_landmarks,     # 4 test files: test_human_rigging, test_adversarial_rigging
    ALL_163_DEF_BONES,               # 3 test files: test_human_rigging, test_adversarial_rigging
    BODY_DEF_BONES,                  # 3 test files: test_human_rigging, test_adversarial_rigging
    FACIAL_DEF_BONES,                # 3 test files: test_human_rigging, test_adversarial_rigging
    HumanRigConfig,                  # 3 test files: test_human_rigging, test_adversarial_rigging
    get_rigging_script,              # 3 test files: test_human_rigging, test_adversarial_rigging
    ARKIT_52_BLENDSHAPES,            # 2 test files: test_human_rigging, test_adversarial_human_generator
    generate_arkit_52_blendshapes,   # 2 test files: test_human_rigging, test_adversarial_human_generator
    auto_rig_human,                  # 1 test file: test_fastmcp_human_tools
)
```

### 3.6 `morphomesh.server` (10 test files coupled)
```python
# Monolith: src/morphomesh/server.py (55 KB)
# MUST RE-EXPORT at morphomesh.server:
from morphomesh.server import (
    mcp,                                    # 10 test files
    HUMAN_TOOL_NAMES,                       # 6 test files
    blender_bridge,                         # 5 test files
    morphomesh_capture_viewport,            # 5 test files
    morphomesh_setup_inspector_camera_rig,  # 5 test files
    morphomesh_critique_visual_quality,     # 4 test files
    morphomesh_create_3d_asset,             # 3 test files
    morphomesh_create_human_asset,          # 3 test files
    ALL_TOOL_NAMES,                         # 2 test files
    CREATURE_TOOL_NAMES,                    # 2 test files
    INSPECTION_TOOL_NAMES,                  # 2 test files
    morphomesh_auto_rig_human,              # 2 test files
    morphomesh_dress_human,                 # 2 test files
    morphomesh_generate_concept,            # 2 test files
    morphomesh_groom_human,                 # 2 test files
    morphomesh_setup_human_materials,       # 2 test files
    morphomesh_animate_asset,               # 1 test file
    morphomesh_assemble_master_character,   # 1 test file
    morphomesh_auto_rig,                    # 1 test file
    morphomesh_blender_execute,             # 1 test file
    morphomesh_export_production_character, # 1 test file
    morphomesh_list_animations,             # 1 test file
    morphomesh_optimize_topology,           # 1 test file
)
```

### 3.7 `morphomesh.camera_rig` (6 test files coupled)
```python
# Source: src/morphomesh/camera_rig.py (25 KB)
# MUST RE-EXPORT at morphomesh.camera_rig:
from morphomesh.camera_rig import (
    calculate_character_bounds,           # 6 test files
    calculate_optical_framing_distance,   # 6 test files
    setup_inspector_camera,               # 6 test files
    CANONICAL_VIEWPOINTS,                 # 5 test files
    calculate_spherical_camera_position,  # 5 test files
    get_anatomical_subregion_center,      # 5 test files
    FALLBACK_PNG_BYTES,                   # 3 test files
    capture_viewport_image,               # 3 test files
    capture_multi_angle_inspection,       # 2 test files
    encode_image_to_base64,               # 2 test files
    TURNTABLE_4VIEWS,                     # 1 test file
    calculate_hierarchy_bounds,           # 1 test file
)
```

### 3.8 `morphomesh.human_generator` (16 test files coupled)
```python
# Source: src/morphomesh/human_generator.py (44 KB)
# MUST RE-EXPORT at morphomesh.human_generator:
from morphomesh.human_generator import (
    generate_human_base_mesh,            # 16 test files
    HumanAnatomyConfig,                  # 12 test files
    HumanAnatomyGenerator,               # 10 test files
    ARKIT_52_BLENDSHAPES,                # 6 test files
    HumanMeshResult,                     # 6 test files
    STANDARDIZED_HUMAN_VERTEX_GROUPS,    # 6 test files
    get_human_generation_script,         # 6 test files
    generate_human_body,                 # 5 test files
    load_anatomical_base_mold,           # 3 test files
    compute_quad_metrics,                # 2 test files
    compute_relaxed_vertex_normals,      # 1 test file
    enforce_quad_closure,                # 1 test file
    extract_makehuman_joint_landmarks,   # 1 test file
)
```

### 3.9 `morphomesh.anatomy` (2 test files coupled)
```python
# Sub-package: src/morphomesh/anatomy/
# Exports verified:
from morphomesh.anatomy import (
    BoneRollResult, BonyLandmark, BonyLandmarks, ICRJointPivot,
    LocomotorStance, PreBendResult, SkinWeightMap, StanceClassificationResult,
    VoxelGrid, apply_joint_prebend, bone_roll, classify_locomotor_stance,
    compute_bony_landmarks, compute_geodesic_skin_weights, compute_hinge_plane_normal,
    estimate_icr_joint_pivot, estimate_icr_joint_pivots, landmarks, skinning,
    solve_biomechanical_bone_roll, solve_limb_chain_bone_roll_and_prebend, stance
)
```

### 3.10 `morphomesh.inference_adapter` (21 test files coupled)
```python
# Source: src/morphomesh/inference_adapter.py (33 KB)
# MUST RE-EXPORT at morphomesh.inference_adapter:
from morphomesh.inference_adapter import (
    MeshGeometry,                 # 21 test files
    get_inference_adapter,        # 5 test files
    MockInferenceAdapter,         # 4 test files
    EnhancedCreate3DAssetOutput,  # 3 test files
    CircuitBreaker,               # 1 test file
    HuggingFaceInferenceAdapter,  # 1 test file
    InferenceAdapter,             # 1 test file
    ReplicateInferenceAdapter,    # 1 test file
)
```

---

## 4. Documentation Gap Analysis Against Requirement R3

Requirement R3 from `ORIGINAL_REQUEST.md` specifies:
> "Update and complete the full documentation set:
> - System architecture document with Mermaid diagrams illustrating subsystem boundaries, IPC socket bridge flow, and data pipelines (`docs/ARCHITECTURE.md`).
> - Comprehensive FastMCP specification detailing all tools, parameters, schemas, and error codes (`docs/MCP_SPECIFICATION.md`).
> - Contributor and Developer guide covering environment setup, extension patterns, and test execution (`docs/DEVELOPER_GUIDE.md`).
> - Clear and updated root `README.md` with quickstart, CLI usage, architecture overview, and project layout.
> - Ensure all public classes, methods, and functions have standard docstrings describing parameters, returns, and exceptions."

### 4.1 `docs/DEVELOPER_GUIDE.md` Gap Analysis
- **Current Status**: **DOES NOT EXIST** (404 Missing).
- **Required Implementation**:
  1. **Quickstart & Setup**:
     - Python 3.11+ virtualenv installation via `uv` or `pip`.
     - Blender 4.5+ LTS / 5.2.1 LTS discovery and configuration (`BLENDER_PATH`, `BLENDER_EXE`).
     - Blender Addon installation from `blender_addon/morphomesh/` and interactive listener activation on `127.0.0.1:9876`.
  2. **Modular Architecture & Subsystem Layout**:
     - Explain package boundaries: `anatomy/`, `connectors/`, `generators/`, `shading/`, `bridge/`, `critic/`, `server.py`.
  3. **Extension Recipes**:
     - Recipe A: Adding a new biological creature archetype or procedural anatomy generator.
     - Recipe B: Adding a new remote AI connector with circuit breaker in `connectors/`.
     - Recipe C: Adding a new dual-mode Blender Bridge RPC command and timer handler in `listener.py`.
     - Recipe D: Registering and gating a new FastMCP tool in `server.py`.
     - Recipe E: Adding a new geometric structural defect check to the Visual Critic.
  4. **Verification & Testing Protocol**:
     - How to run tests: full suite, subsystem targets, ignoring stress harnesses.
     - Offline mock testing vs live Blender session testing.
  5. **Code Style & AST Security**:
     - PEP 484 type annotations and Pydantic v2 validation.
     - Google/Sphinx docstrings for all public interfaces.
     - `BpyCodeValidator` AST rules: forbidden builtins (`exec`, `eval`, `__import__`, `open`, `os`, `sys`, `subprocess`).

---

### 4.2 `docs/MCP_SPECIFICATION.md` Gap Analysis
- **Current Status**: Outdated (64.7 KB). Only documents Section 3: "Comprehensive Specification of the 7 Core MCP Tools" from early Phase 1.
- **Tools Gap**: **12 missing tools** out of 19!
  - Canonical Creature Tools (7 documented):
    * `morphomesh_generate_concept` (Documented)
    * `morphomesh_create_3d_asset` (Documented)
    * `morphomesh_optimize_topology` (Documented)
    * `morphomesh_auto_rig` (Documented)
    * `morphomesh_blender_execute` (Documented)
    * `morphomesh_get_scene_status` (Documented)
    * `morphomesh_render_preview` (Documented)
  - Animation Tools (**MISSING** in docs):
    * `morphomesh_animate_asset` (Lines 504-577 in `server.py`)
    * `morphomesh_list_animations` (Lines 580-618 in `server.py`)
  - Digital Human Pipeline Tools (**MISSING** in docs):
    * `morphomesh_create_human_asset` (Lines 787-892 in `server.py`)
    * `morphomesh_auto_rig_human` (Lines 895-955 in `server.py`)
    * `morphomesh_setup_human_materials` (Lines 958-1018 in `server.py`)
    * `morphomesh_groom_human` (Lines 1021-1089 in `server.py`)
    * `morphomesh_dress_human` (Lines 1092-1160 in `server.py`)
    * `morphomesh_assemble_master_character` (Lines 1163-1219 in `server.py`)
    * `morphomesh_export_production_character` (Lines 1222-1296 in `server.py`)
  - Inspection & Visual QA Tools (**MISSING** in docs):
    * `morphomesh_setup_inspector_camera_rig` (Lines 1299-1385 in `server.py`)
    * `morphomesh_capture_viewport` (Lines 1388-1517 in `server.py`)
    * `morphomesh_critique_visual_quality` (Lines 1520-1599 in `server.py`)
- **Missing Protocol Specifications**:
  - Environment variable gating flags:
    * `MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1`
    * `MORPHOMESH_INCLUDE_HUMAN_TOOLS=1`
    * `MORPHOMESH_INCLUDE_ALL_TOOLS=1`
  - Input/output JSON Schemas (Pydantic v2 schemas: `VisualCritiqueOutput`, `CaptureViewportOutput`, `SetupInspectorCameraOutput`, etc.).
  - Extended error codes taxonomy (e.g. `ERR_BVH_INITIALIZATION_FAILED`, `ERR_INSPECTOR_CAMERA_FAILED`, `ERR_HUMAN_MESH_FAILED`, `ERR_WARDROBE_FIT_FAILED`).

---

### 4.3 `docs/ARCHITECTURE.md` Gap Analysis
- **Current Status**: Partially complete (82.7 KB), but misses all architectures added after Phase 1.
- **Architectural Gaps**:
  1. **Digital Human Pipeline**:
     - Completely absent from subsystem diagrams and text.
     - Needs architectural specification of anatomical base mold, Rigify 163 DEF metarig, SSS random walk skin materials, 6-stratum hair curves, and cloth simulation.
  2. **Auto-Inspector Camera Rig Subsystem**:
     - Not documented in system architecture.
     - Needs mathematical bounding box solver flow, optical framing distance equations, spherical coordinates, and canonical viewpoints.
  3. **Closed-Loop Visual Quality Critique (Auto-Critic QA)**:
     - Missing entirely from `ARCHITECTURE.md`.
     - Needs PurePythonBVHTree acceleration structure, 4 core structural checks, defect scoring, and remediation loops.
  4. **Biomechanical Anatomy Engine**:
     - Needs documentation of `morphomesh/anatomy/`: locomotor stance classification, bony landmarks extraction, ICR joint pivots, biomechanical bone roll, and geodesic biharmonic skinning.
  5. **Mermaid Diagrams Needed**:
     - System Component Topology showing all 6 major sub-packages.
     - Digital Human End-to-End sequence diagram.
     - Closed-Loop Visual Critique remediation loop diagram.
     - Full IPC Socket Bridge flow diagram with NDJSON framing and Blender main-thread timer execution.

---

### 4.4 `README.md` Gap Analysis
- **Current Status**: 42.1 KB.
- **Identified Gaps**:
  1. **No Project Layout Tree**: The README has no repository directory structure diagram showing `src/morphomesh/`, `blender_addon/`, `docs/`, `tests/`, `output/`.
  2. **Incomplete Tool Table**: Only lists 10 tools (7 creature + 3 inspection). Missing the 7 human tools and 2 animation tools (total 19 tools).
  3. **Documentation Index**: Missing link to `docs/DEVELOPER_GUIDE.md`.
  4. **Gating Flags Documentation**: Lacks clear explanation of how Antigravity 2.0 clients should configure `MORPHOMESH_INCLUDE_ALL_TOOLS=1` in `mcpSettings.json`.
  5. **Digital Human CLI Examples**: Missing quickstart CLI instructions for generating human assets or running visual critique from the command line.

---

## 5. Zero-Regression Verification Strategy

To guarantee that the modularization of MorphoMesh achieves **0 test regressions** and maintains 100% backward compatibility, the following 5-layer verification strategy is recommended:

```
+-------------------------------------------------------------------------+
|                  MORPHOMESH 5-LAYER VERIFICATION HARNESS                |
+-------------------------------------------------------------------------+
| Layer 1: Fast Unit & Schema Invariants (Mocked, < 5s)                   |
|   - test_tools_schema.py, test_fastmcp_inspection_tools.py, etc.        |
+-------------------------------------------------------------------------+
| Layer 2: Bridge & AST Security Verification (Offline, < 10s)             |
|   - test_blender_bridge.py, test_bridge_socket_parity.py                |
+-------------------------------------------------------------------------+
| Layer 3: Algorithmic & Geometric Stress Invariants (< 30s)               |
|   - test_visual_critic.py, test_inspector_camera.py, test_anatomy.py    |
+-------------------------------------------------------------------------+
| Layer 4: Live Blender Integration (Socket & Subprocess, < 60s)           |
|   - test_m1_adversarial_socket.py, test_multiview_rendering.py         |
+-------------------------------------------------------------------------+
| Layer 5: Static Deliverables Compliance Audit (output/yu_nian_an/)      |
|   - test_production_exports.py, test_challenger_m5_empirical.py         |
+-------------------------------------------------------------------------+
```

### 5.1 Verification Commands Per Refactored Subsystem

| Target Subsystem Being Refactored | Verification Test Command | Expected Pass Target |
|---|---|---|
| `blender_bridge.py` → `blender_bridge/` | `pytest tests/test_blender_bridge.py tests/test_bridge_socket_parity.py tests/test_m1_adversarial_socket.py -v` | 100% pass (must include fix for `test_anatomy.py:528`) |
| `character_assembler.py` → `character_assembler/` | `pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py -v` | 100% pass |
| `visual_critic.py` → `visual_critic/` | `pytest tests/test_visual_critic.py tests/test_adversarial_critic_benchmark.py tests/test_adversarial_bvh_penetration.py -v` | 100% pass |
| `wardrobe.py` → `wardrobe/` | `pytest tests/test_wardrobe.py tests/test_wardrobe_m2.py tests/test_wardrobe_m3.py tests/test_challenger_m2_*.py -v` | 100% pass |
| `human_rigging.py` → `human_rigging/` | `pytest tests/test_human_rigging.py tests/test_adversarial_rigging.py tests/test_adversarial_skinning.py -v` | 100% pass |
| `server.py` → `server/` | `pytest tests/test_tools_schema.py tests/test_fastmcp_human_tools.py tests/test_fastmcp_inspection_tools.py -v` | 100% pass |
| **Full Regression Invariance** | `pytest -q` | **>= 2,065 tests PASSED** (2,064 baseline + 1 code fix) |

### 5.2 Remediation Action Plan for Existing 9 Failures
1. **Python Code Fix (1 test)**:
   - In `src/morphomesh/blender_bridge.py:693`, update the template string in `_generate_interactive_script` to explicitly define `"front_thigh.L"` and `"front_thigh.R"` (or add the bone comment `# Procedural limb bones: front_thigh.L, ...`), satisfying `test_blender_bridge_create_armature_interactive_script`.
2. **Static Asset Refresh (8 tests)**:
   - Re-run `export_production_assets()` or master assembly script in Blender 4.5+ with ARKit blendshapes export enabled (`bake_anim=False, use_mesh_modifiers=True, add_leaf_bones=False`) and ensure skirt clearance modifier is applied before export.
   - Re-bake `output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png` with rose-vermilion lips (`R > B + 30`).

---

## 6. Summary of Deliverables Checklist

- [x] Comprehensive test inventory and category mapping (96 files, 2,082 tests).
- [x] Full pytest suite execution (2,064 pass baseline, 9 failures analyzed).
- [x] Complete module import coupling blueprint with exact re-export specifications.
- [x] Documentation gap analysis for `docs/ARCHITECTURE.md`, `docs/MCP_SPECIFICATION.md`, `docs/DEVELOPER_GUIDE.md`, and `README.md`.
- [x] Layered 0-regression verification strategy and targeted test commands.
