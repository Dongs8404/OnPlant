from dataclasses import dataclass


@dataclass
class TrackingResult:
    target_found: bool
    direction: str
    offset_x: int
    turn_speed: int


class PersonTracker:
    def __init__(self, dead_zone=150, max_offset=500, min_speed=30, max_speed=80):
        self.dead_zone = dead_zone
        self.max_offset = max_offset
        self.min_speed = min_speed
        self.max_speed = max_speed

    def calculate_speed(self, offset_x):
        abs_offset = abs(offset_x)

        if abs_offset <= self.dead_zone:
            return 0

        ratio = min(abs_offset / self.max_offset, 1.0)
        speed = int(self.min_speed + (self.max_speed - self.min_speed) * ratio)

        return speed

    def track_target(self, center_x, screen_center_x):
        offset_x = center_x - screen_center_x

        if offset_x < -self.dead_zone:
            direction = "LEFT"
        elif offset_x > self.dead_zone:
            direction = "RIGHT"
        else:
            direction = "CENTER"

        turn_speed = self.calculate_speed(offset_x)

        return TrackingResult(
            target_found=True,
            direction=direction,
            offset_x=offset_x,
            turn_speed=turn_speed
        )

    def no_target(self):
        return TrackingResult(
            target_found=False,
            direction="NO_PERSON",
            offset_x=0,
            turn_speed=0
        )