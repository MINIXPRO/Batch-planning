import json

filepath = "/home/shivam/frappe-bench/frappe-bench/apps/custom_batch_planning/custom_batch_planning/fixtures/custom_field.json"

with open(filepath, 'r') as f:
    data = json.load(f)

doctypes_to_check = [
    "Material Request", "Material Request Item",
    "Purchase Order", "Purchase Order Item",
    "Purchase Receipt", "Purchase Receipt Item",
    "Purchase Invoice", "Purchase Invoice Item",
    "Stock Entry", "Stock Entry Detail"
]

options_to_remove = ["Batches Planned"]

new_data = []
removed_fields = []

for d in data:
    if d.get('dt') in doctypes_to_check and d.get('options') in options_to_remove:
        removed_fields.append(f"{d.get('dt')} - {d.get('fieldname')} (Options: {d.get('options')})")
    else:
        new_data.append(d)

print("Removed fields:")
for f in removed_fields:
    print(f)

with open(filepath, 'w') as f:
    json.dump(new_data, f, indent=1)

print("Updated custom_field.json successfully.")
