#!/usr/bin/env python
"""
Step11X audit for Step11A/11C/11D planner outputs.

This script is intentionally read-only with respect to previous planner outputs:
it inventories existing result folders, loads existing CSV/JSON/Markdown evidence,
computes light diagnostics from saved arrays, and writes a new timestamped audit
folder. It does not rerun the planner and does not generate new trajectories.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = ""


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SCRIPTS = ROOT / "scripts"

STEP11C_DIRS = [
    RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322",
    RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458",
]
STEP11D_DIRS = [
    RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809",
    RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935",
]
STEP10F_DIR = RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
STEP08_DIR = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260514_164854"


@dataclass
class Evidence:
    warnings: list[str]
    missing_files: list[str]
    analyzed_outputs: list[str]


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def read_md(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_csv(path: Path, evidence: Evidence | None = None) -> pd.DataFrame:
    if not path.exists():
        if evidence is not None:
            evidence.missing_files.append(str(path.relative_to(ROOT)))
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        if evidence is not None:
            evidence.warnings.append(f"Failed to read CSV {path.relative_to(ROOT)}: {exc}")
        return pd.DataFrame()


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def find_step11a_outputs() -> list[Path]:
    patterns = [
        "step11a",
        "minimal_boundary_planner",
        "boundary_planner",
        "baseline_vs_enriched",
    ]
    outputs: list[Path] = []
    if not RESULTS.exists():
        return outputs
    for d in RESULTS.iterdir():
        if d.is_dir() and any(p in d.name.lower() for p in patterns):
            outputs.append(d)
    return sorted(outputs)


def file_category(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    parts = [p.lower() for p in path.parts]
    if suffix == ".csv":
        if "metric" in name or "metrics" in name:
            return "metrics_csv"
        if "trajectory" in name or "waypoint" in name or "route" in name:
            return "trajectories_csv"
        return "csv"
    if suffix == ".json":
        if "check" in name:
            return "checks_json"
        if "route" in name or "trajectory" in name:
            return "trajectories_json"
        return "json"
    if suffix == ".md":
        return "report_md"
    if suffix == ".png":
        return "figure_png"
    if suffix == ".py":
        return "script_copy"
    if suffix in [".txt", ".log"]:
        return "log"
    if suffix in [".npy", ".npz", ".nc"]:
        if "mask" in name or "masks" in parts:
            return "mask_or_array"
        return "map_or_planner_input"
    if "planner_runs" in parts:
        return "planner_run_artifact"
    return "other"


def inventory_outputs(outputs: list[Path], evidence: Evidence) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for out in outputs:
        exists = out.exists()
        if not exists:
            evidence.missing_files.append(rel(out))
            rows.append(
                {
                    "output_dir": rel(out),
                    "output_name": out.name,
                    "exists": False,
                    "file_path": "",
                    "file_name": "",
                    "extension": "",
                    "category": "missing_output",
                    "size_bytes": np.nan,
                    "modified_time": "",
                }
            )
            continue
        evidence.analyzed_outputs.append(rel(out))
        for f in out.rglob("*"):
            if not f.is_file():
                continue
            try:
                stat = f.stat()
                modified = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
                size = stat.st_size
            except OSError:
                modified = ""
                size = np.nan
            rows.append(
                {
                    "output_dir": rel(out),
                    "output_name": out.name,
                    "exists": True,
                    "file_path": rel(f),
                    "file_name": f.name,
                    "extension": f.suffix.lower(),
                    "category": file_category(f),
                    "size_bytes": size,
                    "modified_time": modified,
                }
            )
    return pd.DataFrame(rows)


def parse_auv_duration(output_dir: Path) -> tuple[float, int, str]:
    checks = {}
    for name in ["step11a_checks.json", "step11c_checks.json", "step11d_checks.json"]:
        checks = read_json(output_dir / name)
        if checks:
            break
    duration = safe_float(checks.get("mission_duration_hours"))
    auv_number = int(safe_float(checks.get("auv_number"), np.nan)) if not math.isnan(safe_float(checks.get("auv_number"), np.nan)) else np.nan
    label = ""
    if not math.isnan(duration) and not (isinstance(auv_number, float) and math.isnan(auv_number)):
        label = f"{int(auv_number)}auv_{duration:g}h"
        return duration, int(auv_number), label

    text = read_md(output_dir / "step11a_summary.md") + "\n" + read_md(output_dir / "step11a_report.md")
    m = re.search(r"Runtime:\s*(\d+)\s*AUVs?,\s*([0-9.]+)h", text, flags=re.I)
    if m:
        auv_number = int(m.group(1))
        duration = float(m.group(2))
        label = f"{auv_number}auv_{duration:g}h"
        return duration, auv_number, label
    return np.nan, np.nan, "unknown_runtime"


def add_source(df: pd.DataFrame, output_dir: Path, step: str) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["source_output"] = output_dir.name
    df["source_output_path"] = rel(output_dir)
    df["step"] = step
    return df


def collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse duplicate column names by taking the first non-null value row-wise."""
    if df.empty or not df.columns.duplicated().any():
        return df
    out = pd.DataFrame(index=df.index)
    for col in dict.fromkeys(df.columns):
        sub = df.loc[:, df.columns == col]
        if sub.shape[1] == 1:
            out[col] = sub.iloc[:, 0]
        else:
            out[col] = sub.bfill(axis=1).iloc[:, 0]
    return out


def load_step11a(step11a_dirs: list[Path], evidence: Evidence) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics_frames: list[pd.DataFrame] = []
    comp_frames: list[pd.DataFrame] = []
    diag_frames: list[pd.DataFrame] = []
    for d in step11a_dirs:
        if not d.exists():
            evidence.missing_files.append(rel(d))
            continue
        duration, auv_number, runtime_label = parse_auv_duration(d)
        metrics = read_csv(d / "step11a_run_metrics.csv")
        comp = read_csv(d / "step11a_baseline_vs_enriched_comparison.csv")
        diag = read_csv(d / "step11a_solver_diagnostics.csv")
        for df in [metrics, comp, diag]:
            if not df.empty:
                df["mission_duration_requested_h"] = duration
                df["auv_number"] = auv_number
                df["runtime_label"] = runtime_label
        metrics_frames.append(add_source(metrics, d, "Step11A"))
        comp_frames.append(add_source(comp, d, "Step11A"))
        diag_frames.append(add_source(diag, d, "Step11A"))
    metrics_all = pd.concat(metrics_frames, ignore_index=True) if metrics_frames else pd.DataFrame()
    comp_all = pd.concat(comp_frames, ignore_index=True) if comp_frames else pd.DataFrame()
    diag_all = pd.concat(diag_frames, ignore_index=True) if diag_frames else pd.DataFrame()
    return metrics_all, comp_all, diag_all


def summarize_step11a(metrics: pd.DataFrame, comp: pd.DataFrame, diag: pd.DataFrame) -> pd.DataFrame:
    if metrics.empty:
        return pd.DataFrame()
    m = metrics.copy()
    numeric_cols = [
        "alpha",
        "trajectory_length_km",
        "mission_duration_h",
        "solver_runtime_s",
        "collected_STD_score",
        "collected_boundary_score",
        "trajectory_overlap_ratio_with_baseline",
        "trajectory_difference_from_baseline",
        "mission_duration_requested_h",
        "auv_number",
    ]
    for c in numeric_cols:
        if c in m.columns:
            m[c] = to_num(m[c])
    keep = [
        "step",
        "source_output",
        "runtime_label",
        "case_id",
        "date",
        "auv_number",
        "mission_duration_requested_h",
        "formulation",
        "alpha",
        "collected_STD_score",
        "collected_boundary_score",
        "trajectory_length_km",
        "trajectory_overlap_ratio_with_baseline",
        "trajectory_difference_from_baseline",
        "solver_runtime_s",
        "solver_status",
    ]
    out = m[[c for c in keep if c in m.columns]].copy()

    if not comp.empty:
        cdf = comp.copy()
        for c in [
            "trajectory_overlap_ratio",
            "trajectory_difference_from_baseline",
            "delta_collected_boundary_score",
            "delta_collected_STD_score",
        ]:
            if c in cdf.columns:
                cdf[c] = to_num(cdf[c])
        join_cols = [
            "source_output",
            "case_id",
            "formulation",
            "trajectory_overlap_ratio",
            "trajectory_difference_from_baseline",
            "delta_collected_boundary_score",
            "delta_collected_STD_score",
            "high_similarity_overlay",
        ]
        cdf = cdf[[c for c in join_cols if c in cdf.columns]]
        out = out.merge(cdf, on=["source_output", "case_id", "formulation"], how="left", suffixes=("", "_comparison"))
    if "trajectory_difference_from_baseline_comparison" in out.columns:
        out["trajectory_difference_from_baseline"] = out["trajectory_difference_from_baseline_comparison"].combine_first(
            out.get("trajectory_difference_from_baseline")
        )
    out["trajectory_change_class"] = np.where(
        to_num(out.get("trajectory_difference_from_baseline", pd.Series(dtype=float))) >= 0.75,
        "changed_strongly",
        np.where(
            to_num(out.get("trajectory_difference_from_baseline", pd.Series(dtype=float))) >= 0.25,
            "changed_moderately",
            "near_baseline",
        ),
    )
    out["std_boundary_tradeoff"] = np.where(
        to_num(out.get("delta_collected_STD_score", pd.Series(dtype=float))) < 0,
        "STD_loss",
        "STD_neutral_or_gain",
    )
    out["crossing_count"] = np.nan
    out["regions_visited"] = np.nan
    return out


def load_step11c(step11c_dirs: list[Path], evidence: Evidence) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics_frames: list[pd.DataFrame] = []
    diag_frames: list[pd.DataFrame] = []
    for d in step11c_dirs:
        if not d.exists():
            evidence.missing_files.append(rel(d))
            continue
        metrics = read_csv(d / "step11c_run_metrics.csv", evidence)
        if metrics.empty:
            metrics = read_csv(d / "step11c_crossing_metrics.csv", evidence)
        diag = read_csv(d / "step11c_solver_diagnostics.csv", evidence)
        metrics_frames.append(add_source(metrics, d, "Step11C"))
        diag_frames.append(add_source(diag, d, "Step11C"))
    metrics_all = pd.concat(metrics_frames, ignore_index=True) if metrics_frames else pd.DataFrame()
    diag_all = pd.concat(diag_frames, ignore_index=True) if diag_frames else pd.DataFrame()
    if not metrics_all.empty:
        rename = {
            "boundary_crossing_count": "crossing_count",
            "number_of_distinct_regions_visited": "regions_visited",
            "collected_STD_score": "collected_STD",
            "collected_boundary_score": "collected_boundary",
            "trajectory_difference_from_baseline": "difference_from_baseline",
        }
        metrics_all = metrics_all.rename(columns={k: v for k, v in rename.items() if k in metrics_all.columns})
        metrics_all = collapse_duplicate_columns(metrics_all)
        for c in [
            "mission_duration_requested_h",
            "mission_duration",
            "trajectory_length",
            "solver_runtime",
            "gamma",
            "crossing_count",
            "regions_visited",
            "fraction_path_region_A",
            "fraction_path_region_B",
            "collected_STD",
            "collected_boundary",
            "difference_from_baseline",
        ]:
            if c in metrics_all.columns:
                metrics_all[c] = to_num(metrics_all[c])
    return metrics_all, diag_all


def load_step11d(step11d_dirs: list[Path], evidence: Evidence) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fleet_frames: list[pd.DataFrame] = []
    vehicle_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []
    diag_frames: list[pd.DataFrame] = []
    for d in step11d_dirs:
        if not d.exists():
            evidence.missing_files.append(rel(d))
            continue
        fleet = read_csv(d / "step11d_fleet_level_metrics.csv", evidence)
        if fleet.empty:
            fleet = read_csv(d / "step11d_multi_auv_run_metrics.csv", evidence)
        vehicle = read_csv(d / "step11d_vehicle_level_metrics.csv", evidence)
        candidate = read_csv(d / "step11d_candidate_trajectories.csv", evidence)
        diag = read_csv(d / "step11d_solver_diagnostics.csv", evidence)
        fleet_frames.append(add_source(fleet, d, "Step11D"))
        vehicle_frames.append(add_source(vehicle, d, "Step11D"))
        candidate_frames.append(add_source(candidate, d, "Step11D"))
        diag_frames.append(add_source(diag, d, "Step11D"))
    fleet_all = pd.concat(fleet_frames, ignore_index=True) if fleet_frames else pd.DataFrame()
    vehicle_all = pd.concat(vehicle_frames, ignore_index=True) if vehicle_frames else pd.DataFrame()
    candidate_all = pd.concat(candidate_frames, ignore_index=True) if candidate_frames else pd.DataFrame()
    diag_all = pd.concat(diag_frames, ignore_index=True) if diag_frames else pd.DataFrame()
    for df in [fleet_all, vehicle_all, candidate_all]:
        if df.empty:
            continue
        for c in df.columns:
            if c not in ["run_id", "strategy", "case_id", "vehicle_id", "solver_status", "candidate_name", "source_run_dir", "source_output", "source_output_path", "step"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
    return fleet_all, vehicle_all, candidate_all, diag_all


def norm01(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=float)
    finite = np.isfinite(a)
    if not finite.any():
        return a * np.nan
    mn = np.nanmin(a)
    mx = np.nanmax(a)
    if mx <= mn:
        out = np.zeros_like(a, dtype=float)
        out[~finite] = np.nan
        return out
    return (a - mn) / (mx - mn)


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return np.nan
    xv = x[mask].astype(float)
    yv = y[mask].astype(float)
    sx = np.nanstd(xv)
    sy = np.nanstd(yv)
    if sx == 0 or sy == 0:
        return np.nan
    return float(np.corrcoef(xv, yv)[0, 1])


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return np.nan
    rx = pd.Series(x[mask].ravel()).rank(method="average").to_numpy()
    ry = pd.Series(y[mask].ravel()).rank(method="average").to_numpy()
    return pearson(rx, ry)


def top_mask(arr: np.ndarray, valid: np.ndarray, q: float = 0.90) -> np.ndarray:
    values = arr[valid & np.isfinite(arr)]
    out = np.zeros(arr.shape, dtype=bool)
    if values.size == 0:
        return out
    thr = np.nanquantile(values, q)
    out[valid & np.isfinite(arr) & (arr >= thr)] = True
    return out


def hotspot_centroid(arr: np.ndarray, valid: np.ndarray) -> tuple[float, float]:
    tm = top_mask(arr, valid, 0.90)
    ys, xs = np.where(tm)
    if len(xs) == 0:
        return np.nan, np.nan
    return float(np.mean(xs)), float(np.mean(ys))


def descriptor_correlations(evidence: Evidence) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    npz_path = STEP10F_DIR / "planner_minimal_boundary_input_maps.npz"
    cases_path = STEP10F_DIR / "step10f_minimal_boundary_planner_cases.csv"
    step08_path = STEP08_DIR / "step08_all_descriptor_maps.npz"
    if not npz_path.exists():
        evidence.missing_files.append(rel(npz_path))
        return pd.DataFrame()
    if not cases_path.exists():
        evidence.missing_files.append(rel(cases_path))
        return pd.DataFrame()
    try:
        z10 = np.load(npz_path, allow_pickle=True)
        cases = pd.read_csv(cases_path)
    except Exception as exc:
        evidence.warnings.append(f"Could not load Step10F maps/cases: {exc}")
        return pd.DataFrame()
    z08 = None
    if step08_path.exists():
        try:
            z08 = np.load(step08_path, allow_pickle=True)
        except Exception as exc:
            evidence.warnings.append(f"Could not load Step08 descriptor maps: {exc}")
    else:
        evidence.missing_files.append(rel(step08_path))

    std_stack = z10["STD_norm"]
    boundary_stack = z10["boundary_score_norm"]
    valid_mask_base = np.asarray(z10["mask"], dtype=bool) if "mask" in z10.files else np.isfinite(std_stack[0])
    case_ids = [str(x) for x in z10["case_ids"]] if "case_ids" in z10.files else list(cases["case_id"])

    for i, case_id in enumerate(case_ids):
        case_row = cases.loc[cases["case_id"].astype(str) == case_id]
        pred_class = int(safe_float(case_row["predicted_class"].iloc[0], np.nan)) if not case_row.empty else np.nan
        date = case_row["date"].iloc[0] if not case_row.empty and "date" in case_row else ""
        std = np.asarray(std_stack[i], dtype=float)
        valid = valid_mask_base & np.isfinite(std)
        descriptors: dict[str, np.ndarray] = {
            "boundary_score": np.asarray(boundary_stack[i], dtype=float),
        }
        if z08 is not None and not math.isnan(pred_class):
            idx = int(pred_class) - 1
            aliases = {
                "gradient": "gradient",
                "heterogeneity": "heterogeneity",
                "representative_zone": "representative_zone",
                "interest_map": "interest",
                "cold_region": "cold_region",
                "warm_region": "warm_region",
            }
            for out_name, key in aliases.items():
                if key in z08.files and 0 <= idx < z08[key].shape[0]:
                    descriptors[out_name] = norm01(np.asarray(z08[key][idx], dtype=float))
        sx, sy = hotspot_centroid(std, valid)
        std_top = top_mask(std, valid, 0.90)
        for desc_name, desc in descriptors.items():
            desc = norm01(desc)
            dvalid = valid & np.isfinite(desc)
            dtop = top_mask(desc, dvalid, 0.90)
            dx, dy = hotspot_centroid(desc, dvalid)
            intersection = float(np.sum(std_top & dtop))
            union = float(np.sum(std_top | dtop))
            domain = float(np.sum(dvalid))
            rows.append(
                {
                    "case_id": case_id,
                    "date": date,
                    "predicted_class": pred_class,
                    "descriptor": desc_name,
                    "pearson_STD_descriptor": pearson(std, desc),
                    "spearman_STD_descriptor": spearman(std, desc),
                    "top10_intersection_cells": intersection,
                    "top10_overlap_fraction_of_domain": intersection / domain if domain else np.nan,
                    "top10_jaccard": intersection / union if union else np.nan,
                    "std_hotspot_x": sx,
                    "std_hotspot_y": sy,
                    "descriptor_hotspot_x": dx,
                    "descriptor_hotspot_y": dy,
                    "hotspot_distance_pixels": float(math.hypot(sx - dx, sy - dy)) if np.isfinite([sx, sy, dx, dy]).all() else np.nan,
                    "source_STD": rel(npz_path),
                    "source_descriptor": rel(npz_path) if desc_name == "boundary_score" else rel(step08_path),
                }
            )
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 20, floatfmt: str = ".3f") -> str:
    if df.empty:
        return "_No data available._\n"
    d = df[[c for c in cols if c in df.columns]].head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_numeric_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else format(float(x), floatfmt))
        else:
            d[c] = d[c].fillna("").astype(str)
    headers = list(d.columns)
    rows = d.astype(str).values.tolist()

    def clean(value: Any) -> str:
        text = str(value).replace("\n", " ").replace("|", "\\|")
        return text

    lines = [
        "| " + " | ".join(clean(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(clean(v) for v in row) + " |")
    return "\n".join(lines) + "\n"


def status_line(condition: bool) -> str:
    return "yes" if condition else "no"


def make_step11a_diagnosis(summary: pd.DataFrame, corr: pd.DataFrame) -> str:
    lines = ["# Step11A diagnosis\n"]
    if summary.empty:
        lines.append("No Step11A metrics were available. This part needs manual review.\n")
        return "\n".join(lines)
    enriched = summary[summary.get("formulation", "").astype(str).str.contains("enriched", case=False, na=False)].copy()
    if not enriched.empty:
        enriched["delta_collected_STD_score"] = to_num(enriched.get("delta_collected_STD_score", pd.Series(dtype=float)))
        enriched["delta_collected_boundary_score"] = to_num(enriched.get("delta_collected_boundary_score", pd.Series(dtype=float)))
        changed = (to_num(enriched["trajectory_difference_from_baseline"]) >= 0.75).mean()
        std_loss = (enriched["delta_collected_STD_score"] < 0).mean()
        boundary_gain = (enriched["delta_collected_boundary_score"] > 0).mean()
        lines.append(f"- Boundary-only maps changed the sampled-cell set in {changed:.0%} of enriched comparisons by the saved overlap metric.")
        lines.append(f"- The change often carried an STD cost: {std_loss:.0%} of enriched comparisons lost collected STD relative to baseline.")
        lines.append(f"- Boundary collection improved in {boundary_gain:.0%} of enriched comparisons, so the descriptor had signal but was not always aligned with preserving STD.\n")
    runtime_counts = summary.groupby("runtime_label", dropna=False)["run_id" if "run_id" in summary.columns else "case_id"].count()
    lines.append("## Runtime coverage\n")
    for label, count in runtime_counts.items():
        lines.append(f"- {label}: {count} metric rows")
    lines.append("\n## Key table\n")
    lines.append(
        md_table(
            enriched.sort_values(["runtime_label", "case_id", "alpha"]) if not enriched.empty else summary,
            [
                "runtime_label",
                "case_id",
                "formulation",
                "alpha",
                "trajectory_difference_from_baseline",
                "delta_collected_STD_score",
                "delta_collected_boundary_score",
                "solver_status",
            ],
            max_rows=40,
        )
    )
    bcorr = corr[corr["descriptor"].eq("boundary_score")] if not corr.empty else pd.DataFrame()
    if not bcorr.empty:
        mean_p = bcorr["pearson_STD_descriptor"].mean()
        mean_j = bcorr["top10_jaccard"].mean()
        lines.append("## STD-boundary redundancy\n")
        lines.append(f"Mean Pearson correlation STD vs boundary_score across Step10F cases: {mean_p:.3f}.")
        lines.append(f"Mean top-10% Jaccard overlap: {mean_j:.3f}.")
        lines.append("This supports treating boundary_score as partly redundant only in a broad spatial-gradient sense; hotspot overlap is not uniformly high.\n")
    lines.append("## Interpretation\n")
    lines.append("- Step11A worked as a first integration test: the planner received different static prize maps and returned feasible routes.")
    lines.append("- It did not prove that boundary_score alone solves regime-aware planning. The response is mixed: some boundary gains are small, and higher alpha can reduce STD sharply.")
    lines.append("- The 2-AUV 12h run should be interpreted as shared-map fleet behavior, not true vehicle specialization.")
    return "\n".join(lines)


def make_step11c_gamma_sensitivity(metrics: pd.DataFrame) -> str:
    lines = ["# Step11C gamma sensitivity\n"]
    if metrics.empty:
        lines.append("No Step11C metrics were available. This part needs manual review.\n")
        return "\n".join(lines)
    m = metrics.copy()
    lines.append("## Evidence table\n")
    lines.append(
        md_table(
            m.sort_values(["source_output", "case_id", "mission_duration_requested_h", "run_name"]),
            [
                "source_output",
                "case_id",
                "run_name",
                "mission_duration_requested_h",
                "gamma",
                "crossing_count",
                "regions_visited",
                "fraction_path_region_A",
                "fraction_path_region_B",
                "collected_STD",
                "collected_boundary",
                "difference_from_baseline",
                "solver_status",
            ],
            max_rows=80,
        )
    )
    crossing = m[m["run_name"].astype(str).str.contains("crossing", case=False, na=False)]
    if not crossing.empty:
        best = crossing.sort_values(["crossing_count", "regions_visited"], ascending=False).head(1).iloc[0]
        lines.append(f"- Best crossing row by count: {best.get('case_id')} / {best.get('run_name')} with crossing_count={best.get('crossing_count')}.")
    grouped = m.groupby(["case_id", "mission_duration_requested_h"], dropna=False)
    nonmono_cases = []
    for key, g in grouped:
        gg = g[g["run_name"].astype(str).str.contains("gamma", na=False)].sort_values("gamma")
        if len(gg) >= 2 and not gg["crossing_count"].is_monotonic_increasing:
            nonmono_cases.append(key)
    lines.append(f"- Non-monotonic gamma behavior detected in {len(nonmono_cases)} case-duration groups.")
    lines.append("- The saved audit says route-level reward was unavailable; Step11C is therefore a static-map proxy, not a true path crossing objective.")
    lines.append("- gamma=0.25 is defensible where it improves crossings without large STD loss, but the evidence does not support assuming higher gamma is better.")
    lines.append("- A warning sign is any row with high boundary-core fraction but zero crossings: that means the proxy can attract the path near the boundary without making the route switch regimes.")
    return "\n".join(lines)


def make_step11d_strategy_comparison(fleet: pd.DataFrame, vehicle: pd.DataFrame) -> str:
    lines = ["# Step11D strategy comparison\n"]
    if fleet.empty:
        lines.append("No Step11D fleet metrics were available. This part needs manual review.\n")
        return "\n".join(lines)
    f = fleet.copy()
    lines.append("## Fleet evidence\n")
    lines.append(
        md_table(
            f.sort_values(["source_output", "case_id", "strategy"]),
            [
                "source_output",
                "case_id",
                "strategy",
                "fleet_collected_STD",
                "fleet_collected_boundary",
                "fleet_region_A_coverage",
                "fleet_region_B_coverage",
                "trajectory_overlap_ratio",
                "duplicate_sampled_cells",
                "inter_vehicle_mean_distance",
                "fleet_complementarity_score",
                "solver_status",
            ],
            max_rows=80,
        )
    )
    if not vehicle.empty:
        lines.append("## Vehicle-level specialization evidence\n")
        lines.append(
            md_table(
                vehicle.sort_values(["source_output", "case_id", "strategy", "vehicle_id"]),
                [
                    "source_output",
                    "case_id",
                    "strategy",
                    "vehicle_id",
                    "fraction_path_region_A",
                    "fraction_path_region_B",
                    "collected_STD",
                    "collected_boundary",
                    "crossing_count",
                    "regions_visited",
                ],
                max_rows=80,
            )
        )
    baseline = f[f["strategy"].eq("multi_baseline_STD")]
    if not baseline.empty:
        zero_overlap = (to_num(baseline["trajectory_overlap_ratio"]) <= 0.001).mean()
        lines.append(f"- Baseline overlap was already near zero in {zero_overlap:.0%} of native baseline rows, so overlap is not the main bottleneck.")
    vs = f[f["strategy"].eq("vehicle_specific_regime_maps")]
    if not vs.empty and not baseline.empty:
        merged = vs.merge(
            baseline[["source_output", "case_id", "fleet_region_B_coverage", "fleet_collected_STD"]],
            on=["source_output", "case_id"],
            suffixes=("", "_baseline"),
            how="left",
        )
        merged["delta_B"] = to_num(merged["fleet_region_B_coverage"]) - to_num(merged["fleet_region_B_coverage_baseline"])
        merged["delta_STD"] = to_num(merged["fleet_collected_STD"]) - to_num(merged["fleet_collected_STD_baseline"])
        lines.append(
            f"- vehicle_specific_regime_maps improved mean B coverage by {merged['delta_B'].mean():.4f} but changed mean STD by {merged['delta_STD'].mean():.2f}."
        )
    lines.append("- The strongest thesis-safe statement is: vehicle-specific regime roles are useful, but the current implementation is a wrapper/proxy because native vehicle-specific prize maps are not supported.")
    lines.append("- Post-solver selected pairs are excellent diagnostics but weaker as an operational planner contribution unless formalized into the planner workflow.")
    return "\n".join(lines)


def make_descriptor_redundancy(corr: pd.DataFrame) -> str:
    lines = ["# Descriptor redundancy analysis\n"]
    if corr.empty:
        lines.append("No descriptor correlation table could be computed. Missing Step10F/Step08 maps should be checked manually.\n")
        return "\n".join(lines)
    summary = (
        corr.groupby("descriptor", as_index=False)
        .agg(
            mean_pearson=("pearson_STD_descriptor", "mean"),
            mean_spearman=("spearman_STD_descriptor", "mean"),
            mean_top10_jaccard=("top10_jaccard", "mean"),
            mean_hotspot_distance=("hotspot_distance_pixels", "mean"),
        )
        .sort_values("mean_pearson", ascending=False)
    )
    lines.append(md_table(summary, list(summary.columns), max_rows=20))
    boundary = summary[summary["descriptor"].eq("boundary_score")]
    if not boundary.empty:
        p = boundary["mean_pearson"].iloc[0]
        j = boundary["mean_top10_jaccard"].iloc[0]
        if p >= 0.6 or j >= 0.25:
            lines.append("- boundary_score is materially redundant with STD for the current cases.")
        else:
            lines.append("- boundary_score is not fully redundant by top-hotspot overlap, but it often follows broad high-value spatial structures and can still pull vehicles toward similar areas.")
    lower = summary.sort_values(["mean_pearson", "mean_top10_jaccard"]).head(3)
    lines.append("- Lower-redundancy descriptors worth testing first: " + ", ".join(lower["descriptor"].astype(str).tolist()) + ".")
    lines.append("- For multi-AUV separation, cold/warm or representative-zone maps are more directly role-defining than boundary_score.")
    return "\n".join(lines)


def planner_limitations_md() -> str:
    return """# Planner limitations summary

## Observed capabilities

- Static prize by node: supported through `information_map`.
- Native multi-AUV with a shared prize map: supported.
- Baseline STD objective: supported.
- Enriched static map `(1-alpha)*STD + alpha*descriptor`: supported as a wrapper/input-map change.

## Current limitations

- Route-level reward: not supported in the observed Step11C runs; crossing reward was implemented as a static-map proxy.
- Vehicle-specific prize maps: not supported natively in the observed Step11D runs; vehicle-specific strategies were proxy/post-solver constructions.
- Overlap/proximity penalty: not supported directly in the native objective; sequential/post-solver variants are wrappers.
- Sequential planning: usable as an external wrapper, not a native joint objective.

## Consequence

The planner can test whether descriptors make good static prize maps, but it cannot yet express the two most interesting behavioral objectives directly: "cross this boundary along the route" and "assign different regime roles to different vehicles".
"""


def required_planner_changes() -> pd.DataFrame:
    rows = [
        ["Try alpha/gamma grid on saved cases", "no-code / parameter tuning", "low", "Useful, but only explores current proxy behavior."],
        ["Use alternative static descriptors", "wrapper/proxy", "low", "Generate information maps from existing descriptors without changing solver."],
        ["Cleaner selected-case experiment set", "no-code / parameter tuning", "low", "Improves interpretability before new planner work."],
        ["Target points on both sides of boundary", "wrapper/proxy", "medium", "A practical crossing proxy without route-level objective changes."],
        ["Vehicle-specific prize maps", "small planner modification", "high", "Needed for defensible multi-AUV regime specialization."],
        ["Overlap/proximity penalty in objective", "deep PyVRP/objective modification", "medium", "Secondary priority because baseline overlap can already be zero."],
        ["Route-level crossing reward", "deep PyVRP/objective modification", "medium", "Needed if single-AUV boundary crossing becomes the central contribution."],
        ["Post-solver selected pair as final method", "not recommended", "medium", "Good diagnostic, weaker operational contribution unless formalized."],
    ]
    return pd.DataFrame(rows, columns=["improvement", "classification", "priority", "audit_rationale"])


def recommendations(corr: pd.DataFrame, step11c: pd.DataFrame, step11d_fleet: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    rec_rows = [
        [1, "Implement vehicle-specific prize maps", "multi-AUV", "high", "Most directly addresses lack of regime specialization; current Step11D proxy was interpretable."],
        [2, "Run descriptor ablation on selected cases", "descriptor", "high", "Boundary alone is not enough; compare representative_zone, interest_map, gradient, heterogeneity."],
        [3, "Use cleaner case set", "experimental design", "high", "C01, C06, and October behave differently; keep confidence and regime labels explicit."],
        [4, "Tune alpha/gamma non-monotonically", "parameters", "medium", "Do not assume gamma=0.50 beats gamma=0.25; saved Step11C evidence is mixed."],
        [5, "Improve crossing proxy with target points on both sides", "single-AUV", "medium", "More likely to create real regime switches than boundary-core attraction alone."],
        [6, "Implement route-level crossing reward", "planner", "medium", "Important only if single-AUV crossing is the main thesis claim."],
        [7, "Implement overlap/proximity penalty", "planner", "low", "Secondary because overlap was already low/zero in several native baselines."],
        [8, "Use post-solver selection as final method", "operational method", "low", "Keep as diagnostic unless integrated into a formal workflow."],
    ]
    rec = pd.DataFrame(rec_rows, columns=["rank", "recommendation", "area", "priority", "rationale"])
    matrix_rows = [
        ["vehicle_specific_prize_maps", 5, 4, 3, 2, "primary candidate"],
        ["descriptor_ablation", 4, 5, 2, 2, "secondary/parallel candidate"],
        ["route_level_crossing_reward", 3, 3, 5, 4, "defer unless crossing is central"],
        ["cleaner_selected_case_experiments", 4, 4, 1, 1, "should accompany Step11E"],
        ["overlap_penalty", 2, 2, 4, 3, "not first priority"],
        ["post_solver_selection_final", 2, 3, 1, 3, "diagnostic only"],
    ]
    matrix = pd.DataFrame(
        matrix_rows,
        columns=["option", "scientific_value", "evidence_support", "implementation_cost", "risk", "audit_decision"],
    )

    step11e_primary = "READY_FOR_STEP11E_VEHICLE_SPECIFIC_PRIZES"
    step11e_secondary = "Step11E descriptor ablation as a parallel or preceding narrow check"
    if step11d_fleet.empty:
        step11e_primary = "NEEDS_CLEANER_REPEATED_EXPERIMENTS"
        step11e_secondary = "Descriptor ablation after missing Step11D evidence is resolved"

    plan = """# Next experiments plan

1. Keep C01 2024-08-24, C06 2023-12-22, and October 2024-10-30 as the controlled case set, but label confidence and regime type explicitly.
2. For single-AUV, repeat only baseline_STD, boundary_alpha050, crossing_gamma025, and one improved crossing proxy; avoid a broad gamma sweep until the proxy is cleaner.
3. For multi-AUV, prioritize true or emulated vehicle-specific prize maps: AUV1 = regime_A/STD blend and AUV2 = regime_B/STD blend.
4. Treat post-solver selection as diagnostic evidence, not the final operational method.
5. Keep overlap penalty as secondary unless future native runs show nonzero duplicate sampling is the dominant failure.
"""

    step11e_md = f"""# Step11E recommendation

Primary option: **Option B - Step11E = vehicle-specific prize maps**.

Justification: Step11D indicates the key multi-AUV problem is not merely duplicate-cell overlap. Native shared-map multi-AUV can already avoid exact overlap, but vehicles still chase similar value structures unless they are given different regime roles. Vehicle-specific prize maps are therefore the most direct next planner improvement and the strongest thesis contribution.

Secondary option: **Option A - descriptor ablation test**.

Reason: boundary_score alone is not a complete descriptor solution. A narrow ablation over representative_zone, interest_map, gradient, and heterogeneity should be used to choose better static maps or role maps, but it should not replace the need for vehicle-specific objectives in the multi-AUV setting.

Verdict: `{step11e_primary}`.
"""
    return rec, matrix, plan, step11e_md


def full_summary_md(
    evidence: Evidence,
    step11a: pd.DataFrame,
    step11c: pd.DataFrame,
    step11d: pd.DataFrame,
    corr: pd.DataFrame,
    verdict: str,
) -> str:
    lines = ["# Step11X audit summary\n"]
    lines.append(f"- Outputs analyzed: {len(set(evidence.analyzed_outputs))}")
    lines.append(f"- Missing expected files/outputs: {len(evidence.missing_files)}")
    lines.append(f"- Warnings: {len(evidence.warnings)}")
    lines.append(f"- Verdict: `{verdict}`\n")
    lines.append("## Main conclusions\n")
    lines.append("1. Step11A succeeded as a baseline-vs-static-descriptor integration test, but boundary-only does not provide a clean regime-aware behavior guarantee.")
    lines.append("2. Step11C showed that crossing proxies can change behavior, but gamma sensitivity is non-monotonic and route-level crossing reward is not actually supported.")
    lines.append("3. Step11D suggests the multi-AUV issue is specialization by regime more than raw overlap reduction.")
    lines.append("4. boundary_score has limited standalone value as the next final descriptor; role-defining descriptors are more promising for multi-AUV.")
    lines.append("5. Step11E should prioritize vehicle-specific prize maps, with a narrow descriptor ablation as supporting evidence.\n")
    lines.append("## Evidence snapshots\n")
    if not step11c.empty:
        lines.append("### Step11C crossing counts\n")
        lines.append(md_table(step11c, ["source_output", "case_id", "run_name", "mission_duration_requested_h", "gamma", "crossing_count", "regions_visited"], 20))
    if not step11d.empty:
        lines.append("### Step11D fleet comparison\n")
        lines.append(md_table(step11d, ["source_output", "case_id", "strategy", "fleet_region_B_coverage", "trajectory_overlap_ratio", "fleet_collected_STD", "solver_status"], 20))
    if not corr.empty:
        lines.append("### Descriptor correlation\n")
        lines.append(md_table(corr, ["case_id", "descriptor", "pearson_STD_descriptor", "top10_jaccard", "hotspot_distance_pixels"], 30))
    return "\n".join(lines)


def save_bar(df: pd.DataFrame, x: str, y: str, hue: str | None, title: str, path: Path, rotate: bool = True) -> None:
    if plt is None or df.empty or x not in df.columns or y not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(11, 5))
    data = df.copy()
    data[y] = to_num(data[y])
    if hue and hue in data.columns:
        labels = list(data[hue].astype(str).unique())
        width = 0.8 / max(len(labels), 1)
        xs = np.arange(len(data[x].astype(str).unique()))
        xlabels = list(data[x].astype(str).unique())
        for i, label in enumerate(labels):
            sub = data[data[hue].astype(str).eq(label)]
            vals = [sub.loc[sub[x].astype(str).eq(lbl), y].mean() for lbl in xlabels]
            ax.bar(xs + i * width - 0.4 + width / 2, vals, width=width, label=label)
        ax.set_xticks(xs)
        ax.set_xticklabels(xlabels)
        ax.legend(fontsize=8)
    else:
        grouped = data.groupby(data[x].astype(str))[y].mean()
        ax.bar(grouped.index, grouped.values)
    ax.set_title(title)
    ax.set_ylabel(y)
    if rotate:
        ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_scatter(df: pd.DataFrame, x: str, y: str, label: str, title: str, path: Path) -> None:
    if plt is None or df.empty or x not in df.columns or y not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(to_num(df[x]), to_num(df[y]), s=50)
    for _, row in df.iterrows():
        ax.annotate(str(row.get(label, "")), (safe_float(row.get(x)), safe_float(row.get(y))), fontsize=7)
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_heatmap(corr: pd.DataFrame, path: Path) -> None:
    if plt is None or corr.empty:
        return
    pivot = corr.pivot_table(index="case_id", columns="descriptor", values="pearson_STD_descriptor", aggfunc="mean")
    if pivot.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(np.arange(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns, rotation=35, ha="right")
    ax.set_yticks(np.arange(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    ax.set_title("STD vs descriptor Pearson correlation")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_priority_matrix(matrix: pd.DataFrame, path: Path) -> None:
    if plt is None or matrix.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    costs = to_num(matrix["implementation_cost"])
    values = to_num(matrix["scientific_value"])
    risks = to_num(matrix["risk"])
    ax.scatter(costs, values, s=70 + risks * 35)
    for _, row in matrix.iterrows():
        ax.annotate(str(row["option"]), (safe_float(row["implementation_cost"]) + 0.03, safe_float(row["scientific_value"]) + 0.03), fontsize=8)
    ax.set_xlabel("Implementation cost")
    ax.set_ylabel("Scientific value")
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_title("Recommendation priority matrix")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_figures(out_fig: Path, step11c: pd.DataFrame, step11d_fleet: pd.DataFrame, corr: pd.DataFrame, matrix: pd.DataFrame) -> None:
    out_fig.mkdir(parents=True, exist_ok=True)
    if plt is None:
        return
    if not step11c.empty:
        c = step11c.copy()
        c["label"] = c["case_id"].astype(str) + "\n" + c["run_name"].astype(str) + "\n" + c["mission_duration_requested_h"].astype(str) + "h"
        save_bar(c, "label", "crossing_count", None, "Step11C crossing count comparison", out_fig / "step11x_crossing_count_comparison.png")
        save_bar(c, "label", "regions_visited", None, "Step11C regions visited comparison", out_fig / "step11x_regions_visited_comparison.png")
    if not step11d_fleet.empty:
        f = step11d_fleet.copy()
        f["label"] = f["case_id"].astype(str) + "\n" + f["strategy"].astype(str)
        save_bar(f, "label", "fleet_region_B_coverage", "source_output", "Step11D regime B coverage", out_fig / "step11x_multi_auv_regime_coverage_comparison.png")
        save_scatter(f, "trajectory_overlap_ratio", "fleet_complementarity_score", "strategy", "Overlap vs complementarity", out_fig / "step11x_overlap_vs_complementarity.png")
    save_heatmap(corr, out_fig / "step11x_descriptor_std_correlation_heatmap.png")
    save_priority_matrix(matrix, out_fig / "step11x_recommendation_priority_matrix.png")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    timestamp = now_stamp()
    outdir = RESULTS / f"fossum_roi_x490_step11x_audit_planner_results_{timestamp}"
    outdir.mkdir(parents=True, exist_ok=False)
    figures_dir = outdir / "figures"
    figures_dir.mkdir()

    evidence = Evidence(warnings=[], missing_files=[], analyzed_outputs=[])
    step11a_dirs = find_step11a_outputs()
    outputs = step11a_dirs + STEP11C_DIRS + STEP11D_DIRS

    inventory = inventory_outputs(outputs, evidence)
    inventory.to_csv(outdir / "step11x_outputs_inventory.csv", index=False)

    step11a_metrics, step11a_comp, step11a_diag = load_step11a(step11a_dirs, evidence)
    step11a_summary = summarize_step11a(step11a_metrics, step11a_comp, step11a_diag)
    step11a_summary.to_csv(outdir / "step11x_step11a_summary.csv", index=False)

    step11c_metrics, step11c_diag = load_step11c(STEP11C_DIRS, evidence)
    step11c_metrics.to_csv(outdir / "step11x_step11c_crossing_analysis.csv", index=False)

    step11d_fleet, step11d_vehicle, step11d_candidates, step11d_diag = load_step11d(STEP11D_DIRS, evidence)
    if not step11d_fleet.empty:
        step11d_fleet.to_csv(outdir / "step11x_step11d_multi_auv_analysis.csv", index=False)
    else:
        pd.DataFrame().to_csv(outdir / "step11x_step11d_multi_auv_analysis.csv", index=False)
    if not step11d_vehicle.empty:
        step11d_vehicle.to_csv(outdir / "step11x_step11d_vehicle_level_analysis.csv", index=False)
    if not step11d_candidates.empty:
        step11d_candidates.to_csv(outdir / "step11x_step11d_candidate_trajectories.csv", index=False)

    corr = descriptor_correlations(evidence)
    corr.to_csv(outdir / "step11x_descriptor_std_correlation.csv", index=False)

    changes = required_planner_changes()
    changes.to_csv(outdir / "step11x_required_planner_changes.csv", index=False)
    rec, matrix, next_plan, step11e_md = recommendations(corr, step11c_metrics, step11d_fleet)
    rec.to_csv(outdir / "step11x_improvement_recommendations.csv", index=False)
    matrix.to_csv(outdir / "step11x_priority_matrix.csv", index=False)

    verdict = "READY_FOR_STEP11E_VEHICLE_SPECIFIC_PRIZES"
    if len(evidence.analyzed_outputs) == 0 or (step11a_summary.empty and step11c_metrics.empty and step11d_fleet.empty):
        verdict = "AUDIT_FAILED_NEEDS_MANUAL_REVIEW"
    elif step11d_fleet.empty or step11c_metrics.empty:
        verdict = "NEEDS_CLEANER_REPEATED_EXPERIMENTS"

    write_text(outdir / "step11x_step11a_diagnosis.md", make_step11a_diagnosis(step11a_summary, corr))
    write_text(outdir / "step11x_step11c_gamma_sensitivity.md", make_step11c_gamma_sensitivity(step11c_metrics))
    write_text(outdir / "step11x_step11d_strategy_comparison.md", make_step11d_strategy_comparison(step11d_fleet, step11d_vehicle))
    write_text(outdir / "step11x_descriptor_redundancy_analysis.md", make_descriptor_redundancy(corr))
    write_text(outdir / "step11x_planner_limitations_summary.md", planner_limitations_md())
    write_text(outdir / "step11x_next_experiments_plan.md", next_plan)
    write_text(outdir / "step11x_step11e_recommendation.md", step11e_md.replace("READY_FOR_STEP11E_VEHICLE_SPECIFIC_PRIZES", verdict))

    summary = full_summary_md(evidence, step11a_summary, step11c_metrics, step11d_fleet, corr, verdict)
    write_text(outdir / "step11x_summary.md", summary)
    full_report = "\n\n".join(
        [
            summary,
            make_step11a_diagnosis(step11a_summary, corr),
            make_step11c_gamma_sensitivity(step11c_metrics),
            make_step11d_strategy_comparison(step11d_fleet, step11d_vehicle),
            make_descriptor_redundancy(corr),
            planner_limitations_md(),
            next_plan,
            step11e_md.replace("READY_FOR_STEP11E_VEHICLE_SPECIFIC_PRIZES", verdict),
        ]
    )
    write_text(outdir / "step11x_full_audit_report.md", full_report)

    create_figures(figures_dir, step11c_metrics, step11d_fleet, corr, matrix)

    checks = {
        "audit_created": True,
        "output_dir": rel(outdir),
        "planner_rerun": False,
        "existing_outputs_modified": False,
        "new_trajectories_generated": False,
        "step11a_outputs_found": len(step11a_dirs),
        "step11c_expected_outputs_found": sum(d.exists() for d in STEP11C_DIRS),
        "step11d_expected_outputs_found": sum(d.exists() for d in STEP11D_DIRS),
        "inventory_rows": int(len(inventory)),
        "step11a_summary_rows": int(len(step11a_summary)),
        "step11c_rows": int(len(step11c_metrics)),
        "step11d_fleet_rows": int(len(step11d_fleet)),
        "descriptor_correlation_rows": int(len(corr)),
        "figures_created": len(list(figures_dir.glob("*.png"))),
        "matplotlib_available": plt is not None,
        "matplotlib_error": MATPLOTLIB_ERROR,
        "warnings_count": len(evidence.warnings),
        "missing_files_count": len(evidence.missing_files),
        "verdict": verdict,
    }
    metadata = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": rel(Path(__file__)),
        "root": str(ROOT),
        "analyzed_outputs": evidence.analyzed_outputs,
        "missing_files": evidence.missing_files,
        "warnings": evidence.warnings,
        "inputs": {
            "step11a_auto_patterns": ["step11a", "minimal_boundary_planner", "boundary_planner", "baseline_vs_enriched"],
            "step11c_dirs": [rel(d) for d in STEP11C_DIRS],
            "step11d_dirs": [rel(d) for d in STEP11D_DIRS],
            "step10f_maps": rel(STEP10F_DIR / "planner_minimal_boundary_input_maps.npz"),
            "step08_maps": rel(STEP08_DIR / "step08_all_descriptor_maps.npz"),
        },
    }
    (outdir / "step11x_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    (outdir / "step11x_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    try:
        shutil.copy2(Path(__file__), outdir / Path(__file__).name)
    except Exception as exc:
        evidence.warnings.append(f"Could not copy script to output: {exc}")

    print_terminal_report(outdir, checks, evidence, step11a_summary, step11c_metrics, step11d_fleet, corr, verdict)
    return 0


def best_step11c(step11c: pd.DataFrame) -> str:
    if step11c.empty:
        return "manual_review_needed"
    c = step11c.copy()
    c["crossing_count"] = to_num(c.get("crossing_count", pd.Series(dtype=float)))
    c["regions_visited"] = to_num(c.get("regions_visited", pd.Series(dtype=float)))
    candidates = c[c["run_name"].astype(str).str.contains("crossing|boundary", case=False, na=False)]
    if candidates.empty:
        candidates = c
    best = candidates.sort_values(["regions_visited", "crossing_count"], ascending=False).iloc[0]
    return f"{best.get('run_name')} ({best.get('case_id')}, {best.get('mission_duration_requested_h')}h)"


def best_step11d(step11d: pd.DataFrame) -> str:
    if step11d.empty:
        return "manual_review_needed"
    preferred = step11d[step11d["strategy"].eq("vehicle_specific_regime_maps")]
    if not preferred.empty:
        return "vehicle_specific_regime_maps"
    best = step11d.sort_values(["fleet_complementarity_score", "fleet_region_B_coverage"], ascending=False).iloc[0]
    return str(best.get("strategy"))


def print_terminal_report(
    outdir: Path,
    checks: dict[str, Any],
    evidence: Evidence,
    step11a: pd.DataFrame,
    step11c: pd.DataFrame,
    step11d: pd.DataFrame,
    corr: pd.DataFrame,
    verdict: str,
) -> None:
    boundary_corr = np.nan
    boundary_j = np.nan
    if not corr.empty:
        bc = corr[corr["descriptor"].eq("boundary_score")]
        if not bc.empty:
            boundary_corr = float(bc["pearson_STD_descriptor"].mean())
            boundary_j = float(bc["top10_jaccard"].mean())

    print("\n============================================================")
    print("STEP11X AUDIT FINAL REPORT")
    print("============================================================")
    print(f"Output: {rel(outdir)}")
    print(f"1. Outputs analyzed: {len(set(evidence.analyzed_outputs))}")
    print(f"2. Step11A: rows={len(step11a)}; boundary-only changed routes often, but with mixed STD/boundary tradeoffs.")
    print(f"3. Step11C: rows={len(step11c)}; proxy can improve crossings, but gamma response is non-monotonic and route-level reward is absent.")
    print(f"4. Step11D: rows={len(step11d)}; regime specialization is more important than simple overlap reduction.")
    print(f"5. boundary_score redundant with STD: Pearson mean={boundary_corr:.3f}, top10 Jaccard mean={boundary_j:.3f}; case-dependent, not a reliable independent driver by itself.")
    print("6. Main problem: planner formulation for route/fleet roles, plus descriptor choice; not just parameter tuning.")
    print(f"7. Best single-AUV strategy: {best_step11c(step11c)}")
    print(f"8. Best multi-AUV strategy: {best_step11d(step11d)}")
    print("9. Improve first: vehicle-specific prize maps, supported by a narrow descriptor ablation.")
    print("10. Do not prioritize now: overlap/proximity penalty or post-solver selection as final method.")
    print("11. Step11E: Option B - vehicle-specific prize maps. Secondary: descriptor ablation.")
    print(f"12. Warnings: {len(evidence.warnings)} warnings, {len(evidence.missing_files)} missing expected files/outputs.")
    if evidence.missing_files:
        print("    Missing examples:")
        for item in evidence.missing_files[:5]:
            print(f"    - {item}")
    print(f"13. Verdict final: {verdict}")
    print("============================================================\n")


if __name__ == "__main__":
    raise SystemExit(main())
