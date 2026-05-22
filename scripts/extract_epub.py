"""从 epub 抽取连续章节正文 → origins/{源名}_full.txt (一段一行, 保留分段)。
仿照白洁流程, 供 split_sentences / 脱敏管线接入。

用法:
    py scripts/extract_epub.py <epub路径> <起章> <止章> <输出源名>
示例:
    py scripts/extract_epub.py "origins/斗破苍穹之淫宗肆虐-琉璃狐.epub" 1 13 斗破
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def hz(s):
    return sum(1 for c in s if "一" <= c <= "鿿")


def text_of(html):
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    out = []
    for para in re.findall(r"(?is)<p[^>]*>(.*?)</p>", h):
        t = re.sub(r"(?s)<[^>]+>", "", para)
        t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
             .replace("&lt;", "<").replace("&gt;", ">").replace("　", ""))
        t = t.strip()
        # 丢弃装饰行(| 古典情色 | 末语 之类)与空段
        if t and not t.startswith("|") and "古典情色" not in t:
            out.append(t)
    return out


def main():
    if len(sys.argv) < 5:
        print("用法: py scripts/extract_epub.py <epub> <起章> <止章> <源名>")
        sys.exit(1)
    epub = Path(sys.argv[1])
    if not epub.is_absolute():
        epub = ROOT / epub
    c0, c1, name = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]

    z = zipfile.ZipFile(epub)
    paras = []
    for i in range(c0, c1 + 1):
        try:
            raw = z.read(f"OEBPS/chapter{i}.html").decode("utf-8", "ignore")
        except KeyError:
            continue
        paras.extend(text_of(raw))

    out = ROOT / "origins" / f"{name}_full.txt"
    out.write_text("\n".join(paras), encoding="utf-8")
    total = sum(hz(p) for p in paras)
    print(f"{name}: ch{c0}-{c1}, {len(paras)} 段, {total} 汉字 → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
