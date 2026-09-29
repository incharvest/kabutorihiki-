"""テクニカル指標の計算（pandas使用）。"""
import pandas as pd, numpy as np
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

def load(symbol):
    p = DATA / f"{symbol.replace('^','IDX_').replace('=','_')}.csv"
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date")
    return df[df["close"].notna()]

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
