from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
from ultralytics import YOLO
import traceback

app = Flask(__name__)
CORS(app)

model = YOLO("yolov8n.pt")

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided."}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "Empty filename."}), 400

        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
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

        return jsonify({"detected_objects": objects})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
