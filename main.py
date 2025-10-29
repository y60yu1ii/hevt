#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import socket
import threading
import time
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests  # HTTP for LINE

# --------------------------------
# Python 版本檢查（建議 3.13.2+）
# --------------------------------
REQUIRED_PY = (3, 13, 2)
if sys.version_info < REQUIRED_PY:
    print(f"[WARN] Python {REQUIRED_PY[0]}.{REQUIRED_PY[1]}.{REQUIRED_PY[2]} 以上較佳，目前為 {sys.version.split()[0]}。")

# --------------------------------
# 本地設定檔（改為與此 Python 檔同目錄）
# --------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "line_config.json")
# 同目錄必然存在，無需 os.makedirs()

# --------------------------------
# 參數（預設值，可於 GUI 覆寫）
# --------------------------------
DEFAULT_BIND_IP = ""           # 留空 => 綁定所有介面 (0.0.0.0)
DEFAULT_STM32_IP = "192.168.5.11"
STM32_CMD_PORT = 1234
STM32_IMG_PORT = 1235
TEMP_MIN = 20
TEMP_MAX = 60
PIX_H, PIX_W = 24, 32

# --------------------------------
# Socket 與共享狀態
# --------------------------------
sock_cmd = None
sock_img = None
threads_started = False
sockets_ready = False

frame_data = np.zeros((PIX_H, PIX_W), dtype=np.float32)
diff_mask = np.zeros((PIX_H, PIX_W), dtype=int)
last_frame = np.zeros((PIX_H, PIX_W), dtype=np.float32)

# LINE 推播控制
last_alarm_state = 0           # 0: NORMAL, 1: OVER
_last_alert_at: datetime | None = None
line_lock = threading.Lock()

# --------------------------------
# Tk GUI
# --------------------------------
root = tk.Tk()
root.title("🔥 HEVT")
root.geometry("1180x680")

# 狀態變數
alarm_state_var = tk.StringVar(value="NORMAL")
max_temp_var  = tk.StringVar(value="000.00 °C")
min_temp_var  = tk.StringVar(value="000.00 °C")
avg_temp_var  = tk.StringVar(value="000.00 °C")
max_slope_var = tk.StringVar(value="000.00 °C")
avg_slope_var = tk.StringVar(value="000.00 °C")
over_count_var = tk.StringVar(value="000")
diff_area_var  = tk.StringVar(value="000")
avgTempT_var   = tk.StringVar(value="000.00")
maxSlopeT_var  = tk.StringVar(value="000.00")
diffAreaT_var  = tk.StringVar(value="000.00")

# 網路設定變數（可編輯）
bind_ip_var  = tk.StringVar(value=DEFAULT_BIND_IP)
stm32_ip_var = tk.StringVar(value=DEFAULT_STM32_IP)
local_ip_hint_var = tk.StringVar(value="Local IP: (unknown)")

# LINE 設定變數（可編輯）
line_enable_var = tk.BooleanVar(value=False)

# - 這兩個會從檔案載入/儲存
line_token_var   = tk.StringVar(value="")   # Channel Access Token（長 token）
line_secret_file_loaded = tk.StringVar(value="Secret: (not loaded)")

# - 目標對象：可同時填（都會推）
line_group_var   = tk.StringVar(value="")   # C...（groupId）
line_user_var    = tk.StringVar(value="")   # U...（userId）

# - 其它
line_tpl_var     = tk.StringVar(
    value="⚠️ 溫度警報：Max={max:.2f}°C, Avg={avg:.2f}°C, DiffArea={diff_area} @ {now}"
)
line_cooldown_var = tk.StringVar(value="60")  # 秒

# --------------------------------
# Matplotlib 熱像圖
# --------------------------------
fig, ax = plt.subplots(figsize=(4, 3))
img_artist = ax.imshow(frame_data, cmap='inferno', vmin=TEMP_MIN, vmax=TEMP_MAX)
ax.axis('off')
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().place(x=20, y=20)

# --------------------------------
# 資訊顯示區
# --------------------------------
frame_info = ttk.LabelFrame(root, text="Report Status")
frame_info.place(x=450, y=20, width=700, height=220)

alarm_label = tk.Label(frame_info, text="🟢 NORMAL", font=("Arial", 16), bg="green", fg="white")
alarm_label.grid(row=0, column=0, columnspan=6, pady=10, sticky="we")

ttk.Label(frame_info, text="Max Temp:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=max_temp_var, font=("Arial", 14)).grid(row=1, column=1, sticky="w")

ttk.Label(frame_info, text="Min Temp:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=min_temp_var, font=("Arial", 14)).grid(row=1, column=3, sticky="w")

ttk.Label(frame_info, text="Avg Temp:").grid(row=1, column=4, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=avg_temp_var, font=("Arial", 14)).grid(row=1, column=5, sticky="w")

ttk.Label(frame_info, text="Max Slope:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=max_slope_var, font=("Arial", 14)).grid(row=2, column=1, sticky="w")

ttk.Label(frame_info, text="Avg Slope:").grid(row=2, column=2, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=avg_slope_var, font=("Arial", 14)).grid(row=2, column=3, sticky="w")

ttk.Label(frame_info, text="Over Count:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=over_count_var, font=("Arial", 14)).grid(row=3, column=1, sticky="w")

ttk.Label(frame_info, text="Diff Area:").grid(row=3, column=2, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=diff_area_var, font=("Arial", 14)).grid(row=3, column=3, sticky="w")

ttk.Label(frame_info, text="avgT Trend:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=avgTempT_var, font=("Arial", 14)).grid(row=4, column=1, sticky="w")

ttk.Label(frame_info, text="maxSlope Trend:").grid(row=4, column=2, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=maxSlopeT_var, font=("Arial", 14)).grid(row=4, column=3, sticky="w")

ttk.Label(frame_info, text="diffArea Trend:").grid(row=4, column=4, sticky="w", padx=10, pady=5)
ttk.Label(frame_info, textvariable=diffAreaT_var, font=("Arial", 14)).grid(row=4, column=5, sticky="w")

# --------------------------------
# 網路設定區
# --------------------------------
frame_net = ttk.LabelFrame(root, text="Network Settings")
frame_net.place(x=20, y=360, width=410, height=220)

ttk.Label(frame_net, text="Bind IP (Local):").grid(row=0, column=0, padx=10, pady=8, sticky="e")
e_bind = ttk.Entry(frame_net, textvariable=bind_ip_var, width=18)
e_bind.grid(row=0, column=1, padx=5, pady=8, sticky="w")
ttk.Label(frame_net, text="(留空=0.0.0.0)").grid(row=0, column=2, padx=5, sticky="w")

ttk.Label(frame_net, text="STM32 IP (Remote):").grid(row=1, column=0, padx=10, pady=8, sticky="e")
e_stm = ttk.Entry(frame_net, textvariable=stm32_ip_var, width=18)
e_stm.grid(row=1, column=1, padx=5, pady=8, sticky="w")

local_ip_hint_var.set("Local IP: (unknown)")
ttk.Label(frame_net, textvariable=local_ip_hint_var).grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="w")

btn_apply = ttk.Button(frame_net, text="Apply Network", width=18)
btn_apply.grid(row=3, column=0, padx=10, pady=12, sticky="w")

btn_connect = ttk.Button(frame_net, text="Start/Connect", width=18)
btn_connect.grid(row=3, column=1, padx=5, pady=12, sticky="w")

# --------------------------------
# LINE 設定區（NEW）
# --------------------------------
frame_line = ttk.LabelFrame(root, text="LINE Settings (Messaging API)")
frame_line.place(x=450, y=260, width=700, height=200)

# 切換、冷卻、測試
ttk.Checkbutton(frame_line, text="Enable LINE Alert", variable=line_enable_var).grid(row=0, column=0, padx=10, pady=6, sticky="w")
ttk.Label(frame_line, text="Cooldown(s):").grid(row=0, column=2, padx=6, pady=4, sticky="e")
ttk.Entry(frame_line, textvariable=line_cooldown_var, width=8).grid(row=0, column=3, padx=6, pady=4, sticky="w")

# Token 與 Secret 檔
ttk.Label(frame_line, text="Channel Access Token:").grid(row=1, column=0, padx=10, pady=4, sticky="e")
ttk.Entry(frame_line, textvariable=line_token_var, width=46, show="•").grid(row=1, column=1, padx=6, pady=4, sticky="w")
ttk.Button(frame_line, text="Load/Save", command=lambda: on_config_dialog()).grid(row=1, column=2, padx=6, pady=4, sticky="w")
ttk.Label(frame_line, textvariable=line_secret_file_loaded, foreground="#666").grid(row=1, column=3, padx=6, pady=4, sticky="w")

# 目標：Group 與 User
ttk.Label(frame_line, text="Group ID (C...):").grid(row=2, column=0, padx=10, pady=4, sticky="e")
ttk.Entry(frame_line, textvariable=line_group_var, width=46).grid(row=2, column=1, padx=6, pady=4, sticky="w")

ttk.Label(frame_line, text="User ID (U...):").grid(row=3, column=0, padx=10, pady=4, sticky="e")
ttk.Entry(frame_line, textvariable=line_user_var, width=46).grid(row=3, column=1, padx=6, pady=4, sticky="w")

# Template & 測試
ttk.Label(frame_line, text="Template:").grid(row=4, column=0, padx=10, pady=4, sticky="e")
ttk.Entry(frame_line, textvariable=line_tpl_var, width=64).grid(row=4, column=1, columnspan=3, padx=6, pady=4, sticky="we")
ttk.Button(frame_line, text="Send Test", command=lambda: send_line_test_popup()).grid(row=0, column=1, padx=6, pady=4, sticky="w")

# --------------------------------
# 原「Threshold Settings」
# --------------------------------
frame_ctrl = ttk.LabelFrame(root, text="Threshold Settings")
frame_ctrl.place(x=450, y=470, width=700, height=170)

fields = ["Alarm", "Slope", "Diffusion", "Interval (ms)"]
default_values = {"Alarm": "30.0", "Slope": "2.0", "Diffusion": "1.2", "Interval (ms)": "100"}
entries = {}
for i, f in enumerate(fields):
    ttk.Label(frame_ctrl, text=f + ":").grid(row=i, column=0, padx=10, pady=5, sticky="w")
    e = ttk.Entry(frame_ctrl, width=10)
    e.insert(0, default_values.get(f, ""))
    e.grid(row=i, column=1, padx=10, pady=5)
    entries[f] = e

def require_cmd_socket():
    if not sockets_ready or sock_cmd is None:
        messagebox.showwarning("Network", "Socket 尚未就緒，請先在 Network Settings 中 Apply/Start。")
        return False
    return True

def set_threshold():
    if not require_cmd_socket(): return
    cmd = f"SET_THRESH:D1={entries['Alarm'].get()},D2={entries['Slope'].get()},D3={entries['Diffusion'].get()},D4={entries['Interval (ms)'].get()}"
    try:
        sock_cmd.sendto(cmd.encode(), (stm32_ip_var.get().strip(), STM32_CMD_PORT))
        print("[CMD] Sent:", cmd)
    except Exception as e:
        messagebox.showerror("Send Error", str(e))

ttk.Button(frame_ctrl, text="Set Threshold", command=set_threshold).grid(row=3, column=2, columnspan=1, pady=10)

def get_image():
    if not require_cmd_socket(): return
    cmd = "GET_IMAGE"
    try:
        sock_cmd.sendto(cmd.encode(), (stm32_ip_var.get().strip(), STM32_CMD_PORT))
        print("[CMD] Sent:", cmd)
    except Exception as e:
        messagebox.showerror("Send Error", str(e))
ttk.Button(frame_ctrl, text="Get Image", command=get_image).grid(row=5, column=0, columnspan=1, pady=10)

auto_flag = tk.BooleanVar(value=False)
def send_check(name, var):
    if not require_cmd_socket(): return
    value = 1 if var.get() else 0
    cmd = f"ENABLE_{name.upper()}={value}"
    try:
        sock_cmd.sendto(cmd.encode(), (stm32_ip_var.get().strip(), STM32_CMD_PORT))
        print("[CMD] Sent:", cmd)
    except Exception as e:
        messagebox.showerror("Send Error", str(e))

ttk.Checkbutton(frame_ctrl, text="Auto", variable=auto_flag, command=lambda: send_check("Auto", auto_flag)).grid(row=5, column=1, padx=10, pady=5, sticky="w")

# --------------------------------
# 內部工具
# --------------------------------
def get_local_ip_for(remote_ip: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((remote_ip, 9))  # 任意 UDP 埠
        return s.getsockname()[0]
    except Exception:
        return "(unknown)"
    finally:
        s.close()

def close_sockets():
    global sock_cmd, sock_img, sockets_ready
    sockets_ready = False
    for s in (sock_cmd, sock_img):
        try:
            if s:
                s.close()
        except Exception:
            pass
    sock_cmd = None
    sock_img = None

def apply_network():
    """套用 GUI 的 IP 設定並重新綁定 socket（尚不啟動接收執行緒）"""
    global sock_cmd, sock_img, sockets_ready

    bind_ip = bind_ip_var.get().strip()
    remote_ip = stm32_ip_var.get().strip()
    if not remote_ip:
        messagebox.showwarning("Network", "請輸入 STM32 IP")
        return

    close_sockets()

    try:
        # 指令 socket
        sc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sc.settimeout(1.0)
        sc.bind((bind_ip if bind_ip else "", STM32_CMD_PORT))

        # 影像 socket
        si = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        si.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        si.settimeout(2.0)
        si.bind((bind_ip if bind_ip else "", STM32_IMG_PORT))

        sock_cmd, sock_img = sc, si
        sockets_ready = True

        local_ip_hint_var.set(f"Local IP: {get_local_ip_for(remote_ip)}  (bind={bind_ip or '0.0.0.0'})")
        messagebox.showinfo("Network", "Socket 綁定成功。可按 Start/Connect 啟動接收。")
        print(f"[NET] bind=({bind_ip or '0.0.0.0'}) cmd:{STM32_CMD_PORT} img:{STM32_IMG_PORT} -> remote:{remote_ip}")
    except Exception as e:
        close_sockets()
        messagebox.showerror("Network Error", f"Socket 綁定失敗：{e}")

btn_apply.configure(command=apply_network)

# --------------------------------
# LINE Messaging API
# --------------------------------
def _line_push(token: str, to_id: str, text: str) -> bool:
    """呼叫 LINE Push，to_id 可為 U*/R*/C*；回 True 表成功"""
    if not token or not to_id:
        return False
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"to": to_id, "messages": [{"type": "text", "text": text}]}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=8)
        if r.status_code < 300:
            return True
        print("[LINE] push FAIL", r.status_code, r.text)
        return False
    except Exception as e:
        print("[LINE] push ERROR", e)
        return False

def format_line_text(tpl: str, stats: dict) -> str:
    try:
        return tpl.format(**stats)
    except Exception:
        return f"⚠️ 警報：Max={stats.get('max', 0):.2f}°C, Avg={stats.get('avg', 0):.2f}°C, DiffArea={stats.get('diff_area', 0)}"

def push_to_all_targets(text: str):
    token = line_token_var.get().strip()
    targets = []
    g = line_group_var.get().strip()
    u = line_user_var.get().strip()
    if g:
        targets.append(g)
    if u:
        targets.append(u)
    if not targets:
        print("[LINE] 無目標 id（Group/User）")
        return
    for t in targets:
        _line_push(token, t, text)


def maybe_send_line_alarm(max_val: float, avg_val: float, diff_area: int, alarm_now: int):
    """在 NORMAL→OVER 或冷卻期屆滿時觸發推送（對 group 與 user 同時）"""
    global last_alarm_state, _last_alert_at

    if not line_enable_var.get():
        last_alarm_state = alarm_now
        return

    token_ok = bool(line_token_var.get().strip())
    tgt_ok = bool(line_group_var.get().strip() or line_user_var.get().strip())
    if not token_ok or not tgt_ok:
        last_alarm_state = alarm_now
        return

    # 冷卻秒數
    try:
        cooldown = max(0, int(line_cooldown_var.get() or "0"))
    except Exception:
        cooldown = 0

    now = datetime.now()
    should_fire = False
    if alarm_now == 1 and last_alarm_state == 0:
        should_fire = True
    elif alarm_now == 1 and _last_alert_at is not None:
        should_fire = (now - _last_alert_at) >= timedelta(seconds=cooldown)

    if alarm_now == 1 and should_fire:
        stats = {
            "max": max_val, "avg": avg_val, "diff_area": diff_area,
            "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        text = format_line_text(line_tpl_var.get(), stats)

        def _worker():
            try:
                with line_lock:
                    push_to_all_targets(text)
                print("[LINE] pushed:", text)
            except Exception as e:
                print("[LINE ERROR]", e)

        threading.Thread(target=_worker, daemon=True).start()
        _last_alert_at = now

    last_alarm_state = alarm_now

# --------------------------------
# 設定檔 Load/Save（Channel Secret 放檔案）
# --------------------------------
def save_config():
    data = {
        "access_token": line_token_var.get().strip(),
        "channel_secret": "(stored)",  # 不把 secret 顯示在 UI；僅在檔案內保存/載入
        "group_id": line_group_var.get().strip(),
        "user_id": line_user_var.get().strip(),
        "template": line_tpl_var.get(),
        "cooldown": line_cooldown_var.get(),
    }
    # 若檔案已存在且含有 channel_secret，就保留舊 secret
    existing = {}
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f) or {}
        except Exception:
            existing = {}
    if "channel_secret" in existing and isinstance(existing["channel_secret"], str):
        data["channel_secret"] = existing["channel_secret"]

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    line_secret_file_loaded.set(f"Secret: (in {CONFIG_PATH})")
    messagebox.showinfo("Config", f"已儲存設定到 {CONFIG_PATH}")

def load_config():
    if not os.path.isfile(CONFIG_PATH):
        messagebox.showwarning("Config", f"找不到設定檔：{CONFIG_PATH}\n請先按 Save 建立，或自行建立 JSON。")
        return
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        # 載入 access token / 目標 / 模板 / 冷卻
        line_token_var.set(data.get("access_token", ""))
        line_group_var.set(data.get("group_id", ""))
        line_user_var.set(data.get("user_id", ""))
        line_tpl_var.set(data.get("template", line_tpl_var.get()))
        line_cooldown_var.set(str(data.get("cooldown", line_cooldown_var.get())))
        # 只顯示 secret 已載入，不顯示內容
        if "channel_secret" in data and isinstance(data["channel_secret"], str) and data["channel_secret"]:
            line_secret_file_loaded.set(f"Secret: (in {CONFIG_PATH})")
        else:
            line_secret_file_loaded.set("Secret: (not loaded)")
        messagebox.showinfo("Config", f"已從 {CONFIG_PATH} 載入設定")
    except Exception as e:
        messagebox.showerror("Config Error", f"讀取失敗：{e}")

def on_config_dialog():
    # 簡單：點一下就先 Load；再按一次 Save
    # 也可改成彈出對話框讓你輸入 Secret 後寫入檔案
    res = messagebox.askyesno("Config", f"從 {CONFIG_PATH} 載入？\n（選否改為儲存目前的 UI 值）")
    if res:
        load_config()
    else:
        # 若要寫入/更新 secret，可在這裡 prompt 一次
        # 為了簡潔，這裡只保存 UI 值；secret 請手動加到檔案中或用一次性小對話窗擴充
        save_config()

# --------------------------------
# GUI 更新
# --------------------------------
def update_gui(alarm, D1, D2, D3, D4, D5, D6, D7, D8, D9, D10):
    # UI
    if alarm:
        alarm_label.config(text="🔴 OVER TEMP", bg="red")
    else:
        alarm_label.config(text="🟢 NORMAL", bg="green")
    max_temp_var.set(f"{D1:.2f} °C")
    min_temp_var.set(f"{D2:.2f} °C")
    avg_temp_var.set(f"{D3:.2f} °C")
    max_slope_var.set(f"{D4:.2f} °C")
    avg_slope_var.set(f"{D5:.2f} °C")
    over_count_var.set(f"{D6}")
    diff_area_var.set(f"{D7}")
    avgTempT_var.set(f"{D8:.2f}")
    maxSlopeT_var.set(f"{D9:.2f}")
    diffAreaT_var.set(f"{D10:.2f}")

    # LINE：警報推送
    try:
        maybe_send_line_alarm(max_val=D1, avg_val=D3, diff_area=D7, alarm_now=int(alarm))
    except Exception as e:
        print("[LINE SEND GUARD ERROR]", e)

# --------------------------------
# 接收執行緒
# --------------------------------
def recv_thread():
    while True:
        try:
            if not sockets_ready or sock_cmd is None:
                time.sleep(0.1)
                continue
            data, addr = sock_cmd.recvfrom(2048)
            msg = data.decode(errors="ignore").strip()
            if msg.startswith("REPORT"):
                parts = msg.split(',')
                try:
                    alarm = int(parts[1].split('=')[1])
                    D1 = float(parts[2].split('=')[1])
                    D2 = float(parts[3].split('=')[1])
                    D3 = float(parts[4].split('=')[1])
                    D4 = float(parts[5].split('=')[1])
                    D5 = float(parts[6].split('=')[1])
                    D6 = int(parts[7].split('=')[1])
                    D7 = int(parts[8].split('=')[1])
                    D8 = float(parts[9].split('=')[1])
                    D9 = float(parts[10].split('=')[1])
                    D10 = float(parts[11].split('=')[1])
                    root.after(0, update_gui, alarm, D1, D2, D3, D4, D5, D6, D7, D8, D9, D10)
                except Exception as e:
                    print("[ERR] Parse REPORT:", e)
        except socket.timeout:
            continue
        except OSError:
            time.sleep(0.1)
        except Exception as e:
            print("[CMD RECV ERR]", e)
            time.sleep(0.1)

def udp_img_thread():
    global frame_data, diff_mask, last_frame
    while True:
        try:
            if not sockets_ready or sock_img is None:
                time.sleep(0.1)
                continue

            frame = np.zeros(PIX_H * PIX_W, dtype=np.float32)
            received = 0
            start_time = time.time()

            while received < PIX_H * PIX_W:
                data, addr = sock_img.recvfrom(2048)
                pixels = np.frombuffer(data, dtype=np.float32)
                n = min(len(pixels), PIX_H * PIX_W - received)
                frame[received:received+n] = pixels[:n]
                received += n
                if time.time() - start_time > 2.0:
                    print("[WARN] Timeout, incomplete frame")
                    break

            if received < PIX_H * PIX_W:
                continue

            frame_data = frame.reshape((PIX_H, PIX_W))
            diff_mask = np.abs(frame_data - last_frame) > 2.0
            last_frame = frame_data.copy()

            img_artist.set_data(frame_data)
            img_artist.set_clim(vmin=TEMP_MIN, vmax=TEMP_MAX)
            root.after_idle(canvas.draw_idle)

        except socket.timeout:
            continue
        except OSError:
            time.sleep(0.1)
        except Exception as e:
            print("[IMG RECV ERR]", e)
            time.sleep(0.1)
def _line_push(token: str, to_id: str, text: str):
    """呼叫 LINE Push，to_id 可為 U*/R*/C*；回傳 (ok, status, body)。"""
    if not token or not to_id:
        return (False, 0, "missing token or to_id")
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {token.strip()}", "Content-Type": "application/json"}
    payload = {"to": to_id.strip(), "messages": [{"type": "text", "text": text}]}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=8)
        ok = r.status_code < 300
        if not ok:
            print("[LINE] push FAIL", r.status_code, r.text)
        return (ok, r.status_code, r.text)
    except Exception as e:
        print("[LINE] push ERROR", e)
        return (False, -1, str(e))


def push_to_all_targets(text: str):
    token = line_token_var.get().strip()
    targets = []
    g = line_group_var.get().strip()
    u = line_user_var.get().strip()
    if g:
        targets.append(("Group/Room", g))
    if u:
        targets.append(("User", u))
    if not targets:
        return [("None", False, 0, "no target id")]
    results = []
    for label, t in targets:
        ok, status, body = _line_push(token, t, text)
        results.append((label, ok, status, body))
    return results


def send_line_test_popup():
    if not line_enable_var.get():
        messagebox.showwarning("LINE", "請先勾選 Enable LINE Alert")
        return
    if not line_token_var.get().strip():
        messagebox.showwarning("LINE", "請先填入 Channel Access Token（或從檔案載入）")
        return
    if not (line_group_var.get().strip() or line_user_var.get().strip()):
        messagebox.showwarning("LINE", "請先填入 Group ID 或 User ID 任一")
        return

    stats = {
        "max": 38.5, "min": 26.2, "avg": 33.0,
        "max_slope": 1.5, "avg_slope": 0.8,
        "over": 3, "diff_area": 42,
        "avgT": 0.0, "maxSlopeT": 0.0, "diffAreaT": 0.0,
        "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    text = "[TEST] " + format_line_text(line_tpl_var.get(), stats)

    results = push_to_all_targets(text)

    lines = []
    success_any = False
    for label, ok, status, body in results:
        success_any = success_any or ok
        lines.append(f"{label}: {'OK' if ok else 'FAIL'} (status={status})\n{body[:400]}")
    msg = "\n\n".join(lines)

    if success_any:
        messagebox.showinfo("LINE Push Result", msg)
    else:
        messagebox.showerror("LINE Push Failed", msg)

# --------------------------------
# 控制：Start/Connect
# --------------------------------
def start_connect():
    global threads_started
    if not sockets_ready:
        messagebox.showwarning("Network", "請先 Apply Network 完成綁定再 Start。")
        return
    if not threads_started:
        threading.Thread(target=recv_thread, daemon=True).start()
        threading.Thread(target=udp_img_thread, daemon=True).start()
        threads_started = True
        messagebox.showinfo("Network", "接收執行緒已啟動。")
    else:
        messagebox.showinfo("Network", "接收執行緒已在運行。")

btn_connect.configure(command=start_connect)
btn_apply.configure(command=apply_network)

# --------------------------------
# 開機自動載入設定（若存在）
# --------------------------------
if os.path.isfile(CONFIG_PATH):
    try:
        load_config()
    except Exception as e:
        print("[CONFIG] load on start error:", e)

# --------------------------------
# 主迴圈
# --------------------------------
root.mainloop()
