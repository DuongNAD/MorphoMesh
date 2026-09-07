import bpy
print("=== ALL OBJECTS IN BLEND ===")
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    print(f"  {o.name} (type: {o.type}, parent: {o.parent.name if o.parent else 'None'})")