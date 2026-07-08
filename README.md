# OnPlant

OnPlant is a Raspberry Pi based plant-care robot project.

The repository is split into two main parts:

- `server/`: FastAPI web server and static dashboard
- `robot/`: Raspberry Pi robot, LiDAR, sensor, camera, display, and movement code

## Server

```bash
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 5050
```

Open:

```text
http://localhost:5050
```

## Robot

Robot-side code is under `robot/`.

Important entry points:

- `robot/lidar_fsm_drive.py`: LiDAR based driving loop
- `robot/send_sensor_to_server.py`: sensor upload script
- `robot/hardware/front_display_app.py`: Raspberry Pi display kiosk
- `robot/hardware/send_remote_key.py`: remote key event sender

Example:

```bash
cd robot
python3 lidar_fsm_drive.py
```

Runtime settings should be kept in local environment files and should not be committed.

## Notes

- Generated files, virtual environments, logs, and `.env` files are ignored.
- The current GitHub repository keeps only project source code: `server/` and `robot/`.
