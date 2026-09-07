"""
Empirical Adversarial Challenge Test Harness for Milestone 2 Iteration 2
Author: Challenger M2 Iteration 2 - 2 (Viewport Capture & Addon Deployment Challenger)
Working Directory: e:\tool\mcp\MorphoMesh\.agents\challenger_m2_iter2_2
"""

import os
import sys
import ast
import tempfile
import subprocess
import unittest
from unittest.mock import patch, MagicMock

# Ensure repo src is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PIL import Image
from morphomesh.camera_rig import capture_viewport_image, FALLBACK_PNG_BYTES
from morphomesh.blender_bridge import BlenderBridge


class TestFallbackPngValidation(unittest.TestCase):
    """1. Fallback PNG validation: Force capture_viewport_image to trigger fallback bytes."""

    def setUp(self):
        self.tmp_files = []

    def tearDown(self):
        for f in self.tmp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def _get_temp_path(self, name: str) -> str:
        p = os.path.join(tempfile.gettempdir(), f"challenger_{name}_{os.getpid()}.png")
        self.tmp_files.append(p)
        return p

    def test_fallback_png_raw_bitstream_integrity(self):
        """Verify raw FALLBACK_PNG_BYTES conforms to PNG spec and opens cleanly."""
        self.assertTrue(FALLBACK_PNG_BYTES.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(FALLBACK_PNG_BYTES.endswith(b"IEND\xaeB\x60\x82"))
        self.assertEqual(len(FALLBACK_PNG_BYTES), 70)

        out_p = self._get_temp_path("raw_bytes")
        with open(out_p, "wb") as f:
            f.write(FALLBACK_PNG_BYTES)

        with Image.open(out_p) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (1, 1))
            self.assertEqual(img.mode, "RGBA")
            img.verify()

        with Image.open(out_p) as img:
            px = img.getpixel((0, 0))
            self.assertEqual(px, (0, 0, 0, 0))

    def test_force_fallback_via_zero_dimensions(self):
        """Force capture_viewport_image to trigger fallback via resolution=(0, 0)."""
        out_p = self._get_temp_path("zero_res")
        res_path = capture_viewport_image(output_path=out_p, resolution=(0, 0))
        self.assertTrue(os.path.isfile(res_path))

        with Image.open(res_path) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (1, 1))
            self.assertEqual(img.mode, "RGBA")
            img.verify()

        with Image.open(res_path) as img:
            self.assertEqual(img.getpixel((0, 0)), (0, 0, 0, 0))

    def test_force_fallback_via_negative_dimensions(self):
        """Force capture_viewport_image to trigger fallback via negative resolution."""
        out_p = self._get_temp_path("neg_res")
        res_path = capture_viewport_image(output_path=out_p, resolution=(-100, -100))
        self.assertTrue(os.path.isfile(res_path))

        with Image.open(res_path) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (1, 1))
            self.assertEqual(img.mode, "RGBA")
            img.verify()

    def test_force_fallback_via_mocked_pil_runtime_error(self):
        """Force capture_viewport_image to trigger fallback via PIL.Image.new exception."""
        out_p = self._get_temp_path("mock_pil_err")
        with patch("PIL.Image.new", side_effect=RuntimeError("Simulated GDI/PIL crash")):
            res_path = capture_viewport_image(output_path=out_p, resolution=(1024, 1024))

        self.assertTrue(os.path.isfile(res_path))
        with Image.open(res_path) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (1, 1))
            self.assertEqual(img.mode, "RGBA")
            img.verify()

    def test_force_fallback_via_mocked_pil_memory_error(self):
        """Force capture_viewport_image to trigger fallback via MemoryError."""
        out_p = self._get_temp_path("mock_oom")
        with patch("PIL.Image.new", side_effect=MemoryError("VRAM Out of memory")):
            res_path = capture_viewport_image(output_path=out_p, resolution=(8192, 8192))

        self.assertTrue(os.path.isfile(res_path))
        with Image.open(res_path) as img:
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.size, (1, 1))
            self.assertEqual(img.mode, "RGBA")
            img.verify()


class TestBundledBlenderPythonDependencyIsolation(unittest.TestCase):
    """2. Bundled Blender Python dependency isolation: Run Blender in headless background mode."""

    BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

    def setUp(self):
        if not os.path.isfile(self.BLENDER_EXE):
            self.skipTest(f"Blender 4.5 binary not found at {self.BLENDER_EXE}")

    def test_blender_headless_camera_rig_import(self):
        """Run exact prompt command to verify OK output, zero exit code, and zero ModuleNotFoundError."""
        py_expr = "import sys; sys.path.insert(0, 'src'); from morphomesh.camera_rig import setup_inspector_camera; print('OK')"
        proc = subprocess.run(
            [self.BLENDER_EXE, "--background", "--python-expr", py_expr],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(proc.returncode, 0, f"Blender exited with code {proc.returncode}\nStdout: {proc.stdout}\nStderr: {proc.stderr}")
        self.assertIn("OK", proc.stdout, "Expected 'OK' printed to stdout")
        self.assertNotIn("ModuleNotFoundError", proc.stdout, "ModuleNotFoundError detected in stdout")
        self.assertNotIn("ModuleNotFoundError", proc.stderr, "ModuleNotFoundError detected in stderr")
        self.assertNotIn("pydantic", proc.stdout.lower(), "Pydantic failure detected in stdout")
        self.assertNotIn("pydantic", proc.stderr.lower(), "Pydantic failure detected in stderr")

    def test_blender_headless_full_camera_rig_symbols_and_execution(self):
        """Verify all public camera rig methods can be imported and executed inside Blender 4.5."""
        py_expr = (
            "import sys; sys.path.insert(0, 'src'); "
            "from morphomesh.camera_rig import "
            "    calculate_character_bounds, setup_inspector_camera, capture_viewport_image, capture_multi_angle_inspection; "
            "res = setup_inspector_camera(viewpoint='three_quarter'); "
            "assert res['status'] == 'success', f'Camera setup failed: {res}'; "
            "print('FULL_SYMBOLS_SUCCESS')"
        )
        proc = subprocess.run(
            [self.BLENDER_EXE, "--background", "--python-expr", py_expr],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(proc.returncode, 0, f"Blender execution failed: {proc.stderr}")
        self.assertIn("FULL_SYMBOLS_SUCCESS", proc.stdout)
        self.assertNotIn("ModuleNotFoundError", proc.stdout)
        self.assertNotIn("ModuleNotFoundError", proc.stderr)


class TestScriptSecurityValidatorCompliance(unittest.TestCase):
    """3. Script security validator compliance: Verify generated scripts against AddonSecurityValidator."""

    def setUp(self):
        listener_path = os.path.join(REPO_ROOT, "blender_addon", "morphomesh", "listener.py")
        self.assertTrue(os.path.isfile(listener_path))

        import importlib.util
        spec = importlib.util.spec_from_file_location("test_listener_mod", listener_path)
        mod = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"bpy": MagicMock(), "mathutils": MagicMock()}):
            spec.loader.exec_module(mod)
        self.validator = mod.AddonSecurityValidator()
        self.bridge = BlenderBridge()

    def test_headless_scripts_trigger_zero_forbidden_import_sys_or_os(self):
        """Verify that scripts generated by _generate_headless_script() trigger zero 'Forbidden import: sys' or 'os'."""
        methods_to_test = [
            ("morphomesh.ping", {}),
            ("morphomesh.get_scene_status", {}),
            ("morphomesh.setup_inspector_camera", {"viewpoint": "three_quarter"}),
            ("morphomesh.capture_viewport", {"resolution": [512, 512]}),
            ("morphomesh.capture_multi_angle_inspection", {"viewpoints": ["front", "side"]}),
            ("morphomesh.critique_visual_quality", {}),
            ("morphomesh.optimize_topology", {"input_mesh_path": "test.glb"}),
            ("morphomesh.create_armature", {"creature_type": "quadruped"}),
            ("morphomesh.render_preview", {}),
            ("morphomesh.setup_creature_fur", {}),
            ("morphomesh.evaluate_fur_ribbons", {}),
            ("morphomesh.setup_creature_materials", {}),
            ("morphomesh.generate_war_armor", {}),
            ("morphomesh.create_human_asset", {}),
            ("morphomesh.auto_rig_human", {}),
        ]

        forbidden_sys_or_os_violations = []
        for method, params in methods_to_test:
            script = self.bridge._generate_headless_script(method, params)
            tree = ast.parse(script)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    try:
                        self.validator.visit_Import(node)
                    except ValueError as e:
                        if "sys" in str(e) or "os" in str(e):
                            forbidden_sys_or_os_violations.append((method, str(e)))
                elif isinstance(node, ast.ImportFrom):
                    try:
                        self.validator.visit_ImportFrom(node)
                    except ValueError as e:
                        if "sys" in str(e) or "os" in str(e):
                            forbidden_sys_or_os_violations.append((method, str(e)))

        self.assertEqual(
            len(forbidden_sys_or_os_violations),
            0,
            f"Found unexpected forbidden sys/os imports: {forbidden_sys_or_os_violations}",
        )

    def test_interactive_scripts_pass_full_addon_security_validator(self):
        """Verify that in-Blender interactive scripts dispatched over socket 100% pass AddonSecurityValidator."""
        interactive_methods = [
            ("morphomesh.ping", {}),
            ("morphomesh.get_scene_status", {}),
            ("morphomesh.setup_inspector_camera", {"viewpoint": "front"}),
            ("morphomesh.setup_inspector_camera", {"viewpoint": "three_quarter", "margin": 0.2}),
            ("morphomesh.capture_viewport", {"resolution": (1024, 1024), "shading_mode": "SOLID"}),
        ]

        for method, params in interactive_methods:
            script = self.bridge._generate_interactive_script(method, params)
            self.validator.validate(script)

    def test_security_validator_blocks_malicious_payloads(self):
        """Verify AddonSecurityValidator actively blocks adversarial payloads."""
        malicious_payloads = [
            ("import subprocess; subprocess.Popen(['calc.exe'])", "Forbidden import: subprocess"),
            ("import socket; s = socket.socket()", "Forbidden import: socket"),
            ("import urllib.request", "Forbidden import: urllib.request"),
            ("eval('1 + 1')", "Forbidden built-in call: eval()"),
            ("exec('x = 1')", "Forbidden built-in call: exec()"),
            ("__import__('os').system('dir')", "Forbidden built-in call: __import__()"),
            ("x = ().__class__", "Forbidden reflection attribute: __class__"),
            ("x = ().__class__.__subclasses__()", "Forbidden reflection attribute: __subclasses__"),
        ]

        for payload, expected_err in malicious_payloads:
            with self.assertRaises(ValueError) as ctx:
                self.validator.validate(payload)
            self.assertIn(expected_err, str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

