# Handoff Report — Explorer M2.1 Iteration 2: Skirt Normal Winding Order & Posterior Sash Clearance

**Agent**: Explorer M2.1 Iteration 2 (`teamwork_preview_critic`, `teamwork_preview_specialist`)  
**Roles**: explorer, synthesizer  
**Recipient**: Parent Orchestrator (`c2422918-70a3-47d9-a8f9-883422a33af0`)  
**Timestamp**: 2026-09-07T15:25:00Z  
**Type**: Hard (Task Complete)  
**Detailed Report**: `E:\tool\mcp\MorphoMesh\.agents\explorer_m2_it2_1\analysis.md`  

---

## 1. Observation

1. **Test Suite Baseline**:
   - Master Wardrobe Test Suite:
     ```powershell
     uv run pytest tests/test_wardrobe.py tests/test_wardrobe_m2.py -v
     ```
     Result: `30 passed in 0.29s`.
   - Challenger M2.2 Empirical Stress Suite:
     ```powershell
     uv run pytest tests/test_challenger_m2_sash.py -v
     ```
     Result: `11 passed, 4 xfailed in 1.40s`.
     - `test_empirical_posterior_skirt_sash_penetration_discovery`: XFAIL (reproduced $-0.064\text{mm}$ penetration at $Z = 1.0275\text{m}$, $\theta = \pi/2$).
     - `test_organic_skirt_faces_outward_normals`: XFAIL (reproduced 1440/1440 inverted faces, 0 outward).
     - `test_barrel_knot_manifold_closed_caps`: XFAIL (reproduced 8 open boundary edges).
     - `test_ribbon_streamer_tip_bias_cut`: XFAIL (reproduced $\Delta Z = 0.000\text{m}$ dead code).

2. **Codebase Observations in `src/morphomesh/wardrobe.py`**:
   - Lines 915–922 (`generate_dress_organic_skirt`):
     ```python
     for r in range(rings_count - 1):
         for i in range(sectors):
             v_bl = rings[r][i]
             v_br = rings[r][i + 1]
             v_tr = rings[r + 1][i + 1]
             v_tl = rings[r + 1][i]
             mesh.add_quad(v_bl, v_br, v_tr, v_tl)
     ```
     Ring $r=0$ is at waist ($Z=1.030\text{m}$) and $r=15$ is at hem ($Z=0.520\text{m}$). Therefore, `rings[r][i]` is Top-Left and `rings[r+1][i]` is Bottom-Left. The traversal `(v_bl, v_br, v_tr, v_tl)` is clockwise, causing normal cross product $\vec{n} = \vec{e}_1 \times \vec{e}_2$ to point into the character body (dot product with centroid $\vec{c}_{XY} \cdot \vec{n}_{XY} < 0$).
   - Lines 548–571 (`generate_dress_waist_sash`):
     Lowest ring sits at $Z_{\text{bottom}} = 1.0275\cdot s$ ($2.5\text{mm}$ below skirt waistline $1.030\cdot s$). The sash is offset forward by $yo = -0.007\cdot s$, while the skirt is centered at $(0, 0)$ and flares outward. At $\theta = \pi/2$, sash vertex 6 ($Y = 0.10550\text{m}$) penetrates the flared skirt ($Y = 0.10556\text{m}$) by $-0.064\text{mm}$, with adjacent vertices 4, 5, 7, 8 having clearances $< +2.0\text{mm}$.
   - Lines 641–648: Barrel knot defines only 2 quads per 8-gon end cap, omitting quads on vertices 2, 3, 4, 5 and leaving 8 unclosed boundary edges.
   - Line 773: `tip_bias = (0.008 * s * (1.0 - t)) if step == streamer_steps else 0.0`. Evaluated at $t=1.0$, multiplying by $0.0$ and disabling the $45^\circ$ bias cut.

---

## 2. Logic Chain

1. **Skirt Normal Vector Reversal**:
   - Observation: Ring index $r$ increases downward ($-Z$). Sector index $i$ advances counter-clockwise around $+Z$, which moves horizontally left-to-right when viewed from the exterior.
   - Geometric Mapping:
     - `rings[r][i]` $\implies$ Top-Left ($V_{\text{TL}}$)
     - `rings[r][i+1]` $\implies$ Top-Right ($V_{\text{TR}}$)
     - `rings[r+1][i+1]` $\implies$ Bottom-Right ($V_{\text{BR}}$)
     - `rings[r+1][i]` $\implies$ Bottom-Left ($V_{\text{BL}}$)
   - Clockwise sequence $(V_{\text{TL}}, V_{\text{TR}}, V_{\text{BR}}, V_{\text{BL}})$ produces inward normals:
     $$\vec{n}_1 = (V_{\text{TR}} - V_{\text{TL}}) \times (V_{\text{BR}} - V_{\text{TL}}) \implies \vec{c}_{XY} \cdot \vec{n}_1 < 0$$
   - To achieve counter-clockwise outward circulation:
     $$\text{Top-Left} \to \text{Bottom-Left} \to \text{Bottom-Right} \to \text{Top-Right}$$
     $$V_{\text{TL}} \to V_{\text{BL}} \to V_{\text{BR}} \to V_{\text{TR}}$$
     Using the existing variable names:
     $$\text{mesh.add\_quad}(v_{\text{bl}}, v_{\text{tl}}, v_{\text{tr}}, v_{\text{br}})$$
   - Verification: In isolated simulation, this flips all 1440 triangular faces to point strictly outward (1440 outward, 0 inward), passing `test_organic_skirt_faces_outward_normals` with 100% compliance. Shared diagonal $(V_{\text{TL}}, V_{\text{BR}})$ is preserved identically.

2. **Posterior Sash Band Clearance**:
   - Observation: Ring 0 ($Z = 1.0275\cdot s$) descends $2.5\text{mm}$ below the skirt waist ($1.030\cdot s$). At $\theta = \pi/2$, the skirt has flared outward to $Y = 0.10556\text{m}$, while sash vertex 6 sits at $Y = 0.10550\text{m}$.
   - Root Cause: Bodice forward offset $yo = -0.007\cdot s$ pulls the posterior sash 7mm forward, while the skirt is centered at $(0, 0)$.
   - Adjustment Formulation:
     - Radial expansion: $\Delta r = +0.0020\cdot s$ on both $rx$ and $ry$.
     - $Y$-offset shift: $\Delta yo = +0.0025\cdot s$ along $+Y$ (adjusting $yo$ from $-0.0070\cdot s$ to $-0.0045\cdot s$).
     - Lower-ring blend factor: $\text{flare}(u_z) = \max(0.0, 1.0 - 2.0 u_z)$ where $u_z = (z_{\text{curr}} - z_{\text{bottom}}) / (z_{\text{top}} - z_{\text{bottom}})$.
       - Ring 0 ($u_z = 0.00$): $\text{flare} = 1.00$ (full flare over skirt).
       - Ring 1 ($u_z = 0.25$): $\text{flare} = 0.50$ (smooth transition).
       - Rings 2, 3, 4 ($u_z \ge 0.50$): $\text{flare} = 0.00$ (unperturbed upper bodice fit).
   - Quantitative Outcome:
     - Posterior midline clearance: Increases from $-0.064\text{mm}$ to **$+4.44\text{mm}$** (exceeding $+2.5\text{mm}$ by $+1.94\text{mm}$).
     - All 24 vertices of Ring 0: Strictly $\ge +3.44\text{mm}$ clearance.
     - 75 parameter combinations: Strictly $\ge +3.33\text{mm}$ clearance.
     - Bodice sweep contract: Uncompromised at $+6.07\text{mm} \ge +5.0\text{mm}$.

---

## 3. Caveats

- **Normal Vector Scope**: Inverted normals are strictly confined to `generate_dress_organic_skirt` (`Dress_OrganicSkirt` and `Dress_PleatedSkirt`). `Dress_Bodice` and `Dress_WaistSash` already have 100% outward-facing normals.
- **Bodice Fit Invariance**: Modulating the lower sash ring adjustment by $\text{flare}(u_z) = \max(0.0, 1.0 - 2.0 u_z)$ ensures zero change to rings $u_z \ge 0.50$, preserving bodice clearance and preventing interference with the costal margin flare at $Z = 1.0725\cdot s$.

---

## 4. Conclusion & Actionable Code Proposals

The investigation confirms the exact mathematical solutions and provides drop-in replacement snippets for Worker M2:

### Proposal 1: Skirt Quad Face Winding Order
In `src/morphomesh/wardrobe.py`, line 921:
```python
<<<<
            mesh.add_quad(v_bl, v_br, v_tr, v_tl)
====
            mesh.add_quad(v_bl, v_tl, v_tr, v_br)
>>>>
```

### Proposal 2: Posterior Sash Band Clearance & Flared Skirt Transition
In `src/morphomesh/wardrobe.py`, lines 567–570:
```python
<<<<
        rx = rx_b + 0.0045 * s
        ry = ry_b + 0.0045 * s
        yo = yo_can
====
        # Smooth flare adjustment for lower rings transitioning over the flared skirt
        flare = max(0.0, 1.0 - 2.0 * u_z)
        rx = rx_b + 0.0045 * s + 0.0020 * s * flare
        ry = ry_b + 0.0045 * s + 0.0020 * s * flare
        yo = yo_can + 0.0025 * s * flare
>>>>
```

### Proposal 3: Barrel Knot Manifold Closed Caps
In `src/morphomesh/wardrobe.py`, lines 643–648:
```python
<<<<
    # Bottom cap
    mesh.add_quad(knot_rings[0][0], knot_rings[0][7], knot_rings[0][6], knot_rings[0][1])
    mesh.add_quad(knot_rings[0][1], knot_rings[0][6], knot_rings[0][5], knot_rings[0][2])
    # Top cap
    mesh.add_quad(knot_rings[3][0], knot_rings[3][1], knot_rings[3][6], knot_rings[3][7])
    mesh.add_quad(knot_rings[3][1], knot_rings[3][2], knot_rings[3][5], knot_rings[3][6])
====
    # Bottom cap
    mesh.add_quad(knot_rings[0][0], knot_rings[0][7], knot_rings[0][6], knot_rings[0][1])
    mesh.add_quad(knot_rings[0][1], knot_rings[0][6], knot_rings[0][5], knot_rings[0][2])
    mesh.add_quad(knot_rings[0][2], knot_rings[0][5], knot_rings[0][4], knot_rings[0][3])
    # Top cap
    mesh.add_quad(knot_rings[3][0], knot_rings[3][1], knot_rings[3][6], knot_rings[3][7])
    mesh.add_quad(knot_rings[3][1], knot_rings[3][2], knot_rings[3][5], knot_rings[3][6])
    mesh.add_quad(knot_rings[3][2], knot_rings[3][3], knot_rings[3][4], knot_rings[3][5])
>>>>
```

### Proposal 4: Streamer Bias Cut Fix
In `src/morphomesh/wardrobe.py`, line 773:
```python
<<<<
            tip_bias = (0.008 * s * (1.0 - t)) if step == streamer_steps else 0.0
====
            tip_bias = (0.008 * s) if step == streamer_steps else 0.0
>>>>
```

---

## 5. Verification Method

To independently verify the proposed solutions:

1. **Execute Isolated Full Test Verification Script**:
   ```powershell
   uv run python E:\tool\mcp\MorphoMesh\.agents\explorer_m2_it2_1\verify_fixes.py
   ```
   Expected output:
   ```
   TestSashClearanceAndZFighting: ALL 4 TESTS PASSED!
   TestBowKnotAndRibbonGeometry: ALL 5 TESTS PASSED!
   TestOrganicSkirtNormalsOrientation: ALL TESTS PASSED!
   TestRigifyDEFSkinningIntegrity: ALL 4 TESTS PASSED!

   *** ALL 14 TESTS IN CHALLENGER TEST SUITE PASSED 100% WITH ZERO FAILURES! ***
   ```

2. **Verify Skirt Face Normal Vectors Orientation**:
   ```powershell
   uv run python -c "from morphomesh.wardrobe import generate_dress_organic_skirt; s = generate_dress_organic_skirt(); print('Outward faces:', sum((v[0]*((v1[1]-v0[1])*(v2[2]-v0[2]) - (v1[2]-v0[2])*(v2[1]-v0[1])) + v[1]*((v1[2]-v0[2])*(v2[0]-v0[0]) - (v1[0]-v0[0])*(v2[2]-v0[2])) > 0) for f in s.faces for v0, v1, v2 in [(s.vertices[f[0]], s.vertices[f[1]], s.vertices[f[2]])] for v in [((v0[0]+v1[0]+v2[0])/3, (v0[1]+v1[1]+v2[1])/3)]))"
   ```
   Expected output after patch: `Outward faces: 1440` (100% outward).

3. **Verify Posterior Sash Clearance**:
   ```powershell
   uv run python -c "from morphomesh.wardrobe import generate_yu_nian_an_wardrobe; w = generate_yu_nian_an_wardrobe(); sash = w['Dress_WaistSash']; skirt = w['Dress_PleatedSkirt']; v6 = sash.vertices[6]; v0 = skirt.vertices[12]; v1 = skirt.vertices[61]; t = (v0[2] - v6[2]) / (v0[2] - v1[2]); y_sk = v0[1] + t * (v1[1] - v0[1]); print(f'Clearance: {(v6[1] - y_sk)*1000:.2f}mm')"
   ```
   Expected output after patch: `Clearance: 4.44mm` ($\ge +2.5	ext{mm}$).
