from dataclasses import dataclass


@dataclass
class SafeWheelCommand:
    front_left: int
    front_right: int
    rear_left: int
    rear_right: int
    action: str
    safe: bool
    reason: str


class SafetyFilter:
    def __init__(self, max_speed=80):
        self.max_speed = max_speed

    def clamp_speed(self, speed):
        if speed > self.max_speed:
            return self.max_speed

        if speed < -self.max_speed:
            return -self.max_speed

        return speed

    def apply(self, wheel_command):
        return SafeWheelCommand(
            front_left=self.clamp_speed(wheel_command.front_left),
            front_right=self.clamp_speed(wheel_command.front_right),
            rear_left=self.clamp_speed(wheel_command.rear_left),
            rear_right=self.clamp_speed(wheel_command.rear_right),
            action=wheel_command.action,
            safe=True,
            reason="OK"
        )