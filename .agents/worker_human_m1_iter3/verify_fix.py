import sys
import os

sys.path.insert(0, "src")
from morphomesh.blender_bridge import BlenderBridge

bb = BlenderBridge()
print("Blender binary path:", bb.blender_bin_path)
assert bb.blender_bin_path is not None, "Blender binary not found"

# 1. Test running generated headless script directly via run_headless_script
print("\n--- Testing run_headless_script directly ---")
script = bb._generate_headless_script("morphomesh.create_human_asset", {"character_name": "TestDirectHeadless"})
raw_result = bb.run_headless_script(script)
print("run_headless_script result status:", raw_result.get("status"))
print("run_headless_script vertex_count:", raw_result.get("vertex_count"))
print("run_headless_script face_count:", raw_result.get("face_count"))
print("run_headless_script quad_ratio:", raw_result.get("quad_ratio"))
print("run_headless_script landmarks count:", len(raw_result.get("landmarks", {})))
assert raw_result.get("status") == "success"
assert raw_result.get("vertex_count") == 2144
assert raw_result.get("face_count") == 2036
assert raw_result.get("quad_ratio") == 1.0
assert len(raw_result.get("landmarks", {})) == 24
assert len(raw_result.get("vertex_groups", [])) == 29

# 2. Test create_human_asset method on BlenderBridge (which catches any exception and falls back)
print("\n--- Testing bb.create_human_asset() ---")
res = bb.create_human_asset(character_name="TestBridgeExecution")
print("bb.create_human_asset status:", res.get("status"))
print("bb.create_human_asset vertex_count:", res.get("vertex_count"))
print("bb.create_human_asset face_count:", res.get("face_count"))
print("bb.create_human_asset quad_ratio:", res.get("quad_ratio"))
print("bb.create_human_asset landmarks count:", len(res.get("landmarks", {})))
print("bb.create_human_asset vgroups count:", len(res.get("vertex_groups", [])))
print("bb.create_human_asset mesh_path:", res.get("mesh_path"))

# Note: In procedural fallback, face_count is 4072 (triangles).
# In genuine Blender headless execution, face_count is 2036 (pure quads).
assert res.get("face_count") == 2036, f"Expected 2036 quads from Blender, got {res.get('face_count')}"
assert res.get("vertex_count") == 2144, f"Expected 2144 vertices from Blender, got {res.get('vertex_count')}"
assert res.get("quad_ratio") == 1.0, f"Expected quad_ratio 1.0, got {res.get('quad_ratio')}"
assert len(res.get("vertex_groups", [])) == 29, f"Expected 29 vertex groups, got {len(res.get('vertex_groups', []))}"
assert len(res.get("landmarks", {})) == 24, f"Expected 24 landmarks, got {len(res.get('landmarks', {}))}"
assert os.path.exists(res.get("mesh_path")), "Mesh path does not exist on disk"
assert os.path.getsize(res.get("mesh_path")) > 1000, "Mesh file size too small"

print("\nALL VERIFICATIONS PASSED! Blender headless execution genuinely succeeds without fallback.")
