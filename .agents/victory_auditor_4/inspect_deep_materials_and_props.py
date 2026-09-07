
import bpy
import bmesh
import json

report = {}

# Check emission on butterflies and red string
emission_info = {}
for mat_name in ['Mat_Magic_Butterfly', 'Mat_Marionette_RedString']:
    mat = bpy.data.materials.get(mat_name)
    if mat and mat.use_nodes and mat.node_tree:
        em_data = {}
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                for inp in node.inputs:
                    if 'emission' in inp.name.lower():
                        em_data[inp.name] = str(getattr(inp, 'default_value', None))
            elif node.type == 'EMISSION':
                em_data['Emission_Node_Strength'] = node.inputs['Strength'].default_value
                em_data['Emission_Node_Color'] = list(node.inputs['Color'].default_value)
        emission_info[mat_name] = em_data
report['emissions'] = emission_info

# Check Wardrobe & Props meshes topology
mesh_objects = [
    'Mesh_Dress_Bodice',
    'Mesh_Dress_PleatedSkirt',
    'Mesh_Dress_WaistSash',
    'Mesh_Sandal_L',
    'Mesh_Sandal_R',
    'Prop_Marionette_Strings',
    'Prop_Butterfly_00'
]
wardrobe_top = {}
for name in mesh_objects:
    obj = bpy.data.objects.get(name)
    if obj and obj.type == 'MESH':
        m = obj.data
        bm = bmesh.new()
        bm.from_mesh(m)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        total_faces = len(bm.faces)
        quads = sum(1 for f in bm.faces if len(f.verts) == 4)
        tris = sum(1 for f in bm.faces if len(f.verts) == 3)
        ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
        non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        
        wardrobe_top[name] = {
            'verts': len(bm.verts),
            'edges': len(bm.edges),
            'faces': total_faces,
            'quads': quads,
            'tris': tris,
            'ngons': ngons,
            'quad_pct': (quads/total_faces*100) if total_faces > 0 else 0,
            'non_manifold_edges': non_manifold,
            'boundary_edges': boundary,
            'uv_layers': [uv.name for uv in m.uv_layers]
        }
        bm.free()
report['wardrobe_topology'] = wardrobe_top

# Check Marionette String connections
string_obj = bpy.data.objects.get('Prop_Marionette_Strings')
if string_obj and string_obj.type == 'MESH':
    # Check vertex positions min/max
    coords = [v.co for v in string_obj.data.vertices]
    min_z = min(v.z for v in coords)
    max_z = max(v.z for v in coords)
    report['marionette_strings'] = {
        'vertex_count': len(coords),
        'min_z': min_z,
        'max_z': max_z,
        'z_span': max_z - min_z
    }

# Check Hair Curves & Splines
hair_names = ['Hair_Hime_Bangs', 'Hair_Hime_Sidelocks', 'Hair_Back_Cascade', 'Hair_Scalp_Crown']
hair_info = {}
for hn in hair_names:
    h_obj = bpy.data.objects.get(hn)
    if h_obj:
        info = {'type': h_obj.type}
        if h_obj.type == 'CURVES':
            info['curves_count'] = len(h_obj.data.curves)
            info['points_count'] = len(h_obj.data.points)
        elif h_obj.type == 'MESH':
            info['verts'] = len(h_obj.data.vertices)
            info['faces'] = len(h_obj.data.polygons)
        info['modifiers'] = [{'name': m.name, 'type': m.type} for m in h_obj.modifiers]
        hair_info[hn] = info
report['hair_details'] = hair_info

# Check Armature Modifiers on all character meshes
arm_obj = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
arm_modifiers = {}
for o in bpy.data.objects:
    if o.type == 'MESH':
        arm_mods = [m.name for m in o.modifiers if m.type == 'ARMATURE' and m.object == arm_obj]
        if arm_mods:
            arm_modifiers[o.name] = arm_mods
report['armature_modifiers'] = arm_modifiers

with open('E:/tool/mcp/MorphoMesh/.agents/victory_auditor_4/deep_materials_props.json', 'w') as f:
    json.dump(report, f, indent=2)

print('DEEP_INSPECTION_COMPLETE')
