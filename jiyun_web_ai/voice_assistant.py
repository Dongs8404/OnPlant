import os
import time
import subprocess
import speech_recognition as sr
from gtts import gTTS

from ai.chat_ai import ask_plant
from hardware.sensors import read_sensor_data
from ai.plant_status import check_plant_status
from db.database import get_recent_chat_logs, save_chat_log


WAKE_WORDS = [
    "하이 오피",
    "하이오피",
    "하이 오피야",
    "오피"
]

last_alert = ""
last_alert_time = 0
ALERT_COOLDOWN = 60


def write_text_file(filename, text):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)


def set_voice_state(state):
    write_text_file("voice_state.txt", state)


def set_voice_input(text):
    write_text_file("voice_input.txt", text)


def set_voice_response(text):
    write_text_file("voice_response.txt", text)


def clear_voice_text():
    set_voice_input("")
    set_voice_response("")


def fix_stt_text(text):
    text = text.replace("바지랑", "바질아")
    text = text.replace("바지리", "바질이")
    text = text.replace("바질랑", "바질아")
    text = text.replace("바지리야", "바질아")
    text = text.replace("바지야", "바질아")
    return text


def speak(text):
    set_voice_state("speaking")
    set_voice_response(text)

    print("🌱 오피:", text)

    tts = gTTS(text=text, lang="ko")
    tts.save("robot_answer.mp3")

    subprocess.run(["mpg123", "robot_answer.mp3"])

    set_voice_state("idle")


def listen(seconds=3):
    set_voice_state("listening")

    r = sr.Recognizer()

    print("\n🎤 듣는 중...")

    os.system(
        f"arecord -D hw:3,0 -c 1 -f S16_LE -r 44100 -d {seconds} voice_input.wav"
    )

    print("🧠 음성 인식 중...")

    with sr.AudioFile("voice_input.wav") as source:
        audio = r.record(source)

    text = r.recognize_google(audio, language="ko-KR")
    text = fix_stt_text(text)

    set_voice_input(text)

    return text


def get_plant_context():
    sensor = read_sensor_data()

    result = check_plant_status(
        sensor["soil"],
        sensor["temperature"],
        sensor["humidity"],
        sensor["light"]
    )

    plant = {
        "name": "바질이",
        "mood": result["mood"],
        "message": result["message"],
        "image": result["image"]
    }

    return sensor, result, plant


def ask_basil(question):
    set_voice_state("thinking")
    set_voice_input(question)

    sensor, result, plant = get_plant_context()

    chat_history = get_recent_chat_logs(5)

    answer = ask_plant(
        question,
        plant,
        sensor,
        result["action_list"],
        chat_history
    )

    save_chat_log(question, answer)
    set_voice_response(answer)

    return answer


def has_wake_word(text):
    return any(word in text for word in WAKE_WORDS)


def check_plant_alert():
    global last_alert, last_alert_time

    now = time.time()

    if now - last_alert_time < ALERT_COOLDOWN:
        return

    sensor, result, plant = get_plant_context()

    alert_type = ""
    alert_message = ""

    if sensor["soil"] < 30:
        alert_type = "soil"
        alert_message = "주인님, 물이 조금 필요해요."

    elif sensor["light"] < 300:
        alert_type = "light"
        alert_message = "주인님, 햇빛이 부족해요."

    elif sensor["temperature"] > 30:
        alert_type = "hot"
        alert_message = "주인님, 조금 더워요."

    elif sensor["temperature"] < 18:
        alert_type = "cold"
        alert_message = "주인님, 조금 추워요."

    if alert_type and alert_type != last_alert:
        speak(alert_message)
        last_alert = alert_type
        last_alert_time = now

    elif not alert_type:
        last_alert = ""


print("🌱 On-Plant 음성 대화 모드 시작")
print("호출어: 하이 오피")
print("종료하려면 Ctrl + C")

set_voice_state("idle")
clear_voice_text()

speak("안녕하세요. 오피 음성 대화를 시작할게요.")

waiting_wake_word = True

while True:
    try:
        check_plant_alert()

        question = listen(seconds=3)
        print("🙋 나:", question)

        if "종료" in question or "그만" in question:
            speak("알겠어요. 음성 대화를 종료할게요.")
            set_voice_state("idle")
            break

        if waiting_wake_word:
            if has_wake_word(question):
                clear_voice_text()
                speak("네, 오피가 듣고 있어요.")
                waiting_wake_word = False
            else:
                print("호출어 없음. 대기 중...")
                set_voice_state("idle")
            continue

        answer = ask_basil(question)
        speak(answer)

        waiting_wake_word = True

    except KeyboardInterrupt:
        print("\n종료됨")
        set_voice_state("idle")
        break

    except Exception as e:
        print("인식 실패:", e)
        set_voice_state("idle")
        continue