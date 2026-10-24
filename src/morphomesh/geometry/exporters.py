"""
MorphoMesh: 3D Geometry Exporters (Wavefront OBJ and Binary glTF 2.0).
"""
from __future__ import annotations

import json
import os
import struct
from typing import Any


def pad_4(b: bytes) -> bytes:
    """Aligns byte buffer to a 4-byte boundary."""
    rem = len(b) % 4
    return b + (b"\x00" * ((4 - rem) % 4))


def export_obj(mesh: Any, filepath: str) -> None:
    """Export geometry to standard Wavefront .obj file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# MorphoMesh Procedural Creature Mesh\n")
        for v in mesh.vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for vn in mesh.normals:
            f.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")
        for vt in mesh.uvs:
            f.write(f"vt {vt[0]:.6f} {vt[1]:.6f}\n")
        for face in mesh.faces:
            # 1-indexed obj faces: f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3
            f.write(
                f"f {face[0]+1}/{face[0]+1}/{face[0]+1} "
                f"{face[1]+1}/{face[1]+1}/{face[1]+1} "
                f"{face[2]+1}/{face[2]+1}/{face[2]+1}\n"
            )


def export_glb(mesh: Any, filepath: str) -> None:
    """Export geometry to standard binary glTF 2.0 (.glb) container."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    num_verts = len(mesh.vertices)
    num_indices = len(mesh.faces) * 3

    # Flatten buffers
    pos_data = struct.pack(f"<{num_verts * 3}f", *[coord for v in mesh.vertices for coord in v])
    norm_data = struct.pack(f"<{num_verts * 3}f", *[coord for vn in mesh.normals for coord in vn])
    uv_data = struct.pack(f"<{num_verts * 2}f", *[coord for vt in mesh.uvs for coord in vt])

    # Indices: use uint16 if num_verts <= 65535, else uint32
    use_uint32 = num_verts > 65535
    idx_fmt = f"<{num_indices}I" if use_uint32 else f"<{num_indices}H"
    idx_type = 5125 if use_uint32 else 5123  # glTF constants: 5125=UNSIGNED_INT, 5123=UNSIGNED_SHORT
    flat_indices = [idx for face in mesh.faces for idx in face]
    idx_data = struct.pack(idx_fmt, *flat_indices)

    pos_bytes = pad_4(pos_data)
    norm_bytes = pad_4(norm_data)
    uv_bytes = pad_4(uv_data)
    idx_bytes = pad_4(idx_data)

    offset_pos = 0
    len_pos = len(pos_data)
    offset_norm = len(pos_bytes)
    len_norm = len(norm_data)
    offset_uv = offset_norm + len(norm_bytes)
    len_uv = len(uv_data)
    offset_idx = offset_uv + len(uv_bytes)
    len_idx = len(idx_data)

    bin_buffer = pos_bytes + norm_bytes + uv_bytes + idx_bytes
    total_bin_length = len(bin_buffer)

    # Min/max positions for glTF bounds
    bbox = mesh.compute_bounding_box()

    gltf_json = {
        "asset": {"version": "2.0", "generator": "MorphoMesh Mock Generator"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "MorphoMesh_Creature"}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 0,
                            "NORMAL": 1,
                            "TEXCOORD_0": 2,
                        },
                        "indices": 3,
                        "mode": 4,  # TRIANGLES
                    }
                ],
                "name": "Creature_Mesh",
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,  # FLOAT
                "count": num_verts,
                "type": "VEC3",
                "max": bbox.max_point,
                "min": bbox.min_point,
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": num_verts,
                "type": "VEC3",
            },
            {
                "bufferView": 2,
                "componentType": 5126,
                "count": num_verts,
                "type": "VEC2",
            },
            {
                "bufferView": 3,
                "componentType": idx_type,
                "count": num_indices,
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": offset_pos,
                "byteLength": len_pos,
                "target": 34962,  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": offset_norm,
                "byteLength": len_norm,
                "target": 34962,
            },
            {
                "buffer": 0,
                "byteOffset": offset_uv,
                "byteLength": len_uv,
                "target": 34962,
            },
            {
                "buffer": 0,
                "byteOffset": offset_idx,
                "byteLength": len_idx,
                "target": 34963,  # ELEMENT_ARRAY_BUFFER
            },
        ],
        "buffers": [{"byteLength": total_bin_length}],
    }

    json_bytes = json.dumps(gltf_json, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad  # glTF JSON chunk padding must be spaces (0x20)

    json_chunk_len = len(json_bytes)
    bin_chunk_len = len(bin_buffer)
    total_glb_len = 12 + (8 + json_chunk_len) + (8 + bin_chunk_len)

    # GLB Header
    header = struct.pack("<4sII", b"glTF", 2, total_glb_len)
    # JSON Chunk header
    chunk0_hdr = struct.pack("<I4s", json_chunk_len, b"JSON")
    # BIN Chunk header
    chunk1_hdr = struct.pack("<I4s", bin_chunk_len, b"BIN\x00")

    with open(filepath, "wb") as f:
        f.write(header)
        f.write(chunk0_hdr)
        f.write(json_bytes)
        f.write(chunk1_hdr)
        f.write(bin_buffer)


__all__ = [
    "export_glb",
    "export_obj",
    "pad_4",
]
