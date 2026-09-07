import sys
sys.path.insert(0, "src")
from morphomesh.blender_bridge import BlenderBridge

bb = BlenderBridge()
script = bb._generate_headless_script("morphomesh.create_human_asset", {"character_name": "TestHuman"})

print("Script length:", len(script))
ret = bb.run_headless_script(script)
print("Run headless script result:", ret)
