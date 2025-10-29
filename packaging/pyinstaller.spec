# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 不依賴 __file__，用工作目錄（請確保是在 repo 根目錄執行 pyinstaller）
PROJECT_ROOT = os.getcwd()
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "main.py")

hiddenimports = collect_submodules("matplotlib") + collect_submodules("numpy")
datas = collect_data_files("matplotlib", include_py_files=True)

# 如果根目錄有 line_config.json，順手打包進去（可選）
CFG = os.path.join(PROJECT_ROOT, "line_config.json")
if os.path.exists(CFG):
    datas.append((CFG, "."))  # 放在 dist/HEVT/ 旁邊

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[PROJECT_ROOT],
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
    console=False,      # Tkinter GUI → 不要黑視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
