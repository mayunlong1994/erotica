"""白洁 v1(有抵抗) vs v2(无抵抗) 配对分析。
同一 基线×源, 比较「有抵抗指令」与「无抵抗指令」两种提示词下的污染强度。
- v1 cell: outputs/{基线}/{源}/      (有抵抗, 题目在前)
- v2 cell: v2_test/outputs/{基线}读{源}/ (无抵抗, 题目在后)
- 共享基准: outputs/{基线}/中性 (两者都以此为参照算漂移)
- 漂移 = cell均值 − 中性均值。看 v2漂移 是否 > v1漂移 (即抵抗指令是否压制传染)。
"""
import re
import statistics as stats
import sys
from collections import Counter
from math import log
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config

ROOT = Path(__file__).resolve().parent.parent
READINGS = ROOT / "readings"
OUTPUTS = ROOT / "outputs"
V2 = ROOT / "v2_test" / "outputs"
SENT_END = "。！？!?…"


def is_ch(c): return "一" <= c <= "鿿"
def hz(s): return sum(1 for c in s if is_ch(c))


def ngrams(text, ns=(2, 3)):
    co = "".join(c for c in text if is_ch(c))
    g = Counter()
    for n in ns:
        for i in range(len(co) - n + 1):
            g[co[i:i+n]] += 1
    return g


def syn(text):
    text = text.strip()
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    plen = [hz(p) for p in paras]
    sents = [s for s in re.split(rf"[{re.escape(SENT_END)}]", text) if s.strip()]
    slen = [hz(s) for s in sents] or [0]
    return {"总字数": hz(text), "句长": stats.mean(slen),
            "段长": stats.mean(plen) if plen else 0}


def borrow(text, fp):
    g = ngrams(text); t = sum(g.values()) or 1
    return sum(f for k, f in g.items() if k in fp) / t * 100


def cell_mean(files, fp):
    if not files:
        return None
    rows = [{**syn(f.read_text(encoding="utf-8")),
             "借词率": borrow(f.read_text(encoding="utf-8"), fp)} for f in files]
    return {k: stats.mean(r[k] for r in rows) for k in rows[0]}


def build_fp():
    cfg = load_config()
    styles = [s["short_name"] for s in cfg.styles]
    src_g = {}
    for s in styles:
        g = Counter()
        for t in (READINGS / s).glob("*.txt"):
            g.update(ngrams(t.read_text(encoding="utf-8")))
        src_g[s] = g
    src_g["白洁"] = ngrams((ROOT / "origins" / "白洁_full.txt").read_text(encoding="utf-8"))
    allg = set()
    for g in src_g.values():
        allg |= set(g)
    N = len(src_g); df = Counter(k for k in allg for g in src_g.values() if k in g)
    fp = {}
    for s, g in src_g.items():
        sc = {k: f*log(N/df[k]) for k, f in g.items() if f >= 3 and df[k] < N and log(N/df[k]) > 0}
        fp[s] = set(k for k, _ in sorted(sc.items(), key=lambda x: -x[1])[:200])
    return fp


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fp = build_fp()
    metrics = ["借词率", "句长", "段长", "总字数"]
    baselines = ["情欲", "武侠", "极简", "反讽"]
    sources = [("白洁", "白洁"), ("白洁A", "白洁"), ("白洁B", "白洁"), ("情欲", "情欲")]

    for b in baselines:
        neu = cell_mean(sorted((OUTPUTS / b / "中性").glob("*.txt")), fp["白洁"])
        neu_qy = cell_mean(sorted((OUTPUTS / b / "中性").glob("*.txt")), fp["情欲"])
        print(f"\n{'='*86}\n基线 {b}  (Δ = cell − 该基线中性; 比较 有抵抗v1 vs 无抵抗v2)\n{'='*86}")
        print(f"{'源':<8}{'指标':<6}{'中性':>9}{'v1有抵抗(Δ)':>18}{'v2无抵抗(Δ)':>18}{'  v2/v1漂移':>12}")
        for src, fpname in sources:
            base = neu_qy if src == "情欲" else neu
            v1 = cell_mean(sorted((OUTPUTS / b / src).glob("*.txt")), fp[fpname])
            v2 = cell_mean(sorted((V2 / f"{b}读{src}").glob("*.txt")), fp[fpname])
            if not v1 or not v2:
                print(f"{src:<8} [缺 v1={bool(v1)} v2={bool(v2)}]")
                continue
            for m in metrics:
                nb = base[m]; d1 = v1[m]-nb; d2 = v2[m]-nb
                ratio = (d2/d1) if abs(d1) > 1e-6 else float('nan')
                rs = f"{ratio:>10.1f}x" if ratio == ratio and abs(d1) > 0.5 else "       —"
                print(f"{src:<8}{m:<6}{nb:>9.2f}{v1[m]:>9.2f}({d1:+6.1f}){v2[m]:>9.2f}({d2:+6.1f}){rs:>12}")
            print("  " + "-"*84)


if __name__ == "__main__":
    main()
