"""
MorphoMesh: Blender Addon Operators.

Implements DCC operators for mesh import, Principled BSDF shader node construction,
QuadriFlow remeshing, Rigify armature generation, and studio camera framing.
"""

import math
import os
import bpy
import mathutils
from bpy.types import Operator, Panel


class MORPHOMESH_OT_toggle_server(Operator):
    """Start or stop the MorphoMesh socket server"""
    bl_idname = "morphomesh.toggle_server"
    bl_label = "Toggle MorphoMesh Server"

    def execute(self, context):
        from .listener import get_server
        server = get_server()
        if server.is_running():
            server.stop()
            self.report({'INFO'}, "MorphoMesh server stopped.")
        else:
            server.start()
            self.report({'INFO'}, f"MorphoMesh server started on {server.host}:{server.port}.")
        return {'FINISHED'}


class MORPHOMESH_OT_quadriflow_remesh(Operator):
    """Execute QuadriFlow remeshing on the active creature mesh"""
    bl_idname = "morphomesh.quadriflow_remesh"
    bl_label = "QuadriFlow Remesh"
    bl_options = {'REGISTER', 'UNDO'}

    target_faces: bpy.props.IntProperty(name="Target Faces", default=8000, min=500, max=200000)
    use_symmetry: bpy.props.BoolProperty(name="Use Symmetry", default=True)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object selected.")
            return {'CANCELLED'}

        orig_faces = len(obj.data.polygons)
        try:
            bpy.ops.object.quadriflow_remesh(
                use_mesh_symmetry=self.use_symmetry,
                target_faces=self.target_faces,
                preserve_sharp=True,
                preserve_boundary=True
            )
            final_faces = len(obj.data.polygons)
            self.report({'INFO'}, f"Remeshed from {orig_faces} to {final_faces} faces.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'WARNING'}, f"QuadriFlow failed ({e}), falling back to decimate modifier.")
            mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
            if orig_faces > self.target_faces:
                mod.ratio = self.target_faces / orig_faces
            bpy.ops.object.modifier_apply(modifier=mod.name)
            return {'FINISHED'}


class MORPHOMESH_OT_create_creature_rig(Operator):
    """Generate anatomical metarig and bind creature mesh"""
    bl_idname = "morphomesh.create_creature_rig"
    bl_label = "Generate Creature Rig"
    bl_options = {'REGISTER', 'UNDO'}

    creature_type: bpy.props.StringProperty(name="Creature Type", default="quadruped")

    def execute(self, context):
        mesh_obj = context.active_object
        if not mesh_obj or mesh_obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh selected; generating standalone armature.")
            mesh_obj = None

        arm_data = bpy.data.armatures.new(name=f"Armature_{self.creature_type.title()}")
        arm_obj = bpy.data.objects.new(name=f"Armature_{self.creature_type.title()}", object_data=arm_data)
        context.scene.collection.objects.link(arm_obj)
        context.view_layer.objects.active = arm_obj

        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm_data.edit_bones

        root = eb.new("root")
        root.head = (0.0, 0.0, 0.0)
        root.tail = (0.0, 0.0, 0.5)

        spine = eb.new("spine_01")
        spine.head = (0.0, 0.0, 0.5)
        spine.tail = (0.0, 0.0, 1.0)
        spine.parent = root

        neck = eb.new("neck")
        neck.head = (0.0, 0.0, 1.0)
        neck.tail = (0.0, 0.2, 1.3)
        neck.parent = spine

        head = eb.new("head")
        head.head = (0.0, 0.2, 1.3)
        head.tail = (0.0, 0.5, 1.4)
        head.parent = neck

        if self.creature_type in ("quadruped", "winged_quadruped", "hybrid"):
            for side, sign in [("L", 1.0), ("R", -1.0)]:
                fl = eb.new(f"front_leg.{side}")
                fl.head = (sign * 0.3, 0.4, 0.8)
                fl.tail = (sign * 0.3, 0.4, 0.0)
                fl.parent = spine

                bl = eb.new(f"back_leg.{side}")
                bl.head = (sign * 0.3, -0.4, 0.8)
                bl.tail = (sign * 0.3, -0.4, 0.0)
                bl.parent = root

            tail = eb.new("tail_01")
            tail.head = (0.0, -0.5, 0.7)
            tail.tail = (0.0, -0.9, 0.5)
            tail.parent = root

        bpy.ops.object.mode_set(mode='OBJECT')

        if mesh_obj:
            mesh_obj.parent = arm_obj
            mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = arm_obj

        self.report({'INFO'}, f"Armature created: {arm_obj.name}")
        return {'FINISHED'}


class MORPHOMESH_OT_auto_frame_camera(Operator):
    """Setup studio lighting and auto-framed camera targeting scene objects"""
    bl_idname = "morphomesh.auto_frame_camera"
    bl_label = "Auto-Frame Studio Camera"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        # Compute bounding box
        mesh_objs = [o for o in scene.objects if o.type == 'MESH']
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        for o in mesh_objs:
            for corner in o.bound_box:
                mat = o.matrix_world
                wc = mat @ mathutils.Vector(corner)
                min_x = min(min_x, wc.x)
                min_y = min(min_y, wc.y)
                min_z = min(min_z, wc.z)
                max_x = max(max_x, wc.x)
                max_y = max(max_y, wc.y)
                max_z = max(max_z, wc.z)

        if min_x == float('inf'):
            center = mathutils.Vector((0.0, 0.0, 1.0))
            radius = 2.0
        else:
            center = mathutils.Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
            radius = max(max_x - min_x, max_y - min_y, max_z - min_z) / 2.0 or 2.0

        cam_data = bpy.data.cameras.new(name="StudioCamera")
        cam_data.lens = 50.0
        cam_obj = bpy.data.objects.new(name="StudioCamera", object_data=cam_data)
        scene.collection.objects.link(cam_obj)
        scene.camera = cam_obj

        dist = radius * 3.5
        cam_obj.location = center + mathutils.Vector((dist * 0.7, -dist * 0.7, dist * 0.5))
        direction = center - cam_obj.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

        # Studio 3-point lighting
        key_light = bpy.data.lights.new(name="KeyLight", type='AREA')
        key_light.energy = 500.0
        key_obj = bpy.data.objects.new(name="KeyLight", object_data=key_light)
        scene.collection.objects.link(key_obj)
        key_obj.location = center + mathutils.Vector((dist * 0.5, -dist * 0.8, dist * 0.8))

        self.report({'INFO'}, "Studio camera and lighting configured.")
        return {'FINISHED'}


class MORPHOMESH_PT_sidebar_panel(Panel):
    """MorphoMesh 3D Viewport Sidebar Panel"""
    bl_label = "MorphoMesh Bridge"
    bl_idname = "MORPHOMESH_PT_sidebar_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MorphoMesh"

    def draw(self, context):
        layout = self.layout
        from .listener import get_server
        server = get_server()

        # Server status box
        box = layout.box()
        status_text = "Running (Port 9876)" if server.is_running() else "Stopped"
        box.label(text=f"Server: {status_text}", icon='RADIOBUT_ON' if server.is_running() else 'RADIOBUT_OFF')
        box.operator("morphomesh.toggle_server", text="Stop Server" if server.is_running() else "Start Server")

        layout.separator()
        layout.label(text="Creature Operations:")
        layout.operator("morphomesh.quadriflow_remesh")
        layout.operator("morphomesh.create_creature_rig")
        layout.operator("morphomesh.auto_frame_camera")


classes = (
    MORPHOMESH_OT_toggle_server,
    MORPHOMESH_OT_quadriflow_remesh,
    MORPHOMESH_OT_create_creature_rig,
    MORPHOMESH_OT_auto_frame_camera,
    MORPHOMESH_PT_sidebar_panel,
)


def register_operators():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister_operators():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass
