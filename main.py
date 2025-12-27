import cv2 as cv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


def frame_generator():
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Encode frame as JPEG
            ret, buffer = cv.imencode(".jpg", frame)
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
    finally:
        cap.release()


@app.get("/video")
def video_feed():
    return StreamingResponse(
        frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
