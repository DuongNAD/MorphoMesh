import bpy
import math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

print("=" * 80)
print("INDEPENDENT AUDIT OF Yu_Nian_An_Master.blend")
print("=" * 80)

scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()

# ----------------------------------------------------------------------
# 1. COLLECTIONS AND OBJECTS HIERARCHY
# ----------------------------------------------------------------------
print("\n--- 1. COLLECTIONS & SCENE HIERARCHY ---")
all_cols = list(bpy.data.collections)
print(f"Total Collections in bpy.data.collections: {len(all_cols)}")
for c in all_cols:
    parent_names = [p.name for p in bpy.data.collections if c.name in p.children]
    print(f"  Collection: '{c.name}', Parents: {parent_names}, Object count: {len(c.objects)}")

all_objs = list(bpy.data.objects)
print(f"\nTotal Objects in scene: {len(all_objs)}")
for o in sorted(all_objs, key=lambda x: x.name):
    col_membership = [c.name for c in bpy.data.collections if o.name in c.objects]
    print(f"  Object: '{o.name}' [{o.type}] in collections: {col_membership}")

# ----------------------------------------------------------------------
# 2. BODY MESH TOPOLOGY & SHAPE KEYS
# ----------------------------------------------------------------------
print("\n--- 2. BODY MESH TOPOLOGY & SHAPE KEYS ---")
body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
if not body_obj:
    print("ERROR: Yu_Nian_An_Body not found!")
else:
    me = body_obj.data
    quad_count = 0
    tri_count = 0
    ngon_count = 0
    for poly in me.polygons:
        if len(poly.vertices) == 4:
            quad_count += 1
        elif len(poly.vertices) == 3:
            tri_count += 1
        else:
            ngon_count += 1
    print(f"Body Mesh '{body_obj.name}': Vertices={len(me.vertices)}, Edges={len(me.edges)}, Polygons={len(me.polygons)}")
    print(f"  Quads: {quad_count}, Tris: {tri_count}, Ngons: {ngon_count}")
    print(f"  Pure quads: {quad_count == len(me.polygons) and tri_count == 0 and ngon_count == 0}")

    # Check non-manifold edges
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
    bm.free()
    print(f"  Non-manifold edges: {len(non_manifold_edges)}")

    # Shape keys
    if me.shape_keys and me.shape_keys.key_blocks:
        blocks = me.shape_keys.key_blocks
        print(f"Shape Keys Count: {len(blocks)} (including Basis)")
        arkit_keys = [k for k in blocks.keys() if k != "Basis"]
        print(f"  Non-basis shape keys count: {len(arkit_keys)}")
        basis_verts = [v.co for v in blocks["Basis"].data]
        zero_delta_keys = []
        max_deltas = {}
        for k in arkit_keys:
            kb = blocks[k]
            deltas = [(v.co - basis_verts[i]).length for i, v in enumerate(kb.data)]
            max_d = max(deltas)
            max_deltas[k] = max_d
            if max_d < 1e-6:
                zero_delta_keys.append(k)
        print(f"  Keys with zero delta (<1e-6): {len(zero_delta_keys)}")
        if zero_delta_keys:
            print(f"    WARNING Zero delta keys: {zero_delta_keys}")
        else:
            min_non_zero = min(max_deltas.values())
            max_non_zero = max(max_deltas.values())
            print(f"  All {len(arkit_keys)} keys have non-zero displacement! Max delta range: [{min_non_zero:.5f}m, {max_non_zero:.5f}m]")
    else:
        print("ERROR: No shape keys found on body mesh!")

# ----------------------------------------------------------------------
# 3. ARMATURE & DEF BONES
# ----------------------------------------------------------------------
print("\n--- 3. ARMATURE & DEF BONES ---")
arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
if not arm_obj:
    print("ERROR: Armature_Yu_Nian_An_Rigify not found!")
else:
    arm = arm_obj.data
    def_bones = [b.name for b in arm.bones if b.name.startswith("DEF-")]
    print(f"Total bones: {len(arm.bones)}")
    print(f"DEF bones count: {len(def_bones)}")

# ----------------------------------------------------------------------
# 4. CAMERAS & FULL BODY FRAMING
# ----------------------------------------------------------------------
print("\n--- 4. CAMERAS & FULL BODY FRAMING ---")
camera_names = [
    "Camera_FullBody",
    "Camera_Front",
    "Camera_ThreeQuarter",
    "Camera_Profile",
    "Camera_Back",
    "Camera_Portrait_85mm"
]

# Character evaluated bounding vertices (including body, dress, hair, sandals)
char_objects = [
    bpy.data.objects.get("Yu_Nian_An_Body"),
    bpy.data.objects.get("Dress_Bodice"),
    bpy.data.objects.get("Dress_WaistSash"),
    bpy.data.objects.get("Dress_PleatedSkirt"),
    bpy.data.objects.get("Mesh_Sandal_Left"),
    bpy.data.objects.get("Mesh_Sandal_Right"),
]
char_objects = [o for o in char_objects if o is not None]

all_world_verts = []
for obj in char_objects:
    eval_obj = obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    for v in eval_mesh.vertices:
        all_world_verts.append(eval_obj.matrix_world @ v.co)
    eval_obj.to_mesh_clear()

print(f"Total evaluated character vertices tested for camera framing: {len(all_world_verts)}")
z_coords = [v.z for v in all_world_verts]
print(f"Character Z range in world space: [{min(z_coords):.4f}m, {max(z_coords):.4f}m], height: {max(z_coords) - min(z_coords):.4f}m")

for cam_name in camera_names:
    cam_obj = bpy.data.objects.get(cam_name)
    if not cam_obj:
        print(f"WARNING: Camera '{cam_name}' not found!")
        continue
    cam_data = cam_obj.data
    lens = cam_data.lens
    loc = [round(x, 4) for x in cam_obj.location]
    rot = [round(math.degrees(x), 2) for x in cam_obj.rotation_euler]
    
    # Calculate NDC projection
    ndc_coords = [world_to_camera_view(scene, cam_obj, v) for v in all_world_verts]
    in_front = [c for c in ndc_coords if c.z > 0]
    min_x = min(c.x for c in in_front)
    max_x = max(c.x for c in in_front)
    min_y = min(c.y for c in in_front)
    max_y = max(c.y for c in in_front)
    
    within_y_bounds = (min_y >= 0.05) and (max_y <= 0.95)
    margin_bottom = min_y
    margin_top = 1.0 - max_y
    
    print(f"\nCamera '{cam_name}':")
    print(f"  Lens: {lens}mm, Location: {loc}, Rotation: {rot}")
    print(f"  NDC X bounds: [{min_x:.4f}, {max_x:.4f}]")
    print(f"  NDC Y bounds: [{min_y:.4f}, {max_y:.4f}]")
    print(f"  Bottom Margin: {margin_bottom*100:.2f}%, Top Margin: {margin_top*100:.2f}%")
    print(f"  Strictly within [0.05, 0.95]: {within_y_bounds}")
    print(f"  Head decapitated: {max_y > 1.0}, Foot amputated: {min_y < 0.0}")

# ----------------------------------------------------------------------
# 5. MARIONETTE STRING PROXIMAL ROOTS vs FINGER DEF BONE TAILS
# ----------------------------------------------------------------------
print("\n--- 5. MARIONETTE STRING ROOTS vs FINGER DEF BONE TAILS ---")
strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
if not strings_obj or not arm_obj:
    print("ERROR: strings or armature missing!")
else:
    finger_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R"
    ]
    str_eval = strings_obj.evaluated_get(depsgraph)
    str_mesh = str_eval.to_mesh()
    verts_per_cord = 14
    
    print(f"Strings mesh total vertices: {len(str_mesh.vertices)}, total faces: {len(str_mesh.polygons)}")
    all_within_threshold = True
    for i, bone_name in enumerate(finger_bones):
        bone = arm_obj.data.bones.get(bone_name)
        if not bone:
            print(f"  ERROR: Bone {bone_name} not found in armature!")
            all_within_threshold = False
            continue
        bone_tail_world = arm_obj.matrix_world @ bone.tail_local
        
        # Root vertices of this cord: indices i*verts_per_cord and i*verts_per_cord + 1
        v_idx_left = i * verts_per_cord
        v_idx_right = i * verts_per_cord + 1
        v_l_world = str_eval.matrix_world @ str_mesh.vertices[v_idx_left].co
        v_r_world = str_eval.matrix_world @ str_mesh.vertices[v_idx_right].co
        root_center_world = (v_l_world + v_r_world) * 0.5
        
        dist_mm = (root_center_world - bone_tail_world).length * 1000.0
        dist_l_mm = (v_l_world - bone_tail_world).length * 1000.0
        dist_r_mm = (v_r_world - bone_tail_world).length * 1000.0
        
        passed = dist_mm < 2.0
        if not passed:
            all_within_threshold = False
        print(f"  Cord {i:02d} -> {bone_name:16s}: root center dist={dist_mm:.4f}mm (L={dist_l_mm:.4f}mm, R={dist_r_mm:.4f}mm) -> PASS={passed}")
        print(f"    Bone tail: [{bone_tail_world.x:.4f}, {bone_tail_world.y:.4f}, {bone_tail_world.z:.4f}]")
        print(f"    Root center: [{root_center_world.x:.4f}, {root_center_world.y:.4f}, {root_center_world.z:.4f}]")
    
    print(f"All 10 strings snapped within <2.0mm: {all_within_threshold}")
    str_eval.to_mesh_clear()

# ----------------------------------------------------------------------
# 6. MATERIALS ASSIGNMENT & SHADER NODES
# ----------------------------------------------------------------------
print("\n--- 6. MATERIALS ASSIGNMENT & SHADER VERIFICATION ---")
key_materials = [
    "Mat_Human_Skin_SSS",
    "Mat_Human_Eye_Outer_Cornea",
    "Mat_Human_Eye_Inner_Iris",
    "Mat_Human_Hair",
    "Mat_Dress_WhiteSilk",
    "Mat_Sash_Satin",
    "Mat_Dress_WaistBelt",
    "Mat_Sandal_White",
    "Mat_Sandal_Leather",
    "Mat_Marionette_RedString",
    "Mat_Magic_Butterfly"
]
for mat_name in key_materials:
    mat = bpy.data.materials.get(mat_name)
    if mat:
        nodes = [n.type for n in mat.node_tree.nodes] if mat.node_tree else []
        print(f"  Material '{mat_name}': Users={mat.users}, Node tree={mat.use_nodes}, Node count={len(nodes)}")
    else:
        print(f"  Material '{mat_name}': NOT PRESENT")

print("\n" + "=" * 80)
print("AUDIT EXECUTION COMPLETE")
print("=" * 80)
