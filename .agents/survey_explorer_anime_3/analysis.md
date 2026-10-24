# Technical Investigation & Architectural Blueprint: Anime Animation & Toon Shading Pipeline (R3 & R4)

**Explorer**: `survey_explorer_anime_3`  
**Milestone**: Anime Character Pipeline Survey & Architecture Specification (R3 & R4)  
**Authoritative Reference**: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\ORIGINAL_REQUEST.md`  
**Environment Verified**: Blender 4.5.4 LTS (`C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`), Python 3.11/NumPy 2.4.6, FFmpeg/FFprobe 9.0.1  
**Timestamp**: 2026-09-09T14:55:00Z  

---

## 1. Executive Summary & Problem Formulation

In anime 3D character production (VTuber / Game-Ready standard), standard realistic 3D pipelines fail catastrophically in two major domains:
1. **Animation & Retargeting Distortion (R3)**:
   - Applying raw human motion capture (Mocap) or generic humanoid walk cycles (e.g., broad masculine strides) causes hideous distortions on anime proportions (larger head, slender limbs, narrow hips, high center of gravity).
   - Without dedicated rotational clamping, human mocap causes knee valgus collapse (knees bending inward), broken hyperextended elbows, rubbery noodle-twisting wrists, and severe shoe/ankle distortion.
   - Secondary elements (hair twintails, pleated skirts) clip violently through the body or remain stiff and lifeless.
2. **Shading & Rendering Failure (R4)**:
   - Standard PBR (Physically Based Rendering) shaders produce an "uncanny plastic doll" or "greasy oily rubber" appearance on anime characters, characterized by muddy grey shadows and specular hotspots across the cheeks and forehead.
   - Traditional screen-space post-processing edge detectors (Freestyle) are slow, flicker during camera motion, and fail in headless real-time pipelines.
   - Photographic camera lenses (wide-angle < 35mm) produce perspective distortion ("fish-eye") that flattens or warps delicate anime face topology.

This document provides the complete technical architecture, mathematical specifications, shader node graph blueprints, and automated verification mechanics to satisfy **R3** and **R4** in Blender 4.5.4 LTS.

---

## 2. Technical Blueprint for R3: Anime Animation & Retargeting

### 2.1 Anime Aesthetic Motion Principles
Anime animation adheres to strict aesthetic conventions that diverge fundamentally from realistic human motion capture:
- **Narrow Stance & Center-Line Locomotion**: Feet track along a narrow center line (avoiding wide cowboy or athletic strides).
- **Contrapposto Weight Shifting**: In resting/idle poses, 80-90% of body weight rests on a single "supporting leg" (hips tilted 4°–8° laterally), while the "free leg" relaxes forward with knee slightly bent.
- **Cute Head Tilt & Delayed Gaze**: The head tilts 3°–6° towards the lowered shoulder or opposite the dominant hip, trailing the torso movement by 2–4 frames.
- **Arm Rest & Graceful Forearm Angles**: Arms are tucked close to the torso, wrists flexed gracefully, avoiding flailing elbows.
- **Secondary Spring Motion**: Twintails and pleated skirts exhibit reactive lag (spring-damper harmonic oscillation) responding to root acceleration.

---

### 2.2 Programmatic Animation Library: Four Core Anime Actions

Each action is designed as an independent Blender `Action` data-block operating in 30 FPS timeline.

#### Action 1: `action_anime_idle_cute` (Looping, 90 Frames / 3.0 Seconds)
- **Timeline & Cadence**: 90-frame seamless loop (Frame 1 == Frame 91).
- **Contrapposto Base Pose**:
  - `Hips`: Shifted +0.035m laterally to the right ($X = +0.035$), rotated roll $Z = -4.5^\circ$, yaw $Y = +2.0^\circ$.
  - `RightUpLeg` (Support): Straight, bearing load, slight outward rotation (+2°).
  - `LeftUpLeg` (Free): Relaxed, knee flexed forward (flexion $X = 8.0^\circ$), toe rested lightly on floor.
  - `Spine` / `Chest`: Counter-tilt roll $Z = +3.5^\circ$ to maintain vertical balance of torso over supporting foot.
- **Breathing & Subtle Sway Cycle**:
  - `Spine1` / `Chest` Pitch ($X$): Sinusoidal breathing curve $\theta_X(t) = 1.5^\circ \cdot \sin(2\pi \cdot \frac{t}{90})$.
  - `Hips` Vertical Bob ($Z$): $Z(t) = Z_0 + 0.006 \cdot \sin(2\pi \cdot \frac{t}{45})$ (2 micro-bobs per breath).
  - `Head` Tilt ($Z$): Gentle tilt $\theta_Z(t) = 4.0^\circ + 1.2^\circ \cdot \sin(2\pi \cdot \frac{t}{90} - \frac{\pi}{4})$ (delayed 11 frames).
- **Cute Arm Placement**:
  - Left arm: Hand resting lightly on upper thigh/skirt edge (`LeftArm`: flexion $18^\circ$, adduction $12^\circ$; `LeftForeArm`: flexion $38^\circ$).
  - Right arm: Bent cutely near chest/collarbone (`RightArm`: flexion $25^\circ$, adduction $18^\circ$; `RightForeArm`: flexion $65^\circ$, wrist gentle pitch).
- **Secondary Spring Oscillations**:
  - `Hair_Twin_L_01..03`: Pendulum lag $\theta(t) = -0.6 \cdot \theta_{\text{head}}(t - 3)$.
  - `Skirt_F / Skirt_B`: Gentle harmonic sway matching hip breathing cycle.

#### Action 2: `action_anime_wave_greeting` (120 Frames / 4.0 Seconds)
- **Phase 1: Weight Shift & Recognition (Frames 1–25)**:
  - Weight shifts actively onto left hip, torso leans slightly forward (pitch $X = +3^\circ$).
  - Head turns towards camera/audience (yaw $Y = -6^\circ$, tilt $Z = +5^\circ$).
  - Right shoulder raises (`RightShoulder`: elevation $+6^\circ$).
- **Phase 2: Arm Raise & Hand Preparation (Frames 26–45)**:
  - `RightArm`: Raises rapidly to shoulder height (elevation $X = 75^\circ$, outward abduction $Y = 35^\circ$).
  - `RightForeArm`: Flexes sharply to $95^\circ$, bringing the palm beside the cheek.
  - `RightHand`: Opens wide, fingers spread gracefully (Thumb abducted, Index–Pinky extended).
- **Phase 3: Energetic Waving Oscillation (Frames 46–95)**:
  - 3 complete waving cycles (16 frames per cycle):
    - `RightForeArm` Roll / Twist ($Y$): Oscillates $\pm 18^\circ$ at frequency $f = \frac{30}{16} = 1.875\text{ Hz}$.
    - `RightHand` Wrist Yaw ($Z$): Oscillates $\pm 15^\circ$, leading the forearm by 2 frames.
    - `Head`: Bobs happily in sync with wave peaks ($\Delta Z = \pm 0.008\text{m}$, tilt $\pm 2^\circ$).
- **Phase 4: Settle & Recovery (Frames 96–120)**:
  - Arm lowers gracefully with smooth ease-out back to cute rest pose.

#### Action 3: `action_anime_walk_cycle` (Looping, 32 Frames / 1.07 Seconds)
- **Cadence**: 32 frames per 2-step cycle (16 frames per step).
- **Narrow Foot Placement**:
  - Feet step along a narrow line with lateral separation $\le 0.08\text{m}$ (tight feminine tracking).
  - Toe angle: Slightly pigeon-toed / neutral (inward toe rotation $Z = +1.5^\circ$ on contact).
- **Vertical Bounce & Hip Mechanics**:
  - Contact phase (Frames 0, 16): Hips at neutral height $Z_0$, legs extended.
  - Down phase (Frames 4, 20): Maximum compression, Hips sink by $-0.032\text{m}$, knee flexes to $25^\circ$.
  - Passing phase (Frames 8, 24): Hips rise to $+0.025\text{m}$ (bouncy spring off the ball of the foot).
  - Pelvic Yaw ($Y$) & Roll ($Z$):
    - Pelvis rolls $+4^\circ$ towards the supporting leg at contact.
    - Pelvis yaws $+6^\circ$ following the advancing leg.
    - Thorax/Shoulders counter-rotate $-4^\circ$ to maintain aesthetic balance.
- **Arm Cadence & Forearm Bend**:
  - Arm swing is subtle and held close to the ribs:
    - `LeftArm`: Swing amplitude $\pm 18^\circ$ (counter to left leg).
    - `LeftForeArm`: Kept bent at $35^\circ$–$45^\circ$, never swinging straight down like a soldier.
- **Pleated Skirt & Hair Dynamics**:
  - Skirt bones follow leg advance with forward swing on stepping side, flared outward by $+8^\circ$ to clear thigh mesh.
  - Twintails bounce vertically with a 3-frame lag behind the hip vertical curve.

#### Action 4: `action_anime_jump_cheer` (75 Frames / 2.5 Seconds)
- **Phase 1: Anticipation Squash (Frames 1–18)**:
  - Hips lower by $-0.14\text{m}$, knees bend deeply to $65^\circ$, torso leans forward ($X = +18^\circ$).
  - Arms swing back behind the body (`Arm` pitch $-35^\circ$, hands curled).
- **Phase 2: Explosive Launch (Frames 19–28)**:
  - Rapid upward impulse: Hips accelerate upward to $+0.35\text{m}$.
  - Feet push off floor, ankles extend fully (plantar flexion $-40^\circ$), toes point downward.
  - Arms swing triumphantly overhead (`Arm` pitch $+145^\circ$, elbows bent $+30^\circ$, fists clenched).
- **Phase 3: Joyful Apex & Bent-Knee "Anime Hop" (Frames 29–42)**:
  - Both knees bend backward cutely (`Leg` flexion $85^\circ$), feet kicked back behind the hips.
  - Chest arches open toward the sky ($X = -12^\circ$), head looks up cheerfully ($X = -15^\circ$).
  - Twintails flare upwards due to upward inertia ($+45^\circ$).
- **Phase 4: Landing Compression (Frames 43–58)**:
  - Balls of feet touch ground first at frame 44.
  - Hips sink to $-0.10\text{m}$ to cushion impact, knees flex to $55^\circ$.
  - Arms lower to shoulder height to balance.
- **Phase 5: Joyful Settle (Frames 59–75)**:
  - Spring back to upright standing posture with cheerful hip sway.

---

### 2.3 Retargeting Architecture, NLA Blending & Rotational Clamping

#### Humanoid Bone Mapping Matrix (VRM / MMD / Rigify / Mixamo Standard)
| Standard Canonical Name | Blender glTF/Meshy Bone | Rigify DEF Bone | MMD Japanese / English | Role / Constraint |
|---|---|---|---|---|
| `Hips` | `Hips` | `DEF-spine` | センター / Center | Root motion & pelvic rotation |
| `Spine` | `Spine` | `DEF-spine.001` | 脊椎 / Spine | Lower torso flexion |
| `Spine1` (Chest) | `Spine01` / `Spine1` | `DEF-spine.002` | 上半身 / Upper Body | Breathing & counter-tilt |
| `Spine2` (UpperChest) | `Spine02` / `Spine2` | `DEF-spine.003` | 上半身2 / Upper Body 2 | Collarbone support |
| `Neck` | `neck` / `Neck` | `DEF-spine.004` | 首 / Neck | Head support |
| `Head` | `Head` | `DEF-spine.005` | 頭 / Head | Gaze & tilt |
| `LeftShoulder` | `LeftShoulder` | `DEF-shoulder.L` | 左肩 / Left Shoulder | Clavicle elevation/shrug |
| `LeftArm` | `LeftArm` | `DEF-upper_arm.L` | 左腕 / Left Arm | Shoulder ball-joint |
| `LeftArm_Twist` | `LeftArm_Twist` | `DEF-upper_arm_twist.L` | 左腕捩 / Left Arm Twist | 50% twist distribution |
| `LeftForeArm` | `LeftForeArm` | `DEF-forearm.L` | 左ひじ / Left Elbow | 1-DOF Hinge (Flexion only) |
| `LeftForeArm_Twist` | `LeftForeArm_Twist` | `DEF-forearm_twist.L` | 左手捩 / Left Wrist Twist | Eliminates candy-wrapper |
| `LeftHand` | `LeftHand` | `DEF-hand.L` | 左手首 / Left Wrist | Wrist pitch/yaw |
| `Thumb01..03_L` | `Thumb0..2_L` | `DEF-thumb.01..03.L` | 左親指１〜３ | Thumb opposition & grasp |
| `Index01..03_L` | `Index1..3_L` | `DEF-f_index.01..03.L` | 左人指１〜３ | Pointing / relaxed splay |
| `Middle01..03_L` | `Middle1..3_L` | `DEF-f_middle.01..03.L` | 左中指１〜３ | Hand silhouette balance |
| `Ring01..03_L` | `Ring1..3_L` | `DEF-f_ring.01..03.L` | 左薬指１〜３ | Grasp alignment |
| `Pinky01..03_L` | `Pinky1..3_L` | `DEF-f_pinky.01..03.L` | 左小指１〜３ | Cute anime finger flair |
| `LeftUpLeg` | `LeftUpLeg` | `DEF-thigh.L` | 左足 / Left Leg | Thigh rotation |
| `LeftLeg` | `LeftLeg` | `DEF-shin.L` | 左ひざ / Left Knee | 1-DOF Hinge (Backwards only) |
| `LeftFoot` | `LeftFoot` | `DEF-foot.L` | 左足首 / Left Ankle | Ground leveling |
| `LeftToeBase` | `LeftToeBase` | `DEF-toe.L` | 左つま先 / Left Toe | Ground contact & toe-off |
| `Hair_Front / Twin_L/R` | `Hair_*` | Custom DEF chains | 髪 / Hair bones | Secondary spring motion |
| `Skirt_Root / Radial` | `Skirt_*` | Custom DEF chains | スカート / Skirt bones | Leg collision avoidance |

#### Bone Rotation Limit Matrix (`LIMIT_ROTATION` Constraints in Pose Mode)
To eliminate grotesque mocap distortions, the following constraints must be assigned programmatically to pose bones:
```python
ROTATION_LIMITS = {
    "LeftForeArm": {
        "use_limit_x": True, "min_x": math.radians(0), "max_x": math.radians(145), # Strict hinge flexion
        "use_limit_y": True, "min_y": math.radians(-15), "max_y": math.radians(15), # Twist clamped (handled by twist bone)
        "use_limit_z": True, "min_z": math.radians(-5), "max_z": math.radians(5),   # Zero sideways hyperextension
    },
    "RightForeArm": {
        "use_limit_x": True, "min_x": math.radians(0), "max_x": math.radians(145),
        "use_limit_y": True, "min_y": math.radians(-15), "max_y": math.radians(15),
        "use_limit_z": True, "min_z": math.radians(-5), "max_z": math.radians(5),
    },
    "LeftLeg": {
        "use_limit_x": True, "min_x": math.radians(0), "max_x": math.radians(140), # Backward knee flexion only
        "use_limit_y": True, "min_y": math.radians(-3), "max_y": math.radians(3),   # Prevent valgus knee collapse
        "use_limit_z": True, "min_z": math.radians(-3), "max_z": math.radians(3),   # Prevent sideways knee dislocation
    },
    "RightLeg": {
        "use_limit_x": True, "min_x": math.radians(0), "max_x": math.radians(140),
        "use_limit_y": True, "min_y": math.radians(-3), "max_y": math.radians(3),
        "use_limit_z": True, "min_z": math.radians(-3), "max_z": math.radians(3),
    },
    "LeftFoot": {
        "use_limit_x": True, "min_x": math.radians(-45), "max_x": math.radians(30),
        "use_limit_y": True, "min_y": math.radians(-8), "max_y": math.radians(8),   # Keep sole flat
        "use_limit_z": True, "min_z": math.radians(-10), "max_z": math.radians(10), # Prevent inward shoe bend
    },
    "RightFoot": {
        "use_limit_x": True, "min_x": math.radians(-45), "max_x": math.radians(30),
        "use_limit_y": True, "min_y": math.radians(-8), "max_y": math.radians(8),
        "use_limit_z": True, "min_z": math.radians(-10), "max_z": math.radians(10),
    },
    "LeftToeBase": {
        "use_limit_x": True, "min_x": math.radians(-5), "max_x": math.radians(45),  # Bending up during step
        "use_limit_y": True, "min_y": math.radians(-2), "max_y": math.radians(2),
        "use_limit_z": True, "min_z": math.radians(-2), "max_z": math.radians(2),
    },
    "RightToeBase": {
        "use_limit_x": True, "min_x": math.radians(-5), "max_x": math.radians(45),
        "use_limit_y": True, "min_y": math.radians(-2), "max_y": math.radians(2),
        "use_limit_z": True, "min_z": math.radians(-2), "max_z": math.radians(2),
    }
}
```

#### NLA (Non-Linear Animation) Stacking Architecture
Blender's NLA system allows seamless blending between actions without destructively baking keyframes:
1. **Track 0 (`NLA_Base_Idle`)**:
   - Holds `action_anime_idle_cute` with `extrapolation = 'HOLD_FORWARD'`, looping continuously.
2. **Track 1 (`NLA_Action_Overlay`)**:
   - Holds performance actions (`action_anime_wave_greeting` or `action_anime_jump_cheer`).
   - `blend_mode = 'REPLACE'`.
   - `blend_in = 12.0` frames (smooth s-curve transition into greeting).
   - `blend_out = 15.0` frames (smooth settle back into idle pose).
3. **Track 2 (`NLA_Additive_Secondary`)**:
   - Holds secondary procedural breathing or wind sway (`blend_mode = 'ADD'`).

---

## 3. Technical Blueprint for R4: Cel-Shading & Cinematic Video Rendering

### 3.1 Blender 4.5 EEVEE-Next Shading Architecture
In Blender 4.5 LTS, the EEVEE engine is upgraded to `BLENDER_EEVEE_NEXT`. The core cel-shading mechanism leverages:
- `ShaderNodeBsdfDiffuse`: Computes Lambertian dot-product irradiance $\mathbf{N} \cdot \mathbf{L}$.
- `ShaderNodeShaderToRGB`: Converts the internal light buffer radiance into an evaluable RGBA color vector.
- `ShaderNodeValToRGB` (ColorRamp): Stepped quantization converting smooth irradiance gradients into crisp 2-tone or 3-tone color bands.

---

### 3.2 Complete Shader Node Graphs

#### 1. Skin Cel-Shader (`M_Anime_Skin`)
- **Aesthetic Objective**: Smooth porcelain matte finish, warm peach/apricot shadow tint, zero oily specular gloss, subtle blush blending.
- **Node Tree Architecture**:
```
[Diffuse BSDF] (Color: Base Skin #FFF0E8)
       │ (BSDF)
       ▼
[Shader to RGB]
       │ (Color)
       ▼
[ColorRamp] (Interpolation: CONSTANT)
  ├─ Stop 0 (Pos: 0.00): Shadow Tint #E8A896 (Warm Apricot Peach)
  └─ Stop 1 (Pos: 0.38): Base Skin   #FFF0E8 (Porcelain Fair)
       │ (Color)
       ▼
[Mix Color] (Mode: MULTIPLY, Factor: Blush Mask Vertex Color)
       │ (Result)
       ▼
[Material Output] (Surface)
```
- **Blender 4.5 Python Construction**:
```python
def build_anime_skin_material():
    mat = bpy.data.materials.new(name="M_Anime_Skin")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Diffuse BSDF
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = (0.98, 0.90, 0.86, 1.0) # #FFF0E8
    diffuse.inputs["Roughness"].default_value = 0.0

    # Shader to RGB
    s2rgb = nodes.new("ShaderNodeShaderToRGB")

    # Stepped ColorRamp
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.88, 0.62, 0.55, 1.0) # Warm peach shadow
    ramp.color_ramp.elements[1].position = 0.35
    ramp.color_ramp.elements[1].color = (0.98, 0.90, 0.86, 1.0) # Base porcelain

    # Output
    output = nodes.new("ShaderNodeOutputMaterial")

    links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], output.inputs["Surface"])
    return mat
```

#### 2. Hair Cel-Shader with "Angel Ring" (`M_Anime_Hair`)
- **Aesthetic Objective**: Stylized anime hair with two-tone shading, vertical root-to-tip gradient, and a procedural horizontal specular highlight band ("Tenshi no Wa" / 天使の輪).
- **Node Tree Architecture**:
```
[Diffuse BSDF] (Hair Base Color)
       │
[Shader to RGB] ──► [ColorRamp: Cel Steps] (Shadow #1B224B -> Base #4A6FE3)
                           │
                           │ (A)
                           ▼
                 [Mix Color: ADD] ◄── [Light Gating Math: GREATER_THAN]
                           ▲                    ▲
                           │ (B)                │ (Fac from Diffuse)
             [ColorRamp: Angel Ring]            │
                           ▲                    │
                 [Separate XYZ: Z]              │
                           ▲                    │
             [Texture Coordinate: Object] ──────┘
                           │
                           ▼
                   [Material Output]
```
- **Blender 4.5 Python Construction**:
```python
def build_anime_hair_material(base_color=(0.35, 0.55, 0.95, 1.0), shadow_color=(0.18, 0.25, 0.55, 1.0)):
    mat = bpy.data.materials.new(name="M_Anime_Hair")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # 1. Base Diffuse Cel Shading
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = base_color
    s2rgb = nodes.new("ShaderNodeShaderToRGB")

    cel_ramp = nodes.new("ShaderNodeValToRGB")
    cel_ramp.color_ramp.interpolation = "CONSTANT"
    cel_ramp.color_ramp.elements[0].position = 0.0
    cel_ramp.color_ramp.elements[0].color = shadow_color
    cel_ramp.color_ramp.elements[1].position = 0.32
    cel_ramp.color_ramp.elements[1].color = base_color

    # 2. Angel Ring Procedural Specular Band
    tex_coord = nodes.new("ShaderNodeTexCoord")
    sep_xyz = nodes.new("ShaderNodeSeparateXYZ")

    ring_ramp = nodes.new("ShaderNodeValToRGB")
    ring_ramp.color_ramp.interpolation = "LINEAR"
    ring_ramp.color_ramp.elements[0].position = 0.50
    ring_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ring_ramp.color_ramp.elements[1].position = 0.56
    ring_ramp.color_ramp.elements[1].color = (0.85, 0.92, 1.0, 1.0) # High-value highlight
    e_close = ring_ramp.color_ramp.elements.new(0.62)
    e_close.color = (0.0, 0.0, 0.0, 1.0)

    # 3. Light Gating: Shine only on lit side
    math_gate = nodes.new("ShaderNodeMath")
    math_gate.operation = "GREATER_THAN"
    math_gate.inputs[1].default_value = 0.20

    ring_gated = nodes.new("ShaderNodeMix")
    ring_gated.data_type = "RGBA"
    ring_gated.blend_type = "MULTIPLY"
    ring_gated.inputs["Factor"].default_value = 1.0

    # 4. Final Composite
    mix_final = nodes.new("ShaderNodeMix")
    mix_final.data_type = "RGBA"
    mix_final.blend_type = "ADD"
    mix_final.inputs["Factor"].default_value = 0.75

    output = nodes.new("ShaderNodeOutputMaterial")

    # Links
    links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    links.new(s2rgb.outputs["Color"], cel_ramp.inputs["Fac"])
    links.new(tex_coord.outputs["Generated"], sep_xyz.inputs["Vector"])
    links.new(sep_xyz.outputs["Z"], ring_ramp.inputs["Fac"])

    links.new(s2rgb.outputs["Color"], math_gate.inputs[0])
    links.new(ring_ramp.outputs["Color"], ring_gated.inputs["A"])
    links.new(math_gate.outputs["Value"], ring_gated.inputs["B"])

    links.new(cel_ramp.outputs["Color"], mix_final.inputs["A"])
    links.new(ring_gated.outputs["Result"], mix_final.inputs["B"])
    links.new(mix_final.outputs["Result"], output.inputs["Surface"])
    return mat
```

#### 3. Clothing & Skirt Cel-Shader (`M_Anime_Cloth`)
- Crisp two-tone fabric shading with subtle Fresnel edge rim:
  - Base tone: Saturated uniform color (e.g. Navy Blue `#1A284F` or Pearl White `#F4F4F8`).
  - Shadow tone: Deep complementary indigo or cool grey-blue (`#0D152C`).
  - Fresnel rim: `Layer Weight` (Facing 0.85) -> `Emission` (Soft luminescence along cloth silhouette).

---

### 3.3 Inverted Hull Outline Technique
The Inverted Hull method is the industry standard for real-time anime outlines (used in *Guilty Gear*, *Genshin Impact*, *Hi-Fi Rush*):
1. **Modifier Stack Configuration**:
   - Add `SOLIDIFY` modifier to character mesh objects.
   - Position: **After** the Armature modifier (`deform_preserve_volume = True`).
   - Settings:
     - `thickness = -0.0035` (negative extrusion along vertex normals).
     - `offset = 1.0` (extrudes purely outward).
     - `use_flip_normals = True` (inverts generated shell normals so faces point inward).
     - `use_rim = False` (disables rim polygons connecting hull to base mesh).
     - `material_offset = outline_mat_slot_index`.
2. **Dedicated Unlit Outline Material (`M_Anime_Outline`)**:
   - `mat.use_backface_culling = True` (**CRITICAL**: Since normals are flipped, only back-facing triangles are rendered, creating a clean silhouette boundary from any camera angle!).
   - Node: `ShaderNodeEmission` with dark anime ink color (`#1E1616` or dark navy `#121422`), strength = 1.0.
   - Shadow mode: `NONE` (never casts shadows on character).

---

### 3.4 Cinematic Camera & Lighting Rig

#### Camera Specifications
- **Focal Length**: 55.0mm (full body) to 85.0mm (portrait closeup). Prevents anime face perspective distortion.
- **Sensor Size**: 36.0mm x 24.0mm (Full Frame 35mm standard).
- **Target Tracking**: `TRACK_TO` constraint targeting an Empty at character chest center ($Z = \text{height} \times 0.55$).

#### Dynamic Camera Motion Presets
1. **Preset A: 360° Full-Body Beauty Orbit**:
   - Radius $R = 3.2\text{m}$, elevation $Z = 1.15\text{m}$.
   - Smooth continuous orbit $\theta(t) = \frac{2\pi \cdot t}{T}$, capturing outfit silhouette and twintail hair flow.
2. **Preset B: Anime Dynamic Introduction (Cut-Shot Sequence)**:
   - *Shot 1 (Frames 1–40, Wide)*: Low-angle tracking shot ($Z = 0.35\text{m}$, lens 50mm, tilted up $+12^\circ$).
   - *Shot 2 (Frames 41–85, Medium)*: Front-right 45° angle at chest height showcasing wave greeting.
   - *Shot 3 (Frames 86–128, Close-Up Portrait)*: 85mm lens focused on face and sparkling anime eyes, gentle orbit.

#### 3-Point Anime Studio Lighting Rig
1. **Key Light (`Key_Light`)**:
   - Type: `AREA`, Size: 2.5m, Energy: 450.0W.
   - Color: Warm soft white `(1.0, 0.96, 0.92)`.
   - Position: Front-right (45° azimuth, 35° elevation).
2. **Anime Rim Light (`Rim_Light`)**:
   - Type: `AREA`, Size: 1.5m, Energy: 550.0W.
   - Color: Crisp golden/peach `(1.0, 0.90, 0.80)`.
   - Position: Directly behind character (145° azimuth, elevated behind head).
   - Produces the signature glowing hair rim and shoulder contour.
3. **Fill Light (`Fill_Light`)**:
   - Type: `AREA`, Size: 3.5m, Energy: 180.0W.
   - Color: Soft cool sky tint `(0.88, 0.94, 1.0)`.
   - Position: Front-left (fill in dark shadows without flattening cel-shading).

---

### 3.5 Headless Blender Render Export Pipeline
- **Command Line Execution**:
  ```bash
  "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b character_animated.blend --python render_pipeline.py -- --output final_anime_render.mp4 --resolution 1920 1080 --fps 30
  ```
- **Blender 4.5 Render Configuration**:
  ```python
  scene = bpy.context.scene
  scene.render.engine = 'BLENDER_EEVEE_NEXT'
  scene.render.resolution_x = 1920
  scene.render.resolution_y = 1080
  scene.render.resolution_percentage = 100
  scene.render.fps = 30

  # FFMPEG H.264 Video Settings
  scene.render.image_settings.file_format = 'FFMPEG'
  scene.render.ffmpeg.format = 'MPEG4'
  scene.render.ffmpeg.codec = 'H264'
  scene.render.ffmpeg.constant_rate_factor = 'HIGH'
  scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
  scene.render.ffmpeg.gopsize = 15
  scene.render.filepath = output_mp4_path

  # Color Management: Standard sRGB to preserve vibrant anime hues
  scene.display_settings.display_device = 'sRGB'
  scene.view_settings.view_transform = 'Standard'
  scene.view_settings.look = 'None'
  ```

---

## 4. Verification Mechanics & Audit Scripts Design

### 4.1 Rig Quality & Bone Completeness Audit Script Design (`verify_anime_rig.py`)

#### Verification Criteria:
1. **Humanoid Core Hierarchy**: Presence of `Hips`, `Spine`, `Spine1`, `Spine2`, `Neck`, `Head` with valid parenting chain.
2. **Complete 5-Finger Articulation**: Verification of 15 finger bones per hand (Thumb 1..3, Index 1..3, Middle 1..3, Ring 1..3, Pinky 1..3) = 30 finger bones total.
3. **Twist Bones**: Verification of `LeftArm_Twist`, `LeftForeArm_Twist`, `RightArm_Twist`, `RightForeArm_Twist` with active copy-rotation drivers.
4. **Secondary Dynamic Chains**:
   - Hair: At least 2 chains for twintails (`Hair_Twin_L_01..03`, `Hair_Twin_R_01..03`).
   - Skirt: At least 6–8 radial skirt bones parented to `Hips` or `Skirt_Root`.
5. **Non-Degenerate Bone Geometry**: All bone lengths $> 0.005\text{m}$.

#### Audit Script Specification:
```python
def audit_rig_structure(armature_obj: bpy.types.Object) -> dict:
    bones = {b.name: b for b in armature_obj.data.bones}
    report = {
        "status": "PASS",
        "total_bones": len(bones),
        "missing_mandatory": [],
        "missing_fingers": [],
        "missing_twist": [],
        "missing_secondary": [],
        "hierarchy_errors": []
    }
    # Check mandatory bones...
    # Return structured audit dictionary and exit code 0 or 1
```

---

### 4.2 Mesh Deformation & Volume Preservation Audit Script Design (`verify_mesh_deformation.py`)

#### Verification Criteria & Mathematical Formulations:
1. **Edge Length Stretch Ratio Metric**:
   - Let $E$ be the set of edges in the character mesh.
   - At rest pose $f=0$, edge $e=(i, j)$ has length $L_0(e) = \|\mathbf{v}_i(0) - \mathbf{v}_j(0)\|$.
   - Across animation frames $f \in [f_{\text{start}}, f_{\text{end}}]$, deformed length is $L(e, f) = \|\mathbf{v}_i(f) - \mathbf{v}_j(f)\|$.
   - Stretch ratio $S(e, f) = \frac{L(e, f)}{L_0(e)}$.
   - **Tearing Threshold**: $\max_{e} S(e, f) \le 1.85$.
   - **Pinching Threshold**: $\min_{e} S(e, f) \ge 0.30$.
2. **Segmented Convex Hull Volume Preservation Metric**:
   - Segment vertices into 4 critical deform zones:
     - Zone A: Left/Right Forearms & Wrists (checks twist collapse).
     - Zone B: Left/Right Knees & Calves (checks flexion flattening).
     - Zone C: Torso & Waist (checks linear skinning squash).
     - Zone D: Pleated Skirt (checks leg penetration tearing).
   - Compute 3D Convex Hull volume $V_k(f)$ for each zone $k$.
   - **Volume Retention Criterion**: $R_V(k, f) = \frac{V_k(f)}{V_k(0)} \ge 0.85$ (Must retain $\ge 85\%$ of rest volume throughout motion).
3. **Dual Quaternion Skinning Verification**:
   - Verify `mesh.modifiers['Armature'].use_deform_preserve_volume == True`.
4. **Skirt-Leg Penetration Collision Metric**:
   - Compute signed distance from thigh vertices to skirt inner faces. Flag any vertex crossing outward ($d > 0.002\text{m}$).

---

### 4.3 Render Verification Script Design (`verify_render_output.py`)

#### Verification Criteria:
1. **File Integrity**: Output MP4 file exists and size $> 500\text{ KB}$.
2. **FFprobe Stream Metadata Audit**:
   - Codec: `h264`.
   - Dimensions: Exact $1920 \times 1080$ (Full HD).
   - Frame rate: $\ge 30.0\text{ FPS}$.
   - Duration: $\ge 2.0\text{ seconds}$ matching timeline.
3. **Sampled Frame Luminance & Non-Blank Check**:
   - Extract frames at 10%, 50%, 90% timeline.
   - Mean pixel luminance $30 \le \mu_I \le 235$ (not black or blown out).
   - Standard deviation $\sigma_I \ge 15.0$ (not a solid uniform background).
4. **Cel-Shading Multi-Modal Histogram Verification**:
   - In cel-shading, the luminance histogram displays distinct discrete peaks (shadow band and base tone band) with low variance within clusters, unlike smooth Gaussian curves of PBR.
   - Compute gradient magnitude $|\nabla I|$ via Sobel operator:
     - Flat color regions: $|\nabla I| \approx 0$ for $\ge 65\%$ of character pixels.
     - Shadow terminator: Sharp step transition.
5. **Inverted Hull Outline Contour Verification**:
   - Silhouette border pixels must exhibit high darkness ($R,G,B \le 45$) and clean 1–3 pixel thickness contouring the character silhouette.

---

## 5. Architectural Recommendations & Milestone Integration

1. **Contract with R1 (Anatomy & Mesh Generation)**:
   - R1 must deliver cleanly separated mesh components (Head, Hair, Torso, Skirt, Limbs) or vertex groups so that `M_Anime_Skin`, `M_Anime_Hair`, and `M_Anime_Cloth` can be mapped cleanly to distinct material slots without bleeding.
2. **Contract with R2 (Auto-Rigging & Spring Bones)**:
   - R2 must implement the 163-bone humanoid hierarchy including twist bones and secondary spring bone chains for twintails and skirt.
   - R2 must enable `use_deform_preserve_volume = True` on the Armature modifier.
3. **Delivery Scripts in `teamwork_projects/anime_character_pipeline`**:
   - `build_anime_actions.py`: Programmatic generation of the 4 anime actions.
   - `setup_anime_shaders.py`: Material node graph creation for Skin, Hair (Angel Ring), Clothes, and Inverted Hull outline.
   - `setup_cinematic_camera.py`: Camera framing, dynamic orbit, and 3-point anime studio lighting.
   - `render_anime_video.py`: Headless Full HD 1080p MP4 rendering pipeline.
   - `tests/test_rig_audit.py`: Automated rig structure audit test.
   - `tests/test_deformation_audit.py`: Automated volume preservation and stretch ratio test.
   - `tests/test_render_audit.py`: Automated MP4 stream and cel-shading image quality verification.
