"""一次性: 合并用户的 白洁.txt(ch9-19) + 提取的 白洁_扩充.txt(ch20-25) → 白洁_full.txt"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
O = Path(r"E:\Claude\EROTICA\origins")
a = (O / "白洁.txt").read_text(encoding="utf-8").rstrip()
b = (O / "白洁_扩充.txt").read_text(encoding="utf-8").strip()
full = a + "\n" + b
(O / "白洁_full.txt").write_text(full, encoding="utf-8")
hz = sum(1 for c in full if "一" <= c <= "鿿")
print(f"合并完成: 白洁_full.txt, {hz} 汉字")
