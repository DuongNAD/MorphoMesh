"""
Pytest Test Infrastructure Configuration for Vegetation Library.
Target File: teamwork_projects/vegetation_library/tests/conftest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure teamwork_projects/vegetation_library is in sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_DIR.parent.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
