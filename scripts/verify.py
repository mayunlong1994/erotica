"""快速核验全部资产数量。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent

readings = sum(1 for _ in (ROOT / "readings").rglob("*.txt"))
outputs = sum(1 for _ in (ROOT / "outputs").rglob("*.txt"))
prompts = sum(1 for _ in (ROOT / "prompts").glob("*.txt"))
scripts_n = len(list((ROOT / "scripts").iterdir()))
analyses_n = len(list((ROOT / "analysis").iterdir()))

print(f"readings: {readings} 篇")
print(f"outputs:  {outputs} 篇")
print(f"prompts:  {prompts} 个")
print(f"scripts/: {scripts_n} 个")
print(f"analysis/: {analyses_n} 个")
print()

naked = sum(1 for _ in (ROOT / "outputs").rglob("*/不读/*.txt"))
neutral = sum(1 for _ in (ROOT / "outputs").rglob("*/中性/*.txt"))
polluted = outputs - naked - neutral
print(f"  不读:    {naked}")
print(f"  中性:    {neutral}")
print(f"  污染:    {polluted}")
