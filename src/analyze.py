"""日足・週足テクニカル分析レポート（依頼②）。
使い方: python3 src/analyze.py 8306.T [6501.T ...]"""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from indicators import load, enrich, weekly, rsi, macd

def last_cross(fast, slow, lookback=60):
    d = np.sign(fast - slow).dropna()
    ch = d[d.diff().fillna(0) != 0].iloc[-lookback:]
    if ch.empty: return "直近なし"
    dt, v = ch.index[-1], ch.iloc[-1]
    return f"{'GC' if v > 0 else 'DC'} {dt.date()}"

def pivots(df, w=5):
    """左右w本より高い/安い足をスイング高値/安値とみなす"""
    h, l = df["high"], df["low"]
    ph = h[(h == h.rolling(2*w+1, center=True).max())]
    pl = l[(l == l.rolling(2*w+1, center=True).min())]
    return ph, pl

def zones(levels, close, tol=0.015):
    """近い価格同士をまとめて価格帯（ゾーン）にする。タッチ回数の多い順"""
    lv = sorted(levels); out = []; cur = [lv[0]]
    for x in lv[1:]:
        if x <= cur[0] * (1 + tol): cur.append(x)
        else: out.append(cur); cur = [x]
    out.append(cur)
    z = [(min(c), max(c), len(c)) for c in out]
    sup = sorted([q for q in z if q[1] < close], key=lambda q: -q[1])[:3]
    res = sorted([q for q in z if q[0] > close], key=lambda q: q[0])[:3]
    return sup, res

def trendline(pts, n_bars_idx):
    """直近2つのスイング点を結んだ線を現在まで延長"""
    if len(pts) < 2: return None
    (i1, p1), (i2, p2) = pts[-2], pts[-1]
    slope = (p2 - p1) / (i2 - i1)
    return p2 + slope * (n_bars_idx - i2), slope

def report(sym):
    raw = load(sym)
    raw = raw[raw["volume"] > 0] if (raw["volume"] > 0).mean() > 0.9 else raw  # 指数・為替は出来高0のため除外しない
    df = enrich(raw); L = df.iloc[-1]; c = L.close
    w = weekly(raw); wc = w["close"]
    w["ma13"], w["ma26"], w["ma52"] = wc.rolling(13).mean(), wc.rolling(26).mean(), wc.rolling(52).mean()
    w["rsi"] = rsi(wc); w["macd"], w["sig"], _ = macd(wc); W = w.iloc[-1]
    hh = w["high"].iloc[-26:]; ll = w["low"].iloc[-26:]
    # 週足トレンド判定
    score = sum([W.close > W.ma13, W.ma13 > W.ma26, W.ma26 > w["ma26"].iloc[-5], W.close > W.ma52, W.macd > W.sig])
    wtrend = {5:"強い上昇",4:"上昇",3:"横ばい〜やや上",2:"横ばい〜やや下",1:"下降",0:"強い下降"}[score]
    d = df.iloc[-160:]
    ph, pl = pivots(d)
    sup, res = zones(list(ph.values) + list(pl.values), c)
    idx = {t: i for i, t in enumerate(d.index)}
    up_tl = trendline([(idx[t], v) for t, v in pl.items()], len(d) - 1)
    dn_tl = trendline([(idx[t], v) for t, v in ph.items()], len(d) - 1)
    f = lambda x: f"{x:,.0f}" if x >= 100 else f"{x:,.1f}"
    lines = [f"### {sym}  終値 {f(c)}円（{L.name.date()}）",
      f"- 週足トレンド: **{wtrend}**（スコア{score}/5）13週{f(W.ma13)} / 26週{f(W.ma26)} / 52週{f(W.ma52)}、週足RSI {W.rsi:.0f}、26週高値{f(hh.max())}・安値{f(ll.min())}",
      f"- 週足クロス(13/26): {last_cross(w['ma13'], w['ma26'], 400)}",
      f"- 日足MA: 5日{f(L.ma5)} / 25日{f(L.ma25)} / 75日{f(L.ma75)} / 200日{f(L.ma200)}  並び: " +
        ("5>25>75（上昇配列）" if L.ma5 > L.ma25 > L.ma75 else "5<25<75（下降配列）" if L.ma5 < L.ma25 < L.ma75 else "混在"),
      f"- 日足クロス: 5/25 {last_cross(df.ma5, df.ma25)}、25/75 {last_cross(df.ma25, df.ma75, 250)}",
      f"- 支持帯: " + ("（直近160日に下値の節目なし＝安値更新中）" if not sup else "") + "、".join(f"{f(a)}〜{f(b)}（{n}回）" for a, b, n in sup),
      f"- 抵抗帯: " + "、".join(f"{f(a)}〜{f(b)}（{n}回）" for a, b, n in res),
      f"- 上昇TL(直近2安値)現在値: {f(up_tl[0])}（傾き{up_tl[1]:+.1f}/日）" if up_tl and up_tl[1] > 0 else "- 上昇TL: 直近の安値が切り下がっており有効な上昇TLなし",
      f"- 下降TL(直近2高値)現在値: {f(dn_tl[0])}（傾き{dn_tl[1]:+.1f}/日）" if dn_tl and dn_tl[1] < 0 else "- 下降TL: 直近の高値が切り上がっており有効な下降TLなし",
      f"- RSI(14) {L.rsi:.0f}、MACD {L.macd:.1f} / シグナル {L.sig:.1f}（ヒスト {L['hist']:+.1f}、前日 {df['hist'].iloc[-2]:+.1f}）、ストキャス %K {L.K:.0f} / %D {L.D:.0f}",
      f"- 出来高: 当日{L.volume/1e6:.2f}百万株、20日平均比 {L.volume/L.vol20:.2f}倍、ATR(14) {f(L.atr)}（{L.atr/c*100:.1f}%）",
      f"- 5日{(c/df.close.iloc[-6]-1)*100:+.1f}%、20日{(c/df.close.iloc[-21]-1)*100:+.1f}%、52週高値比{(c/df.high.iloc[-250:].max()-1)*100:+.1f}%"]
    return "\n".join(lines)

if __name__ == "__main__":
    for s in sys.argv[1:]: print(report(s)); print()
