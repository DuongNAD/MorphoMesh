
import bpy
s = bpy.data.objects.get('Prop_Marionette_Strings')
print('STRING_TYPE:', s.type)
if s.type == 'MESH':
    print('MESH_VERTICES:', len(s.data.vertices))
    print('MESH_EDGES:', len(s.data.edges))
    print('MESH_POLYGONS:', len(s.data.polygons))
elif s.type == 'CURVE':
    print('CURVE_SPLINES:', len(s.data.splines))
