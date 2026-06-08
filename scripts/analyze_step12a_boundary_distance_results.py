#!/usr/bin/env python
"""Analyze Step12A boundary-distance descriptor sensitivity outputs.

This script only reads completed Step12A outputs. It does not call the planner.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_INPUT = Path(
    "results/fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260605_152501"
)
CASE_ID = "C01_representative"
DURATION_H = 12.0
DESCRIPTORS = [
    "boundary_score",
    "boundary_distance_score_r1_cells",
    "boundary_distance_score_r3_cells",
    "boundary_distance_score_r5_cells",
    "interest_map",
]
OUTPUT_REPORT = "step12a_boundary_distance_results_report.md"
OUTPUT_SUMMARY = "step12a_boundary_distance_results_summary.csv"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "n/a"
    return f"{number:.{digits}f}"


def md_table(df: pd.DataFrame, columns: Iterable[str], max_rows: int = 80) -> str:
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return "_No columns available._"
    view = df.loc[:, cols].head(max_rows).copy()
    if view.empty:
        return "_No rows available._"
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]) or pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: fmt(x, 3))
        else:
            view[col] = view[col].fillna("n/a").astype(str)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in view.to_numpy()]
    return "\n".join([header, sep, *rows])


def normalize_high(values: pd.Series) -> pd.Series:
    values = safe_num(values)
    lo = values.min(skipna=True)
    hi = values.max(skipna=True)
    if not math.isfinite(float(lo)) or not math.isfinite(float(hi)) or abs(float(hi - lo)) < 1e-12:
        return pd.Series(np.ones(len(values)), index=values.index)
    return (values - lo) / (hi - lo)


def normalize_low(values: pd.Series) -> pd.Series:
    return 1.0 - normalize_high(values)


def discover_files(outdir: Path) -> dict[str, list[Path]]:
    files = [p for p in outdir.rglob("*") if p.is_file()]
    return {
        "csv": sorted(p for p in files if p.suffix.lower() == ".csv"),
        "json": sorted(p for p in files if p.suffix.lower() == ".json"),
        "figures": sorted(p for p in files if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".svg"}),
        "diagnostics": sorted(p for p in files if "diagnostic" in p.name.lower() or "stderr" in p.name.lower() or "stdout" in p.name.lower()),
    }


def find_main_metrics_csv(csv_paths: list[Path]) -> tuple[Path, pd.DataFrame, list[str]]:
    preferred = [p for p in csv_paths if p.name == "step12a_single_auv_metrics.csv"]
    candidates = preferred or csv_paths
    required_groups = [
        {"case_id", "mission_duration_requested_h", "descriptor", "alpha"},
        {"collected_STD", "trajectory_length"},
        {"solver_status"},
    ]
    scored: list[tuple[int, Path, pd.DataFrame]] = []
    for path in candidates:
        try:
            df = read_csv(path)
        except Exception:
            continue
        score = 0
        cols = set(df.columns)
        for group in required_groups:
            score += len(cols.intersection(group))
        score += int("collected_information_score" in cols)
        score += int("collected_descriptor" in cols)
        score += int("percentage_path_in_top10_descriptor" in cols)
        scored.append((score, path, df))
    if not scored:
        raise FileNotFoundError("No readable CSV files were found.")
    scored.sort(key=lambda item: (item[0], item[1].name == "step12a_single_auv_metrics.csv"), reverse=True)
    score, path, df = scored[0]
    missing = sorted(set().union(*required_groups) - set(df.columns))
    if score < 6:
        raise ValueError(f"Could not identify a complete main metrics CSV. Best candidate: {path}")
    return path, df, missing


def load_optional_csv(outdir: Path, name: str) -> pd.DataFrame | None:
    path = outdir / name
    if not path.exists():
        return None
    return read_csv(path)


def prepare_summary(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = metrics.copy()
    df["mission_duration_requested_h"] = safe_num(df["mission_duration_requested_h"])
    df["alpha"] = safe_num(df["alpha"])
    sub = df[
        df["case_id"].astype(str).eq(CASE_ID)
        & np.isclose(df["mission_duration_requested_h"], DURATION_H)
        & df["descriptor"].astype(str).isin(DESCRIPTORS)
    ].copy()
    if sub.empty:
        raise ValueError(
            f"No rows found for case={CASE_ID}, duration={DURATION_H:g}, descriptors={', '.join(DESCRIPTORS)}"
        )

    numeric_cols = [
        "trajectory_length",
        "mission_duration",
        "solver_runtime",
        "solver_returncode",
        "number_of_valid_cells_sampled",
        "collected_STD",
        "collected_descriptor",
        "collected_information_score",
        "percentage_path_in_top10_STD",
        "percentage_path_in_top10_descriptor",
        "trajectory_overlap_ratio_with_baseline",
        "path_difference_from_baseline",
        "regions_visited",
        "crossing_count",
        "fraction_path_region_A",
        "fraction_path_region_B",
        "regime_balance",
        "STD_retention",
        "baseline_STD",
        "baseline_runtime",
    ]
    for col in numeric_cols:
        if col in sub.columns:
            sub[col] = safe_num(sub[col])

    if "collected_information_score" in sub.columns:
        sub["total_collected_reward"] = sub["collected_information_score"]
    else:
        sub["total_collected_reward"] = sub["collected_STD"]

    if "trajectory_length" in sub.columns:
        sub["route_length_km"] = sub["trajectory_length"]
        sub["reward_per_distance_km"] = sub["total_collected_reward"] / sub["route_length_km"].replace(0, np.nan)
    else:
        sub["route_length_km"] = np.nan
        sub["reward_per_distance_km"] = np.nan

    if "STD_retention" not in sub.columns:
        baseline_std = (
            sub[sub["alpha"].eq(0)]
            .groupby("descriptor")["collected_STD"]
            .max()
            .rename("baseline_STD")
        )
        sub = sub.merge(baseline_std, on="descriptor", how="left", suffixes=("", "_computed"))
        if "baseline_STD_computed" in sub.columns:
            sub["baseline_STD"] = sub.get("baseline_STD", sub["baseline_STD_computed"]).fillna(sub["baseline_STD_computed"])
            sub = sub.drop(columns=["baseline_STD_computed"])
        sub["STD_retention"] = sub["collected_STD"] / sub["baseline_STD"].replace(0, np.nan)

    if "regime_balance" not in sub.columns:
        if {"fraction_path_region_A", "fraction_path_region_B"}.issubset(sub.columns):
            sub["regime_balance"] = 2.0 * np.minimum(
                sub["fraction_path_region_A"].fillna(0),
                sub["fraction_path_region_B"].fillna(0),
            )
        else:
            sub["regime_balance"] = np.nan

    baseline_cols = [
        "descriptor",
        "total_collected_reward",
        "collected_STD",
        "collected_descriptor",
        "route_length_km",
        "reward_per_distance_km",
        "solver_runtime",
        "percentage_path_in_top10_STD",
        "percentage_path_in_top10_descriptor",
    ]
    baseline = (
        sub[sub["alpha"].eq(0)]
        .sort_values("total_collected_reward", ascending=False)
        .drop_duplicates("descriptor")
        .loc[:, [c for c in baseline_cols if c in sub.columns]]
        .rename(columns={c: f"baseline_{c}" for c in baseline_cols if c != "descriptor"})
    )
    sub = sub.merge(baseline, on="descriptor", how="left")

    for col in [
        "total_collected_reward",
        "collected_STD",
        "collected_descriptor",
        "route_length_km",
        "reward_per_distance_km",
        "solver_runtime",
        "percentage_path_in_top10_STD",
        "percentage_path_in_top10_descriptor",
    ]:
        bcol = f"baseline_{col}"
        if col in sub.columns and bcol in sub.columns:
            sub[f"delta_{col}_vs_baseline"] = sub[col] - sub[bcol]
            sub[f"pct_{col}_vs_baseline"] = sub[col] / sub[bcol].replace(0, np.nan) - 1.0

    sub["success_flag"] = sub.get("solver_status", "").astype(str).str.upper().isin({"SUCCESS", "REUSED"})
    if "solver_returncode" in sub.columns:
        sub["success_flag"] = sub["success_flag"] & sub["solver_returncode"].fillna(0).eq(0)

    descriptor_norm = sub.groupby("descriptor")["collected_descriptor"].transform(
        lambda s: normalize_high(s).fillna(0)
    )
    top10_desc = sub.get("percentage_path_in_top10_descriptor", pd.Series(np.nan, index=sub.index)).fillna(0)
    sub["descriptor_coverage_score"] = 0.60 * top10_desc + 0.40 * descriptor_norm

    sub["efficiency_score"] = normalize_high(sub["reward_per_distance_km"]).fillna(0)
    sub["std_preservation_score"] = sub["STD_retention"].clip(lower=0, upper=1.05).fillna(0) / 1.05
    sub["route_feasibility_score"] = normalize_low(sub["route_length_km"]).fillna(0)
    sub["runtime_feasibility_score"] = normalize_low(sub["solver_runtime"]).fillna(0)
    sub["operational_feasibility_score"] = (
        0.45 * sub["route_feasibility_score"]
        + 0.45 * sub["runtime_feasibility_score"]
        + 0.10 * sub["success_flag"].astype(float)
    )
    sub["overall_rank_score"] = (
        0.30 * sub["efficiency_score"]
        + 0.25 * sub["std_preservation_score"]
        + 0.25 * sub["descriptor_coverage_score"]
        + 0.20 * sub["operational_feasibility_score"]
    )

    sub["rank_reward_efficiency"] = sub["reward_per_distance_km"].rank(ascending=False, method="min")
    sub["rank_std_preservation"] = sub["STD_retention"].rank(ascending=False, method="min")
    sub["rank_descriptor_coverage"] = sub["descriptor_coverage_score"].rank(ascending=False, method="min")
    sub["rank_operational_feasibility"] = sub["operational_feasibility_score"].rank(ascending=False, method="min")
    sub["rank_overall"] = sub["overall_rank_score"].rank(ascending=False, method="min")

    summary_cols = [
        "case_id",
        "mission_duration_requested_h",
        "descriptor",
        "alpha",
        "run_name",
        "solver_status",
        "solver_returncode",
        "success_flag",
        "total_collected_reward",
        "collected_STD",
        "collected_descriptor",
        "route_length_km",
        "reward_per_distance_km",
        "solver_runtime",
        "STD_retention",
        "percentage_path_in_top10_STD",
        "percentage_path_in_top10_descriptor",
        "number_of_valid_cells_sampled",
        "trajectory_overlap_ratio_with_baseline",
        "path_difference_from_baseline",
        "regions_visited",
        "crossing_count",
        "fraction_path_region_A",
        "fraction_path_region_B",
        "regime_balance",
        "delta_total_collected_reward_vs_baseline",
        "pct_total_collected_reward_vs_baseline",
        "delta_collected_STD_vs_baseline",
        "pct_collected_STD_vs_baseline",
        "delta_collected_descriptor_vs_baseline",
        "pct_collected_descriptor_vs_baseline",
        "delta_route_length_km_vs_baseline",
        "pct_route_length_km_vs_baseline",
        "delta_reward_per_distance_km_vs_baseline",
        "pct_reward_per_distance_km_vs_baseline",
        "descriptor_coverage_score",
        "operational_feasibility_score",
        "overall_rank_score",
        "rank_reward_efficiency",
        "rank_std_preservation",
        "rank_descriptor_coverage",
        "rank_operational_feasibility",
        "rank_overall",
        "run_dir",
        "physical_run_id",
        "information_map_formula",
    ]
    summary = sub.loc[:, [c for c in summary_cols if c in sub.columns]].sort_values(
        ["rank_overall", "descriptor", "alpha"]
    )
    return sub, summary


def diagnostics_status(summary: pd.DataFrame, diagnostics: pd.DataFrame | None) -> tuple[bool, pd.DataFrame]:
    failures = summary[~summary["success_flag"]].copy()
    if diagnostics is not None and not diagnostics.empty:
        diag = diagnostics.copy()
        for col in ["returncode", "solver_returncode"]:
            if col in diag.columns:
                diag[col] = safe_num(diag[col])
        bad = pd.Series(False, index=diag.index)
        for col in ["status", "solver_status"]:
            if col in diag.columns:
                bad = bad | ~diag[col].astype(str).str.upper().isin({"SUCCESS", "REUSED", ""})
        for col in ["returncode", "solver_returncode"]:
            if col in diag.columns:
                bad = bad | ~diag[col].fillna(0).eq(0)
        diag_bad = diag[bad].copy()
        if not diag_bad.empty:
            failures = pd.concat([failures, diag_bad], ignore_index=True, sort=False)
    return failures.empty, failures


def plot_line(df: pd.DataFrame, y: str, ylabel: str, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for descriptor, group in df.sort_values("alpha").groupby("descriptor"):
        ax.plot(group["alpha"], group[y], marker="o", linewidth=2, label=descriptor)
    ax.set_xlabel("alpha")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_plots(outdir: Path, rows: pd.DataFrame, summary: pd.DataFrame) -> list[Path]:
    plot_dir = outdir / "figures"
    plot_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        plot_dir / "step12a_alpha_vs_reward.png",
        plot_dir / "step12a_alpha_vs_route_length.png",
        plot_dir / "step12a_alpha_vs_reward_efficiency.png",
        plot_dir / "step12a_descriptor_alpha_ranking.png",
    ]
    plot_line(
        rows,
        "total_collected_reward",
        "total collected reward (objective score)",
        "Step12A alpha sensitivity: accumulated reward-map proxy",
        paths[0],
    )
    plot_line(
        rows,
        "route_length_km",
        "route length (km)",
        "Step12A alpha sensitivity: route length",
        paths[1],
    )
    plot_line(
        rows,
        "reward_per_distance_km",
        "reward per km",
        "Step12A alpha sensitivity: reward efficiency",
        paths[2],
    )
    top = summary.sort_values("overall_rank_score", ascending=False).head(15).copy()
    top["label"] = top["descriptor"].astype(str) + " a=" + top["alpha"].map(lambda x: fmt(x, 2))
    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.barh(top["label"][::-1], top["overall_rank_score"][::-1], color="#356a73")
    ax.set_xlabel("overall ranking score")
    ax.set_title("Descriptor-alpha ranking across efficiency, STD preservation, coverage, feasibility")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths[3], dpi=180)
    plt.close(fig)
    return paths


def descriptor_comparison_text(rows: pd.DataFrame, summary: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    best_by_descriptor = (
        summary[summary["alpha"].ne(0)]
        .sort_values("overall_rank_score", ascending=False)
        .drop_duplicates("descriptor")
        .sort_values("rank_overall")
    )
    for row in best_by_descriptor.itertuples(index=False):
        lines.append(
            f"- `{row.descriptor}` is best represented by alpha={fmt(row.alpha, 2)} in this run: "
            f"reward efficiency={fmt(row.reward_per_distance_km)}, STD retention={fmt(row.STD_retention)}, "
            f"descriptor coverage score={fmt(row.descriptor_coverage_score)}, route={fmt(row.route_length_km)} km, "
            f"runtime={fmt(row.solver_runtime)} s."
        )
    return lines


def boundary_radius_text(summary: pd.DataFrame) -> list[str]:
    wanted = [
        "boundary_distance_score_r1_cells",
        "boundary_distance_score_r3_cells",
        "boundary_distance_score_r5_cells",
    ]
    available = summary[summary["descriptor"].isin(wanted) & summary["alpha"].ne(0)].copy()
    if available.empty:
        return ["- Boundary-distance radius comparison could not be computed because r1/r3/r5 rows were not all available."]
    best = (
        available.sort_values("overall_rank_score", ascending=False)
        .drop_duplicates("descriptor")
        .set_index("descriptor")
    )
    lines: list[str] = []
    for descriptor in wanted:
        if descriptor in best.index:
            row = best.loc[descriptor]
            lines.append(
                f"- `{descriptor}` best alpha={fmt(row['alpha'], 2)}: overall={fmt(row['overall_rank_score'])}, "
                f"efficiency={fmt(row['reward_per_distance_km'])}, STD retention={fmt(row['STD_retention'])}, "
                f"coverage={fmt(row['descriptor_coverage_score'])}."
            )
    if "boundary_distance_score_r3_cells" in best.index:
        r3 = best.loc["boundary_distance_score_r3_cells"]
        r1 = best.loc["boundary_distance_score_r1_cells"] if "boundary_distance_score_r1_cells" in best.index else None
        r5 = best.loc["boundary_distance_score_r5_cells"] if "boundary_distance_score_r5_cells" in best.index else None
        notes = []
        if r1 is not None:
            if r1["descriptor_coverage_score"] < r3["descriptor_coverage_score"] and r1["overall_rank_score"] < r3["overall_rank_score"]:
                notes.append("r1 behaves as a narrow boundary proxy: it is less competitive on descriptor coverage and overall utility than r3.")
            else:
                notes.append("r1 does not clearly fail on coverage, but its competitiveness should be interpreted as a more localized boundary/regime signal.")
        if r5 is not None:
            if r5["overall_rank_score"] < r3["overall_rank_score"] and r5["STD_retention"] <= r3["STD_retention"]:
                notes.append("r5 looks broader but less useful operationally than r3 in this run, because it does not improve STD preservation or the overall score.")
            else:
                notes.append("r5 remains competitive, but its broader boundary band should be described as lower selectivity unless it also improves efficiency.")
        if (r1 is not None and r3["overall_rank_score"] >= r1["overall_rank_score"]) and (
            r5 is None or r3["overall_rank_score"] >= r5["overall_rank_score"]
        ):
            notes.append("r3 gives the clearest compromise among the pure boundary-distance radii for this completed run.")
        lines.extend(f"- {note}" for note in notes)
    return lines


def write_report(
    outdir: Path,
    files: dict[str, list[Path]],
    main_csv: Path,
    main_df: pd.DataFrame,
    rows: pd.DataFrame,
    summary: pd.DataFrame,
    all_succeeded: bool,
    failures: pd.DataFrame,
    plots: list[Path],
) -> Path:
    alphas = ", ".join(fmt(a, 2) for a in sorted(rows["alpha"].dropna().unique()))
    recommendation_pool = summary[summary["alpha"].ne(0)].copy()
    if recommendation_pool.empty:
        recommendation_pool = summary.copy()
    recommended = recommendation_pool.sort_values("overall_rank_score", ascending=False).iloc[0]

    coverage_cols = [
        c
        for c in [
            "percentage_path_in_top10_STD",
            "percentage_path_in_top10_descriptor",
            "number_of_valid_cells_sampled",
            "trajectory_overlap_ratio_with_baseline",
            "path_difference_from_baseline",
            "regions_visited",
            "crossing_count",
            "fraction_path_region_A",
            "fraction_path_region_B",
            "regime_balance",
        ]
        if c in rows.columns
    ]
    metric_columns = [
        "case_id",
        "mission_duration_requested_h",
        "descriptor",
        "alpha",
        "solver_status",
        "total_collected_reward",
        "collected_STD",
        "collected_descriptor",
        "route_length_km",
        "reward_per_distance_km",
        "solver_runtime",
        *coverage_cols,
    ]
    rank_columns = [
        "descriptor",
        "alpha",
        "total_collected_reward",
        "reward_per_distance_km",
        "STD_retention",
        "descriptor_coverage_score",
        "operational_feasibility_score",
        "overall_rank_score",
        "rank_reward_efficiency",
        "rank_std_preservation",
        "rank_descriptor_coverage",
        "rank_operational_feasibility",
        "rank_overall",
    ]

    rel = lambda p: str(p.relative_to(outdir)).replace("\\", "/") if p.is_relative_to(outdir) else str(p)
    lines = [
        "# Step12A boundary-distance descriptor results interpretation",
        "",
        "## Scope and input audit",
        f"- Input folder: `{outdir}`",
        f"- Main metrics CSV identified: `{main_csv.name}`.",
        f"- Main metrics shape: {len(main_df)} rows x {len(main_df.columns)} columns.",
        f"- CSV files inspected: {len(files['csv'])}. JSON/manifests inspected: {len(files['json'])}. Figure/media files found: {len(files['figures'])}.",
        f"- Filtered analysis subset: case `{CASE_ID}`, duration `{DURATION_H:g}` h, descriptors `{', '.join(DESCRIPTORS)}`, alphas `{alphas}`.",
        "",
        "## Main metrics columns",
        "The main metrics table combines the logical run definition, planner diagnostics, route outputs, accumulated reward-map proxies, and route coverage/proxy metrics. Its columns are:",
        "",
        ", ".join(f"`{col}`" for col in main_df.columns),
        "",
        "For this thesis interpretation, `collected_information_score` is treated as total collected reward, i.e. the accumulated reward-map proxy along the route. `collected_STD` is the accumulated STD/uncertainty-proxy reward, and `collected_descriptor` is the accumulated descriptor-specific proxy where available.",
        "",
        "## Planner completion check",
        f"- All filtered planner runs succeeded: `{all_succeeded}`.",
        f"- Filtered rows checked: {len(summary)}.",
    ]
    if all_succeeded:
        lines.append("- No failed runs were found in the filtered metrics/diagnostics tables.")
    else:
        lines.extend(["- Failed or suspect rows:", md_table(failures, failures.columns, 20)])

    lines.extend(
        [
            "",
            "## Extracted metrics by descriptor and alpha",
            md_table(rows.sort_values(["descriptor", "alpha"]), metric_columns, 200),
            "",
            "## Baseline comparison",
            "Each descriptor-alpha row is compared with its STD-only baseline (`alpha=0`) for the same descriptor. Positive reward/STD deltas mean the route accumulated more of that proxy than the baseline; positive route-length/runtime deltas mean higher operational cost.",
            md_table(
                summary.sort_values(["descriptor", "alpha"]),
                [
                    "descriptor",
                    "alpha",
                    "total_collected_reward",
                    "delta_total_collected_reward_vs_baseline",
                    "pct_total_collected_reward_vs_baseline",
                    "collected_STD",
                    "delta_collected_STD_vs_baseline",
                    "pct_collected_STD_vs_baseline",
                    "route_length_km",
                    "delta_route_length_km_vs_baseline",
                    "reward_per_distance_km",
                    "delta_reward_per_distance_km_vs_baseline",
                    "solver_runtime",
                ],
                200,
            ),
            "",
            "## Rankings",
            "The ranking uses four thesis-oriented criteria: reward efficiency, preservation of accumulated STD reward, descriptor/boundary coverage, and operational feasibility. The composite rank is only a decision aid; the raw columns above should remain the primary evidence.",
            md_table(summary.sort_values("rank_overall"), rank_columns, 200),
            "",
            "## Descriptor comparison",
            *descriptor_comparison_text(rows, summary),
            "",
            "## Boundary-distance radius comparison",
            *boundary_radius_text(summary),
            "",
            "## Recommended combination",
            f"The recommended non-baseline combination is `{recommended['descriptor']}` with alpha={fmt(recommended['alpha'], 2)}.",
            f"It is recommended because it gives the strongest combined balance in this run: reward efficiency={fmt(recommended['reward_per_distance_km'])}, STD retention={fmt(recommended['STD_retention'])}, descriptor/boundary coverage score={fmt(recommended['descriptor_coverage_score'])}, operational feasibility={fmt(recommended['operational_feasibility_score'])}, and overall score={fmt(recommended['overall_rank_score'])}.",
            "This should be described as a reward-map sensitivity and potential-informativeness result, not as demonstrated data-assimilation uncertainty reduction.",
            "",
            "## Thesis wording guardrails",
            "- Use: potential informativeness, accumulated uncertainty proxy, boundary/regime coverage, reward-map sensitivity, operational efficiency.",
            "- Avoid claiming actual data-assimilation uncertainty reduction, because these outputs evaluate planner reward proxies rather than a completed assimilation experiment.",
            "",
            "## Generated plots",
            *[f"- `{rel(path)}`" for path in plots],
            "",
            "## Existing diagnostics and figures inspected",
            f"- Diagnostics/log-like files found: {len(files['diagnostics'])}.",
            f"- Existing figures/media found: {len(files['figures'])}.",
        ]
    )
    report_path = outdir / OUTPUT_REPORT
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Step12A output directory")
    args = parser.parse_args()
    outdir = args.input
    if not outdir.exists():
        raise FileNotFoundError(f"Input folder does not exist: {outdir}")

    files = discover_files(outdir)
    main_csv, main_df, _missing = find_main_metrics_csv(files["csv"])
    diagnostics = load_optional_csv(outdir, "step12a_solver_diagnostics.csv")
    manifest = load_optional_csv(outdir, "step12a_run_manifest.csv")
    if manifest is not None:
        files["csv"].append(outdir / "step12a_run_manifest.csv")

    rows, summary = prepare_summary(main_df)
    all_succeeded, failures = diagnostics_status(summary, diagnostics)
    summary_path = outdir / OUTPUT_SUMMARY
    summary.to_csv(summary_path, index=False)
    plots = create_plots(outdir, rows, summary)
    report_path = write_report(
        outdir=outdir,
        files=files,
        main_csv=main_csv,
        main_df=main_df,
        rows=rows,
        summary=summary,
        all_succeeded=all_succeeded,
        failures=failures,
        plots=plots,
    )
    check = {
        "input": str(outdir),
        "main_metrics_csv": str(main_csv),
        "summary_csv": str(summary_path),
        "report": str(report_path),
        "plots": [str(p) for p in plots],
        "all_filtered_runs_succeeded": bool(all_succeeded),
        "filtered_rows": int(len(summary)),
    }
    (outdir / "step12a_boundary_distance_results_checks.json").write_text(
        json.dumps(check, indent=2), encoding="utf-8"
    )
    print(json.dumps(check, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
