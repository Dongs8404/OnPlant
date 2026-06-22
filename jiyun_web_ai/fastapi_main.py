from fastapi.responses import StreamingResponse, RedirectResponse
from camera.camera_manager import generate_frames
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.plant_status import check_plant_status
from ai.chat_ai import ask_plant
from hardware.sensors import read_sensor_logs
from db.mysql_database import (
    init_db,
    save_sensor_logs,
    save_plant_status,
    get_recent_sensor_logs,
    save_chat_log,
    get_recent_chat_logs,
    create_user,
    authenticate_user,
    get_usernames_by_password,
    verify_user_recovery_info,
    verify_user_and_reset_password,
    get_board_posts,
    get_board_post,
    create_board_post,
    update_board_post,
    delete_board_post,
    create_board_comment,
    get_board_comments,
    increment_post_likes
)

import os
import subprocess
from gtts import gTTS

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()

current_sensor = {}
current_plant = {}
current_action_list = []


class ChatRequest(BaseModel):
    message: str


def get_current_user(request):
    return request.cookies.get("onplant_user")


def redirect_to_login():
    return RedirectResponse(url="/login", status_code=303)

def get_voice_state():
    try:
        with open("voice_state.txt", "r") as f:
            return f.read().strip()
    except:
        return "idle"
    
def read_text_file(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return default


@app.get("/voice-status")
def voice_status():
    voice_state = read_text_file("voice_state.txt", "idle")
    voice_input = read_text_file("voice_input.txt", "")
    voice_response = read_text_file("voice_response.txt", "")

    return {
        "state": voice_state,
        "input": voice_input,
        "response": voice_response
    }

def speak_robot(text):
    output_path = "robot_voice.mp3"

    tts = gTTS(text=text, lang="ko")
    tts.save(output_path)

    subprocess.Popen([
        "mpg123",
        "-a",
        "hw:2,0",
        output_path
    ])


def calculate_health(sensor):
    score = 100

    if sensor["soil_moisture"] < 30:
        score -= 20
    elif sensor["soil_moisture"] > 70:
        score -= 10

    if sensor["temperature"] < 18:
        score -= 15
    elif sensor["temperature"] > 30:
        score -= 15

    if sensor["humidity"] < 40:
        score -= 10
    elif sensor["humidity"] > 80:
        score -= 10

    if sensor["light"] < 300:
        score -= 10
    elif sensor["light"] > 900:
        score -= 10

    return max(score, 0)


def get_soil_status(soil):
    if soil < 30:
        return "조금 목말라요"
    elif soil > 70:
        return "물이 많아요"
    else:
        return "딱 좋아요"


def get_temperature_status(temperature):
    if temperature < 18:
        return "조금 추워요"
    elif temperature > 30:
        return "조금 더워요"
    else:
        return "딱 좋아요"


def get_humidity_status(humidity):
    if humidity < 40:
        return "건조해요"
    elif humidity > 80:
        return "습해요"
    else:
        return "딱 좋아요"


def get_light_status(light):
    if light < 300:
        return "조금 부족해요"
    elif light > 900:
        return "너무 강해요"
    else:
        return "딱 좋아요"


@app.get("/")
def home(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    global current_sensor, current_plant, current_action_list

    sensor = read_sensor_logs()

    result = check_plant_status(
        sensor["soil_moisture"],
        sensor["temperature"],
        sensor["humidity"],
        sensor["light"]
    )

    health_score = calculate_health(sensor)

    save_sensor_logs(sensor)
    save_plant_status(result)

    recent_logs = get_recent_sensor_logs(10)
    recent_chats = get_recent_chat_logs(5)

    plant = {
        "name": "바질이",
        "mood": result["mood"],
        "message": result["message"],
        "image": result["image"]
    }

    current_sensor = sensor
    current_plant = plant
    current_action_list = result["action_list"]

    sensors = [
        {
            "icon": "droplet",
            "name": "수분",
            "status": get_soil_status(sensor["soil_moisture"]),
            "value": str(sensor["soil_moisture"]) + "%"
        },
        {
            "icon": "sun",
            "name": "햇빛",
            "status": get_light_status(sensor["light"]),
            "value": str(sensor["light"]) + " lx"
        },
        {
            "icon": "thermometer",
            "name": "온도",
            "status": get_temperature_status(sensor["temperature"]),
            "value": str(sensor["temperature"]) + "℃"
        },
        {
            "icon": "droplets",
            "name": "습도",
            "status": get_humidity_status(sensor["humidity"]),
            "value": str(sensor["humidity"]) + "%"
        }
    ]

    logs = [
        "💧 수분 상태를 확인했어요",
        "☀️ 햇빛 상태를 확인했어요",
        "💬 사용자에게 상태를 알려줬어요"
    ]

    status_display_list = []
    for s in result["status_list"]:
        if "수분" in s:
            icon = "droplet"
        elif "온도" in s:
            icon = "thermometer"
        elif "습도" in s:
            icon = "droplets"
        elif "조도" in s or "햇빛" in s:
            icon = "sun"
        else:
            icon = "circle-alert"
        status_display_list.append({"icon": icon, "text": s})

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "plant": plant,
            "sensor": sensor,
            "sensors": sensors,
            "logs": logs,
            "status_list": status_display_list,
            "status_icon_list": result["status_icon_list"],
            "action_list": result["action_list"],
            "recent_logs": recent_logs,
            "health_score": health_score,
            "recent_chats": recent_chats,
            "current_user": get_current_user(request)
        }
    )

@app.get("/face")
def face(request: Request):
    sensor = read_sensor_logs()

    result = check_plant_status(
        sensor["soil_moisture"],
        sensor["temperature"],
        sensor["humidity"],
        sensor["light"]
    )

    mood = result["mood"]

    if mood == "행복해요":
        mood_class = "happy"
    elif mood == "목말라요":
        mood_class = "thirsty"
    elif mood == "축축해요":
        mood_class = "thirsty"
    elif mood == "건조해요":
        mood_class = "thirsty"
    elif mood == "더워요":
        mood_class = "hot"
    elif mood == "추워요":
        mood_class = "cold"
    elif mood == "졸려요":
        mood_class = "sleepy"
    else:
        mood_class = "danger"

    return templates.TemplateResponse(
        request=request,
        name="face.html",
        context={
            "request": request,
            "mood_class": mood_class,
            "mood": mood
        }
    )


@app.get("/face-status")
def face_status():
    sensor = read_sensor_logs()

    result = check_plant_status(
        sensor["soil_moisture"],
        sensor["temperature"],
        sensor["humidity"],
        sensor["light"]
    )

    mood = result["mood"]

    if mood == "행복해요":
        mood_class = "happy"
    elif mood == "목말라요":
        mood_class = "thirsty"
    elif mood == "축축해요":
        mood_class = "thirsty"
    elif mood == "건조해요":
        mood_class = "thirsty"
    elif mood == "더워요":
        mood_class = "hot"
    elif mood == "추워요":
        mood_class = "cold"
    elif mood == "졸려요":
        mood_class = "sleepy"
    else:
        mood_class = "danger"

    voice_messages = {
        "행복해요": "오늘은 기분이 좋아요.",
        "목말라요": "물이 필요해요.",
        "축축해요": "물이 너무 많아요.",
        "건조해요": "공기가 조금 건조해요.",
        "더워요": "조금 더워요.",
        "추워요": "조금 추워요.",
        "졸려요": "햇빛을 보고 싶어요.",
        "도와주세요": "상태가 좋지 않아요."
    }

    voice_state = get_voice_state()

    if voice_state == "listening":
        mood_class = "danger"
        mood = "듣는 중"
    elif voice_state == "thinking":
        mood_class = "sleepy"
        mood = "생각 중"
    elif voice_state == "speaking":
        mood_class = "happy"
        mood = "말하는 중"

    return {
	 "mood": mood,
   	 "mood_class": mood_class,
   	 "voice": voice_messages.get(mood, "상태를 확인해주세요."),
   	 "action": result["action"],
   	 "action_message": result["action_message"]
}

@app.get("/chat")
def chat_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "request": request,
            "current_user": current_user
        }
    )


@app.get("/camera")
def camera_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()
    return templates.TemplateResponse(
        request=request,
        name="camera.html",
        context={
            "request": request,
            "current_user": current_user
        }
    )


@app.get("/logs")
def logs_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    recent_logs = get_recent_sensor_logs(20)
    recent_chats = get_recent_chat_logs(20)

    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "request": request,
            "recent_logs": recent_logs,
            "recent_chats": recent_chats,
            "current_user": current_user
        }
    )

@app.get("/settings")
def settings_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "request": request,
            "current_user": current_user
        }
    )


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "error": "",
            "current_user": get_current_user(request)
        }
    )


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username.strip(), password)

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "아이디 또는 비밀번호를 확인해 주세요.",
                "current_user": get_current_user(request)
            }
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("onplant_user", user, httponly=True)
    return response


@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "request": request,
            "error": "",
            "current_user": get_current_user(request)
        }
    )


@app.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    username = username.strip()
    email = email.strip()

    if len(username) < 2 or len(password) < 4:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "아이디는 2글자 이상, 비밀번호는 4글자 이상으로 입력해 주세요.",
                "current_user": get_current_user(request)
            }
        )

    if not create_user(username, password, email):
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "이미 사용 중인 아이디예요.",
                "current_user": get_current_user(request)
            }
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("onplant_user", username, httponly=True)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("onplant_user")
    return response


@app.post("/forgot-id")
def forgot_id(password: str = Form(...)):
    usernames = get_usernames_by_password(password)
    return {"usernames": usernames}


@app.post("/verify-recovery-info")
def verify_recovery_route(username: str = Form(...), email: str = Form(...)):
    valid = verify_user_recovery_info(username.strip(), email.strip())
    return {"valid": valid}


@app.post("/forgot-password")
def forgot_password(username: str = Form(...), email: str = Form(...), original_password: str = Form(...), new_password: str = Form(...)):
    success = verify_user_and_reset_password(username.strip(), email.strip(), original_password, new_password)
    return {"success": success}


@app.get("/board")
def board_page(request: Request, filter: str = None):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    posts = get_board_posts()
    is_filtered = False
    if filter == "my" and current_user:
        posts = [p for p in posts if p[2] == current_user]
        is_filtered = True

    return templates.TemplateResponse(
        request=request,
        name="board.html",
        context={
            "request": request,
            "posts": posts,
            "current_user": current_user,
            "is_filtered": is_filtered
        }
    )


@app.get("/board/new")
def board_new_page(request: Request):
    current_user = get_current_user(request)

    if not current_user:
        return redirect_to_login()

    return templates.TemplateResponse(
        request=request,
        name="board_form.html",
        context={
            "request": request,
            "mode": "new",
            "post": None,
            "current_user": current_user
        }
    )


@app.post("/board/new")
def board_create(request: Request, title: str = Form(...), content: str = Form(...), is_notice: int = Form(0)):
    current_user = get_current_user(request)

    if not current_user:
        return redirect_to_login()

    create_board_post(title.strip(), content.strip(), current_user, is_notice)
    return RedirectResponse(url="/board", status_code=303)


@app.get("/board/{post_id}")
def board_detail(request: Request, post_id: int):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    post = get_board_post(post_id)

    if not post:
        return RedirectResponse(url="/board", status_code=303)

    comments = get_board_comments(post_id)

    return templates.TemplateResponse(
        request=request,
        name="board_detail.html",
        context={
            "request": request,
            "post": post,
            "comments": comments,
            "current_user": current_user
        }
    )


@app.post("/board/{post_id}/comments")
def board_comment_create(request: Request, post_id: int, content: str = Form(...)):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    if content.strip():
        create_board_comment(post_id, current_user, content.strip())

    return RedirectResponse(url=f"/board/{post_id}", status_code=303)


@app.post("/board/{post_id}/like")
def board_like(request: Request, post_id: int):
    current_user = get_current_user(request)
    if not current_user:
        return redirect_to_login()

    increment_post_likes(post_id)
    return RedirectResponse(url=f"/board/{post_id}", status_code=303)


@app.get("/board/{post_id}/edit")
def board_edit_page(request: Request, post_id: int):
    current_user = get_current_user(request)
    post = get_board_post(post_id)

    if not current_user:
        return redirect_to_login()

    if not post or post[3] != current_user:
        return RedirectResponse(url="/board", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="board_form.html",
        context={
            "request": request,
            "mode": "edit",
            "post": post,
            "current_user": current_user
        }
    )


@app.post("/board/{post_id}/edit")
def board_update(request: Request, post_id: int, title: str = Form(...), content: str = Form(...), is_notice: int = Form(0)):
    current_user = get_current_user(request)
    post = get_board_post(post_id)

    if not current_user:
        return redirect_to_login()

    if not post or post[3] != current_user:
        return RedirectResponse(url="/board", status_code=303)

    update_board_post(post_id, title.strip(), content.strip(), is_notice)
    return RedirectResponse(url=f"/board/{post_id}", status_code=303)


@app.post("/board/{post_id}/delete")
def board_delete(request: Request, post_id: int):
    current_user = get_current_user(request)
    post = get_board_post(post_id)

    if not current_user:
        return redirect_to_login()

    if post and post[3] == current_user:
        delete_board_post(post_id)

    return RedirectResponse(url="/board", status_code=303)


@app.post("/chat")
def chat(data: ChatRequest):
    global current_sensor, current_plant, current_action_list

    if not current_sensor:
        current_sensor = read_sensor_logs()

    if not current_plant:
        current_plant = {
            "name": "바질이",
            "mood": "알 수 없음",
            "message": "아직 상태를 확인하는 중이에요.",
            "image": "basil_normal.png"
        }

    if not current_action_list:
        current_action_list = ["상태를 다시 확인해주세요"]

    question = data.message
    chat_history = get_recent_chat_logs(5)

    answer = ask_plant(
        question,
        current_plant,
        current_sensor,
        current_action_list,
        chat_history
    )

    save_chat_log(question, answer)

    speak_robot(answer)

    return {
        "answer": answer
    }

@app.get("/video_feed")
def video_feed(request: Request):
    if not get_current_user(request):
        from fastapi.responses import Response
        return Response(status_code=401)
    return StreamingResponse(
        generate_frames("plant"),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/video_feed/plant")
def video_feed_plant(request: Request):
    if not get_current_user(request):
        from fastapi.responses import Response
        return Response(status_code=401)
    return StreamingResponse(
        generate_frames("plant"),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/video_feed/user")
def video_feed_user(request: Request):
    if not get_current_user(request):
        from fastapi.responses import Response
        return Response(status_code=401)
    return StreamingResponse(
        generate_frames("user"),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/video_feed/user/yolo")
def video_feed_user_yolo(request: Request):
    if not get_current_user(request):
        from fastapi.responses import Response
        return Response(status_code=401)
    return StreamingResponse(
        generate_frames("user", yolo=True),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/video_feed/plant/yolo")
def video_feed_plant_yolo(request: Request):
    if not get_current_user(request):
        from fastapi.responses import Response
        return Response(status_code=401)
    return StreamingResponse(
        generate_frames("plant", yolo=True),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# 동현 수정
class SensorLogRequest(BaseModel):
    light: float
    robot_id: str = "rasbot"
    temperature: float = 25.0
    humidity: float = 50.0
    soil_moisture: float = 45.0


@app.post("/api/sensor")
@app.post("/sensor")
def api_save_sensor(data: SensorLogRequest):
    sensor = data.model_dump()
    save_sensor_logs(sensor)

    return {
        "result": "success",
        "data": sensor
    }
