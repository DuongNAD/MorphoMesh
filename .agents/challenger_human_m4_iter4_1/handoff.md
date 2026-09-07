# Handoff Report: Milestone 4 Iteration 4 — Adversarial Challenge & Stress Audit

**Agent**: `challenger_human_m4_iter4_1`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Timestamp**: 2026-09-07T04:17:30+07:00  
**Target Asset**: Yu Nian An (余念安) Master Digital Human Asset (`output/yu_nian_an/Yu_Nian_An_Master.blend`)  
**Verdict**: **CHALLENGE**

---

## 1. Observation

### 1.1 Direct Observations from Live Blender 4.5.4 LTS & Empirical Test Harness

We authored and executed the independent test suite `tests/test_challenger_m4_iter4_empirical.py` directly against `output/yu_nian_an/Yu_Nian_An_Master.blend` using Blender 4.5.4 LTS (`C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`).

#### Audit 1: Deep BVH Occlusion & Normal-Dot Containment
Command:
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python tests/test_challenger_m4_iter4_empirical.py
```
Direct output:
```text
>>> [AUDIT 1] DEEP BVH OCCLUSION & NORMAL-DOT CONTAINMENT AUDIT
Portrait Camera Position: (0.0000, -2.0000, 1.5500)
Hair Layer               | Verts  | Inside | RayOccluded | Outside %  | Status
--------------------------------------------------------------------------------
Hair_Hime_Bangs          | 2640   | 0      | 0           | 100.0    % | PASS
Hair_Eyebrows            | 100    | 0      | 0           | 100.0    % | PASS
Hair_Eyelashes           | 100    | 0      | 0           | 100.0    % | PASS
Hair_Scalp_Crown         | 640    | 0      | 168         | 100.0    % | FAIL (Occluded)
Hair_Hime_Sidelocks      | 2976   | 0      | 0           | 100.0    % | PASS
Hair_Back_Cascade        | 7320   | 174    | 6722        | 97.6     % | PASS
```
Key observations:
- `Hair_Hime_Bangs`, `Hair_Eyebrows`, `Hair_Eyelashes`, and `Hair_Hime_Sidelocks` have **0 vertices buried** inside the body mesh (`dot >= 0`) and **0 vertices occluded** by the body mesh from `Camera_Portrait_85mm`.
- `Hair_Scalp_Crown` has **0 vertices buried** (`dot >= 0` on 100% of vertices), BUT **168 out of 640 vertices (26.25%) are occluded** from `Camera_Portrait_85mm` via BVH raycast (`hit_dist < ray_dist - 0.001`).
  - Coordinate range of occluded crown vertices: $Y \in [+0.0489\text{m}, +0.1091\text{m}]$, $Z \in [1.5970\text{m}, 1.6470\text{m}]$.
  - Nearest hit points on cranial mesh: $Y \in [-0.038\text{m}, +0.003\text{m}]$, $Z \approx 1.595\text{m}$.
  - Source code: `src/morphomesh/human_grooming.py` lines 328–338:
    ```python
    else:  # Crown: radius expanded to envelop cranium mesh without flared wings
        ang = u * 2.0 * math.pi
        r_cx = 0.095 * s
        r_cy = 0.102 * s
        x0 = r_cx * math.cos(ang)
        y0 = r_cy * math.sin(ang) + 0.005 * s
        z0 = z_crown + 0.002 * s
        tip_x = x0 * 1.02
        tip_y = y0 * 1.02
        tip_z = z0 - 0.050 * s
    ```

#### Audit 2: Garment Signed Clearance & BVH Overlaps
Direct output:
```text
>>> [AUDIT 2] GARMENT SIGNED CLEARANCE AUDIT (>= +4.0mm, 0 PENETRATIONS)
Garment Component        | Verts  | Min Dist    | Avg Dist    | Penetrations | Face Overlaps
--------------------------------------------------------------------------------
Mesh_Dress_Bodice        | 140    |    +6.48 mm |   +17.73 mm | 0            | 8             | FAIL (Overlaps)
Mesh_Dress_WaistSash     | 112    |    +6.82 mm |   +28.44 mm | 0            | 0             | PASS
Mesh_Dress_PleatedSkirt  | 400    |    +8.30 mm |   +86.99 mm | 0            | 0             | PASS
```
Deep surface sampling and BVH intersection analysis on `Mesh_Dress_Bodice`:
- Vertex minimum clearance: `+6.48 mm` (passes discrete vertex test).
- Vertex penetrations: `0 / 140`.
- **BVH Face Overlaps**: **8 intersecting face pairs detected** between `Mesh_Dress_Bodice` and `Yu_Nian_An_Body`.
  - Body Face 268 (center `(0.042, 0.071, 1.36)`) overlaps Bodice Face 198 & 199.
  - Body Face 244 (center `(0.064, 0.080, 1.335)`) overlaps Bodice Face 198 & 199.
  - Body Face 271 (center `(-0.042, 0.071, 1.36)`) overlaps Bodice Face 206 & 207.
  - Body Face 247 (center `(-0.064, 0.080, 1.335)`) overlaps Bodice Face 206 & 207.
- **Dense continuous surface sampling**: Minimum signed clearance on rear bodice straps is **`-2.64 mm`** (2.64mm penetration into the body volume).
  - Source code: `src/morphomesh/wardrobe.py` lines 158–164:
    ```python
    strap_pts = [
        (x_anchor, y_front, z_front),
        (x_anchor, y_front * 0.55, z_top - 0.015 * s),
        (x_anchor, 0.005 * s, z_top),
        (x_anchor, y_back * 0.65, z_top - 0.015 * s),
        (x_anchor, y_back, z_back),
    ]
    ```
  - Point 3: `(x_anchor, 0.105 * 0.65, 1.370)` = `(0.070, 0.06825, 1.370)`.
  - Point 4: `(x_anchor, 0.105, 1.260)` = `(0.070, 0.105, 1.260)`.
  - Between Point 3 and Point 4 is a single un-subdivided quad facet. The body mesh thoracic surface bulges to $Y \approx 0.087\text{m}$ at $Z \approx 1.32\text{m}$. The flat polygon chord passes through $Y \approx 0.0865\text{m}$, creating a physical intersection of $-2.64\text{mm}$.

#### Audit 3: Live Rigging & Props Kinematics
Direct output:
```text
>>> [AUDIT 3] LIVE RIGGING & PROPS KINEMATICS AUDIT

  --- [3a] Proximal String Root to Bone Tail Alignment (< 2.0mm) ---
  Cord 00 -> DEF-thumb.03.L  : root gap = 1.0000 mm
  Cord 01 -> DEF-f_index.03.L: root gap = 1.0000 mm
  Cord 02 -> DEF-f_middle.03.L: root gap = 1.0000 mm
  Cord 03 -> DEF-f_ring.03.L : root gap = 1.0000 mm
  Cord 04 -> DEF-f_pinky.03.L: root gap = 1.0000 mm
  Cord 05 -> DEF-thumb.03.R  : root gap = 1.0000 mm
  Cord 06 -> DEF-f_index.03.R: root gap = 1.0000 mm
  Cord 07 -> DEF-f_middle.03.R: root gap = 1.0000 mm
  Cord 08 -> DEF-f_ring.03.R : root gap = 1.0000 mm
  Cord 09 -> DEF-f_pinky.03.R: root gap = 1.0000 mm

  --- [3b] Butterfly Spatial Separation (Non-Origin, Z > 0.8m, Separation >= 50mm) ---
  Butterflies Count: 10 | Min Pairwise Separation: 107.70 mm between Prop_Butterfly_00 & Prop_Butterfly_04

  --- [3c] Dynamic Deformation under 45° and 60° Finger DEF Rotations ---
  45° Rotations:
    DEF-thumb.03.L   : String Disp = 211.32 mm | Butterfly Disp = 234.47 mm | PASS
    DEF-f_index.03.L : String Disp = 390.30 mm | Butterfly Disp = 426.30 mm | PASS
    DEF-f_middle.03.L: String Disp = 515.68 mm | Butterfly Disp = 555.91 mm | PASS
    DEF-f_ring.03.L  : String Disp = 381.72 mm | Butterfly Disp = 392.68 mm | PASS
    DEF-f_pinky.03.L : String Disp = 154.64 mm | Butterfly Disp = 190.59 mm | PASS
    DEF-thumb.03.R   : String Disp =  43.96 mm | Butterfly Disp =  74.86 mm | PASS
    DEF-f_index.03.R : String Disp = 228.00 mm | Butterfly Disp = 246.29 mm | PASS
    DEF-f_middle.03.R: String Disp = 459.91 mm | Butterfly Disp = 504.22 mm | PASS
    DEF-f_ring.03.R  : String Disp = 283.58 mm | Butterfly Disp = 327.04 mm | PASS
    DEF-f_pinky.03.R : String Disp =  72.02 mm | Butterfly Disp =  95.74 mm | PASS
  60° Rotations:
    Max string displacement up to 609.00 mm; butterfly displacement up to 655.72 mm across all 10 digits.
```

#### Audit 4: Execution of Assigned Pytest Command
Command:
```powershell
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_adversarial_character_assembler.py tests/verify_master_blend_deep.py -v
```
Verbatim error:
```text
=================================== ERRORS ====================================
_____________ ERROR collecting tests/verify_master_blend_deep.py ______________
ImportError while importing test module 'E:\tool\mcp\MorphoMesh\tests\verify_master_blend_deep.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Users\Admin\AppData\Local\Programs\Python\Python311\Lib\importlib\__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\verify_master_blend_deep.py:3: in <module>
    import bpy
E   ModuleNotFoundError: No module named 'bpy'
=========================== short test summary info ===========================
ERROR tests/verify_master_blend_deep.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 0.13s ===============================
```
- When run individually:
  - `pytest tests/test_adversarial_character_assembler.py -v`: **7 passed in 5.43s** (100% pass).
  - `blender.exe --background output/yu_nian_an/Yu_Nian_An_Master.blend --python tests/verify_master_blend_deep.py`: **OVERALL CRITICAL VERIFICATION PASS: True** (Exit code 0).

---

## 2. Logic Chain

1. **Bodice Back Strap Penetration**:
   - *Observation*: `bvh_b.overlap(bvh_d)` yields 8 intersecting face pairs. Dense barycentric sampling along the back strap quad facets (Bodice faces 198, 199, 206, 207) finds points with signed distance $s_{\text{dist}} = -2.64\text{mm}$ relative to the body surface.
   - *Logic*: The discrete vertices of `Mesh_Dress_Bodice` were placed with $+6.48\text{mm}$ clearance at $Z=1.37\text{m}$ (shoulder blade apex) and $Z=1.26\text{m}$ (mid-back rim). However, because no intermediate edge ring exists between $Z=1.37\text{m}$ and $Z=1.26\text{m}$, the planar polygon chord forms a straight line segment. The human thoracic kyphosis curves outward between these elevations ($Y \approx 0.087\text{m}$ at $Z \approx 1.32\text{m}$), penetrating through the strap polygon by up to $2.64\text{mm}$.
   - *Conclusion*: `Mesh_Dress_Bodice` fails the continuous minimum clearance requirement ($\ge +4.0\text{mm}$ with 0 penetrations).

2. **Crown Scalp Frontal Occlusion**:
   - *Observation*: BVH raycasting from `Camera_Portrait_85mm` to `Hair_Scalp_Crown` vertices finds 168 occluded vertices ($26.25\%$). All 168 occluded vertices lie in the posterior hemisphere ($Y \in [0.0489\text{m}, 0.1091\text{m}]$).
   - *Logic*: `Hair_Scalp_Crown` is procedurally lofted as a full 360-degree cylinder ($0 \le \theta \le 2\pi$) surrounding the cranium. Because `Camera_Portrait_85mm` is positioned anteriorly at $Y = -2.0\text{m}$, the anterior cranial dome ($Y \in [-0.10\text{m}, 0.0\text{m}]$) lies directly along the line of sight between the camera and the posterior crown splines.
   - *Conclusion*: While 0 vertices are buried under normal-dot containment, `Hair_Scalp_Crown` strictly fails the literal requirement of 0 raycast occlusions from the portrait camera due to its 360-degree distribution.

3. **Pytest CLI Collection Failure**:
   - *Observation*: `pytest tests/test_adversarial_character_assembler.py tests/verify_master_blend_deep.py -v` crashes immediately with `ModuleNotFoundError: No module named 'bpy'`.
   - *Logic*: `tests/verify_master_blend_deep.py` was authored as a pure Blender script without a `try: import bpy` guard or a subprocess test runner wrapper. When pytest is given an explicit filepath argument, it attempts to import the module into the active Python environment, failing because `bpy` only exists inside Blender.
   - *Conclusion*: The test suite cannot be invoked as requested via standard `pytest` without triggering an import crash.

---

## 3. Caveats

1. **Crown Scalp Functionality**: Under normal-dot containment, `Hair_Scalp_Crown` achieves $100.0\%$ exterior clearance ($0$ buried vertices). The 168 occlusions from `Camera_Portrait_85mm` are caused by the natural self-occlusion of the skull when viewing the posterior half of a 360° scalp ring from a single frontal camera. If the intent was solely to ensure hair roots are not buried inside the skull, crown hair passes. However, strictly as specified in the dispatch ("Verify 0 vertices occluded on bangs, eyebrows, eyelashes, crown, and sidelocks!"), it fails.
2. **Discrete vs. Continuous Clearance**: At the vertex level, `Mesh_Dress_Bodice` exhibits $+6.48\text{mm}$ minimum distance with 0 penetrating vertices. The failure occurs purely at the polygon face interior due to coarse strap discretization over convex anatomy.

---

## 4. Conclusion

**Final Verdict**: **CHALLENGE**

The Yu Nian An master asset in `output/yu_nian_an/Yu_Nian_An_Master.blend` cannot be confirmed as fully robust due to:
1. **Critical Geometry Defect**: `Mesh_Dress_Bodice` back straps penetrate into the dorsal thoracic body mesh by up to $-2.64\text{mm}$ with 8 BVH face overlaps, violating the $\ge +4.0\text{mm}$ continuous clearance mandate.
2. **Camera Occlusion**: `Hair_Scalp_Crown` fails the 0 raycast occlusion requirement from `Camera_Portrait_85mm` (168 vertices occluded).
3. **Test Infrastructure**: `tests/verify_master_blend_deep.py` cannot be executed via `pytest` outside Blender.

### Recommended Remediation
1. **Subdivide Bodice Straps**: In `src/morphomesh/wardrobe.py` lines 158–164, insert an intermediate strap anchor point at the thoracic apex (e.g. `(x_anchor, y_back * 0.88, 1.32 * s)`) so the rear strap curves outward along the scapulae rather than cutting straight through the back.
2. **Re-evaluate Crown Occlusion Specification**: Either restrict crown hair to the anterior/dorsal crest ($\theta \in [0.8\pi, 2.2\pi]$) or clarify that posterior crown self-occlusion from a frontal camera is expected.
3. **Wrap Blender Script**: Add `try: import bpy ... except ImportError: bpy = None` guard and a `test_*` wrapper to `tests/verify_master_blend_deep.py`.

---

## 5. Verification Method

To independently reproduce and verify all observations and failures:

1. **Run Empirical Challenger Stress Test Suite**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python tests/test_challenger_m4_iter4_empirical.py
   ```
   *Expected Output*: Exits with code 2 (`CHALLENGE`), detailing the 168 crown occlusions and 8 bodice face overlaps.

2. **Reproduce Bodice -2.64mm Penetration Directly**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python-expr "import bpy, bmesh, mathutils; b = bpy.data.objects['Yu_Nian_An_Body']; d = bpy.data.objects['Mesh_Dress_Bodice']; bm_b = bmesh.new(); bm_b.from_mesh(b.data); bm_b.transform(b.matrix_world); bvh_b = mathutils.bvhtree.BVHTree.FromBMesh(bm_b); bm_d = bmesh.new(); bm_d.from_mesh(d.data); bm_d.transform(d.matrix_world); bm_d.faces.ensure_lookup_table(); min_d = min((d if (pt - loc).dot(norm) >= 0 else -d) for f in [bm_d.faces[i] for i in [198,199,206,207]] for pt in [sum((v.co for v in f.verts), mathutils.Vector())/len(f.verts)] for loc, norm, idx, d in [bvh_b.find_nearest(pt)]); print(f'Min Strap Clearance: {min_d*1000:.2f} mm'); assert min_d > 0.004, 'Bodice penetrating body!'"
   ```
   *Expected Result*: Prints `Min Strap Clearance: -2.64 mm` and raises `AssertionError`.

3. **Reproduce Pytest Collection Failure**:
   ```powershell
   & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_adversarial_character_assembler.py tests/verify_master_blend_deep.py -v
   ```
   *Expected Result*: Exits with code 1, reporting `ModuleNotFoundError: No module named 'bpy'`.
