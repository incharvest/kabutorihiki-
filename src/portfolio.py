"""ポートフォリオのリスク分析（依頼⑤）。
使い方: python3 src/portfolio.py --capital 3000000 --w 7203.T=0.20 8306.T=0.15 ... CASH=0.10
各銘柄の日経225に対するβ（感応度）、ドル円・金利代理（銀行株）との相関、-20%シナリオ損失、ヘッジ量を計算。"""
import sys, argparse, math; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from indicators import load
from universe import UNIVERSE

def bs_put(S, K, T, r, q, v):
    N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    d1 = (math.log(S / K) + (r - q + v * v / 2) * T) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    return K * math.exp(-r * T) * N(-d2) - S * math.exp(-q * T) * N(-d1)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--capital", type=float, default=3_000_000)
    ap.add_argument("--w", nargs="+", required=True); ap.add_argument("--days", type=int, default=250)
    a = ap.parse_args()
    w = {k: float(v) for k, v in (x.split("=") for x in a.w)}; cash = w.pop("CASH", 0.0)
    assert abs(sum(w.values()) + cash - 1) < 1e-6, "比率の合計は1にしてください"
    idx = load("^N225").close; fx = load("JPY=X").close
    px = pd.DataFrame({s: load(s).close for s in w}); px["N225"] = idx; px["USDJPY"] = fx
    ret = px.ffill().pct_change().dropna().iloc[-a.days:]
    rows = []
    for s in w:
        b = ret[s].cov(ret.N225) / ret.N225.var()
        rows.append(dict(銘柄=f"{s[:4]} {UNIVERSE.get(s, '')}", 比率=f"{w[s]*100:.0f}%", 金額=f"{w[s]*a.capital:,.0f}",
            β=round(b, 2), 相関_N225=round(ret[s].corr(ret.N225), 2), 相関_ドル円=round(ret[s].corr(ret.USDJPY), 2),
            相関_銀行株=round(ret[s].corr(ret["8306.T"]), 2) if "8306.T" in ret else None,
            年率ボラ=f"{ret[s].std()*np.sqrt(250)*100:.0f}%"))
    t = pd.DataFrame(rows); pd.set_option("display.width", 250)
    print(f"分析期間: 直近{a.days}営業日（〜{ret.index[-1].date()}）  資金 {a.capital:,.0f}円  現金 {cash*100:.0f}%\n"); print(t.to_string(index=False))
    stocks = list(w); wv = np.array([w[s] for s in stocks])
    port = (ret[stocks] * wv).sum(axis=1)
    beta_p = port.cov(ret.N225) / ret.N225.var()
    print("\n銘柄間の相関行列:"); print(ret[stocks].corr().round(2).rename(columns=lambda c: c[:4], index=lambda c: c[:4]).to_string())
    vol = port.std() * np.sqrt(250)
    print(f"\nポートフォリオβ(現金込み) {beta_p:.2f} / 年率ボラ {vol*100:.1f}% / ドル円相関 {port.corr(ret.USDJPY):.2f}")
    loss = beta_p * 0.20 * a.capital
    print(f"日経225が-20%のときの想定損失（β×20%）: {loss:,.0f}円（資金の{loss/a.capital*100:.1f}%）")
    # 暴落時はβが上がりやすいので下落日だけのβも出す
    dn = ret.N225 < -0.02
    bdn = (port[dn] * 1).mean() / ret.N225[dn].mean() if dn.sum() > 5 else float("nan")
    print(f"日経が-2%超下落した日だけで見た感応度 {bdn:.2f}（{dn.sum()}日）→ 想定損失 {bdn*0.2*a.capital:,.0f}円")
    # 過去の急落局面で実際にどれだけ下げたか（平常時のβは急落時の連動を過小評価しやすい）
    worst = 0
    for st, en in (("2024-07-11", "2024-08-05"), ("2025-03-26", "2025-04-07")):
        try:
            pr = sum(w[s] * (load(s).close.asof(pd.Timestamp(en)) / load(s).close.asof(pd.Timestamp(st)) - 1) for s in stocks)
            nr = idx.asof(pd.Timestamp(en)) / idx.asof(pd.Timestamp(st)) - 1
            print(f"ストレス {st}〜{en}: 日経{nr*100:+.1f}% → PF{pr*100:+.1f}%（実効β {pr/nr:.2f}）")
            worst = max(worst, pr / nr)
        except Exception: pass
    if worst:
        print(f"→ 急落時の実効β {worst:.2f} で日経-20%を想定すると損失 {worst*0.2*a.capital:,.0f}円（資金の{worst*20:.1f}%）")
        beta_p = max(beta_p, worst)
    S = idx.iloc[-1]; hedge_notional = beta_p * a.capital
    print(f"\n[ヘッジ量の目安] 日経 {S:,.0f}  ヘッジ必要額（β調整後）{hedge_notional:,.0f}円")
    for nm, mult in (("日経225ミニ先物(100倍)", 100), ("日経225マイクロ先物(10倍)", 10)):
        n = hedge_notional / (S * mult); print(f"  {nm}: 1枚の名目 {S*mult:,.0f}円 → {n:.2f}枚（完全ヘッジ）")
    for m, k in ((3, 0.95), (3, 0.90)):
        K = round(S * k / 250) * 250; T = m / 12
        p = bs_put(S, K, T, 0.0125, 0.017, 0.24)
        print(f"  ミニオプション(100倍) {m}か月 権利行使価格{K:,}（{k*100:.0f}%）プット理論値 約{p:,.0f}円/単位 → 1枚 {p*100:,.0f}円（名目比{p/S*100:.1f}%、IV24%仮定）")
    print("  インバースETF(1571: -1倍) 必要額 ≒ " + f"{hedge_notional:,.0f}円 / ダブルインバース(1357: -2倍) ≒ {hedge_notional/2:,.0f}円")

if __name__ == "__main__": main()
