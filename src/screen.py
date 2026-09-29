"""ユニバースをテクニカル条件でスクリーニングし一覧表示。"""
import sys; sys.path.insert(0, "src")
import pandas as pd
from indicators import load, enrich, weekly
from universe import UNIVERSE
rows = []
for s, n in UNIVERSE.items():
    try: df = enrich(load(s))
    except Exception as e: continue
    df = df[df["volume"] > 0] if df["volume"].iloc[-1] == 0 and len(df) > 1 else df
    L = df.iloc[-1]; w = weekly(df); w13 = w["close"].rolling(13).mean(); w26 = w["close"].rolling(26).mean()
    hi52 = df["high"].iloc[-250:].max(); lo52 = df["low"].iloc[-250:].min()
    rows.append(dict(code=s[:4], name=n, date=L.name.date(), close=round(L.close,1),
        chg5=round((L.close/df.close.iloc[-6]-1)*100,1), chg20=round((L.close/df.close.iloc[-21]-1)*100,1),
        vs25=round((L.close/L.ma25-1)*100,1), vs75=round((L.close/L.ma75-1)*100,1),
        ma_order="5>25>75" if L.ma5>L.ma25>L.ma75 else ("5<25<75" if L.ma5<L.ma25<L.ma75 else "mixed"),
        wk="up" if w13.iloc[-1]>w26.iloc[-1] else "dn", rsi=round(L.rsi,0), K=round(L.K,0),
        hist=round(L["hist"],2), vr=round(L.volume/L.vol20,2), atr_pct=round(L.atr/L.close*100,1),
        off_hi=round((L.close/hi52-1)*100,1)))
t = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(t.sort_values("vs75").to_string(index=False))
