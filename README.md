# kabutorihiki — 日本株トレード分析ツール

| スクリプト | 用途 |
|---|---|
| `src/fetch.py SYMBOL...` | Yahoo Finance から日足を取得（例 `7203.T` `^N225` `JPY=X`） |
| `src/fetch_all.py` | `src/universe.py` の主要銘柄を一括取得 |
| `src/screen.py` | ユニバースのテクニカル・スクリーニング |
| `src/analyze.py CODE...` | 日足・週足分析（支持/抵抗帯、トレンドライン、MAクロス、RSI・MACD・ストキャス、出来高） |
| `src/fundamentals.py CODE...` | PER・PBR・信用倍率・決算要約（Yahoo!ファイナンス） |
| `src/position_size.py 資金 entry stop ...` | 許容損失1%/2%で100株単位のポジションサイズ |
| `src/backtest.py [--sym ^N225 --years 10 --fee 0.001 --slip 0.0005]` | MAクロス・RSIダイバージェンスのバックテスト |
| `src/daily.sh` | 定期レポート用の一括実行（reports/daily/日付/ に出力） |
| `src/portfolio.py --capital 3000000 --w 7203.T=0.2 ... CASH=0.1` | β・相関・ストレス損失・ヘッジ量 |

必要: Python 3.10+, `pip install pandas numpy`。レポートは `reports/` に保存。投資助言ではありません。
