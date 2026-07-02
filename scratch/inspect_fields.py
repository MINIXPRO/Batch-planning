import json
import subprocess

original_json_str = subprocess.check_output(['git', 'show', 'HEAD:custom_batch_planning/fixtures/custom_field.json'], cwd='/home/shivam/frappe-bench/frappe-bench/apps/custom_batch_planning').decode('utf-8')
data = json.loads(original_json_str)

removed = []
kept = []

doctypes_to_check = [
    "Material Request", "Material Request Item",
    "Purchase Order", "Purchase Order Item",
    "Purchase Receipt", "Purchase Receipt Item",
    "Purchase Invoice", "Purchase Invoice Item",
    "Stock Entry", "Stock Entry Detail"
]

for d in data:
    if d.get('dt') in doctypes_to_check:
        if d.get('options') == "Batches Planned":
            removed.append(d)
        elif d.get('options') == "Batch Planning":
            kept.append(d)

print("=== REMOVED BLOCKS ===")
for r in removed:
    print(json.dumps(r, indent=2))
    print("----------------------")

print("\n=== KEPT FIELDS (Options: Batch Planning) ===")
for k in kept:
    print(f"{k.get('dt')} -> {k.get('fieldname')} (Options: {k.get('options')})")
