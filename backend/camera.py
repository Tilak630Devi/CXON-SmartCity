from flask import Flask, Response
import cv2
import torch
import time

app = Flask(__name__)

# ----------------------
# Model Initialization
# ----------------------
model = torch.hub.load('ultralytics/yolov5', 'yolov5l', pretrained=True)
model.conf = 0.5

vehicle_classes = ['car', 'bicycle', 'motorcycle', 'bus', 'truck']
vehicle_class_indices = {}
for idx, name in model.names.items():
    if name.lower() in vehicle_classes:
        vehicle_class_indices[name.lower()] = idx

if not vehicle_class_indices:
    raise ValueError("None of the specified vehicle classes were found in the model's classes.")

print("Vehicle classes detected and their indices:", vehicle_class_indices)

# ----------------------
# Streaming Generator
# ----------------------
def gen_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return
    try:
        # Process frames as fast as possible (no artificial delay)
        while cap.isOpened():
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            results = model(frame)
            detections = results.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2, conf, class]

            vehicle_counts = {cls: 0 for cls in vehicle_classes}
            for *box, conf, cls in detections:
                cls = int(cls)
                for vehicle, v_idx in vehicle_class_indices.items():
                    if cls == v_idx:
                        vehicle_counts[vehicle] += 1
                        x1, y1, x2, y2 = map(int, box)
                        if vehicle == 'car':
                            color = (0, 255, 0)
                        elif vehicle == 'bicycle':
                            color = (255, 0, 0)
                        elif vehicle == 'motorcycle':
                            color = (0, 255, 255)
                        elif vehicle == 'bus':
                            color = (255, 0, 255)
                        elif vehicle == 'truck':
                            color = (0, 0, 255)
                        else:
                            color = (255, 255, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label = f'{vehicle.capitalize()} {conf:.2f}'
                        cv2.putText(frame, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        break

            total_vehicles = sum(vehicle_counts.values())
            cv2.putText(frame, f'Total Vehicles: {total_vehicles}', (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            y_offset = 80
            for vehicle, count in vehicle_counts.items():
                cv2.putText(frame, f'{vehicle.capitalize()}: {count}', (20, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                y_offset += 40

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # (Optionally, you could compute processing time here if needed.)
    except GeneratorExit:
        # Client disconnected; stop processing
        print("Client disconnected. Stopping stream.")
    finally:
        cap.release()

@app.route('/stream/<video_id>')
def stream_video(video_id):
    video_path = f"video/{video_id}.mp4"
    return Response(gen_frames(video_path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=11000 , debug=True)
