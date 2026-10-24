# Empirical Challenge Report — Challenger M2.2: Sash Clearance, Z-Fighting & Rigify Skinning

**Agent**: Challenger M2.2 (`teamwork_preview_critic`, `teamwork_preview_specialist`)  
**Target Milestone**: M2 (Organic Dress Drapery, Bodice Sculpting & Conforming Sash)  
**Evaluated Artifacts**: `src/morphomesh/wardrobe.py`, `tests/test_wardrobe_m2.py`, `tests/test_wardrobe.py`  
**Test Suite Created**: `tests/test_challenger_m2_sash.py`  
**Timestamp**: 2026-09-07T15:10:00Z  
**Verdict**: **`REQUEST_CHANGES`**

---

## 1. Executive Summary

Challenger M2.2 performed exhaustive empirical stress testing on the waist sash, 3D bow knot, ribbon streamers, organic skirt drapery, and Rigify 163 DEF skinning implementation in `src/morphomesh/wardrobe.py`.

### Verdict Summary
While the Rigify DEF skinning normalization (100% vertex coverage, 0 orphans, 0 negative weights) and the volumetric hollow bow loops (closed 2-manifold, volume $> 10\,\text{cm}^3$) are robustly implemented, **four confirmed empirical defects** were discovered:
1. **CRITICAL**: 100% of organic skirt faces (1440/1440) possess **inverted (inward-pointing) normals** due to reversed quad vertex winding order in `generate_dress_organic_skirt`.
2. **HIGH**: The 3D barrel cuff knot has **unclosed caps with 8 open boundary edges** (missing the 3rd quad on top and bottom), violating manifold topology and leaving two 4-vertex holes.
3. **HIGH**: The posterior waist sash ring at $Z = 1.0275\text{m}$ **penetrates the flared organic skirt** (clearance $-0.06\text{mm}$, with adjacent vertices at $+0.16\text{mm}$ to $+0.92\text{mm} < 2.0\text{mm}$), causing mesh intersection and Z-fighting along the lower lumbar waistband.
4. **MEDIUM**: The 45° haute-couture bias cut on ribbon streamer tips is **dead code** evaluating identically to $0.0\text{mm}$ due to algebraic cancellation `(1.0 - t) == 0.0` at $t=1.0$.

---

## 2. Empirical Stress Test Findings & Bug Reproductions

### Defect 1 (CRITICAL): Inverted Normal Orientation on 100% of Organic Skirt Faces

- **Location**: `src/morphomesh/wardrobe.py`, lines 915–921 (`generate_dress_organic_skirt`).
- **Code**:
  ```python
  for r in range(rings_count - 1):
      for i in range(sectors):
          v_bl = rings[r][i]
          v_br = rings[r][i + 1]
          v_tr = rings[r + 1][i + 1]
          v_tl = rings[r + 1][i]
          mesh.add_quad(v_bl, v_br, v_tr, v_tl)
  ```
- **Empirical Observation**:
  In `generate_dress_organic_skirt`, rings are generated descending from waist ($r=0, Z=1.030\text{m}$) down to the hem ($r=15, Z=0.520\text{m}$). Therefore, ring index $r$ is physically above $r+1$. Looking at the mesh from the outside:
  - $v_{\text{bl}} = \text{rings}[r][i]$ (top-left)
  - $v_{\text{br}} = \text{rings}[r][i+1]$ (top-right)
  - $v_{\text{tr}} = \text{rings}[r+1][i+1]$ (bottom-right)
  - $v_{\text{tl}} = \text{rings}[r+1][i]$ (bottom-left)
  This traversal ($v_{\text{bl}} \to v_{\text{br}} \to v_{\text{tr}} \to v_{\text{tl}}$) is **clockwise**.
  Under the standard right-hand rule, clockwise winding produces surface normals pointing **inward toward character body**:
  ```
  Skirt total faces: 1440
  Outward-pointing faces: 0
  Inward-pointing (inverted) faces: 1440 (100.0%)
  ```
- **Blast Radius**: Direct violation of `ORIGINAL_REQUEST.md` line 222 ("không có inverted normals"). In Blender EEVEE/Cycles, inverted normals cause backface culling blackouts, inverted PBR Charlie sheen highlights, and broken shadow bias.
- **Recommended Remediation**: Reverse vertex winding to counter-clockwise:
  ```python
  mesh.add_quad(v_bl, v_tl, v_tr, v_br)
  ```

---

### Defect 2 (HIGH): Incomplete Caps on 3D Barrel Cuff Knot (Non-Manifold Boundary Edges)

- **Location**: `src/morphomesh/wardrobe.py`, lines 641–648 (`generate_dress_waist_sash`).
- **Code**:
  ```python
  # Closed caps for 3D manifold knot
  # Bottom cap
  mesh.add_quad(knot_rings[0][0], knot_rings[0][7], knot_rings[0][6], knot_rings[0][1])
  mesh.add_quad(knot_rings[0][1], knot_rings[0][6], knot_rings[0][5], knot_rings[0][2])
  # Top cap
  mesh.add_quad(knot_rings[3][0], knot_rings[3][1], knot_rings[3][6], knot_rings[3][7])
  mesh.add_quad(knot_rings[3][1], knot_rings[3][2], knot_rings[3][5], knot_rings[3][6])
  ```
- **Empirical Observation**:
  Each knot ring contains 8 vertices (indices 0, 1, 2, 3, 4, 5, 6, 7).
  Capping an 8-gon with quads requires 3 quads:
  - Quad 1: `(0, 7, 6, 1)`
  - Quad 2: `(1, 6, 5, 2)`
  - Quad 3: `(2, 5, 4, 3)` — **OMITTED!**
  Similarly on the top cap, `(2, 3, 4, 5)` is **OMITTED**.
  Empirical edge traversal on `knot_faces` reveals 8 boundary edges:
  ```
  Edge (122, 123): relative (2, 3) count = 1
  Edge (123, 124): relative (3, 4) count = 1
  Edge (124, 125): relative (4, 5) count = 1
  Edge (122, 125): relative (2, 5) count = 1
  Edge (146, 147): relative (26, 27) count = 1
  Edge (147, 148): relative (27, 28) count = 1
  Edge (148, 149): relative (28, 29) count = 1
  Edge (146, 149): relative (26, 29) count = 1
  ```
- **Blast Radius**: The knot is non-manifold and has two gaping 4-vertex quadrilateral holes at the dorsal side of the knot, directly contradicting the worker's claims of "closed caps for 3D manifold knot".
- **Recommended Remediation**: Add the missing 3rd quad to both caps:
  ```python
  # Bottom cap
  mesh.add_quad(knot_rings[0][0], knot_rings[0][7], knot_rings[0][6], knot_rings[0][1])
  mesh.add_quad(knot_rings[0][1], knot_rings[0][6], knot_rings[0][5], knot_rings[0][2])
  mesh.add_quad(knot_rings[0][2], knot_rings[0][5], knot_rings[0][4], knot_rings[0][3])
  # Top cap
  mesh.add_quad(knot_rings[3][0], knot_rings[3][1], knot_rings[3][6], knot_rings[3][7])
  mesh.add_quad(knot_rings[3][1], knot_rings[3][2], knot_rings[3][5], knot_rings[3][6])
  mesh.add_quad(knot_rings[3][2], knot_rings[3][3], knot_rings[3][4], knot_rings[3][5])
  ```

---

### Defect 3 (HIGH): Posterior Waist Sash Penetration & Z-Fighting at Skirt Junction

- **Location**: `src/morphomesh/wardrobe.py`, lines 548–570 (`generate_dress_waist_sash`).
- **Code**:
  ```python
  z_center = 1.050 * s
  z_bottom = z_center - belt_width * 0.5 * s  # = 1.0275 * s
  ...
  rx_b, ry_b, yo_can = compute_dress_waist_radii(z_curr, s=s, k_w=k_w, k_c=k_c, clearance=clearance)
  rx = rx_b + 0.0045 * s
  ry = ry_b + 0.0045 * s
  yo = yo_can
  ```
- **Empirical Observation**:
  1. The bottom sash ring is positioned at $Z = 1.0275\cdot s$, which is below the bodice bottom boundary ($Z_{\text{bot}} = 1.030\cdot s$).
  2. The skirt waistband begins at $Z = 1.030\cdot s$ and flares outward towards the gluteal/buttocks region ($Y$ expands backward rapidly below $Z=1.030\cdot s$).
  3. The sash envelope has a forward shift `yo = -0.007 * s`, which pulls the posterior sash ring forward by 7mm toward the spine.
  4. At $Z = 1.0275\cdot s$ on the posterior midline ($\theta = \pi/2$):
     - Skirt posterior surface interpolates to $Y = 0.10556\text{m}$.
     - Sash vertex 6 is at $Y = 0.10550\text{m}$.
     - Clearance = $-0.06\text{mm}$ (penetration!).
     - Adjacent posterior vertices 4, 5, 7, 8 have clearances of $+0.92\text{mm}$, $+0.20\text{mm}$, $+0.16\text{mm}$, $+0.92\text{mm}$ — all failing the $>+2.0\text{mm}$ clearance specification.
- **Blast Radius**: Causes coplanar Z-fighting flickering and mesh penetration along the posterior waistband where the sash overlaps the flared skirt.
- **Recommended Remediation**:
  Align `z_bottom` to not descend below $z_{\text{waist}} = 1.030\cdot s$ (e.g. set $z_{\text{center}} = 1.0525\cdot s$ so $z_{\text{bottom}} = 1.030\cdot s$), or evaluate the combined $\max(r_{\text{bodice}}, r_{\text{skirt}})$ envelope when computing posterior sash radii.

---

### Defect 4 (MEDIUM): Ribbon Streamer Bias Cut Dead Code

- **Location**: `src/morphomesh/wardrobe.py`, line 773 (`generate_dress_waist_sash`).
- **Code**:
  ```python
  tip_bias = (0.008 * s * (1.0 - t)) if step == streamer_steps else 0.0
  ```
- **Empirical Observation**:
  At `step == streamer_steps`, $t = \text{step} / \text{streamer\_steps} = 1.0$.
  Therefore, $(1.0 - t) = 1.0 - 1.0 = 0.0$.
  Hence `tip_bias = 0.008 * s * 0.0 = 0.0`.
  For all other steps, `tip_bias = 0.0`.
  The calculated `tip_bias` is **identically 0.0 at all vertices**.
  The streamer tip points have $\Delta Z = 0.000000\text{m}$ (a flat perpendicular cut), making the claimed 45° haute-couture bias cut non-functional.
- **Recommended Remediation**:
  Change to:
  ```python
  tip_bias = (0.008 * s) if step == streamer_steps else 0.0
  ```

---

## 3. Verified Positive Implementation Elements

The empirical challenge confirms the following components are correctly implemented and meet authoritative standards:

1. **Rigify 163 DEF Skinning Integrity**:
   - **Bodice** (352 vertices): 100% assigned normalized weights ($\sum w_i = 1.0 \pm 10^{-4}$), 0 orphans, 0 negative weights. Assigned to `DEF-spine.001..004`, `DEF-shoulder.L/R`.
   - **Skirt** (784 vertices): 100% assigned normalized weights ($\sum w_i = 1.0 \pm 10^{-4}$), 0 orphans, 0 negative weights. Assigned to `DEF-spine`, `DEF-spine.001`, `DEF-thigh.L/R`, `DEF-thigh.L/R.001`.
   - **Sash** (350 vertices): 100% assigned normalized weights ($\sum w_i = 1.0 \pm 10^{-4}$), 0 orphans, 0 negative weights. Assigned to `DEF-spine`, `DEF-spine.001..002`, `DEF-thigh.L/R`, `DEF-thigh.L/R.001`.
   - In-memory `mesh.skin_weights` and `mesh.vertex_groups` are completely populated.
   - `get_wardrobe_script()` properly serializes `BONE_WEIGHTS` JSON and binds vertex groups in Blender.

2. **3D Volumetric Hollow Bow Loops**:
   - Both loops are closed 2-manifolds with 0 boundary edges and 0 non-manifold edges (144 edges each, all shared by exactly 2 faces).
   - Non-zero volume verified via Divergence Theorem:
     * Left loop: $10.52\,\text{cm}^3$ ($1.052 \times 10^{-5}\,\text{m}^3$)
     * Right loop: $13.77\,\text{cm}^3$ ($1.377 \times 10^{-5}\,\text{m}^3$)
   - 100% positive triangular face areas ($> 10^{-9}\,\text{m}^2$).

3. **Bodice-Sash Envelope Clearance (Anterior and Lateral)**:
   - Evaluated across 81 parameter sweeps ($scale \in [0.85, 1.15]$, $k_{\text{waist}} \in [0.85, 1.20]$, $k_{\text{chest}} \in [0.85, 1.20]$, $bust \in [0.80, 1.30]$):
   - All sash band vertices maintain $>+6.0\text{mm}$ clearance over the dress bodice envelope under `generate_organic_dress` + `generate_waist_sash_and_bow`.
   - Zero Z-fighting across anterior and lateral contours.

4. **Master Test Suites**:
   - `uv run pytest tests/test_wardrobe.py tests/test_wardrobe_m2.py -v`: **30 passed in 0.30s (100%)**.

---

## 4. Test Suite Implementation

An empirical test suite was implemented in `tests/test_challenger_m2_sash.py`:
- 11 passing tests validating the verified components.
- 4 strict `XFAIL` tests capturing the four empirical defects.
- Execution:
  ```powershell
  uv run pytest tests/test_challenger_m2_sash.py -v
  ```
  Output: `11 passed, 4 xfailed in 1.43s`.
