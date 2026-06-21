import time
import cv2
import numpy as np

from vision.yolo_detector import YOLODetector

try:
    from picamera2 import Picamera2
    PI_CAMERA_AVAILABLE = True
except ImportError:
    PI_CAMERA_AVAILABLE = False


class DummyCamera:
    def __init__(self, name, dummy_text):
        self.name = name
        self.dummy_text = dummy_text
        self.camera_type = "dummy"

    def get_frame(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:] = (245, 248, 240)

        cv2.putText(
            frame,
            self.dummy_text,
            (300, 300),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.7,
            (80, 120, 70),
            4,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            f"{self.name.upper()} CAMERA - DUMMY MODE",
            (360, 380),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (90, 90, 90),
            2,
            cv2.LINE_AA
        )

        return frame

    def stop(self):
        pass


class PiCamera:
    def __init__(self, name="plant", camera_num=0):
        self.name = name
        self.camera_num = camera_num
        self.camera_type = "picamera2"
        self.picam2 = None

        if not PI_CAMERA_AVAILABLE:
            raise RuntimeError("Picamera2 is not available.")

        self.picam2 = Picamera2(camera_num)

        config = self.picam2.create_video_configuration(
            main={"size": (1280, 720)}
        )

        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(1)

        print(f"[CAMERA] {self.name} Picamera2 started. camera_num={camera_num}")

    def get_frame(self):
        frame = self.picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    def stop(self):
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
            print(f"[CAMERA] {self.name} PiCamera2 stopped.")

    def __del__(self):
        self.stop()


class USBCamera:
    def __init__(self, name="user", device_index=0):
        self.name = name
        self.device_index = device_index
        self.camera_type = "usb"
        self.cap = cv2.VideoCapture(device_index)

        if not self.cap.isOpened():
            raise RuntimeError(f"USB camera open failed. device_index={device_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print(f"[CAMERA] {self.name} USB camera started. device_index={device_index}")

    def get_frame(self):
        ret, frame = self.cap.read()

        if not ret:
            raise RuntimeError("USB camera frame read failed.")

        return frame

    def stop(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            print(f"[CAMERA] {self.name} USB camera released.")

    def __del__(self):
        self.stop()


class CameraManager:
    def __init__(self):
        self.plant_camera = self.create_plant_camera()
        self.user_camera = self.create_user_camera()
        self.yolo_detector = YOLODetector()

    def create_plant_camera(self):
        try:
            return PiCamera(
                name="plant",
                camera_num=0
            )
        except Exception as e:
            print(f"[CAMERA] Plant camera fallback to dummy. error={e}")
            return DummyCamera(
                name="plant",
                dummy_text="On-Plant Plant Camera"
            )

    def create_user_camera(self):
        try:
            return PiCamera(
                name="user",
                camera_num=1
            )
        except Exception as e:
            print(f"[CAMERA] User Picamera2 fallback to USB. error={e}")

        try:
            return USBCamera(
                name="user",
                device_index=8
            )
        except Exception as e:
            print(f"[CAMERA] User camera fallback to dummy. error={e}")
            return DummyCamera(
                name="user",
                dummy_text="On-Plant User Tracking Camera"
            )

    def get_camera(self, camera_name="plant"):
        if camera_name == "user":
            return self.user_camera

        return self.plant_camera

    def get_frame(self, camera_name="plant", yolo=False):
        camera = self.get_camera(camera_name)

        try:
            frame = camera.get_frame()
        except Exception as e:
            print(f"[CAMERA] Frame read failed. camera={camera_name}, error={e}")

            if camera_name == "user":
                frame = DummyCamera(
                    name="user",
                    dummy_text="On-Plant User Tracking Camera"
                ).get_frame()
            else:
                frame = DummyCamera(
                    name="plant",
                    dummy_text="On-Plant Plant Camera"
                ).get_frame()

        if yolo:
            if camera_name == "user":
                frame = self.yolo_detector.detect_and_draw(frame, mode="person")
        else:
            frame = self.yolo_detector.detect_and_draw(frame, mode="general")

        return frame

    def get_jpeg(self, camera_name="plant", yolo=False):
        frame = self.get_frame(camera_name, yolo=yolo)

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            return None

        return buffer.tobytes()

    def generate_frames(self, camera_name="plant", yolo=False):
        while True:
            frame = self.get_jpeg(camera_name, yolo=yolo)

            if frame is None:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame +
                b"\r\n"
            )

    def stop(self):
        for cam in [self.plant_camera, self.user_camera]:
            if hasattr(cam, "stop"):
                cam.stop()

    def __del__(self):
        self.stop()


# ✅ 싱글톤 패턴: 임포트 시 즉시 실행하지 않고 첫 호출 시에만 초기화
_camera_manager = None


def get_camera_manager():
    global _camera_manager
    
    if _camera_manager is None:
        _camera_manager = CameraManager()
    
    return _camera_manager


def generate_frames(camera_name="plant", yolo=False):
    print(f"[STREAM START] {camera_name}")

    return get_camera_manager().generate_frames(
        camera_name, 
        yolo=yolo
    )
