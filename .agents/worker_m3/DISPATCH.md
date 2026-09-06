# Dispatch Assignment: Worker M3 (PBR Material Suite & War Armor Engine)

**Identity**: teamwork_preview_worker
**Assigned Task**: Milestone M3 Implementation — High-Fidelity Organic PBR Shader Engine & War Armor Integration
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m3`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (read sections `## 2026-09-05T15:44:52Z` and `## 2026-09-05T15:47:35Z`)
**Project Plan**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
**Technical References**:
- Explorer 3 Survey Report: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_3/survey_report.md` (Section 3: PBR Material Architecture & War Armor Geometry)
- Milestone M1 & M2 Handoffs:
  - `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2/handoff.md`
  - `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m2/handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You exclusively own and may edit/create:
- `src/morphomesh/materials.py`
- `src/morphomesh/armor.py`
- `src/morphomesh/blender_bridge.py` (add materials and armor dispatch helpers)
- `tests/test_materials_and_armor.py`

## Objectives & Deliverables
1. **Implement `src/morphomesh/materials.py` (`CreaturePBRSuite` class)**:
   - Create 5 distinct 4-channel PBR materials using Blender 5.2.1 Principled BSDF v2 socket names:
     1. `Mat_Bear_Fur`: Roughness 0.85, Sheen Weight 0.65, Sheen Roughness 0.30, Subsurface Weight 0.08, Metallic 0.0.
     2. `Mat_Bear_Skin_Nose`: Wet moisture layer on nose, mouth, paw pads: Roughness 0.15, Coat Weight 0.85, Coat Roughness 0.04, Specular IOR Level 0.60, Metallic 0.0.
     3. `Mat_Bear_Claws`: Keratin striation gradient on all 20 forward claws: Roughness 0.38, Metallic 0.0.
     4. `Mat_Armor_WeatheredSteel`: Cold blued steel plates: Roughness 0.42, Metallic 1.0 (pure conductor).
     5. `Mat_Armor_BrassTrim`: Antique brass/gold filigree & rivets: Roughness 0.32, Metallic 1.0.
   - Provide `setup_bear_materials(creature_obj_dict)` assigning distinct slots to snout/nose, teeth, eyes, claws, fur ribbons, and armor plates.
2. **Implement `src/morphomesh/armor.py` (`ProceduralArmorEngine` class)**:
   - Procedural generation of battle-hardened war armor:
     - Shoulder Pauldrons (`Armor_Pauldron_L`, `Armor_Pauldron_R`) fitted to `armor_mounts_shoulder`.
     - Neck Gorget (`Armor_Gorget`) encircling cervical spine.
     - Forearm Bracers (`Armor_Bracer_L`, `Armor_Bracer_R`) fitted to `armor_mounts_wrist`.
     - Dorsal Backplate (`Armor_Backplate`) contoured along thoracic spine.
   - Non-intersection clearance: Enforce guaranteed radial clearance $\Delta r \in [0.020, 0.045]\text{m}$ (minimum distance $d_{\min} > 0.015\text{m}$) over underlying bear mesh vertices and undercoat.
   - Clean 2-manifold geometry, outward face normals, zero zero-area faces.
3. **Integrate with `src/morphomesh/blender_bridge.py`**:
   - Add bridge methods `setup_creature_materials()` and `generate_war_armor()`.
4. **Automated Unit & Integration Tests (`tests/test_materials_and_armor.py`)**:
   - Assert all 5 materials have valid Principled BSDF v2 node connections and parameter ranges.
   - Assert all armor plates have minimum clearance distance $\ge 0.015\text{m}$ from skin mesh.
   - Assert zero degenerate zero-area faces in armor meshes.
   - Run `pytest -v tests/` and verify all tests pass with 0 failures.
5. **Blender 5.2.1 LTS Verification**:
   - Execute in headless Blender and over live socket (127.0.0.1:9876).
6. **Handoff Report**:
   - Deliver comprehensive 5-component report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m3/handoff.md` and message orchestrator.

## 2026-09-05T16:40:42Z

<USER_REQUEST>
You are Worker M3 (PBR Material Suite & War Armor Specialist).
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m3`.
Read your dispatch at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m3/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, and `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`.
Also consult:
- `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_3/survey_report.md` (Section 3: PBR Material Architecture & War Armor Geometry)
- `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2/handoff.md`
- `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m2/handoff.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
- `src/morphomesh/materials.py`
- `src/morphomesh/armor.py`
- `src/morphomesh/blender_bridge.py`
- `tests/test_materials_and_armor.py`

Execute the implementation:
1. Implement `src/morphomesh/materials.py` (`CreaturePBRSuite` class) generating the 5 distinct Principled BSDF v2 materials: Fur, Wet Skin/Nose (coat moisture 0.85), Keratin Claws, Weathered Steel (metallic 1.0), and Brass Trim (metallic 1.0).
2. Implement `src/morphomesh/armor.py` (`ProceduralArmorEngine` class) generating fitted war armor plates (pauldrons, gorget, bracers, backplate) with non-intersecting clearance offset $\Delta r \ge 0.015$m over bear anatomy.
3. Integrate with `src/morphomesh/blender_bridge.py`.
4. Add unit and integration tests in `tests/test_materials_and_armor.py`. Run `pytest -v tests/` and verify in Blender 5.2.1 LTS.
5. Deliver handoff report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m3/handoff.md` and message orchestrator when done.
</USER_REQUEST>
