import bpy
import math
from mathutils import Vector, Euler

# Import landmarks
import sys
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import extract_makehuman_joint_landmarks

lm = extract_makehuman_joint_landmarks(1.65)

bpy.ops.wm.read_factory_settings(use_empty=True)
arm_data = bpy.data.armatures.new("Test_Hand_Armature")
arm_obj = bpy.data.objects.new("Test_Hand_Armature", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

# Create Hand.L
b_hand = eb.new("Hand.L")
b_hand.head = Vector(lm["joint-l-hand"])
b_hand.tail = Vector(lm["joint-l-finger-3-1"]) # Middle MCP

# Up-vector for the back of the hand / dorsal
# In our mesh, back of hand normal has positive Z and negative Y (pointing up and slightly forward)
dorsal_normal_L = Vector((-0.2, -0.6, 0.77)).normalized()
b_hand.align_roll(dorsal_normal_L)

# Create 5 fingers for Left Hand
finger_defs = [
    ("Thumb", ["joint-l-finger-1-1", "joint-l-finger-1-2", "joint-l-finger-1-3", "joint-l-finger-1-4"]),
    ("Index", ["joint-l-finger-2-1", "joint-l-finger-2-2", "joint-l-finger-2-3", "joint-l-finger-2-4"]),
    ("Middle", ["joint-l-finger-3-1", "joint-l-finger-3-2", "joint-l-finger-3-3", "joint-l-finger-3-4"]),
    ("Ring", ["joint-l-finger-4-1", "joint-l-finger-4-2", "joint-l-finger-4-3", "joint-l-finger-4-4"]),
    ("Pinky", ["joint-l-finger-5-1", "joint-l-finger-5-2", "joint-l-finger-5-3", "joint-l-finger-5-4"]),
]

phalanges = ["01", "02", "03"]

for finger_name, pts in finger_defs:
    parent = b_hand
    # Dorsal normal for this finger can be computed from the 3 joints (plane of finger)
    # The finger bends in the plane defined by pts[0], pts[1], pts[2]
    p0 = Vector(lm[pts[0]])
    p1 = Vector(lm[pts[1]])
    p2 = Vector(lm[pts[2]])
    p3 = Vector(lm[pts[3]])
    
    # Bone direction
    v01 = (p1 - p0).normalized()
    v12 = (p2 - p1).normalized()
    v23 = (p3 - p2).normalized()

    # Finger bend hinge axis: cross product of bone segments
    hinge_axis = v01.cross(v12)
    if hinge_axis.length < 1e-4:
        hinge_axis = v12.cross(v23)
    if hinge_axis.length > 1e-4:
        hinge_axis.normalize()
        # Ensure hinge axis points in consistent lateral direction
        # Local X = hinge axis, Local Y = bone, Local Z = X x Y
        finger_up = hinge_axis.cross(v01).normalized()
        if finger_up.z < 0: # Ensure Z points upwards (dorsal)
            finger_up = -finger_up
    else:
        finger_up = dorsal_normal_L

    for i, ph in enumerate(phalanges):
        bname = f"{finger_name}.{ph}.L"
        b = eb.new(bname)
        b.head = Vector(lm[pts[i]])
        b.tail = Vector(lm[pts[i+1]])
        b.parent = parent
        b.use_connect = (i > 0)
        b.align_roll(finger_up)
        parent = b

bpy.ops.object.mode_set(mode='POSE')
pb = arm_obj.pose.bones

# Test curling Index.01.L, Index.02.L, Index.03.L by +45 degrees local X
print("\n--- Testing Index finger curl ---")
for ph in phalanges:
    bname = f"Index.{ph}.L"
    pbone = pb[bname]
    print(f"{bname}: rest head={pbone.head}, tail={pbone.tail}")
    pbone.rotation_mode = 'XYZ'
    pbone.rotation_euler = Euler((math.radians(45.0), 0, 0), 'XYZ')

bpy.context.view_layer.update()
tip_curled = pb["Index.03.L"].tail
print(f"Curled Index.03.L tail: {tip_curled}")
print(f"Distance to palm center {lm['joint-l-hand-2']}:")
dist_rest = (Vector(lm["joint-l-finger-2-4"]) - Vector(lm["joint-l-hand-2"])).length
dist_curled = (tip_curled - Vector(lm["joint-l-hand-2"])).length
print(f"  Rest distance: {dist_rest:.4f}m")
print(f"  Curled distance: {dist_curled:.4f}m")
assert dist_curled < dist_rest, "Finger curled AWAY from palm instead of toward palm!"
print("Curl test SUCCESS: Finger cleanly curled toward palm into a fist!")

bpy.ops.object.mode_set(mode='OBJECT')
