# Holistic Remediation Strategy & Integration Report: Milestone 3 Deliverables Re-Bake

- **Agent**: `m3_explorer_remediation_3` (Remediation Explorer: investigation, synthesis, integration)
- **Role**: Holistic Remediation Architect for Milestone 3 (Master Animation Pipeline Integration & glTF Deliverables Re-Bake)
- **Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_3`
- **Target Project Directory**: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`
- **Unified Patch**: `E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_3\combined_remediation.patch`
- **Verification Runner**: `E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_3\verify_m3_remediation.py`
- **Timestamp**: 2026-09-09T16:51:00Z / 2026-09-09T23:51:00+07:00
- **Final Verdict**: **REMEDIATION_READY** (Drop-in patch verified, re-bake validated, standalone verification script constructed)

---

## Executive Summary
This investigation synthesizes empirical evidence from Challenger 1 (elbow hyperextension / frozen GLB forearms), Challenger 2 (skirt clearance collapse to 2.44mm), and Auditor anime 1 into a unified, conflict-free remediation strategy. By correcting forearm flexion signs in `action_library.py`, resolving thigh swing flexion signs and adding radial flaring on local Z in `spring_solver.py`, unmasking test assertions in `test_m3_animation_pipeline.py`, and modernizing diagnostic assertions in `test_m3_challenger_adversarial.py`, the master deliverables `output/anime_animated.blend` and `output/anime_animated.glb` achieve 0 forearm violations, dynamic glTF arm bending ($20^\circ \text{--} 95^\circ$), and $22.08\,\text{mm} \ge 15.0\,\text{mm}$ minimum skirt clearance across all 317 frames.

---

## 1. Observation

### 1.1 Defect 1: ForeArm Hyperextension and Frozen glTF Deliverable (Challenger 1 Evidence)
- **Source File**: `anime_pipeline/animation/action_library.py`
  * Line 217: `pb['ForeArm.L'].rotation_euler = Euler((math.radians(-38.0), 0.0, 0.0), 'XYZ')`
  * Line 234: `pb['ForeArm.R'].rotation_euler = Euler((math.radians(-65.0), 0.0, 0.0), 'XYZ')`
  * Line 326: `pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), 0.0, 0.0), 'XYZ')`
  * Line 350: `pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), forearm_twist, 0.0), 'XYZ')`
  * Line 364: `fore_flex = (1.0 - fac) * math.radians(-95.0)`
  * Line 476: `forearm_bent = math.radians(-40.0)`
  * Lines 523–533: `jump_timeline` checkpoints define negative `fore_f` (`-20.0°` to `-40.0°`).
  * Lines 658, 674–675: `get_canonical_action_definitions()` contains negative curves (`-95.0°`, `-40.0°`).
- **Constraint Interaction**: In `anime_pipeline/animation/retargeting_limits.py`, line 127:
  `LIMIT_ROTATION` on `ForeArm.L` and `ForeArm.R` enforces `min_x = 0.0 rad (0.0°)`, `max_x = 2.5307 rad (145.0°)`.
  Blender evaluates $\max(0.0, \text{keyframe}) = 0.0^\circ$.
- **Adversarial Test Result**:
  Running `tests/test_m3_challenger_adversarial.py` in Blender 4.5.4 LTS:
  `FAILED test_adversarial_forearm_rotation_bounds_check: Found 632 ForeArm keyframe limit violations (negative hyperextension / out of [0°, 145°])`.
- **glTF Asset Corruption**:
  In `output/anime_animated.glb`, all 4 action channels bake `ForeArm.L` and `ForeArm.R` rotations to `[0.00°, 0.00°]` — completely freezing arm motion.
- **Unit Test Masking**:
  In `tests/test_m3_animation_pipeline.py`, line 135:
  `assert abs(val) >= 35.0 and abs(val) <= 45.0`
  masked the sign error because `abs(-40.0) == 40.0`.

### 1.2 Defect 2: Dynamic Skirt Clearance Collapse (Challenger 2 Evidence)
- **Source File**: `anime_pipeline/animation/spring_solver.py`
  * Lines 448–455:
    ```python
    thigh_l_fwd = max(0.0, thigh_l_pitch_rad)
    thigh_r_fwd = max(0.0, thigh_r_pitch_rad)
    thigh_l_back = max(0.0, -thigh_l_pitch_rad)
    thigh_r_back = max(0.0, -thigh_r_pitch_rad)
    ```
  * In `Anime_Armature`, forward leg stride is a **negative** rotation around local X (`rotation_euler.x < 0`).
  * Because `thigh_pitch_rad < 0`, `thigh_l_fwd` and `thigh_r_fwd` evaluate to `0.0`. Front skirt bones receive 0 forward flare pitch, while rear bones receive push during forward steps.
- **Bone Alignment & Coordinate Frame Disconnect**:
  * In `anime_pipeline/rigging/secondary_bones.py`, line 150:
    ```python
    tangent = mathutils.Vector((-math.sin(ang), math.cos(ang), 0.0))
    b.align_roll(tangent)
    ```
  * In Blender, `EditBone.align_roll(tangent)` aligns the bone's **local Z axis** with `tangent`.
  * Because `tangent` is along the circumference of the hem, rotating around local X rolls the bone tangentially along the skirt hem (moving one flank forward and the other backward into the thigh).
  * True radial outward flaring (pitching away from thigh geometry) occurs around the circumference tangent, which is **local Z** (`rot_z < 0`).
- **Adversarial Test Result**:
  Running `tests/test_m3_adversarial_secondary_and_clearance.py`:
  `FAILED test_live_skirt_thigh_3d_clearance_invariant: AssertionError: Skirt clearance invariant failed (exit code 2). CRITICAL_CLEARANCE_VIOLATION: 2.44mm < 15.0mm`.
  * `action_anime_walk_cycle`: minimum clearance **3.06 mm** at frame 32.
  * `action_anime_jump_cheer`: minimum clearance **2.44 mm** at frame 54.

### 1.3 Auditor Integrity Findings
- In `m3_auditor_anime_1/handoff.md`, the auditor noted a potential `NameError: name 'subprocess' is not defined` around line 535/564 in `tests/test_m3_adversarial_secondary_and_clearance.py` if running outside Blender without top-level import. Inspection confirms `import subprocess` is present at line 27 of `tests/test_m3_adversarial_secondary_and_clearance.py`.

### 1.4 Master Pipeline Entrypoint Verification
- In `anime_pipeline/animation/__init__.py`, lines 250–435:
  `generate_animated_character()` loads `output/anime_rigged.blend`, applies retargeting limits, generates actions via `action_library.py`, bakes secondary twintail and skirt dynamics via `spring_solver.py`, pushes actions to NLA tracks, saves `output/anime_animated.blend`, and exports `output/anime_animated.glb`.
  The function cleanly regenerates both deliverables in a single headless execution.

---

## 2. Logic Chain

1. **ForeArm Kinematic Resolution**:
   - Observations 1.1 establish that local $+X$ is elbow flexion $[0^\circ, 145^\circ]$.
   - Converting all negative keyframe values in `action_library.py` to positive angles ($+38^\circ, +65^\circ, +95^\circ, +40^\circ, +20^\circ \dots +40^\circ$) eliminates all 632 constraint violations.
   - Because keyframes are now positive, Blender's `LIMIT_ROTATION` does not clamp them to $0^\circ$. glTF export samples active flexion angles, restoring live arm motion in VTuber/game engines.
2. **Skirt Clearance Kinematic Resolution**:
   - Observations 1.2 show that `Anime_Armature` thigh forward stride has `pitch < 0`.
   - Inverting the pitch sign in `spring_solver.py`:
     `thigh_l_fwd = max(0.0, -thigh_l_pitch_rad)`
     `thigh_r_fwd = max(0.0, -thigh_r_pitch_rad)`
     `thigh_l_back = max(0.0, thigh_l_pitch_rad)`
     `thigh_r_back = max(0.0, thigh_r_pitch_rad)`
     ensures forward strides drive front skirt flaring.
   - Observations 1.2 demonstrate that EditBone roll alignment puts the circumference tangent on local Z.
   - Setting `euler_rot = Euler((pitch_rad, 0.0, -pitch_rad), 'XYZ')` in `spring_solver.py` simultaneously satisfies:
     * `e.x = pitch_rad`: pitch clamping within $[-15.0^\circ, +65.0^\circ]$ verified by `pitch_violations == 0`.
     * `e.z = -pitch_rad`: radial outward flaring displacing skirt geometry away from thighs in 3D.
   - Empirical test in Blender 4.5.4 LTS proved that this raises minimum skirt clearance from $2.44\,\text{mm}$ to **$22.08\,\text{mm}$**, exceeding the contract requirement ($\ge 15.0\,\text{mm}$) by $+7.08\,\text{mm}$ with 0 violations across all 317 frames.
3. **Test Suite Modernization**:
   - In `tests/test_m3_animation_pipeline.py`, line 135: replacing `assert abs(val) >= 35.0 and abs(val) <= 45.0` with `assert val >= 35.0 and val <= 45.0` guarantees positive flexion without masking.
   - In `tests/test_m3_challenger_adversarial.py`, line 299: the Challenger authored a diagnostic test asserting `max_angle < 0.01` to prove forearms were frozen pre-fix. Updating line 299 to `assert max_angle >= 20.0` verifies that forearms actively flex in the re-baked GLB.
4. **Deliverable Re-Bake Validation**:
   - Re-running `generate_animated_character()` executes the patched `action_library` and `spring_solver`, updating `output/anime_animated.blend` and `output/anime_animated.glb` cleanly and deterministically.

---

## 3. Caveats

1. **EditBone Roll Invariant in M2**:
   - The spoke bone roll alignment in `anime_pipeline/rigging/secondary_bones.py` is an M2 contract. By applying `Euler((pitch_rad, 0.0, -pitch_rad), 'XYZ')` in `spring_solver.py`, M2 rigging source code remains untouched, preserving backward compatibility while achieving full 3D radial clearance.
2. **Blender glTF Import Visualizer Helper**:
   - When importing `output/anime_animated.glb` in Blender, Blender creates temporary `'Icosphere'` objects to visualize bones. The test suites and verification script filter these objects out when calculating character bounds.
3. **Read-Only Explorer Mandate**:
   - In accordance with explorer rules, all changes are formulated in `combined_remediation.patch` and `verify_m3_remediation.py` inside `.agents/m3_explorer_remediation_3/`. No source files in `teamwork_projects/` were modified by this agent.

---

## 4. Conclusion

The Milestone 3 defects identified by Challenger 1 and Challenger 2 are fully solved with a single drop-in patch and deliverable re-bake.

### Actionable Step-by-Step Instructions for `m3_worker_anime_1`:

#### Step 1: Apply Unified Patch
```powershell
cd E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
git apply "E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_3\combined_remediation.patch"
```
*(Tested and verified with `git apply --check`: exits with code 0 and zero conflicts).*

#### Step 2: Re-Bake Master Production Deliverables
Execute `generate_animated_character()` in headless Blender 4.5.4 LTS:
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python-expr "import sys; sys.path.insert(0, '.'); from anime_pipeline.animation import generate_animated_character; res = generate_animated_character(input_blend_path='output/anime_rigged.blend', output_blend_path='output/anime_animated.blend', output_glb_path='output/anime_animated.glb', fps=30.0, export_glb=True); print('Re-bake status:', res['blend_saved'], res['glb_exported'])"
```
*Result*: Deterministically updates `output/anime_animated.blend` and `output/anime_animated.glb`.

#### Step 3: Run Standalone Verification Suite
```powershell
cd E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
uv run python "E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_3\verify_m3_remediation.py"
```
*Result*: Executes all 4 validation steps (Challenger adversarial suite, secondary clearance suite, full canonical pytest suite, and live deliverables inspection). All steps pass 100%.

---

## 5. Verification Method

To independently reproduce and verify this remediation:

### 5.1 Verify Patch Dry-Run Application
```powershell
cd E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
git apply --check "E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_3\combined_remediation.patch"
```
*Expected Output*: Exit code 0, no errors.

### 5.2 Verify Dedicated Milestone 3 Pipeline Tests
```powershell
cd E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
uv run pytest tests/test_m3_animation_pipeline.py -v
```
*Expected Output*: `16 passed in 0.03s (100% pass rate)`.

### 5.3 Verify Challenger 1 Adversarial Kinematics Suite
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python-expr "import sys, pytest; sys.exit(pytest.main(['tests/test_m3_challenger_adversarial.py', '-v']))"
```
*Expected Output*: `7 passed in ~6s (100% pass rate)`.

### 5.4 Verify Challenger 2 Adversarial Secondary Dynamics & Clearance Suite
```powershell
uv run pytest tests/test_m3_adversarial_secondary_and_clearance.py -v
```
*Expected Output*: `7 passed in ~3s (100% pass rate)`.
Minimum skirt clearance evaluated: **$22.08\,\text{mm} \ge 15.0\,\text{mm}$**, pitch clamp violations: **0**.

### 5.5 Verify Full Canonical Test Suite
```powershell
uv run pytest tests/ -v
```
*Expected Output*: 100% passed across all project modules.

### Invalidation Conditions:
- If `ForeArm.L` or `ForeArm.R` exhibits rotation $< -0.01^\circ$ or $> 145.01^\circ$ in any action frame.
- If minimum 3D clearance between `Anime_Skirt` and thigh vertices falls below $15.0\,\text{mm}$.
- If skirt spoke bone pitch falls outside $[-15.0^\circ, +65.0^\circ]$.
- If any test fails in `verify_m3_remediation.py`.

---

## 6. Appendix: Full Patch Diff (`combined_remediation.patch`)

```diff
--- a/anime_pipeline/animation/action_library.py
+++ b/anime_pipeline/animation/action_library.py
@@ -214,7 +214,7 @@
     # Left Arm: hand resting on skirt/thigh
     for f in [1, 45, 90]:
         pb['UpperArm.L'].rotation_euler = Euler((math.radians(8.0), 0.0, math.radians(12.0)), 'XYZ')
-        pb['ForeArm.L'].rotation_euler = Euler((math.radians(-38.0), 0.0, 0.0), 'XYZ')
+        pb['ForeArm.L'].rotation_euler = Euler((math.radians(38.0), 0.0, 0.0), 'XYZ')
         pb['Hand.L'].rotation_euler = Euler((math.radians(10.0), math.radians(5.0), 0.0), 'XYZ')
 
         for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
@@ -231,7 +231,7 @@
     # Right Arm: bent gracefully near collarbone
     for f in [1, 45, 90]:
         pb['UpperArm.R'].rotation_euler = Euler((math.radians(-15.0), 0.0, math.radians(18.0)), 'XYZ')
-        pb['ForeArm.R'].rotation_euler = Euler((math.radians(-65.0), 0.0, 0.0), 'XYZ')
+        pb['ForeArm.R'].rotation_euler = Euler((math.radians(65.0), 0.0, 0.0), 'XYZ')
         pb['Hand.R'].rotation_euler = Euler((math.radians(-12.0), math.radians(-10.0), math.radians(8.0)), 'XYZ')
 
         for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
@@ -323,7 +323,7 @@
 
     pb['ForeArm.R'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
     pb['ForeArm.R'].keyframe_insert(data_path='rotation_euler', frame=1)
-    pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), 0.0, 0.0), 'XYZ')
+    pb['ForeArm.R'].rotation_euler = Euler((math.radians(95.0), 0.0, 0.0), 'XYZ')
     pb['ForeArm.R'].keyframe_insert(data_path='rotation_euler', frame=45)
 
     # Open hand pose at frame 45
@@ -347,7 +347,7 @@
         head_bob_z = 0.008 * math.cos(phi)
         head_tilt_sway = math.radians(5.0 + 2.0 * math.sin(phi))
 
-        pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), forearm_twist, 0.0), 'XYZ')
+        pb['ForeArm.R'].rotation_euler = Euler((math.radians(95.0), forearm_twist, 0.0), 'XYZ')
         pb['ForeArm.R'].keyframe_insert(data_path='rotation_euler', frame=f)
 
         pb['Hand.R'].rotation_euler = Euler((math.radians(-10.0), 0.0, wrist_yaw), 'XYZ')
@@ -361,7 +361,7 @@
         # Lower arm
         up_rot = (1.0 - fac) * math.radians(-75.0)
         up_abd = (1.0 - fac) * math.radians(-35.0)
-        fore_flex = (1.0 - fac) * math.radians(-95.0)
+        fore_flex = (1.0 - fac) * math.radians(95.0)
         pb['UpperArm.R'].rotation_euler = Euler((up_rot, 0.0, up_abd), 'XYZ')
         pb['UpperArm.R'].keyframe_insert(data_path='rotation_euler', frame=f)
 
@@ -473,7 +473,7 @@
         # Natural tucked arm swing: Forearms kept bent at 35°-45°!
         arm_swing_r = math.radians(18.0 * math.cos(phase))
         arm_swing_l = -arm_swing_r
-        forearm_bent = math.radians(-40.0) # tucked forearm bend (35-45°)
+        forearm_bent = math.radians(40.0) # tucked forearm bend (35-45°)
 
         pb['UpperArm.R'].rotation_euler = Euler((arm_swing_r, 0.0, math.radians(12.0)), 'XYZ')
         pb['ForeArm.R'].rotation_euler = Euler((forearm_bent, 0.0, 0.0), 'XYZ')
@@ -520,17 +520,17 @@
 
     jump_timeline = [
         # Frame, Hips_Z, Torso_Pitch, Knee_Flex, Arms_Pitch, Arms_Abd, Forearm_Flex
-        (1,   0.0,    0.0,   0.0,   0.0,    15.0,  -20.0),
-        (8,  -0.08,   10.0,  35.0,  20.0,   12.0,  -25.0),
-        (16, -0.14,   18.0,  65.0,  35.0,   10.0,  -35.0), # Anticipation squash
-        (22,  0.05,    5.0,  15.0, -45.0,   25.0,  -20.0), # Launch thrust
-        (28,  0.30,  -10.0,  60.0, -120.0,  35.0,  -30.0), # Ascending
-        (35,  0.35,  -12.0,  85.0, -145.0,  40.0,  -35.0), # Joyful apex "anime hop"
-        (42,  0.25,   -5.0,  70.0, -130.0,  35.0,  -30.0), # Descending
-        (44,  0.02,    0.0,  20.0,  -80.0,  25.0,  -30.0), # Touchdown
-        (50, -0.10,   10.0,  55.0,  -30.0,  20.0,  -40.0), # Landing cushion
-        (62, -0.02,    3.0,  10.0,  -10.0,  18.0,  -25.0), # Recovery
-        (75,  0.0,     0.0,   0.0,    0.0,  15.0,  -20.0), # Upright settle
+        (1,   0.0,    0.0,   0.0,   0.0,    15.0,  20.0),
+        (8,  -0.08,   10.0,  35.0,  20.0,   12.0,  25.0),
+        (16, -0.14,   18.0,  65.0,  35.0,   10.0,  35.0), # Anticipation squash
+        (22,  0.05,    5.0,  15.0, -45.0,   25.0,  20.0), # Launch thrust
+        (28,  0.30,  -10.0,  60.0, -120.0,  35.0,  30.0), # Ascending
+        (35,  0.35,  -12.0,  85.0, -145.0,  40.0,  35.0), # Joyful apex "anime hop"
+        (42,  0.25,   -5.0,  70.0, -130.0,  35.0,  30.0), # Descending
+        (44,  0.02,    0.0,  20.0,  -80.0,  25.0,  30.0), # Touchdown
+        (50, -0.10,   10.0,  55.0,  -30.0,  20.0,  40.0), # Landing cushion
+        (62, -0.02,    3.0,  10.0,  -10.0,  18.0,  25.0), # Recovery
+        (75,  0.0,     0.0,   0.0,    0.0,  15.0,  20.0), # Upright settle
     ]
 
     for f, hz, t_pitch, knee, arm_p, arm_abd, fore_f in jump_timeline:
@@ -644,6 +644,8 @@
             "Hips.loc_z": [(1, 0.0), (23, 0.006), (45, 0.0), (68, -0.006), (90, 0.0)],
             "Spine1.rot_x": [(1, 0.0), (23, 1.5), (45, 0.0), (68, -1.5), (90, 0.0)],
             "Head.rot_z": [(1, 4.0), (34, 5.2), (56, 4.0), (78, 2.8), (90, 4.0)],
+            "ForeArm.L.rot_x": [(1, 38.0), (45, 38.0), (90, 38.0)],
+            "ForeArm.R.rot_x": [(1, 65.0), (45, 65.0), (90, 65.0)],
         }
     )
 
@@ -655,7 +657,7 @@
         curves={
             "Hips.loc_x": [(1, 0.0), (25, -0.025), (95, -0.025), (120, 0.0)],
             "UpperArm.R.rot_x": [(1, 0.0), (45, -75.0), (95, -75.0), (120, 0.0)],
-            "ForeArm.R.rot_x": [(1, 0.0), (45, -95.0), (95, -95.0), (120, 0.0)],
+            "ForeArm.R.rot_x": [(1, 0.0), (45, 95.0), (95, 95.0), (120, 0.0)],
             "ForeArm.R.rot_y": [(46, 0.0), (50, 18.0), (58, -18.0), (66, 18.0), (74, -18.0), (82, 18.0), (90, -18.0), (95, 0.0)],
             "Hand.R.rot_z": [(46, 0.0), (48, 15.0), (56, -15.0), (64, 15.0), (72, -15.0), (80, 15.0), (88, -15.0), (95, 0.0)],
         }
@@ -671,8 +673,8 @@
             "Thigh.R.rot_x": [(1, -28.0), (8, 5.0), (17, 28.0), (24, -10.0), (32, -28.0)],
             "Thigh.L.rot_x": [(1, 28.0), (8, -10.0), (17, -28.0), (24, 5.0), (32, 28.0)],
             "Hips.rot_z": [(1, -4.0), (8, 2.0), (17, 4.0), (24, -2.0), (32, -4.0)],
-            "ForeArm.R.rot_x": [(1, -40.0), (16, -40.0), (32, -40.0)],
-            "ForeArm.L.rot_x": [(1, -40.0), (16, -40.0), (32, -40.0)],
+            "ForeArm.R.rot_x": [(1, 40.0), (16, 40.0), (32, 40.0)],
+            "ForeArm.L.rot_x": [(1, 40.0), (16, 40.0), (32, 40.0)],
         }
     )
 
@@ -687,6 +689,8 @@
             "UpperArm.R.rot_x": [(1, 0.0), (16, 35.0), (35, -145.0), (50, -30.0), (75, 0.0)],
             "Spine1.rot_x": [(1, 0.0), (16, 18.0), (35, -12.0), (50, 10.0), (75, 0.0)],
             "Head.rot_x": [(1, 0.0), (35, -15.0), (75, 0.0)],
+            "ForeArm.R.rot_x": [(1, 20.0), (16, 35.0), (35, 35.0), (50, 40.0), (75, 20.0)],
+            "ForeArm.L.rot_x": [(1, 20.0), (16, 35.0), (35, 35.0), (50, 40.0), (75, 20.0)],
         }
     )
 
--- a/anime_pipeline/animation/spring_solver.py
+++ b/anime_pipeline/animation/spring_solver.py
@@ -446,12 +446,12 @@
         pitches: Dict[str, float] = {}
 
-        # Forward swing (flexion) is positive pitch
-        thigh_l_fwd = max(0.0, thigh_l_pitch_rad)
-        thigh_r_fwd = max(0.0, thigh_r_pitch_rad)
-
-        # Backward swing (extension) is negative pitch
-        thigh_l_back = max(0.0, -thigh_l_pitch_rad)
-        thigh_r_back = max(0.0, -thigh_r_pitch_rad)
+        # Forward swing (flexion) is negative local X rotation in Anime_Armature
+        thigh_l_fwd = max(0.0, -thigh_l_pitch_rad)
+        thigh_r_fwd = max(0.0, -thigh_r_pitch_rad)
+
+        # Backward swing (extension) is positive local X rotation
+        thigh_l_back = max(0.0, thigh_l_pitch_rad)
+        thigh_r_back = max(0.0, thigh_r_pitch_rad)
 
         # Hip vertical compression adds subtle outward flare
         bounce_flare_rad = max(0.0, -hip_bounce_z * 2.5)
@@ -600,6 +600,7 @@
                 continue
 
-            # In Blender, local X represents pitch for skirt bones
-            euler_rot = Euler((pitch_rad, 0.0, 0.0), 'XYZ')
+            # In Blender, local X represents pitch for skirt bone limit compliance ([-15°, 65°]),
+            # while local Z provides radial flaring outward away from thighs.
+            euler_rot = Euler((pitch_rad, 0.0, -pitch_rad), 'XYZ')
 
             if p_bone.rotation_mode == 'QUATERNION':
--- a/tests/test_m3_animation_pipeline.py
+++ b/tests/test_m3_animation_pipeline.py
@@ -133,5 +133,5 @@
         # Forearm tuck angle (bent 35-45 deg)
         for f, val in act.curves["ForeArm.R.rot_x"]:
-            assert abs(val) >= 35.0 and abs(val) <= 45.0
+            assert val >= 35.0 and val <= 45.0
 
     def test_jump_cheer_kinematic_extremes(self):
--- a/tests/test_m3_challenger_adversarial.py
+++ b/tests/test_m3_challenger_adversarial.py
@@ -295,5 +295,5 @@
                 frozen_forearms[f"{act.name}:{bname}"] = max_abs_rx
 
         # Document that all GLB forearms are locked to <= 0.01 deg
         for bone_act, max_angle in frozen_forearms.items():
-            assert max_angle < 0.01, f"Expected {bone_act} to be frozen at 0° due to baking clamp, but found {max_angle}°"
+            assert max_angle >= 20.0, f"Expected {bone_act} to exhibit active flexion (>= 20°), but found {max_angle}°"
```
