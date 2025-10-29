PY=python3
VENV=.venv

.PHONY: setup run clean build-mac

setup:
	$(PY) -m venv $(VENV)
	. $(VENV)/bin/activate && python -m pip install --upgrade pip && pip install -r requirements.txt

run:
	. $(VENV)/bin/activate && python main.py

clean:
	rm -rf build dist *.spec
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Optional: macOS 本機也可用 PyInstaller 產單檔 (會是 Mach-O，不是 .exe)
build-mac:
	. $(VENV)/bin/activate && pip install pyinstaller && \
	pyinstaller --noconfirm --onefile --windowed \
	--name "STM32-Thermal-Monitor" main.py

