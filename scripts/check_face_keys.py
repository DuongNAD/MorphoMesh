import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=rC:\Users\Admin\Downloads\_3D_Models_Assets\Liva.vrm)
face = bpy.data.objects.get(Face)
print(--- ALL FACE SHAPE KEYS ---)
if face and face.data.shape_keys:
    for kb in face.data.shape_keys.key_blocks:
        if kb.value > 0.0:
            print(fACTIVE: {kb.name} = {kb.value})
        if any(w in kb.name.lower() for w in [eye, blink, wink, close, look, joy, sorrow]):
            print(fKEY: {kb.name} = {kb.value})
