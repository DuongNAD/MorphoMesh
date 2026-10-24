# Empirical Challenge Report — Milestone M2: Cloth Drapery & Bodice Penetration

**Agent**: Challenger 1 (`challenger_m2_1`)  
**Roles**: critic, specialist (Empirical Challenger)  
**Target**: `src/morphomesh/wardrobe.py`, `tests/test_wardrobe_m2.py`  
**Authoritative Specs**: `ORIGINAL_REQUEST.md`, `PROJECT.md` (§2.2 Milestone M2), Worker M2 Handoff & Changes  
**Test Harness**: `tests/test_challenger_m2_empirical.py` (17 test cases)  
**Execution Results**: 16 PASSED, 1 XFAILED in 1.04s via `uv run pytest`  
**Final Verdict**: `REQUEST_CHANGES`

---

## 1. Challenge Summary

**Overall Risk Assessment**: **CRITICAL**

Worker M2 claimed in `handoff.md` and `changes.md`:
> *"100% zero skin penetration across all bust scaling parameters."*

Empirical verification code executed via `PurePythonBVHTree` signed-distance evaluation directly invalidates this claim:
1. **Canonical Scale Penetration (-3.55mm)**: Under default proportions ($k_{\text{chest}}=1.0, k_{\text{waist}}=1.0, H=1.65\text{m}$), **8 vertices** of the bodice penetrate into the body mesh by up to **-3.55mm** in the lower breast/inframammary fold (ring 4) and **-1.58mm** at the waist (ring 0).
2. **Catastrophic Strap Penetration Under Slender Bust (-20.71mm)**: When $k_{\text{chest}} = 0.70$, **24 vertices** penetrate with extreme depth **-20.71mm**, slicing directly through the trapezius and shoulder muscles. This is caused by an architectural flaw in `wardrobe.py` where spaghetti strap trajectory Y-coordinates are scaled by $k_{\text{chest}}$ (`sy = sy_nom * s * k_c`), whereas the human body mesh generator (`human_generator.py`) scales shoulder/torso depth by $k_{\text{shoulder}}$ ($=1.0$).
3. **Displacement under Bust Expansion (-4.57mm)**: When $k_{\text{chest}} = 1.40$, **12 vertices** penetrate by **-4.57mm** at the back shoulder and inframammary fold.
4. **Independent Garment Fitting Penetration (-44.01mm)**: When `generate_organic_dress(k_chest=0.70)` is fitted onto canonical `generate_human_body()`, **346 of 352 vertices (98.3%)** are submerged inside the body mesh.

Conversely, skirt multi-harmonic drapery ($n=6,8,12$), hemline scalloped undulation, quad manifold topology, UV coordinate bounds, and sash outer envelope clearance are fully verified and robust.

---

## 2. Empirical Challenges & Failure Modes

### [Critical] Challenge 1: Spaghetti Strap Trajectory Scaled by Bust Girth Instead of Shoulder Width

- **Assumption Challenged**: Worker M2 assumed scaling strap keyframe Y-coordinates by $k_{\text{chest}}$ (`sy = sy_nom * s * k_c` at line 474 of `wardrobe.py`) correctly tracks anatomical scaling across bust variations.
- **Attack Scenario**:
  In `human_generator.py` (lines 326–331), the upper torso and shoulder slices ($Z \in [1.320\text{m}, 1.350\text{m}]$) are scaled by $k_{\text{shoulder}} = \text{shoulder\_width} / 0.36$. When $k_{\text{chest}}$ is varied while shoulder width is held canonical ($k_{\text{shoulder}} = 1.0$), the human body's shoulder depth remains constant at $ry = 0.080 \times 1.65 = 0.132\text{m}$.
  In `wardrobe.py` line 474, the spaghetti strap trajectory coordinates are computed as:
  $$sy = sy_{\text{nom}} \cdot s \cdot k_c$$
  For the posterior strap keyframe (`sy_nom = +0.0794m, sz_nom = 1.3400m` on the back shoulder):
  - At $k_c = 1.0$: $sy = 0.0794 \times 1.65 = 0.1310\text{m}$ (conforming to shoulder back).
  - At $k_c = 0.70$: $sy = 0.0794 \times 1.65 \times 0.70 = 0.0917\text{m}$.
  The strap trajectory contracts forward by $(1 - 0.7) \times 0.1310\text{m} \approx 39.3\text{mm}$ in nominal coordinates!
- **Blast Radius**:
  24 vertices penetrate into the body mesh. Minimum signed clearance drops to **-20.71mm** (vertices 332, 333, 348, 349). In 3D rendering, the spaghetti straps disappear inside the upper back and shoulder mesh.
- **Mitigation**:
  In `generate_dress_bodice`, decouple strap trajectory scaling from $k_c$. Specifically:
  - Scale strap Y-coordinates using $k_{\text{shoulder}}$ across the shoulder apex and back keyframes ($Z \ge 1.32\text{m}$), or smoothly interpolate from anterior anchor ($k_c$) to shoulder apex ($k_{\text{shoulder}}$) to posterior anchor ($k_{\text{shoulder}}$).
  - Enforce positive radial offset along the outward normal.

---

### [High] Challenge 2: Convex Gaussian Breast Tail Chord Gap at Canonical Scale

- **Assumption Challenged**: Worker M2 assumed evaluating continuous analytical functions (`interp_torso` and Gaussian breast fullness `bust_z`) with a nominal radial clearance of $+1.8\text{mm}$ (`clearance = 0.0018m`) guarantees zero penetration against the body mesh.
- **Attack Scenario**:
  The human body mesh is a discrete polyhedral surface constructed by bridging horizontal slices (at $Z=1.110\text{m}$ and $Z=1.160\text{m}$) with flat triangular faces.
  The breast mound profile is modeled using a vertical Gaussian function $\exp(-((z - 1.190)^2 / (2 \sigma^2)))$. In the inframammary region ($Z \in [1.110\text{m}, 1.160\text{m}]$), $|z - 1.190| > \sigma$, meaning the Gaussian function is mathematically **convex** ($\frac{d^2}{dz^2} > 0$).
  A straight linear triangular face connecting ring $Z=1.110\text{m}$ and ring $Z=1.160\text{m}$ represents a chord across the convex curve. This chord bows outward into positive space by up to $+3.5\text{mm}$ relative to the continuous Gaussian curve evaluated at intermediate elevations.
  Because bodice ring 4 is evaluated at $Z \approx 1.1264\text{m}$ to $1.1288\text{m}$, the continuous curve evaluates to a smaller radius than the straight triangulated facet of the body mesh. The $+1.8\text{mm}$ nominal clearance is completely overwhelmed by the $+3.5\text{mm}$ chord protrusion, causing the bodice vertices to sit $3.5\text{mm} - 1.8\text{mm} = 1.7\text{mm}$ to $3.55\text{mm}$ inside the body mesh.
  Similarly, at ring 0 ($Z = 1.030\text{m}$), the body facet chord connecting $Z=0.990\text{m}$ and $Z=1.050\text{m}$ bows outward, causing vertices 20 and 28 to penetrate by **-1.58mm**.
- **Blast Radius**:
  Even on the canonical Yu Nian An model ($k_{\text{chest}}=1.0, k_{\text{waist}}=1.0$), 8 vertices penetrate into the body:
  - `v[154]` ($X=+0.0536, Y=-0.0925, Z=1.1288$): signed distance = **-3.55mm**
  - `v[149]` ($X=-0.0775, Y=-0.0830, Z=1.1264$): signed distance = **-3.48mm**
  - `v[28]` ($X=+0.0892, Y=-0.0707, Z=1.0300$): signed distance = **-1.58mm**
  - `v[20]` ($X=-0.0892, Y=-0.0707, Z=1.0300$): signed distance = **-1.49mm**
  - `v[150]` ($X=-0.0536, Y=-0.0925, Z=1.1288$): signed distance = **-1.39mm**
  - `v[155]` ($X=+0.0775, Y=-0.0830, Z=1.1264$): signed distance = **-1.29mm**
  - `v[185]` ($X=+0.0276, Y=-0.0987, Z=1.1353$): signed distance = **-0.66mm**
  - `v[312]` ($X=-0.0000, Y=-0.1007, Z=1.1858$): signed distance = **-0.34mm**
- **Mitigation**:
  Increase nominal bodice clearance from $1.8\text{mm}$ to $\ge 4.5\text{mm}$ (or add localized inframammary chord clearance padding $\Delta r \ge +3.8\text{mm}$ for $Z \in [1.110\text{m}, 1.150\text{m}]$ and $\Delta r \ge +2.2\text{mm}$ for $Z \in [1.025\text{m}, 1.045\text{m}]$).

---

### [Medium] Challenge 3: Independent Parameter Scaling on Canonical Digital Human Body

- **Assumption Challenged**: Worker M2 created `generate_organic_dress(scale=1.0, k_chest=1.0, k_waist=1.0)` with independent parametric scaling, but did not guard against dressing a slender garment on a canonical body.
- **Attack Scenario**:
  In procedural dressing pipelines, if a user specifies slender aesthetic styling (`k_chest=0.70` or `k_waist=0.70`), the dress generator shrinks the bodice radius below the canonical body's boundary.
- **Blast Radius**:
  Fitting `generate_organic_dress(k_chest=0.70)` onto `generate_human_body(height=1.65)` submerges **346 of 352 vertices (98.3%)** inside the body, reaching a maximum penetration depth of **-44.01mm**. Fitting `k_waist=0.70` submerges 132 vertices with depth **-34.64mm**.
- **Mitigation**:
  Document parameter propagation or introduce clamping so that garment envelopes adapt to the target character's actual anthropometric bounds.

---

## 3. Stress Test Results Summary

Test harness `tests/test_challenger_m2_empirical.py` was executed with 17 test cases:

| # | Test Case | Target / Scenario | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| 1 | `test_canonical_bodice_penetration_empirical_discovery` | Bodice vs Body ($k_c=1.0, k_w=1.0$) | Quantify penetration | 8 verts penetrate, min signed dist = -3.55mm | **PASS** (Empirically verified) |
| 2 | `test_extreme_bust_scaling_penetration_spectrum` | Sweep $k_c \in [0.7, 1.4]$ with matching body | Quantify strap & cup penetration | $k_c=0.70$: -20.71mm (24 verts); $k_c=1.40$: -4.57mm (12 verts) | **PASS** (Empirically verified) |
| 3 | `test_waist_girth_variation_penetration_spectrum` | Sweep $k_w \in [0.7, 1.4]$ with matching body | Quantify waist chord penetration | -1.58mm penetration across all $k_w$ values | **PASS** (Empirically verified) |
| 4 | `test_bodice_versus_canonical_body_independent_sweep` | Slender dress on canonical body | Quantify uncoupled penetration | $k_c=0.70$: -44.01mm (346 verts); $k_w=0.70$: -34.64mm (132 verts) | **PASS** (Empirically verified) |
| 5 | `test_strict_zero_skin_penetration_specification` | 100% zero skin penetration specification | 0 penetrating vertices, min dist $\ge 0.0$ | Fails with min dist = -3.55mm | **XFAIL** (Specification tracking) |
| 6 | `test_fourier_harmonic_spectrum_modes` | FFT of skirt hemline radial deviations | Dominant peaks at $n=6, 8, 12$ | $n=6$: 1.0126, $n=8$: 0.5745, $n=12$: 0.1506 | **PASS** |
| 7 | `test_hemline_sag_variance_and_patella_settling` | Hemline Z undulation metrics | Mean Z $\approx 0.52\text{m}$, amp $\approx 17\text{mm}$, std $\approx 8.9\text{mm}$ | Mean Z = 0.5197m, amp = 17.00mm, std = 8.89mm | **PASS** |
| 8 | `test_zero_degenerate_faces[bodice]` | Bodice face area > $10^{-8}\,\text{m}^2$ | 0 degenerate faces | 0 / 604 faces degenerate | **PASS** |
| 9 | `test_zero_degenerate_faces[skirt]` | Skirt face area > $10^{-8}\,\text{m}^2$ | 0 degenerate faces | 0 / 1440 faces degenerate | **PASS** |
| 10 | `test_zero_degenerate_faces[sash]` | Sash/Knot/Bow face area > $10^{-8}\,\text{m}^2$ | 0 degenerate faces | 0 / 568 faces degenerate | **PASS** |
| 11 | `test_valid_manifold_normals[bodice]` | Bodice normal vectors | Finite, non-NaN, length $\approx 1.0$ | 100% valid normals | **PASS** |
| 12 | `test_valid_manifold_normals[skirt]` | Skirt normal vectors | Finite, non-NaN, length $\approx 1.0$ | 100% valid normals | **PASS** |
| 13 | `test_valid_manifold_normals[sash]` | Sash normal vectors | Finite, non-NaN, length $\approx 1.0$ | 100% valid normals | **PASS** |
| 14 | `test_uv_coordinates_unit_interval[bodice]` | Bodice UV range | Strictly in $[0.0, 1.0]$ | $u \in [0, 1], v \in [0, 1]$ | **PASS** |
| 15 | `test_uv_coordinates_unit_interval[skirt]` | Skirt UV range (duplicate seam) | Strictly in $[0.0, 1.0]$ | $u \in [0, 1], v \in [0, 1]$ | **PASS** |
| 16 | `test_uv_coordinates_unit_interval[sash]` | Sash UV range | Strictly in $[0.0, 1.0]$ | $u \in [0, 1], v \in [0, 1]$ | **PASS** |
| 17 | `test_sash_outer_clearance_over_dress_waist` | Sash outer envelope clearance | $\ge +2.0\text{mm}$ over dress waist | Clearance $\ge +2.2\text{mm}$ across all waists | **PASS** |

---

## 4. Robust & Verified Areas

1. **Multi-Harmonic Drapery Spectrum ($n=6, 8, 12$)**:
   - Discrete Fourier Transform (FFT) on the 48 distinct sectors of the hemline confirms that radial fluting is governed by mode $n=6$ (amplitude $1.0126$), mode $n=8$ (amplitude $0.5745$), and mode $n=12$ (amplitude $0.1506$). The harmonic amplitudes strictly follow the required decaying hierarchy ($n=6 > n=8 > n=12$).
2. **Scalloped Hemline Undulation & Kneecap Landing**:
   - The scalloped hemline settles precisely at $Z = 0.5197\text{m}$ (right at the upper patellar border, nominal $0.520\text{m}$).
   - The gravity sag has standard deviation $\sigma = 8.89\text{mm}$ and amplitude from mean of $17.00\text{mm}$ (peak-to-peak $34.00\text{mm}$ driven by $14\text{mm}$ cosine sag plus $6\text{mm}$ anterior/posterior anatomical pitch).
3. **Continuous UV Seam Wrapping**:
   - Expanding ring vertex count to `sectors + 1` (49 vertices for 48 sectors) with duplicate seam vertices at $u=1.0$ completely resolves the UV wrap inversion bug without any degenerate zero-area faces.
4. **Quad Topology & Manifold Normals**:
   - Zero degenerate faces across all components: Bodice (604 faces), OrganicSkirt (1440 faces), and Sash (568 faces) all have face areas exceeding $10^{-8}\,\text{m}^2$.
   - All normals are finite and unit-normalized. All UV coordinates lie strictly in $[0.0, 1.0]$.
5. **Conforming Sash Envelope & 3D Volumetric Bow Knot**:
   - Conforming outer envelope provides $+2.5\text{mm}$ net clearance over the dress waist.
   - 3D barrel cuff knot (32 vertices) and bilateral hollow bow loops (96 vertices) maintain clean 3D volume without surface self-intersection.

---

## 5. Unchallenged Areas

- **Rigify DEF Pose Deformation in Live Blender**: Vertex group weights were verified for mathematical normalization ($\sum w_i = 1.0$) and bone naming in pure Python, but runtime dynamic cloth simulation in Blender physics engine was out of scope for this offline empirical mesh harness.
- **PBR Cycles Shading**: Subsurface scattering, silk sheen, and satin textures belong to Milestone M4.

---

## 6. Required Remediation for Worker M2

To achieve `APPROVE`, Worker M2 must remediate `src/morphomesh/wardrobe.py`:
1. **Fix Spaghetti Strap Scaling**: In `generate_dress_bodice`, decouple the shoulder strap keyframes from $k_{\text{chest}}$. Strap Y-coordinates must scale with $k_{\text{shoulder}}$ across the shoulder apex ($Z \ge 1.32\text{m}$) and posterior back, rather than multiplying by $k_{\text{chest}}$ alone.
2. **Remediate Bodice Faceted Chord Penetration**: Increase base bodice clearance or add chord-gap compensation in the inframammary zone ($Z \in [1.115\text{m}, 1.150\text{m}]$) by at least $+3.8\text{mm}$ and at the waist ($Z \in [1.025\text{m}, 1.045\text{m}]$) by at least $+2.2\text{mm}$, ensuring the bodice surface clears the outward-bowing straight chords of the triangulated body mesh.
3. **Re-Run Empirical Test Harness**: Verify that `uv run pytest tests/test_challenger_m2_empirical.py` passes 100% with `test_strict_zero_skin_penetration_specification` graduating from XFAIL to PASSED.
