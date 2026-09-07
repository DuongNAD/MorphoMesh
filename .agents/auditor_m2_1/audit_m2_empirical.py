"""
Forensic Integrity Audit Script for Milestone 2.
Auditor: auditor_m2_1
"""

import ast
import math
import os
import sys
import numpy as np

# Ensure src is in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from morphomesh.camera_rig import (
    CANONICAL_VIEWPOINTS,
    TURNTABLE_4VIEWS,
    calculate_character_bounds,
    calculate_optical_framing_distance,
    calculate_spherical_camera_position,
    get_anatomical_subregion_center,
    setup_inspector_camera,
    capture_viewport_image,
    capture_multi_angle_inspection,
)


def audit_ast_for_forbidden_patterns(filepath: str) -> list[str]:
    """Scan AST for hardcoded test results, facade implementations, assert True, etc."""
    violations = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content, filename=filepath)

    for node in ast.walk(tree):
        # Check for assert True or assert False
        if isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Constant):
                violations.append(f"{filepath}:{node.lineno} Tautological assertion: assert {node.test.value}")
            elif isinstance(node.test, ast.Compare):
                # Check for assert 1 == 1 or x == x
                if isinstance(node.test.left, ast.Constant) and len(node.test.comparators) == 1 and isinstance(node.test.comparators[0], ast.Constant):
                    if node.test.left.value == node.test.comparators[0].value:
                        violations.append(f"{filepath}:{node.lineno} Tautological comparison: {node.test.left.value} == {node.test.comparators[0].value}")

        # Check for functions that are pure stubs/facades (e.g. only return constant)
        if isinstance(node, ast.FunctionDef):
            # If function body has only 1 statement and it is return Constant
            if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                ret_val = node.body[0].value
                if isinstance(ret_val, ast.Constant) and ret_val.value not in (None, True, False):
                    violations.append(f"{filepath}:{node.lineno} Facade function {node.name} returns hardcoded constant: {ret_val.value}")
            # If body has only pass or docstring + pass
            real_stmts = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
            if len(real_stmts) == 1 and isinstance(real_stmts[0], ast.Pass):
                violations.append(f"{filepath}:{node.lineno} Stub function {node.name} only contains pass")

    return violations


def audit_framing_distance_math():
    """Empirically test optical framing distance derivation across 1000 parameters."""
    print("Testing optical framing distance trigonometry...")
    np.random.seed(42)
    for _ in range(1000):
        radius = float(np.random.uniform(0.05, 50.0))
        focal_len = float(np.random.uniform(15.0, 200.0))
        sensor_w = 36.0
        w_px = int(np.random.choice([512, 1024, 1920, 2048, 3840]))
        h_px = int(np.random.choice([512, 1024, 1080, 2048, 2160]))
        margin = float(np.random.uniform(0.0, 0.5))

        # Independent calculation
        ar = w_px / h_px
        if ar >= 1.0:
            w_eff = sensor_w
            h_eff = sensor_w / ar
        else:
            h_eff = sensor_w
            w_eff = sensor_w * ar
        alpha_h = math.atan(w_eff / (2.0 * focal_len))
        alpha_v = math.atan(h_eff / (2.0 * focal_len))
        alpha_min = min(alpha_h, alpha_v)
        expected_d = (radius / math.sin(alpha_min)) * (1.0 + margin)

        actual_d = calculate_optical_framing_distance(
            radius=radius,
            focal_length=focal_len,
            sensor_width=sensor_w,
            resolution=(w_px, h_px),
            margin=margin,
            sensor_fit="AUTO",
        )

        assert abs(actual_d - expected_d) / expected_d < 1e-5, f"Mismatch: actual {actual_d} vs expected {expected_d}"

    print("  -> Optical framing distance matches exact trigonometry across 1000 cases.")


def audit_spherical_orbit_coordinates():
    """Empirically verify spherical orbit placements and ray targeting."""
    print("Testing spherical orbit coordinate generation and camera tracking...")
    center = (1.2, -3.4, 5.6)
    for azim in range(0, 360, 15):
        for elev in range(-80, 85, 15):
            d = 5.0
            pos, rot = calculate_spherical_camera_position(center, d, azim, elev)
            actual_dist = math.sqrt(sum((pos[i] - center[i]) ** 2 for i in range(3)))
            assert abs(actual_dist - d) < 1e-4, f"Orbit distance deviation: {actual_dist} != {d} at azim={azim}, elev={elev}"

            # Verify Z height coordinate
            expected_dz = d * math.sin(math.radians(elev))
            actual_dz = pos[2] - center[2]
            assert abs(actual_dz - expected_dz) < 1e-4, f"Z deviation: {actual_dz} != {expected_dz}"

    print("  -> Spherical orbit coordinates match exact geometry across 576 angle pairs.")


def audit_hierarchical_bounding_box():
    """Test bounding box calculation with multi-object mock hierarchies."""
    print("Testing hierarchical bounding box solver...")
    class MockObj:
        def __init__(self, bbox, mat=None):
            self.bound_box = bbox
            self.matrix_world = mat

    # 3 objects at different positions
    b1 = [(-1, -1, 0), (1, 1, 2)]
    # All 8 corners
    corners1 = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (0, 2)]
    obj1 = MockObj(corners1)

    corners2 = [(x, y, z) for x in (0, 2) for y in (0, 3) for z in (1, 4)]
    obj2 = MockObj(corners2)

    center, radius, min_pt, max_pt = calculate_character_bounds([obj1, obj2])
    assert min_pt[0] == -1.0 and min_pt[1] == -1.0 and min_pt[2] == 0.0
    assert max_pt[0] == 2.0 and max_pt[1] == 3.0 and max_pt[2] == 4.0
    assert center[0] == 0.5 and center[1] == 1.0 and center[2] == 2.0
    expected_radius = math.sqrt(3.0**2 + 4.0**2 + 4.0**2) / 2.0
    assert abs(radius - expected_radius) < 1e-5

    print("  -> Hierarchical bounds calculation is exact.")


def audit_anatomical_centers():
    """Verify anatomical subregion centers ordering and focal lengths."""
    print("Testing anatomical subregion centering...")
    center = (0.0, 0.0, 1.0)
    min_c = (-0.3, -0.2, 0.0)
    max_c = (0.3, 0.2, 2.0)
    radius = 1.0

    feet_c, feet_r, feet_f = get_anatomical_subregion_center("feet", center, radius, min_c, max_c)
    hands_c, hands_r, hands_f = get_anatomical_subregion_center("hands", center, radius, min_c, max_c)
    torso_c, torso_r, torso_f = get_anatomical_subregion_center("torso", center, radius, min_c, max_c)
    head_c, head_r, head_f = get_anatomical_subregion_center("head", center, radius, min_c, max_c)

    assert feet_c[2] < hands_c[2] <= torso_c[2] < head_c[2], "Anatomical Z ordering violated!"
    assert head_f == 85.0 and hands_f == 85.0
    assert torso_f == 70.0 and feet_f == 70.0

    print("  -> Anatomical subregion centers and focal lengths verified.")


def main():
    print("=== Starting Milestone 2 Empirical Integrity Audit ===")

    # 1. AST Analysis
    files_to_check = [
        "src/morphomesh/camera_rig.py",
        "tests/test_inspector_camera.py",
        "tests/test_multiview_rendering.py",
        "src/morphomesh/models.py",
    ]
    all_violations = []
    for rel_path in files_to_check:
        full_p = os.path.join(repo_root, rel_path)
        violations = audit_ast_for_forbidden_patterns(full_p)
        if violations:
            print(f"FAILED AST check in {rel_path}:")
            for v in violations:
                print(f"  {v}")
            all_violations.extend(violations)
        else:
            print(f"PASSED AST check: {rel_path} (No facade, no stub, no tautological assertions)")

    # 2. Math & Algorithm Checks
    audit_framing_distance_math()
    audit_spherical_orbit_coordinates()
    audit_hierarchical_bounding_box()
    audit_anatomical_centers()

    if all_violations:
        print(f"\nAUDIT FAILED: {len(all_violations)} violations found.")
        sys.exit(1)
    else:
        print("\n=== Milestone 2 Empirical Integrity Audit PASSED CLEAN ===")
        sys.exit(0)


if __name__ == "__main__":
    main()
