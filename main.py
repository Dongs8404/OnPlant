import time

from hardware.raspbot_driver import Raspbot
from movement.movement_controller import MovementController

from sensor.fake_light import FakeLightSensor
from movement.light_seek import LightSeekFSM
from movement.move_manager import MoveManager


bot = Raspbot()
controller = MovementController()

light_sensor = FakeLightSensor()
light_fsm = LightSeekFSM(light_sensor)
manager = MoveManager(light_fsm)

bot.Ctrl_IR_Switch(1)

try:
    while True:
        data = bot.read_data_array(0x0c, 1)
        key = data[0]

        if key == 1:          # 위
            print("전진")
            manager.set_manual_command("forward")

        elif key == 9:        # 아래
            print("후진")
            manager.set_manual_command("backward")

        elif key == 4:        # 왼쪽
            print("좌회전")
            manager.set_manual_command("left")

        elif key == 6:        # 오른쪽
            print("우회전")
            manager.set_manual_command("right")

        elif key == 13:       # 숫자 0
            print("정지")
            manager.set_manual_command("stop")

        manager.tick()

        time.sleep(0.15)

except KeyboardInterrupt:
    controller.stop()
    bot.Ctrl_IR_Switch(0)
    print("종료")