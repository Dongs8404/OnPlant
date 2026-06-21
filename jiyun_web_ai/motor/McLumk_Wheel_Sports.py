try:
    from Raspbot_Lib import Raspbot
except Exception as e:
    print("[McLumk_Wheel_Sports] Raspbot_Lib import failed:", e)
    Raspbot = None


bot = None


def init_bot():
    global bot

    if bot is not None:
        return bot

    if Raspbot is None:
        raise ImportError("Raspbot_Lib is not available.")

    bot = Raspbot()
    return bot


def move_forward(speed):
    robot = init_bot()

    robot.Ctrl_Muto(0, speed)
    robot.Ctrl_Muto(1, speed)
    robot.Ctrl_Muto(2, speed)
    robot.Ctrl_Muto(3, speed)


def move_backward(speed):
    robot = init_bot()

    robot.Ctrl_Muto(0, -speed)
    robot.Ctrl_Muto(1, -speed)
    robot.Ctrl_Muto(2, -speed)
    robot.Ctrl_Muto(3, -speed)


def rotate_left(speed):
    robot = init_bot()

    robot.Ctrl_Muto(0, -speed)
    robot.Ctrl_Muto(1, -speed)
    robot.Ctrl_Muto(2, speed)
    robot.Ctrl_Muto(3, speed)


def rotate_right(speed):
    robot = init_bot()

    robot.Ctrl_Muto(0, speed)
    robot.Ctrl_Muto(1, speed)
    robot.Ctrl_Muto(2, -speed)
    robot.Ctrl_Muto(3, -speed)


def stop_robot():
    robot = init_bot()

    robot.Ctrl_Car(0, 0, 0)
    robot.Ctrl_Car(1, 0, 0)
    robot.Ctrl_Car(2, 0, 0)
    robot.Ctrl_Car(3, 0, 0)