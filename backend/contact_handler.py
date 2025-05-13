import requests
import os

def handle_contact_submission(data):
    required_fields = ["first_name", "last_name", "email", "message"]

    # Validate fields
    for field in required_fields:
        if field not in data or not data[field].strip():
            return {"status": "error", "message": f"{field} is missing or empty."}

    if len(data["message"].strip()) < 50:
        return {"status": "error", "message": "Message must be at least 50 characters."}

    # Forward to external webhook
    webhook_url = os.environ.get("CONTACT_WEBHOOK_URL") # Dummy webhook
    if not webhook_url:
        return {"status": "error", "message": "Webhook URL not configured."}

    try:
        response = requests.post(webhook_url, json=data)
        if response.status_code == 200:
            return {"status": "success"}
        else:
            return {"status": "error", "message": f"Webhook returned status {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
