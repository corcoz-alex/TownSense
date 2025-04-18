import smtplib
import os
from email.message import EmailMessage

SENDER_MAIL = os.environ.get("EMAIL_ADDRESS")
SENDER_PASS = os.environ.get("EMAIL_PASSWORD")

def send_email(location, details, image_bytes, image_name, image_type):
    try:
        receiver_email = "alexcorcoz11@gmail.com"

        msg = EmailMessage()
        msg["Subject"] = f"New Urban Issue Report - {location}"
        msg["From"] = SENDER_MAIL
        msg["To"] = receiver_email

        msg.set_content(f"""
New problem reported via TownSense 🏙️

Location: {location}
Details:
{details}

Image attached.
""")

        # Attach image
        msg.add_attachment(
            image_bytes,
            maintype="image",
            subtype=image_type.split("/")[-1],
            filename=image_name
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_MAIL, SENDER_PASS)
            smtp.send_message(msg)

        return {"status": "success"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
