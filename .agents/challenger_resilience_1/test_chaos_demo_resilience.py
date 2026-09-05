"""
Chaos Test Suite 4: Demo Script Resilience & Mock Configuration Verification
MorphoMesh Phase 2: Resilience & Chaos Challenger
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEMO_SCRIPT = PROJECT_ROOT / "examples" / "open_source_pipeline_demo.py"


class TestDemoScriptResilience(unittest.TestCase):
    """Empirical verification of examples/open_source_pipeline_demo.py under diverse environments."""

    def test_demo_script_default_execution(self):
        """Verify demo script runs successfully with exit code 0 under standard environment."""
        self.assertTrue(DEMO_SCRIPT.is_file(), f"Demo script not found: {DEMO_SCRIPT}")

        cmd = [sys.executable, str(DEMO_SCRIPT)]
        res = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

        self.assertEqual(
            res.returncode,
            0,
            f"Demo script failed with exit code {res.returncode}.\nStderr: {res.stderr}\nStdout: {res.stdout}",
        )
        self.assertIn("Pipeline Demo Execution Complete: SUCCESS", res.stdout)
        self.assertIn("Stage 1: Prompt Parsing & BodyGraph Compilation", res.stdout)
        self.assertIn("Stage 2: 3D Asset & 4-Channel PBR Texture Synthesis", res.stdout)
        self.assertIn("Stage 3: Autoregressive Quad Retopology", res.stdout)
        self.assertIn("Stage 4: 35-Joint SMAL Landmark Extraction", res.stdout)
        self.assertIn("Stage 5: Pipeline Metrics Summary", res.stdout)

    def test_demo_script_isolated_env_variables(self):
        """Verify demo script executes cleanly with isolated custom environment variables."""
        temp_cache = tempfile.mkdtemp(prefix="morphomesh_demo_cache_")
        try:
            env = os.environ.copy()
            env["MORPHOMESH_STORAGE_DIR"] = temp_cache
            env["MORPHOMESH_BACKEND"] = "mock"
            env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

            cmd = [sys.executable, str(DEMO_SCRIPT)]
            res = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )

            self.assertEqual(
                res.returncode,
                0,
                f"Demo failed under custom env.\nStderr: {res.stderr}\nStdout: {res.stdout}",
            )
            self.assertIn("Pipeline Demo Execution Complete: SUCCESS", res.stdout)
        finally:
            shutil.rmtree(temp_cache, ignore_errors=True)

    def test_demo_script_consecutive_idempotent_runs(self):
        """Verify demo script is idempotent and can execute consecutively without file collision errors."""
        for run_idx in range(3):
            res = subprocess.run(
                [sys.executable, str(DEMO_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Consecutive run #{run_idx + 1} failed.\nStderr: {res.stderr}\nStdout: {res.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
