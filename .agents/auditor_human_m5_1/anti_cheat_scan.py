"""
Anti-cheat forensic scanner for MorphoMesh repository.
"""
import os
import re
import ast

SUSPICIOUS_PATTERNS = [
    (r"def\s+[a-zA-Z0-9_]+\([^)]*\):\s*(?:pass|\.\.\.|return\s+(?:True|False|None|\"\"\s*|0|\{\}))\s*$", "Trivial/Empty function body"),
    (r"assert\s+(?:True|1\s*==\s*1|True\s*is\s*True)\b", "Trivial assertion assert True"),
    (r"mock|unittest\.mock|MagicMock|patch", "Mocking usage in production export tests"),
    (r"pytest\.skip\([^)]*\)", "Explicit test skips"),
    (r"raise\s+NotImplementedError", "Unimplemented placeholders"),
]

print("=== ANTI-CHEAT SCAN IN tests/test_production_exports.py ===")
target_test = "tests/test_production_exports.py"
with open(target_test, "r", encoding="utf-8") as f:
    test_content = f.read()

for pat, desc in SUSPICIOUS_PATTERNS:
    matches = list(re.finditer(pat, test_content, re.MULTILINE))
    print(f"Pattern '{desc}': {len(matches)} occurrences")
    for m in matches:
        line_no = test_content[:m.start()].count("\n") + 1
        print(f"  Line {line_no}: {m.group(0)}")

print("\n=== ANTI-CHEAT SCAN IN src/morphomesh/character_assembler.py (Export sections) ===")
with open("src/morphomesh/character_assembler.py", "r", encoding="utf-8") as f:
    asm_content = f.read()

# Check lines after 1550 (export logic)
lines = asm_content.split("\n")
export_lines = "\n".join(lines[1550:])
for pat, desc in SUSPICIOUS_PATTERNS:
    matches = list(re.finditer(pat, export_lines, re.MULTILINE))
    print(f"Pattern '{desc}': {len(matches)} occurrences")
    for m in matches:
        line_no = 1550 + export_lines[:m.start()].count("\n") + 1
        print(f"  Line {line_no}: {m.group(0)}")

print("\n=== AST ANALYSIS OF tests/test_production_exports.py ===")
parsed = ast.parse(test_content)
classes = [n for n in parsed.body if isinstance(n, ast.ClassDef)]
test_methods = []
for c in classes:
    for item in c.body:
        if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
            test_methods.append((c.name, item.name, len(item.body)))

print(f"Total test classes: {len(classes)}")
print(f"Total test methods: {len(test_methods)}")
for cname, mname, stmts in test_methods:
    if stmts <= 1:
        print(f"WARNING: Ultra-short test method: {cname}.{mname} with {stmts} statements")

print("AST Analysis Complete.")
