# app_yellowx_yolo.py
# Detect a single class "yellow_x" on three AirSim cameras using Ultralytics YOLOv8.
# pip install ultralytics opencv-python numpy airsim

import os, re, socket, subprocess, shlex, time
from collections import defaultdict

import cv2
import numpy as np
import airsim

# ---------- CONFIG ----------
WEIGHTS = "yellow_x_best.pt"   # <-- put your trained weights here
CLASS_NAME = "yellow_x"        # single class in your model

VEHICLES = ["Drone_1", "Drone_2", "Drone_3"]
CAM_NAME  = "down"
IMG_W, IMG_H = 640, 360
RPC_PORT = 41451

CONF_THRESH = 0.35
IOU_THRESH  = 0.45
PERSIST_FRAMES = 2         # require N consecutive frames to confirm
PROCESS_EVERY_N = 1        # set 2–3 to cut CPU
SAVE_DIR = "yellowx_snaps"
os.makedirs(SAVE_DIR, exist_ok=True)

# ---------- AirSim helpers ----------
def resolve_airsim_host():
    try:
        out = subprocess.check_output(shlex.split("ip route")).decode()
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[0] == "default" and "eth0" in parts:
                return parts[2]
    except Exception:
        pass
    env_ip = os.getenv("AIRSIM_HOST")
    if env_ip:
        return env_ip
    try:
        with open("/etc/resolv.conf") as f:
            m = re.search(r"nameserver (\d+\.\d+\.\d+\.\d+)", f.read())
            if m:
                return m.group(1)
    except Exception:
        pass
    return "127.0.0.1"

def quick_port_check(ip, port, timeout=1.5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(timeout)
        s.connect((ip, port)); s.close(); return True
    except Exception:
        return False

def get_image(client, vehicle_name, cam_name):
    req = [airsim.ImageRequest(cam_name, airsim.ImageType.Scene, False, False)]
    resp = client.simGetImages(req, vehicle_name=vehicle_name)
    if not resp or resp[0].height == 0:
        return None
    img1d = np.frombuffer(resp[0].image_data_uint8, dtype=np.uint8)
    bgr = img1d.reshape(resp[0].height, resp[0].width, 3)
    if (bgr.shape[1], bgr.shape[0]) != (IMG_W, IMG_H):
        bgr = cv2.resize(bgr, (IMG_W, IMG_H), interpolation=cv2.INTER_AREA)
    return bgr

# ---------- YOLO ----------
class YellowXDetector:
    def __init__(self, weights):
        from ultralytics import YOLO
        if not os.path.exists(weights):
            raise FileNotFoundError(f"YOLO weights not found: {weights}")
        self.model = YOLO(weights)
        self.names = {int(k):v for k,v in self.model.names.items()}

    def infer(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        res = self.model.predict(
            source=rgb, imgsz=640, conf=CONF_THRESH, iou=IOU_THRESH, verbose=False
        )
        boxes = []
        for r in res:
            if r.boxes is None: 
                continue
            xyxy = r.boxes.xyxy.cpu().numpy()
            cls  = r.boxes.cls.cpu().numpy().astype(int)
            conf = r.boxes.conf.cpu().numpy()
            for (x1,y1,x2,y2), c, cf in zip(xyxy, cls, conf):
                name = self.names.get(int(c), f"id{int(c)}")
                if name != CLASS_NAME:
                    continue
                boxes.append((int(x1), int(y1), int(x2-x1), int(y2-y1), float(cf)))
        return boxes

# ---------- Main ----------
def main():
    host = resolve_airsim_host()
    print(f"[airsim] connecting {host}:{RPC_PORT}")
    if not quick_port_check(host, RPC_PORT):
        print("[error] cannot reach AirSim RPC. Start Unreal/AirSim and allow firewall.")
        return
    client = airsim.MultirotorClient(ip=host)
    client.confirmConnection()
    print("[airsim] RPC connected")

    try:
        detector = YellowXDetector(WEIGHTS)
    except Exception as e:
        print("[fatal] could not load YOLO weights:", e)
        return

    persist = {v: 0 for v in VEHICLES}
    last_save = {v: 0.0 for v in VEHICLES}
    frame_ctr = defaultdict(int)

    cv2.namedWindow("Yellow-X (D1|D2|D3)", cv2.WINDOW_NORMAL)

    while True:
        tiles = []
        now = time.time()
        for v in VEHICLES:
            bgr = get_image(client, v, CAM_NAME)
            if bgr is None:
                canvas = np.zeros((IMG_H, IMG_W, 3), np.uint8)
                cv2.putText(canvas, f"{v}: no image", (20, IMG_H//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
                tiles.append(canvas); continue

            frame_ctr[v] += 1
            vis = bgr.copy()
            is_hit = False
            boxes = []

            if frame_ctr[v] % PROCESS_EVERY_N == 0:
                boxes = detector.infer(bgr)
                if boxes:
                    persist[v] += 1
                else:
                    persist[v] = 0
                is_hit = persist[v] >= PERSIST_FRAMES

                for (x,y,w,h,cf) in boxes:
                    cv2.rectangle(vis, (x,y), (x+w,y+h), (0,255,255), 2)
                    cv2.putText(vis, f"{CLASS_NAME}:{cf:.2f}", (x, max(0,y-6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 3, cv2.LINE_AA)
                    cv2.putText(vis, f"{CLASS_NAME}:{cf:.2f}", (x, max(0,y-6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 1, cv2.LINE_AA)

                if is_hit and (now - last_save[v] > 1.0):
                    path = os.path.join(SAVE_DIR, f"{v}_{int(now)}.jpg")
                    cv2.imwrite(path, vis); last_save[v] = now
                    print(f"[SAVE] {path}")

            hud = f"{v}  Yellow-X:{'YES' if is_hit else 'no'} ({persist[v]}/{PERSIST_FRAMES})"
            cv2.putText(vis, hud, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(vis, hud, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0,255,0) if is_hit else (0,255,255), 2)
            tiles.append(vis)

        grid = cv2.hconcat(tiles)
        cv2.imshow("Yellow-X (D1|D2|D3)", grid)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q')):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
