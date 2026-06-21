import time


class TargetMemory:
    def __init__(self, hold_time=0.5):
        self.hold_time = hold_time
        self.last_seen_time = 0
        self.last_result = None

    def update(self, tracking_result):
        if tracking_result.target_found:
            self.last_seen_time = time.time()
            self.last_result = tracking_result
            return tracking_result

        if self.last_result is not None:
            elapsed = time.time() - self.last_seen_time

            if elapsed <= self.hold_time:
                return self.last_result

        return tracking_result