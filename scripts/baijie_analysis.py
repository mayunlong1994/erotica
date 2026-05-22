"""白洁 phase-1 专项分析:
对比 武侠基线 被 {白洁原版, 白洁A, 白洁B, AI情欲} 污染的 借词率 + 句法漂移。
- 白洁指纹: 用 origins/白洁_full.txt 作第 8 源, 跟 7 个 AI 源一起算 TF-IDF。
- 基线: outputs/武侠/中性 (n=20)。
- 漂移: 各 cell 均值 vs 中性, z = |delta|/中性sd。
"""
import json
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
    np_ = len(paras) or 1
    plen = [hz(p) for p in paras]
    sents = [s for s in re.split(rf"[{re.escape(SENT_END)}]", text) if s.strip()]
    slen = [hz(s) for s in sents] or [0]
    dia = sum(1 for p in paras if "“" in p or "”" in p or '"' in p)
    tot = hz(text) or 1
    disc = ["其实","总之","也就是","不过","然而","这就","这便","这种","不必",
            "因此","不妨","所谓","无非","毕竟","大概","所以"]
    return {
        "句长": stats.mean(slen),
        "段长": stats.mean(plen) if plen else 0,
        "对话密度": dia/np_,
        "议论密度": sum(text.count(m) for m in disc)/tot*1000,
    }


def borrow(text, fp):
    g = ngrams(text); t = sum(g.values()) or 1
    return sum(f for k,f in g.items() if k in fp)/t*100


def cell_stats(files, fp):
    rows = [{**syn(f.read_text(encoding="utf-8")),
             "借词率": borrow(f.read_text(encoding="utf-8"), fp)} for f in files]
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
    allg = set();
    for g in src_g.values(): allg |= set(g)
    N = len(src_g)
    df = Counter(k for k in allg for g in src_g.values() if k in g)
    fp = {}
    for s, g in src_g.items():
        sc = {k: f*log(N/df[k]) for k,f in g.items() if f>=3 and df[k]<N and log(N/df[k])>0}
        fp[s] = set(k for k,_ in sorted(sc.items(), key=lambda x:-x[1])[:200])

    print("白洁指纹 top30:", "、".join(list(fp["白洁"])[:30]))

    # 基线 武侠中性
    neu_files = sorted((OUTPUTS / "武侠" / "中性").glob("*.txt"))
    base = cell_stats(neu_files, fp["白洁"])
    base_qy = cell_stats(neu_files, fp["情欲"])  # 情欲指纹基线

    cells = [
        ("武侠读白洁(原版)", "武侠读白洁", "白洁"),
        ("武侠读白洁A", "武侠读白洁A", "白洁"),
        ("武侠读白洁B", "武侠读白洁B", "白洁"),
        ("武侠读情欲(AI对照)", "武侠读情欲", "情欲"),
    ]
    metrics = ["借词率", "句长", "段长", "对话密度", "议论密度"]
    print(f"\n{'cell':<22}" + "".join(f"{m:>14}" for m in metrics))
    print(f"{'武侠中性(基线)':<22}" + "".join(
        f"{(base if m!='借词率' else None) and base[m][0] or (base[m][0] if m=='借词率' else base[m][0]):>14.2f}" for m in metrics))
    for label, cell, srcfp in cells:
        files = sorted((V2 / cell).glob("*.txt"))
        st = cell_stats(files, fp[srcfp])
        bb = base if srcfp == "白洁" else base_qy
        row = f"{label:<22}"
        for m in metrics:
            mean = st[m][0]; bmean, bsd = bb[m]
            z = abs(mean-bmean)/bsd if bsd>0 else 0
            flag = "!" if z>=2 else ("." if z>=1 else " ")
            row += f"{mean:>8.2f}({z:.1f}{flag})"
        print(row)
    print("\n借词率列: 白洁三档用白洁指纹, 情欲档用情欲指纹; 括号内 z=vs武侠中性")


if __name__ == "__main__":
    main()
