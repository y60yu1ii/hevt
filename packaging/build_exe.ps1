param(
  [string]$PythonExe = "python"
)

# 建議用 PowerShell 以系統安裝的 Python 或 venv 執行
$ErrorActionPreference = "Stop"

Write-Host "Upgrading pip and installing requirements..."
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt
& $PythonExe -m pip install pyinstaller

Write-Host "Building with PyInstaller..."
& $PythonExe -m PyInstaller --noconfirm packaging\pyinstaller.spec

Write-Host "`nBuild done. Check dist\STM32-Thermal-Monitor(.exe)."

