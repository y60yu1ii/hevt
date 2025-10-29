#!/usr/bin/env bash
set -euo pipefail

# 找到 conda 並啟用 shell 支援
if command -v conda >/dev/null 2>&1; then
  CONDA_BASE="$(conda info --base)"
  # shellcheck disable=SC1091
  source "$CONDA_BASE/etc/profile.d/conda.sh"
else
  # 嘗試常見安裝路徑（Miniforge/Miniconda）
  for p in \
    "$HOME/miniforge3/etc/profile.d/conda.sh" \
    "$HOME/mambaforge/etc/profile.d/conda.sh" \
    "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" \
    "/opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh" \
    "/opt/miniconda3/etc/profile.d/conda.sh" \
    "/opt/miniforge3/etc/profile.d/conda.sh"
  do
    if [ -f "$p" ]; then
      # shellcheck disable=SC1091
      source "$p"
      break
    fi
  done
fi

# 若仍找不到 conda，給出安裝指引
if ! command -v conda >/dev/null 2>&1; then
  echo "❌ 找不到 conda。請先安裝 Miniforge 或 Miniconda（建議 Miniforge + conda-forge）："
  echo "   https://github.com/conda-forge/miniforge"
  exit 1
fi

# 建立／更新 conda 環境
conda env update -f environment.yml --prune

# 啟用環境並執行
conda activate stm32-thermal
exec python main.py
