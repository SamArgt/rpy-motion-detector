import cv2
import io
from PIL import Image

def main():
    cap = cv2.VideoCapture("/dev/video0")
    if not cap.isOpened():
        raise IOError(f"Cannot open video file: {video_path}")
    ret, frame = cap.read()
    if not ret:
        raise IOError(f"Cannot read video file: {video_path}")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("No frame read")
            break
        # Convert the frame from BGR to RGB format
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Convert the frame to a PIL Image
        pil_image = Image.fromarray(frame_rgb)

        # Save the PIL Image to a BytesIO object in JPEG format
        with open("test.jpg", "wb") as output:
            pil_image.save(output, format="JPEG")
        print("Saved image to test.jpg")
        break
    cap.release()


if __name__ == "__main__":
    main()



