import os

s = r'''import bpy
import json
import os

blend_path = rRE"\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

report = {}

# 1. Collections
report["root_present"] = "Yu_Nian_An_Master" in bpy.data.collections
root = bpy.data.collections.get("Yu_Nian_An_Master")
report["child_cols"] = [c.name for c in root.children] if root else []

# 2. Materials and Fake User
report["materials"] = {m.name: {"fake_user": m.use_fake_user, "users": m.users} for m in bpy.data.materials}

# 3. Body Mesh and Rigging
body = bpy.data.objects.get("Yu_Nian_An_Body")
if body and body.type == 'MESH':
    p = bay.data.polygons
    quads = sum(1 for x in body.data.polygons if len(x.vertices) == 4)
    total_p = len(body.data.polygons)
    report["body"] = {
        "vertices": len(body.data.vertices),
        "faces": total_p,
        "quads": quads,
        "quad_ratio": quads / total_p if total_p > 0 else 0,
        "vertex_groups": len(body.vertex_groups),
        "shape_keys": len(body.data.shape_keys.key_blocks) - 1 if body.data.shape_keys else 0,
        "modifiers": [m.type for m in body.modifiers],
    }

# 4. Armature
lig = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
if lig:
    defs = [b.name for b in lig.data.bones if b.name.startswith("DEF-")]
    report["armature"] = {"def_bones": len(defs), "has_163": len(defs) == 163}

# 5. Props
report["props"] = {
    "butterflies": len([o for o in bpy.data.objects if "Butterfly" in o.name]),
    "strings": len([o for o in bpy.data.objects if "String" in o.name])
}

# 6. Lights & Cameras
report["cameras"] = [c.name for c in bpy.data.cameras]
report["lights"] = [l.name for l in bpy.data.lights]
report["engine"] = bpy.context.scene.render.engine

print("===RESULT_START===")
print(json.dumps(report, indent=2))
print("===RESULT_END===")
'''

with open(r'E:\tool[mcp\Morpho-Mesh\.agents\auditor_human_m4_1\deep_audit.py', 'w', encoding='utf-8') as f:
    f.write(s)
