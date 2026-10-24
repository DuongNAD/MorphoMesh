# Empirical Challenger M3.2 Report: Props Snapping, Butterfly Topology & Flocking

**Author**: Challenger 2 (Challenger M3.2: Props Snapping, Butterfly Topology & Flocking Empirical Challenger)  
**Target Milestone**: M3 (Yu Nian An Character Realism Upgrade)  
**Date**: 2026-09-07  
**Status**: COMPLETE  
**Explicit Verdict**: **`REQUEST_CHANGES`**

---

## Executive Summary

As Empirical Challenger 2 for Milestone M3, I conducted rigorous mathematical verification, boundary stress-testing, and live Blender headless AST/runtime inspection on the signature props (10 crimson cords and 10 glowing white butterflies) across `src/morphomesh/wardrobe.py` and `src/morphomesh/character_assembler.py`.

The standalone implementations in `src/morphomesh/wardrobe.py` are mathematically sound:
- Exact invariant `verts_per_cord = 14` (140 vertices, 120 faces across 10 cords) is strictly preserved.
- Ribbon width $2 \cdot half\_w = 0.8\text{mm}$ is maintained with positive face areas ($> 10^{-5}\text{m}^2$).
- Butterfly quad topology generates exactly 24 quads = 48 tris, 48 vertices, with zero degenerate faces (all face areas $\ge 2.72 \times 10^{-6}\text{m}^2 > 10^{-6}\text{m}^2$).
- Flocking algorithm `get_butterfly_vortex_positions()` achieves minimum pairwise separation of **153.31mm** ($\ge 150\text{mm}$) within $Z \in [0.88\text{m}, 1.32\text{m}]$ and $|X| \ge 0.35\text{m}$.

**However, critical defects were discovered during integration into `src/morphomesh/character_assembler.py` and in the on-disk master deliverables:**
1. **Critical Defect**: In `character_assembler.py:1296-1314`, an obsolete hardcoded `flutter_positions` array overwrites the positions of `Prop_Butterfly_{00..09}`. This reduces minimum pairwise separation to **107.70mm** (violating the $\ge 150\text{mm}$ requirement) and causes the butterflies to **detach by up to 635.15mm away from the ends of the crimson strings** they are supposed to control!
2. **High Defect**: The production binary file on disk (`output/yu_nian_an/Yu_Nian_An_Master.blend`) contains stale M2 props: butterflies have only 18 vertices (10 faces), and strings have root vertices collapsed into a single point ($v_0 = v_1$, 0.0000mm ribbon width, degenerate zero-area faces).

Therefore, the explicit verdict is **`REQUEST_CHANGES`**.

---

## 1. Empirical Verification of Required Tasks

### 1.1 Invariant Verification: 10 Crimson Cords
- **Requirement**: Exactly `verts_per_cord = 14` (total 140 vertices across 10 cords).
- **Observed Metrics**:
  * Total vertices: exactly `140` across 10 cords.
  * Total faces: exactly `120` triangular faces (60 quads = 6 quads per cord).
  * Scale invariance: tested across $s \in [0.5, 0.85, 1.0, 1.25, 1.65, 2.0]$, vertex count remained identically 140 and faces 120.
  * Disconnected vertices: 0.
  * Minimum cord face surface area: $1.0546 \times 10^{-5}\text{m}^2 \gg 10^{-9}\text{m}^2$.
- **Test Result**: `PASSED` (`TestChallengerPropsInvariants::test_invariant_verts_per_cord_equals_14`).

### 1.2 Snapping Precision to Distal Bone Tails
- **Requirement**: Root vertex pair midpoint snaps to distal finger bone tails (`DEF-thumb.03.L/R`, `DEF-f_index.03.L/R`, `DEF-f_middle.03.L/R`, `DEF-f_ring.03.L/R`, `DEF-f_pinky.03.L/R`) with $0.0000\text{mm}$ error.
- **Observed Metrics**:
  * In `character_assembler.py:1268-1274`:
    $$\vec{v}_0 = \vec{t}_{\text{local}} - (half\_w, 0, 0), \quad \vec{v}_1 = \vec{t}_{\text{local}} + (half\_w, 0, 0)$$
    $$\text{Midpoint} = \frac{\vec{v}_0 + \vec{v}_1}{2} = \vec{t}_{\text{local}}$$
    Algebraic error = **$0.000000\text{mm}$**.
  * In standalone Python (`wardrobe.py:1565-1576`):
    `finger_anchors` constants are rounded to 5 decimal places (`0.37472, -0.06344, 0.68727`), producing a sub-10-micron quantization error:
    - Cord 0 (Thumb L): $0.0049\text{mm}$ ($4.9\ \mu\text{m}$)
    - Cord 1 (Index L): $0.0056\text{mm}$ ($5.6\ \mu\text{m}$)
    - Cord 2 (Middle L): $0.0024\text{mm}$ ($2.4\ \mu\text{m}$)
    - Cord 3 (Ring L): $0.0032\text{mm}$ ($3.2\ \mu\text{m}$)
    - Cord 4 (Pinky L): $0.0050\text{mm}$ ($5.0\ \mu\text{m}$)
    - Cords 5..9 (Right Hand): identical bilateral mirror errors ($2.4\ \mu\text{m}$ to $5.6\ \mu\text{m}$).
  * All 10 cords satisfy sub-10-micron error ($< 0.010\text{mm}$) in Python, and $0.0000\text{mm}$ in Blender assembly.
- **Test Result**: `PASSED` (`TestChallengerSnappingPrecision::test_snapping_precision_micron_level_to_bone_tails` and `test_blender_algebraic_snapping_precision_zero_error`).

### 1.3 Ribbon Width & Surface Area
- **Requirement**: Non-zero width ($2 \cdot half\_w = 0.8\text{mm}$) with positive face surface area.
- **Observed Metrics**:
  * Measured ribbon width: $\|\vec{v}_1 - \vec{v}_0\| = 0.8000\text{mm}$ across all 10 cords.
  * Symmetrical offset: $\|\vec{v}_0 - \vec{t}\| = 0.4000\text{mm}$, $\|\vec{v}_1 - \vec{t}\| = 0.4000\text{mm}$.
  * Individual vertex gap to bone tail: $0.40\text{mm} \le 1.0\text{mm}$.
  * Tangent-normal orthogonality: $\left|\hat{w} \cdot \hat{t}\right| \le 0.005 \approx 0.0$.
  * Face surface area: all 120 triangular faces strictly $> 1.05 \times 10^{-5}\text{m}^2 > 10^{-9}\text{m}^2$.
- **Test Result**: `PASSED` (`TestChallengerSnappingPrecision::test_ribbon_width_0_8mm_and_symmetric_offset` and `test_ribbon_tangent_orthogonality`).

### 1.4 Butterfly Topology & Dihedral Flutter
- **Requirement**: Exactly 24 quads = 48 tris per butterfly, 48 vertices, zero degenerate faces (face area $> 10^{-6}\text{m}^2$), valid dihedral flutter angles.
- **Observed Metrics**:
  * Vertices: exactly `48`.
  * Faces: exactly `48` triangular faces = 24 quads.
  * Minimum face area at $25^\circ$ flutter: **$2.7248 \times 10^{-6}\text{m}^2$** ($> 10^{-6}\text{m}^2$).
  * Maximum face area: $2.8602 \times 10^{-4}\text{m}^2$.
  * Total surface area: $3.7073 \times 10^{-3}\text{m}^2$.
  * Degenerate faces ($< 10^{-6}\text{m}^2$): **0**.
  * Morphological validation:
    - 4-ring body (16 verts, 12 quads): Head ($Y > 0.015$), Thorax, Abdomen Base, Abdomen Tail ($Y < -0.015$).
    - Dual curved 3D antennae (12 verts, 4 quads): Tips at indices 20 and 26 reach forward ($Y > 0.030$) and curve upward ($Z > 0.004$).
    - Wings (20 verts, 8 quads): Swallowtail caudal spurs at indices 36 and 46 project backward ($Y < -0.040$) and outward ($|X| > 0.015$).
  * Dihedral flutter kinematics: tested across $\theta \in [-30^\circ, -15^\circ, 0^\circ, 15^\circ, 25^\circ, 45^\circ, 60^\circ, 80^\circ]$. All face areas remain $> 10^{-7}\text{m}^2$ with no inverted or collapsed triangles.
- **Test Result**: `PASSED` (`TestChallengerButterflyTopology::*` - 11 tests passed).

### 1.5 Flocking Distribution & Vortex Dynamics
- **Requirement**: Bilateral upward vortex spiral ($Z \in [0.88\text{m}, 1.32\text{m}]$, minimum pairwise separation $\ge 150\text{mm} \ge 50\text{mm}$, $|X| \ge 0.35\text{m}$).
- **Observed Metrics in `wardrobe.py:get_butterfly_vortex_positions()`**:
  * Total positions: 10.
  * Bilateral distribution: 5 on left flank ($X > 0$), 5 on right flank ($X < 0$).
  * Elevation range: $Z \in [0.88000\text{m}, 1.31709\text{m}] \subset [0.88\text{m}, 1.32\text{m}]$.
  * Lateral flank clearance: $|X| \in [0.375\text{m}, 0.510\text{m}] \ge 0.35\text{m}$.
  * Radial clearance from vertical axis: $r \in [0.44\text{m}, 0.56\text{m}] \ge 0.40\text{m}$.
  * Minimum pairwise separation: **153.31mm** (between butterfly 1 and 2), which strictly satisfies $\ge 150\text{mm} \ge 50\text{mm}$.
  * String tip alignment: distance between string tip midpoint and butterfly position is $0.0000\text{mm}$.
- **Test Result**: `PASSED` (`TestChallengerFlockingDistribution::*` - 4 tests passed).

---

## 2. Critical Defect Investigation

While `wardrobe.py` functions correctly in isolation, deep empirical inspection revealed two significant defects during character assembly and in master deliverables:

### Defect 1: Butterfly Position Overwrite in `character_assembler.py` (CRITICAL)

#### Observation
In `src/morphomesh/character_assembler.py` lines 1296–1314:
```python
flutter_positions = [
    (0.46 * s, -0.16 * s, 0.96 * s),
    (0.52 * s, -0.06 * s, 1.14 * s),
    (0.44 * s, 0.12 * s, 1.28 * s),
    (0.54 * s, 0.08 * s, 1.06 * s),
    (0.42 * s, -0.10 * s, 0.88 * s),
    (-0.46 * s, -0.16 * s, 0.96 * s),
    (-0.52 * s, -0.06 * s, 1.14 * s),
    (-0.44 * s, 0.12 * s, 1.28 * s),
    (-0.54 * s, 0.08 * s, 1.06 * s),
    (-0.42 * s, -0.10 * s, 0.88 * s),
]

mat_bf = bpy.data.materials.get("Mat_Magic_Butterfly")
for i in range({cfg_obj.butterfly_count}):
    bf_obj = bpy.data.objects.get(f"Prop_Butterfly_{{i:02d}}")
    if bf_obj:
        pos = flutter_positions[i % len(flutter_positions)]
        bf_obj.location = pos
```

#### Empirical Impact
1. **Flocking separation violation**:
   In this hardcoded array, the distance between butterfly 0 `(0.46, -0.16, 0.96)` and butterfly 4 `(0.42, -0.10, 0.88)` is:
   $$d = \sqrt{(0.46 - 0.42)^2 + (-0.16 - -0.10)^2 + (0.96 - 0.88)^2} = \sqrt{0.04^2 + 0.06^2 + 0.08^2} \approx \mathbf{107.70\text{mm}}$$
   This fails the requirement: $\text{minimum separation} \ge 150\text{mm}$.
2. **Marionette strings detachment**:
   `Prop_Marionette_Strings` is synthesized with cord tips aimed at `get_butterfly_vortex_positions()`. Overwriting `bf_obj.location` with the old coordinates creates massive discrepancies between the string tips and the butterflies:
   - Cord 0: string tip to butterfly distance = **136.03mm**
   - Cord 1: string tip to butterfly distance = **167.70mm**
   - Cord 2: string tip to butterfly distance = **247.04mm**
   - Cord 3: string tip to butterfly distance = **152.63mm**
   - **Cord 4: string tip to butterfly distance = 590.39mm**
   - Cord 5: string tip to butterfly distance = **97.59mm**
   - Cord 6: string tip to butterfly distance = **147.83mm**
   - Cord 7: string tip to butterfly distance = **219.17mm**
   - Cord 8: string tip to butterfly distance = **201.92mm**
   - **Cord 9: string tip to butterfly distance = 635.15mm**
   In the 3D scene, the magic threads end in mid-air up to **0.635 meters** away from the butterflies!

#### Root Cause
In `src/morphomesh/wardrobe.py` line 2056, `get_wardrobe_script()` already creates the butterfly objects and positions them at `get_butterfly_flutter_positions()` (the vortex positions).
Subsequently in `character_assembler.py:1296-1314`, a redundant legacy loop re-fetches `bf_obj` and overwrites `bf_obj.location` with the obsolete 10-point array.

---

### Defect 2: Stale M2 Props in On-Disk Master Blend (HIGH)

#### Observation
Direct headless inspection of `output/yu_nian_an/Yu_Nian_An_Master.blend` using Blender 4.5.4 LTS revealed:
```
=== DIRECT CHECK ===
bf0 is: <bpy_struct, Object("Prop_Butterfly_00")>
bf0.data.vertices count: 18
bf0.data.polygons count: 10
v0 = <Vector (0.3894, -0.0798, 0.7307)>, v1 = <Vector (0.3894, -0.0798, 0.7307)>
diff = 0.0mm
```

#### Empirical Impact
1. Butterflies on disk have only 18 vertices (10 faces), not the 48 vertices (24 quads) created in M3.
2. The marionette strings have root vertices collapsed into a single point ($v_0 = v_1$), resulting in zero ribbon width ($0.0000\text{mm}$) and degenerate zero-area faces at the finger roots.

#### Root Cause
Worker M3 updated the Python generators in `src/morphomesh/wardrobe.py` and `src/morphomesh/character_assembler.py`, but did not execute the master assembly pipeline to regenerate `Yu_Nian_An_Master.blend` on disk.

---

## 3. Test Battery Execution Matrix

| Test Suite | Total Tests | Passed | Failed / XFailed | Execution Time | Notes |
|---|---|---|---|---|---|
| `tests/test_wardrobe_m3.py` | 25 | 25 | 0 | 0.10s | All Worker M3 tests pass |
| `tests/test_adversarial_character_assembler.py` | 7 | 7 | 0 | 6.85s | Master assembler baseline passes |
| `tests/test_challenger_m3_props.py` | 32 | 29 | 3 XFAIL | 0.82s | 29 empirical tests pass; 3 strict xfails confirm the defects above |
| **Full Combined Battery** | **64** | **61** | **3 XFAIL** | **7.75s** | 100% execution integrity |

---

## 4. Remediation Steps Required

To achieve `APPROVE` status, the following targeted fixes must be applied by Worker M3 or subsequent implementer:

1. **Fix `src/morphomesh/character_assembler.py` lines 1296–1314**:
   Replace the hardcoded `flutter_positions` array with `get_butterfly_vortex_positions` or eliminate the location re-assignment:
   ```python
   # Option A: Import and serialize vortex positions
   vortex_positions = get_butterfly_vortex_positions(height=cfg_obj.height, count=cfg_obj.butterfly_count)
   # Or Option B: Do not overwrite bf_obj.location since wardrobe_script already set it accurately!
   ```
2. **Regenerate Master Deliverable**:
   Execute `python scripts/build_and_render_master.py` or `character_assembler.py` to regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend` with the 48-vertex butterflies and 0.8mm ribbon strings.
3. **Remove `@pytest.mark.xfail` in `tests/test_challenger_m3_props.py`**:
   Once fixed, all 32 tests in `test_challenger_m3_props.py` will pass cleanly.
