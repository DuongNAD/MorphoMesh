# Technical Analysis & Architectural Blueprint: Joint Rotational Clamping & Retargeting Limits (F12)

**Agent**: `m3_explorer_anime_2`  
**Milestone**: Milestone 3: Anime Motion Library, Action Keyframes & Retargeting (Feature F12)  
**Authoritative Request**: `teamwork_projects/anime_character_pipeline/ORIGINAL_REQUEST.md` (R3, Acceptance Criteria)  
**Scope Document**: `.agents/orchestrator_anime_1/PROJECT.md` (Feature F12, Interface Contract M2 ↔ M3)  
**Survey 3 Reference**: `.agents/survey_explorer_anime_3/analysis.md` (Section 2.3)  
**Input Asset Verified**: `teamwork_projects/anime_character_pipeline/output/anime_rigged.blend` (78 bones)  
**Environment**: Blender 4.5.4 LTS, Python 3.11, NumPy 2.4.6  
**Timestamp**: 2026-09-09T16:24:00Z  

---

## 1. Executive Summary

Applying raw human motion capture (Mocap) or generic humanoid animation data directly to anime characters produces catastrophic anatomical and aesthetic failures:
1. **Broken Hyperextension**: Elbows snapping backward past $0^\circ$ and knees bending forward, creating broken "alien" limbs.
2. **Knee Valgus & Dislocation Collapse**: Broad mocap walk cycles forcing anime knees inward into grotesque knock-kneed or dislocated scissor collisions.
3. **Shoe Sole Ground Penetration & Warping**: Unconstrained ankle pitch/roll driving shoe soles through the floor or tilting sideways on loafers.
4. **Toe Splay Distortion**: Inappropriate toe yaw/roll twisting shoe tips into rubber spirals.
5. **Cross-Standard Incompatibility**: Mocap and asset libraries arrive in disparate naming standards (VRM 1.0 Humanoid, MMD Japanese PMX, Rigify DEF, Adobe Mixamo `mixamorig:`), requiring robust bidirectional aliasing.

To permanently resolve these failure modes, this document provides the **Two-Tiered Protection Architecture**:
- **Tier 1: Pre-Keyframe Pure-Python Pose Sanitizer (`clamp_pose_rotations`)**: Intercepts arbitrary incoming animation curves/rotations (quaternions or Eulers) in pure Python, resolves standard bone names, and clamps them to physiological limits prior to keyframing. This guarantees clean f-curves that export safely to GLTF, VRM, and external game engines.
- **Tier 2: Live Viewport & Constraint Clamping (`apply_retargeting_limits`)**: Attaches `LIMIT_ROTATION` constraints on pose bones in `owner_space = 'LOCAL'`, guaranteeing that interactive posing, procedural actions, and NLA blending never violate physiological boundaries.

The blueprint has been fully verified on `output/anime_rigged.blend` in Blender 4.5.4 LTS (51 pose bone constraints attached, audited, and verified under extreme $-60^\circ$ to $+180^\circ$ input tests with 100% compliance).

---

## 2. Anatomical Coordinate System & Axis Alignment Analysis

Inspection of `Anime_Armature` in `output/anime_rigged.blend` reveals the local coordinate frame orientations created by Milestone 2:

| Bone Group | Longitudinal Axis ($Y$) | Flexion / Pitch Axis ($X$) | Deviation / Lateral Tilt ($Z$) | Rest Orientation Details |
|---|---|---|---|---|
| **ForeArms** (`ForeArm.L`, `ForeArm.R`) | Longitudinal along limb (Elbow $\to$ Wrist) | Pure 1-DOF Hinge Flexion ($+X$ curls forearm toward upper arm) | Sideways deviation (constrained) | Roll $0.0$, positive $X$ flexion brings wrist toward shoulder |
| **Knees / Shins** (`Shin.L`, `Shin.R`) | Longitudinal along limb (Knee $\to$ Ankle) | Backward Hinge Flexion ($+X$ swings shin backward toward buttocks) | Valgus / varus tilt (constrained) | `align_roll(Vector((0, 1, 0)))`, roll $\approx \pm 0.1624$, $+X$ bends backward |
| **Feet** (`Foot.L`, `Foot.R`) | Along foot length (Heel $\to$ Ball) | Pitch ($+X$ dorsiflexion up, $-X$ plantarflexion down) | Yaw (inward/outward turning) | `align_roll(Vector((0, 0, 1)))`, sole resting on ground plane $Z=0$ |
| **Toes** (`Toe.L`, `Toe.R`) | Along toe length (Ball $\to$ Tip) | Pitch ($+X$ upward toe-off flexion) | Splay / yaw | `align_roll(Vector((0, 0, 1)))`, $+X$ flexes up during step push-off |
| **Spine & Head** (`Spine..Head`) | Longitudinal along vertebral column | Pitch (forward flexion / backward extension) | Lateral roll / tilt | `align_roll(Vector((0, 1, 0)))`, $+X$ extension, $-X$ flexion |
| **Fingers** (30 Phalanges) | Along finger segment (Knuckle $\to$ Tip) | Pure palmar flexion ($+X$ curls finger into palm) | Lateral splay (only proximal knuckle) | Palmar normal cross-product bone roll, $+X$ curls inward |

### Local Space Guarantee (`owner_space = 'LOCAL'`)
In Blender, setting `owner_space = 'LOCAL'` on `LIMIT_ROTATION` constraints ensures that the rotational clamping is evaluated relative to the bone's rest parent transform, completely invariant to the character's global position, root trajectory, or body rotation.

---

## 3. Physiological Joint Rotational Clamping Matrix

The following matrix specifies the exact limits implemented in `PHYSIOLOGICAL_ROTATION_LIMITS`:

| Bone Name | Local X Limit (Flexion/Pitch) | Local Y Limit (Twist/Roll) | Local Z Limit (Deviation/Yaw) | Physiological & Aesthetic Rationale |
|---|---|---|---|---|
| `ForeArm.L`, `ForeArm.R` | $[0.0^\circ, 145.0^\circ]$ | $[-15.0^\circ, +15.0^\circ]$ | $[-5.0^\circ, +5.0^\circ]$ | **Elbow pure hinge**: Strictly eliminates hyperextension ($<0^\circ$) and hyper-flexion ($>145^\circ$). Axial twist is clamped because `ForeArm_Twist` absorbs 50% twist via `COPY_ROTATION`. Sideways dislocation strictly clamped to $\pm 5^\circ$. |
| `Shin.L`, `Shin.R` | $[0.0^\circ, 140.0^\circ]$ | $[-3.0^\circ, +3.0^\circ]$ | $[-3.0^\circ, +3.0^\circ]$ | **Knee backward flexion only**: Zero front hyperextension ($<0^\circ$), maximum anime backward flexion $140^\circ$. Local Y & Z restricted to $\pm 3^\circ$ to prevent grotesque valgus collapse or inward dislocation. |
| `Foot.L`, `Foot.R` | $[-45.0^\circ, +30.0^\circ]$ | $[-8.0^\circ, +8.0^\circ]$ | $[-10.0^\circ, +10.0^\circ]$ | **Ankle & sole ground stability**: Natural plantarflexion down to $-45^\circ$, dorsiflexion up to $+30^\circ$. Roll clamped to $\pm 8^\circ$ keeping shoe sole flat against floor; yaw clamped to $\pm 10^\circ$ preventing shoe twisting. |
| `Toe.L`, `Toe.R` | $[-5.0^\circ, +45.0^\circ]$ | $[-2.0^\circ, +2.0^\circ]$ | $[-2.0^\circ, +2.0^\circ]$ | **Toe-off push**: Upward bend up to $+45^\circ$ for natural walking/jumping. Roll and yaw restricted to $\pm 2^\circ$ preventing rubber-spiral shoe tips. |
| `Clavicle.L`, `Clavicle.R` | $[-15.0^\circ, +25.0^\circ]$ | $[-5.0^\circ, +5.0^\circ]$ | $[-15.0^\circ, +15.0^\circ]$ | **Shoulder girdle stability**: Prevents clavicle tearing, excessive shoulder shrugging, or cutting into neck mesh. |
| `UpperArm.L`, `UpperArm.R` | $[-60.0^\circ, +160.0^\circ]$ | $[-30.0^\circ, +30.0^\circ]$ | $[-45.0^\circ, +115.0^\circ]$ | **Shoulder ball joint**: Permits full range of motion (arms down, forward, overhead) while preventing torso penetration or extreme backward twisting. |
| `Thigh.L`, `Thigh.R` | $[-30.0^\circ, +110.0^\circ]$ | $[-15.0^\circ, +15.0^\circ]$ | $[-25.0^\circ, +45.0^\circ]$ | **Hip ball joint**: Permits high kicks and seated poses while bounding hyperextension and lateral abduction to prevent pelvis tearing. |
| `Hand.L`, `Hand.R` | $[-50.0^\circ, +50.0^\circ]$ | $[-20.0^\circ, +20.0^\circ]$ | $[-30.0^\circ, +25.0^\circ]$ | **Wrist articulation**: Graceful hand gestures, wrist tilt, and waving without candy-wrapper collapse. |
| `Spine` (Lumbar) | $[-15.0^\circ, +30.0^\circ]$ | $[-15.0^\circ, +15.0^\circ]$ | $[-12.0^\circ, +12.0^\circ]$ | **Lower torso articulation**: Natural lumbar curvature and gentle tilt; prevents backward spine breakage. |
| `Spine1` (Chest) | $[-15.0^\circ, +20.0^\circ]$ | $[-15.0^\circ, +15.0^\circ]$ | $[-10.0^\circ, +10.0^\circ]$ | **Breathing & posture sway**: Supports natural breathing oscillation ($\pm 1.5^\circ$) and upper torso sway. |
| `Spine2` (UpperChest) | $[-10.0^\circ, +15.0^\circ]$ | $[-10.0^\circ, +10.0^\circ]$ | $[-8.0^\circ, +8.0^\circ]$ | **Collarbone anchor**: Subtle thoracic curvature without distortion. |
| `Neck` | $[-25.0^\circ, +25.0^\circ]$ | $[-35.0^\circ, +35.0^\circ]$ | $[-20.0^\circ, +20.0^\circ]$ | **Neck flexibility**: Natural nodding, head turning, and tilting. |
| `Head` | $[-35.0^\circ, +30.0^\circ]$ | $[-45.0^\circ, +45.0^\circ]$ | $[-25.0^\circ, +25.0^\circ]$ | **Gaze & anime tilt**: Aesthetic head tilts ($3^\circ$–$6^\circ$), side glances, and expressive nodding. |
| Finger Proximal (`*.01.[L/R]`) | $[-10.0^\circ, +90.0^\circ]$ | $[-5.0^\circ, +5.0^\circ]$ | $[-15.0^\circ, +15.0^\circ]$ | Knuckle curling into palm ($+X$) with subtle lateral splay ($\pm 15^\circ$). |
| Finger Intermediate (`*.02.[L/R]`) | $[0.0^\circ, +100.0^\circ]$ | $[-2.0^\circ, +2.0^\circ]$ | $[-2.0^\circ, +2.0^\circ]$ | Strict 1-DOF interphalangeal hinge flexion. |
| Finger Distal (`*.03.[L/R]`) | $[0.0^\circ, +90.0^\circ]$ | $[-2.0^\circ, +2.0^\circ]$ | $[-2.0^\circ, +2.0^\circ]$ | Strict 1-DOF fingertip hinge flexion. |

---

## 4. Pure-Python Mathematical Sanitizer (`clamp_pose_rotations`)

### Mathematical Equivalence & Conversion
To guarantee testability without Blender binaries in standard Python test runners (CI, local pytest), `retargeting_limits.py` implements bit-accurate Quaternion $\longleftrightarrow$ Euler 'XYZ' conversion:

Given a normalized quaternion $q = (w, x, y, z)$:
The rotation matrix $M$ corresponding to Blender's extrinsic $XYZ$ convention is:
$$
M = \begin{bmatrix}
1 - 2(y^2 + z^2) & 2(xy - wz) & 2(xz + wy) \\
2(xy + wz) & 1 - 2(x^2 + z^2) & 2(yz - wx) \\
2(xz - wy) & 2(yz + wx) & 1 - 2(x^2 + y^2)
\end{bmatrix}
$$

Let $c_y = \sqrt{M_{00}^2 + M_{10}^2}$. When $c_y > 10^{-6}$:
$$
\alpha = \text{atan2}(M_{21}, M_{22}), \quad \beta = \text{atan2}(-M_{20}, c_y), \quad \gamma = \text{atan2}(M_{10}, M_{00})
$$

Euler clamping is applied directly:
$$
\alpha' = \text{clamp}(\alpha, \min_x, \max_x), \quad \beta' = \text{clamp}(\beta, \min_y, \max_y), \quad \gamma' = \text{clamp}(\gamma, \min_z, \max_z)
$$

The clamped quaternion $(w', x', y', z')$ is computed from $(\alpha', \beta', \gamma')$:
$$
\begin{aligned}
w' &= \cos(\gamma'/2)\cos(\beta'/2)\cos(\alpha'/2) + \sin(\gamma'/2)\sin(\beta'/2)\sin(\alpha'/2) \\
x' &= \cos(\gamma'/2)\cos(\beta'/2)\sin(\alpha'/2) - \sin(\gamma'/2)\sin(\beta'/2)\cos(\alpha'/2) \\
y' &= \cos(\gamma'/2)\sin(\beta'/2)\cos(\alpha'/2) + \sin(\gamma'/2)\cos(\beta'/2)\sin(\alpha'/2) \\
z' &= \sin(\gamma'/2)\cos(\beta'/2)\cos(\alpha'/2) - \cos(\gamma'/2)\sin(\beta'/2)\sin(\alpha'/2)
\end{aligned}
$$

### Execution Behavior
`clamp_pose_rotations` takes a dictionary mapping bone names (canonical, VRM, MMD, Rigify, or Mixamo) to rotations:
- Detects whether the input is a Quaternion, Euler, tuple, or list.
- Resolves aliases automatically to the canonical bone.
- Clamps values strictly to physiological bounds.
- Normalizes quaternions to unit length ($w^2 + x^2 + y^2 + z^2 = 1.0$).
- Returns a sanitized dictionary in identical data formats.

---

## 5. Cross-Standard Retargeting Mapping Table

The module incorporates full bidirectional mappings across the 4 primary industry standards:

```
+------------------+-----------------------+-------------------+--------------------+--------------------------+
| Canonical Name   | VRM 1.0 Humanoid      | MMD (Japanese)    | Rigify DEF         | Adobe Mixamo             |
+------------------+-----------------------+-------------------+--------------------+--------------------------+
| Hips             | hips                  | 下半身 / センター  | DEF-spine          | mixamorig:Hips           |
| Spine            | spine                 | 上半身            | DEF-spine.001      | mixamorig:Spine          |
| Spine1           | chest                 | 上半身2           | DEF-spine.002      | mixamorig:Spine1         |
| Spine2           | upperChest            | 上半身3           | DEF-spine.003      | mixamorig:Spine2         |
| Neck             | neck                  | 首                | DEF-spine.004      | mixamorig:Neck           |
| Head             | head                  | 頭                | DEF-head           | mixamorig:Head           |
| Clavicle.L       | leftShoulder          | 左肩              | DEF-shoulder.L     | mixamorig:LeftShoulder   |
| UpperArm.L       | leftUpperArm          | 左腕              | DEF-upper_arm.L    | mixamorig:LeftArm        |
| UpperArm_Twist.L | (twist helper)        | 左腕捩            | DEF-upper_arm.L.001| (none)                   |
| ForeArm.L        | leftLowerArm          | 左ひじ            | DEF-forearm.L      | mixamorig:LeftForeArm    |
| ForeArm_Twist.L  | (twist helper)        | 左手捩            | DEF-forearm.L.001  | (none)                   |
| Hand.L           | leftHand              | 左手首            | DEF-hand.L         | mixamorig:LeftHand       |
| Thigh.L          | leftUpperLeg          | 左足              | DEF-thigh.L        | mixamorig:LeftUpLeg      |
| Shin.L           | leftLowerLeg          | 左ひざ            | DEF-shin.L         | mixamorig:LeftLeg        |
| Foot.L           | leftFoot              | 左足首            | DEF-foot.L         | mixamorig:LeftFoot       |
| Toe.L            | leftToes              | 左つま先          | DEF-toe.L          | mixamorig:LeftToeBase    |
| Thumb.01..03.L   | leftThumb*            | 左親指０〜２       | DEF-thumb.01..03.L | mixamorig:LeftHandThumb* |
| Index.01..03.L   | leftIndex*            | 左人指１〜３       | DEF-f_index.*.L    | mixamorig:LeftHandIndex* |
| Middle.01..03.L  | leftMiddle*           | 左中指１〜３       | DEF-f_middle.*.L   | mixamorig:LeftHandMiddle*|
| Ring.01..03.L    | leftRing*             | 左薬指１〜３       | DEF-f_ring.*.L     | mixamorig:LeftHandRing*  |
| Pinky.01..03.L   | leftLittle*           | 左小指１〜３       | DEF-f_pinky.*.L    | mixamorig:LeftHandPinky* |
| (Right Side)     | (right* equivalents)  | (右* equivalents) | (*.R equivalents)  | (mixamorig:Right* equiv) |
+------------------+-----------------------+-------------------+--------------------+--------------------------+
```

### Prefix Stripping & Fuzzy Normalization
`resolve_to_canonical(bone_name)` automatically handles:
- Exact alias lookup
- Prefix stripping (`mixamorig:`, `mixamo:`, `DEF-`, `b_`, `Bip01_`, `Bip001_`)
- Case-insensitive alphanumeric normalization (stripping underscores, dots, hyphens)

---

## 6. Live Armature Constraint Integration & Audit

The API provides three primary operations on live Blender armatures:

1. `apply_retargeting_limits(armature_obj, limits_dict=None, replace_existing=True)`:
   - Sets `c.name = "Physiological_Limit_Rotation"`
   - Sets `c.owner_space = 'LOCAL'`
   - Sets `c.euler_order = 'XYZ'`
   - Sets `c.use_transform_limit = True`
   - Assigns corresponding $X, Y, Z$ minimum/maximum radians.
   - Verified on `Anime_Armature`: Attaches 51 active physiological constraints.

2. `verify_retargeting_limits(armature_obj, limits_dict=None)`:
   - Scans all pose bones against the limit specification.
   - Verifies constraint presence, `owner_space == 'LOCAL'`, and numerical bound accuracy ($\pm 10^{-4}$ rad).
   - Returns audit summary (`pass_status: True`, `verified_count: 51`, `discrepancies: []`).

3. `remove_retargeting_limits(armature_obj)`:
   - Cleans up all `Physiological_Limit_Rotation` constraints safely when resetting or rebaking.

---

## 7. Two-Tiered Protection Architecture

```
                      RAW HUMAN MOTION CAPTURE / BVH / FBX
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ TIER 1: Pre-Keyframe Pure-Python Sanitizer        │
             │   - Function: clamp_pose_rotations()             │
             │   - Bone Name Resolver: VRM / MMD / Rigify / Mix │
             │   - Quat / Euler Pure-Math Clamping              │
             │   - Clamps raw f-curves prior to keyframe insert │
             └──────────────────────────────────────────────────┘
                                      │
                                      ▼ Clean F-Curves
             ┌──────────────────────────────────────────────────┐
             │ TIER 2: Live Viewport & Pose Bone Constraints    │
             │   - Function: apply_retargeting_limits()         │
             │   - Constraint: LIMIT_ROTATION                   │
             │   - Owner Space: LOCAL                           │
             │   - Real-time protection during interactive pose │
             └──────────────────────────────────────────────────┘
                                      │
                                      ▼
                      GAME-READY / VTUBER ANIME ANIMATION
             (Zero elbow hyperextension, zero knee valgus collapse,
              stable shoe soles, flawless GLTF / VRM export)
```

---

## 8. Verification Commands & Independent Replication

All tests can be replicated with the following commands:

```powershell
# 1. Run Pure-Python Math & Resolution Unit Tests (6/6 pass)
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" "E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_2\test_proposed_retargeting_limits.py"

# 2. Run Live Blender 4.5+ LTS Pose Bone Constraint Tests (100% pass)
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b "E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_rigged.blend" --python "E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_2\test_blender_retargeting_limits.py"

# 3. Run Existing Pytest Test Suite (122/122 pass)
pytest -q "E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\tests"
```
