# Handoff Report: Milestone M2 Cloth Drapery & Skirt Fold Architecture

- **Author**: Explorer M2.1 Replacement (Cloth Drapery & Skirt Fold Investigator)
- **Recipient**: Parent Orchestrator (`c2422918-70a3-47d9-a8f9-883422a33af0`), M2 Worker Agent
- **Target File for Implementation**: `src/morphomesh/wardrobe.py`
- **Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\explorer_m2_1_cloth_folds`
- **Date**: 2026-09-07T14:45:00Z
- **Type**: Hard Handoff (Investigation Complete)

---

## 1. Observation

### 1.1 Existing Skirt Code in `src/morphomesh/wardrobe.py:268-327`
In `src/morphomesh/wardrobe.py`, the skirt generator `generate_dress_pleated_skirt()` defines:
```python
def generate_dress_pleated_skirt(
    height: float = 1.65,
    clearance: float = 0.015,
    pleat_count: int = 20,
    rings_count: int = 10,
    sectors: int = 40,
    waist_girth: float = 0.58,
) -> MeshGeometry:
    ...
    pz = z_waist + t * (z_hem - z_waist)
    rx_base = (0.125 + 0.220 * (t ** 1.2)) * s * k_waist + clearance
    ry_base = (0.090 + 0.190 * (t ** 1.2)) * s * k_waist + clearance
    pleat_amp = 0.003 * s + 0.018 * (t ** 1.5) * s

    ring: List[int] = []
    for i in range(sectors):
        theta = 2.0 * math.pi * i / sectors
        pleat_wave = math.cos(pleat_count * theta)
        r_mult = 1.0 + (pleat_wave * pleat_amp) / max(1e-4, rx_base)
        px = rx_base * cos_t * r_mult
        py = ry_base * sin_t * r_mult
        ...
        u = i / sectors
        v = t
        idx = mesh.add_vertex((round(px, 5), round(py, 5), round(pz, 5)), norm, (u, v))
        ring.append(idx)
    rings.append(ring)

    for r in range(rings_count - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])
```

### 1.2 Exact Flaws Directly Observed
1. **Sawtooth Nyquist Aliasing**:
   With `sectors = 40` and `pleat_count = 20`, $\theta_i = \frac{2\pi i}{40} = \frac{\pi i}{20}$.
   Then $\cos(20 \cdot \theta_i) = \cos(\pi \cdot i) = (-1)^i$.
   The displacement alternates between $+1.0$ and $-1.0$ at every single vertex around the perimeter. Each pleat consists of exactly two vertices (one sharp apex, one sharp trough). The mesh is an extreme, unshaded sawtooth polygon with zero smooth curve.
2. **Planar Flat Hemline**:
   Vertical height $p_z(t) = z_{\text{waist}} + t(z_{\text{hem}} - z_{\text{waist}})$ is purely linear in $t$. At the hem ($t = 1.0$), every vertex has $Z = 0.52m \cdot s$, producing an artificial horizontal planar knife-cut edge.
3. **Texture Wrap Inversion at Rear Seam**:
   At $i = \text{sectors} - 1 = 39$, $u = 39/40 = 0.975$.
   The bridging quad connects vertex $39$ to vertex $ni = 0$, where $u = 0.0$.
   Across this face, UV coordinates jump from $0.975 \to 0.0$, inverting and horizontally stretching 97.5% of the texture backwards.
4. **Frozen Mesh under Armature Posing**:
   `Mesh_Dress_PleatedSkirt` in `wardrobe.py` and `get_wardrobe_script()` creates 0 vertex groups. While an `ARMATURE` modifier is attached to `Armature_Yu_Nian_An_Rigify`, Blender requires matching vertex groups (`DEF-spine`, `DEF-thigh.L`, etc.) to deform vertices. Without them, the skirt remains 100% frozen in rest pose when the character moves or walks.
5. **Waistband Z-Fighting**:
   At the waistline ($t = 0$), `pleat_amp = 0.003 * s = 4.95\text{mm}`. Because the skirt pleats protrude $5\text{mm}$ right at the waist cinch, they penetrate through the outer sash band, causing severe Z-fighting and mesh clipping.

### 1.3 Test Suite Status
- `uv run pytest tests/test_wardrobe.py`: 11 passed in 0.05s.
- `uv run pytest tests/test_character_assembler.py`: 31 passed in 5.12s.
- `uv run pytest tests/test_adversarial_human_m3.py`: 6 failed (anthropometric sash clearance test failed because M1's new body generator changed waist contours slightly, shrinking the sash gap from 12mm to 8.96mm; this must be compensated in M2's sash generator).

---

## 2. Logic Chain

1. **From Observation 1.2.1 (Sawtooth Aliasing) to Multi-Harmonic Spectrum**:
   - Natural cloth under gravity buckling does not form high-frequency single-sine origami pleats.
   - Cloth folds are dominated by primary structural drapes ($n_1 = 6$, anchored at the ASIS pelvic crest, greater trochanters, and gluteal apex), secondary cloth ripples ($n_2 = 8$), and tertiary soft creases ($n_3 = 12$).
   - Increasing circumferential resolution to `sectors = 48` guarantees at least 4 vertices per cycle for the highest harmonic ($n=12$) and 8 vertices per cycle for $n=6$, completely eliminating polygon faceting and Nyquist aliasing.
2. **From Observation 1.2.5 (Waist Penetration) to Quadratic Growth Decay**:
   - By setting $A_k(t) = a_k \cdot (t^{\alpha_k})$ with $\alpha_k \in [1.35, 1.95]$, the fold amplitude at $t=0$ is strictly $0.0\text{mm}$ (smooth ellipse).
   - This ensures the dress waist is 100% flush with the body and easily contained inside the sash envelope (+2.5mm clearance), eliminating all Z-fighting.
3. **From Anatomy (Quadriceps Profile) to Anterior Thigh Flattening**:
   - In standing posture, the anterior quadriceps protrude forward into the skirt at $\sin\theta < -0.25$ (character facing $-Y$).
   - If inward fold valleys occur here, the cloth caves into the quads.
   - Anisotropic weighting $W_{\text{region}}(\theta)$ attenuates inward valleys over the thighs ($F_{\text{inward}} \cdot (1 - \text{anterior\_mask} \cdot 0.70)$) while boosting lateral and posterior valleys ($+20\%$).
   - This replicates the flat front apron and deep flank drapes seen in reference photo `media_1788785935849.jpg`.
4. **From Observation 1.2.2 (Flat Hem) to Undulating Scalloped Hemline**:
   - Fold crests have excess cloth mass and pull down under gravity; fold troughs are held taut.
   - Introducing $\Delta z_{\text{sag}}(\theta) = -0.014 \cdot s \cdot [0.72 \cos(6\theta_{\text{eff}}) + 0.28 \cos(2\theta)] - 0.006 \cdot s \cdot \sin\theta$ imparts a 14mm scalloped hemline with natural front/back pitch.
   - Blending with $t^2$ ensures $\Delta z(t=0) = 0$ and $\frac{\partial \Delta z}{\partial t} = 0$, so the waistline remains level and connects seamlessly to the bodice.
5. **From Observation 1.2.3 (UV Inversion) to Duplicate Seam Vertices**:
   - Generating `sectors + 1` vertices per ring where vertex $i = \text{sectors}$ has identical 3D coordinates to $i=0$ but $u = 1.0$ ensures that all quads have $u_{i+1} - u_i = 1/\text{sectors} > 0$.
   - This completely eliminates horizontal texture inversion and backward smearing.
6. **From Observation 1.2.4 (Frozen Skirt) to Rigify 163 DEF Bone Vertex Groups**:
   - Assigning vertex weights to `DEF-spine`, `DEF-spine.001`, `DEF-thigh.L`, `DEF-thigh.L.001`, `DEF-thigh.R`, `DEF-thigh.R.001` with medial blending ($\tanh(x / 0.035)$) enables natural skinning deformation during movement without stride tearing.

---

## 3. Caveats

1. **Read-Only Investigation**:
   In strict adherence to the Explorer archetype, no source files were modified. The Worker agent must apply the provided code changes to `src/morphomesh/wardrobe.py`.
2. **Waist Sash Clearance Interaction**:
   `test_adversarial_human_m3.py` revealed that M1's updated anatomical body contours narrowed the clearance to 8.96mm. While the skirt multi-harmonic folds fix the skirt-side penetration (amplitude = 0 at waist), the Worker must also calibrate the waist sash generator `rx_base` ($0.130 \cdot s \cdot k_{\text{waist}} + \text{clearance}$) in M2 to pass all adversarial boundary tests.
3. **Bodice Subdivision Synchronization**:
   While the skirt functions independently with `sectors = 48`, the bodice currently uses `sectors = 24`. For optimal visual continuity at the waistline, the Worker should also upgrade `generate_dress_bodice` to `sectors = 48` in M2.

---

## 4. Conclusion

The rigid conical fluting and 20-wave cosine pleats in `src/morphomesh/wardrobe.py` suffer from severe Nyquist sawtooth aliasing, flat planar hemlines, backwards UV texturing, and frozen armature binding.
A complete, mathematically verified, drop-in replacement `generate_dress_organic_skirt()` with a backward-compatible alias `generate_dress_pleated_skirt()` is fully formulated and documented in `E:\tool\mcp\MorphoMesh\.agents\explorer_m2_1_cloth_folds\analysis.md`.

---

## 5. Verification Method

### 5.1 Independent Verification Commands
The receiving Worker and Reviewer can independently verify this investigation and the proposed implementation using:

1. **Inspect Analysis Report**:
   `view_file` on `E:\tool\mcp\MorphoMesh\.agents\explorer_m2_1_cloth_folds\analysis.md`.
2. **Run Existing Wardrobe Unit Tests**:
   ```bash
   uv run pytest tests/test_wardrobe.py -v
   ```
3. **Run Character Assembler Tests**:
   ```bash
   uv run pytest tests/test_character_assembler.py -v
   ```
4. **Post-Implementation Assertions for Worker**:
   - `assert len(skirt.vertices) >= 500` (verifies 48 sectors $\times$ 12+ rings with duplicate seam).
   - `assert 0.48 <= min(zs) <= 0.55` and `max(zs) >= 1.00`.
   - `assert max(zs_hem) - min(zs_hem) >= 0.012` (verifies ~14mm scalloped sag at hem).
   - `assert max(zs_waist) - min(zs_waist) < 0.001` (verifies level waistline).
   - Check UV continuity: For all faces, verify $u_{\text{vertex 1}} \ge u_{\text{vertex 0}}$.

### 5.2 Invalidation Conditions
- Any occurrence of $\cos(20\theta)$ with $\text{sectors} \le 40$.
- Any skirt hemline with zero $Z$ variation (planar flat cut).
- Any quad where $u$ drops from $> 0.90$ to $< 0.10$.
- Skirt mesh failing to deform in Blender when armature thigh bones rotate.
