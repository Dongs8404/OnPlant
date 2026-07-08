# Onplant Hardware

Raspberry Pi robot-side code goes here.

Planned files:

```text
lidar_drive_only.py
lidar_fsm_drive.py
front_display_app.py
send_remote_key.py
sensor_check.py
dht_check.py
raspi_picamera2_to_pc.py
raspi_send_camera_to_pc.py
```

Robot-side responsibilities:

- LiDAR scan and FSM driving
- Raspbot expansion board motor/remote control
- Camera, front display, microphone, and speaker
- Optional direct I2C sensor checks
- Fetch latest light data from the server when sensors move to ESP32

## Front display

The 5-inch display must open the server display page. Do not use `127.0.0.1`
unless the FastAPI server is running on the Raspberry Pi itself.

Example when the server PC is on Wi-Fi `192.168.100.198`:

```bash
cd hardware
python3 front_display_app.py --server http://192.168.100.198:5050 --robot-id raspbot-a
```

The page polls:

```text
GET /api/robots/raspbot-a/display
```

Remote key behavior:

```text
3: show plant status report
4: show camera area
5: hide camera area
```

Manual test from Raspberry Pi:

```bash
python3 send_remote_key.py 3 --server http://192.168.100.198:5050 --robot-id raspbot-a
python3 send_remote_key.py 4 --server http://192.168.100.198:5050 --robot-id raspbot-a
python3 send_remote_key.py 5 --server http://192.168.100.198:5050 --robot-id raspbot-a
```

For boot auto-start, run `front_display_app.py` from the Raspberry Pi desktop
autostart or a systemd user service after the network is online.

## Recommended runtime split

Run the robot as two separate processes:

```text
onplant-display.service  opens the 5-inch display page in kiosk mode
onplant-drive.service    runs LiDAR/FSM driving code
```

This keeps the display alive even if the drive loop restarts, and the drive
loop can call `send_remote_key.py` or import `send_remote_key.send_remote_key`
when the physical remote receives keys 3, 4, or 5.

Install on Raspberry Pi:

```bash
cd hardware
chmod +x install_user_services.sh
./install_user_services.sh
```

Edit the server address if needed:

```bash
nano ~/.config/onplant/onplant-robot.env
```

Start only the display:

```bash
systemctl --user start onplant-display.service
```

When `lidar_fsm_drive.py` is ready:

```bash
systemctl --user enable --now onplant-drive.service
```

Check logs:

```bash
journalctl --user -u onplant-display.service -f
journalctl --user -u onplant-drive.service -f
```

If Chromium shows a first-run language or keyring popup, update
`front_display_app.py` on the Raspberry Pi and restart:

```bash
systemctl --user restart onplant-display.service
```
