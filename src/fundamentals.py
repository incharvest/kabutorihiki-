"""Yahoo!ファイナンス(日本)の銘柄ページから PER・PBR・信用残・決算要約などを抽出する。"""
import re, html, sys, json, time, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
FIELDS = {
 "PER(会社予想)": r"PER （会社予想） 用語 (\(連\) )?([\d,.\-]+) 倍",
 "PBR(実績)": r"PBR （実績） 用語 (\(連\) )?([\d,.\-]+) 倍",
 "配当利回り": r"配当利回り （会社予想） 用語 ()([\d,.\-]+) %",
 "1株配当": r"1株配当 （会社予想） 用語 ()([\d,.\-]+) 円",
 "時価総額(百万円)": r"時価総額 用語 ()([\d,]+) 百万円",
 "信用買残": r"信用買残 用語 ()([\d,]+) 株 \( (\d\d/\d\d)",
 "信用売残": r"信用売残 用語 ()([\d,]+) 株",
 "信用倍率": r"信用倍率 用語 ()([\d,.\-]+) 倍 \( (\d\d/\d\d)",
}
def get(code):
    req = urllib.request.Request(f"https://finance.yahoo.co.jp/quote/{code}", headers={"User-Agent": UA})
    s = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)))
    out = {"code": code}
    for k, rx in FIELDS.items():
        m = re.search(rx, t)
        out[k] = m.group(2) + (f"（{m.group(3)}時点）" if m and m.lastindex >= 3 and m.group(3) else "") if m else "N/A"
    m = re.search(r"次回の決算発表日は(.{0,30}?)(です|。)", t); out["次回決算"] = m.group(1) if m else "N/A"
    m = re.search(r"決算短信の要約 まとめ (.{0,400}?)(続きを読む|決算|$)", t); out["決算要約"] = m.group(1) if m else "N/A"
    return out
if __name__ == "__main__":
    res = []
    for c in sys.argv[1:]:
        res.append(get(c)); time.sleep(1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
