"""一次性: 把 readings/白洁/ 的专名替换成中性名, 生成 readings/白洁B/。
只改人名, 不删任何露骨内容 —— 用于检验"名字触发 vs 内容触发"。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\Claude\EROTICA")
src = ROOT / "readings" / "白洁"
dst = ROOT / "readings" / "白洁B"
dst.mkdir(parents=True, exist_ok=True)

# 专名 → 中性名 (大众化、无 IP 关联)
REPL = {
    "白洁": "林岚",
    "高义": "赵海",
    "王申": "陈帆",
    "王芬": "刘梅",
}

for f in sorted(src.glob("*.txt")):
    t = f.read_text(encoding="utf-8")
    for a, b in REPL.items():
        t = t.replace(a, b)
    newname = f.name.replace("白洁", "白洁B")
    (dst / newname).write_text(t, encoding="utf-8")

# 校验残留
remain = 0
for f in dst.glob("*.txt"):
    txt = f.read_text(encoding="utf-8")
    for a in REPL:
        remain += txt.count(a)
print(f"写入 {len(list(dst.glob('*.txt')))} 段到 readings/白洁B/, 原专名残留 {remain} 处")
