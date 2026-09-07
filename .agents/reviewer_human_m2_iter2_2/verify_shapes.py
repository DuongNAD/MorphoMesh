import sys
import os
import json
import subprocess
import shutil

sys.path.insert(0, os.path.abspath("src"))

from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig, get_human_generation_script
from morphomesh.human_rigging import (
    generate_arkit_52_blendshapes,
    ARKIT_52_BLENDSHAPES,
    get_rigging_script,
    calculate_anti_pinch_weights,
    generate_rigify_human_metarig,
)

def test_shape_keys():
    mesh_res = generate_human_base_mesh()
    mesh = mesh_res.mesh
    shapes = generate_arkit_52_blendshapes(mesh)
    
    print(f"Total defined ARKIT shapes: {len(ARKIT_52_BLENDSHAPES)}")
    print(f"Total generated shapes: {len(shapes)}")
    assert len(shapes) == 52, f"Expected 52 shapes, got {len(shapes)}"
    
    empty_shapes = []
    zero_movement_shapes = []
    
    for k in ARKIT_52_BLENDSHAPES:
        if k not in shapes:
            empty_shapes.append(k)
            continue
        v_deltas = shapes[k]
        if not v_deltas:
            empty_shapes.append(k)
            continue
        max_disp = max((math_norm(d) for d in v_deltas.values()), default=0.0)
        if max_disp <= 1e-6:
            zero_movement_shapes.append((k, max_disp))
            
    print(f"Empty shapes: {empty_shapes}")
    print(f"Zero-movement shapes: {zero_movement_shapes}")
    assert len(empty_shapes) == 0, f"Shapes without deltas: {empty_shapes}"
    assert len(zero_movement_shapes) == 0, f"Shapes with 0 displacement: {zero_movement_shapes}"
    print("ALL 52 ARKit FACS shape keys have non-zero vertex movement in Python!")

def test_script_generation():
    mesh_res = generate_human_base_mesh()
    script = get_rigging_script(mesh_obj_name="Human_Base_Mesh", mesh_geometry=mesh_res.mesh)
    
    # Check that required coordinate baking expression is in script
    target_pattern = "kb.data[vi].co = ("
    assert target_pattern in script, f"Missing '{target_pattern}' in script!"
    
    assert "base_coords[vi][0] + delta[0]" in script, "Missing X delta baking!"
    assert "base_coords[vi][1] + delta[1]" in script, "Missing Y delta baking!"
    assert "base_coords[vi][2] + delta[2]" in script, "Missing Z delta baking!"
    
    print("Baking coordinate formula verified in script!")

def test_live_blender_execution():
    blender_path = shutil.which("blender")
    if not blender_path:
        for candidate in [
            r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        ]:
            if os.path.exists(candidate):
                blender_path = candidate
                break

    if not blender_path:
        print("Blender binary not found on standard paths, skipping live test.")
        return

    print(f"Testing in live Blender: {blender_path}")
    gen_script = get_human_generation_script()
    rig_script = get_rigging_script(mesh_obj_name="Human_Base_Mesh")
    
    verify_script = f"""
{gen_script}

{rig_script}

# Verify shape keys in Blender scene
obj = bpy.data.objects.get("Human_Base_Mesh")
assert obj is not None, "Human_Base_Mesh not created"
skeys = obj.data.shape_keys
assert skeys is not None, "No shape keys on mesh"
kb_list = skeys.key_blocks
print(f"Total key blocks in Blender: {{len(kb_list)}}")
assert len(kb_list) == 53, f"Expected 53 (Basis + 52 FACS), got {{len(kb_list)}}"

basis_coords = [list(v.co) for v in kb_list["Basis"].data]

zero_keys = []
key_stats = {{}}
for name, kb in kb_list.items():
    if name == "Basis":
        continue
    displacements = []
    for vi, v in enumerate(kb.data):
        bco = basis_coords[vi]
        disp = ((v.co.x - bco[0])**2 + (v.co.y - bco[1])**2 + (v.co.z - bco[2])**2)**0.5
        if disp > 1e-6:
            displacements.append(disp)
    if not displacements:
        zero_keys.append(name)
    else:
        key_stats[name] = (len(displacements), max(displacements))

print(f"Shape keys with ZERO movement: {{zero_keys}}")
assert len(zero_keys) == 0, f"Found shape keys with 0 displacement: {{zero_keys}}"
print(f"SUCCESS: All 52 ARKit keys have non-zero movement in Blender! (Sample: eyeBlinkLeft={{key_stats.get('eyeBlinkLeft')}}, jawOpen={{key_stats.get('jawOpen')}})")
"""
    tmp_file = os.path.abspath(".agents/reviewer_human_m2_iter2_2/blender_verify_tmp.py")
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(verify_script)

    cmd = [blender_path, "--background", "--python", tmp_file]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("Blender STDOUT:")
    for line in res.stdout.splitlines():
        if "key blocks" in line or "movement" in line or "SUCCESS" in line or "Error" in line:
            print("  ", line)
    if res.returncode != 0:
        print("Blender STDERR:")
        print(res.stderr)
    assert res.returncode == 0, f"Blender exited with code {res.returncode}"

def math_norm(d):
    return (d[0]**2 + d[1]**2 + d[2]**2)**0.5

if __name__ == "__main__":
    test_shape_keys()
    test_script_generation()
    test_live_blender_execution()
