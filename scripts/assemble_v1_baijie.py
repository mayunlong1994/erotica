"""为白洁三档生成「有抵抗 v1」提示词(复用 assemble_prompts.build_body 的 v1 模板)。
4 基线(武侠/极简/情欲/反讽)× 白洁/白洁A/白洁B = 12 个 prompt。
写到 prompts/{基线}读{源}.txt(与 v1 大矩阵同目录、同命名)。
AI对照(读情欲)与中性已在 outputs/ 里有 v1 数据, 不重跑。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config
from assemble_prompts import build_body, polluted_picks, PROMPTS_DIR

BASELINES = ["武侠", "极简", "情欲", "反讽"]
SOURCES = ["白洁", "白洁A", "白洁B"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    # 可传参: py assemble_v1_baijie.py <基线> <源1> [源2...]; 不传则用白洁默认 4×3
    if len(sys.argv) >= 3:
        baselines, sources = [sys.argv[1]], sys.argv[2:]
    else:
        baselines, sources = BASELINES, SOURCES
    cfg = load_config()
    by_short = {s["short_name"]: s for s in cfg.styles}
    for b in baselines:
        bg = by_short[b]["background"]
        for src in sources:
            paths = polluted_picks(src)
            if not paths:
                print(f"  跳过 {b}读{src}: readings/{src}/ 为空")
                continue
            body = build_body(cfg, bg, paths)
            out = PROMPTS_DIR / f"{b}读{src}.txt"
            out.write_text(body, encoding="utf-8")
            print(f"  {out.name}: {len(body)} chars, {len(paths)} 材料")


if __name__ == "__main__":
    main()
