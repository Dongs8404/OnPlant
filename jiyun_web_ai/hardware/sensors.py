import random


def read_mock_sensor_data():
    return {
        "soil": random.randint(0, 100),
        "temperature": random.randint(10, 40),
        "humidity": random.randint(20, 90),
        "light": random.randint(0, 1000),
    }


def read_real_sensor_data():
    # TODO: Raspberry Pi 센서 연결 후 실제 값 읽기
    raise NotImplementedError("실제 센서 연동은 아직 구현되지 않았습니다.")


def read_sensor_data(use_mock=True):
    if use_mock:
        return read_mock_sensor_data()

    return read_real_sensor_data()