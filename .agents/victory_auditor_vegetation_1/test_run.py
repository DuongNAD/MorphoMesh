import os, re, sys
from pathlib import Path
root = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library")
py_files = list(root.glob("**/*.py"))
print(f"Total python files found: {len(py_files)}")
