"""按露骨度标注重组脱敏版白洁, 接入 readings/ 作污染源。

A 版: 保留 {0,1} 级句子(删全部 2 级)
(B 版: 保留 {0,1} + 低尺度 2 级, 需第二遍分句标注, 另脚本)

用法:
    py scripts/dehydrate.py A            # 预览: 保留字数、能切几段
    py scripts/dehydrate.py A --write 白洁A   # 重组并写入 readings/白洁A/ (20段)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data_work"
# 可被 --src 覆盖: base=白洁 → NAME=白洁full, 原文=origins/白洁_full.txt
BASE = "白洁"
NAME = "白洁full"
ORIGIN = "白洁_full.txt"


def hz(s):
    return sum(1 for c in s if "一" <= c <= "鿿")


def load():
    sents = json.loads((WORK / f"{NAME}_sentences.json").read_text(encoding="utf-8"))
    sents = {int(k): v for k, v in sents.items()}
    labels = {}
    for p in sorted(WORK.glob(f"{NAME}_labels*.tsv")):
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*(\d+)\s*[\t,]\s*([012])\s*$", line)
            if m:
                labels[int(m.group(1))] = int(m.group(2))
    return sents, labels


def repack(sents, keep_ids, seg_target=900, seg_min=800, seg_max=1000):
    """把保留的句子按原文顺序拼成连续文本, 切成 800-1000 字的段。"""
    kept = [sents[i] for i in sorted(keep_ids)]
    pieces, buf, blen = [], [], 0
    for s in kept:
        slen = hz(s)
        if blen + slen > seg_max and blen >= seg_min:
            pieces.append("".join(buf))
            buf, blen = [s], slen
        else:
            buf.append(s)
            blen += slen
    if buf and blen >= 600:
        pieces.append("".join(buf))
    return pieces


def load_clauses():
    """B 版用: 分句映射 + 分句标注。"""
    mp = json.loads((WORK / f"{NAME}_L2分句.json").read_text(encoding="utf-8"))
    clabels = {}
    for p in sorted(WORK.glob(f"{NAME}_L2labels*.tsv")):
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*(\d+_\d+)\s*[\t,]\s*([012])\s*$", line)
            if m:
                clabels[m.group(1)] = int(m.group(2))
    return mp, clabels


def load_paras(sents):
    """还原每句的原文段落号(基于 origins/白洁_full.txt 的 \\n 分段)。"""
    raw = (ROOT / "origins" / ORIGIN).read_text(encoding="utf-8")
    paras = []
    for line in raw.split("\n"):
        line = line.strip()
        if line and not re.fullmatch(r"[＊*=\-—_~·\s]+", line):
            paras.append(line)
    bounds, cum = [], 0
    for p in paras:
        cum += hz(p); bounds.append(cum)
    id2para, acc, pi = {}, 0, 0
    for i in sorted(sents):
        acc += hz(sents[i])
        while pi < len(bounds) - 1 and acc > bounds[pi]:
            pi += 1
        id2para[i] = pi
    return id2para


def build_units(version, sents, labels):
    """返回 [(文本, 原段落号)], 按原句号顺序。重组时用段落号还原分段。"""
    id2para = load_paras(sents)
    if version == "A":
        return [(sents[i], id2para[i]) for i in sorted(sents) if labels.get(i) in (0, 1)]
    # B 版
    mp, clabels = load_clauses()
    by_sent = {}
    for cid, info in mp.items():
        by_sent.setdefault(info["sent"], []).append((info["seq"], cid, info["text"]))
    units = []
    for i in sorted(sents):
        lv = labels.get(i)
        if lv in (0, 1):
            units.append((sents[i], id2para[i]))
        elif lv == 2:
            clauses = sorted(by_sent.get(i, []))
            kept = "".join(t for _, cid, t in clauses if clabels.get(cid) in (0, 1))
            if hz(kept) >= 4:
                units.append((kept, id2para[i]))
    return units


def main():
    if len(sys.argv) < 2:
        print("用法: py scripts/dehydrate.py <A|B> [--write 源名]")
        sys.exit(1)
    version = sys.argv[1].upper()
    write = "--write" in sys.argv
    out_name = sys.argv[sys.argv.index("--write") + 1] if write else None
    global BASE, NAME, ORIGIN
    if "--src" in sys.argv:
        BASE = sys.argv[sys.argv.index("--src") + 1]
        NAME = f"{BASE}full"
        ORIGIN = f"{BASE}_full.txt"

    sents, labels = load()
    units = build_units(version, sents, labels)
    kept_hz = sum(hz(u) for u, _ in units)
    total_hz = sum(hz(s) for s in sents.values())
    print(f"版本 {version}: 保留 {len(units)} 个文本单元 / {kept_hz} 汉字 "
          f"(原文 {total_hz}, 保留 {kept_hz*100//total_hz}%)")

    # 先按原段落号还原分段(同段直连, 跨段插空行), 再按 800-1000 切段
    blocks, cur, prev = [], [], None
    for text, para in units:
        if prev is not None and para != prev and cur:
            blocks.append("".join(cur)); cur = []
        cur.append(text); prev = para
    if cur:
        blocks.append("".join(cur))

    pieces, buf, blen = [], [], 0
    for blk in blocks:
        blen_b = hz(blk)
        if blen + blen_b > 1150 and blen >= 1000:
            pieces.append("\n\n".join(buf)); buf, blen = [blk], blen_b
        else:
            buf.append(blk); blen += blen_b
    if buf and blen >= 800:
        pieces.append("\n\n".join(buf))

    print(f"  可切成 {len(pieces)} 段" + ("  ✓ 够 20 段" if len(pieces) >= 20 else f"  ⚠️ 不足 20"))

    if write:
        out_dir = ROOT / "readings" / out_name
        out_dir.mkdir(parents=True, exist_ok=True)
        n = min(20, len(pieces))
        for i in range(n):
            (out_dir / f"{out_name}{i+1:02d}.txt").write_text(pieces[i], encoding="utf-8")
        print(f"  ✓ 写入 {n} 段到 readings/{out_name}/")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
