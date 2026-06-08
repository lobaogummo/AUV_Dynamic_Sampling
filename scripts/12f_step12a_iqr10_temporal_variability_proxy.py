#!/usr/bin/env python
"""Post-process Step12A trajectories with an IQR10 temporal-variability proxy.

This script does not rerun the planner. It reads existing routes and metrics,
computes the interquartile range over the previous available temperature days,
and samples the resulting map along each existing trajectory.
"""

from __future__ import annotations

import argparse
import importlib.util
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
RESULTS = ROOT / "results"
DEFAULT_STEP12A = RESULTS / "fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260605_152501"
DEFAULT_STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260605_141912"
DEFAULT_STEP11Y = RESULTS / "fossum_roi_x490_step11y_prototype_based_planner_input_audit_20260605_143425"
DEFAULT_STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
HRES = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
SCRIPTS = ROOT / "scripts"

ROI_ROW_MIN = 55
ROI_COL_MIN = 47
ROI_SHAPE = (72, 117)
WINDOW_DAYS = 10


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        return None if not math.isfinite(val) else val
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_map(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    valid = mask & np.isfinite(arr)
    if not np.any(valid):
        return out
    lo = float(np.nanmin(arr[valid]))
    hi = float(np.nanmax(arr[valid]))
    out[valid] = 0.0 if hi <= lo else ((arr[valid] - lo) / (hi - lo)).astype(np.float32)
    return out


def finite_stats(prefix: str, arr: np.ndarray, mask: np.ndarray) -> dict[str, float | int]:
    vals = np.asarray(arr, dtype=float)[mask & np.isfinite(arr)]
    if vals.size == 0:
        return {
            f"{prefix}_finite_cells": 0,
            f"{prefix}_min": float("nan"),
            f"{prefix}_max": float("nan"),
            f"{prefix}_mean": float("nan"),
            f"{prefix}_p90": float("nan"),
        }
    return {
        f"{prefix}_finite_cells": int(vals.size),
        f"{prefix}_min": float(np.nanmin(vals)),
        f"{prefix}_max": float(np.nanmax(vals)),
        f"{prefix}_mean": float(np.nanmean(vals)),
        f"{prefix}_p90": float(np.nanpercentile(vals, 90)),
    }


def locate_temperature_inputs(step00: Path) -> tuple[Path, Path, Path, list[str]]:
    searched = [
        step00 / "X_surface_370_roi_x490.npy",
        step00 / "thetao_surface_370_roi_x490.npy",
        RESULTS / "fresnel_paper_roi_x490_surface_370_20260509_180348" / "thetao_surface_370_hres_paper_roi_x490.npy",
    ]
    date_candidates = [
        step00 / "dates_370.csv",
        HRES / "dates_370.csv",
    ]
    mask_candidates = [
        step00 / "mask_common_roi_x490.npy",
    ]
    temp_path = next((p for p in searched if p.exists()), None)
    dates_path = next((p for p in date_candidates if p.exists()), None)
    mask_path = next((p for p in mask_candidates if p.exists()), None)
    searched_text = [rel(p) for p in searched + date_candidates + mask_candidates]
    missing = []
    if temp_path is None:
        missing.append("temperature stack")
    if dates_path is None:
        missing.append("dates CSV")
    if mask_path is None:
        missing.append("ROI mask")
    if missing:
        raise FileNotFoundError(f"Could not locate {', '.join(missing)}. Searched: {searched_text}")
    return temp_path, dates_path, mask_path, searched_text


def compute_iqr10_maps(
    cases: pd.DataFrame,
    temp_stack: np.ndarray,
    dates: pd.DataFrame,
    mask: np.ndarray,
    outdir: Path,
) -> tuple[dict[tuple[str, str], dict[str, Any]], pd.DataFrame]:
    maps_dir = outdir / "iqr10_maps"
    maps_dir.mkdir(exist_ok=True)
    dates = dates.copy()
    dates["date"] = pd.to_datetime(dates["date"]).dt.strftime("%Y-%m-%d")
    if "time_index" not in dates.columns:
        dates["time_index"] = np.arange(len(dates))
    case_maps: dict[tuple[str, str], dict[str, Any]] = {}
    rows = []
    for _, case in cases.iterrows():
        case_id = str(case["case_id"])
        date = pd.to_datetime(case["date"]).strftime("%Y-%m-%d")
        match = dates[dates["date"].eq(date)]
        if match.empty:
            raise ValueError(f"Planning date {date} for {case_id} not found in dates CSV.")
        time_index = int(match.iloc[0]["time_index"])
        previous = dates[dates["time_index"].astype(int) < time_index].tail(WINDOW_DAYS)
        indices = previous["time_index"].astype(int).to_numpy()
        if len(indices) == 0:
            raw = np.full(ROI_SHAPE, np.nan, dtype=np.float32)
        else:
            window = np.asarray(temp_stack[indices], dtype=np.float32)
            raw = (np.nanpercentile(window, 75, axis=0) - np.nanpercentile(window, 25, axis=0)).astype(np.float32)
            raw[~mask] = np.nan
        norm = normalize_map(raw, mask)
        stem = f"{case_id}__{date}"
        raw_path = maps_dir / f"{stem}_iqr10_raw.npy"
        norm_path = maps_dir / f"{stem}_iqr10_norm.npy"
        np.save(raw_path, raw)
        np.save(norm_path, norm)
        start_date = str(previous.iloc[0]["date"]) if len(previous) else ""
        end_date = str(previous.iloc[-1]["date"]) if len(previous) else ""
        row = {
            "case_id": case_id,
            "date": date,
            "planning_time_index": time_index,
            "iqr10_previous_days_used": int(len(indices)),
            "iqr10_requested_days": WINDOW_DAYS,
            "iqr10_full_window_available": bool(len(indices) == WINDOW_DAYS),
            "iqr10_window_start_date": start_date,
            "iqr10_window_end_date": end_date,
            "iqr10_window_time_indices": "|".join(map(str, indices.tolist())),
            "iqr10_raw_map_path": rel(raw_path),
            "iqr10_norm_map_path": rel(norm_path),
            **finite_stats("iqr10_raw", raw, mask),
            **finite_stats("iqr10_norm", norm, mask),
        }
        rows.append(row)
        case_maps[(case_id, date)] = {"raw": raw, "norm": norm, "meta": row}
    return case_maps, pd.DataFrame(rows)


def route_roi_points(s11a, run_dir: Path, lat_hres: np.ndarray, lon_hres: np.ndarray, mask: np.ndarray) -> list[tuple[int, int]]:
    routes_path = run_dir / "routes_file.txt"
    routes = s11a.parse_routes_file(routes_path)
    points = s11a.route_grid_points(routes, lat_hres, lon_hres) if routes else []
    seen: dict[tuple[int, int], None] = {}
    for r, c in points:
        rr = int(r) - ROI_ROW_MIN
        cc = int(c) - ROI_COL_MIN
        if 0 <= rr < mask.shape[0] and 0 <= cc < mask.shape[1] and bool(mask[rr, cc]):
            seen[(rr, cc)] = None
    return list(seen.keys())


def sample_route_metrics(points: list[tuple[int, int]], iqr_norm: np.ndarray, iqr_raw: np.ndarray, top10_threshold: float, length_km: float) -> dict[str, Any]:
    n = len(points)
    if n == 0:
        return {
            "iqr10_collected_total": float("nan"),
            "iqr10_collected_mean": float("nan"),
            "iqr10_collected_per_km": float("nan"),
            "percentage_path_in_top10_IQR10": float("nan"),
            "iqr10_raw_collected_total": float("nan"),
            "iqr10_raw_collected_mean": float("nan"),
            "iqr10_route_valid_cells": 0,
            "iqr10_route_mapped_any": False,
        }
    rr = np.array([p[0] for p in points], dtype=int)
    cc = np.array([p[1] for p in points], dtype=int)
    vals = iqr_norm[rr, cc]
    raw_vals = iqr_raw[rr, cc]
    vals = vals[np.isfinite(vals)]
    raw_vals = raw_vals[np.isfinite(raw_vals)]
    total = float(np.nansum(vals)) if vals.size else float("nan")
    mean = float(np.nanmean(vals)) if vals.size else float("nan")
    raw_total = float(np.nansum(raw_vals)) if raw_vals.size else float("nan")
    raw_mean = float(np.nanmean(raw_vals)) if raw_vals.size else float("nan")
    top_frac = float(np.mean(vals >= top10_threshold)) if vals.size and math.isfinite(top10_threshold) else float("nan")
    per_km = total / float(length_km) if math.isfinite(float(length_km)) and float(length_km) > 0 and math.isfinite(total) else float("nan")
    return {
        "iqr10_collected_total": total,
        "iqr10_collected_mean": mean,
        "iqr10_collected_per_km": per_km,
        "percentage_path_in_top10_IQR10": top_frac,
        "iqr10_raw_collected_total": raw_total,
        "iqr10_raw_collected_mean": raw_mean,
        "iqr10_route_valid_cells": int(vals.size),
        "iqr10_route_mapped_any": bool(vals.size > 0),
    }


def baseline_lookup(metrics: pd.DataFrame) -> pd.DataFrame:
    base = metrics[np.isclose(metrics["alpha"].astype(float), 0.0)].copy()
    base["dedup_sort"] = base.get("deduplicated_baseline", False).astype(str).str.lower().eq("true").astype(int)
    base = base.sort_values(["case_id", "date", "mission_duration_requested_h", "descriptor", "dedup_sort"], ascending=[True, True, True, True, False])
    return base.drop_duplicates(["case_id", "date", "mission_duration_requested_h", "descriptor"], keep="first")


def add_baseline_comparison(enriched: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = baseline_lookup(enriched)
    keys = ["case_id", "date", "mission_duration_requested_h", "descriptor"]
    keep = keys + ["iqr10_collected_total", "iqr10_collected_mean", "iqr10_collected_per_km", "run_dir"]
    base_small = base[keep].rename(
        columns={
            "iqr10_collected_total": "baseline_iqr10_collected_total",
            "iqr10_collected_mean": "baseline_iqr10_collected_mean",
            "iqr10_collected_per_km": "baseline_iqr10_collected_per_km",
            "run_dir": "baseline_iqr10_run_dir",
        }
    )
    out = enriched.merge(base_small, on=keys, how="left")
    out["IQR10_retention_vs_baseline"] = out["iqr10_collected_total"] / out["baseline_iqr10_collected_total"]
    out.loc[~np.isfinite(out["IQR10_retention_vs_baseline"]), "IQR10_retention_vs_baseline"] = np.nan
    out["IQR10_gain_vs_baseline"] = out["iqr10_collected_total"] - out["baseline_iqr10_collected_total"]
    out["IQR10_gain_pct_vs_baseline"] = out["IQR10_gain_vs_baseline"] / out["baseline_iqr10_collected_total"]
    out["iqr10_baseline_comparison_exists"] = np.isfinite(out["baseline_iqr10_collected_total"])
    return out, base


def make_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["descriptor", "alpha"]
    agg_cols = {
        "iqr10_collected_total": "mean",
        "iqr10_collected_mean": "mean",
        "iqr10_collected_per_km": "mean",
        "percentage_path_in_top10_IQR10": "mean",
        "IQR10_retention_vs_baseline": "mean",
        "IQR10_gain_vs_baseline": "mean",
        "IQR10_gain_pct_vs_baseline": "mean",
        "collected_STD": "mean",
        "STD_retention": "mean",
        "collected_descriptor": "mean",
        "collected_information_score": "mean",
        "reward_per_distance_km": "mean",
        "trajectory_length": "mean",
        "solver_runtime": "mean",
    }
    available = {k: v for k, v in agg_cols.items() if k in metrics.columns}
    summary = metrics.groupby(group_cols, as_index=False).agg(run_count=("run_name", "count"), **{f"mean_{k}": (k, v) for k, v in available.items()})
    return summary


def plot_lines(metrics: pd.DataFrame, y: str, title: str, out: Path, ylabel: str | None = None) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for descriptor, group in metrics.sort_values("alpha").groupby("descriptor"):
        ax.plot(group["alpha"], group[y], marker="o", linewidth=1.8, label=descriptor)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.4)
    ax.set_xlabel("alpha")
    ax.set_ylabel(ylabel or y)
    ax.set_title(title)
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def plot_scatter(metrics: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for descriptor, group in metrics.groupby("descriptor"):
        ax.scatter(group["STD_retention"], group["IQR10_gain_vs_baseline"], label=descriptor, s=45)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.45)
    ax.axvline(1, color="gray", linewidth=0.8, alpha=0.45)
    ax.set_xlabel("STD retention")
    ax.set_ylabel("IQR10 gain vs baseline")
    ax.set_title("STD retention vs IQR10 temporal-variability gain")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def plot_map_and_routes(metrics: pd.DataFrame, case_maps: dict[tuple[str, str], dict[str, Any]], out: Path) -> None:
    case_key = next(iter(case_maps))
    cmap = case_maps[case_key]["norm"]
    case_id, date = case_key
    selected = []
    baseline = metrics[np.isclose(metrics["alpha"].astype(float), 0.0)].head(1)
    if not baseline.empty:
        selected.append(("baseline_STD", baseline.iloc[0]))
    best = metrics.sort_values("iqr10_collected_total", ascending=False).head(1)
    if not best.empty:
        selected.append(("max_IQR10", best.iloc[0]))
    best_gain = metrics.sort_values("IQR10_gain_vs_baseline", ascending=False).head(1)
    if not best_gain.empty:
        selected.append(("max_gain", best_gain.iloc[0]))

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(cmap, origin="lower", cmap="magma", vmin=0, vmax=1, aspect="equal")
    colors = {"baseline_STD": "white", "max_IQR10": "cyan", "max_gain": "lime"}
    for label, row in selected:
        pts = row.get("_route_points", [])
        if pts:
            rr = [p[0] for p in pts]
            cc = [p[1] for p in pts]
            ax.plot(cc, rr, color=colors.get(label, "white"), linewidth=2.0, label=f"{label}: {row['descriptor']} a={float(row['alpha']):.2f}")
    ax.set_title(f"{case_id} {date}: IQR10 map and selected Step12A routes")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(fontsize=8, loc="lower left")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("IQR10 normalized")
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def make_report(outdir: Path, metrics: pd.DataFrame, summary: pd.DataFrame, map_checks: pd.DataFrame, checks: dict[str, Any]) -> None:
    best = metrics.sort_values("iqr10_collected_total", ascending=False).head(5)
    best_gain = metrics.sort_values("IQR10_gain_vs_baseline", ascending=False).head(5)

    def md_table(df: pd.DataFrame, cols: list[str]) -> str:
        if df.empty:
            return "_No rows available._"
        d = df[[c for c in cols if c in df.columns]].copy()
        for col in d.columns:
            if pd.api.types.is_numeric_dtype(d[col]):
                d[col] = d[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.4f}")
            else:
                d[col] = d[col].fillna("").astype(str)
        lines = [
            "| " + " | ".join(d.columns) + " |",
            "| " + " | ".join("---" for _ in d.columns) + " |",
        ]
        for row in d.astype(str).values.tolist():
            lines.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
        return "\n".join(lines)

    lines = [
        "# Step12A IQR10 Temporal-Variability Proxy",
        "",
        "This is post-processing only. The planner, VRP objective, Step08, Step11Y, and Step12A execution were not modified or rerun.",
        "",
        "## Interpretation",
        "IQR10 is the interquartile range of temperature over the previous available days at each ROI cell. It is a robust temporal-variability proxy: high values indicate places where recent temperature variability was larger, which may be relevant for future adaptive sampling or data-assimilation experiments.",
        "",
        "This is not actual data assimilation. It does not prove uncertainty reduction and should not be described as assimilation skill. It only indicates whether an existing trajectory sampled recently variable regions that could be valuable for model-error diagnosis, model uncertainty evaluation, or future assimilation-aware mission planning.",
        "",
        "Conceptual link: recent temporal variability is often associated with dynamical change, model mismatch potential, and information-rich sampling opportunities. In adaptive sampling, such regions are plausible candidates for observations because they may constrain evolving features more strongly than temporally stable zones.",
        "",
        "## Literature Notes for Thesis Framing",
        "Use IQR10 as a diagnostic proxy rather than an assimilation result. The interpretation is conceptually aligned with data-assimilation and adaptive-sampling literature in which observations are valuable when they target regions of larger forecast/model uncertainty, temporal change, or dynamically active structure. Suitable background references include Kalnay (2003) for atmospheric/oceanic data assimilation principles, Evensen (2009) for ensemble-based uncertainty and assimilation framing, and Lermusiaux (2007) for adaptive sampling/modeling links in ocean applications.",
        "",
        "## IQR10 Window Validation",
        md_table(map_checks, ["case_id", "date", "iqr10_previous_days_used", "iqr10_window_start_date", "iqr10_window_end_date", "iqr10_raw_min", "iqr10_raw_max", "iqr10_raw_mean", "iqr10_raw_finite_cells"]),
        "",
        "## Top Routes by IQR10 Collected",
        md_table(best, ["descriptor", "alpha", "iqr10_collected_total", "iqr10_collected_mean", "iqr10_collected_per_km", "percentage_path_in_top10_IQR10", "collected_STD", "STD_retention", "trajectory_length"]),
        "",
        "## Top Routes by IQR10 Gain vs Baseline",
        md_table(best_gain, ["descriptor", "alpha", "IQR10_gain_vs_baseline", "IQR10_retention_vs_baseline", "iqr10_collected_total", "baseline_iqr10_collected_total", "STD_retention", "trajectory_length"]),
        "",
        "## Validation Checks",
        f"- Existing Step12A rows processed: {checks['metrics_rows']}",
        f"- Routes with at least one valid ROI cell: {checks['routes_mapped_successfully']}/{checks['metrics_rows']}",
        f"- Baseline comparisons available: {checks['baseline_comparisons_available']}/{checks['metrics_rows']}",
        f"- Planner rerun: `{checks['planner_rerun']}`",
        "",
        "## Outputs",
        "- `step12a_iqr10_metrics.csv`",
        "- `step12a_iqr10_summary_by_descriptor_alpha.csv`",
        "- `step12a_iqr10_checks.json`",
        "- `figures/step12a_alpha_vs_iqr10_collected.png`",
        "- `figures/step12a_iqr10_gain_vs_baseline.png`",
        "- `figures/step12a_STD_retention_vs_IQR10_gain.png`",
        "- `figures/step12a_iqr10_map_and_selected_routes.png`",
    ]
    (outdir / "step12a_iqr10_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add IQR10 post-processing metrics to existing Step12A results.")
    parser.add_argument("--step12a", type=Path, default=DEFAULT_STEP12A)
    parser.add_argument("--step08", type=Path, default=DEFAULT_STEP08)
    parser.add_argument("--step11y", type=Path, default=DEFAULT_STEP11Y)
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    args = parser.parse_args()

    step12a = args.step12a.resolve()
    step08 = args.step08.resolve()
    step11y = args.step11y.resolve()
    step00 = args.step00.resolve()
    figdir = step12a / "figures"
    figdir.mkdir(exist_ok=True)

    temp_path, dates_path, mask_path, searched = locate_temperature_inputs(step00)
    metrics_path = step12a / "step12a_single_auv_metrics.csv"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Missing Step12A metrics: {metrics_path}")
    if not step08.exists():
        raise FileNotFoundError(f"Missing validated Step08 directory: {step08}")
    if not step11y.exists():
        raise FileNotFoundError(f"Missing validated Step11Y directory: {step11y}")

    temp_stack = np.load(temp_path, mmap_mode="r")
    dates = pd.read_csv(dates_path)
    mask = np.load(mask_path).astype(bool)
    if temp_stack.shape[1:] != ROI_SHAPE or mask.shape != ROI_SHAPE:
        raise ValueError(f"Unexpected ROI shapes: temp={temp_stack.shape}, mask={mask.shape}")

    metrics = pd.read_csv(metrics_path)
    metrics["date"] = pd.to_datetime(metrics["date"]).dt.strftime("%Y-%m-%d")
    cases = metrics[["case_id", "date"]].drop_duplicates().reset_index(drop=True)
    case_maps, map_checks = compute_iqr10_maps(cases, temp_stack, dates, mask, step12a)

    s11a = load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")
    lat_hres = np.load(HRES / "LAT_hres.npy")
    lon_hres = np.load(HRES / "LON_hres.npy")

    enriched_rows = []
    route_valid_counts = []
    for _, row in metrics.iterrows():
        out = row.to_dict()
        case_key = (str(row["case_id"]), pd.to_datetime(row["date"]).strftime("%Y-%m-%d"))
        maps = case_maps[case_key]
        iqr_raw = maps["raw"]
        iqr_norm = maps["norm"]
        top10 = float(maps["meta"]["iqr10_norm_p90"])
        run_dir = Path(str(row["run_dir"]))
        if not run_dir.is_absolute():
            run_dir = ROOT / run_dir
        points = route_roi_points(s11a, run_dir, lat_hres, lon_hres, mask)
        route_valid_counts.append(len(points))
        length_km = float(row.get("trajectory_length", float("nan")))
        out.update(sample_route_metrics(points, iqr_norm, iqr_raw, top10, length_km))
        out["iqr10_route_points_roi"] = "|".join(f"{r}:{c}" for r, c in points)
        out["iqr10_route_valid_fraction_vs_existing_sampled_cells"] = (
            len(points) / float(row.get("number_of_valid_cells_sampled", len(points)) or len(points) or 1)
        )
        out["_route_points"] = points
        out.update({k: v for k, v in maps["meta"].items() if k.startswith("iqr10_") or k in {"planning_time_index"}})
        enriched_rows.append(out)

    enriched = pd.DataFrame(enriched_rows)
    enriched, baseline = add_baseline_comparison(enriched)
    summary = make_summary(enriched)

    save_cols = [c for c in enriched.columns if c != "_route_points"]
    enriched[save_cols].to_csv(step12a / "step12a_iqr10_metrics.csv", index=False)
    summary.to_csv(step12a / "step12a_iqr10_summary_by_descriptor_alpha.csv", index=False)
    map_checks.to_csv(step12a / "iqr10_maps" / "step12a_iqr10_map_checks.csv", index=False)

    plot_lines(enriched, "iqr10_collected_total", "Alpha vs collected IQR10 temporal-variability proxy", figdir / "step12a_alpha_vs_iqr10_collected.png", "IQR10 collected total")
    plot_lines(enriched, "IQR10_gain_vs_baseline", "Alpha vs IQR10 gain relative to STD-only baseline", figdir / "step12a_iqr10_gain_vs_baseline.png", "IQR10 gain vs baseline")
    plot_scatter(enriched, figdir / "step12a_STD_retention_vs_IQR10_gain.png")
    plot_map_and_routes(enriched, case_maps, figdir / "step12a_iqr10_map_and_selected_routes.png")

    checks = {
        "planner_rerun": False,
        "step12a": rel(step12a),
        "step08": rel(step08),
        "step11y": rel(step11y),
        "temperature_stack": rel(temp_path),
        "dates_csv": rel(dates_path),
        "mask": rel(mask_path),
        "searched_files": searched,
        "metrics_rows": int(len(enriched)),
        "case_count": int(len(cases)),
        "cases": cases.to_dict(orient="records"),
        "map_checks": map_checks.to_dict(orient="records"),
        "routes_mapped_successfully": int(np.sum(np.asarray(route_valid_counts) > 0)),
        "min_route_valid_cells": int(np.min(route_valid_counts)) if route_valid_counts else 0,
        "max_route_valid_cells": int(np.max(route_valid_counts)) if route_valid_counts else 0,
        "baseline_rows": int(len(baseline)),
        "baseline_comparisons_available": int(enriched["iqr10_baseline_comparison_exists"].sum()),
        "outputs": {
            "metrics": rel(step12a / "step12a_iqr10_metrics.csv"),
            "summary": rel(step12a / "step12a_iqr10_summary_by_descriptor_alpha.csv"),
            "report": rel(step12a / "step12a_iqr10_report.md"),
            "figures": [
                rel(figdir / "step12a_alpha_vs_iqr10_collected.png"),
                rel(figdir / "step12a_iqr10_gain_vs_baseline.png"),
                rel(figdir / "step12a_STD_retention_vs_IQR10_gain.png"),
                rel(figdir / "step12a_iqr10_map_and_selected_routes.png"),
            ],
        },
    }
    (step12a / "step12a_iqr10_checks.json").write_text(json.dumps(checks, indent=2, default=json_default), encoding="utf-8")
    make_report(step12a, enriched, summary, map_checks, checks)
    print(json.dumps(checks, indent=2, default=json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
