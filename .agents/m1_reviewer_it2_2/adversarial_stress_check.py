"""
adversarial_stress_check.py
Adversarial Stress Testing by m1_reviewer_it2_2
"""

import math
import sys
from pathlib import Path

proj_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
sys.path.insert(0, str(proj_dir))

from anime_pipeline.mesh.generator import AnimeMeshGenerator, AnimeMeshConfig
from anime_pipeline.mesh.topology_cleaner import TopologyValidator, NormalHarmonizer

def stress_test_face_areas_and_aspect_ratios():
    print("--- ADVERSARIAL TEST 1: FACE AREAS & ASPECT RATIOS ---")
    gen = AnimeMeshGenerator()
    res = gen.generate()
    
    for name, sm in res.submeshes.items():
        min_area = float("inf")
        max_aspect = 0.0
        for q in sm.quads:
            p0, p1, p2, p3 = [sm.vertices[i] for i in q]
            def tri_area(a, b, c):
                ab = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
                ac = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
                cx = ab[1]*ac[2] - ab[2]*ac[1]
                cy = ab[2]*ac[0] - ab[0]*ac[2]
                cz = ab[0]*ac[1] - ab[1]*ac[0]
                return 0.5 * math.sqrt(cx*cx + cy*cy + cz*cz)
            area = tri_area(p0, p1, p2) + tri_area(p0, p2, p3)
            min_area = min(min_area, area)
            
            edges = [
                math.sqrt((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2),
                math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2),
                math.sqrt((p3[0]-p2[0])**2 + (p3[1]-p2[1])**2 + (p3[2]-p2[2])**2),
                math.sqrt((p0[0]-p3[0])**2 + (p0[1]-p3[1])**2 + (p0[2]-p3[2])**2),
            ]
            aspect = max(edges) / max(1e-12, min(edges))
            max_aspect = max(max_aspect, aspect)
            
        print(f"  [{name}]: Min Quad Area = {min_area:.8e} m^2, Max Aspect Ratio = {max_aspect:.2f}")
        assert min_area > 1e-8, f"{name} contains near-zero area quad ({min_area})"
        assert max_aspect < 50.0, f"{name} contains hyper-stretched quad (aspect {max_aspect})"
    print("PASS: Face areas and aspect ratios within healthy limits.")

def stress_test_grounding_sweep():
    print("\n--- ADVERSARIAL TEST 2: GROUNDING SWEEP ---")
    offsets = [-0.15, -0.05, 0.0, 0.05, 0.15, 1.0]
    for gz in offsets:
        cfg = AnimeMeshConfig(ground_sole_z=gz)
        res = AnimeMeshGenerator(cfg).generate()
        shoes_min_z = min(v[2] for v in res.submeshes["Anime_Shoes"].vertices)
        legs_min_z = min(v[2] for v in res.submeshes["Anime_Legs"].vertices)
        diff = abs(shoes_min_z - legs_min_z)
        assert diff < 1e-4, f"Grounding mismatch at gz={gz}: shoes={shoes_min_z}, legs={legs_min_z}, diff={diff}"
        assert abs(shoes_min_z - gz) < 1e-4, f"Shoes not at ground plane gz={gz}: got {shoes_min_z}"
    print("PASS: Grounding offset strictly synchronized across arbitrary ground planes.")

def stress_test_integrity_scan():
    print("\n--- ADVERSARIAL TEST 3: INTEGRITY AND FACADE AUDIT ---")
    mesh_dir = proj_dir / "anime_pipeline" / "mesh"
    for py_file in mesh_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "if 'test' in sys.argv" not in content, f"Test bypass found in {py_file}"
        assert "mock" not in content.lower(), f"Mock reference found in {py_file}"
        assert "unittest.mock" not in content, f"Mock reference found in {py_file}"
        if "class NormalHarmonizer" in content:
            assert "math.sqrt" in content, "NormalHarmonizer missing normalization"
            assert "harmonize_discrete_seam_normals" in content, "Missing seam calculation"
    print("PASS: No hardcoded test mocks, bypasses, or facade flags detected.")

if __name__ == "__main__":
    stress_test_face_areas_and_aspect_ratios()
    stress_test_grounding_sweep()
    stress_test_integrity_scan()
    print("\nALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
