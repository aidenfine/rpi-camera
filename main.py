import cv2 as cv
import threading
import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

camera = cv.VideoCapture(0)
if not camera.isOpened():
    raise RuntimeError("Could not open camera")

lock = threading.Lock()
latest_frame = None


def capture_loop():
    global latest_frame
    while True:
        ret, frame = camera.read()
        if not ret:
            time.sleep(0.1)
            continue

        with lock:
            latest_frame = frame

        time.sleep(0.03)  # ~30 FPS


@app.on_event("startup")
def start_camera():
    thread = threading.Thread(target=capture_loop, daemon=True)
    thread.start()


def frame_generator():
    while True:
        with lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()

        ret, buffer = cv.imencode(".jpg", frame)
        if not ret:
            continue

        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )


@app.get("/video")
def video_feed():
    return StreamingResponse(
        frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
