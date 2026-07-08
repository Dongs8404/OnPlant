from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import choices, uniform
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_PATH = Path(os.getenv("ONPLANT_DATA", BASE_DIR / "onplant_state.json"))

app = FastAPI(title="OnPlant Server", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=4, max_length=128)
    display_name: str = Field(default="사용자", min_length=1, max_length=32)
    plant_name: str = Field(default="토로예", min_length=1, max_length=64)


class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=4, max_length=128)


class UserPublic(BaseModel):
    username: str
    display_name: str
    robot_id: str
    role: str = "user"


class RobotCreate(BaseModel):
    robot_id: str = Field(min_length=1, max_length=64)
    name: str = Field(default="Raspbot A", min_length=1, max_length=64)
    plant_name: str = Field(default="나의 반려 식물", min_length=1, max_length=64)
    robot_key: str | None = Field(default=None, max_length=128)
    camera_url: str = Field(default="", max_length=300)


class RobotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    plant_name: str | None = Field(default=None, min_length=1, max_length=64)
    plant_avatar: str | None = Field(default=None, max_length=300000)
    camera_url: str | None = Field(default=None, max_length=300)


class RobotPublic(BaseModel):
    robot_id: str
    name: str
    plant_name: str
    plant_avatar: str = ""
    camera_url: str = ""
    created_at: str
    last_seen: str | None = None
    link_code: str = ""
    assigned_username: str | None = None


class SensorReadingIn(BaseModel):
    robot_id: str = Field(default="raspbot-a", min_length=1, max_length=64)
    robot_key: str | None = Field(default=None, max_length=128)
    lux: float | None = Field(default=None, ge=0)
    temperature: float | None = Field(default=None)
    humidity: float | None = Field(default=None, ge=0, le=100)
    soil_moisture: float | None = Field(default=None, ge=0, le=100)
    source: str = Field(default="dummy", min_length=1, max_length=64)


class StoredReading(BaseModel):
    id: int
    robot_id: str
    lux: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    soil_moisture: float | None = None
    source: str
    received_at: str


class LidarPoint(BaseModel):
    x: float
    y: float
    distance: float | None = None
    angle: float | None = None
    ignored: bool = False


class LidarFrameIn(BaseModel):
    points: list[LidarPoint] = Field(default_factory=list, max_length=720)
    state: str = Field(default="UNKNOWN", max_length=32)
    action: str = Field(default="STOP", max_length=32)
    current_lux: float | None = None
    best_lux: float | None = None
    lux_error: float | None = None
    best_time: float = 0.0
    explore_elapsed: float = 0.0
    return_index: int = 0
    return_total: int = 0
    return_avoid_count: int = 0
    return_elapsed: float = 0.0
    seek_elapsed: float = 0.0
    seek_seconds: float = 0.0
    pose_x: float | None = None
    pose_y: float | None = None
    heading: str | None = Field(default=None, max_length=16)
    best_x: float | None = None
    best_y: float | None = None
    blocked_count: int = 0
    front_blocked: bool = False
    danger: bool = False
    emergency: bool = False
    front_points: int = 0
    left_score: float | None = None
    right_score: float | None = None
    source: str = Field(default="raspberry-pi", max_length=64)


class StoredLidarFrame(LidarFrameIn):
    robot_id: str
    received_at: str


class RobotConfig(BaseModel):
    speaker_volume: int = Field(default=60, ge=0, le=100)
    display_brightness: int = Field(default=80, ge=0, le=100)
    display_text: str = Field(default="OnPlant", max_length=80)
    drive_enabled: bool = False
    explore_seconds: int = Field(default=50, ge=5, le=600)
    lidar_speed: int = Field(default=45, ge=0, le=100)
    camera_enabled: bool = True
    camera_url: str = Field(default="", max_length=300)


class CommandIn(BaseModel):
    command: str = Field(min_length=1, max_length=64)
    value: str | int | float | bool | None = None


class StoredCommand(CommandIn):
    id: int
    robot_id: str
    created_at: str


class BoardPostIn(BaseModel):
    category: str = Field(default="공지", min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=1000)
    author: str = Field(default="관리자", min_length=1, max_length=32)
    author_username: str = Field(default="admin", min_length=1, max_length=32)


class BoardPostUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=24)
    title: str | None = Field(default=None, min_length=1, max_length=80)
    body: str | None = Field(default=None, min_length=1, max_length=1000)


class BoardPost(BoardPostIn):
    id: int
    created_at: str
    updated_at: str | None = None



class MoveLogIn(BaseModel):
    state: str = Field(default="UNKNOWN", max_length=32)
    action: str = Field(default="STOP", max_length=32)
    message: str = Field(default="", max_length=200)
    target_lux: float | None = None
    current_lux: float | None = None
    source: str = Field(default="fsm", max_length=64)


class StoredMoveLog(MoveLogIn):
    id: int
    robot_id: str
    created_at: str


class DisplayState(BaseModel):
    screen: str = Field(default="idle", max_length=32)
    camera_visible: bool = False
    updated_at: str
    report_until: str | None = None


class RemoteIn(BaseModel):
    key: str = Field(min_length=1, max_length=8)


_lock = Lock()
_next_sensor_id = 1
_next_command_id = 1
_next_post_id = 1
_robots: dict[str, RobotPublic] = {}
_users: dict[str, dict[str, str]] = {}
_configs: dict[str, RobotConfig] = {}
_history: dict[str, deque[StoredReading]] = defaultdict(lambda: deque(maxlen=500))
_commands: dict[str, deque[StoredCommand]] = defaultdict(lambda: deque(maxlen=100))
_board_posts: deque[BoardPost] = deque(maxlen=200)
_lidar_latest: dict[str, StoredLidarFrame] = {}
_move_logs: dict[str, deque[StoredMoveLog]] = defaultdict(lambda: deque(maxlen=200))
_display_states: dict[str, DisplayState] = {}
_next_move_log_id = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _robot_link_code(robot_id: str) -> str:
    digest = hashlib.sha1(robot_id.encode("utf-8")).hexdigest().upper()
    return f"OP-{digest[:4]}-{digest[4:8]}"


def _plant_profile() -> dict[str, Any]:
    return {
        "species": "하월시아",
        "lux_target": 900,
        "lux_range": "800~1000 lux",
        "temperature_range": "18~28°C",
        "humidity_range": "35~60%",
        "soil_moisture_range": "20~45%",
        "note": "테스트베드에서는 조도를 900 lux 기준으로 맞춰 관찰합니다.",
    }


def _normalize_board_category(category: str | None) -> str:
    return "자유게시판" if category == "자유게시판" else "공지"


def _user_public(username: str) -> UserPublic:
    user = _users[username]
    return UserPublic(
        username=user["username"],
        display_name=user["display_name"],
        robot_id=user["robot_id"],
        role=user.get("role", "admin" if username == "admin" else "user"),
    )


def _default_robot() -> None:
    if "raspbot-a" not in _robots:
        _robots["raspbot-a"] = RobotPublic(
            robot_id="raspbot-a",
            name="Raspbot A",
            plant_name="토로예",
            created_at=_now_iso(),
            link_code=_robot_link_code("raspbot-a"),
            assigned_username="demo",
        )
    if not _robots["raspbot-a"].link_code:
        _robots["raspbot-a"].link_code = _robot_link_code("raspbot-a")
    if "raspbot-a" not in _configs:
        _configs["raspbot-a"] = RobotConfig()
    if "demo" not in _users:
        _users["demo"] = {
            "username": "demo",
            "display_name": "사용자",
            "password_hash": _hash_password("1234"),
            "robot_id": "raspbot-a",
            "role": "user",
        }
    else:
        _users["demo"].setdefault("role", "user")
    if "admin" not in _users:
        _users["admin"] = {
            "username": "admin",
            "display_name": "관리자",
            "password_hash": _hash_password("1234"),
            "robot_id": "raspbot-a",
            "role": "admin",
        }
    else:
        _users["admin"].setdefault("role", "admin")


def _ensure_robot(robot_id: str) -> None:
    if robot_id not in _robots:
        _robots[robot_id] = RobotPublic(
            robot_id=robot_id,
            name=robot_id,
            plant_name="나의 반려 식물",
            created_at=_now_iso(),
            link_code=_robot_link_code(robot_id),
        )
    if not _robots[robot_id].link_code:
        _robots[robot_id].link_code = _robot_link_code(robot_id)
    if robot_id not in _configs:
        _configs[robot_id] = RobotConfig(camera_url=_robots[robot_id].camera_url)


def _serialize_state() -> dict[str, Any]:
    return {
        "next_sensor_id": _next_sensor_id,
        "next_command_id": _next_command_id,
        "next_post_id": _next_post_id,
        "robots": {key: value.model_dump() for key, value in _robots.items()},
        "users": _users,
        "configs": {key: value.model_dump() for key, value in _configs.items()},
        "history": {
            key: [item.model_dump() for item in values]
            for key, values in _history.items()
        },
        "commands": {
            key: [item.model_dump() for item in values]
            for key, values in _commands.items()
        },
        "board_posts": [item.model_dump() for item in _board_posts],
        "move_logs": {key: [item.model_dump() for item in values] for key, values in _move_logs.items()},
        "display_states": {key: value.model_dump() for key, value in _display_states.items()},
        "next_move_log_id": _next_move_log_id,
    }


def _save_state() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(_serialize_state(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_state() -> None:
    global _next_sensor_id, _next_command_id, _next_post_id, _next_move_log_id

    if not DATA_PATH.exists():
        _default_robot()
        _board_posts.extend(
            [
                BoardPost(
                    id=1,
                    category="공지",
                    title="조도 탐색 테스트 순서",
                    body="센서값이 안정적으로 들어오는지 확인한 뒤 탐색 시간을 50초로 두고 주행 로그를 비교합니다.",
                    author="OnPlant",
                    created_at=_now_iso(),
                ),
                BoardPost(
                    id=2,
                    category="공지",
                    title="라즈봇 I2C 확인",
                    body="BH1750이 0x23으로 잡히면 Pi I2C는 정상입니다. 확장보드 주소는 별도로 확인합니다.",
                    author="OnPlant",
                    created_at=_now_iso(),
                ),
            ]
        )
        _next_post_id = 3
        _save_state()
        return

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    _next_sensor_id = int(data.get("next_sensor_id", 1))
    _next_command_id = int(data.get("next_command_id", 1))
    _next_post_id = int(data.get("next_post_id", 1))
    _next_move_log_id = int(data.get("next_move_log_id", 1))

    _robots.clear()
    for key, value in data.get("robots", {}).items():
        _robots[key] = RobotPublic(**value)

    _users.clear()
    _users.update(data.get("users", {}))

    _configs.clear()
    for key, value in data.get("configs", {}).items():
        _configs[key] = RobotConfig(**value)

    _history.clear()
    for key, values in data.get("history", {}).items():
        _history[key] = deque((StoredReading(**item) for item in values), maxlen=500)

    _commands.clear()
    for key, values in data.get("commands", {}).items():
        _commands[key] = deque((StoredCommand(**item) for item in values), maxlen=100)

    _board_posts.clear()
    for item in data.get("board_posts", []):
        item["category"] = _normalize_board_category(item.get("category"))
        item.setdefault("updated_at", None)
        item.setdefault("author_username", "admin")
        _board_posts.append(BoardPost(**item))

    _move_logs.clear()
    for key, values in data.get("move_logs", {}).items():
        _move_logs[key] = deque((StoredMoveLog(**item) for item in values), maxlen=200)

    _display_states.clear()
    for key, value in data.get("display_states", {}).items():
        _display_states[key] = DisplayState(**value)
    _default_robot()


def _append_move_log_locked(robot_id: str, log: MoveLogIn) -> StoredMoveLog:
    global _next_move_log_id
    stored = StoredMoveLog(
        id=_next_move_log_id,
        robot_id=robot_id,
        created_at=_now_iso(),
        **log.model_dump(),
    )
    _next_move_log_id += 1
    _move_logs[robot_id].append(stored)
    return stored


def _latest_for(robot_id: str) -> StoredReading | None:
    items = _history.get(robot_id)
    return items[-1] if items else None


def _status_from(reading: StoredReading | None) -> dict[str, str]:
    if not reading:
        return {
            "level": "대기",
            "tone": "idle",
            "emoji": "⏳",
            "message": "아직 수신된 센서 데이터가 없습니다.",
            "recommendation": "더미 데이터를 보내거나 라즈베리파이 센서 POST를 연결하세요.",
        }

    problems: list[str] = []
    if reading.temperature is not None and not 18 <= reading.temperature <= 28:
        problems.append("온도")
    if reading.humidity is not None and not 35 <= reading.humidity <= 60:
        problems.append("습도")
    if reading.lux is not None and not 800 <= reading.lux <= 1000:
        problems.append("조도")
    if reading.soil_moisture is not None and not 20 <= reading.soil_moisture <= 45:
        problems.append("토양수분")

    if not problems:
        return {
            "level": "건강",
            "tone": "good",
            "emoji": "😊",
            "message": "식물이 매우 건강한 상태입니다.",
            "recommendation": "햇빛과 물을 적절히 받고 있어요. 지금처럼 관리해 주세요.",
        }

    label = ", ".join(problems)
    return {
        "level": "주의",
        "tone": "warn",
        "emoji": "🙂",
        "message": f"{label} 값을 확인해야 합니다.",
        "recommendation": f"{label} 범위가 적정값에서 벗어났습니다. 환경을 조정하고 다음 데이터를 확인하세요.",
    }


def _display_screen_for_robot(robot_id: str) -> str:
    return "idle"


def _report_is_active(state: DisplayState) -> bool:
    if not state.report_until:
        return False
    try:
        return datetime.fromisoformat(state.report_until) > datetime.now(timezone.utc)
    except ValueError:
        return False


def _display_state_for_response(robot_id: str, state: DisplayState) -> DisplayState:
    screen = "report" if _report_is_active(state) else _display_screen_for_robot(robot_id)
    return state.model_copy(update={"screen": screen})


def _dummy_reading(robot_id: str) -> SensorReadingIn:

    return SensorReadingIn(
        robot_id=robot_id,
        lux=round(uniform(220.0, 720.0), 1),
        temperature=round(uniform(21.0, 26.0), 1),
        humidity=round(uniform(42.0, 62.0), 1),
        soil_moisture=round(uniform(34.0, 66.0), 1),
        source="dummy",
    )


_load_state()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/display")
def display_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "display.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=UserPublic)
def register_user(user: UserCreate) -> UserPublic:
    with _lock:
        if user.username in _users:
            raise HTTPException(status_code=409, detail="username already exists")
        robot_id = f"{user.username}-robot"
        _robots[robot_id] = RobotPublic(
            robot_id=robot_id,
            name=f"{user.display_name}의 라즈봇",
            plant_name=user.plant_name,
            created_at=_now_iso(),
        )
        _configs[robot_id] = RobotConfig()
        _users[user.username] = {
            "username": user.username,
            "display_name": user.display_name,
            "password_hash": _hash_password(user.password),
            "robot_id": robot_id,
        }
        _save_state()
        return _user_public(user.username)


@app.post("/api/auth/login", response_model=UserPublic)
def login_user(login: LoginIn) -> UserPublic:
    with _lock:
        user = _users.get(login.username)
        if not user or user["password_hash"] != _hash_password(login.password):
            raise HTTPException(status_code=401, detail="invalid username or password")
        _ensure_robot(user["robot_id"])
        return _user_public(login.username)


@app.get("/api/robots", response_model=list[RobotPublic])
def list_robots() -> list[RobotPublic]:
    with _lock:
        return sorted(_robots.values(), key=lambda item: item.robot_id)


@app.post("/api/robots", response_model=RobotPublic)
def create_robot(robot: RobotCreate) -> RobotPublic:
    with _lock:
        if robot.robot_id in _robots:
            raise HTTPException(status_code=409, detail="robot_id already exists")
        public = RobotPublic(
            robot_id=robot.robot_id,
            name=robot.name,
            plant_name=robot.plant_name,
            camera_url=robot.camera_url,
            created_at=_now_iso(),
        )
        _robots[robot.robot_id] = public
        _configs[robot.robot_id] = RobotConfig(camera_url=robot.camera_url)
        _save_state()
        return public


@app.patch("/api/robots/{robot_id}", response_model=RobotPublic)
def update_robot(robot_id: str, robot: RobotUpdate) -> RobotPublic:
    with _lock:
        _ensure_robot(robot_id)
        current = _robots[robot_id]
        if robot.name is not None:
            current.name = robot.name
        if robot.plant_name is not None:
            current.plant_name = robot.plant_name
        if robot.plant_avatar is not None:
            current.plant_avatar = robot.plant_avatar
        if robot.camera_url is not None:
            current.camera_url = robot.camera_url
            _configs[robot_id].camera_url = robot.camera_url
        _save_state()
        return current


@app.get("/api/robots/{robot_id}/summary")
def robot_summary(robot_id: str) -> dict[str, Any]:
    with _lock:
        _ensure_robot(robot_id)
        latest = _latest_for(robot_id)
        return {
            "robot": _robots[robot_id],
            "latest": latest,
            "config": _configs[robot_id],
            "status": _status_from(latest),
            "history_count": len(_history.get(robot_id, [])),
            "command_count": len(_commands.get(robot_id, [])),
            "plant_profile": _plant_profile(),
            "display": _display_states.get(robot_id) or DisplayState(updated_at=_now_iso()),
        }


@app.post("/api/robots/{robot_id}/lidar", response_model=StoredLidarFrame)
def receive_lidar_frame(robot_id: str, frame: LidarFrameIn) -> StoredLidarFrame:
    with _lock:
        _ensure_robot(robot_id)
        stored = StoredLidarFrame(
            robot_id=robot_id,
            received_at=_now_iso(),
            **frame.model_dump(),
        )
        _lidar_latest[robot_id] = stored
        _robots[robot_id].last_seen = stored.received_at
        _append_move_log_locked(
            robot_id,
            MoveLogIn(
                state=frame.state,
                action=frame.action,
                message=("전방 위험 감지" if frame.front_blocked or frame.danger or frame.emergency else "FSM 주행 상태 갱신"),
                target_lux=frame.best_lux,
                current_lux=frame.current_lux,
                source=frame.source,
            ),
        )
        _save_state()
        return stored


@app.get("/api/robots/{robot_id}/lidar", response_model=StoredLidarFrame | None)
def latest_lidar_frame(robot_id: str) -> StoredLidarFrame | None:
    with _lock:
        return _lidar_latest.get(robot_id)


@app.post("/api/sensors", response_model=StoredReading)
def receive_sensor(reading: SensorReadingIn) -> StoredReading:
    global _next_sensor_id

    with _lock:
        _ensure_robot(reading.robot_id)
        stored = StoredReading(
            id=_next_sensor_id,
            robot_id=reading.robot_id,
            lux=reading.lux,
            temperature=reading.temperature,
            humidity=reading.humidity,
            soil_moisture=reading.soil_moisture,
            source=reading.source,
            received_at=_now_iso(),
        )
        _next_sensor_id += 1
        _history[reading.robot_id].append(stored)
        _robots[reading.robot_id].last_seen = stored.received_at
        _save_state()
        return stored


@app.post("/api/sensors/dummy", response_model=StoredReading)
def create_dummy_sensor(robot_id: str = "raspbot-a") -> StoredReading:
    return receive_sensor(_dummy_reading(robot_id))


@app.get("/api/robots/{robot_id}/history", response_model=list[StoredReading])
def sensor_history(robot_id: str, limit: int = 100) -> list[StoredReading]:
    limit = max(1, min(limit, 500))
    with _lock:
        return list(_history.get(robot_id, []))[-limit:]


@app.delete("/api/robots/{robot_id}/history")
def clear_sensor_history(robot_id: str) -> dict[str, Any]:
    with _lock:
        count = len(_history.get(robot_id, []))
        _history[robot_id].clear()
        _save_state()
        return {"robot_id": robot_id, "cleared": count}


@app.get("/api/robots/{robot_id}/config", response_model=RobotConfig)
def get_robot_config(robot_id: str) -> RobotConfig:
    with _lock:
        _ensure_robot(robot_id)
        return _configs[robot_id]


@app.patch("/api/robots/{robot_id}/config", response_model=RobotConfig)
def update_robot_config(robot_id: str, config: RobotConfig) -> RobotConfig:
    with _lock:
        _ensure_robot(robot_id)
        _configs[robot_id] = config
        _robots[robot_id].camera_url = config.camera_url
        _save_state()
        return config


@app.post("/api/robots/{robot_id}/commands", response_model=StoredCommand)
def create_robot_command(robot_id: str, command: CommandIn) -> StoredCommand:
    global _next_command_id

    with _lock:
        _ensure_robot(robot_id)
        stored = StoredCommand(
            id=_next_command_id,
            robot_id=robot_id,
            created_at=_now_iso(),
            **command.model_dump(),
        )
        _next_command_id += 1
        _commands[robot_id].append(stored)
        _save_state()
        return stored


@app.get("/api/robots/{robot_id}/commands", response_model=list[StoredCommand])
def list_robot_commands(robot_id: str, limit: int = 30) -> list[StoredCommand]:
    limit = max(1, min(limit, 100))
    with _lock:
        return list(_commands.get(robot_id, []))[-limit:]


@app.get("/api/board", response_model=list[BoardPost])
def list_board_posts(category: str | None = None) -> list[BoardPost]:
    with _lock:
        posts = list(_board_posts)
        if category and category != "전체":
            target = _normalize_board_category(category)
            posts = [post for post in posts if post.category == target]
        return posts


@app.post("/api/board", response_model=BoardPost)
def create_board_post(post: BoardPostIn) -> BoardPost:
    global _next_post_id

    with _lock:
        data = post.model_dump()
        data["category"] = _normalize_board_category(data.get("category"))
        stored = BoardPost(id=_next_post_id, created_at=_now_iso(), **data)
        _next_post_id += 1
        _board_posts.appendleft(stored)
        _save_state()
        return stored


@app.get("/api/board/{post_id}", response_model=BoardPost)
def get_board_post(post_id: int) -> BoardPost:
    with _lock:
        for post in _board_posts:
            if post.id == post_id:
                return post
        raise HTTPException(status_code=404, detail="post not found")


@app.patch("/api/board/{post_id}", response_model=BoardPost)
def update_board_post(post_id: int, update: BoardPostUpdate) -> BoardPost:
    with _lock:
        for index, post in enumerate(_board_posts):
            if post.id == post_id:
                patched = post.model_copy(
                    update={
                        **({"category": update.category} if update.category is not None else {}),
                        **({"title": update.title} if update.title is not None else {}),
                        **({"body": update.body} if update.body is not None else {}),
                        "updated_at": _now_iso(),
                    }
                )
                patched.category = _normalize_board_category(patched.category)
                _board_posts[index] = patched
                _save_state()
                return patched
        raise HTTPException(status_code=404, detail="post not found")


@app.delete("/api/board/{post_id}")
def delete_board_post(post_id: int) -> dict[str, int]:
    with _lock:
        remaining = [post for post in _board_posts if post.id != post_id]
        removed = len(_board_posts) - len(remaining)
        _board_posts.clear()
        _board_posts.extend(remaining)
        _save_state()
        return {"deleted": removed}


@app.get("/api/robots/{robot_id}/move-logs", response_model=list[StoredMoveLog])
def list_move_logs(robot_id: str, limit: int = 80) -> list[StoredMoveLog]:
    limit = max(1, min(limit, 200))
    with _lock:
        return list(_move_logs.get(robot_id, []))[-limit:]


@app.post("/api/robots/{robot_id}/move-logs", response_model=StoredMoveLog)
def create_move_log(robot_id: str, log: MoveLogIn) -> StoredMoveLog:
    with _lock:
        _ensure_robot(robot_id)
        stored = _append_move_log_locked(robot_id, log)
        _save_state()
        return stored


@app.get("/api/robots/{robot_id}/display", response_model=DisplayState)
def get_display_state(robot_id: str) -> DisplayState:
    with _lock:
        _ensure_robot(robot_id)
        if robot_id not in _display_states:
            _display_states[robot_id] = DisplayState(updated_at=_now_iso())
        return _display_state_for_response(robot_id, _display_states[robot_id])


@app.post("/api/robots/{robot_id}/remote", response_model=DisplayState)
def remote_button(robot_id: str, remote: RemoteIn) -> DisplayState:
    with _lock:
        _ensure_robot(robot_id)
        current = _display_states.get(robot_id) or DisplayState(updated_at=_now_iso())
        if remote.key == "3":
            current.screen = "report"
            current.report_until = (datetime.now(timezone.utc) + timedelta(seconds=12)).isoformat()
        elif remote.key == "4":
            current.camera_visible = True
        elif remote.key == "5":
            current.camera_visible = False
        else:
            raise HTTPException(status_code=400, detail="unsupported remote key")
        current.updated_at = _now_iso()
        _display_states[robot_id] = current
        response = _display_state_for_response(robot_id, current)
        _commands[robot_id].append(StoredCommand(id=0, robot_id=robot_id, command=f"remote-{remote.key}", value=response.screen, created_at=current.updated_at))
        _save_state()
        return response


@app.get("/api/admin/users")
def admin_users() -> list[dict[str, str]]:
    with _lock:
        return [
            {
                "username": user["username"],
                "display_name": user.get("display_name", user["username"]),
                "robot_id": user.get("robot_id", ""),
                "role": user.get("role", "admin" if user["username"] == "admin" else "user"),
            }
            for user in sorted(_users.values(), key=lambda item: item["username"])
        ]


@app.post("/api/admin/link-robot", response_model=UserPublic)
def admin_link_robot(payload: dict[str, str]) -> UserPublic:
    username = payload.get("username", "").strip()
    code = payload.get("link_code", "").strip().upper()
    robot_id = payload.get("robot_id", "").strip()
    with _lock:
        if username not in _users:
            raise HTTPException(status_code=404, detail="user not found")
        if code:
            for robot in _robots.values():
                if robot.link_code.upper() == code:
                    robot_id = robot.robot_id
                    break
        if not robot_id:
            raise HTTPException(status_code=400, detail="robot_id or link_code required")
        _ensure_robot(robot_id)
        _users[username]["robot_id"] = robot_id
        _robots[robot_id].assigned_username = username
        _save_state()
        return _user_public(username)


@app.get("/api/sensors/latest", response_model=StoredReading | None)
def latest_sensor_compat() -> StoredReading | None:
    with _lock:
        return _latest_for("raspbot-a")


@app.get("/api/sensors/history", response_model=list[StoredReading])
def sensor_history_compat(limit: int = 100) -> list[StoredReading]:
    return sensor_history("raspbot-a", limit)


@app.delete("/api/sensors/history")
def clear_sensor_history_compat() -> dict[str, Any]:
    return clear_sensor_history("raspbot-a")
