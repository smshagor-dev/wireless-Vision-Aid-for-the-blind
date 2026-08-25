#!/usr/bin/env python3
"""Explicit smartphone/IP-camera launcher for WVAB.

The previous network scanner was removed: WVAB does not probe local subnets or
require an Internet route to discover a camera. Supply the trusted camera URL
shown by the phone app.
"""

import argparse


class SmartphoneVisionAid:
    def __init__(self, camera_url):
        camera_url = str(camera_url or "").strip()
        if not camera_url:
            raise ValueError("camera_url is required")
        if not (camera_url.startswith("http://") or camera_url.startswith("https://") or camera_url.startswith("rtsp://")):
            raise ValueError("camera URL must use http://, https://, or rtsp://")
        self.camera_url = camera_url

    def test_connection(self):
        import cv2

        cap = cv2.VideoCapture(self.camera_url)
        try:
            if not cap.isOpened():
                return False, "could not open stream"
            ok, frame = cap.read()
            if not ok or frame is None:
                return False, "stream opened but no frame was received"
            return True, f"captured {frame.shape[1]}x{frame.shape[0]} frame"
        finally:
            cap.release()

    def run(self, model="yolov8n.pt", language="en", headless=False, enable_tts=True):
        from vision_server import VisionAidServer

        server = VisionAidServer(
            camera_url=self.camera_url,
            model_path=model,
            language=language,
            headless=headless,
            enable_tts=enable_tts,
        )
        return server.run_with_opencv_stream()


def main():
    parser = argparse.ArgumentParser(description="Run WVAB from a trusted smartphone/IP-camera stream")
    parser.add_argument("camera_url", help="Exact stream URL from the camera app, e.g. http://192.168.1.20:8080/video")
    parser.add_argument("--test-only", action="store_true", help="Capture one frame and exit")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--language", default="en")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-tts", action="store_true")
    args = parser.parse_args()

    aid = SmartphoneVisionAid(args.camera_url)
    ok, message = aid.test_connection()
    print(("PASS" if ok else "FAIL") + f" | Smartphone camera: {message}")
    if not ok:
        raise SystemExit(1)
    if not args.test_only:
        aid.run(
            model=args.model,
            language=args.language,
            headless=args.headless,
            enable_tts=not args.no_tts,
        )


if __name__ == "__main__":
    main()
