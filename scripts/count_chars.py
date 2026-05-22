"""统计指定源目录(拼好的20段)里特定字的出现次数和密度。
用法: py scripts/count_chars.py 乳 胸
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\Claude\EROTICA\readings")
chars = sys.argv[1:] if len(sys.argv) > 1 else ["乳", "胸"]


def hz(s):
    return sum(1 for c in s if "一" <= c <= "鿿")


for src in ["白洁A", "白洁B", "白洁"]:
    d = ROOT / src
    if not d.exists():
        continue
    text = "".join(f.read_text(encoding="utf-8") for f in sorted(d.glob("*.txt")))
    total = hz(text)
    n_files = len(list(d.glob("*.txt")))
    print(f"\n=== {src} ({n_files} 段, {total} 汉字) ===")
    sub = 0
    for ch in chars:
        c = text.count(ch)
        sub += c
        print(f"  「{ch}」 {c} 次  ({c/total*1000:.2f}/千字)")
    print(f"  合计 {sub} 次  ({sub/total*1000:.2f}/千字)")
