from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
from email_handler import send_email
from ultralytics import YOLO
import traceback
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load multiple YOLO models
models = {
    "cigarettes": YOLO("roboflow_cig.pt"),
    "potholes": YOLO("roboflow_potholes.pt"),
    "waste": YOLO("waste.pt")
}

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

        combined_results = {}

        # Run the image through each model
        for model_name, model in models.items():
            results = model(image)
            objects = []

            for result in results:
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

        app.logger.info("Detection completed successfully.")
        return jsonify({"detected_objects": combined_results})

    except Exception as e:
        app.logger.error(f"Detection failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500

@app.route("/send_email", methods=["POST"])
def handle_send_email():
    try:
        data = request.form
        location = data.get("location")
        details = data.get("details")
        file = request.files.get("image")

        if not all([location, details, file]):
            return jsonify({"status": "error", "message": "Missing data"}), 400

        result = send_email(
            location,
            details,
            file.read(),
            file.filename,
            file.content_type
        )

        if not isinstance(result, dict):
            return jsonify({"status": "error", "message": "Unexpected email handler output"}), 500

        return jsonify(result)

    except Exception as e:
        print("BACKEND ERROR:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)

