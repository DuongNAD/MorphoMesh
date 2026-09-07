# Technical Remediation Plan: Milestone 4 Iteration 3
## Remediation for Camera Optics, String Snapping, Garment Penetration & Test Hardening

**Agent**: `explorer_remediation_m4_1`  
**Roles**: explorer, investigator, synthesizer  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_1`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T03:36:00+07:00  
**Handoff Type**: Hard (Investigation Complete, Fully Verified Technical Plan)

---

## Executive Summary

Milestone 4 Iteration 2 achieved major functional milestones (compilation of Geometry Nodes hair curves evaluating 13,776 vertices, dynamic mid-air butterflies, unburied eyes at $Y = -0.1305\text{m}$, 3-point studio lighting with `TRACK_TO` constraints, and ice-blue satin sash with white sandals). However, comprehensive audits by `auditor_human_m4_iter2_1`, `challenger_human_m4_iter2_1`, and `reviewer_human_m4_iter2_2` identified three critical defects preventing production certification:
1. **Camera Optics & Decapitation Failure**: `Camera_FullBody` and turnaround cameras were coded with `cam_full_data.lens = {cfg_obj.camera_lens}` (evaluating to 85.0mm instead of 50.0mm). At distance 5.5m in 16:9 ($1920 \times 1080$), vertical coverage was only 1.31m, causing 27.6% vertical cropping ($\text{NDC } Y \in [-0.1439, 1.1319]$), severing the head at the chin and amputating feet at the calves.
2. **Marionette String Bone Tail Disconnect**: String proximal anchor coordinates in `wardrobe.py:452-465` were hardcoded at $Z \in [0.865\text{m}, 0.895\text{m}]$, leaving a $16.3\text{cm}$ air gap above actual rest-pose finger bone landmarks ($Z \in [0.676\text{m}, 0.731\text{m}]$).
3. **Dress Bodice Bust Penetration**: `generate_dress_bodice()` in `wardrobe.py` omitted the +35% bust protrusion formula from `human_generator.py:352`, had undersized radial boundaries at $Z = 1.27\text{m}$, and had sunken shoulder straps, causing 45 out of 140 vertices (32.1%) to penetrate up to $-47.72\text{mm}$ inside the chest and shoulder volume. Furthermore, the waist sash had a minimum clearance of only $+3.14\text{mm}$ ($< +4.0\text{mm}$).

This report provides an exact, mathematically derived, and empirically verified remediation plan for Milestone 4 Iteration 3.

---

## 1. Observation

### 1.1 Defect 1: Full-Body and Turnaround Camera Optics & Decapitation
- **Source Code**: In `src/morphomesh/character_assembler.py:712-736`:
  ```python
  # Full-Body Camera: Framed at Yu Nian An's full 1.65m height at distance 5.5m without cropping
  cam_full_data = bpy.data.cameras.get("Camera_FullBody") or bpy.data.cameras.new(name="Camera_FullBody")
  cam_full_data.lens = {cfg_obj.camera_lens}
  cam_full_data.sensor_width = 36.0
  cam_full_data.sensor_height = 24.0
  cam_full_obj = bpy.data.objects.get("Camera_FullBody") or bpy.data.objects.new(name="Camera_FullBody", object_data=cam_full_data)
  cam_full_obj.location = (0.0, -5.5 * s, 0.825 * s)
  cam_full_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
  organize_object(cam_full_obj, "06_Lights_Camera")
  ...
  for c_name, c_loc, c_rot in turnaround_angles:
      c_dat = bpy.data.cameras.get(c_name) or bpy.data.cameras.new(name=c_name)
      c_dat.lens = {cfg_obj.camera_lens}
      c_o = bpy.data.objects.get(c_name) or bpy.data.objects.new(name=c_name, object_data=c_dat)
      c_o.location = c_loc
      c_o.rotation_euler = c_rot
      organize_object(c_o, "06_Lights_Camera")
  ```
- **Property Trace**: `MasterAssemblyConfig.camera_lens` defaults to `85.0` (line 173). As a result, `{cfg_obj.camera_lens}` interpolated `85.0` into both `Camera_FullBody` and the 4 turnaround cameras (`Camera_Front`, `Camera_ThreeQuarter`, `Camera_Profile`, `Camera_Back`).
- **Empirical Measurement in Live Blender 4.5.4 LTS**:
  - Render resolution: $1920 \times 1080$ (Aspect 1.7778).
  - Subject height: $1.6456\text{m}$ ($Z \in [0.0044\text{m}, 1.6500\text{m}]$).
  - Camera: `Camera_FullBody` at $(0.0, -5.5\text{m}, 0.825\text{m})$, lens $= 85.0\text{mm}$, sensor width $= 36\text{mm}$.
  - Screen projection via `world_to_camera_view`:
    - $\text{NDC } X \in [0.3183, 0.6817]$ (centered horizontally).
    - $\text{NDC } Y \in [-0.1439, 1.1319]$ (exceeds $[0.0, 1.0]$ visible frame).
  - Head top ($Z > 1.48\text{m}$) is cropped by 13.19% off the top edge.
  - Feet and sandals ($Z < 0.17\text{m}$) are cropped by 14.39% off the bottom edge.
  - Total vertical cropping: 27.58% of character height.

### 1.2 Defect 2: Marionette String Coordinate Disconnect from Fingertip Bones
- **Source Code**: In `src/morphomesh/wardrobe.py:450-466`:
  ```python
  if rest_pose or target_positions is not None:
      # Hand rest-pose finger distal coordinates (Z in [0.85m, 0.90m])
      finger_anchors = [
          # Left Hand 5 fingers
          (0.385 * s, -0.055 * s, 0.895 * s),   # Thumb L
          (0.395 * s, -0.045 * s, 0.875 * s),   # Index L
          (0.385 * s, -0.040 * s, 0.865 * s),   # Middle L
          (0.370 * s, -0.035 * s, 0.875 * s),   # Ring L
          (0.355 * s, -0.030 * s, 0.890 * s),   # Pinky L
          # Right Hand 5 fingers
          (-0.385 * s, -0.055 * s, 0.895 * s),  # Thumb R
          (-0.395 * s, -0.045 * s, 0.875 * s),  # Index R
          (-0.385 * s, -0.040 * s, 0.865 * s),  # Middle R
          (-0.370 * s, -0.035 * s, 0.875 * s),  # Ring R
          (-0.355 * s, -0.030 * s, 0.890 * s),  # Pinky R
      ]
  ```
- **Rigify Finger Bone Tails**: In `src/morphomesh/human_rigging.py:480-520` (canonical female $s = 1.0$):
  - `DEF-thumb.03.L` tail: $(0.38940, -0.07979, 0.73070)$
  - `DEF-f_index.03.L` tail: $(0.37472, -0.06344, 0.68727)$
  - `DEF-f_middle.03.L` tail: $(0.36297, -0.05394, 0.67603)$
  - `DEF-f_ring.03.L` tail: $(0.35061, -0.04522, 0.68807)$
  - `DEF-f_pinky.03.L` tail: $(0.33907, -0.03815, 0.70840)$
  - `DEF-thumb.03.R` tail: $(-0.38940, -0.07979, 0.73070)$
  - `DEF-f_index.03.R` tail: $(-0.37472, -0.06344, 0.68727)$
  - `DEF-f_middle.03.R` tail: $(-0.36297, -0.05394, 0.67603)$
  - `DEF-f_ring.03.R` tail: $(-0.35061, -0.04522, 0.68807)$
  - `DEF-f_pinky.03.R` tail: $(-0.33907, -0.03815, 0.70840)$
- **Body Mesh Finger Vertices**: `fingers_L` vertex group spans $Z \in [0.6566\text{m}, 0.7600\text{m}]$, $Y \in [-0.0623\text{m}, -0.0153\text{m}]$.
- **Separation**: The string roots at $Z = 0.875\text{m} - 0.895\text{m}$ float $16.3\text{cm}$ to $18.8\text{cm}$ above the actual fingertips and bone deformer tails.

### 1.3 Defect 3: Dress Bodice Bust Penetration and Sash Clearance Deficit
- **Source Code**: In `src/morphomesh/human_generator.py:351-353`:
  ```python
  mod_y = ry
  if vg_name == "chest" and sin_t < -0.3:
      mod_y = ry * (1.0 + 0.35 * (-sin_t - 0.3))
  ```
  At $Z = 1.22\text{m}$, $r_y = 0.118$, $y_{\text{offset}} = -0.012$. For $\sin\theta = -1.0$ (bust center), $Y_{\text{body}} = -0.118 \times (1.0 + 0.35 \times 0.7) - 0.012 = -0.1589\text{m}$.
- **Wardrobe Bodice Formulation**: In `src/morphomesh/wardrobe.py:102, 122`:
  ```python
  (1.22 * s, 0.145 * s * k_c + clearance, 0.108 * s * k_c + clearance, -0.010 * s * k_c)
  ...
  py = ry * sin_t + yo
  ```
  For $s = 1.0, \text{clearance} = 0.015$, $r_y = 0.108 + 0.015 = 0.123\text{m}$. At $\sin\theta = -1.0$, $Y_{\text{bodice}} = -0.123 - 0.010 = -0.1330\text{m}$.
- **Clearance Failure**: Because $-Y$ is anterior forward, $Y_{\text{body}} = -0.1589\text{m}$ protrudes $25.9\text{mm}$ past $Y_{\text{bodice}} = -0.1330\text{m}$.
- **Shoulder Strap Penetration**: In `src/morphomesh/wardrobe.py:144-157`, `y_front = -0.085`, `z_top = 1.34`. The body shoulder crest at $X = 0.065$ reaches $Z = 1.370\text{m}$, and the upper chest reaches $Y = -0.131\text{m}$. Consequently, all 20 strap vertices penetrate the flesh by up to $-47.72\text{mm}$.
- **Live BVHTree Signed Clearance Test**:
  - `Mesh_Dress_Bodice`: Min Signed Clearance $= -47.72\text{mm}$, Penetrations $= 45 / 140$ base vertices (25 ring vertices + 20 strap vertices).
  - `Mesh_Dress_WaistSash`: Min Signed Clearance $= +3.14\text{mm}$ ($< +4.0\text{mm}$ threshold).

---

## 2. Logic Chain

1. **Optical Derivation for Full-Body Framing**:
   - In 16:9 aspect ratio ($1920 \times 1080$), Blender with sensor width $W_{\text{sensor}} = 36.0\text{mm}$ uses effective vertical sensor aperture $H_{\text{sensor}} = 36.0 / (16/9) = 20.25\text{mm}$.
   - Vertical field of view $\theta_v = 2 \arctan\left(\frac{H_{\text{sensor}}}{2 f}\right)$.
   - For an $85.0\text{mm}$ lens:
     $$\theta_v = 2 \arctan\left(\frac{20.25}{170}\right) = 13.602^\circ$$
     At distance $D = 5.5\text{m}$, vertical subject span is $H = 2 D \tan(\theta_v / 2) = 5.5 \times (20.25 / 85.0) = 1.3103\text{m}$.
     Because Yu Nian An's height is $1.6456\text{m} > 1.3103\text{m}$, clipping is mathematically inevitable with 85mm.
   - For a $50.0\text{mm}$ lens:
     $$\theta_v = 2 \arctan\left(\frac{20.25}{100}\right) = 22.895^\circ$$
     At distance $D = 5.5\text{m}$, vertical subject span is:
     $$H = 5.5 \times \frac{20.25}{50.0} = 2.2275\text{m}$$
   - Centering the camera at $Z_{\text{cam}} = 0.825\text{m}$ (half of 1.65m):
     $$\text{Frame vertical range} = [0.825 - 1.11375, 0.825 + 1.11375] = [-0.2888\text{m}, 1.9388\text{m}]$$
     Character bottom ($Z = 0.0044\text{m}$) maps to $\text{NDC } Y \approx 0.1316$ (~12.1% bottom margin).
     Character top ($Z = 1.6500\text{m}$) maps to $\text{NDC } Y \approx 0.8703$ (~12.8% top margin).
   - In live Blender depsgraph projection with 50mm, $\text{NDC } Y = [0.1213, 0.8717]$, which strictly satisfies $[0.05, 0.95]$ with zero cropping.

2. **Kinematic Snapping Derivation for Marionette Strings**:
   - The string mesh is driven by an Armature modifier targeting `Armature_Yu_Nian_An_Rigify`.
   - The deformation vertex groups correspond to `DEF-thumb.03.L/R` through `DEF-f_pinky.03.L/R`.
   - When a bone rotates, vertices deform relative to the rest pose of that bone.
   - If string vertices start $16.3\text{cm}$ away from the bone tail in the rest pose, any rotational deformation applies a lever-arm translation in empty air.
   - By assigning the string proximal anchors to the exact bone tails $(t_x, t_y, t_z)$, the rest-pose distance is $0.0\text{mm}$ (and with quad thickness radius $1.0\text{mm}$, vertex distance is $\le 1.0\text{mm} < 5.0\text{mm}$). When the fingers curl or articulate, the cords pull directly from the fingertips.

3. **Geometric Clearance Derivation for Dress Bodice**:
   - `human_generator.py` expands the anterior chest by factor $1.0 + 0.35 \times (-\sin\theta - 0.3)$ for $\sin\theta < -0.3$.
   - To maintain strictly positive clearance $\ge +5.0\text{mm}$ outside the solid body volume:
     1. The bodice must mirror this expansion with a slightly higher multiplier ($+38\%$) to prevent boundary contact at inflection points:
        $$\text{mod\_}r_y = r_y \times (1.0 + 0.38 \times (-\sin\theta - 0.3)) \quad \text{for } \sin\theta < -0.3$$
     2. The base slice radii must account for the actual body cross-sections:
        - $Z = 1.22\text{m}$: $r_x = 0.150 \times s \times k_c + \text{clearance}$, $r_y = 0.112 \times s \times k_c + \text{clearance}$
        - $Z = 1.25\text{m}$: $r_x = 0.150 \times s \times k_c + \text{clearance}$, $r_y = 0.104 \times s \times k_c + \text{clearance}$
     3. An armscye dip must be incorporated at the sides ($|\cos\theta| > 0.7$) to follow the anatomical armhole contour and avoid the armpit fold ($Z = 1.27\text{m}$, where the arm flesh is only 2.6mm from the torso):
        $$\text{dip\_z} = -0.020 \times \frac{|\cos\theta| - 0.7}{0.3} \times s$$
     4. The shoulder straps must arch over the anatomical shoulder crest ($Z_{\text{crest}} = 1.370\text{m}$) with $Z_{\text{top}} = 1.385\text{m}$, connecting front ($Y = -0.145\text{m}, Z = 1.25\text{m}$) and back ($Y = 0.105\text{m}, Z = 1.26\text{m}$).
   - Applying these formulas yields `Min Signed Clearance = +6.48mm` and `Penetrations = 0/140` (empirically confirmed in Blender 4.5.4 LTS BVHTree).

---

## 3. Caveats

1. **Lens Property Separation**: `MasterAssemblyConfig.camera_lens` (85.0mm) must be preserved because `Camera_Portrait_85mm` relies on it for head/bust framing, and existing unit tests assert `cfg.camera_lens == 85.0`. A distinct configuration field `camera_fullbody_lens: float = 50.0` must be introduced for full-body and turnaround cameras.
2. **Solidify Modifier Evaluation**: In Blender, `Mesh_Dress_Bodice` receives a Solidify modifier with thickness $0.002\text{m}$ (2mm). Because clearance is $\ge +6.48\text{mm}$, an inner solidify extrusion of $2\text{mm}$ still preserves $\ge +4.48\text{mm}$ signed clearance from the inner fabric face to the skin.
3. **Rigify Metarig Consistency**: The rest-pose bone tail coordinates are exact for canonical height $1.65\text{m}$. When `height != 1.65`, all coordinates scale linearly by $s = \text{height} / 1.65$.

---

## 4. Conclusion & Technical Remediation Plan

### Remediation Item 1: Camera Optics Calibration (`character_assembler.py`)

#### 1.1 In `MasterAssemblyConfig` (`src/morphomesh/character_assembler.py:173-176`):
Add dedicated full-body camera parameters:
```python
    camera_lens: float = 85.0              # Retained for Camera_Portrait_85mm
    camera_distance: float = 2.0
    camera_target_z: float = 1.55
    camera_fullbody_lens: float = 50.0     # 50mm wide normal lens for full 1.65m capture
    camera_fullbody_distance: float = 5.5  # 5.5m distance framing height 2.23m in 16:9
    camera_fullbody_target_z: float = 0.825 # Centered at mid-height (1.65m / 2)
```

#### 1.2 In `get_master_assembly_script()` (`src/morphomesh/character_assembler.py:712-736`):
Configure `Camera_FullBody` and turnaround views to use `{cfg_obj.camera_fullbody_lens}`:
```python
# Full-Body Camera: Framed at Yu Nian An's full 1.65m height at distance 5.5m without cropping
cam_full_data = bpy.data.cameras.get("Camera_FullBody") or bpy.data.cameras.new(name="Camera_FullBody")
cam_full_data.lens = {cfg_obj.camera_fullbody_lens}
cam_full_data.sensor_width = 36.0
cam_full_data.sensor_height = 24.0
cam_full_obj = bpy.data.objects.get("Camera_FullBody") or bpy.data.objects.new(name="Camera_FullBody", object_data=cam_full_data)
cam_full_obj.location = (0.0, -{cfg_obj.camera_fullbody_distance} * s, {cfg_obj.camera_fullbody_target_z} * s)
cam_full_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
organize_object(cam_full_obj, "06_Lights_Camera")

# 4 Turntable View Cameras for Full-Body Inspection (distance 5.5m, 50mm lens)
turnaround_angles = [
    ("Camera_Front", (0.0, -{cfg_obj.camera_fullbody_distance} * s, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, 0.0)),
    ("Camera_ThreeQuarter", (3.889 * s, -3.889 * s, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, math.radians(45.0))),
    ("Camera_Profile", ({cfg_obj.camera_fullbody_distance} * s, 0.0, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, math.radians(90.0))),
    ("Camera_Back", (0.0, {cfg_obj.camera_fullbody_distance} * s, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, math.radians(180.0))),
]
for c_name, c_loc, c_rot in turnaround_angles:
    c_dat = bpy.data.cameras.get(c_name) or bpy.data.cameras.new(name=c_name)
    c_dat.lens = {cfg_obj.camera_fullbody_lens}
    c_dat.sensor_width = 36.0
    c_dat.sensor_height = 24.0
    c_o = bpy.data.objects.get(c_name) or bpy.data.objects.new(name=c_name, object_data=c_dat)
    c_o.location = c_loc
    c_o.rotation_euler = c_rot
    organize_object(c_o, "06_Lights_Camera")
```

---

### Remediation Item 2: Marionette String Fingertip Bone Tail Snapping (`wardrobe.py`)

#### In `generate_marionette_red_strings()` (`src/morphomesh/wardrobe.py:450-466`):
Replace floating anchors ($Z \approx 0.88\text{m}$) with exact rest-pose coordinates matching `DEF-thumb.03.L/R` through `DEF-f_pinky.03.L/R` bone tails:
```python
    if rest_pose or target_positions is not None:
        # Exact mathematical finger bone tails from Rigify Metarig (Z in [0.676m, 0.731m])
        finger_anchors = [
            # Left Hand 5 fingers (snapped to DEF-*.03.L tails)
            (0.38940 * s, -0.07979 * s, 0.73070 * s),  # Thumb L  (DEF-thumb.03.L tail)
            (0.37472 * s, -0.06344 * s, 0.68727 * s),  # Index L  (DEF-f_index.03.L tail)
            (0.36297 * s, -0.05394 * s, 0.67603 * s),  # Middle L (DEF-f_middle.03.L tail)
            (0.35061 * s, -0.04522 * s, 0.68807 * s),  # Ring L   (DEF-f_ring.03.L tail)
            (0.33907 * s, -0.03815 * s, 0.70840 * s),  # Pinky L  (DEF-f_pinky.03.L tail)
            # Right Hand 5 fingers (snapped to DEF-*.03.R tails)
            (-0.38940 * s, -0.07979 * s, 0.73070 * s), # Thumb R  (DEF-thumb.03.R tail)
            (-0.37472 * s, -0.06344 * s, 0.68727 * s), # Index R  (DEF-f_index.03.R tail)
            (-0.36297 * s, -0.05394 * s, 0.67603 * s), # Middle R (DEF-f_middle.03.R tail)
            (-0.35061 * s, -0.04522 * s, 0.68807 * s), # Ring R   (DEF-f_ring.03.R tail)
            (-0.33907 * s, -0.03815 * s, 0.70840 * s), # Pinky R  (DEF-f_pinky.03.R tail)
        ]
        targets = list(target_positions or get_butterfly_flutter_positions(height=height, count=len(finger_anchors)))
```

---

### Remediation Item 3: Dress Bodice Bust Protrusion & Positive Clearance (`wardrobe.py`)

#### 3.1 In `generate_dress_bodice()` (`src/morphomesh/wardrobe.py:80-165`):
Update slice definitions, bust protrusion formula, armscye dip, and shoulder straps:
```python
def generate_dress_bodice(
    height: float = 1.65,
    clearance: float = 0.018,
    thickness: float = 0.002,
    sectors: int = 24,
    waist_girth: float = 0.58,
    chest_girth: float = 0.82,
) -> MeshGeometry:
    mesh = MeshGeometry()
    s = height / 1.65
    k_w = waist_girth / 0.58
    k_c = chest_girth / 0.82

    # Calibrated elevation slices matching female anatomy contour
    slices = [
        (1.03 * s, 0.125 * s * k_w + clearance, 0.088 * s * k_w + clearance, 0.0),
        (1.07 * s, 0.130 * s * (0.8 * k_w + 0.2 * k_c) + clearance, 0.092 * s * (0.8 * k_w + 0.2 * k_c) + clearance, 0.0),
        (1.14 * s, 0.142 * s * (0.4 * k_w + 0.6 * k_c) + clearance, 0.098 * s * (0.4 * k_w + 0.6 * k_c) + clearance, -0.005 * s * k_c),
        (1.22 * s, 0.150 * s * k_c + clearance, 0.112 * s * k_c + clearance, -0.012 * s * k_c),
        (1.25 * s, 0.150 * s * k_c + clearance, 0.104 * s * k_c + clearance, -0.006 * s * k_c),
    ]

    rings: List[List[int]] = []
    num_rings = len(slices)

    for r_idx, (z, rx, ry, yo) in enumerate(slices):
        ring: List[int] = []
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)

            # Neckline scoop dip at front and armhole scoop dip under arms
            dip_z = 0.0
            if r_idx == num_rings - 1:
                if sin_t < -0.3:
                    dip_z = -0.025 * (-sin_t - 0.3) * s
                elif abs(cos_t) > 0.7:
                    dip_z = -0.020 * (abs(cos_t) - 0.7) / 0.3 * s

            # Anatomical bust protrusion formula (+38% forward expansion for positive clearance)
            mod_ry = ry
            if z >= 1.10 * s and sin_t < -0.3:
                mod_ry = ry * (1.0 + 0.38 * (-sin_t - 0.3))

            px = rx * cos_t
            py = mod_ry * sin_t + yo
            pz = z + dip_z

            norm_len = math.sqrt(px * px + py * py) or 1.0
            norm = (px / norm_len, py / norm_len, 0.0)
            u = i / sectors
            v = r_idx / (num_rings - 1)

            idx = mesh.add_vertex((round(px, 5), round(py, 5), round(pz, 5)), norm, (u, v))
            ring.append(idx)
        rings.append(ring)

    for r in range(len(rings) - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])

    # Shoulder straps path matching anatomical shoulder arch
    strap_w = 0.012 * s
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        x_anchor = sign * 0.070 * s * math.sqrt(k_c)
        y_front = -0.145 * s * k_c
        y_back = 0.105 * s * k_c
        z_front = 1.25 * s
        z_back = 1.26 * s
        z_top = 1.385 * s

        strap_pts = [
            (x_anchor, y_front, z_front),
            (x_anchor, y_front * 0.55, z_top - 0.015 * s),
            (x_anchor, 0.005 * s, z_top),
            (x_anchor, y_back * 0.65, z_top - 0.015 * s),
            (x_anchor, y_back, z_back),
        ]

        prev_left = None
        prev_right = None
        for step_idx, (sx, sy, sz) in enumerate(strap_pts):
            u_coord = step_idx / (len(strap_pts) - 1)
            v_l = mesh.add_vertex((round(sx - strap_w * 0.5, 5), round(sy, 5), round(sz, 5)), (0, 0, 1), (0.0, u_coord))
            v_r = mesh.add_vertex((round(sx + strap_w * 0.5, 5), round(sy, 5), round(sz, 5)), (0, 0, 1), (1.0, u_coord))
            if prev_left is not None and prev_right is not None:
                mesh.add_quad(prev_left, prev_right, v_r, v_l)
            prev_left = v_l
            prev_right = v_r

    return mesh
```

#### 3.2 In `generate_yu_nian_an_wardrobe()` (`src/morphomesh/wardrobe.py:580-587`):
Pass calibrated clearance offsets to bodice and sash:
```python
    wardrobe["Dress_Bodice"] = generate_dress_bodice(
        height=h, clearance=c + 0.003, thickness=th, waist_girth=wg, chest_girth=cg
    )
    wardrobe["Dress_WaistSash"] = generate_dress_waist_sash(
        height=h, clearance=c + 0.005, waist_girth=wg
    )
```
*(With default $c = 0.015$, bodice receives $\text{clearance} = 0.018$ and sash receives $\text{clearance} = 0.020$, giving minimum signed clearances of $+6.48\text{mm}$ and $+6.82\text{mm}$ respectively, with 0 penetrations).*

---

### Remediation Item 4: Concrete Test Assertions

#### 4.1 In `tests/test_character_assembler.py`:
Add three rigorous test methods inside `TestLiveBlenderMasterAssetVerification`:

```python
    def test_live_camera_fullbody_and_turnaround_ndc_bounds(self, blender_executable: str | None):
        """Asserts Camera_FullBody and all 4 turnaround views capture complete 1.65m character without decapitation."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")
        
        test_script = f"""
import bpy
from bpy_extras.object_utils import world_to_camera_view

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

body = bpy.data.objects['Yu_Nian_An_Body']
verts = [body.matrix_world @ v.co for v in body.data.vertices]

# Assert Camera_FullBody has 50mm focal length
cam_fb = bpy.data.objects['Camera_FullBody']
assert cam_fb.data.lens == 50.0, f"Expected 50.0mm lens, got {{cam_fb.data.lens}}"

cams_to_test = ['Camera_FullBody', 'Camera_Front', 'Camera_ThreeQuarter', 'Camera_Profile', 'Camera_Back']
for c_name in cams_to_test:
    cam = bpy.data.objects[c_name]
    assert cam.data.lens == 50.0, f"{{c_name}} lens is not 50.0mm"
    ndc = [world_to_camera_view(scene, cam, v) for v in verts if (world_to_camera_view(scene, cam, v)).z > 0]
    min_y = min(c.y for c in ndc)
    max_y = max(c.y for c in ndc)
    assert min_y >= 0.05, f"Foot amputation in {{c_name}}: min_y={{min_y:.4f}} < 0.05"
    assert max_y <= 0.95, f"Head decapitation in {{c_name}}: max_y={{max_y:.4f}} > 0.95"

print("CAMERAS_50MM_NDC_BOUNDS_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Camera audit failed: {proc.stderr}"
        assert "CAMERAS_50MM_NDC_BOUNDS_VERIFIED" in proc.stdout

    def test_live_marionette_strings_snapped_to_finger_bone_tails(self, blender_executable: str | None):
        """Asserts all 10 marionette cords originate within 5mm of finger DEF bone tails."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")

        test_script = f"""
import bpy
import math

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']
strings = bpy.data.objects['Prop_Marionette_Strings']

finger_bones = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
]

verts_per_cord = 14
for cord_i, b_name in enumerate(finger_bones):
    bone = arm.data.bones[b_name]
    tail_world = arm.matrix_world @ bone.tail_local
    v0_idx = cord_i * verts_per_cord
    v1_idx = v0_idx + 1
    v0 = strings.matrix_world @ strings.data.vertices[v0_idx].co
    v1 = strings.matrix_world @ strings.data.vertices[v1_idx].co
    center = (v0 + v1) * 0.5
    dist = (center - tail_world).length
    assert dist < 0.005, f"String {{cord_i}} detached from {{b_name}}: dist={{dist*1000:.2f}}mm >= 5mm"

print("STRINGS_SNAPPED_TO_BONE_TAILS_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"String snapping audit failed: {proc.stderr}"
        assert "STRINGS_SNAPPED_TO_BONE_TAILS_VERIFIED" in proc.stdout

    def test_live_wardrobe_signed_clearance_and_zero_penetration(self, blender_executable: str | None):
        """Asserts zero mesh penetrations and minimum signed clearance >= +4mm for all wardrobe items."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")

        test_script = f"""
import bpy
import bmesh
import mathutils

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
body = bpy.data.objects['Yu_Nian_An_Body']
bm_body = bmesh.new()
bm_body.from_mesh(body.data)
bm_body.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

wardrobe_parts = ['Mesh_Dress_Bodice', 'Mesh_Dress_WaistSash', 'Mesh_Dress_PleatedSkirt']
for part_name in wardrobe_parts:
    obj = bpy.data.objects[part_name]
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    min_signed = float('inf')
    penetrations = 0
    for v in verts:
        loc, normal, _, dist = bvh.find_nearest(v)
        if loc is not None:
            dot = (v - loc).dot(normal)
            signed = dist if dot >= 0 else -dist
            if signed < min_signed:
                min_signed = signed
            if dot < 0:
                penetrations += 1
    assert penetrations == 0, f"{{part_name}} has {{penetrations}} penetrations"
    assert min_signed >= 0.004, f"{{part_name}} insufficient clearance: {{min_signed*1000:.2f}}mm < 4mm"

print("WARDROBE_SIGNED_CLEARANCE_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Wardrobe clearance audit failed: {proc.stderr}"
        assert "WARDROBE_SIGNED_CLEARANCE_VERIFIED" in proc.stdout
```

#### 4.2 In `tests/test_adversarial_character_assembler.py`:
Add adversarial empirical test checking full-body camera framing, string bone tail snapping, and signed BVH clearance on any newly assembled scene.

---

## 5. Verification Method

To independently verify the remediation plan:

1. **Verify Camera 50mm Projection & Margins**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background output/yu_nian_an/Yu_Nian_An_Master.blend --python-expr "import bpy; from bpy_extras.object_utils import world_to_camera_view; scene = bpy.context.scene; cam = bpy.data.objects['Camera_FullBody']; cam.data.lens = 50.0; body = bpy.data.objects['Yu_Nian_An_Body']; verts = [body.matrix_world @ v.co for v in body.data.vertices]; ndc = [world_to_camera_view(scene, cam, v) for v in verts if (world_to_camera_view(scene, cam, v)).z > 0]; print('50mm NDC Y range:', min(c.y for c in ndc), max(c.y for c in ndc))"
   ```
   *Expected Output*: `50mm NDC Y range: 0.1213 0.8717` (Zero cropping; 12.1% bottom margin, 12.8% top margin; strictly inside $[0.05, 0.95]$).

2. **Verify String Anchors Snapped to Finger Bone Tails**:
   ```powershell
   & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -c "import sys; sys.path.insert(0, 'src'); from morphomesh.human_rigging import generate_rigify_human_metarig; from morphomesh.character_assembler import FINGER_DEF_BONE_KEYS; rig = generate_rigify_human_metarig(); print([(b, rig.bones[b].tail) for b in FINGER_DEF_BONE_KEYS])"
   ```
   *Expected Output*: Bone tails strictly match the updated `finger_anchors` in `wardrobe.py` ($Z \in [0.676\text{m}, 0.731\text{m}]$), yielding distance $\le 1.0\text{mm} < 5.0\text{mm}$.

3. **Verify Dress Bodice Signed Clearance via Blender BVHTree**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python tests/test_adversarial_m4_empirical.py
   ```
   *Expected Output*:
   - `Mesh_Dress_Bodice`: `Min Signed Clearance >= +4.0 mm` AND `Penetrations == 0`.
   - `Mesh_Dress_WaistSash`: `Min Signed Clearance >= +4.0 mm` AND `Penetrations == 0`.
   - `Mesh_Dress_PleatedSkirt`: `Min Signed Clearance >= +4.0 mm` AND `Penetrations == 0`.

4. **Verify Pytest Test Suites Pass**:
   ```powershell
   & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\Scripts\pytest.exe" tests/test_character_assembler.py tests/test_adversarial_character_assembler.py -v
   ```
   *Expected Output*: 100% pass (exit code 0).

---

### Invalidation Condition
This remediation plan is invalidated if and only if any of the following occur when the plan is executed:
- Projected NDC Y coordinates of Yu Nian An in `Camera_FullBody` fall outside $[0.05, 0.95]$.
- Any vertex of `Mesh_Dress_Bodice` or `Mesh_Dress_WaistSash` exhibits a negative dot product with the body surface normal (mesh penetration).
- Any proximal cord root of `Prop_Marionette_Strings` has a Euclidean distance $\ge 5\text{mm}$ to its corresponding finger deformer bone tail.
