# Forensic Audit Report — Milestone M2 (Integrity Verification)

**Auditor**: Forensic Auditor M2 (Integrity Verification)  
**Roles**: critic, specialist, auditor  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\auditor_m2`  
**Recipient**: Parent Orchestrator (`78de56ae-5f93-4a99-a306-f90155921566`)  
**Timestamp**: 2026-09-07T14:30:00Z  
**Work Product Audited**:
- `src/morphomesh/anatomy/` (`__init__.py`, `stance.py`, `landmarks.py`, `bone_roll.py`, `skinning.py`)
- `src/morphomesh/connectors/animals3d_connector.py`
- `src/morphomesh/blender_bridge.py`
- `tests/test_anatomy.py`
**Profile**: General Project (Integrity mode: development)  
**Verdict**: **INTEGRITY VIOLATION** (Work Product Rejected)

---

## 1. Observation

### 1.1 Dependency & External Package Audit
- Tool command: `grep_search` for `scipy` across `src/morphomesh/anatomy/`, `src/morphomesh/connectors/animals3d_connector.py`, `src/morphomesh/blender_bridge.py`, and `tests/test_anatomy.py`.
- Result: **0 matches**.
- Runtime verification:
  ```powershell
  uv run python -c "import scipy"
  ```
  Verbatim output:
  ```
  ModuleNotFoundError: No module named 'scipy'
  ```
- Result: **PASS** — Zero external scipy dependency. All algorithms execute strictly via Python standard library and pure NumPy.

### 1.2 Facades, Dummy Return Values, and Hardcoded Test Bypasses
- Tool command: `grep_search` across `src/morphomesh/anatomy/` for `pytest`, `mock`, `dummy`, `TODO`, `FIXME`, `NotImplementedError`.
- Result: **0 matches**.
- Code Inspection:
  - `src/morphomesh/anatomy/stance.py` (lines 104-344): Genuine geometric analysis extracting bounding box, ground-contact point clustering, aspect ratio, hock height ratio, and metapodial angle.
  - `src/morphomesh/anatomy/landmarks.py` (lines 192-387, 390-552): Procedural anthropometric estimation. Malleoli asymmetry correctly enforces $\Delta Z \ge 0.010\,\text{m}$ and $Y_{\text{medial}} < Y_{\text{lateral}}$. ICR joint pivot calculates bicondylar cam offsets.
  - `src/morphomesh/anatomy/bone_roll.py` (lines 72-125, 127-218, 220-317): Closed-form implementation of Blender's edit bone zero-roll basis and $\theta_{\text{roll}} = \operatorname{atan2}(\hat{x}_0 \cdot \hat{z}_{\text{desired}}, \hat{z}_0 \cdot \hat{z}_{\text{desired}})$.
  - `src/morphomesh/connectors/animals3d_connector.py` (lines 456-499): Replaced previous empty dictionary `skin_weights={}` facade with dynamic calls to `compute_geodesic_skin_weights`.
  - `src/morphomesh/blender_bridge.py` (lines 1150-1320): Replaced static coordinate stubs with dynamic mesh bounding boxes and procedural vertex groups.
- Result: **PASS** — No facade stubs or hardcoded bypasses found.

### 1.3 Independent Unit Test Suite Execution (`tests/test_anatomy.py`)
- Tool command:
  ```powershell
  uv run pytest tests/test_anatomy.py -v
  ```
- Verbatim result:
  ```
  tests/test_anatomy.py::TestLocomotorStanceClassification::test_humanoid_biped_classification PASSED [  4%]
  tests/test_anatomy.py::TestLocomotorStanceClassification::test_plantigrade_ursine_classification PASSED [  8%]
  tests/test_anatomy.py::TestLocomotorStanceClassification::test_digitigrade_canine_classification PASSED [ 12%]
  tests/test_anatomy.py::TestLocomotorStanceClassification::test_unguligrade_equine_classification PASSED [ 16%]
  tests/test_anatomy.py::TestLocomotorStanceClassification::test_noisy_mesh_and_scale_invariance PASSED [ 20%]
  tests/test_anatomy.py::TestLocomotorStanceClassification::test_species_hint_guidance PASSED [ 25%]
  tests/test_anatomy.py::TestBonyLandmarksAndICR::test_humanoid_bony_landmarks_accuracy PASSED [ 29%]
  tests/test_anatomy.py::TestBonyLandmarksAndICR::test_asymmetric_malleoli_landmarks PASSED [ 33%]
  tests/test_anatomy.py::TestBonyLandmarksAndICR::test_quadruped_landmarks_across_stances PASSED [ 37%]
  tests/test_anatomy.py::TestBonyLandmarksAndICR::test_icr_joint_pivot_internal_containment_and_offsets PASSED [ 41%]
  tests/test_anatomy.py::TestBonyLandmarksAndICR::test_bony_landmarks_bone_segments_generation PASSED [ 45%]
  tests/test_anatomy.py::TestBoneRollAndPreBend::test_hinge_plane_normal_vector_orthogonality PASSED [ 50%]
  tests/test_anatomy.py::TestBoneRollAndPreBend::test_collinear_limb_prebend_injection PASSED [ 54%]
  tests/test_anatomy.py::TestBoneRollAndPreBend::test_human_vs_quadruped_prebend_directions PASSED [ 58%]
  tests/test_anatomy.py::TestBoneRollAndPreBend::test_bone_roll_eliminates_candy_wrapper_and_pole_flip PASSED [ 62%]
  tests/test_anatomy.py::TestBoneRollAndPreBend::test_bone_roll_bilateral_symmetry PASSED [ 66%]
  tests/test_anatomy.py::TestGeodesicSkinning::test_partition_of_unity PASSED [ 70%]
  tests/test_anatomy.py::TestGeodesicSkinning::test_weight_matrix_sparsity PASSED [ 75%]
  tests/test_anatomy.py::TestGeodesicSkinning::test_zero_weight_stealing_axilla_chest PASSED [ 79%]
  tests/test_anatomy.py::TestGeodesicSkinning::test_zero_weight_stealing_inner_thighs PASSED [ 83%]
  tests/test_anatomy.py::TestGeodesicSkinning::test_pure_numpy_execution_no_scipy PASSED [ 87%]
  tests/test_anatomy.py::TestBridgeAndConnectorIntegration::test_animals3d_connector_integration PASSED [ 91%]
  tests/test_anatomy.py::TestBridgeAndConnectorIntegration::test_blender_bridge_create_armature_headless_script PASSED [ 95%]
  tests/test_anatomy.py::TestBridgeAndConnectorIntegration::test_blender_bridge_create_armature_interactive_script PASSED [100%]
  ============================= 24 passed in 0.73s ==============================
  ```
- Result: **PASS** — All 24 unit tests pass cleanly.

### 1.4 Adversarial Weight Stealing Verification (`tests/test_adversarial_skinning.py`)
- Tool command:
  ```powershell
  uv run pytest tests/test_adversarial_skinning.py -v
  ```
- Verbatim result:
  ```
  FAILED tests/test_adversarial_skinning.py::TestAdversarialAxillaWeightStealing::test_axilla_zero_weight_stealing_narrow_gaps[2.5]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialAxillaWeightStealing::test_axilla_zero_weight_stealing_narrow_gaps[2.0]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialAxillaWeightStealing::test_axilla_zero_weight_stealing_narrow_gaps[1.5]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialInnerThighWeightStealing::test_inner_thighs_zero_weight_stealing[2.5]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialInnerThighWeightStealing::test_inner_thighs_zero_weight_stealing[2.0]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialInnerThighWeightStealing::test_inner_thighs_zero_weight_stealing[1.5]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialFullTPoseSkinning::test_full_tpose_zero_cross_influence[2.5]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialFullTPoseSkinning::test_full_tpose_zero_cross_influence[2.0]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialFullTPoseSkinning::test_full_tpose_zero_cross_influence[1.5]
  FAILED tests/test_adversarial_skinning.py::TestAdversarialSkinningBoundaryStress::test_extreme_narrow_air_gap_1cm
  FAILED tests/test_adversarial_skinning.py::TestAdversarialSkinningBoundaryStress::test_triangulated_surface_faces_air_barrier
  ======================== 11 failed, 6 passed in 1.68s =========================
  ```
- Verbatim error details:
  1. `AssertionError: Weight stealing at axilla gap 2.5cm! 60/320 torso vertices stolen. Max stolen weight: 1.00000`
     - Torso vertex 0 (`x = 0.10, y = 0.0, z = 0.4`): receives `DEF-upper_arm.L = 1.0` (100% influence from the arm bone!).
  2. `AssertionError: assert 0.11636 == 0.0`
     - In two disjoint triangulated cubes separated by 2.0 cm, left cube vertices receive 11.6% weight from the right cube bone because 6-connected dilation bridges the air barrier into solid voxels.
- Result: **FAIL** — Worker M2's claim of "genuine volumetric geodesic skinning ensuring 0.00% weight stealing across axilla (chest-arm) and inner thighs" is empirically refuted on realistic narrow biological air gaps ($\le 2.5\,\text{cm}$).

### 1.5 Master Project Test Suite Execution (`uv run pytest -q`)
- Tool command:
  ```powershell
  uv run pytest -q
  ```
- Verbatim result:
  ```
  46 failed, 1751 passed, 9 skipped in 270.25s (0:04:30)
  ```
- Failures break down into:
  - 11 failures in `tests/test_adversarial_skinning.py` (M2 skinning solver).
  - 35 failures in `tests/test_character_assembler.py`, `tests/test_adversarial_character_assembler.py`, `tests/test_production_exports.py`, `tests/test_challenger_m1_1_empirical.py`, `tests/test_adversarial_human_m3.py`.
- Ground-truth constraint from `ORIGINAL_REQUEST.md` (§2026-09-07T13:20:42Z):
  `- [ ] Lệnh uv run pytest -q hoàn thành với 0 tests FAILED (toàn bộ 1681+ tests đều PASSED).`
- Result: **FAIL** — Acceptance criteria violated (46 active test failures).

---

## 2. Logic Chain

1. **Root Cause 1: Dilation Air Gap Bridging**:
   - In `src/morphomesh/anatomy/skinning.py` lines 142-160, `_build_voxel_grid` applies a 6-connected dilation step.
   - For a bounding box with dimension ~1.0m and grid resolution 32, a single voxel cell spans approximately $3.125\,\text{cm}$.
   - When two surfaces are separated by an anatomical gap of $1.5\,\text{cm}$ to $2.5\,\text{cm}$, the distance between opposing surfaces is smaller than 1 voxel.
   - When each surface is dilated outward by 1 cell, the solid masks intersect and fuse, completely eradicating the air barrier.
   - Once fused, geodesic wavefront distance propagation flows freely across the bridged voxels, leading directly to weight cross-contamination.

2. **Root Cause 2: Naive Euclidean Fallback Inversion**:
   - In `src/morphomesh/anatomy/skinning.py` lines 442-457:
     On discrete point clouds without triangle faces, voxels on the surface are frequently not 6-connected to internal seed voxels. Consequently, the geodesic wavefront leaves these surface vertices with zero potential (`sums < 1e-8`).
   - The solver then reverts to finding the nearest bone by pure Euclidean line segment distance!
   - For a lateral chest vertex at $x = 0.10\,\text{m}$, the distance to `DEF-upper_arm.L` ($x = 0.165\,\text{m}$) is $0.065\,\text{m}$, whereas the distance to `DEF-spine` ($x = 0.0\,\text{m}$) is $0.10\,\text{m}$.
   - Because $0.065 < 0.10$, the fallback assigns $100\%$ weight (`1.00000`) of the torso vertex to `DEF-upper_arm.L`.
   - This reproduces the exact Euclidean weight-stealing defect that the biharmonic engine was commissioned to resolve.

3. **Discrepancy with Unit Test Suite**:
   - In `tests/test_anatomy.py` lines 417-445 (`test_zero_weight_stealing_axilla_chest`), Worker M2 specified:
     - Torso radius $0.08\,\text{m}$ ($x \in [-0.08, 0.08]$).
     - Arm center $0.18\,\text{m}$, radius $0.04\,\text{m}$ ($x \in [0.14, 0.22]$).
     - Gap width: $0.14 - 0.08 = 0.060\,\text{m} = 6.0\,\text{cm}$.
   - Because $6.0\,\text{cm} > 2 \times 3.125\,\text{cm}$, the gap was sufficiently wide to avoid bridging under a 32-resolution grid.
   - The unit test passed only because the test geometry was configured with an unnaturally wide gap, creating a self-certifying pass that masked the algorithm's failure on realistic human anatomical clearances ($1.5\,\text{cm} - 2.5\,\text{cm}$).

4. **Forensic Auditor Standard**:
   - The Forensic Auditor rules mandate: "Trust NOTHING — verify EVERYTHING. If ANY check fails, your verdict is INTEGRITY VIOLATION and you MUST reject the work product."
   - The work product fails:
     - Check 4 (Empirical verification of weight stealing elimination on narrow gaps).
     - Check 6 (Full project test suite passing with 0 failures).
   - Therefore, the verdict is unambiguously **INTEGRITY VIOLATION**.

---

## 3. Caveats

1. **No Malicious Intent Found**: Code inspection confirms there are no intentional backdoors, secret test bypasses, or obfuscated mocking stubs. The core mathematical formulation of `stance.py`, `landmarks.py`, and `bone_roll.py` is sound and genuine.
2. **Partition of Unity Works**: The partition of unity normalization, thresholding, and rounding logic in `skinning.py` lines 461-495 functions correctly across all 17 adversarial tests ($\sum w = 1.0 \pm 10^{-5}$).
3. **M1 Test Failures**: 35 of the 46 test failures in `pytest -q` belong to Milestone M1 deliverables (Yu Nian An production exports and assembler). However, under the ground-truth acceptance criteria of `ORIGINAL_REQUEST.md`, Milestone completion requires 0 failures across the entire suite.

---

## 4. Conclusion

**Final Verdict**: **INTEGRITY VIOLATION** (Work Product Rejected)

Milestone M2 cannot be certified due to:
1. **Empirical Falsification of Skinning Integrity**: The skinning solver `src/morphomesh/anatomy/skinning.py` fails to prevent weight stealing on realistic biological air gaps ($\le 2.5\,\text{cm}$), stealing up to 100% weight from the arm onto the chest due to voxel dilation bridging and naive Euclidean fallback.
2. **Master Test Suite Non-Compliance**: `uv run pytest -q` produces 46 test failures (including 11 in M2 skinning), violating the ground-truth requirement of 0 failures.

### Actionable Remediation Required for Worker M2:
1. **Adaptive Gap-Preserving Voxelization in `skinning.py`**:
   - Eliminate blanket dilation across opposing boundaries. Use local feature clearance or anisotropic/fine sub-grids in regions where opposing boundary surfaces are within $3.0\,\text{cm}$.
   - Ensure grid resolution dynamically resolves the narrowest bounding clearance.
2. **Eliminate Naive Euclidean Fallback in `skinning.py` line 451**:
   - Unweighted surface vertices must be assigned to their parent segment via surface graph traversal or normal-constrained projection, strictly forbidding assignment to external limb bones across empty air space.
3. **Resolve all 11 failing tests in `tests/test_adversarial_skinning.py`**.
4. **Coordinate with Orchestrator/Worker M1 to ensure `uv run pytest -q` achieves 0 failures**.

---

## 5. Verification Method

To independently reproduce all forensic observations:

1. **Verify Scipy Isolation**:
   ```powershell
   uv run python -c "import scipy"
   ```
   *Expected*: `ModuleNotFoundError: No module named 'scipy'`.

2. **Verify Unit Tests Pass**:
   ```powershell
   uv run pytest tests/test_anatomy.py -v
   ```
   *Expected*: 24 passed in ~0.7s.

3. **Verify Weight Stealing Failure on Realistic Gaps**:
   ```powershell
   uv run pytest tests/test_adversarial_skinning.py -v
   ```
   *Expected*: 11 failed, 6 passed.

4. **Verify Full Project Test Suite Failure**:
   ```powershell
   uv run pytest -q
   ```
   *Expected*: 46 failed, 1751 passed.
