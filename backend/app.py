from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import jwt
import os
import datetime
from datetime import datetime, timezone, timedelta
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
from db import users_collection, feedback_collection
from report_handler import save_user_report
from auth_handler import (
    register_user,
    login_user,
    request_password_reset_code,
    verify_reset_code_and_update_password,
)

# Import the GitHub AI client
from github_ai import GitHubAIClient, update_model_based_on_feedback

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


# Function to resize large images
def resize_image(image, max_dimension=1280):
    """Resize an image if it exceeds the maximum dimension while preserving aspect ratio."""
    width, height = image.size

    # If the image is already smaller than the max dimension, return it as is
    if width <= max_dimension and height <= max_dimension:
        return image

    # Calculate the resize factor to maintain aspect ratio
    if width > height:
        resize_factor = max_dimension / width
    else:
        resize_factor = max_dimension / height

    new_width = int(width * resize_factor)
    new_height = int(height * resize_factor)

    app.logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
    return image.resize((new_width, new_height), Image.LANCZOS)


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

        # Resize large images before processing
        image = resize_image(image)

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
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
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
        # Instead of deleting, mark reports as not visible
        result = reports_collection.update_many(
            {"username": username},
            {"$set": {"visible": False}}
        )

        return jsonify({
            "status": "success",
            "hidden": result.modified_count,
            "message": f"{result.modified_count} reports have been hidden from your history."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/admin/all_reports", methods=["POST"])
def admin_get_all_reports():
    """Admin endpoint to access all reports including hidden ones"""
    try:
        data = request.json
        admin_key = data.get("admin_key")
        username = data.get("username")  # Optional filter
        date_from = data.get("date_from")
        date_to = data.get("date_to")

        from report_handler import get_all_reports
        result = get_all_reports(admin_key, username, date_from, date_to)
        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/evaluate", methods=["POST"])
def evaluate_image():
    try:
        data = request.get_json()
        detections = data.get("detections", {})
        base64_image = data.get("image")  # Get the base64 image from the request

        if not base64_image:
            return jsonify({"status": "error", "message": "Missing image data"}), 400
            
        # Always try to use GitHub AI first, even if no detections from local models
        try:
            app.logger.info("Calling GitHub AI for evaluation and marking")
            github_ai = GitHubAIClient()
            result = github_ai.generate_interpretation(detections, base64_image)
            
            if result["status"] == "success":
                # Create a response that includes any marked image
                response = {
                    "status": "success",
                    "evaluation": result["evaluation"]
                }
                
                # Include marked image if available
                if "marked_image" in result:
                    app.logger.info("Marked image received from GitHub AI")
                    response["marked_image"] = result["marked_image"]
                else:
                    app.logger.warning("No marked image received from GitHub AI")

                return jsonify(response)
            else:
                app.logger.warning(f"GitHub AI failed: {result.get('message')}. Using fallback analysis.")
        except Exception as e:
            app.logger.exception(f"Error using GitHub AI: {str(e)}. Using fallback analysis.")

        return jsonify({
            "status": "success",
            "evaluation": "analysis:",
            "note": "This analysis was generated using a local fallback system as the advanced AI analysis service was unavailable."
        })

    except Exception as e:
        app.logger.exception("Evaluation failed")
        return jsonify({
            "status": "error",
            "message": f"Evaluation failed: {str(e)}"
        }), 500

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        correct = data.get("correct")
        comments = data.get("comments", "")
        detections = data.get("detections", {})
        username = data.get("username", "anonymous")

        # Log feedback for now (can be stored in a database or file)
        app.logger.info(f"Feedback received from {username}: Correct={correct}, Comments={comments}")

        # Prepare feedback entry
        feedback_entry = {
            "username": username,
            "correct": correct,
            "comments": comments,
            "detections": detections,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Store in database
        feedback_collection.insert_one(feedback_entry)

        # Use the feedback to update the model behavior
        update_result = update_model_based_on_feedback(feedback_entry)
        app.logger.info(f"Model update based on feedback: {update_result}")

        return jsonify({"status": "success", "message": "Feedback submitted successfully."})

    except Exception as e:
        app.logger.exception("Error handling feedback submission")
        return jsonify({"status": "error", "message": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True, port=5000)

