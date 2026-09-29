"""低位株（株価1,000円以内）レポート。
流動性でふるい分け → 買い／空売りの候補を点数化 → 支持・抵抗帯からエントリー・利確・損切りを自動算出
→ ポジションサイズ → Markdown 出力。
使い方: python3 src/lowprice.py [--max-price 1000] [--min-turnover 3e8] [--capital 3000000] [--out FILE] [--no-fund]"""
import sys, argparse, math, time; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from indicators import load, enrich, weekly, rsi, macd
from analyze import pivots, zones, report
from universe_lowprice import load_universe, tick
U = load_universe()
from position_size import size

def weekly_score(raw):
    w = weekly(raw); c = w["close"]
    m13, m26, m52 = c.rolling(13).mean(), c.rolling(26).mean(), c.rolling(52).mean()
    m, s = macd(c)[:2]
    return int(sum([c.iloc[-1] > m13.iloc[-1], m13.iloc[-1] > m26.iloc[-1], m26.iloc[-1] > m26.iloc[-5],
                    c.iloc[-1] > m52.iloc[-1] if not np.isnan(m52.iloc[-1]) else False, m.iloc[-1] > s.iloc[-1]]))

def levels(df, side, tk=1.0):
    """支持・抵抗帯とATRからエントリー・損切り・利確を決める（side: 'long'/'short'）"""
    L = df.iloc[-1]; c, a = L.close, L.atr; d = df.iloc[-160:]
    ph, pl = pivots(d); sup, res = zones(list(ph.values) + list(pl.values), c)
    r1 = lambda x: round(round(x / tk) * tk, 1)            # 呼値の単位に丸める
    if side == "long":
        entry = c - 0.5 * a                                   # 押し目の指値
        near = [z for z in sup if z[1] >= c - 2 * a]
        if near: entry = max(near[0][1], entry)
        below = [z for z in sup if z[1] < entry - 0.3 * a]
        stop = (below[0][0] - 0.3 * a) if below else entry - 1.5 * a
        stop = min(max(stop, entry - 2.5 * a), entry - 1.0 * a)
        R = entry - stop
        above = [z[0] for z in res if z[0] > entry + 1.5 * R]
        tp1 = above[0] if above else entry + 2 * R
        tp2 = max(entry + 3 * R, above[1] if len(above) > 1 else 0, tp1 + R)
    else:
        entry = c + 0.5 * a                                   # 戻り売りの指値
        near = [z for z in res if z[0] <= c + 2 * a]
        if near: entry = min(near[0][0], entry)
        above = [z for z in res if z[0] > entry + 0.3 * a]
        stop = (above[0][1] + 0.3 * a) if above else entry + 1.5 * a
        stop = max(min(stop, entry + 2.5 * a), entry + 1.0 * a)
        R = stop - entry
        below = [z[1] for z in sup if z[1] < entry - 1.5 * R]
        tp1 = below[0] if below else entry - 2 * R
        tp2 = min(entry - 3 * R, below[1] if len(below) > 1 else 1e18, tp1 - R)
    e, s, t1, t2 = map(r1, (entry, stop, tp1, tp2))
    rr = lambda t: abs(t - e) / abs(e - s)
    return dict(entry=e, stop=s, tp1=t1, tp2=t2, rr1=rr(t1), rr2=rr(t2))

def scan(max_price, min_turnover):
    rows = []
    for sym, info in U.items():
        name = info["name"]
        try: raw = load(sym)
        except Exception: continue
        raw = raw[raw["volume"] > 0]
        if len(raw) < 120: continue
        df = enrich(raw); L = df.iloc[-1]
        turnover = (df.close * df.volume).iloc[-20:].mean()
        if L.close > max_price or turnover < min_turnover: continue
        ws = weekly_score(raw)
        up = L.close > L.ma25 > L.ma75; dn = L.close < L.ma25 < L.ma75
        vs25 = (L.close / L.ma25 - 1) * 100
        long_s = ws + up * 2 + (40 <= L.rsi <= 65) + (L["hist"] > 0) + (vs25 < 6) - (L.K > 85)
        short_s = (5 - ws) + dn * 2 + (35 <= L.rsi <= 60) + (L["hist"] < 0) + (vs25 > -6) - (L.K < 15)
        pinned = L.atr / L.close < 0.008          # TOB（公開買付け）等で値動きが止まっている可能性
        rows.append(dict(sym=sym, code=sym[:4], name=name, sector=info["sector"] or "-", tk=tick(L.close, info["scale"]), pinned=pinned, date=L.name.date(), close=L.close, turnover=turnover,
                         ws=ws, rsi=L.rsi, K=L.K, vs25=vs25, atr_pct=L.atr / L.close * 100, vr=L.volume / L.vol20,
                         long_s=long_s, short_s=short_s, df=df))
    return rows

def fmt(x): return f"{x:,.1f}" if x < 1000 else f"{x:,.0f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-price", type=float, default=1000); ap.add_argument("--min-turnover", type=float, default=3e8)
    ap.add_argument("--capital", type=float, default=3_000_000); ap.add_argument("--n-long", type=int, default=3)
    ap.add_argument("--n-short", type=int, default=2); ap.add_argument("--out"); ap.add_argument("--no-fund", action="store_true")
    a = ap.parse_args()
    rows = scan(a.max_price, a.min_turnover)
    if not rows: print("条件を満たす低位株がありません"); return
    asof = max(r["date"] for r in rows)
    ok = [r for r in rows if not r["pinned"] and r["close"] >= 100]
    longs = [r for r in sorted(ok, key=lambda r: (-r["long_s"], -r["turnover"])) if r["long_s"] >= 7][:a.n_long]
    shorts = [r for r in sorted(ok, key=lambda r: (-r["short_s"], -r["turnover"])) if r["short_s"] >= 7][:a.n_short]
    pinned = [r for r in rows if r["pinned"]]
    out = [f"# 低位株レポート（株価{a.max_price:,.0f}円以内）— データ日付 {asof}",
           "", f"> 対象: 候補{len(U)}銘柄のうち、終値{a.max_price:,.0f}円以下かつ20日平均売買代金{a.min_turnover/1e8:.0f}億円以上の **{len(rows)}銘柄**。"
           f" 資金{a.capital/1e4:,.0f}万円・許容損失1%/2%・100株単位で計算。株価は Yahoo Finance（{asof} 終値）。",
           ("> 値動きがほぼ止まっている銘柄（TOB等の可能性）は候補から除外: " + "、".join(f"{r['name']}（{r['code']}）" for r in pinned)) if pinned else ">",
           "> エントリー・利確・損切りは支持帯・抵抗帯とATR（1日の平均的な値幅）から機械的に算出したもの【推測を含む】。投資助言ではありません。", ""]
    out.append("## 流動性上位の低位株一覧\n")
    out.append("| コード | 銘柄 | 業種 | 終値 | 売買代金(億円/日) | 週足 | RSI | 25日線乖離 | ATR% | 呼値(1ティック) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: -r["turnover"])[:25]:
        out.append(f"| {r['code']} | {r['name']} | {r['sector']} | {fmt(r['close'])} | {r['turnover']/1e8:,.1f} | {r['ws']}/5 | {r['rsi']:.0f} | {r['vs25']:+.1f}% | {r['atr_pct']:.1f}% | {r['tk']}円（{r['tk']/r['close']*100:.2f}%） |")
    summary, skipped = [], []
    longs_all = [r for r in sorted(ok, key=lambda r: (-r["long_s"], -r["turnover"])) if r["long_s"] >= 7]
    shorts_all = [r for r in sorted(ok, key=lambda r: (-r["short_s"], -r["turnover"])) if r["short_s"] >= 7]
    for side, lst, n in (("long", longs_all, a.n_long), ("short", shorts_all, a.n_short)):
        done = 0
        for r in lst:
            if done >= n: break
            lv = levels(r["df"], side, r["tk"])
            if abs(lv["entry"] - lv["stop"]) / r["tk"] < 8:        # 損切り幅が8ティック未満だと約定ずれの影響が大きい
                skipped.append(f"{r['name']}（{r['code']}）: 損切り幅が呼値{abs(lv['entry']-lv['stop'])/r['tk']:.0f}ティックしかない"); continue
            s1 = size(a.capital, 0.01, lv["entry"], lv["stop"]); s2 = size(a.capital, 0.02, lv["entry"], lv["stop"])
            f = {}
            if not a.no_fund:
                try:
                    from fundamentals import get; f = get(r["sym"]); time.sleep(1)
                except Exception as e: f = {"取得失敗": str(e)[:60]}
            lab = "買い" if side == "long" else "空売り"
            out += ["", f"## {lab}候補: {r['name']}（{r['code']}）", "",
                    f"| エントリー | 利確1 | 利確2 | 損切り | RR（利確1/2） | 1%時（必要資金） | 2%時（必要資金） | 業種 |", "|---|---|---|---|---|---|---|---|",
                    f"| {fmt(lv['entry'])} | {fmt(lv['tp1'])} | {fmt(lv['tp2'])} | {fmt(lv['stop'])} | 1:{lv['rr1']:.1f} / 1:{lv['rr2']:.1f} | {s1['株数']}株（{s1['必要資金']/1e4:,.0f}万円） | {s2['株数']}株（{s2['必要資金']/1e4:,.0f}万円） | {r['sector']} |", "",
                    report(r["sym"]).replace("### ", "**テクニカル【事実】** ", 1)]
            if f:
                out.append("- **ファンダ・需給【事実】**: " + "、".join(f"{k} {v}" for k, v in f.items() if k not in ("code", "決算要約")))
                if f.get("決算要約", "N/A") != "N/A": out.append(f"- **直近決算【事実】**: {f['決算要約'].strip()}")
                if "継続企業の前提" in f.get("決算要約", ""):
                    out.append("- ⚠️ **継続企業の前提に関する注記あり**：経営破綻・上場廃止・大規模増資のリスクが高い。値動きが極端になりやすいので、見送りも選択肢。")
            if side == "short": out.append("- **注意**: 空売りは貸借銘柄のみ（制度信用）。日証金の増担保規制・逆日歩の有無を発注前に確認。")
            done += 1
            summary.append(f"| {r['name']} {r['code']} | {lab} | {fmt(lv['entry'])} | {fmt(lv['tp1'])} | {fmt(lv['tp2'])} | {fmt(lv['stop'])} | 1:{lv['rr2']:.1f} | {s1['株数']} / {s2['株数']} |")
    out += ["", "## まとめ", "", "| 銘柄 | 方向 | エントリー | 利確1 | 利確2 | 損切り | RR(利確2) | 株数 1%/2% |", "|---|---|---|---|---|---|---|---|"] + summary
    if not summary: out.append("| 条件を満たす候補なし | | | | | | | |")
    if skipped: out += ["", "候補から外した銘柄: " + "／".join(skipped)]
    out += ["", "## 低位株に特有のリスク",
            "- **複数銘柄の同時保有**: 株数は1銘柄ずつ計算している。同時に持つ場合は合計の許容損失（例: 6%以内）と必要資金の合計が資金を超えないよう減らすこと。",
            "- **1ティック（呼値）の重さ**: 株価300円で呼値1円なら1ティック＝0.33%。指値のずれやスプレッド（売り買いの気配値の差）が効きやすい。",
            "- **仕手化・急騰急落**: 出来高が急に膨らんだ銘柄は、材料が乏しいと数日で元に戻りやすい。",
            "- **増資・希薄化**: 業績不振の低位株は公募増資・新株予約権の発行で1株の価値が薄まることがある（適時開示を確認）。",
            "- **信用規制**: 日証金の増担保規制・貸株停止が出ると需給が急変する。",
            "- **上場維持基準**: 超低位（数十円台）や赤字が続く銘柄は、上場維持基準への抵触や上場廃止のリスクに注意。"]
    text = "\n".join(out)
    if a.out: open(a.out, "w").write(text)
    print(text)

if __name__ == "__main__": main()
