# Handoff Report — Explorer M4-Iter2-2: Pauldron Penetration & Test Integrity Remediation

**Agent**: Explorer M4-Iter2-2 (Armor Clearance & BVH Penetration Specialist)  
**Date**: 2026-09-06T11:05:00Z  
**Recipient**: Orchestrator Bear Gen 2 (`c332dd9a-5201-4cf0-84e2-35aa3c9c5afa`) / Worker M4  
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_2`  
**Investigation Report**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_2/survey_report.md`  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

Direct observations, file paths, line numbers, tool commands, and verbatim execution outputs:

### 1.1 Baseline Pauldron Penetration & Normal Orientation
- In `examples/Armored_War_Bear_HD.blend`:
  Running `/Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python-expr ...` executing `mathutils.bvhtree.BVHTree.FromPolygons` on `Bear_Base_Mesh` revealed:
  ```
  Armor_Pauldron_L: inside_count=9, min_surface_dist=0.000208m, min_signed=-0.033574m
  Armor_Pauldron_R: inside_count=9, min_surface_dist=0.000207m, min_signed=-0.033574m
  Armor_Gorget    : inside_count=0, min_surface_dist=0.016373m, min_signed=+0.016373m
  Armor_Bracer_L  : inside_count=0, min_surface_dist=0.025000m, min_signed=+0.022880m
  Armor_Bracer_R  : inside_count=0, min_surface_dist=0.025000m, min_signed=+0.023000m
  Armor_Backplate : inside_count=0, min_surface_dist=0.021403m, min_signed=+0.021378m
  ```
- Executing signed volume divergence calculation on procedural pauldrons from `ProceduralArmorEngine.generate_pauldron`:
  ```
  p_l signed volume: +0.00103105 m^3
  p_r signed volume: -0.00103105 m^3 (INVERTED NORMALS)
  Face 0 normal dot with radial vector (R): -0.17507 (INWARD POINTING)
  ```

### 1.2 Inspection of Production Code & Tests
1. `src/morphomesh/armor.py:94-117` & `src/morphomesh/blender_bridge.py:1384-1425`:
   - `cx = sign * (0.32 * scale + 0.002)`: Chest ellipsoid in `src/morphomesh/inference_adapter.py:894` has lateral radius $r_x = 0.36\text{m}$. At $z = 0.96\text{m}$, the chest surface reaches $x = 0.345\text{m}$. Setting $cx = 0.322\text{m}$ places the pauldron origin 23 mm *inside* the chest surface.
   - `phi_min, phi_max = (-0.35 * math.pi, 0.85 * math.pi)` for `L`: Azimuthal angle wraps $216^\circ$ ($1.2\pi$). At $\phi = 153^\circ$ ($0.85\pi$), $\cos(\phi) = -0.891$, causing the pauldron inner shell to wrap inward to $x = 0.157\text{m}, y = -0.115\text{m}$, which is deep inside the chest volume.
   - `src/morphomesh/armor.py:167-228`: Inverted quad winding for `side == "R"` flips face normals inward, producing negative signed volume.
2. `verify_bear_anatomy.py:419-427`:
   ```python
   min_dist = min(min((v.co - b_co).length for b_co in bear_coords) for v in ao.data.vertices)
   report.check(min_dist >= 0.015, ...)
   ```
   - On the old penetrating pauldron, `min_dist` measured **$0.0280\text{m} \ge 0.015\text{m}$**, falsely reporting PASS despite 33.6 mm of penetration. Because polygon face vertices are spaced 80–150 mm apart, a vertex can penetrate 33.6 mm into the face interior while remaining 28 mm away from the triangle vertices.
3. `tests/test_bear_anatomy.py:209-219`:
   ```python
   def test_pauldron_clearance_and_watertightness(self):
       armor = ProceduralArmorEngine()
       p_l = armor.generate_pauldron("L")
       p_r = armor.generate_pauldron("R")
       assert len(p_l.vertices) > 50
       assert len(p_r.vertices) > 50
       assert len(p_l.faces) > 50
       assert len(p_r.faces) > 50
   ```
   - Only checks `len > 50`. Zero watertightness, zero volume, and zero clearance assertions.

---

## 2. Logic Chain

1. *Premise 1*: Under `ORIGINAL_REQUEST.md` R3 and `PROJECT.md` Feature 10, war armor plates must cleanly fit the creature's shoulders and forelegs with true Euclidean clearance $d_{\min} \ge 0.015\text{m}$ and zero self-intersection/penetration (0 inside vertices).
2. *Premise 2*: In the original code, the pauldron origin $cx = 0.322\text{m}$ was set too close to the body midline relative to the chest width ($0.345\text{m}$ at $z=0.96\text{m}$), and the angular span $\phi$ wrapped $216^\circ$ into the medial body ($\phi = 153^\circ$).
3. *Premise 3*: Adjusting $cx = \pm 0.350\text{m}$, $cy = -0.250\text{m}$, $cz = 0.980\text{m}$, $ry = 0.170\text{m}$, $\phi_L \in [-0.25\pi, 0.55\pi]$, and $\phi_R \in [0.45\pi, 1.25\pi]$ aligns the pauldron with the anatomical shoulder/scapula joint ($x = 0.35 - 0.38\text{m}$), truncates the medial intrusion, and prevents posterior collision with the thoracic hump.
4. *Premise 4*: Eliminating the inverted quad winding for `R` unifies normal orientations, guaranteeing positive signed volume ($V = +0.000684\text{ m}^3 > 0$) for both plates.
5. *Premise 5*: Empirical evaluation across creature scales ($0.5\times, 0.75\times, 1.0\times, 1.25\times, 1.5\times, 2.0\times$) in Blender's BVHTree confirms **0 inside vertices across all scales** and $d_{\min} = 0.0315\text{m}$ at scale 1.0.
6. *Premise 6*: Replacing sparse vertex-to-vertex Euclidean distance in `verify_bear_anatomy.py` with `BVHTree.FromPolygons` enables true point-to-surface distance and signed penetration checking ($s < -0.001\text{m}$).
7. *Premise 7*: Rewriting `tests/test_bear_anatomy.py:209-219` with authentic 2-manifold edge checks (`verify_2_manifold`), divergence-theorem positive volume checks ($V > 0$), and point-to-polygon surface clearance checks ($d_{\min} \ge 0.015\text{m}$) eliminates the facade test and prevents regression.

---

## 3. Caveats

1. **Production Code Edits**: In strict compliance with Explorer read-only protocol, production code in `src/morphomesh/armor.py`, `src/morphomesh/blender_bridge.py`, `verify_bear_anatomy.py`, and `tests/test_bear_anatomy.py` was NOT modified. Complete, tested diff patches are provided in `survey_report.md`.
2. **Re-Export of Blend and GLB Artifacts**: The master files `examples/Armored_War_Bear_HD.blend` and `examples/Armored_War_Bear_HD.glb` currently contain the old meshes with 9 penetrating vertices. Once the Worker agent applies the patches to `armor.py` and `blender_bridge.py`, the scene assembly script must be re-run to update the `.blend` and `.glb` files.
3. **Finding 3 Scope**: Finding 3 (anatomical continuity in `creature_generator.py` and beauty re-renders) is investigated separately by Explorer M4-Iter2-1.

---

## 4. Conclusion & Recommendations

### Final Assessment:
The pauldron penetration (-33.6 mm), flawed vertex distance verification, and facade unit test have been fully diagnosed and solved mathematically.

### Specific Actions for Worker Agent:
1. **Apply Patch 1 to `src/morphomesh/armor.py`**:
   - Update $cx = \text{sign} \times 0.350 \times \text{scale}$, $cy = -0.250 \times \text{scale}$, $cz = 0.980 \times \text{scale}$, $ry = 0.170 \times \text{scale} + \Delta r$.
   - Set $\phi_L \in [-0.25\pi, 0.55\pi]$ and $\phi_R \in [0.45\pi, 1.25\pi]$.
   - Remove reversed winding in `generate_pauldron` and `get_armor_blender_script` (use unified quad winding).
2. **Apply Patch 2 to `src/morphomesh/blender_bridge.py`**:
   - Update `make_pauldron` in method `morphomesh.generate_war_armor` to match the new pauldron parameters and unified winding.
   - Update clearance calculation to use `BVHTree.FromPolygons`.
3. **Apply Patch 3 to `verify_bear_anatomy.py`**:
   - Update `verify_blender_scene` to evaluate point-to-surface distance via `BVHTree.FromPolygons`, assert 0 inside vertices, assert 2-manifold watertightness, and assert positive volume.
   - Update `verify_procedural_engine` with standalone point-to-triangle clearance checking.
4. **Apply Patch 4 to `tests/test_bear_anatomy.py`**:
   - Replace `test_pauldron_clearance_and_watertightness` with authentic 2-manifold check, positive signed volume assertion, and point-to-polygon surface clearance assertion ($d_{\min} \ge 0.015\text{m}$).
5. **Re-generate Master Assets**:
   - Re-run Blender scene assembly to overwrite `examples/Armored_War_Bear_HD.blend` and export `examples/Armored_War_Bear_HD.glb`.

---

## 5. Verification Method

To independently verify the proposed remediation:

1. **Verify Pauldron Clearance and Zero Penetration in Blender**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python-expr "
   import bpy, math
   from mathutils.bvhtree import BVHTree
   from mathutils import Vector

   bear = bpy.data.objects['Bear_Base_Mesh']
   bvh = BVHTree.FromPolygons([v.co for v in bear.data.vertices], [p.vertices for p in bear.data.polygons])

   def eval_p(cx, cy, cz, rx, ry, rz, pmin, pmax):
       eff_cl = 0.025
       rx_in, ry_in, rz_in = rx + eff_cl, ry + eff_cl, rz + eff_cl
       rx_out, ry_out, rz_out = rx_in + 0.009, ry_in + 0.009, rz_in + 0.009
       verts = []
       for i in range(6):
           t = 0.08*math.pi + (i/5)*(0.48-0.08)*math.pi
           for j in range(8):
               p = pmin + (j/7)*(pmax - pmin)
               verts.append(Vector((cx + rx_in*math.sin(t)*math.cos(p), cy + ry_in*math.sin(t)*math.sin(p), cz + rz_in*math.cos(t))))
               verts.append(Vector((cx + rx_out*math.sin(t)*math.cos(p), cy + ry_out*math.sin(t)*math.sin(p), cz + rz_out*math.cos(t))))
       inside = [v for v in verts if (v - bvh.find_nearest(v)[0]).dot(bvh.find_nearest(v)[1]) < -0.001]
       min_d = min(bvh.find_nearest(v)[3] for v in verts)
       return len(inside), min_d

   ins_l, d_l = eval_p(0.35, -0.25, 0.98, 0.16, 0.17, 0.14, -0.25*math.pi, 0.55*math.pi)
   ins_r, d_r = eval_p(-0.35, -0.25, 0.98, 0.16, 0.17, 0.14, 0.45*math.pi, 1.25*math.pi)
   print(f'L: inside={ins_l}, min_dist={d_l:.4f}m')
   print(f'R: inside={ins_r}, min_dist={d_r:.4f}m')
   assert ins_l == 0 and ins_r == 0, 'Must have 0 inside vertices'
   assert 0.020 <= d_l <= 0.035 and 0.020 <= d_r <= 0.035, 'Clearance must be in [0.020, 0.035]m'
   print('PROPOSED PARAMETERS VERIFIED PASS!')
   "
   ```
   *Expected Output*: `L: inside=0, min_dist=0.0315m`, `R: inside=0, min_dist=0.0315m`, `PROPOSED PARAMETERS VERIFIED PASS!`.

2. **Verify Signed Volume Symmetry & Positivity**:
   ```bash
   python3 -c "
   import math, numpy as np
   def make_p(side):
       cx = 0.35 if side == 'L' else -0.35
       p_min, p_max = (-0.25*math.pi, 0.55*math.pi) if side == 'L' else (0.45*math.pi, 1.25*math.pi)
       verts, og, ig = [], [], []
       for i in range(6):
           t = 0.08*math.pi + (i/5)*0.40*math.pi
           ir, or_ = [], []
           for j in range(8):
               p = p_min + (j/7)*(p_max - p_min)
               ir.append(len(verts)); verts.append((cx + 0.185*math.sin(t)*math.cos(p), -0.25 + 0.195*math.sin(t)*math.sin(p), 0.98 + 0.165*math.cos(t)))
               or_.append(len(verts)); verts.append((cx + 0.194*math.sin(t)*math.cos(p), -0.25 + 0.204*math.sin(t)*math.sin(p), 0.98 + 0.174*math.cos(t)))
           ig.append(ir); og.append(or_)
       faces = []
       for i in range(5):
           for j in range(7):
               faces.append((og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1]))
               faces.append((ig[i][j], ig[i][j+1], ig[i+1][j+1], ig[i+1][j]))
       for j in range(7):
           faces.append((ig[0][j], og[0][j], og[0][j+1], ig[0][j+1]))
           faces.append((ig[-1][j], ig[-1][j+1], og[-1][j+1], og[-1][j]))
       for i in range(5):
           faces.append((ig[i][0], ig[i+1][0], og[i+1][0], og[i][0]))
           faces.append((ig[i][-1], og[i][-1], og[i+1][-1], ig[i+1][-1]))
       v_arr = np.array(verts)
       vol = sum(np.dot(v_arr[f[0]], np.cross(v_arr[f[k]], v_arr[f[k+1]])) / 6.0 for f in faces for k in range(1, len(f)-1))
       return vol
   vl, vr = make_p('L'), make_p('R')
   print(f'V_L = {vl:.8f}, V_R = {vr:.8f}')
   assert vl > 0 and vr > 0 and abs(vl - vr) < 1e-6
   print('POSITIVE VOLUME VERIFIED PASS!')
   "
   ```
   *Expected Output*: `V_L = 0.00068428, V_R = 0.00068428`, `POSITIVE VOLUME VERIFIED PASS!`.

3. **Verify Full Pytest Suite**:
   ```bash
   pytest -v tests/test_bear_anatomy.py
   ```
   *Expected Output*: All tests pass with exit code 0.
