# Handoff Report - Empirical Challenge of Milestone 2 (Human Rigging & Blendshapes)

**Agent**: `challenger_human_m2_1`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T02:01:00Z  
**Verdict**: **CHALLENGE** (Critical Functional Defects Found in Live Blender Execution & Anthropometric Articulation)  

---

## 1. Observation

### 1.1 Scope & Test Execution
- Inspected implementation code:
  - `src/morphomesh/human_rigging.py` (1454 lines)
  - `src/morphomesh/blender_bridge.py` (2475 lines)
  - `tests/test_human_rigging.py` (411 lines)
- Authored dedicated adversarial stress-test suite:
  - `tests/test_adversarial_rigging.py` (576 lines, 24 test cases)
- Executed automated test harness:
  - Command: `$env:PYTHONPATH="E:\tool\mcp\MorphoMesh\src"; python -m pytest tests/test_adversarial_rigging.py -v`
  - Output: `22 passed, 2 xfailed in 3.97s` (exit code 0)
- Executed full human regression suite:
  - Command: `$env:PYTHONPATH="E:\tool\mcp\MorphoMesh\src"; python -m pytest tests/test_human_generator.py tests/test_adversarial_human_generator.py tests/test_fastmcp_human_tools.py tests/test_adversarial_fastmcp_bridge_human.py tests/test_human_rigging.py tests/test_adversarial_rigging.py`
  - Output: `173 passed, 2 xfailed in 19.98s` (exit code 0)
- Verified Flake8 lint compliance:
  - Command: `flake8 --select=F tests/test_adversarial_rigging.py`
  - Output: `Exit code 0` (0 errors)

---

### 1.2 Observed Critical Defect 1: Headless Blender Script Generates Empty Shells with 0 Weights and 0 Shape Key Deltas

#### Verbatim Code Inspection:
1. In `src/morphomesh/human_rigging.py`, lines 1349-1354:
```python
# Create vertex groups for all 163 DEF bones
def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
for b_name in def_bones:
    if b_name not in obj.vertex_groups:
        obj.vertex_groups.new(name=b_name)
```
2. In `src/morphomesh/human_rigging.py`, lines 1376-1378:
```python
for k_name in arkit_52:
    if k_name not in obj.data.shape_keys.key_blocks:
        obj.shape_key_add(name=k_name, from_mix=False)
```
3. In `src/morphomesh/blender_bridge.py`, lines 1748-1753:
```python
# Bind skinning
if obj and obj.type == 'MESH':
    mod = obj.modifiers.get("Armature") or obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = arm_obj
    mod.use_deform_preserve_volume = True
```

#### Verbatim Tool Command & Output in Blender 4.5.4 LTS:
Command:
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --factory-startup --python-expr "
import sys
sys.path.insert(0, r'E:\tool\mcp\MorphoMesh\src')
sys.path.append(r'C:\Users\Admin\AppData\Local\Programs\Python\Python311\Lib\site-packages')

import bpy, math
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script

mesh_name = 'Human_Base_Mesh'
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name))

obj = bpy.data.objects[mesh_name]
arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']

# Count vertices with DEF weights
def_group_indices = {g.index for g in obj.vertex_groups if g.name.startswith('DEF-')}
weighted_verts = sum(1 for v in obj.data.vertices if any(g.group in def_group_indices and g.weight > 0 for g in v.groups))

# Rotate forearm by 90 degrees in pose mode
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
pbone = arm.pose.bones.get('DEF-forearm.L')
if pbone:
    pbone.rotation_mode = 'XYZ'
    pbone.rotation_euler = (math.radians(90), 0, 0)

bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = obj.evaluated_get(depsgraph)
eval_mesh = eval_obj.to_mesh()

arm_low_vg = obj.vertex_groups.get('arm_lower_L')
v_indices = [v.index for v in obj.data.vertices for g in v.groups if arm_low_vg and g.group == arm_low_vg.index and g.weight > 0.5]
rest_pos = [list(obj.data.vertices[i].co) for i in v_indices]
def_pos = [list(eval_mesh.vertices[i].co) for i in v_indices]
max_disp = max((math.sqrt(sum((a - b)**2 for a, b in zip(p0, p1))) for p0, p1 in zip(rest_pos, def_pos)), default=0.0)

# Check shape key deltas in Blender
basis = obj.data.shape_keys.key_blocks['Basis']
non_zero_keys = sum(
    1 for kb in obj.data.shape_keys.key_blocks
    if kb.name != 'Basis' and any((kb.data[i].co - basis.data[i].co).length > 1e-6 for i in range(len(kb.data)))
)

print(f'TOTAL VERTS: {len(obj.data.vertices)}')
print(f'WEIGHTED_VERTS_COUNT: {weighted_verts}')
print(f'MAX_DEFORMATION_DISPLACEMENT: {max_disp:.6f} m')
print(f'NON_ZERO_SHAPE_KEYS_IN_BLENDER: {non_zero_keys}')
"
```
Output:
```
Verified DEF bones: 163 (64 body + 99 facial)
Verified Shape keys: 52 ARKit keys
TOTAL VERTS: 2144
WEIGHTED_VERTS_COUNT: 0
MAX_DEFORMATION_DISPLACEMENT: 0.000000 m
NON_ZERO_SHAPE_KEYS_IN_BLENDER: 0
```
- **Direct Finding**:
  - `WEIGHTED_VERTS_COUNT: 0` out of 2,144 vertices. All 163 DEF vertex groups in Blender are empty shells.
  - When bones rotate by 90 degrees, `MAX_DEFORMATION_DISPLACEMENT: 0.000000 m`. The mesh does not deform at all.
  - `NON_ZERO_SHAPE_KEYS_IN_BLENDER: 0` out of 52 shape keys. All 52 shape keys in Blender are identical copies of Basis with zero displacement.

---

### 1.3 Observed Critical Defect 2: Hardcoded `palm_x` Breaks 10-Finger Partitioning on Non-Default Arm Spans

#### Verbatim Code Inspection:
In `src/morphomesh/human_rigging.py`, lines 731-744:
```python
scale_f = lm.get("head_top", (0, 0, 1.65))[2] / 1.65
palm_x = s_sign * 0.385 * scale_f
rel_x = (vx - palm_x) * s_sign

if rel_x > 0.017 * scale_f:
    best_digit = "thumb"
elif rel_x > 0.007 * scale_f:
    best_digit = "f_index"
elif rel_x > -0.003 * scale_f:
    best_digit = "f_middle"
elif rel_x > -0.013 * scale_f:
    best_digit = "f_ring"
else:
    best_digit = "f_pinky"
```
Note: Lines 662-669 pre-extract actual finger bone locations into `finger_data`, but `finger_data` was left completely unused.

#### Verbatim Tool Command & Output:
Command:
```powershell
python -c "
from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig
from morphomesh.human_rigging import generate_rigify_human_metarig, calculate_anti_pinch_weights

# Case A: Broad shoulders / long arm span
cfg_broad = HumanAnatomyConfig(shoulder_width=0.50, arm_span=2.0)
res_broad = generate_human_base_mesh(config=cfg_broad)
meta_broad = generate_rigify_human_metarig(landmarks=res_broad.landmarks)
w_broad = calculate_anti_pinch_weights(res_broad.mesh, meta_broad, landmarks=res_broad.landmarks)

digits_broad = {d: 0 for d in ['thumb', 'f_index', 'f_middle', 'f_ring', 'f_pinky']}
for v in res_broad.vertex_groups.get('fingers_L', []):
    for d in digits_broad:
        if w_broad.get_vertex_weight(v, f'DEF-{d}.01.L') > 0:
            digits_broad[d] += 1
            break
print('Broad Shoulders Digits:', digits_broad)

# Case B: Narrow shoulders / short arm span
cfg_narrow = HumanAnatomyConfig(shoulder_width=0.28, arm_span=1.30)
res_narrow = generate_human_base_mesh(config=cfg_narrow)
meta_narrow = generate_rigify_human_metarig(landmarks=res_narrow.landmarks)
w_narrow = calculate_anti_pinch_weights(res_narrow.mesh, meta_narrow, landmarks=res_narrow.landmarks)

digits_narrow = {d: 0 for d in ['thumb', 'f_index', 'f_middle', 'f_ring', 'f_pinky']}
for v in res_narrow.vertex_groups.get('fingers_L', []):
    for d in digits_narrow:
        if w_narrow.get_vertex_weight(v, f'DEF-{d}.01.L') > 0:
            digits_narrow[d] += 1
            break
print('Narrow Shoulders Digits:', digits_narrow)
"
```
Output:
```
Broad Shoulders Digits: {'thumb': 270, 'f_index': 0, 'f_middle': 0, 'f_ring': 0, 'f_pinky': 0}
Narrow Shoulders Digits: {'thumb': 0, 'f_index': 0, 'f_middle': 0, 'f_ring': 0, 'f_pinky': 270}
```
- **Direct Finding**:
  - Whenever `shoulder_width` or `arm_span` departs from default, the cylinder partitioning completely collapses: all 270 finger vertices are mapped to `thumb` (on broad shoulders) or `pinky` (on narrow shoulders).
  - Four out of five fingers receive exactly zero vertex weights. Moving individual fingers in pose mode moves either the whole hand or nothing.

---

### 1.4 Observed Confirmed Robust Capabilities
Under canonical and extreme scales (tested in Python memory):
1. **Metarig Architecture**:
   - Exactly 163 DEF bones (64 body + 99 facial) across heights from 1.2m to 2.2m, extreme WHR (0.33 to 1.375), and chest variations (0.55m to 1.40m).
   - Zero degenerate bone lengths ($> 1\text{mm}$ for all bones).
   - Pre-bends strictly maintained: $+Y$ on elbow ($> 0.010\text{m}$) and $-Y$ on knee ($< -0.015\text{m}$).
2. **Skin Weights Mathematical Normalization**:
   - Strict weight normalization: 100% of vertices sum to $1.000000 \pm 10^{-6}$ across all scales.
3. **Simulated Joint Articulation Physics**:
   - **Elbow 90 deg flexion**: maintains 100% cross-sectional diameter ($D_{90} / D_0 = 1.00$, minimum distance to pivot $= 0.0216\text{m}$).
   - **Knee 90 deg flexion**: patella rigid sesamoid locking preserves 97% of radial thickness from joint pivot ($R_{90} / R_0 = 0.97$).
   - **Shoulder 90 deg abduction**: axilla fold displacement is clamped to 25% of arm movement, anchoring the skin fold to `DEF-spine.003`.
4. **52 ARKit Facial Blendshapes**:
   - All 52 shape keys displace non-zero vertices in Python memory with zero NaNs and zero Infs across scales (0.727, 1.0, 1.333, 1.75).
   - Displacements strictly align with anatomical facial zones.

---

## 2. Logic Chain

1. **Premise 1 (Acceptance Criteria Mandate)**:
   - `ORIGINAL_REQUEST.md` §R1 & Acceptance Criteria require:
     - "Khung xương hoạt động trơn tru, uốn gập tay chân không bị móp/méo bất thường tại khớp khuỷu tay, đầu gối và vai."
     - "Thiết lập hệ thống xương Rigify hoàn chỉnh, gắn trọng số da (vertex weighting) chuẩn xác, cùng bộ Shape Keys biểu cảm khuôn mặt (52 ARKit FACS blendshapes) sẵn sàng cho mocap/lip-sync."
     - Standalone script generation for Blender 4.5+ execution.
2. **Premise 2 (Empirical State of Blender Integration)**:
   - As observed in §1.2, `get_rigging_script` creates vertex group names and shape key names, but omits:
     - Assignment of weights: `obj.vertex_groups[b_name].add([vi], w, 'REPLACE')`.
     - Assignment of displacement vectors: `kb.data[vi].co += mathutils.Vector((dx, dy, dz))`.
   - In live Blender 4.5.4 LTS, `weighted_verts = 0`, `max_disp = 0.000000 m`, and `non_zero_keys = 0`.
3. **Premise 3 (Empirical State of Finger Articulation)**:
   - As observed in §1.3, finger partitioning relies on `palm_x = 0.385 * (height / 1.65)`.
   - When character anatomy has customized shoulder width or arm span, all finger vertices collapse into 1 finger, leaving 4 fingers with zero weights.
4. **Inference**:
   - While the Python data structures (`SkinWeightMap`, `shape_key_deltas`) are mathematically correct in memory, the asset inside Blender cannot articulate or deform, and facial animation is completely inactive.
   - Customized anthropometric variations fail finger articulation.
5. **Conclusion**:
   - Milestone 2 cannot be confirmed as production-ready. The verdict must be **CHALLENGE**, requiring remediation by `worker_human_m2`.

---

## 3. Caveats

- **Dual Quaternion Skinning (DQS)**: Blender modifier configuration has `use_deform_preserve_volume = True`, which is the correct setting for volume preservation. Once vertex weights are populated into the vertex groups, DQS will function as intended.
- **Python-Level vs Blender-Level Disconnect**: The pure Python functions (`calculate_anti_pinch_weights`, `generate_arkit_52_blendshapes`) calculate valid values; the failure is purely in the bridge serialization / script generation step (`get_rigging_script` and `blender_bridge.py` lines 1681-1780).
- **No Manual Edits Made**: Per challenger constraints, no production code was modified. The adversarial test suite `tests/test_adversarial_rigging.py` codifies the reproduction harness.

---

## 4. Conclusion & Required Remediation

### Final Verdict: **CHALLENGE**

### Actionable Remediation Plan for Worker M2:

1. **Remediation Item 1: Populate Skin Weights and Shape Key Deltas in `get_rigging_script` & `blender_bridge.py`**:
   - In `get_rigging_script(mesh_obj_name, landmarks, config)`:
     - Serialize `weight_map = calculate_anti_pinch_weights(mesh, metarig, landmarks)` and inject Python loop:
       ```python
       for vi, b_dict in weights_data.items():
           for b_name, w in b_dict.items():
               if b_name in obj.vertex_groups:
                   obj.vertex_groups[b_name].add([vi], w, 'REPLACE')
       ```
     - Serialize `shape_keys = generate_arkit_52_blendshapes(mesh, landmarks)` and inject Python loop:
       ```python
       for k_name, deltas in shape_key_deltas.items():
           kb = obj.data.shape_keys.key_blocks.get(k_name)
           if kb:
               for vi, (dx, dy, dz) in deltas.items():
                   kb.data[vi].co += mathutils.Vector((dx, dy, dz))
       ```
     - Mirror this logic in `src/morphomesh/blender_bridge.py` method `morphomesh.auto_rig_human` (lines 1748-1755).

2. **Remediation Item 2: Fix Finger Partitioning to Use Actual Hand Landmarks / Bone Heads**:
   - In `src/morphomesh/human_rigging.py` lines 731-744:
     - Replace hardcoded `palm_x = s_sign * 0.385 * scale_f` with dynamic hand center:
       `palm_pt = lm.get(f"wrist_{side_f}", (s_sign * 0.360 * scale_f, -0.020, 0.830))`
       `rel_x = (vx - palm_pt[0]) * s_sign`
     - OR assign vertices by minimum 3D Euclidean distance to the pre-extracted finger bones in `finger_data` (lines 662-669), which naturally adapts to arbitrary shoulder widths and arm spans.

---

## 5. Verification Method

To independently reproduce and verify these findings:

```powershell
# 1. Run the complete adversarial test suite (passes with 2 xfailed tests documenting defects)
$env:PYTHONPATH="E:\tool\mcp\MorphoMesh\src"
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_adversarial_rigging.py -v

# 2. Directly verify live Blender unweighted shell defect:
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --factory-startup --python-expr "
import sys; sys.path.insert(0, r'E:\tool\mcp\MorphoMesh\src'); sys.path.append(r'C:\Users\Admin\AppData\Local\Programs\Python\Python311\Lib\site-packages')
import bpy
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script
exec(get_human_generation_script('Human_Base_Mesh'))
exec(get_rigging_script('Human_Base_Mesh'))
obj = bpy.data.objects['Human_Base_Mesh']
def_groups = {g.index for g in obj.vertex_groups if g.name.startswith('DEF-')}
w_verts = sum(1 for v in obj.data.vertices if any(g.group in def_groups and g.weight > 0 for g in v.groups))
print('WEIGHTED_VERTS_COUNT:', w_verts)
"
# Expected output on current codebase: WEIGHTED_VERTS_COUNT: 0

# 3. Directly verify finger collapse on broad shoulders:
& "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -c "
from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig
from morphomesh.human_rigging import generate_rigify_human_metarig, calculate_anti_pinch_weights
res = generate_human_base_mesh(config=HumanAnatomyConfig(shoulder_width=0.50, arm_span=2.0))
meta = generate_rigify_human_metarig(landmarks=res.landmarks)
w = calculate_anti_pinch_weights(res.mesh, meta, landmarks=res.landmarks)
counts = {d: sum(1 for v in res.vertex_groups.get('fingers_L', []) if w.get_vertex_weight(v, f'DEF-{d}.01.L') > 0) for d in ['thumb', 'f_index', 'f_middle', 'f_ring', 'f_pinky']}
print('FINGER_COUNTS:', counts)
"
# Expected output on current codebase: FINGER_COUNTS: {'thumb': 270, 'f_index': 0, 'f_middle': 0, 'f_ring': 0, 'f_pinky': 0}
```

### Invalidation Conditions:
This challenge is invalidated if and only if:
1. `get_rigging_script` populates vertex weights such that `WEIGHTED_VERTS_COUNT > 0` and rotating `DEF-forearm.L` by 90 degrees produces `max_disp > 0.05m` in Blender 4.5.4 LTS.
2. All 52 shape keys in Blender have non-zero vertex deltas (`non_zero_keys == 52`).
3. Finger partitioning distributes vertices across all 5 digits under non-default arm spans and shoulder widths.
