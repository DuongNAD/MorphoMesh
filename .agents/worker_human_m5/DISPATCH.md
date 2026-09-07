# Task Assignment: Milestone 5 Production Packaging & Multi-Format Exports Worker

## Agent Identity
- Agent: `worker_human_m5`
- Archetype: `teamwork_preview_worker`
- Parent: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)
- Working Directory: `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5`

## Mandatory Reading
1. `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md`
2. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md`
3. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md`
4. Master Asset: `E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You have exclusive write ownership of:
- `src/morphomesh/character_assembler.py`
- `src/morphomesh/server.py` (FastMCP tool registration for exports if applicable)
- `tests/test_production_exports.py`
- `output/yu_nian_an/` (Yu_Nian_An.fbx, Yu_Nian_An.glb, textures/, README_EXPORT.md)
- `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5\`

Do NOT alter Yu_Nian_An_Body's 2,036 pure quads / 2,144 vertices base topology in `human_generator.py`.

## Technical Objectives

### 1. Production `.blend` Validation & Clean Packaging
- Verify `output/yu_nian_an/Yu_Nian_An_Master.blend`:
  * All 16 materials have `use_fake_user = True`.
  * Exactly 7 collections: `Yu_Nian_An_Master`, `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, `05_Armature`, `06_Lights_Camera`.
  * Cycles and EEVEE Next compatibility confirmed.
  * Pack external images/assets if any (`bpy.ops.file.pack_all()`).

### 2. Multi-Format Rigged `.fbx` Export
- Export `output/yu_nian_an/Yu_Nian_An.fbx` from `Yu_Nian_An_Master.blend` via Blender Python `bpy.ops.export_scene.fbx`:
  * Include meshes in `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, and `05_Armature`.
  * `mesh_smooth_type = 'FACE'`, `add_leaf_bones = False`, `primary_bone_axis = 'Y'`, `secondary_bone_axis = 'X'`.
  * Armature deformers, vertex groups, and 52 ARKit FACS shape keys preserved.
  * Verify file size > 1 MB, valid FBX binary header, and readable via FBX parsers.

### 3. Web & Real-Time Ready `.glb` / `.gltf` Export
- Export `output/yu_nian_an/Yu_Nian_An.glb` from `Yu_Nian_An_Master.blend` via Blender Python `bpy.ops.export_scene.gltf`:
  * `export_format = 'GLB'`.
  * `export_skins = True`, `export_morph = True` (52 ARKit FACS shape keys exported as glTF morph targets).
  * `export_materials = 'EXPORT'`, PBR Principled BSDF materials mapped to glTF PBR standard.
  * Verify file size > 1 MB, valid glTF binary magic `glTF`, and non-empty scene nodes.

### 4. 4K PBR Texture Maps Generation & Packaging
- Generate complete 4K ($4096 \times 4096$) PBR texture maps in `output/yu_nian_an/textures/`:
  * `Yu_Nian_An_BaseColor_4K.png`: Porcelain skin, soft rose lips, dark eyeliner, ivory silk dress, ice-blue satin sash.
  * `Yu_Nian_An_Normal_4K.png`: Tangent-space normal map with micro-skin pores, lip vermilion wrinkles, and fabric weave.
  * `Yu_Nian_An_Roughness_4K.png`: Dual roughness map (face 0.38, lips 0.28, scalp 0.70, dress 0.45, sash 0.22 satin).
  * `Yu_Nian_An_Metallic_4K.png`: Non-metal dielectric (0.0) with subtle metallic sheen on ribbon aglets/buckles.
  * `Yu_Nian_An_SSS_4K.png`: Subsurface scattering mask (high on ears, nose, lips, low on scalp/body).
  * `Yu_Nian_An_Alpha_4K.png`: Eyelashes/eyebrows and bangs fringe opacity mask.
  * `Yu_Nian_An_Height_4K.png`: Displacement / bump height map.
- Generate `output/yu_nian_an/README_EXPORT.md` documenting asset specifications, collection hierarchy, rigging conventions, texture channel packing, and engine import guides (Unreal Engine 5.4+, Unity 6, WebGL/Three.js).

### 5. Automated Comprehensive Test Suite
- Write `tests/test_production_exports.py`:
  * Verify existence and non-zero sizes of `Yu_Nian_An_Master.blend`, `Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, and all 7 4K textures in `output/yu_nian_an/textures/`.
  * Verify texture resolutions are strictly $4096 \times 4096$.
  * Verify FBX binary header and GLB magic bytes.
  * Verify glTF morph targets count (52 ARKit keys) and bone skinning.
- Run `pytest tests/test_production_exports.py -v`.
- Run full repository regression test suite `pytest tests/` (verify 100% pass rate).

### 6. Delivery
- Deliver your handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5\handoff.md` and message orchestrator_human_1.

## 2026-09-06T22:46:29Z
You are worker_human_m5.
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_human_m5
Your parent is orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7).

Read your dispatch file at E:\tool\mcp\MorphoMesh\.agents\worker_human_m5\DISPATCH.md.
Read all mandatory reading files:
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. Master Asset: E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR WRITE OWNERSHIP:
You have exclusive write ownership of:
- src/morphomesh/character_assembler.py (add export automation functions if needed)
- src/morphomesh/server.py (export FastMCP tools if applicable)
- tests/test_production_exports.py
- output/yu_nian_an/ (Yu_Nian_An.fbx, Yu_Nian_An.glb, textures/, README_EXPORT.md)
- .agents/worker_human_m5/

Do NOT alter Yu_Nian_An_Body's 2,036 quads / 2,144 vertices base topology in human_generator.py.

IMPLEMENTATION TASKS:
1. Multi-Format Production Exports from Yu_Nian_An_Master.blend:
   - Export output/yu_nian_an/Yu_Nian_An.fbx with armature deformers, vertex groups, and 52 shape keys.
   - Export output/yu_nian_an/Yu_Nian_An.glb with PBR materials, skinning, and glTF morph targets.
2. Complete 4K PBR Texture Set in output/yu_nian_an/textures/ (4096 x 4096):
   - BaseColor, Normal, Roughness, Metallic, SSS, Alpha, Height maps.
   - Author output/yu_nian_an/README_EXPORT.md with import guides for UE5, Unity 6, and Three.js.
3. Automated Comprehensive Test Suite:
   - Create tests/test_production_exports.py verifying file existence, headers/magic bytes, texture dimensions (4096x4096), and shape key count.
   - Run full regression test suite `pytest tests/` (verify 100% pass rate).
4. Deliver handoff report to E:\tool\mcp\MorphoMesh\.agents\worker_human_m5\handoff.md and message orchestrator_human_1.

