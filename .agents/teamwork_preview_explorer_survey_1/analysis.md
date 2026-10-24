# Architectural Survey & Monolithic Decomposition Analysis for MorphoMesh

## Executive Summary

This report presents the comprehensive Phase 0 survey of the MorphoMesh Python codebase (`src/morphomesh/`).
The objective is to analyze the structural topology, measure file metrics, identify monolithic files exceeding 50KB or 800 lines,
audit import dependencies and couplings, identify performance and serialization bottlenecks, and propose clean,
Single Responsibility Principle (SRP) compliant sub-package decompositions with 100% backward compatibility.

### Quantitative Overview

- **Total Python Modules Analyzed**: 35 files across `src/morphomesh/`
- **Total Code Volume**: 1,485,538 bytes (~1.42 MB), 34,609 lines of code
- **Monolithic Files (>= 50 KB)**: 11 files (974,151 bytes, 21,938 lines) — representing **65.6%** of total bytes and **63.4%** of codebase lines
- **Large Secondary Files (>= 800 lines, < 50 KB)**: 6 files (242,383 bytes, 5,843 lines) — representing **16.3%** of codebase
- **Standard / Modular Files (< 800 lines, < 50 KB)**: 18 files (269,004 bytes, 6,828 lines) — representing **18.1%** of codebase
- **Module Circular Import Cycles**: **0 cycles** detected when resolving exact module paths; all top-level modules import without circular dependency errors.
- **Full Pytest Suite Baseline**: 2,082 tests total — **2,064 PASSED**, **9 SKIPPED**, **9 FAILED** (in 255.19s).
  - *Baseline Failure Analysis*: All 9 pre-existing failures are confined to empirical output binary assertions in `output/yu_nian_an/` (`Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, `Yu_Nian_An_Master.blend`), such as live Blender wardrobe clearance, binary FBX shape key string matching, and GLB lip texture color sampling. The core codebase logic, FastMCP tool schemas, bridge dispatchers, anatomy engines, and procedural modeling tests achieve **100% PASS** (2,064 tests).
  - The 9 pre-existing failing tests:
    1. `tests/test_anatomy.py::TestBridgeAndConnectorIntegration::test_blender_bridge_create_armature_interactive_script`
    2. `tests/test_challenger_m1_1_empirical.py::TestEmpiricalFBXContainer::test_fbx_shape_keys_and_uv_layers`
    3. `tests/test_challenger_m1_1_empirical.py::TestLiveBlenderReimportAudit::test_live_blender_reimport_depsgraph`
    4. `tests/test_challenger_m3_props.py::TestChallengerCharacterAssemblerDiscrepancies::test_on_disk_master_blend_has_m3_props_adversarial`
    5. `tests/test_challenger_m4_iter4_empirical.py::test_empirical_adversarial_audit_in_blender`
    6. `tests/test_challenger_m5_empirical.py::TestEmpiricalContainersAndTextures::test_fbx_binary_header_and_bones`
    7. `tests/test_character_assembler.py::TestLiveBlenderMasterAssetVerification::test_live_wardrobe_signed_clearance_and_zero_penetration`
    8. `tests/test_production_exports.py::TestFBXBinaryIntegrity::test_fbx_contains_def_bones_and_shape_keys`
    9. `tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_uv_semantic_texture_sampling`

---

## 1. Complete Codebase Inventory (All 35 Files)

| # | Module Path | Size (Bytes) | Size (KB) | Lines | Classes | Functions | Inbound (Src) | Inbound (Tests/Addon) | Category |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `src/morphomesh/blender_bridge.py` | 155,140 | 151.50 KB | 3,454 | 4 | 0 | 2 | 22 | **Monolith (>=50KB)** |
| 2 | `src/morphomesh/character_assembler.py` | 107,667 | 105.14 KB | 2,431 | 2 | 8 | 0 | 7 | **Monolith (>=50KB)** |
| 3 | `src/morphomesh/inference_adapter.py` | 98,993 | 96.67 KB | 2,357 | 8 | 1 | 11 | 22 | **Monolith (>=50KB)** |
| 4 | `src/morphomesh/visual_critic.py` | 95,343 | 93.11 KB | 2,295 | 5 | 32 | 0 | 8 | **Monolith (>=50KB)** |
| 5 | `src/morphomesh/wardrobe.py` | 90,136 | 88.02 KB | 2,182 | 1 | 21 | 1 | 12 | **Monolith (>=50KB)** |
| 6 | `src/morphomesh/human_rigging.py` | 84,527 | 82.55 KB | 1,835 | 4 | 9 | 1 | 9 | **Monolith (>=50KB)** |
| 7 | `src/morphomesh/connectors/meshy_connector.py` | 76,049 | 74.27 KB | 1,580 | 8 | 0 | 2 | 2 | **Monolith (>=50KB)** |
| 8 | `src/morphomesh/human_generator.py` | 75,324 | 73.56 KB | 1,695 | 2 | 13 | 1 | 19 | **Monolith (>=50KB)** |
| 9 | `src/morphomesh/server.py` | 73,670 | 71.94 KB | 1,689 | 0 | 24 | 1 | 17 | **Monolith (>=50KB)** |
| 10 | `src/morphomesh/models.py` | 65,310 | 63.78 KB | 1,232 | 62 | 0 | 10 | 29 | **Monolith (>=50KB)** |
| 11 | `src/morphomesh/human_grooming.py` | 51,992 | 50.77 KB | 1,188 | 3 | 9 | 1 | 5 | **Monolith (>=50KB)** |
| 12 | `src/morphomesh/camera_rig.py` | 47,229 | 46.12 KB | 1,166 | 0 | 9 | 0 | 10 | *Large (>=800L)* |
| 13 | `src/morphomesh/connectors/tripo_connector.py` | 47,193 | 46.09 KB | 1,110 | 4 | 2 | 2 | 2 | *Large (>=800L)* |
| 14 | `src/morphomesh/connectors/gemini_image_connector.py` | 40,147 | 39.21 KB | 909 | 4 | 0 | 1 | 0 | *Large (>=800L)* |
| 15 | `src/morphomesh/human_materials.py` | 37,227 | 36.35 KB | 920 | 2 | 5 | 1 | 4 | *Large (>=800L)* |
| 16 | `src/morphomesh/armor.py` | 37,093 | 36.22 KB | 868 | 2 | 1 | 0 | 4 | *Large (>=800L)* |
| 17 | `src/morphomesh/export_manager.py` | 34,642 | 33.83 KB | 780 | 1 | 6 | 0 | 0 | Medium (20-50KB) |
| 18 | `src/morphomesh/grooming.py` | 33,494 | 32.71 KB | 870 | 2 | 5 | 0 | 3 | *Large (>=800L)* |
| 19 | `src/morphomesh/creature_generator.py` | 26,717 | 26.09 KB | 651 | 3 | 4 | 0 | 9 | Medium (20-50KB) |
| 20 | `src/morphomesh/anatomy/landmarks.py` | 24,330 | 23.76 KB | 552 | 3 | 4 | 1 | 1 | Medium (20-50KB) |
| 21 | `src/morphomesh/anatomy/skinning.py` | 21,196 | 20.70 KB | 557 | 2 | 6 | 1 | 2 | Medium (20-50KB) |
| 22 | `src/morphomesh/connectors/animals3d_connector.py` | 21,132 | 20.64 KB | 503 | 6 | 1 | 1 | 1 | Medium (20-50KB) |
| 23 | `src/morphomesh/connectors/registry.py` | 19,654 | 19.19 KB | 501 | 2 | 1 | 1 | 0 | Small-Med (5-20KB) |
| 24 | `src/morphomesh/materials.py` | 18,310 | 17.88 KB | 467 | 2 | 2 | 0 | 3 | Small-Med (5-20KB) |
| 25 | `src/morphomesh/connectors/trellis_connector.py` | 16,585 | 16.20 KB | 407 | 4 | 0 | 1 | 0 | Small-Med (5-20KB) |
| 26 | `src/morphomesh/connectors/anycreature_connector.py` | 14,172 | 13.84 KB | 354 | 7 | 0 | 1 | 0 | Small-Med (5-20KB) |
| 27 | `src/morphomesh/anatomy/bone_roll.py` | 14,152 | 13.82 KB | 384 | 2 | 5 | 1 | 1 | Small-Med (5-20KB) |
| 28 | `src/morphomesh/anatomy/stance.py` | 13,306 | 12.99 KB | 344 | 2 | 3 | 2 | 1 | Small-Med (5-20KB) |
| 29 | `src/morphomesh/connectors/hunyuan_connector.py` | 12,979 | 12.67 KB | 335 | 4 | 0 | 1 | 0 | Small-Med (5-20KB) |
| 30 | `src/morphomesh/connectors/meshanything_connector.py` | 11,335 | 11.07 KB | 298 | 4 | 0 | 1 | 0 | Small-Med (5-20KB) |
| 31 | `src/morphomesh/connectors/base.py` | 7,240 | 7.07 KB | 211 | 6 | 0 | 10 | 0 | Small-Med (5-20KB) |
| 32 | `src/morphomesh/main.py` | 4,334 | 4.23 KB | 133 | 0 | 1 | 0 | 0 | Small (<5KB) |
| 33 | `src/morphomesh/connectors/__init__.py` | 3,865 | 3.77 KB | 160 | 0 | 0 | 0 | 6 | Small (<5KB) |
| 34 | `src/morphomesh/__init__.py` | 3,718 | 3.63 KB | 139 | 0 | 0 | 1 | 71 | Small (<5KB) |
| 35 | `src/morphomesh/anatomy/__init__.py` | 1,337 | 1.31 KB | 52 | 0 | 0 | 1 | 3 | Small (<5KB) |

---

## 2. In-Depth Survey of Monolithic Modules (>= 50 KB)

### 2.1 `src/morphomesh/blender_bridge.py`
- **File Size**: 151.5 KB (155,140 bytes)
- **Line Count**: 3,454 lines
- **Role**: Blender Socket & Subprocess Bridge — Dual-mode interactive TCP socket and headless subprocess bridge connecting Python/MCP to Blender 4.5+ / 5.2.1 LTS.
- **Coupling**: Imported by **2** internal modules and **22** test/addon files
- **Classes (4)**:
  - `class SecurityException(MorphoMeshException)`: lines 85-93 (9 lines, 1 methods)
  - `class BlenderExecutionError(MorphoMeshException)`: lines 96-104 (9 lines, 1 methods)
  - `class BpyCodeValidator(ast.NodeVisitor)`: lines 107-265 (159 lines, 6 methods)
  - `class BlenderBridge()`: lines 272-3453 (3182 lines, 31 methods)
- **Top-Level Functions (0)**:
- **Embedded Python Script Templates (>10 lines)**: 8 detected
  - Lines 967-2554 (1588 lines): `import bpy import json import os import math import mathutils import uuid import...`
  - Lines 967-2554 (1588 lines): `")  def ensure_auto_camera(scene=None):     if scene is None:         scene = bp...`
  - Lines 967-2554 (1588 lines): `arm_data = bpy.data.armatures.new(name=f"Armature_{creature_type.title()}")     ...`
- **Architectural Smell / SRP Violation**:
  > Mixes low-level socket NDJSON transport, AST code safety validation, headless process invocation, sentinel stdout parsing, and 1,800+ lines of domain-specific Blender Python script generation (scenes, meshes, armatures, human body, rigging, wardrobe, grooming, materials).
- **Proposed Modular Decomposition (`src/morphomesh/bridge/`)**:
  - `security.py`: BpyCodeValidator (AST visitor), forbidden AST calls, syntax and security checks, SecurityException.
  - `exceptions.py`: SecurityException, BlenderExecutionError (subclassed from MorphoMeshException).
  - `socket_client.py`: Low-level TCP socket connection, NDJSON framing, buffer chunk reading, socket timeout/retry logic.
  - `process_runner.py`: Subprocess execution for headless Blender (`blender -b`), tempfile creation, sentinel extraction.
  - `script_generator.py`: Modular builders for Blender execution scripts (sub-divided into scene_scripts, mesh_scripts, camera_scripts, human_scripts).
  - `client.py`: Unified BlenderBridge class maintaining all 31 public methods, coordinating transport, validation, and script generation.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/blender_bridge.py` acts as a facade re-exporting `BlenderBridge`, `SecurityException`, `BlenderExecutionError`, and `BpyCodeValidator` via `__all__`.

### 2.2 `src/morphomesh/character_assembler.py`
- **File Size**: 105.14 KB (107,667 bytes)
- **Line Count**: 2,431 lines
- **Role**: Digital Human Master Character Assembler — Authoritative Master Assembler for the Yu Nian An digital human character scene, integrating geometry, metarig, wardrobe, grooming, lighting, and cameras.
- **Coupling**: Imported by **0** internal modules and **7** test/addon files
- **Classes (2)**:
  - `class MasterAssemblyConfig()`: lines 205-254 (50 lines, 1 methods)
  - `class YuNianAnAssembler()`: lines 1505-1874 (370 lines, 14 methods)
- **Top-Level Functions (8)**:
  - `def _get_uv_unwrapping_script_snippet()`: lines 258-453 (196 lines)
  - `def assign_texture_atlas_uvs()`: lines 456-462 (7 lines)
  - `def get_master_assembly_script()`: lines 469-1498 (1030 lines)
  - `def assemble_master_character()`: lines 1885-1922 (38 lines)
  - `def _resolve_blender_binary()`: lines 1929-1950 (22 lines)
  - `def get_export_script()`: lines 1953-2066 (114 lines)
  - `def generate_yu_nian_an_pbr_textures()`: lines 2069-2341 (273 lines)
  - `def export_production_assets()`: lines 2344-2430 (87 lines)
- **Embedded Python Script Templates (>10 lines)**: 8 detected
  - Lines 551-1497 (947 lines): `# ==============================================================================...`
  - Lines 551-1497 (947 lines): `body_obj = bpy.data.objects.get("...`
  - Lines 551-1497 (947 lines): `# Ensure all created materials have fake user so Blender never purges them all_m...`
- **Architectural Smell / SRP Violation**:
  > Combines scene hierarchy constants, 4K procedural texture map generation (PIL/NumPy baking), UV unwrapping script generation, 1,030-line embedded Blender master assembly script, YuNianAnAssembler scene coordinator, and binary export packaging (FBX, GLB, .blend).
- **Proposed Modular Decomposition (`src/morphomesh/assembler/`)**:
  - `config.py`: MasterAssemblyConfig, ALL_SEVEN_COLLECTIONS, ROOT_COLLECTION_NAME, collection hierarchy constants.
  - `texture_baker.py`: generate_yu_nian_an_pbr_textures (procedural 4K Albedo, Normal, Roughness, Metallic, SSS texture maps via PIL & NumPy).
  - `uv_unwrapper.py`: _get_uv_unwrapping_script_snippet, assign_texture_atlas_uvs.
  - `scene_assembly.py`: get_master_assembly_script (modular script builder assembling collections, materials, metarig, wardrobe, hair).
  - `master_assembler.py`: YuNianAnAssembler class (manifest generators, assemble, scene integrity verification).
  - `export.py`: get_export_script, export_production_assets, assemble_master_character packaging routines.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/character_assembler.py` acts as a facade re-exporting `YuNianAnAssembler`, `MasterAssemblyConfig`, `assemble_master_character`, etc.

### 2.3 `src/morphomesh/inference_adapter.py`
- **File Size**: 96.67 KB (98,993 bytes)
- **Line Count**: 2,357 lines
- **Role**: Generative AI Inference Adapter & Mesh Container — Multi-backend adapter routing requests to remote GPU endpoints (Replicate, HuggingFace) and offline mock generators.
- **Coupling**: Imported by **11** internal modules and **22** test/addon files
- **Classes (8)**:
  - `class BaseInferenceAdapter(ABC)`: lines 58-93 (36 lines, 5 methods)
  - `class MeshGeometry()`: lines 101-1208 (1108 lines, 17 methods)
  - `class EnhancedCreate3DAssetOutput(Create3DAssetOutput)`: lines 1282-1289 (8 lines, 0 methods)
  - `class MockInferenceAdapter(BaseInferenceAdapter)`: lines 1296-2210 (915 lines, 20 methods)
  - `class CircuitBreaker()`: lines 2217-2245 (29 lines, 4 methods)
  - `class ReplicateInferenceAdapter(BaseInferenceAdapter)`: lines 2248-2278 (31 lines, 3 methods)
  - `class HuggingFaceInferenceAdapter(BaseInferenceAdapter)`: lines 2281-2305 (25 lines, 3 methods)
  - `class InferenceAdapter(MockInferenceAdapter)`: lines 2312-2320 (9 lines, 0 methods)
- **Top-Level Functions (1)**:
  - `def get_inference_adapter()`: lines 2323-2333 (11 lines)
- **Embedded Python Script Templates (>10 lines)**: 2 detected
  - Lines 1-13 (13 lines): `MorphoMesh: AI Inference Adapter Module.  Provides an extensible abstraction for...`
  - Lines 1504-1514 (11 lines): `Reconstruct 3D textured mesh with multi-backend connector routing.              ...`
- **Architectural Smell / SRP Violation**:
  > Major SRP violation: Contains 1,108 lines of pure-python procedural 3D modeling (`MeshGeometry` with cylinders, ellipsoids, plantigrade paws, curved claws, articulated heads, and binary glTF 2.0 exporter) embedded inside an AI inference dispatcher, alongside 915 lines of MockInferenceAdapter.
- **Proposed Modular Decomposition (`src/morphomesh/geometry/ and src/morphomesh/inference/`)**:
  - `src/morphomesh/geometry/mesh.py`: MeshGeometry container: vertices, normals, UVs, vertex groups, quad/triangle primitives, bounding box, binary glTF 2.0 exporter, OBJ exporter.
  - `src/morphomesh/geometry/creature_primitives.py`: Anatomical primitive generators: add_curved_claw, add_plantigrade_paw, add_articulated_head, add_anatomical_torso.
  - `src/morphomesh/inference/base.py`: BaseInferenceAdapter, EnhancedCreate3DAssetOutput.
  - `src/morphomesh/inference/circuit_breaker.py`: CircuitBreaker pattern implementation for remote API resilience.
  - `src/morphomesh/inference/mock_adapter.py`: MockInferenceAdapter (offline concept synthesis, turnaround sheets, fallback creature generators).
  - `src/morphomesh/inference/remote_adapters.py`: ReplicateInferenceAdapter, HuggingFaceInferenceAdapter.
  - `src/morphomesh/inference/factory.py`: get_inference_adapter(mode) factory function.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/inference_adapter.py` re-exports `MeshGeometry` from `geometry.mesh` and all inference classes from `inference/`.

### 2.4 `src/morphomesh/visual_critic.py`
- **File Size**: 93.11 KB (95,343 bytes)
- **Line Count**: 2,295 lines
- **Role**: Closed-Loop Visual QA & Defect Inspection Critic — Diagnostic quality critic evaluating mesh penetration, body proportions, joint skinning pinching, and grooming intersections.
- **Coupling**: Imported by **0** internal modules and **8** test/addon files
- **Classes (5)**:
  - `class PurePythonAABB()`: lines 424-461 (38 lines, 3 methods)
  - `class PurePythonBVHNode()`: lines 464-470 (7 lines, 1 methods)
  - `class PurePythonBVHTree()`: lines 473-721 (249 lines, 7 methods)
  - `class AnthropometricMetrics()`: lines 1365-1378 (14 lines, 0 methods)
  - `class JointDeformationMetrics()`: lines 1547-1556 (10 lines, 0 methods)
- **Top-Level Functions (32)**:
  - `def _cross_product()`: lines 66-71 (6 lines)
  - `def _dot_product()`: lines 74-75 (2 lines)
  - `def _sub_vec()`: lines 78-79 (2 lines)
  - `def _add_vec()`: lines 82-83 (2 lines)
  - `def _scale_vec()`: lines 86-87 (2 lines)
  - `def _norm_vec()`: lines 90-94 (5 lines)
  - `def _vec_len()`: lines 97-98 (2 lines)
  - `def point_to_triangle_distance_eberly()`: lines 101-197 (97 lines)
  - *(... and 24 more functions)*
- **Embedded Python Script Templates (>10 lines)**: 1 detected
  - Lines 1-12 (12 lines): `MorphoMesh: Closed-Loop Visual Quality Critique Engine.  Milestone 3 Core Module...`
- **Architectural Smell / SRP Violation**:
  > Combines pure-python 3D scalar vector math, complex computational geometry (Eberly point-triangle distance, Möller ray-triangle intersection), a 250-line pure-Python BVH spatial index (`PurePythonBVHTree`), 4 distinct defect diagnostics, synthetic benchmark test fixtures, and report orchestration.
- **Proposed Modular Decomposition (`src/morphomesh/critic/`)**:
  - `math_utils.py`: Vector algebra, Eberly point-to-triangle distance, Möller-Trumbore ray-triangle intersection, 2D/3D triangle-triangle intersection.
  - `bvh.py`: PurePythonAABB, PurePythonBVHNode, PurePythonBVHTree, and get_bvh_tree (with Blender mathutils.bvhtree fallback).
  - `penetration.py`: evaluate_mesh_penetration, evaluate_hair_grooming_intersections, _find_garment_boundary_edges.
  - `proportions.py`: AnthropometricMetrics, evaluate_body_proportions.
  - `deformation.py`: JointDeformationMetrics, compute_mesh_signed_volume, compute_bounding_slice_volume, compute_mesh_dihedral_creases, evaluate_rig_skinning_deformation, evaluate_rig_skinning_pinch.
  - `fixtures.py`: create_penetration_fixture, create_proportion_fixture, create_skinning_fixture, create_grooming_fixture, run_defect_detection_benchmark.
  - `orchestrator.py`: run_visual_critique, critique_visual_quality report synthesis.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/visual_critic.py` acts as a facade re-exporting all functions, classes, and models.

### 2.5 `src/morphomesh/wardrobe.py`
- **File Size**: 88.02 KB (90,136 bytes)
- **Line Count**: 2,182 lines
- **Role**: Procedural Wardrobe & Magic Props Synthesizer — Procedural generator for digital human garments (dress bodice, waist sash, organic skirt, flat strappy sandals) and magical props (marionette threads, luminous butterflies).
- **Coupling**: Imported by **1** internal modules and **12** test/addon files
- **Classes (1)**:
  - `class WardrobeConfig()`: lines 84-106 (23 lines, 1 methods)
- **Top-Level Functions (21)**:
  - `def resolve_finger_def_bone_name()`: lines 65-67 (3 lines)
  - `def compute_dress_waist_radii()`: lines 113-134 (22 lines)
  - `def assign_dress_pin_weights()`: lines 137-165 (29 lines)
  - `def assign_bodice_skin_weights()`: lines 168-220 (53 lines)
  - `def assign_skirt_skin_weights()`: lines 223-283 (61 lines)
  - `def assign_sash_skin_weights()`: lines 286-353 (68 lines)
  - `def compute_wardrobe_skin_weights()`: lines 356-375 (20 lines)
  - `def generate_dress_bodice()`: lines 378-621 (244 lines)
  - *(... and 13 more functions)*
- **Embedded Python Script Templates (>10 lines)**: 6 detected
  - Lines 1906-2108 (203 lines): `""" Blender 4.5+ Standalone Wardrobe & Magic Props Generation Script. Yu Nian An...`
  - Lines 1906-2108 (203 lines): `''')  body_obj = bpy.data.objects.get(TARGET_OBJ_NAME) armature_obj = bpy.data.o...`
  - Lines 1906-2108 (203 lines): `for b_i in range(b_count):         bf_obj = create_mesh_obj(f"Prop_Butterfly_{b_...`
- **Architectural Smell / SRP Violation**:
  > Massive monolithic module combining vertex skin weighting heuristics, procedural cloth geometry modeling (bodice, sash, organic skirt, sandals), catenary physics strings modeling, butterfly flocking positioning, and embedded Blender script generation.
- **Proposed Modular Decomposition (`src/morphomesh/wardrobe/`)**:
  - `config.py`: WardrobeConfig, bone name aliases (resolve_finger_def_bone_name).
  - `skinning.py`: Skin weighting heuristics: assign_dress_pin_weights, assign_bodice_skin_weights, assign_skirt_skin_weights, assign_sash_skin_weights, compute_wardrobe_skin_weights.
  - `garments/bodice.py`: generate_dress_bodice (sweetheart neckline, teardrop bust, spaghetti straps).
  - `garments/sash.py`: generate_dress_waist_sash, generate_waist_sash_and_bow (barrel cuff knot, hollow loops, cascading ribbons).
  - `garments/skirt.py`: generate_dress_organic_skirt (harmonic drapery, gravity folds), generate_dress_pleated_skirt, generate_organic_dress.
  - `garments/sandals.py`: generate_flat_strappy_sandals (footbed, instep strap, ankle wrap, toe exposure).
  - `props/strings.py`: generate_catenary_magic_strings (catenary sag curvature, finger-snapped marionette cords).
  - `props/butterflies.py`: generate_swallowtail_quad_butterfly, get_butterfly_vortex_positions, get_butterfly_flutter_positions.
  - `suite.py`: generate_yu_nian_an_wardrobe, get_wardrobe_script, dress_human coordinator.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/wardrobe.py` acts as a facade re-exporting all functions and `WardrobeConfig`.

### 2.6 `src/morphomesh/human_rigging.py`
- **File Size**: 82.55 KB (84,527 bytes)
- **Line Count**: 1,835 lines
- **Role**: Digital Human Rigify Metarig & ARKit 52 Synthesizer — Biomechanical rigging engine generating 163 DEF bones Rigify Human metarig, landmark pivot alignments, anti-pinch skin weights, and 52 ARKit FACS facial blendshapes.
- **Coupling**: Imported by **1** internal modules and **9** test/addon files
- **Classes (4)**:
  - `class HumanRigConfig(BaseModel)`: lines 250-263 (14 lines, 0 methods)
  - `class BoneDefinition()`: lines 267-291 (25 lines, 2 methods)
  - `class MetarigStructure()`: lines 295-335 (41 lines, 4 methods)
  - `class SkinWeightMap()`: lines 340-385 (46 lines, 5 methods)
- **Top-Level Functions (9)**:
  - `def _point_to_segment_distance()`: lines 51-63 (13 lines)
  - `def _get_canonical_finger_map()`: lines 69-98 (30 lines)
  - `def get_default_human_landmarks()`: lines 392-434 (43 lines)
  - `def generate_rigify_human_metarig()`: lines 437-794 (358 lines)
  - `def align_rigify_metarig_pivots()`: lines 797-917 (121 lines)
  - `def calculate_anti_pinch_weights()`: lines 924-1306 (383 lines)
  - `def generate_arkit_52_blendshapes()`: lines 1313-1522 (210 lines)
  - `def get_rigging_script()`: lines 1529-1780 (252 lines)
  - *(... and 1 more functions)*
- **Embedded Python Script Templates (>10 lines)**: 7 detected
  - Lines 1588-1780 (193 lines): `import bpy import math import mathutils import json import os import tempfile im...`
  - Lines 1588-1780 (193 lines): `# Locate target character mesh obj = bpy.data.objects.get(mesh_name) if not obj:...`
  - Lines 1588-1780 (193 lines): `) for b_name, b_info in metarig_bones.items():     b = eb.new(b_name)     b.head...`
- **Architectural Smell / SRP Violation**:
  > Combines metarig data models, 358 lines of bone coordinate math, joint pivot alignment, 383 lines of anti-pinch skin weight calculations, 210 lines of ARKit facial blendshapes delta synthesis, and 252 lines of Blender rigging script generation.
- **Proposed Modular Decomposition (`src/morphomesh/rigging/`)**:
  - `config.py`: HumanRigConfig, ALL_163_DEF_BONES, BODY_DEF_BONES, FACIAL_DEF_BONES, canonical finger mapping.
  - `structure.py`: BoneDefinition, MetarigStructure (pre-bends check), SkinWeightMap (normalization).
  - `landmarks.py`: get_default_human_landmarks, _point_to_segment_distance.
  - `metarig.py`: generate_rigify_human_metarig, align_rigify_metarig_pivots.
  - `weights.py`: calculate_anti_pinch_weights (volumetric skinning heuristics for 163 DEF bones).
  - `blendshapes.py`: generate_arkit_52_blendshapes (52 ARKit FACS morph targets with delta offsets).
  - `runner.py`: get_rigging_script, auto_rig_human.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/human_rigging.py` acts as a facade re-exporting all symbols and constants.

### 2.7 `src/morphomesh/connectors/meshy_connector.py`
- **File Size**: 74.27 KB (76,049 bytes)
- **Line Count**: 1,580 lines
- **Role**: Meshy.ai SOTA Generative 3D Connector — Production connector integrating Meshy API v1/v2 for text-to-3d, image-to-3d, multi-view generation, autorigging, and animation retargeting.
- **Coupling**: Imported by **2** internal modules and **2** test/addon files
- **Classes (8)**:
  - `class MeshyConfig(BaseModel)`: lines 87-111 (25 lines, 1 methods)
  - `class MeshyInput(BaseModel)`: lines 114-179 (66 lines, 2 methods)
  - `class MeshyOutput(BaseModel)`: lines 182-201 (20 lines, 0 methods)
  - `class MeshyRiggingInput(BaseModel)`: lines 204-213 (10 lines, 0 methods)
  - `class MeshyRiggingOutput(BaseModel)`: lines 216-229 (14 lines, 0 methods)
  - `class MeshyAnimationInput(BaseModel)`: lines 232-241 (10 lines, 0 methods)
  - `class MeshyAnimationOutput(BaseModel)`: lines 244-259 (16 lines, 0 methods)
  - `class MeshyConnector(BaseConnector)`: lines 309-1580 (1272 lines, 22 methods)
- **Top-Level Functions (0)**:
- **Embedded Python Script Templates (>10 lines)**: 2 detected
  - Lines 1-17 (17 lines): `MorphoMesh: Meshy AI 3D Foundation Model Connector (Phase 2).  Integrates the Me...`
  - Lines 469-481 (13 lines): `Execute Meshy AI 3D asset generation workload.          Args:             reques...`
- **Architectural Smell / SRP Violation**:
  > Massive 1,580-line connector mixing Pydantic configuration schemas, asynchronous HTTP polling, REST API execution, offline preview mock generation, Meshy autorigging API, and Meshy animation library retargeting.
- **Proposed Modular Decomposition (`src/morphomesh/connectors/meshy/`)**:
  - `models.py`: MeshyConfig, MeshyInput, MeshyOutput, MeshyRiggingInput/Output, MeshyAnimationInput/Output.
  - `client.py`: REST API client: HTTP communication, authentication, task polling with exponential backoff, asset downloading.
  - `mock.py`: _execute_mock procedural preview generator for zero-network testing.
  - `services.py`: Specialized rigging and animation retargeting methods (rig_asset, animate_asset).
  - `connector.py`: MeshyConnector orchestrator implementing BaseConnector lifecycle.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/connectors/meshy_connector.py` acts as a facade re-exporting `MeshyConnector`, `MeshyConfig`, etc.

### 2.8 `src/morphomesh/human_generator.py`
- **File Size**: 73.56 KB (75,324 bytes)
- **Line Count**: 1,695 lines
- **Role**: Anatomical Human Base Mold & Morphology Synthesizer — Digital human base mold synthesizer morphing MakeHuman CC0 template geometry into anatomically authentic human forms.
- **Coupling**: Imported by **1** internal modules and **19** test/addon files
- **Classes (2)**:
  - `class HumanMeshResult()`: lines 89-106 (18 lines, 0 methods)
  - `class HumanAnatomyGenerator()`: lines 773-1156 (384 lines, 3 methods)
- **Top-Level Functions (13)**:
  - `def compute_quad_metrics()`: lines 113-138 (26 lines)
  - `def add_quad_cap()`: lines 141-158 (18 lines)
  - `def add_quad_ellipsoid()`: lines 161-221 (61 lines)
  - `def _get_templates_dir()`: lines 238-250 (13 lines)
  - `def load_anatomical_base_mold()`: lines 253-354 (102 lines)
  - `def extract_makehuman_joint_landmarks()`: lines 357-415 (59 lines)
  - `def enforce_quad_closure()`: lines 418-438 (21 lines)
  - `def compute_relaxed_vertex_normals()`: lines 441-498 (58 lines)
  - *(... and 5 more functions)*
- **Embedded Python Script Templates (>10 lines)**: 3 detected
  - Lines 1235-1695 (461 lines): `import bpy import bmesh import math import mathutils  mesh_name =...`
  - Lines 1235-1695 (461 lines): `scale = target_height / 1.65 s = scale  # Parametric scaling factors k_chest = c...`
  - Lines 1-12 (12 lines): `MorphoMesh: Anthropometric Procedural Human Generator Module.  Synthesizes high-...`
- **Architectural Smell / SRP Violation**:
  > Combines OBJ template parsing, landmark extraction, quad topology closure and normal relaxation algorithms, 32 standardized vertex group assignments, parametric morphological body deformation, and a 490-line embedded Blender script generator.
- **Proposed Modular Decomposition (`src/morphomesh/human/`)**:
  - `base_mold.py`: load_anatomical_base_mold, extract_makehuman_joint_landmarks, _get_templates_dir.
  - `vertex_groups.py`: compute_standardized_vertex_groups, STANDARDIZED_HUMAN_VERTEX_GROUPS constants.
  - `quad_topology.py`: compute_quad_metrics, add_quad_cap, add_quad_ellipsoid, enforce_quad_closure, compute_relaxed_vertex_normals.
  - `morphology.py`: HumanAnatomyGenerator (bust teardrop profile, gluteal curvature, lumbar lordosis, limb proportions).
  - `generator.py`: resolve_human_anatomy_config, generate_human_base_mesh, generate_human_body, get_human_generation_script.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/human_generator.py` acts as a facade re-exporting all classes, functions, and constants.

### 2.9 `src/morphomesh/server.py`
- **File Size**: 71.94 KB (73,670 bytes)
- **Line Count**: 1,689 lines
- **Role**: FastMCP Server & Multi-Tool Registry — Model Context Protocol (FastMCP) server exposing 17 specialized 3D tools for Antigravity and external LLM clients.
- **Coupling**: Imported by **1** internal modules and **17** test/addon files
- **Classes (0)**:
- **Top-Level Functions (24)**:
  - `def morphomesh_generate_concept()`: lines 112-164 (53 lines)
  - `def morphomesh_create_3d_asset()`: lines 172-232 (61 lines)
  - `def morphomesh_optimize_topology()`: lines 240-323 (84 lines)
  - `def morphomesh_auto_rig()`: lines 331-497 (167 lines)
  - `def morphomesh_animate_asset()`: lines 505-573 (69 lines)
  - `def morphomesh_list_animations()`: lines 581-613 (33 lines)
  - `def morphomesh_blender_execute()`: lines 622-658 (37 lines)
  - `def morphomesh_get_scene_status()`: lines 666-697 (32 lines)
  - *(... and 16 more functions)*
- **Embedded Python Script Templates (>10 lines)**: 3 detected
  - Lines 187-197 (11 lines): `Stage 2: Reconstruct a textured 3D mesh with PBR maps from a 2D concept image or...`
  - Lines 1179-1189 (11 lines): `Stage 6 Master Assembly: Orchestrate complete digital human scene in Blender 4.5...`
  - Lines 1529-1539 (11 lines): `Stage 8 Closed-Loop Quality Assurance: Automated visual defect critique.      Or...`
- **Architectural Smell / SRP Violation**:
  > All 17 MCP tools are implemented in this single file, spanning creature generation, digital human pipeline, wardrobe, production export, camera rig setup, viewport capture, and visual critique, mixed with environment-gated filtering logic.
- **Proposed Modular Decomposition (`src/morphomesh/tools/ and server.py`)**:
  - `src/morphomesh/tools/base.py`: Context logging helpers (_safe_ctx_info, _safe_ctx_progress), common error decorators, exception translators.
  - `src/morphomesh/tools/creature.py`: 7 creature pipeline tools (concept, create_3d_asset, optimize_topology, auto_rig, animate_asset, list_animations, blender_execute, scene_status, render_preview).
  - `src/morphomesh/tools/human.py`: 7 digital human & wardrobe tools (create_human_asset, auto_rig_human, setup_human_materials, groom_human, dress_human, assemble_master_character, export_production_character).
  - `src/morphomesh/tools/inspection.py`: 3 camera and visual QA tools (setup_inspector_camera_rig, capture_viewport, critique_visual_quality).
  - `src/morphomesh/server.py`: FastMCP server initialization, tool registration loop, environment variable gating (MORPHOMESH_INCLUDE_ALL_TOOLS), and entry point.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/server.py` exposes `mcp` instance and all tool functions with identical names, docstrings, and parameter signatures.

### 2.10 `src/morphomesh/models.py`
- **File Size**: 63.78 KB (65,310 bytes)
- **Line Count**: 1,232 lines
- **Role**: Unified Domain Schemas, Enums & Models — Pydantic v2 data models, enums, error codes, and exception types for all subsystems.
- **Coupling**: Imported by **10** internal modules and **29** test/addon files
- **Classes (62)**:
  - `class MorphoMeshException(Exception)`: lines 55-67 (13 lines, 1 methods)
  - `class CreatureType(str, Enum)`: lines 74-86 (13 lines, 0 methods)
  - `class ViewMode(str, Enum)`: lines 89-97 (9 lines, 0 methods)
  - `class Pose(str, Enum)`: lines 100-104 (5 lines, 0 methods)
  - `class Style(str, Enum)`: lines 107-113 (7 lines, 0 methods)
  - `class QualityTier(str, Enum)`: lines 116-120 (5 lines, 0 methods)
  - `class TopologyType(str, Enum)`: lines 123-127 (5 lines, 0 methods)
  - `class RetopoMethod(str, Enum)`: lines 130-135 (6 lines, 0 methods)
  - `class RigType(str, Enum)`: lines 138-142 (5 lines, 0 methods)
  - `class SkinningMethod(str, Enum)`: lines 145-148 (4 lines, 0 methods)
  - `class RenderEngine(str, Enum)`: lines 151-155 (5 lines, 0 methods)
  - `class LightingPreset(str, Enum)`: lines 158-163 (6 lines, 0 methods)
  - `class BoundingBox(BaseModel)`: lines 170-174 (5 lines, 0 methods)
  - `class SceneObjectInfo(BaseModel)`: lines 177-190 (14 lines, 0 methods)
  - `class GenerateConceptInput(BaseModel)`: lines 197-217 (21 lines, 1 methods)
  - `class GenerateConceptOutput(BaseModel)`: lines 220-232 (13 lines, 0 methods)
  - `class Create3DAssetInput(BaseModel)`: lines 239-265 (27 lines, 1 methods)
  - `class Create3DAssetOutput(BaseModel)`: lines 268-279 (12 lines, 0 methods)
  - `class OptimizeTopologyInput(BaseModel)`: lines 286-295 (10 lines, 0 methods)
  - `class OptimizeTopologyOutput(BaseModel)`: lines 298-309 (12 lines, 0 methods)
  - `class AutoRigInput(BaseModel)`: lines 316-328 (13 lines, 0 methods)
  - `class AutoRigOutput(BaseModel)`: lines 331-346 (16 lines, 0 methods)
  - `class BlenderExecuteInput(BaseModel)`: lines 353-360 (8 lines, 0 methods)
  - `class BlenderExecuteOutput(BaseModel)`: lines 363-370 (8 lines, 0 methods)
  - `class SceneStatusInput(BaseModel)`: lines 377-384 (8 lines, 0 methods)
  - `class SceneStatusOutput(BaseModel)`: lines 387-398 (12 lines, 0 methods)
  - `class RenderPreviewInput(BaseModel)`: lines 405-425 (21 lines, 1 methods)
  - `class RenderPreviewOutput(BaseModel)`: lines 428-438 (11 lines, 0 methods)
  - `class HumanAnatomyConfig(BaseModel)`: lines 445-459 (15 lines, 0 methods)
  - `class CreateHumanAssetInput(BaseModel)`: lines 463-493 (31 lines, 1 methods)
  - `class HumanAssetResult(BaseModel)`: lines 496-514 (19 lines, 0 methods)
  - `class AutoRigHumanInput(BaseModel)`: lines 521-533 (13 lines, 0 methods)
  - `class HumanRigResult(BaseModel)`: lines 536-549 (14 lines, 0 methods)
  - `class SetupHumanMaterialsInput(BaseModel)`: lines 556-568 (13 lines, 0 methods)
  - `class HumanMaterialResult(BaseModel)`: lines 571-582 (12 lines, 0 methods)
  - `class GroomHumanInput(BaseModel)`: lines 589-603 (15 lines, 0 methods)
  - `class HumanGroomingResult(BaseModel)`: lines 606-616 (11 lines, 0 methods)
  - `class DressHumanInput(BaseModel)`: lines 623-637 (15 lines, 0 methods)
  - `class HumanWardrobeResult(BaseModel)`: lines 640-650 (11 lines, 0 methods)
  - `class InspectorViewpoint(str, Enum)`: lines 660-676 (17 lines, 0 methods)
  - `class AnthropometricPreset(str, Enum)`: lines 679-685 (7 lines, 0 methods)
  - `class DiagnosticShadingMode(str, Enum)`: lines 699-704 (6 lines, 0 methods)
  - `class DiagnosticColorType(str, Enum)`: lines 707-712 (6 lines, 0 methods)
  - `class BoundingBox3D(BaseModel)`: lines 715-721 (7 lines, 0 methods)
  - `class SetupInspectorCameraInput(BaseModel)`: lines 724-745 (22 lines, 1 methods)
  - `class SetupInspectorCameraOutput(BaseModel)`: lines 748-761 (14 lines, 0 methods)
  - `class CaptureViewportInput(BaseModel)`: lines 764-797 (34 lines, 2 methods)
  - `class CaptureViewportOutput(BaseModel)`: lines 800-812 (13 lines, 0 methods)
  - `class MultiAngleCaptureFrame(BaseModel)`: lines 815-831 (17 lines, 0 methods)
  - `class CaptureMultiAngleInspectionInput(BaseModel)`: lines 834-851 (18 lines, 0 methods)
  - `class CaptureMultiAngleInspectionOutput(BaseModel)`: lines 854-861 (8 lines, 0 methods)
  - `class DefectSeverity(str, Enum)`: lines 868-892 (25 lines, 1 methods)
  - `class DefectCategory(str, Enum)`: lines 895-927 (33 lines, 1 methods)
  - `class ActionableRecommendation(BaseModel)`: lines 930-973 (44 lines, 3 methods)
  - `class DefectItem(BaseModel)`: lines 976-1071 (96 lines, 3 methods)
  - `class VisualCritiqueInput(BaseModel)`: lines 1074-1130 (57 lines, 2 methods)
  - `class VisualCritiqueOutput(BaseModel)`: lines 1133-1163 (31 lines, 1 methods)
  - `class AnimationItem(BaseModel)`: lines 1170-1179 (10 lines, 0 methods)
  - `class ListAnimationsInput(BaseModel)`: lines 1182-1190 (9 lines, 0 methods)
  - `class ListAnimationsOutput(BaseModel)`: lines 1193-1199 (7 lines, 0 methods)
  - `class AnimateAssetInput(BaseModel)`: lines 1202-1213 (12 lines, 0 methods)
  - `class AnimateAssetOutput(BaseModel)`: lines 1216-1229 (14 lines, 0 methods)
- **Top-Level Functions (0)**:
- **Architectural Smell / SRP Violation**:
  > Crams 62 classes, 32 error constants, 17 enums, and complex validation/aliasing logic into 1,232 lines. Any change in any domain's schemas touches this single hub file.
- **Proposed Modular Decomposition (`src/morphomesh/models/`)**:
  - `errors.py`: All 32 ERR_* string constants and MorphoMeshException base class.
  - `enums.py`: Domain enums: CreatureType, ViewMode, Pose, Style, QualityTier, TopologyType, RetopoMethod, RigType, SkinningMethod, RenderEngine, LightingPreset, InspectorViewpoint, AnthropometricPreset, DiagnosticShadingMode, DiagnosticColorType, DefectSeverity, DefectCategory.
  - `geometry.py`: BoundingBox, BoundingBox3D, SceneObjectInfo.
  - `creature.py`: GenerateConceptInput/Output, Create3DAssetInput/Output, OptimizeTopologyInput/Output, AutoRigInput/Output, BlenderExecuteInput/Output, SceneStatusInput/Output, RenderPreviewInput/Output.
  - `human.py`: HumanAnatomyConfig, CreateHumanAssetInput, HumanAssetResult, AutoRigHumanInput, HumanRigResult, SetupHumanMaterialsInput, HumanMaterialResult, GroomHumanInput, HumanGroomingResult, DressHumanInput, HumanWardrobeResult.
  - `inspection.py`: SetupInspectorCameraInput/Output, CaptureViewportInput/Output, MultiAngleCaptureFrame, CaptureMultiAngleInspectionInput/Output.
  - `critique.py`: ActionableRecommendation, DefectItem, VisualCritiqueInput, VisualCritiqueOutput (with alias validators).
  - `animation.py`: AnimationItem, ListAnimationsInput/Output, AnimateAssetInput/Output.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/models/__init__.py` re-exports all 62 classes, error constants, and enums so `from morphomesh.models import X` remains 100% invariant.

### 2.11 `src/morphomesh/human_grooming.py`
- **File Size**: 50.77 KB (51,992 bytes)
- **Line Count**: 1,188 lines
- **Role**: Hime-Cut 6-Stratum Hair Grooming Synthesizer — Procedural hair grooming engine synthesizing 6-stratum hime cut hairstyles with Geometry Nodes and polygonal ribbon fallback.
- **Coupling**: Imported by **1** internal modules and **5** test/addon files
- **Classes (3)**:
  - `class HairLayerConfig()`: lines 50-68 (19 lines, 1 methods)
  - `class HairGroomConfig()`: lines 72-96 (25 lines, 2 methods)
  - `class HairCurveSpline()`: lines 251-257 (7 lines, 0 methods)
- **Top-Level Functions (9)**:
  - `def get_6_stratum_hime_cut_layers()`: lines 99-165 (67 lines)
  - `def get_default_hime_cut_layers()`: lines 168-243 (76 lines)
  - `def _calc_spline_length()`: lines 260-265 (6 lines)
  - `def generate_hime_cut_splines()`: lines 268-555 (288 lines)
  - `def generate_6_stratum_hime_cut_splines()`: lines 558-569 (12 lines)
  - `def convert_curves_to_ribbon_mesh()`: lines 572-653 (82 lines)
  - `def build_hair_geom_node_tree()`: lines 660-771 (112 lines)
  - `def get_grooming_script()`: lines 778-1131 (354 lines)
  - *(... and 1 more functions)*
- **Embedded Python Script Templates (>10 lines)**: 4 detected
  - Lines 846-1130 (285 lines): `""" Blender 4.5+ Standalone Geometry Nodes Hair Curves Grooming Script. Yu Nian ...`
  - Lines 846-1130 (285 lines): `''')  body_obj = bpy.data.objects.get(TARGET_OBJ_NAME)  # Ensure hair shader exi...`
  - Lines 1-24 (24 lines): `MorphoMesh: Digital Human Geometry Nodes Hair Curves Grooming Engine.  Implement...`
- **Architectural Smell / SRP Violation**:
  > Mixes hair layer configuration, 3D parametric spline generation (straight bangs, cheek locks, crown, back hair), ribbon polygonal mesh extrusion, Blender Geometry Nodes modifier tree generation, and a 354-line embedded Blender Python script generator.
- **Proposed Modular Decomposition (`src/morphomesh/grooming/`)**:
  - `config.py`: HairLayerConfig, HairGroomConfig, get_6_stratum_hime_cut_layers, get_default_hime_cut_layers.
  - `splines.py`: HairCurveSpline, generate_hime_cut_splines, generate_6_stratum_hime_cut_splines, _calc_spline_length.
  - `ribbons.py`: convert_curves_to_ribbon_mesh (polygonal quad ribbon extrusion for game engines and glTF export).
  - `nodes.py`: build_hair_geom_node_tree (procedural Blender Geometry Nodes hair modifier tree).
  - `runner.py`: get_grooming_script, groom_human entry point.
- **Backward Compatibility Strategy**:
  > `src/morphomesh/human_grooming.py` acts as a facade re-exporting all grooming symbols.

---

## 3. Survey of Large Secondary Modules (30 KB – 50 KB / >800 Lines)

| Module Path | Size (KB) | Lines | Domain | Analysis & Modularization Path |
|---|---|---|---|---|
| `src/morphomesh/camera_rig.py` | 46.12 KB | 1,166 | Camera Positioning & Viewport Capture Rig | Contains spherical camera positioning math, bounding box calculation for 5 anatomical regions, interactive OpenGL viewport capture, headless Workbench fallback capture, and base64 preview serialization. Recommended refactoring into `src/morphomesh/camera/` or `src/morphomesh/inspection/`. |
| `src/morphomesh/connectors/tripo_connector.py` | 46.09 KB | 1,110 | Tripo3D Generative Connector | Contains GLB binary metrics parser, multi-map PBR texture extractor, REST API polling, and offline mock generation. Naturally modularizes into `src/morphomesh/connectors/tripo/`. |
| `src/morphomesh/connectors/gemini_image_connector.py` | 39.21 KB | 909 | Google Gemini Image Concept Connector | Contains REST API and SDK clients, base64 payload handling, mock turnaround sheet synthesis. Naturally modularizes into `src/morphomesh/connectors/gemini/`. |
| `src/morphomesh/human_materials.py` | 36.35 KB | 920 | Human PBR Cycles/EEVEE Shader Suite | Contains Principled BSDF v2 node trees, 2-chamber eye refraction, Random Walk SSS setups, and a 312-line embedded Blender shader script. Naturally combines with `materials.py` into a unified `src/morphomesh/materials/` package. |
| `src/morphomesh/armor.py` | 36.22 KB | 868 | Procedural War Armor Generator | Contains pauldron, gorget, bracer, backplate procedural modeling, BVH clearance offsets, and a 223-line embedded Blender armor script. Recommended refactoring into `src/morphomesh/armor/`. |
| `src/morphomesh/grooming.py` | 32.71 KB | 870 | Volumetric Animal Fur Grooming Engine | Contains multi-layer fur curve setups, biological flow vector computation, density masks, and a 247-line embedded Blender script. Can be unified with `human_grooming.py` under `src/morphomesh/grooming/`. |

---

## 4. Dependency Topology & Circular Import Audit

### Import Cycle Audit
A full cycle detection traversal was executed across the directed import graph of all 35 modules in `src/morphomesh/`.
- Initial naive prefix matching flagged apparent cycles involving `morphomesh.connectors` and submodules due to wildcard module prefixes.
- When exact module path resolution was enforced (distinguishing `morphomesh.connectors.__init__` from `morphomesh.connectors.base` and individual connector modules), **ZERO circular dependency cycles were found**.
- Runtime verification (`python -c 'import morphomesh.blender_bridge; import morphomesh.character_assembler; ...'`) confirmed clean, deterministic module loading with 0 ImportError or CircularImportError exceptions.

### High-Coupling Hubs
Three primary coupling hubs were identified that represent significant architectural gravity:
1. **`morphomesh.models`**: Imported by **10 internal modules** and **29 test files**. Because 62 classes are located in a single file, modifying any schema triggers widespread re-parsing. Decomposing into domain submodules while preserving `models/__init__.py` re-exports eliminates blast radius.
2. **`morphomesh.inference_adapter`** (specifically `MeshGeometry`): Imported by **11 internal modules** and **22 test files**. Modules like `wardrobe.py`, `human_generator.py`, `human_rigging.py`, and `armor.py` only import `MeshGeometry`, but are forced to depend on the entire generative AI inference adapter. Moving `MeshGeometry` into a dedicated `src/morphomesh/geometry/mesh.py` module immediately decouples geometric algorithms from AI inference backends.
3. **`morphomesh.blender_bridge`**: Imported by **2 internal modules** and **22 test files**. It serves as the primary gateway to Blender, but currently couples transport, security, and script generation. Refactoring into `src/morphomesh/bridge/` isolates the transport layer from script generation.

---

## 5. Cross-Cutting Technical Bottlenecks

### Bottleneck 1: Pure-Python Geometry Math vs. Vectorization
- **Observation**: `visual_critic.py` implements scalar vector math (`_cross_product`, `_dot_product`, `_norm_vec`), Eberly point-to-triangle distance (97 lines), Möller ray-triangle intersection (38 lines), and a pure-Python spatial BVH tree (`PurePythonBVHTree`, 249 lines) using native Python float loops and list operations.
- **Impact**: In headless offline mode where Blender C++ `mathutils.bvhtree` is absent, running penetration detection over detailed meshes (thousands of faces) incurs significant CPU overhead.
- **Recommendation**: Vectorize hotspot inner loops using NumPy array operations where possible, or ensure early bounding-box pruning before running fine triangle-triangle tests.

### Bottleneck 2: In-Band Socket Serialization of Large Binary Payloads
- **Observation**: `blender_bridge.py` uses Newline-Delimited JSON (NDJSON) over TCP socket 9876. High-resolution viewport captures and beauty renders are Base64-encoded and transmitted directly within the NDJSON payload.
- **Impact**: A 4K uncompressed or high-res PNG image encoded in Base64 can produce a 10MB–25MB single-line JSON string. `socket.recv(4096)` loops must perform dozens of buffer concats and large string allocations, stressing Python memory.
- **Recommendation**: Support direct disk-file exchange for large binary assets (saving to a temporary file on disk and returning the filepath in the JSON response) rather than embedding multi-megabyte base64 strings in NDJSON.

### Bottleneck 3: Massive Embedded Blender Python Script Strings
- **Observation**: Across 9 files, over **4,900 lines** of Python code are stored as multiline string literals/templates passed to Blender:
  - `blender_bridge.py`: 1,596 lines (`_generate_headless_script`) + 218 lines (`_generate_interactive_script`)
  - `character_assembler.py`: 1,030 lines (`get_master_assembly_script`) + 196 lines (`_get_uv_unwrapping_script_snippet`)
  - `human_generator.py`: 490 lines (`get_human_generation_script`)
  - `human_grooming.py`: 354 lines (`get_grooming_script`)
  - `human_materials.py`: 312 lines (`get_material_setup_script`)
  - `wardrobe.py`: 280 lines (`get_wardrobe_script`)
  - `human_rigging.py`: 252 lines (`get_rigging_script`)
  - `grooming.py`: 247 lines (`get_grooming_blender_script`)
  - `armor.py`: 223 lines (`get_armor_blender_script`)
- **Impact**: Embedded strings cannot be easily linted, type-checked, or syntax-validated during static analysis. String interpolation with f-strings requires double braces `{{` and `}}` which is prone to escaping bugs.
- **Recommendation**: Modularize script generation into dedicated template modules with automated syntax validation tests.

---

## 6. Consolidated Target Architecture

To transform MorphoMesh from a collection of monolithic files into a clean, modular, production-grade system, the following target architecture is recommended:

```
src/morphomesh/
├── __init__.py               # Top-level public package exports
├── main.py                   # CLI entrypoint
├── server.py                 # FastMCP server registration & CLI entry point
│
├── models/                   # Modularized Pydantic schemas & enums
│   ├── __init__.py           # Re-exports all 62 classes & 32 error constants
│   ├── errors.py             # Error constants & MorphoMeshException
│   ├── enums.py              # Common Enums
│   ├── geometry.py           # BoundingBox, BoundingBox3D, SceneObjectInfo
│   ├── creature.py           # Creature generation schemas
│   ├── human.py              # Digital human schemas
│   ├── inspection.py         # Camera & viewport capture schemas
│   ├── critique.py           # Visual quality critique schemas
│   └── animation.py          # Animation schemas
│
├── geometry/                 # Core geometric primitives & mesh representations
│   ├── __init__.py           # Re-exports MeshGeometry
│   ├── mesh.py               # MeshGeometry container, glTF 2.0 / OBJ exporters
│   ├── quad_utils.py         # Quad caps, quad ellipsoids, normal relaxation
│   └── creature_shapes.py    # Curved claws, plantigrade paws, heads, torsos
│
├── bridge/                   # Blender communication & process management
│   ├── __init__.py           # Re-exports BlenderBridge, SecurityException, etc.
│   ├── security.py           # BpyCodeValidator AST safety visitor
│   ├── exceptions.py         # SecurityException, BlenderExecutionError
│   ├── socket_client.py      # TCP socket NDJSON transport
│   ├── process_runner.py     # Headless subprocess executor & sentinel parser
│   ├── script_builder.py     # Modular script generation
│   └── client.py             # BlenderBridge facade class
│
├── inference/                # AI generative backends & adapters
│   ├── __init__.py           # Re-exports InferenceAdapter, etc.
│   ├── base.py               # BaseInferenceAdapter, EnhancedCreate3DAssetOutput
│   ├── circuit_breaker.py    # CircuitBreaker pattern
│   ├── mock_adapter.py       # MockInferenceAdapter procedural fallbacks
│   ├── remote_adapters.py    # Replicate & HuggingFace adapters
│   └── factory.py            # get_inference_adapter factory
│
├── critic/                   # Closed-loop visual QA & inspection
│   ├── __init__.py           # Re-exports run_visual_critique, etc.
│   ├── math_utils.py         # Vector math, Eberly distance, Möller intersection
│   ├── bvh.py                # PurePythonBVHTree spatial index
│   ├── penetration.py        # Garment & grooming penetration detection
│   ├── proportions.py        # Anthropometric proportion diagnostics
│   ├── deformation.py        # Rigging pinch & volume collapse diagnostics
│   ├── fixtures.py           # Defect injection test fixtures
│   └── orchestrator.py       # Critique report aggregator
│
├── human/                    # Digital human base mold & anatomy
│   ├── __init__.py           # Re-exports HumanAnatomyGenerator, etc.
│   ├── base_mold.py          # MakeHuman CC0 OBJ template loader & landmarks
│   ├── vertex_groups.py      # 32 Standardized anatomical vertex groups
│   ├── morphology.py         # Parametric body shaping (bust, hips, limbs)
│   └── generator.py          # Generation scripts & base mesh creation
│
├── rigging/                  # Metarigs, skin weighting & blendshapes
│   ├── __init__.py           # Re-exports Rigify rigging functions
│   ├── config.py             # 163 DEF bones constants, rig configuration
│   ├── structure.py          # BoneDefinition, MetarigStructure, SkinWeightMap
│   ├── metarig.py            # Rigify metarig generation & pivot alignment
│   ├── weights.py            # Anti-pinch volumetric skin weighting
│   ├── blendshapes.py        # 52 ARKit FACS facial blendshapes
│   └── runner.py             # Rigging script execution
│
├── wardrobe/                 # Procedural clothing & accessories
│   ├── __init__.py           # Re-exports dress_human, WardrobeConfig
│   ├── config.py             # WardrobeConfig & bone aliases
│   ├── skinning.py           # Cloth skin weight heuristics
│   ├── garments/             # Bodice, sash, skirt, sandals
│   ├── props/                # Catenary strings, swallowtail butterflies
│   └── suite.py              # Master wardrobe script & dress_human
│
├── grooming/                 # Hair curves & fur synthesis
│   ├── __init__.py           # Re-exports hair & fur grooming functions
│   ├── config.py             # HairLayerConfig, HairGroomConfig, strata presets
│   ├── splines.py            # Hime cut curve splines generation
│   ├── ribbons.py            # Ribbon quad mesh extrusion
│   ├── nodes.py              # Geometry Nodes tree builder
│   └── creature_fur.py       # Multi-layer animal fur & biological flow
│
├── materials/                # PBR shader suites (Human & Creature)
│   ├── __init__.py           # Re-exports shader builders
│   ├── human_shaders.py      # Random Walk SSS, dual-chamber eye refraction
│   └── creature_shaders.py   # Coat scattering, wet specular, keratin claws
│
├── camera/                   # Inspection camera rig & viewport capture
│   ├── __init__.py           # Re-exports camera setup & capture
│   ├── math.py               # Spherical camera positioning & framing
│   └── capture.py            # OpenGL viewport grab & Workbench render
│
├── assembler/                # Character assembly & export packaging
│   ├── __init__.py           # Re-exports YuNianAnAssembler, etc.
│   ├── config.py             # MasterAssemblyConfig, collection hierarchy
│   ├── texture_baker.py      # 4K procedural PBR texture map baking
│   ├── scene_assembly.py     # Master assembly script generator
│   └── master_assembler.py   # Assembly execution & production export
│
├── tools/                    # FastMCP tool implementations (decoupled)
│   ├── __init__.py           # Re-exports all 17 tools
│   ├── base.py               # Context helpers & decorators
│   ├── creature.py           # 7 creature pipeline tools
│   ├── human.py              # 7 digital human tools
│   └── inspection.py         # 3 inspection & QA tools
│
├── connectors/               # SOTA connectors (already semi-modular)
│   ├── base.py
│   ├── registry.py
│   ├── meshy/                # Decomposed Meshy connector
│   ├── tripo_connector.py
│   ├── trellis_connector.py
│   ├── anycreature_connector.py
│   ├── animals3d_connector.py
│   ├── hunyuan_connector.py
│   ├── meshanything_connector.py
│   └── gemini_image_connector.py
│
└── anatomy/                  # Biomechanical engine (already modular)
    ├── __init__.py
    ├── stance.py
    ├── landmarks.py
    ├── bone_roll.py
    └── skinning.py
```

### Backward Compatibility Preservation Guarantee
To guarantee zero regression across all 2,082 tests and all client applications:
1. **Facade Legacy Modules**: Keep `blender_bridge.py`, `character_assembler.py`, `visual_critic.py`, `wardrobe.py`, `human_rigging.py`, `human_generator.py`, `human_grooming.py`, `inference_adapter.py`, `models.py`, `camera_rig.py`, `human_materials.py`, `armor.py`, `grooming.py` in place as lightweight facades that import and re-export all public symbols via `__all__`.
2. **Package `__init__.py` Re-exports**: `src/morphomesh/__init__.py` continues to re-export top-level interfaces.
3. **FastMCP Tool Signatures**: In `server.py` and `tools/`, all tool function signatures, type annotations, and docstrings remain identical byte-for-byte.
4. **Socket Wire Protocol**: The NDJSON socket communication protocol on port 9876 remains completely unchanged.