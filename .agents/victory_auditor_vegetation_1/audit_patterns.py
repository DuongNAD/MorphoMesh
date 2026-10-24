import os
import re
from pathlib import Path

root = Path(rE:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library)
py_files = list(root.glob(**/*.py))

print(fTotal python files found: {len(py_files)})
findings = []

patterns = [
    (re.compile(rdef\s+\w+\([^)]*\):\s*return\s+(True|False|\d+|None|'[^']+'|"[^"]+")\s*$, re.IGNORECASE), empty_return),
    (re.compile(r\b(mock|fake|bypass|skip_validation|hardcode)\b, re.IGNORECASE), suspicious_term),
]

for p in py_files:
    rel = p.relative_to(root)
    with open(p, r, encoding=utf-8, errors=ignore) as f:
        lines = f.readlines()
    for idx, line in enumerate(lines):
        line_s = line.strip()
        if line_s.startswith(#):
            continue
        for pat, tag in patterns:
            if pat.search(line_s):
                findings.append((str(rel), idx + 1, line_s, tag))

print(fTotal matching occurrences: {len(findings)})
for rel, line_no, line_s, tag in findings:
    print(f{rel}:{line_no} [{tag}] -> {line_s[:100]})