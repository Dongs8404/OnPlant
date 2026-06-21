from dataclasses import dataclass


@dataclass
class WheelCommand:
    front_left: int
    front_right: int
    rear_left: int
    rear_right: int
    action: str


class RobotController:
    def convert(self, motor_command):
        if motor_command.action == "STOP":
            return WheelCommand(0, 0, 0, 0, "STOP")

        if motor_command.action == "TURN_LEFT":
            return WheelCommand(-25, 25, -25, 25, "TURN_LEFT")

        if motor_command.action == "TURN_RIGHT":
            return WheelCommand(25, -25, 25, -25, "TURN_RIGHT")

        if motor_command.action == "FORWARD":
            return WheelCommand(35, 35, 35, 35, "FORWARD")

        return WheelCommand(0, 0, 0, 0, "STOP")