# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 專案根目錄（spec 在 packaging/，主程式在上層）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")

# 為了在 CI 上穩一點，把 matplotlib / numpy 的隱式相依與資料帶進來
hiddenimports = collect_submodules("matplotlib") + collect_submodules("numpy")
datas = collect_data_files("matplotlib", include_py_files=True)

# 若專案根目錄有 line_config.json，包進去（可選）
CFG = os.path.join(BASE_DIR, "line_config.json")
if os.path.exists(CFG):
    datas.append((CFG, "."))  # 放在 dist 同層

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="HEVT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,      # Tkinter GUI → 關閉主控台視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # 有圖示就換路徑
)