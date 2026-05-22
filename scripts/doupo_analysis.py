"""斗破快分析: 网文基线(天蚕土豆原型) 读 斗破同人(真人) vs 情欲(AI对照) vs 中性。
全部 v1。Δ = cell均值 − 网文中性。斗破档用斗破指纹, 情欲档用情欲指纹。
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
    rows = [{**syn(f.read_text(encoding="utf-8")),
             "借词率": borrow(f.read_text(encoding="utf-8"), fp)} for f in files]
    return {k: stats.mean(r[k] for r in rows) for k in rows[0]} if rows else None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    styles = [s["short_name"] for s in cfg.styles]
    src_g = {}
    for s in styles:
        g = Counter()
        for t in (READINGS / s).glob("*.txt"):
            g.update(ngrams(t.read_text(encoding="utf-8")))
        src_g[s] = g
    src_g["白洁"] = ngrams((ROOT / "origins" / "白洁_full.txt").read_text(encoding="utf-8"))
    src_g["斗破"] = ngrams((ROOT / "origins" / "斗破_full.txt").read_text(encoding="utf-8"))
    allg = set()
    for g in src_g.values():
        allg |= set(g)
    N = len(src_g); df = Counter(k for k in allg for g in src_g.values() if k in g)
    fp = {}
    for s, g in src_g.items():
        sc = {k: f*log(N/df[k]) for k, f in g.items() if f >= 3 and df[k] < N and log(N/df[k]) > 0}
        fp[s] = set(k for k, _ in sorted(sc.items(), key=lambda x: -x[1])[:200])

    print("斗破指纹 top25:", "、".join(list(fp["斗破"])[:25]))
    metrics = ["借词率", "句长", "段长", "总字数"]
    neu = cell_mean(sorted((OUTPUTS / "网文" / "中性").glob("*.txt")), fp["斗破"])
    neu_qy = cell_mean(sorted((OUTPUTS / "网文" / "中性").glob("*.txt")), fp["情欲"])
    cells = [("读斗破(真人原版)", "斗破", "斗破"), ("读斗破A(真人脱敏)", "斗破A", "斗破"),
             ("读情欲(AI对照)", "情欲", "情欲")]
    print(f"\n基线 网文 (Δ = cell − 网文中性, 全 v1)")
    print(f"{'cell':<18}" + "".join(f"{m:>14}" for m in metrics))
    print(f"{'网文·中性':<18}" + "".join(f"{neu[m]:>14.2f}" for m in metrics))
    for label, src, fpn in cells:
        v = cell_mean(sorted((OUTPUTS / "网文" / src).glob("*.txt")), fp[fpn])
        base = neu_qy if fpn == "情欲" else neu
        row = f"{label:<18}"
        for m in metrics:
            d = v[m] - base[m]
            row += f"{v[m]:>8.2f}({d:+5.1f})"
        print(row)
    print("注: 借词率 斗破档用斗破指纹、情欲档用情欲指纹; 中性行借词率用斗破指纹")


if __name__ == "__main__":
    main()
