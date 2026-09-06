# Investigation & Survey Report: Face Normal Winding Order Fix

**Document ID**: `MM-SURVEY-M1-ITER2-002`  
**Author**: Explorer M1-Iter2-2 (Face Normal Winding Specialist)  
**Date**: 2026-09-05T16:15:00Z  
**Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_2`  
**Target Milestone**: Milestone M1 — Reusable Anatomy Generator & Claw Fix (Iteration 2)  
**Parent Orchestrator**: `504d045c-25c5-48a2-a65a-2a5b368eafa7`  

---

## 1. Executive Summary

Challenger M1-2 detected **104 inverted face normals** in `generate_bear_base_mesh()` via adversarial stress test `test_adversarial_inverted_face_normals`. Empirical investigation confirmed that:
1. `add_box()` in `src/morphomesh/inference_adapter.py` defines 4 side faces (Front $+Y$, Back $-Y$, Left $-X$, Right $+X$) with clockwise vertex winding when viewed from outside the bounding box, pointing face normals directly into the interior volume ($fn \cdot vn = -1.00$). With 13 box primitives in the bear mesh, exactly $13 \times 8 = 104$ triangles are inverted.
2. `add_cylinder(axis="Y")` in `src/morphomesh/inference_adapter.py` exhibits normal inversion because the Cartesian cross product of the $XZ$-plane circle tangent with the $+Y$ cylinder height vector yields $-\vec{n}_{\text{radial}}$, producing 100% inverted side faces ($fn \cdot vn = -0.9960$).
3. `get_blender_generation_script()` in `src/morphomesh/creature_generator.py` has 12/12 inverted box triangles in `box_faces`.

This report provides the exact, verified counter-clockwise (CCW) vertex winding orders for all 6 box faces and cylinder side quads, complete vector calculus proofs, and a verified unified git patch (`inverted_normals.patch`) ready for immediate application by Worker M1.

---

## 2. Mathematical Coordinate Frame & Normal Definitions

In MorphoMesh and Blender 5.2.1, 3D geometry uses a right-handed Cartesian coordinate system:
- $+X$: Lateral Right, $-X$: Lateral Left
- $+Y$: Anterior / Forward, $-Y$: Posterior / Back
- $+Z$: Superior / Up, $-Z$: Inferior / Down

Unit basis cross products:
$$\hat{i} \times \hat{j} = \hat{k}, \quad \hat{j} \times \hat{k} = \hat{i}, \quad \hat{k} \times \hat{i} = \hat{j}$$

For any planar polygon with vertices $(v_0, v_1, v_2, \dots)$, the outward geometric normal is governed by the right-hand rule. For quad $(i_0, i_1, i_2, i_3)$ triangulated by `add_quad(i0, i1, i2, i3)`:
- **Triangle 1**: $(i_0, i_1, i_2)$ with edge vectors $e_1 = v_1 - v_0$, $e_2 = v_2 - v_0$. Geometric normal:
  $$N_1 = (v_1 - v_0) \times (v_2 - v_0)$$
- **Triangle 2**: $(i_0, i_2, i_3)$ with edge vectors $e_1 = v_2 - v_0$, $e_2 = v_3 - v_0$. Geometric normal:
  $$N_2 = (v_2 - v_0) \times (v_3 - v_0)$$

For both triangles to point strictly outward toward the exterior ($N \cdot \hat{n}_{\text{outward}} > 0$), the quad vertices must be traversed in **counter-clockwise (CCW) order** when viewed from the outside looking onto the face.

---

## 3. Investigation of `add_box` (`inference_adapter.py`)

### 3.1 Defect Isolation
In `add_box()` (lines 140–153), a box is defined with center $(cx, cy, cz)$ and half-extents $sx, sy, sz$:
```python
faces_def = [
    # Front (+Y)
    ([(cx - sx, cy + sy, cz - sz), (cx + sx, cy + sy, cz - sz), (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)], (0.0, 1.0, 0.0)),
    # Back (-Y)
    ([(cx + sx, cy - sy, cz - sz), (cx - sx, cy - sy, cz - sz), (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz)], (0.0, -1.0, 0.0)),
    # Left (-X)
    ([(cx - sx, cy - sy, cz - sz), (cx - sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz + sz), (cx - sx, cy - sy, cz + sz)], (-1.0, 0.0, 0.0)),
    # Right (+X)
    ([(cx + sx, cy + sy, cz - sz), (cx + sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz + sz), (cx + sx, cy + sy, cz + sz)], (1.0, 0.0, 0.0)),
    # Top (+Z)
    ([(cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz), (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)], (0.0, 0.0, 1.0)),
    # Bottom (-Z)
    ([(cx - sx, cy + sy, cz - sz), (cx + sx, cy + sy, cz - sz), (cx + sx, cy - sy, cz - sz), (cx - sx, cy - sy, cz - sz)], (0.0, 0.0, -1.0)),
]
```

Computing $N_1 = (v_1 - v_0) \times (v_2 - v_0)$ and $N_2 = (v_2 - v_0) \times (v_3 - v_0)$ for all 6 faces reveals:
| Face | Expected Normal | Computed $N_1 / ||N_1||$ | Computed $N_2 / ||N_2||$ | Dot Product | Status |
|---|---|---|---|---|---|
| Front (+Y) | $(0, 1, 0)$ | $(0, -1, 0)$ | $(0, -1, 0)$ | $-1.00$ | **INVERTED** |
| Back (-Y) | $(0, -1, 0)$ | $(0, 1, 0)$ | $(0, 1, 0)$ | $-1.00$ | **INVERTED** |
| Left (-X) | $(-1, 0, 0)$ | $(1, 0, 0)$ | $(1, 0, 0)$ | $-1.00$ | **INVERTED** |
| Right (+X) | $(1, 0, 0)$ | $(-1, 0, 0)$ | $(-1, 0, 0)$ | $-1.00$ | **INVERTED** |
| Top (+Z) | $(0, 0, 1)$ | $(0, 0, 1)$ | $(0, 0, 1)$ | $+1.00$ | PASS |
| Bottom (-Z) | $(0, 0, -1)$ | $(0, 0, -1)$ | $(0, 0, -1)$ | $+1.00$ | PASS |

### 3.2 Exact Inverted Face Count in Bear Mesh
In `generate_bear_base_mesh()`, exactly 13 box primitives are constructed:
1. `snout`: 2 boxes (snout block + rhinarium tip)
2. `mouth_cavity`: 1 box
3. `jaw`: 1 box
4. `eyelids`: 4 boxes (left/right $\times$ upper/lower)
5. `pads`: 4 boxes (left/right front paws + left/right hind paws foot bases)
6. `dorsal_spine`: 1 box

Total box primitives: $2 + 1 + 1 + 4 + 4 + 1 = 13$.  
Inverted faces per box: 4 quads $= 8$ triangles.  
Total inverted triangles across mesh: $13 \times 8 = 104$.  
This matches Challenger M1-2's defect finding verbatim.

### 3.3 Formulation of Correct Counter-Clockwise Winding Order
To maintain standard texture mapping (`uv_corners = [(0, 0), (1, 0), (1, 1), (0, 1)]`) where $U$ spans the horizontal face axis and $V$ ascends vertically ($Z$), the vertices must be:

1. **Front (+Y)**: Viewed from $+Y$ looking towards $-Y$:
   - $v_0 = (cx + sx, cy + sy, cz - sz)$ — bottom-left for observer ($U=0, V=0$)
   - $v_1 = (cx - sx, cy + sy, cz - sz)$ — bottom-right for observer ($U=1, V=0$)
   - $v_2 = (cx - sx, cy + sy, cz + sz)$ — top-right for observer ($U=1, V=1$)
   - $v_3 = (cx + sx, cy + sy, cz + sz)$ — top-left for observer ($U=0, V=1$)
   - Proof: $v_1 - v_0 = (-2sx, 0, 0)$, $v_2 - v_0 = (-2sx, 0, 2sz)$.
     $N_1 = (-2sx, 0, 0) \times (-2sx, 0, 2sz) = (0, 4sx \cdot sz, 0) \implies (0, 1, 0)$. Dot = $+1.00$.

2. **Back (-Y)**: Viewed from $-Y$ looking towards $+Y$:
   - $v_0 = (cx - sx, cy - sy, cz - sz)$ — bottom-left for observer ($U=0, V=0$)
   - $v_1 = (cx + sx, cy - sy, cz - sz)$ — bottom-right for observer ($U=1, V=0$)
   - $v_2 = (cx + sx, cy - sy, cz + sz)$ — top-right for observer ($U=1, V=1$)
   - $v_3 = (cx - sx, cy - sy, cz + sz)$ — top-left for observer ($U=0, V=1$)
   - Proof: $v_1 - v_0 = (2sx, 0, 0)$, $v_2 - v_0 = (2sx, 0, 2sz)$.
     $N_1 = (2sx, 0, 0) \times (2sx, 0, 2sz) = (0, -4sx \cdot sz, 0) \implies (0, -1, 0)$. Dot = $+1.00$.

3. **Left (-X)**: Viewed from $-X$ looking towards $+X$:
   - $v_0 = (cx - sx, cy + sy, cz - sz)$ — bottom-left for observer ($U=0, V=0$)
   - $v_1 = (cx - sx, cy - sy, cz - sz)$ — bottom-right for observer ($U=1, V=0$)
   - $v_2 = (cx - sx, cy - sy, cz + sz)$ — top-right for observer ($U=1, V=1$)
   - $v_3 = (cx - sx, cy + sy, cz + sz)$ — top-left for observer ($U=0, V=1$)
   - Proof: $v_1 - v_0 = (0, -2sy, 0)$, $v_2 - v_0 = (0, -2sy, 2sz)$.
     $N_1 = (0, -2sy, 0) \times (0, -2sy, 2sz) = (-4sy \cdot sz, 0, 0) \implies (-1, 0, 0)$. Dot = $+1.00$.

4. **Right (+X)**: Viewed from $+X$ looking towards $-X$:
   - $v_0 = (cx + sx, cy - sy, cz - sz)$ — bottom-left for observer ($U=0, V=0$)
   - $v_1 = (cx + sx, cy + sy, cz - sz)$ — bottom-right for observer ($U=1, V=0$)
   - $v_2 = (cx + sx, cy + sy, cz + sz)$ — top-right for observer ($U=1, V=1$)
   - $v_3 = (cx + sx, cy - sy, cz + sz)$ — top-left for observer ($U=0, V=1$)
   - Proof: $v_1 - v_0 = (0, 2sy, 0)$, $v_2 - v_0 = (0, 2sy, 2sz)$.
     $N_1 = (0, 2sy, 0) \times (0, 2sy, 2sz) = (4sy \cdot sz, 0, 0) \implies (1, 0, 0)$. Dot = $+1.00$.

5. **Top (+Z)** (Existing order preserved):
   - $v_0 = (cx - sx, cy - sy, cz + sz)$
   - $v_1 = (cx + sx, cy - sy, cz + sz)$
   - $v_2 = (cx + sx, cy + sy, cz + sz)$
   - $v_3 = (cx - sx, cy + sy, cz + sz)$
   - Normal: $(0, 0, 1)$. Dot = $+1.00$.

6. **Bottom (-Z)** (Existing order preserved):
   - $v_0 = (cx - sx, cy + sy, cz - sz)$
   - $v_1 = (cx + sx, cy + sy, cz - sz)$
   - $v_2 = (cx + sx, cy - sy, cz - sz)$
   - $v_3 = (cx - sx, cy - sy, cz - sz)$
   - Normal: $(0, 0, -1)$. Dot = $+1.00$.

---

## 4. Investigation of `add_cylinder` (`inference_adapter.py`)

### 4.1 Vector Calculus Proof of Inversion
In `add_cylinder(..., axis)`:
For ring segment $s \in [0, \text{segments}-1]$, let $\theta_s = \frac{2\pi s}{\text{segments}}$, $\Delta\theta > 0$.
The circumferential tangent vector is $\vec{t} = \frac{d\vec{p}}{d\theta}$.
The longitudinal cylinder height vector is $\vec{h}$.
The quad normal is proportional to $\vec{t} \times \vec{h}$.

1. **`axis == "Z"`**:
   - $\vec{p}(\theta) = (r\cos\theta, r\sin\theta, 0)$
   - $\vec{t} = (-r\sin\theta, r\cos\theta, 0)$
   - $\vec{h} = (0, 0, h)$
   - $\vec{t} \times \vec{h} = (r h \cos\theta, r h \sin\theta, 0) = r h \vec{n}_{\text{radial}}$
   - $\implies$ **Outward ($+1.00$)**.

2. **`axis == "X"`**:
   - $\vec{p}(\theta) = (0, r\cos\theta, r\sin\theta)$
   - $\vec{t} = (0, -r\sin\theta, r\cos\theta)$
   - $\vec{h} = (h, 0, 0)$
   - $\vec{t} \times \vec{h} = (0, r h \cos\theta, r h \sin\theta) = r h \vec{n}_{\text{radial}}$
   - $\implies$ **Outward ($+1.00$)**.

3. **`axis == "Y"`**:
   - $\vec{p}(\theta) = (r\cos\theta, 0, r\sin\theta)$
   - $\vec{t} = (-r\sin\theta, 0, r\cos\theta)$
   - $\vec{h} = (0, h, 0)$
   - $\vec{t} \times \vec{h} = (-r h \cos\theta, 0, -r h \sin\theta) = -r h \vec{n}_{\text{radial}}$
   - $\implies$ **INWARD ($-1.00$)**.

The inversion occurs specifically because in right-handed 3D space, $\hat{i} \times \hat{k} = -\hat{j}$. The cyclic order of coordinates for circle parameterization is $X$ then $Z$, which opposes the positive orientation around $Y$.

### 4.2 Remediation
In `add_cylinder()` lines 204–211:
```python
# Connect side quads
for s in range(segments):
    next_s = (s + 1) % segments
    if axis == "Y":
        self.add_quad(
            bottom_indices[next_s],
            bottom_indices[s],
            top_indices[s],
            top_indices[next_s],
        )
    else:
        self.add_quad(
            bottom_indices[s],
            bottom_indices[next_s],
            top_indices[next_s],
            top_indices[s],
        )
```
- Empirical validation: With this conditional branch, all cylinder faces for `axis="Y"` achieve $dot = +0.9960 > 0.50$ (outward).

---

## 5. Investigation of `get_blender_generation_script()` (`creature_generator.py`)

In `get_blender_generation_script()`, lines 450–457:
All 12 triangles in `box_faces` have reversed index order:
```python
box_faces = [
    (s_idx, s_idx+1, s_idx+2), (s_idx, s_idx+2, s_idx+3),
    (s_idx+4, s_idx+6, s_idx+5), (s_idx+4, s_idx+7, s_idx+6),
    (s_idx, s_idx+4, s_idx+5), (s_idx, s_idx+5, s_idx+1),
    (s_idx+2, s_idx+6, s_idx+7), (s_idx+2, s_idx+7, s_idx+3),
    (s_idx, s_idx+3, s_idx+7), (s_idx, s_idx+7, s_idx+4),
    (s_idx+1, s_idx+5, s_idx+6), (s_idx+1, s_idx+6, s_idx+2),
]
```
Reversing the second and third indices in each triangle produces exact outward normals for all 12 triangles:
```python
box_faces = [
    (s_idx, s_idx+2, s_idx+1), (s_idx, s_idx+3, s_idx+2),      # bottom (-Z)
    (s_idx+4, s_idx+5, s_idx+6), (s_idx+4, s_idx+6, s_idx+7),  # top (+Z)
    (s_idx, s_idx+5, s_idx+4), (s_idx, s_idx+1, s_idx+5),      # back (-Y)
    (s_idx+2, s_idx+7, s_idx+6), (s_idx+2, s_idx+3, s_idx+7),  # front (+Y)
    (s_idx, s_idx+7, s_idx+3), (s_idx, s_idx+4, s_idx+7),      # left (-X)
    (s_idx+1, s_idx+6, s_idx+5), (s_idx+1, s_idx+2, s_idx+6),  # right (+X)
]
```

---

## 6. Empirical Verification Summary

1. **Simulation on Canonical Bear Base Mesh**:
   When `patched_add_box` is applied:
   - Inverted faces count in `test_adversarial_inverted_face_normals`: drops from **104 to 0**.
   - All 18 standardized vertex groups remain intact with valid non-zero counts.
   - Indented nostrils, recessed mouth cavity, 12 teeth components, and eyelid bracketing continue to pass 100%.
2. **Simulation on Cylinder Generation**:
   - `axis="Z"`: 0 inverted faces ($dot = +0.9960$).
   - `axis="Y"`: drops from 24/24 inverted to 0 inverted faces ($dot = +0.9960$).
   - `axis="X"`: 0 inverted faces ($dot = +0.9960$).
3. **Simulation on Blender Socket Script**:
   - Inverted triangles in `box_faces`: drops from **12/12 to 0/12**.
4. **Git Patch Validity**:
   - Executed: `git apply --check .agents/explorer_m1_iter2_2/inverted_normals.patch`.
   - Exit code: 0 (clean, no rejects or warnings).

---

## 7. Deliverables & Handoff Reference

- Complete patch file: `.agents/explorer_m1_iter2_2/inverted_normals.patch`
- Formal 5-component handoff report: `.agents/explorer_m1_iter2_2/handoff.md`
