from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
from ultralytics import YOLO
import traceback
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load multiple YOLO models
models = {
    "cigarettes": YOLO("ciggaretes.pt"),
    "potholes": YOLO("potholes.pt"),
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

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)

