
import bpy, json, sys

blend_path = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

root = bpy.data.collections.get('Yu_Nian_An_Master')
body = bpy.data.objects.get('Yu_Nian_An_Body')
arm = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')

defs = [b.name for b in arm.data.bones if b.name.startswith('DEF-')] if arm else []
p_count = len(body.data.polygons) if body else 0
quads = sum(1 for p in body.data.polygons if len(p.vertices) == 4) if body else 0
shape_keys = len(body.data.shape_keys.key_blocks) - 1 if (body and body.data.shape_keys) else 0

materials = {m.name: {'fake_user': m.use_fake_user, 'users': m.users} for m in bpy.data.materials}
butterflies = [o.name for o in bpy.data.objects if 'Butterfly' in o.name]
strings = [o.name for o in bpy.data.objects if 'String' in o.name]

report = {
    'has_root': root is not None,
    'child_cols': [c.name for c in root.children] if root else [],
    'all_cols': [c.name for c in bpy.data.collections],
    'body_vertices': len(body.data.vertices) if body else 0,
    'body_polygons': p_count,
    'body_quads': quads,
    'body_quad_ratio': quads / p_count if p_count else 0,
    'body_vgs': len(body.vertex_groups) if body else 0,
    'body_shape_keys': shape_keys,
    'body_modifiers': [m.type for m in body.modifiers] if body else [],
    'body_armature_preserve_volume': next((m.use_deform_preserve_volume for m in body.modifiers if m.type == 'ARMATURE'), None) if body else None,
    'armature_total_bones': len(arm.data.bones) if arm else 0,
    'armature_def_bones': len(defs),
    'materials': materials,
    'butterflies_count': len(butterflies),
    'strings_count': len(strings),
    'cameras': [c.name for c in bpy.data.cameras],
    'lights': [l.name for l in bpy.data.lights],
    'engine': bpy.context.scene.render.engine,
    'samples': bpy.context.scene.cycles.samples if hasattr(bpy.context.scene, 'cycles') else None,
}

print('===FORENSIC_RESULT_START===')
print(json.dumps(report, indent=2))
print('===FORENSIC_RESULT_END===')
