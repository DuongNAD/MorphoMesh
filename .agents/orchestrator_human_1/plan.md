# Master Project Plan: MorphoMesh Digital Human Engine Upgrade & Yu Nian An 3D Asset

## 1. Overview & Objectives
Upgrade MorphoMesh into an industrial-grade Photorealistic Digital Human Pipeline and construct the complete, high-fidelity 3D character asset of Yu Nian An (余念安) based on the reference design `media_1788716034772.jpg`.

## 2. Methodology & Phases

### Phase 0: Comprehensive Survey (Exploration)
- Dispatch 3 parallel Explorers:
  - **Explorer 1 (Codebase Architecture & MCP Tools)**: Map existing `src/morphomesh`, Blender bridge, socket protocol (port 9876), FastMCP endpoints, existing tests, and integration points for new modules.
  - **Explorer 2 (Anatomy, Rigify & Blendshapes Specification)**: Investigate parametric mesh generation (female proportions, quad-dominant >=95%, 5-finger hands, feet), Rigify 163 DEF bones metarig alignment, skin weighting, and 52 ARKit FACS shape keys.
  - **Explorer 3 (Visual Aesthetics, Reference Image, Shading & Props)**: Analyze reference image `media_1788716034772.jpg`, hime cut bangs hair curves, white strap dress & belt, flat sandals, marionette red strings and glowing butterflies, PBR SSS skin and eye shaders.

### Phase 1: PROJECT.md & Feature Inventory
- Synthesize survey findings into `PROJECT.md` with complete Feature Inventory, interface contracts, and module boundaries.

### Phase 2: Milestone Execution (Iterative Direct Execution or Sub-Orchestration)
- **Milestone 1**: `src/morphomesh/human_generator.py` + FastMCP & Socket Bridge registration.
- **Milestone 2**: `src/morphomesh/human_rigging.py` (Rigify 163 DEF bones, automated alignment, skinning, 52 ARKit FACS blendshapes).
- **Milestone 3**: `src/morphomesh/human_materials.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/wardrobe.py`.
- **Milestone 4**: Yu Nian An 3D Master Asset, Collections structure, Magic Props (red strings, luminous butterflies), High-End Stylized Photorealism.
- **Milestone 5**: Full Unit & E2E Test Suite (`pytest tests/`), Export to `.blend`, `.fbx`, `.gltf` with 4K PBR textures, Victory Verification.
