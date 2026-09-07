import sys
import os
import subprocess
import tempfile

sys.path.insert(0, "src")
from morphomesh.human_generator import get_human_generation_script, HumanAnatomyConfig, STANDARDIZED_HUMAN_VERTEX_GROUPS
from morphomesh.blender_bridge import BlenderBridge

# Test 1: Check get_human_generation_script in Blender
script = get_human_generation_script("Audit_VGroups_Mesh", HumanAnatomyConfig())

blender_audit = """
import bpy

obj = bpy.data.objects.get("Audit_VGroups_Mesh")
assert obj is not None, "Audit_VGroups_Mesh not found"
me = obj.data

print(f"Total Blender Vertices: {len(me.vertices)}")
print(f"Total Blender Polygons: {len(me.polygons)}")
print(f"Total Vertex Groups on Object: {len(obj.vertex_groups)}")

# Map vertices to groups
group_counts = {}
for vg in obj.vertex_groups:
    group_counts[vg.name] = 0

for v in me.vertices:
    for g in v.groups:
        vg_name = obj.vertex_groups[g.group].name
        group_counts[vg_name] += 1

empty_groups = [name for name, count in group_counts.items() if count == 0]
print(f"Empty Groups Count: {len(empty_groups)}")
for name, count in sorted(group_counts.items()):
    print(f"  VG '{name}': {count} vertices")

assert len(empty_groups) == 0, f"Found empty vertex groups: {empty_groups}"
assert len(obj.vertex_groups) == 29, f"Expected 29 vertex groups, got {len(obj.vertex_groups)}"

# Check landmarks
landmarks = dict(obj.get("morphomesh_landmarks", {}))
print(f"Total Landmarks: {len(landmarks)}")
assert "head_top" in landmarks
assert "fingers_L" in landmarks
assert "toe_L" in landmarks
assert "thumb_L" in landmarks
assert "pinky_R" in landmarks

# Check 52 ARKit Shape Keys
shape_keys = [k.name for k in (me.shape_keys.key_blocks if me.shape_keys else []) if k.name != "Basis"]
print(f"Total Shape Keys: {len(shape_keys)}")
assert len(shape_keys) == 52, f"Expected 52 ARKit shape keys, got {len(shape_keys)}"
"""

full_script = script + "\n" + blender_audit

with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
    f.write(full_script)
    tmp_path = f.name

try:
    proc = subprocess.run(
        [r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe", "--background", "--factory-startup", "--python", tmp_path],
        capture_output=True,
        text=True
    )
    print("STDOUT:")
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:")
        print(proc.stderr)
    assert proc.returncode == 0
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

print("Check 1 PASSED!")

# Test 2: Test BlenderBridge.create_human_asset() headless execution
bb = BlenderBridge()
bridge_res = bb.create_human_asset(character_name="Yu_Nian_An_Bridge_Test", export_format="glb")
print("Bridge execution status:", bridge_res.get("status"))
print("Bridge vertex count:", bridge_res.get("vertex_count"))
print("Bridge face count:", bridge_res.get("face_count"))
print("Bridge quad ratio:", bridge_res.get("quad_ratio"))
print("Bridge vertex groups count:", len(bridge_res.get("vertex_groups", [])))
print("Bridge shape keys count:", len(bridge_res.get("shape_keys", [])))
print("Bridge mesh path:", bridge_res.get("mesh_path"))
assert bridge_res.get("status") == "success"
assert bridge_res.get("vertex_count") == 2144
assert bridge_res.get("face_count") == 2036
assert bridge_res.get("quad_ratio") == 1.0
assert len(bridge_res.get("vertex_groups", [])) == 29
assert len(bridge_res.get("shape_keys", [])) == 52
assert os.path.exists(bridge_res.get("mesh_path"))
print("Check 2 PASSED!")
