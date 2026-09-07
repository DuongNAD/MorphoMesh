import bpy
import bmesh
import mathutils

def inspect_geometry_and_props():
    print("=== EMPIRICAL GEOMETRY, CLEARANCE & PROPS AUDIT ===")
    
    # 1. Body Mesh Quality
    body = bpy.data.objects.get("Yu_Nian_An_Body")
    assert body is not None, "Body object missing"
    bm = bmesh.new()
    bm.from_mesh(body.data)
    
    total_faces = len(bm.faces)
    quad_faces = sum(1 for f in bm.faces if len(f.verts) == 4)
    tri_faces = sum(1 for f in bm.faces if len(f.verts) == 3)
    ngon_faces = sum(1 for f in bm.faces if len(f.verts) > 4)
    zero_area = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    
    print(f"Body Mesh Stats:")
    print(f"  Total Faces: {total_faces}")
    print(f"  Quads: {quad_faces} ({quad_faces/total_faces*100:.2f}%)")
    print(f"  Tris: {tri_faces}")
    print(f"  N-gons: {ngon_faces}")
    print(f"  Zero-area faces: {zero_area}")
    print(f"  Non-manifold edges: {non_manifold}")
    print(f"  Loose vertices: {loose_verts}")
    
    assert total_faces == quad_faces, "Body mesh contains non-quad faces!"
    assert non_manifold == 0, "Body mesh has non-manifold edges!"
    assert zero_area == 0, "Body mesh has zero-area faces!"
    bm.free()
    
    # 2. Wardrobe Clearance Check
    # Check minimum distance between dress bodice and body
    bodice = bpy.data.objects.get("Mesh_Dress_Bodice")
    if bodice:
        print("Auditing Dress Bodice clearance...")
        bodice_verts = [bodice.matrix_world @ v.co for v in bodice.data.vertices]
        body_verts = [body.matrix_world @ v.co for v in body.data.vertices]
        
        # Check Z range of bodice
        min_z = min(v.z for v in bodice_verts)
        max_z = max(v.z for v in bodice_verts)
        
        # Filter body vertices within same Z range
        relevant_body_verts = [v for v in body_verts if min_z <= v.z <= max_z]
        if relevant_body_verts:
            # Build KDTree for fast distance calculation
            kd = mathutils.kdtree.KDTree(len(relevant_body_verts))
            for i, v in enumerate(relevant_body_verts):
                kd.insert(v, i)
            kd.balance()
            
            distances = []
            for bv in bodice_verts:
                co, index, dist = kd.find(bv)
                distances.append(dist)
                
            min_dist = min(distances)
            avg_dist = sum(distances) / len(distances)
            print(f"  Bodice-to-Body Min Distance: {min_dist*1000:.2f} mm")
            print(f"  Bodice-to-Body Avg Distance: {avg_dist*1000:.2f} mm")
            assert min_dist >= 0.001, f"Severe clipping detected: min_dist={min_dist}"
            
    # 3. Props: Strings & Butterflies Placement
    strings = bpy.data.objects.get("Prop_Marionette_Strings")
    print(f"Marionette Strings object: {strings.name if strings else 'None'}")
    
    butterflies = [o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")]
    print(f"Luminous Butterflies count: {len(butterflies)}")
    assert len(butterflies) == 10, f"Expected 10 butterflies, got {len(butterflies)}"
    
    for i, bf in enumerate(butterflies):
        loc = bf.location
        print(f"  Butterfly {i:02d} loc: ({loc.x:.3f}, {loc.y:.3f}, {loc.z:.3f}), mats: {[m.name for m in bf.data.materials]}")
        assert len(bf.data.materials) > 0 and bf.data.materials[0].name == "Mat_Magic_Butterfly"
        
    print("\nGEOMETRY, CLEARANCE & PROPS AUDIT: ALL PASSED")

inspect_geometry_and_props()
