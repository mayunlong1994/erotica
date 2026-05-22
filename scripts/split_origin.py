"""把真人原文切成 N 段 × 800-1000 汉字, 接入 readings/ 作为新污染源。

按段落边界累积切分(不从句子中间断), 清洗分隔符/水印。
连续取前 N 段(代表原文的叙事节奏, 而非挑段)。

用法:
    py scripts/split_origin.py <origin_txt> <源短名> [段数=20]
示例:
    py scripts/split_origin.py origins/白洁.txt 白洁 20
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def hz(s):
    return sum(1 for c in s if "一" <= c <= "鿿")


def clean_line(line):
    line = line.strip()
    # 去掉 ＊＊＊ / *** / ===== 之类的分隔行
    if not line:
        return ""
    if re.fullmatch(r"[＊*=\-—_~·\s]+", line):
        return ""
    # 去掉常见网站水印 / 章节行(保守: 只去明显的)
    if re.search(r"(www\.|http|\.com|\.net|手机阅读|本书来自|更新最快|第\s*[一二三四五六七八九十百千\d]+\s*章)", line):
        return ""
    return line


def main():
    if len(sys.argv) < 3:
        print("用法: py scripts/split_origin.py <origin_txt> <源短名> [段数=20]")
        sys.exit(1)
    origin = Path(sys.argv[1])
    if not origin.is_absolute():
        origin = ROOT / origin
    short = sys.argv[2]
    n_target = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    raw = origin.read_text(encoding="utf-8")
    paras = [clean_line(l) for l in raw.split("\n")]
    paras = [p for p in paras if p]

    # 按段落累积到 800-1000 汉字
    pieces = []
    buf, buf_len = [], 0
    for p in paras:
        plen = hz(p)
        if buf_len + plen > 1150 and buf_len >= 1000:
            pieces.append("\n\n".join(buf))
            buf, buf_len = [p], plen
        else:
            buf.append(p)
            buf_len += plen
    if buf and buf_len >= 800:  # 末段够长也收
        pieces.append("\n\n".join(buf))

    print(f"原文 {hz(raw)} 汉字 → 切出 {len(pieces)} 段")
    for i, pc in enumerate(pieces, 1):
        print(f"  段{i:02d}: {hz(pc)} 汉字" + ("  [取用]" if i <= n_target else "  [弃用]"))

    if len(pieces) < n_target:
        print(f"\n⚠️ 只切出 {len(pieces)} 段, 不足 {n_target} 段。原文需更长。")
        return

    # 写入 readings/{short}/
    out_dir = ROOT / "readings" / short
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n_target):
        (out_dir / f"{short}{i+1:02d}.txt").write_text(pieces[i], encoding="utf-8")
    print(f"\n✓ 已写入 {n_target} 段到 readings/{short}/")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
