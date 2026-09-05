"""
Chaos Test Suite 2: Connector Fallback Robustness Harness
MorphoMesh Phase 2: Resilience & Chaos Challenger
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from morphomesh.connectors import (
    ConnectorRegistry,
    MeshAnythingConnector,
    MeshAnythingInput,
    RetopologyConfig,
    TrellisConfig,
    TrellisConnector,
    TrellisInput,
)
from morphomesh.inference_adapter import (
    EnhancedCreate3DAssetOutput,
    HuggingFaceInferenceAdapter,
    InferenceAdapter,
    MeshGeometry,
    MockInferenceAdapter,
    ReplicateInferenceAdapter,
)
from morphomesh.models import (
    Create3DAssetInput,
    GenerateConceptInput,
    MorphoMeshException,
)


class TestConnectorFallbackRobustness(unittest.TestCase):
    """Empirical testing of fallback robustness across connectors and inference adapter."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="morphomesh_chaos_")
        self.adapter = InferenceAdapter(cache_dir=self.temp_dir)
        # Create a valid input mesh for retopology testing
        self.sample_mesh_path = os.path.join(self.temp_dir, "sample_input.glb")
        geom = MeshGeometry()
        geom.add_box((0.0, 0.0, 0.5), (0.8, 1.2, 0.6))
        geom.add_sphere((0.0, 0.6, 1.1), 0.3)
        geom.export_glb(self.sample_mesh_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_trellis_unavailable_remote_endpoint_fallback(self):
        """Verify Trellis remote endpoint failure automatically falls back to procedural mock generation."""
        registry = ConnectorRegistry
        trellis_conn = registry.get("trellis")

        # Save original config
        orig_config = trellis_conn.trellis_config
        try:
            # Reconfigure Trellis to an unreachable remote endpoint
            trellis_conn.trellis_config = TrellisConfig(
                mode="remote",
                endpoint_url="http://127.0.0.1:59998/nonexistent_service",
                timeout_seconds=5.0,
            )

            req = Create3DAssetInput(
                concept_id="chimera-quadruped",
                model_backend="trellis",
                export_format="glb",
                generate_pbr=True,
                texture_resolution=512,
            )

            # Invoke generate_3d_asset on InferenceAdapter
            out = self.adapter.generate_3d_asset(req)

            # Verification: output must be valid EnhancedCreate3DAssetOutput
            self.assertIsInstance(out, EnhancedCreate3DAssetOutput)
            self.assertEqual(out.backend_used, "mock")
            self.assertEqual(out.metadata.get("connector"), "mock")
            self.assertEqual(out.metadata.get("mode"), "procedural")
            self.assertTrue(os.path.isfile(out.mesh_path))
            self.assertGreater(os.path.getsize(out.mesh_path), 0)
            self.assertGreater(out.vertex_count, 0)
            self.assertGreater(out.face_count, 0)
            self.assertTrue(out.has_pbr_materials)
            self.assertIn("albedo", out.texture_paths)
            self.assertTrue(os.path.isfile(out.texture_paths["albedo"]))

        finally:
            trellis_conn.trellis_config = orig_config

    def test_hunyuan_unavailable_remote_endpoint_fallback(self):
        """Verify Hunyuan connector failure triggers procedural mock generation."""
        registry = ConnectorRegistry
        hunyuan_conn = registry.get("hunyuan")

        # Mock hunyuan connector execute to simulate connection error / 503 backend failure
        with patch.object(hunyuan_conn, "execute", side_effect=ConnectionRefusedError("Hunyuan endpoint unavailable")):
            req = Create3DAssetInput(
                concept_id="direwolf-beast",
                model_backend="hunyuan",
                export_format="glb",
                generate_pbr=False,
            )

            out = self.adapter.generate_3d_asset(req)

            self.assertIsInstance(out, EnhancedCreate3DAssetOutput)
            self.assertEqual(out.backend_used, "mock")
            self.assertEqual(out.metadata.get("connector"), "mock")
            self.assertEqual(out.metadata.get("mode"), "procedural")
            self.assertTrue(os.path.isfile(out.mesh_path))
            self.assertGreater(out.vertex_count, 0)

    def test_anycreature_failure_fallback(self):
        """Verify anyCreature connector failure falls back smoothly to procedural mock."""
        registry = ConnectorRegistry
        anycreature_conn = registry.get("anycreature")

        with patch.object(anycreature_conn, "execute", side_effect=RuntimeError("anyCreature DAG solver crash")):
            req = Create3DAssetInput(
                concept_id="winged-chimera",
                model_backend="anycreature",
                export_format="glb",
            )

            out = self.adapter.generate_3d_asset(req)

            self.assertIsInstance(out, EnhancedCreate3DAssetOutput)
            self.assertEqual(out.backend_used, "mock")
            self.assertEqual(out.metadata.get("connector"), "mock")
            self.assertEqual(out.metadata.get("mode"), "procedural")
            self.assertTrue(os.path.isfile(out.mesh_path))

    def test_meshanything_remote_failure_triggers_quadriflow_fallback(self):
        """Verify MeshAnything remote failure triggers Quadriflow fallback under 1600 face budget."""
        connector = MeshAnythingConnector()

        # Specify unreachable remote endpoint with valid timeout (>= 5.0)
        inp = MeshAnythingInput(
            input_mesh_path=self.sample_mesh_path,
            config=RetopologyConfig(
                target_face_count=1300,
                remote_endpoint="http://127.0.0.1:59997/unreachable_meshanything",
                timeout_seconds=5.0,
                enforce_pure_quad=True,
            ),
            output_dir=os.path.join(self.temp_dir, "retopo_out"),
            output_format="glb",
        )

        out = connector.execute(inp)

        self.assertIn("quadriflow", out.solver_used)
        self.assertTrue(os.path.isfile(out.optimized_mesh_path))
        self.assertGreater(os.path.getsize(out.optimized_mesh_path), 0)
        self.assertLessEqual(out.optimized_face_count, 1600)
        self.assertGreaterEqual(out.quad_ratio, 0.90)

    def test_meshanything_custom_fallback_handler(self):
        """Verify MeshAnything invokes registered custom fallback handler upon remote endpoint failure."""
        connector = MeshAnythingConnector()
        custom_called = False

        def custom_handler(inp, **kwargs):
            nonlocal custom_called
            custom_called = True
            from morphomesh.connectors.meshanything_connector import MeshAnythingOutput
            return MeshAnythingOutput(
                optimized_mesh_path=self.sample_mesh_path,
                original_face_count=10000,
                original_vertex_count=5000,
                optimized_face_count=1100,
                optimized_vertex_count=550,
                quad_ratio=0.96,
                reduction_ratio=0.11,
                solver_used="custom_decimate_fallback",
                duration_seconds=0.05,
            )

        connector.register_fallback(custom_handler)

        inp = MeshAnythingInput(
            input_mesh_path=self.sample_mesh_path,
            config=RetopologyConfig(
                target_face_count=1100,
                remote_endpoint="http://127.0.0.1:59997/fail_endpoint",
                timeout_seconds=5.0,
            ),
            output_dir=self.temp_dir,
        )

        out = connector.execute(inp)
        self.assertTrue(custom_called)
        self.assertEqual(out.solver_used, "custom_decimate_fallback")
        self.assertEqual(out.optimized_face_count, 1100)

    def test_adapter_optimize_topology_fallback_integration(self):
        """Verify InferenceAdapter.optimize_topology_with_connector executes fallback when connector fails."""
        # Intentionally break meshanything connector in registry
        registry = ConnectorRegistry
        meshanything_conn = registry.get("meshanything")

        with patch.object(meshanything_conn, "execute", side_effect=RuntimeError("MeshAnything OOM failure")):
            res = self.adapter.optimize_topology_with_connector(
                mesh_path=self.sample_mesh_path,
                method="meshanything_v2",
                target_faces=1450,
                output_dir=self.temp_dir,
            )

            self.assertIsInstance(res, dict)
            self.assertIn("optimized_mesh_path", res)
            self.assertTrue(os.path.isfile(res["optimized_mesh_path"]))
            self.assertLessEqual(res["optimized_face_count"], 1600)
            self.assertIn("fallback", res["solver_used"])

    def test_cloud_adapters_fallback_with_broken_token_or_cb(self):
        """Verify Replicate and Hugging Face adapters fall back cleanly to mock implementation."""
        # Replicate without token
        rep_adapter = ReplicateInferenceAdapter(api_token=None)
        c_req = GenerateConceptInput(prompt="frost wolf", creature_type="quadruped")
        c_res = rep_adapter.generate_concept(c_req)
        self.assertEqual(c_res.status, "mock_success")

        a_req = Create3DAssetInput(concept_id=c_res.concept_id, export_format="glb")
        a_res = rep_adapter.generate_3d_asset(a_req)
        self.assertTrue(os.path.isfile(a_res.mesh_path))

        # HuggingFace with breaker tripped to OPEN
        hf_adapter = HuggingFaceInferenceAdapter(api_token="dummy_token")
        for _ in range(hf_adapter.circuit_breaker.failure_threshold):
            hf_adapter.circuit_breaker.record_failure()
        self.assertEqual(hf_adapter.circuit_breaker.state, "OPEN")
        self.assertFalse(hf_adapter.circuit_breaker.can_attempt())

        hf_c_res = hf_adapter.generate_concept(c_req)
        self.assertEqual(hf_c_res.status, "mock_success")

        hf_a_res = hf_adapter.generate_3d_asset(a_req)
        self.assertTrue(os.path.isfile(hf_a_res.mesh_path))


if __name__ == "__main__":
    unittest.main()
