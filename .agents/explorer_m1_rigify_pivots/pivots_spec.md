# Technical Specification: Biological Realigned Rigify 163 DEF Metarig Joint Pivots (Feature 7)

**Author**: Rigify Pivots Explorer (`explorer_m1_rigify_pivots`)  
**Target Module**: `src/morphomesh/human_rigging.py`  
**Milestone**: M1 — Medical-Grade Human Anatomy & Rigify 163 DEF Rigging  
**Authoritative References**: `ORIGINAL_REQUEST.md` (## 2026-09-07T13:01:03Z), `PROJECT.md`, `survey_anatomy.md`

---

## 1. Executive Summary

Milestone M1 Feature 7 realigns the Rigify Human Metarig joint pivots from naive geometric approximations to true medical-grade biological skeletal centers. The current rig exhibits four critical kinematic defects:
1. **Hip Pivot Defect**: Placed at crotch line ($Z = z_{crotch} = 0.825\text{m}$), which is $38\text{mm}$ below the true acetabular cup, causing the gluteal fold and pelvic volume to collapse upon forward leg flexion.
2. **Knee Pivot Defect**: Placed too far forward ($Y = -0.020\text{m}$), directly adjacent to the anterior patellar surface, depriving the patella of an anatomical lever arm and causing the kneecap to collapse into the knee joint cavity during $90^\circ$ flexion.
3. **Ankle Axis Defect**: Placed horizontally along global X ($Z = 0.082\text{m}$, roll = 0), ignoring the asymmetric bimalleolar line where the medial malleolus is higher and anterior ($Z = 0.088\text{m}, Y = +0.002\text{m}$) and the lateral malleolus is lower and posterior ($Z = 0.076\text{m}, Y = -0.006\text{m}$).
4. **MTP Break Axis Defect**: Placed with a flat planar horizontal cut ($Y = -0.095\text{m}$, roll = 0), ignoring the natural oblique $\sim 65^\circ$ metatarsal break line connecting the prominent 1st metatarsal head to the recessed 5th metatarsal head.

This specification provides the exact mathematical derivations, coordinate values, bone roll angles, and code modifications for `src/morphomesh/human_rigging.py`, while preserving 100% of the 163 DEF bone invariant (64 body + 99 facial) and achieving 100% compliance with `tests/test_adversarial_rigging.py`.

---

## 2. Anatomical & Mathematical Formulations

### 2.1. Femoral Head Hip Pivot (Acetabulofemoral Joint)

#### Anatomical Rationale
The femoral head (*caput femoris*) sits deeply recessed within the acetabulum of the pelvis, bounded superiorly by the iliac crest and laterally by the greater trochanter (*trochanter major*). The true pivot of the hip joint is located medial and superior to the perineal crotch line. Placing the pivot at the crotch line ($Z = 0.825\text{m}$) creates an unnatural downward translation of the entire thigh upon rotation. Raising the pivot into the acetabular socket ($Z = 0.863\text{m}$) preserves the inguinal crease anteriorly and the gluteal contour posteriorly.

#### Mathematical Formulation
At standard canonical female height $H = 1.65\text{m}$ ($s = H / 1.65$):
- Pelvic crest reference height: $z_{pelvic\_crest} = 0.945\text{m} \cdot s$
- Crotch reference height: $z_{crotch} = 0.825\text{m} \cdot s$
- Acetabular socket elevation:
  $$Z_{hip} = z_{pelvic\_crest} - 0.082\text{m} \cdot s = 0.945\text{m} - 0.082\text{m} = 0.863\text{m} \cdot s$$
  $$\Delta Z = Z_{hip} - z_{crotch} = 0.863\text{m} - 0.825\text{m} = +0.038\text{m} \cdot s$$
- Anteroposterior placement:
  $$Y_{hip} = -0.010\text{m} \cdot s$$
- Mediolateral placement (medial femoral head, inset from greater trochanter):
  $$X_{hip\_L} = +0.088\text{m} \cdot s \cdot k_{hip}, \quad X_{hip\_R} = -0.088\text{m} \cdot s \cdot k_{hip}$$

#### Armature Bones Affected
- `DEF-thigh.L` / `DEF-thigh.R`:
  - `head`: $(\pm 0.088 \cdot s, -0.010 \cdot s, 0.863 \cdot s)$
  - `tail`: $P_{th\_mid} = 0.5 \cdot (P_{hip} + P_{knee})$
  - `roll`: $0.0\text{ rad}$
- `DEF-thigh.L.001` / `DEF-thigh.R.001`:
  - `head`: $P_{th\_mid}$
  - `tail`: $P_{knee}$
  - `roll`: $0.0\text{ rad}$

---

### 2.2. Knee Condylar Hinge Axis (Femorotibial Bicondylar Joint)

#### Anatomical Rationale
The human knee is a bicondylar hinge joint. The femoral condyles roll and slide on the tibial plateau with a transverse hinge axis passing through the centers of curvature of the medial and lateral condyles. The patella (*patella*) is a sesamoid bone gliding anterior to this axis. 
- In the anteriorly sculpted mesh, the patella apex/surface is situated at $Y \approx -0.038\text{m}$ to $-0.040\text{m}$ and $Z \approx 0.445\text{m}$ to $0.470\text{m}$.
- By recessing the condylar hinge axis to $Y = -0.008\text{m} \cdot s$, the patella maintains a biological lever arm of:
  $$\text{Lever Arm} = |Y_{patella} - Y_{hinge}| \approx |-0.038 - (-0.008)| = 0.030\text{m} \quad (30\text{mm})$$
- When the lower leg flexes $90^\circ$ backward, the patella swings in an arc of radius $R \ge 30\text{mm}$, ensuring the knee retains a smooth, rounded, volumetric profile with zero kneecap flattening or collapse into the joint space.

#### Mathematical Formulation
- Patella reference center: $z_{patella} = 0.470\text{m} \cdot s$
- Condylar hinge height:
  $$Z_{knee} = z_{patella} - 0.025\text{m} \cdot s = 0.470\text{m} - 0.025\text{m} = 0.445\text{m} \cdot s$$
- Condylar hinge depth:
  $$Y_{knee} = -0.008\text{m} \cdot s$$
- Mediolateral position:
  $$X_{knee\_L} = +0.100\text{m} \cdot s \cdot k_{hip}, \quad X_{knee\_R} = -0.100\text{m} \cdot s \cdot k_{hip}$$
- Pre-bend enforcement:
  Since $Y_{knee} = -0.008\text{m} < 0.0$, the anterior $-Y$ pre-bend condition required by Rigify IK solvers is strictly maintained. The configuration parameter `knee_prebend_y` defaults to `-0.008\text{m}`.
- Calculated pre-bend interior angle (Hip -> Knee -> Ankle):
  $$\angle_{knee} = 176.55^\circ \in [160.0^\circ, 179.5^\circ]$$

#### Armature Bones Affected
- `DEF-shin.L` / `DEF-shin.R`:
  - `head`: $(\pm 0.100 \cdot s, -0.008 \cdot s, 0.445 \cdot s)$
  - `tail`: $P_{sh\_mid} = 0.5 \cdot (P_{knee} + P_{ankle})$
  - `roll`: $0.0\text{ rad}$
- `DEF-thigh.L.001` / `DEF-thigh.R.001`:
  - `tail`: $(\pm 0.100 \cdot s, -0.008 \cdot s, 0.445 \cdot s)$

---

### 2.3. Oblique Bimalleolar Ankle Axis (Talocrural Joint)

#### Anatomical Rationale
The ankle joint (talocrural mortise) does not rotate around a horizontal axis parallel to the coronal plane. It articulates around the oblique bimalleolar line connecting the tips of the medial malleolus (tibia) and lateral malleolus (fibula).
- **Medial malleolus** (*malleolus medialis*): High and anterior.
  $$(X_{med}, Y_{med}, Z_{med}) = (\pm 0.072\text{m} \cdot s, +0.002\text{m} \cdot s, 0.088\text{m} \cdot s)$$
- **Lateral malleolus** (*malleolus lateralis*): Low and posterior.
  $$(X_{lat}, Y_{lat}, Z_{lat}) = (\pm 0.106\text{m} \cdot s, -0.006\text{m} \cdot s, 0.076\text{m} \cdot s)$$

#### Mathematical Formulation
1. **Ankle Center Pivot** (midpoint of bimalleolar line):
   $$P_{ankle\_L} = \left(\frac{0.072 + 0.106}{2}, \frac{0.002 - 0.006}{2}, \frac{0.088 + 0.076}{2}\right) \cdot s = (+0.089\text{m} \cdot s, -0.002\text{m} \cdot s, 0.082\text{m} \cdot s)$$
   $$P_{ankle\_R} = (-0.089\text{m} \cdot s, -0.002\text{m} \cdot s, 0.082\text{m} \cdot s)$$
2. **Bimalleolar Vector** ($\vec{v}_{bm}$ for Left ankle):
   $$\vec{v}_{bm} = P_{lat} - P_{med} = (+0.034\text{m}, -0.008\text{m}, -0.012\text{m}) \cdot s$$
   $$\|\vec{v}_{bm}\| = \sqrt{0.034^2 + (-0.008)^2 + (-0.012)^2} = \sqrt{0.001364} \approx 0.03693\text{m}$$
   $$\hat{u}_{bm} = (0.9206, -0.2166, -0.3249)$$
3. **Coronal Downward Slant**:
   $$\theta_{coronal} = \arctan\left(\frac{\Delta Z}{\Delta X}\right) = \arctan\left(\frac{-0.012}{0.034}\right) \approx -19.4^\circ$$
4. **Transverse External Torsion**:
   $$\theta_{transverse} = \arctan\left(\frac{\Delta Y}{\Delta X}\right) = \arctan\left(\frac{-0.008}{0.034}\right) \approx -13.2^\circ$$
5. **Roll Angle for `DEF-foot.L/R`**:
   The foot bone vector $\vec{y}_{foot}$ runs from $P_{ankle}$ to $P_{mtp}$:
   $$\vec{v}_{foot} = (0.000\text{m}, -0.087\text{m}, -0.060\text{m}) \cdot s \implies \hat{y}_{foot} \approx (0.0, -0.823, -0.568)$$
   Projecting $\hat{u}_{bm}$ onto the plane normal to $\hat{y}_{foot}$ and computing the rotation from Blender's default unrolled X axis gives:
   $$\text{Roll}_{foot.L} = -0.15627\text{ rad} \approx -8.95^\circ$$
   $$\text{Roll}_{foot.R} = +0.15627\text{ rad} \approx +8.95^\circ$$

#### Armature Bones Affected
- `DEF-shin.L.001` / `DEF-shin.R.001`:
  - `tail`: $(\pm 0.089 \cdot s, -0.002 \cdot s, 0.082 \cdot s)$
- `DEF-foot.L` / `DEF-foot.R`:
  - `head`: $(\pm 0.089 \cdot s, -0.002 \cdot s, 0.082 \cdot s)$
  - `tail`: $P_{mtp} = (\pm 0.089 \cdot s, -0.089 \cdot s, 0.022 \cdot s)$
  - `roll`: $-0.156\text{ rad}$ (Left), $+0.156\text{ rad}$ (Right)

---

### 2.4. Oblique MTP Break Axis (Metatarsophalangeal Articulation)

#### Anatomical Rationale
The human metatarsal heads form an oblique arch ("metatarsal break line") across the ball of the foot:
- The 1st metatarsal head (hallux/big toe ball) is situated significantly more anteriorly ($Y \approx -0.100\text{m}$) and higher on the medial longitudinal arch ($Z \approx 0.025\text{m}$).
- The 5th metatarsal head (pinky toe ball) is recessed posteriorly ($Y \approx -0.078\text{m}$) and lower on the lateral arch ($Z \approx 0.020\text{m}$).
- When walking or raising the heel (plantarflexion with toe dorsiflexion), the foot hinges across this oblique $\sim 65^\circ$ axis relative to the long axis of the foot (or $25^\circ$ oblique relative to the transverse coronal axis).

#### Mathematical Formulation
1. **MTP Joint Center Pivot** ($P_{mtp}$):
   $$P_{mtp\_L} = (+0.089\text{m} \cdot s, -0.089\text{m} \cdot s, 0.022\text{m} \cdot s)$$
   $$P_{mtp\_R} = (-0.089\text{m} \cdot s, -0.089\text{m} \cdot s, 0.022\text{m} \cdot s)$$
2. **Oblique Slant Formula**:
   $$\Delta X = X_5 - X_1 = 0.050\text{m} \cdot s$$
   $$\Delta Y = Y_5 - Y_1 = -0.078 - (-0.100) = +0.022\text{m} \cdot s$$
   $$\tan(\theta_{break}) = \frac{\Delta Y}{\Delta X} = \frac{0.022}{0.050} = 0.440 \approx \tan(23.75^\circ) \dots \tan(25^\circ) \approx 0.4663$$
   $$\text{Angle relative to long axis} = 90^\circ - 23.75^\circ = 66.25^\circ \approx 65^\circ$$
3. **Roll Angle for `DEF-toe.L/R`**:
   $$\text{Roll}_{toe.L} = -0.153\text{ rad} \approx -8.74^\circ$$
   $$\text{Roll}_{toe.R} = +0.153\text{ rad} \approx +8.74^\circ$$
4. **Toe Tip Coordinates** ($P_{toe}$):
   $$P_{toe\_L} = (+0.090\text{m} \cdot s, -0.145\text{m} \cdot s, 0.015\text{m} \cdot s)$$
   $$P_{toe\_R} = (-0.090\text{m} \cdot s, -0.145\text{m} \cdot s, 0.015\text{m} \cdot s)$$

#### Armature Bones Affected
- `DEF-toe.L` / `DEF-toe.R`:
  - `head`: $(\pm 0.089 \cdot s, -0.089 \cdot s, 0.022 \cdot s)$
  - `tail`: $(\pm 0.090 \cdot s, -0.145 \cdot s, 0.015 \cdot s)$
  - `roll`: $-0.153\text{ rad}$ (Left), $+0.153\text{ rad}$ (Right)

---

## 3. 163 DEF Bones Invariant & Hierarchy Verification

The Rigify Human Metarig is strictly bound by compile-time invariants:
- Total DEF bones: exactly **163**
- Body DEF bones: exactly **64**
- Facial DEF bones: exactly **99**

### 3.1. Complete Lower Limb Hierarchy Table
| Bone Name | Parent | Head $(x, y, z)$ [m] | Tail $(x, y, z)$ [m] | Length [m] | Roll [rad] |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DEF-thigh.L` | `DEF-spine` | $(+0.088, -0.010, 0.863)$ | $(+0.094, -0.009, 0.654)$ | $0.2091$ | $0.0$ |
| `DEF-thigh.L.001` | `DEF-thigh.L` | $(+0.094, -0.009, 0.654)$ | $(+0.100, -0.008, 0.445)$ | $0.2091$ | $0.0$ |
| `DEF-shin.L` | `DEF-thigh.L.001` | $(+0.100, -0.008, 0.445)$ | $(+0.0945, -0.005, 0.2635)$ | $0.1816$ | $0.0$ |
| `DEF-shin.L.001` | `DEF-shin.L` | $(+0.0945, -0.005, 0.2635)$ | $(+0.089, -0.002, 0.082)$ | $0.1816$ | $0.0$ |
| `DEF-foot.L` | `DEF-shin.L.001` | $(+0.089, -0.002, 0.082)$ | $(+0.089, -0.089, 0.022)$ | $0.1057$ | $-0.156$ |
| `DEF-toe.L` | `DEF-foot.L` | $(+0.089, -0.089, 0.022)$ | $(+0.090, -0.145, 0.015)$ | $0.0564$ | $-0.153$ |
| `DEF-thigh.R` | `DEF-spine` | $(-0.088, -0.010, 0.863)$ | $(-0.094, -0.009, 0.654)$ | $0.2091$ | $0.0$ |
| `DEF-thigh.R.001` | `DEF-thigh.R` | $(-0.094, -0.009, 0.654)$ | $(-0.100, -0.008, 0.445)$ | $0.2091$ | $0.0$ |
| `DEF-shin.R` | `DEF-thigh.R.001` | $(-0.100, -0.008, 0.445)$ | $(-0.0945, -0.005, 0.2635)$ | $0.1816$ | $0.0$ |
| `DEF-shin.R.001` | `DEF-shin.R` | $(-0.0945, -0.005, 0.2635)$ | $(-0.089, -0.002, 0.082)$ | $0.1816$ | $0.0$ |
| `DEF-foot.R` | `DEF-shin.R.001` | $(-0.089, -0.002, 0.082)$ | $(-0.089, -0.089, 0.022)$ | $0.1057$ | $+0.156$ |
| `DEF-toe.R` | `DEF-foot.R` | $(-0.089, -0.089, 0.022)$ | $(-0.090, -0.145, 0.015)$ | $0.0564$ | $+0.153$ |

**Integrity Assertions**:
- Bone count: exactly 12 lower limb DEF bones.
- All bone lengths strictly positive and $> 0.05\text{m}$ (far exceeding the $0.001\text{m}$ degenerate bone test threshold).
- Parent-child tree remains 100% homeomorphic to original Rigify hierarchy.

---

## 4. Skin Weighting Realignment (Feature 8 Anchoring)

In `src/morphomesh/human_rigging.py`, the function `calculate_anti_pinch_weights` must be upgraded to anchor the malleoli and smoothly interpolate across the oblique MTP break line:

1. **Malleoli Anchoring**:
   Vertices in the upper ankle region ($Z > 0.05\text{m} \cdot s$, $Y > -0.04\text{m} \cdot s$) must be anchored $\ge 80\%$ to `DEF-shin.001` so that foot rotation (plantarflexion / dorsiflexion) does not tear or twist the ankle malleoli away from the shin:
   $$\text{Weight}(DEF\text{-}shin.{side}.001) = 0.82, \quad \text{Weight}(DEF\text{-}foot.{side}) = 0.18$$
2. **Oblique MTP Hermite Smoothstep**:
   The break boundary between `DEF-foot` and `DEF-toe` follows the oblique angle:
   $$Y_{MTP}(X) = \left(-0.089 + 0.4663 \cdot (X - X_{ankle}) \cdot \text{sign}\right) \cdot scale$$
   $$u = \text{clamp}\left(\frac{Y_{MTP} - Y}{0.030 \cdot scale} + 0.5, 0.0, 1.0\right)$$
   $$W_{toe} = 3 u^2 - 2 u^3$$
   $$W(DEF\text{-}toe) = 0.90 \cdot W_{toe}$$
   $$W(DEF\text{-}foot) = 0.85 \cdot (1 - W_{toe}) + 0.10 \cdot W_{toe}$$
   $$W(DEF\text{-}shin.001) = 0.15 \cdot (1 - W_{toe})$$

---

## 5. Precise Code Changes for `src/morphomesh/human_rigging.py`

### 5.1. Update `HumanRigConfig`
In `src/morphomesh/human_rigging.py`, change default `knee_prebend_y`:
```python
<<<<
    knee_prebend_y: float = Field(default=-0.020, description="Knee anterior -Y pre-bend in meters.")
====
    knee_prebend_y: float = Field(default=-0.008, description="Knee anterior -Y pre-bend in meters (behind patella at condylar hinge axis).")
>>>>
```

### 5.2. Update `get_default_human_landmarks`
In `src/morphomesh/human_rigging.py`:
```python
<<<<
        "spine_chest": (0.0, -0.005 * s, 1.250 * s),
        "spine_waist": (0.0, -0.010 * s, 1.050 * s),
        "spine_pelvis": (0.0, 0.000 * s, 0.825 * s),
        "hip_L": (0.095 * s, -0.010 * s, 0.825 * s),
        "hip_R": (-0.095 * s, -0.010 * s, 0.825 * s),
        "knee_L": (0.100 * s, -0.020 * s, 0.445 * s),  # Pre-bend in -Y
        "knee_R": (-0.100 * s, -0.020 * s, 0.445 * s),
        "ankle_L": (0.090 * s, 0.005 * s, 0.082 * s),
        "ankle_R": (-0.090 * s, 0.005 * s, 0.082 * s),
        "toe_L": (0.090 * s, -0.145 * s, 0.025 * s),
        "toe_R": (-0.090 * s, -0.145 * s, 0.025 * s),
====
        "spine_chest": (0.0, -0.005 * s, 1.250 * s),
        "spine_waist": (0.0, -0.010 * s, 1.050 * s),
        "spine_pelvis": (0.0, 0.000 * s, 0.825 * s),
        # Biological skeletal landmarks (Feature 7)
        "pelvic_crest_L": (0.145 * s, -0.005 * s, 0.945 * s),
        "pelvic_crest_R": (-0.145 * s, -0.005 * s, 0.945 * s),
        # Femoral head hip pivot: raised +0.038m into true acetabular socket (Z = z_pelvic_crest - 0.082m, Y = -0.010m)
        "hip_L": (0.088 * s, -0.010 * s, 0.863 * s),
        "hip_R": (-0.088 * s, -0.010 * s, 0.863 * s),
        "patella_L": (0.100 * s, -0.038 * s, 0.470 * s),
        "patella_R": (-0.100 * s, -0.038 * s, 0.470 * s),
        # Knee condylar hinge axis: Z = z_patella - 0.025m = 0.445m, Y = -0.008m (recessed behind patella)
        "knee_L": (0.100 * s, -0.008 * s, 0.445 * s),  # Pre-bend in -Y
        "knee_R": (-0.100 * s, -0.008 * s, 0.445 * s),
        # Asymmetric bimalleolar ankle landmarks (Medial higher/anterior, Lateral lower/posterior)
        "malleolus_medial_L": (0.072 * s, 0.002 * s, 0.088 * s),
        "malleolus_lateral_L": (0.106 * s, -0.006 * s, 0.076 * s),
        "malleolus_medial_R": (-0.072 * s, 0.002 * s, 0.088 * s),
        "malleolus_lateral_R": (-0.106 * s, -0.006 * s, 0.076 * s),
        # Ankle center: midpoint of true bimalleolar line connecting medial and lateral malleoli
        "ankle_L": (0.089 * s, -0.002 * s, 0.082 * s),
        "ankle_R": (-0.089 * s, -0.002 * s, 0.082 * s),
        # Oblique MTP break axis & toe tip
        "toe_L": (0.090 * s, -0.145 * s, 0.015 * s),
        "toe_R": (-0.090 * s, -0.145 * s, 0.015 * s),
>>>>
```

### 5.3. Update `generate_rigify_human_metarig` Lower Limbs
In `src/morphomesh/human_rigging.py`:
```python
<<<<
    # --------------------------------------------------------------------------
    # 3. LOWER LIMBS & FEET (12 DEF BONES)
    # --------------------------------------------------------------------------
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        p_hip = lm[f"hip_{side}"]
        p_kn = lm[f"knee_{side}"]
        # Enforce pre-bend -Y on knee
        kn_y = min(p_kn[1], cfg.knee_prebend_y * scale)
        p_kn = (p_kn[0], kn_y, p_kn[2])

        p_ak = lm[f"ankle_{side}"]
        p_toe = lm[f"toe_{side}"]

        # Thigh midpoint for dual-bone twist
        p_th_mid = (
            0.5 * (p_hip[0] + p_kn[0]),
            0.5 * (p_hip[1] + p_kn[1]),
            0.5 * (p_hip[2] + p_kn[2]),
        )
        # Shin midpoint for dual-bone twist
        p_sh_mid = (
            0.5 * (p_kn[0] + p_ak[0]),
            0.5 * (p_kn[1] + p_ak[1]),
            0.5 * (p_kn[2] + p_ak[2]),
        )

        bones[f"DEF-thigh.{side}"] = BoneDefinition(
            f"DEF-thigh.{side}", p_hip, p_th_mid, parent="DEF-spine", category="body"
        )
        bones[f"DEF-thigh.{side}.001"] = BoneDefinition(
            f"DEF-thigh.{side}.001", p_th_mid, p_kn, parent=f"DEF-thigh.{side}", category="body"
        )
        bones[f"DEF-shin.{side}"] = BoneDefinition(
            f"DEF-shin.{side}", p_kn, p_sh_mid, parent=f"DEF-thigh.{side}.001", category="body"
        )
        bones[f"DEF-shin.{side}.001"] = BoneDefinition(
            f"DEF-shin.{side}.001", p_sh_mid, p_ak, parent=f"DEF-shin.{side}", category="body"
        )
        bones[f"DEF-foot.{side}"] = BoneDefinition(
            f"DEF-foot.{side}", p_ak, (p_toe[0], p_toe[1] + 0.05 * scale, p_toe[2] + 0.01 * scale),
            parent=f"DEF-shin.{side}.001", category="body"
        )
        bones[f"DEF-toe.{side}"] = BoneDefinition(
            f"DEF-toe.{side}",
            bones[f"DEF-foot.{side}"].tail,
            p_toe,
            parent=f"DEF-foot.{side}",
            category="body",
        )
====
    # --------------------------------------------------------------------------
    # 3. LOWER LIMBS & FEET (12 DEF BONES) - BIOLOGICAL SKELETAL REALIGNMENT
    # --------------------------------------------------------------------------
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        # 3a. Femoral head hip pivot: raised +0.038m into true acetabular socket
        # Z = z_pelvic_crest - 0.082m, Y = -0.010m
        if f"pelvic_crest_{side}" in lm:
            z_pelvic = lm[f"pelvic_crest_{side}"][2]
        elif "spine_pelvis" in lm:
            z_pelvic = lm["spine_pelvis"][2] + 0.120 * scale
        else:
            z_pelvic = 0.945 * scale
        z_hip = z_pelvic - 0.082 * scale
        y_hip = -0.010 * scale
        x_hip = lm.get(f"hip_{side}", (sign * 0.088 * scale, y_hip, z_hip))[0]
        if abs(x_hip) > 0.090 * scale:
            x_hip = sign * 0.088 * scale
        p_hip = (x_hip, y_hip, z_hip)

        # 3b. Knee condylar hinge axis: Z = z_patella - 0.025m, Y = -0.008m (recessed behind patella)
        if f"patella_{side}" in lm:
            z_pat = lm[f"patella_{side}"][2]
        elif f"knee_{side}" in lm:
            z_pat = lm[f"knee_{side}"][2] + 0.025 * scale
        else:
            z_pat = 0.470 * scale
        z_knee = z_pat - 0.025 * scale
        p_kn_raw = lm.get(f"knee_{side}", (sign * 0.100 * scale, -0.008 * scale, z_knee))
        kn_y = min(-0.008 * scale, p_kn_raw[1], cfg.knee_prebend_y * scale)
        p_kn = (p_kn_raw[0], kn_y, z_knee)

        # 3c. Oblique bimalleolar ankle axis: line connecting medial and lateral malleoli
        if f"malleolus_medial_{side}" in lm and f"malleolus_lateral_{side}" in lm:
            p_med = lm[f"malleolus_medial_{side}"]
            p_lat = lm[f"malleolus_lateral_{side}"]
        else:
            p_med = (sign * 0.072 * scale, 0.002 * scale, 0.088 * scale)
            p_lat = (sign * 0.106 * scale, -0.006 * scale, 0.076 * scale)
        p_ak = (
            0.5 * (p_med[0] + p_lat[0]),
            0.5 * (p_med[1] + p_lat[1]),
            0.5 * (p_med[2] + p_lat[2]),
        )
        ankle_roll = sign * -0.156  # -8.95 deg tilt matching bimalleolar slant

        # 3d. Oblique MTP break axis: angled ~65 degrees across metatarsal heads
        p_mtp = (p_ak[0], -0.089 * scale, 0.022 * scale)
        p_toe_raw = lm.get(f"toe_{side}", (sign * 0.090 * scale, -0.145 * scale, 0.015 * scale))
        p_toe = (p_toe_raw[0], p_toe_raw[1], min(p_toe_raw[2], 0.020 * scale))
        mtp_roll = sign * -0.153  # -8.74 deg roll aligning transverse arch drop

        # Thigh midpoint for dual-bone twist
        p_th_mid = (
            0.5 * (p_hip[0] + p_kn[0]),
            0.5 * (p_hip[1] + p_kn[1]),
            0.5 * (p_hip[2] + p_kn[2]),
        )
        # Shin midpoint for dual-bone twist
        p_sh_mid = (
            0.5 * (p_kn[0] + p_ak[0]),
            0.5 * (p_kn[1] + p_ak[1]),
            0.5 * (p_kn[2] + p_ak[2]),
        )

        bones[f"DEF-thigh.{side}"] = BoneDefinition(
            f"DEF-thigh.{side}", p_hip, p_th_mid, parent="DEF-spine", roll=0.0, category="body"
        )
        bones[f"DEF-thigh.{side}.001"] = BoneDefinition(
            f"DEF-thigh.{side}.001", p_th_mid, p_kn, parent=f"DEF-thigh.{side}", roll=0.0, category="body"
        )
        bones[f"DEF-shin.{side}"] = BoneDefinition(
            f"DEF-shin.{side}", p_kn, p_sh_mid, parent=f"DEF-thigh.{side}.001", roll=0.0, category="body"
        )
        bones[f"DEF-shin.{side}.001"] = BoneDefinition(
            f"DEF-shin.{side}.001", p_sh_mid, p_ak, parent=f"DEF-shin.{side}", roll=0.0, category="body"
        )
        bones[f"DEF-foot.{side}"] = BoneDefinition(
            f"DEF-foot.{side}", p_ak, p_mtp, parent=f"DEF-shin.{side}.001", roll=ankle_roll, category="body"
        )
        bones[f"DEF-toe.{side}"] = BoneDefinition(
            f"DEF-toe.{side}",
            p_mtp,
            p_toe,
            parent=f"DEF-foot.{side}",
            roll=mtp_roll,
            category="body",
        )
>>>>
```

### 5.4. Add `align_rigify_metarig_pivots` Implementation
Add after `generate_rigify_human_metarig`:
```python
def align_rigify_metarig_pivots(
    armature_obj: Any,
    landmarks: Dict[str, Tuple[float, float, float]],
    scale: float = 1.0,
) -> None:
    """
    Realigns 163 DEF Rigify metarig joint pivots to anatomical skeletal centers (Feature 7 of M1):
    - Femoral head hip joint: Z = z_pelvic_crest - 0.082m, Y = -0.010m
    - Condylar knee hinge: Z = z_patella - 0.025m, Y = -0.008m (behind patella)
    - Oblique bimalleolar ankle: connecting medial (Z=0.088m, Y=+0.002m) and lateral (Z=0.076m, Y=-0.006m) malleoli
    - MTP break axis: oblique angle ~65 degrees across metatarsal heads

    Operates polymorphically on:
    - MetarigStructure Python instances
    - Live Blender Armature objects (edit_bones or pose.bones)
    - Metarig bone dictionaries
    """
    s = scale
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        # 1. Femoral head hip joint: raised +0.038m into true acetabular socket
        if f"pelvic_crest_{side}" in landmarks:
            z_pelvic = landmarks[f"pelvic_crest_{side}"][2]
        elif "spine_pelvis" in landmarks:
            z_pelvic = landmarks["spine_pelvis"][2] + 0.120 * s
        else:
            z_pelvic = 0.945 * s
        z_hip = z_pelvic - 0.082 * s
        y_hip = -0.010 * s
        x_hip = landmarks.get(f"hip_{side}", (sign * 0.088 * s, y_hip, z_hip))[0]
        if abs(x_hip) > 0.090 * s:
            x_hip = sign * 0.088 * s
        p_hip = (x_hip, y_hip, z_hip)

        # 2. Condylar knee hinge: recessed behind patella
        if f"patella_{side}" in landmarks:
            z_pat = landmarks[f"patella_{side}"][2]
        elif f"knee_{side}" in landmarks:
            z_pat = landmarks[f"knee_{side}"][2] + 0.025 * s
        else:
            z_pat = 0.470 * s
        z_knee = z_pat - 0.025 * s
        y_knee = -0.008 * s
        x_knee = landmarks.get(f"knee_{side}", (sign * 0.100 * s, y_knee, z_knee))[0]
        p_knee = (x_knee, y_knee, z_knee)

        # 3. Oblique bimalleolar ankle
        if f"malleolus_medial_{side}" in landmarks and f"malleolus_lateral_{side}" in landmarks:
            p_med = landmarks[f"malleolus_medial_{side}"]
            p_lat = landmarks[f"malleolus_lateral_{side}"]
        else:
            p_med = (sign * 0.072 * s, 0.002 * s, 0.088 * s)
            p_lat = (sign * 0.106 * s, -0.006 * s, 0.076 * s)
        p_ankle = (
            0.5 * (p_med[0] + p_lat[0]),
            0.5 * (p_med[1] + p_lat[1]),
            0.5 * (p_med[2] + p_lat[2]),
        )
        ankle_roll = sign * -0.156

        # 4. Oblique MTP break axis (~65 deg)
        p_mtp = (p_ankle[0], -0.089 * s, 0.022 * s)
        toe_tip = landmarks.get(f"toe_{side}", (sign * 0.090 * s, -0.145 * s, 0.015 * s))
        mtp_roll = sign * -0.153

        # Midpoints for dual-bone twist
        p_th_mid = (0.5 * (p_hip[0] + p_knee[0]), 0.5 * (p_hip[1] + p_knee[1]), 0.5 * (p_hip[2] + p_knee[2]))
        p_sh_mid = (0.5 * (p_knee[0] + p_ankle[0]), 0.5 * (p_knee[1] + p_ankle[1]), 0.5 * (p_knee[2] + p_ankle[2]))

        # Polymorphic application
        if isinstance(armature_obj, MetarigStructure):
            bones = armature_obj.bones
            if f"DEF-thigh.{side}" in bones:
                bones[f"DEF-thigh.{side}"].head = p_hip
                bones[f"DEF-thigh.{side}"].tail = p_th_mid
            if f"DEF-thigh.{side}.001" in bones:
                bones[f"DEF-thigh.{side}.001"].head = p_th_mid
                bones[f"DEF-thigh.{side}.001"].tail = p_knee
            if f"DEF-shin.{side}" in bones:
                bones[f"DEF-shin.{side}"].head = p_knee
                bones[f"DEF-shin.{side}"].tail = p_sh_mid
            if f"DEF-shin.{side}.001" in bones:
                bones[f"DEF-shin.{side}.001"].head = p_sh_mid
                bones[f"DEF-shin.{side}.001"].tail = p_ankle
            if f"DEF-foot.{side}" in bones:
                bones[f"DEF-foot.{side}"].head = p_ankle
                bones[f"DEF-foot.{side}"].tail = p_mtp
                bones[f"DEF-foot.{side}"].roll = ankle_roll
            if f"DEF-toe.{side}" in bones:
                bones[f"DEF-toe.{side}"].head = p_mtp
                bones[f"DEF-toe.{side}"].tail = toe_tip
                bones[f"DEF-toe.{side}"].roll = mtp_roll
        elif hasattr(armature_obj, "data") and hasattr(armature_obj.data, "edit_bones"):
            eb = armature_obj.data.edit_bones
            bone_specs = [
                (f"DEF-thigh.{side}", p_hip, p_th_mid, 0.0),
                (f"DEF-thigh.{side}.001", p_th_mid, p_knee, 0.0),
                (f"DEF-shin.{side}", p_knee, p_sh_mid, 0.0),
                (f"DEF-shin.{side}.001", p_sh_mid, p_ankle, 0.0),
                (f"DEF-foot.{side}", p_ankle, p_mtp, ankle_roll),
                (f"DEF-toe.{side}", p_mtp, toe_tip, mtp_roll),
            ]
            for b_n, h_pt, t_pt, r_val in bone_specs:
                if b_n in eb:
                    eb[b_n].head = h_pt
                    eb[b_n].tail = t_pt
                    eb[b_n].roll = r_val
        elif isinstance(armature_obj, dict):
            bone_specs = [
                (f"DEF-thigh.{side}", p_hip, p_th_mid, 0.0),
                (f"DEF-thigh.{side}.001", p_th_mid, p_knee, 0.0),
                (f"DEF-shin.{side}", p_knee, p_sh_mid, 0.0),
                (f"DEF-shin.{side}.001", p_sh_mid, p_ankle, 0.0),
                (f"DEF-foot.{side}", p_ankle, p_mtp, ankle_roll),
                (f"DEF-toe.{side}", p_mtp, toe_tip, mtp_roll),
            ]
            for b_n, h_pt, t_pt, r_val in bone_specs:
                if b_n in armature_obj:
                    armature_obj[b_n]["head"] = [round(c, 5) for c in h_pt]
                    armature_obj[b_n]["tail"] = [round(c, 5) for c in t_pt]
                    armature_obj[b_n]["roll"] = round(r_val, 5)
```

### 5.5. Update `calculate_anti_pinch_weights`
In `src/morphomesh/human_rigging.py`:
```python
<<<<
        elif "foot_L" in groups or "foot_R" in groups:
            side_f = "L" if "foot_L" in groups or vx >= 0.0 else "R"
            if vy < -0.10:
                weight_map.set_weight(i, f"DEF-toe.{side_f}", 0.90)
                weight_map.set_weight(i, f"DEF-foot.{side_f}", 0.10)
            else:
                weight_map.set_weight(i, f"DEF-foot.{side_f}", 0.85)
                weight_map.set_weight(i, f"DEF-shin.{side_f}.001", 0.15)
            assigned = True
====
        elif "foot_L" in groups or "foot_R" in groups:
            side_f = "L" if "foot_L" in groups or vx >= 0.0 else "R"
            s_sign = 1.0 if side_f == "L" else -1.0
            scale_f = lm.get("head_top", (0, 0, 1.65))[2] / 1.65
            ak_x = lm.get(f"ankle_{side_f}", (s_sign * 0.090 * scale_f, 0, 0))[0]

            # Oblique MTP break axis: angled ~65 degrees across metatarsal heads
            # tan(25 deg) ~ 0.4663 gives the oblique slant across medial/lateral heads
            y_mtp = (-0.089 + 0.4663 * (vx - ak_x) * s_sign) * scale_f

            # Smooth Hermite transition across MTP break line
            u_break = max(0.0, min(1.0, (y_mtp - vy) / (0.030 * scale_f) + 0.5))
            w_toe = 3.0 * (u_break ** 2) - 2.0 * (u_break ** 3)

            # Malleoli and upper tarsus anchoring (>=80% to DEF-shin.001)
            is_malleoli_or_upper_tarsus = (vy > -0.04 * scale_f) and (vz > 0.05 * scale_f)
            if is_malleoli_or_upper_tarsus:
                weight_map.set_weight(i, f"DEF-shin.{side_f}.001", 0.82)
                weight_map.set_weight(i, f"DEF-foot.{side_f}", 0.18)
            else:
                weight_map.set_weight(i, f"DEF-toe.{side_f}", w_toe * 0.90)
                weight_map.set_weight(i, f"DEF-foot.{side_f}", (1.0 - w_toe) * 0.85 + w_toe * 0.10)
                weight_map.set_weight(i, f"DEF-shin.{side_f}.001", (1.0 - w_toe) * 0.15)
            assigned = True
>>>>
```

### 5.6. Update `get_rigging_script` for Roll Angle Preservation
In `src/morphomesh/human_rigging.py`:
```python
<<<<
    for b_name, b_def in metarig.bones.items():
        metarig_bones_data[b_name] = {
            "head": [round(x, 5) for x in b_def.head],
            "tail": [round(x, 5) for x in b_def.tail],
            "parent": b_def.parent,
            "use_deform": b_def.use_deform,
        }
====
    for b_name, b_def in metarig.bones.items():
        metarig_bones_data[b_name] = {
            "head": [round(x, 5) for x in b_def.head],
            "tail": [round(x, 5) for x in b_def.tail],
            "parent": b_def.parent,
            "roll": round(b_def.roll, 5),
            "use_deform": b_def.use_deform,
        }
>>>>
```
And in the Blender script template:
```python
<<<<
metarig_bones = json.loads({repr(json.dumps(metarig_bones_data))})
for b_name, b_info in metarig_bones.items():
    b = eb.new(b_name)
    b.head = b_info["head"]
    b.tail = b_info["tail"]
    b.use_deform = b_info.get("use_deform", True)
====
metarig_bones = json.loads({repr(json.dumps(metarig_bones_data))})
for b_name, b_info in metarig_bones.items():
    b = eb.new(b_name)
    b.head = b_info["head"]
    b.tail = b_info["tail"]
    b.use_deform = b_info.get("use_deform", True)
    if "roll" in b_info:
        b.roll = b_info["roll"]
>>>>
```

---

## 6. Verification and Regression Checklist

1. **163 DEF Bones Invariant**:
   - `def_bone_count == 163` (64 body DEF + 99 facial DEF).
   - Zero duplicates in bone naming.
2. **Knee Pre-Bend Geometry**:
   - `verify_prebends()` passes with `elbow_L_y > 0.0` and `knee_L_y < 0.0`.
   - Knee pre-bend interior angle $\angle = 176.55^\circ \in [160^\circ, 179.5^\circ]$.
3. **Roll Angle Integrity**:
   - `DEF-foot.L`: $-0.156\text{ rad}$ ($-8.95^\circ$).
   - `DEF-foot.R`: $+0.156\text{ rad}$ ($+8.95^\circ$).
   - `DEF-toe.L`: $-0.153\text{ rad}$ ($-8.74^\circ$).
   - `DEF-toe.R`: $+0.153\text{ rad}$ ($+8.74^\circ$).
4. **Vertex Weight Normalization**:
   - 100% of vertices sum to $1.0 \pm 10^{-4}$.
   - Malleoli anchored $\ge 80\%$ to `DEF-shin.001`.
   - Patella locked $\ge 90\%$ to `DEF-shin`.
5. **Headless Blender 4.5+ LTS**:
   - `get_rigging_script` executes with zero syntax errors.
   - All 163 edit bones inherit calibrated coordinates and roll angles.
