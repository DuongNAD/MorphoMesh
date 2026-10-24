# Handoff Report — Challenger M2.2: Sash Clearance, Z-Fighting & Rigify Skinning

**Agent**: Challenger M2.2 (`teamwork_preview_critic`, `teamwork_preview_specialist`)  
**Roles**: critic, specialist  
**Recipient**: Parent Orchestrator (`c2422918-70a3-47d9-a8f9-883422a33af0`)  
**Timestamp**: 2026-09-07T15:15:00Z  
**Type**: Hard (Task Complete)  
**Explicit Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation

1. **Test Suite Execution & Results**:
   - Master Wardrobe Test Suite:
     ```powershell
     uv run pytest tests/test_wardrobe.py tests/test_wardrobe_m2.py -v
     ```
     Result: `30 passed in 0.30s` (100% pass rate).
   - Challenger M2.2 Empirical Stress Test Suite (`tests/test_challenger_m2_sash.py`):
     ```powershell
     uv run pytest tests/test_challenger_m2_sash.py -v
     ```
     Result: `11 passed, 4 xfailed in 1.43s`.
     * `test_contract_sash_clearance_parameter_sweep`: PASSED (81/81 parameter sweeps maintain $> 6.0\text{mm}$ clearance over bodice).
     * `test_default_wardrobe_sash_bodice_clearance_all_angles`: PASSED (min clearance $= 4.56\text{mm}$).
     * `test_empirical_posterior_skirt_sash_penetration_discovery`: XFAIL (reproduced $-0.06\text{mm}$ penetration at posterior waistband).
     * `test_costal_margin_flare_clearance_narrowing`: PASSED (verified positive clearance under costal margin flare).
     * `test_bow_loops_strictly_positive_volume`: PASSED (left loop $= 10.52\,\text{cm}^3$, right loop $= 13.77\,\text{cm}^3$).
     * `test_bow_loops_closed_2_manifold`: PASSED (0 boundary edges, 0 non-manifold edges).
     * `test_barrel_knot_manifold_closed_caps`: XFAIL (reproduced 8 unclosed boundary edges on knot caps).
     * `test_ribbon_streamer_cascade_trajectory`: PASSED (Z descends below $0.75\text{m}$, lateral flare $> 0.030\text{m}$).
     * `test_ribbon_streamer_tip_bias_cut`: XFAIL (reproduced $\Delta Z = 0.000\text{m}$ dead code on tip bias).
     * `test_organic_skirt_faces_outward_normals`: XFAIL (reproduced 1440/1440 faces with inverted normals).
     * `test_bodice_skin_weights_normalization_and_orphans`: PASSED (352/352 normalized, 0 orphans, 0 negative weights).
     * `test_skirt_skin_weights_normalization_and_orphans`: PASSED (784/784 normalized, 0 orphans, 0 negative weights).
     * `test_sash_skin_weights_normalization_and_orphans`: PASSED (350/350 normalized, 0 orphans, 0 negative weights).
     * `test_rigify_def_bones_schema_compliance`: PASSED (all assigned bones in DEF-spine, DEF-shoulder, DEF-thigh).
     * `test_wardrobe_script_bone_weights_and_solidify`: PASSED (AST valid, `solid_mod.offset = 1.0`).

2. **Empirical Code Observations**:
   - `src/morphomesh/wardrobe.py`:
     * Lines 915–921: `generate_dress_organic_skirt` constructs quads via `mesh.add_quad(v_bl, v_br, v_tr, v_tl)` where $r$ decreases downwards ($Z$ goes from $1.030\text{m}$ to $0.520\text{m}$). This clockwise order causes face normals to point inward (into the body). Dot product with character radial vector $\vec{c} \cdot \vec{n} < 0$ for all 1440 faces.
     * Lines 641–648: `generate_dress_waist_sash` adds only 2 quads for each 8-gon cap on the barrel knot. Vertices 2, 3, 4, 5 are omitted on both caps, leaving 8 boundary edges (`(122,123), (123,124), (124,125), (122,125), (146,147), (147,148), (148,149), (146,149)`).
     * Lines 548–570: Sash lowest ring is placed at $Z = 1.0275\cdot s$ with forward offset `yo = -0.007 * s`. At posterior angle $\theta = \pi/2$, sash vertex 6 ($Y = 0.10550\text{m}$) penetrates the flared skirt surface ($Y = 0.10556\text{m}$) by $-0.06\text{mm}$, with adjacent vertices 4, 5, 7, 8 having clearances of $+0.16\text{mm}$ to $+0.92\text{mm}$ ($< +2.0\text{mm}$).
     * Line 773: `tip_bias = (0.008 * s * (1.0 - t)) if step == streamer_steps else 0.0`. When `step == streamer_steps`, $t = 1.0 \implies 1.0 - t = 0.0 \implies \text{tip\_bias} = 0.0$ identically.

---

## 2. Logic Chain

1. **Organic Skirt Inverted Normals (Defect 1)**:
   - Observation: 1440/1440 skirt faces point toward $(-X, -Y)$.
   - Deduction: In `generate_dress_organic_skirt`, `r=0` is at $Z=1.030\text{m}$ (top) and `r=15` is at $Z=0.520\text{m}$ (bottom). The quad loop constructs `v_bl = rings[r][i]` (top left), `v_br = rings[r][i+1]` (top right), `v_tr = rings[r+1][i+1]` (bottom right), `v_tl = rings[r+1][i]` (bottom left).
   - In 3D space, this creates a clockwise winding. By the right-hand rule, $\vec{n} = (\vec{v}_{\text{br}} - \vec{v}_{\text{bl}}) \times (\vec{v}_{\text{tr}} - \vec{v}_{\text{bl}})$ points inward.
   - Inference: Inverted normals violate `ORIGINAL_REQUEST.md` line 222 ("không có inverted normals") and will produce rendering artifacts in Cycles/EEVEE.

2. **Barrel Knot Unclosed Caps (Defect 2)**:
   - Observation: 8 edges in `knot_faces` have an edge count of 1.
   - Deduction: An 8-vertex perimeter partitioned into quads requires 3 quads: $Q_1 = (0,7,6,1)$, $Q_2 = (1,6,5,2)$, $Q_3 = (2,5,4,3)$.
   - Lines 643–647 only define $Q_1$ and $Q_2$. $Q_3$ is omitted on both top and bottom.
   - Inference: The barrel knot is not a manifold closed shell, leaving two 4-vertex quadrilateral holes on the dorsal side of the knot.

3. **Posterior Sash Band Z-Fighting (Defect 3)**:
   - Observation: At $Z = 1.0275\cdot s$, sash vertex 6 has clearance $-0.06\text{mm}$ relative to the skirt.
   - Deduction: The sash band extends from $Z = 1.0275\cdot s$ to $1.0725\cdot s$. The skirt begins at $Z = 1.030\cdot s$ and flares outward towards the gluteals. The sash envelope includes a forward shift `yo = -0.007 * s`, pulling the posterior sash band 7mm forward towards the spine.
   - At $Z = 1.0275\cdot s$ on the posterior side, the skirt has flared to $Y = 0.10556\text{m}$, while the sash band is at $Y = 0.10550\text{m}$.
   - Inference: The sash band and skirt penetrate and Z-fight on the posterior waistband.

4. **Streamer Tip Bias Dead Code (Defect 4)**:
   - Observation: Streamer tip vertices have identical $Z$ values ($\Delta Z = 0.000\text{m}$).
   - Deduction: Line 773 evaluates `0.008 * s * (1.0 - t)` only at `step == streamer_steps`. At this step, $t = 1.0$, multiplying the expression by $0.0$.
   - Inference: The 45° bias cut never manifests in geometry.

---

## 3. Caveats

- **Scope of Inverted Normals**: The inverted normals are isolated to `Dress_OrganicSkirt` / `Dress_PleatedSkirt`. `Dress_Bodice` and `Dress_WaistSash` both possess 100% outward-facing normals.
- **Contract Robustness**: When used purely as specified in `PROJECT.md` (`generate_organic_dress` + `generate_waist_sash_and_bow`), anterior and lateral clearance exceeds $6.0\text{mm}$ across all 81 tested parameter configurations. Only the posterior junction below $Z=1.030\text{m}$ incurs penetration.
- **Skinning Quality**: The Rigify DEF skinning implementation is verified to be 100% compliant with zero defects.

---

## 4. Conclusion & Actionable Verdict

### Verdict: **`REQUEST_CHANGES`**

Milestone M2 cannot be approved in its current state due to the four identified defects. Worker M2 must remediate the following in `src/morphomesh/wardrobe.py`:

1. **Fix Organic Skirt Normals** (Line 921): Change quad winding to counter-clockwise:
   `mesh.add_quad(v_bl, v_tl, v_tr, v_br)`
2. **Fix Barrel Knot Caps** (Lines 644 & 648): Add the 3rd quad to both bottom and top caps:
   `mesh.add_quad(knot_rings[0][2], knot_rings[0][5], knot_rings[0][4], knot_rings[0][3])` (bottom)  
   `mesh.add_quad(knot_rings[3][2], knot_rings[3][3], knot_rings[3][4], knot_rings[3][5])` (top)
3. **Fix Posterior Sash Clearance**: Ensure the sash band does not descend below the skirt waistline ($Z \ge 1.030\cdot s$), or ensure posterior radius at ring 0 accommodates the flared skirt ($+2.5\text{mm}$ net clearance).
4. **Fix Ribbon Streamer Bias Cut** (Line 773): Remove the `(1.0 - t)` factor:
   `tip_bias = (0.008 * s) if step == streamer_steps else 0.0`

---

## 5. Verification Method

To independently reproduce the empirical challenger findings:

1. **Execute Challenger M2.2 Test Suite**:
   ```powershell
   uv run pytest tests/test_challenger_m2_sash.py -v
   ```
   *Expected Output*: `11 passed, 4 xfailed in ~1.5s`.
   The 4 XFAIL tests reproduce each of the 4 defects with strict assertion traces.

2. **Verify Inverted Normals on Organic Skirt**:
   ```powershell
   uv run python -c "from morphomesh.wardrobe import generate_dress_organic_skirt; s = generate_dress_organic_skirt(); print('Inward faces:', sum((v[0]*((v1[1]-v0[1])*(v2[2]-v0[2]) - (v1[2]-v0[2])*(v2[1]-v0[1])) + v[1]*((v1[2]-v0[2])*(v2[0]-v0[0]) - (v1[0]-v0[0])*(v2[2]-v0[2])) < 0) for f in s.faces for v0, v1, v2 in [(s.vertices[f[0]], s.vertices[f[1]], s.vertices[f[2]])] for v in [((v0[0]+v1[0]+v2[0])/3, (v0[1]+v1[1]+v2[1])/3)]))"
   ```
   *Expected Output*: `Inward faces: 1440` (100% inverted).

3. **Verify Barrel Knot Open Boundary Edges**:
   ```powershell
   uv run python -c "from collections import defaultdict; from morphomesh.wardrobe import generate_dress_waist_sash; s = generate_dress_waist_sash(); kf = [f for f in s.faces if all(120 <= i < 152 for i in f)]; ec = defaultdict(int); [ec.__setitem__(e, ec[e]+1) for f in kf for e in [(min(f[0],f[1]), max(f[0],f[1])), (min(f[1],f[2]), max(f[1],f[2])), (min(f[2],f[0]), max(f[2],f[0]))]]; print('Boundary edges:', sum(1 for c in ec.values() if c == 1))"
   ```
   *Expected Output*: `Boundary edges: 8`.
