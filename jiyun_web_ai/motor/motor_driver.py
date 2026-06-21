class VirtualMotorDriver:
    def __init__(self):
        self.last_command = None

    def is_same_command(self, wheel_command):
        return self.last_command == wheel_command

    def apply(self, wheel_command):
        print("★★★★★ APPLY CALLED ★★★★★")
        if self.is_same_command(wheel_command):
            return

        self.last_command = wheel_command

        print("========== VIRTUAL MOTOR COMMAND ==========")
        print(f"ACTION      : {wheel_command.action}")
        print(f"FRONT LEFT  : {wheel_command.front_left}")
        print(f"FRONT RIGHT : {wheel_command.front_right}")
        print(f"REAR LEFT   : {wheel_command.rear_left}")
        print(f"REAR RIGHT  : {wheel_command.rear_right}")
        print("===========================================")

    def stop(self):
        self.last_command = None
        print("[VirtualMotorDriver] STOP")


class YahboomMotorDriver:
    def __init__(self, default_speed=35):
        self.default_speed = default_speed
        self.last_action = None

        try:
            from motor.McLumk_Wheel_Sports import (
                move_forward,
                rotate_left,
                rotate_right,
                stop_robot,
            )

            self.move_forward = move_forward
            self.rotate_left = rotate_left
            self.rotate_right = rotate_right
            self.stop_robot = stop_robot
            self.available = True

            print("[YahboomMotorDriver] Ready")

        except Exception as e:
            print("[YahboomMotorDriver] Load failed:", e)
            self.available = False

    def apply(self, wheel_command):
        action = wheel_command.action

        if action == self.last_action:
            return

        self.last_action = action

        print("========== YAHBOOM ACTION COMMAND ==========")
        print(f"ACTION : {action}")
        print("============================================")

        if not self.available:
            print("[YahboomMotorDriver] unavailable")
            return

        try:
            if action == "FORWARD":
                self.move_forward(self.default_speed)

            elif action == "TURN_LEFT":
                self.rotate_left(self.default_speed)

            elif action == "TURN_RIGHT":
                self.rotate_right(self.default_speed)

            elif action == "STOP":
                self.stop_robot()

            else:
                self.stop_robot()

        except Exception as e:
            print("[YahboomMotorDriver] motor error:", e)
            self.stop()

    def stop(self):
        self.last_action = None

        if self.available:
            self.stop_robot()

        print("[YahboomMotorDriver] STOP")