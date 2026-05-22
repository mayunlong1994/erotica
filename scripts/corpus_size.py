"""统计各污染源 readings 的材料总量(喂进 prompt 的 20 篇/段), 对比是否量级一致。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\Claude\EROTICA")
READINGS = ROOT / "readings"


def hz(s): return sum(1 for c in s if "一" <= c <= "鿿")

# 关注的污染源
srcs = ["白洁", "白洁A", "白洁B", "情欲", "反讽", "纯爱", "网文", "极简", "武侠", "清欢"]
print(f"{'源':<8}{'篇数':>6}{'总汉字':>10}{'篇均':>8}{'最短':>8}{'最长':>8}")
for s in srcs:
    d = READINGS / s
    if not d.exists():
        continue
    files = sorted(d.glob("*.txt"))
    lens = [hz(f.read_text(encoding="utf-8")) for f in files]
    if not lens:
        continue
    print(f"{s:<8}{len(lens):>6}{sum(lens):>10}{sum(lens)//len(lens):>8}{min(lens):>8}{max(lens):>8}")

# prompt 文件字符数对比
print("\nprompt 字符数(含背景+20材料+指令):")
pdir = ROOT / "v2_test" / "prompts"
for name in ["武侠读白洁", "武侠读白洁A", "武侠读白洁B", "武侠读情欲", "武侠读反讽", "武侠读纯爱"]:
    p = pdir / f"{name}.txt"
    if p.exists():
        print(f"  {name}: {len(p.read_text(encoding='utf-8'))}")
