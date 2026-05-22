"""白洁 phase-2 多基线分析:
对比 3 个基线作家 {极简, 情欲, 反讽} 各自被 {白洁原版, 白洁A, 白洁B, AI情欲} 污染的
借词率 + 句法漂移 + 总字数。每个基线 vs 自己的「中性」读取条件 (n=20)。

- 白洁指纹: origins/白洁_full.txt 作第 8 源, 跟 7 个 AI 源一起算 TF-IDF。
- 白洁三档(原版/A/B)借词率用「白洁指纹」; AI对照(情欲)用「情欲指纹」。
- z = |均值 - 中性均值| / 中性sd。
- 加 总字数 作协变量(发现各 cell 产出长度差异明显)。
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
    return {
        "总字数": hz(text),
        "句长": stats.mean(slen),
        "段长": stats.mean(plen) if plen else 0,
    }


def borrow(text, fp):
    g = ngrams(text); t = sum(g.values()) or 1
    return sum(f for k, f in g.items() if k in fp) / t * 100


def cell_stats(files, fp):
    rows = []
    for f in files:
        txt = f.read_text(encoding="utf-8")
        rows.append({**syn(txt), "借词率": borrow(txt, fp)})
    keys = rows[0].keys()
    return {k: (stats.mean(r[k] for r in rows),
                stats.stdev([r[k] for r in rows]) if len(rows) > 1 else 0) for k in keys}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    styles = [s["short_name"] for s in cfg.styles]

    # 各源 n-gram (7 AI + 白洁)
    src_g = {}
    for s in styles:
        g = Counter()
        for t in (READINGS / s).glob("*.txt"):
            g.update(ngrams(t.read_text(encoding="utf-8")))
        src_g[s] = g
    src_g["白洁"] = ngrams((ROOT / "origins" / "白洁_full.txt").read_text(encoding="utf-8"))

    # TF-IDF 指纹 (8 源)
    allg = set()
    for g in src_g.values():
        allg |= set(g)
    N = len(src_g)
    df = Counter(k for k in allg for g in src_g.values() if k in g)
    fp = {}
    for s, g in src_g.items():
        sc = {k: f*log(N/df[k]) for k, f in g.items() if f >= 3 and df[k] < N and log(N/df[k]) > 0}
        fp[s] = set(k for k, _ in sorted(sc.items(), key=lambda x: -x[1])[:200])

    metrics = ["借词率", "总字数", "句长", "段长"]
    baselines = ["极简", "情欲", "反讽"]
    # (标签, v2 cell 目录, 用哪个指纹)
    cell_spec = [
        ("读白洁(原版)", "读白洁", "白洁"),
        ("读白洁A",      "读白洁A", "白洁"),
        ("读白洁B",      "读白洁B", "白洁"),
        ("读情欲(AI对照)", "读情欲", "情欲"),
    ]

    for b in baselines:
        neu_files = sorted((OUTPUTS / b / "中性").glob("*.txt"))
        base_bj = cell_stats(neu_files, fp["白洁"])   # 白洁指纹基线
        base_qy = cell_stats(neu_files, fp["情欲"])   # 情欲指纹基线
        print(f"\n{'='*78}\n基线作家: {b}  (vs 自身「中性」读取, n={len(neu_files)})\n{'='*78}")
        # 中性行
        row = f"{(b+'·中性'):<20}"
        for m in metrics:
            bb = base_bj if m == "借词率" else base_bj  # 中性自身用白洁fp展示借词
            row += f"{bb[m][0]:>9.2f}        "
        print(f"{'cell':<20}" + "".join(f"{m:>17}" for m in metrics))
        print(row)
        for label, suffix, srcfp in cell_spec:
            files = sorted((V2 / f"{b}{suffix}").glob("*.txt"))
            if not files:
                print(f"{(b+label):<20}  [缺失]")
                continue
            st = cell_stats(files, fp[srcfp])
            bb = base_bj if srcfp == "白洁" else base_qy
            row = f"{(b+label):<20}"
            for m in metrics:
                mean = st[m][0]
                bmean, bsd = bb[m]
                z = abs(mean - bmean) / bsd if bsd > 0 else 0
                flag = "!" if z >= 2 else ("." if z >= 1 else " ")
                row += f"{mean:>8.2f}({z:>4.1f}{flag})"
            print(row)
        print("注: 借词率列 白洁三档用白洁指纹、情欲档用情欲指纹; 括号内 z=|vs该基线中性|/中性sd")


if __name__ == "__main__":
    main()
