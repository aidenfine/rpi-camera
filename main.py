import cv2 as cv
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

lock = threading.Lock()
latest_frame = None
stop_event = threading.Event()


def capture_loop(camera):
    global latest_frame
    while not stop_event.is_set():
        ret, frame = camera.read()
        if not ret:
            time.sleep(0.1)
            continue

        with lock:
            latest_frame = frame

        time.sleep(0.03)  # ~30 FPS


@asynccontextmanager
async def lifespan(app: FastAPI):
    camera = cv.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("Could not open camera")

    thread = threading.Thread(target=capture_loop, args=(camera,), daemon=True)
    thread.start()

    yield

    stop_event.set()
    camera.release()


app = FastAPI(lifespan=lifespan)


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
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
