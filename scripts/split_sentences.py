"""把原文切成带编号的句子清单, 供 LLM 露骨度标注用。
输出:
  data_work/{源名}_sentences.tsv   每行: id<TAB>句子
  data_work/{源名}_sentences.json  id -> 句子 映射(供后续重组)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data_work"
WORK.mkdir(exist_ok=True)


def hz(s):
    return sum(1 for c in s if "一" <= c <= "鿿")


def clean(raw):
    out = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"[＊*=\-—_~·\s]+", line):
            continue
        out.append(line)
    return "\n".join(out)


def split_sentences(text, min_hz=10):
    """按句末标点切, 然后把过短片段(< min_hz 汉字, 含纯标点/语气词/省略号)
    并入相邻句, 避免碎片单句。"""
    # 句末标点后切; 不含省略号…(它常在句中表停顿/拟声, 切了会断裂);
    # 且若紧跟闭引号(”"」』)则不切, 让 。" 整体归前句
    parts = re.split(r'(?<=[。！？!?；])(?![”"」』])', text.replace("\n", ""))
    raw = [p.strip() for p in parts if p.strip()]
    merged = []
    for seg in raw:
        if merged and hz(seg) < min_hz:
            merged[-1] += seg          # 短片段并入前一句
        else:
            merged.append(seg)
    # 若开头几句仍过短(无前句可并), 向后并入
    while len(merged) >= 2 and hz(merged[0]) < min_hz:
        merged[1] = merged[0] + merged[1]
        merged.pop(0)
    return merged


def main():
    if len(sys.argv) < 3:
        print("用法: py scripts/split_sentences.py <origin_txt> <源名>")
        sys.exit(1)
    origin = Path(sys.argv[1])
    if not origin.is_absolute():
        origin = ROOT / origin
    name = sys.argv[2]

    raw = clean(origin.read_text(encoding="utf-8"))
    sents = split_sentences(raw)

    tsv = WORK / f"{name}_sentences.tsv"
    mapping = {}
    with open(tsv, "w", encoding="utf-8") as f:
        for i, s in enumerate(sents, 1):
            f.write(f"{i}\t{s}\n")
            mapping[i] = s
    (WORK / f"{name}_sentences.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=0), encoding="utf-8")

    lens = [hz(s) for s in sents]
    short = sum(1 for x in lens if x < 10)
    print(f"{name}: {len(sents)} 句, 总 {sum(lens)} 汉字, 句均 {sum(lens)//len(sents)} 字")
    print(f"  最长句 {max(lens)} 字, 最短 {min(lens)} 字, <10字的句子 {short} 句")
    print(f"  清单: {tsv.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
