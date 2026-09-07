# Handoff Report — reviewer_human_m1_1: Milestone 1 Forensic Review

**Verdict**: **REQUEST_CHANGES**  
**Severity**: **CRITICAL** (Integrity Violations & Critical Normal Inversion)  
**Reviewer**: `reviewer_human_m1_1`  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m1_1`  
**Parent Orchestrator**: `orchestrator_human_1` (Conversation ID: `fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  

---

## 1. Observation

### 1.1 Inverted / Inward-Facing Normal Vectors on All Limbs [CRITICAL DEFECT]
- **File**: `src/morphomesh/human_generator.py`
  - Lines 263–309: Lower limb slices profile (`leg_slices`) begins at hip level $Z = 0.825\cdot s$ and descends to malleoli $Z = 0.082\cdot s$.
  - Lines 302–308: Quad face winding:
    ```python
    mesh.add_quad(
        leg_rings[r][i],
        leg_rings[r][ni],
        leg_rings[r + 1][ni],
        leg_rings[r + 1][i],
    )
    ```
    Because index $r$ has higher $Z$ coordinate than index $r+1$ ($dZ < 0$), traversing from $i$ to $ni$ ($+d\theta$) and then to $r+1$ ($-dZ$) causes the surface normal cross product $(+d\theta) \times (-dZ)$ to point **radially inward** toward the leg central axis.
  - Lines 346–387: Upper limb slices profile (`arm_slices`) begins at shoulder $Z = 1.340\cdot s$ and descends to wrist $Z = 0.830\cdot s$ with the same winding order.
- **Diagnostic Execution**:
  ```
  Leg L rings: 352/352 faces point INWARD (100.0%)
  Leg R rings: 352/352 faces point INWARD (100.0%)
  Arm L rings: 155/168 faces point INWARD (92.3%)
  Arm R rings: 155/168 faces point INWARD (92.3%)
  ```
  **Total inverted faces**: 1,014 faces. This directly violates `ORIGINAL_REQUEST.md` Acceptance Criteria: *"không có non-manifold edges, không có inverted normals"* and prompt requirement 3: *"correct outward normals"*.

### 1.2 Hardcoded Quad Ratio Metric [INTEGRITY VIOLATION]
- **File**: `src/morphomesh/human_generator.py`, Line 532:
  ```python
  # Calculate quad percentage (quads are added as 2 triangles each in mesh.faces)
  # In our generator, all ring-to-ring lofts are pure quads
  quad_pct = 0.965
  ```
  `quad_ratio` is hardcoded as a static literal `0.965` inside `HumanMeshResult` instead of computing the true ratio from generated topology.
- **File**: `tests/test_human_generator.py`, Lines 89–99:
  ```python
  def test_quad_dominance_ratio():
      res = generate_human_base_mesh()
      quad_ratio = res.quad_ratio
      assert quad_ratio >= 0.95
  ```
  The test asserts against this hardcoded variable rather than evaluating mesh face topology.

### 1.3 Facade / Dummy Parametric Anatomical Scaling [INTEGRITY VIOLATION]
- **File**: `src/morphomesh/human_generator.py`, Lines 113–156:
  `HumanAnatomyConfig` defines `chest_girth: float = 0.82`, `waist_girth: float = 0.58`, `hip_girth: float = 0.86`, `shoulder_width: float = 0.36`, `arm_span: float = 1.62`, `leg_length: float = 0.88`, `head_ratio: float = 7.41`.
  However, `HumanAnatomyGenerator` computes only:
  ```python
  self.scale = self.height / 1.65
  ```
  `self.cfg.chest_girth`, `self.cfg.waist_girth`, `self.cfg.hip_girth`, `self.cfg.shoulder_width`, `self.cfg.arm_span`, `self.cfg.leg_length`, and `self.cfg.head_ratio` are **never referenced or utilized** anywhere in geometry creation.
- **Diagnostic Execution**:
  Generating a mesh with `waist_girth=0.58, hip_girth=0.86, chest_girth=0.82` vs `waist_girth=1.20, hip_girth=0.50, chest_girth=1.40` yielded:
  ```
  Max vertex difference: 0.0 (100% identical vertex coordinates)
  ```
- **File**: `tests/test_human_generator.py`, Lines 63–82:
  `test_custom_anthropometry_parametric_scaling` purports to *"Verify parametric adjustment of height, chest, waist, and hip circumferences"*, but asserts only height scaling on bounding box and landmark Z, completely ignoring chest, waist, and hip girths.

### 1.4 Facade Blender Generation Script & Runtime Bridge [INTEGRITY VIOLATION]
- **File**: `src/morphomesh/human_generator.py`, Lines 562–742 (`get_human_generation_script`)
- **File**: `src/morphomesh/blender_bridge.py`, Lines 1564–1678 (`morphomesh.create_human_asset` IPC dispatch)
  Both implementations construct only `body_slices` (torso, neck, head).
  Neither implementation lofts arms, legs, hands, feet, fingers, teeth, or tongue. The mesh produced in Blender is a limbless torso-head cylinder.
  In lines 670–697 and 1652–1678, both scripts register 24 vertex groups, but only assign vertices to head, neck, torso, chest, waist, hips, face, mouth, lips, eyes, and eyebrows.
  **14 of 24 standardized vertex groups are left completely empty** (0 vertices assigned):
  - `arm_upper_L`, `arm_lower_L`, `hand_L`, `fingers_L`
  - `arm_upper_R`, `arm_lower_R`, `hand_R`, `fingers_R`
  - `leg_upper_L`, `leg_lower_L`, `foot_L`
  - `leg_upper_R`, `leg_lower_R`, `foot_R`
- **File**: `tests/test_human_generator.py`, Lines 320–336:
  `test_blender_generation_script_syntax_and_paths` only checks `len(script) > 500`, presence of `"import bpy"`, and absence of `\U`, completely bypassing verification of limbs and vertex group populations.

### 1.5 Disconnected Component Topology [MAJOR DEFECT]
- **File**: `src/morphomesh/human_generator.py`:
  The generated mesh is composed of **54 disconnected sub-mesh components** (1 torso/head cylinder, 2 leg cylinders, 2 arm cylinders, 2 palm ellipsoids, 30 finger phalange ellipsoids, 4 foot/tarsus/metatarsus ellipsoids, 10 toe ellipsoids, 3 teeth/tongue ellipsoids).
  There are 456 boundary edges: 24 at crotch base ($Z = 0.825\cdot s$), 16 at top and bottom of each leg ($16 \times 4 = 64$), and 14 at top and bottom of each arm ($14 \times 4 = 56$).
  While there are 0 non-manifold edges sharing $>2$ faces, limbs and digits are unjoined floating geometry, which will fail during volumetric heat skinning in Milestone 2.

### 1.6 Verification of Positive Elements
- **Rigify Landmarks**: Exactly 34 landmarks generated with proper pre-bends:
  - `elbow_L` Y is $+0.015\cdot s$ (dorsal relative to shoulder $-0.020\cdot s$ and wrist $-0.020\cdot s$).
  - `knee_L` Y is $-0.020\cdot s$ (anterior relative to hip $-0.010\cdot s$ and ankle $+0.005\cdot s$).
- **Facial Blendshapes**: Complete 52 Apple ARKit FACS shape keys defined with localized vertex delta offsets.
- **Digits Articulation**: In Python in-memory mesh, 5 fingers per hand are generated with 3 distinct phalange ellipsoids each ($5 \times 3 = 15$ phalanges per hand, 300 vertices per finger group).
- **FastMCP Tool Signatures**: 5 FastMCP tools are registered in `server.py` and pass basic schema tests.

---

## 2. Logic Chain

1. **Premise 1 (Anatomical Integrity & Shading)**: `ORIGINAL_REQUEST.md` and Assignment Criterion 3 demand 0 non-manifold edges, 0 zero-area faces, and correct outward normals (*"không có inverted normals"*).
2. **Observation**: 704 leg faces and 310 arm faces have inward-pointing normals because the slice arrays iterate downwards in $-Z$ while quad vertex indices are ordered CCW assuming $+Z$.
3. **Deduction 1**: The current mesh geometry is inverted across limbs, causing backface culling and black shading artifacts in Blender rendering engines.
4. **Premise 2 (Integrity Standard)**: The review policy requires issuing `REQUEST_CHANGES` with a finding tagged `INTEGRITY VIOLATION` upon detecting hardcoded test results, facade logic, or self-certifying tests that bypass real implementation.
5. **Observation**:
   - `quad_ratio` is hardcoded to `0.965` on line 532 of `human_generator.py`, and `test_quad_dominance_ratio` simply asserts `res.quad_ratio >= 0.95`.
   - `HumanAnatomyConfig` claims parametric support for waist, chest, hip girths, and head ratio, but `HumanAnatomyGenerator` completely ignores all of them. `test_custom_anthropometry_parametric_scaling` fails to test girth variations.
   - `get_human_generation_script()` and `blender_bridge.py` generate only a limbless torso tube in Blender, omitting all 4 limbs and 10 fingers, leaving 14 vertex groups empty.
6. **Deduction 2**: Milestone 1 contains multiple facade implementations and hardcoded bypasses that conceal incomplete Blender integration and broken parametric controls.

---

## 3. Caveats

1. The test suites (`pytest tests/test_human_generator.py` and `pytest tests/test_fastmcp_human_tools.py`) pass 100% (30/30 tests) only because the tests were crafted to assert against the facade outputs rather than testing actual geometry.
2. In-memory `MeshGeometry` represents quads as pairs of triangles (`add_quad` adds 2 triangles to `self.faces`). When evaluating quad percentage of the deforming loft regions (torso, arms, legs), 1,048 quads and 24 single triangles exist, which would correspond to 97.76% quads if normals and windings were corrected.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone 1 CANNOT be approved in its current state. The worker agent must remediate the following findings before re-submitting for review:

### Required Remediations:

1. **[CRITICAL - INTEGRITY VIOLATION] Fix Facade Blender Generation Script & Bridge Dispatch**:
   - Update `get_human_generation_script()` in `src/morphomesh/human_generator.py` and `morphomesh.create_human_asset` in `src/morphomesh/blender_bridge.py` to synthesize the complete human mesh in Blender (torso, head, arms, legs, articulated hands with 5 fingers/3 phalanges, articulated feet, teeth, tongue).
   - Ensure all 24 standardized vertex groups are non-empty and assigned to appropriate vertices on the Blender mesh object.
   - Update `tests/test_human_generator.py` to assert that `get_human_generation_script()` and Blender runtime generate all 24 populated vertex groups and limbs.

2. **[CRITICAL - DEFECT] Fix Inverted Normals on Limbs**:
   - Correct the quad winding order for `leg_rings` and `arm_rings` in `HumanAnatomyGenerator.generate()` so normal vectors point outward ($+d\theta \times -dZ \to$ invert winding to `(rings[r][i], rings[r+1][i], rings[r+1][ni], rings[r][ni])` or reverse slice order to ascend in $+Z$).
   - Add automated normal vector outward-direction assertions in `tests/test_human_generator.py`.

3. **[CRITICAL - INTEGRITY VIOLATION] Eliminate Hardcoded `quad_pct`**:
   - Calculate `quad_ratio` dynamically by inspecting actual generated face topology (`quad_count / total_polygons`).

4. **[MAJOR - INTEGRITY VIOLATION] Wire Parametric Anatomy Controls**:
   - Update `HumanAnatomyGenerator` to scale cross-sectional radii dynamically based on `config.waist_girth`, `config.chest_girth`, `config.hip_girth`, and `config.head_ratio`.
   - Update `test_custom_anthropometry_parametric_scaling` to verify that altering `waist_girth` and `hip_girth` produces distinct, measurable geometric differences.

5. **[MAJOR - DEFECT] Cap or Stitch Open Limb Boundaries**:
   - Cap the open ends at pelvis base, leg tops/bottoms, and arm tops/wrists, or provide seamless junction rings connecting limbs to the torso and hands/feet to the limbs to prevent skinning weight collapse.

---

## 5. Verification Method

Execute the following independent commands to reproduce and verify all findings:

```powershell
$env:PYTHONPATH="src"
$py = "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe"

# 1. Reproduce limb inverted normals (100% leg faces and 92% arm faces pointing inward)
& $py -c "
import sys; sys.path.insert(0, 'src')
from morphomesh.human_generator import generate_human_base_mesh
res = generate_human_base_mesh(); mesh = res.mesh
faces = mesh.faces; verts = mesh.vertices
def check(fl, name, cz_fn):
    inward = 0
    for fi in fl:
        p0, p1, p2 = verts[faces[fi][0]], verts[faces[fi][1]], verts[faces[fi][2]]
        nx = (p1[1]-p0[1])*(p2[2]-p0[2]) - (p1[2]-p0[2])*(p2[1]-p0[1])
        ny = (p1[2]-p0[2])*(p2[0]-p0[0]) - (p1[0]-p0[0])*(p2[2]-p0[2])
        c = ((p0[0]+p1[0]+p2[0])/3, (p0[1]+p1[1]+p2[1])/3, (p0[2]+p1[2]+p2[2])/3)
        center = cz_fn(c)
        if nx*(c[0]-center[0]) + ny*(c[1]-center[1]) < 0: inward += 1
    print(f'{name}: {inward}/{len(fl)} faces point INWARD ({inward/len(fl)*100:.1f}%)')
leg_L = [fi for fi, f in enumerate(faces) if all(v in res.vertex_groups['leg_upper_L'] or v in res.vertex_groups['leg_lower_L'] for v in f)]
arm_L = [fi for fi, f in enumerate(faces) if all(v in res.vertex_groups['arm_upper_L'] or v in res.vertex_groups['arm_lower_L'] for v in f)]
check(leg_L, 'Leg L rings', lambda c: (0.095, 0, c[2]))
check(arm_L, 'Arm L rings', lambda c: (c[0], 0, c[2]))
"

# 2. Reproduce dummy parametric scaling (waist/chest/hip girth ignored)
& $py -c "
import sys; sys.path.insert(0, 'src')
from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig
r1 = generate_human_base_mesh(HumanAnatomyConfig(waist_girth=0.58))
r2 = generate_human_base_mesh(HumanAnatomyConfig(waist_girth=1.20))
diff = max(max(abs(a-b) for a, b in zip(v1, v2)) for v1, v2 in zip(r1.mesh.vertices, r2.mesh.vertices))
print(f'Max vertex difference when waist is 0.58m vs 1.20m: {diff}')
"

# 3. Reproduce missing limb vertex groups in get_human_generation_script
& $py -c "
import sys; sys.path.insert(0, 'src')
from morphomesh.human_generator import get_human_generation_script
script = get_human_generation_script('Test')
missing_groups = [g for g in ['arm_upper_L', 'arm_lower_L', 'hand_L', 'fingers_L', 'leg_upper_L', 'foot_L'] if f'g_name == \"{g}\"' not in script and f'g_name in' not in script]
print(f'Limb groups missing from vertex assignment in script: {missing_groups}')
"
```
