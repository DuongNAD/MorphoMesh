"""
Empirical Verification & Adversarial Audit Suite:
Visual Preview Renders, Turntable Images, Thumbnail Contact Sheets, and PBR Textures.

Milestone 5 (M5) Challenger 2 Verification Script
Working Directory: E:/tool/mcp/MorphoMesh/.agents/m5_veg_challenger_2
Target Output: teamwork_projects/vegetation_library/output
"""

import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library" / "output"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@dataclass
class AuditResult:
    test_name: str
    target: str
    passed: bool
    details: str
    metrics: Dict[str, Any] = field(default_factory=dict)


class VisualPBRAuditor:
    def __init__(self, output_dir: Path, manifest_path: Path):
        self.output_dir = output_dir
        self.manifest_path = manifest_path
        self.results: List[AuditResult] = []
        self.species_records: Dict[str, Dict[str, Any]] = {}
        self.hashes: Dict[str, Dict[str, str]] = {}

    def load_manifest(self) -> bool:
        if not self.manifest_path.is_file():
            self.results.append(
                AuditResult(
                    test_name="Manifest Exists",
                    target=str(self.manifest_path),
                    passed=False,
                    details=f"Manifest file missing at {self.manifest_path}",
                )
            )
            return False

        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.species_records = data.get("assets", {})
            self.results.append(
                AuditResult(
                    test_name="Manifest Exists and Parsable",
                    target=str(self.manifest_path),
                    passed=True,
                    details=f"Loaded manifest with {len(self.species_records)} indexed species.",
                    metrics={"species_count": len(self.species_records)},
                )
            )
            return True
        except Exception as e:
            self.results.append(
                AuditResult(
                    test_name="Manifest Parsable",
                    target=str(self.manifest_path),
                    passed=False,
                    details=f"Error parsing manifest JSON: {e}",
                )
            )
            return False

    def audit_all(self):
        print(f"=== Starting Empirical Audit across {len(self.species_records)} species ===")
        assert len(self.species_records) == 35, f"Expected exactly 35 species, found {len(self.species_records)}"

        # 1. Turntables
        self.audit_turntable_renders()

        # 2. Thumbnails
        self.audit_thumbnail_contact_sheets()

        # 3. PBR Textures
        self.audit_pbr_textures()

        # 4. Cross-Species Hash Diversity & Distinctness
        self.audit_hash_diversity()

    def audit_turntable_renders(self):
        print("\n--- Auditing 140 Turntable Renders (4 per species) ---")
        turntable_angles = ["turntable_01.png", "turntable_02.png", "turntable_03.png", "turntable_04.png"]

        for sp_id, rec in self.species_records.items():
            category = rec.get("category", "")
            sp_dir = self.output_dir / category / sp_id

            for tt_name in turntable_angles:
                tt_path = sp_dir / tt_name
                target_desc = f"{sp_id}/{tt_name}"

                # 1. Existence and size
                if not tt_path.is_file():
                    self.results.append(
                        AuditResult(
                            test_name="Turntable File Exists",
                            target=target_desc,
                            passed=False,
                            details=f"Missing turntable file: {tt_path}",
                        )
                    )
                    continue

                size_bytes = tt_path.stat().st_size
                if size_bytes == 0:
                    self.results.append(
                        AuditResult(
                            test_name="Turntable Non-Empty",
                            target=target_desc,
                            passed=False,
                            details="File is 0 bytes",
                        )
                    )
                    continue

                # 2. PNG Magic bytes
                with open(tt_path, "rb") as f:
                    magic = f.read(8)
                magic_ok = magic == PNG_MAGIC
                if not magic_ok:
                    self.results.append(
                        AuditResult(
                            test_name="Turntable Valid PNG Magic",
                            target=target_desc,
                            passed=False,
                            details=f"Invalid PNG magic bytes: {magic!r}",
                        )
                    )
                    continue

                # 3. Dimensions and format via PIL
                try:
                    with Image.open(tt_path) as img:
                        img.load()
                        fmt = img.format
                        dims = img.size
                        mode = img.mode

                        dim_ok = dims == (512, 512)
                        fmt_ok = fmt == "PNG"

                        # 4. Statistical analysis (mean intensity > 0.01, std > 0.01)
                        # We convert to RGBA numpy array normalized to [0, 1]
                        arr_rgba = np.array(img.convert("RGBA"), dtype=np.float32) / 255.0
                        # Calculate mean pixel intensity across RGBA or RGB
                        mean_val = float(np.mean(arr_rgba))
                        std_val = float(np.std(arr_rgba))

                        # Also check alpha channel specifically: plant geometry must occupy alpha > 0
                        alpha_channel = arr_rgba[:, :, 3]
                        alpha_coverage = float(np.mean(alpha_channel > 0.05))

                        # Check RGB visible channels
                        rgb_arr = arr_rgba[:, :, :3]
                        rgb_mean = float(np.mean(rgb_arr))
                        rgb_std = float(np.std(rgb_arr))

                        non_blank = (std_val > 0.01) and (mean_val > 0.01) and (alpha_coverage > 0.005)

                        passed = dim_ok and fmt_ok and non_blank

                        details = (
                            f"Format={fmt}, Mode={mode}, Dims={dims}, Mean={mean_val:.4f}, Std={std_val:.4f}, "
                            f"RGB_Mean={rgb_mean:.4f}, RGB_Std={rgb_std:.4f}, AlphaCoverage={alpha_coverage * 100:.1f}%, "
                            f"Bytes={size_bytes}"
                        )

                        self.results.append(
                            AuditResult(
                                test_name="Turntable Spec Verification",
                                target=target_desc,
                                passed=passed,
                                details=details,
                                metrics={
                                    "size_bytes": size_bytes,
                                    "dimensions": list(dims),
                                    "format": fmt,
                                    "mode": mode,
                                    "mean": mean_val,
                                    "std": std_val,
                                    "rgb_mean": rgb_mean,
                                    "rgb_std": rgb_std,
                                    "alpha_coverage": alpha_coverage,
                                },
                            )
                        )

                        # Store hash for diversity audit
                        if sp_id not in self.hashes:
                            self.hashes[sp_id] = {}
                        with open(tt_path, "rb") as f_hash:
                            self.hashes[sp_id][tt_name] = hashlib.sha256(f_hash.read()).hexdigest()

                except Exception as e:
                    self.results.append(
                        AuditResult(
                            test_name="Turntable Open & Decode",
                            target=target_desc,
                            passed=False,
                            details=f"PIL decode failure: {e}",
                        )
                    )

    def audit_thumbnail_contact_sheets(self):
        print("\n--- Auditing 35 Visual Showcase Thumbnails ---")

        for sp_id, rec in self.species_records.items():
            category = rec.get("category", "")
            sp_dir = self.output_dir / category / sp_id
            thumb_path = sp_dir / "thumbnail.png"
            target_desc = f"{sp_id}/thumbnail.png"

            if not thumb_path.is_file():
                self.results.append(
                    AuditResult(
                        test_name="Thumbnail File Exists",
                        target=target_desc,
                        passed=False,
                        details=f"Missing thumbnail file: {thumb_path}",
                    )
                )
                continue

            size_bytes = thumb_path.stat().st_size
            if size_bytes == 0:
                self.results.append(
                    AuditResult(
                        test_name="Thumbnail Non-Empty",
                        target=target_desc,
                        passed=False,
                        details="Thumbnail is 0 bytes",
                    )
                )
                continue

            with open(thumb_path, "rb") as f:
                magic = f.read(8)
            if magic != PNG_MAGIC:
                self.results.append(
                    AuditResult(
                        test_name="Thumbnail Valid PNG Magic",
                        target=target_desc,
                        passed=False,
                        details=f"Invalid PNG magic bytes: {magic!r}",
                    )
                )
                continue

            try:
                with Image.open(thumb_path) as img:
                    img.load()
                    fmt = img.format
                    dims = img.size
                    dim_ok = (dims == (1024, 1024))
                    fmt_ok = (fmt == "PNG")

                    arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0

                    # 1. Header Banner Check (y in [0, 72])
                    header = arr[0:72, :, :]
                    header_mean = float(np.mean(header))
                    header_std = float(np.std(header))
                    # Header base is dark (mean < 0.35)
                    dark_header_ok = header_mean < 0.35
                    # Text presence: bright pixels (> 0.5) must be present in header
                    text_pixels = int(np.sum(np.mean(header, axis=2) > 0.5))
                    text_present = text_pixels > 300  # At least 300 bright text pixels

                    header_ok = dark_header_ok and text_present and (header_std > 0.05)

                    # 2. 2x2 Grid Montage Quadrant Population
                    # Cell 0 (Hero): [80:528, 8:508]
                    # Cell 1 (Front): [80:528, 516:1016]
                    # Cell 2 (Side): [536:984, 8:508]
                    # Cell 3 (Crown): [536:984, 516:1016]
                    quadrants = {
                        "q0_hero": arr[80:528, 8:508, :],
                        "q1_front": arr[80:528, 516:1016, :],
                        "q2_side": arr[536:984, 8:508, :],
                        "q3_crown": arr[536:984, 516:1016, :],
                    }

                    quad_metrics = {}
                    quad_ok = True
                    for q_name, q_arr in quadrants.items():
                        q_mean = float(np.mean(q_arr))
                        q_std = float(np.std(q_arr))
                        q_min = float(np.min(q_arr))
                        quad_metrics[q_name] = {"mean": q_mean, "std": q_std, "min": q_min}
                        # Must not be solid blank (blank canvas would be uniform with std < 0.005)
                        if q_std < 0.01 or q_min > 0.98:
                            quad_ok = False

                    overall_thumb_ok = dim_ok and fmt_ok and header_ok and quad_ok

                    details = (
                        f"Dims={dims}, HeaderMean={header_mean:.3f}, TextPix={text_pixels}, "
                        f"QuadsPopulated={quad_ok}, Q_Stds={[round(m['std'], 3) for m in quad_metrics.values()]}"
                    )

                    self.results.append(
                        AuditResult(
                            test_name="Thumbnail Montage & Header Spec",
                            target=target_desc,
                            passed=overall_thumb_ok,
                            details=details,
                            metrics={
                                "size_bytes": size_bytes,
                                "dimensions": list(dims),
                                "header_mean": header_mean,
                                "header_std": header_std,
                                "text_pixels": text_pixels,
                                "header_ok": header_ok,
                                "quad_metrics": quad_metrics,
                                "quad_ok": quad_ok,
                            },
                        )
                    )

                    with open(thumb_path, "rb") as f_hash:
                        self.hashes[sp_id]["thumbnail"] = hashlib.sha256(f_hash.read()).hexdigest()

            except Exception as e:
                self.results.append(
                    AuditResult(
                        test_name="Thumbnail Open & Decode",
                        target=target_desc,
                        passed=False,
                        details=f"PIL decode failure: {e}",
                    )
                )

    def audit_pbr_textures(self):
        print("\n--- Auditing 140 Discrete PBR Textures (4 channels per species) ---")
        texture_channels = ["albedo.png", "normal.png", "roughness.png", "metallic.png"]

        for sp_id, rec in self.species_records.items():
            category = rec.get("category", "")
            tex_dir = self.output_dir / category / sp_id / "textures"

            for ch_name in texture_channels:
                tex_path = tex_dir / ch_name
                target_desc = f"{sp_id}/textures/{ch_name}"

                if not tex_path.is_file():
                    self.results.append(
                        AuditResult(
                            test_name="PBR Texture Exists",
                            target=target_desc,
                            passed=False,
                            details=f"Missing texture file: {tex_path}",
                        )
                    )
                    continue

                size_bytes = tex_path.stat().st_size
                if size_bytes == 0:
                    self.results.append(
                        AuditResult(
                            test_name="PBR Texture Non-Empty",
                            target=target_desc,
                            passed=False,
                            details="File is 0 bytes",
                        )
                    )
                    continue

                with open(tex_path, "rb") as f:
                    magic = f.read(8)
                if magic != PNG_MAGIC:
                    self.results.append(
                        AuditResult(
                            test_name="PBR Texture Valid PNG Magic",
                            target=target_desc,
                            passed=False,
                            details=f"Invalid PNG magic bytes: {magic!r}",
                        )
                    )
                    continue

                try:
                    with Image.open(tex_path) as img:
                        img.load()
                        dims = img.size
                        dim_ok = (dims[0] >= 256 and dims[1] >= 256)

                        passed = dim_ok
                        details = f"Dims={dims}, Size={size_bytes}B"
                        metrics = {"dims": list(dims), "size_bytes": size_bytes}

                        # Channel-specific physical assertions
                        if ch_name == "albedo.png":
                            arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
                            mean_val = float(np.mean(arr))
                            # Spatial std across pixels per channel
                            std_val = float(np.mean(np.std(arr, axis=(0, 1))))
                            metrics["albedo_mean"] = mean_val
                            metrics["albedo_std"] = std_val

                            # Assert non-solid-black: mean > 0.05, std > 0.02
                            non_black_ok = (mean_val > 0.05) and (std_val > 0.02)
                            passed = passed and non_black_ok
                            details += f", Mean={mean_val:.4f} (>0.05), Std={std_val:.4f} (>0.02)"

                        elif ch_name == "normal.png":
                            arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
                            nx = 2.0 * arr[:, :, 0] - 1.0
                            ny = 2.0 * arr[:, :, 1] - 1.0
                            nz = 2.0 * arr[:, :, 2] - 1.0
                            mag = np.sqrt(nx**2 + ny**2 + nz**2)

                            mean_nz = float(np.mean(nz))
                            mean_mag = float(np.mean(mag))
                            metrics["normal_mean_nz"] = mean_nz
                            metrics["normal_mean_mag"] = mean_mag

                            # Assert tangent space outward Z in [0.5, 1.0]
                            nz_ok = (0.5 <= mean_nz <= 1.0)
                            mag_ok = abs(mean_mag - 1.0) <= 0.15
                            passed = passed and nz_ok and mag_ok
                            details += f", MeanNZ={mean_nz:.4f} in [0.5, 1.0], MeanMag={mean_mag:.4f} (~1.0)"

                        elif ch_name == "roughness.png":
                            arr = np.array(img.convert("L"), dtype=np.float32) / 255.0
                            mean_r = float(np.mean(arr))
                            std_r = float(np.std(arr))
                            metrics["roughness_mean"] = mean_r
                            metrics["roughness_std"] = std_r

                            # Assert organic roughness in [0.20, 0.95], std > 0.01
                            r_ok = (0.20 <= mean_r <= 0.95) and (std_r > 0.01)
                            passed = passed and r_ok
                            details += f", MeanR={mean_r:.4f} in [0.20, 0.95], StdR={std_r:.4f} (>0.01)"

                        elif ch_name == "metallic.png":
                            arr = np.array(img.convert("L"), dtype=np.float32) / 255.0
                            max_m = float(np.max(arr))
                            mean_m = float(np.mean(arr))
                            metrics["metallic_max"] = max_m
                            metrics["metallic_mean"] = mean_m

                            # Assert strictly dielectric: max <= 0.05, mean <= 0.02
                            metal_ok = (max_m <= 0.05) and (mean_m <= 0.02)
                            passed = passed and metal_ok
                            details += f", MaxM={max_m:.4f} (<=0.05), MeanM={mean_m:.4f} (<=0.02)"

                        self.results.append(
                            AuditResult(
                                test_name=f"PBR {ch_name.split('.')[0].title()} Verification",
                                target=target_desc,
                                passed=passed,
                                details=details,
                                metrics=metrics,
                            )
                        )

                        with open(tex_path, "rb") as f_hash:
                            self.hashes[sp_id][ch_name] = hashlib.sha256(f_hash.read()).hexdigest()

                except Exception as e:
                    self.results.append(
                        AuditResult(
                            test_name="PBR Texture Open & Decode",
                            target=target_desc,
                            passed=False,
                            details=f"PIL decode failure: {e}",
                        )
                    )

    def audit_hash_diversity(self):
        print("\n--- Auditing Cross-Species Hash Diversity ---")
        # Check if assets are distinct across species
        albedo_hashes = set()
        thumbnail_hashes = set()
        tt01_hashes = set()

        for sp_id, hdict in self.hashes.items():
            if "albedo.png" in hdict:
                albedo_hashes.add(hdict["albedo.png"])
            if "thumbnail" in hdict:
                thumbnail_hashes.add(hdict["thumbnail"])
            if "turntable_01.png" in hdict:
                tt01_hashes.add(hdict["turntable_01.png"])

        total_sp = len(self.hashes)
        # Thumbnails and turntable renders must be 100% unique per species
        unique_thumbnails = len(thumbnail_hashes) == total_sp
        unique_tt01 = len(tt01_hashes) == total_sp

        self.results.append(
            AuditResult(
                test_name="Thumbnail Uniqueness Across Species",
                target="35 Visual Showcase Thumbnails",
                passed=unique_thumbnails,
                details=f"Unique thumbnail SHA-256 hashes: {len(thumbnail_hashes)} / {total_sp}",
                metrics={"unique_thumbnails": len(thumbnail_hashes), "total": total_sp},
            )
        )

        self.results.append(
            AuditResult(
                test_name="Turntable Hero Uniqueness Across Species",
                target="35 Turntable 01 Renders",
                passed=unique_tt01,
                details=f"Unique turntable_01 SHA-256 hashes: {len(tt01_hashes)} / {total_sp}",
                metrics={"unique_tt01": len(tt01_hashes), "total": total_sp},
            )
        )

        self.results.append(
            AuditResult(
                test_name="Albedo Diversity Across Species",
                target="35 Albedo Textures",
                passed=len(albedo_hashes) > 1,
                details=f"Unique albedo SHA-256 hashes: {len(albedo_hashes)} / {total_sp}",
                metrics={"unique_albedos": len(albedo_hashes), "total": total_sp},
            )
        )

    def generate_report(self) -> Dict[str, Any]:
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = sum(1 for r in self.results if not r.passed)

        failures = [r for r in self.results if not r.passed]

        # Summary statistics by category
        tt_results = [r for r in self.results if "Turntable" in r.test_name]
        thumb_results = [r for r in self.results if "Thumbnail" in r.test_name]
        pbr_results = [r for r in self.results if "PBR" in r.test_name]

        report = {
            "total_audited_files": 315,
            "total_assertions": total_tests,
            "passed_assertions": passed_tests,
            "failed_assertions": failed_tests,
            "pass_rate_pct": round(passed_tests / total_tests * 100, 2) if total_tests > 0 else 0.0,
            "verdict": "APPROVE" if failed_tests == 0 else "REQUEST_CHANGES",
            "turntable_summary": {
                "total": len(tt_results),
                "passed": sum(1 for r in tt_results if r.passed),
            },
            "thumbnail_summary": {
                "total": len(thumb_results),
                "passed": sum(1 for r in thumb_results if r.passed),
            },
            "pbr_summary": {
                "total": len(pbr_results),
                "passed": sum(1 for r in pbr_results if r.passed),
            },
            "failures": [
                {"test": f.test_name, "target": f.target, "details": f.details}
                for f in failures
            ],
        }
        return report


def main():
    auditor = VisualPBRAuditor(OUTPUT_DIR, MANIFEST_PATH)
    if not auditor.load_manifest():
        print("FATAL: Failed to load manifest.")
        sys.exit(1)

    auditor.audit_all()
    report = auditor.generate_report()

    print("\n" + "=" * 80)
    print(f"AUDIT VERDICT: {report['verdict']}")
    print(f"Total Assertions: {report['total_assertions']}")
    print(f"Passed: {report['passed_assertions']} / {report['total_assertions']} ({report['pass_rate_pct']}%)")
    print(f"Failed: {report['failed_assertions']}")
    print(f"Turntables: {report['turntable_summary']['passed']}/{report['turntable_summary']['total']}")
    print(f"Thumbnails: {report['thumbnail_summary']['passed']}/{report['thumbnail_summary']['total']}")
    print(f"PBR Textures: {report['pbr_summary']['passed']}/{report['pbr_summary']['total']}")
    print("=" * 80)

    # Save detailed JSON report to working directory
    out_json = Path(__file__).parent / "audit_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": report,
                "detailed_results": [
                    {
                        "test_name": r.test_name,
                        "target": r.target,
                        "passed": r.passed,
                        "details": r.details,
                        "metrics": r.metrics,
                    }
                    for r in auditor.results
                ],
            },
            f,
            indent=2,
        )
    print(f"Saved full audit report to: {out_json}")

    if report["verdict"] != "APPROVE":
        sys.exit(1)


if __name__ == "__main__":
    main()
