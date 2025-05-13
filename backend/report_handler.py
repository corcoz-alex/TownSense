from PIL import Image
import io
import base64
from db import reports_collection, all_reports_collection
from datetime import datetime, timezone

def resize_image(image_bytes, max_width=640):
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert RGBA to RGB if needed (JPEG doesn't support alpha channel)
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            # Resize image while maintaining aspect ratio
            if img.width > max_width:
                new_height = int((max_width / img.width) * img.height)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=90, optimize=True)
            return buffer.getvalue()
    except Exception as e:
        print(f"Error resizing image: {e}")
        return image_bytes  # Return original if resize fails

def save_user_report(username, location, details, image_bytes):
    try:
        compressed_image = resize_image(image_bytes)  # resize to reduce payload
        encoded_image = base64.b64encode(compressed_image).decode("utf-8")

        # Create report document
        report_doc = {
            "username": username,
            "location": location,
            "details": details,
            "image": encoded_image,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "visible": True  # Flag to track if report is visible to the user
        }

        # Save to both collections
        reports_collection.insert_one(report_doc)
        all_reports_collection.insert_one(report_doc)

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_reports_by_username(username):
    try:
        # Only return reports marked as visible
        results = list(reports_collection.find(
            {"username": username, "visible": True}
        ).sort("timestamp", -1))

        for r in results:
            r["_id"] = str(r["_id"])  # Convert ObjectId to string
        return {"status": "success", "reports": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_all_reports(admin_key=None, username=None, date_from=None, date_to=None):
    """
    Admin function to get all reports, including hidden ones
    Can filter by username and date range
    Requires admin key for security
    """
    try:
        # Simple security check
        if admin_key != "ADMIN_SECRET_KEY":  # Replace with actual secure method
            return {"status": "error", "message": "Unauthorized access"}

        # Build query
        query = {}
        if username:
            query["username"] = username

        # Date filtering
        if date_from or date_to:
            query["timestamp"] = {}
            if date_from:
                query["timestamp"]["$gte"] = date_from
            if date_to:
                query["timestamp"]["$lte"] = date_to

        results = list(all_reports_collection.find(query).sort("timestamp", -1))
        for r in results:
            r["_id"] = str(r["_id"])

        return {"status": "success", "reports": results, "total": len(results)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
