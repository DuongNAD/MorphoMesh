"""
Inspect Yu_Nian_An_Master.blend using Blender 4.5 background runner.
"""
import bpy

print("\n--- COLLECTIONS ---")
top_cols = [c.name for c in bpy.data.collections]
print("Collections:", top_cols)

print("\n--- OBJECTS ---")
for obj in bpy.data.objects:
    print(f"Object: {obj.name} | Type: {obj.type} | Users: {obj.users}")

print("\n--- MATERIALS ---")
print(f"Total materials: {len(bpy.data.materials)}")
for mat in bpy.data.materials:
    print(f"Material: {mat.name} | FakeUser: {mat.use_fake_user} | Users: {mat.users}")

print("\n--- BODY MESH INTEGRITY ---")
body = bpy.data.objects.get("Yu_Nian_An_Body")
if body and body.type == 'MESH':
    mesh = body.data
    verts = len(mesh.vertices)
    polys = len(mesh.polygons)
    quads = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
    tris = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
    ngons = sum(1 for p in mesh.polygons if len(p.vertices) > 4)
    print(f"Body Mesh: Verts={verts}, Polys={polys}, Quads={quads} ({quads/polys*100:.1f}%), Tris={tris}, Ngons={ngons}")
    if mesh.shape_keys and mesh.shape_keys.key_blocks:
        skeys = [kb.name for kb in mesh.shape_keys.key_blocks]
        print(f"Shape keys count: {len(skeys)} (Basis + {len(skeys)-1} targets)")
    else:
        print("No shape keys on body!")

print("\n--- ARMATURE INTEGRITY ---")
arm = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
if arm and arm.type == 'ARMATURE':
    bones = arm.data.bones
    def_bones = [b.name for b in bones if b.name.startswith("DEF-")]
    print(f"Armature: Total bones={len(bones)}, DEF bones={len(def_bones)}")

print("\nBLENDER_SCENE_INSPECTION_SUCCESSFUL")
