#!/usr/bin/env bash
# 定期レポート用の一括実行。出力先: reports/daily/<日付>/
#   ./src/daily.sh        主要銘柄（screen.txt, technical.md）
#   ./src/daily.sh low    低位株（lowprice_discover.txt, lowprice.md）
#   ./src/daily.sh all    両方
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=${1:-main}
python3 -c "import pandas, openpyxl" 2>/dev/null || pip install -q pandas numpy openpyxl
D=$(TZ=Asia/Tokyo date +%F); OUT=reports/daily/$D; mkdir -p "$OUT"
python3 src/fetch.py ^N225 1306.T JPY=X > /dev/null
if [[ $MODE == main || $MODE == all ]]; then
  python3 src/fetch_all.py > /dev/null
  python3 src/screen.py > "$OUT/screen.txt"
  python3 src/analyze.py ^N225 1306.T JPY=X 8306.T 6501.T 6857.T 8802.T 4519.T > "$OUT/technical.md" 2>/dev/null
fi
if [[ $MODE == low || $MODE == all ]]; then
  python3 src/discover_lowprice.py > "$OUT/lowprice_discover.txt" || echo "低位株の銘柄発見に失敗（固定リストで続行）"
  python3 src/fetch_all.py low > /dev/null
  python3 src/lowprice.py --out "$OUT/lowprice.md" > /dev/null 2>&1
  python3 src/analyze.py ^N225 JPY=X > "$OUT/market.md" 2>/dev/null
fi
echo "$OUT"
