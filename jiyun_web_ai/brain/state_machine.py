from enum import Enum


class RobotState(Enum):
    IDLE = "IDLE"
    SEARCHING = "SEARCHING"
    TRACKING = "TRACKING"
    FOLLOWING = "FOLLOWING"
    LOST = "LOST"


class StateMachine:
    def __init__(self):
        self.state = RobotState.IDLE

    def update(self, tracking_result):
        if not tracking_result.target_found:
            self.state = RobotState.LOST
            return self.state

        if tracking_result.direction == "CENTER":
            self.state = RobotState.FOLLOWING
            return self.state

        if tracking_result.direction in ["LEFT", "RIGHT"]:
            self.state = RobotState.TRACKING
            return self.state

        self.state = RobotState.SEARCHING
        return self.state