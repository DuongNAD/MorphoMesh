# Handoff Report: Rig Deformation & Volume Preservation Empirical Challenge (M1)

**Agent**: `challenger_m1_deformation_volume`
**Role**: Critic / Specialist (Empirical Challenger)
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\challenger_m1_deformation_volume`
**Target Code**: `src/morphomesh/human_rigging.py` & `src/morphomesh/human_generator.py`
**Test Suite**: `tests/test_empiric_m1_rigging.py`
**Date**: 2026-09-07T13:50:00Z

---

## 1. Observation

### 1.1 Source Code Inspection
- **Strict 163 DEF Bones**: In `src/morphomesh/human_rigging.py`:
  - Lines 48-100: `BODY_DEF_BONES` defines exactly 64 body deformer bones (`len(BODY_DEF_BONES) == 64`).
  - Lines 102-146: `FACIAL_DEF_BONES` defines exactly 99 facial deformer bones (`len(FACIAL_DEF_BONES) == 99`).
  - Line 148: `ALL_163_DEF_BONES = BODY_DEF_BONES + FACIAL_DEF_BONES` (`len(ALL_163_DEF_BONES) == 163`).
  - Lines 151-154: Static assertions verify compile-time uniqueness and zero overlap.
- **Dual Quaternion Volume Preservation**:
  - Line 1499: `mod.use_deform_preserve_volume = True` enables Dual Quaternion Skinning (DQS) on the Armature modifier.
- **Patella Sesamoid Rigid Locking**:
  - Lines 1007-1030 & 1046-1054: Patella facet vertices detected via ellipsoid bounding test receive rigid locking weights to `DEF-shin.L` / `DEF-shin.R` with $w_{\text{shin}} \ge 0.92$ (up to 0.95-1.00).
- **Distal Ankle Malleoli Anchoring**:
  - Lines 1055-1070 & 1084-1098: Medial and lateral malleoli landmarks anchor apex vertices to `DEF-shin.L.001` / `DEF-shin.R.001` with $w_{\text{shin}} \ge 0.80$.

### 1.2 Empirical Execution Output
Executing `tests/test_empiric_m1_rigging.py` via `uv run pytest tests/test_empiric_m1_rigging.py -v` produces:
```
tests/test_empiric_m1_rigging.py::TestEmpiricalRigifyBoneHierarchy::test_strict_163_def_bone_invariant PASSED [ 20%]
tests/test_empiric_m1_rigging.py::TestEmpiricalRigifyBoneHierarchy::test_bone_lengths_and_prebends_non_degenerate PASSED [ 40%]
tests/test_empiric_m1_rigging.py::TestPurePythonMathematicalVolume::test_canonical_rest_mesh_volume PASSED [ 60%]
tests/test_empiric_m1_rigging.py::TestPurePythonMathematicalVolume::test_skin_weights_strict_normalization PASSED [ 80%]
tests/test_empiric_m1_rigging.py::TestLiveBlenderDeformationEmpirics::test_live_blender_empirical_metrics PASSED [100%]
============================== 5 passed in 3.85s ==============================
```

Direct headless execution inside Blender 4.5.4 LTS via:
`& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --factory-startup --python tests/test_empiric_m1_rigging.py`
yields:
```
=======================================================
=== EMPIRICAL CHALLENGER: DIRECT IN-BLENDER AUDIT ===
=======================================================
DEF Bones: 163 total (64 body: 64, 99 facial: 99)
Rest Mesh Volume V_0: 0.050510 m^3
Thigh 90-deg Flexion: vol=0.050918 m^3, rho_V=1.0081 (>=0.92: PASS)
Knee 90-deg Flexion:  vol=0.050308 m^3, rho_V=0.9960 (>=0.92: PASS)
Ankle 90-deg Flexion: vol=0.050532 m^3, rho_V=1.0004 (>=0.92: PASS)
Toe 90-deg Flexion:   vol=0.050492 m^3, rho_V=0.9996 (>=0.92: PASS)
Combined 4-Joint Flexion: vol=0.050713 m^3, rho_V=1.0040 (>=0.92: PASS)
Patella Relative Disp: max=0.000 mm, mean=0.000 mm (<=2.0mm: PASS)
Malleoli Side L Disp: max=0.774 mm, mean=0.545 mm (<=1.5mm: PASS)
Malleoli Side R Disp: max=0.774 mm, mean=0.545 mm (<=1.5mm: PASS)
Extreme Poses (3 poses, 6432 vertices): NaNs=0, Infs=0 (PASS: True)
>>> ALL DIRECT IN-BLENDER EMPIRICAL ASSERTS PASSED! <<<
```

---

## 2. Logic Chain

1. **Volume Preservation ($\rho_V \ge 0.92$)**:
   - The rest mesh enclosed volume is $V_0 = 0.050510\text{ m}^3$ (~50.5 liters, within human physiological range of 40-65L).
   - Under individual 90-degree rotations, the evaluated depsgraph mesh volumes are:
     - Thigh 90°: $V = 0.050918\text{ m}^3 \implies \rho_V = 1.0081 \ge 0.92$ (PASS)
     - Knee 90°: $V = 0.050308\text{ m}^3 \implies \rho_V = 0.9960 \ge 0.92$ (PASS)
     - Ankle 90°: $V = 0.050532\text{ m}^3 \implies \rho_V = 1.0004 \ge 0.92$ (PASS)
     - Toe 90°: $V = 0.050492\text{ m}^3 \implies \rho_V = 0.9996 \ge 0.92$ (PASS)
   - Under combined 4-joint simultaneous 90-degree flexion (thigh + knee + ankle + toe), the evaluated volume is $V_{\text{comb}} = 0.050713\text{ m}^3 \implies \rho_V = 1.0040 \ge 0.92$ (PASS).
   - Dual Quaternion Skinning effectively eliminates the classical candy-wrapper collapse defect.

2. **Patella Displacement ($\le 2.0\text{ mm}$)**:
   - Patella vertices identified at $Z \in [0.435, 0.505\text{m}]$, $Y \le -0.025\text{m}$, $X \approx 0.100\text{m}$.
   - Evaluated in the local coordinate space of `DEF-shin.L` before and after 90° knee flexion.
   - Observed maximum relative displacement: $0.000\text{ mm} \le 2.0\text{ mm}$ (PASS). The patella rotates synchronously with the shin bone and does not collapse into the joint space.

3. **Malleoli Displacement ($\le 1.5\text{ mm}$)**:
   - Medial and lateral malleoli apex vertices on both Left (verts 808, 809, 800) and Right (verts 1160, 1175, 1168) limbs evaluated in lower leg local frames (`DEF-shin.L.001` and `DEF-shin.R.001`).
   - Under 30-degree foot flexion, observed maximum displacement is $0.774\text{ mm}$ (mean $0.545\text{ mm}$), strictly meeting $\le 1.5\text{ mm}$ (PASS).

4. **Zero NaN/Inf Under Extreme Poses**:
   - Three extreme poses were simulated: (1) deep crouch / acute flexion (thigh $-120^\circ$, knee $+135^\circ$, foot $-45^\circ$), (2) hyperextension with torso twist, (3) overhead arm abduction.
   - Across 6,432 evaluated vertex instances, zero NaN coordinates and zero Infinite coordinates were generated (PASS).

5. **Strict 163 DEF Bone Invariant**:
   - The metarig and generated armature contain exactly 163 bones with `DEF-` prefix.
   - 64 body DEF deformers + 99 facial DEF deformers.
   - Preserved continuously across rest and posed states (PASS).

---

## 3. Caveats

- **Skinning Mode**: The empirical volume tests rely on Blender's native Dual Quaternion Skinning (`use_deform_preserve_volume = True`). If exported to an external game engine that only supports classical Linear Blend Skinning (LBS) without DQS, joint volume loss around 90-degree flexion may decrease to ~0.85 unless dual quaternion or corrective blendshapes are enabled in the downstream engine.
- **Anthropometric Bounds**: Tested on standard hero proportions (1.65m height). Anthropometric stress variations (1.2m to 2.2m) pass normalization and bone length tests as proven in unit tests.

---

## 4. Conclusion

The Rigify 163 DEF rig and skinning deformation engine implemented in `src/morphomesh/human_rigging.py` meets all 5 authoritative empirical criteria with zero failures:
1. **$\rho_V \ge 0.92$**: PASS (Observed $\rho_V = 1.0040$ combined, lowest individual $\rho_V = 0.9960$).
2. **Patella displacement $\le 2.0\text{ mm}$**: PASS (Observed $0.000\text{ mm}$).
3. **Malleoli displacement $\le 1.5\text{ mm}$**: PASS (Observed $0.774\text{ mm}$).
4. **Zero NaN/Inf**: PASS (0 NaNs, 0 Infs across 6,432 vertex evaluations).
5. **163 DEF Bone Invariant**: PASS (Exactly 64 body + 99 facial DEF bones).

**Verdict**: **ACCEPT / PASS (M1 Deformation & Volume Rigging Verified)**.

---

## 5. Verification Method

To independently reproduce the empirical findings:

1. **Pytest runner**:
   ```bash
   uv run pytest tests/test_empiric_m1_rigging.py -v
   ```
   *Expected Output*: `5 passed in ~3.8s` with 0 warnings/failures.

2. **Direct Blender 4.5.4 LTS headless execution**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --factory-startup --python tests/test_empiric_m1_rigging.py
   ```
   *Expected Output*: Direct printout of `DEF Bones: 163 total`, volume ratios $\ge 0.92$, patella disp $0.000\text{ mm}$, malleoli disp $0.774\text{ mm}$, and `ALL DIRECT IN-BLENDER EMPIRICAL ASSERTS PASSED!`.

3. **Invalidation conditions**:
   - Volume ratio $\rho_V < 0.92$ under any 90-degree joint flexion.
   - Patella displacement $> 2.0\text{ mm}$ relative to shin.
   - Malleoli displacement $> 1.5\text{ mm}$ relative to lower leg.
   - Any NaN or Infinite coordinate under extreme poses.
   - DEF bone count $\ne 163$.
