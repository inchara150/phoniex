import hmac
import hashlib
import json
import requests

# Test settings
URL = "http://127.0.0.1:8000/api/v1/github/webhook"
SECRET = "mock-secret"

payload = {
    "action": "completed",
    "check_run": {
        "status": "completed",
        "conclusion": "failure",
        "name": "pytest / build"
    },
    "mock_trace": "Traceback (most recent call last):\n  File \"app.py\", line 6, in get_user_config\n    return settings[key]\nKeyError: 'database_url'"
}
payload_bytes = json.dumps(payload).encode("utf-8")

# Generate signature
hash_object = hmac.new(SECRET.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
signature = "sha256=" + hash_object.hexdigest()

headers = {
    "X-GitHub-Event": "check_run",
    "X-Hub-Signature-256": signature,
    "Content-Type": "application/json"
}

print(f"Sending webhook with signature {signature}...")
response = requests.post(URL, data=payload_bytes, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
