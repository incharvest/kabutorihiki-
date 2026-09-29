"""テクニカル指標の計算（pandas使用）。"""
import pandas as pd, numpy as np
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

SPLIT_RATIOS = (1.5, 2, 2.5, 3, 4, 5, 8, 10, 15, 20, 25, 50, 100)

def adjust_splits(df):
    """Yahoo が株式分割を調整し忘れた系列を補正する。
    前日終値÷当日始値が一般的な分割比率（±8%）に一致し、かつ30%超の変化なら分割とみなし、それ以前のOHLCを割り戻す。"""
    df = df.copy(); o, pc = df["open"], df["close"].shift()
    for i in range(1, len(df)):
        r = pc.iloc[i] / o.iloc[i]
        if not (r > 1.3 or r < 1 / 1.3) or np.isnan(r): continue
        k = r if r > 1 else 1 / r
        m = min(SPLIT_RATIOS, key=lambda x: abs(k / x - 1))
        if abs(k / m - 1) > 0.08: continue
        f = m if r > 1 else 1 / m
        idx = df.index[:i]
        df.loc[idx, ["open", "high", "low", "close"]] /= f
        df.loc[idx, "volume"] *= f
    return df

def load(symbol):
    p = DATA / f"{symbol.replace('^','IDX_').replace('=','_')}.csv"
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date")
    df = df[df["close"].notna()]
    return df if symbol.startswith("^") or "=" in symbol else adjust_splits(df)

def rsi(s, n=14):
    d = s.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    ru = up.ewm(alpha=1/n, adjust=False).mean(); rd = dn.ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd)

def macd(s, f=12, sl=26, sig=9):
    m = s.ewm(span=f, adjust=False).mean() - s.ewm(span=sl, adjust=False).mean()
    sg = m.ewm(span=sig, adjust=False).mean()
    return m, sg, m - sg

def stoch(df, k=14, d=3, sd=3):
    ll = df["low"].rolling(k).min(); hh = df["high"].rolling(k).max()
    fk = 100 * (df["close"] - ll) / (hh - ll)
    K = fk.rolling(d).mean(); D = K.rolling(sd).mean()   # スローストキャスティクス
    return K, D

def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"]-df["low"], (df["high"]-pc).abs(), (df["low"]-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def weekly(df):
    return df.resample("W-FRI").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()

def enrich(df):
    df = df.copy(); c = df["close"]
    for n in (5, 25, 75, 200): df[f"ma{n}"] = c.rolling(n).mean()
    df["rsi"] = rsi(c); df["macd"], df["sig"], df["hist"] = macd(c)
    df["K"], df["D"] = stoch(df); df["atr"] = atr(df)
    df["vol20"] = df["volume"].rolling(20).mean()
    return df
