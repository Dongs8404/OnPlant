from dataclasses import dataclass


@dataclass
class MotorCommand:
    left_speed: int
    right_speed: int
    action: str


class DecisionMaker:
    def decide(self, tracking_result):
        if not tracking_result.target_found:
            return MotorCommand(0, 0, "STOP")

        if tracking_result.direction == "LEFT":
            return MotorCommand(30, 70, "TURN_LEFT")

        if tracking_result.direction == "RIGHT":
            return MotorCommand(70, 30, "TURN_RIGHT")

        if tracking_result.direction == "CENTER":
            return MotorCommand(45, 45, "FORWARD")

        return MotorCommand(0, 0, "STOP")
