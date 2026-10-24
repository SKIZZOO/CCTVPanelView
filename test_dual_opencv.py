import cv2
import time
import threading
import os

# Configure FFmpeg options for low latency and TCP transport
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|max_delay;500000"

feed1_url = "rtsp://admin:password123@192.168.1.100:554/live/ch00_0"
feed2_url = "rtsp://admin:password123@192.168.1.100:554/live/ch01_0"

results = {}

def capture_stream(name, url):
    print(f"[{name}] Opening stream: {url}")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print(f"[{name}] FAILED to open stream!")
        results[name] = False
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[{name}] CONNECTED: {width}x{height} @ {fps} fps")

    frame_count = 0
    start = time.time()
    for _ in range(30):
        ret, frame = cap.read()
        if not ret:
            print(f"[{name}] Frame read failed!")
            break
        frame_count += 1

    elapsed = time.time() - start
    print(f"[{name}] Successfully read {frame_count} frames in {elapsed:.2f}s ({frame_count/elapsed:.1f} fps)!")
    cap.release()
    results[name] = True

t1 = threading.Thread(target=capture_stream, args=("FEED_1 (Lens 1)", feed1_url))
t2 = threading.Thread(target=capture_stream, args=("FEED_2 (Lens 2)", feed2_url))

t1.start()
t2.start()

t1.join()
t2.join()

print("\n--- TEST SUMMARY ---")
print("Results:", results)
if all(results.values()) and len(results) == 2:
    print(">>> DUAL STREAM SUCCESSFUL: Both ONVIF/RTSP feeds streamed simultaneously without issues! <<<")
