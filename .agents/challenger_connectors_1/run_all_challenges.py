"""
Master Empirical Challenge Harness for MorphoMesh Phase 2 Connectors.
Runs all 4 empirical challenge suites and generates consolidated test audit data.
"""

from __future__ import annotations

import json
import os
import sys
import time
import pytest

CHALLENGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CHALLENGE_DIR, "../.."))

SUITES = [
    os.path.join(CHALLENGE_DIR, "test_math_transform_empirical.py"),
    os.path.join(CHALLENGE_DIR, "test_topology_budget_empirical.py"),
    os.path.join(CHALLENGE_DIR, "test_dag_schema_empirical.py"),
    os.path.join(CHALLENGE_DIR, "test_pbr_textures_empirical.py"),
]


def run_challenge_harness() -> Dict[str, Any]:
    print("=" * 80)
    print("MORPHOMESH PHASE 2: EMPIRICAL CHALLENGER MASTER HARNESS")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Harness directory: {CHALLENGE_DIR}")
    print("=" * 80)

    start_total = time.time()
    results = {}
    total_passed = 0
    total_failed = 0

    for suite_path in SUITES:
        suite_name = os.path.basename(suite_path)
        print(f"\n>>> Running Suite: {suite_name}")
        t0 = time.time()

        ret = pytest.main([
            "-v",
            "-s",
            "--tb=short",
            suite_path,
        ])

        elapsed = time.time() - t0
        passed = (ret == pytest.ExitCode.OK)
        status = "PASSED" if passed else "FAILED"
        print(f">>> Suite {suite_name} {status} in {elapsed:.2f}s (ExitCode: {ret})")

        results[suite_name] = {
            "status": status,
            "exit_code": int(ret),
            "duration_seconds": round(elapsed, 3),
        }
        if passed:
            total_passed += 1
        else:
            total_failed += 1

    total_elapsed = time.time() - start_total
    all_passed = (total_failed == 0)

    verdict = "APPROVE" if all_passed else "CHALLENGE_FAILED"

    summary = {
        "verdict": verdict,
        "total_suites": len(SUITES),
        "suites_passed": total_passed,
        "suites_failed": total_failed,
        "total_duration_seconds": round(total_elapsed, 3),
        "suite_details": results,
    }

    report_path = os.path.join(CHALLENGE_DIR, "challenge_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print(f"FINAL VERDICT: {verdict}")
    print(f"Suites passed: {total_passed}/{len(SUITES)} in {total_elapsed:.2f}s")
    print(f"Results recorded to: {report_path}")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    summary = run_challenge_harness()
    if summary["verdict"] != "APPROVE":
        sys.exit(1)
    sys.exit(0)
