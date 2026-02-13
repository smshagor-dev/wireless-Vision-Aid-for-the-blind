"""
Alternative setup: use a smartphone as the camera source for WVAB.
"""

import socket
import cv2


class SmartphoneVisionAid:
    """
    Use smartphone camera via IP Camera app.

    Recommended apps:
    - Android: IP Webcam (by Pavel Khlebovich)
    - iOS: IP Camera Lite
    """

    def __init__(self, camera_ip="192.168.1.100", port="8080"):
        self.camera_url = f"http://{camera_ip}:{port}/video"

        print("=" * 60)
        print("Smartphone Vision Aid Setup")
        print("=" * 60)
        print(f"Camera URL: {self.camera_url}")
        print("\nMake sure:")
        print("1. Smartphone and computer are on same Wi-Fi")
        print("2. IP Camera app is running on smartphone")
        print("3. You can access the camera URL in a web browser")
        print("=" * 60)

    def test_connection(self):
        """Test connection to smartphone camera."""
        print("\nTesting connection...")

        cap = cv2.VideoCapture(self.camera_url)

        if not cap.isOpened():
            print("FAILED: Could not connect to camera")
            print("\nTroubleshooting:")
            print("1. Check if IP address is correct")
            print("2. Make sure app is running on phone")
            print("3. Try accessing URL in web browser")
            print(f"   URL to test: {self.camera_url}")
            return False

        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            print("PASS: Connection successful")
            print(f"PASS: Frame size: {frame.shape[1]}x{frame.shape[0]}")
            return True

        print("FAILED: Could not read frame from camera")
        return False

    def run(self):
        """Run the vision aid system with smartphone camera."""
        if not self.test_connection():
            return

        from vision_server import VisionAidServer

        server = VisionAidServer(camera_url=self.camera_url)
        print("\nStarting vision aid system...")
        server.run_with_opencv_stream()


def scan_network_for_cameras():
    """Scan local network for likely smartphone camera URLs."""
    print("\n" + "=" * 60)
    print("IP Camera Scanner")
    print("=" * 60)
    print("\nNote: This tests only common IP camera URLs")
    print("Checking the phone app for the exact URL is faster")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        network_base = ".".join(local_ip.split(".")[:-1])
        print(f"\nYour computer IP: {local_ip}")
        print(f"Scanning network: {network_base}.x")
    except Exception:
        print("Could not determine local network")
        return

    common_ports = ["8080", "8081", "4747"]
    found_cameras = []

    print("\nScanning... (this may take a minute)")

    for port in common_ports:
        print(f"\nTrying port {port}...")
        for i in range(100, 110):
            ip = f"{network_base}.{i}"
            url = f"http://{ip}:{port}/video"

            try:
                cap = cv2.VideoCapture(url)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        print(f"PASS: Found camera at: {url}")
                        found_cameras.append(url)
                cap.release()
            except Exception:
                pass

    if found_cameras:
        print(f"\nPASS: Found {len(found_cameras)} camera(s):")
        for cam in found_cameras:
            print(f"  - {cam}")
    else:
        print("\nFAILED: No cameras found in scan")
        print("\nTip: Check your phone's IP Camera app for the exact URL")


def interactive_setup():
    """Interactive setup wizard."""
    print("\n" + "=" * 60)
    print("WVAB Smartphone Setup Wizard")
    print("=" * 60)

    print("\n1. Scan network for cameras (slow)")
    print("2. Enter camera IP manually (recommended)")
    print("3. Exit")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        scan_network_for_cameras()
    elif choice == "2":
        print("\nEnter camera details:")
        ip = input("Camera IP address (e.g., 192.168.1.100): ").strip()
        port = input("Port (default 8080): ").strip() or "8080"

        aid = SmartphoneVisionAid(camera_ip=ip, port=port)

        if input("\nTest connection? (y/n): ").strip().lower() == "y":
            if aid.test_connection() and input("\nStart vision aid system? (y/n): ").strip().lower() == "y":
                aid.run()
        else:
            aid.run()
    else:
        print("Exiting...")


if __name__ == "__main__":
    interactive_setup()
