
import bpy
import bmesh
import json
import math
import sys
from mathutils import Vector

report = {}

report['filepath'] = bpy.data.filepath
report['objects'] = [obj.name for obj in bpy.data.objects]
report['collections'] = {col.name: [o.name for o in col.objects] for col in bpy.data.collections}

# 1. Inspect Body
body_obj = bpy.data.objects.get('Yu_Nian_An_Body')
if not body_obj:
    # Try finding mesh object with 'Body' in name
    for o in bpy.data.objects:
        if 'body' in o.name.lower() and o.type == 'MESH':
            body_obj = o
            break

if body_obj:
    mesh = body_obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    total_faces = len(bm.faces)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    quad_pct = (quads / total_faces * 100.0) if total_faces > 0 else 0.0

    non_manifold_edges = sum(1 for e in bm.edges if not e.is_manifold)
    boundary_edges = sum(1 for e in bm.edges if e.is_boundary)
    wire_edges = sum(1 for e in bm.edges if e.is_wire)

    # Check normals
    zero_normal_faces = sum(1 for f in bm.faces if f.normal.length < 1e-4)

    # Check deforming zones (e.g. joints: neck, elbows, knees, etc.)
    # Faces in deforming zones
    deforming_non_quads = 0
    # Let's inspect non-quad faces if any
    non_quad_details = []
    for f in bm.faces:
        if len(f.verts) != 4:
            center = f.calc_center_median()
            non_quad_details.append({'center': list(center), 'sides': len(f.verts)})

    report['body'] = {
        'name': body_obj.name,
        'verts': len(bm.verts),
        'edges': len(bm.edges),
        'faces': total_faces,
        'quads': quads,
        'tris': tris,
        'ngons': ngons,
        'quad_percentage': quad_pct,
        'non_manifold_edges': non_manifold_edges,
        'boundary_edges': boundary_edges,
        'wire_edges': wire_edges,
        'zero_normal_faces': zero_normal_faces,
        'non_quad_details': non_quad_details,
        'uv_layers': [uv.name for uv in mesh.uv_layers],
    }

    # Shape keys inspection
    if mesh.shape_keys:
        key_blocks = mesh.shape_keys.key_blocks
        basis = key_blocks.get('Basis')
        basis_co = [v.co for v in basis.data] if basis else []
        shape_keys_info = {}
        for kb in key_blocks:
            if kb.name == 'Basis':
                continue
            delta_sum = 0.0
            max_delta = 0.0
            for i, v in enumerate(kb.data):
                d = (v.co - basis_co[i]).length
                delta_sum += d
                if d > max_delta:
                    max_delta = d
            shape_keys_info[kb.name] = {
                'delta_sum': delta_sum,
                'max_delta': max_delta,
                'is_non_zero': delta_sum > 1e-5
            }
        report['shape_keys'] = {
            'total_keys': len(key_blocks) - (1 if basis else 0),
            'has_basis': basis is not None,
            'keys': shape_keys_info
        }
    else:
        report['shape_keys'] = None

    # Vertex groups inspection
    vgroups = {vg.name: 0 for vg in body_obj.vertex_groups}
    for v in mesh.vertices:
        for g in v.groups:
            if g.group < len(body_obj.vertex_groups):
                gname = body_obj.vertex_groups[g.group].name
                if g.weight > 0.001:
                    vgroups[gname] += 1
    report['vertex_groups'] = {
        'total_groups': len(body_obj.vertex_groups),
        'groups_with_weights': sum(1 for c in vgroups.values() if c > 0),
        'groups': vgroups
    }

    bm.free()

# 2. Inspect Armature
arm_obj = None
for o in bpy.data.objects:
    if o.type == 'ARMATURE':
        arm_obj = o
        break

if arm_obj:
    arm = arm_obj.data
    bones = arm.bones
    def_bones = [b.name for b in bones if b.name.startswith('DEF-')]
    def_face = [b for b in def_bones if any(part in b.lower() for part in ['face', 'eye', 'lid', 'lip', 'jaw', 'brow', 'chin', 'ear', 'nose', 'tongue', 'forehead', 'cheek', 'temple', 'teeth'])]
    def_body = [b for b in def_bones if b not in def_face]

    report['armature'] = {
        'name': arm_obj.name,
        'total_bones': len(bones),
        'def_bones_total': len(def_bones),
        'def_bones_body': len(def_body),
        'def_bones_face': len(def_face),
        'sample_def_bones': def_bones[:20]
    }

# 3. Inspect Materials & Shaders
materials_info = {}
for mat in bpy.data.materials:
    mat_data = {'use_nodes': mat.use_nodes, 'nodes': []}
    if mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            node_desc = {'type': node.type, 'name': node.name}
            if node.type == 'BSDF_PRINCIPLED':
                # Check subsurface scattering
                inputs = {inp.name: inp.default_value for inp in node.inputs if hasattr(inp, 'default_value')}
                node_desc['subsurface_method'] = getattr(node, 'subsurface_method', None)
                node_desc['subsurface_weight'] = inputs.get('Subsurface Weight', inputs.get('Subsurface'))
                node_desc['subsurface_radius'] = list(inputs.get('Subsurface Radius', [])) if hasattr(inputs.get('Subsurface Radius', None), '__iter__') else None
                node_desc['roughness'] = inputs.get('Roughness')
                node_desc['ior'] = inputs.get('IOR')
                node_desc['transmission'] = inputs.get('Transmission Weight', inputs.get('Transmission'))
            elif node.type == 'EMISSION':
                inputs = {inp.name: inp.default_value for inp in node.inputs if hasattr(inp, 'default_value')}
                node_desc['strength'] = inputs.get('Strength')
            mat_data['nodes'].append(node_desc)
    materials_info[mat.name] = mat_data
report['materials'] = materials_info

# 4. Inspect Hair and Modifiers
hair_objects = []
for o in bpy.data.objects:
    if 'hair' in o.name.lower() or o.type == 'CURVES':
        mods = [{'name': m.name, 'type': m.type} for m in o.modifiers]
        hair_objects.append({'name': o.name, 'type': o.type, 'modifiers': mods})
report['hair_objects'] = hair_objects

# 5. Inspect Wardrobe & Props
wardrobe_props = []
for o in bpy.data.objects:
    name_lower = o.name.lower()
    if any(k in name_lower for k in ['dress', 'belt', 'sash', 'sandal', 'shoe', 'thread', 'string', 'butterfl', 'marionette']):
        mods = [{'name': m.name, 'type': m.type} for m in o.modifiers]
        wardrobe_props.append({'name': o.name, 'type': o.type, 'modifiers': mods})
report['wardrobe_props'] = wardrobe_props

with open('E:/tool/mcp/MorphoMesh/.agents/victory_auditor_4/blend_inspection_report.json', 'w') as f:
    json.dump(report, f, indent=2, default=str)

print('BLENDER_INSPECTION_COMPLETE')
