"""
Empirical Forensic Verification Script for Milestone M2.
Tests wardrobe procedural math genuineness, parameter sensitivity, and anti-cheating rules.
"""

import ast
import math
import sys
from morphomesh.wardrobe import (
    generate_dress_organic_skirt,
    generate_dress_bodice,
    generate_dress_waist_sash,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    compute_dress_waist_radii,
)

def test_ast_integrity():
    print("=== Phase 1: Static AST & Anti-Cheating Analysis ===")
    with open("src/morphomesh/wardrobe.py", "r", encoding="utf-8") as f:
        code = f.read()

    tree = ast.parse(code)

    # 1. Check for banned inspection/cheating calls
    banned_names = {"inspect", "_getframe", "environ", "pytest"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in banned_names:
            raise AssertionError(f"Banned identifier found in AST: {node.id}")
        if isinstance(node, ast.Attribute) and node.attr in banned_names:
            raise AssertionError(f"Banned attribute found in AST: {node.attr}")

    print("[PASS] Zero cheating/stack inspection/environment flags detected in wardrobe.py.")

    # 2. Count mathematical calls in generate_dress_organic_skirt, generate_dress_bodice, generate_dress_waist_sash
    funcs = {}
    for item in tree.body:
        if isinstance(item, ast.FunctionDef):
            funcs[item.name] = item

    for fname in ["generate_dress_organic_skirt", "generate_dress_bodice", "generate_dress_waist_sash"]:
        assert fname in funcs, f"Missing function {fname}"
        fn_node = funcs[fname]
        math_calls = []
        loops = []
        for child in ast.walk(fn_node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and isinstance(child.func.value, ast.Name) and child.func.value.id == "math":
                    math_calls.append(child.func.attr)
            elif isinstance(child, (ast.For, ast.While)):
                loops.append(child)

        print(f"[{fname}] AST Metrics: {len(math_calls)} math calls {set(math_calls)}, {len(loops)} loops.")
        assert len(math_calls) >= 8, f"{fname} has too few math calls ({len(math_calls)}) to be procedural!"
        assert len(loops) >= 2, f"{fname} has too few loops ({len(loops)}) to be procedural!"

    print("[PASS] Procedural math complexity confirmed via AST analysis.")

def test_parameter_mutation():
    print("\n=== Phase 2: Dynamic Parameter Mutation & Sensitivity Analysis ===")

    # 1. Skirt parameter mutations
    print("Testing generate_dress_organic_skirt parameter mutations:")
    skirt_base = generate_dress_organic_skirt(height=1.65, waist_girth=0.58, sectors=48, rings_count=16)
    skirt_tall = generate_dress_organic_skirt(height=1.98, waist_girth=0.58, sectors=48, rings_count=16)
    skirt_wide = generate_dress_organic_skirt(height=1.65, waist_girth=0.87, sectors=48, rings_count=16)
    skirt_dense = generate_dress_organic_skirt(height=1.65, waist_girth=0.58, sectors=64, rings_count=20)

    # Check height scaling: Z coordinates must scale linearly by 1.98 / 1.65 = 1.20
    scale_h = 1.98 / 1.65
    z_base_max = max(v[2] for v in skirt_base.vertices)
    z_tall_max = max(v[2] for v in skirt_tall.vertices)
    ratio_z = z_tall_max / z_base_max
    print(f"  Height scaling ratio: {ratio_z:.4f} (expected: {scale_h:.4f})")
    assert math.isclose(ratio_z, scale_h, rel_tol=1e-3), "Skirt Z failed linear height scaling"

    # Check waist girth scaling: radius at waist must scale with waist_girth (0.87 / 0.58 = 1.50)
    scale_w = 0.87 / 0.58
    r_base_waist = max(math.hypot(v[0], v[1]) for v in skirt_base.vertices[:49])
    r_wide_waist = max(math.hypot(v[0], v[1]) for v in skirt_wide.vertices[:49])
    # Note: radius has a constant clearance offset of 0.015m, so:
    # (r_wide_waist - 0.015) / (r_base_waist - 0.015) should be close to scale_w
    raw_ratio_w = (r_wide_waist - 0.015) / (r_base_waist - 0.015)
    print(f"  Waist girth scaling ratio (net clearance): {raw_ratio_w:.4f} (expected: {scale_w:.4f})")
    assert math.isclose(raw_ratio_w, scale_w, rel_tol=1e-2), "Skirt radius failed waist girth scaling"

    # Check topological grid scaling: sectors and rings
    expected_base_verts = 16 * 49
    expected_dense_verts = 20 * 65
    print(f"  Vertex counts: base={len(skirt_base.vertices)} (exp {expected_base_verts}), dense={len(skirt_dense.vertices)} (exp {expected_dense_verts})")
    assert len(skirt_base.vertices) == expected_base_verts
    assert len(skirt_dense.vertices) == expected_dense_verts

    # 2. Bodice parameter mutations
    print("\nTesting generate_dress_bodice parameter mutations:")
    bodice_base = generate_dress_bodice(height=1.65, waist_girth=0.58, chest_girth=0.82, bust_cup_scale=1.0)
    bodice_bigbust = generate_dress_bodice(height=1.65, waist_girth=0.58, chest_girth=0.82, bust_cup_scale=1.6)

    # Bust projection: compare Y coordinates of breast apex between base and bigbust
    y_min_base = min(v[1] for v in bodice_base.vertices if 1.15 <= v[2] <= 1.25)
    y_min_big = min(v[1] for v in bodice_bigbust.vertices if 1.15 <= v[2] <= 1.25)
    delta_y = abs(y_min_big) - abs(y_min_base)
    print(f"  Bust apex Y: base={y_min_base:.4f}m, big={y_min_big:.4f}m, delta={delta_y*1000:.1f}mm forward projection")
    assert delta_y > 0.010, f"Bust cup scale 1.6 did not project significantly forward ({delta_y*1000:.1f}mm)"

    # 3. Waist sash parameter mutations
    print("\nTesting generate_dress_waist_sash parameter mutations:")
    sash_base = generate_dress_waist_sash(height=1.65, waist_girth=0.58)
    sash_wide = generate_dress_waist_sash(height=1.65, waist_girth=0.87)

    r_sash_base = max(math.hypot(v[0], v[1]) for v in sash_base.vertices[:120])
    r_sash_wide = max(math.hypot(v[0], v[1]) for v in sash_wide.vertices[:120])
    print(f"  Sash band max radius: base={r_sash_base:.4f}m, wide={r_sash_wide:.4f}m")
    assert r_sash_wide > r_sash_base * 1.3, "Sash band did not expand with waist girth"

    # Verify clearance between sash and bodice
    bodice_waist_r = max(math.hypot(v[0], v[1]) for v in bodice_base.vertices if 1.03 <= v[2] <= 1.06)
    sash_waist_r = max(math.hypot(v[0], v[1]) for v in sash_base.vertices if 1.03 <= v[2] <= 1.06)
    clearance_measured = (sash_waist_r - bodice_waist_r) * 1000.0
    print(f"  Sash clearance over bodice: {clearance_measured:.2f}mm")
    assert clearance_measured >= 2.0, "Sash envelope failed >= 2.0mm outer clearance"

    # 4. Interface contracts
    print("\nTesting interface contracts:")
    dress_dict = generate_organic_dress(scale=1.1, k_waist=1.05, k_chest=1.05)
    assert "Dress_Bodice" in dress_dict and "Dress_OrganicSkirt" in dress_dict
    sash_dict = generate_waist_sash_and_bow(scale=1.1, k_waist=1.05)
    assert "Dress_WaistSash" in sash_dict
    print("  Contracts generated and returned genuine MeshGeometry objects.")

    print("\n[ALL EMPIRICAL CHECKS PASSED]")

if __name__ == "__main__":
    test_ast_integrity()
    test_parameter_mutation()
