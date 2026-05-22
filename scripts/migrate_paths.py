"""大迁移脚本: 把当前中文目录结构改成英文(只保留作家名是中文)+ 重命名 江南→清欢、裸→不读。

旧:
    阅读材料/江南/江南找东西01.txt
    产出/武侠/裸/武侠裸01.txt
    产出/武侠/江南/武侠读江南01.txt
    提示词/江南中性.txt
    提示词/武侠读江南.txt
    分析结果/分析报告.json + 分析摘要.md
    脚本/...

新:
    readings/清欢/清欢找东西01.txt
    outputs/武侠/不读/武侠不读01.txt
    outputs/武侠/清欢/武侠读清欢01.txt
    prompts/清欢中性.txt
    prompts/武侠读清欢.txt
    analysis/analysis_report.json + analysis_summary.md
    scripts/...

执行前后做完整复制, 旧目录保留, 验证无误后用户手动删除。
"""
import shutil
from pathlib import Path

ROOT = Path(r"E:\Claude\EROTICA")

# 旧 → 新顶层目录
DIR_MAP = {
    "阅读材料": "readings",
    "产出": "outputs",
    "提示词": "prompts",
    "分析结果": "analysis",
}
# 文件级别 token rename (作家短名和"裸")
TOKEN_MAP = {
    "江南": "清欢",
    "裸": "不读",
}
# 分析结果文件名英文化
ANALYSIS_FILE_MAP = {
    "分析报告.json": "analysis_report.json",
    "分析摘要.md": "analysis_summary.md",
}


def rename_tokens(s: str) -> str:
    """对一段路径片段做 token 替换 (江南→清欢, 裸→不读)。"""
    for old, new in TOKEN_MAP.items():
        s = s.replace(old, new)
    return s


def migrate_readings():
    """阅读材料/{short}/{file}.txt → readings/{short_new}/{file_new}.txt"""
    src_root = ROOT / "阅读材料"
    dst_root = ROOT / "readings"
    n = 0
    for txt in src_root.rglob("*.txt"):
        rel = txt.relative_to(src_root)
        new_parts = [rename_tokens(p) for p in rel.parts]
        dst = dst_root / Path(*new_parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(txt, dst)
        n += 1
    print(f"  迁移 阅读材料 → readings/ : {n} 篇")


def migrate_outputs():
    """产出/{baseline}/{cond}/{file}.txt → outputs/{baseline_new}/{cond_new}/{file_new}.txt"""
    src_root = ROOT / "产出"
    dst_root = ROOT / "outputs"
    n = 0
    for txt in src_root.rglob("*.txt"):
        rel = txt.relative_to(src_root)
        new_parts = [rename_tokens(p) for p in rel.parts]
        dst = dst_root / Path(*new_parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(txt, dst)
        n += 1
    print(f"  迁移 产出 → outputs/ : {n} 篇")


def migrate_prompts():
    """提示词/{file}.txt → prompts/{file_new}.txt"""
    src_root = ROOT / "提示词"
    dst_root = ROOT / "prompts"
    dst_root.mkdir(exist_ok=True)
    n = 0
    for txt in src_root.glob("*.txt"):
        new_name = rename_tokens(txt.name)
        shutil.copy2(txt, dst_root / new_name)
        n += 1
    print(f"  迁移 提示词 → prompts/ : {n} 个")


def migrate_analysis():
    """分析结果/{文件} → analysis/{英文名}"""
    src_root = ROOT / "分析结果"
    dst_root = ROOT / "analysis"
    dst_root.mkdir(exist_ok=True)
    n = 0
    for f in src_root.iterdir():
        if f.name in ANALYSIS_FILE_MAP:
            shutil.copy2(f, dst_root / ANALYSIS_FILE_MAP[f.name])
            n += 1
    print(f"  迁移 分析结果 → analysis/ : {n} 个文件")


def main():
    print("==> 开始迁移 (复制模式,旧目录保留)")
    migrate_readings()
    migrate_outputs()
    migrate_prompts()
    migrate_analysis()
    print("\n==> 迁移完成。验证无误后用户手动删除旧中文目录。")


if __name__ == "__main__":
    main()
