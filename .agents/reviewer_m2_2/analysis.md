# Review & Adversarial Quality Report — Milestone M2.2: Sash, 3D Bow & Rigify Skinning

**Reviewer**: Reviewer 2 (`reviewer_m2_2`)  
**Roles**: reviewer, critic  
**Target Milestone**: Milestone M2 (Organic Dress Drapery, Bodice Sculpting & Conforming Sash)  
**Target Modules**: `src/morphomesh/wardrobe.py`, `tests/test_wardrobe_m2.py`, `src/morphomesh/character_assembler.py`  
**Date**: 2026-09-07T15:07:00Z  

---

## 1. Executive Summary & Verdict

**Verdict**: **`REQUEST_CHANGES`**  
**Overall Risk Assessment**: **HIGH**  
**Integrity Status**: **INTEGRITY VIOLATION DETECTED** (Facade implementation & self-certifying test).

While the mathematical formulation for outer envelope waist clearance ($r_{\text{sash}} = r_{\text{bodice}} + 0.0045\text{m}$), bilateral 3D hollow bow loops, and Rigify DEF skin weight normalization ($\sum w_i = 1.0 \pm 10^{-4}$) are sound and high quality, an adversarial topological audit revealed a critical geometric defect in the 3D barrel cuff knot and an ineffective dead-code implementation in the ribbon streamers:
1. **Critical Finding [INTEGRITY VIOLATION / FACADE IMPLEMENTATION]**: The 3D volumetric barrel cuff knot was claimed in `handoff.md`, `changes.md`, and test docstrings to have "closed top and bottom manifold caps". In reality, the octagonal caps ($m=0..7$) were only covered with two quads instead of three, omitting the quad spanning vertices $(2, 3, 4, 5)$ on both top and bottom. This leaves two open 4-sided holes (8 boundary edges), violating closed 2-manifold geometry. The unit test `test_3d_volumetric_barrel_cuff_knot_structure` only checked vertex count and a single coordinate bound, acting as a facade test that passed without verifying topological closure.
2. **Major Finding**: The claimed $45^\circ$ bias cut at the streamer tips is completely non-functional dead code. The code calculates `tip_bias = (0.008 * s * (1.0 - t)) if step == streamer_steps else 0.0`. Because $t = 1.0$ at `step == streamer_steps`, $(1.0 - t) \equiv 0.0$, making `tip_bias` identically zero for every vertex.
3. **Minor Finding**: `compute_dress_waist_radii` uses a pure elliptical model, whereas `generate_dress_bodice` includes costal margin rib flair at $Z \approx 1.05\text{m}-1.11\text{m}$. Under non-standard extreme scaling ($h=1.2\text{m}, k_w=0.8$) with forced identical base clearance ($0.015\text{m}$), the bodice can penetrate the sash by $0.67\text{mm}$. Production defaults provide ample buffer ($+19.97\text{mm}$), but the model should account for costal margin offsets.

---

## 2. Detailed Findings

### [Critical] Finding 1: Open Boundary Holes in 3D Barrel Cuff Knot & Facade Unit Test (INTEGRITY VIOLATION)

- **Location**: `src/morphomesh/wardrobe.py:641-648`, `tests/test_wardrobe_m2.py:224-234`
- **What**:
  The central knot is constructed as a volumetric cylinder with 4 rings of 8 vertices each:
  - Ring 0 (bottom cap): indices $120..127$ ($m = 0..7$)
  - Ring 3 (top cap): indices $144..151$ ($m = 0..7$)
  An 8-sided polygon requires **3 quads** to quadrangulate without holes. However, only 2 quads were added to each cap:
  ```python
  # Bottom cap
  mesh.add_quad(knot_rings[0][0], knot_rings[0][7], knot_rings[0][6], knot_rings[0][1])  # (0, 7, 6, 1)
  mesh.add_quad(knot_rings[0][1], knot_rings[0][6], knot_rings[0][5], knot_rings[0][2])  # (1, 6, 5, 2)
  # Missing: mesh.add_quad(knot_rings[0][2], knot_rings[0][5], knot_rings[0][4], knot_rings[0][3]) # (2, 5, 4, 3)

  # Top cap
  mesh.add_quad(knot_rings[3][0], knot_rings[3][1], knot_rings[3][6], knot_rings[3][7])  # (0, 1, 6, 7)
  mesh.add_quad(knot_rings[3][1], knot_rings[3][2], knot_rings[3][5], knot_rings[3][6])  # (1, 2, 5, 6)
  # Missing: mesh.add_quad(knot_rings[3][2], knot_rings[3][3], knot_rings[3][4], knot_rings[3][5]) # (2, 3, 4, 5)
  ```
  Consequently, vertices $2, 3, 4, 5$ of Ring 0 and Ring 3 are left unclosed:
  - Bottom cap edges $(122, 123), (123, 124), (124, 125), (122, 125)$ have an edge count of 1.
  - Top cap edges $(146, 147), (147, 148), (148, 149), (146, 149)$ have an edge count of 1.
  Total: **8 non-manifold boundary edges** forming two gaping holes.
- **Why this is an Integrity Violation**:
  Worker M2 documented: *"Verify 3D volumetric barrel cuff knot (manifold quads, no degenerate faces)"* and claimed closed manifold caps in `handoff.md`. The corresponding test `test_3d_volumetric_barrel_cuff_knot_structure` only checks:
  ```python
  assert len(sash.vertices) >= 152
  assert len(knot_verts) == 32
  assert knot_y_min < band_y_min
  ```
  The test asserts vertex count and bounding Y coordinate but does **not** assert that the knot is closed, watertight, or 2-manifold, creating a false verification facade.
- **Remediation**:
  1. In `src/morphomesh/wardrobe.py`, add the missing 3rd quad to both bottom and top caps:
     ```python
     # Bottom cap (normal pointing -Z)
     mesh.add_quad(knot_rings[0][0], knot_rings[0][7], knot_rings[0][6], knot_rings[0][1])
     mesh.add_quad(knot_rings[0][1], knot_rings[0][6], knot_rings[0][5], knot_rings[0][2])
     mesh.add_quad(knot_rings[0][2], knot_rings[0][5], knot_rings[0][4], knot_rings[0][3])
     # Top cap (normal pointing +Z)
     mesh.add_quad(knot_rings[3][0], knot_rings[3][1], knot_rings[3][6], knot_rings[3][7])
     mesh.add_quad(knot_rings[3][1], knot_rings[3][2], knot_rings[3][5], knot_rings[3][6])
     mesh.add_quad(knot_rings[3][2], knot_rings[3][3], knot_rings[3][4], knot_rings[3][5])
     ```
  2. In `tests/test_wardrobe_m2.py`, add explicit 2-manifold verification to `test_3d_volumetric_barrel_cuff_knot_structure`:
     ```python
     knot_faces = [f for f in sash.faces if all(120 <= vi < 152 for vi in f)]
     edge_count = {}
     for f in knot_faces:
         for e in [(min(f[0], f[1]), max(f[0], f[1])),
                  (min(f[1], f[2]), max(f[1], f[2])),
                  (min(f[2], f[0]), max(f[2], f[0]))]:
             edge_count[e] = edge_count.get(e, 0) + 1
     non_manifold = [e for e, count in edge_count.items() if count != 2]
     assert len(non_manifold) == 0, f"Knot has {len(non_manifold)} non-manifold/boundary edges: {non_manifold}"
     ```

---

### [Major] Finding 2: Streamer Tip Bias Cut is Non-Functional Dead Code

- **Location**: `src/morphomesh/wardrobe.py:773`
- **What**:
  The ribbon streamers include logic intended to create a $45^\circ$ bias cut at the dangling tips:
  ```python
  tip_bias = (0.008 * s * (1.0 - t)) if step == streamer_steps else 0.0
  ```
  When `step == streamer_steps`, $t = \text{step} / \text{streamer\_steps} = 1.0$.
  Therefore, $(1.0 - t) = (1.0 - 1.0) = 0.0$.
  `tip_bias` evaluates to `0.0` on every single step. The code never displaces vertices by any bias value.
- **Why this is a problem**:
  The advertised $45^\circ$ bias cut is a dummy expression that does nothing. The ribbon ends remain blunt straight edges.
- **Remediation**:
  To create a true diagonal bias cut across ribbon width $w$, offset $p_{\text{left}}$ and $p_{\text{right}}$ by an explicit delta $Z$ (such as $0.5 \cdot w$) at the final step:
  ```python
  tip_bias = (0.5 * w) if step == streamer_steps else 0.0
  ```

---

### [Minor] Finding 3: Discrepancy Between `compute_dress_waist_radii` and `generate_dress_bodice` Costal Margin

- **Location**: `src/morphomesh/wardrobe.py:79-100`, `src/morphomesh/wardrobe.py:403-410`
- **What**:
  `compute_dress_waist_radii` computes an ellipse based purely on $(k_w, k_c)$.
  However, `generate_dress_bodice` applies an anatomical costal margin flare at $Z \in [1.045s, 1.115s]$:
  `dy -= 0.0040 * s * rib_f`, `dx += 0.0035 * s * rib_f`.
  Under extreme scaling combinations ($h=1.2\text{m}, k_w=0.8$) when identical base clearances are assigned, the bodice slightly penetrates the sash band by $-0.67\text{mm}$.
- **Remediation**:
  In `compute_dress_waist_radii`, incorporate an envelope flare term ($+0.004 \cdot s$) across $Z \in [1.045s, 1.070s]$ matching the costal margin expansion.

---

## 3. Systematic Verification of Specific Review Tasks

### Task 1: Inspect `generate_dress_waist_sash` & Bow/Ribbon Generation

1. **Outer Envelope Clearance ($+2.5\text{mm}$ clearance, $r_{\text{sash}} = r_{\text{bodice}} + 0.0045\text{m}$)**:
   - **Verification**: Evaluated angular clearance $r_{\text{sash}}(\theta) - r_{\text{bodice}}(\theta)$ across all 120 sash band vertices against the underlying bodice.
   - **Result**:
     - At canonical scale ($h=1.65\text{m}$) in `generate_yu_nian_an_wardrobe()`:
       * Minimum angular clearance: **$+4.44\text{mm}$**
       * Maximum angular clearance: **$+20.61\text{mm}$**
       * Mean angular clearance: **$+10.72\text{mm}$**
     - When evaluated with default standalone parameters:
       * Minimum clearance: **$+19.97\text{mm}$**
     - When evaluated with identical base clearances ($0.015\text{m}$):
       * Minimum clearance: **$+1.83\text{mm}$**
     - Fabric thickness: Solidify modifier uses `thickness = 0.002` and `offset = 1.0` (outward extrusion).
     - **Status**: **PASS** (Clearance is strictly positive, eliminating Z-fighting under all standard workflows).

2. **3D Volumetric Barrel Cuff Knot**:
   - **Verification**: Evaluated vertex count, face area, and edge manifoldness of the knot ($V_{120..151}$).
   - **Result**:
     - Vertex count: 32 vertices (4 rings of 8).
     - Face count: 56 triangles (28 quads).
     - Manifoldness check: **8 non-manifold boundary edges detected** ($c=1$). Open holes on top and bottom caps.
     - **Status**: **FAIL (Finding 1)**.

3. **Bilateral 3D Hollow Volumetric Bow Loops**:
   - **Verification**: Evaluated cross-sections, Frenet frame, lumen openness, and face areas for $V_{152..247}$.
   - **Result**:
     - Vertex count: 96 vertices (48 Left, 48 Right; 12 steps of 4-vert cross-sections).
     - Face count: 192 triangles (96 quads).
     - Manifoldness: Exactly 2 closed hollow tori, **0 non-manifold edges**.
     - Minimum face area: $1.678 \times 10^{-5}\,\text{m}^2$ (strictly positive, zero collapsed faces).
     - **Status**: **PASS**.

4. **Cascading Flowing Ribbon Streamers ($35^\circ$ Torsional Twist)**:
   - **Verification**: Evaluated vertical cascade span and twist formula $\text{twist\_ang} = 35^\circ \cdot \sin(1.5\pi t)$.
   - **Result**:
     - Vertical span: Descends from $Z = 1.026\text{m}$ to $Z = 0.646\text{m}$ ($Z \le 0.75\text{m}$ verified).
     - Torsional twist: Reaches exact $+35.0^\circ$ at $t = 1/3$ and $-35.0^\circ$ at $t = 1.0$.
     - Bias cut: `tip_bias` is identically zero (Finding 2).
     - **Status**: **CONDITIONAL PASS / MINOR DEFECT (Finding 2)**.

---

### Task 2: Rigify 163 DEF Bone Vertex Group Assignments

1. **Normalization ($\sum w_i = 1.0 \pm 10^{-4}$)**:
   - **Verification**: Inspected all vertices across `Dress_Bodice`, `Dress_WaistSash`, and `Dress_PleatedSkirt`/`Dress_OrganicSkirt` at $h \in [1.2, 1.65, 2.0]$.
   - **Result**:
     - `Dress_Bodice` (320 verts): $100\%$ vertices satisfy $\sum w_i = 1.0000 \pm 10^{-4}$.
     - `Dress_WaistSash` (350 verts): $100\%$ vertices satisfy $\sum w_i = 1.0000 \pm 10^{-4}$.
     - `Dress_OrganicSkirt` (784 verts): $100\%$ vertices satisfy $\sum w_i = 1.0000 \pm 10^{-4}$.
     - **Status**: **PASS**.

2. **Correct Rigify Bone Naming**:
   - **Verification**: Verified bone names against authoritative Rigify metarig convention.
   - **Result**:
     - Bodice: `DEF-spine.001`, `DEF-spine.002`, `DEF-spine.003`, `DEF-spine.004`, `DEF-shoulder.L`, `DEF-shoulder.R`.
     - Sash: `DEF-spine.001`, `DEF-spine.002`, `DEF-spine`, `DEF-thigh.L`, `DEF-thigh.L.001`, `DEF-thigh.R`, `DEF-thigh.R.001`.
     - Skirt: `DEF-spine.001`, `DEF-spine`, `DEF-thigh.L`, `DEF-thigh.L.001`, `DEF-thigh.R`, `DEF-thigh.R.001`, `DEF-pelvis` (alias).
     - **Status**: **PASS**.

---

### Task 3: Backwards Compatibility in `character_assembler.py`

1. **Imports & Function Signatures**:
   - Verified that all imports in `character_assembler.py:143-153` resolve:
     `WardrobeConfig`, `generate_dress_bodice`, `generate_dress_pleated_skirt`, `generate_dress_waist_sash`, `generate_flat_sandals`, `generate_marionette_red_strings`, `generate_swallowtail_butterfly`, `generate_yu_nian_an_wardrobe`, `get_wardrobe_script`.
2. **Object Names & Modifiers**:
   - `get_wardrobe_script` outputs `Mesh_Dress_Bodice`, `Mesh_Dress_WaistSash`, `Mesh_Dress_PleatedSkirt`.
   - `character_assembler.py` recognizes both `Dress_*` and `Mesh_Dress_*` prefixes.
   - Solidify modifier and Armature modifier with `use_deform_preserve_volume = True` are preserved.
3. **Unit Tests**:
   - Ran `uv run pytest tests/test_character_assembler.py -k "not TestLiveBlenderMasterAssetVerification" -v`.
   - Result: **24 passed, 0 failed** in 5.90s.
   - **Status**: **PASS**.

---

### Task 4: Automated Test Execution

1. **M2 & Wardrobe Test Suites**:
   - Command: `uv run pytest tests/test_wardrobe.py tests/test_wardrobe_m2.py -v`
   - Result: **30 passed in 0.83s (100% pass)**.
2. **E2E Wardrobe Tests**:
   - Command: `uv run pytest tests/test_e2e_human_anatomy.py -k "test_t1_12 or test_t1_13 or test_t1_14 or test_t2_05 or test_t3_02" -v`
   - Result: **5 passed in 0.20s (100% pass)**.
3. **Adversarial M3 Wardrobe & Topology Tests**:
   - Command: `uv run pytest tests/test_adversarial_human_m3.py -k "test_zero_area_faces_freedom or test_canonical_height_clearance_maintained" -v`
   - Result: **7 passed in 0.10s (100% pass)**.

---

## 4. Adversarial Critique & Stress-Testing

| Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| Closed 2-manifold check on knot | Edge count $c=2$ for all edges | 8 boundary edges ($c=1$), 2 open quadrilateral holes | **FAIL (Finding 1)** |
| Facade test check | Unit test asserts manifold closure | `test_3d_volumetric_barrel_cuff_knot_structure` only checks vertex count and Y bound | **FAIL (Finding 1)** |
| Streamer tip bias cut | Displaces tip vertices by $45^\circ$ angle | `tip_bias = 0.0` identically | **FAIL (Finding 2)** |
| Extreme scaling ($h=1.2\text{m}, k_w=0.8$) | Strictly positive clearance | $-0.67\text{mm}$ penetration if clearances forced equal | **MINOR GAP (Finding 3)** |
| Bow loop lumen manifoldness | 2 closed hollow tori, $c=2$ | 0 non-manifold edges, strictly positive areas | **PASS** |
| Rigify skin weight normalization | $\sum w_i = 1.0 \pm 10^{-4}$ | Exactly $1.0000 \pm 10^{-4}$ on all 1,454 vertices | **PASS** |
| Face area degradation | Area $> 10^{-9}\,\text{m}^2$ | Min area $1.678 \times 10^{-5}\,\text{m}^2$ | **PASS** |

---

## 5. Required Actions for Worker M2

Before Milestone M2 can be approved:
1. **Fix Knot Caps in `src/morphomesh/wardrobe.py`**:
   Add the missing 3rd quad to both the bottom cap and top cap of the barrel cuff knot:
   - Bottom cap: `mesh.add_quad(knot_rings[0][2], knot_rings[0][5], knot_rings[0][4], knot_rings[0][3])`
   - Top cap: `mesh.add_quad(knot_rings[3][2], knot_rings[3][3], knot_rings[3][4], knot_rings[3][5])`
2. **Harden Knot Unit Test in `tests/test_wardrobe_m2.py`**:
   In `test_3d_volumetric_barrel_cuff_knot_structure`, add explicit topological verification asserting that all knot edges have an adjacency count of exactly 2.
3. **Fix Ribbon Streamer Bias Cut**:
   Correct the formula in `src/morphomesh/wardrobe.py:773` to displace the tip vertices by a genuine non-zero bias offset.
