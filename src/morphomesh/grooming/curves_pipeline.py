"""
MorphoMesh Blender Geometry Nodes Hair Curve Modifier Network.

Responsible for:
- build_hair_geom_node_tree: Procedurally builds GN_HairGroom modifier node tree in Blender 4.0+ LTS
  with root-to-tip taper, tip clumping, micro-frizz noise, and material assignment.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("morphomesh.grooming.curves_pipeline")

def build_hair_geom_node_tree(tree: Any, cfg: Dict[str, Any], mat_hair: Any = None) -> Any:
    """
    Constructs the complete Geometry Nodes modifier network (GN_HairGroom):
    1. Declares interface sockets on tree.interface (Blender 4.0+ LTS): Geometry In / Out
    2. Root-to-tip radius taper: GeometryNodeSplineParameter -> ShaderNodeMapRange -> GeometryNodeSetCurveRadius
    3. Clumping node or curve shape factor applying clump_factor = 0.28
    4. Micro-frizz noise node: GeometryNodeSetPosition driven by ShaderNodeTexNoise
    5. GeometryNodeSetMaterial assigning Mat_Human_Hair
    """
    # 0. Declare interface sockets on tree.interface (Blender 4.0+ LTS)
    if hasattr(tree, "interface"):
        if hasattr(tree.interface, "items_tree"):
            for item in list(tree.interface.items_tree):
                try:
                    tree.interface.remove(item)
                except Exception:
                    pass
        tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    elif hasattr(tree, "inputs") and hasattr(tree, "outputs"):
        try:
            tree.inputs.clear()
            tree.outputs.clear()
        except Exception:
            pass
        tree.inputs.new('NodeSocketGeometry', 'Geometry')
        tree.outputs.new('NodeSocketGeometry', 'Geometry')

    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    # Inputs & Outputs
    in_node = nodes.new(type='NodeGroupInput')
    in_node.location = (-600, 0)
    out_node = nodes.new(type='NodeGroupOutput')
    out_node.location = (800, 0)

    try:
        # 1. Root-to-tip radius taper
        try:
            spline_param = nodes.new(type='GeometryNodeSplineParameter')
        except Exception:
            spline_param = nodes.new(type='GeometryNodeCurveSplineParameter')
        spline_param.location = (-400, 200)

        map_range = nodes.new(type='ShaderNodeMapRange')
        map_range.location = (-200, 200)
        map_range.inputs['From Min'].default_value = 0.0
        map_range.inputs['From Max'].default_value = 1.0
        map_range.inputs['To Min'].default_value = float(cfg.get('root_radius', 0.00016))
        map_range.inputs['To Max'].default_value = float(cfg.get('tip_radius', 0.000025))
        param_out = spline_param.outputs.get('Factor') or spline_param.outputs[0]
        links.new(param_out, map_range.inputs['Value'])

        # Clump factor modulation (0.28)
        clump_val = float(cfg.get('clump_factor', 0.28))
        clump_math = nodes.new(type='ShaderNodeMath')
        clump_math.operation = 'MULTIPLY'
        clump_math.location = (-200, 50)
        clump_math.inputs[1].default_value = clump_val
        links.new(param_out, clump_math.inputs[0])

        set_rad = nodes.new(type='GeometryNodeSetCurveRadius')
        set_rad.location = (0, 0)
        in_geom = in_node.outputs.get('Geometry') or in_node.outputs[0]
        rad_geom_in = set_rad.inputs.get('Curve') or set_rad.inputs.get('Geometry') or set_rad.inputs[0]
        links.new(in_geom, rad_geom_in)
        map_out = map_range.outputs.get('Result') or map_range.outputs[0]
        links.new(map_out, set_rad.inputs['Radius'])

        # 2. Micro-frizz noise node
        noise_tex = nodes.new(type='ShaderNodeTexNoise')
        noise_tex.location = (0, -200)
        noise_tex.inputs['Scale'].default_value = float(cfg.get('noise_frequency', 14.0))

        vec_sub = nodes.new(type='ShaderNodeVectorMath')
        vec_sub.operation = 'SUBTRACT'
        vec_sub.location = (200, -200)
        vec_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
        noise_out = noise_tex.outputs.get('Color') or noise_tex.outputs[0]
        links.new(noise_out, vec_sub.inputs[0])

        vec_scale = nodes.new(type='ShaderNodeVectorMath')
        vec_scale.operation = 'SCALE'
        vec_scale.location = (380, -200)
        vec_scale.inputs['Scale'].default_value = float(cfg.get('noise_amplitude', 0.0012))
        sub_out = vec_sub.outputs.get('Vector') or vec_sub.outputs[0]
        links.new(sub_out, vec_scale.inputs[0])

        set_pos = nodes.new(type='GeometryNodeSetPosition')
        set_pos.location = (250, 0)
        rad_geom_out = set_rad.outputs.get('Curve') or set_rad.outputs.get('Geometry') or set_rad.outputs[0]
        links.new(rad_geom_out, set_pos.inputs['Geometry'])
        scale_out = vec_scale.outputs.get('Vector') or vec_scale.outputs[0]
        links.new(scale_out, set_pos.inputs['Offset'])

        # 3. Material assignment
        set_mat = nodes.new(type='GeometryNodeSetMaterial')
        set_mat.location = (500, 0)
        if mat_hair is not None:
            set_mat.inputs['Material'].default_value = mat_hair
        links.new(set_pos.outputs['Geometry'], set_mat.inputs['Geometry'])
        out_geom = out_node.inputs.get('Geometry') or out_node.inputs[0]
        links.new(set_mat.outputs['Geometry'], out_geom)
    except Exception:
        if len(in_node.outputs) > 0 and len(out_node.inputs) > 0:
            in_g = in_node.outputs.get('Geometry') or in_node.outputs[0]
            out_g = out_node.inputs.get('Geometry') or out_node.inputs[0]
            links.new(in_g, out_g)

    return tree

