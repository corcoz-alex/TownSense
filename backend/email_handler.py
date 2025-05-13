import os
from email.message import EmailMessage
import smtplib
from dotenv import load_dotenv
import time

load_dotenv()

SENDER_MAIL = os.environ.get("EMAIL_ADDRESS")
SENDER_PASS = os.environ.get("EMAIL_PASSWORD")

def send_email(location, details, image_bytes, image_name, image_type):
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            msg = EmailMessage()
            msg["Subject"] = f"New Urban Issue Report - {location}"
            msg["From"] = SENDER_MAIL
            msg["To"] = "alexcorcoz11@gmail.com" # My personal email, replace this with the user email

            msg.set_content(f"""
            New problem reported via TownSense 🏙️

            Location: {location}
            Details:
            {details}

            Image attached.
            """)

            msg.add_attachment(
                image_bytes,
                maintype="image",
                subtype=image_type.split("/")[-1],
                filename=image_name
            )

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
                smtp.login(SENDER_MAIL, SENDER_PASS)
                smtp.send_message(msg)

            return {"status": "success"}

        except smtplib.SMTPException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("EMAIL ERROR:", str(e))
                return {"status": "error", "message": str(e)}
