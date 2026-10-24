# Task Assignment: Worker M4-1 (Milestone 4 Modularization: Assembler & Visual Critic)

## Context
Milestone 4: Character Assembler & Visual Quality Critic Subsystems Modularization.
You are Worker M4-1. You are responsible for decomposing two large monolithic files (>50KB) into cohesive sub-packages with single responsibilities while keeping original filenames as backward-compatible facades re-exporting all symbols via `__all__`.

## Authoritative Reference
- User Request: `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md`
- Master Plan: `E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md`

## Monoliths to Decompose
1. `src/morphomesh/character_assembler.py` (105.1 KB, 2,367 lines)
   -> Sub-package: `src/morphomesh/assembler/`
   -> Facade: `src/morphomesh/character_assembler.py`
2. `src/morphomesh/visual_critic.py` (93.1 KB, 2,126 lines)
   -> Sub-package: `src/morphomesh/critic/`
   -> Facade: `src/morphomesh/visual_critic.py`

## Detailed Implementation Blueprint

### 1. `src/morphomesh/assembler/`
Decompose `src/morphomesh/character_assembler.py` into:
- `scene_builder.py`: In-Blender collection hierarchy management, lighting setups (3-point studio, cinematic dramatic, high-key anime), and multi-angle camera rigs (turntable, front/side ortho, hero 3/4 portrait).
- `pbr_baker.py`: 4K PBR procedural texture baking pipeline (albedo, roughness, metallic, normal map, emission), shader node trees, bake margin.
- `packager.py`: Multi-format packaging (glTF 2.0 binary, FBX, OBJ), archive bundling (ZIP), manifest generation, thumbnail previews.
- `assembler.py`: Core `YuNianAnCharacterAssembler` class coordinating mesh assembly, metarig alignment, wardrobe fitting, hair groom binding, material assignment, scene setup, and final rendering/packaging.
- `__init__.py`: Re-export all public symbols, classes, constants, functions with exact `__all__`.
- `src/morphomesh/character_assembler.py`: Facade module that imports all symbols from `morphomesh.assembler` and re-exports them via `__all__`.

### 2. `src/morphomesh/critic/`
Decompose `src/morphomesh/visual_critic.py` into:
- `geometry_math.py`: 3D vector arithmetic, triangle-ray intersection (Möller–Trumbore), AABB bounding boxes, point-plane projection, barycentric coordinates.
- `bvh.py`: `PurePythonBVHTree` (spatial bounding volume hierarchy for fast ray casting and nearest-neighbor triangle collision detection without external C dependencies).
- `penetration.py`: Cloth-body, cloth-cloth, hair-body mesh penetration detection and collision depth evaluation.
- `proportions.py`: Anatomical proportions evaluation (head-to-body ratios, limb lengths, golden ratio, stylized/heroic aesthetic critique).
- `deformation.py`: Extreme pose mesh deformation inspection, volume preservation checks, joint collapse detection, inverted normal detection under pose transformations.
- `reporter.py`: Quality critique score calculation, structured JSON/Markdown quality report generation, automated remediation suggestions.
- `__init__.py`: Re-export all public symbols, classes, constants, functions with exact `__all__`.
- `src/morphomesh/visual_critic.py`: Facade module that imports all symbols from `morphomesh.critic` and re-exports them via `__all__`.

## Backward Compatibility & Symbol Parity
1. Scan all symbols in `src/morphomesh/character_assembler.py` and `src/morphomesh/visual_critic.py` before refactoring. Ensure 100% of public symbols (classes, functions, constants, types, enums) are present in `__all__` of both the sub-package `__init__.py` and the root facade `.py` file.
2. Check for circular imports across all modules:
   `uv run python -c "import morphomesh.assembler, morphomesh.critic, morphomesh.character_assembler, morphomesh.visual_critic; print('M4 imports clean!')"`

## Verification Commands
```bash
# Assembler test suites
uv run pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py -v

# Visual Critic test suites
uv run pytest tests/test_visual_critic.py tests/test_adversarial_critic_benchmark.py tests/test_adversarial_bvh_penetration.py -v

# Cross-cutting integration tests
uv run pytest tests/test_production_exports.py tests/test_e2e_final_pipeline.py -v
```

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverables
- Fully modularized `src/morphomesh/assembler/` and `src/morphomesh/critic/`
- Backward-compatible facades `src/morphomesh/character_assembler.py` and `src/morphomesh/visual_critic.py`
- Full test pass on all assembler and critic test suites
- Detailed report in `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m4_1\handoff.md`
- Send message to orchestrator when finished.

## 2026-09-09T06:28:30Z
You are Worker M4-1 for Milestone 4: Character Assembler & Visual Quality Critic Subsystems Modularization.
Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m4_1.
Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m4_1\DISPATCH.md, PROJECT.md at E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md, and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md.

Task:
1. Decompose src/morphomesh/character_assembler.py (105.1 KB) into src/morphomesh/assembler/ (scene_builder.py, pbr_baker.py, packager.py, assembler.py, __init__.py) and refactor src/morphomesh/character_assembler.py into a 100% backward-compatible facade re-exporting all symbols via __all__.
2. Decompose src/morphomesh/visual_critic.py (93.1 KB) into src/morphomesh/critic/ (geometry_math.py, bvh.py, penetration.py, proportions.py, deformation.py, reporter.py, __init__.py) and refactor src/morphomesh/visual_critic.py into a 100% backward-compatible facade re-exporting all symbols via __all__.
3. Maintain exact symbol parity and object identity across facades.
4. Ensure zero circular imports across all modules.
5. Run the assembler and critic test suites:
   uv run pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py tests/test_visual_critic.py tests/test_adversarial_critic_benchmark.py tests/test_adversarial_bvh_penetration.py -v
6. Run integration suites:
   uv run pytest tests/test_production_exports.py tests/test_e2e_final_pipeline.py -v

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Document commands and results in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m4_1\handoff.md. Send a message to orchestrator when finished.

