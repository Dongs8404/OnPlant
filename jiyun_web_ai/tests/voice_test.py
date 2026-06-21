import os
import subprocess
import speech_recognition as sr
from gtts import gTTS

from ai.chat_ai import ask_plant
from hardware.sensors import read_sensor_data
from ai.plant_status import check_plant_status
from db.database import get_recent_chat_logs, save_chat_log


def fix_stt_text(text):
    text = text.replace("바지랑", "바질아")
    text = text.replace("바지리", "바질이")
    text = text.replace("바질랑", "바질아")
    return text


def speak(text):
    print("바질이:", text)

    tts = gTTS(text=text, lang="ko")
    tts.save("robot_answer.mp3")

    subprocess.run([
        "mpg123",
        "robot_answer.mp3"
    ])


r = sr.Recognizer()

print("🎤 녹음 시작...")
os.system("arecord -D hw:3,0 -c 1 -f S16_LE -r 44100 -d 5 test.wav")

print("🧠 음성 인식 중...")

with sr.AudioFile("test.wav") as source:
    audio = r.record(source)

try:
    question = r.recognize_google(audio, language="ko-KR")
    question = fix_stt_text(question)

    print("나:", question)

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

    chat_history = get_recent_chat_logs(5)

    answer = ask_plant(
        question,
        plant,
        sensor,
        result["action_list"],
        chat_history
    )

    save_chat_log(question, answer)

    speak(answer)

except Exception as e:
    print("에러:", e)