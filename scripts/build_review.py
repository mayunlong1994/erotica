"""合并 sentences + labels(自动 glob 分批文件), 生成人工核查用对照文件。
用法: py scripts/build_review.py [源名=白洁v2]
输出(均在 data_work/):
  {名}_对照.tsv        编号<TAB>等级<TAB>句子  (按原文顺序, 可导入 Excel)
  {名}_对照_按等级.txt  分 0/1/2 三组, 看每级同质性/误判
  {名}_顺读.txt        等级|编号|句子 按原文顺序, 行首竖扫看密度节奏
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data_work"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    name = sys.argv[1] if len(sys.argv) > 1 else "白洁v2"

    sents = json.loads((WORK / f"{name}_sentences.json").read_text(encoding="utf-8"))
    sents = {int(k): v for k, v in sents.items()}

    labels, dup = {}, []
    label_files = sorted(WORK.glob(f"{name}_labels*.tsv"))
    for p in label_files:
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*(\d+)\s*[\t,]\s*([012])\s*$", line)
            if not m:
                continue
            sid, lv = int(m.group(1)), int(m.group(2))
            if sid in labels and labels[sid] != lv:
                dup.append((sid, labels[sid], lv))
            labels[sid] = lv

    all_ids = set(sents)
    missing = sorted(all_ids - set(labels))

    # 1. 按编号对照 tsv
    with open(WORK / f"{name}_对照.tsv", "w", encoding="utf-8") as f:
        f.write("编号\t等级\t句子\n")
        for sid in sorted(all_ids):
            f.write(f"{sid}\t{labels.get(sid,'?')}\t{sents[sid]}\n")

    # 2. 按等级分组
    with open(WORK / f"{name}_对照_按等级.txt", "w", encoding="utf-8") as f:
        for lv in (0, 1, 2):
            ids = [s for s in sorted(all_ids) if labels.get(s) == lv]
            f.write(f"\n{'='*60}\n等级 {lv}  —  共 {len(ids)} 句\n{'='*60}\n")
            for sid in ids:
                f.write(f"[{sid}] {sents[sid]}\n")

    # 3. 顺读
    with open(WORK / f"{name}_顺读.txt", "w", encoding="utf-8") as f:
        f.write("# 等级 | 编号 | 句子  (按原文顺序; 行首 0/1/2 竖扫看露骨度节奏)\n\n")
        for sid in sorted(all_ids):
            f.write(f"{labels.get(sid,'?')}  [{sid:>3}]  {sents[sid]}\n")

    dist = {lv: sum(1 for v in labels.values() if v == lv) for lv in (0, 1, 2)}
    print(f"源: {name}  句数: {len(all_ids)}  已标注: {len(labels)}  标注文件 {len(label_files)} 个")
    if missing:
        print(f"⚠️ 漏标 {len(missing)}: {missing[:20]}")
    if dup:
        print(f"⚠️ 冲突 {len(dup)}: {dup[:10]}")
    total = sum(dist.values())
    print(f"分布: 0={dist[0]}({dist[0]*100//total}%)  1={dist[1]}({dist[1]*100//total}%)  2={dist[2]}({dist[2]*100//total}%)")
    print(f"输出: {name}_对照.tsv / {name}_对照_按等级.txt / {name}_顺读.txt (在 data_work/)")


if __name__ == "__main__":
    main()
