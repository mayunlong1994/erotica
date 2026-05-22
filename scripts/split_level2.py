"""把 2 级(露骨)句子按逗号类标点拆成分句, 生成分句清单供第二遍标注。
用于 B 版: 只删分句级仍判 2 的部分, 保留同句里的非露骨分句。

输出:
  data_work/白洁full_L2分句.tsv    每行: 分句ID<TAB>分句文本   (分句ID = 原句号_序号)
  data_work/白洁full_L2分句.json   分句ID -> {原句号, 序, 文本}
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data_work"
NAME = "白洁full"

# 分句标点(逗号/顿号/分号); 不拆冒号(常引出引语)和句末标点
SPLIT_PUNCT = "，,、；;"


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


def split_clauses(text):
    # 在分句标点后切, 保留标点
    parts = re.split(rf"(?<=[{SPLIT_PUNCT}])", text)
    return [p for p in (x.strip() for x in parts) if p]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sents, labels = load()
    l2_ids = [i for i in sorted(sents) if labels.get(i) == 2]

    rows = []        # (分句ID, 文本)
    mapping = {}
    for sid in l2_ids:
        clauses = split_clauses(sents[sid])
        for j, cl in enumerate(clauses, 1):
            cid = f"{sid}_{j}"
            rows.append((cid, cl))
            mapping[cid] = {"sent": sid, "seq": j, "text": cl}

    tsv = WORK / f"{NAME}_L2分句.tsv"
    with open(tsv, "w", encoding="utf-8") as f:
        for cid, cl in rows:
            f.write(f"{cid}\t{cl}\n")
    (WORK / f"{NAME}_L2分句.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=0), encoding="utf-8")

    print(f"2 级句 {len(l2_ids)} 句 → 拆成 {len(rows)} 个分句")
    print(f"  平均每句 {len(rows)/len(l2_ids):.1f} 个分句")
    print(f"  清单: {tsv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
