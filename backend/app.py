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
from dotenv import load_dotenv
from email_handler import send_email
from ultralytics import YOLO
from contact_handler import handle_contact_submission
from visuals import draw_custom_boxes
from auth_handler import (
    register_user,
    login_user,
    request_password_reset_code,
    verify_reset_code_and_update_password,
)

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
    "potholes": YOLO("models/roboflow_potholes.pt"),
#    "waste": YOLO("models/waste.pt"),
    "garbage_detection": YOLO("models/garbage_detector.pt"),
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
        file = request.files.get("image")

        if not all([location, details, file]):
            app.logger.warning("Missing data in send_email")
            return jsonify({"status": "error", "message": "Missing data"}), 400

        app.logger.info(f"Sending email for report at '{location}'")

        result = send_email(
            location,
            details,
            file.read(),
            file.filename,
            file.content_type
        )

        app.logger.info(f"Email send result: {result}")
        return jsonify(result)

    except Exception as e:
        app.logger.exception("Email sending failed")
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
        return jsonify({"status": "success", "token": token, "username": result["username"]})
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)

