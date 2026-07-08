import math
import json
import os
import queue
import random
import threading
import time
import urllib.request
from enum import Enum

import smbus
from rplidar import RPLidar

from Raspbot_Lib import Raspbot
from movement.movement_controller import MovementController

PORT = "/dev/ttyUSB0"
LIDAR_FRONT_ANGLE = -4.0
LIDAR_MIRROR_ANGLE = True

USE_DUMMY_LUX = True
USE_DUMMY_SOIL = True

SELF_IGNORE_ZONES = [
    (105, 125, 180, 280),
    (-125, -105, 180, 280),
    (-105, -80, 110, 180),
    (-45, -20, 150, 240),
]

START_KEY = 16
STOP_KEY = 17
IGNORE_KEYS = [0, 65, 255]

MIN_VALID = 50
MAX_VALID = 2000

LIDAR_TO_FRONT_AXLE = 25
LIDAR_TO_LEFT_OUTER = 80
LIDAR_TO_RIGHT_OUTER = 80
SAFETY_MARGIN = 20

LEFT_CLEARANCE = LIDAR_TO_LEFT_OUTER + SAFETY_MARGIN
RIGHT_CLEARANCE = LIDAR_TO_RIGHT_OUTER + SAFETY_MARGIN

FRONT_WARN_X = LIDAR_TO_FRONT_AXLE + SAFETY_MARGIN + 300
FRONT_DANGER_X = LIDAR_TO_FRONT_AXLE + SAFETY_MARGIN + 160
FRONT_EMERGENCY_X = LIDAR_TO_FRONT_AXLE + SAFETY_MARGIN + 70
FRONT_CLEAR_X = LIDAR_TO_FRONT_AXLE + SAFETY_MARGIN + 360

SIDE_FRONT_MIN_X = 0
SIDE_FRONT_MAX_X = 650
LEFT_SECTOR = (15, 115)
RIGHT_SECTOR = (-115, -15)
SIDE_SCORE_DEADBAND = 60

POINT_LIMIT = 2
THIN_POINT_X = LIDAR_TO_FRONT_AXLE + SAFETY_MARGIN + 280

BACKWARD_X = 180
BACKWARD_WIDTH = 120

BH1750_ADDR = 0x23
BH1750_CONT_HIGH_RES = 0x10
LIGHT_READ_INTERVAL = 0.35
SOIL_READ_INTERVAL = 1.0

KEY_READ_INTERVAL = 0.2
LIDAR_MAX_BUF_MEAS = 1000
PRINT_INTERVAL = 0.3
LIDAR_POST_ENABLED = True
LIDAR_POST_DEBUG = True
LIDAR_POST_INTERVAL = 0.35
LIDAR_POST_MAX_POINTS = 360
ONPLANT_SERVER_URL = os.getenv("ONPLANT_SERVER_URL", "http://192.168.100.198:5050").rstrip("/")
ONPLANT_ROBOT_ID = os.getenv("ONPLANT_ROBOT_ID", "raspbot-a")

EXPLORE_SECONDS = 50.0
LIGHT_SEEK_SECONDS = 18.0
LIGHT_IMPROVE_MARGIN = 3.0
LIGHT_FOUND_MARGIN = 35.0
RETURN_STOP_MARGIN = 5.0
RETURN_SEGMENT_MAX_SECONDS = 0.45
RETURN_BACKWARD_MAX_SECONDS = 0.25
RETURN_ALLOW_BACKWARD = False
RETURN_TURN_AROUND_SECONDS = 0.85

TURN_PULSE_SECONDS = 0.28
BACKUP_SECONDS = 0.30
ESCAPE_TURN_SECONDS = 0.65
COMMAND_REFRESH_SECONDS = 0.6

EXPLORE_NUDGE_INTERVAL = 2.8
EXPLORE_NUDGE_SECONDS = 0.45
EXPLORE_BIAS_SWITCH_SECONDS = 8.0
EXPLORE_PASSAGE_SIDE_LIMIT = 300
SIDE_TOO_CLOSE_X = 260
SIDE_SOFT_CLOSE_X = 330
SIDE_BALANCE_DEADBAND = 90
TURN_SPACE_MIN_X = 280
TRAPPED_BACKUP_SECONDS = 0.45
TRAPPED_FORWARD_SECONDS = 0.30
AVOID_REPEAT_BACKUP_COUNT = 3
AVOID_REPEAT_ESCAPE_COUNT = 5


class State(Enum):
    IDLE = "IDLE"
    EXPLORE = "EXPLORE"
    AVOID = "AVOID"
    BACKUP = "BACKUP"
    ESCAPE = "ESCAPE"
    RETURN_TO_BEST = "RETURN_TO_BEST"
    SEEK_LIGHT = "SEEK_LIGHT"


lidar = RPLidar(PORT)
bot = Raspbot()
controller = MovementController()
light_bus = None if USE_DUMMY_LUX else smbus.SMBus(1)

bot.Ctrl_IR_Switch(1)

state = State.IDLE
state_until = 0.0
state_started = 0.0
explore_started = 0.0
seek_started = 0.0
return_segments = []
return_index = 0
return_until = 0.0
resume_state = None

current_motion = "STOP"
last_motion_send = 0.0
motion_log = []
active_motion = "STOP"
active_motion_started = 0.0
avoid_turn = "LEFT"
last_turn = "LEFT"
turn_repeat_count = 0

current_lux = 0.0
current_soil = 0.0
best_lux = -1.0
best_lux_time = 0.0
best_motion_time = 0.0
last_lux_read = 0.0
last_soil_read = 0.0
last_print = 0.0
last_key_read = 0.0
dummy_sensor_started = time.monotonic()
explore_last_nudge = 0.0
explore_nudge_until = 0.0
explore_nudge_motion = "FORWARD"
last_lidar_post = 0.0
last_lidar_post_error = 0.0
lidar_post_ok_printed = False
lidar_post_queue = queue.Queue(maxsize=1)


def lidar_post_worker():
    global last_lidar_post_error, lidar_post_ok_printed

    while True:
        payload = lidar_post_queue.get()
        if payload is None:
            return

        url = f"{ONPLANT_SERVER_URL}/api/robots/{ONPLANT_ROBOT_ID}/lidar"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=0.12).read()
            if LIDAR_POST_DEBUG and not lidar_post_ok_printed:
                print(f"LIDAR POST OK -> {url}")
                lidar_post_ok_printed = True
        except Exception:
            if LIDAR_POST_DEBUG:
                now = time.monotonic()
                if now - last_lidar_post_error >= 5.0:
                    print(f"LIDAR POST ERROR -> {url}")
                    last_lidar_post_error = now


def start_lidar_post_worker():
    if not LIDAR_POST_ENABLED:
        return
    worker = threading.Thread(target=lidar_post_worker, daemon=True)
    worker.start()


def maybe_post_lidar(scan_info, now):
    global last_lidar_post

    if not LIDAR_POST_ENABLED:
        return
    if now - last_lidar_post < LIDAR_POST_INTERVAL:
        return
    last_lidar_post = now

    points = scan_info["points"]
    stride = max(1, len(points) // LIDAR_POST_MAX_POINTS)
    sampled = points[::stride][:LIDAR_POST_MAX_POINTS]
    payload = {
        "state": state.value,
        "action": current_motion,
        "front_blocked": scan_info["front_blocked"],
        "danger": scan_info["danger"],
        "emergency": scan_info["emergency"],
        "front_points": len(scan_info["front"]),
        "left_score": round(scan_info["left_score"], 1),
        "right_score": round(scan_info["right_score"], 1),
        "source": "raspberry-pi",
        "points": [
            {
                "angle": round(angle, 1),
                "distance": round(distance, 1),
                "x": round(x, 1),
                "y": round(y, 1),
            }
            for angle, distance, x, y in sampled
        ],
    }

    try:
        if lidar_post_queue.full():
            lidar_post_queue.get_nowait()
        lidar_post_queue.put_nowait(payload)
    except Exception:
        pass


def normalize_angle(angle):
    angle %= 360
    if angle > 180:
        angle -= 360
    return angle


def normalize_lidar_angle(angle):
    angle = normalize_angle(angle - LIDAR_FRONT_ANGLE)
    if LIDAR_MIRROR_ANGLE:
        angle = -angle
    return normalize_angle(angle)


def angle_to_xy(angle, distance):
    angle = normalize_lidar_angle(angle)
    rad = math.radians(angle)
    return distance * math.cos(rad), distance * math.sin(rad)


def is_self_noise(angle, distance):
    for min_angle, max_angle, min_distance, max_distance in SELF_IGNORE_ZONES:
        if min_angle <= angle <= max_angle and min_distance <= distance <= max_distance:
            return True
    return False


def get_scan_points(scan):
    points = []
    for quality, raw_angle, distance in scan:
        if distance < MIN_VALID or distance > MAX_VALID:
            continue

        angle = normalize_lidar_angle(raw_angle)
        if is_self_noise(angle, distance):
            continue

        x, y = angle_to_xy(raw_angle, distance)
        points.append((angle, distance, x, y))
    return points


def in_front_lane(x, y):
    return x > 0 and -RIGHT_CLEARANCE <= y <= LEFT_CLEARANCE


def get_front_points(points):
    front = []
    for angle, distance, x, y in points:
        if in_front_lane(x, y) and x <= FRONT_WARN_X:
            front.append((angle, distance, x, y))
    return front


def get_rear_blocked(points):
    count = 0
    for angle, distance, x, y in points:
        if x < 0 and abs(x) <= BACKWARD_X and -BACKWARD_WIDTH <= y <= BACKWARD_WIDTH:
            count += 1
    return count >= 2


def get_side_scores(points):
    left_nearest = MAX_VALID
    right_nearest = MAX_VALID
    left_count = 0
    right_count = 0

    for angle, distance, x, y in points:
        if x < SIDE_FRONT_MIN_X or x > SIDE_FRONT_MAX_X:
            continue

        if LEFT_SECTOR[0] <= angle <= LEFT_SECTOR[1]:
            left_count += 1
            left_nearest = min(left_nearest, distance)
        elif RIGHT_SECTOR[0] <= angle <= RIGHT_SECTOR[1]:
            right_count += 1
            right_nearest = min(right_nearest, distance)

    left_score = left_nearest if left_count else FRONT_CLEAR_X
    right_score = right_nearest if right_count else FRONT_CLEAR_X
    return left_score, right_score, left_count, right_count


def choose_open_turn(points):
    left_score, right_score, left_count, right_count = get_side_scores(points)
    if abs(left_score - right_score) <= SIDE_SCORE_DEADBAND:
        if left_count > right_count + 2:
            return "RIGHT", left_score, right_score
        if right_count > left_count + 2:
            return "LEFT", left_score, right_score
        return avoid_turn, left_score, right_score

    if left_score >= right_score:
        return "LEFT", left_score, right_score
    return "RIGHT", left_score, right_score


def choose_escape_turn(points):
    turn, left_score, right_score = choose_open_turn(points)
    if turn == last_turn and turn_repeat_count >= 2:
        turn = "RIGHT" if turn == "LEFT" else "LEFT"
    return turn, left_score, right_score


def remember_turn_choice(turn):
    global last_turn, turn_repeat_count

    if turn == last_turn:
        turn_repeat_count += 1
    else:
        turn_repeat_count = 0
    last_turn = turn


def has_turn_space(scan_info):
    return (
        scan_info["left_score"] >= TURN_SPACE_MIN_X
        or scan_info["right_score"] >= TURN_SPACE_MIN_X
    )


def both_sides_tight(scan_info):
    return (
        scan_info["left_count"] >= 2
        and scan_info["right_count"] >= 2
        and scan_info["left_score"] < TURN_SPACE_MIN_X
        and scan_info["right_score"] < TURN_SPACE_MIN_X
    )


def analyze_scan(scan):
    points = get_scan_points(scan)
    front = get_front_points(points)
    nearest = min(front, key=lambda p: p[2], default=None)
    left_score, right_score, left_count, right_count = get_side_scores(points)

    front_blocked = len(front) >= POINT_LIMIT
    thin_blocked = any(p[2] <= THIN_POINT_X for p in front)
    danger = nearest is not None and nearest[2] <= FRONT_DANGER_X
    emergency = nearest is not None and nearest[2] <= FRONT_EMERGENCY_X
    clear = nearest is None or nearest[2] > FRONT_CLEAR_X

    return {
        "points": points,
        "front": front,
        "nearest": nearest,
        "front_blocked": front_blocked or thin_blocked,
        "danger": danger,
        "emergency": emergency,
        "clear": clear,
        "rear_blocked": get_rear_blocked(points),
        "left_score": left_score,
        "right_score": right_score,
        "left_count": left_count,
        "right_count": right_count,
    }


def init_lux_sensor():
    if USE_DUMMY_LUX:
        return

    try:
        light_bus.write_byte(BH1750_ADDR, BH1750_CONT_HIGH_RES)
    except Exception as e:
        print("BH1750 INIT ERROR", e)


def read_dummy_lux():
    t = time.monotonic() - dummy_sensor_started
    lux = random.uniform(420, 620)

    # Dummy bright zone for the current testbed.
    if 22.0 <= t <= 34.0:
        center = 28.0
        width = 6.0
        peak = max(0.0, 1.0 - abs(t - center) / width)
        lux = 800 + 90 * peak + random.uniform(-8, 8)

    return round(lux, 1)


def read_lux_fast():
    if USE_DUMMY_LUX:
        return read_dummy_lux()

    try:
        data = light_bus.read_i2c_block_data(BH1750_ADDR, 0x00, 2)
        return ((data[0] << 8) + data[1]) / 1.2
    except Exception as e:
        print("BH1750 READ ERROR", e)
        return -1


def read_dummy_soil():
    return round(random.uniform(38, 52), 1)


def read_soil_fast():
    if USE_DUMMY_SOIL:
        return read_dummy_soil()

    # Real soil sensor is intentionally disabled until it is inserted in soil
    # and its normal range is confirmed.
    return -1


def read_ir_key():
    try:
        key = bot.read_data_array(0x0c, 1)[0]
        if key not in IGNORE_KEYS:
            return key
    except Exception:
        pass
    return 0


def should_log_motion():
    return state in (State.EXPLORE, State.AVOID, State.BACKUP, State.ESCAPE)


def log_motion_change(next_motion, now):
    global active_motion, active_motion_started

    if active_motion == next_motion:
        return

    if should_log_motion() and active_motion != "STOP" and active_motion_started > 0:
        duration = now - active_motion_started
        if duration >= 0.05:
            motion_log.append(
                {
                    "start": active_motion_started,
                    "end": now,
                    "motion": active_motion,
                    "duration": duration,
                }
            )

    active_motion = next_motion
    active_motion_started = now


def finalize_motion_log(now):
    log_motion_change("STOP", now)


def reverse_motion(motion):
    if motion == "FORWARD":
        return "BACKWARD"
    if motion == "BACKWARD":
        return "FORWARD"
    if motion == "LEFT":
        return "RIGHT"
    if motion == "RIGHT":
        return "LEFT"
    return "STOP"


def append_return_segment(segments, motion, duration):
    if motion == "STOP" or duration < 0.08:
        return
    segments.append({"motion": motion, "duration": duration})


def build_return_segments(now):
    finalize_motion_log(now)
    segments = []
    return_facing_backward = False

    for item in reversed(motion_log):
        if item["end"] <= best_motion_time:
            break

        duration = item["duration"]
        if item["start"] < best_motion_time:
            duration = item["end"] - best_motion_time

        reversed_motion = reverse_motion(item["motion"])
        if reversed_motion == "STOP" or duration < 0.08:
            continue

        if not RETURN_ALLOW_BACKWARD and reversed_motion in ("FORWARD", "BACKWARD"):
            if reversed_motion == "BACKWARD" and not return_facing_backward:
                append_return_segment(segments, "LEFT", RETURN_TURN_AROUND_SECONDS)
                return_facing_backward = True
            elif reversed_motion == "FORWARD" and return_facing_backward:
                append_return_segment(segments, "LEFT", RETURN_TURN_AROUND_SECONDS)
                return_facing_backward = False

            while duration > 0:
                chunk = min(duration, RETURN_SEGMENT_MAX_SECONDS)
                append_return_segment(segments, "FORWARD", chunk)
                duration -= chunk
            continue

        max_duration = RETURN_BACKWARD_MAX_SECONDS if reversed_motion == "BACKWARD" else RETURN_SEGMENT_MAX_SECONDS
        while duration > 0:
            chunk = min(duration, max_duration)
            append_return_segment(segments, reversed_motion, chunk)
            duration -= chunk

    return segments


def elapsed_from_start(now):
    if explore_started <= 0:
        return 0.0
    return now - explore_started


def set_motion(motion, force=False):
    global current_motion, last_motion_send

    now = time.monotonic()
    if not force and motion == current_motion and now - last_motion_send < COMMAND_REFRESH_SECONDS:
        return

    if motion != current_motion:
        log_motion_change(motion, now)

    current_motion = motion
    last_motion_send = now

    if motion == "FORWARD":
        controller.forward()
    elif motion == "LEFT":
        controller.rotate_left()
    elif motion == "RIGHT":
        controller.rotate_right()
    elif motion == "BACKWARD":
        controller.backward()
    else:
        controller.stop()


def enter_state(new_state, duration=0.0):
    global state, state_started, state_until
    state = new_state
    state_started = time.monotonic()
    state_until = state_started + duration if duration > 0 else 0.0


def update_light(now):
    global current_lux, best_lux, best_lux_time, best_motion_time, last_lux_read

    if now - last_lux_read < LIGHT_READ_INTERVAL:
        return

    lux = read_lux_fast()
    last_lux_read = now
    if lux < 0:
        return

    current_lux = lux
    if lux > best_lux:
        best_lux = lux
        best_lux_time = now
        best_motion_time = now


def update_soil(now):
    global current_soil, last_soil_read

    if now - last_soil_read < SOIL_READ_INTERVAL:
        return

    soil = read_soil_fast()
    last_soil_read = now
    if soil < 0:
        return

    current_soil = soil


def exploration_bias():
    if best_lux < 0:
        return None
    if current_lux >= best_lux - LIGHT_IMPROVE_MARGIN:
        return None
    return last_turn


def choose_explore_clear_motion(scan_info, now):
    global explore_last_nudge, explore_nudge_until, explore_nudge_motion

    if scan_info["emergency"] or scan_info["danger"] or scan_info["front_blocked"]:
        return None

    if now < explore_nudge_until:
        return explore_nudge_motion

    front_points = len(scan_info["front"])
    left_score = scan_info["left_score"]
    right_score = scan_info["right_score"]
    left_count = scan_info["left_count"]
    right_count = scan_info["right_count"]

    # If both sides are close but the front lane is open, treat it as a passage
    # and keep moving through the middle instead of turning away.
    if (
        front_points == 0
        and left_score < EXPLORE_PASSAGE_SIDE_LIMIT
        and right_score < EXPLORE_PASSAGE_SIDE_LIMIT
    ):
        return "FORWARD"

    # Side-only obstacles do not always enter the front lane. Handle them here
    # so the robot does not keep spinning or scraping near a box/wall.
    if right_count >= 2 and right_score < SIDE_TOO_CLOSE_X:
        explore_last_nudge = now
        return "LEFT"

    if left_count >= 2 and left_score < SIDE_TOO_CLOSE_X:
        explore_last_nudge = now
        return "RIGHT"

    if right_count >= 2 and right_score < SIDE_SOFT_CLOSE_X and left_score - right_score > SIDE_BALANCE_DEADBAND:
        explore_last_nudge = now
        return "LEFT"

    if left_count >= 2 and left_score < SIDE_SOFT_CLOSE_X and right_score - left_score > SIDE_BALANCE_DEADBAND:
        explore_last_nudge = now
        return "RIGHT"

    if now - explore_last_nudge < EXPLORE_NUDGE_INTERVAL:
        return "FORWARD"

    explore_last_nudge = now
    elapsed = elapsed_from_start(now)
    if int(elapsed // EXPLORE_BIAS_SWITCH_SECONDS) % 2 == 0:
        explore_nudge_motion = "LEFT"
    else:
        explore_nudge_motion = "RIGHT"
    explore_nudge_until = now + EXPLORE_NUDGE_SECONDS
    return explore_nudge_motion


def fsm_step(scan_info, now):
    global avoid_turn, last_turn, turn_repeat_count
    global explore_started, seek_started, best_lux, best_lux_time
    global return_segments, return_index, return_until, resume_state

    nearest = scan_info["nearest"]
    front_gap = nearest[2] - LIDAR_TO_FRONT_AXLE if nearest else None

    if state == State.IDLE:
        set_motion("STOP")
        return "WAIT", front_gap

    if state in (State.EXPLORE, State.SEEK_LIGHT):
        if state == State.EXPLORE and now - explore_started >= EXPLORE_SECONDS:
            return_segments = build_return_segments(now)
            return_index = 0
            return_until = 0.0
            if return_segments:
                enter_state(State.RETURN_TO_BEST)
                print(
                    f"EXPLORE DONE: best_lux={best_lux:.1f} "
                    f"best_time={best_lux_time - explore_started:.1f}s "
                    f"return_segments={len(return_segments)}"
                )
                return "RETURN_START", front_gap

            seek_started = now
            enter_state(State.SEEK_LIGHT)
            print(
                f"EXPLORE DONE: best_lux={best_lux:.1f} "
                f"best_time={best_lux_time - explore_started:.1f}s "
                "entering SEEK_LIGHT"
            )

        if scan_info["emergency"]:
            if scan_info["rear_blocked"]:
                avoid_turn, _, _ = choose_escape_turn(scan_info["points"])
                enter_state(State.ESCAPE, ESCAPE_TURN_SECONDS)
                set_motion(avoid_turn, force=True)
            else:
                enter_state(State.BACKUP, BACKUP_SECONDS)
                set_motion("BACKWARD", force=True)
            return "EMERGENCY", front_gap

        if scan_info["danger"] or scan_info["front_blocked"]:
            avoid_turn, _, _ = choose_escape_turn(scan_info["points"])
            remember_turn_choice(avoid_turn)
            if both_sides_tight(scan_info):
                if not scan_info["rear_blocked"]:
                    enter_state(State.BACKUP, TRAPPED_BACKUP_SECONDS)
                    set_motion("BACKWARD", force=True)
                    return "TRAPPED_BACKUP", front_gap
                set_motion("STOP", force=True)
                return "TRAPPED_STOP", front_gap

            if scan_info["rear_blocked"] or not scan_info["danger"]:
                enter_state(State.AVOID, TURN_PULSE_SECONDS)
                set_motion(avoid_turn, force=True)
                return "AVOID_START", front_gap

            enter_state(State.BACKUP, BACKUP_SECONDS)
            set_motion("BACKWARD", force=True)
            return f"BACKUP_BEFORE_{avoid_turn}", front_gap

        if state == State.SEEK_LIGHT:
            if seek_started <= 0:
                seek_started = now

            if abs(current_lux - best_lux) <= LIGHT_FOUND_MARGIN:
                set_motion("STOP", force=True)
                return "SEEK_LIGHT_FOUND", front_gap

            if now - seek_started >= LIGHT_SEEK_SECONDS:
                set_motion("STOP", force=True)
                return "SEEK_LIGHT_TIMEOUT", front_gap

            seek_motion = choose_explore_clear_motion(scan_info, now)
            if seek_motion is not None:
                set_motion(seek_motion)
                return f"SEEK_{seek_motion}", front_gap

            set_motion("FORWARD")
            return "SEEK_FORWARD", front_gap

        if state == State.EXPLORE:
            explore_motion = choose_explore_clear_motion(scan_info, now)
            if explore_motion is not None:
                set_motion(explore_motion)
                return f"EXPLORE_{explore_motion}", front_gap

            bias = exploration_bias()
            if bias and not scan_info["front_blocked"]:
                set_motion(bias)
                return f"EXPLORE_BEST_{bias}", front_gap

        set_motion("FORWARD")
        return "FORWARD", front_gap

    if state == State.RETURN_TO_BEST:
        if current_lux >= best_lux - RETURN_STOP_MARGIN:
            seek_started = now
            enter_state(State.SEEK_LIGHT)
            set_motion("STOP", force=True)
            return "RETURN_LUX_FOUND", front_gap

        if return_index >= len(return_segments):
            seek_started = now
            enter_state(State.SEEK_LIGHT)
            set_motion("STOP", force=True)
            return "RETURN_DONE", front_gap

        active_return_motion = current_motion if return_until > 0.0 and now < return_until else None
        next_return_motion = active_return_motion or return_segments[return_index]["motion"]

        if next_return_motion == "BACKWARD" and scan_info["rear_blocked"]:
            set_motion("STOP", force=True)
            return_until = 0.0
            if active_return_motion is None:
                return_index += 1
            return "RETURN_REAR_BLOCK_SKIP", front_gap

        if next_return_motion != "BACKWARD" and (
            scan_info["emergency"] or scan_info["danger"] or scan_info["front_blocked"]
        ):
            if both_sides_tight(scan_info) and not scan_info["rear_blocked"]:
                resume_state = State.RETURN_TO_BEST
                enter_state(State.BACKUP, TRAPPED_BACKUP_SECONDS)
                set_motion("BACKWARD", force=True)
                return "RETURN_TRAPPED_BACKUP", front_gap

            avoid_turn, _, _ = choose_escape_turn(scan_info["points"])
            remember_turn_choice(avoid_turn)
            resume_state = State.RETURN_TO_BEST
            enter_state(State.AVOID, TURN_PULSE_SECONDS)
            set_motion(avoid_turn, force=True)
            return "RETURN_AVOID", front_gap

        if return_until == 0.0 or now >= return_until:
            segment = return_segments[return_index]
            return_until = now + segment["duration"]
            return_index += 1
            set_motion(segment["motion"], force=True)
            return f"RETURN_{segment['motion']}", front_gap

        set_motion(current_motion)
        return "RETURNING", front_gap

    if state == State.AVOID:
        if state_until and now >= state_until:
            if scan_info["clear"] or (not scan_info["danger"] and not scan_info["front_blocked"]):
                next_state = resume_state or (
                    State.EXPLORE if now - explore_started < EXPLORE_SECONDS else State.SEEK_LIGHT
                )
                resume_state = None
                enter_state(next_state)
                if next_state == State.RETURN_TO_BEST:
                    set_motion("STOP", force=True)
                    return_until = 0.0
                else:
                    set_motion("FORWARD", force=True)
                return "AVOID_DONE", front_gap

            avoid_turn, _, _ = choose_escape_turn(scan_info["points"])
            remember_turn_choice(avoid_turn)
            if both_sides_tight(scan_info) and not scan_info["rear_blocked"]:
                enter_state(State.BACKUP, TRAPPED_BACKUP_SECONDS)
                set_motion("BACKWARD", force=True)
                return "AVOID_TRAPPED_BACKUP", front_gap

            if turn_repeat_count >= AVOID_REPEAT_ESCAPE_COUNT:
                turn_repeat_count = 0
                if not scan_info["rear_blocked"]:
                    enter_state(State.BACKUP, TRAPPED_BACKUP_SECONDS)
                    set_motion("BACKWARD", force=True)
                    return "AVOID_REPEAT_BACKUP", front_gap

                enter_state(State.ESCAPE, ESCAPE_TURN_SECONDS)
                set_motion(avoid_turn, force=True)
                return "ESCAPE_REPEAT", front_gap

            if turn_repeat_count >= AVOID_REPEAT_BACKUP_COUNT and not scan_info["rear_blocked"]:
                enter_state(State.BACKUP, BACKUP_SECONDS)
                set_motion("BACKWARD", force=True)
                return "AVOID_SOFT_BACKUP", front_gap

            enter_state(State.AVOID, TURN_PULSE_SECONDS)
            set_motion(avoid_turn, force=True)
            return "AVOID_MORE", front_gap

        set_motion(avoid_turn)
        return "AVOIDING", front_gap

    if state == State.BACKUP:
        if state_until and now >= state_until:
            if (scan_info["front_blocked"] or scan_info["danger"]) and both_sides_tight(scan_info):
                if not scan_info["rear_blocked"]:
                    enter_state(State.BACKUP, TRAPPED_BACKUP_SECONDS)
                    set_motion("BACKWARD", force=True)
                    return "TRAPPED_BACKUP_MORE", front_gap
                set_motion("STOP", force=True)
                return "TRAPPED_STOP", front_gap

            if resume_state == State.RETURN_TO_BEST:
                enter_state(State.RETURN_TO_BEST)
                set_motion("STOP", force=True)
                return_until = 0.0
                resume_state = None
                return "BACKUP_RETURN_RESUME", front_gap

            enter_state(State.AVOID, TURN_PULSE_SECONDS)
            set_motion(avoid_turn, force=True)
            return "BACKUP_DONE", front_gap

        set_motion("BACKWARD")
        return "BACKING", front_gap

    if state == State.ESCAPE:
        if state_until and now >= state_until:
            enter_state(State.EXPLORE if now - explore_started < EXPLORE_SECONDS else State.SEEK_LIGHT)
            set_motion("FORWARD", force=True)
            return "ESCAPE_DONE", front_gap

        set_motion(avoid_turn)
        return "ESCAPING", front_gap

    set_motion("STOP")
    return "UNKNOWN", front_gap


def print_status(label, scan_info, front_gap):
    nearest = scan_info["nearest"]
    if nearest:
        nearest_text = f"x={nearest[2]:.0f} y={nearest[3]:.0f} gap={front_gap:.0f}"
    else:
        nearest_text = "front=clear"

    elapsed = elapsed_from_start(time.monotonic())
    best_elapsed = best_lux_time - explore_started if explore_started > 0 else 0.0
    lux_error = max(0.0, best_lux - current_lux)
    print(
        f"FSM={state.value} action={current_motion} {label} "
        f"t={elapsed:.1f}/{EXPLORE_SECONDS:.0f}s "
        f"LUX={current_lux:.1f} SOIL={current_soil:.1f}% "
        f"BEST={best_lux:.1f}@{best_elapsed:.1f}s ERR={lux_error:.1f} "
        f"{nearest_text} "
        f"L={scan_info['left_score']:.0f} R={scan_info['right_score']:.0f} "
        f"front_points={len(scan_info['front'])}"
    )


try:
    print("=" * 50)
    print("FSM lidar drive + light exploration")
    print("Remote key 1: start, key 2: stop")
    print(f"USE_DUMMY_LUX={USE_DUMMY_LUX} USE_DUMMY_SOIL={USE_DUMMY_SOIL}")
    print(f"LIDAR_POST={LIDAR_POST_ENABLED} url={ONPLANT_SERVER_URL} robot={ONPLANT_ROBOT_ID}")
    print("=" * 50)

    start_lidar_post_worker()

    init_lux_sensor()
    time.sleep(0.2)
    first_lux = read_lux_fast()
    if first_lux >= 0:
        current_lux = first_lux
        best_lux = first_lux
    current_soil = read_soil_fast()
    print(f"Initial light: {current_lux:.2f} lux, soil: {current_soil:.1f}%")

    lidar.stop()
    lidar.clean_input()
    time.sleep(0.5)
    lidar.start_motor()
    time.sleep(1.5)

    for scan in lidar.iter_scans(max_buf_meas=LIDAR_MAX_BUF_MEAS):
        now = time.monotonic()

        if now - last_key_read >= KEY_READ_INTERVAL:
            key = read_ir_key()
            last_key_read = now
        else:
            key = 0

        if key == START_KEY and state == State.IDLE:
            explore_started = now
            dummy_sensor_started = now
            explore_last_nudge = now
            seek_started = 0.0
            return_segments = []
            return_index = 0
            return_until = 0.0
            resume_state = None
            motion_log = []
            active_motion = "STOP"
            active_motion_started = now
            best_lux = current_lux
            best_lux_time = now
            best_motion_time = now
            enter_state(State.EXPLORE)
            set_motion("FORWARD", force=True)
            print("AUTO START: EXPLORE")
        elif key == STOP_KEY and state != State.IDLE:
            finalize_motion_log(now)
            enter_state(State.IDLE)
            set_motion("STOP", force=True)
            print("AUTO STOP")

        update_light(now)
        update_soil(now)
        scan_info = analyze_scan(scan)
        label, front_gap = fsm_step(scan_info, now)
        maybe_post_lidar(scan_info, now)

        if now - last_print >= PRINT_INTERVAL:
            print_status(label, scan_info, front_gap)
            last_print = now

except KeyboardInterrupt:
    print("\nInterrupted")

finally:
    set_motion("STOP", force=True)
    bot.Ctrl_IR_Switch(0)

    try:
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()
    except Exception:
        pass

    print("Finished")
