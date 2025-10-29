#!/usr/bin/env bash
set -euo pipefail

echo "🐍 Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "📦 Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "🔍 Checking environment (Tkinter, etc.)..."
python check_env.py

echo "✅ venv setup complete. Run with: ./run_macos.sh"

