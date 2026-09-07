
import bpy
strings_obj = bpy.data.objects.get('Prop_Marionette_Strings')
if strings_obj and strings_obj.type == 'CURVE':
    print('STRINGS_OBJECT_TYPE: CURVE')
    print('SPLINES_COUNT:', len(strings_obj.data.splines))
    print('BEVEL_DEPTH:', strings_obj.data.bevel_depth)
else:
    print('STRINGS_OBJ:', strings_obj)
