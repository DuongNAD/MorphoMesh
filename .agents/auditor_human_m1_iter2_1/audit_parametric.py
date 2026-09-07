import sys
import math

sys.path.insert(0, "src")
from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig, HumanAnatomyGenerator

# 1. Test head_ratio responsiveness
r_head_5 = generate_human_base_mesh(HumanAnatomyConfig(head_ratio=5.5))
r_head_8 = generate_human_base_mesh(HumanAnatomyConfig(head_ratio=8.5))

print(f"head_ratio=5.5 -> output head_ratio: {r_head_5.head_ratio}")
print(f"head_ratio=8.5 -> output head_ratio: {r_head_8.head_ratio}")
assert r_head_5.head_ratio == 5.5, f"Expected 5.5, got {r_head_5.head_ratio}"
assert r_head_8.head_ratio == 8.5, f"Expected 8.5, got {r_head_8.head_ratio}"

delta_head = max(
    math.sqrt(sum((a - b)**2 for a, b in zip(v1, v2)))
    for v1, v2 in zip(r_head_5.mesh.vertices, r_head_8.mesh.vertices)
)
print(f"Max vertex delta between head_ratio 5.5 and 8.5: {delta_head:.4f}m")
assert delta_head > 0.05, f"Vertex delta for head_ratio {delta_head} <= 0.05m"

# 2. Test waist_girth responsiveness
r_waist_slim = generate_human_base_mesh(HumanAnatomyConfig(waist_girth=0.45))
r_waist_wide = generate_human_base_mesh(HumanAnatomyConfig(waist_girth=1.10))
delta_waist = max(
    math.sqrt(sum((a - b)**2 for a, b in zip(v1, v2)))
    for v1, v2 in zip(r_waist_slim.mesh.vertices, r_waist_wide.mesh.vertices)
)
print(f"Max vertex delta between waist 0.45 and 1.10: {delta_waist:.4f}m")
assert delta_waist > 0.05, f"Vertex delta for waist {delta_waist} <= 0.05m"

# 3. Test chest_girth responsiveness
r_chest_small = generate_human_base_mesh(HumanAnatomyConfig(chest_girth=0.65))
r_chest_large = generate_human_base_mesh(HumanAnatomyConfig(chest_girth=1.20))
delta_chest = max(
    math.sqrt(sum((a - b)**2 for a, b in zip(v1, v2)))
    for v1, v2 in zip(r_chest_small.mesh.vertices, r_chest_large.mesh.vertices)
)
print(f"Max vertex delta between chest 0.65 and 1.20: {delta_chest:.4f}m")
assert delta_chest > 0.05, f"Vertex delta for chest {delta_chest} <= 0.05m"

# 4. Test hip_girth responsiveness
r_hip_slim = generate_human_base_mesh(HumanAnatomyConfig(hip_girth=0.70))
r_hip_wide = generate_human_base_mesh(HumanAnatomyConfig(hip_girth=1.20))
delta_hip = max(
    math.sqrt(sum((a - b)**2 for a, b in zip(v1, v2)))
    for v1, v2 in zip(r_hip_slim.mesh.vertices, r_hip_wide.mesh.vertices)
)
print(f"Max vertex delta between hip 0.70 and 1.20: {delta_hip:.4f}m")
assert delta_hip > 0.05, f"Vertex delta for hip {delta_hip} <= 0.05m"

# 5. Test height scaling
r_h150 = generate_human_base_mesh(HumanAnatomyConfig(height=1.50))
r_h180 = generate_human_base_mesh(HumanAnatomyConfig(height=1.80))
delta_h = max(
    math.sqrt(sum((a - b)**2 for a, b in zip(v1, v2)))
    for v1, v2 in zip(r_h150.mesh.vertices, r_h180.mesh.vertices)
)
print(f"Max vertex delta between height 1.50 and 1.80: {delta_h:.4f}m")
assert delta_h > 0.05, f"Vertex delta for height {delta_h} <= 0.05m"

print("ALL PARAMETRIC RESPONSIVENESS CHECKS PASSED!")
