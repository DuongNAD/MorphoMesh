import bpy
import json
import sys

print("=== BLENDER INSPECTION SCRIPT ===")
print("Blender version:", bpy.app.version_string)

data = {
    "collections": [c.name for c in bpy.data.collections],
    "root_collection": "Yu_Nian_An_Master" in bpy.data.collections,
    "materials": [m.name for m in bpy.data.materials],
    "materials_fake_user": {m.name: m.use_fake_user for m in bpy.data.materials},
    "objects": [(o.name, o.type, [c.name for c in o.users_collection]) for o in bpy.data.objects],
}

body = bpy.data.objects.get("Yu_Nian_An_Body")
if body:
    data["body"] = {
        "vertices": len(body.data.vertices),
        "polygons": len(body.data.polygons),
        "quads": sum(1 for p in body.data.polygons if len(p.vertices) == 4),
        "vertex_groups": len(body.vertex_groups),
        "shape_keys": len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0,
        "modifiers": [m.type for m in body.modifiers],
    }
    if body.data.shape_keys:
        data["shape_key_names"] = [k.name for k in body.data.shape_keys.key_blocks]

arm = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
if arm:
    data["armature"] = {
        "total_bones": len(arm.data.bones),
        "def_bones": len([b for b in arm.data.bones if b.name.startswith("DEF-")]),
    }

print("INSPECTION_JSON_START")
print(json.dumps(data, indent=2))
print("INSPECTION_JSON_END")
