import bpy
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
arm_data = bpy.data.armatures.new("Test_Armature")
arm_obj = bpy.data.objects.new("Test_Armature", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

b = eb.new("Finger")
b.head = Vector((0.44, -0.26, 1.01))
b.tail = Vector((0.45, -0.28, 0.99))

has_align_roll = hasattr(b, "align_roll")
print(f"Has align_roll: {has_align_roll}")
if has_align_roll:
    b.align_roll(Vector((0.0, 0.0, 1.0)))
    print(f"After align_roll((0,0,1)): roll={b.roll}, x_axis={b.x_axis}, y_axis={b.y_axis}, z_axis={b.z_axis}")
    b.align_roll(Vector((0.0, -1.0, 1.0)))
    print(f"After align_roll((0,-1,1)): roll={b.roll}, x_axis={b.x_axis}, y_axis={b.y_axis}, z_axis={b.z_axis}")

bpy.ops.object.mode_set(mode='OBJECT')
