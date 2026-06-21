# On-Plant Developer Guide

## 1. Document Information

| Item              | Description              |
| ----------------- | ------------------------ |
| Project Name      | On-Plant                 |
| Project Type      | AI Companion Plant Robot |
| Main Platform     | PC, Raspberry Pi 5       |
| Backend Framework | FastAPI                  |
| Database          | SQLite                   |
| Last Updated      | 2026-06-10               |

---

## 2. Project Overview

On-Plant is an AI-based companion plant robot system that monitors plant status, provides voice interaction, displays facial expressions, manages sensor records, and supports a web dashboard.

The system is designed to combine plant care, AI conversation, real-time monitoring, and robot interaction into one integrated service.

---

## 3. System Roles

### 3.1 PC Server

The PC server is mainly used for development and web dashboard management.

Main responsibilities:

* Web dashboard
* Voice chat UI
* Logs page
* Settings page
* AI interaction API
* SQLite data management
* Frontend development and testing

Recommended local development URL:

```text
http://127.0.0.1:8010
```

---

### 3.2 Raspberry Pi 5

The Raspberry Pi 5 is used as the robot-side device.

Main responsibilities:

* Robot face display
* Camera Module 3
* USB microphone
* USB speaker
* Sensor reading
* Voice assistant
* Robot-side UI
* Future motor control and light tracking

Recommended robot-side URL:

```text
http://localhost:8000
```

External access example:

```text
http://192.168.100.89:8000
```

---

## 4. Hardware Environment

| Device                       | Usage                           |
| ---------------------------- | ------------------------------- |
| Raspberry Pi 5               | Robot control and robot-side UI |
| Raspberry Pi Camera Module 3 | Camera input                    |
| USB Microphone               | Voice input                     |
| USB Speaker                  | Voice output                    |
| Soil Moisture Sensor         | Soil moisture monitoring        |
| Temperature Sensor           | Temperature monitoring          |
| Humidity Sensor              | Humidity monitoring             |
| Light Sensor                 | Light level monitoring          |
| Touch Display                | Robot face and robot UI display |

---

## 5. Software Environment

### 5.1 PC Environment

| Item            | Version / Tool        |
| --------------- | --------------------- |
| OS              | Windows               |
| Editor          | Visual Studio Code    |
| Language        | Python                |
| Backend         | FastAPI               |
| Frontend        | HTML, CSS, JavaScript |
| Database        | SQLite                |
| Browser         | Chrome                |
| Version Control | Git, GitHub           |

---

### 5.2 Raspberry Pi Environment

| Item              | Tool              |
| ----------------- | ----------------- |
| OS                | Raspberry Pi OS   |
| Camera Tool       | rpicam            |
| Camera Library    | libcamera         |
| Voice Recognition | SpeechRecognition |
| Text-to-Speech    | gTTS              |
| Audio Playback    | mpg123            |
| Image Processing  | OpenCV            |
| Backend           | FastAPI           |

---

## 6. Project Directory Structure

```text
on_plant_ai/
│
├── ai/
│   ├── chat_ai.py
│   └── plant_status.py
│
├── db/
│   └── database.py
│
├── hardware/
│   └── sensors.py
│
├── static/
│   ├── style.css
│   ├── face.css
│   ├── script.js
│   ├── garden_bg.png
│   ├── images/
│   └── basil_status/
│
├── templates/
│   ├── index.html
│   ├── chat.html
│   ├── camera.html
│   ├── logs.html
│   ├── settings.html
│   └── face.html
│
├── fastapi_main.py
├── voice_assistant.py
├── requirements.txt
├── README.md
├── DEVELOPER_GUIDE.md
└── .gitignore
```

---

## 7. Installation Guide

### 7.1 Raspberry Pi System Packages

Run the following commands on Raspberry Pi:

```bash
sudo apt update
sudo apt install git -y
sudo apt install python3-pip -y
sudo apt install python3-venv -y
sudo apt install python3-opencv -y
sudo apt install mpg123 -y
```

---

### 7.2 Camera Test

Check whether the Raspberry Pi Camera Module 3 is recognized:

```bash
rpicam-hello
```

Take a test image:

```bash
rpicam-still -o test.jpg
```

Check the generated file:

```bash
file test.jpg
```

Expected result:

```text
JPEG image data
```

---

### 7.3 Python Package Installation

Use a virtual environment when possible.

Create virtual environment:

```bash
python3 -m venv venv
```

Activate virtual environment:

```bash
source venv/bin/activate
```

Install Python packages:

```bash
pip install fastapi
pip install uvicorn
pip install jinja2
pip install gtts
pip install SpeechRecognition
pip install pydantic
pip install python-multipart
```

If OpenCV is needed on Raspberry Pi, prefer the following command instead of pip:

```bash
sudo apt install python3-opencv -y
```

---

## 8. Running the Project

### 8.1 Run PC Development Server

On PC:

```bash
python -m uvicorn fastapi_main:app --reload --port 8010
```

Access pages:

```text
http://127.0.0.1:8010/
http://127.0.0.1:8010/chat
http://127.0.0.1:8010/logs
http://127.0.0.1:8010/settings
http://127.0.0.1:8010/camera
```

---

### 8.2 Run Raspberry Pi Server

On Raspberry Pi:

```bash
cd ~/on-plant-ai
python3 -m uvicorn fastapi_main:app --host 0.0.0.0 --port 8000
```

Access from Raspberry Pi:

```text
http://localhost:8000
```

Access from PC:

```text
http://192.168.100.89:8000
```

---

### 8.3 Run Voice Assistant

On Raspberry Pi:

```bash
python3 voice_assistant.py
```

Voice assistant workflow:

```text
Wake word: "하이 오피"
↓
Listening
↓
Thinking
↓
Speaking
↓
Return to idle
```

---

## 9. Main Routes

| Route           | Description                  |
| --------------- | ---------------------------- |
| `/`             | Main dashboard               |
| `/chat`         | Voice chat UI                |
| `/logs`         | Sensor and chat logs         |
| `/settings`     | Settings page                |
| `/camera`       | Camera page                  |
| `/face`         | Robot face page              |
| `/face-status`  | Robot face status API        |
| `/voice-status` | Voice state and subtitle API |

---

## 10. Voice State Files

The voice assistant and web UI communicate using text files.

| File                 | Description            |
| -------------------- | ---------------------- |
| `voice_state.txt`    | Current voice state    |
| `voice_input.txt`    | Recognized user speech |
| `voice_response.txt` | AI response text       |

Available voice states:

```text
idle
listening
thinking
speaking
```

---

## 11. Database

Database type:

```text
SQLite
```

Main data:

| Data          | Description                                 |
| ------------- | ------------------------------------------- |
| Sensor data   | Soil moisture, temperature, humidity, light |
| Plant status  | Plant mood and status result                |
| Chat log      | User question and AI response               |
| Dashboard log | Dashboard-related records                   |

---

## 12. Git Workflow

Check current status:

```bash
git status
```

Stage changes:

```bash
git add .
```

Commit changes:

```bash
git commit -m "Commit message"
```

Push to GitHub:

```bash
git push origin main
```

Pull latest changes:

```bash
git pull origin main
```

---

## 13. Development Rules

### 13.1 UI Rules

* Keep the same visual style across all pages.
* Use the existing On-Plant theme.
* Keep pastel colors, rounded cards, dashed borders, and soft visual elements.
* Do not replace the current design with a Bootstrap-like dashboard.
* Maintain consistency between dashboard, voice chat, logs, settings, and camera pages.

---

### 13.2 Code Rules

* Provide complete code when modifying files.
* Avoid partial snippets when replacing major files.
* Separate HTML, CSS, JavaScript, and Python logic clearly.
* Avoid unnecessary duplication.
* Keep file names and route names consistent.

---

## 14. Development Progress

| Feature                     | Status      |
| --------------------------- | ----------- |
| Main Dashboard              | In progress |
| Voice Chat UI               | In progress |
| Logs Page                   | In progress |
| Settings Page               | In progress |
| Face Page                   | Working     |
| Camera Module 3 Recognition | Working     |
| Camera Streaming            | Planned     |
| PC Voice Control            | Planned     |
| Light Tracking              | Planned     |
| Robot Movement              | Planned     |
| YOLO Plant Analysis         | Planned     |

---

## 15. Future Development Plan

Planned next features:

1. Camera streaming with Camera Module 3
2. Camera page UI integration
3. Dashboard live camera preview
4. PC web voice command support
5. Raspberry Pi and PC voice state synchronization
6. YOLO-based plant image analysis
7. Light tracking
8. Manual control mode
9. Automatic robot movement
10. Full system integration

---

## 16. Troubleshooting

### 16.1 CSS Changes Are Not Applied

Use hard refresh:

```text
Ctrl + F5
```

Or add version query:

```text
/static/style.css?v=2
```

---

### 16.2 Port Already in Use

Check running process:

```bash
ps -ef | grep uvicorn
```

Stop uvicorn:

```bash
pkill -f uvicorn
```

Restart server:

```bash
python3 -m uvicorn fastapi_main:app --host 0.0.0.0 --port 8000
```

---

### 16.3 Camera Not Found

Check camera connection and run:

```bash
rpicam-hello
```

If the camera is recognized, the sensor name should appear as:

```text
imx708
```

---

### 16.4 Raspberry Pi IP Changed

Check Raspberry Pi IP:

```bash
hostname -I
```

Use the returned IP address when accessing from PC.

---

## 17. Notes

This document should be updated whenever the project structure, installation steps, hardware configuration, or execution method changes.
