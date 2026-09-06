# Task Assignment: Worker M4 (Scene Assembly, Production Export, Verification Suite & Beauty Renders)

## Mission
Execute Milestone M4: Assemble the complete Armored War Bear production asset in Blender 5.2.1 LTS, export production `.blend` and `.glb` files, create the automated standalone verification script `verify_bear_anatomy.py`, render 4 high-resolution beauty shots via Cycles, and verify 100% test passage.

## Authoritative Reference
- Request: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (see section `## 2026-09-05T15:44:52Z`)
- Project Scope: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
- Testing Track Spec: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/TEST_INFRA.md`
- Module APIs:
  * Anatomy: `src/morphomesh/creature_generator.py` (`generate_bear_base_mesh`, `get_blender_generation_script`)
  * Fur/Grooming: `src/morphomesh/grooming.py` (`CreatureGroomingEngine`, `create_bear_fur_pipeline`)
  * Materials: `src/morphomesh/materials.py` (`CreaturePBRSuite`, `create_pbr_creature_materials`)
  * Armor: `src/morphomesh/armor.py` (`ProceduralArmorEngine`, `fit_war_armor`)
  * Bridge: `src/morphomesh/blender_bridge.py`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
- `examples/Armored_War_Bear_HD.blend`
- `examples/Armored_War_Bear_HD.glb`
- `verify_bear_anatomy.py`
- `examples/renders/` (all 4 render image files)
- `tests/test_bear_anatomy.py`
- Auxiliary updates to `src/morphomesh/` if needed for master scene assembly/export

## Detailed Objectives & Acceptance Criteria

### 1. Master Scene Assembly (`examples/Armored_War_Bear_HD.blend`)
- Combine all components into a unified Blender 5.2.1 LTS scene:
  * `Bear_Base_Mesh` with plantigrade stance, articulated facial features (cranium, snout, nostrils, mouth cavity, jaw, teeth, eyelids, ears), forward-and-downward curving claws on all 4 paws ($\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} > 0.60, d_z < 0$), and all 18 standardized vertex groups populated.
  * 5 Principled BSDF v2 PBR materials assigned (`Mat_Bear_Fur`, `Mat_Bear_Skin_Nose`, `Mat_Bear_Claws`, `Mat_Armor_WeatheredSteel`, `Mat_Armor_BrassTrim`).
  * Multi-layer volumetric hair particle systems: undercoat + guard hairs ($\ge 10,000$ guide strands total, $> 100,000$ render strands), dorsal biological flow, clumping, tapering, and zero-fur density masks on naked facial and pad features.
  * Fur curve ribbon mesh (`Bear_Fur_Ribbons`) evaluated with normalized UVs and assigned `Mat_Bear_Fur` for glTF compatibility.
  * 6 fitted war armor plates (`Armor_Pauldron_L`, `Armor_Pauldron_R`, `Armor_Gorget`, `Armor_Bracer_L`, `Armor_Bracer_R`, `Armor_Backplate`) with guaranteed clearance $\ge 0.015\text{m}$, watertight 2-manifold closed shells, and positive signed volumes. (Note: Apply `bmesh.ops.recalc_face_normals` if needed to ensure all armor normals point outward).
  * 3-point cinematic lighting rig (Key light, Fill light, Rim/Kicker light) and ground plane/backdrop for studio rendering.
- Save master scene to `examples/Armored_War_Bear_HD.blend`.

### 2. Production Asset Export (`examples/Armored_War_Bear_HD.glb`)
- Export production asset to `examples/Armored_War_Bear_HD.glb` using Blender's glTF 2.0 exporter (`bpy.ops.export_scene.gltf`).
- Include: Bear base mesh, 6 fitted armor plates, and fur ribbon mesh (`Bear_Fur_Ribbons`).
- Include all assigned PBR materials and vertex colors/groups.
- Verify file size > 500 KB and valid glTF 2.0 structure.

### 3. Automated Inspection Script (`verify_bear_anatomy.py`)
- Standalone Python script executable from project root:
  ```bash
  python3 verify_bear_anatomy.py
  ```
  and headless Blender mode:
  ```bash
  /Applications/Blender.app/Contents/MacOS/Blender --background --python verify_bear_anatomy.py
  ```
- Must programmatically inspect and assert:
  * **Claw Orientation**: Dot product of claw tip vectors with character forward axis $> 0.60$ and downward $d_z < 0$ on all 20 claws (5 per paw $\times$ 4 paws).
  * **Vertex Groups**: All 18 standardized facial and anatomical vertex groups are present and populated with non-zero vertex counts.
  * **Volumetric Fur**: Hair particle systems contain $\ge 10,000$ parent guide strands; zero-fur density mask vertices have 0.0 density.
  * **War Armor Clearance**: All 6 armor plates maintain minimum clearance $d_{\min} \ge 0.015\text{m}$ from the bear skin mesh, with zero penetration.
  * **Export Artifacts**: Verify existence and integrity of `examples/Armored_War_Bear_HD.blend` and `examples/Armored_War_Bear_HD.glb`.
- Returns exit code 0 on success, prints formatted verification metrics with pass/fail markers.

### 4. Multi-Angle High-Resolution Cycles Beauty Renders
- Render 4 distinct beauty shots using Blender Cycles (or EEVEE Next fallback if GPU/Cycles is slow, but Cycles preferred with 64-128 samples and denoising):
  1. `examples/renders/bear_front_three_quarter.png`: Front 3/4 perspective hero shot showcasing silhouette, shoulder armor, facial expression, and paw claws.
  2. `examples/renders/bear_head_closeup.png`: Close-up of organic facial sculpting (snout, wet nose, open mouth, teeth, eyelids, ears) and gorget neck armor.
  3. `examples/renders/bear_paw_claws_closeup.png`: Close-up of front paw showing forward-curving claws, keratin material, digital pads, and bracer armor.
  4. `examples/renders/bear_full_body.png`: Dramatic side/wide angle showcasing full plantigrade anatomy, volumetric fur grooming, dorsal backplate, and pauldron armor.
- Images must be high-resolution ($\ge 1280 \times 720$ or $1920 \times 1080$), non-empty (file size > 50 KB each), and visually verified.

### 5. Integration Test Suite (`tests/test_bear_anatomy.py`)
- Implement pytest harness running `verify_bear_anatomy.py` and asserting that all assets exist and pass.
- Run `pytest -v tests/test_bear_anatomy.py` and full repo suite `pytest -v tests/` (all tests must pass 100%).

## Deliverables
- Deliver comprehensive handoff report at `.agents/worker_m4/handoff.md` detailing all generated files, render paths, verification outputs, and test results.
- Message orchestrator upon completion.

## 2026-09-05T18:03:56Z
You are Worker M4 (Scene Assembly, Production Export, Verification Suite & Beauty Renders Specialist).
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4`.
Read your dispatch assignment at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`, and `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/TEST_INFRA.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
- `examples/Armored_War_Bear_HD.blend`
- `examples/Armored_War_Bear_HD.glb`
- `verify_bear_anatomy.py`
- `examples/renders/` (4 images: `bear_front_three_quarter.png`, `bear_head_closeup.png`, `bear_paw_claws_closeup.png`, `bear_full_body.png`)
- `tests/test_bear_anatomy.py`
- Auxiliary helpers in `src/morphomesh/` if needed for master assembly/export

## 2026-09-05T20:33:30Z
You are Worker M4 (Replacement) for Milestone M4 (Scene Assembly, Production Export, Verification Suite & Beauty Renders).
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4`.
Read your dispatch assignment at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, and `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Context from Predecessor:
The previous Worker M4 successfully produced all core artifacts before encountering a network transport disconnection:
- `examples/Armored_War_Bear_HD.blend` (1,103,445 bytes)
- `examples/Armored_War_Bear_HD.glb` (2,985,604 bytes)
- `examples/renders/bear_front_three_quarter.png` (1,161,979 bytes)
- `examples/renders/bear_head_closeup.png` (1,351,197 bytes)
- `examples/renders/bear_paw_claws_closeup.png` (1,227,232 bytes)
- `examples/renders/bear_full_body.png` (1,118,135 bytes)
- `verify_bear_anatomy.py` (477 lines)
- `tests/test_bear_anatomy.py` (284 lines)
- `scripts/assemble_and_render_armored_war_bear.py`

Your tasks from interruption point:
1. Run `python3 verify_bear_anatomy.py` and confirm all mathematical assertions pass with exit code 0.
2. Run headless Blender verification: `/Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python verify_bear_anatomy.py` and confirm exit code 0.
3. Run `pytest -v tests/test_bear_anatomy.py` (all tests must PASS).
4. Run full repository test suite `pytest -v tests/` (all 320+ tests must PASS with 0 failures).
5. Verify the 4 renders in `examples/renders/` (check resolutions, file sizes > 50 KB, valid PNGs).
6. Write a comprehensive handoff report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4/handoff.md` detailing all assets, verification outputs, and test results.
7. Message the orchestrator upon completion.
