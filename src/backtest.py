"""日経225のバックテスト（依頼④）。
戦略A: 25日・75日移動平均のゴールデンクロスで買い、デッドクロスで手仕舞い（ロングのみ）
戦略B: RSI強気ダイバージェンス（価格は安値更新・RSIは安値切り上げ）で買い、RSI70超 or 20日経過 or 損切り(-2ATR)で手仕舞い
約定: シグナル翌営業日の始値。手数料・スリッページは片道ごとに控除。
使い方: python3 src/backtest.py [--years 10] [--fee 0.001] [--slip 0.0005]
"""
import sys, argparse; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from indicators import load, rsi, atr

def run_trades(df, entries, exit_fn, fee, slip):
    """entries: bool Series（当日終値でシグナル）→翌日始値で約定。exit_fn(i, entry_i, entry_px)->bool"""
    o, c = df["open"].values, df["close"].values
    trades, equity = [], np.ones(len(df)); pos = False; cash = 1.0; sh = 0.0
    for i in range(1, len(df)):
        if not pos and entries.iloc[i-1]:
            px = o[i] * (1 + slip); sh = cash * (1 - fee) / px; ei, epx, pos = i, px, True
        elif pos and exit_fn(i-1, ei, epx):
            px = o[i] * (1 - slip); new_cash = sh * px * (1 - fee)
            trades.append(dict(entry=df.index[ei].date(), exit=df.index[i].date(), ret=new_cash / cash - 1, days=i - ei))
            cash, pos = new_cash, False
        equity[i] = sh * c[i] if pos else cash
    if pos:  # 最終日に評価上の手仕舞い
        new_cash = sh * c[-1] * (1 - slip) * (1 - fee)
        trades.append(dict(entry=df.index[ei].date(), exit=df.index[-1].date(), ret=new_cash / cash - 1, days=len(df) - 1 - ei, open=True))
        equity[-1] = new_cash
    return pd.DataFrame(trades), pd.Series(equity, index=df.index)

def stats(name, tr, eq, exposure=None):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    dd = (eq / eq.cummax() - 1).min()
    if tr is None or tr.empty:
        return dict(戦略=name, 取引回数="-", 勝率="-", 損益比率="-", PF="-", 最大DD=f"{dd*100:.1f}%",
                    年率リターン=f"{(eq.iloc[-1]**(1/yrs)-1)*100:.1f}%", 累積=f"{(eq.iloc[-1]-1)*100:.0f}%", 市場滞在率="100%")
    w, l = tr[tr.ret > 0].ret, tr[tr.ret <= 0].ret
    return dict(戦略=name, 取引回数=len(tr), 勝率=f"{len(w)/len(tr)*100:.0f}%",
        損益比率=f"{w.mean()/-l.mean():.2f}" if len(l) and len(w) else "-",
        PF=f"{w.sum()/-l.sum():.2f}" if len(l) else "∞",
        最大DD=f"{dd*100:.1f}%", 年率リターン=f"{(eq.iloc[-1]**(1/yrs)-1)*100:.1f}%",
        累積=f"{(eq.iloc[-1]-1)*100:.0f}%", 市場滞在率=f"{exposure*100:.0f}%" if exposure is not None else "-")

def ma_cross(df, f=25, s=75, trend_filter=None):
    mf, ms = df.close.rolling(f).mean(), df.close.rolling(s).mean()
    above = mf > ms
    ent = above & ~above.shift(1, fill_value=False)
    if trend_filter: ent &= df.close > df.close.rolling(trend_filter).mean()
    ex = (~above).values
    return ent, lambda i, ei, epx: ex[i]

def rsi_div(df, look=20, hold=20, atr_mult=2.0, rsi_max=40, rsi_low=30):
    r = rsi(df.close).values; lo = df.low.values; a = atr(df).values; c = df.close.values
    ent = np.zeros(len(df), bool)
    # 直近 look 日の最安値を今日更新し、RSIはその時点より高い（強気ダイバージェンス）＆ RSIが売られ過ぎ圏
    for i in range(look + 20, len(df)):
        j = i - look + int(np.argmin(lo[i-look:i]))
        if lo[i] < lo[j] and r[i] > r[j] + 3 and r[j] < rsi_low and r[i] < rsi_max and c[i] > lo[i] + 0.5 * (df.high.values[i] - lo[i]):
            ent[i] = True
    def ex(i, ei, epx):
        return r[i] > 70 or (i - ei) >= hold or c[i] < epx - atr_mult * a[ei]
    return pd.Series(ent, index=df.index), ex

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sym", default="^N225"); ap.add_argument("--years", type=float, default=10)
    ap.add_argument("--fee", type=float, default=0.001); ap.add_argument("--slip", type=float, default=0.0005)
    a = ap.parse_args()
    df = load(a.sym); df = df[df.index >= df.index[-1] - pd.DateOffset(years=a.years)]
    rows = []; exposure = lambda tr: tr.days.sum() / len(df) if len(tr) else 0
    bh = df.close / df.close.iloc[0] * (1 - a.fee - a.slip)
    rows.append(stats("日経225 買い持ち（配当除く）", None, bh))
    for label, (ent, ex) in {
        "A: 25/75日MAクロス": ma_cross(df),
        "A': 25/75クロス+200日線上フィルター": ma_cross(df, trend_filter=200),
        "B: RSI強気ダイバージェンス(RSI<30)": rsi_div(df),
        "B': RSIダイバージェンス緩和(RSI<40,60日保有)": rsi_div(df, rsi_low=40, rsi_max=50, hold=60),
    }.items():
        tr, eq = run_trades(df, ent, ex, a.fee, a.slip)
        rows.append(stats(label, tr, eq, exposure(tr)))
        if label.startswith("A:"): tr.to_csv("reports/trades_ma_cross.csv", index=False)
        if label.startswith("B:"): tr.to_csv("reports/trades_rsi_div.csv", index=False)
    # パラメータ感応度（過剰最適化チェック）
    sens = []
    for f in (10, 20, 25, 50):
        for s in (50, 75, 100, 200):
            if f >= s: continue
            e, x = ma_cross(df, f, s); tr, eq = run_trades(df, e, x, a.fee, a.slip); st = stats(f"{f}/{s}", tr, eq)
            sens.append((f"{f}/{s}", st["取引回数"], st["勝率"], st["PF"], st["年率リターン"], st["最大DD"]))
    # 前半・後半の分割検証
    half = df.index[len(df)//2]; split = []
    for nm, part in (("前半", df[df.index < half]), ("後半", df[df.index >= half])):
        e, x = ma_cross(part); tr, eq = run_trades(part, e, x, a.fee, a.slip); st = stats(nm, tr, eq)
        bhp = part.close / part.close.iloc[0]; sb = stats(nm, None, bhp)
        split.append((f"{nm} {part.index[0].date()}〜{part.index[-1].date()}", st["取引回数"], st["PF"], st["年率リターン"], st["最大DD"], sb["年率リターン"], sb["最大DD"]))
    pd.set_option("display.width", 250)
    print(f"対象 {a.sym}  期間 {df.index[0].date()}〜{df.index[-1].date()}  手数料 片道{a.fee*100:.2f}%  スリッページ 片道{a.slip*100:.2f}%\n")
    print(pd.DataFrame(rows).to_string(index=False)); print("\n[パラメータ感応度: 短期/長期MA]")
    print(pd.DataFrame(sens, columns=["MA", "回数", "勝率", "PF", "年率", "最大DD"]).to_string(index=False))
    print("\n[期間分割（25/75）]"); print(pd.DataFrame(split, columns=["期間", "回数", "PF", "年率", "最大DD", "B&H年率", "B&H最大DD"]).to_string(index=False))

if __name__ == "__main__": main()
