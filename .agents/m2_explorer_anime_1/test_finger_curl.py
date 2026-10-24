import bpy
import math
from mathutils import Vector, Euler, Matrix

bpy.ops.wm.read_factory_settings(use_empty=True)
arm_data = bpy.data.armatures.new("Test_Armature")
arm_obj = bpy.data.objects.new("Test_Armature", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

# Suppose a finger bone in rest pose
# Bone starts at wrist / knuckle and points along finger
b1 = eb.new("Finger_01")
b1.head = Vector((0.44, -0.26, 1.00))
b1.tail = Vector((0.45, -0.28, 0.98))
# Normal to back of hand: say dorsal up/forward
up_vec = Vector((0.0, 0.0, 1.0))
b1.align_roll(up_vec)

b2 = eb.new("Finger_02")
b2.head = b1.tail
b2.tail = Vector((0.45, -0.30, 0.96))
b2.parent = b1
b2.use_connect = True
b2.align_roll(up_vec)

bpy.ops.object.mode_set(mode='POSE')
pb1 = arm_obj.pose.bones["Finger_01"]
pb2 = arm_obj.pose.bones["Finger_02"]

print("Rest pose:")
print(f"  b1 head={pb1.head}, tail={pb1.tail}")
print(f"  b2 head={pb2.head}, tail={pb2.tail}")

# Rotate pb1 by +30 deg around local X
pb1.rotation_mode = 'XYZ'
pb1.rotation_euler = Euler((math.radians(30.0), 0, 0), 'XYZ')
bpy.context.view_layer.update()

print("Rotated +30 deg local X:")
print(f"  b2 head={pb2.head}, tail={pb2.tail}")

# Rotate pb1 by -30 deg around local X
pb1.rotation_euler = Euler((math.radians(-30.0), 0, 0), 'XYZ')
bpy.context.view_layer.update()

print("Rotated -30 deg local X:")
print(f"  b2 head={pb2.head}, tail={pb2.tail}")

bpy.ops.object.mode_set(mode='OBJECT')
