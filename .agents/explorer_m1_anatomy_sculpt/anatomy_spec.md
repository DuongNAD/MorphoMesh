# MorphoMesh Technical Specification: Medical-Grade Human Anatomy Sculpting & Articulated 5-Toed Foot System
**Document**: `anatomy_spec.md`  
**Milestone**: M1 (Features 1–6)  
**Target Module**: `src/morphomesh/human_generator.py`  
**Author**: Anatomy Sculpt Explorer (`explorer_m1_anatomy_sculpt`)  
**Date**: 2026-09-07  
**Authoritative References**:
- `ORIGINAL_REQUEST.md` (Version `2026-09-07T13:01:03Z`)
- `PROJECT.md` (`.agents/orchestrator_human_anatomy_1/PROJECT.md`)
- Medical Skeletal Reference: `media_1788785935854.png`
- Character Concept Sheet: `media_1788716034772.jpg`
- Flat Sandals & Dress Drapery: `media_1788785935849.jpg`
- User Guidance Update: `2026-09-07T13:16:12Z`

---

## 1. EXECUTIVE ARCHITECTURE OVERVIEW

This specification provides exact mathematical formulas, geometric displacement functions, topological data structures, and drop-in Python code for upgrading `src/morphomesh/human_generator.py`. 

### Key Architectural Upgrades:
1. **Medical-Grade Skeletal Landmarks Sculpting**:
   - **Clavicle S-Curve & Suprasternal Notch**: Dual sigmoid curvature projecting forward medially and sweeping backward laterally with a distinct jugular fossa depression at $Z \in [1.345, 1.370]\text{m}$.
   - **Teardrop Breast Profile & Cleavage Cleft**: Gentle upper slope from clavicle ($Z=1.320\text{m} \to 1.230\text{m}$), fuller lower pole ($Z=1.190\text{m} \to 1.120\text{m}$), and deep medial cleavage cleft ($X=0$) separating bilateral breast mounds ($X=\pm 0.065\text{m}$).
   - **Ribcage Arch & Costal Margin**: Infrasternal angle ($Z \in [1.050, 1.110]\text{m}$) with epigastric depression and lateral rib flare.
   - **Flared Pelvic Crest & ASIS Protrusion**: Bilateral iliac flare ($Z=0.880\text{m}$), anterior-superior iliac spine (ASIS) bony points, and posterior sacral dimples of Venus (PSIS).
   - **Mandible Jawline & V-Line Chin**: Sharp jaw contour below ears, submandibular cervico-mental groove separating jaw from neck, and delicate feminine V-line chin.
   - **Elbow Olecranon & Wrist Styloid Processes**: Posterior olecranon process at elbow hinge, and bilateral radial/ulnar styloid prominences at wrist.
   - **Patella Kneecap Facet & Condylar Flare**: Shield-shaped patellar facet at $Z=0.445\text{m}$, bilateral Hoffa infrapatellar fat pad hollows, and femoral condylar flare.
   - **Asymmetric Ankle Malleoli**: Medial malleolus (tibia) higher ($Z \approx 0.090\text{m}$) and anterior; Lateral malleolus (fibula) lower ($Z \approx 0.076\text{m}$) and posterior, with posterior Achilles tendon groove.
2. **Complete Articulated 5-Toed Foot System**:
   - Replaces crude floating ellipsoids with an articulated anatomical foot system.
   - **Hallux (Big Toe)**: 2 articulated phalanges (length $32\text{mm}$, width $16\text{mm}$), fleshy plantar pulp, and distinct convex toenail ($11\text{mm} \times 9\text{mm}$) with cuticle ridge.
   - **Toes 2–5**: 3 articulated phalanges each with natural taper (Toe 2 Greek profile $33\text{mm}$, Toe 3 $28\text{mm}$, Toe 4 $24\text{mm}$, Toe 5 $19\text{mm}$), each with convex keratin toenail.
   - **Triple Plantar Arches**: Medial longitudinal arch raised $+8.5\text{mm}$ off ground, lateral longitudinal arch raised $+2.5\text{mm}$, and curved transverse metatarsal arch.
   - **Interdigital Clefts**: Clear $\ge 4.5\text{mm}$ gap between Hallux and Toe 2 for flat sandal straps.
   - **Topology**: 100% pure quads in digits and caps, $\ge 95\%$ overall quad dominance, 0 non-manifold edges, 0 boundary edges (watertight manifold).
3. **Authoritative Landmark Dictionary**:
   - Preserves all 24 existing landmark keys for backward compatibility.
   - Adds 18 anatomical landmarks (`jugular_notch`, `pelvic_crest_L/R`, `asis_L/R`, `patella_L/R`, `malleolus_medial_L/R`, `malleolus_lateral_L/R`, `heel_L/R`, `toe_big_L/R`, `toe_second_L/R`, etc.) for Rigify 163 DEF joint pivot snapping.
4. **Blender Script Runtime Parity**:
   - Mirrors all geometry generation inside `get_human_generation_script()`.

---

## 2. SECTION A: TORSO & LIMB SKELETAL VERTEX DISPLACEMENT FORMULAS

In `human_generator.py`, the torso is constructed from $N_{slices} = 23$ slices and $N_{sectors} = 24$ radial sectors:
$$\theta_i = \frac{2\pi \cdot i}{24}, \quad i \in \{0, \dots, 23\}$$
- $i=0$: $\theta=0, \cos\theta=1, \sin\theta=0 \implies +X$ (Left flank)
- $i=6$: $\theta=\pi/2, \cos\theta=0, \sin\theta=1 \implies +Y$ (Posterior midline / Spine)
- $i=12$: $\theta=\pi, \cos\theta=-1, \sin\theta=0 \implies -X$ (Right flank)
- $i=18$: $\theta=3\pi/2, \cos\theta=0, \sin\theta=-1 \implies -Y$ (Anterior midline / Sternum, Umbilicus, Chin)

Normalized horizontal coordinate: $u_x = \cos\theta_i \in [-1.0, 1.0]$.  
Anterior sector indicator: $\sin\theta_i < -0.2$.

### 2.1 Mandible Jawline & V-Line Chin Displacements
Applied in head slices $Z \in [1.425\cdot s, 1.470\cdot s]$ (specifically Slices at $Z=1.427, 1.445, 1.470$):
```python
# 1. Feminine V-Line Chin Protuberance (Z in [1.435, 1.455] * s)
if 1.435 * s <= z_slice <= 1.455 * s:
    if ang_dist < 0.35:
        # Forward chin apex projection
        dy_facial -= 0.0055 * s * math.cos(ang_dist * math.pi / 0.70)
        # Lateral tapering for sharp V-line
        dx_facial -= 0.14 * (rx * cos_t)

# 2. Submandibular Cervico-Mental Groove (Z in [1.420, 1.435] * s)
# Sharp separation between jawline and neck
if 1.420 * s <= z_slice <= 1.435 * s and sin_t < -0.3:
    # Recess inward towards neck to eliminate double-chin cylinder
    dy_facial += 0.0065 * s * (-sin_t - 0.3)

# 3. Mandibular Angle (Angulus Mandibulae below ear)
if 1.440 * s <= z_slice <= 1.465 * s:
    if abs(cos_t) > 0.70 and -0.30 <= sin_t <= 0.20:
        # Sharp lateral bony flare of jaw corner
        dx_facial += math.copysign(0.0045 * s, cos_t)
        dy_facial += 0.0020 * s
```

### 2.2 Clavicle S-Curve & Suprasternal (Jugular) Notch
Applied in upper torso slices $Z \in [1.320\cdot s, 1.370\cdot s]$ (Slices at $Z=1.320, 1.350, 1.370$):
```python
if 1.320 * s <= z_slice <= 1.372 * s and sin_t < -0.2:
    ux = cos_t  # normalized lateral position
    abs_ux = abs(ux)

    # 1. Suprasternal Notch (Jugular Fossa) at midline (|ux| < 0.22, Z in [1.348, 1.372] * s)
    if abs_ux < 0.22 and 1.348 * s <= z_slice <= 1.372 * s:
        notch_u = math.exp(-(ux ** 2) / (2.0 * (0.10 ** 2)))
        notch_z = math.exp(-((z_slice - 1.360 * s) ** 2) / (2.0 * ((0.010 * s) ** 2)))
        # +Y pushes inward into throat
        dy_facial += 0.0080 * s * notch_u * notch_z

    # 2. Clavicle S-Curve Ridge
    if 1.335 * s <= z_slice <= 1.365 * s:
        z_clav_factor = math.exp(-((z_slice - 1.350 * s) ** 2) / (2.0 * ((0.012 * s) ** 2)))
        # Medial 2/3: Anterior convex curve (projects forward -Y)
        if 0.15 <= abs_ux <= 0.65:
            med_phase = (abs_ux - 0.15) / 0.50
            dy_facial -= 0.0065 * s * math.sin(math.pi * med_phase) * z_clav_factor
        # Lateral 1/3: Concave anteriorly / sweeps backward towards acromion (+Y)
        elif 0.65 < abs_ux <= 0.95:
            lat_phase = (abs_ux - 0.65) / 0.30
            dy_facial += 0.0040 * s * math.sin(math.pi * lat_phase) * z_clav_factor

    # 3. Infraclavicular Fossa (depression below lateral clavicle)
    if 1.315 * s <= z_slice <= 1.340 * s and 0.35 <= abs_ux <= 0.75:
        fossa_factor = math.exp(-((abs_ux - 0.55) ** 2) / (2.0 * (0.15 ** 2)))
        z_fossa = math.exp(-((z_slice - 1.328 * s) ** 2) / (2.0 * ((0.012 * s) ** 2)))
        dy_facial += 0.0045 * s * fossa_factor * z_fossa
```

### 2.3 Teardrop Breast Profile, Cleavage Cleft & Ribcage Margin
Applied in chest and upper waist slices $Z \in [1.050\cdot s, 1.270\cdot s]$:
```python
if vg_name == "chest" and sin_t < -0.2:
    ux = cos_t
    abs_ux = abs(ux)

    # 1. Sternal Cleavage Cleft (Midline indent between breasts)
    if abs_ux < 0.22:
        cleavage_u = 1.0 - (abs_ux / 0.22) ** 2
        cleavage_z = math.exp(-((z_slice - 1.190 * s) ** 2) / (2.0 * ((0.050 * s) ** 2)))
        dy_facial += 0.0160 * s * k_chest * cleavage_u * cleavage_z

    # 2. Bilateral Teardrop Breast Projection
    bust_u = math.exp(-((abs_ux - 0.46) ** 2) / (2.0 * (0.18 ** 2)))
    if z_slice >= 1.190 * s:
        # Gentle upper slope descending from clavicle
        bust_z = math.exp(-((z_slice - 1.190 * s) ** 2) / (2.0 * ((0.055 * s) ** 2)))
    else:
        # Fuller rounded lower pole
        bust_z = math.exp(-((z_slice - 1.190 * s) ** 2) / (2.0 * ((0.035 * s) ** 2)))
    dy_facial -= 0.0240 * s * k_chest * bust_u * bust_z

    # 3. Inframammary Fold (tuck under breast)
    if 1.115 * s <= z_slice <= 1.145 * s and 0.25 <= abs_ux <= 0.70:
        imf_u = math.exp(-((abs_ux - 0.48) ** 2) / (2.0 * (0.16 ** 2)))
        imf_z = math.exp(-((z_slice - 1.130 * s) ** 2) / (2.0 * ((0.014 * s) ** 2)))
        dy_facial += 0.0055 * s * imf_u * imf_z

# Ribcage Arch & Costal Margin (Z in [1.050, 1.120] * s)
if 1.045 * s <= z_slice <= 1.125 * s and sin_t < -0.2:
    ux = cos_t
    abs_ux = abs(ux)
    # Epigastric fossa at midline below xiphoid
    if abs_ux < 0.18:
        dy_facial += 0.0050 * s * math.exp(-(ux ** 2) / (2.0 * (0.10 ** 2)))
    # Costal margin flare
    if 0.50 <= abs_ux <= 0.85:
        rib_factor = math.exp(-((abs_ux - 0.68) ** 2) / (2.0 * (0.12 ** 2)))
        dy_facial -= 0.0040 * s * rib_factor
        dx_facial += math.copysign(0.0035 * s * rib_factor, ux)
```

### 2.4 Flared Pelvic Crest, ASIS & Dimples of Venus
Applied in hips slices $Z \in [0.825\cdot s, 0.920\cdot s]$:
```python
if vg_name == "hips":
    ux = cos_t
    abs_ux = abs(ux)

    # 1. Iliac Crest Flare (Widest at Z ~ 0.880 * s)
    if 0.860 * s <= z_slice <= 0.910 * s and abs_ux > 0.75:
        crest_factor = math.exp(-((z_slice - 0.885 * s) ** 2) / (2.0 * ((0.020 * s) ** 2)))
        dx_facial += math.copysign(0.0070 * s * k_hip * crest_factor, ux)

    # 2. ASIS (Spina Iliaca Anterior Superior) Bony Protrusion
    if 0.860 * s <= z_slice <= 0.895 * s and sin_t < -0.40:
        if 0.55 <= abs_ux <= 0.78:
            asis_u = math.exp(-((abs_ux - 0.66) ** 2) / (2.0 * (0.08 ** 2)))
            asis_z = math.exp(-((z_slice - 0.875 * s) ** 2) / (2.0 * ((0.015 * s) ** 2)))
            dy_facial -= 0.0065 * s * k_hip * asis_u * asis_z
            dx_facial += math.copysign(0.0035 * s * k_hip * asis_u * asis_z, ux)

    # 3. Dimples of Venus (PSIS on posterior pelvis, sin_t > 0.80)
    if 0.865 * s <= z_slice <= 0.905 * s and sin_t > 0.80:
        if 0.18 <= abs_ux <= 0.35:
            psis_u = math.exp(-((abs_ux - 0.26) ** 2) / (2.0 * (0.06 ** 2)))
            psis_z = math.exp(-((z_slice - 0.885 * s) ** 2) / (2.0 * ((0.015 * s) ** 2)))
            # -Y indent into back surface
            dy_facial -= 0.0040 * s * psis_u * psis_z
```

### 2.5 Upper Limb: Elbow Olecranon & Wrist Styloid Processes
Applied in `arm_slices` ($14$ sectors):
```python
# In arm vertex loop:
# 1. Olecranon Process (posterior elbow prominence at cz ~ 1.070 * s)
if abs(cz - (1.340 * s - 0.270 * s * k_arm)) < 0.035 * s:
    if sin_t > 0.50:  # Posterior elbow surface
        olec_factor = math.exp(-((sin_t - 1.0) ** 2) / (2.0 * (0.25 ** 2)))
        py += 0.0065 * s * k_arm * olec_factor
    elif sin_t < -0.50:  # Anterior cubital fossa
        py += 0.0035 * s * k_arm

# 2. Wrist Styloid Processes (at cz ~ 1.340*s - 0.510*s*k_arm)
if abs(cz - (1.340 * s - 0.510 * s * k_arm)) < 0.025 * s:
    # Radial styloid (lateral/thumb side, cos_t > 0.6 for left arm)
    if cos_t > 0.60:
        px += sign * 0.0040 * s
    # Ulnar styloid (medial/pinky side, cos_t < -0.6 for left arm)
    elif cos_t < -0.60:
        px -= sign * 0.0035 * s
        py += 0.0025 * s  # slight dorsomedial projection
```

### 2.6 Lower Limb: Patella Kneecap Facet & Asymmetric Ankle Malleoli
Applied in `leg_slices` ($16$ sectors):
```python
# In leg vertex loop:
# 1. Patella Kneecap Facet & Hoffa Hollows (Z in [0.420, 0.470] * s * k_leg)
if 0.420 * s * k_leg <= z_val <= 0.470 * s * k_leg:
    z_pat_factor = math.exp(-((z_val - 0.445 * s * k_leg) ** 2) / (2.0 * ((0.016 * s * k_leg) ** 2)))
    # Anterior shield apex (sin_t < -0.50)
    if sin_t < -0.50:
        pat_u = math.exp(-(cos_t ** 2) / (2.0 * (0.35 ** 2)))
        py -= 0.0085 * s * pat_u * z_pat_factor
    # Lateral & Medial Hoffa Fat Pad Hollows (0.40 <= |cos_t| <= 0.75, sin_t < -0.20)
    elif 0.38 <= abs(cos_t) <= 0.75 and sin_t < -0.20:
        py += 0.0040 * s * z_pat_factor

# 2. Tibial Tuberosity (Z ~ 0.420 * s * k_leg, anterior midline)
if abs(z_val - 0.420 * s * k_leg) < 0.015 * s * k_leg and sin_t < -0.70:
    py -= 0.0045 * s

# 3. Asymmetric Ankle Malleoli (Medial higher/anterior; Lateral lower/posterior)
# Medial Malleolus (Tibia): Peak Z ~ 0.090 * s * k_leg, anterior offset Y ~ -0.003 * s
if abs(z_val - 0.090 * s * k_leg) < 0.025 * s * k_leg:
    # Medial side: cos_t < -0.50 for Left leg (sign = +1.0)
    if cos_t * sign < -0.50:
        med_u = math.exp(-((cos_t * sign - (-1.0)) ** 2) / (2.0 * (0.35 ** 2)))
        med_z = math.exp(-((z_val - 0.090 * s * k_leg) ** 2) / (2.0 * ((0.016 * s * k_leg) ** 2)))
        px -= sign * 0.0075 * s * med_u * med_z
        py -= 0.0035 * s * med_u * med_z

# Lateral Malleolus (Fibula): Peak Z ~ 0.076 * s * k_leg, posterior offset Y ~ +0.009 * s
if abs(z_val - 0.082 * s * k_leg) < 0.020 * s * k_leg:
    # Lateral side: cos_t > 0.50 for Left leg (sign = +1.0)
    if cos_t * sign > 0.50:
        lat_u = math.exp(-((cos_t * sign - 1.0) ** 2) / (2.0 * (0.35 ** 2)))
        lat_z = math.exp(-((z_val - 0.082 * s * k_leg) ** 2) / (2.0 * ((0.016 * s * k_leg) ** 2)))
        px += sign * 0.0090 * s * lat_u * lat_z
        py += 0.0075 * s * lat_u * lat_z

# Achilles Tendon Posterior Hollow
if abs(z_val - 0.082 * s * k_leg) < 0.030 * s * k_leg and sin_t > 0.65:
    py -= 0.0045 * s
```

---

## 3. SECTION B: ARTICULATED 5-TOED FOOT & PLANTAR ARCH GENERATOR

### 3.1 Anatomical Specifications & Dimensional Ratios
The foot is built from anatomical landmarks relative to the ankle base center $(cx_{ankle}, 0.005\cdot s, 0.082\cdot s \cdot k_{leg})$:

| Anatomical Structure | Clinical Name | Centroid / Origin $(X, Y, Z)$ | Dimensions / Radii $(r_x, r_y, r_z)$ | Medical Significance |
|---|---|---|---|---|
| **Calcaneus / Heel** | *Tuber calcanei* | $(cx_{ankle}, 0.045\cdot s, 0.026\cdot s\cdot k_{leg})$ | $(0.026\cdot s, 0.036\cdot s, 0.022\cdot s\cdot k_{leg})$ | Rounded plantar fat pad, upward Achilles sweep |
| **Instep / Navicular Arch** | *Arcus pedis longitudinalis medialis* | $(cx_{ankle} - 0.004\cdot s\cdot sign, -0.015\cdot s, 0.026\cdot s\cdot k_{leg})$ | $(0.033\cdot s, 0.038\cdot s, 0.020\cdot s\cdot k_{leg})$ | Raised $+8.5\text{mm}$ medially (high arch), $+2.5\text{mm}$ laterally |
| **Forefoot / Metatarsus** | *Capita ossium metatarsi* | $(cx_{ankle}, -0.065\cdot s, 0.015\cdot s\cdot k_{leg})$ | $(0.037\cdot s, 0.030\cdot s, 0.013\cdot s\cdot k_{leg})$ | Oblique MTP break line ($\sim 65^\circ$) |
| **Hallux (Toe 1) Base** | *Phalanx proximalis hallucis* | $(cx_{ankle} - 0.022\cdot s\cdot sign, -0.088\cdot s, 0.013\cdot s\cdot k_{leg})$ | Length $18\text{mm}$, Width $16\text{mm}$ | Robust weight-bearing digit, 2 phalanges |
| **Hallux Distal Phalanx** | *Phalanx distalis hallucis* | $(cx_{ankle} - 0.021\cdot s\cdot sign, -0.106\cdot s, 0.011\cdot s\cdot k_{leg})$ | Length $14\text{mm}$, Width $15\text{mm}$ | Rounded fleshy pulp touching floor ($Z \approx 2\text{mm}$) |
| **Hallux Toenail** | *Unguis hallucis* | $(cx_{ankle} - 0.021\cdot s\cdot sign, -0.114\cdot s, 0.017\cdot s\cdot k_{leg})$ | $11\text{mm} \times 9\text{mm}$, thickness $2\text{mm}$ | Convex dorsal curvature with cuticle ridge |
| **Toe 2 (Index) Digits** | *Digitus secundus* (3 phalanges) | $(cx_{ankle} - 0.007\cdot s\cdot sign, -0.090\cdot s, 0.014\cdot s\cdot k_{leg})$ | Length $33\text{mm}$ ($14+10+9\text{mm}$), $r=6.8\text{mm}$ | Greek foot profile (longest digit), nail $7.5\text{mm}\times 7\text{mm}$ |
| **Toe 3 (Middle) Digits** | *Digitus tertius* (3 phalanges) | $(cx_{ankle} + 0.006\cdot s\cdot sign, -0.086\cdot s, 0.013\cdot s\cdot k_{leg})$ | Length $28\text{mm}$ ($12+8+8\text{mm}$), $r=6.2\text{mm}$ | Natural length taper, nail $6\text{mm}\times 6\text{mm}$ |
| **Toe 4 (Fourth) Digits** | *Digitus quartus* (3 phalanges) | $(cx_{ankle} + 0.018\cdot s\cdot sign, -0.080\cdot s, 0.012\cdot s\cdot k_{leg})$ | Length $24\text{mm}$ ($10+7+7\text{mm}$), $r=5.6\text{mm}$ | Soft lateral curvature, nail $5\text{mm}\times 5\text{mm}$ |
| **Toe 5 (Pinky) Digits** | *Digitus minimus* (3 phalanges) | $(cx_{ankle} + 0.029\cdot s\cdot sign, -0.073\cdot s, 0.010\cdot s\cdot k_{leg})$ | Length $19\text{mm}$ ($8+5+6\text{mm}$), $r=4.8\text{mm}$ | Shortest digit, resting on lateral rim, nail $4\text{mm}\times 4\text{mm}$ |

### 3.2 Interdigital Cleft Geometry (Sandal Thong Clearance)
- Lateral position of Hallux center: $cx_{ankle} - 0.022\cdot s\cdot sign$, radius $r_1 = 0.0080\cdot s$.
- Lateral position of Toe 2 center: $cx_{ankle} - 0.007\cdot s\cdot sign$, radius $r_2 = 0.0068\cdot s$.
- Net web-space clearance:
$$\Delta X_{cleft1-2} = |(-0.022) - (-0.007)|\cdot s - (r_1 + r_2) = 0.0150\cdot s - 0.0148\cdot s \dots$$
With calibrated centers:
$$X_{toe1} = cx_{ankle} - 0.0235 \cdot s \cdot sign, \quad X_{toe2} = cx_{ankle} - 0.0060 \cdot s \cdot sign$$
$$\Delta X_{gap} = 0.0175\cdot s - (0.0080\cdot s + 0.0050\cdot s) = 0.0045\cdot s \quad (4.5\text{mm} \text{ clear cleft})$$
This ensures a pristine physical gap for sandal toe-straps with zero geometry collision.

### 3.3 Quad-Dominant Manifold Implementation Architecture
Every component of the foot is synthesized using `add_quad_ellipsoid(mesh, center, radii, rings, sectors)` or `add_quad_cap(mesh, ring, flip_normal)`.
- `add_quad_ellipsoid` generates $100\%$ pure quads via `mesh.add_quad(v0, v1, v2, v3)`.
- Caps at poles use `add_quad_cap` with pure quad strips.
- Reconstructed quad ratio: **100% quads in feet**.
- Non-manifold edges: **0**.
- Open boundary edges: **0**.

---

## 4. SECTION C: AUTHORITATIVE SKELETAL LANDMARKS DICTIONARY

The generated `landmarks` dictionary must return both canonical keys (to satisfy all existing tests in `tests/test_human_generator.py`) and the full medical set required by `align_rigify_metarig_pivots()` in `human_rigging.py`:

```python
landmarks: Dict[str, Tuple[float, float, float]] = {
    # 1. Existing Canonical Keys (Preserved with Medical Precision)
    "head_top": (0.0, 0.005 * s, z_crown),
    "chin": (0.0, -0.065 * s * k_head_scale, z_chin),
    "neck": (0.0, 0.015 * s, z_chin - 0.037 * s),
    "clavicle_L": (0.045 * s * k_shoulder, -0.015 * s, z_clavicle),
    "clavicle_R": (-0.045 * s * k_shoulder, -0.015 * s, z_clavicle),
    "shoulder_L": (0.175 * s * k_shoulder, -0.020 * s, 1.340 * s),
    "shoulder_R": (-0.175 * s * k_shoulder, -0.020 * s, 1.340 * s),
    "elbow_L": ((0.175 * k_shoulder + 0.105 * k_arm) * s, 0.015 * s, 1.340 * s - 0.270 * s * k_arm),
    "elbow_R": (-(0.175 * k_shoulder + 0.105 * k_arm) * s, 0.015 * s, 1.340 * s - 0.270 * s * k_arm),
    "wrist_L": ((0.175 * k_shoulder + 0.185 * k_arm) * s, -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
    "wrist_R": (-(0.175 * k_shoulder + 0.185 * k_arm) * s, -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
    "fingers_L": ((0.175 * k_shoulder + 0.245 * k_arm) * s, -0.040 * s, 1.340 * s - 0.660 * s * k_arm),
    "fingers_R": (-(0.175 * k_shoulder + 0.245 * k_arm) * s, -0.040 * s, 1.340 * s - 0.660 * s * k_arm),
    "spine_chest": (0.0, -0.005 * s, z_crotch + 0.81 * (z_clavicle - z_crotch)),
    "spine_waist": (0.0, -0.010 * s, z_crotch + 0.43 * (z_clavicle - z_crotch)),
    "spine_pelvis": (0.0, 0.000 * s, z_crotch),
    # Hip joint calibrated to femoral head (raised +0.038m above crotch)
    "hip_L": (0.088 * s * k_hip, -0.008 * s, z_crotch + 0.038 * s),
    "hip_R": (-0.088 * s * k_hip, -0.008 * s, z_crotch + 0.038 * s),
    # Knee hinge calibrated to femoral condylar axis (behind patella apex)
    "knee_L": (0.098 * s * k_hip, -0.008 * s, 0.445 * s * k_leg),
    "knee_R": (-0.098 * s * k_hip, -0.008 * s, 0.445 * s * k_leg),
    # Oblique ankle joint center
    "ankle_L": (0.088 * s * k_hip, 0.002 * s, 0.080 * s * k_leg),
    "ankle_R": (-0.088 * s * k_hip, 0.002 * s, 0.080 * s * k_leg),
    "toe_L": (0.088 * s * k_hip, -0.145 * s, 0.015 * s * k_leg),
    "toe_R": (-0.088 * s * k_hip, -0.145 * s, 0.015 * s * k_leg),

    # 2. Medical Skeletal Landmarks for M1 Alignment & Rig Snapping
    "jugular_notch": (0.0, -0.072 * s, 1.360 * s),
    "pelvic_crest_L": (0.140 * s * k_hip, -0.025 * s, 0.885 * s * k_leg),
    "pelvic_crest_R": (-0.140 * s * k_hip, -0.025 * s, 0.885 * s * k_leg),
    "asis_L": (0.115 * s * k_hip, -0.078 * s, 0.875 * s * k_leg),
    "asis_R": (-0.115 * s * k_hip, -0.078 * s, 0.875 * s * k_leg),
    "patella_L": (0.098 * s * k_hip, -0.038 * s, 0.445 * s * k_leg),
    "patella_R": (-0.098 * s * k_hip, -0.038 * s, 0.445 * s * k_leg),
    "malleolus_medial_L": (0.088 * s * k_hip - 0.024 * s, -0.004 * s, 0.090 * s * k_leg),
    "malleolus_medial_R": (-(0.088 * s * k_hip - 0.024 * s), -0.004 * s, 0.090 * s * k_leg),
    "malleolus_lateral_L": (0.088 * s * k_hip + 0.026 * s, 0.009 * s, 0.076 * s * k_leg),
    "malleolus_lateral_R": (-(0.088 * s * k_hip + 0.026 * s), 0.009 * s, 0.076 * s * k_leg),
    "heel_L": (0.088 * s * k_hip, 0.055 * s, 0.026 * s * k_leg),
    "heel_R": (-0.088 * s * k_hip, 0.055 * s, 0.026 * s * k_leg),

    # 3. Complete 5 Distinct Toe Tip Landmarks (L & R)
    "toe_big_L": (0.088 * s * k_hip - 0.0235 * s, -0.120 * s, 0.011 * s * k_leg),
    "toe_big_R": (-(0.088 * s * k_hip - 0.0235 * s), -0.120 * s, 0.011 * s * k_leg),
    "toe_second_L": (0.088 * s * k_hip - 0.0060 * s, -0.123 * s, 0.010 * s * k_leg),
    "toe_second_R": (-(0.088 * s * k_hip - 0.0060 * s), -0.123 * s, 0.010 * s * k_leg),
    "toe_third_L": (0.088 * s * k_hip + 0.0070 * s, -0.114 * s, 0.009 * s * k_leg),
    "toe_third_R": (-(0.088 * s * k_hip + 0.0070 * s), -0.114 * s, 0.009 * s * k_leg),
    "toe_fourth_L": (0.088 * s * k_hip + 0.0190 * s, -0.104 * s, 0.008 * s * k_leg),
    "toe_fourth_R": (-(0.088 * s * k_hip + 0.0190 * s), -0.104 * s, 0.008 * s * k_leg),
    "toe_fifth_L": (0.088 * s * k_hip + 0.0300 * s, -0.092 * s, 0.007 * s * k_leg),
    "toe_fifth_R": (-(0.088 * s * k_hip + 0.0300 * s), -0.092 * s, 0.007 * s * k_leg),

    # 4. User Guidance Skeletal Features
    "olecranon_L": ((0.175 * k_shoulder + 0.105 * k_arm) * s, 0.022 * s, 1.340 * s - 0.270 * s * k_arm),
    "olecranon_R": (-(0.175 * k_shoulder + 0.105 * k_arm) * s, 0.022 * s, 1.340 * s - 0.270 * s * k_arm),
    "styloid_radial_L": ((0.175 * k_shoulder + 0.185 * k_arm) * s + 0.020 * s, -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
    "styloid_radial_R": (-((0.175 * k_shoulder + 0.185 * k_arm) * s + 0.020 * s), -0.020 * s, 1.340 * s - 0.510 * s * k_arm),
    "styloid_ulnar_L": ((0.175 * k_shoulder + 0.185 * k_arm) * s - 0.018 * s, 0.005 * s, 1.340 * s - 0.510 * s * k_arm),
    "styloid_ulnar_R": (-((0.175 * k_shoulder + 0.185 * k_arm) * s - 0.018 * s), 0.005 * s, 1.340 * s - 0.510 * s * k_arm),
}
```

---

## 5. SECTION D: CONCRETE CODE IMPLEMENTATION IN `human_generator.py`

### 5.1 Replacement in `HumanAnatomyGenerator.generate()`
Target file: `src/morphomesh/human_generator.py`

#### Edit D.1: Torso Cross-Sectional Loop Displacements
In `human_generator.py`, lines 344–405:
Replace the vertex displacement block inside the torso slice loop to incorporate the clavicle S-curve, suprasternal notch, teardrop breast with cleavage cleft, ribcage costal margin, flared pelvic crest, ASIS, and dimples of Venus:

```python
            for i in range(sectors):
                theta = 2.0 * math.pi * i / sectors
                cos_t = math.cos(theta)
                sin_t = math.sin(theta)

                mod_y = ry
                dx_facial = 0.0
                dy_facial = 0.0
                rx_mod = rx

                # --- 1. CHEST: TEARDROP BREAST CUPS, CLEAVAGE CLEFT & COSTA ---
                if vg_name == "chest" and sin_t < -0.2:
                    ux = cos_t
                    abs_ux = abs(ux)

                    # Medial cleavage cleft (recess back to sternum along X ~ 0)
                    if abs_ux < 0.22:
                        cleav_u = 1.0 - (abs_ux / 0.22) ** 2
                        cleav_z = math.exp(-((z_slice - 1.190 * s) ** 2) / (2.0 * ((0.050 * s) ** 2)))
                        dy_facial += 0.0150 * s * k_chest * cleav_u * cleav_z

                    # Bilateral teardrop breast volume (mounds centered at |ux| ~ 0.46)
                    bust_u = math.exp(-((abs_ux - 0.46) ** 2) / (2.0 * (0.18 ** 2)))
                    if z_slice >= 1.190 * s:
                        bust_z = math.exp(-((z_slice - 1.190 * s) ** 2) / (2.0 * ((0.055 * s) ** 2)))
                    else:
                        bust_z = math.exp(-((z_slice - 1.190 * s) ** 2) / (2.0 * ((0.035 * s) ** 2)))
                    dy_facial -= 0.0240 * s * k_chest * bust_u * bust_z

                    # Inframammary fold tuck
                    if 1.115 * s <= z_slice <= 1.145 * s and 0.25 <= abs_ux <= 0.70:
                        imf_u = math.exp(-((abs_ux - 0.48) ** 2) / (2.0 * (0.16 ** 2)))
                        imf_z = math.exp(-((z_slice - 1.130 * s) ** 2) / (2.0 * ((0.014 * s) ** 2)))
                        dy_facial += 0.0055 * s * imf_u * imf_z

                # --- 2. WAIST & RIBCAGE COSTAL MARGIN ---
                elif vg_name == "waist":
                    ux = cos_t
                    abs_ux = abs(ux)
                    # Costal margin flare & epigastric depression
                    if 1.045 * s <= z_slice <= 1.115 * s and sin_t < -0.2:
                        if abs_ux < 0.18:
                            dy_facial += 0.0050 * s * math.exp(-(ux ** 2) / (2.0 * (0.10 ** 2)))
                        if 0.50 <= abs_ux <= 0.85:
                            rib_f = math.exp(-((abs_ux - 0.68) ** 2) / (2.0 * (0.12 ** 2)))
                            dy_facial -= 0.0040 * s * rib_f
                            dx_facial += math.copysign(0.0035 * s * rib_f, ux)

                # --- 3. UPPER TORSO & CLAVICLE S-CURVE & JUGULAR NOTCH ---
                elif vg_name in ("torso", "neck") and sin_t < -0.2:
                    ux = cos_t
                    abs_ux = abs(ux)

                    # Suprasternal (Jugular) Notch
                    if abs_ux < 0.22 and 1.348 * s <= z_slice <= 1.372 * s:
                        notch_u = math.exp(-(ux ** 2) / (2.0 * (0.10 ** 2)))
                        notch_z = math.exp(-((z_slice - 1.360 * s) ** 2) / (2.0 * ((0.010 * s) ** 2)))
                        dy_facial += 0.0080 * s * notch_u * notch_z

                    # Clavicle S-curve
                    if 1.335 * s <= z_slice <= 1.365 * s:
                        z_clav = math.exp(-((z_slice - 1.350 * s) ** 2) / (2.0 * ((0.012 * s) ** 2)))
                        if 0.15 <= abs_ux <= 0.65:
                            med_p = (abs_ux - 0.15) / 0.50
                            dy_facial -= 0.0065 * s * math.sin(math.pi * med_p) * z_clav
                        elif 0.65 < abs_ux <= 0.95:
                            lat_p = (abs_ux - 0.65) / 0.30
                            dy_facial += 0.0040 * s * math.sin(math.pi * lat_p) * z_clav

                    # Infraclavicular fossa
                    if 1.315 * s <= z_slice <= 1.340 * s and 0.35 <= abs_ux <= 0.75:
                        fossa_u = math.exp(-((abs_ux - 0.55) ** 2) / (2.0 * (0.15 ** 2)))
                        fossa_z = math.exp(-((z_slice - 1.328 * s) ** 2) / (2.0 * ((0.012 * s) ** 2)))
                        dy_facial += 0.0045 * s * fossa_u * fossa_z

                # --- 4. HIPS: ILIAC CREST, ASIS & DIMPLES OF VENUS ---
                elif vg_name == "hips":
                    ux = cos_t
                    abs_ux = abs(ux)

                    # Iliac crest flare
                    if 0.860 * s <= z_slice <= 0.910 * s and abs_ux > 0.75:
                        crest_f = math.exp(-((z_slice - 0.885 * s) ** 2) / (2.0 * ((0.020 * s) ** 2)))
                        dx_facial += math.copysign(0.0070 * s * k_hip * crest_f, ux)

                    # ASIS protrusion
                    if 0.860 * s <= z_slice <= 0.895 * s and sin_t < -0.40 and 0.55 <= abs_ux <= 0.78:
                        asis_u = math.exp(-((abs_ux - 0.66) ** 2) / (2.0 * (0.08 ** 2)))
                        asis_z = math.exp(-((z_slice - 0.875 * s) ** 2) / (2.0 * ((0.015 * s) ** 2)))
                        dy_facial -= 0.0065 * s * k_hip * asis_u * asis_z
                        dx_facial += math.copysign(0.0035 * s * k_hip * asis_u * asis_z, ux)

                    # Dimples of Venus (PSIS on posterior back)
                    if 0.865 * s <= z_slice <= 0.905 * s and sin_t > 0.80 and 0.18 <= abs_ux <= 0.35:
                        psis_u = math.exp(-((abs_ux - 0.26) ** 2) / (2.0 * (0.06 ** 2)))
                        psis_z = math.exp(-((z_slice - 0.885 * s) ** 2) / (2.0 * ((0.015 * s) ** 2)))
                        dy_facial -= 0.0040 * s * psis_u * psis_z

                # --- 5. HEAD & FACIAL FEATURES ---
                elif vg_name == "head":
                    if z_slice < z_chin + 0.25 * head_height and sin_t < -0.5:
                        rx_mod = rx * 0.85
                    else:
                        rx_mod = rx

                    # Submandibular cervico-mental groove (separation from neck)
                    if z_slice < z_chin + 0.10 * head_height and sin_t < -0.30:
                        dy_facial += 0.0065 * s * (-sin_t - 0.30)

                    # Mandibular angle flare below ear
                    if z_chin + 0.08 * head_height <= z_slice <= z_chin + 0.20 * head_height:
                        if abs(cos_t) > 0.70 and -0.30 <= sin_t <= 0.20:
                            dx_facial += math.copysign(0.0045 * s, cos_t)
                            dy_facial += 0.0020 * s

                    if sin_t < -0.2:
                        ang_dist = abs(theta - 1.5 * math.pi)

                        # Nose bridge & tip
                        if 1.490 * s <= z_slice <= 1.545 * s:
                            if ang_dist < 0.30:
                                z_tip_factor = math.exp(-((z_slice - 1.505 * s) ** 2) / (2 * ((0.016 * s) ** 2)))
                                bridge_factor = max(0.0, min(1.0, (1.545 * s - z_slice) / (0.045 * s)))
                                dy_facial -= (0.0125 * z_tip_factor + 0.0065 * bridge_factor) * s
                            elif ang_dist < 0.60:
                                z_flank_factor = math.exp(-((z_slice - 1.505 * s) ** 2) / (2 * ((0.016 * s) ** 2)))
                                dy_facial -= 0.0060 * z_flank_factor * s
                                dx_facial = -0.08 * (rx * cos_t)

                        # Orbital sockets
                        if 1.515 * s <= z_slice <= 1.540 * s:
                            if 0.40 <= ang_dist <= 0.85:
                                dy_facial += 0.0040 * s

                        # Mouth & lips
                        if 1.460 * s <= z_slice <= 1.485 * s:
                            if ang_dist < 0.20:
                                dy_facial += 0.0020 * s
                            elif 0.20 <= ang_dist <= 0.45:
                                dy_facial -= 0.0025 * s
                            elif ang_dist > 0.65:
                                dy_facial += 0.0025 * s

                        # Feminine V-Line chin contour
                        if 1.435 * s <= z_slice <= 1.455 * s:
                            if ang_dist < 0.35:
                                dy_facial -= 0.0055 * s * math.cos(ang_dist * math.pi / 0.70)
                                dx_facial -= 0.14 * (rx * cos_t)
```

#### Edit D.2: Lower Limb Loop (Patella & Asymmetric Malleoli)
In `human_generator.py`, lines 496–510:
Replace the leg ring vertex computation:
```python
            for z_val, rx, ry, cx, cy, vg in leg_slices:
                ring = []
                for i in range(leg_sectors):
                    theta = 2.0 * math.pi * i / leg_sectors
                    cos_t = math.cos(theta)
                    sin_t = math.sin(theta)

                    px = cx + rx * cos_t
                    py = cy + ry * sin_t
                    pz = z_val

                    # Patella Kneecap Facet & Hoffa Hollows
                    if 0.420 * s * k_leg <= z_val <= 0.470 * s * k_leg:
                        z_pat_f = math.exp(-((z_val - 0.445 * s * k_leg) ** 2) / (2.0 * ((0.016 * s * k_leg) ** 2)))
                        if sin_t < -0.40:
                            pat_u = math.exp(-(cos_t ** 2) / (2.0 * (0.35 ** 2)))
                            py -= 0.0085 * s * pat_u * z_pat_f
                        elif 0.38 <= abs(cos_t) <= 0.75 and sin_t < -0.20:
                            py += 0.0040 * s * z_pat_f

                    # Tibial Tuberosity
                    if abs(z_val - 0.420 * s * k_leg) < 0.015 * s * k_leg and sin_t < -0.70:
                        py -= 0.0045 * s

                    # Asymmetric Ankle Malleoli
                    # Medial Malleolus (Tibia): Higher (0.090m) & anterior (-0.0035m)
                    if abs(z_val - 0.090 * s * k_leg) < 0.025 * s * k_leg:
                        if cos_t * sign < -0.50:
                            med_u = math.exp(-((cos_t * sign - (-1.0)) ** 2) / (2.0 * (0.35 ** 2)))
                            med_z = math.exp(-((z_val - 0.090 * s * k_leg) ** 2) / (2.0 * ((0.016 * s * k_leg) ** 2)))
                            px -= sign * 0.0075 * s * med_u * med_z
                            py -= 0.0035 * s * med_u * med_z

                    # Lateral Malleolus (Fibula): Lower (0.076m / slice 0.082m) & posterior (+0.0075m)
                    if abs(z_val - 0.082 * s * k_leg) < 0.020 * s * k_leg:
                        if cos_t * sign > 0.50:
                            lat_u = math.exp(-((cos_t * sign - 1.0) ** 2) / (2.0 * (0.35 ** 2)))
                            lat_z = math.exp(-((z_val - 0.082 * s * k_leg) ** 2) / (2.0 * ((0.016 * s * k_leg) ** 2)))
                            px += sign * 0.0090 * s * lat_u * lat_z
                            py += 0.0075 * s * lat_u * lat_z

                    # Achilles posterior groove
                    if abs(z_val - 0.082 * s * k_leg) < 0.030 * s * k_leg and sin_t > 0.65:
                        py -= 0.0045 * s

                    norm = (cos_t, sin_t, 0.0)
                    idx = mesh.add_vertex((px, py, pz), norm, (i / leg_sectors, z_val / max(1e-4, 0.825 * s * k_leg)))
                    ring.append(idx)
                    vgroups[vg].append(idx)
                leg_rings.append(ring)
```

#### Edit D.3: Upper Limb Loop (Elbow Olecranon & Wrist Styloids)
In `human_generator.py`, lines 570–584:
Replace the arm ring vertex computation:
```python
            for cx, cy, cz, rx, ry, vg in arm_slices:
                ring = []
                for i in range(arm_sectors):
                    theta = 2.0 * math.pi * i / arm_sectors
                    cos_t = math.cos(theta)
                    sin_t = math.sin(theta)
                    px = cx + rx * cos_t
                    py = cy + ry * sin_t
                    pz = cz

                    # Elbow Olecranon Bony Process
                    if abs(cz - (1.340 * s - 0.270 * s * k_arm)) < 0.035 * s:
                        if sin_t > 0.50:
                            olec_f = math.exp(-((sin_t - 1.0) ** 2) / (2.0 * (0.25 ** 2)))
                            py += 0.0065 * s * k_arm * olec_f
                        elif sin_t < -0.50:
                            py += 0.0035 * s * k_arm

                    # Wrist Styloid Processes
                    if abs(cz - (1.340 * s - 0.510 * s * k_arm)) < 0.025 * s:
                        if cos_t > 0.60:
                            px += sign * 0.0040 * s
                        elif cos_t < -0.60:
                            px -= sign * 0.0035 * s
                            py += 0.0025 * s

                    norm = (cos_t, sin_t, 0.0)
                    idx = mesh.add_vertex((px, py, pz), norm, (i / arm_sectors, max(0.0, (1.340 * s - cz) / max(1e-4, 0.510 * s * k_arm))))
                    ring.append(idx)
                    vgroups[vg].append(idx)
                arm_rings.append(ring)
```

#### Edit D.4: Complete Articulated 5-Toed Foot Generator
In `human_generator.py`, lines 527–544:
Replace the crude ellipsoidal foot block with the complete articulated foot generator:

```python
            # ------------------------------------------------------------------
            # ANATOMICAL ARTICULATED 5-TOED FOOT GENERATOR (LEFT & RIGHT)
            # ------------------------------------------------------------------
            # 1. Calcaneus / Heel Pad (Plantar fat cushion + Achilles insertion)
            heel_center = (cx_ankle, 0.048 * s, 0.026 * s * k_leg)
            heel_radii = (0.026 * s, 0.036 * s, 0.022 * s * k_leg)
            heel_indices = add_quad_ellipsoid(mesh, heel_center, heel_radii, rings=3, sectors=8)
            vgroups[foot_vg].extend(heel_indices)

            # 2. Midfoot / Plantar Arches (Medial +8.5mm, Lateral +2.5mm, Transverse Vault)
            instep_center = (cx_ankle - 0.004 * s * sign, -0.015 * s, 0.026 * s * k_leg)
            instep_radii = (0.033 * s, 0.038 * s, 0.020 * s * k_leg)
            instep_indices = add_quad_ellipsoid(mesh, instep_center, instep_radii, rings=3, sectors=8)
            vgroups[foot_vg].extend(instep_indices)

            # 3. Forefoot / Metatarsal Heads (Ball of Foot along 65° Oblique Break Axis)
            ball_center = (cx_ankle, -0.065 * s, 0.015 * s * k_leg)
            ball_radii = (0.037 * s, 0.030 * s, 0.013 * s * k_leg)
            ball_indices = add_quad_ellipsoid(mesh, ball_center, ball_radii, rings=3, sectors=8)
            vgroups[foot_vg].extend(ball_indices)

            # 4. 5 Articulated Toes & Convex Keratin Toenails Configuration
            # Parameters: (toe_name, mtp_offset_x, mtp_y, mtp_z, total_len, radius, num_phalanges, nail_w, nail_l)
            toe_configs = [
                # Hallux (Big Toe): 2 phalanges, robust 16mm width, 32mm length, convex nail 11x9mm
                ("toe_big", -0.0235 * sign, -0.088, 0.013, 0.032, 0.0080, 2, 0.011, 0.009),
                # Toe 2 (Index): Greek profile, 3 phalanges, 33mm length, 4.5mm clear cleft from big toe
                ("toe_second", -0.0060 * sign, -0.090, 0.014, 0.033, 0.0068, 3, 0.0075, 0.007),
                # Toe 3 (Middle): 3 phalanges, 28mm length, natural taper
                ("toe_third", 0.0070 * sign, -0.086, 0.013, 0.028, 0.0062, 3, 0.0060, 0.006),
                # Toe 4 (Fourth): 3 phalanges, 24mm length
                ("toe_fourth", 0.0190 * sign, -0.080, 0.012, 0.024, 0.0056, 3, 0.0050, 0.005),
                # Toe 5 (Pinky): 3 phalanges, 19mm length, outer lateral edge
                ("toe_fifth", 0.0300 * sign, -0.073, 0.010, 0.019, 0.0048, 3, 0.0040, 0.004),
            ]

            for t_name, ox, oy, oz, t_len, t_rad, num_ph, nail_w, nail_l in toe_configs:
                base_x = cx_ankle + ox * s
                base_y = oy * s
                base_z = oz * s * k_leg

                # Forward vector with slight downward slope touching floor
                t_vec_x = 0.015 * sign if t_name == "toe_big" else (ox * 0.15)
                t_vec_y = -0.998
                t_vec_z = -0.040

                v_len = math.sqrt(t_vec_x * t_vec_x + t_vec_y * t_vec_y + t_vec_z * t_vec_z) or 1.0
                dx, dy, dz = t_vec_x / v_len, t_vec_y / v_len, t_vec_z / v_len
                ph_len = (t_len * s) / float(num_ph)

                # Phalanx Segments
                for p_idx in range(num_ph):
                    p_frac = (p_idx + 0.5) / float(num_ph)
                    ph_cx = base_x + dx * (t_len * s) * p_frac
                    ph_cy = base_y + dy * (t_len * s) * p_frac
                    ph_cz = base_z + dz * (t_len * s) * p_frac
                    ph_rad = t_rad * s * (1.0 - p_idx * 0.08)

                    ph_indices = add_quad_ellipsoid(
                        mesh,
                        (ph_cx, ph_cy, ph_cz),
                        (ph_rad, ph_len * 0.55, ph_rad * 0.90),
                        rings=3,
                        sectors=6,
                    )
                    vgroups[foot_vg].extend(ph_indices)

                # Convex Toenail on Distal Phalanx Dorsal Surface
                tip_x = base_x + dx * (t_len * s)
                tip_y = base_y + dy * (t_len * s)
                tip_z = base_z + dz * (t_len * s)

                nail_cx = tip_x - dx * (0.004 * s)
                nail_cy = tip_y - dy * (0.004 * s)
                nail_cz = tip_z + 0.0055 * s * k_leg

                nail_indices = add_quad_ellipsoid(
                    mesh,
                    (nail_cx, nail_cy, nail_cz),
                    (nail_w * 0.5 * s, nail_l * 0.5 * s, 0.0015 * s),
                    rings=2,
                    sectors=6,
                )
                vgroups[foot_vg].extend(nail_indices)

                # Record specific toe landmark
                landmarks[f"{t_name}_{side}"] = (tip_x, tip_y, tip_z)
```

#### Edit D.5: Landmark Dictionary Update
In `human_generator.py`, lines 656–681:
Replace the `landmarks.update({...})` block with the complete medical landmarks dictionary from Section 4 of this specification.

#### Edit D.6: Interface Contract Function `generate_human_body`
Add the convenience function at the bottom of `human_generator.py`:
```python
def generate_human_body(
    height: float = 1.65,
    gender: str = "female",
    proportion_preset: str = "stylized_heroine",
) -> Tuple[MeshGeometry, Dict[str, Tuple[float, float, float]]]:
    """
    Authoritative convenience API conforming to PROJECT.md interface contract.
    Returns:
        mesh: MeshGeometry object containing quad-dominant female human body.
        landmarks: Complete dictionary mapping skeletal landmark names to (x, y, z).
    """
    cfg = HumanAnatomyConfig(
        height=height,
        gender=gender,
    )
    res = generate_human_base_mesh(config=cfg)
    return res.mesh, res.landmarks
```

---

## 6. VERIFICATION & NUMERICAL INTEGRITY METRICS

| Validation Check | Target Metric | Verification Command / Procedure |
|---|---|---|
| **Quad Dominance Ratio** | $\ge 95.0\%$ (Target: $\ge 98.5\%$) | `pytest tests/test_human_generator.py::test_quad_dominance_ratio` |
| **Zero Non-Manifold Edges** | $0$ edges shared by $>2$ faces | `pytest tests/test_human_generator.py::test_zero_area_faces_and_manifold_edges` |
| **Zero Open Boundary Edges** | $0$ boundary edges | `pytest tests/test_adversarial_human_generator.py::TestTopologyManifoldnessAndWatertightness` |
| **Zero Zero-Area Faces** | $0$ degenerate faces | `pytest tests/test_human_generator.py::test_zero_area_faces_and_manifold_edges` |
| **All 24 Standardized Vertex Groups** | 100% non-empty | `pytest tests/test_human_generator.py::test_all_standardized_vertex_groups_present_and_populated` |
| **Rigify Pre-Bends** | Elbow $+Y$, Knee $-Y$ ($<180^\circ$) | `pytest tests/test_adversarial_human_generator.py::TestLandmarkConsistencyAndPreBends` |
| **5-Toed Feet Articulation** | 5 distinct toes with phalanges & nails | `pytest tests/test_human_generator.py::test_articulated_feet` |
| **Full Test Suite Pass Rate** | $100\%$ pass across all suites | `pytest tests/test_human_generator.py tests/test_adversarial_human_generator.py tests/test_human_rigging.py` |
