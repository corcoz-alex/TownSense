from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import jwt
import os
import datetime
import logging
import base64
import numpy as np
import json
from dotenv import load_dotenv
from email_handler import send_email
from ultralytics import YOLO
from contact_handler import handle_contact_submission
from report_handler import get_reports_by_username
from visuals import draw_custom_boxes
from db import users_collection
from report_handler import save_user_report
from auth_handler import (
    register_user,
    login_user,
    request_password_reset_code,
    verify_reset_code_and_update_password,
)

# Import the GitHub AI client
from github_ai import GitHubAIClient

load_dotenv()

print("✅ Flask app starting...")
print("MONGO URI:", os.getenv("COSMOSDB_URI"))
print("JWT Secret:", os.getenv("JWT_SECRET"))

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", 60))

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymongo").setLevel(logging.ERROR)  # Disable Mongo spam

# Load multiple YOLO models
models = {
#    "cigarettes": YOLO("models/roboflow_cig.pt"),
    "potholes": YOLO("backend/models/roboflow_potholes.pt"),
#    "waste": YOLO("models/waste.pt"),
    "garbage_detection": YOLO("backend/models/garbage_detector.pt"),
}

# Warm up models once on startup
dummy_image = Image.new("RGB", (640, 416))
try:
    for name, model in models.items():
        model(dummy_image)
        app.logger.info(f"Warmed up model: {name}")
except Exception as e:
    app.logger.exception("Error during model warmup")

# Add a simple health check endpoint
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Backend server is running"})

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            app.logger.error("No image file provided in the request.")
            return jsonify({"error": "No image file provided."}), 400

        file = request.files['image']
        if file.filename == '':
            app.logger.error("Empty filename received.")
            return jsonify({"error": "Empty filename."}), 400

        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        annotated = np.array(image)  # Convert to NumPy for OpenCV

        combined_results = {}

        for model_name, model in models.items():
            results = model(image)
            objects = []

            for result in results:
                draw_custom_boxes(annotated, result, model_name)

                boxes = result.boxes.xyxy.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy()

                for box, confidence, cls in zip(boxes, confidences, classes):
                    objects.append({
                        "name": result.names[int(cls)],
                        "confidence": round(float(confidence), 3),
                        "bbox": [round(coord, 2) for coord in box.tolist()]
                    })

            combined_results[model_name] = objects

        # Encode final image with all annotations
        annotated_image = Image.fromarray(annotated)
        buffered = io.BytesIO()
        annotated_image.save(buffered, format="PNG")
        encoded_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return jsonify({
            "detected_objects": combined_results,
            "image": encoded_image
        })

    except Exception as e:
        app.logger.exception("Detection failed")
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500

@app.route("/send_email", methods=["POST"])
def handle_send_email():
    try:
        data = request.form
        location = data.get("location")
        details = data.get("details")
        username = data.get("username")  # <- NEW!
        file = request.files.get("image")

        if not all([location, details, file, username]):
            return jsonify({"status": "error", "message": "Missing data"}), 400

        # Save to DB
        save_result = save_user_report(username, location, details, file.read())
        if save_result["status"] != "success":
            return jsonify(save_result), 500

        file.stream.seek(0)
        result = send_email(location, details, file.read(), file.filename, file.content_type)
        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/contact", methods=["POST"])
def contact():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        result = handle_contact_submission(data)
        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# JWT helper
def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=JWT_EXPIRY_MINUTES)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    result = register_user(email, username, password)
    return jsonify(result)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username_or_email = data.get("username_or_email")
    password = data.get("password")

    result = login_user(username_or_email, password)
    if result["status"] == "success":
        token = generate_token(result["user_id"])
        return jsonify({
            "status": "success",
            "token": token,
            "username": result["username"],
            "bio": result.get("bio", ""),  # ✅ include bio
            "profile_picture": result.get("profile_picture", "")  # ✅ include profile_picture
        })
    return jsonify(result)

@app.route("/request-reset-code", methods=["POST"])
def request_reset_code():
    data = request.json
    email = data.get("email")
    result = request_password_reset_code(email)
    return jsonify(result)

@app.route("/reset-password", methods=["POST"])
def reset_password_route():
    data = request.json
    email = data.get("email")
    code = data.get("code")
    new_password = data.get("new_password")
    result = verify_reset_code_and_update_password(email, code, new_password)
    return jsonify(result)

@app.route("/update_profile", methods=["POST"])
def update_profile():
    try:
        data = request.json

        old_username = data.get("username")  # CURRENT username (before change)
        new_display_name = data.get("new_display_name")
        bio = data.get("bio")
        profile_picture = data.get("profile_picture")

        if not old_username:
            return jsonify({"status": "error", "message": "Missing username."}), 400

        update_fields = {}

        if new_display_name and new_display_name.strip() != old_username:
            # Check if new username already exists
            if users_collection.find_one({"username": new_display_name.strip()}):
                return jsonify({"status": "error", "message": "Username already taken."}), 400
            update_fields["username"] = new_display_name.strip()

        if bio is not None:
            update_fields["bio"] = bio.strip()

        if profile_picture:
            update_fields["profile_picture"] = profile_picture

        if not update_fields:
            return jsonify({"status": "error", "message": "No changes to update."}), 400

        # search by old_username, update new fields
        result = users_collection.update_one(
            {"username": old_username},
            {"$set": update_fields}
        )

        if result.modified_count > 0:
            return jsonify({"status": "success", "message": "Profile updated."})
        else:
            return jsonify({"status": "error", "message": "Profile update failed."}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_reports", methods=["POST"])
def get_reports():
    try:
        data = request.json
        username = data.get("username")
        if not username:
            return jsonify({"status": "error", "message": "Missing username"}), 400

        result = get_reports_by_username(username)
        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/clear_reports", methods=["POST"])
def clear_reports():
    try:
        data = request.json
        username = data.get("username")
        if not username:
            return jsonify({"status": "error", "message": "Missing username"}), 400

        from db import reports_collection
        result = reports_collection.delete_many({"username": username})
        return jsonify({"status": "success", "deleted": result.deleted_count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/evaluate", methods=["POST"])
def evaluate_image():
    try:
        data = request.get_json()
        detections = data.get("detections")
        base64_image = data.get("image")  # Get the base64 image from the request

        if not detections:
            return jsonify({"status": "error", "message": "Missing detection results"}), 400
            
        # Try using GitHub AI first for comprehensive analysis
        try:
            github_ai = GitHubAIClient()
            result = github_ai.generate_interpretation(detections, base64_image)
            
            if result["status"] == "success":
                return jsonify({
                    "status": "success",
                    "evaluation": result["evaluation"]
                })
            else:
                app.logger.warning(f"GitHub AI failed: {result.get('message')}. Using fallback analysis.")
        except Exception as e:
            app.logger.exception(f"Error using GitHub AI: {str(e)}. Using fallback analysis.")

        # Fallback to local analysis if GitHub AI fails
        analysis = analyze_urban_issues(detections)
        
        return jsonify({
            "status": "success",
            "evaluation": analysis,
            "note": "This analysis was generated using a local fallback system as the advanced AI analysis service was unavailable."
        })

    except Exception as e:
        app.logger.exception("Evaluation failed")
        return jsonify({
            "status": "error",
            "message": f"Evaluation failed: {str(e)}"
        }), 500

def analyze_urban_issues(detections):
    """Generate an analysis of detected urban issues without external API calls"""

    problems_found = []
    recommendations = []

    # Check for garbage/waste issues
    garbage_objects = detections.get("garbage_detection", [])
    if garbage_objects:
        garbage_count = len(garbage_objects)
        confidence_sum = sum(obj['confidence'] for obj in garbage_objects)
        avg_confidence = confidence_sum / garbage_count if garbage_count > 0 else 0

        if garbage_count > 3:
            problems_found.append(f"Significant waste pollution detected with {garbage_count} waste items identified")
            recommendations.append("Schedule urgent waste collection and cleanup")
        elif garbage_count > 0:
            problems_found.append(f"Minor waste issue detected with {garbage_count} waste items")
            recommendations.append("Regular waste collection needed")

    # Check for pothole issues
    pothole_objects = detections.get("potholes", [])
    if pothole_objects:
        pothole_count = len(pothole_objects)
        if pothole_count > 2:
            problems_found.append(f"Multiple potholes detected ({pothole_count}) - road surface is compromised")
            recommendations.append("Immediate road maintenance required to prevent vehicle damage and accidents")
        elif pothole_count > 0:
            problems_found.append(f"{pothole_count} pothole(s) detected on the road surface")
            recommendations.append("Schedule road maintenance to fix the identified potholes")

    # Generate final analysis
    if not problems_found:
        analysis = """
## Urban Analysis

No significant urban issues were detected in this image. The area appears to be in good condition based on our detection models.

### Recommendations
- Continue regular maintenance of the area
- Monitor for any developing issues
"""
    else:
        problems_text = "\n".join([f"- {p}" for p in problems_found])
        recommendations_text = "\n".join([f"- {r}" for r in recommendations])

        analysis = f"""
## Urban Analysis

### Detected Issues
{problems_text}

### Recommendations
{recommendations_text}

### Impact
These issues can affect public safety, environmental health, and the overall appearance of the urban landscape. Addressing them promptly will improve the quality of life for residents and visitors.
"""

    return analysis


if __name__ == '__main__':
    app.run(debug=True, port=5000)

