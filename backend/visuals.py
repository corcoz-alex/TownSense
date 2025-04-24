import cv2
import numpy as np

MODEL_COLORS = {
    "potholes": (0, 255, 0),             # Green
    "garbage_detection": (255, 165, 0),  # Orange
}

def adjust_color_for_confidence(base_color, confidence):
    """
    High confidence → darker color
    Low confidence → lighter color
    """
    conf = np.clip(confidence, 0.0, 1.0)
    blend_factor = 1.0 - conf  # 0 = bold color, 1 = white

    r, g, b = base_color
    r = int(r + (255 - r) * blend_factor)
    g = int(g + (255 - g) * blend_factor)
    b = int(b + (255 - b) * blend_factor)

    return (r, g, b)

def draw_custom_boxes(image, result, model_name, show_conf=True, font_scale=0.5, box_thickness=2):
    base_color = MODEL_COLORS.get(model_name, (255, 255, 255))

    for box, conf, cls in zip(
        result.boxes.xyxy.cpu().numpy(),
        result.boxes.conf.cpu().numpy(),
        result.boxes.cls.cpu().numpy()
    ):
        x1, y1, x2, y2 = [int(coord) for coord in box]
        label = result.names[int(cls)]
        text = f"{label} {conf:.2f}" if show_conf else label

        # Adjust color based on confidence
        color = adjust_color_for_confidence(base_color, conf)

        # Draw bounding box
        cv2.rectangle(image, (x1, y1), (x2, y2), color, box_thickness)

        # Draw label background
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        cv2.rectangle(image, (x1, y1 - th - 4), (x1 + tw + 4, y1), color, -1)

        # Draw label text
        cv2.putText(image, text, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

