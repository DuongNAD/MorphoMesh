"""
Chaos Test Suite 3: FastMCP Tool Invariance & Concurrency Harness
MorphoMesh Phase 2: Resilience & Chaos Challenger
"""

import asyncio
import os
import shutil
import tempfile
import unittest
from mcp.server.fastmcp.exceptions import ToolError
from morphomesh.server import (
    mcp,
    morphomesh_create_3d_asset,
    morphomesh_generate_concept,
    morphomesh_optimize_topology,
)


class TestFastMCPConcurrency(unittest.IsolatedAsyncioTestCase):
    """Empirical verification of FastMCP server concurrency and tool invariance."""

    EXPECTED_TOOL_NAMES = {
        "morphomesh_generate_concept",
        "morphomesh_create_3d_asset",
        "morphomesh_optimize_topology",
        "morphomesh_auto_rig",
        "morphomesh_blender_execute",
        "morphomesh_get_scene_status",
        "morphomesh_render_preview",
    }

    async def asyncSetUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="morphomesh_mcp_chaos_")
        os.environ["MORPHOMESH_STORAGE_DIR"] = self.temp_dir

    async def asyncTearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_concurrent_tool_list_invariance(self):
        """Verify that mcp.list_tools() returns invariant 7 tools under heavy concurrent querying and execution."""
        query_count = 50
        results = []

        async def query_tools(idx: int):
            tools = await mcp.list_tools()
            return idx, tools

        async def background_tool_execution(idx: int):
            # Run background tool executions simultaneously
            res = await morphomesh_generate_concept(
                prompt=f"concept_stress_{idx}",
                seed=100 + idx,
                width=512,
                height=512,
            )
            return res

        # Run 50 tool listings and 10 background executions concurrently
        listing_tasks = [query_tools(i) for i in range(query_count)]
        exec_tasks = [background_tool_execution(i) for i in range(10)]

        all_results = await asyncio.gather(*listing_tasks, *exec_tasks)
        listing_results = all_results[:query_count]

        self.assertEqual(len(listing_results), query_count)

        for idx, tools in listing_results:
            self.assertEqual(
                len(tools),
                7,
                f"Iteration {idx} saw unexpected tool count: {len(tools)}",
            )
            tool_names = {t.name for t in tools}
            self.assertEqual(
                tool_names,
                self.EXPECTED_TOOL_NAMES,
                f"Iteration {idx} tool names diverged: {tool_names}",
            )
            # Verify tool properties are non-empty strings
            for t in tools:
                self.assertTrue(t.name)
                self.assertTrue(t.description)

    async def test_concurrent_mixed_tool_calls(self):
        """Verify server handles concurrent mixed tool invocations without cross-talk or race conditions."""
        concurrent_calls = 16

        async def worker(idx: int):
            # 1. Generate concept
            c_res = await morphomesh_generate_concept(
                prompt=f"quadruped creature {idx}",
                creature_type="quadruped",
                seed=42 + idx,
                width=512,
                height=512,
            )
            concept_id = c_res["concept_id"]

            # 2. Interleaved list_tools inspection
            tools = await mcp.list_tools()
            assert len(tools) == 7

            # 3. Create 3D asset from concept
            a_res = await morphomesh_create_3d_asset(
                concept_id=concept_id,
                model_backend="mock",
                export_format="glb",
                generate_pbr=False,
            )
            assert os.path.isfile(a_res["mesh_path"])

            # 4. Optimize topology
            o_res = await morphomesh_optimize_topology(
                input_mesh_path=a_res["mesh_path"],
                target_poly_count=1200,
                method="meshanything_v2",
            )
            assert o_res["optimized_face_count"] <= 1600
            return {
                "idx": idx,
                "concept_id": concept_id,
                "asset_id": a_res["asset_id"],
                "retopo_mesh": o_res["output_mesh_path"],
            }

        tasks = [worker(i) for i in range(concurrent_calls)]
        outputs = await asyncio.gather(*tasks)

        self.assertEqual(len(outputs), concurrent_calls)
        # Verify uniqueness of generated asset IDs across concurrent workers
        asset_ids = [o["asset_id"] for o in outputs]
        self.assertEqual(len(asset_ids), len(set(asset_ids)), "Asset IDs collided under concurrency!")

    async def test_concurrent_error_isolation(self):
        """Verify faulty invocations raise ToolError without crashing server or corrupting concurrent valid tasks."""
        async def valid_call(idx: int):
            return await morphomesh_generate_concept(
                prompt=f"valid prompt {idx}",
                seed=10,
                width=512,
                height=512,
            )

        async def invalid_call(idx: int):
            try:
                # Missing both image_path and concept_id triggers ToolError
                await morphomesh_create_3d_asset()
                return "unexpected_success"
            except ToolError as te:
                return f"caught_tool_error: {te}"

        tasks = []
        for i in range(15):
            tasks.append(valid_call(i))
            tasks.append(invalid_call(i))

        results = await asyncio.gather(*tasks)
        self.assertEqual(len(results), 30)

        # Check that valid calls produced concepts and invalid calls raised ToolError cleanly
        for i in range(15):
            valid_res = results[2 * i]
            invalid_res = results[2 * i + 1]
            self.assertIn("concept_id", valid_res)
            self.assertTrue(invalid_res.startswith("caught_tool_error"))


if __name__ == "__main__":
    unittest.main()
