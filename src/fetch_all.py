import time, sys
sys.path.insert(0, "src")
from fetch import fetch
from universe import UNIVERSE
for s in UNIVERSE:
    try: fetch(s, rng="2y")
    except Exception as e: print("FAIL", s, e)
    time.sleep(0.4)
print("done")
