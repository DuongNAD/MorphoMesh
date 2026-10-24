import re

with open('src/morphomesh/human_rigging.py', 'r', encoding='utf-8') as f:
    content = f.read()

lm_keys = set(re.findall(r'landmarks\[["\']([^"\']+)["\']\]', content))
lm_get_keys = set(re.findall(r'landmarks\.get\(["\']([^"\']+)["\']', content))
lm_in_keys = set(re.findall(r'["\']([^"\']+)["\'] in landmarks', content))
all_rigging_keys = sorted(lm_keys | lm_get_keys | lm_in_keys)

print(f"Total landmark keys queried in human_rigging.py: {len(all_rigging_keys)}")
for k in all_rigging_keys:
    print("  ", k)

with open('src/morphomesh/human_generator.py', 'r', encoding='utf-8') as f:
    gen_content = f.read()

gen_lm_keys = set(re.findall(r'landmarks\[["\']([^"\']+)["\']\]', gen_content))
gen_keys_quoted = set(re.findall(r'["\']([a-zA-Z0-9_]+)[\'"]:\s*\([^)]+\)', gen_content))
print(f"\nSample keys from human_generator.py: {len(gen_keys_quoted)}")
