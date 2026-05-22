"""从产物里统计筛选「精选集」:挑跨风格反差高的 cell,
每个 cell 用 per-piece 借词率(phase1)或句长漂移(phase2)选最具传染性的一篇。
打印每 cell top-3 备选,复制选中篇到 精选集/,并生成索引。
"""
import re
import shutil
import statistics as stats
import sys
from collections import Counter
from math import log
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config

ROOT = Path(__file__).resolve().parent.parent
READINGS = ROOT / "readings"
OUT = ROOT / "精选集"
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


def sent_len(text):
    s = [x for x in re.split(rf"[{re.escape(SENT_END)}]", text) if x.strip()]
    return stats.mean([hz(x) for x in s]) if s else 0


def borrow(text, fp):
    g = ngrams(text); t = sum(g.values()) or 1
    return sum(f for k, f in g.items() if k in fp) / t * 100


def build_fp():
    cfg = load_config()
    src_g = {}
    for s in [x["short_name"] for x in cfg.styles]:
        g = Counter()
        for t in (READINGS / s).glob("*.txt"):
            g.update(ngrams(t.read_text(encoding="utf-8")))
        src_g[s] = g
    for nm, fn in [("白洁", "白洁_full.txt"), ("斗破", "斗破_full.txt")]:
        src_g[nm] = ngrams((ROOT / "origins" / fn).read_text(encoding="utf-8"))
    allg = set()
    for g in src_g.values():
        allg |= set(g)
    N = len(src_g); df = Counter(k for k in allg for g in src_g.values() if k in g)
    fp = {}
    for s, g in src_g.items():
        sc = {k: f*log(N/df[k]) for k, f in g.items() if f >= 3 and df[k] < N and log(N/df[k]) > 0}
        fp[s] = set(k for k, _ in sorted(sc.items(), key=lambda x: -x[1])[:200])
    return fp


# (展示标题, cell目录, 源, 排序指标, 用户指定篇号None/int, 一句话看点)
CANDIDATES = [
    ("金庸被王小波带跑", "outputs/武侠/反讽", "反讽", "borrow", None, "议论腔混进刀光剑影"),
    ("海明威读情欲", "outputs/极简/情欲", "情欲", "borrow", 7, "冰山极简碰上暧昧凝视(你指定)"),
    ("汪曾祺读爽文", "outputs/清欢/网文", "网文", "borrow", 10, "淡味小品里冒出修为等级(你指定)"),
    ("金庸读郭敬明", "outputs/武侠/纯爱", "纯爱", "borrow", None, "侠客忽然伤春悲秋"),
    ("天蚕土豆读王小波", "outputs/网文/反讽", "反讽", "borrow", None, "爽文作家被塞进哲学反讽"),
    ("王小波被灌糖", "outputs/反讽/纯爱", "纯爱", "borrow", None, "冷峻反讽被郭敬明腔软化"),
    ("天蚕土豆读自己的黄暴同人", "outputs/网文/斗破", "斗破", "句长", None, "phase2:读色情同人,写成干净爽文"),
    ("情欲读真人情色(白洁)", "outputs/情欲/白洁", "白洁", "句长", None, "phase2:长句重力被真人原文拉满"),
    ("海明威发糖", "outputs/极简/纯爱", "纯爱", "borrow", None, "冰山极简被郭敬明灌糖"),
    ("王小波读少妇白洁", "outputs/反讽/白洁", "白洁", "句长", None, "phase2:王小波冷峻反讽碰真人情色"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fp = build_fp()
    OUT.mkdir(exist_ok=True)
    index = []
    for title, cell, src, metric, override, note in CANDIDATES:
        d = ROOT / cell
        files = sorted(d.glob("*.txt"))
        if not files:
            print(f"⚠️ 跳过 {title}: {cell} 为空"); continue
        scored = []
        for f in files:
            txt = f.read_text(encoding="utf-8")
            scored.append((f, borrow(txt, fp[src]), sent_len(txt)))
        key = (lambda r: r[1]) if metric == "borrow" else (lambda r: r[2])
        scored.sort(key=key, reverse=True)
        # 选中:用户指定优先,否则排序第一
        pick = None
        if override is not None:
            pick = next((r for r in scored if f"{override:02d}.txt" in r[0].name), None)
        if pick is None:
            pick = scored[0]
        print(f"\n【{title}】 {cell}  排序={metric}")
        for f, bw, sl in scored[:3]:
            mark = "← 选" if f is pick[0] else "  "
            print(f"  {mark} {f.name}  借词率={bw:.2f}  句长={sl:.1f}")
        dst = OUT / f"{title}_{pick[0].name}"
        shutil.copy(pick[0], dst)
        index.append((title, dst.name, src, metric, pick[1], pick[2], note))

    # 索引
    lines = ["# 精选集 — 污染最显眼的几篇\n",
             "> 统计筛选:phase1 取借词率最高(词汇被污染最狠)、phase2 取句长最长(借词锁死,看句法跑偏)的一篇。",
             "> 都是 AI 产物,题目都是「幻林折枝」。想看完整对照去 `outputs/`。\n",
             "| 看点 | 文件 | 源 | 选取依据 | 借词率 | 句长 |",
             "|---|---|---|---|---|---|"]
    for title, fn, src, metric, bw, sl, note in index:
        lines.append(f"| {note} | `{fn}` | {src} | {metric} | {bw:.2f} | {sl:.1f} |")
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n✓ 复制 {len(index)} 篇到 精选集/ + 写入 精选集/README.md")


if __name__ == "__main__":
    main()
