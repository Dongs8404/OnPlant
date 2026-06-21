from ultralytics import YOLO
import cv2

from vision.tracker import PersonTracker
from vision.target_memory import TargetMemory
from brain.state_machine import StateMachine
from brain.decision import DecisionMaker
from control.controller import RobotController
from safety.safety_filter import SafetyFilter
from motor.motor_driver import VirtualMotorDriver, YahboomMotorDriver


class YOLODetector:
    def __init__(self, model_name="yolo11n.pt"):
        print(f"[YOLO] Loading model: {model_name}")

        self.model = YOLO(model_name)
        self.tracker = PersonTracker()
        self.memory = TargetMemory()
        self.state_machine = StateMachine()
        self.decision = DecisionMaker()
        self.controller = RobotController()
        self.safety = SafetyFilter()

        self.motor_driver = self.create_motor_driver()

    def create_motor_driver(self):
        try:
            motor_driver = YahboomMotorDriver()
            print("[MOTOR] YahboomMotorDriver enabled")
            return motor_driver

        except Exception as e:
            print("[MOTOR] YahboomMotorDriver unavailable:", e)
            print("[MOTOR] Falling back to VirtualMotorDriver")
            return VirtualMotorDriver()

    def detect(self, frame):
        return self.model(frame, verbose=False)

    def detect_person_and_draw(self, frame):
        results = self.detect(frame)
        result = results[0]

        person_count = 0
        tracking_result = self.tracker.no_target()

        frame_height, frame_width = frame.shape[:2]
        screen_center_x = frame_width // 2

        cv2.line(
            frame,
            (screen_center_x, 0),
            (screen_center_x, frame_height),
            (255, 180, 0),
            2,
        )

        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            confidence = float(box.conf[0])

            if class_name != "person" or confidence < 0.7:
                continue

            person_count += 1

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            tracking_result = self.tracker.track_target(
                center_x,
                screen_center_x
            )

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 0), 3)
            cv2.circle(frame, (center_x, center_y), 7, (0, 0, 255), -1)

            cv2.putText(
                frame,
                f"person {confidence:.2f}",
                (x1, y1 - 42),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 180, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                frame,
                f"center=({center_x},{center_y})",
                (x1, y1 - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 180, 0),
                2,
                cv2.LINE_AA,
            )

            break

        tracking_result = self.memory.update(tracking_result)
        robot_state = self.state_machine.update(tracking_result)
        motor_command = self.decision.decide(tracking_result)
        wheel_command = self.controller.convert(motor_command)
        safe_command = self.safety.apply(wheel_command)

        DEBUG = False

        if DEBUG:
    
            print("=" * 50)
            print(f"TRACKING : {tracking_result.direction}")
            print(f"MOTOR    : {motor_command.action}")
            print(f"WHEEL    : {wheel_command.action}")
            print(f"SAFE     : {safe_command.action}")
            print(f"DRIVER   : {type(self.motor_driver).__name__}")
            print("=" * 50)

        self.motor_driver.apply(safe_command)

        cv2.putText(
            frame,
            f"PERSON DETECTED: {person_count}",
            (40, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            f"DIRECTION: {tracking_result.direction} "
            f"SPEED: {tracking_result.turn_speed}",
            (40, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (0, 0, 255),
            3,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            f"ACTION : {motor_command.action}",
            (40, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 80, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            f"STATE : {robot_state.value}",
            (40, 195),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            f"SAFE : {safe_command.reason}",
            (40, 220),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            f"WHEEL FL:{safe_command.front_left} "
            f"FR:{safe_command.front_right} "
            f"RL:{safe_command.rear_left} "
            f"RR:{safe_command.rear_right}",
            (40, 270),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 80, 0),
            2,
            cv2.LINE_AA,
        )

        return frame, tracking_result, person_count

    def detect_and_draw(self, frame, mode="general"):
        if mode == "person":
            frame, tracking_result, person_count = self.detect_person_and_draw(frame)
            return frame

        results = self.detect(frame)
        return results[0].plot()