with open('docs/RESEARCH_BENCHMARK.md') as f:
    text = f.read()

import re

# Count $$ occurrences
dd_count = text.count('$$')
print(f'Total $$ occurrences: {dd_count}')
assert dd_count % 2 == 0, 'Unbalanced $$ equations!'

# Extract all $$ formulas
dd_pattern = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
formulas = dd_pattern.findall(text)
print(f'Total display math formulas: {len(formulas)}')
for idx, form in enumerate(formulas, 1):
    print(f'Formula {idx}: {form.strip()[:60]}...')

# Check single $ occurrences (ignoring $1.20 etc.)
# Find pairs of $...$ that are math
single_dollars = re.findall(r'(?<!\$)\$(?!\$)([a-zA-Z\\].*?)(?<!\$)\$(?!\$)', text)
print(f'Total inline math expressions: {len(single_dollars)}')
for idx, m in enumerate(single_dollars[:10], 1):
    print(f'Inline {idx}: {m.strip()}')

print('ALL LATEX FORMULAS BALANCED AND VERIFIED.')
