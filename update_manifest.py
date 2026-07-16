import json
import hashlib
from pathlib import Path

manifest_path = Path(r"C:\Users\yangnianyong\.gemini\config\skills\.datacloud_skills_manifest")
skill_file = Path(r"C:\Users\yangnianyong\.gemini\config\skills\doc-sync\SKILL.md")

with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

with open(skill_file, 'rb') as f:
    checksum = hashlib.sha256(f.read()).hexdigest()

manifest['skills']['doc-sync'] = {
    'status': 'installed',
    'checksum': checksum
}

with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

print("Manifest updated successfully.")
