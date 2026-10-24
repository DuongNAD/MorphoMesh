import bpy
import math
from mathutils import Vector, Matrix

# Create fresh scene and armature
bpy.ops.wm.read_factory_settings(use_empty=True)
arm_data = bpy.data.armatures.new("Test_Armature")
arm_obj = bpy.data.objects.new("Test_Armature", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

b = eb.new("Bone_Y")
b.head = Vector((0, 0, 0))
b.tail = Vector((0, 1, 0))
print(f"Bone along +Y: x_axis={b.x_axis}, y_axis={b.y_axis}, z_axis={b.z_axis}, roll={b.roll}")

b_x = eb.new("Bone_X")
b_x.head = Vector((0, 0, 0))
b_x.tail = Vector((1, 0, 0))
print(f"Bone along +X: x_axis={b_x.x_axis}, y_axis={b_x.y_axis}, z_axis={b_x.z_axis}, roll={b_x.roll}")

b_z = eb.new("Bone_Z")
b_z.head = Vector((0, 0, 0))
b_z.tail = Vector((0, 0, 1))
print(f"Bone along +Z: x_axis={b_z.x_axis}, y_axis={b_z.y_axis}, z_axis={b_z.z_axis}, roll={b_z.roll}")

bpy.ops.object.mode_set(mode='OBJECT')
