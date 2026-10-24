"""
Extract and decompose wardrobe.py into src/morphomesh/wardrobe/ sub-package.
"""

import ast

source_path = "src/morphomesh/wardrobe.py"
with open(source_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

content = "".join(lines)
tree = ast.parse(content)

print(f"Total lines in wardrobe.py: {len(lines)}")
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        print(f"{type(node).__name__}: {node.name} (lines {node.lineno} to {node.end_lineno})")
    elif isinstance(node, ast.Assign):
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if targets:
            print(f"Assign: {', '.join(targets)} (lines {node.lineno} to {node.end_lineno})")
