# OnPlant Server

Dummy-first FastAPI web app for the OnPlant robot project.

Current MVP:

- Robot ID based dashboard, without login
- Sensor ingest and dummy sensor generation
- Plant health summary and care recommendation
- Live camera placeholder with configurable stream URL
- Sensor history chart/table
- Speaker, display, drive, LiDAR speed, and exploration settings
- Robot command log
- Care board for management notes
- JSON file persistence through `onplant_state.json`

## Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Send dummy readings

From the server page, press `Send dummy` or `Auto: off`.

From a terminal:

```bash
python send_dummy_sensor.py --url http://127.0.0.1:8000/api/sensors --interval 2 --count 10
```

From Raspberry Pi or ESP32, POST JSON to:

```text
POST /api/sensors
```

Example body:

```json
{
  "robot_id": "raspbot-a",
  "robot_key": "optional-secret",
  "lux": 345.2,
  "temperature": 24.8,
  "humidity": 58.1,
  "soil_moisture": 42.0,
  "source": "esp32"
}
```

Useful API endpoints:

```text
GET    /api/health
POST   /api/sensors
POST   /api/sensors/dummy
GET    /api/sensors/latest
GET    /api/sensors/history?limit=100
DELETE /api/sensors/history
```
