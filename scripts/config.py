"""配置加载器。从 writers/*.md(一级目录)和 scripts/experiment.toml 读出统一配置。

writer .md 格式 (前几行 key-value, 然后 ## 背景 段后的全文是 background):
    # 极简白描

    - **short_name**: 极简
    - **full_name**: 极简白描
    - **id**: s1_minimal

    ## 背景

    你是一位虚构作家...

用法:
    from config import load_config
    cfg = load_config()
    cfg.styles  -> list of dict {id, short_name, full_name, background}
    cfg.output_title  -> "幻林折枝"
    cfg.reading_titles  -> [{"id": "t1", "title": "找东西"}, ...]
    cfg.params  -> dict
"""
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WRITERS_DIR = SCRIPTS_DIR.parent / "writers"  # 一级目录,用户第一层即可访问人设
EXPERIMENT_TOML = SCRIPTS_DIR / "experiment.toml"


@dataclass
class Config:
    styles: list  # [{id, short_name, full_name, background}]
    output_title: str
    reading_titles: list  # [{id, title}]
    params: dict


def _parse_writer_md(text: str) -> dict:
    """解析一个 writer md 文件的 key-value header 和 background 正文。"""
    short_name = re.search(r"\*\*short_name\*\*:\s*(\S+)", text).group(1)
    full_name = re.search(r"\*\*full_name\*\*:\s*(\S+)", text).group(1)
    sid = re.search(r"\*\*id\*\*:\s*(\S+)", text).group(1)
    # 背景: ## 背景 之后到文件末尾
    m = re.search(r"##\s*背景\s*\n+(.*)", text, re.DOTALL)
    background = m.group(1).strip() if m else ""
    return {
        "id": sid,
        "short_name": short_name,
        "full_name": full_name,
        "background": background,
    }


def load_config() -> Config:
    # writers - 按 id 排序加载 (s1 ... s7)
    styles = []
    for md in WRITERS_DIR.glob("*.md"):
        styles.append(_parse_writer_md(md.read_text(encoding="utf-8")))
    styles.sort(key=lambda s: s["id"])
    # experiment.toml
    with open(EXPERIMENT_TOML, "rb") as f:
        exp = tomllib.load(f)
    return Config(
        styles=styles,
        output_title=exp["output_title"],
        reading_titles=exp["reading_titles"],
        params=exp["experiment_params"],
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    print(f"作家数: {len(cfg.styles)}")
    for s in cfg.styles:
        print(f"  {s['id']} | {s['short_name']} | {s['full_name']} | "
              f"background {len(s['background'])} chars")
    print(f"\n产出题目: {cfg.output_title}")
    print(f"阅读题目: {[t['title'] for t in cfg.reading_titles]}")
    print(f"实验参数: {cfg.params}")
