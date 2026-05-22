"""生成 4 张可视化:
1. borrow_heatmap.png      — 7×7 借词漂移热力图
2. zscore_heatmap.png      — 49 cells × 5 维 句法 z-score 热力图
3. role_scatter.png        — 7 作家: 作为源的传染力 vs 作为基线的抗污染力
4. borrow_vs_syntax.png    — 49 cells: 借词漂移 vs 平均句法 z

依赖 matplotlib + numpy + pandas (无需 seaborn)。
输出到 analysis/figures/。
"""
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

# 中文字体 (Windows: 微软雅黑)
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
METRIC_LABELS = ["句长", "段长", "单句成段率", "对话密度", "议论密度"]


def get(key, metric):
    """从 report 取某 cell 的某指标。"""
    if key not in REPORT:
        return None
    return REPORT[key].get(metric)


# ============ 图 1: 7×7 借词漂移热力图 ============
def plot_borrow_heatmap():
    mat = np.full((len(STYLES), len(STYLES)), np.nan)
    for i, baseline in enumerate(STYLES):
        neu_key = f"{baseline}::中性"
        if neu_key not in REPORT:
            continue
        for j, src in enumerate(STYLES):
            pol_key = f"{baseline}::污染::{src}"
            if pol_key not in REPORT:
                continue
            pol_borrow = REPORT[pol_key][f"borrow_{src}"]["mean"]
            neu_borrow = REPORT[neu_key][f"borrow_{src}"]["mean"]
            mat[i, j] = pol_borrow - neu_borrow

    fig, ax = plt.subplots(figsize=(8, 7))
    # 双色 diverging colormap, 0 = 白
    vmax = np.nanmax(np.abs(mat))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    cmap = LinearSegmentedColormap.from_list(
        "borrow", ["#2166AC", "#F7F7F7", "#B2182B"]
    )
    im = ax.imshow(mat, cmap=cmap, norm=norm, aspect="equal")
    ax.set_xticks(range(len(STYLES)))
    ax.set_yticks(range(len(STYLES)))
    ax.set_xticklabels(STYLES)
    ax.set_yticklabels(STYLES)
    ax.set_xlabel("污染源 (source)")
    ax.set_ylabel("基线作家 (baseline)")
    ax.set_title("借词漂移 (polluted - neutral, %)\n"
                 "正值=该源指纹词进入产出, 负值=反向", fontsize=11)
    # 单元格数值
    for i in range(len(STYLES)):
        for j in range(len(STYLES)):
            if not np.isnan(mat[i, j]):
                ax.text(j, i, f"{mat[i,j]:+.2f}", ha="center", va="center",
                        color="black", fontsize=9)
    plt.colorbar(im, ax=ax, label="%")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "borrow_heatmap.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  borrow_heatmap.png")


# ============ 图 2: 49 cells × 5 metric z-score 热力图 ============
def plot_zscore_heatmap():
    rows = []
    row_labels = []
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
                z = abs(p - n) / sd if sd > 0 else 0
                zs.append(z)
            rows.append(zs)
            row_labels.append(f"{baseline}←{src}")

    mat = np.array(rows)
    fig, ax = plt.subplots(figsize=(8, 14))
    cmap = LinearSegmentedColormap.from_list(
        "z", ["#FFFFFF", "#FDE0DD", "#FA9FB5", "#C51B8A", "#7A0177"]
    )
    im = ax.imshow(mat, cmap=cmap, vmin=0, vmax=6, aspect="auto")
    ax.set_xticks(range(len(METRICS)))
    ax.set_xticklabels(METRIC_LABELS)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8)
    ax.set_title("49 cells × 5 维度 句法漂移 |z|\n"
                 "z≥2 强信号, 1≤z<2 中等, z<1 噪声内", fontsize=11)
    # 数值
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            color = "white" if v >= 3 else "black"
            mark = "!" if v >= 2 else ("." if v >= 1 else "")
            ax.text(j, i, f"{v:.1f}{mark}", ha="center", va="center",
                    color=color, fontsize=7)
    plt.colorbar(im, ax=ax, label="|z|")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "zscore_heatmap.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  zscore_heatmap.png")


# ============ 图 3: 作家角色散点图 ============
def plot_role_scatter():
    """
    x 轴: 作为源, 让别的基线产生的强信号总数 (跨 6 个非对角 cell × 5 metric)
    y 轴: 作为基线, 被别的源打出的强信号总数 (跨 6 个非对角 cell × 5 metric)
    每个作家一个点。
    """
    attack = {s: 0 for s in STYLES}  # 作为源,造成的强信号数
    defense_breached = {s: 0 for s in STYLES}  # 作为基线,被打穿的强信号数

    for baseline in STYLES:
        neu_key = f"{baseline}::中性"
        if neu_key not in REPORT:
            continue
        for src in STYLES:
            if src == baseline:
                continue  # 排除对角线
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

    fig, ax = plt.subplots(figsize=(8, 7))
    xs = [attack[s] for s in STYLES]
    ys = [defense_breached[s] for s in STYLES]
    ax.scatter(xs, ys, s=200, c="#1f77b4", alpha=0.7, edgecolors="black")
    for s, x, y in zip(STYLES, xs, ys):
        ax.annotate(s, (x, y), xytext=(8, 8), textcoords="offset points",
                    fontsize=11, fontweight="bold")
    ax.set_xlabel("作为污染源 → 让别人产生的强信号数 (传染力)")
    ax.set_ylabel("作为基线 → 被别人打出的强信号数 (易感度)")
    ax.set_title("7 作家的角色定位\n"
                 "右上 = 既能污染又被污染; 左上 = 易感弱传染; "
                 "右下 = 强传染抗污染; 左下 = 中立沉默", fontsize=10)
    ax.grid(True, alpha=0.3)
    # 中线
    ax.axhline(np.mean(ys), color="gray", linestyle="--", alpha=0.4)
    ax.axvline(np.mean(xs), color="gray", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "role_scatter.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  role_scatter.png")


# ============ 图 4: 借词漂移 vs 句法漂移 ============
def plot_borrow_vs_syntax():
    """
    每 cell 一个点: x = 该 cell 借词漂移 (该源指纹), y = 该 cell 句法 z 平均。
    分类着色: 对角 vs 非对角。
    """
    points = []
    for baseline in STYLES:
        neu_key = f"{baseline}::中性"
        if neu_key not in REPORT:
            continue
        for src in STYLES:
            pol_key = f"{baseline}::污染::{src}"
            if pol_key not in REPORT:
                continue
            # 借词漂移 (用该 source 的指纹)
            pol_borrow = REPORT[pol_key][f"borrow_{src}"]["mean"]
            neu_borrow = REPORT[neu_key][f"borrow_{src}"]["mean"]
            db = pol_borrow - neu_borrow
            # 句法 z 平均
            zs = []
            for m in METRICS:
                p = REPORT[pol_key][m]["mean"]
                n = REPORT[neu_key][m]["mean"]
                sd = REPORT[neu_key][m]["sd"]
                if sd > 0:
                    zs.append(abs(p - n) / sd)
            avg_z = np.mean(zs) if zs else 0
            points.append({
                "baseline": baseline, "src": src,
                "borrow": db, "z": avg_z,
                "diag": baseline == src,
                "label": f"{baseline}←{src}",
            })

    df = pd.DataFrame(points)
    fig, ax = plt.subplots(figsize=(10, 8))
    diag = df[df["diag"]]
    off = df[~df["diag"]]
    ax.scatter(off["borrow"], off["z"], s=80, c="#1f77b4", alpha=0.6,
               label="非对角 (跨风格污染)", edgecolors="black")
    ax.scatter(diag["borrow"], diag["z"], s=140, c="#d62728", alpha=0.8,
               label="对角 (自我强化)", edgecolors="black", marker="s")
    # 高 z 的点加 label
    high = df[df["z"] >= 2]
    for _, r in high.iterrows():
        ax.annotate(r["label"], (r["borrow"], r["z"]),
                    xytext=(5, 5), textcoords="offset points",
                    fontsize=8, alpha=0.85)
    ax.axhline(2, color="gray", linestyle="--", alpha=0.4,
               label="z=2 强信号阈值")
    ax.axvline(0, color="gray", linestyle="--", alpha=0.4)
    ax.set_xlabel("借词漂移 (polluted - neutral, %)")
    ax.set_ylabel("句法漂移 (5 维度 |z| 平均)")
    ax.set_title("49 cells: 借词漂移 vs 句法漂移\n"
                 "右上 = 又染词又染骨架; 右下 = 只染词; 左上 = 只染骨架", fontsize=11)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "borrow_vs_syntax.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  borrow_vs_syntax.png")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"==> 输出到 {FIG_DIR.relative_to(ROOT)}/")
    plot_borrow_heatmap()
    plot_zscore_heatmap()
    plot_role_scatter()
    plot_borrow_vs_syntax()
    print("\n完成。")


if __name__ == "__main__":
    main()
