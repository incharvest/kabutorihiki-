#!/usr/bin/env bash
# 定期レポート用：データ取得→スクリーニング→指数/主要銘柄の分析を reports/daily/ に出力
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c "import pandas" 2>/dev/null || pip install -q pandas numpy
D=$(TZ=Asia/Tokyo date +%F); OUT=reports/daily/$D; mkdir -p "$OUT"
python3 src/fetch.py ^N225 1306.T JPY=X > /dev/null
python3 src/fetch_all.py > /dev/null
python3 src/screen.py > "$OUT/screen.txt"
python3 src/analyze.py ^N225 1306.T JPY=X 8306.T 6501.T 6857.T 8802.T 4519.T > "$OUT/technical.md"
echo "$OUT"
