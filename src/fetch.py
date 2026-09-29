"""Yahoo Finance chart API から日足OHLCVを取得して data/<symbol>.csv に保存する。"""
import urllib.parse
import csv, json, sys, time, urllib.request, datetime as dt
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
DATA = Path(__file__).resolve().parent.parent / "data"

def fetch(symbol, rng="10y", interval="1d"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={rng}&interval={interval}&events=div,split"
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.load(r)
            break
        except Exception as e:
            if i == 3: raise
            time.sleep(2 ** (i + 1))
    res = j["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")
    rows = []
    for k, t in enumerate(res["timestamp"]):
        if q["close"][k] is None: continue
        d = dt.datetime.fromtimestamp(t, dt.timezone(dt.timedelta(hours=9))).date()
        rows.append([d.isoformat(), q["open"][k], q["high"][k], q["low"][k], q["close"][k],
                     q["volume"][k] or 0, adj[k] if adj else q["close"][k]])
    DATA.mkdir(exist_ok=True)
    out = DATA / f"{symbol.replace('^','IDX_').replace('=','_')}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date","open","high","low","close","volume","adjclose"]); w.writerows(rows)
    return out, res["meta"]

if __name__ == "__main__":
    import urllib.parse
    for s in sys.argv[1:]:
        p, m = fetch(s)
        print(s, p.name, m.get("regularMarketPrice"), m.get("longName") or m.get("shortName"))
