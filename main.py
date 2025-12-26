import cv2 as cv


def main():
    cap = cv.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Cannot access webcam")
        exit()

    print("Webcam in use press q to quit")
    while True:
        ret, frame = cap.read()

        if not ret:
            print("breaking")
            break
        cv.imshow("webcam free", frame)

        if cv.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
