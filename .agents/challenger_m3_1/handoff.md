# Handoff Report: Milestone M3 Sandals Empirical Challenge

**Agent**: Challenger 1 (Challenger M3.1: Sandals Clearance, Height & Toes Exposure Empirical Challenger)  
**Parent Agent**: orchestrator_human_anatomy_gen2 (`c2422918-70a3-47d9-a8f9-883422a33af0`)  
**Date**: 2026-09-07  
**Verdict**: **REQUEST_CHANGES**  
**Status**: Hard Handoff (Adversarial Audit Complete)

---

## 1. Observation

1. **Height Scale Dilation at $H = 1.80\text{m}$**:
   - In `src/morphomesh/wardrobe.py:1360-1363`:
     ```python
     z_mid = (0.0440 - 0.0015 * sin_t + 0.0010 * cos_t) * s
     z_low = z_mid - 0.0025 * s
     z_up  = z_mid + 0.0025 * s
     ```
   - Running `generate_flat_strappy_sandals(height=1.80, scale=1.0)`:
     `min_z = 0.000000m`, `max_z = 0.052660m`, total footwear height = $52.66\text{mm} > 50.0\text{mm}$.
   - Verbatim pytest assertion error in `tests/test_challenger_m3_sandals.py:141`:
     ```
     AssertionError: Scale dilation failure at H=1.8m: total height 52.66mm exceeds 50.0mm limit
     assert 52.66 <= 50.0
     ```

2. **Sole Length Bound Violation at $H = 1.80\text{m}$**:
   - In `src/morphomesh/wardrobe.py:1103-1104`:
     ```python
     y_heel_post = 0.100 * s
     y_toe_ant   = -0.138 * s
     ```
   - At $H = 1.80\text{m}$ ($s = 1.80/1.65 = 1.090909$):
     `y_heel_post = 0.1091m`, `y_toe_ant = -0.1505m`.
     Sole length $L_{\text{sole}} = 0.1091 - (-0.1505) = 0.2676\text{m} > 0.25\text{m}$.
   - Verbatim pytest assertion error in `tests/test_challenger_m3_sandals.py:154`:
     ```
     AssertionError: Sole length bounds failure at H=1.8m: sole length 0.2676m not in [0.22, 0.25]m
     assert 0.26755 <= 0.25
     ```

3. **Toes Exposure and Landmark Clearance Discrepancies**:
   - In `src/morphomesh/human_generator.py:1742-1751`:
     `toe_big_L` landmark coordinate is `(0.0615, -0.138, 0.011)`.
     `toe_fifth_L` landmark coordinate is `(0.1185, -0.103, 0.006)`.
   - In `src/morphomesh/wardrobe.py:1104`:
     `y_toe_ant = -0.138 * s`.
   - Measured clearance against sole front $Y = -0.138\text{m}$:
     * Big toe landmark clearance: `(-0.138) - (-0.138) = 0.00mm < 7.0mm`.
     * Big toe mesh vertices ($Y_{\min} = -0.13812\text{m}$): clearance is `0.12mm < 7.0mm`.
     * Pinky toe landmark clearance: `(-0.138) - (-0.103) = -35.00mm < 7.0mm` (landmark is $35\text{mm}$ behind the sole front).
     * Pinky toe mesh vertices ($Y_{\min} = -0.11502\text{m}$): clearance is `-22.98mm < 7.0mm` (pinky toe sits on top of sole rather than projecting past it).
   - Verbatim pytest assertion error in `tests/test_challenger_m3_sandals.py:175`:
     ```
     AssertionError: Big toe exposure clearance failure: clearance is 0.00mm < 7.0mm
     assert 0.0 >= 7.0
     ```

4. **Canonical Skin Penetration on Ankle Collar Wrap (Band 3)**:
   - In `src/morphomesh/wardrobe.py:1368`:
     Vertex 206 coordinate is `(0.0880, 0.0180, 0.0425)`.
   - Signed distance to closest body foot polygon (`loc = (0.0880, 0.0179, 0.0426)`, `norm = (-0.37, -0.64, 0.67)`):
     $\text{offset} \cdot \vec{n} = -0.000132 \implies s_{\text{dist}} = -0.132\text{mm} < 0.0\text{mm}$ (penetration).
   - Verbatim pytest assertion error in `tests/test_challenger_m3_sandals.py:201`:
     ```
     AssertionError: Skin penetration / buffer failure: min signed distance is -0.132mm < +1.5mm. Penetrating vertices count: 1, below buffer: 1.
     assert -0.00013229419566845727 >= 0.0015
     ```

5. **Unhandled Leg Girth Variation Parameter ($k_{\text{leg}}$)**:
   - In `src/morphomesh/wardrobe.py:1077`, `k_leg: float = 1.0` is declared in `generate_flat_strappy_sandals` signature, but `k_leg` is referenced zero times in the function body (`occurrences of k_leg: 1` total).
   - In `src/morphomesh/human_generator.py:1493`, foot vertical elevations scale with `s * k_leg`.
   - Testing with $k_{\text{leg}} = 0.8$: Band 2 penetrates by $-7.64\text{mm}$, Band 1 penetrates by $-4.65\text{mm}$.
   - Testing with $k_{\text{leg}} = 1.2$: Band 2 penetrates by $-4.05\text{mm}$, Band 3 penetrates by $-2.24\text{mm}$.
   - Verbatim pytest assertion error in `tests/test_challenger_m3_sandals.py:218`:
     ```
     AssertionError: Leg variation clearance failure at k_leg=0.8: min signed clearance is -7.64mm < +1.5mm
     assert -0.007639458935766613 >= 0.0015
     ```

6. **Passing Dimensions Verified**:
   - Ground elevation: $Z_{\min} = 0.00000\text{m}$ (PASS).
   - Degenerate faces: 0 degenerate faces; minimum triangle face area is $3.31 \times 10^{-6}\text{m}^2 > 10^{-9}$ (PASS).
   - Normalized Rigify skinning: 100% of vertices have normalized weights $\sum w_i = 1.000000$ in `DEF-foot` and `DEF-toe` (PASS).
   - Medial arch rise: $+3.95\text{mm} > +3.5\text{mm}$ relative rise along medial border (PASS).
   - `uv run pytest tests/test_wardrobe_m3.py -v`: 25 passed in 0.08s (PASS).

---

## 2. Logic Chain

1. From Observation 1, total footwear height is constrained to $\le 50.0\text{mm}$ across all scales. Because `wardrobe.py` scales all vertical coordinates by $s = H / 1.65$, at $H = 1.80\text{m}$, peak height expands to $52.66\text{mm}$. This directly breaks the height specification.
2. From Observation 2, sole length is constrained to $[0.22\text{m}, 0.25\text{m}]$. At $H = 1.80\text{m}$, unconstrained scaling results in $L_{\text{sole}} = 0.2676\text{m}$, directly breaking the upper length bound.
3. From Observation 3, Worker M3 asserted toe clearance in `test_wardrobe_m3.py` via hardcoded arithmetic `(-0.138) - (-0.145) = 0.007m`, but in the actual human generator model, `toe_big_L` landmark is at $-0.138\text{m}$ ($0.0\text{mm}$ clearance), and the pinky toe landmark is at $-0.103\text{m}$ ($35\text{mm}$ behind the sole front). A straight transverse sole front at $Y = -0.138\text{m}$ fails to provide $\ge 7\text{mm}$ clearance for the big toe and leaves the pinky toe enclosed rather than exposed.
4. From Observation 4, vertex 206 of Band 3 collar wrap has a negative signed distance of $-0.132\text{mm}$, penetrating the ankle tissue and failing the $\ge +1.5\text{mm}$ skin buffer requirement.
5. From Observation 5, because `generate_flat_strappy_sandals` ignores `k_leg`, variations in character leg girth / length ($k_{\text{leg}} \in [0.8, 1.2]$) cause severe strap clipping through the foot mesh (up to $-7.64\text{mm}$ penetration).
6. Combining Steps 1-5, while baseline components function at canonical scale, the implementation fails adversarial stress testing under extreme scaling, leg variation, toe exposure geometry, and collar skin clearance. Therefore, the implementation cannot be approved in its current state.

---

## 3. Caveats

- **Props & Grooming Out of Scope for M3.1**: Marionette strings, butterflies, and 6-stratum hime cut were verified to pass their unit tests in `tests/test_wardrobe_m3.py` and `tests/test_hime_cut_6_strata.py`, but this report focuses strictly on sandals clearance, height, and toe exposure per the dispatch assignment.
- **Blender Scene Verification**: Headless BVH and mathutils checks match the pure Python BVH results within $0.05\text{mm}$.
- No other caveats.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Worker M3 must address the following five defects in `src/morphomesh/wardrobe.py`:
1. **Height Clamping**: Clamp or recalibrate peak ankle collar height so that total height $\le 50.0\text{mm}$ across all $H \in [1.50\text{m}, 1.80\text{m}]$.
2. **Sole Length Clamping**: Constrain $L_{\text{sole}} \in [0.22\text{m}, 0.25\text{m}]$ across all character scales.
3. **Anatomical Oblique Sole Front**: Adapt $y_{\text{toe\_ant}}$ across transverse coordinates to follow the oblique MTP angle, ensuring $\ge 7\text{mm}$ clearance for both the big toe and pinky toe landmarks.
4. **Band 3 Collar Clearance**: Add $+2.0\text{mm}$ offset to Band 3 sector 0 to eliminate the $-0.132\text{mm}$ skin penetration at vertex 206.
5. **Propagate $k_{\text{leg}}$**: Connect `k_leg` to strap and footbed Z-elevation in `generate_flat_strappy_sandals`.

---

## 5. Verification Method

To independently reproduce all observations and verify the defects:

1. **Run the Adversarial Test Suite**:
   ```bash
   uv run pytest tests/test_challenger_m3_sandals.py -v
   ```
   *Current Result*: 4 passed, 5 failed.
   *Target Result after Worker M3 remediation*: 9 passed.

2. **Run the Wardrobe M3 Regression Suite**:
   ```bash
   uv run pytest tests/test_wardrobe_m3.py -v
   ```
   *Expected*: 25 passed.

*Invalidation Conditions*:
- Any failure in the 4 invariant tests (`test_sandals_ground_elevation_invariant`, `test_sandals_topology_and_zero_degenerate_faces`, `test_sandals_normalized_rigify_skinning_all_vertices`, `test_sandals_medial_arch_rise_greater_than_3_5mm`).
- Continued failure of the 5 stress tests in `tests/test_challenger_m3_sandals.py`.
