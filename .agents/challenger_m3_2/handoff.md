# Handoff Report: Milestone M3 Props Snapping, Butterfly Topology & Flocking Challenger

**Module**: MorphoMesh Milestone M3 Character Realism Upgrade (Yu Nian An)  
**Agent**: Challenger 2 (Challenger M3.2: Props Snapping, Butterfly Topology & Flocking Empirical Challenger)  
**Recipient**: Parent Agent (`c2422918-70a3-47d9-a8f9-883422a33af0`) / Worker M3  
**Date**: 2026-09-07  
**Status**: Hard Handoff  
**Explicit Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation

1. **Props Topology & Snapping Precision in `src/morphomesh/wardrobe.py`**:
   - `generate_catenary_magic_strings(count=10, height=1.65, rest_pose=True)`:
     * Total vertices: exactly `140` across 10 cords (`verts_per_cord = 14`).
     * Total faces: exactly `120` triangular faces (60 quads, 6 quads per cord).
     * Face areas: all 120 faces have positive area $\ge 1.0546 \times 10^{-5}\text{m}^2 \gg 10^{-9}\text{m}^2$.
     * Ribbon width: $\|\vec{v}_1 - \vec{v}_0\| = 0.8000\text{mm}$, with symmetric offsets $\|\vec{v}_0 - \vec{t}\| = 0.4000\text{mm}$ and $\|\vec{v}_1 - \vec{t}\| = 0.4000\text{mm}$.
     * Root vertex midpoint snap error against `generate_rigify_human_metarig().bones`:
       - Thumb L/R: $0.0049\text{mm}$ ($4.9\ \mu\text{m}$)
       - Index L/R: $0.0056\text{mm}$ ($5.6\ \mu\text{m}$)
       - Middle L/R: $0.0024\text{mm}$ ($2.4\ \mu\text{m}$)
       - Ring L/R: $0.0032\text{mm}$ ($3.2\ \mu\text{m}$)
       - Pinky L/R: $0.0050\text{mm}$ ($5.0\ \mu\text{m}$)
       All 10 cords achieve sub-10-micron error in standalone Python, and strictly $0.0000\text{mm}$ algebraic error in character assembler.

2. **Butterfly Morphology & Dihedral Flutter in `src/morphomesh/wardrobe.py`**:
   - `generate_swallowtail_quad_butterfly(scale=0.045, wing_angle_deg=25.0)`:
     * Exactly 48 vertices, 48 faces (24 quads).
     * Minimum face surface area: $2.7248 \times 10^{-6}\text{m}^2 > 10^{-6}\text{m}^2$. Zero degenerate faces.
     * Dual antennae tips at vertices 20 and 26 project forward ($Y = 0.035$) and upward ($Z = 0.006$).
     * Swallowtail caudal spurs at vertices 36 and 46 project backward ($Y = -0.053$) and outward ($|X| = 0.033$).
     * Dihedral flutter angles $\theta \in [-30^\circ, +80^\circ]$ maintain strictly non-zero face areas ($> 10^{-7}\text{m}^2$).

3. **Flocking Vortex in `src/morphomesh/wardrobe.py`**:
   - `get_butterfly_vortex_positions(scale=1.0)`:
     * 10 positions: 5 on left flank ($X > 0$), 5 on right flank ($X < 0$).
     * Elevation range: $Z \in [0.88000\text{m}, 1.31709\text{m}] \subset [0.88\text{m}, 1.32\text{m}]$.
     * Minimum pairwise Euclidean separation: **153.31mm** (between butterfly 1 and 2), strictly satisfying $\ge 150\text{mm} \ge 50\text{mm}$.
     * Lateral flank clearance: $|X| \in [0.375\text{m}, 0.510\text{m}] \ge 0.35\text{m}$.
     * String tip midpoints coincide with butterfly target positions with $0.0000\text{mm}$ error.

4. **Flocking Overwrite Defect in `src/morphomesh/character_assembler.py` (CRITICAL)**:
   - Verbatim code at `character_assembler.py:1296-1314`:
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
   - Pairwise distance between position 0 `(0.46, -0.16, 0.96)` and position 4 `(0.42, -0.10, 0.88)` is **107.70mm**, failing the requirement $\ge 150\text{mm}$.
   - Distance between string tips and butterflies:
     * Cord 0: 136.03mm
     * Cord 1: 167.70mm
     * Cord 2: 247.04mm
     * Cord 3: 152.63mm
     * **Cord 4: 590.39mm**
     * Cord 5: 97.59mm
     * Cord 6: 147.83mm
     * Cord 7: 219.17mm
     * Cord 8: 201.92mm
     * **Cord 9: 635.15mm**
   - The strings terminate up to **0.635m** away from the butterflies!

5. **Stale M2 Props in On-Disk `Yu_Nian_An_Master.blend` (HIGH)**:
   - Direct headless Blender query on `output/yu_nian_an/Yu_Nian_An_Master.blend`:
     ```
     bf0 is: <bpy_struct, Object("Prop_Butterfly_00")>
     bf0.data.vertices count: 18
     bf0.data.polygons count: 10
     v0 = <Vector (0.3894, -0.0798, 0.7307)>, v1 = <Vector (0.3894, -0.0798, 0.7307)>
     diff = 0.0mm
     ```
   - Butterflies on disk have only 18 vertices (10 faces), and strings have collapsed 0.0mm root vertices with degenerate zero-area faces.

---

## 2. Logic Chain

1. From Observation 1, `generate_catenary_magic_strings()` satisfies all topological invariants (`verts_per_cord = 14`, 140 verts, 120 faces, positive area $> 10^{-5}\text{m}^2$, $0.8\text{mm}$ ribbon width).
2. From Observation 2, `generate_swallowtail_quad_butterfly()` satisfies all anatomical requirements (24 quads, 48 verts, 0 degenerate faces $> 10^{-6}\text{m}^2$, valid dihedral flutter).
3. From Observation 3, `get_butterfly_vortex_positions()` in `wardrobe.py` produces valid upward vortex spiral coordinates with pairwise distance $\ge 153.31\text{mm} \ge 150\text{mm}$ and perfect 0.00mm string tip tethering.
4. From Observation 4, `character_assembler.py:1296-1314` contains redundant legacy code that re-assigns `bf_obj.location` to an obsolete hardcoded array. This overrides the valid positions set by `wardrobe_script`, degrading pairwise separation to 107.70mm (< 150mm requirement) and detaching cords from butterflies by up to 635.15mm.
5. From Observation 5, `output/yu_nian_an/Yu_Nian_An_Master.blend` was not regenerated following M3 props implementation, containing outdated 18-vertex butterflies and collapsed zero-width cords.
6. Combining Observations 4 and 5, character generation through `character_assembler.py` and the existing master deliverable fail key acceptance criteria for flocking separation and prop coherence. Therefore, the implementation cannot be approved as-is.

---

## 3. Caveats

- **Scope of Defect 1**: The defect is localized entirely to lines 1296–1314 of `src/morphomesh/character_assembler.py`. Removing or updating this block immediately restores the 153.3mm vortex positions and 0.00mm string tethering already provided by `wardrobe_script`.
- **Milestone M4 Interaction**: Milestone M4 plans a master asset regeneration for PBR shaders and lighting. However, if `character_assembler.py` is not corrected now, M4 will bake the corrupted 107.7mm flocking positions and detached strings into the final deliverables.
- No other caveats.

---

## 4. Conclusion

**Verdict: `REQUEST_CHANGES`**

While the low-level geometry generators in `src/morphomesh/wardrobe.py` successfully meet all specifications, two integration issues must be remediated:
1. **Fix `src/morphomesh/character_assembler.py` lines 1296–1314**: Stop overwriting `bf_obj.location` with the hardcoded 10-point array so that the vortex positions ($153.31\text{mm} \ge 150\text{mm}$) and cord attachments are preserved.
2. **Regenerate Master Deliverable**: Re-execute the assembly script to produce an updated `output/yu_nian_an/Yu_Nian_An_Master.blend` containing the 48-vertex butterflies and 0.8mm ribbon strings.

---

## 5. Verification Method

To independently verify these findings and reproduce the defects:

1. **Run the Challenger Test Battery**:
   ```bash
   uv run pytest tests/test_challenger_m3_props.py -v
   ```
   *Expected Result*: 29 passed, 3 xfailed (the 3 xfails strictly verify the 3 documented defects).

2. **Run the Full Milestone M3 Regression Battery**:
   ```bash
   uv run pytest tests/test_wardrobe_m3.py tests/test_adversarial_character_assembler.py -v
   ```
   *Expected Result*: 32 passed in ~7s.

3. **Empirical Measurement Commands**:
   - Verify string detachment in `character_assembler.py`:
     ```bash
     uv run python -c "import numpy as np; from morphomesh.wardrobe import get_butterfly_vortex_positions, generate_catenary_magic_strings; targets = get_butterfly_vortex_positions(); s = generate_catenary_magic_strings(rest_pose=True, target_positions=targets); old_bf = [(0.46,-0.16,0.96), (0.52,-0.06,1.14), (0.44,0.12,1.28), (0.54,0.08,1.06), (0.42,-0.10,0.88), (-0.46,-0.16,0.96), (-0.52,-0.06,1.14), (-0.44,0.12,1.28), (-0.54,0.08,1.06), (-0.42,-0.10,0.88)]; print('Cord 9 detachment:', np.linalg.norm(0.5*(np.array(s.vertices[9*14+12])+np.array(s.vertices[9*14+13])) - np.array(old_bf[9]))*1000.0, 'mm')"
     ```
     *Output*: `Cord 9 detachment: 635.15 mm`
   - Verify stale on-disk blend file:
     ```bash
     & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "output/yu_nian_an/Yu_Nian_An_Master.blend" --python-expr "import bpy; bf = bpy.data.objects['Prop_Butterfly_00']; print('On-disk butterfly verts:', len(bf.data.vertices))"
     ```
     *Output*: `On-disk butterfly verts: 18` (Expected: 48).
