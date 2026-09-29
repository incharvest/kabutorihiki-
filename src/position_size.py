"""1トレードの許容損失から株数を計算（単元100株）。依頼③用。
使い方: python3 src/position_size.py 資金 リスク率 エントリー 損切り [...繰り返し]"""
import sys
def size(capital, risk_pct, entry, stop, lot=100):
    per = abs(entry - stop); budget = capital * risk_pct
    lots = int(budget // (per * lot))
    lots = min(lots, int(capital // (entry * lot)))          # 資金を超える株数は持てない
    sh = lots * lot
    return dict(株数=sh, 想定損失=sh * per, 必要資金=sh * entry, 上限超過=sh * entry > capital,
                単元未満の目安=int(budget // per) if lots == 0 else None)
if __name__ == "__main__":
    cap = float(sys.argv[1])
    for r in (0.01, 0.02):
        for e, s in zip(sys.argv[2::2], sys.argv[3::2]):
            print(f"資金{cap:,.0f} 許容{r*100:.0f}% entry{e} stop{s}:", size(cap, r, float(e), float(s)))
