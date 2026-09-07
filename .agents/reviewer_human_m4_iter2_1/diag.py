import bpy

print("=== EYE VERTEX COORDINATES ===")
eye_l = bpy.data.objects.get("Mesh_Eye_Left_CorneaSclera")
if eye_l:
    print(f"eye_l.location = {eye_l.location}")
    print(f"eye_l.matrix_world.translation = {eye_l.matrix_world.translation}")
    ys = [v.co.y for v in eye_l.data.vertices]
    zs = [v.co.z for v in eye_l.data.vertices]
    xs = [v.co.x for v in eye_l.data.vertices]
    print(f"eye_l mesh X range: [{min(xs):.4f}, {max(xs):.4f}]")
    print(f"eye_l mesh Y range: [{min(ys):.4f}, {max(ys):.4f}]")
    print(f"eye_l mesh Z range: [{min(zs):.4f}, {max(zs):.4f}]")
    print(f"eye_l center Y: {(min(ys) + max(ys))/2:.4f}")

print("\n=== MATERIALS IN BPY.DATA ===")
for m in bpy.data.materials:
    print(f"Name: {m.name}, users: {m.users}, use_fake_user: {m.use_fake_user}")
