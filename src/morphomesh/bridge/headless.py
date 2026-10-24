"""
MorphoMesh: Blender Headless CLI Runner.

Provides binary resolution and subprocess execution of standalone Python scripts
inside Blender in background mode, extracting structured JSON payloads
delimited by sentinel tokens.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional

from morphomesh.bridge.constants import SENTINEL_END, SENTINEL_START
from morphomesh.bridge.validator import BlenderExecutionError
from morphomesh.models import MorphoMeshException

logger = logging.getLogger("morphomesh.bridge.headless")


def resolve_blender_binary(explicit_path: Optional[str] = None) -> Optional[str]:
    """Auto-detect Blender executable on macOS / Linux / Windows."""
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = [
        explicit_path,
        os.environ.get("BLENDER_BIN_PATH"),
        os.environ.get("BLENDER_PATH"),
        os.path.join(prog_files, "Blender Foundation", "Blender 4.5", "blender.exe"),
        os.path.join(prog_files, "Blender Foundation", "Blender 5.2", "blender.exe"),
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/Applications/Blender 5.2.app/Contents/MacOS/Blender",
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        shutil.which("blender"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            if os.name == "nt" or os.access(path, os.X_OK):
                return path
    return None


def run_headless_script(
    blender_bin_path: Optional[str],
    script_content: str,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """
    Execute standalone Python script inside Blender headless mode
    and extract structured response from sentinel tokens.
    """
    if not blender_bin_path:
        raise MorphoMeshException(
            code="ERR_BLENDER_UNAVAILABLE",
            message=(
                "Blender binary not found. Set BLENDER_BIN_PATH or install Blender at "
                "/Applications/Blender.app/Contents/MacOS/Blender"
            ),
        )

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        # Scrub API tokens from child environment
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if not k.endswith("_KEY") and not k.endswith("_TOKEN")
        }
        repo_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        clean_env["PYTHONPATH"] = f"{repo_src};{clean_env.get('PYTHONPATH', '')}" if os.name == "nt" else f"{repo_src}:{clean_env.get('PYTHONPATH', '')}"

        cmd = [
            blender_bin_path,
            "--background",
            "--factory-startup",
            "--python",
            script_path,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=clean_env,
        )

        stdout = proc.stdout
        stderr = proc.stderr

        pattern = re.compile(
            rf"{re.escape(SENTINEL_START)}\s*({{.*?}})\s*{re.escape(SENTINEL_END)}",
            re.DOTALL,
        )
        match = pattern.search(stdout)
        if match:
            try:
                result_data = json.loads(match.group(1))
                if result_data.get("status") == "error":
                    raise BlenderExecutionError(
                        result_data.get("message", "Unknown headless script error"),
                        details=result_data,
                    )
                return result_data
            except json.JSONDecodeError as e:
                raise BlenderExecutionError(
                    f"Failed to parse sentinel JSON: {e}\nRaw stdout:\n{stdout}"
                )

        if proc.returncode != 0:
            raise BlenderExecutionError(
                f"Headless Blender process exited with code {proc.returncode}.\nStderr: {stderr}\nStdout: {stdout}"
            )

        raise BlenderExecutionError(
            f"Sentinel JSON not found in Blender output.\nStdout: {stdout}\nStderr: {stderr}"
        )

    except subprocess.TimeoutExpired:
        raise MorphoMeshException(
            code="ERR_SCRIPT_EXECUTION_TIMEOUT",
            message=f"Headless Blender process exceeded timeout of {timeout_seconds}s.",
        )
    finally:
        if os.path.exists(script_path):
            try:
                os.remove(script_path)
            except OSError:
                pass


__all__ = [
    "resolve_blender_binary",
    "run_headless_script",
]
