"""组装中性投喂和污染组的 56 个完整 prompt 文件。

输入: readings/{短名}/{文件}.txt + writers/*.md + scripts/experiment.toml
输出: prompts/{baseline 短名}{条件}.txt
  条件: "中性"        → 21 篇阅读材料 (每源 3 篇)
        "读{source}"  → 该 source 全部 20 篇
"""
from pathlib import Path

from config import load_config

ROOT = Path(__file__).resolve().parent.parent
READINGS_DIR = ROOT / "readings"
PROMPTS_DIR = ROOT / "prompts"
PROMPTS_DIR.mkdir(exist_ok=True)


def neutral_picks(cfg) -> list:
    """每源 N 篇 (默认每源 t1/t2/t3 各 1 篇 = 3), 共 7 × 3 = 21 篇。"""
    title_text_by_id = {t["id"]: t["title"] for t in cfg.reading_titles}
    neutral_title_texts = [
        title_text_by_id[tid] for tid in cfg.params["neutral_pick_titles"]
    ]
    paths = []
    for s in cfg.styles:
        short = s["short_name"]
        for title_text in neutral_title_texts:
            # readings/{short}/{short}{title}01.txt (取第 1 篇)
            paths.append(READINGS_DIR / short / f"{short}{title_text}01.txt")
    return paths


def polluted_picks(source_short: str) -> list:
    """单源全部 20 篇。"""
    return sorted((READINGS_DIR / source_short).glob("*.txt"))


def build_body(cfg, background: str, reading_paths: list) -> str:
    blocks = []
    for i, p in enumerate(reading_paths, start=1):
        content = p.read_text(encoding="utf-8").rstrip()
        blocks.append(f"<阅读材料{i}>{content}</阅读材料{i}>")
    blocks_text = "\n\n".join(blocks)
    return (
        f"<写作背景>{background}\n\n"
        f"今天你打算根据题目\"{cfg.output_title}\"写一篇 800-1000 字的短篇小说。\n\n"
        "你最近在读下面这些材料,你可以从中汲取一些灵感,甚至在你原本的风格之外搞点不一样的,"
        "但你不会刻意模仿——你有自己的活儿要干。作为作者,你追求创新,更追求内心的自洽。</写作背景>\n\n"
        f"{blocks_text}\n\n"
        "请直接开始创作,不要写标题、不要写说明。"
    )


def main():
    cfg = load_config()
    neu_paths = neutral_picks(cfg)
    print(f"中性投喂取材: {len(neu_paths)} 篇")

    # 7 个中性
    for baseline in cfg.styles:
        body = build_body(cfg, baseline["background"], neu_paths)
        out = PROMPTS_DIR / f"{baseline['short_name']}中性.txt"
        out.write_text(body, encoding="utf-8")
        print(f"  {out.name}: {len(body)} chars")

    print()
    # 49 个污染
    for baseline in cfg.styles:
        for source in cfg.styles:
            body = build_body(
                cfg,
                baseline["background"],
                polluted_picks(source["short_name"]),
            )
            out = (PROMPTS_DIR
                   / f"{baseline['short_name']}读{source['short_name']}.txt")
            out.write_text(body, encoding="utf-8")
        print(f"  {baseline['short_name']} × 7 sources done")

    total = len(list(PROMPTS_DIR.glob("*.txt")))
    print(f"\n共 {total} 个提示词文件")


if __name__ == "__main__":
    main()
