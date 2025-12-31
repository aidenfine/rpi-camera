import cv2 as cv
import threading
import time
from contextlib import asynccontextmanager
import datetime as dt

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse


connected_clients = set()
clients_lock = threading.Lock()

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


def frame_generator(client_id: str):
    try:
        while True:
            with lock:
                if latest_frame is None:
                    continue
                frame = latest_frame.copy()

            ret, buffer = cv.imencode(".jpg", frame)
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
    except GeneratorExit:
        with clients_lock:
            connected_clients.discard(client_id)
            write_client_connect_to_logs({"ip": client_id, "time": dt.datetime.now()})
        print(f"Client disconnected: {client_id}")


def write_client_connect_to_logs(client):
    today = dt.date.today()
    with open(f"logs/{today}", "a") as f:
        f.write(f"Client: {client['ip']}, Time: {client['time']}\n")


@app.get("/video")
def video_feed(request: Request):
    client_ip = request.client.host

    with clients_lock:
        connected_clients.add(client_ip)
        print(f"Client connected: {client_ip}")
        print(f"Active clients: {len(connected_clients)}")

    return StreamingResponse(
        frame_generator(client_ip),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
