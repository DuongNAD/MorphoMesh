# Handoff Report — Challenger M3-1 (Adversarial Clearance, Manifold & PBR Verification)

**Author**: Challenger M3-1 (`challenger_m3_1`)  
**Date**: 2026-09-05T17:00:00Z  
**Milestone**: M3 — High-Fidelity Organic PBR Shader Engine & War Armor Integration  
**Role**: Empirical Challenger (`critic`, `specialist`)  
**Parent Orchestrator**: `504d045c-25c5-48a2-a65a-2a5b368eafa7`  
**Verdict**: **REJECT** (Critical Topology, Inverted Normals & Scaling Collision Defects Found)

---

## 1. Observation

### 1.1 Defect 1: `Armor_Pauldron_R` Non-Manifold Topology in Blender (140 Open Boundary Edges)
- **File**: `src/morphomesh/armor.py`
- **Line 665**:
  ```python
  faces.append((og[i][j], og[i][j+1], og[i+1][j+1], og[i][j]))
  ```
  In `get_armor_blender_script()` subroutine `make_pauldron(side)`:
  For `side == 'R'`, the outer surface quad is generated with vertices `(og[i][j], og[i][j+1], og[i+1][j+1], og[i][j])`. The first and fourth vertex are identical (`og[i][j]`), instead of `og[i+1][j]`.
- **Empirical Execution in Headless Blender 5.2.1 LTS**:
  Command:
  ```bash
  /Applications/Blender.app/Contents/MacOS/Blender --background --python <audit_script>
  ```
  BMesh topology audit result on `Armor_Pauldron_R`:
  ```json
  {
    "Armor_Pauldron_R": {
      "vertex_count": 96,
      "edge_count": 258,
      "face_count": 94,
      "non_manifold_edge_count": 140,
      "zero_area_face_count": 0,
      "is_watertight": false,
      "edge_link_faces": {"1": 140, "2": 118}
    }
  }
  ```
  `Armor_Pauldron_R` in Blender has **140 non-manifold edges** (boundary edges with only 1 adjacent face). It is **not watertight** and violates the 2-manifold closed shell requirement.
  *(Note: In `generate_pauldron()` in Python line 175, it was written correctly as `outer_grid[i + 1][j]`. However, `get_armor_blender_script()`, which generates the actual Blender asset, had a critical indexing typo).*

---

### 1.2 Defect 2: `Armor_Backplate` Inverted Face Normals (Inside-Out Winding)
- **File**: `src/morphomesh/armor.py`
- **Lines 786–787** (Blender script) & **Lines 508–514** (Python generator):
  ```python
  # Outer surface quads
  for i in range(u_steps - 1):
      for j in range(v_steps - 1):
          faces.append((og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1]))
          faces.append((ig[i][j], ig[i][j+1], ig[i+1][j+1], ig[i+1][j]))
  ```
- **Vector Analysis**:
  In `make_backplate`, index `i` steps along $+y$ and index `j` steps along $+x$.
  The outer quad winding `(og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1])` traverses from $(0, 0)$ to $(0, +\Delta y)$ then to $(+\Delta x, +\Delta y)$.
  The cross product $(v_1 - v_0) \times (v_3 - v_0) = (0, \Delta y, 0) \times (\Delta x, 0, 0) = (0, 0, -\Delta x \Delta y)$.
  **Normal vector points in $-z$ (downward into the interior of the bear)** rather than outward $(+z)$.
- **Empirical Execution in Blender 5.2.1 LTS**:
  Signed volume computation over all faces via divergence theorem:
  ```
  Armor_Pauldron_L: Signed Volume = +0.001031 m^3
  Armor_Pauldron_R: Signed Volume = +0.016745 m^3
  Armor_Gorget:     Signed Volume = +0.001031 m^3
  Armor_Bracer_L:   Signed Volume = +0.000219 m^3
  Armor_Bracer_R:   Signed Volume = +0.000219 m^3
  Armor_Backplate:  Signed Volume = -0.003077 m^3
  ```
  `Armor_Backplate` has a **negative signed volume** ($-0.003077 \text{ m}^3$), confirming that all outward face normals are pointing inwards towards the bear.

---

### 1.3 Defect 3: Backplate Severe Penetration / Intersection Under Scaling (Scale 0.5x)
- **File**: `src/morphomesh/armor.py`
- **Lines 460–464** (`generate_backplate`) & **Line 765** (`get_armor_blender_script`):
  ```python
  nearby = [
      v[2]
      for v in bear_mesh.vertices
      if -0.15 <= v[1] <= 0.45 and abs(v[0]) <= 0.30 and v[2] >= 0.80
      and (v[0] - x) ** 2 + (v[1] - y) ** 2 <= 0.08 ** 2
  ]
  ```
- **Root Cause**:
  The coordinate bounding box for adaptive scapular hump sampling contains **unscaled constants**: `v[2] >= 0.80` and `(v[0]-x)**2 + (v[1]-y)**2 <= 0.08**2`.
  When `scale = 0.5`:
  The bear's highest dorsal vertex is at $z \approx 0.72\text{m} < 0.80\text{m}$.
  Therefore, `nearby` is **always empty (`[]`)**!
  The engine falls back to the default analytic profile:
  ```python
  midline_z = (1.170 - 0.025 * math.sin(math.pi * t_y)) * scale
  ```
  At `x = 0.0`, `y = -0.05` ($y_{\text{unscaled}} = -0.10$):
  - Backplate inner surface height: $z = 0.5975\text{m}$.
  - Bear's actual scapular hump height at that point: $z = 0.7120\text{m}$.
  - **The bear's hump protrudes through the backplate by $0.1145\text{m}$ (over 11 cm)!**
- **Empirical Clearance Measurements**:
  - In Python:
    `min_d = 0.0000m` (Exact vertex collision: Backplate vertex `(0.0, 0.075, 0.585)` collides with Bear vertex `(0.0, 0.075, 0.585)`).
  - In Blender:
    `measured_clearances["Armor_Backplate"] = 0.0050m < 0.015m` (Severe clearance failure).
  - Pauldrons at scale 0.5x:
    `min_d = 0.0144m < 0.015m` because $0.025 \times 0.5 = 0.0125\text{m}$, breaching the absolute $0.015\text{m}$ threshold.

---

### 1.4 Passing Elements Verified
1. **Zero-Area Faces**:
   All 6 plates in Blender 5.2.1 LTS have **zero degenerate faces** (min face area $\approx 2.2 \times 10^{-4}\text{ m}^2 > 10^{-7}\text{ m}^2$).
2. **PBR Principled BSDF v2 Shaders**:
   All 5 materials in Blender 5.2.1 LTS instantiate valid Principled BSDF v2 sockets:
   - `Mat_Armor_WeatheredSteel`: `Metallic == 1.0`, `Roughness == 0.42`.
   - `Mat_Armor_BrassTrim`: `Metallic == 1.0`, `Roughness == 0.32`.
   - `Mat_Bear_Skin_Nose`: `Coat Weight == 0.85` ($\ge 0.80$), `Roughness == 0.15`, `Metallic == 0.0`.
   - `Mat_Bear_Fur`: `Roughness == 0.85`, `Sheen Weight == 0.65`, `Subsurface Weight == 0.08`.
   - `Mat_Bear_Claws`: `Roughness == 0.38`, `Specular IOR Level == 0.50`.
3. **Canonical Scale 1.0 Clearance**:
   At scale 1.0, all 6 plates in Python and Blender achieve $d_{\min} \in [0.0250, 0.0359]\text{m} \ge 0.015\text{m}$.

---

## 2. Logic Chain

1. **Topological Invalidation (Requirement 2 Violation)**:
   - Worker M3 claimed: `Armor_Pauldron_R: 2-Manifold: True, Non-Manifold Edges: 0`.
   - Observation 1.1 shows that when executed in headless Blender 5.2.1 LTS via `get_armor_blender_script()`, line 665 has a typo `(og[i][j], og[i][j+1], og[i+1][j+1], og[i][j])` repeating `og[i][j]`.
   - This causes Blender's `from_pydata()` to construct collapsed quad faces, resulting in 140 non-manifold boundary edges.
   - Therefore, the claim of watertight 2-manifold armor shells in Blender is empirically false.

2. **Normal Orientation Invalidation**:
   - Outward face normal vectors are necessary for lighting, shading, baking, and collision detection.
   - Observation 1.2 proves that `Armor_Backplate` quads are wound clockwise from the outside view, generating downward-pointing normal vectors (signed volume $-0.003077\text{ m}^3$).
   - This causes inverted shading artifacts and invalid displacement/bumping.

3. **Scale Invariance Collapse (Requirements 1 & 5 Violation)**:
   - Worker M3 claimed guaranteed clearance $\ge 0.015\text{m}$ across proportional variations.
   - Observation 1.3 demonstrates that at scale $0.5\times$, unscaled filtering bounds (`v[2] >= 0.80`) fail to capture bear vertices.
   - This produces complete geometrical penetration ($d_{\min} = 0.0000\text{m}$), with the bear's scapular hump protruding 11cm through the backplate.
   - Pauldron clearance drops to $0.0144\text{m} < 0.015\text{m}$.

---

## 3. Caveats

- At canonical scale 1.0, clearances for all 6 plates in Python and Blender are within the expected range ($0.025 - 0.036\text{m}$).
- The PBR Principled BSDF v2 shader pipeline is fully compliant with Blender 5.2.1 LTS specifications.
- The defect in `Armor_Pauldron_R` exists in `get_armor_blender_script()`; in `generate_pauldron()` (Python `MeshGeometry`), line 175 was written correctly. Worker M3's tests passed only because they tested the Python `MeshGeometry` directly, failing to audit the BMesh topology of the generated Blender script.

---

## 4. Conclusion

**Verdict: REJECT**

Milestone M3 cannot be approved in its current state due to three critical, empirically confirmed defects:
1. `Armor_Pauldron_R` is non-manifold with **140 open boundary edges** in Blender.
2. `Armor_Backplate` has **inverted face normals** (negative signed volume).
3. Under scaling to $0.5\times$, `Armor_Backplate` **intersects and clips through the bear body** ($d_{\min} = 0.0000\text{m}$), and pauldron clearance drops below $0.015\text{m}$.

### Required Remediations for Worker M3:
1. In `src/morphomesh/armor.py` line 665:
   Change `faces.append((og[i][j], og[i][j+1], og[i+1][j+1], og[i][j]))`  
   To `faces.append((og[i][j], og[i][j+1], og[i+1][j+1], og[i+1][j]))`.
2. In `src/morphomesh/armor.py` lines 509 & 786:
   Reverse the vertex winding on outer backplate quads:
   Change `(og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1])`  
   To `(og[i][j], og[i][j+1], og[i+1][j+1], og[i+1][j])`.
   Reverse inner quads accordingly to point inward.
3. In `src/morphomesh/armor.py` lines 460–464 and 765–768:
   Scale all bounding box thresholds with `scale` (`sc`):
   `-0.15*sc <= v[1] <= 0.45*sc`, `abs(v[0]) <= 0.30*sc`, `v[2] >= 0.80*sc`, and search radius `(0.08*sc)**2`.
   Ensure pauldron minimum clearance is bounded below by $\max(0.015, \text{clearance} \times \text{scale})$ or fixed minimum.

---

## 5. Verification Method

To independently reproduce every finding and verify the defects:

1. **Run Challenger M3 Adversarial Pytest Suite**:
   ```bash
   pytest -v tests/test_m3_adversarial_materials_and_armor.py
   ```
   *Result*: 10/10 tests pass, confirming empirical reproduction of all 3 defects (Pauldron R 140 non-manifold edges, Backplate negative volume, and Scale 0.5x clipping).

2. **Run Headless Blender 5.2.1 LTS BMesh Topology Check**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy, bmesh
   from morphomesh.creature_generator import get_blender_generation_script
   from morphomesh.armor import ProceduralArmorEngine
   exec(get_blender_generation_script('Bear_Base_Mesh'))
   exec(ProceduralArmorEngine().get_armor_blender_script('Bear_Base_Mesh'))
   obj = bpy.data.objects['Armor_Pauldron_R']
   bm = bmesh.new(); bm.from_mesh(obj.data)
   nm = [e for e in bm.edges if not e.is_manifold or len(e.link_faces) != 2]
   print(f'CRITICAL: Armor_Pauldron_R has {len(nm)} non-manifold edges (is_watertight={len(nm)==0})')
   assert len(nm) == 140
   "
   ```

3. **Run Scale 0.5x Collision Check in Python**:
   ```bash
   python3 -c "
   from morphomesh.creature_generator import generate_bear_base_mesh, UrsineAnatomyConfig
   from morphomesh.armor import ProceduralArmorEngine
   bear = generate_bear_base_mesh(UrsineAnatomyConfig(scale=0.5)).mesh
   engine = ProceduralArmorEngine()
   plates = engine.generate_all_armor_plates(scale=0.5, bear_mesh=bear)
   m = engine.compute_clearance_metrics(plates['Armor_Backplate'], bear)
   print(f'CRITICAL: Backplate min distance at scale 0.5x is {m[\"min_distance\"]:.4f}m (collision!)')
   assert m['min_distance'] == 0.0
   "
   ```
