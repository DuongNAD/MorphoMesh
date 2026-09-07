import sys
import subprocess
import tempfile
import json
import os

sys.path.insert(0, "src")
from morphomesh.blender_bridge import BlenderBridge

bb = BlenderBridge()
script = bb._generate_headless_script("morphomesh.create_human_asset", {"character_name": "TestFix"})

# Replace the serialization line in the generated script to test root cause
fixed_script = script.replace(
    'landmarks = dict(obj.get("morphomesh_landmarks", {}))',
    'landmarks = {k: list(v) for k, v in dict(obj.get("morphomesh_landmarks", {})).items()}'
)

with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
    f.write(fixed_script)
    tmp_path = f.name

try:
    proc = subprocess.run(
        [r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe", "--background", "--factory-startup", "--python", tmp_path],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print("Return code:", proc.returncode)
    print("STDOUT:")
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:")
        print(proc.stderr)
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
