import sys
import os

sys.path.insert(0, "src")
from morphomesh.blender_bridge import BlenderBridge
from morphomesh.human_generator import generate_human_base_mesh, compute_quad_metrics

# Test Bridge headless script generation
bb = BlenderBridge()
script = bb._generate_headless_script("morphomesh.create_human_asset", {})
print("Generated script length:", len(script))
print("Contains 0.965 in returned script:", "0.965" in script)
print("Contains dyn_quad_ratio in returned script:", "dyn_quad_ratio" in script)
print("Contains add_bmesh_quad_cap in returned script:", "add_bmesh_quad_cap" in script)

# Test Python generator quad ratio
res = generate_human_base_mesh()
q, t, r = compute_quad_metrics(res.mesh)
print(f"Generator result: quads={q}, tris={t}, ratio={r}")
print(f"res.quad_ratio={res.quad_ratio}")
