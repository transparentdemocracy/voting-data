"""
Use this tiny script to base64 encode our Google Drive service account credentials json file content into the
environment variables in PyCharm's run configurations.
See the explanation about this environment variable in code comment in config.py.
"""
import json

SECRETS_JSON_ABS_PATH = '/Users/sandervandenhautte/Downloads/wddp-storage-service-account-credentials.json'
with open(SECRETS_JSON_ABS_PATH, 'r', encoding='utf-8') as secrets_json_file:
    secrets_json_str = json.loads(secrets_json_file.read())
escaped = json.dumps(secrets_json_str).replace('"', '\\"')
print(escaped)
