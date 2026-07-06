import json

file_path = '/home/shivam/frappe-bench/frappe-bench/apps/lms/lms/fixtures/custom_field.json'

with open(file_path, 'r') as f:
    data = json.load(f)

new_data = []
removed_fields = []

for d in data:
    if d.get('options') == 'Batches Planned':
        removed_fields.append((d.get('dt'), d.get('fieldname')))
    else:
        new_data.append(d)

with open(file_path, 'w') as f:
    json.dump(new_data, f, indent=1)

print('Removed:', removed_fields)
