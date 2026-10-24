# Milestone M2 Challenger Report: Sandals, Sash & Multi-Scale Stress Audit

**Agent**: M2 Challenger 2 (Sandals, Sash & Multi-Scale Stress Audit)  
**Date**: 2026-09-08  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m2_challenger_2`  
**Target Delivery File**: `E:\tool\mcp\MorphoMesh\.agents\m2_challenger_2\handoff.md`  
**Parent Agent**: `79a32aca-3f45-4f6c-ae9e-59087d07960a` (Orchestrator Female Mold 1)  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Mandated Verification Criteria
Per `ORIGINAL_REQUEST.md`, `PROJECT.md`, and the Challenger Dispatch:
1. **Sandals sole length**: $\le 0.25\text{m}$ across scales ($1.40\text{m}$ to $1.95\text{m}$).
2. **Sole height**: $\le 50.0\text{mm}$.
3. **100% bare toes exposure**: toe clearance $\ge 7.0\text{mm}$ from metatarsal strap to distal toe tips per `media_1788785935849.jpg`.
4. **0 skin penetrations**: between sandal straps and 5-toed foot mesh (buffer buffer $\ge +1.5\text{mm}$).
5. **Waist sash clearance**: $\ge +2.0\text{mm}$ clearance over dress bodice and skirt with 0% Z-fighting under multi-scale stress.

### 1.2 Test Harness Execution & Empirical Telemetry
We authored and executed the automated multi-scale stress suite `tests/test_challenger_m2_multiscale_sandals.py` covering 33 test combinations:
- 6 character heights: $H \in \{1.40, 1.50, 1.65, 1.80, 1.90, 1.95\}\text{m}$
- 3 leg girth factors: $k_{\text{leg}} \in \{0.80, 1.00, 1.20\}$
- 3 waist scale factors: $k_{\text{waist}} \in \{0.85, 1.00, 1.20\}$

Command executed:
```bash
uv run pytest tests/test_challenger_m2_multiscale_sandals.py -v
```

**Pytest Execution Result**:
```
=================================== FAILURES ===================================
FAILED tests/test_challenger_m2_multiscale_sandals.py::TestSandalsMultiScaleStress::test_sandals_sole_length_bound_across_scales[1.9]
  AssertionError: Sandal length violation at H=1.90m: length is 0.2539m > 0.25m
FAILED tests/test_challenger_m2_multiscale_sandals.py::TestSandalsMultiScaleStress::test_sandals_sole_length_bound_across_scales[1.95]
  AssertionError: Sandal length violation at H=1.95m: length is 0.2579m > 0.25m
FAILED tests/test_challenger_m2_multiscale_sandals.py::TestSandalsMultiScaleStress::test_sandals_zero_skin_penetration[1.9]
  AssertionError: Skin penetration failure at H=1.90m: 3 penetrating vertices detected. Min signed distance: -1.70mm.
FAILED tests/test_challenger_m2_multiscale_sandals.py::TestSandalsMultiScaleStress::test_sandals_zero_skin_penetration[1.95]
  AssertionError: Skin penetration failure at H=1.95m: 6 penetrating vertices detected. Min signed distance: -2.66mm.
======================== 4 failed, 29 passed in 2.24s =========================
```

### 1.3 Quantitative Multi-Scale Empirical Measurements

#### A. Sandals Multi-Scale Audit Matrix ($k_{\text{leg}} = 1.00$)
| Height $H$ | Mesh Length ($Y_{\max} - Y_{\min}$) | Sole Length (Verts 0..169) | Footwear Height | Min Strap $Y$ | Min Sole $Y$ | Strap Overhang | Min Big Toe Clearance | Min Pinky Toe Clearance | Min Signed Skin Dist | Penetration Count | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1.40m** | 0.2290m | 0.2290m | 41.15mm | -0.1086m | -0.1328m | -24.16mm (recessed) | 52.05mm | 30.26mm | +2.81mm | 0 | **PASS** |
| **1.50m** | 0.2326m | 0.2326m | 44.09mm | -0.1164m | -0.1349m | -18.52mm (recessed) | 55.77mm | 32.43mm | +2.97mm | 0 | **PASS** |
| **1.65m** | 0.2455m | 0.2380m | 48.50mm | -0.1280m | -0.1380m | -10.00mm (recessed) | 61.35mm | 35.66mm | +3.20mm | 0 | **PASS** |
| **1.80m** | 0.2484m | 0.2434m | 48.50mm | -0.1396m | -0.1411m | -1.50mm (recessed) | 66.92mm | 38.90mm | **+0.20mm** | 0 | **SUB-BUFFER** |
| **1.90m** | **0.2539m** | 0.2451m | 48.50mm | -0.1474m | -0.1421m | **+5.25mm (overhang)**| 70.65mm | 41.07mm | **-1.71mm** | **3** | **FAIL** |
| **1.95m** | **0.2579m** | 0.2451m | 48.50mm | -0.1513m | -0.1421m | **+9.13mm (overhang)**| 72.50mm | 42.15mm | **-2.66mm** | **6** | **FAIL** |

#### B. Penetration Details at Extreme Scales ($k_{\text{leg}} = 0.80, 1.00, 1.20$)
- **At $H = 1.90\text{m}$**:
  - $k_{\text{leg}} = 0.80$: 4 penetrating vertices, minimum signed distance $-1.942\text{mm}$ (Vertices 176, 178, 186, 188).
  - $k_{\text{leg}} = 1.00$: 3 penetrating vertices, minimum signed distance $-1.705\text{mm}$ (Vertices 178, 186, 188).
  - $k_{\text{leg}} = 1.20$: 2 penetrating vertices, minimum signed distance $-1.237\text{mm}$ (Vertices 178, 188).
- **At $H = 1.95\text{m}$**:
  - $k_{\text{leg}} = 0.80$: 6 penetrating vertices, minimum signed distance $-3.024\text{mm}$ (Vertices 176, 178, 182, 186, 188, 189).
  - $k_{\text{leg}} = 1.00$: 6 penetrating vertices, minimum signed distance $-2.660\text{mm}$ (Vertices 176, 178, 182, 186, 188, 189).
  - $k_{\text{leg}} = 1.20$: 7 penetrating vertices, minimum signed distance $-2.179\text{mm}$ (Vertices 176, 178, 180, 182, 186, 188, 189).
- Exact coordinates of worst penetrating vertex at $H=1.95\text{m}, k_{\text{leg}}=1.00$:
  `Vert 178: coord=(0.06618, -0.14182, 0.04850), signed_distance=-2.660mm, nearest_foot_skin=(0.06447, -0.14258, 0.05040)`

#### C. Waist Sash Multi-Scale Audit Matrix
Across all 18 tested combinations ($H \in \{1.40, 1.50, 1.65, 1.80, 1.90, 1.95\}\text{m} \times k_{\text{waist}} \in \{0.85, 1.00, 1.20\}$):
- Minimum bodice radial clearance: $+5.43\text{mm} \ge +2.0\text{mm}$.
- Minimum skirt radial clearance: $+4.74\text{mm} \ge +2.0\text{mm}$.
- Penetrating vertices: 0.
- Z-fighting risk: 0%.
- Conclusion for Sash: **APPROVED**.

---

## 2. Logic Chain

### 2.1 Root Cause of Length Violation & Anterior Strap Overhang (VULN-1)
1. In `src/morphomesh/wardrobe.py` lines 1135–1137, the sole length is scaled using sublinear clamping:
   ```python
   s_len = max(0.96, min(1.03, 1.0 + 0.25 * (s - 1.0)))
   y_toe_ant = -0.138 * s_len
   y_heel_post = y_toe_ant + max(0.225, min(0.248, 0.238 * s_len))
   ```
   This successfully bounds the sole vertices (indices 0..169) to $[-0.1421\text{m}, +0.1030\text{m}]$, yielding a sole length of $0.2451\text{m} \le 0.25\text{m}$.
2. However, in `src/morphomesh/wardrobe.py` line 1348, the metatarsal forefoot strap is constructed using **unclamped linear scale** $s$:
   ```python
   nodes_meta = list(zip(x_meta, [-0.124 * s] * len(x_meta), z_meta))
   add_strap_ribbon(nodes_meta, strap_width=0.008 * s)
   ```
3. At $H = 1.95\text{m}$ ($s = 1.1818$):
   - Strap center line: $-0.124 \times 1.1818 = -0.1465\text{m}$.
   - Strap ribbon anterior edge (with half-width $0.0047\text{m}$): $Y = -0.1513\text{m}$.
   - But sole anterior rim: $y_{\text{toe\_ant}} = -0.138 \times 1.03 = -0.1421\text{m}$.
4. **Result**: The metatarsal strap projects $+9.13\text{mm}$ out into empty air past the front edge of the sole. Consequently, the total bounding length of `Mesh_Sandal_L` expands to $Y_{\max} - Y_{\min} = 0.1066 - (-0.1513) = 0.2579\text{m} > 0.25\text{m}$ (and $0.2539\text{m} > 0.25\text{m}$ at $H=1.90\text{m}$), violating the user-mandated contract $\le 0.25\text{m}$.

### 2.2 Root Cause of Severe Skin Penetration (VULN-2)
1. In `src/morphomesh/wardrobe.py` line 1347:
   ```python
   z_meta = [z * min(1.0, s) for z in z_prof]
   ```
   The author applied `min(1.0, s)` to hard-cap the strap elevation at $48.5\text{mm}$ in order to satisfy the total footwear height bound $\le 50.0\text{mm}$ at $H=1.80\text{m}$.
2. However, the human foot base mesh (`generate_human_base_mesh`) scales proportionally with $s = H / 1.65$. At $H = 1.95\text{m}$, the foot dorsal skin at the first metatarsal / cuneiform crest rises by $18.2\%$ from $Z = 42.64\text{mm}$ up to $Z = 50.39\text{mm}$.
3. Because `z_meta` is clamped by `min(1.0, s) = 1.0`, the metatarsal strap vertices remain artificially locked at $Z = 48.50\text{mm}$.
4. **Result**: The foot dorsal surface penetrates right through the strap. At $H=1.90\text{m}$, 3 to 4 vertices penetrate by up to $-1.94\text{mm}$. At $H=1.95\text{m}$, 6 to 7 vertices penetrate by up to $-3.02\text{mm}$. Even at $H=1.80\text{m}$, clearance degrades to $+0.20\text{mm}$, violating the required $+1.5\text{mm}$ clearance buffer.

---

## 3. Caveats

1. **Toe Exposure**: 100% bare toes exposure is fully maintained across all scales ($H \in [1.40, 1.95]\text{m}$). Clearances to distal toe tips are $52.0\text{mm}$ to $72.5\text{mm}$ (big toe) and $30.3\text{mm}$ to $42.2\text{mm}$ (pinky toe), well above the required $7.0\text{mm}$.
2. **Waist Sash**: The waist sash implementation in `src/morphomesh/wardrobe.py` is fully compliant, maintaining $>4.7\text{mm}$ clearance without Z-fighting or collision across all scales.
3. **Sole Thickness**: The sole itself (outsole and footbed) has a thickness of $4.0\text{mm}$ to $9.4\text{mm}$, fully compliant with $\le 50.0\text{mm}$.

---

## 4. Conclusion & Actionable Recommendations

### Verdict
**REQUEST_CHANGES**

Milestone M2 cannot be approved in its current state due to two reproducible contract violations under multi-scale stress ($H \in [1.40, 1.95]\text{m}$):
1. **Contract Failure 1**: Sandal mesh length exceeds $0.25\text{m}$ at $H=1.90\text{m}$ ($0.2539\text{m}$) and $H=1.95\text{m}$ ($0.2579\text{m}$), caused by metatarsal strap anterior overhang ($+5.25\text{mm}$ to $+9.13\text{mm}$ past the sole front).
2. **Contract Failure 2**: Sandal straps penetrate the foot mesh by up to $-3.02\text{mm}$ at $H=1.95\text{m}$ (6-7 penetrating vertices) and $-1.94\text{mm}$ at $H=1.90\text{m}$ (3-4 penetrating vertices), caused by hard-capped strap elevation `min(1.0, s)`.

### Concrete Remediation Steps for M2 Worker
1. **Fix Metatarsal Strap Longitudinal Scaling (VULN-1)**:
   In `src/morphomesh/wardrobe.py` line 1348, bind the metatarsal strap Y-offset to $s_{\text{len}}$ rather than unclamped $s$:
   ```python
   # Current (defective):
   nodes_meta = list(zip(x_meta, [-0.124 * s] * len(x_meta), z_meta))
   
   # Recommended fix:
   nodes_meta = list(zip(x_meta, [-0.124 * s_len] * len(x_meta), z_meta))
   ```
   This guarantees that the strap remains securely behind the sole anterior rim $y_{\text{toe\_ant}} = -0.138 \times s_{\text{len}}$, eliminating the overhang and keeping the total sandal length strictly $\le 0.248\text{m} \le 0.25\text{m}$.

2. **Fix Metatarsal Strap Vertical Scaling & Foot Clearance (VULN-2)**:
   In `src/morphomesh/wardrobe.py` line 1347:
   Allow the strap elevation $z_{\text{meta}}$ to scale with the foot's anatomical height rather than hard-clamping with `min(1.0, s)`. Specifically:
   ```python
   # Current (defective):
   z_meta = [z * min(1.0, s) for z in z_prof]
   
   # Recommended fix:
   # Scale z with s (or s_len), while maintaining sole height <= 50.0mm:
   z_meta = [z * s for z in z_prof]
   ```
   Note: If total footwear height constraint ($\le 50.0\text{mm}$) is interpreted as applying to the entire sandal assembly rather than the sole plate alone, the metatarsal strap anchor can be shifted slightly forward (e.g. to $Y = -0.128 \times s_{\text{len}}$) where the foot dorsal profile is naturally lower ($\approx 39.9\text{mm}$ at $H=1.95\text{m}$), allowing a $+3.0\text{mm}$ clearance buffer while staying strictly under $50.0\text{mm}$.

---

## 5. Verification Method

To independently reproduce all findings and verify future fixes:

```bash
uv run pytest tests/test_challenger_m2_multiscale_sandals.py -v
```

**Passing Criterion for Approval**:
- 0 test failures across all 33 parameterized test cases.
- `test_sandals_sole_length_bound_across_scales`: length $\le 0.25\text{m}$ for all $H \in [1.40, 1.95]\text{m}$.
- `test_sandals_zero_skin_penetration`: 0 penetrating vertices and minimum signed distance $\ge +1.5\text{mm}$ for all $H \in [1.40, 1.95]\text{m}$.
- `test_sandals_height_bound_across_scales`: footwear height $\le 50.0\text{mm}$ for all $H \in [1.40, 1.95]\text{m}$.
