"""B+C+D 统一分析。

- B: n-gram overlap  (产出里多少 2-3gram 命中源独有指纹)
- C: TF-IDF 源特异词 (自动从 7 源 reading 抽取每源指纹词)
- D: 句法/结构指标

输入:
- readings/{短名}/{文件}.txt
- outputs/{短名 baseline}/{不读|中性|短名 source}/{文件}.txt

输出:
- analysis/analysis_report.json
- analysis/analysis_summary.md
"""
import json
import re
import statistics as stats
from collections import Counter
from math import log
from pathlib import Path

from config import load_config

ROOT = Path(__file__).resolve().parent.parent
READINGS_DIR = ROOT / "readings"
OUTPUTS_DIR = ROOT / "outputs"
ANALYSIS_DIR = ROOT / "analysis"
ANALYSIS_DIR.mkdir(exist_ok=True)

cfg = load_config()
STYLES = [s["short_name"] for s in cfg.styles]
SENT_END = "。！？!?…"


def is_chinese(c):
    return "一" <= c <= "鿿"


# ============ D: 句法/结构 ============
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
        "n_para": n_para,
        "mean_para_len": mean_para_len,
        "single_sent_ratio": single_sent_ratio,
        "n_sent": len(sentences),
        "mean_sent_len": mean_sent_len,
        "dialogue_ratio": dialogue_ratio,
        "marker_density": marker_density,
        "total_chinese": total_chinese,
    }


# ============ B/C 共享 ============
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


# ============ C: TF-IDF ============
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
        distinctive[s] = [g for g, _ in top]
    return distinctive


# ============ B: 借词率 ============
def borrowing_rate(text_grams, distinctive_set):
    total = sum(text_grams.values())
    if not total:
        return 0.0
    hits = sum(f for g, f in text_grams.items() if g in distinctive_set)
    return hits / total * 100


def analyze_cell(files, distinctive_by_source):
    results = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        m = syntactic_metrics(text)
        text_grams = extract_ngrams(text)
        for s, distinctive_list in distinctive_by_source.items():
            m[f"borrow_{s}"] = borrowing_rate(text_grams, set(distinctive_list))
        results.append(m)
    if not results:
        return {}
    summary = {}
    for k in results[0].keys():
        vals = [r[k] for r in results]
        summary[k] = {
            "mean": stats.mean(vals),
            "sd": stats.stdev(vals) if len(vals) > 1 else 0,
            "n": len(vals),
        }
    return summary


def main():
    print("==> 阶段 1: 提取 7 源 reading 的 n-gram")
    source_grams = {s: collect_source_grams(s) for s in STYLES}
    for s in STYLES:
        print(f"  {s}: {len(source_grams[s])} unique, "
              f"total {sum(source_grams[s].values())}")

    print("\n==> 阶段 2: TF-IDF 抽指纹词 (top 200, min_freq 3)")
    distinctive = compute_distinctive(source_grams, top_n=200, min_freq=3)
    for s in STYLES:
        print(f"  {s} top 15: {distinctive[s][:15]}")

    print("\n==> 阶段 3: 分析每个 cell")
    results = {}
    for baseline in STYLES:
        bdir = OUTPUTS_DIR / baseline
        if not bdir.exists():
            continue
        for sub in bdir.iterdir():
            if not sub.is_dir():
                continue
            cond = sub.name
            files = sorted(sub.glob("*.txt"))
            if not files:
                continue
            if cond == "不读":
                key = f"{baseline}::不读"
            elif cond == "中性":
                key = f"{baseline}::中性"
            elif cond in STYLES:
                key = f"{baseline}::污染::{cond}"
            else:
                continue
            results[key] = analyze_cell(files, distinctive)

    # JSON
    out_path = ANALYSIS_DIR / "analysis_report.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n==> JSON 报告: {out_path.relative_to(ROOT)}")

    # Markdown 摘要
    md_path = ANALYSIS_DIR / "analysis_summary.md"
    lines = ["# EROTICA 分析摘要\n",
             "## 1. 每源自动抽取的指纹词 (TF-IDF top 30)\n"]
    for s in STYLES:
        lines.append(f"**{s}**:")
        lines.append("`" + "、".join(distinctive[s][:30]) + "`\n")
    lines.append("## 2. 借词漂移矩阵 (polluted − neutral, %)\n")
    lines.append("行=基线作家, 列=污染源。带 * 表示 n≥5 可靠数据。\n")
    lines.append("| baseline \\ source | " + " | ".join(STYLES) + " |")
    lines.append("|---" * (len(STYLES) + 1) + "|")
    for baseline in STYLES:
        row = [f"**{baseline}**"]
        neu_key = f"{baseline}::中性"
        for src in STYLES:
            pol_key = f"{baseline}::污染::{src}"
            if pol_key in results and neu_key in results:
                delta = (results[pol_key][f"borrow_{src}"]["mean"]
                         - results[neu_key][f"borrow_{src}"]["mean"])
                n_pol = results[pol_key][f"borrow_{src}"]["n"]
                marker = " *" if n_pol >= 5 else ""
                row.append(f"{delta:+.2f}{marker}")
            else:
                row.append("n/a")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("\n## 3. 高 n cell 多维漂移 (|delta|/neutral_sd)\n")
    lines.append("z≥2 是强信号 (!), 1≤z<2 中等 (.), z<1 在噪声内。\n")
    metrics_to_show = ["mean_sent_len", "mean_para_len",
                       "single_sent_ratio", "dialogue_ratio", "marker_density"]
    lines.append("| cell | " + " | ".join(metrics_to_show) + " |")
    lines.append("|---" * (len(metrics_to_show) + 1) + "|")
    for key, data in sorted(results.items()):
        if "::污染::" not in key:
            continue
        if list(data.values())[0]["n"] < 5:
            continue
        baseline = key.split("::")[0]
        neu = results.get(f"{baseline}::中性")
        if not neu:
            continue
        src = key.split("::")[-1]
        label = f"{baseline}←{src} (n={list(data.values())[0]['n']})"
        row = [label]
        for m in metrics_to_show:
            delta = data[m]["mean"] - neu[m]["mean"]
            z = abs(delta) / neu[m]["sd"] if neu[m]["sd"] > 0 else 0
            flag = " !" if z >= 2 else (" ." if z >= 1 else "")
            row.append(f"{delta:+.2f} (z={z:.2f}{flag})")
        lines.append("| " + " | ".join(row) + " |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"==> Markdown 摘要: {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
