import sys
import os

sys.path.insert(0, os.path.abspath("src"))

from morphomesh.blender_bridge import BlenderBridge

def test_bridge():
    bridge = BlenderBridge()
    print(f"Blender bin path: {bridge.blender_bin_path}")
    print(f"Interactive connected: {bridge.is_interactive_connected()}")
    
    # Test auto_rig_human
    res = bridge.auto_rig_human(mesh_object_name="Human_Base_Mesh")
    print(f"Rig result status: {res.get('status')}")
    print(f"DEF bone count: {res.get('def_bone_count')}")
    print(f"Shape key count: {res.get('shape_key_count')}")
    print(f"Armature name: {res.get('armature_name')}")
    print(f"Exported mesh path: {res.get('exported_mesh_path')}")
    
    assert res.get("status") == "success"
    assert res.get("def_bone_count") == 163
    assert res.get("shape_key_count") == 52
    print("BlenderBridge.auto_rig_human verification PASSED!")

if __name__ == "__main__":
    test_bridge()
