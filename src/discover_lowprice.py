"""東証の上場銘柄一覧（JPX）から、株価が上限以下の銘柄を洗い出して data/lowprice_universe.csv に保存。
使い方: python3 src/discover_lowprice.py [--max-price 1000] [--markets プライム スタンダード]"""
import sys, json, time, argparse, urllib.request, io
from pathlib import Path
import pandas as pd
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
DATA = Path(__file__).resolve().parent.parent / "data"
JPX = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx"

def get(url):
    for i in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()
        except Exception:
            if i == 3: raise
            time.sleep(2 ** (i + 1))

def listed(markets):
    cache = DATA / "jpx_listed.xlsx"
    if not cache.exists() or time.time() - cache.stat().st_mtime > 7 * 86400:   # 週1回更新
        DATA.mkdir(exist_ok=True); cache.write_bytes(get(JPX))
    d = pd.read_excel(cache, dtype={"コード": str})
    d = d[d["市場・商品区分"].str.contains("|".join(markets)) & d["市場・商品区分"].str.contains("内国株式")]
    return d

def last_prices(codes):
    out = {}
    for i in range(0, len(codes), 20):
        syms = ",".join(c + ".T" for c in codes[i:i+20])
        try:
            j = json.loads(get(f"https://query2.finance.yahoo.com/v8/finance/spark?symbols={syms}&range=5d&interval=1d"))
            for s, v in j.items():
                cl = [x for x in (v.get("close") or []) if x is not None]
                if cl: out[s] = cl[-1]
        except Exception as e:
            print("spark失敗", syms[:30], e, file=sys.stderr)
        time.sleep(0.3)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--max-price", type=float, default=1000)
    ap.add_argument("--min-price", type=float, default=100); ap.add_argument("--markets", nargs="+", default=["プライム"])
    a = ap.parse_args()
    d = listed(a.markets)
    px = last_prices(d["コード"].tolist())
    d["symbol"] = d["コード"] + ".T"; d["price"] = d["symbol"].map(px)
    lo = d[(d.price <= a.max_price) & (d.price >= a.min_price)]
    lo = lo[["symbol", "銘柄名", "市場・商品区分", "33業種区分", "規模区分", "price"]]
    lo.to_csv(DATA / "lowprice_universe.csv", index=False)
    print(f"{len(d)}銘柄中、{len(px)}銘柄の価格を取得 → {a.min_price:.0f}〜{a.max_price:.0f}円: {len(lo)}銘柄")
