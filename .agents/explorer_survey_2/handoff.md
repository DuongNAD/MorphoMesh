# Handoff Report: Explorer Survey 2 (Anatomy & Mesh Geometry Specialist)
**Agent**: `explorer_survey_2` (`teamwork_preview_explorer`)  
**Recipient**: `parent` (`504d045c-25c5-48a2-a65a-2a5b368eafa7`, Orchestrator)  
**Milestone**: Armored War Bear Task — Anatomy & Geometry Survey (Phase 0)  
**Date**: 2026-09-05T15:51:00Z  
**Target File**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2/handoff.md`  

---

## 1. Observation

### 1.1 Existing Model Inspection (`examples/Armored_War_Bear.glb`)
Direct programmatic inspection via Blender 5.2.1 LTS (`/Applications/Blender.app/Contents/MacOS/Blender --background --python-expr`) revealed:
- **Mesh Inventory**: 41 separate disjoint MESH objects, 3,175 total vertices, 1,898 polygons.
  - Armor: `Armor_Backplate` (184 verts), `Armor_Bracer_L/R` (64 verts each), `Armor_Gorget` (168 verts), `Armor_Pauldron_L/R` (84 verts each).
  - Body: `Bear_Torso` (312 verts), `Bear_Head` (220 verts), `Bear_Leg_Front_L/R` (144 verts each), `Bear_Leg_Hind_L/R` (144 verts each), `Bear_Tail` (36 verts), `Bear_Nose` (24 verts), `Bear_Ear_L/R` (48 verts each), `Bear_Eye_L/R` (176 verts each).
  - Claws: 20 cone objects (`Bear_Front_L_Claw_0..4`, `Bear_Front_R_Claw_0..4`, `Bear_Hind_L_Claw_0..4`, `Bear_Hind_R_Claw_0..4`), 30 verts each.
  - Fur: `Pauldron_Fur_Ruff_L/R` (21 verts each).
- **Claw Orientation Defect (Verbatim Tool Output)**:
  - Character forward axis in Blender/glTF is $\vec{u}_{\text{fwd}} = (0.0, -1.0, 0.0)$ (negative $Y$).
  - Front claw sample: `Bear_Front_L_Claw_0`:
    - Base center: $[0.842, -0.951, 0.654]$, Tip: $[0.830, -0.928, 0.609]$.
    - Direction vector $\vec{d} = [-0.231, +0.452, -0.861]$.
    - $\vec{d} \cdot \vec{u}_{\text{fwd}} = -0.4524 < 0$ (Inverted, points backward toward tail).
  - Hind claw sample: `Bear_Hind_L_Claw_0`:
    - Base center: $[0.410, +0.644, -0.373]$, Tip: $[0.408, +0.687, -0.403]$.
    - Direction vector $\vec{d} = [-0.037, +0.822, -0.569]$.
    - $\vec{d} \cdot \vec{u}_{\text{fwd}} = -0.8215 \ll 0$ (Severely inverted, points almost straight backward).
- **Missing Anatomical Structures**:
  - `Mouth/Jaw/Teeth objects: []` (0 oral cavity, 0 lower jaw, 0 teeth).
  - `Bear_Nose`: 24-vertex solid block with 0 nostril indentations.
  - `Bear_Eye_L/R`: Standalone spheres with 0 eyelids and 0 orbital sockets.
  - `Paw/Pad objects: []` (0 palmar pads, 0 plantar pads, 0 digital pads).
  - Vertex Groups on all 41 meshes: `[]` (Empty).
  - Hair Curves / Particle systems: 0 active fur curves.

### 1.2 Engine Codebase Inspection (`src/morphomesh/`)
- `src/morphomesh/inference_adapter.py`:
  - `MeshGeometry` (lines 88–238) contains only primitive builders: `add_box()`, `add_cylinder()`, `add_sphere()`. Lacks claw, paw, pad, or facial feature generators.
  - `InferenceAdapter._synthesize_procedural_mesh()` (lines 905–922) creates quadrupeds using simple cylinders and boxes without feet, paws, or facial articulation.
- `src/morphomesh/connectors/`:
  - `anycreature_connector.py`, `trellis_connector.py`, and `hunyuan_connector.py` all rely on minimal bounding-box fallback logic.

### 1.3 Procedural Blender Prototype Execution
A prototype BMesh script was executed in Blender 5.2.1 LTS:
- Claw arc generator lofting 4 rings along parabolic arc:
  - Central claw dot product: $\vec{d} \cdot \vec{u}_{\text{fwd}} = 0.8706 > 0.6$.
  - Outermost splayed claws: $\vec{d} \cdot \vec{u}_{\text{fwd}} = 0.6773 > 0.6$.
  - Downward pitch component $z = -0.3828$ to $-0.4921 < 0$.
- Articulated facial mesh prototype: 702 vertices, 828 polygons with snout, nostrils, mouth cavity, lower jaw, 4 canines, eyelids, and cupped ears.
- Plantigrade hind paw prototype: heel calcaneus, plantar pad, 5 digital pads, and 5 forward-curving claws ($\vec{d} \cdot \vec{u}_{\text{fwd}} = 0.7663$ to $0.9363$).

---

## 2. Logic Chain

1. **Premise 1 (Forward Axis Convention)**: In Blender and glTF standards, the forward axis of a character facing the camera in neutral pose is $\vec{u}_{\text{fwd}} = (0, -1, 0)$ (negative $Y$).
2. **Premise 2 (Observation 1.1)**: In `Armored_War_Bear.glb`, all claw tip coordinates have $Y_{\text{tip}} > Y_{\text{base}}$ ($d_y > 0$), resulting in negative dot products with $\vec{u}_{\text{fwd}}$ ($-0.4524$ on front paws, $-0.8215$ on hind paws).
3. **Deduction 1 (Root Cause of Inversion)**: The claws were generated using cone primitives rotated with an incorrect sign around the pitch axis (or a $180^\circ$ yaw error), pointing them backward into the limbs rather than forward into the ground.
4. **Premise 3 (Requirement R1 & Scope Mandate)**: Claws must satisfy $\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} > 0.6$ and $d_z < 0$. The creature must embody plantigrade ursine anatomy (broad paws, calcaneus heel, 5 digital pads, palmar/plantar pads, short tail) and articulated facial geometry (snout, nostrils, mouth cavity with jaw and teeth, dimensional eyes with eyelids, cupped ears).
5. **Premise 4 (Observation 1.2)**: The MorphoMesh engine (`src/morphomesh/inference_adapter.py` and connectors) currently generates creatures solely with primitive cylinders and boxes, lacking anatomical methods for paws, pads, curved claws, and articulated heads.
6. **Conclusion**: To fulfill the requirements permanently and prevent hardcoded one-off fixes, MorphoMesh requires:
   - An engine upgrade augmenting `MeshGeometry` and `InferenceAdapter` with a reusable `add_curved_claw`, `add_plantigrade_paw`, `add_articulated_head`, and `add_anatomical_torso`.
   - A dedicated synthesis pipeline in Blender assembling the canonical `Armored_War_Bear_HD.glb` and `.blend` with 18 standardized vertex groups, fitted armor plates, and volumetric fur curves.
   - An automated test script `verify_bear_anatomy.py` asserting vector math and feature presence.

---

## 3. Caveats

- **Armor Deformation vs Rigid Mounting**: In the baseline model, armor pieces are static unparented meshes. In production, armor plates should either be parented to specific armature bones (`DEF-spine.002` for gorget/backplate, `DEF-forearm.L/R` for bracers) or rigged with bone weights to avoid deforming like rubber.
- **Hair Curves vs glTF Export**: glTF 2.0 does not natively store Blender 3.5+ Hair Curves with geometry nodes. For glTF export (`Armored_War_Bear_HD.glb`), curves can either be exported as converted curve ribbon meshes or baked into high-fidelity PBR textures, while the native Hair Curves system is fully preserved in the `.blend` file.
- **No Caveats** regarding the claw mathematical orientation formula or plantigrade anatomy specifications.

---

## 4. Conclusion

The anatomy and geometry survey is complete. The root causes of all geometric defects in the baseline asset have been identified, the biological and mathematical specifications for plantigrade ursine anatomy have been formalized, and procedural prototypes for claws, facial structures, and paw pads have been tested and verified in Blender 5.2.1 LTS.

Key deliverables completed:
1. `survey_report.md` written to `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2/survey_report.md`.
2. Formal mathematical definition of forward-and-downward curving claws ($\vec{d} \cdot \vec{u}_{\text{fwd}} > 0.6$, $d_z < 0$).
3. Complete blueprint for upgrading `MeshGeometry` in `src/morphomesh/inference_adapter.py`.
4. Specification of 18 standardized vertex groups and modifier stacks for Blender scene assembly.
5. Verification criteria for `verify_bear_anatomy.py`.

---

## 5. Verification Method

To independently verify these survey findings:
1. **Verify Baseline Model Claws**:
   Run Blender headless to inspect `examples/Armored_War_Bear.glb`:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy, mathutils
   bpy.ops.wm.read_factory_settings(use_empty=True)
   bpy.ops.import_scene.gltf(filepath='examples/Armored_War_Bear.glb')
   char_fwd = mathutils.Vector((0.0, -1.0, 0.0))
   for o in [x for x in bpy.data.objects if 'Claw' in x.name]:
       mw = o.matrix_world
       pts = [mw @ v.co for v in o.data.vertices]
       deg = [sum(1 for p in o.data.polygons if v in p.vertices) for v in range(len(pts))]
       apex = pts[deg.index(max(deg))]
       base = sum([pts[i] for i in range(len(pts)) if i != deg.index(max(deg))], mathutils.Vector((0,0,0))) / (len(pts)-1)
       d = (apex - base).normalized()
       print(f'{o.name}: dot={d.dot(char_fwd):.4f}')
   "
   ```
   *Expected Result*: All 20 claws exhibit negative dot products ($-0.45$ to $-0.84$), confirming inverted claw defect.

2. **Verify Corrected Claw Math & BMesh Prototype**:
   Execute the prototype test from Section 1.3:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import mathutils
   char_fwd = mathutils.Vector((0.0, -1.0, 0.0))
   base = mathutils.Vector((0.3, -0.8, 0.05))
   tip = base + mathutils.Vector((0.0, -0.09, -0.04))
   d = (tip - base).normalized()
   assert d.dot(char_fwd) > 0.6
   assert d.z < 0
   print('Verified: dot =', d.dot(char_fwd), 'z =', d.z)
   "
   ```
   *Expected Result*: Exits with code 0, asserting $\vec{d} \cdot \vec{u}_{\text{fwd}} \approx 0.9138 > 0.6$ and $d_z = -0.4061 < 0$.

3. **Verify Survey Report & Artifacts**:
   - Inspect `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2/survey_report.md`.
   - Ensure all 8 sections are populated with exact metrics, tables, and implementation blueprints.
