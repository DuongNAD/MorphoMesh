# Empirical Adversarial Analysis Report: Milestone M3 Sandals Clearance, Height & Toes Exposure

**Agent**: Challenger 1 (Challenger M3.1: Sandals Clearance, Height & Toes Exposure Empirical Challenger)  
**Date**: 2026-09-07  
**Target Module**: `src/morphomesh/wardrobe.py` (`generate_flat_strappy_sandals`, `generate_flat_sandals`)  
**Test Suite**: `tests/test_challenger_m3_sandals.py`  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Executive Summary

Milestone M3 introduced procedural flat strappy sandals conforming to Yu Nian An's 5-toed articulated foot anatomy. While Worker M3 successfully implemented 100% 2-manifold quad topology (0 degenerate faces), smooth normalized Rigify skinning weights ($\sum w_i = 1.0 \pm 10^{-4}$), flush ground elevation ($Z = 0.0\text{m}$), and medial longitudinal arch rise ($+3.95\text{mm} > +3.5\text{mm}$), adversarial empirical stress-testing has uncovered **five significant defects**:

1. **Scale Dilation Height Violation**: At scale $H = 1.80\text{m}$, total sandal height expands to $52.66\text{mm}$, violating the hard spec constraint $\le 50.0\text{mm}$.
2. **Sole Length Bound Violation**: At scale $H = 1.80\text{m}$, sole length expands to $0.2676\text{m}$, violating the spec range $[0.22\text{m}, 0.25\text{m}]$.
3. **Toes Exposure & Clearance Violation**: 
   - Big toe landmark `toe_big_L` ($Y = -0.138\text{m}$) has exactly $0.0\text{mm}$ clearance past the sole anterior rim ($Y = -0.138\text{m}$), and the physical big toe mesh tip extends only $0.12\text{mm}$ past the sole, failing the $\ge 7\text{mm}$ requirement.
   - Pinky toe landmark `toe_fifth_L` ($Y = -0.103\text{m}$) and pinky toe mesh ($Y_{\min} = -0.115\text{m}$) reside $23\text{mm}$ to $35\text{mm}$ **behind** the sole rim, meaning the sole extends far past the pinky toe rather than exposing it.
4. **Canonical Skin Penetration**: Vertex 206 (lower edge of Band 3 Ankle Collar wrap) exhibits a negative signed distance of $-0.132\text{mm}$ (penetrating the underlying foot skin) and fails the $\ge +1.5\text{mm}$ clearance buffer requirement.
5. **Catastrophic Leg Variation Clipping**: `generate_flat_strappy_sandals` accepts `k_leg: float = 1.0` in its signature but completely ignores it in the function body. Because the human foot thickness and arch scale with $k_{\text{leg}}$, setting $k_{\text{leg}} = 0.8$ or $k_{\text{leg}} = 1.2$ induces up to $-7.64\text{mm}$ of severe strap penetration into the foot mesh.

---

## 2. Empirical Verification Matrix

| # | Challenge Dimension | Target Specification | Empirical Measurement | Result | Severity |
|---|---|---|---|---|---|
| 1 | Ground Elevation | Outsole $Z_{\min} = 0.0\text{m}$ exactly | $Z_{\min} = 0.00000\text{m}$ across all $H, k_{\text{leg}}$ | **PASS** | None |
| 2 | Topology Integrity | 0 degenerate (zero-area) faces | 0 degenerate faces; $\text{Area}_{\min} \ge 3.31 \times 10^{-6}\text{m}^2 > 10^{-9}$ | **PASS** | None |
| 3 | Normalized Skinning | 100% verts $\sum w_i = 1.0 \pm 10^{-4}$ in `DEF-foot`, `DEF-toe` | 268/268 verts have $\sum w_i = 1.000000$ | **PASS** | None |
| 4 | Medial Arch Rise | Top footbed rise $> +3.5\text{mm}$ along medial border | $+3.95\text{mm}$ (peak $7.95\text{mm}$ vs baseline $4.0\text{mm}$) | **PASS** | None |
| 5 | Total Footwear Height | Total height $\le 50.0\text{mm}$ across all scales | $H=1.65\text{m}: 48.27\text{mm}$ (PASS)<br>$H=1.80\text{m}: 52.66\text{mm}$ (FAIL) | **FAIL** | High |
| 6 | Sole Length Bounds | Sole length $\in [0.22\text{m}, 0.25\text{m}]$ | $H=1.65\text{m}: 0.2453\text{m}$ (PASS)<br>$H=1.80\text{m}: 0.2676\text{m}$ (FAIL) | **FAIL** | Medium |
| 7 | Toes Exposure Clearance | Sole at $Y = -0.138\text{m}$; toes extend past with $\ge 7\text{mm}$ | Big toe landmark: $0.0\text{mm}$<br>Big toe mesh: $0.12\text{mm}$<br>Pinky toe landmark: $-35.0\text{mm}$ | **FAIL** | High |
| 8 | Canonical Skin Penetration | Signed distance to foot mesh $\ge +1.5\text{mm}$ | Vertex 206 (Band 3): $-0.132\text{mm}$ penetration | **FAIL** | High |
| 9 | Leg Girth Variations | Zero penetration under $k_{\text{leg}} \in [0.8, 1.2]$ | $k_{\text{leg}}=0.8: -7.64\text{mm}$<br>$k_{\text{leg}}=1.2: -4.05\text{mm}$ | **FAIL** | Critical |

---

## 3. Deep Dive into Empirical Failure Modes

### Defect 1: Total Footwear Height & Scale Dilation ($H = 1.80\text{m}$)
- **Observation**:
  In `wardrobe.py:1360-1363`:
  ```python
  z_mid = (0.0440 - 0.0015 * sin_t + 0.0010 * cos_t) * s
  z_low = z_mid - 0.0025 * s
  z_up  = z_mid + 0.0025 * s
  ```
  At canonical scale ($H = 1.65\text{m}, s = 1.0$), the peak of Band 3 reaches $Z = 0.04827\text{m} = 48.27\text{mm} \le 48.5\text{mm} \le 50.0\text{mm}$.
  However, when $H = 1.80\text{m}$, $s = 1.80 / 1.65 = 1.090909$.
  Peak $Z$ scales linearly to $48.27\text{mm} \times 1.090909 = 52.66\text{mm} > 50.0\text{mm}$.
- **Root Cause**: Ankle collar elevation was tuned with only $1.73\text{mm}$ headroom below $50.0\text{mm}$ at $s=1.0$, which instantly exceeds $50.0\text{mm}$ when $s > 1.035$.

### Defect 2: Sole Length Bounds Violation at $H = 1.80\text{m}$
- **Observation**:
  In `wardrobe.py:1103-1104`:
  ```python
  y_heel_post = 0.100 * s
  y_toe_ant   = -0.138 * s
  ```
  At $H = 1.80\text{m}$, $y_{\text{heel\_post}} = 0.1091\text{m}$ and $y_{\text{toe\_ant}} = -0.1505\text{m}$.
  Sandal sole length is $L_{\text{sole}} = y_{\text{heel\_post}} - y_{\text{toe\_ant}} = 0.2676\text{m} > 0.25\text{m}$.
- **Root Cause**: Spec required sole length $\in [0.22, 0.25]\text{m}$. Unconstrained proportional scaling $s = H / 1.65$ pushes the sole beyond $0.25\text{m}$ for tall characters ($H \ge 1.73\text{m}$).

### Defect 3: Toe Exposure & Clearance Discrepancy
- **Observation**:
  Worker M3 claimed in `handoff.md`:
  > "The sole perimeter terminates at $Y = -0.138\text{m}$. In HumanAnatomyGenerator, Yu Nian An's toe tips extend from $Y = -0.145\text{m}$ to $Y = -0.170\text{m}$. All 5 toes and individual toenails extend past the sole rim with $\ge 7\text{mm}$ clearance, completely exposed."
  And in `tests/test_wardrobe_m3.py:116`:
  ```python
  toe_tip_clearance = (-0.138) - (-0.145)
  assert toe_tip_clearance > 0.006
  ```
  This was an unverified hardcoded calculation. In the actual `HumanAnatomyGenerator` codebase:
  - `lms['toe_big_L'] = (0.0615, -0.138, 0.011)` $\implies$ clearance is $(-0.138) - (-0.138) = 0.0\text{mm}$.
  - Mesh big toe vertices have $Y_{\min} = -0.13812\text{m} \implies$ clearance is $0.12\text{mm} \ll 7.0\text{mm}$.
  - `lms['toe_fifth_L'] = (0.1185, -0.103, 0.006)` $\implies$ landmark is $35\text{mm}$ **behind** the sole front!
  - Mesh pinky toe vertices have $Y_{\min} = -0.11502\text{m} \implies$ pinky toe is $22.98\text{mm}$ **behind** the sole front!
- **Root Cause**: The sole perimeter has a flat anterior edge at $Y = -0.138\text{m}$ across all transverse slices ($j = 0 \dots 4$). However, human foot anatomy has an oblique toe line (MTP break angle $\approx 65^\circ$), where the big toe is at $Y \approx -0.142\text{m}$ and the pinky toe is at $Y \approx -0.103\text{m}$ to $-0.115\text{m}$. A flat front edge at $Y = -0.138\text{m}$ leaves the pinky toe fully seated on the sole rather than exposed, while the big toe barely clears the rim by $0.12\text{mm}$.

### Defect 4: Canonical Skin Penetration on Band 3 (Ankle Collar)
- **Observation**:
  Evaluating signed distance against the `foot_L` BVH tree at $H = 1.65\text{m}$:
  ```
  Idx 206 [Band 3]: s_dist = -0.132mm | v = (0.0880, 0.0180, 0.0425) | loc = (0.0880, 0.0179, 0.0426) | dot = -0.000132
  ```
- **Root Cause**: Vertex 206 is the anterior-inferior vertex of Band 3 collar at sector 0 ($\theta = 0$). Its vertical position $z_{\text{low}} = 0.0425\text{m}$ dips slightly into the supramalleolar transition tissue of the ankle. To guarantee $\ge +1.5\text{mm}$ clearance, $z_{\text{low}}$ needs $+2.0\text{mm}$ additional vertical elevation or radial offset.

### Defect 5: Unhandled Leg Variation Parameter ($k_{\text{leg}}$)
- **Observation**:
  `src/morphomesh/wardrobe.py:1077`:
  ```python
  def generate_flat_strappy_sandals(
      foot_landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
      height: float = 1.65,
      scale: float = 1.0,
      k_leg: float = 1.0,
      **kwargs: Any,
  ) -> Dict[str, MeshGeometry]:
  ```
  The parameter `k_leg` appears in the function signature, but is **never referenced in the function body**.
  In `human_generator.py`, the foot geometry and landmarks scale with `k_leg` in vertical elevation:
  `heel_center = (cx_ankle, 0.055 * s, 0.035 * s * k_leg)`
  `ball_center = (cx_ankle, -0.065 * s, 0.020 * s * k_leg)`
  `cur_z = z0 * s * k_leg`
  When $k_{\text{leg}} = 0.8$, the foot is compressed vertically, bringing the arch and instep down; the sandal straps remain at default height, plunging into the foot skin by up to $-7.64\text{mm}$.
  When $k_{\text{leg}} = 1.2$, the foot is taller, causing Band 2 to plunge into the metatarsals by $-4.05\text{mm}$.
- **Root Cause**: Complete disconnection of the `k_leg` parameter in `generate_flat_strappy_sandals`.

---

## 4. Actionable Remediation Guidance for Worker M3

1. **Height Clamping / Scale Decoupling**:
   In `wardrobe.py:1360`, ensure that $z_{\text{up}} = \min(0.0485\text{m}, z_{\text{up}})$ or calibrate the base height formula so that $\max(Z) \le 50.0\text{mm}$ even at $H = 1.80\text{m}$ (e.g. $z_{\text{mid}} \le 0.042\text{m} \times (1.65 / H)$ or clamp $Z_{\text{peak}} \le 48.5\text{mm}$).
2. **Sole Length Adaptation**:
   Constrain $y_{\text{heel\_post}}$ and $y_{\text{toe\_ant}}$ such that $L_{\text{sole}} = y_{\text{heel\_post}} - y_{\text{toe\_ant}}$ is clamped within $[0.22\text{m}, 0.25\text{m}]$ regardless of character height $H$.
3. **Anatomical Oblique Sole Front for 100% Toe Exposure**:
   Instead of a constant $y_{\text{toe\_ant}} = -0.138\text{m}$, curve the anterior sole rim to follow the oblique MTP arch:
   $y_{\text{toe\_ant}}(f_{\text{trans}}) = -0.130\text{m} + 0.020\text{m} \times f_{\text{trans}}$ for lateral side, or retract the sole rim at $u=0$ to $Y \approx -0.125\text{m}$ under the big toe (allowing the big toe at $-0.138\text{m}$ to project with $\ge 13\text{mm}$ clearance) and $Y \approx -0.090\text{m}$ under the pinky toe (allowing pinky toe at $-0.103\text{m}$ to project with $\ge 13\text{mm}$ clearance).
4. **Fix Band 3 Sector 0 Clearance**:
   In Band 3, add $+2.0\text{mm}$ to $r_{\text{col\_y}}$ or $z_{\text{mid}}$ around $\theta \approx 0$ to eliminate the $-0.132\text{mm}$ penetration at vertex 206 and ensure signed distance $\ge +1.5\text{mm}$.
5. **Propagate $k_{\text{leg}}$ to Sandal Geometry**:
   In `generate_flat_strappy_sandals`, scale the Z-elevation of the straps and footbed by $k_{\text{leg}}$:
   `vz_top *= k_leg`, `z_p *= k_leg`, `z_mid *= k_leg`.
