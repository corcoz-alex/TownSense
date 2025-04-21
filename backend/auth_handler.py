import bcrypt
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from db import users_collection
import random

# --- Registration ---
def register_user(email, username, password):
    if users_collection.find_one({"$or": [{"email": email}, {"username": username}]}):
        return {"status": "error", "message": "Email or username already exists."}

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = {
        "email": email,
        "username": username,
        "password": hashed_pw,
        "reports": []
    }
    users_collection.insert_one(user)
    return {"status": "success", "message": "User registered successfully."}

# --- Login ---
def login_user(username_or_email, password):
    user = users_collection.find_one({
        "$or": [
            {"email": username_or_email},
            {"username": username_or_email}
        ]
    })

    if not user:
        return {"status": "error", "message": "User not found."}

    if not bcrypt.checkpw(password.encode(), user['password'].encode()):
        return {"status": "error", "message": "Incorrect password."}

    return {"status": "success", "user_id": str(user['_id']), "username": user['username']}

# --- Request Password Reset Code ---
def request_password_reset_code(email):
    user = users_collection.find_one({"email": email})
    if not user:
        return {"status": "error", "message": "Email not found."}

    code = str(random.randint(100000, 999999))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_code": code,
            "reset_expiry": expiry.isoformat()
        }}
    )

    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_code": code,
            "reset_expiry": expiry.isoformat()
        }}
    )

# Send email
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_pass = os.getenv("EMAIL_PASSWORD")
        msg = EmailMessage()
        msg["Subject"] = "Your TownSense Password Reset Code"
        msg["From"] = sender_email
        msg["To"] = email
        msg.set_content(f"""
Someone requested a password reset for your TownSense account.

Your reset code is: {code}

This code will expire in 10 minutes. If you did not request a reset, you can ignore this email.
""")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, sender_pass)
            smtp.send_message(msg)

        return {"status": "success", "message": "Reset code sent to email."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}

# --- Verify Code and Reset Password ---
def verify_reset_code_and_update_password(email, code, new_password):
    user = users_collection.find_one({"email": email})
    if not user or "reset_code" not in user or "reset_expiry" not in user:
        return {"status": "error", "message": "Reset code not found or already used."}

    if user["reset_code"] != code:
        return {"status": "error", "message": "Invalid reset code."}

    if datetime.now(timezone.utc) > datetime.fromisoformat(user["reset_expiry"]):
        return {"status": "error", "message": "Reset code has expired."}

    hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hashed_pw}, "$unset": {"reset_code": "", "reset_expiry": ""}}
    )
    return {"status": "success", "message": "Password reset successfully."}
