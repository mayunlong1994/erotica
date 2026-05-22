"""把一个 tsv 切成 N 个子文件, 供多 subagent 并行标注。
用法: py scripts/chunk_tsv.py <文件名(不含.tsv)> <份数>
"""
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
WORK = Path(r"E:\Claude\EROTICA\data_work")
name, n = sys.argv[1], int(sys.argv[2])
lines = [l for l in (WORK / f"{name}.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
sz = math.ceil(len(lines) / n)
for i in range(n):
    chunk = lines[i * sz:(i + 1) * sz]
    if chunk:
        out = WORK / f"{name}_part{i+1}.tsv"
        out.write_text("\n".join(chunk), encoding="utf-8")
        print(f"part{i+1}: {len(chunk)} 行 -> {out.name}")
