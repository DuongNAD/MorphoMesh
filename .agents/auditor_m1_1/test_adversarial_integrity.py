"""
Auditor M1_1: Forensic Integrity & Adversarial Stress Test Suite
Milestone 1: Vegetation Library Pipeline & Validator Hardening
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
from unittest.mock import patch

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VEG_LIB_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library"
for p in (str(REPO_ROOT), str(VEG_LIB_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from vegetation_pipeline.catalog import get_catalog
from vegetation_pipeline.generator import MeshyGenerator, generate_plant
from vegetation_pipeline.validator import (
    decode_glb_geometry,
    parse_glb_container,
    validate_asset,
)


def run_all_checks() -> bool:
    results = {}
    cat = get_catalog()
    oak = cat["veg_tree_oak_01"]
    oak_dir = VEG_LIB_DIR / "output" / "broadleaf_trees" / "veg_tree_oak_01"

    print("\n" + "=" * 70)
    print("FORENSIC INTEGRITY AUDIT: MILESTONE 1 VEGETATION LIBRARY")
    print("=" * 70)

    # 1. Strict Meshy Mode Enforcement
    print("\n[CHECK 1] Strict Meshy Mode Enforcement...")
    with patch.dict(os.environ, {}, clear=True):
        try:
            generate_plant(oak, mode="meshy", output_dir=oak_dir / "_test_dummy")
            results["strict_meshy_no_key"] = False
            print("  FAIL: generate_plant(mode='meshy') did not raise on missing key!")
        except RuntimeError as e:
            results["strict_meshy_no_key"] = True
            print(f"  PASS: Strictly raised RuntimeError on unset key: {e}")

    with patch.dict(os.environ, {"MESHY_API_KEY": "msy_mock_test_key_12345"}):
        with patch.object(MeshyGenerator, "generate", side_effect=RuntimeError("Meshy cloud failure 500")):
            try:
                generate_plant(oak, mode="meshy", output_dir=oak_dir / "_test_dummy")
                results["strict_meshy_on_error"] = False
                print("  FAIL: generate_plant(mode='meshy') fell back on cloud error!")
            except RuntimeError as e:
                results["strict_meshy_on_error"] = True
                print(f"  PASS: Strictly raised RuntimeError on cloud failure (0% procedural fallback): {e}")

    # 2. Cache Provenance Enforcement
    print("\n[CHECK 2] Cache Provenance Enforcement...")
    meshy_gen = MeshyGenerator()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        (tmp_p / "cache_manifest.json").write_text(
            json.dumps({"source": "procedural", "species_id": "veg_tree_oak_01", "vertex_count": 4320}),
            encoding="utf-8"
        )
        fake_glb = tmp_p / "veg_tree_oak_01.glb"
        fake_glb.write_bytes(b"glTF\x02\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00JSON\x00\x00\x00\x00")
        cached = meshy_gen.check_cache(oak, target_dir=tmp_p, expected_source="meshy")
        if cached is None:
            results["cache_provenance_enforced"] = True
            print("  PASS: check_cache(expected_source='meshy') strictly rejected procedural cache candidate.")
        else:
            results["cache_provenance_enforced"] = False
            print("  FAIL: check_cache accepted procedural asset under meshy mode!")

    # 3. Live Meshy Cloud Provenance & Bit-Level Identity
    print("\n[CHECK 3] Live Meshy Cloud Provenance & Hash Verification...")
    task_id = "01a089f7-2837-7074-af0e-89c25070c634"
    cloud_url = f"https://api.meshy.ai/openapi/v2/text-to-3d/{task_id}"
    auth_key = "msy_3EH0wmTqFmJQm3RJcpbXxc26b96yVcXK37x6"
    req = urllib.request.Request(cloud_url, headers={"Authorization": f"Bearer {auth_key}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            cloud_meta = json.loads(resp.read().decode("utf-8"))

        assert cloud_meta.get("id") == task_id
        assert cloud_meta.get("status") == "SUCCEEDED"
        assert cloud_meta.get("mode") == "refine"
        assert "Quercus robur" in cloud_meta.get("prompt", "")
        remote_glb_url = cloud_meta.get("model_urls", {}).get("glb")
        assert remote_glb_url is not None
        print(f"  PASS: Meshy task {task_id} verified live on cloud API (status={cloud_meta.get('status')}).")

        raw_local_glb = oak_dir / "raw_meshy_model.glb"
        assert raw_local_glb.is_file(), f"Missing {raw_local_glb}"
        local_bytes = raw_local_glb.read_bytes()
        local_hash = hashlib.sha256(local_bytes).hexdigest()

        c_req = urllib.request.Request(remote_glb_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(c_req, timeout=30) as c_resp:
            cloud_bytes = c_resp.read()
        cloud_hash = hashlib.sha256(cloud_bytes).hexdigest()

        assert local_hash == cloud_hash, f"Hash mismatch: local={local_hash} vs cloud={cloud_hash}"
        print(f"  PASS: SHA-256 bit-level match verified: {local_hash}")
        results["meshy_cloud_provenance_and_hash"] = True
    except Exception as e:
        print(f"  FAIL: Cloud verification failed: {e}")
        results["meshy_cloud_provenance_and_hash"] = False

    # 4. Mesh Geometry & Static Invariants
    print("\n[CHECK 4] Normalized Mesh Geometry & Static Invariants...")
    norm_glb = oak_dir / "veg_tree_oak_01.glb"
    assert norm_glb.is_file(), f"Missing normalized GLB: {norm_glb}"
    gltf, bin_bytes = parse_glb_container(norm_glb)
    geom = decode_glb_geometry(gltf, bin_bytes)
    positions = geom["positions"]
    triangles = geom["triangles"]
    n_verts = len(positions)
    n_faces = len(triangles)
    z_min = float(positions[:, 2].min())
    z_max = float(positions[:, 2].max())
    h = z_max - z_min

    base_slice = positions[positions[:, 2] <= (z_min + 0.05 * h)]
    cx = float(np.mean(base_slice[:, 0]))
    cy = float(np.mean(base_slice[:, 1]))
    base_dist = np.sqrt(cx**2 + cy**2)

    skins = gltf.get("skins", [])
    anims = gltf.get("animations", [])

    print(f"  Vertices: {n_verts:,} (expected 58,853)")
    print(f"  Faces: {n_faces:,} (expected 59,487)")
    print(f"  Height: {h:.4f}m (target 12.0000m)")
    print(f"  Z_min: {z_min:.6f}m (tolerance <= 0.005m)")
    print(f"  Base centroid offset: {base_dist:.4f}m (tolerance <= 0.05m)")
    print(f"  Skins: {len(skins)}, Animations: {len(anims)}")

    assert n_verts == 58853, f"Unexpected vertex count: {n_verts}"
    assert n_faces == 59487, f"Unexpected face count: {n_faces}"
    assert abs(h - 12.0) <= 0.01, f"Height deviation: {h}"
    assert abs(z_min) <= 0.005, f"Ground alignment error: {z_min}"
    assert base_dist <= 0.05, f"Base centering error: {base_dist}"
    assert len(skins) == 0 and len(anims) == 0, "Static mesh invariant violated!"
    results["geometry_and_invariants"] = True
    print("  PASS: All geometry metrics and static mesh invariants fully verified.")

    # 5. 2K PBR Texture Suite Authenticity & Dielectric Clamping
    print("\n[CHECK 5] 2K PBR Texture Authenticity & Dielectric Clamping...")
    tex_dir = oak_dir / "textures"
    for ch in ["albedo", "normal", "roughness", "metallic"]:
        tp = tex_dir / f"{ch}.png"
        assert tp.is_file(), f"Missing texture file: {tp}"
        img = Image.open(tp)
        assert img.size == (2048, 2048), f"{ch} size is {img.size}, expected (2048, 2048)"
        arr = np.array(img)
        std_val = float(np.std(arr))
        unique_cnt = len(np.unique(arr))
        print(f"  {ch:>9}: shape={arr.shape}, std={std_val:.2f}, unique_values={unique_cnt}")
        assert unique_cnt > 10, f"{ch} is a solid color mock (unique values: {unique_cnt})!"
        assert std_val > 0.01, f"{ch} lacks spatial variation (std={std_val})!"

        if ch == "metallic":
            m_max = float(np.max(arr)) / 255.0
            m_mean = float(np.mean(arr)) / 255.0
            print(f"    metallic max={m_max:.4f}, mean={m_mean:.4f} (dielectric ceiling <= 0.05)")
            assert m_max <= 0.05, f"Metallic max {m_max} exceeds dielectric ceiling 0.05!"
            assert m_mean <= 0.02, f"Metallic mean {m_mean} exceeds dielectric mean 0.02!"

    results["texture_authenticity"] = True
    print("  PASS: 2K PBR textures verified authentic with real surface detail and dielectric clamping.")

    # 6. Validator Tamper Sensitivity
    print("\n[CHECK 6] Validator Tamper Sensitivity...")
    rep_baseline = validate_asset(oak_dir)
    assert rep_baseline.is_valid, f"Baseline validation failed: {rep_baseline.errors}"
    assert rep_baseline.passed_checks_count == 21, f"Expected 21/21 passed, got {rep_baseline.passed_checks_count}"
    print("  Baseline oak: 21/21 checks PASSED.")

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "oak_sandbox"
        shutil.copytree(oak_dir, sandbox)

        # Tamper 1: empty task_id in manifest
        m_file = sandbox / "asset_manifest.json"
        with open(m_file, "r", encoding="utf-8") as f:
            m_data = json.load(f)
        m_data["provenance"]["task_id"] = ""
        m_data["provenance"]["generator_metadata"]["task_id"] = ""
        m_data["metadata"]["task_id"] = ""
        with open(m_file, "w", encoding="utf-8") as f:
            json.dump(m_data, f)

        rep_tamper1 = validate_asset(sandbox)
        assert not rep_tamper1.is_valid, "Validator failed to catch missing task_id!"
        assert rep_tamper1.checks.get("meshy_cloud_provenance") is False
        print("  PASS: Validator caught empty task_id tamper.")

        # Restore manifest
        shutil.copyfile(oak_dir / "asset_manifest.json", m_file)

        # Tamper 2: non-dielectric metallic texture
        met_file = sandbox / "textures" / "metallic.png"
        bad_metal = Image.new("L", (2048, 2048), 255)
        bad_metal.save(met_file)
        rep_tamper2 = validate_asset(sandbox)
        assert not rep_tamper2.is_valid, "Validator failed to catch non-dielectric metallic texture!"
        assert rep_tamper2.checks.get("texture_metallic_dielectric") is False
        print("  PASS: Validator caught non-dielectric metallic tamper.")

    results["validator_tamper_sensitivity"] = True

    print("\n" + "=" * 70)
    print("AUDIT SUMMARY:")
    all_clean = all(results.values())
    for k, v in results.items():
        print(f"  {k:35}: {'PASS' if v else 'FAIL'}")
    print(f"FINAL AUDIT VERDICT: {'CLEAN' if all_clean else 'INTEGRITY VIOLATION'}")
    print("=" * 70)
    return all_clean


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
