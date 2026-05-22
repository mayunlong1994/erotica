"""对比 v1 vs v2 提示词在同一 cell 上的漂移。

v1: outputs/{baseline}/{source}/  (发布数据)
v2: v2_test/outputs/             (测试数据)
对照: outputs/{baseline}/中性/    (同基线 neutral, n=20)

输出到 v2_test/compare.md。
"""
import re
import statistics as stats
import sys
from collections import Counter
from math import log
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config

ROOT = Path(__file__).resolve().parent.parent
READINGS_DIR = ROOT / "readings"
OUTPUTS_DIR = ROOT / "outputs"
V2_DIR = ROOT / "v2_test" / "outputs"

# 所有已跑 v2 的 cell: (baseline, source)
CELLS = [
    ("极简", "反讽"),
    ("极简", "情欲"),
    ("极简", "纯爱"),
    ("极简", "武侠"),
    ("极简", "网文"),
    ("反讽", "情欲"),
    ("反讽", "纯爱"),
    ("反讽", "网文"),
    ("反讽", "武侠"),
    ("反讽", "极简"),
    ("武侠", "反讽"),
    ("武侠", "情欲"),
    ("武侠", "纯爱"),
    ("武侠", "网文"),
    ("清欢", "反讽"),
    ("清欢", "情欲"),
    ("清欢", "纯爱"),
    ("清欢", "网文"),
]

SENT_END = "。！？!?…"


def is_chinese(c):
    return "一" <= c <= "鿿"


def syntactic_metrics(text):
    text = text.strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    n_para = len(paragraphs)
    para_lens = [sum(1 for c in p if is_chinese(c)) for p in paragraphs]
    mean_para_len = stats.mean(para_lens) if para_lens else 0
    single_sent = sum(1 for p in paragraphs
                      if sum(1 for c in p if c in SENT_END) <= 1)
    single_sent_ratio = single_sent / n_para if n_para else 0
    sentences = [s.strip()
                 for s in re.split(rf"[{re.escape(SENT_END)}]", text)
                 if s.strip()]
    sent_lens = [sum(1 for c in s if is_chinese(c)) for s in sentences]
    mean_sent_len = stats.mean(sent_lens) if sent_lens else 0
    dialogue_paras = sum(1 for p in paragraphs
                         if "“" in p or "”" in p or '"' in p)
    dialogue_ratio = dialogue_paras / n_para if n_para else 0
    total_chinese = sum(1 for c in text if is_chinese(c))
    discourse = ["其实", "总之", "也就是", "不过", "然而", "这就", "这便",
                 "这种", "不必", "因此", "不妨", "所谓", "无非", "毕竟",
                 "大概", "所以"]
    n_markers = sum(text.count(m) for m in discourse)
    marker_density = n_markers / total_chinese * 1000 if total_chinese else 0
    return {
        "句长": mean_sent_len,
        "段长": mean_para_len,
        "单句成段率": single_sent_ratio,
        "对话密度": dialogue_ratio,
        "议论密度": marker_density,
    }


def extract_ngrams(text, ns=(2, 3)):
    chinese_only = "".join(c for c in text if is_chinese(c))
    grams = Counter()
    for n in ns:
        for i in range(len(chinese_only) - n + 1):
            grams[chinese_only[i:i + n]] += 1
    return grams


def collect_source_grams(short_name):
    total = Counter()
    for txt in (READINGS_DIR / short_name).glob("*.txt"):
        total.update(extract_ngrams(txt.read_text(encoding="utf-8")))
    return total


def compute_distinctive(source_grams_by_style, top_n=200, min_freq=3):
    all_grams = set()
    for grams in source_grams_by_style.values():
        all_grams.update(grams)
    N = len(source_grams_by_style)
    df = Counter()
    for gram in all_grams:
        for grams in source_grams_by_style.values():
            if gram in grams:
                df[gram] += 1
    distinctive = {}
    for s, grams in source_grams_by_style.items():
        scores = {}
        for gram, freq in grams.items():
            if freq < min_freq:
                continue
            idf = log(N / df[gram]) if df[gram] else 0
            if idf > 0:
                scores[gram] = freq * idf
        top = sorted(scores.items(), key=lambda x: -x[1])[:top_n]
        distinctive[s] = set(g for g, _ in top)
    return distinctive


def borrowing_rate(text_grams, distinctive_set):
    total = sum(text_grams.values())
    if not total:
        return 0.0
    hits = sum(f for g, f in text_grams.items() if g in distinctive_set)
    return hits / total * 100


def analyze_batch(files, source_fingerprint):
    """对一组文件返回各指标的均值列表(同 cell 内)。"""
    metrics_lists = {}
    borrow_list = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        m = syntactic_metrics(text)
        for k, v in m.items():
            metrics_lists.setdefault(k, []).append(v)
        borrow_list.append(borrowing_rate(extract_ngrams(text), source_fingerprint))
    metrics_lists["借词率(%)"] = borrow_list
    return metrics_lists


def summarize(metrics_lists):
    return {
        k: (stats.mean(v), stats.stdev(v) if len(v) > 1 else 0)
        for k, v in metrics_lists.items()
    }


def analyze_one_cell(baseline, source, distinctive):
    """对单个 cell 返回 rows + 强信号统计。"""
    source_fp = distinctive[source]
    v1_files = sorted((OUTPUTS_DIR / baseline / source).glob("*.txt"))
    neu_files = sorted((OUTPUTS_DIR / baseline / "中性").glob("*.txt"))
    v2_files = sorted((V2_DIR / f"{baseline}读{source}").glob("*.txt"))

    v1_sum = summarize(analyze_batch(v1_files, source_fp))
    neu_sum = summarize(analyze_batch(neu_files, source_fp))
    v2_sum = summarize(analyze_batch(v2_files, source_fp))

    rows = []
    for metric in v1_sum.keys():
        nm, ns = neu_sum[metric]
        v1m, _ = v1_sum[metric]
        v2m, _ = v2_sum[metric]
        v1_delta, v2_delta = v1m - nm, v2m - nm
        v1_z = abs(v1_delta) / ns if ns > 0 else 0
        v2_z = abs(v2_delta) / ns if ns > 0 else 0
        rows.append({
            "metric": metric, "nm": nm, "ns": ns, "v1m": v1m, "v2m": v2m,
            "v1_delta": v1_delta, "v2_delta": v2_delta,
            "v1_z": v1_z, "v2_z": v2_z,
            "n_v1": len(v1_files), "n_v2": len(v2_files),
        })
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    STYLES = [s["short_name"] for s in cfg.styles]
    source_grams = {s: collect_source_grams(s) for s in STYLES}
    distinctive = compute_distinctive(source_grams)

    md = ["# v2 提示词对比测试 (去除抵抗指令)\n"]
    md.append("**v1**: 背景 + 题目 + 「你不会刻意模仿—你有自己的活儿要干」 + 阅读材料\n")
    md.append("**v2**: 背景 + 「你最近在读下面这些材料」 + 阅读材料 + 题目 (去掉抵抗指令)\n")
    md.append("z≥2 强信号, 1≤z<2 中等, z<1 噪声内。每 cell n=20。\n")
    md.append("---\n")

    summary_table = []  # (cell, v1_strong, v2_strong)

    for baseline, source in CELLS:
        rows = analyze_one_cell(baseline, source, distinctive)
        v1_strong = sum(1 for r in rows if r["v1_z"] >= 2)
        v2_strong = sum(1 for r in rows if r["v2_z"] >= 2)
        summary_table.append((f"{baseline}←{source}", v1_strong, v2_strong))

        print(f"\n=== {baseline} ← {source} | v1 强信号 {v1_strong}/6, v2 强信号 {v2_strong}/6 ===")
        for r in rows:
            print(f"  {r['metric']:<10} 中性={r['nm']:>7.2f}±{r['ns']:<5.2f} "
                  f"v1漂移={r['v1_delta']:>+7.2f}(z={r['v1_z']:>5.2f}) "
                  f"v2漂移={r['v2_delta']:>+7.2f}(z={r['v2_z']:>5.2f})")

        md.append(f"## {baseline} ← {source}\n")
        md.append(f"v1 强信号 **{v1_strong}/6**, v2 强信号 **{v2_strong}/6**\n")
        md.append("| 指标 | 中性(均值±sd) | v1 漂移 (z) | v2 漂移 (z) |")
        md.append("|---|---|---|---|")
        for r in rows:
            f1 = "!" if r["v1_z"] >= 2 else ("." if r["v1_z"] >= 1 else "")
            f2 = "!" if r["v2_z"] >= 2 else ("." if r["v2_z"] >= 1 else "")
            md.append(f"| {r['metric']} | {r['nm']:.2f}±{r['ns']:.2f} | "
                      f"{r['v1_delta']:+.2f} (z={r['v1_z']:.2f}{f1}) | "
                      f"{r['v2_delta']:+.2f} (z={r['v2_z']:.2f}{f2}) |")
        md.append("")

    # 汇总
    md.append("---\n## 汇总\n")
    md.append("| cell | v1 强信号 | v2 强信号 | 变化 |")
    md.append("|---|---|---|---|")
    print("\n=== 汇总 ===")
    for cell, v1s, v2s in summary_table:
        delta = v2s - v1s
        arrow = f"+{delta}" if delta > 0 else ("0" if delta == 0 else str(delta))
        md.append(f"| {cell} | {v1s}/6 | {v2s}/6 | {arrow} |")
        print(f"  {cell}: v1 {v1s}/6 → v2 {v2s}/6  ({arrow})")

    md.append("")
    md.append("**结论**: 若 v2 普遍 > v1 → 去抵抗指令后污染普遍增强, "
              "FINDINGS.md 的「人格饱和度」假说大部分实为「抵抗指令效应」, 需重写。\n")

    out = ROOT / "v2_test" / "compare.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"\n==> 报告写入: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
