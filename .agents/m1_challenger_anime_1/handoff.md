# Adversarial Challenge Report & Handoff: Milestone 1 — Geometry & Mesh Stress

**Challenger**: `m1_challenger_anime_1` (Empirical Challenger: Critic & Specialist)  
**Target Milestone**: Milestone 1: Anime Mesh Synthesis & Anatomy Topology  
**Target Modules**: `anime_pipeline/mesh/generator.py`, `anime_pipeline/mesh/topology_cleaner.py`  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m1_challenger_anime_1`  
**Target Project**: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`  
**Date**: 2026-09-09  
**Final Verdict**: **`REQUEST_CHANGES`** (Actionable Blocking Defects Found)  

---

## Challenge Summary

- **Overall Risk Assessment**: **CRITICAL**
- **Test Execution Summary**: `uv run pytest tests/test_m1_adversarial_stress.py -v`
  - **Total Adversarial Tests**: 18
  - **Passed**: 10
  - **Failed**: 8
  - **Pass Rate**: 55.6%

### Core Findings Matrix

| Ref | Finding | Severity | Blast Radius | Status |
|---|---|---|---|---|
| **C1** | True 3D Skirt Clearance drops to 6.41mm (nominal) and 1.14mm (+10% girth), violating $\ge 15\text{mm}$ requirement | **CRITICAL** | Pelvis & thigh mesh penetration during animation; cloth clipping | **REPRODUCED & BLOCKS** |
| **C2** | Catastrophic Shoe-Foot Spatial Misalignment (165.7mm displacement; shoes float in mid-air between legs) | **CRITICAL** | Milestone 2 Rigging failure; foot bones outside shoes; broken skin weights | **REPRODUCED & BLOCKS** |
| **C3** | Skeletal Joint Landmarks (Ankle off by 128.8mm, Knee off by 61.3mm) | **HIGH** | M2 Armature generation will place leg/foot bones in wrong positions | **REPRODUCED & BLOCKS** |
| **C4** | Desynchronized Ground Sole Z Translation (`ground_sole_z` lifts shoes, leaves feet at Z=0) | **HIGH** | Sole-foot penetration if ground elevation changes | **REPRODUCED & BLOCKS** |
| **C5** | `TopologyValidator.audit_mesh()` crashes with unhandled `ValueError`/`OverflowError` on NaN/Inf floats | **MEDIUM** | Inability to audit corrupt mesh buffers | **REPRODUCED** |
| **C6** | Dead/Ignored Configuration Parameters in `AnimeMeshConfig` (`skirt_clearance_mm`, `twintail_segments`) | **LOW** | Parameter changes have zero effect on generated geometry | **CONFIRMED** |

---

## 1. Observation

### 1.1 Skirt Clearance Invariant Failure
- **Contract Requirement**: `PROJECT.md` line 103:
  > "`Anime_Skirt`: Pleated A-line skirt with $+15\text{mm}$ clearance above thighs."
- **Worker Claim**: `E:\tool\mcp\MorphoMesh\.agents\m1_worker_anime_1\handoff.md` lines 66 & 101:
  > "Minimum 3D clearance across all thigh vertices within skirt height: **+19.87 mm** (exceeds +15.0 mm threshold)"
- **Empirical Execution**:
  Command executed:
  ```bash
  uv run pytest tests/test_m1_adversarial_stress.py -k "skirt_clearance" -v
  ```
  Output verbatim:
  ```
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_skirt_clearance_nominal_15mm_invariant - AssertionError: Nominal skirt clearance 6.41mm violates required >=15.0mm threshold!
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_skirt_clearance_under_thigh_girth_variations[1.0] - AssertionError: Under thigh girth scale 100%, skirt clearance 10.75mm fell below 15.0mm!
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_skirt_clearance_under_thigh_girth_variations[1.05] - AssertionError: Under thigh girth scale 105%, skirt clearance 5.63mm fell below 15.0mm!
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_skirt_clearance_under_thigh_girth_variations[1.1] - AssertionError: Under thigh girth scale 110%, skirt clearance 1.14mm fell below 15.0mm!
  ```
- **Geometry Inspection**:
  - In `generator.py` lines 435-440:
    ```python
    rx_waist = 0.185 * s
    rx_hem = 0.285 * s
    ry_waist = 0.155 * s
    ry_hem = 0.235 * s
    amp_waist = 0.006 * s
    amp_hem = 0.022 * s
    ```
  - The skirt waist is elliptical with semi-axes $R_x = 0.185\text{m}, R_y = 0.155\text{m}$, while the character's hips and upper thighs (`Anime_Torso` and `Anime_Legs`) extend to $X = \pm 0.192\text{m}$ at $Z \approx 0.75\text{m}$.
  - At vertex `(0.15422, -0.08875, 0.86125)` in `Anime_Torso`, the true minimum 3D surface distance to the skirt is only **6.41 mm**.
  - At vertex `(0.17289, -0.09938, 0.75415)` in `Anime_Legs`, the true minimum 3D surface distance to the skirt is only **10.75 mm**.
  - Worker's "+19.87 mm" was empirically traced to comparing skirt waist vertices ($Z=0.88\text{m}$) against ankle/foot vertices ($Z \approx 0.01\text{m}$), e.g. skirt vertex `(0.17827, -0.03466, 0.88)` against foot vertex `(0.19378, -0.02219, 0.01713)`, yielding an invalid horizontal projection delta of $19.87\text{mm}$.

### 1.2 Catastrophic Shoe-Foot Spatial Misalignment
- **Contract Requirement**: `PROJECT.md` line 104:
  > "`Anime_Shoes`: Loafers/boots with flat ground-plane sole at $Z = 0.0$."
  And `ORIGINAL_REQUEST.md`: "bàn chân có khớp cổ chân và ngón chân tiếp đất tự nhiên... không có hiện tượng bẹp đế giày...".
- **Empirical Execution**:
  Command executed:
  ```bash
  uv run pytest tests/test_m1_adversarial_stress.py -k "test_adversarial_shoes_foot_containment_and_alignment" -v
  ```
  Output verbatim:
  ```
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_shoes_foot_containment_and_alignment
  AssertionError: Catastrophic shoe-foot misalignment: Left shoe center (0.0880, -0.0350) is displaced 165.7mm from anatomical foot center (0.2263, -0.1262)!
  assert 0.16565585570343047 <= 0.03
  ```
- **Geometry Inspection**:
  - In `generator.py` line 564:
    ```python
    cx = 0.088 * side * s
    ```
    `Anime_Shoes` is hardcoded to be centered at $X = \pm 0.088\text{m}$, spanning $X \in [0.0430, 0.1330]\text{m}$ for the Left shoe.
  - In `Anime_Legs` (partitioned from `data/templates/makehuman_clean_body.obj`), the actual Left foot ground vertices span $X \in [0.1748, 0.2642]\text{m}$, with center of mass at $(0.2263, -0.1262, 0.0194)\text{m}$.
  - The right edge of the Left shoe is at $X = 0.1330\text{m}$, while the inner edge of the foot is at $X = 0.1748\text{m}$.
  - **There is an empty air gap of 4.18 cm** between the shoe and the foot. 100% of the 2,094 foot vertices in `Anime_Legs` protrude completely outside the bounding box of `Anime_Shoes`. The shoes float in empty space between the character's legs.

### 1.3 Skeletal Landmark Discrepancies
- **Empirical Execution**:
  ```bash
  uv run pytest tests/test_m1_adversarial_stress.py -k "test_adversarial_landmark_alignment_with_mesh_geometry" -v
  ```
  Output verbatim:
  ```
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_landmark_alignment_with_mesh_geometry
  AssertionError: Ankle landmark X=0.0900 deviates 128.8mm from mesh ankle center X=0.2188!
  assert 0.1287876388888889 < 0.03
  ```
- In `generator.py._extract_landmarks()`, fallback coordinates assume straight vertical legs:
  - `knee_L`: $(0.090, -0.030, 0.440)$ — actual mesh knee center is $(0.1513, -0.0234, 0.4402)$ (error: $61.3\text{mm}$).
  - `ankle_L`: $(0.090, -0.020, 0.080)$ — actual mesh ankle center is $(0.2188, -0.0190, 0.0787)$ (error: $128.8\text{mm}$).

### 1.4 Desynchronized Sole Grounding
- **Empirical Execution**:
  ```bash
  uv run pytest tests/test_m1_adversarial_stress.py -k "test_adversarial_ground_sole_z_offset_coincidence" -v
  ```
  Output verbatim:
  ```
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_ground_sole_z_offset_coincidence
  AssertionError: Desynchronized sole grounding: Shoes min Z=0.0500m but Legs min Z=0.0000m
  ```
- In `generator.py` line 340: `scaled_verts = [(v[0] * s, v[1] * s, v[2] * s) for v in raw_verts]`.
  The `ground_sole_z` parameter is added to shoe Z-coordinates (line 569), but is not applied to the anatomical base mold. If `ground_sole_z > 0`, feet penetrate through the bottom of the shoes.

### 1.5 TopologyValidator Crash on NaN/Inf
- **Empirical Execution**:
  ```bash
  uv run pytest tests/test_m1_adversarial_stress.py -k "test_adversarial_topology_validator_nan_inf_robustness" -v
  ```
  Output verbatim:
  ```
  FAILED tests\test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_topology_validator_nan_inf_robustness
  Failed: TopologyValidator crashed on NaN vertices: ValueError: cannot convert float NaN to integer
  ```
- In `topology_cleaner.py` line 189: `cx = int(math.floor(x * inv_eps))`. Passing `float('nan')` causes an unhandled `ValueError: cannot convert float NaN to integer`. Passing `float('inf')` causes `OverflowError: cannot convert float infinity to integer`.

### 1.6 Successful Invariants Verified (10/18 Tests Passed)
- Uniform height scaling in range $[1.45\text{m}, 1.75\text{m}]$ preserves exact $1:6.68$ Bishoujo head ratio across all scales.
- Seam coincident boundary loops remain invariant across all heights: 46 neck vertices, 92 shoulder vertices, 50 hip vertices.
- Mesh vertex arrays are free of duplicate vertices and degenerate faces across the standard height range $[1.45\text{m}, 1.75\text{m}]$.
- All 7 sub-meshes exhibit 100% 2-manifold pure quads with zero non-manifold edges.

---

## 2. Logic Chain

1. **Premise 1**: Feature F01 & Interface Contract M1 ↔ M2 require discrete sub-meshes where accessories enclose and align with anatomical counterparts. Specifically, `Anime_Skirt` must clear thighs by $\ge 15\text{mm}$, and `Anime_Shoes` must envelope the feet at the ground plane.
2. **Observation (1.1)**: Direct 3D distance evaluation between `Anime_Skirt` polygons and body vertices reveals a minimum clearance of $6.41\text{mm}$ to the lower pelvis/torso and $10.75\text{mm}$ to the upper thighs at nominal scale. Under an edge-case $+10\%$ thigh girth expansion, clearance drops to $1.14\text{mm}$.
3. **Inference 1**: The current skirt radii ($rx_{waist}=0.185\text{m}, ry_{waist}=0.155\text{m}$) are too tight for the base mold's actual pelvis/thigh dimensions ($X \approx 0.192\text{m}$). During joint flexion or animation, clothing will clip through the body.
4. **Observation (1.2)**: `Anime_Shoes` is synthesized centered at $X = \pm 0.088\text{m}$, while `Anime_Legs` ground foot vertices are centered at $X = \pm 0.2263\text{m}$.
5. **Inference 2**: The shoes are displaced by $16.57\text{cm}$ in 3D from the feet. The shoes do not envelope the feet; they float in the empty space between the legs.
6. **Observation (1.3)**: Skeletal landmarks for ankles and knees are off by $12.9\text{cm}$ and $6.1\text{cm}$ respectively.
7. **Inference 3**: In Milestone 2, automated bone placement relying on these landmarks will generate an armature whose leg bones do not align with the mesh, or whose foot bones align with empty space, causing catastrophic skinning artifacts.
8. **Deduction**: Because C1, C2, and C3 directly break Milestone 1 acceptance criteria and will cause Milestone 2 to fail, Milestone 1 cannot be approved in its current state. The explicit verdict is `REQUEST_CHANGES`.

---

## 3. Caveats

1. **Adversarial Test Location**: Per Project Layout Compliance rules, tests were authored in `teamwork_projects/anime_character_pipeline/tests/test_m1_adversarial_stress.py` so they can be run via standard `pytest` without placing tests in `.agents/`.
2. **Dynamic Physics**: Clearance was evaluated statically in rest pose. Dynamic cloth collisions and spring bone deformation will be audited in Milestones 2 and 3.
3. **No other caveats.**

---

## 4. Conclusion & Required Remediations

**Verdict**: **`REQUEST_CHANGES`**

Milestone 1 shows high topological quality in pure quad extraction, seam coincident loops, and Bishoujo proportions. However, it contains two critical geometric blockers and two high-severity data defects that must be resolved by `m1_worker_anime_1`:

### Required Remediations for `m1_worker_anime_1`:

1. **Fix Skirt Clearance (Mandatory)**:
   - In `generator.py._synthesize_skirt()`:
     - Increase waist elliptical radii to guarantee $\ge 15.0\text{mm}$ clearance everywhere:
       - Set $rx_{waist} \ge 0.212 \times s$ (current $0.185 \times s$ is smaller than hip width $0.192 \times s$).
       - Set $ry_{waist} \ge 0.175 \times s$.
       - Set $rx_{hem} \ge 0.315 \times s$ and $ry_{hem} \ge 0.255 \times s$.
     - Wire `self.cfg.skirt_clearance_mm` to dynamically add an offset to $rx_{waist}, ry_{waist}, rx_{hem}, ry_{hem}$.
2. **Fix Shoe Position & Alignment (Mandatory)**:
   - In `generator.py._synthesize_shoes()`:
     - Determine lateral shoe position dynamically from `Anime_Legs` foot vertices, or set $cx = 0.226 \times s$ (or $\text{sign} \times 0.226 \times s$) and $cy = -0.040 \times s$.
     - Ensure the shoe bounds completely enclose the foot vertices in `Anime_Legs`.
     - Synchronize `ground_sole_z`: if non-zero, translate the entire anatomical mold or account for sole thickness.
3. **Fix Joint Landmarks (Mandatory)**:
   - In `generator.py._extract_landmarks()`:
     - Update `knee_L` to $(0.151 \times s, -0.023 \times s, 0.440 \times s)$ and `knee_R` to $(-0.151 \times s, -0.023 \times s, 0.440 \times s)$.
     - Update `ankle_L` to $(0.219 \times s, -0.019 \times s, 0.079 \times s)$ and `ankle_R` to $(-0.219 \times s, -0.019 \times s, 0.079 \times s)$.
4. **Fix `TopologyValidator` Robustness**:
   - In `topology_cleaner.py.detect_duplicates()`:
     - Add check: `if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)): continue` (or record non-finite vertex in report).
5. **Re-export Deliverables**:
   - Re-run `generator.py` to regenerate all OBJs, `.blend`, and `.glb` files in `output/` once the geometric fixes are in place.

---

## 5. Verification Method

To independently reproduce all empirical findings and verify remediations, execute the following commands in `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`:

### 5.1 Run Empirical Adversarial Stress Suite
```bash
uv run pytest tests/test_m1_adversarial_stress.py -v
```
*Current Result*: 8 failed, 10 passed.  
*Target After Worker Remediation*: 18 passed in < 15s with exit code 0.

### 5.2 Specific Sub-Test Reproduction Commands

1. **Verify Skirt Clearance Defect (Current: 6.41mm, Fails)**:
   ```bash
   uv run pytest tests/test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_skirt_clearance_nominal_15mm_invariant -v
   ```

2. **Verify Shoe Misalignment Defect (Current: 165.7mm displacement, Fails)**:
   ```bash
   uv run pytest tests/test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_shoes_foot_containment_and_alignment -v
   ```

3. **Verify Ankle Landmark Deviation (Current: 128.8mm deviation, Fails)**:
   ```bash
   uv run pytest tests/test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_landmark_alignment_with_mesh_geometry -v
   ```

4. **Verify Validator Crash on NaN (Current: Unhandled ValueError, Fails)**:
   ```bash
   uv run pytest tests/test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_topology_validator_nan_inf_robustness -v
   ```

5. **Verify Scale Invariants (Passes)**:
   ```bash
   uv run pytest tests/test_m1_adversarial_stress.py::TestM1AdversarialStress::test_adversarial_scale_invariants_145_to_175 -v
   ```
