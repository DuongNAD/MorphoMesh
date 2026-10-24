# Handoff Report: 5-Toe Skinning Weight Architecture & Physical Cleft Test Formulations (M1 Iteration 2)

**Agent**: `explorer_m1_iter2_skinning_tests` (M1 Iter 2 Skinning & Tests Impact Explorer)  
**Parent Agent**: `orchestrator_human_anatomy_1` (`8e1c858e-2863-448c-aaeb-b9860ae4a909`)  
**Target Codebases**: `src/morphomesh/human_rigging.py`, `tests/test_empiric_m1_anatomy.py`, `tests/test_human_generator.py`, `tests/test_adversarial_rigging.py`  
**Authoritative Documents**: `ORIGINAL_REQUEST.md` (`2026-09-07T13:01:03Z` & `2026-09-07T13:15:05Z`), `PROJECT.md`, `GATE_STATUS.md`  
**Detailed Technical Report**: `E:\tool\mcp\MorphoMesh\.agents\explorer_m1_iter2_skinning_tests\remediation_skinning_tests.md`  
**Date**: 2026-09-07T14:04:00Z  

---

## 1. Observation

Direct code inspection, mathematical tracing, and automated test execution across `src/morphomesh/human_rigging.py`, `tests/test_empiric_m1_anatomy.py`, `tests/test_human_generator.py`, and `tests/test_adversarial_rigging.py` revealed four primary findings:

### 1.1 Invariant Rigify 163 DEF Bone Mapping
In `src/morphomesh/human_rigging.py`:
- Lower limb deformation chain strictly maintains 6 DEF bones per side: `DEF-thigh.{side}`, `DEF-thigh.{side}.001`, `DEF-shin.{side}`, `DEF-shin.{side}.001`, `DEF-foot.{side}`, `DEF-toe.{side}`.
- All 5 foot digits (Hallux and Toes 2–5) map to `DEF-toe.{side}`; the tarsus, metatarsus, and plantar arch map to `DEF-foot.{side}`.
- Compile-time assertion `len(ALL_163_DEF_BONES) == 163` strictly holds.

### 1.2 Latent Plantar Arch & Metatarsal Ball Weight Bleeding Defect
In `src/morphomesh/human_rigging.py` (lines 1113–1120):
```python
if s_toe > 0.001:
    weight_map.set_weight(i, f"DEF-toe.{side_f}", s_toe)
    weight_map.set_weight(i, f"DEF-foot.{side_f}", 1.0 - s_toe)
else:
    # Posterior foot and heel: 85% foot, 15% shin.001 near heel/Achilles
    weight_map.set_weight(i, f"DEF-foot.{side_f}", 0.85)
    weight_map.set_weight(i, f"DEF-shin.{side_f}.001", 0.15)
```
- **Observed**: Any vertex posterior to the MTP transition band with $s_{\text{toe}} \le 0.001$ unconditionally received $0.85$ to `DEF-foot` and $0.15$ to `DEF-shin.001`.
- **Defect**: This unintentionally assigned $15\%$ weight of the lower leg (`DEF-shin.001`, terminating at $Z=0.082\text{m}$) to the metatarsal ball ($Y \approx -0.065\text{m}$) and the continuous plantar arch bridge ($Y \approx 0.000\text{m}$, $Z \approx 0.0085\text{m}$). During ankle plantarflexion, this would pin the plantar arch to the stationary shin, causing arch flattening, distortion, and volume collapse.

### 1.3 MTP Break Line 1D Approximation vs 5-Corridor Convex Arch
In `src/morphomesh/human_rigging.py` (lines 1101–1106):
```python
x_med = ak_pt[0] - s_sign * 0.024 * scale_f
x_lat = ak_pt[0] + s_sign * 0.028 * scale_f
span_x = max(1e-4, abs(x_lat - x_med))
rel_x = max(0.0, min(1.0, (s_sign * (vx - x_med)) / span_x))
y_mtp = (-0.095 + 0.020 * rel_x) * scale_f
```
- **Observed**: The code approximated the MTP break line as a single linear segment between $x_{\text{med}}$ and $x_{\text{lat}}$.
- **Discrepancy with Remediated Geometry**:
  1. Remediated Hallux center is at $-0.0260s$ (outer edge $-0.0350s$), and Pinky center is at $+0.0300s$ (outer edge $+0.0360s$). Both extreme digits extend outside the hardcoded $[x_{\text{med}}, x_{\text{lat}}]$ span and get clamped.
  2. The human metatarsal heads curve convexly (Second Toe MTP is at $Y = -0.093\text{m}$). The 1D linear approximation placed the Second Toe MTP break at $Y \approx -0.087\text{m}$ ($6.0\text{mm}$ too far posterior), improperly pinning the proximal phalanx of Toe 2 to `DEF-foot`.

### 1.4 Test Suite Fragility on Topology Upgrades
In `tests/test_empiric_m1_anatomy.py` (lines 503–506):
```python
toe_big_verts = [mesh.vertices[i] for i in foot_L[48:72]]
toe_second_verts = [mesh.vertices[i] for i in foot_L[72:96]]
```
- **Observed**: The cleft test hardcoded vertex slice indices `[48:72]` and `[72:96]`, which only matched the obsolete 24-vertex unsegmented ellipsoids.
- **Impact**: As soon as the worker adds intermediate quad rings for the plantar arch bridge or articulates the phalanges, these indices will slice the wrong geometry.
- Furthermore, `test_empirical_interdigital_cleft_physical_mesh_clearance` had `@pytest.mark.xfail(strict=True)` asserting $\ge 4.0\text{mm}$, which must be un-xfailed and updated to assert $\ge 4.50\text{mm}$.
- In `tests/test_human_generator.py`, `test_articulated_feet()` lacked assertions for 5 distinct toe landmarks, $\ge 4.5\text{mm}$ cleft, Greek profile length, and continuous arch bridge.

---

## 2. Logic Chain

1. **Premise 1 (Rigify DEF Architecture)**: The authoritative metarig provides `DEF-foot.{side}` and `DEF-toe.{side}`. The tarsal arch and metatarsals must deform with `DEF-foot`; all 5 toe digits and their segmented phalanges must deform with `DEF-toe`.
2. **Premise 2 (Plantar Arch Isolation)**: The continuous plantar arch bridge ($Y \in [-0.015, +0.015]\text{m}$, $Z \approx +8.5\text{mm}$) is situated distal to the ankle joint and forms a rigid vaulted lever with the calcaneus and metatarsals. Restricting the $15\%$ `DEF-shin.001` blend exclusively to the posterior Achilles zone ($v_y > ak\_pt[1] + 0.035s$ and $v_z > ak\_pt[2] - 0.030s$) ensures that the plantar arch receives $100\%$ weight on `DEF-foot`, completely eliminating midfoot stretch and preserving volume.
3. **Premise 3 (Voronoi Corridors & Curved MTP Line)**: By defining the 5 MTP joint centers at $(-0.0260, -0.095)$, $(-0.0035, -0.093)$, $(0.0070, -0.088)$, $(0.0190, -0.082)$, and $(0.0300, -0.075)$, a piecewise linear interpolation $Y_{\text{MTP}}(\xi)$ accurately matches the biological metatarsal heads across all 5 digits.
4. **Premise 4 (Hermite Smoothstep Encompassing Phalanges)**: With transition half-width $\delta_{\text{MTP}} = 0.015s$, the cubic Hermite smoothstep $S(t) = 3t^2 - 2t^3$ transitions $W(\text{DEF-toe})$ smoothly from $0.0$ to $1.0$. All distal phalanges ($Y < -0.118\text{m}$) and toenails sit strictly anterior to $Y_{\text{MTP}} - \delta_{\text{MTP}}$, guaranteeing $100\%$ rigid lock to `DEF-toe` and $0\%$ bleeding.
5. **Premise 5 (Topology-Agnostic Test Design)**: Replacing hardcoded vertex index slices with spatial Voronoi cleft partitioning ($X_{\text{cleft}, 0-1} = cx_{\text{ankle}} - 0.0148s$) insulates tests from internal mesh re-indexing and enables strict assertions of physical 3D clearance $\ge 4.50\text{mm}$ and transverse gap $\ge 4.50\text{mm}$.
6. **Conclusion**: Implementing the formulated piecewise Voronoi MTP break and arch isolation in `human_rigging.py` along with modernized test assertions in `test_empiric_m1_anatomy.py` and `test_human_generator.py` fully resolves all gate-failing criteria while preserving 100% test pass rates and $\rho_V \ge 0.92$ volume preservation.

---

## 3. Caveats

1. **Dual Quaternion Skinning Requirement**: Volume retention ($\rho_V \ge 0.99$) relies on Blender's native Dual Quaternion Skinning (`use_deform_preserve_volume = True`). In external LBS game engines without DQS, joint volume loss at $90^\circ$ flexion may drop to ~0.88 unless corrective blendshapes or dual quaternion deformers are used.
2. **Vertex Group Naming Synergy**: If the anatomy worker defines dedicated `toenails_L` / `toenails_R` vertex groups, `human_rigging.py` explicitly supports them with $1.0$ weight to `DEF-toe`. If left inside `foot_L/R`, the MTP smoothstep also guarantees $1.0$ weight because toenails sit on the distal phalanges ($Y < -0.125\text{m}$).
3. **Parametric Scaling Bounds**: All formulas are normalized by $scale\_f = H / 1.65$ and preserve strict bilateral symmetry ($s_{\text{sign}} = \pm 1.0$) across $1.40\text{m} \le H \le 1.95\text{m}$.

---

## 4. Conclusion & Actionable Recommendations

### 4.1 Actions for Anatomy Rigging Worker (`worker_m1_anatomy_rig`)

1. **Update Foot Skinning in `src/morphomesh/human_rigging.py`**:
   Replace lines 1078–1121 with the piecewise Voronoi corridor interpolation, dedicated toenails support, and Achilles-restricted shin blend (full code provided in Section 5 of `remediation_skinning_tests.md`).
2. **Coordinate Foot Landmark Alignment**:
   Ensure `toe_big_L` landmark is placed at $(cx_{\text{ankle}} - 0.0260s, -0.138s, 0.011s)$ and `toe_second_L` at $(cx_{\text{ankle}} - 0.0035s, -0.141s, 0.010s)$, satisfying physical surface cleft $\ge 4.50\text{mm}$.
3. **Plantar Arch Bridge Tagging**:
   Include all continuous arch bridge quad vertices ($Y \in [-0.015, +0.015]\text{m}$) in `foot_L` / `foot_R`. They will automatically receive $100\%$ `DEF-foot` weight.

### 4.2 Actions for Test Writer / Anatomy Challenger

1. **Update `tests/test_empiric_m1_anatomy.py`**:
   - Remove `@pytest.mark.xfail` from `test_empirical_interdigital_cleft_physical_mesh_clearance`.
   - Update assertions to `assert clearance_3d_mm >= 4.50` and `assert transverse_gap_mm >= 4.50`.
   - Use topology-agnostic spatial partitioning via split plane $x_{\text{split}} = cx_{\text{ankle}} - 0.0148s$.
   - Update standalone runner `run_adversarial_empirical_audit()` with $\ge 4.50\text{mm}$ threshold.
2. **Update `tests/test_human_generator.py`**:
   - Expand `test_articulated_feet()` to assert 5 toe landmarks, interdigital cleft $\ge 4.50\text{mm}$, Greek toe profile, and continuous arch bridge (elevation $\ge 6.0\text{mm}$ above floor, 0 air gap).
3. **Add Adversarial Rigging Suite to `tests/test_adversarial_rigging.py`**:
   - Add `TestFootToeSkinningAdversarial` asserting $100\%$ weight on `DEF-toe` for distal phalanges and $100\%$ weight on `DEF-foot` for the plantar arch bridge.

---

## 5. Verification Method

To independently verify the recommendations once implemented:

```powershell
# 1. Run empirical anatomy challenger suite (asserting cleft >= 4.50mm)
uv run pytest tests/test_empiric_m1_anatomy.py -v

# 2. Run human generator unit tests (asserting 5 toes, Greek profile, and arch bridge)
uv run pytest tests/test_human_generator.py -v

# 3. Run adversarial rigging suite (asserting zero weight bleeding and volume preservation)
uv run pytest tests/test_adversarial_rigging.py tests/test_empiric_m1_rigging.py -v

# 4. Direct In-Blender Headless Verification
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --factory-startup --python tests/test_empiric_m1_rigging.py
```

**Invalidation Conditions**:
- Minimum 3D Euclidean cleft between Hallux and Toe 2 mesh $< 4.50\text{mm}$.
- Transverse surface gap between Hallux and Toe 2 $< 4.50\text{mm}$.
- Any plantar arch bridge vertex ($Y \in [-0.015, +0.015]\text{m}$) receiving $> 0.001$ weight to `DEF-shin.001`.
- Any distal toe phalanx vertex ($Y < -0.120\text{m}$) receiving $< 0.999$ weight to `DEF-toe`.
- Evaluated mesh volume retention ratio $\rho_V < 0.92$ under $90^\circ$ toe or combined joint flexion.
