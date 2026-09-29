"""ユニバースの日足を一括取得。使い方: python3 src/fetch_all.py [main|low]"""
import time, sys
sys.path.insert(0, "src")
from fetch import fetch
if len(sys.argv) > 1 and sys.argv[1] == "low":
    from universe_lowprice import load_universe
    U = load_universe()
else:
    from universe import UNIVERSE as U
fail = []
for s in U:
    try: fetch(s, rng="2y")
    except Exception as e: fail.append(s)
    time.sleep(0.4)
print("done", f"失敗: {fail}" if fail else "")
