# Project: Anime Character Pipeline

## Architecture
Hệ thống pipeline tự động tạo nhân vật 3D Anime Girl Game-Ready / VTuber / VRM hoàn chỉnh, loại bỏ hoàn toàn các lỗi biến dạng khớp, vặn xoắn cổ tay và xé tà váy, tích hợp hoạt ảnh anime tự nhiên và xuất video anime điện ảnh Full HD 1080p MP4 thông qua Blender 4.5.4 LTS.

```
+-----------------------------------------------------------------------------------+
|                           Anime Character Pipeline Architecture                    |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [M1: Anime Mesh Synthesis & Anatomy Topology]                                    |
|      ├── 7 Modular Sub-Meshes (Head, Torso, Arms, Legs, Hair, Pleated Skirt, Shoes) |
|      ├── Clean Quad Deformation Loops (3-5 loop hinges, neck/shoulder/pelvis)     |
|      └── Bishoujo Anime Proportions (1:6.5-7.0 head ratio, slender limbs)         |
|                                     │                                             |
|                                     ▼ (Mesh Objects with Vertex Groups)           |
|  [M2: Anime Auto-Rigging, Twist & Spring Bones, DQS]                              |
|      ├── Humanoid / VRM / MMD / Rigify Universal Armature                         |
|      ├── Full 30-Phalange Articulated Fingers (15 L + 15 R)                       |
|      ├── Forearm & Arm Twist Bones (0.5 Copy-Rotation local Y constraint)         |
|      ├── 12-Radial Skirt Bone Rig (Pitch Clamped [-15°, 65°], zero thigh weights) |
|      ├── 5-Bone Twintail Secondary Chains (Inertial Spring & Damping)             |
|      └── Dual Quaternion Skinning (use_deform_preserve_volume = True)             |
|                                     │                                             |
|                                     ▼ (Rigged Armature + Skinned Mesh)            |
|  [M3: Anime Motion Library, Retargeting & Secondary Dynamics]                     |
|      ├── 4 Anime Keyframed Actions: Idle Cute, Wave Hello, Walk Cycle, Jump/Cheer |
|      ├── Hinge Rotational Clamping (Elbow 0-145°, Knee 0-140°, Toe limits)        |
|      └── Inertial Secondary Spring/Damping Motion Solver                          |
|                                     │                                             |
|                                     ▼ (Animated Character Scene)                  |
|  [M4: Toon Cel-Shading, Inverted Hull Outline & Cinematic MP4 Render]             |
|      ├── Stepped Cel-Shading Tree (Skin: warm peach shadow; Hair: Angel Ring band)|
|      ├── Inverted Hull Outline (Solidify, -0.015, Backface Culling Unlit)        |
|      ├── 3-Point Studio Anime Lighting & 50-85mm Cinematic Camera Framing         |
|      └── Headless EEVEE-Next Full HD 1080p @ 30 FPS MP4 FFMPEG Video Exporter     |
|                                     │                                             |
|                                     ▼                                             |
|  [M5: Final E2E Integration, Verification Suite & Hardening]                      |
|      ├── Phase 1: Pass 100% E2E Test Suite (Tiers 1-4) published by Test Track   |
|      └── Phase 2: Adversarial Coverage Hardening (Tier 5 White-Box Stress Tests)  |
+-----------------------------------------------------------------------------------+
```

---

## Feature Inventory

Every feature identified in the Survey phase and `ORIGINAL_REQUEST.md` is assigned to a milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | 7-Component Modular Mesh Synthesis | Generates Head, Torso, Arms, Legs, Hair, Skirt, Shoes as discrete sub-meshes | M1 | R1, Survey 1 & 2 |
| F02 | Clean Quad Skinning Topology | 3-loop and 5-loop edge flow at elbows, knees, waist, crotch; positive boundary clearance | M1 | R1, Survey 2 |
| F03 | Bishoujo Anime Proportions | Slender anime limbs, head-to-body ratio 1:6.5 to 1:7.0, stylized facial geometry | M1 | R1, Survey 2 |
| F04 | Universal Humanoid Bone Hierarchy | VRM 1.0, MMD, Rigify compatible armature hierarchy and naming conventions | M2 | R2, Survey 1 & 2 |
| F05 | 30-Phalange Articulated Fingers | Full 5-finger hands (Thumb, Index, Middle, Ring, Pinky with 3 phalanges each) | M2 | R2, Survey 1 & 2 |
| F06 | Forearm & Arm Twist Bones | 0.5 factor local Y copy-rotation constraints eliminating candy-wrapper collapse | M2 | R2, Survey 2 |
| F07 | 12-Radial Skirt Secondary Rig | Pelvis-anchored radial spoke bones with pitch limit clamp; 0% thigh weight transfer | M2 | R2, Survey 2 |
| F08 | 5-Bone Twintail Secondary Chains | Spring bone chains with damping and stiffness parameters for dynamic hair sway | M2 | R2, Survey 2 |
| F09 | Dual Quaternion Skinning Integration | Armature modifier `use_deform_preserve_volume = True` eliminating joint volume loss | M2 | R2, Survey 1 & 2 |
| F10 | Smooth Weight Paint Transfer | Heatmap/proximity weight assignment isolating modular components | M2 | R2, Survey 2 |
| F11 | 4 Programmatic Anime Actions | Keyframed actions: `Idle_Cute`, `Wave_Greeting`, `Walk_Cycle`, `Jump_Cheer` | M3 | R3, Survey 3 |
| F12 | Joint Rotational Clamping | Hinge limits (Elbows 0°-145°, Knees 0°-140°, Ankle/Toe limits) preventing mocap distortion | M3 | R3, Survey 3 |
| F13 | Secondary Inertial Physics Solver | Evaluates twintail and skirt spring-damper motion across animation frames | M3 | R3, Survey 1 & 3 |
| F14 | Stepped Cel-Shading Node Trees | EEVEE-Next `ShaderNodeShaderToRGB` + `ColorRamp [CONSTANT]` (warm peach skin shadow) | M4 | R4, Survey 1 & 3 |
| F15 | Procedural Hair Angel Ring | Object-space Z-band highlight with diffuse gating simulating anime hair specular ring | M4 | R4, Survey 3 |
| F16 | Inverted Hull Solidify Outline | Solidify modifier (thickness -0.015, flipped normals, unlit emission material) | M4 | R4, Survey 3 |
| F17 | Cinematic Camera & 3-Point Lighting | 50-85mm focal length, optical character framing, 550W key/rim anime light setup | M4 | R4, Survey 1 & 3 |
| F18 | Headless Full HD MP4 Video Exporter | Automated Blender CLI rendering 1920x1080 @ >=30 FPS H.264 MP4 video | M4 | R4, Survey 1 & 3 |
| F19 | Master Reusable Pipeline CLI | End-to-end CLI script executing generation, rigging, animating, shading & rendering | M4 | R4, Acceptance |
| F20 | Automated Rig Completeness Audit | Script verifying 30 finger bones, twist bones, hair, and skirt bones | M5 | Verification, Survey 3 |
| F21 | Automated Mesh Volume & Stretch Audit | Script computing edge stretch $S \le 1.85$ and volume retention $R_V \ge 0.85$ | M5 | Verification, Survey 3 |
| F22 | Automated Video & Shading Render Audit | Script verifying MP4 stream specs via FFprobe and cel-shading histogram step | M5 | Verification, Survey 3 |
| F23 | 100% E2E Test Suite Pass & Hardening | Full validation of Tiers 1-4 from E2E Track, followed by Tier 5 adversarial tests | M5 | Project Pattern Final Milestone |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Anime Mesh Synthesis & Anatomy Topology | F01, F02, F03 (Modular 7 sub-meshes, clean quads, anime proportions) | none | DONE (Assets generated in output/, 98/98 tests passing, gate approved) |
| M2 | Anime Auto-Rigging, Twist/Spring Bones & DQS | F04, F05, F06, F07, F08, F09, F10 (Rigging, fingers, twist, skirt, hair, DQS) | M1 | DONE (78 bones, DQS, 122/122 tests passing, gate approved) |
| M3 | Anime Motion Library & Retargeting | F11, F12, F13 (4 actions, hinge rotational clamps, secondary dynamics) | M2 | DONE (4 actions, 51 limits, 20.9k baked keyframes, skirt clearance 22.08mm, 148/148 tests pass, gate approved) |
| M4 | Cel-Shading, Outline, Camera & Video Pipeline | F14, F15, F16, F17, F18, F19 (Shaders, outline, camera, MP4 export, CLI) | M3 | IN_PROGRESS |
| M5 | Final E2E Test Pass & Adversarial Hardening | F20, F21, F22, F23 (Tiers 1-4 test pass, Tier 5 adversarial hardening) | M4, TEST_READY.md | PLANNED |

*Parallel Track*: **E2E Testing Track** (`test_writer_e2e_track`)
- Responsible for `TEST_INFRA.md`, Tiers 1-4 tests (`test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_interactions.py`, `test_tier4_workloads.py`), and publishing `TEST_READY.md`.

---

## Interface Contracts

### M1 ↔ M2: Mesh ↔ Rigging Contract
- Input to M2: Blender Scene or OBJ/GLTF containing discrete mesh objects:
  - `Anime_Head`: Facial mesh, eyes, mouth. Coincident neck boundary vertices match `Anime_Torso`.
  - `Anime_Torso`: Neck, chest, abdomen, pelvis.
  - `Anime_Arms`: Shoulders, upper arms, forearms, hands with 5 separated fingers.
  - `Anime_Legs`: Thighs, knees, shins, ankles, feet.
  - `Anime_Hair`: Scalp base + left & right twintail meshes.
  - `Anime_Skirt`: Pleated A-line skirt with $+15\text{mm}$ clearance above thighs.
  - `Anime_Shoes`: Loafers/boots with flat ground-plane sole at $Z = 0.0$.
- Vertex Group Contract: M2 creates vertex groups on each object matching bone names. No thigh vertex group weights on `Anime_Skirt`.

### M2 ↔ M3: Rigging ↔ Animation Contract
- Armature Object: Named `Anime_Armature`.
- Bone Hierarchy:
  - Root: `Hips`
  - Spine: `Spine` -> `Spine1` -> `Spine2` -> `Neck` -> `Head`
  - Arms: `Clavicle.[L/R]` -> `UpperArm.[L/R]` (with `UpperArm_Twist.[L/R]`) -> `ForeArm.[L/R]` (with `ForeArm_Twist.[L/R]`) -> `Hand.[L/R]`
  - Fingers: `Thumb.01..03.[L/R]`, `Index.01..03.[L/R]`, `Middle.01..03.[L/R]`, `Ring.01..03.[L/R]`, `Pinky.01..03.[L/R]`
  - Legs: `Thigh.[L/R]` (with `Thigh_Twist.[L/R]`) -> `Shin.[L/R]` (with `Shin_Twist.[L/R]`) -> `Foot.[L/R]` -> `Toe.[L/R]`
  - Secondary Bones:
    - `Skirt_01` .. `Skirt_12` parented to `Hips`.
    - `Hair_L_01..05` parented to `Head`, `Hair_R_01..05` parented to `Head`.
- Constraints: Arm twist bones have `COPY_ROTATION` targeting child bone with $0.5$ influence on local $Y$ axis.
- Armature Modifier: `use_deform_preserve_volume = True` on all deforming meshes.

### M3 ↔ M4: Animation ↔ Shading & Rendering Contract
- Output of M3: Blender scene with `Anime_Armature` assigned keyframed actions or baked NLA tracks (`action_anime_idle_cute`, `action_anime_wave_greeting`, `action_anime_walk_cycle`, `action_anime_jump_cheer`).
- M4 attaches Materials:
  - `M_Anime_Skin`: Applied to Head, Torso, Arms, Legs.
  - `M_Anime_Hair`: Applied to Hair with procedural Angel Ring.
  - `M_Anime_Clothes`: Applied to Shirt / Skirt.
  - `M_Anime_Outline`: Applied as material slot 1 on Solidify modifier.
- M4 Camera & Render:
  - Camera: `Anime_Camera`, 65mm focal length, tracked to `Spine2` / `Head`.
  - Resolution: 1920x1080 @ 30 FPS. Container: MP4 (H.264 / AAC).
  - Output path: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_girl_cinematic.mp4`.

---

## Code Layout

Target working directory: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`

```
anime_character_pipeline/
├── ORIGINAL_REQUEST.md                   # Immutable user request
├── PROJECT.md                            # Global architecture, milestones & index
├── pipeline.py                           # Master reusable CLI pipeline entry point
├── anime_pipeline/                       # Core python package
│   ├── __init__.py
│   ├── mesh/
│   │   ├── __init__.py
│   │   ├── generator.py                  # M1: Modular anime sub-mesh synthesis
│   │   └── topology_cleaner.py           # M1: Quad subdivision & boundary isolation
│   ├── rigging/
│   │   ├── __init__.py
│   │   ├── armature_builder.py           # M2: Bone hierarchy, fingers, twists, skirt
│   │   ├── skinning_dqs.py               # M2: Anti-pinch weights & DQS configuration
│   │   └── secondary_bones.py            # M2: Twintail chains & skirt pitch clamps
│   ├── animation/
│   │   ├── __init__.py
│   │   ├── action_library.py             # M3: 4 anime keyframe actions
│   │   ├── retargeting_limits.py         # M3: Hinge rotational limits
│   │   └── spring_solver.py              # M3: Inertial secondary motion evaluator
│   ├── shading/
│   │   ├── __init__.py
│   │   ├── cel_shader.py                 # M4: Stepped cel-shading & Angel Ring nodes
│   │   └── inverted_hull.py              # M4: Solidify outline modifier setup
│   └── render/
│       ├── __init__.py
│       ├── camera_rig.py                 # M4: 50-85mm cinematic camera & framing
│       └── video_exporter.py             # M4: Headless 1080p 30fps MP4 export
├── tests/
│   ├── __init__.py
│   ├── verify_anime_rig.py               # M5: Rig completeness auditor
│   ├── verify_mesh_deformation.py        # M5: Volume retention & stretch auditor
│   ├── verify_render_output.py           # M5: FFprobe MP4 & cel histogram auditor
│   ├── test_tier1_features.py            # E2E Track: Tier 1 Feature Coverage
│   ├── test_tier2_boundaries.py          # E2E Track: Tier 2 Boundary & Extremes
│   ├── test_tier3_interactions.py        # E2E Track: Tier 3 Pairwise Combinations
│   └── test_tier4_workloads.py           # E2E Track: Tier 4 Real-World Scenarios
└── output/
    ├── anime_girl_model.blend            # Master blend file with complete character
    ├── anime_girl_model.glb              # Exported Game-Ready / VTuber asset
    ├── anime_girl_cinematic.mp4          # Full HD 1080p 30fps cinematic video
    └── snapshots/                        # Snapshot PNGs verifying cel-shading
```

### Write Ownership Boundaries
- **Milestone 1**: Owns `anime_pipeline/mesh/*`.
- **Milestone 2**: Owns `anime_pipeline/rigging/*`.
- **Milestone 3**: Owns `anime_pipeline/animation/*`.
- **Milestone 4**: Owns `anime_pipeline/shading/*`, `anime_pipeline/render/*`, `pipeline.py`.
- **E2E Testing Track**: Owns `tests/test_tier*.py`, `TEST_INFRA.md`, `TEST_READY.md`.
- **Milestone 5**: Owns `tests/verify_*.py` and E2E integration test runners.
