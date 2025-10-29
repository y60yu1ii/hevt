#!/usr/bin/env python3
import os
import sys
import subprocess

def check_tkinter():
    try:
        import tkinter
        print("✅ tkinter is available.")
        return True
    except ImportError:
        print("⚠️ tkinter is missing!")
        if sys.platform == "darwin":
            print("→ Installing Tcl/Tk via Homebrew...")
            try:
                subprocess.run(["brew", "install", "tcl-tk"], check=True)
            except subprocess.CalledProcessError:
                print("❌ Failed to install tcl-tk via Homebrew. Please install manually.")
                return False

            # 設定環境變數
            tk_path = "/opt/homebrew/opt/tcl-tk/Frameworks"
            os.environ["DYLD_FRAMEWORK_PATH"] = tk_path
            print(f"✅ Set DYLD_FRAMEWORK_PATH={tk_path}")
            print("✅ Tcl/Tk installed. You may need to restart the terminal and re-run.")
            return True

        elif sys.platform.startswith("win"):
            print("⚠️ On Windows, tkinter is bundled with Python. Try reinstalling Python from python.org.")
            return False
        else:
            print("⚠️ Please install Tkinter manually using your package manager.")
            return False

def check_python_packages():
    print("📦 Checking Python packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    print("✅ All Python dependencies are installed.")

if __name__ == "__main__":
    print("🔍 Checking environment setup...")
    check_python_packages()
    check_tkinter()
    print("🎉 Environment setup complete!")

