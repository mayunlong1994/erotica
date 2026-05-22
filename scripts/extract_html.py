"""从 epub 解压的 chapterN.html 提取正文, 扩充白洁原文池。
只取正文 <p>(排除 class=head 的页眉水印 / <h3> 标题 / logo 图片), 去 HTML 标签。

用法:
    py scripts/extract_html.py <起始章> <结束章>      # 预览各章字数
    py scripts/extract_html.py <起始章> <结束章> --write  # 写出 origins/白洁_扩充.txt
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = ROOT / "origins" / "少妇白洁v1.1" / "OEBPS" / "Text"


def hz(s):
    return sum(1 for c in s if "一" <= c <= "鿿")


def extract_chapter(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    # 只取 <p>...</p>, 但排除 class="head"(页眉) 的
    paras = []
    for m in re.finditer(r'<p(?P<attr>[^>]*)>(?P<body>.*?)</p>', raw, re.DOTALL):
        if 'class="head"' in m.group("attr"):
            continue
        text = m.group("body")
        text = re.sub(r"<[^>]+>", "", text)      # 去内部标签(<b> 等)
        text = html.unescape(text).strip()
        if text:
            paras.append(text)
    return "\n".join(paras)


def main():
    if len(sys.argv) < 3:
        print("用法: py scripts/extract_html.py <起始章> <结束章> [--write]")
        sys.exit(1)
    start, end = int(sys.argv[1]), int(sys.argv[2])
    write = "--write" in sys.argv

    chunks, total = [], 0
    for n in range(start, end + 1):
        p = TEXT_DIR / f"chapter{n}.html"
        if not p.exists():
            print(f"  chapter{n}: (缺失, 跳过)")
            continue
        body = extract_chapter(p)
        c = hz(body)
        total += c
        chunks.append(body)
        print(f"  chapter{n}: {c} 汉字")
    print(f"\n合计 chapter{start}-{end}: {total} 汉字")

    if write:
        out = ROOT / "origins" / "白洁_扩充.txt"
        out.write_text("\n".join(chunks), encoding="utf-8")
        print(f"✓ 写出 {out.relative_to(ROOT)} ({total} 汉字)")
    else:
        print("(预览模式; 加 --write 写出文件)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
