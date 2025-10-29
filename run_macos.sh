# run_macos.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

# 進入 venv
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python3 main.py
