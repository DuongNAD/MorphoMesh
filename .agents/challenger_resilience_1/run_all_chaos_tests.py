"""
MorphoMesh Phase 2: Resilience & Chaos Master Test Harness
Orchestrates and executes all empirical fault-tolerance and chaos test suites:
1. Circuit Breaker FSM & Concurrency Stress Harness
2. Connector Fallback Robustness Harness
3. FastMCP Invariance & Concurrency Harness
4. Demo Script Resilience & Mock Configuration Verification
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Add src to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(current_dir))

import test_chaos_circuit_breaker
import test_chaos_connector_fallback
import test_chaos_fastmcp_concurrency
import test_chaos_demo_resilience


def main():
    print("=" * 80)
    print("MORPHOMESH PHASE 2: RESILIENCE & CHAOS EMPIRICAL TEST SUITE")
    print(f"Working Directory: {current_dir}")
    print(f"Project Root:      {project_root}")
    print("=" * 80)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromModule(test_chaos_circuit_breaker))
    suite.addTests(loader.loadTestsFromModule(test_chaos_connector_fallback))
    suite.addTests(loader.loadTestsFromModule(test_chaos_fastmcp_concurrency))
    suite.addTests(loader.loadTestsFromModule(test_chaos_demo_resilience))

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print(f"CHAOS SUITE EXECUTION COMPLETED IN {elapsed:.2f}s")
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Errors:          {len(result.errors)}")
    print(f"Failures:        {len(result.failures)}")
    print(f"Success Rate:    {((result.testsRun - len(result.errors) - len(result.failures)) / result.testsRun) * 100:.1f}%")
    print("=" * 80)

    if result.wasSuccessful():
        print("VERDICT: ALL CHAOS & RESILIENCE TESTS PASSED EMPIRICALLY (APPROVE)")
        sys.exit(0)
    else:
        print("VERDICT: CHAOS / RESILIENCE FAILURES DETECTED (CHALLENGE_FAILED)")
        sys.exit(1)


if __name__ == "__main__":
    main()
