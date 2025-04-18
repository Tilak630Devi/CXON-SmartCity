# File: app.py
import cv2
import torch
import numpy as np
import requests
from flask import Flask, Response
import time

# Load the YOLOv5l model (default pretrained model)
model = torch.hub.load("ultralytics/yolov5", "yolov5l", pretrained=True)
model.conf = 0.4  # Set confidence threshold to 0.5
model.eval()

# URL for your ESP32-CAM JPEG stream.
CAM_URL = "http://192.168.167.52/"    # Replace with your ESP32-CAM IP address
# Ensure the ESP32-CAM is connected to the same network as your computer.

app = Flask(__name__)

def generate_frames():
    """
    Connects to the ESP32-CAM's JPEG stream, extracts JPEG frames, processes
    each frame with YOLOv5l, and yields the annotated frame as part of an MJPEG stream.
    The processing loop is throttled to approximately 15 FPS.
    """
    try:
        stream = requests.get(CAM_URL, stream=True, timeout=10)
    except Exception as e:
        print("Error connecting to ESP32-CAM:", e)
        return

    if stream.status_code != 200:
        print("Error: Received non-200 status code from ESP32-CAM:", stream.status_code)
        return

    bytes_data = b""
    target_frame_time = 1.0 / 60
    for chunk in stream.iter_content(chunk_size=1024):
        start_time = time.time()
        bytes_data += chunk
        # Look for JPEG start and end markers
        start = bytes_data.find(b"\xff\xd8")
        end = bytes_data.find(b"\xff\xd9")
        if start != -1 and end != -1:
            jpg = bytes_data[start: end + 2]
            bytes_data = bytes_data[end + 2:]
            
            # Check if the jpg buffer is empty
            if not jpg or len(jpg) == 0:
                print("Warning: Extracted JPEG is empty, skipping frame.")
                continue

            # Decode JPEG image
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                print("Warning: cv2.imdecode returned None, skipping frame.")
                continue

            # Convert frame from BGR to RGB for the model
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Run detection using YOLOv5l
            results = model(frame_rgb)

            # Annotate frame with detection results (bounding boxes, labels)
            annotated_frame = results.render()[0]

            # Encode annotated frame as JPEG
            ret, buffer = cv2.imencode(".jpg", annotated_frame)
            if not ret:
                print("Warning: cv2.imencode failed, skipping frame.")
                continue

            frame_bytes = buffer.tobytes()

            # Yield the frame in the MJPEG format
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

            # Calculate processing time and sleep to maintain ~15 FPS
            elapsed = time.time() - start_time
            sleep_time = target_frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

@app.route("/")
def index():
    return "MJPEG Stream is available at /stream"

@app.route("/stream")
def stream():
    response = Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=32000)
