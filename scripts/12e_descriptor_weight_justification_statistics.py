#!/usr/bin/env python
"""Compute descriptor diagnostics for alpha-weight justification.

The script only reads Step08/Step11Y artifacts and does not rerun any planner.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEP08 = ROOT / "results" / "fossum_roi_x490_step08_final_descriptors_20260605_141912"
DEFAULT_STEP11Y = ROOT / "results" / "fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260605_143425"

DESCRIPTORS = {
    "boundary_score": {
        "step08": "step08_descriptor_boundary_map.npy",
        "step11y": "prototype_based_boundary_score_norm.npy",
        "used_in": "Step12A",
    },
    "boundary_distance_score_r1_cells": {
        "step08": "step08_descriptor_boundary_distance_score_r1_cells.npy",
        "step11y": "prototype_based_boundary_distance_score_r1_cells_norm.npy",
        "used_in": "Step12A",
    },
    "boundary_distance_score_r3_cells": {
        "step08": "step08_descriptor_boundary_distance_score_r3_cells.npy",
        "step11y": "prototype_based_boundary_distance_score_r3_cells_norm.npy",
        "used_in": "Step12A",
    },
    "boundary_distance_score_r5_cells": {
        "step08": "step08_descriptor_boundary_distance_score_r5_cells.npy",
        "step11y": "prototype_based_boundary_distance_score_r5_cells_norm.npy",
        "used_in": "Step12A",
    },
    "interest_map": {
        "step08": "step08_descriptor_interest_map.npy",
        "step11y": "prototype_based_interest_map_norm.npy",
        "used_in": "Step12A",
    },
    "representative_zone": {
        "step08": "step08_descriptor_representative_zone_map.npy",
        "step11y": "prototype_based_representative_zone_norm.npy",
        "used_in": "optional_single_AUV",
    },
    "cold_region": {
        "step08": "step08_descriptor_cold_region_map.npy",
        "step11y": "prototype_based_cold_region_norm.npy",
        "used_in": "multi_AUV",
    },
    "warm_region": {
        "step08": "step08_descriptor_warm_region_map.npy",
        "step11y": "prototype_based_warm_region_norm.npy",
        "used_in": "multi_AUV",
    },
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def finite_values(arr: np.ndarray) -> np.ndarray:
    vals = np.asarray(arr, dtype=float).ravel()
    return vals[np.isfinite(vals)]


def stats(vals: np.ndarray) -> dict[str, float]:
    if vals.size == 0:
        return {
            "median_descriptor_value": float("nan"),
            "mean_descriptor_value": float("nan"),
            "p25": float("nan"),
            "p75": float("nan"),
            "IQR": float("nan"),
            "p5": float("nan"),
            "p95": float("nan"),
            "robust_amplitude": float("nan"),
            "finite_cells": 0,
        }
    p5, p25, p75, p95 = np.nanpercentile(vals, [5, 25, 75, 95])
    return {
        "median_descriptor_value": float(np.nanmedian(vals)),
        "mean_descriptor_value": float(np.nanmean(vals)),
        "p25": float(p25),
        "p75": float(p75),
        "IQR": float(p75 - p25),
        "p5": float(p5),
        "p95": float(p95),
        "robust_amplitude": float(p95 - p5),
        "finite_cells": int(vals.size),
    }


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, dtype=float).ravel()
    y = np.asarray(b, dtype=float).ravel()
    valid = np.isfinite(x) & np.isfinite(y)
    if int(valid.sum()) < 3:
        return float("nan")
    xv = x[valid]
    yv = y[valid]
    if float(np.nanstd(xv)) <= 1e-12 or float(np.nanstd(yv)) <= 1e-12:
        return float("nan")
    return float(np.corrcoef(xv, yv)[0, 1])


def suggested_alpha(utility: float) -> tuple[str, float]:
    if not math.isfinite(utility):
        return "not_available", float("nan")
    if utility < 0.5:
        return "low utility", 0.25
    if utility < 1.0:
        return "medium utility", 0.50
    return "high utility", 0.75


def score_to_alpha(score: float, prefix: str = "utility") -> tuple[str, float]:
    if not math.isfinite(score):
        return "not_available", float("nan")
    if score < 0.33:
        return f"low {prefix}", 0.25
    if score < 0.66:
        return f"medium {prefix}", 0.50
    if score < 0.85:
        return f"high {prefix}", 0.75
    return f"very high {prefix}", 0.75


def normalized_entropy(proportions: list[float]) -> float:
    vals = np.asarray([p for p in proportions if math.isfinite(float(p)) and float(p) > 0], dtype=float)
    if vals.size == 0:
        return float("nan")
    vals = vals / vals.sum()
    return float(-np.sum(vals * np.log(vals)) / math.log(3.0))


def minmax_metric(values: pd.Series) -> pd.Series:
    vals = pd.to_numeric(values, errors="coerce").astype(float)
    mn = float(np.nanmin(vals))
    mx = float(np.nanmax(vals))
    if not math.isfinite(mn) or not math.isfinite(mx) or mx <= mn:
        return pd.Series(np.zeros(len(vals)), index=values.index, dtype=float)
    return (vals - mn) / (mx - mn)


def class_heterogeneity_table(class_df: pd.DataFrame) -> pd.DataFrame:
    out = class_df.copy()
    out["class_id"] = out["class_id"].astype(int)
    regime = out.get("cv_regime_label", pd.Series([""] * len(out))).fillna("").astype(str)
    out["prototype_robust_amplitude"] = pd.to_numeric(out["prototype_p95"], errors="coerce") - pd.to_numeric(out["prototype_p05"], errors="coerce")
    out["prototype_gradient_p90"] = pd.to_numeric(out["gradient_p90"], errors="coerce")
    out["prototype_local_variance_mean"] = pd.to_numeric(out["local_variance_mean"], errors="coerce")
    out["prototype_boundary_density"] = pd.to_numeric(out["boundary_fraction"], errors="coerce")
    out["prototype_boundary_density_effective"] = np.where(regime.eq("multi_regime"), out["prototype_boundary_density"], 0.0)
    out["prototype_regime_entropy_raw"] = out.apply(
        lambda r: normalized_entropy(
            [
                float(r.get("cold_fraction", float("nan"))),
                float(r.get("neutral_fraction", float("nan"))),
                float(r.get("warm_fraction", float("nan"))),
            ]
        ),
        axis=1,
    )
    out["prototype_regime_entropy"] = np.select(
        [regime.eq("multi_regime"), regime.eq("single_gradient")],
        [out["prototype_regime_entropy_raw"], 0.5 * out["prototype_regime_entropy_raw"]],
        default=0.0,
    )

    components = [
        ("H_amp_norm", "prototype_robust_amplitude"),
        ("H_grad_norm", "prototype_gradient_p90"),
        ("H_var_norm", "prototype_local_variance_mean"),
        ("H_boundary_norm", "prototype_boundary_density_effective"),
        ("H_entropy_norm", "prototype_regime_entropy"),
    ]
    for norm_col, raw_col in components:
        out[norm_col] = minmax_metric(out[raw_col])
    norm_cols = [c for c, _ in components]
    out["class_heterogeneity_score"] = out[norm_cols].mean(axis=1)
    cats = []
    alphas = []
    for score in out["class_heterogeneity_score"].astype(float):
        cat, alpha = score_to_alpha(score, "heterogeneity")
        cats.append(cat)
        alphas.append(alpha)
    out["class_heterogeneity_category"] = cats
    out["class_alpha_cap"] = alphas
    return out


def read_cases(step11y: Path) -> pd.DataFrame:
    cases = pd.read_csv(step11y / "step11y_case_lineage.csv")
    cases["predicted_class"] = cases["predicted_class"].astype(int)
    cases["case_order"] = range(len(cases))
    return cases


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if not math.isfinite(val) else val
    return str(obj)


def pivot_for_plot(df: pd.DataFrame, value: str) -> pd.DataFrame:
    labels = [f"C{i:02d}" for i in range(1, 7)]
    p = df.pivot_table(index="descriptor", columns="class_label_short", values=value, aggfunc="first")
    return p.reindex(index=list(DESCRIPTORS.keys()), columns=labels)


def plot_heatmap(df: pd.DataFrame, value: str, title: str, out: Path, cmap: str = "viridis", vmin: float | None = None, vmax: float | None = None) -> None:
    p = pivot_for_plot(df, value)
    arr = p.to_numpy(dtype=float)
    masked = np.ma.masked_invalid(arr)
    fig_w = max(9.0, 0.75 * len(p.columns) + 4.5)
    fig_h = max(5.0, 0.42 * len(p.index) + 2.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(np.arange(len(p.columns)))
    ax.set_xticklabels(p.columns)
    ax.set_yticks(np.arange(len(p.index)))
    ax.set_yticklabels(p.index)
    ax.set_title(title)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            if math.isfinite(arr[i, j]):
                ax.text(j, i, f"{arr[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(arr[i, j]) > 0.55 else "black")
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def plot_descriptor_bar(df: pd.DataFrame, value: str, title: str, out: Path) -> None:
    agg = df.groupby("descriptor", as_index=False)[value].median(numeric_only=True)
    agg = agg.set_index("descriptor").reindex(list(DESCRIPTORS.keys())).reset_index()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.bar(agg["descriptor"], agg[value], color="#3b82f6")
    ax.set_title(title)
    ax.set_ylabel(value)
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def plot_class_heterogeneity(df: pd.DataFrame, out: Path) -> None:
    cols = [
        "class_label_short",
        "H_amp_norm",
        "H_grad_norm",
        "H_var_norm",
        "H_boundary_norm",
        "H_entropy_norm",
        "class_heterogeneity_score",
    ]
    h = df[cols].drop_duplicates("class_label_short").sort_values("class_label_short")
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    x = np.arange(len(h))
    ax.bar(x, h["class_heterogeneity_score"].astype(float), color="#2563eb", label="H_c")
    ax.set_xticks(x)
    ax.set_xticklabels(h["class_label_short"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("normalized score")
    ax.set_title("Class/prototype heterogeneity score")
    ax.legend()
    for xi, val in zip(x, h["class_heterogeneity_score"].astype(float)):
        ax.text(xi, val + 0.025, f"{val:.2f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def md_table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if df.empty:
        return "_No rows available._"
    d = df.copy()
    for col in d.columns:
        if pd.api.types.is_numeric_dtype(d[col]):
            d[col] = d[col].map(lambda x: "" if pd.isna(x) else format(float(x), floatfmt))
        else:
            d[col] = d[col].fillna("").astype(str)
    headers = list(d.columns)
    lines = [
        "| " + " | ".join(h.replace("|", "\\|") for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in d.astype(str).values.tolist():
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
    return "\n".join(lines)


def make_report(outdir: Path, df: pd.DataFrame, step08: Path, step11y: Path) -> None:
    finite_utility = df[np.isfinite(df["hierarchical_alpha_score"])]
    descriptor_summary = (
        finite_utility.groupby("descriptor", as_index=False)
        .agg(
            median_hierarchical_score=("hierarchical_alpha_score", "median"),
            median_class_heterogeneity=("class_heterogeneity_score", "median"),
            median_selectivity=("descriptor_selectivity_score", "median"),
            median_abs_correlation=("correlation_with_STD", lambda s: float(np.nanmedian(np.abs(s)))),
            median_hierarchical_alpha=("hierarchical_suggested_alpha", "median"),
            rows_with_STD=("correlation_with_STD", lambda s: int(np.isfinite(s).sum())),
        )
        .sort_values(["median_hierarchical_score", "median_class_heterogeneity"], ascending=False)
    )
    h_table = (
        df[
            [
                "class_label_short",
                "cv_regime_label",
                "prototype_robust_amplitude",
                "prototype_gradient_p90",
                "prototype_local_variance_mean",
                "prototype_boundary_density",
                "prototype_regime_entropy",
                "class_heterogeneity_score",
                "class_heterogeneity_category",
                "class_alpha_cap",
            ]
        ]
        .drop_duplicates("class_label_short")
        .sort_values("class_label_short")
    )
    top = descriptor_summary.head(10)
    unavailable = df[df["correlation_note"].ne("available")][["class_label_short", "descriptor", "correlation_note"]]

    lines = [
        "# Descriptor weight justification statistics",
        "",
        "This diagnostic supports alpha-weight interpretation only. It does not rerun the planner and does not claim data-assimilation uncertainty reduction.",
        "",
        "## Inputs",
        f"- Step08: `{rel(step08)}`",
        f"- Step11Y: `{rel(step11y)}`",
        "",
        "## Computation",
        "- Per-prototype statistics use finite valid cells from the Step08 descriptor maps.",
        "- Class heterogeneity `H_c` is computed first from robust prototype amplitude, gradient P90, mean local variance, boundary density, and cold/neutral/warm entropy, after min-max normalization across classes.",
        "- Descriptor selectivity `S_c,D` is computed from descriptor robust amplitude relative to its global robust amplitude and clipped to [0,1] for the hierarchical score.",
        "- Global descriptor median/IQR pool finite cells across all six Step08 prototype maps for the same descriptor.",
        "- STD correlation uses Step11Y `prototype_based_baseline_STD_norm` for cases whose predicted class matches the prototype.",
        "- Classes without a Step11Y case have correlation, novelty, utility score, and alpha category marked as unavailable.",
        "- Hierarchical alpha score uses `0.50*H_c + 0.30*S_c,D + 0.20*(1-|corr_STD|)` when STD correlation is available.",
        "- When STD correlation is unavailable, the fallback diagnostic is `0.65*H_c + 0.35*S_c,D`; those rows are marked in `hierarchical_alpha_basis`.",
        "- The final alpha is capped by class heterogeneity: low H -> max 0.25; medium H -> max 0.50; high/very-high H -> max 0.75. Alpha 1.00 is retained only as descriptor-only sensitivity.",
        "",
        "## Class Heterogeneity First",
        md_table(h_table, ".3f"),
        "",
        "## Descriptor-Level Ranking",
        md_table(top, ".3f"),
        "",
        "## Interpretation",
        "- High relative contrast means the descriptor varies strongly within that prototype relative to its global contrast.",
        "- For sparse boundary-distance maps, very small global IQR can inflate relative contrast; use robust amplitude and planner behavior as companion evidence.",
        "- Low absolute STD correlation means the descriptor adds a more independent reward-map signal, summarized by novelty = 1 - |correlation|.",
        "- The hierarchical alpha score is therefore a diagnostic for reward-map sensitivity, not a direct measure of assimilation benefit.",
        "- Boundary-distance descriptors should be interpreted as boundary/regime coverage proxies, while interest/representative maps are potential informativeness or typical-zone proxies.",
        "",
        "## Correlation Availability",
        f"- Rows with available STD correlation: {int(np.isfinite(df['correlation_with_STD']).sum())}/{len(df)}",
        f"- Rows without matching Step11Y STD case: {len(unavailable)}",
        "",
        "## Outputs",
        "- `descriptor_weight_justification_statistics.csv`",
        "- `figures/descriptor_weight_iqr_heatmap.png`",
        "- `figures/descriptor_weight_robust_amplitude_heatmap.png`",
        "- `figures/descriptor_weight_correlation_with_STD_heatmap.png`",
        "- `figures/descriptor_weight_suggested_alpha_heatmap.png`",
        "- `figures/descriptor_weight_class_heterogeneity.png`",
    ]
    (outdir / "descriptor_weight_justification_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Descriptor diagnostics for alpha-weight justification.")
    parser.add_argument("--step08", type=Path, default=DEFAULT_STEP08)
    parser.add_argument("--step11y", type=Path, default=DEFAULT_STEP11Y)
    args = parser.parse_args()

    step08 = args.step08.resolve()
    step11y = args.step11y.resolve()
    outdir = step11y
    figdir = outdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    class_df = pd.read_csv(step08 / "step08_final_class_descriptors.csv")
    class_df["class_id"] = class_df["class_id"].astype(int)
    heterogeneity_df = class_heterogeneity_table(class_df)
    cases = read_cases(step11y)
    std_stack = np.load(step11y / "prototype_based_baseline_STD_norm.npy").astype(np.float32)

    rows: list[dict[str, Any]] = []
    for descriptor, meta in DESCRIPTORS.items():
        step08_path = step08 / meta["step08"]
        step11y_path = step11y / meta["step11y"]
        if not step08_path.exists():
            continue
        maps = np.load(step08_path).astype(np.float32)
        if maps.ndim != 3:
            raise ValueError(f"Expected 3-D descriptor map for {descriptor}: {maps.shape}")
        global_vals = finite_values(maps)
        global_stats = stats(global_vals)
        global_iqr = global_stats["IQR"]
        step11y_maps = np.load(step11y_path).astype(np.float32) if step11y_path.exists() else None

        for i in range(maps.shape[0]):
            class_id = i + 1
            class_row = heterogeneity_df[heterogeneity_df["class_id"].eq(class_id)]
            class_label = str(class_row.iloc[0].get("class_label", f"class_{class_id:02d}")) if not class_row.empty else f"class_{class_id:02d}"
            regime = str(class_row.iloc[0].get("cv_regime_label", "")) if not class_row.empty else ""
            vals = finite_values(maps[i])
            row_stats = stats(vals)
            rel_contrast = row_stats["IQR"] / global_iqr if math.isfinite(global_iqr) and global_iqr > 1e-12 else float("nan")
            global_robust = global_stats["robust_amplitude"]
            selectivity_raw = row_stats["robust_amplitude"] / global_robust if math.isfinite(global_robust) and global_robust > 1e-12 else float("nan")
            selectivity_score = float(np.clip(selectivity_raw, 0.0, 1.0)) if math.isfinite(selectivity_raw) else float("nan")

            matches = cases[cases["predicted_class"].eq(class_id)]
            corr = float("nan")
            corr_case_id = ""
            corr_date = ""
            corr_note = "no_matching_step11y_case"
            if not matches.empty and step11y_maps is not None:
                corrs = []
                corr_case_ids = []
                corr_dates = []
                for _, case in matches.iterrows():
                    case_idx = int(case["case_order"])
                    c = pearson(step11y_maps[case_idx], std_stack[case_idx])
                    if math.isfinite(c):
                        corrs.append(c)
                    corr_case_ids.append(str(case["case_id"]))
                    corr_dates.append(str(case["date"]))
                if corrs:
                    corr = float(np.nanmean(corrs))
                    corr_note = "available"
                else:
                    corr_note = "constant_descriptor_or_STD"
                corr_case_id = "|".join(corr_case_ids)
                corr_date = "|".join(corr_dates)

            novelty = 1.0 - abs(corr) if math.isfinite(corr) else float("nan")
            redundancy = abs(corr) if math.isfinite(corr) else float("nan")
            utility = rel_contrast * novelty if math.isfinite(rel_contrast) and math.isfinite(novelty) else float("nan")
            alpha_category, alpha = suggested_alpha(utility)
            h_score = float(class_row.iloc[0].get("class_heterogeneity_score", float("nan"))) if not class_row.empty else float("nan")
            h_cap = float(class_row.iloc[0].get("class_alpha_cap", float("nan"))) if not class_row.empty else float("nan")
            novelty_for_alpha = novelty if math.isfinite(novelty) else 0.5
            alpha_basis = "H_plus_S_plus_R" if math.isfinite(novelty) else "H_plus_S_no_STD_correlation"
            if math.isfinite(h_score) and math.isfinite(selectivity_score):
                if math.isfinite(novelty):
                    hierarchical_score = 0.50 * h_score + 0.30 * selectivity_score + 0.20 * novelty
                else:
                    hierarchical_score = 0.65 * h_score + 0.35 * selectivity_score
            else:
                hierarchical_score = float("nan")
            hierarchical_category, hierarchical_alpha = score_to_alpha(hierarchical_score, "hierarchical utility")
            if math.isfinite(h_cap) and math.isfinite(hierarchical_alpha):
                hierarchical_alpha = min(hierarchical_alpha, h_cap)
                if h_cap <= 0.25:
                    hierarchical_category = "low heterogeneity cap"
                elif h_cap <= 0.50 and hierarchical_alpha <= 0.50:
                    hierarchical_category = "medium heterogeneity cap" if hierarchical_score >= 0.33 else hierarchical_category
            descriptor_matches_class = (
                ("boundary" in descriptor and "homogeneous" not in regime)
                or (descriptor in {"interest_map", "representative_zone"})
                or (descriptor in {"cold_region", "warm_region"} and h_score >= 0.5)
            )

            rows.append(
                {
                    "class_id": class_id,
                    "class_label_short": f"C{class_id:02d}",
                    "class_label": class_label,
                    "cv_regime_label": regime,
                    "descriptor": descriptor,
                    "used_in": meta["used_in"],
                    "prototype_robust_amplitude": float(class_row.iloc[0].get("prototype_robust_amplitude", float("nan"))) if not class_row.empty else float("nan"),
                    "prototype_gradient_p90": float(class_row.iloc[0].get("prototype_gradient_p90", float("nan"))) if not class_row.empty else float("nan"),
                    "prototype_local_variance_mean": float(class_row.iloc[0].get("prototype_local_variance_mean", float("nan"))) if not class_row.empty else float("nan"),
                    "prototype_boundary_density": float(class_row.iloc[0].get("prototype_boundary_density", float("nan"))) if not class_row.empty else float("nan"),
                    "prototype_regime_entropy": float(class_row.iloc[0].get("prototype_regime_entropy", float("nan"))) if not class_row.empty else float("nan"),
                    "H_amp_norm": float(class_row.iloc[0].get("H_amp_norm", float("nan"))) if not class_row.empty else float("nan"),
                    "H_grad_norm": float(class_row.iloc[0].get("H_grad_norm", float("nan"))) if not class_row.empty else float("nan"),
                    "H_var_norm": float(class_row.iloc[0].get("H_var_norm", float("nan"))) if not class_row.empty else float("nan"),
                    "H_boundary_norm": float(class_row.iloc[0].get("H_boundary_norm", float("nan"))) if not class_row.empty else float("nan"),
                    "H_entropy_norm": float(class_row.iloc[0].get("H_entropy_norm", float("nan"))) if not class_row.empty else float("nan"),
                    "class_heterogeneity_score": h_score,
                    "class_heterogeneity_category": str(class_row.iloc[0].get("class_heterogeneity_category", "")) if not class_row.empty else "",
                    "class_alpha_cap": h_cap,
                    **row_stats,
                    "global_descriptor_median": global_stats["median_descriptor_value"],
                    "global_descriptor_IQR": global_stats["IQR"],
                    "global_descriptor_robust_amplitude": global_stats["robust_amplitude"],
                    "relative_contrast": rel_contrast,
                    "descriptor_selectivity_raw": selectivity_raw,
                    "descriptor_selectivity_score": selectivity_score,
                    "descriptor_matches_class_heterogeneity": bool(descriptor_matches_class),
                    "correlation_with_STD": corr,
                    "redundancy_with_STD_abs_corr": redundancy,
                    "correlation_case_id": corr_case_id,
                    "correlation_date": corr_date,
                    "correlation_note": corr_note,
                    "novelty_score": novelty,
                    "novelty_score_for_alpha": novelty_for_alpha,
                    "descriptor_utility_score": utility,
                    "suggested_alpha_category": alpha_category,
                    "suggested_alpha": alpha,
                    "hierarchical_alpha_basis": alpha_basis,
                    "hierarchical_alpha_formula": "0.50*H + 0.30*S + 0.20*(1-|corr_STD|)" if math.isfinite(novelty) else "0.65*H + 0.35*S; STD correlation unavailable",
                    "hierarchical_alpha_score": hierarchical_score,
                    "hierarchical_suggested_alpha_category": hierarchical_category,
                    "hierarchical_suggested_alpha": hierarchical_alpha,
                    "alpha_1_descriptor_only_sensitivity": True,
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "descriptor_weight_justification_statistics.csv", index=False)
    plot_heatmap(df, "IQR", "Per-prototype descriptor IQR", figdir / "descriptor_weight_iqr_heatmap.png")
    plot_heatmap(df, "robust_amplitude", "Per-prototype robust amplitude (P95-P5)", figdir / "descriptor_weight_robust_amplitude_heatmap.png")
    plot_heatmap(df, "correlation_with_STD", "Descriptor correlation with Step11Y STD", figdir / "descriptor_weight_correlation_with_STD_heatmap.png", cmap="coolwarm", vmin=-1, vmax=1)
    plot_heatmap(df, "hierarchical_suggested_alpha", "Hierarchical suggested alpha by class and descriptor", figdir / "descriptor_weight_suggested_alpha_heatmap.png", cmap="YlGnBu", vmin=0.25, vmax=0.75)
    plot_descriptor_bar(df, "hierarchical_alpha_score", "Median hierarchical alpha score by descriptor", figdir / "descriptor_weight_utility_score_by_descriptor.png")
    plot_class_heterogeneity(df, figdir / "descriptor_weight_class_heterogeneity.png")
    make_report(outdir, df, step08, step11y)

    checks = {
        "rows": int(len(df)),
        "descriptors": sorted(df["descriptor"].unique().tolist()),
        "classes": sorted(df["class_label_short"].unique().tolist()),
        "step08": rel(step08),
        "step11y": rel(step11y),
        "planner_rerun": False,
        "available_correlations": int(np.isfinite(df["correlation_with_STD"]).sum()),
        "hierarchical_alpha_formula": "0.50*H + 0.30*S + 0.20*(1-|corr_STD|), capped by class heterogeneity",
        "outputs": {
            "csv": rel(outdir / "descriptor_weight_justification_statistics.csv"),
            "report": rel(outdir / "descriptor_weight_justification_report.md"),
            "figures": [rel(p) for p in sorted(figdir.glob("descriptor_weight_*.png"))],
        },
    }
    (outdir / "descriptor_weight_justification_checks.json").write_text(json.dumps(checks, indent=2, default=json_default), encoding="utf-8")
    print(json.dumps(checks, indent=2, default=json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
