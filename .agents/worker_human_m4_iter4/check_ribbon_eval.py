import bpy
import bmesh
import mathutils
import sys

from morphomesh.human_grooming import (
    generate_hime_cut_splines,
    convert_curves_to_ribbon_mesh,
)

body = bpy.data.objects.get('Yu_Nian_An_Body')
bm = bmesh.new()
bm.from_mesh(body.data)
bm.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

# We will test this after modifying human_grooming.py
print("Checking module import...")
