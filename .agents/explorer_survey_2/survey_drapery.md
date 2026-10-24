# MorphoMesh: Organic Dress Drapery & Ice-Blue Sash Technical Survey (R2)

**Author:** Cloth Drapery Explorer (`explorer_survey_2`)  
**Target Milestone:** R2 — Realistic Organic One-Piece Dress & Conforming Ice-Blue Sash  
**Authoritative Reference:** `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (under `## 2026-09-07T13:01:03Z`)  
**Date:** 2026-09-07  

---

## 1. Executive Summary & Survey Objectives

The authoritative prompt for MorphoMesh defines Requirement R2 as:
> **R2. Thiết Kế Váy Liền Thân Hữu Cơ Với Nếp Gấp Và Độ Rủ Vải Chân Thực (Realistic Organic Dress)**:
> - Tái thiết kế váy thành dạng váy liền thân cao cấp dựa trên tham chiếu đời thực và minh họa thời trang (`media_1788785935849.jpg` & `media_1788785935824.jpg`): loại bỏ hoàn toàn các nếp gấp nón cơ học cứng nhắc, thay bằng các nếp gấp vải hữu cơ tự nhiên (gravity folds, tension lines từ ngực và eo, nếp gấp mềm mại rủ xuống ngang gối).
> - Phần thân trên ôm sát cơ thể với cúp ngực tự nhiên (teardrop profile), rãnh ngực thanh thoát, cổ áo sweetheart scoop và dây áo spaghetti mảnh mai tự nhiên qua vai.
> - Đai thắt lưng satin xanh băng (ice-blue sash) ôm khít 100% bên ngoài eo váy kèm nút thắt nơ và dải ruy-băng rủ tự nhiên, triệt tiêu hoàn toàn hiện tượng Z-fighting hay đốm xuyên thấu.

This survey provides a comprehensive forensic analysis of the current wardrobe generator in `src/morphomesh/wardrobe.py`, deconstructs the reference visual assets, and establishes the exact geometric equations, topological structure, vertex weight distributions, modifier pipelines, and PBR shader parameters required to achieve a production-grade, photorealistic organic dress.

---

## 2. Forensic Audit of Existing Implementation (`wardrobe.py`)

### 2.1 Skirt Drapery: Rigid Conical Fluting & Mathematical Cones
In `src/morphomesh/wardrobe.py`, skirt generation is handled by `generate_dress_pleated_skirt()` (lines 268–327):
```python
pz = z_waist + t * (z_hem - z_waist)
rx_base = (0.125 + 0.220 * (t ** 1.2)) * s * k_waist + clearance
ry_base = (0.090 + 0.190 * (t ** 1.2)) * s * k_waist + clearance
pleat_amp = 0.003 * s + 0.018 * (t ** 1.5) * s

pleat_wave = math.cos(pleat_count * theta)
r_mult = 1.0 + (pleat_wave * pleat_amp) / max(1e-4, rx_base)
px = rx_base * cos_t * r_mult
py = ry_base * sin_t * r_mult
```

#### Structural Flaws Identified:
1. **Mathematical Truncated Elliptic Cone**:
   The skirt base is an idealized truncated elliptical cone expanding monotonically via $(t^{1.2})$. It lacks the biological shape of human hips, buttocks, and thighs. It does not drape over the legs; instead, it behaves like an inverted paper lampshade or a rigid wire hoop petticoat.
2. **Artificial 20-Wave Cosine Fluting**:
   Modulating the radius by $\cos(20 \cdot \theta)$ produces 20 identical, perfectly symmetric, rigid fluted corrugations around the circumference. Real fabric does not form repetitive sinusoidal fluting unless artificially heat-pleated or ironed into rigid accordion folds.
3. **Severe Polygon Aliasing (Sawtooth Zigzag Artifact)**:
   The sector count is configured as `sectors = 40` while `pleat_count = 20`. For vertex index $i \in [0, 39]$, the sample angle is $\theta_i = \frac{2\pi i}{40} = \frac{\pi i}{20}$. Thus:
   $$\cos(20 \cdot \theta_i) = \cos(\pi \cdot i) = (-1)^i$$
   The pleat wave oscillates between $+1.0$ and $-1.0$ at alternating vertices! Each pleat cycle consists of only two vertices (one peak, one trough). Rather than a smooth curve, the mesh forms a harsh, jagged, sawtooth zigzag polygon.
4. **Completely Flat Hemline**:
   Elevation $p_z$ is strictly linear in $t$. At the hem ($t = 1.0$), every vertex has identical $Z = 0.52m \cdot s$. In real cloth, fold crests and troughs produce an undulating, scalloped hem contour with natural gravity sag.
5. **Disjointed Topology**:
   `Mesh_Dress_Bodice` and `Mesh_Dress_PleatedSkirt` are generated as two completely disconnected open mesh shells. Bodice has 24 circumferential sectors at $Z = 1.03m$, whereas skirt has 40 sectors at $Z = 1.03m$. When deformed by skeletal bones, a visible gap or tearing artifact will occur at the waistline.

---

### 2.2 Upper Bodice: Single-Ellipse Protrusion & Disconnected Straps
In `src/morphomesh/wardrobe.py`, `generate_dress_bodice()` (lines 79–179) uses 5 vertical elevation slices:
```python
# Anatomical bust protrusion formula
mod_ry = ry
if z >= 1.10 * s and sin_t < -0.3:
    mod_ry = ry * (1.0 + 0.38 * (-sin_t - 0.3))
```

#### Structural Flaws Identified:
1. **Lack of Bilateral Teardrop Breast Cups**:
   Expanding $r_y$ where $\sin(\theta) < -0.3$ creates a single uniform anterior cylindrical bulge across the front torso (a "mono-breast" or barrel chest). It completely fails to form two distinct left and right breast mounds.
2. **Missing Medial Cleavage (Sternal Sulcus)**:
   There is no inward dip at the midline ($X = 0$). Real female anatomy exhibits a distinct cleavage indentation between the breast mounds.
3. **Absence of Sweetheart Scoop Neckline**:
   The neckline dip is implemented simply as `dip_z = -0.025 * (-sin_t - 0.3) * s` on the topmost ring. It lacks the distinctive sweetheart curve: central plunge at $X=0$, upward arching crests over the breast cups, and soft transition into strap anchors.
4. **Disconnected 2D Ribbon Spaghetti Straps**:
   Each shoulder strap is generated as 6 isolated points at a fixed $X$ coordinate (`x_anchor = +/- 0.070 * s * math.sqrt(k_c)`). The straps do not curve along the 3D contour of the clavicle, trapezius, and shoulder. Furthermore, they are disconnected floating quad strips that do not share vertices with the bodice rim.

---

### 2.3 Waist Sash: Rigid Cylinder, Missing Bow Loops, and Inappropriate Color
In `src/morphomesh/wardrobe.py`, `generate_dress_waist_sash()` (lines 181–265):
```python
z_center = 1.05 * s
z_bottom = z_center - belt_width * 0.5 * s
z_top = z_center + belt_width * 0.5 * s
rx = 0.126 * s * k_waist + clearance
ry = 0.089 * s * k_waist + clearance
```

#### Structural Flaws Identified:
1. **Straight Elliptic Cylinder**:
   The sash band consists of 3 horizontal rings with constant $r_x, r_y$. It does not conform to the tapered feminine waist profile ($Z=1.05m$ is the waist apex, tapering out towards $Z=0.99m$ and $Z=1.11m$).
2. **High Penetration & Clipping Risk**:
   The sash clearance is hardcoded as `0.020m`, while the skirt clearance is `0.015m`. The radial difference is only $5\text{mm}$. However, the skirt pleat amplitude at waist is $0.003 \cdot 1.65 \approx 4.95\text{mm}$. With a 2mm solidify modifier, the skirt pleats penetrate through the sash, causing severe Z-fighting and visual clipping.
3. **Flat 2D Single-Quad "Knot"**:
   The central knot is modeled as a single flat rectangular polygon (`mesh.add_quad(k0, k1, k2, k3)`). It possesses zero 3D volume or wrap creasing.
4. **Complete Absence of Bow Loops (Nút Thắt Nơ)**:
   The concept sheet (`media_1788716034772.jpg`) and prompt explicitly require a tied bow knot with ribbon loops and cascading streamers. The existing code has NO bow loops whatsoever.
5. **Wrong Material Definition**:
   In `src/morphomesh/human_materials.py` (lines 213–224), `Mat_Dress_WaistBelt` is defined with `base_color=(0.15, 0.15, 0.15, 1.0)` (dark grey/black). The concept turnaround sheet and prompt explicitly require an **Ice-Blue Satin** sash (`satin xanh băng`).

---

### 2.4 Critical Rigging Defect: Absence of Vertex Groups on Dress Objects
An inspection of `src/morphomesh/wardrobe.py` (lines 749–754) reveals:
```python
# Solidify modifier for realistic fabric thickness (2mm)
solid_mod = d_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
solid_mod.thickness = float(CFG.get("thickness", 0.002))

# Armature / Deform modifier binding
if armature_obj:
    arm_mod = d_obj.modifiers.new(name="Armature", type='ARMATURE')
    arm_mod.object = armature_obj
```
#### Finding:
While the `ARMATURE` modifier is added and targeted to `Armature_Yu_Nian_An_Rigify`, **NO VERTEX GROUPS ARE EVER CREATED ON `Mesh_Dress_Bodice`, `Mesh_Dress_WaistSash`, OR `Mesh_Dress_PleatedSkirt`**.
Because Blender's Armature modifier deforms mesh vertices based on matching vertex group names (`DEF-spine`, `DEF-thigh.L`, etc.), the dress meshes currently have **0% deformation**. When the character rig is posed or animated, the character body moves, but the dress remains completely frozen in rest pose!

---

### 2.5 UV Unwrap Discontinuity (Seam Stretch)
In `MeshGeometry`, UV coordinates are stored per-vertex (`mesh.add_vertex(..., (u, v))`). In `wardrobe.py`, the cylinder circumferential coordinate is computed as $u = \frac{i}{\text{sectors}}$.
When the final quad is constructed bridging vertex `sectors - 1` ($u \approx 0.96$) to vertex `0` ($u = 0.0$), the UV mapping spans backwards across the entire $[0, 1]$ interval. This causes extreme texture smearing across the rear seam line unless duplicate seam vertices with $u = 1.0$ are introduced.

---

## 3. Visual Reference Deconstruction

### 3.1 Real-World Drapery Benchmark (`media_1788785935849.jpg`)
![Real Drapery](C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935849.jpg)
- **Fabric Physics**: Lightweight summer cotton/linen dress. Under gravitational acceleration, fabric drops in soft, vertical catenary folds.
- **Waist Gathering**: Natural gathers at the waist seam form gentle vertical ripples rather than sharp geometric pleats.
- **Hem Contour**: The hem is not a flat planar cut; it undulates naturally with gentle waves as fabric drapes around the knees.
- **Silhouette Interaction**: The fabric falls straight down from the anterior thigh and pelvis without excessive outward flare.

### 3.2 Fashion Silhouette & Fold Flow (`media_1788785935824.jpg`)
![Fashion Silhouette](C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935824.jpg)
- **Cinched Waist Definition**: Clear contrast between tight waist cinching and gentle A-line skirt flare.
- **Tension Lines**: Diagonal tension creases originating from the cinched waist and wrapping around hip curves.
- **Volume & Breathability**: Soft fabric volume supported by gravity and natural textile stiffness.

### 3.3 Authoritative Character Concept Sheet (`media_1788716034772.jpg`)
![Concept Sheet](C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg)
- **Bodice Structure**:
  - Sweetheart scoop neckline dipping gracefully at the center.
  - Distinct teardrop breast cup contouring with gentle cleavage.
  - Thin, delicate spaghetti straps resting naturally over the shoulder apex and running straight down the upper back.
  - Exposed upper back (back neckline settles at mid-scapular level, $Z \approx 1.23m$).
- **Waist Sash**:
  - High-waist / empire cinching band, colored soft ice-blue / powder-blue.
  - Tied bow knot positioned at the front center-left with neat horizontal knot wrap.
  - Two cascading ribbon streamers dangling down to approximately knee/mid-thigh level ($Z \approx 0.65m$).
- **Skirt Silhouette**:
  - Knee-length A-line flared silhouette settling right above the patella ($Z \approx 0.52m$).
  - 6 to 8 major organic gravity folds radiating gracefully from the waistline.
  - Flowing, soft cloth drape rather than rigid conical pleating.

---

## 4. Architectural Redesign Blueprint: Realistic Organic One-Piece Dress

### 4.1 Topology Strategy: Unified One-Piece vs Coordinated Seamless Parts
To meet the requirement for a "realistic organic one-piece dress" while maintaining 100% backward compatibility with existing test suites (`test_wardrobe.py`, `test_challenger_m4_iter7_empirical.py`, `test_fastmcp_human_tools.py`):
1. **Synchronized Topology Resolution**:
   Both `Dress_Bodice` and `Dress_PleatedSkirt` (or the unified `Mesh_Dress_OnePiece`) will share an identical circumferential resolution of **48 sectors** (or 64 sectors).
   At the waist junction ($Z = 1.03m \cdot s$), the bottom ring of the bodice and the top ring of the skirt share the exact same $(X, Y, Z)$ coordinates, normals, and UV seams.
2. **Master One-Piece Generator (`generate_organic_one_piece_dress`)**:
   A unified procedural generator will construct the entire dress from top shoulder straps down to the scalloped hem as a single 100% manifold, pure-quad mesh.
3. **Coordinated Component Export**:
   For existing pipeline callers and unit tests expecting `Dress_Bodice` and `Dress_PleatedSkirt`, the generator provides seamless slices that match vertex-for-vertex at the waist seam line.

---

### 4.2 Upper Bodice Mathematical Modeling

#### 4.2.1 Bilateral Teardrop Breast Cups
Let $s = \frac{\text{height}}{1.65}$ and $k_c = \frac{\text{chest\_girth}}{0.82}$.
The breast cup centers are located at:
$$C_{\text{breast}, L} = (+0.065 \cdot s \cdot \sqrt{k_c}, -0.115 \cdot s \cdot k_c, 1.215 \cdot s)$$
$$C_{\text{breast}, R} = (-0.065 \cdot s \cdot \sqrt{k_c}, -0.115 \cdot s \cdot k_c, 1.215 \cdot s)$$

For a vertex on the frontal hemisphere ($\sin(\theta) < -0.1$ and $Z \in [1.10m \cdot s, 1.28m \cdot s]$):
Let $d_L = \sqrt{(x - C_{x,L})^2 + (z - C_{z,L})^2}$ and $d_R = \sqrt{(x - C_{x,R})^2 + (z - C_{z,R})^2}$.
The outward teardrop displacement $\Delta y_{\text{cup}}(x, z)$ is modeled as:
$$\Delta y_{\text{cup}}(x, z) = -A_{\text{cup}} \cdot \left[ \exp\left(-\frac{d_L^2}{2\sigma_{\text{cup}}^2}\right) + \exp\left(-\frac{d_R^2}{2\sigma_{\text{cup}}^2}\right) \right] \cdot \tau_{\text{tear}}(z)$$
Where:
- $A_{\text{cup}} = 0.032 \cdot s \cdot k_c$ (cup projection amplitude)
- $\sigma_{\text{cup}} = 0.045 \cdot s$ (radial cup spread)
- $\tau_{\text{tear}}(z)$ is the asymmetric teardrop factor:
  $$\tau_{\text{tear}}(z) = \begin{cases} 
  1.0 + 0.35 \cdot \frac{C_z - z}{0.10 \cdot s} & \text{for } z < C_z \text{ (fuller underbust)} \\
  1.0 - 0.40 \cdot \frac{z - C_z}{0.08 \cdot s} & \text{for } z \ge C_z \text{ (gentle upper slope)}
  \end{cases}$$

#### 4.2.2 Medial Cleavage (Sternal Cleft)
At the midline between the breasts ($|x| < 0.025 \cdot s$), fabric is pulled inward toward the sternum:
$$\Delta y_{\text{cleavage}}(x, z) = +0.012 \cdot s \cdot \exp\left(-\frac{x^2}{2(0.018 \cdot s)^2}\right) \cdot \exp\left(-\frac{(z - 1.21 \cdot s)^2}{2(0.040 \cdot s)^2}\right)$$
This produces a natural, elegant 12mm cleavage cleft.

#### 4.2.3 Sweetheart Scoop Neckline Curve
The top boundary of the bodice at $Z \approx 1.25m \cdot s$ follows an anatomically contoured curve $Z_{\text{neck}}(\theta)$:
- **Central Cleavage Plunge** ($\theta = \frac{3\pi}{2}$, $X = 0$): Dips to $Z = 1.185 \cdot s$.
- **Cup Crest Peaks** ($X = \pm 0.065 \cdot s$): Rises smoothly to $Z = 1.255 \cdot s$.
- **Axillary Armhole Scoop** ($X = \pm 0.145 \cdot s$): Dips under the arms to $Z = 1.205 \cdot s$.
- **Dorsal Scapular Line** ($\theta = \frac{\pi}{2}$, back): Settles at a clean horizontal line $Z = 1.230 \cdot s$.

#### 4.2.4 Anatomical Spaghetti Straps
Rather than a constant $X$, each strap follows the 3D curvature of the female shoulder girdle across 8 quad segments:
- Anchor on front cup crest: $( \pm 0.065 \cdot s, -0.125 \cdot s, 1.255 \cdot s )$
- Passing over the clavicle: $( \pm 0.072 \cdot s, -0.060 \cdot s, 1.320 \cdot s )$
- Shoulder apex ridge (trapezius): $( \pm 0.078 \cdot s, +0.010 \cdot s, 1.368 \cdot s )$
- Back shoulder descent: $( \pm 0.072 \cdot s, +0.055 \cdot s, 1.310 \cdot s )$
- Back bodice anchor: $( \pm 0.066 \cdot s, +0.095 \cdot s, 1.230 \cdot s )$
Strap width is calibrated to $0.009 \cdot s$ (9mm), cleanly welded to the top rim vertices.

---

### 4.3 Skirt Drapery: Organic Gravity Folds & Hemline Sag

#### 4.3.1 Multi-Harmonic Gravity Drapery Formula
To replace the artificial 20-wave cosine fluting, the skirt radius modulation uses a multi-harmonic fold synthesis with anisotropic angular weighting:
$$R(\theta, z) = R_{\text{base}}(z) \cdot \left[ 1.0 + \sum_{k=1}^{3} A_k(z) \cdot \cos(n_k \cdot \theta + \phi_k) \cdot W_{\text{region}}(\theta) \right]$$
Where:
- $n_1 = 6$ (primary body drape folds: 2 front-lateral, 2 side-hip, 2 rear-gluteal)
- $n_2 = 8$ (secondary cloth ripples)
- $n_3 = 12$ (fine fabric soft creases)
- Harmonic amplitudes grow naturally under gravity:
  $$A_1(z) = 0.065 \cdot (t^{1.4}), \quad A_2(z) = 0.025 \cdot (t^{1.6}), \quad A_3(z) = 0.012 \cdot (t^{1.8})$$
  where $t = \frac{z_{\text{waist}} - z}{z_{\text{waist}} - z_{\text{hem}}} \in [0, 1]$.
  At the waist ($t = 0$), fold amplitude is exactly **0** (perfectly smooth cinch).
  At the hem ($t = 1$), folds reach their full natural volume (~25–35mm ripple).

#### 4.3.2 Anisotropic Thigh Flattening ($W_{\text{region}}(\theta)$)
In real clothing, fabric resting against the anterior thighs cannot form deep inward folds because the legs push it outward:
$$W_{\text{region}}(\theta) = \begin{cases}
0.35 + 0.65 \cdot |\cos(\theta)| & \text{if } \sin(\theta) < -0.2 \text{ (anterior thigh region)} \\
1.00 & \text{otherwise (lateral and posterior drape)}
\end{cases}$$
This prevents the skirt from caving into the thighs and creates the authentic smooth drape seen in `media_1788785935849.jpg`.

#### 4.3.3 Undulating Scalloped Hemline with Natural Gravity Sag
The hem elevation $Z_{\text{hem}}(\theta)$ incorporates an organic gravity sag function:
$$Z_{\text{hem}}(\theta) = Z_{\text{base\_hem}} - 0.014 \cdot s \cdot \left[ \cos(6\theta) + 0.5 \cdot \cos(2\theta) \right] + \Delta z_{\text{front/back}}(\theta)$$
- Fold crests drop $12\text{mm}$ lower than troughs.
- Front hem settles slightly higher than rear hem ($\Delta z_{\text{front/back}} = -0.010 \cdot s \cdot \sin(\theta)$) to account for buttock curvature and matching the concept turnaround profile.

---

### 4.4 Ice-Blue Satin Sash Engineering: Conforming Fit & Bow Knot

#### 4.4.1 Zero-Penetration Conforming Offset
To eliminate Z-fighting and mesh intersections:
- The sash inner surface is constructed by taking the exact outer boundary of the dress waist at $Z \in [1.02m \cdot s, 1.07m \cdot s]$ and applying a strict radial offset:
  $$R_{\text{sash\_inner}}(\theta, z) = R_{\text{dress}}(\theta, z) + \Delta r_{\text{clearance}}$$
  where $\Delta r_{\text{clearance}} = +0.0025 \cdot s$ (2.5mm).
- The sash band has an outer thickness of $0.0020 \cdot s$ (2.0mm).
- Clearance margin between sash inner surface and dress outer surface is guaranteed positive:
  $$\min(d_{\text{sash} \to \text{dress}}) \ge +2.0\text{mm} > 0$$
- Result: **0% Z-fighting, 0 penetrating vertices, 0 BVH face overlaps**.

#### 4.4.2 Volumetric 3D Bow Knot (Nút Thắt Nơ)
Located at the front center-left ($X_{\text{knot}} \approx -0.015 \cdot s$, $Z_{\text{knot}} \approx 1.045 \cdot s$):
1. **Central Knot Wrap**:
   A 3D rounded cuboid pillow (width 32mm, height 26mm, depth 18mm) with quad-capped rounded edges, resting cleanly on the sash band with $+3\text{mm}$ clearance.
2. **Left and Right Bow Loops**:
   - Each loop is constructed as an arching ribbon tube with thickness.
   - Left loop sweeps from knot outward to $X \approx -0.075 \cdot s$, $Z \approx 1.075 \cdot s$, curving gracefully back to the knot.
   - Right loop sweeps symmetrically to $X \approx +0.045 \cdot s$, $Z \approx 1.075 \cdot s$.
   - Loop width: $22\text{mm}$, thickness: $1.5\text{mm}$.
3. **Twin Cascading Ribbon Streamers (Dải Ruy-Băng)**:
   - Suspended from beneath the central knot at $Z \approx 1.030 \cdot s$.
   - Cascading length: $0.38 \cdot s$ (extending down to $Z \approx 0.65m$, mid-thigh).
   - Dynamic S-curve flutter along $X$ and $Y$ to follow the flare of the skirt:
     $$x_{\text{ribbon}}(t) = x_{\text{base}} \pm 0.035 \cdot (t^{1.3}) \cdot s$$
     $$y_{\text{ribbon}}(t) = y_{\text{skirt}}(z) - 0.004 \cdot s - 0.008 \cdot \sin(\pi t) \cdot s$$
   - Streamer hem finished with an angled fishtail cut.

---

## 5. Rigging, Deformation & Modifier Pipeline

### 5.1 Rigify 163 DEF Bone Weight Distribution
To resolve the critical defect where the dress does not deform with the character rig, the dress generator must create standardized vertex groups corresponding to Rigify 163 DEF bones:

| Garment Region | Elevation $Z$ | Controlling DEF Bones | Weight Distribution Formula |
|---|---|---|---|
| **Bodice Straps & Neckline** | $Z > 1.25m$ | `DEF-spine.003` (85%), `DEF-spine.002` (15%) | Fixed anchor to upper chest |
| **Bodice Breast Cups** | $Z \in [1.12m, 1.25m]$ | `DEF-spine.002` (80%), `DEF-spine.003` (10%), `DEF-spine.001` (10%) | Follows ribcage & breathing |
| **Bodice Lower Midriff** | $Z \in [1.03m, 1.12m]$ | `DEF-spine.001` (80%), `DEF-spine.002` (20%) | Follows waist twist |
| **Waist Sash & Bow** | $Z \in [1.02m, 1.07m]$ | `DEF-spine.001` (70%), `DEF-spine` (30%) | Follows waistline snugly |
| **Upper Skirt** | $Z \in [0.88m, 1.03m]$ | `DEF-spine` (75%), `DEF-spine.001` (25%) | Follows pelvis tilt |
| **Mid Skirt (Left Flank)** | $Z \in [0.65m, 0.88m], X > 0.03$ | `DEF-spine` (30%), `DEF-thigh.L` (50%), `DEF-thigh.L.001` (20%) | Moves with left leg |
| **Mid Skirt (Right Flank)** | $Z \in [0.65m, 0.88m], X < -0.03$ | `DEF-spine` (30%), `DEF-thigh.R` (50%), `DEF-thigh.R.001` (20%) | Moves with right leg |
| **Skirt Center Crotch Zone** | $Z \in [0.65m, 0.88m], \|X\| \le 0.03$ | `DEF-spine` (50%), `DEF-thigh.L` (25%), `DEF-thigh.R` (25%) | Prevents skirt splitting in stride |
| **Lower Skirt Hem** | $Z \in [0.50m, 0.65m]$ | `DEF-thigh.L.001` (40%), `DEF-thigh.R.001` (40%), `DEF-spine` (20%) | Smooth blending around knees |

Every vertex will have its weights strictly normalized such that $\sum w_i = 1.0$.

### 5.2 Complementary Surface Deform Binding
In Blender, in addition to direct Rigify vertex groups, the script will support a `SURFACE_DEFORM` modifier binding `Mesh_Dress` to `Yu_Nian_An_Body`. This allows zero-penetration tracking of subtle body morphs and FACS blendshapes.

### 5.3 Solidify Modifier Configuration
- `thickness = 0.002` (2.0mm fabric thickness).
- `offset = 1.0` (**Outward extrusion**). This ensures that adding thickness expands fabric away from the body rather than pushing it inward into the skin!
- `use_even_offset = True` (prevents pinching at sharp fold corners).
- `use_rim = True` and `use_rim_only = False` (clean manifold edge loops).
- `use_quality_normals = True`.

### 5.4 Seam-Preserving UV Unwrap
- Cylinder seam placed along the posterior dorsal midline ($\theta = \frac{\pi}{2}$, $X = 0, Y > 0$).
- Seam vertices duplicated with $U = 1.0$ (while starting vertices have $U = 0.0$).
- Eliminates 100% of horizontal reverse texture wrapping artifacts.

---

## 6. PBR Material Upgrade Specifications

### 6.1 White Silk Dress (`Mat_Dress_WhiteSilk`)
```python
MAT_DRESS_WHITESILK = HumanMaterialConfig(
    name="Mat_Dress_WhiteSilk",
    base_color=(0.95, 0.95, 0.96, 1.0),   # Off-white pure ivory silk
    roughness=0.36,
    metallic=0.0,
    specular_ior_level=0.55,
    ior=1.46,
    sheen_weight=0.75,                     # Rich micro-fiber cloth sheen
    sheen_roughness=0.30,
    sheen_tint=(0.92, 0.95, 1.00, 1.0),
    subsurface_weight=0.12,                # Translucent backlight SSS
    subsurface_radius=(0.85, 0.88, 0.95),
    subsurface_scale=0.010,
    bump_strength=0.018,                   # Delicate fine silk weave
    bump_scale=500.0,
    texture_type="NOISE",
    description="Off-white organic silk dress with micro-sheen and subtle translucency",
)
```

### 6.2 Ice-Blue Satin Sash (`Mat_Dress_WaistBelt` / `Mat_Sash_IceBlueSatin`)
```python
MAT_DRESS_WAISTBELT = HumanMaterialConfig(
    name="Mat_Dress_WaistBelt",
    base_color=(0.65, 0.78, 0.90, 1.0),   # Ice-blue pastel sky tone (matching turnaround)
    roughness=0.20,                        # Glossy liquid satin finish
    metallic=0.05,
    specular_ior_level=0.60,
    ior=1.49,
    sheen_weight=0.90,                     # Intense high-sheen satin luster
    sheen_roughness=0.22,
    sheen_tint=(0.80, 0.90, 1.00, 1.0),
    bump_strength=0.012,                   # Ultra-fine satin warp/weft
    bump_scale=650.0,
    texture_type="NOISE",
    description="Ice-blue satin waist sash and bow knot with radiant high-sheen luster",
)
```

---

## 7. Comparative Assessment: Current vs Proposed Redesign

| Feature | Current Implementation (`wardrobe.py`) | Proposed Organic Redesign |
|---|---|---|
| **Skirt Drape Math** | Rigid cone + $\cos(20\theta)$ fluting (sawtooth zigzag) | Multi-harmonic gravity folds ($n=6,8,12$) + thigh flattening |
| **Hemline Profile** | Perfectly flat in Z ($Z = 0.52m$) | Organic undulating scalloped hem with gravity sag ($\Delta z = 14\text{mm}$) |
| **Bust Contour** | Single forward elliptical stretch ("uniboob") | Dual sculpted teardrop breast cups with 12mm medial cleavage |
| **Neckline** | Simple dip on top ring | Sweetheart scoop curve with cup crests and strap transitions |
| **Spaghetti Straps** | Flat 2D floating strips with constant X | 3D contoured quad ribbons following shoulder girdle curvature |
| **Waist Sash** | Straight cylinder + flat 1-quad "knot", no bow loops | 100% conforming envelope + 3D bow knot + twin cascading streamers |
| **Sash Material** | Dark grey / black `(0.15, 0.15, 0.15)` | Authentic Ice-Blue Satin `(0.65, 0.78, 0.90)` with high sheen |
| **Z-Fighting / Penetration** | Skirt pleats penetrate sash (clearance gap $\le 0$) | Strict $+2.5\text{mm}$ offset envelope: 0 penetrations, 0 Z-fighting |
| **Rigging & Deformation** | **0 vertex groups** (completely frozen in armature pose) | Full Rigify DEF bone weighting (`DEF-spine.*`, `DEF-thigh.*`) |
| **Cloth Thickness** | Solidify inward (penetrates body) | Solidify outward (`offset=1.0`, `thickness=0.002`, `use_even_offset=True`) |
| **UV Unwrap** | Discontinuous rear seam stretching ($0.96 \to 0.0$) | Clean cylindrical UV projection with duplicate seam vertices |

---

## 8. Verification & Invalidation Protocol

### 8.1 Automated Verification Commands
1. **Geometry & Topology Assertions (`pytest tests/test_wardrobe.py`)**:
   - Verify pure-quad / quad-dominant topology ($\ge 95\%$ quads, 0 non-manifold edges).
   - Verify A-line flare ratio ($r_{\text{hem}} > 1.8 \cdot r_{\text{waist}}$).
   - Verify strap top reaches $Z \ge 1.34m$ and skirt hem reaches $Z \in [0.48m, 0.55m]$.
2. **Clearance & Penetration Audit (`tests/test_challenger_m4_iter7_empirical.py`)**:
   - Bodice-to-Body signed clearance $\ge +4.0\text{mm}$ (0 penetrations, 0 BVH face overlaps).
   - Sash-to-Dress signed clearance $\ge +2.0\text{mm}$ (0 penetrations, 0 BVH face overlaps).
3. **Vertex Group & Weight Sum Validation**:
   - Assert all dress meshes contain vertex groups: `DEF-spine.003`, `DEF-spine.002`, `DEF-spine.001`, `DEF-spine`, `DEF-thigh.L`, `DEF-thigh.R`.
   - Assert every vertex has $\sum w_i = 1.0 \pm 10^{-4}$.
4. **Color & Shader Validation**:
   - Assert `Mat_Dress_WaistBelt` base color is ice-blue ($R \in [0.60, 0.70]$, $G \in [0.72, 0.84]$, $B \in [0.85, 0.95]$).

### 8.2 Invalidation Conditions
- Any occurrence of rigid sinusoidal fluting $\cos(k\theta)$ with $k \ge 16$ on low sector counts.
- Any planar flat hemline with zero $Z$ variation.
- Any mesh penetration between body, dress, or sash in rest pose or standard stride pose ($\text{clearance} < 0$).
- Missing vertex groups causing frozen garments under armature pose transforms.
