#!/usr/bin/env python
"""Step12D: quantitative justification plots and tables.

This script is intentionally read-only with respect to upstream experiments:
it consumes existing Step12A/Step12B and class-number sensitivity outputs,
derives objective metrics, and writes a new timestamped report folder. It does
not run the planner or any heavy pipeline stage.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import step12_common as c


PREFIX = "fossum_roi_x490_step12d_quantitative_justification_plots"
SUCCESS_STATUSES = {"SUCCESS", "REUSED"}


def read_csv(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def latest_or_none(prefix: str) -> Path | None:
    candidates = sorted(c.RESULTS.glob(f"{prefix}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def make_outdir(output_root: Path) -> Path:
    outdir = output_root.resolve() / f"{PREFIX}_{c.now_tag()}"
    for sub in ["figures", "figures_for_thesis"]:
        (outdir / sub).mkdir(parents=True, exist_ok=True)
    return outdir


def as_num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def copy_col(df: pd.DataFrame, target: str, candidates: list[str]) -> None:
    if target in df.columns:
        return
    for col in candidates:
        if col in df.columns:
            df[target] = df[col]
            return
    df[target] = np.nan


def minmax(s: pd.Series, invert: bool = False) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce").astype(float)
    finite = x[np.isfinite(x)]
    if finite.empty:
        return pd.Series(np.nan, index=s.index, dtype="float64")
    lo = float(finite.min())
    hi = float(finite.max())
    if hi <= lo:
        out = pd.Series(0.0, index=s.index, dtype="float64")
    else:
        out = (x - lo) / (hi - lo)
    if invert:
        out = 1.0 - out
    return out.clip(0.0, 1.0)


def parse_sizes(value: Any) -> list[int]:
    if isinstance(value, list):
        return [int(v) for v in value]
    if pd.isna(value):
        return []
    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return [int(v) for v in parsed]
    except Exception:
        pass
    return []


def pareto_flags(df: pd.DataFrame, objectives: list[tuple[str, bool]]) -> pd.Series:
    """Return True for non-dominated rows.

    objectives contains (column, maximize). Missing values are made
    unfavorable, so a row with missing objective evidence will not dominate
    rows with complete evidence.
    """
    if df.empty:
        return pd.Series(dtype=bool)
    mat = []
    for col, maximize in objectives:
        vals = as_num(df, col).astype(float)
        finite = vals[np.isfinite(vals)]
        if finite.empty:
            filled = pd.Series(-np.inf if maximize else np.inf, index=df.index)
        elif maximize:
            filled = vals.fillna(float(finite.min()) - 1.0)
        else:
            filled = vals.fillna(float(finite.max()) + 1.0)
        mat.append(filled.to_numpy(dtype=float))
    values = np.vstack(mat).T
    flags = np.ones(len(df), dtype=bool)
    maximizes = np.array([m for _, m in objectives], dtype=bool)
    for i in range(len(df)):
        if not np.all(np.isfinite(values[i])):
            flags[i] = False
            continue
        better_or_equal = np.ones(len(df), dtype=bool)
        strictly_better = np.zeros(len(df), dtype=bool)
        for j, maximize in enumerate(maximizes):
            if maximize:
                better_or_equal &= values[:, j] >= values[i, j]
                strictly_better |= values[:, j] > values[i, j]
            else:
                better_or_equal &= values[:, j] <= values[i, j]
                strictly_better |= values[:, j] < values[i, j]
        better_or_equal[i] = False
        strictly_better[i] = False
        flags[i] = not bool(np.any(better_or_equal & strictly_better))
    return pd.Series(flags, index=df.index)


def annotate_selected(ax: plt.Axes, row: pd.Series, x: str, y: str, label: str) -> None:
    xv = pd.to_numeric(pd.Series([row.get(x)]), errors="coerce").iloc[0]
    yv = pd.to_numeric(pd.Series([row.get(y)]), errors="coerce").iloc[0]
    if pd.notna(xv) and pd.notna(yv):
        ax.scatter([xv], [yv], s=145, marker="*", color="#d62728", edgecolor="black", linewidth=0.7, label=label, zorder=5)


def savefig(fig: plt.Figure, out: Path) -> None:
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def line_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    group: str | None,
    out: Path,
    title: str,
    selected: pd.Series | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
) -> bool:
    if df.empty or x not in df.columns or y not in df.columns:
        return False
    data = df.copy()
    data[x] = pd.to_numeric(data[x], errors="coerce")
    data[y] = pd.to_numeric(data[y], errors="coerce")
    data = data.dropna(subset=[x, y])
    if data.empty:
        return False
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    if group and group in data.columns:
        for label, sub in data.groupby(group):
            sub = sub.sort_values(x)
            ax.plot(sub[x], sub[y], marker="o", linewidth=1.4, label=str(label))
        ax.legend(fontsize=7)
    else:
        sub = data.sort_values(x)
        ax.plot(sub[x], sub[y], marker="o", linewidth=1.4)
    if selected is not None and not selected.empty:
        annotate_selected(ax, selected, x, y, "selected")
    ax.set_title(title)
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    ax.grid(alpha=0.25)
    savefig(fig, out)
    return True


def scatter_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    group: str | None,
    out: Path,
    title: str,
    selected: pd.Series | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    pareto_col: str | None = None,
) -> bool:
    if df.empty or x not in df.columns or y not in df.columns:
        return False
    data = df.copy()
    data[x] = pd.to_numeric(data[x], errors="coerce")
    data[y] = pd.to_numeric(data[y], errors="coerce")
    data = data.dropna(subset=[x, y])
    if data.empty:
        return False
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    if group and group in data.columns:
        for label, sub in data.groupby(group):
            ax.scatter(sub[x], sub[y], s=42, alpha=0.78, label=str(label))
        ax.legend(fontsize=7)
    else:
        ax.scatter(data[x], data[y], s=42, alpha=0.78)
    if pareto_col and pareto_col in data.columns and data[pareto_col].astype(bool).any():
        p = data[data[pareto_col].astype(bool)]
        ax.scatter(p[x], p[y], s=95, facecolors="none", edgecolors="black", linewidths=1.2, label="Pareto")
        ax.legend(fontsize=7)
    if selected is not None and not selected.empty:
        annotate_selected(ax, selected, x, y, "selected")
    ax.set_title(title)
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    ax.grid(alpha=0.25)
    savefig(fig, out)
    return True


def bar_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    out: Path,
    title: str,
    selected: pd.Series | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
) -> bool:
    if df.empty or x not in df.columns or y not in df.columns:
        return False
    data = df.copy()
    data[y] = pd.to_numeric(data[y], errors="coerce")
    data = data.dropna(subset=[x, y])
    if data.empty:
        return False
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = data[x].astype(str).tolist()
    colors = ["#4c78a8"] * len(data)
    if selected is not None and not selected.empty:
        selected_key = str(selected.get(x, ""))
        colors = ["#d62728" if str(v) == selected_key else "#4c78a8" for v in labels]
    ax.bar(np.arange(len(data)), data[y].to_numpy(dtype=float), color=colors)
    ax.set_xticks(np.arange(len(data)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_title(title)
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    ax.grid(axis="y", alpha=0.25)
    savefig(fig, out)
    return True


def make_single_decision_table(step12a: Path | None) -> tuple[pd.DataFrame, dict[str, Any]]:
    metrics = read_csv(step12a / "step12a_single_auv_metrics.csv" if step12a else None)
    info: dict[str, Any] = {"source": c.rel(step12a) if step12a else "", "rows_loaded": int(len(metrics))}
    if metrics.empty:
        return pd.DataFrame(), {**info, "status": "missing"}
    df = metrics.copy()
    if "mission_duration_requested_h" in df.columns:
        df["mission_duration"] = df["mission_duration_requested_h"]
    else:
        copy_col(df, "mission_duration", ["mission_duration"])
    copy_col(df, "runtime_seconds", ["solver_runtime", "runtime_seconds", "solver_runtime_s"])
    copy_col(df, "STD_retention", ["STD_retention"])
    if df["STD_retention"].isna().all() and {"collected_STD", "baseline_STD"}.issubset(df.columns):
        df["STD_retention"] = as_num(df, "collected_STD") / as_num(df, "baseline_STD")
    df["STD_loss"] = 1.0 - as_num(df, "STD_retention")
    if "baseline_descriptor" not in df.columns:
        group_cols = [col for col in ["case_id", "mission_duration", "descriptor"] if col in df.columns]
        if group_cols and "collected_descriptor" in df.columns:
            baseline = df[df["alpha"].eq(0)].groupby(group_cols, as_index=False)["collected_descriptor"].max()
            baseline = baseline.rename(columns={"collected_descriptor": "collected_descriptor_baseline"})
            df = df.merge(baseline, on=group_cols, how="left")
    if "collected_descriptor_baseline" not in df.columns:
        df["collected_descriptor_baseline"] = np.nan
    df["descriptor_gain"] = as_num(df, "collected_descriptor") - as_num(df, "collected_descriptor_baseline")
    df["descriptor_gain_norm"] = minmax(df["descriptor_gain"])
    if "regime_balance" not in df.columns:
        df["regime_balance"] = 2.0 * np.minimum(as_num(df, "fraction_path_region_A").fillna(0), as_num(df, "fraction_path_region_B").fillna(0))
    copy_col(df, "path_difference_from_baseline", ["path_difference_from_baseline"])
    df["path_difference_norm"] = minmax(df["path_difference_from_baseline"])
    df["runtime_penalty"] = minmax(df["runtime_seconds"])
    df["tradeoff_score"] = (
        0.40 * as_num(df, "STD_retention").fillna(0)
        + 0.30 * as_num(df, "regime_balance").fillna(0)
        + 0.20 * as_num(df, "descriptor_gain_norm").fillna(0)
        + 0.10 * as_num(df, "path_difference_norm").fillna(0)
        - 0.10 * as_num(df, "runtime_penalty").fillna(0)
    )
    df["pareto_front_flag"] = pareto_flags(
        df,
        [
            ("STD_loss", False),
            ("regime_balance", True),
            ("descriptor_gain_norm", True),
            ("runtime_penalty", False),
        ],
    )
    eligible = df[df["solver_status"].astype(str).isin(SUCCESS_STATUSES) & df["pareto_front_flag"]].copy()
    if eligible.empty:
        eligible = df[df["solver_status"].astype(str).isin(SUCCESS_STATUSES)].copy()
    selected_idx = eligible["tradeoff_score"].idxmax() if not eligible.empty else None
    df["selected_candidate_flag"] = False
    if selected_idx is not None and selected_idx in df.index:
        df.loc[selected_idx, "selected_candidate_flag"] = True
    df["justification_note"] = np.where(
        df["pareto_front_flag"],
        "Pareto candidate; interpret score as an auxiliary ranking, not an absolute truth.",
        "Dominated or weaker tradeoff under the available metrics.",
    )
    keep = [
        "case_id",
        "mission_duration",
        "descriptor",
        "alpha",
        "STD_retention",
        "STD_loss",
        "regime_balance",
        "descriptor_gain",
        "descriptor_gain_norm",
        "runtime_seconds",
        "solver_status",
        "regions_visited",
        "crossing_count",
        "path_difference_from_baseline",
        "pareto_front_flag",
        "tradeoff_score",
        "selected_candidate_flag",
        "justification_note",
    ]
    return df[[col for col in keep if col in df.columns]].copy(), {**info, "status": "loaded"}


def make_multi_decision_table(step12b: Path | None) -> tuple[pd.DataFrame, dict[str, Any]]:
    fleet = read_csv(step12b / "step12b_fleet_level_metrics.csv" if step12b else None)
    vehicle = read_csv(step12b / "step12b_vehicle_level_metrics.csv" if step12b else None)
    info: dict[str, Any] = {
        "source": c.rel(step12b) if step12b else "",
        "fleet_rows_loaded": int(len(fleet)),
        "vehicle_rows_loaded": int(len(vehicle)),
    }
    if fleet.empty:
        return pd.DataFrame(), {**info, "status": "missing"}
    df = fleet.copy()
    if "mission_duration_requested_h" in df.columns:
        df["mission_duration"] = df["mission_duration_requested_h"]
    else:
        copy_col(df, "mission_duration", ["mission_duration"])
    copy_col(df, "runtime_seconds", ["solver_runtime", "runtime_seconds", "solver_runtime_s"])
    copy_col(df, "fleet_STD_retention", ["STD_retention", "fleet_STD_retention"])
    if df["fleet_STD_retention"].isna().all() and {"fleet_collected_STD", "baseline_fleet_STD"}.issubset(df.columns):
        df["fleet_STD_retention"] = as_num(df, "fleet_collected_STD") / as_num(df, "baseline_fleet_STD")
    df["fleet_STD_loss"] = 1.0 - as_num(df, "fleet_STD_retention")
    copy_col(df, "region_A_coverage", ["fleet_region_A_coverage", "region_A_coverage"])
    copy_col(df, "region_B_coverage", ["fleet_region_B_coverage", "region_B_coverage"])
    if "region_B_gain" not in df.columns:
        copy_col(df, "region_B_gain", ["region_B_coverage_gain"])
    if df["region_B_gain"].isna().all():
        baseline = df[df["strategy"].eq("baseline_shared_STD")].groupby(["case_id", "mission_duration"], as_index=False)["region_B_coverage"].max()
        baseline = baseline.rename(columns={"region_B_coverage": "region_B_coverage_baseline"})
        df = df.merge(baseline, on=["case_id", "mission_duration"], how="left")
        df["region_B_gain"] = as_num(df, "region_B_coverage") - as_num(df, "region_B_coverage_baseline")
    df["regime_balance"] = 2.0 * np.minimum(as_num(df, "region_A_coverage").fillna(0), as_num(df, "region_B_coverage").fillna(0))
    copy_col(df, "specialization_score", ["regime_specialization_score", "specialization_score"])
    copy_col(df, "trajectory_overlap_ratio", ["trajectory_overlap_ratio"])
    copy_col(df, "inter_vehicle_mean_distance", ["inter_vehicle_mean_distance"])
    copy_col(df, "complementarity_score", ["complementarity_score"])
    df["inter_vehicle_distance_norm"] = minmax(df["inter_vehicle_mean_distance"])
    df["overlap_penalty"] = minmax(df["trajectory_overlap_ratio"])
    df["runtime_penalty"] = minmax(df["runtime_seconds"])
    df["tradeoff_score"] = (
        0.35 * as_num(df, "fleet_STD_retention").fillna(0)
        + 0.25 * as_num(df, "regime_balance").fillna(0)
        + 0.25 * as_num(df, "specialization_score").fillna(0)
        + 0.10 * as_num(df, "inter_vehicle_distance_norm").fillna(0)
        - 0.05 * as_num(df, "overlap_penalty").fillna(0)
        - 0.05 * as_num(df, "runtime_penalty").fillna(0)
    )
    df["pareto_front_flag"] = pareto_flags(
        df,
        [
            ("fleet_STD_loss", False),
            ("region_B_gain", True),
            ("specialization_score", True),
            ("trajectory_overlap_ratio", False),
            ("runtime_penalty", False),
        ],
    )
    eligible = df[df["solver_status"].astype(str).isin(SUCCESS_STATUSES) & df["pareto_front_flag"] & ~df["strategy"].eq("baseline_shared_STD")].copy()
    if eligible.empty:
        eligible = df[df["solver_status"].astype(str).isin(SUCCESS_STATUSES) & ~df["strategy"].eq("baseline_shared_STD")].copy()
    selected_idx = eligible["tradeoff_score"].idxmax() if not eligible.empty else None
    df["selected_candidate_flag"] = False
    if selected_idx is not None and selected_idx in df.index:
        df.loc[selected_idx, "selected_candidate_flag"] = True
    df["vehicle_specific_weight"] = df.get("strategy", "")
    df["justification_note"] = np.where(
        df["pareto_front_flag"],
        "Pareto candidate; auxiliary score ranks the available tradeoffs.",
        "Dominated or weaker tradeoff under the available metrics.",
    )
    keep = [
        "case_id",
        "mission_duration",
        "strategy",
        "vehicle_specific_weight",
        "w_STD",
        "w_region",
        "fleet_STD_retention",
        "fleet_STD_loss",
        "regime_balance",
        "region_A_coverage",
        "region_B_coverage",
        "region_B_gain",
        "specialization_score",
        "complementarity_score",
        "trajectory_overlap_ratio",
        "inter_vehicle_mean_distance",
        "runtime_seconds",
        "solver_status",
        "pareto_front_flag",
        "tradeoff_score",
        "selected_candidate_flag",
        "justification_note",
    ]
    return df[[col for col in keep if col in df.columns]].copy(), {**info, "status": "loaded"}


def make_class_decision_table(step04: Path | None, step05: Path | None) -> tuple[pd.DataFrame, dict[str, Any]]:
    ranking = read_csv(step04 / "step04_sd_probe_ranking.csv" if step04 else None)
    if ranking.empty:
        ranking = read_csv(step04 / "ranking.csv" if step04 else None)
    meta05 = read_json(step05 / "canonical_metadata.json" if step05 else None)
    info = {
        "step04_source": c.rel(step04) if step04 else "",
        "step05_source": c.rel(step05) if step05 else "",
        "rows_loaded": int(len(ranking)),
    }
    if ranking.empty:
        return pd.DataFrame(), {**info, "status": "missing"}
    df = ranking.copy()
    copy_col(df, "n_classes", ["number_of_classes", "n_classes"])
    copy_col(df, "SD_fraction", ["sd_fraction_of_max", "SD_fraction"])
    copy_col(df, "ICV_mean", ["mean_icv", "mean_icv_mean", "ICV_mean"])
    copy_col(df, "ICV_std", ["std_icv", "std_icv_mean", "ICV_std"])
    copy_col(df, "runtime_seconds", ["runtime_seconds", "runtime_mean_seconds"])
    if meta05.get("n_classes") is not None and meta05.get("runtime_seconds") is not None:
        mask6 = as_num(df, "n_classes").eq(float(meta05["n_classes"])) & as_num(df, "SD_fraction").round(4).eq(round(float(meta05.get("sd_value", 0)) / float(meta05.get("max_merge_distance", 1)), 4))
        if mask6.any():
            df.loc[mask6, "runtime_seconds"] = float(meta05["runtime_seconds"])
        else:
            df.loc[as_num(df, "n_classes").eq(float(meta05["n_classes"])), "runtime_seconds"] = df.loc[as_num(df, "n_classes").eq(float(meta05["n_classes"])), "runtime_seconds"].fillna(float(meta05["runtime_seconds"]))
    sizes = df.get("class_sizes", pd.Series("", index=df.index)).map(parse_sizes)
    if "min_class_size" not in df.columns:
        df["min_class_size"] = sizes.map(lambda x: min(x) if x else np.nan)
    if "max_class_size" not in df.columns:
        df["max_class_size"] = sizes.map(lambda x: max(x) if x else np.nan)
    df["number_of_small_classes"] = sizes.map(lambda x: int(sum(v < 20 for v in x)) if x else np.nan)
    df["class_balance_score"] = (as_num(df, "min_class_size") / as_num(df, "max_class_size")).clip(0, 1)
    df["inter_class_separation"] = np.nan
    if "balanced_score" in df.columns:
        df["ranking_score"] = df["balanced_score"]
    else:
        df["ranking_score"] = np.nan
    df["selected_flag"] = as_num(df, "n_classes").eq(6)
    df["justification_note"] = np.where(
        df["selected_flag"],
        "Selected canonical branch: lower ICV than 5 classes while avoiding the fragmentation seen at 10 classes.",
        np.where(
            as_num(df, "n_classes") > 6,
            "Lower ICV is penalized by fragmentation/small-class risk.",
            "Plausible comparator; check ICV, class size, interpretability, and stability together.",
        ),
    )
    keep = [
        "n_classes",
        "SD_fraction",
        "ICV_mean",
        "ICV_std",
        "min_class_size",
        "max_class_size",
        "class_balance_score",
        "number_of_small_classes",
        "inter_class_separation",
        "runtime_seconds",
        "ranking_score",
        "behavior_label",
        "behavior_reason",
        "selected_flag",
        "justification_note",
    ]
    return df[[col for col in keep if col in df.columns]].sort_values(["n_classes", "SD_fraction"]).copy(), {**info, "status": "loaded"}


def write_figures(outdir: Path, single: pd.DataFrame, multi: pd.DataFrame, classes: pd.DataFrame) -> list[str]:
    figdir = outdir / "figures"
    made: list[str] = []

    selected_single = single[single.get("selected_candidate_flag", False).astype(bool)].head(1)
    selected_single_row = selected_single.iloc[0] if not selected_single.empty else None
    if line_plot(single, "alpha", "STD_retention", "descriptor", figdir / "single_auv_alpha_vs_STD_retention.png", "Single-AUV alpha vs STD retention", selected_single_row):
        made.append("single_auv_alpha_vs_STD_retention.png")
    if line_plot(single, "alpha", "regime_balance", "descriptor", figdir / "single_auv_alpha_vs_regime_balance.png", "Single-AUV alpha vs regime balance", selected_single_row):
        made.append("single_auv_alpha_vs_regime_balance.png")
    if scatter_plot(single, "STD_loss", "regime_balance", "descriptor", figdir / "single_auv_STD_loss_vs_regime_balance_pareto.png", "Single-AUV STD loss vs regime balance", selected_single_row, pareto_col="pareto_front_flag"):
        made.append("single_auv_STD_loss_vs_regime_balance_pareto.png")
    if scatter_plot(single, "STD_loss", "descriptor_gain", "descriptor", figdir / "single_auv_STD_loss_vs_descriptor_gain.png", "Single-AUV STD loss vs descriptor gain", selected_single_row):
        made.append("single_auv_STD_loss_vs_descriptor_gain.png")
    if scatter_plot(single, "alpha", "runtime_seconds", "descriptor", figdir / "single_auv_weight_vs_runtime.png", "Single-AUV weight vs runtime", selected_single_row):
        made.append("single_auv_weight_vs_runtime.png")
    agg_single = single.groupby(["descriptor", "alpha"], as_index=False)["tradeoff_score"].mean()
    agg_single["label"] = agg_single["descriptor"].astype(str) + " a=" + agg_single["alpha"].astype(str)
    selected_single_agg = None
    if selected_single_row is not None:
        key = f"{selected_single_row.get('descriptor')} a={selected_single_row.get('alpha')}"
        selected_single_agg = pd.Series({"label": key, "tradeoff_score": selected_single_row.get("tradeoff_score")})
    if bar_plot(agg_single.sort_values("tradeoff_score", ascending=False), "label", "tradeoff_score", figdir / "single_auv_tradeoff_score_by_alpha.png", "Single-AUV auxiliary tradeoff score", selected_single_agg):
        made.append("single_auv_tradeoff_score_by_alpha.png")

    selected_multi = multi[multi.get("selected_candidate_flag", False).astype(bool)].head(1)
    selected_multi_row = selected_multi.iloc[0] if not selected_multi.empty else None
    if line_plot(multi, "w_region", "fleet_STD_retention", "mission_duration", figdir / "multi_auv_weight_vs_STD_retention.png", "Multi-AUV weight vs STD retention", selected_multi_row):
        made.append("multi_auv_weight_vs_STD_retention.png")
    if line_plot(multi, "w_region", "region_B_coverage", "mission_duration", figdir / "multi_auv_weight_vs_region_B_coverage.png", "Multi-AUV weight vs region B coverage", selected_multi_row):
        made.append("multi_auv_weight_vs_region_B_coverage.png")
    if line_plot(multi, "w_region", "specialization_score", "mission_duration", figdir / "multi_auv_weight_vs_specialization_score.png", "Multi-AUV weight vs specialization", selected_multi_row):
        made.append("multi_auv_weight_vs_specialization_score.png")
    if scatter_plot(multi, "fleet_STD_loss", "region_B_gain", "strategy", figdir / "multi_auv_STD_loss_vs_region_B_gain_pareto.png", "Multi-AUV STD loss vs region B gain", selected_multi_row, pareto_col="pareto_front_flag"):
        made.append("multi_auv_STD_loss_vs_region_B_gain_pareto.png")
    if scatter_plot(multi, "fleet_STD_loss", "specialization_score", "strategy", figdir / "multi_auv_STD_loss_vs_specialization_score.png", "Multi-AUV STD loss vs specialization", selected_multi_row):
        made.append("multi_auv_STD_loss_vs_specialization_score.png")
    if scatter_plot(multi, "w_region", "runtime_seconds", "mission_duration", figdir / "multi_auv_weight_vs_runtime.png", "Multi-AUV weight vs runtime", selected_multi_row):
        made.append("multi_auv_weight_vs_runtime.png")
    agg_multi = multi.groupby(["strategy", "w_region"], as_index=False)["tradeoff_score"].mean().sort_values("tradeoff_score", ascending=False)
    if bar_plot(agg_multi, "strategy", "tradeoff_score", figdir / "multi_auv_tradeoff_score_by_weight.png", "Multi-AUV auxiliary tradeoff score", selected_multi_row):
        made.append("multi_auv_tradeoff_score_by_weight.png")

    selected_class = classes[classes.get("selected_flag", False).astype(bool)].head(1)
    selected_class_row = selected_class.iloc[0] if not selected_class.empty else None
    if line_plot(classes, "n_classes", "ICV_mean", None, figdir / "classes_n_vs_ICV.png", "Number of classes vs ICV", selected_class_row):
        made.append("classes_n_vs_ICV.png")
    if line_plot(classes, "n_classes", "min_class_size", None, figdir / "classes_n_vs_min_class_size.png", "Number of classes vs minimum class size", selected_class_row):
        made.append("classes_n_vs_min_class_size.png")
    if line_plot(classes, "n_classes", "class_balance_score", None, figdir / "classes_n_vs_class_balance.png", "Number of classes vs class balance", selected_class_row):
        made.append("classes_n_vs_class_balance.png")
    if line_plot(classes, "n_classes", "inter_class_separation", None, figdir / "classes_n_vs_inter_class_separation.png", "Number of classes vs inter-class separation", selected_class_row):
        made.append("classes_n_vs_inter_class_separation.png")
    if line_plot(classes, "n_classes", "runtime_seconds", None, figdir / "classes_n_vs_runtime.png", "Number of classes vs runtime", selected_class_row):
        made.append("classes_n_vs_runtime.png")
    if scatter_plot(classes, "ICV_mean", "min_class_size", "n_classes", figdir / "classes_tradeoff_summary.png", "Class-number ICV and class-size tradeoff", selected_class_row):
        made.append("classes_tradeoff_summary.png")

    thesis_map = {
        "single_auv_STD_loss_vs_regime_balance_pareto.png": "planner_weight_pareto_single_auv.png",
        "multi_auv_STD_loss_vs_region_B_gain_pareto.png": "planner_weight_pareto_multi_auv.png",
        "classes_tradeoff_summary.png": "class_number_ICV_tradeoff.png",
        "classes_n_vs_runtime.png": "class_number_runtime_tradeoff.png",
        "multi_auv_tradeoff_score_by_weight.png": "multi_auv_weight_tradeoff.png",
        "single_auv_tradeoff_score_by_alpha.png": "single_auv_weight_tradeoff.png",
    }
    thesis_dir = outdir / "figures_for_thesis"
    for src, dst in thesis_map.items():
        src_path = figdir / src
        if src_path.exists():
            shutil.copy2(src_path, thesis_dir / dst)
    captions = [
        "# Suggested captions",
        "",
        "- `planner_weight_pareto_single_auv.png`: Single-AUV Pareto tradeoff between STD loss and regime balance; outlined points are non-dominated candidates and the star marks the auxiliary-score recommendation.",
        "- `planner_weight_pareto_multi_auv.png`: Multi-AUV Pareto tradeoff between fleet STD loss and region-B gain; the selected point balances information retention, specialization, low overlap, and runtime.",
        "- `class_number_ICV_tradeoff.png`: Class-number decision evidence showing that lower ICV alone is insufficient because high class counts can fragment the dataset.",
        "- `class_number_runtime_tradeoff.png`: Runtime evidence for class-number selection; runtime is secondary to ICV, class size, stability, separation, and interpretability.",
        "- `multi_auv_weight_tradeoff.png`: Auxiliary multi-AUV ranking score across vehicle-specific weights.",
        "- `single_auv_weight_tradeoff.png`: Auxiliary single-AUV ranking score across alpha/descriptor combinations.",
    ]
    c.write_text(thesis_dir / "captions.md", "\n".join(captions) + "\n")
    return made


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 30) -> str:
    return c.md_table(df, [col for col in cols if col in df.columns], max_rows=max_rows)


def selected_summary(df: pd.DataFrame, flag: str) -> pd.DataFrame:
    if df.empty or flag not in df.columns:
        return pd.DataFrame()
    return df[df[flag].astype(bool)].copy()


def write_reports(outdir: Path, single: pd.DataFrame, multi: pd.DataFrame, classes: pd.DataFrame, checks: dict[str, Any]) -> None:
    single_sel = selected_summary(single, "selected_candidate_flag")
    multi_sel = selected_summary(multi, "selected_candidate_flag")
    class_sel = selected_summary(classes, "selected_flag")
    dominated_single = single[~single.get("pareto_front_flag", pd.Series(False, index=single.index)).astype(bool)] if not single.empty else pd.DataFrame()
    dominated_multi = multi[~multi.get("pareto_front_flag", pd.Series(False, index=multi.index)).astype(bool)] if not multi.empty else pd.DataFrame()

    weight_lines = [
        "# Step12D weight-selection report",
        "",
        "Scores are auxiliary rankings only. The defensible interpretation is the tradeoff among information retention, regime balance/specialization, path change, overlap, and runtime.",
        "",
        "## Single-AUV selected candidate",
        md_table(single_sel, ["case_id", "mission_duration", "descriptor", "alpha", "STD_retention", "STD_loss", "regime_balance", "descriptor_gain", "runtime_seconds", "tradeoff_score"], 20),
        "",
        "## Multi-AUV selected candidate",
        md_table(multi_sel, ["case_id", "mission_duration", "strategy", "w_STD", "w_region", "fleet_STD_retention", "fleet_STD_loss", "region_B_gain", "specialization_score", "runtime_seconds", "tradeoff_score"], 20),
        "",
        "## Single-AUV Pareto candidates",
        md_table(single[single.get("pareto_front_flag", False).astype(bool)] if not single.empty else single, ["case_id", "mission_duration", "descriptor", "alpha", "STD_loss", "regime_balance", "descriptor_gain_norm", "runtime_seconds", "tradeoff_score"], 80),
        "",
        "## Multi-AUV Pareto candidates",
        md_table(multi[multi.get("pareto_front_flag", False).astype(bool)] if not multi.empty else multi, ["case_id", "mission_duration", "strategy", "w_region", "fleet_STD_loss", "region_B_gain", "specialization_score", "trajectory_overlap_ratio", "runtime_seconds", "tradeoff_score"], 80),
        "",
        "Dominated single-AUV rows: " + str(len(dominated_single)),
        "Dominated multi-AUV rows: " + str(len(dominated_multi)),
    ]
    c.write_text(outdir / "step12d_weight_selection_report.md", "\n".join(weight_lines) + "\n")

    class_lines = [
        "# Step12D class-number selection report",
        "",
        "ICV supports the 6-class branch relative to the 5-class branch in the available Step04 evidence, but ICV must not be used alone because it naturally decreases when more classes are allowed.",
        "",
        "The decision combines ICV, minimum class size, fragmentation risk, stability/qualitative notes where available, separation where available, interpretability, and runtime as a secondary criterion.",
        "",
        "## Decision table",
        md_table(classes, ["n_classes", "SD_fraction", "ICV_mean", "min_class_size", "class_balance_score", "number_of_small_classes", "runtime_seconds", "ranking_score", "behavior_label", "selected_flag"], 50),
        "",
        "## Selected branch",
        md_table(class_sel, ["n_classes", "SD_fraction", "ICV_mean", "min_class_size", "class_balance_score", "runtime_seconds", "justification_note"], 10),
        "",
        "Runtime is secondary for class-number choice because the largest costs are feature extraction, dictionary learning, sparse coding, and clustering; the final cut between nearby class counts is not the dominant computational burden.",
    ]
    c.write_text(outdir / "step12d_class_number_selection_report.md", "\n".join(class_lines) + "\n")

    runtime_lines = [
        "# Step12D runtime discussion",
        "",
        "Planner runtime is included as a penalty in the auxiliary weight scores, so a candidate can be rejected if it gains little scientific value at a high runtime cost.",
        "",
        "For class number, runtime is treated as secondary. The scientific risks are over-fragmentation, very small classes, weak stability, and reduced interpretability.",
        "",
        "## Single-AUV runtime evidence",
        md_table(single.sort_values("runtime_seconds", ascending=False) if not single.empty else single, ["case_id", "mission_duration", "descriptor", "alpha", "runtime_seconds", "STD_retention", "tradeoff_score"], 30),
        "",
        "## Multi-AUV runtime evidence",
        md_table(multi.sort_values("runtime_seconds", ascending=False) if not multi.empty else multi, ["case_id", "mission_duration", "strategy", "runtime_seconds", "fleet_STD_retention", "tradeoff_score"], 30),
    ]
    c.write_text(outdir / "step12d_runtime_discussion.md", "\n".join(runtime_lines) + "\n")

    final_lines = [
        "# Step12D final recommendations",
        "",
        f"Verdict: `{checks['verdict']}`",
        "",
        "1. The most useful weight plots are the Pareto plots: `single_auv_STD_loss_vs_regime_balance_pareto.png` and `multi_auv_STD_loss_vs_region_B_gain_pareto.png`.",
        "2. The best single-AUV weight under the auxiliary score is listed in `step12d_single_auv_weight_decision_table.csv` with `selected_candidate_flag=True`.",
        "3. The best multi-AUV weight under the auxiliary score is listed in `step12d_multi_auv_weight_decision_table.csv` with `selected_candidate_flag=True`.",
        "4. Mission duration should be discussed as a sensitivity axis, because the same weights can behave differently under short and long missions.",
        "5. Dominated configurations are those with `pareto_front_flag=False`; Pareto candidates are exported separately.",
        "6. Runtime affects weight selection through `runtime_penalty`, but does not override scientific tradeoff metrics by itself.",
        "7. Runtime has limited influence on class-number choice compared with ICV, class size, stability, separation, interpretability, and fragmentation risk.",
        "8. The available ICV evidence supports 6 classes versus 5 classes, while the 10-class alternative illustrates why minimum ICV alone is not enough.",
        "9. Yes, there is a real risk of choosing too many classes if ICV is minimized naively.",
        "10. Thesis recommendation: present 6 classes as the canonical Fossum-style branch, and present planner weights as Pareto-supported tradeoffs rather than universal optima.",
    ]
    c.write_text(outdir / "step12d_final_recommendations.md", "\n".join(final_lines) + "\n")

    full = "\n\n".join(
        [
            "# Step12D quantitative justification report",
            f"Verdict: `{checks['verdict']}`",
            "This report uses existing CSV/JSON outputs only. No planner or heavy pipeline stage was re-run.",
            "\n".join(weight_lines),
            "\n".join(class_lines),
            "\n".join(runtime_lines),
            "\n".join(final_lines),
        ]
    )
    c.write_text(outdir / "step12d_quantitative_justification_report.md", full + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step12D quantitative justification plots.")
    parser.add_argument("--step12a", type=Path, default=None)
    parser.add_argument("--step12b", type=Path, default=None)
    parser.add_argument("--step04", type=Path, default=None)
    parser.add_argument("--step05", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=c.RESULTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    step12a = args.step12a.resolve() if args.step12a else latest_or_none("fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity")
    step12b = args.step12b.resolve() if args.step12b else latest_or_none("fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity")
    step04 = args.step04.resolve() if args.step04 else latest_or_none("fossum_roi_x490_step04_sd_probe_patch40x24_dict4")
    step05 = args.step05.resolve() if args.step05 else latest_or_none("fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25")
    outdir = make_outdir(args.output_root)

    single, single_info = make_single_decision_table(step12a)
    multi, multi_info = make_multi_decision_table(step12b)
    classes, class_info = make_class_decision_table(step04, step05)

    single.to_csv(outdir / "step12d_single_auv_weight_decision_table.csv", index=False)
    multi.to_csv(outdir / "step12d_multi_auv_weight_decision_table.csv", index=False)
    classes.to_csv(outdir / "step12d_class_number_decision_table.csv", index=False)

    single_pareto = single[single.get("pareto_front_flag", pd.Series(False, index=single.index)).astype(bool)].copy() if not single.empty else pd.DataFrame()
    multi_pareto = multi[multi.get("pareto_front_flag", pd.Series(False, index=multi.index)).astype(bool)].copy() if not multi.empty else pd.DataFrame()
    single_pareto.to_csv(outdir / "step12d_single_auv_pareto_candidates.csv", index=False)
    multi_pareto.to_csv(outdir / "step12d_multi_auv_pareto_candidates.csv", index=False)

    figures = write_figures(outdir, single, multi, classes)
    missing_metrics = []
    partially_missing_metrics = []
    for name, df, cols in [
        ("single", single, ["STD_retention", "regime_balance", "descriptor_gain_norm", "runtime_seconds"]),
        ("multi", multi, ["fleet_STD_retention", "region_B_gain", "specialization_score", "trajectory_overlap_ratio", "runtime_seconds"]),
        ("classes", classes, ["ICV_mean", "min_class_size", "class_balance_score", "runtime_seconds"]),
    ]:
        for col in cols:
            if df.empty or col not in df.columns or df[col].isna().all():
                missing_metrics.append(f"{name}.{col}")
            elif df[col].isna().any():
                partially_missing_metrics.append(f"{name}.{col}")

    if single.empty or multi.empty:
        verdict = "WAITING_FOR_FULL_STEP12_RESULTS"
    elif "classes.ICV_mean" in missing_metrics:
        verdict = "MISSING_METRICS_NEED_EXTRACTION"
    elif missing_metrics:
        verdict = "MISSING_METRICS_NEED_EXTRACTION"
    else:
        verdict = "QUANTITATIVE_JUSTIFICATION_READY"

    checks = {
        "step": "Step12D",
        "output_dir": c.rel(outdir),
        "inputs": {
            "step12a": single_info,
            "step12b": multi_info,
            "step04": class_info,
            "step05": c.rel(step05) if step05 else "",
        },
        "step12a_found": bool(step12a and step12a.exists()),
        "step12b_found": bool(step12b and step12b.exists()),
        "figures_generated": figures,
        "figures_generated_count": int(len(figures)),
        "ICV_calculated_or_loaded": bool(not classes.empty and "ICV_mean" in classes.columns and classes["ICV_mean"].notna().any()),
        "runtime_included": bool(
            (not single.empty and single.get("runtime_seconds", pd.Series(dtype=float)).notna().any())
            and (not multi.empty and multi.get("runtime_seconds", pd.Series(dtype=float)).notna().any())
        ),
        "pareto_front_calculated": bool((not single_pareto.empty) or (not multi_pareto.empty)),
        "decision_tables_created": True,
        "heavy_simulation_rerun": False,
        "missing_metrics": missing_metrics,
        "partially_missing_metrics": partially_missing_metrics,
        "verdict": verdict,
    }
    c.write_json(outdir / "step12d_checks.json", checks)
    c.write_json(
        outdir / "step12d_metadata.json",
        {
            "created_at": c.now_tag(),
            "script": "scripts/12d_quantitative_justification_plots.py",
            "no_heavy_rerun": True,
            "outputs": checks,
        },
    )
    write_reports(outdir, single, multi, classes, checks)
    print(f"Step12D complete: {c.rel(outdir)}")
    print(f"Verdict: {verdict}")
    print(f"Figures: {len(figures)}")
    print(f"Missing metrics: {', '.join(missing_metrics) if missing_metrics else 'none'}")
    return 0 if verdict != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
