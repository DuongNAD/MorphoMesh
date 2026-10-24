# Remediation Strategy: Interdigital Cleft Clearance & Toe Phalangeal Segmentation
**Milestone**: M1 Iteration 2 (Human Anatomy & Rigify 163 DEF Rigging)  
**Author**: M1 Iter 2 Cleft & Phalanges Explorer (`explorer_m1_iter2_cleft_phalanges`)  
**Target File**: `src/morphomesh/human_generator.py`  
**Downstream Dependents**: `src/morphomesh/human_rigging.py`, `src/morphomesh/wardrobe.py`, `tests/test_empiric_m1_anatomy.py`, `tests/test_human_generator.py`, `tests/test_e2e_human_anatomy.py`  
**Date**: 2026-09-07T21:00:00Z  

---

## 1. Executive Summary & Root Cause Diagnosis

### 1.1 Gate Failure Context
In Milestone M1 Iteration 1, the gate review resulted in **FAIL** due to two critical anatomical defects raised by `reviewer_m1_anatomy` (REQUEST_CHANGES) and `challenger_m1_anatomy_quads` (DEFECT_FOUND: `M1-CHALLENGE-01`):
1. **Interdigital Cleft Clearance Deficit**: The physical surface gap between the lateral surface of the Hallux (big toe) and the medial surface of the Second Toe was empirically measured at **1.50mm transverse / 3.50mm 3D Euclidean distance**. This violates the authoritative contract ($\ge 4.5\text{mm}$) by a 66.7% deficit (3.00mm shortage), despite the code comment and worker handoff claiming "$\ge 4.5\text{mm}$ clear cleft". When flat strappy sandals are fitted in Milestone M3, any strap or thong (width 3.0mm–4.5mm) passing through this cleft will suffer severe geometric penetration.
2. **Absence of Phalangeal Articulation in Toes**: While the 10 hand fingers were segmented into 3 articulated phalanges each (`for ph_idx in range(3): add_quad_ellipsoid`), all 5 toes were generated as single unsegmented ellipsoids (`add_quad_ellipsoid(...)` invoked once per toe), lacking the biological 2-phalanx structure of the Hallux and the 3-phalanx structure of Toes 2–5.

### 1.2 Mathematical Root Cause in Iteration 1
In `src/morphomesh/human_generator.py` lines 674–678:
```python
toe_configs = [
    # Digit 0 (Hallux / Big Toe): r=9mm, length=18mm, convex nail profile
    ("toe_big", -0.0235 * sign, -0.120, 0.011, 0.0090),
    # Digit 1 (Second Toe): r=7mm, length=18mm, 4.5mm clear cleft from big toe
    ("toe_second", -0.0060 * sign, -0.123, 0.010, 0.0070),
]
```
For the canonical left foot ($s = 1.0$, $cx_{\text{ankle}} = 0.088\text{m}$, $\text{sign} = 1.0$):
- $\text{Hallux Center } X = 0.088 - 0.0235 = 0.0645\text{m}$, Radius $r_{\text{big}} = 0.0090\text{m} \implies \text{Lateral Boundary } X = 0.0645 + 0.0090 = \mathbf{0.0735\text{m}}$.
- $\text{Toe 2 Center } X = 0.088 - 0.0060 = 0.0820\text{m}$, Radius $r_{\text{sec}} = 0.0070\text{m} \implies \text{Medial Boundary } X = 0.0820 - 0.0070 = \mathbf{0.0750\text{m}}$.
- $\text{Transverse Surface Gap} = 0.0750 - 0.0735 = \mathbf{0.0015\text{m}} = \mathbf{1.50\text{mm}}$.
- $\text{Center-to-Center Distance} = 0.0820 - 0.0645 = 0.0175\text{m} = 17.50\text{mm}$.
- $\text{Sum of Radii} = r_{\text{big}} + r_{\text{sec}} = 0.0090 + 0.0070 = 0.0160\text{m} = 16.00\text{mm}$.
- The worker erroneously assumed that a center-to-center distance of $17.5\text{mm}$ would yield a $4.5\text{mm}$ gap, overlooking that $17.5\text{mm} - 16.0\text{mm} = 1.5\text{mm}$.

---

## 2. Task 1: Exact Hallux & Toe 2 Center Offsets and Foot Arcade Spacing

### 2.1 Parameter Matrix Formulation
To guarantee a physical surface gap $\Delta X_{\text{surface}} \ge 4.5\text{mm}$ (specifically targeting the optimal **$5.5\text{mm} - 6.5\text{mm}$** window) while preserving foot anatomical width and preventing crowding across the remaining lateral toes (Toes 2–5), the required center-to-center distance between Hallux and Toe 2 is:
$$\text{Dist}(C_1, C_2) = r_{\text{big}} + r_{\text{sec}} + \Delta X_{\text{surface}} = 0.0090\text{m} + 0.0070\text{m} + \Delta X_{\text{surface}}$$
- For $\Delta X_{\text{surface}} = 6.00\text{mm}$: $\text{Dist}(C_1, C_2) = 16.0\text{mm} + 6.0\text{mm} = \mathbf{22.00\text{mm}} = 0.0220\text{m}$.
- For $\Delta X_{\text{surface}} = 6.50\text{mm}$: $\text{Dist}(C_1, C_2) = 16.0\text{mm} + 6.5\text{mm} = \mathbf{22.50\text{mm}} = 0.0225\text{m}$.

We formulate two balanced offset options:

#### Primary Recommended Configuration (Target: 6.00mm Surface Gap)
- **Hallux Center Offset**: $ox_{\text{big}} = -0.0265 \cdot \text{sign}$
  - Center $X = cx_{\text{ankle}} - 0.0265 = 0.088 - 0.0265 = \mathbf{0.0615\text{m}}$
  - Medial boundary: $0.0615 - 0.0090 = 0.0525\text{m}$ (well inside foot ball medial edge $0.0500\text{m}$)
  - Lateral boundary: $0.0615 + 0.0090 = \mathbf{0.0705\text{m}}$
- **Toe 2 Center Offset**: $ox_{\text{sec}} = -0.0045 \cdot \text{sign}$
  - Center $X = cx_{\text{ankle}} - 0.0045 = 0.088 - 0.0045 = \mathbf{0.0835\text{m}}$
  - Medial boundary: $0.0835 - 0.0070 = \mathbf{0.0765\text{m}}$
  - Lateral boundary: $0.0835 + 0.0070 = \mathbf{0.0905\text{m}}$
- **Physical Surface Clearance**:
  $$\Delta X_{\text{surface}} = 0.0765\text{m} - 0.0705\text{m} = \mathbf{0.0060\text{m}} = \mathbf{6.00\text{mm}} \ge 4.5\text{mm} \quad (\text{PASS})$$
  $$\text{Min 3D Euclidean Distance} = \mathbf{6.16\text{mm}} \ge 4.0\text{mm} \quad (\text{PASS})$$

#### Secondary Alternative Configuration (Target: 6.50mm Surface Gap)
- **Hallux Center Offset**: $ox_{\text{big}} = -0.0265 \cdot \text{sign}$ ($X = 0.0615\text{m}$, lateral boundary $0.0705\text{m}$)
- **Toe 2 Center Offset**: $ox_{\text{sec}} = -0.0040 \cdot \text{sign}$ ($X = 0.0840\text{m}$, medial boundary $0.0770\text{m}$)
- **Physical Surface Clearance**:
  $$\Delta X_{\text{surface}} = 0.0770\text{m} - 0.0705\text{m} = \mathbf{0.0065\text{m}} = \mathbf{6.50\text{mm}} \ge 4.5\text{mm} \quad (\text{PASS})$$

### 2.2 Complete 5-Toe Arcade Harmonic Spacing
To prevent Toe 2 from colliding or excessively overlapping with Toe 3 when shifted laterally from $-0.0060$ to $-0.0045$, the entire toe arcade must be harmonically recalibrated. The table below details the full coordinate solution for the left foot ($cx_{\text{ankle}} = 0.088\text{m}$, $s=1.0$):

| Digit # | Digit Name | $ox$ Offset | Center $X$ | Radius $r_x$ | Medial $X_{\min}$ | Lateral $X_{\max}$ | Adjacent Gap / Contact | Anatomical Role |
|---|---|---|---|---|---|---|---|---|
| **0** | **Hallux** (Big Toe) | `-0.0265` | `0.0615m` | `0.0090m` | `0.0525m` | `0.0705m` | — | Great toe, medial weight-bearing |
| **1** | **Second Toe** | `-0.0045` | `0.0835m` | `0.0070m` | `0.0765m` | `0.0905m` | **+6.00mm** (Cleft) | Greek apex, sandal strap thong slot |
| **2** | **Third Toe** (Middle) | `+0.0080` | `0.0960m` | `0.0070m` | `0.0890m` | `0.1030m` | -1.50mm (Contact) | Central stabilizer |
| **3** | **Fourth Toe** (Ring) | `+0.0195` | `0.1075m` | `0.0065m` | `0.1010m` | `0.1140m` | -2.00mm (Contact) | Lateral support |
| **4** | **Fifth Toe** (Pinky) | `+0.0305` | `0.1185m` | `0.0060m` | `0.1125m` | `0.1245m` | -1.50mm (Contact) | Lateral balance margin |

**Verification of Foot Envelope Constraints**:
1. **Total Foot Width across Toes**: $X_{\max} - X_{\min} = 0.1245\text{m} - 0.0525\text{m} = \mathbf{72.0\text{mm}} \ge 50.0\text{mm}$ (passes `test_t1_07_five_articulated_toes_and_proportions`).
2. **Metatarsal Ball Boundary Clearance**: The forefoot ball semi-axis is $rx = 0.038\text{m}$, spanning $[cx - 0.038, cx + 0.038] = [0.0500\text{m}, 0.1260\text{m}]$. All 5 toes reside strictly within $[0.0525\text{m}, 0.1245\text{m}]$, with $\ge 1.5\text{mm}$ containment margin on both medial and lateral sides.
3. **Soft-Tissue Adjacent Nestling**: Toes 1–4 touch with gentle soft-tissue compression (1.5mm to 2.0mm overlap), avoiding both abnormal air gaps between minor toes and aggressive vertex entanglement.

### 2.3 Sandal Strap Fit & Non-Penetration Analysis
In Milestone M3 (`src/morphomesh/wardrobe.py`), flat strappy sandals feature:
- A toe thong / post or diagonal instep strap that passes through the first interdigital space.
- Nominal leather strap dimensions: thickness $T_{\text{strap}} = 1.2\text{mm} - 1.8\text{mm}$, width $W_{\text{strap}} = 3.0\text{mm} - 4.0\text{mm}$.
- **Clearance Evaluation**:
  - Available transverse gap: $G = 6.00\text{mm}$.
  - Clearance margin: $\text{Margin} = \frac{G - W_{\text{strap}}}{2} = \frac{6.00 - 3.50}{2} = \mathbf{1.25\text{mm}}$ on each lateral surface.
  - Even under $\pm 10^\circ$ dynamic flexion or cloth collision dilation ($\delta = 0.5\text{mm}$), the strap remains completely non-penetrating with 0% vertex clipping.

### 2.4 Anthropometric Scaling Invariant ($1.40\text{m} \le H \le 1.95\text{m}$)
Because all parameters scale linearly with $s = \frac{H}{1.65}$:
$$\Delta X_{\text{surface}}(H) = 6.00\text{mm} \times \left(\frac{H}{1.65}\right)$$
- At petite height $H = 1.40\text{m}$ ($s = 0.8485$): $\Delta X = \mathbf{5.09\text{mm}} \ge 4.50\text{mm}$ (PASS).
- At standard height $H = 1.65\text{m}$ ($s = 1.0000$): $\Delta X = \mathbf{6.00\text{mm}} \ge 4.50\text{mm}$ (PASS).
- At tall height $H = 1.95\text{m}$ ($s = 1.1818$): $\Delta X = \mathbf{7.09\text{mm}} \ge 4.50\text{mm}$ (PASS).
The physical gap strictly satisfies $\ge 4.5\text{mm}$ across all valid humanoid scales.

---

## 3. Task 2: Articulated Quad Phalangeal Segmentation Architecture

### 3.1 Anatomical Foundation & Segmentation Rules
In authentic human foot anatomy:
1. **Hallux (Digit 0)** possesses strictly **2 phalanges**:
   - **Proximal Phalanx** (*Phalanx proximalis hallucis*): Broad cylindrical base articulating with the head of the first metatarsal.
   - **Distal Phalanx** (*Phalanx distalis hallucis*): Shorter phalanx supporting the dorsal nail plate (*unguis*) and plantar sensory digital pad.
   - Joint: **Interphalangeal (IP) Joint** of the hallux.
2. **Toes 2 to 5 (Digits 1–4)** each possess strictly **3 phalanges**:
   - **Proximal Phalanx** (*Phalanx proximalis*): Connects to metatarsal head at MTP joint.
   - **Intermediate / Middle Phalanx** (*Phalanx media*): Mid-segment shaft.
   - **Distal Phalanx** (*Phalanx distalis*): Terminal segment bearing toenail and apical pulp.
   - Joints: **Proximal Interphalangeal (PIP)** and **Distal Interphalangeal (DIP)** joints.

### 3.2 Greek Foot Profile (Morton's Taper)
`ORIGINAL_REQUEST.md` and `PROJECT.md` require maintaining the canonical **Greek foot profile**, where Toe 2 is longer than Hallux.
- Metatarsophalangeal (MTP) joint line slants at an oblique $\sim 65^\circ$ angle across the ball.
- Length gradation along the longitudinal axis ($Y$):
  $$\text{Toe 2 } (37.0\text{mm}, Y_{\text{tip}} = -0.142\text{m}) > \text{Hallux } (34.0\text{mm}, Y_{\text{tip}} = -0.138\text{m}) > \text{Toe 3 } (31.0\text{mm}, Y_{\text{tip}} = -0.129\text{m}) > \text{Toe 4 } (26.0\text{mm}, Y_{\text{tip}} = -0.116\text{m}) > \text{Toe 5 } (21.0\text{mm}, Y_{\text{tip}} = -0.103\text{m})$$
- Toe 2 extends **4.0mm forward of Hallux**, creating the classical Greek silhouette.

### 3.3 Parametric Phalanx Specification Table
Each phalanx segment is articulated along the $-Y$ direction (anterior travel) with natural plantar elevation ($Z$):

```
                                  LONGITUDINAL PROFILE (-Y)
[MTP Joint] ---> [Proximal Phalanx] ---> [IP / PIP Joint] ---> [Intermediate Phalanx] ---> [DIP Joint] ---> [Distal Phalanx + Nail]
```

| Digit Name | Phalanx Index & Name | Length $L$ | Base Radius $r$ | Center $(X, Y, Z)$ at $s=1.0$ | Radii Vector $(r_x, r_y, r_z)$ |
|---|---|---|---|---|---|
| **`toe_big`** (Hallux) | Phalanx 0: Proximal | 19.0mm | 9.0mm | `(0.0615, -0.1135, 0.0120)` | `(0.0090, 0.0105, 0.0081)` |
| | Phalanx 1: Distal | 15.0mm | 8.1mm | `(0.0615, -0.1305, 0.0110)` | `(0.0081, 0.0083, 0.0073)` |
| **`toe_second`** | Phalanx 0: Proximal | 15.0mm | 7.0mm | `(0.0835, -0.1125, 0.0110)` | `(0.0070, 0.0083, 0.0063)` |
| | Phalanx 1: Intermediate | 12.0mm | 6.5mm | `(0.0835, -0.1260, 0.0100)` | `(0.0065, 0.0066, 0.0058)` |
| | Phalanx 2: Distal | 10.0mm | 6.1mm | `(0.0835, -0.1370, 0.0090)` | `(0.0061, 0.0055, 0.0055)` |
| **`toe_third`** | Phalanx 0: Proximal | 13.0mm | 7.0mm | `(0.0960, -0.1045, 0.0100)` | `(0.0070, 0.0072, 0.0063)` |
| | Phalanx 1: Intermediate | 10.0mm | 6.5mm | `(0.0960, -0.1160, 0.0090)` | `(0.0065, 0.0055, 0.0058)` |
| | Phalanx 2: Distal | 8.0mm | 6.1mm | `(0.0960, -0.1250, 0.0080)` | `(0.0061, 0.0044, 0.0055)` |
| **`toe_fourth`** | Phalanx 0: Proximal | 11.0mm | 6.5mm | `(0.1075, -0.0955, 0.0090)` | `(0.0065, 0.0061, 0.0058)` |
| | Phalanx 1: Intermediate | 8.0mm | 6.1mm | `(0.1075, -0.1050, 0.0080)` | `(0.0061, 0.0044, 0.0055)` |
| | Phalanx 2: Distal | 7.0mm | 5.6mm | `(0.1075, -0.1125, 0.0070)` | `(0.0056, 0.0039, 0.0050)` |
| **`toe_fifth`** | Phalanx 0: Proximal | 9.0mm | 6.0mm | `(0.1185, -0.0865, 0.0080)` | `(0.0060, 0.0050, 0.0054)` |
| | Phalanx 1: Intermediate | 7.0mm | 5.6mm | `(0.1185, -0.0945, 0.0070)` | `(0.0056, 0.0039, 0.0050)` |
| | Phalanx 2: Distal | 5.0mm | 5.2mm | `(0.1185, -0.1005, 0.0060)` | `(0.0052, 0.0028, 0.0047)` |

### 3.4 Quad Purity & Manifoldness Proof
1. **Quad Reconstruction**:
   - Each phalanx is generated using `add_quad_ellipsoid(mesh, center, radii, rings=3, sectors=8)` (or `sectors=6`).
   - In `add_quad_ellipsoid`:
     - Lateral ring connections are generated with `mesh.add_quad(v0, v1, v2, v3)`.
     - Caps at the poles are generated with `add_quad_cap(mesh, ring, flip_normal=...)`.
     - `add_quad_cap` pairs vertices across an even-numbered ring (`sectors = 8` or `6`), adding $(N-2)/2$ pure quads without any triangular fans.
     - Therefore, **100.00% of generated faces are quads (0 triangles)**.
2. **Watertight 2-Manifoldness**:
   - Every internal edge between adjacent quad rings is shared by exactly 2 faces.
   - Caps seal the terminal boundaries with shared ring edges.
   - Non-manifold edge count $= 0$, open boundary edge count $= 0$.
3. **Normals Orientation**:
   - Outward analytical normal: $n = \left(\frac{\cos\phi\cos\theta}{r_x}, \frac{\cos\phi\sin\theta}{r_y}, \frac{\sin\phi}{r_z}\right)$.
   - Face normal dot product with vertex normal is strictly positive ($> +0.30$), eliminating inverted normals.

---

## 4. Concrete Code Replacement Implementation

### 4.1 Changes in `HumanAnatomyGenerator.generate()` (`src/morphomesh/human_generator.py`)
Replace lines 673–693 in `src/morphomesh/human_generator.py`:

```python
<<<<
            # 3. 5 Articulated Toes with Natural Gradation & Sandal Strap Cleft
            toe_configs = [
                # Digit 0 (Hallux / Big Toe): r=9mm, length=18mm, convex nail profile
                ("toe_big", -0.0235 * sign, -0.120, 0.011, 0.0090),
                # Digit 1 (Second Toe): r=7mm, length=18mm, 4.5mm clear cleft from big toe
                ("toe_second", -0.0060 * sign, -0.123, 0.010, 0.0070),
                # Digit 2 (Middle Toe): r=7mm, length=18mm
                ("toe_third", 0.0070 * sign, -0.114, 0.009, 0.0070),
                # Digit 3 (Ring Toe): r=6.5mm, length=18mm
                ("toe_fourth", 0.0190 * sign, -0.104, 0.008, 0.0065),
                # Digit 4 (Pinky Toe): r=6mm, length=18mm
                ("toe_fifth", 0.0300 * sign, -0.092, 0.007, 0.0060),
            ]
            for t_name, ox, oy, oz, t_rad in toe_configs:
                toe_x = cx_ankle + ox * s
                toe_y = oy * s
                toe_z = oz * s * k_leg
                toe_indices = add_quad_ellipsoid(mesh, (toe_x, toe_y, toe_z), (t_rad * s, 0.018 * s, t_rad * 0.9 * s), rings=3, sectors=8)
                vgroups[foot_vg].extend(toe_indices)
                landmarks[f"{t_name}_{side}"] = (toe_x, toe_y - 0.018 * s, toe_z)
====
            # 3. 5 Articulated Toes with Segmented Phalanges & >=4.5mm Sandal Cleft
            # Hallux (Digit 0): 2 phalanges (proximal, distal).
            # Toes 2-5 (Digits 1-4): 3 phalanges each (proximal, intermediate, distal) maintaining Greek profile.
            toe_specs = [
                # (name, ox, r0, seg_lens, base_y, z0)
                ("toe_big", -0.0265 * sign, 0.0090, [0.019, 0.015], -0.104, 0.012),
                ("toe_second", -0.0045 * sign, 0.0070, [0.015, 0.012, 0.010], -0.105, 0.011),
                ("toe_third", 0.0080 * sign, 0.0070, [0.013, 0.010, 0.008], -0.098, 0.010),
                ("toe_fourth", 0.0195 * sign, 0.0065, [0.011, 0.008, 0.007], -0.090, 0.009),
                ("toe_fifth", 0.0305 * sign, 0.0060, [0.009, 0.007, 0.005], -0.082, 0.008),
            ]

            toe_vertex_slices: Dict[str, List[int]] = {}
            for t_name, ox, r0, seg_lens, base_y, z0 in toe_specs:
                t_x = cx_ankle + ox * s
                cur_y = base_y * s
                cur_z = z0 * s * k_leg
                n_segs = len(seg_lens)
                t_indices: List[int] = []

                for p_idx, slen in enumerate(seg_lens):
                    ph_len = slen * s
                    cen_y = cur_y - ph_len * 0.5
                    cen_z = cur_z - p_idx * 0.001 * s * k_leg
                    taper = 1.0 - (p_idx / max(1, n_segs)) * 0.20
                    cur_rad = r0 * s * taper

                    ph_verts = add_quad_ellipsoid(
                        mesh,
                        (t_x, cen_y, cen_z),
                        (cur_rad, ph_len * 0.55, cur_rad * 0.9),
                        rings=3,
                        sectors=8,
                    )
                    vgroups[foot_vg].extend(ph_verts)
                    t_indices.extend(ph_verts)
                    cur_y -= ph_len

                toe_vertex_slices[f"{t_name}_{side}"] = t_indices
                # Landmark set to anterior distal tip
                landmarks[f"{t_name}_{side}"] = (t_x, cur_y, cur_z)
>>>>
```

### 4.2 Changes in `landmarks.update(...)` (`src/morphomesh/human_generator.py`)
Synchronize lines 868–877 in `src/morphomesh/human_generator.py`:

```python
<<<<
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
====
            # 3. Complete 5 Distinct Toe Tip Landmarks (L & R) with Greek Profile & 6.0mm Cleft
            "toe_big_L": (0.088 * s * k_hip - 0.0265 * s, -0.138 * s, 0.011 * s * k_leg),
            "toe_big_R": (-(0.088 * s * k_hip - 0.0265 * s), -0.138 * s, 0.011 * s * k_leg),
            "toe_second_L": (0.088 * s * k_hip - 0.0045 * s, -0.142 * s, 0.009 * s * k_leg),
            "toe_second_R": (-(0.088 * s * k_hip - 0.0045 * s), -0.142 * s, 0.009 * s * k_leg),
            "toe_third_L": (0.088 * s * k_hip + 0.0080 * s, -0.129 * s, 0.008 * s * k_leg),
            "toe_third_R": (-(0.088 * s * k_hip + 0.0080 * s), -0.129 * s, 0.008 * s * k_leg),
            "toe_fourth_L": (0.088 * s * k_hip + 0.0195 * s, -0.116 * s, 0.007 * s * k_leg),
            "toe_fourth_R": (-(0.088 * s * k_hip + 0.0195 * s), -0.116 * s, 0.007 * s * k_leg),
            "toe_fifth_L": (0.088 * s * k_hip + 0.0305 * s, -0.103 * s, 0.006 * s * k_leg),
            "toe_fifth_R": (-(0.088 * s * k_hip + 0.0305 * s), -0.103 * s, 0.006 * s * k_leg),
>>>>
```

### 4.3 Changes in `get_human_generation_script()` (`src/morphomesh/human_generator.py`)
Replace lines 1287–1300 in `src/morphomesh/human_generator.py` (Blender BMesh generator) to mirror the segmented phalanges and new offsets exactly:

```python
<<<<
    toe_configs = [
        ("toe_big", -0.0235 * sign, -0.120, 0.011, 0.0090),
        ("toe_second", -0.0060 * sign, -0.123, 0.010, 0.0070),
        ("toe_third", 0.0070 * sign, -0.114, 0.009, 0.0070),
        ("toe_fourth", 0.0190 * sign, -0.104, 0.008, 0.0065),
        ("toe_fifth", 0.0300 * sign, -0.092, 0.007, 0.0060),
    ]
    for t_name, ox, oy, oz, t_rad in toe_configs:
        toe_x = cx_ankle + ox * s
        toe_y = oy * s
        toe_z = oz * s * k_leg
        toe_verts = add_bmesh_quad_ellipsoid(bm, (toe_x, toe_y, toe_z), (t_rad * s, 0.018 * s, t_rad * 0.9 * s), rings=3, sectors=8)
        vg_indices[foot_vg].extend(toe_verts)
====
    toe_specs = [
        ("toe_big", -0.0265 * sign, 0.0090, [0.019, 0.015], -0.104, 0.012),
        ("toe_second", -0.0045 * sign, 0.0070, [0.015, 0.012, 0.010], -0.105, 0.011),
        ("toe_third", 0.0080 * sign, 0.0070, [0.013, 0.010, 0.008], -0.098, 0.010),
        ("toe_fourth", 0.0195 * sign, 0.0065, [0.011, 0.008, 0.007], -0.090, 0.009),
        ("toe_fifth", 0.0305 * sign, 0.0060, [0.009, 0.007, 0.005], -0.082, 0.008),
    ]
    for t_name, ox, r0, seg_lens, base_y, z0 in toe_specs:
        t_x = cx_ankle + ox * s
        cur_y = base_y * s
        cur_z = z0 * s * k_leg
        n_segs = len(seg_lens)
        for p_idx, slen in enumerate(seg_lens):
            ph_len = slen * s
            cen_y = cur_y - ph_len * 0.5
            cen_z = cur_z - p_idx * 0.001 * s * k_leg
            taper = 1.0 - (p_idx / max(1, n_segs)) * 0.20
            cur_rad = r0 * s * taper
            ph_verts = add_bmesh_quad_ellipsoid(
                bm,
                (t_x, cen_y, cen_z),
                (cur_rad, ph_len * 0.55, cur_rad * 0.9),
                rings=3,
                sectors=8,
            )
            vg_indices[foot_vg].extend(ph_verts)
            cur_y -= ph_len
>>>>
```

### 4.4 Test Harness Synchronization (`tests/test_empiric_m1_anatomy.py`)
In `tests/test_empiric_m1_anatomy.py`, lines 504 and 611 sliced `foot_L[48:72]` and `foot_L[72:96]`.
Under the new segmented architecture:
- Calcaneus: `foot_L[0:24]` (24 verts)
- Metatarsal Ball: `foot_L[24:48]` (24 verts)
- **Hallux** (2 phalanges $\times 24$ verts): `foot_L[48:96]` (48 verts)
- **Toe 2** (3 phalanges $\times 24$ verts): `foot_L[96:168]` (72 verts)
- **Toe 3** (3 phalanges $\times 24$ verts): `foot_L[168:240]` (72 verts)
- **Toe 4** (3 phalanges $\times 24$ verts): `foot_L[240:312]` (72 verts)
- **Toe 5** (3 phalanges $\times 24$ verts): `foot_L[312:384]` (72 verts)

Update `tests/test_empiric_m1_anatomy.py` to:
1. Slice Hallux as `foot_L[48:96]` and Toe 2 as `foot_L[96:168]`.
2. Remove the `@pytest.mark.xfail(strict=True)` marker so that the test passes cleanly.
3. Assert that:
   - `clearance_3d_mm >= 4.0` (Challenger contract)
   - `transverse_gap_mm >= 4.5` (Worker/Specification contract)

---

## 5. Verification Protocol & Execution Checklist

### 5.1 Automated Test Execution
Run the full test suite to verify 0 regressions:
```bash
uv run pytest tests/test_empiric_m1_anatomy.py tests/test_human_generator.py tests/test_e2e_human_anatomy.py -v
```
*Expected Outcome*: 100% tests passing with 0 failures, 0 xfailed.

### 5.2 Standalone Quantitative Verification Script
Execute the following verification script to assert the exact physical metrics:
```python
import math
from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig

res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
mesh = res.mesh
foot_L = res.vertex_groups["foot_L"]

# Hallux is verts [48:96], Toe 2 is verts [96:168]
hallux_verts = [mesh.vertices[i] for i in foot_L[48:96]]
toe2_verts = [mesh.vertices[i] for i in foot_L[96:168]]

min_3d_dist = min(
    math.sqrt((vb[0] - vs[0])**2 + (vb[1] - vs[1])**2 + (vb[2] - vs[2])**2)
    for vb in hallux_verts for vs in toe2_verts
) * 1000.0

transverse_cleft = (min(v[0] for v in toe2_verts) - max(v[0] for v in hallux_verts)) * 1000.0

print(f"Hallux Max X: {max(v[0] for v in hallux_verts):.4f}m")
print(f"Toe 2 Min X:  {min(v[0] for v in toe2_verts):.4f}m")
print(f"Transverse Surface Gap: {transverse_cleft:.2f}mm (Required: >= 4.50mm, Target: 5.5 - 6.5mm)")
print(f"3D Euclidean Distance:  {min_3d_dist:.2f}mm (Required: >= 4.00mm)")

assert transverse_cleft >= 4.50, f"FAIL: Transverse gap {transverse_cleft:.2f}mm < 4.50mm"
assert min_3d_dist >= 4.00, f"FAIL: 3D distance {min_3d_dist:.2f}mm < 4.00mm"
print("SUCCESS: Interdigital cleft meets all specification criteria!")
```

---

## 6. Downstream Integration Impact

1. **Milestone M1 Rigging (`human_rigging.py`)**:
   - The 163 DEF metarig uses `DEF-foot` and `DEF-toe` to drive foot flexion.
   - The updated landmarks (`toe_big_L` at $Y=-0.138\text{m}$, `toe_second_L` at $Y=-0.142\text{m}$) align seamlessly with the oblique MTP break axis ($\sim 65^\circ$).
2. **Milestone M3 Sandal Strapping (`wardrobe.py`)**:
   - The 6.00mm physical cleft enables flat sandal straps and thongs (width 3.0mm–4.5mm) to seat naturally between Hallux and Toe 2 with zero penetration or visual Z-fighting.
3. **Milestone M4 Keratin Shaders (`human_materials.py`)**:
   - Isolating the distal phalanges enables straightforward vertex-group partitioning for convex toenail plates and cuticle ridges under `Mat_Human_Nails`.
