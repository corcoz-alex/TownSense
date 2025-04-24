from PIL import Image
import io
import base64
from db import reports_collection
from datetime import datetime, timezone

def resize_image(image_bytes, max_width=640):
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Resize image while maintaining aspect ratio
        if img.width > max_width:
            new_height = int((max_width / img.width) * img.height)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

def save_user_report(username, location, details, image_bytes):
    try:
        compressed_image = resize_image(image_bytes)  # resize to reduce payload
        encoded_image = base64.b64encode(compressed_image).decode("utf-8")
        reports_collection.insert_one({
            "username": username,
            "location": location,
            "details": details,
            "image": encoded_image,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_reports_by_username(username):
    try:
        results = list(reports_collection.find({"username": username}).sort("timestamp", -1))
        for r in results:
            r["_id"] = str(r["_id"])  # Convert ObjectId to string
        return {"status": "success", "reports": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}
