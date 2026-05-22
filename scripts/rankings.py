"""排行榜可视化: 一张图 4 个子排名榜。
- 污染力 TOP 7 (作家作为源)
- 抗污染力 TOP 7 (作家作为基线, 强信号数倒序)
- 最猛 cell TOP 10 (按句法 5 维 |z| 平均)
- 最大借词漂移 cell TOP 10

输出 analysis/figures/rankings.png
"""
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config

ROOT = Path(__file__).resolve().parent.parent
REPORT = json.loads((ROOT / "analysis" / "analysis_report.json").read_text(encoding="utf-8"))
FIG_DIR = ROOT / "analysis" / "figures"
FIG_DIR.mkdir(exist_ok=True)

cfg = load_config()
STYLES = [s["short_name"] for s in cfg.styles]
METRICS = ["mean_sent_len", "mean_para_len", "single_sent_ratio",
           "dialogue_ratio", "marker_density"]


def compute_attack_defense():
    """每作家:作为源的强信号总数 (跨 6 非对角 baseline × 5 metric)
                作为基线被打穿的强信号总数 (跨 6 非对角 source × 5 metric)
    """
    attack = {s: 0 for s in STYLES}
    defense_breached = {s: 0 for s in STYLES}
    for baseline in STYLES:
        neu_key = f"{baseline}::中性"
        if neu_key not in REPORT:
            continue
        for src in STYLES:
            if src == baseline:
                continue
            pol_key = f"{baseline}::污染::{src}"
            if pol_key not in REPORT:
                continue
            for m in METRICS:
                p = REPORT[pol_key][m]["mean"]
                n = REPORT[neu_key][m]["mean"]
                sd = REPORT[neu_key][m]["sd"]
                z = abs(p - n) / sd if sd > 0 else 0
                if z >= 2:
                    attack[src] += 1
                    defense_breached[baseline] += 1
    return attack, defense_breached


def compute_cell_scores():
    """每 cell 句法 |z| 平均 + 借词漂移 (用该源指纹)"""
    cells = []
    for baseline in STYLES:
        neu_key = f"{baseline}::中性"
        if neu_key not in REPORT:
            continue
        for src in STYLES:
            pol_key = f"{baseline}::污染::{src}"
            if pol_key not in REPORT:
                continue
            zs = []
            for m in METRICS:
                p = REPORT[pol_key][m]["mean"]
                n = REPORT[neu_key][m]["mean"]
                sd = REPORT[neu_key][m]["sd"]
                if sd > 0:
                    zs.append(abs(p - n) / sd)
            avg_z = float(np.mean(zs)) if zs else 0
            db = (REPORT[pol_key][f"borrow_{src}"]["mean"]
                  - REPORT[neu_key][f"borrow_{src}"]["mean"])
            cells.append({
                "label": f"{baseline}←{src}",
                "z": avg_z,
                "borrow": db,
                "diag": baseline == src,
            })
    return cells


def bar_panel(ax, labels, values, title, xlabel, color, fmt="{:.1f}"):
    """单个排行榜面板。"""
    y_pos = np.arange(len(labels))
    colors = [color] * len(labels)
    bars = ax.barh(y_pos, values, color=colors, edgecolor="black", alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()  # 第一名在顶上
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(True, axis="x", alpha=0.3)
    # 数值
    for bar, v in zip(bars, values):
        x = bar.get_width()
        ax.text(x + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                fmt.format(v), va="center", fontsize=9)
    # top 3 用颜色加深突出 (排名信息从条形长度就能看出, 不再重复 #1/#2/#3 文字)
    for i in range(min(3, len(bars))):
        bars[i].set_alpha(1.0)
        bars[i].set_linewidth(2)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    attack, defense = compute_attack_defense()
    cells = compute_cell_scores()

    # 1. 污染力 (按 attack 降序)
    rank_attack = sorted(STYLES, key=lambda s: -attack[s])
    # 2. 抗污染力 (按 defense_breached 升序, 越少越抗)
    rank_defense = sorted(STYLES, key=lambda s: defense[s])
    # 3. 最猛 cell (按 z 降序, top 10)
    rank_z = sorted(cells, key=lambda c: -c["z"])[:10]
    # 4. 最大借词漂移 cell (top 10)
    rank_borrow = sorted(cells, key=lambda c: -c["borrow"])[:10]

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle("EROTICA 排行榜",
                 fontsize=16, fontweight="bold", y=0.995)

    # 子图 1: 污染力
    bar_panel(
        axes[0, 0],
        labels=rank_attack,
        values=[attack[s] for s in rank_attack],
        title="污染力 (作为源, 让别人产生的强信号数)",
        xlabel="强信号数 (max=30 = 6 基线 × 5 维度)",
        color="#C51B8A",
        fmt="{:.0f}",
    )

    # 子图 2: 抗污染力
    bar_panel(
        axes[0, 1],
        labels=rank_defense,
        values=[30 - defense[s] for s in rank_defense],  # 反向: 30-被打穿=抗住数
        title="抗污染力 (作为基线, 抗住的强信号数)",
        xlabel="抗住数 (max=30, 越大越抗)",
        color="#2166AC",
        fmt="{:.0f}",
    )

    # 子图 3: 最猛 cell
    bar_panel(
        axes[1, 0],
        labels=[c["label"] for c in rank_z],
        values=[c["z"] for c in rank_z],
        title="句法漂移 TOP 10 cells (|z| 5 维平均)",
        xlabel="|z| 平均",
        color="#D7301F",
        fmt="{:.2f}",
    )

    # 子图 4: 最大借词漂移
    bar_panel(
        axes[1, 1],
        labels=[c["label"] for c in rank_borrow],
        values=[c["borrow"] for c in rank_borrow],
        title="借词漂移 TOP 10 cells (polluted - neutral, %)",
        xlabel="借词率漂移 (%)",
        color="#7A0177",
        fmt="{:+.2f}",
    )

    plt.tight_layout()
    plt.savefig(FIG_DIR / "rankings.png", dpi=120, bbox_inches="tight")
    plt.close()
    print(f"  rankings.png -> {FIG_DIR.relative_to(ROOT)}/")

    # 打印文字版让用户也能看
    print("\n=== 污染力排行 ===")
    for i, s in enumerate(rank_attack, 1):
        print(f"  {i}. {s:<6} {attack[s]} 强信号")
    print("\n=== 抗污染力排行 ===")
    for i, s in enumerate(rank_defense, 1):
        print(f"  {i}. {s:<6} 抗住 {30 - defense[s]} / 30 (被打穿 {defense[s]})")
    print("\n=== 句法漂移最猛 TOP 5 ===")
    for i, c in enumerate(rank_z[:5], 1):
        print(f"  {i}. {c['label']:<10} z={c['z']:.2f}")
    print("\n=== 借词漂移最大 TOP 5 ===")
    for i, c in enumerate(rank_borrow[:5], 1):
        print(f"  {i}. {c['label']:<10} {c['borrow']:+.2f}%")


if __name__ == "__main__":
    main()
