# Challenger Empirical Report: Milestone 4 Iteration 2 (Yu Nian An Master Asset)

**Challenger**: challenger_human_m4_iter2_1  
**Parent**: orchestrator_human_1 (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T03:29:00Z  
**Verdict**: **CHALLENGE** (Critical Defect in Dress-to-Body Clearance & Mesh Penetration)

---

## 1. Observation

### 1.1 Executed Pytest Test Suites
1. Command:
   ```powershell
   pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py -v
   ```
   Result:
   `31 passed in 6.66s` (100% pass).
2. Command:
   ```powershell
   pytest tests/test_m4_adversarial_geometry_stress.py -v
   ```
   Result:
   `11 passed in 28.03s` (100% pass).

### 1.2 Deep Empirical Live Blender 4.5.4 LTS Stress Audit
Authored and executed standalone stress harness `tests/test_adversarial_m4_empirical.py` against `output/yu_nian_an/Yu_Nian_An_Master.blend` (4,109,423 bytes, timestamp `2026-09-07 03:22:25`):
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background output/yu_nian_an/Yu_Nian_An_Master.blend --python tests/test_adversarial_m4_empirical.py
```

#### Test 1: Evaluated Hair Curve Layers Geometry (> 0 vertices) — PASS
- `Hair_Hime_Bangs`: 2,640 evaluated vertices, 2,420 evaluated polygons, active `GN_HairGroom` modifier, $Z \in [1.535\text{m}, 1.620\text{m}]$, $Y \in [-0.092\text{m}, -0.065\text{m}]$.
- `Hair_Hime_Sidelocks`: 2,976 evaluated vertices, 2,728 evaluated polygons, active `GN_HairGroom` modifier, $Z \in [1.350\text{m}, 1.585\text{m}]$, $Y \in [-0.040\text{m}, -0.005\text{m}]$.
- `Hair_Scalp_Crown`: 640 evaluated vertices, 320 evaluated polygons, active `GN_HairGroom` modifier, $Z \in [1.577\text{m}, 1.637\text{m}]$, $Y \in [-0.068\text{m}, 0.068\text{m}]$.
- `Hair_Back_Cascade`: 7,320 evaluated vertices, 6,710 evaluated polygons, active `GN_HairGroom` modifier, $Z \in [0.700\text{m}, 1.605\text{m}]$, $Y \in [0.035\text{m}, 0.122\text{m}]$.
- `Hair_Eyebrows`: 100 evaluated vertices, 50 evaluated polygons, active `GN_HairGroom` modifier, $Z \in [1.533\text{m}, 1.550\text{m}]$.
- `Hair_Eyelashes`: 100 evaluated vertices, 50 evaluated polygons, active `GN_HairGroom` modifier, $Z \in [1.518\text{m}, 1.520\text{m}]$.
- **Total evaluated hair mesh geometry**: 13,776 vertices and 12,548 polygons across 6 layers. 0 compilation errors or missing socket warnings in Blender 4.5.4 LTS.

#### Test 2: Butterfly 3D Non-Origin & Spatial Separation (Z > 0.8m) — PASS
- 10 butterflies found: `Prop_Butterfly_00` through `Prop_Butterfly_09`.
- All locations strictly non-origin: distance to origin ranges from $0.980\text{m}$ to $1.359\text{m}$ ($> 0.1\text{m}$).
- All elevations $Z > 0.8\text{m}$: elevations range from $Z = 0.880\text{m}$ to $Z = 1.280\text{m}$.
- Minimum pairwise 3D Euclidean distance: **$107.70\text{mm}$** between `Prop_Butterfly_00` and `Prop_Butterfly_04` (well above the $\ge 50\text{mm}$ requirement). Maximum distance is $1080.00\text{mm}$ across the hand span.

#### Test 3: Live Bone Rotation on Finger DEF Bones — PASS
Live pose rotation test on `Armature_Yu_Nian_An_Rigify` pose bones (rotation $+60^\circ$ on X, $+30^\circ$ on Z):
- `DEF-thumb.03.L`: String Max Disp = $263.08\text{mm}$ (14 verts moved), `Prop_Butterfly_00` Max Disp = $282.15\text{mm}$.
- `DEF-f_index.03.L`: String Max Disp = $496.70\text{mm}$ (14 verts moved), `Prop_Butterfly_01` Max Disp = $530.55\text{mm}$.
- `DEF-f_middle.03.L`: String Max Disp = $668.19\text{mm}$ (14 verts moved), `Prop_Butterfly_02` Max Disp = $723.05\text{mm}$.
- `DEF-f_ring.03.L`: String Max Disp = $432.27\text{mm}$ (14 verts moved), `Prop_Butterfly_03` Max Disp = $436.91\text{mm}$.
- `DEF-f_pinky.03.L`: String Max Disp = $201.35\text{mm}$ (14 verts moved), `Prop_Butterfly_04` Max Disp = $250.42\text{mm}$.
- `DEF-thumb.03.R`: String Max Disp = $150.67\text{mm}$ (14 verts moved), `Prop_Butterfly_05` Max Disp = $202.46\text{mm}$.
- `DEF-f_index.03.R`: String Max Disp = $412.00\text{mm}$ (14 verts moved), `Prop_Butterfly_06` Max Disp = $421.21\text{mm}$.
- `DEF-f_middle.03.R`: String Max Disp = $648.83\text{mm}$ (14 verts moved), `Prop_Butterfly_07` Max Disp = $698.78\text{mm}$.
- `DEF-f_ring.03.R`: String Max Disp = $407.84\text{mm}$ (14 verts moved), `Prop_Butterfly_08` Max Disp = $462.96\text{mm}$.
- `DEF-f_pinky.03.R`: String Max Disp = $176.81\text{mm}$ (14 verts moved), `Prop_Butterfly_09` Max Disp = $166.88\text{mm}$.
- Armature modifiers and vertex groups on both strings and butterflies successfully propagate dynamic joint rotation.

#### Test 4: Dress-to-Body Clearance Offset (>= +4mm with 0 penetration) — **FAIL**
- `Mesh_Dress_PleatedSkirt`: Min Signed Clearance = $+8.30\text{mm}$, Avg = $+86.99\text{mm}$, Penetrations = $0 / 400$ (PASS).
- `Mesh_Dress_WaistSash`: Min Signed Clearance = **$+3.14\text{mm}$**, Avg = $+24.69\text{mm}$, Penetrations = $0 / 112$ (**FAIL**: fails the $\ge +4.0\text{mm}$ threshold by $0.86\text{mm}$).
- `Mesh_Dress_Bodice`: Min Signed Clearance = **$-47.72\text{mm}$**, Avg = $+2.25\text{mm}$, Penetrations = **$45 / 140$ base vertices** ($90 / 280$ evaluated vertices with Solidify) (**CRITICAL FAIL**):
  - Vertex 66: $v = (0.000, -0.116, 1.140\text{m})$, body surface $= (0.001, -0.121, 1.139\text{m})$, penetration $= -4.91\text{mm}$.
  - Vertex 89: $v = (-0.041, -0.129, 1.220\text{m})$, body surface $= (-0.049, -0.144, 1.212\text{m})$, penetration $= -18.60\text{mm}$.
  - Vertex 90 (front bust center): $v = (0.000, -0.133, 1.220\text{m})$, body surface $= (0.003, -0.152, 1.209\text{m})$, penetration $= \mathbf{-22.07\text{mm}}$ ($2.2\text{cm}$ inside the chest).
  - Contour extremes on shoulder/chest junctions penetrate up to $-47.72\text{mm}$.

#### Test 5: Eye Mesh Anterior Y Coordinate & Front Camera Visibility — PASS
- Eye objects: `Mesh_Eye_Left_CorneaSclera`, `Mesh_Eye_Left_IrisPupil`, `Mesh_Eye_Right_CorneaSclera`, `Mesh_Eye_Right_IrisPupil`.
- Anterior Y coordinates:
  - Corneas: $\min Y = -0.13050\text{m}$, center $= (\pm 0.0310, -0.1180, 1.5430\text{m})$. Satisfies $\min Y \ge -0.135\text{m}$ (margin $+4.50\text{mm}$) and flush with orbital rims (not buried at $-0.065\text{m}$).
  - Irises: $\min Y = -0.12650\text{m}$, recessed naturally inside the anterior corneal chamber.
- Camera line of sight: Raycast from `Camera_Front` at $(0.0, -5.5, 0.825\text{m})$ to cornea centers confirms 0 cranial/facial occlusion.

---

## 2. Logic Chain

### 2.1 Why the Bodice Penetrates the Body
1. In `src/morphomesh/human_generator.py` lines 352-353:
   ```python
   mod_y = ry
   if vg_name == "chest" and sin_t < -0.3:
       mod_y = ry * (1.0 + 0.35 * (-sin_t - 0.3))
   ```
   At the bust center slice ($Z = 1.22\text{m}$), $r_y = 0.118\text{m}$ and $y_{\text{offset}} = -0.012\text{m}$. For $\sin\theta = -1$ (front anterior chest), the body radius scales by $1.0 + 0.35 \times 0.7 = 1.245$, reaching $Y_{\text{body}} = -0.118 \times 1.245 - 0.012 = -0.1589\text{m}$.
2. In `src/morphomesh/wardrobe.py` lines 102-123 (`generate_two_strap_bodice`):
   ```python
   (1.22 * s, 0.145 * s * k_c + clearance, 0.108 * s * k_c + clearance, -0.010 * s * k_c)
   ...
   py = ry * sin_t + yo
   ```
   For canonical scale with `clearance = 0.015`, $r_y = 0.108 + 0.015 = 0.123\text{m}$, and $y_{\text{offset}} = -0.010\text{m}$. For $\sin\theta = -1$, the front of the bodice reaches only $Y_{\text{bodice}} = -0.123 - 0.010 = -0.1330\text{m}$.
3. Comparing $Y_{\text{body}} = -0.1589\text{m}$ with $Y_{\text{bodice}} = -0.1330\text{m}$: because $-Y$ is anterior forward, the body protrudes **$25.9\text{mm}$** past the front surface of the dress bodice!
4. The same omission occurs at $Z = 1.14\text{m}$ (underbust) and $Z = 1.27\text{m}$ (upper chest), causing 45 out of 140 bodice vertices (32.1% of the bodice mesh) to be buried inside the female torso.

### 2.2 Why Upstream Verification Failed to Catch This
In Worker M4 Iteration 2's verification script `tests/verify_geometry_props_deep.py` lines 58-62:
```python
kd = mathutils.kdtree.KDTree(len(relevant_body_verts))
...
for bv in bodice_verts:
    co, index, dist = kd.find(bv)
    distances.append(dist)
min_dist = min(distances)
```
`kd.find()` returns the *unsigned Euclidean distance* $\|\vec{v}_{\text{bodice}} - \vec{v}_{\text{body}}\|$. For an internal vertex embedded inside the chest, its nearest neighbor is the exterior chest skin, yielding a positive distance ($4.88\text{mm}$). The worker asserted `assert min_dist >= 0.001`, mistaking internal embedding distance for exterior clearance offset.

---

## 3. Caveats

- All other deliverables are verified to be high-grade and robust:
  - Hair geometry nodes tree interface compiles cleanly in Blender 4.5.4 LTS with 13,776 evaluated vertices.
  - 10 butterflies are distributed in 3D mid-air flutter space with $> 100\text{mm}$ separation.
  - Finger DEF bone rotations dynamically propagate deformation to marionette strings and butterflies.
  - Eye corneas and irises are unburied, anatomically positioned at $Y = -0.1305\text{m}$, with clear line of sight from cameras.
  - Studio lights are constrained with `TRACK_TO` targeting bust center.
  - Master collection hierarchy has 7 tiers and 38 organized objects.
- Only the dress bodice and sash clearance fail the acceptance criteria.

---

## 4. Conclusion

**Verdict: CHALLENGE.**

The asset `output/yu_nian_an/Yu_Nian_An_Master.blend` cannot be certified as production-ready due to:
1. **Critical Defect**: 45 vertices of `Mesh_Dress_Bodice` penetrate inside the body mesh by up to $-22.1\text{mm}$ at the chest/breasts (minimum signed clearance is $-47.72\text{mm}$).
2. **Clearance Defect**: `Mesh_Dress_WaistSash` minimum clearance is $+3.14\text{mm}$, violating the $\ge +4.0\text{mm}$ requirement.

### Actionable Remediation for Worker M4 Iteration 3:
1. In `src/morphomesh/wardrobe.py` (`generate_two_strap_bodice`), update slice generation to incorporate the parametric chest protrusion factor matching `human_generator.py`:
   ```python
   # In loop over slice vertices:
   mod_ry = ry
   if z >= 1.10 * s and z <= 1.28 * s and sin_t < -0.3:
       mod_ry = ry * (1.0 + 0.38 * (-sin_t - 0.3))
   py = mod_ry * sin_t + yo
   ```
2. In `generate_dress_waist_sash`, increase base clearance from `0.016` to `0.018` or adjust radial scale so that `min_signed_clearance >= 0.0045m` (+4.5mm).
3. In `tests/verify_geometry_props_deep.py`, replace unsigned KDTree search with signed normal projection via `mathutils.bvhtree.BVHTree.find_nearest()`:
   ```python
   loc, normal, idx, dist = bvh.find_nearest(v)
   signed_dist = dist if (v - loc).dot(normal) >= 0 else -dist
   assert signed_dist >= 0.004, f"Penetration or insufficient clearance: {signed_dist*1000:.2f}mm"
   ```
4. Re-run master character assembly to regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend`.

---

## 5. Verification Method

To independently reproduce this finding:
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background output/yu_nian_an/Yu_Nian_An_Master.blend --python tests/test_adversarial_m4_empirical.py
```

### Invalidation Condition:
The CHALLENGE verdict is invalidated if and only if re-running `tests/test_adversarial_m4_empirical.py` in live Blender 4.5.4 LTS yields:
- `Mesh_Dress_Bodice`: `Min Signed Clearance >= +4.0 mm` AND `Penetrations == 0`.
- `Mesh_Dress_WaistSash`: `Min Signed Clearance >= +4.0 mm` AND `Penetrations == 0`.
- Exit code 0.