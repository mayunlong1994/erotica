"""为单个 cell 生成 v2 提示词。

v2 vs v1 关键差异:
- v1: 背景 + 题目 + "你不会刻意模仿..." + 阅读材料
- v2: 背景 + "你最近在读下面这些材料" + 阅读材料 + 题目
  (去掉抵抗指令, 把题目放到最后, 让模型先读再写)

用法:
    py scripts/v2_assemble.py 极简 反讽
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config

ROOT = Path(__file__).resolve().parent.parent
READINGS_DIR = ROOT / "readings"
V2_DIR = ROOT / "v2_test"
PROMPTS_DIR = V2_DIR / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    if len(sys.argv) != 3:
        print("用法: py scripts/v2_assemble.py <baseline_short> <source_short>")
        print("示例: py scripts/v2_assemble.py 极简 反讽")
        sys.exit(1)
    baseline_short, source_short = sys.argv[1], sys.argv[2]
    cfg = load_config()
    baseline = next((s for s in cfg.styles if s["short_name"] == baseline_short), None)
    if not baseline:
        print(f"未知基线作家: {baseline_short} (须是 config 里有 background 的 7 作家之一)")
        sys.exit(1)
    # source 不要求在 config 里 —— 可以是真人原文源(如 白洁), 只需 readings/{source}/ 有材料
    reading_paths = sorted((READINGS_DIR / source_short).glob("*.txt"))
    if not reading_paths:
        print(f"源目录为空或不存在: readings/{source_short}/")
        sys.exit(1)
    blocks = []
    for i, p in enumerate(reading_paths, start=1):
        content = p.read_text(encoding="utf-8").rstrip()
        blocks.append(f"<阅读材料{i}>{content}</阅读材料{i}>")
    blocks_text = "\n\n".join(blocks)

    # v2 模板: 背景 + 简洁的"读了这些" + 材料 + 题目放最后
    body = (
        f"<写作背景>{baseline['background']}\n\n"
        "你最近在读下面这些材料。</写作背景>\n\n"
        f"{blocks_text}\n\n"
        f"今天你打算根据题目\"{cfg.output_title}\"写一篇 800-1000 字的短篇小说。\n\n"
        "请直接开始创作,不要写标题、不要写说明。"
    )

    out_path = PROMPTS_DIR / f"{baseline_short}读{source_short}.txt"
    out_path.write_text(body, encoding="utf-8")
    print(f"  写入: {out_path.relative_to(ROOT)} ({len(body)} chars)")


if __name__ == "__main__":
    main()
