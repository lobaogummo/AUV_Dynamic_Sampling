#!/usr/bin/env python
"""Post-process Step12B multi-AUV trajectories with an IQR10 proxy.

This script does not rerun the planner. It reads the existing Step12B vehicle
routes, computes the interquartile range over the previous 10 temperature days,
and compares route-level IQR10 sampling against the STD-only baseline.
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
DEFAULT_STEP12B = RESULTS / "fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity_20260608_163658"
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


def locate_temperature_inputs(step00: Path) -> tuple[Path, Path, Path, list[str]]:
    temp_candidates = [
        step00 / "X_surface_370_roi_x490.npy",
        step00 / "thetao_surface_370_roi_x490.npy",
        RESULTS / "fresnel_paper_roi_x490_surface_370_20260509_180348" / "thetao_surface_370_hres_paper_roi_x490.npy",
    ]
    date_candidates = [step00 / "dates_370.csv", HRES / "dates_370.csv"]
    mask_candidates = [step00 / "mask_common_roi_x490.npy"]
    searched = temp_candidates + date_candidates + mask_candidates
    temp_path = next((p for p in temp_candidates if p.exists()), None)
    dates_path = next((p for p in date_candidates if p.exists()), None)
    mask_path = next((p for p in mask_candidates if p.exists()), None)
    missing = []
    if temp_path is None:
        missing.append("temperature stack")
    if dates_path is None:
        missing.append("dates CSV")
    if mask_path is None:
        missing.append("ROI mask")
    if missing:
        raise FileNotFoundError(f"Could not locate {', '.join(missing)}. Searched: {[rel(p) for p in searched]}")
    return temp_path, dates_path, mask_path, [rel(p) for p in searched]


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
        row = {
            "case_id": case_id,
            "date": date,
            "planning_time_index": time_index,
            "iqr10_previous_days_used": int(len(indices)),
            "iqr10_requested_days": WINDOW_DAYS,
            "iqr10_full_window_available": bool(len(indices) == WINDOW_DAYS),
            "iqr10_window_start_date": str(previous.iloc[0]["date"]) if len(previous) else "",
            "iqr10_window_end_date": str(previous.iloc[-1]["date"]) if len(previous) else "",
            "iqr10_window_time_indices": "|".join(map(str, indices.tolist())),
            "iqr10_raw_map_path": rel(raw_path),
            "iqr10_norm_map_path": rel(norm_path),
            **finite_stats("iqr10_raw", raw, mask),
            **finite_stats("iqr10_norm", norm, mask),
        }
        rows.append(row)
        case_maps[(case_id, date)] = {"raw": raw, "norm": norm, "meta": row}
    return case_maps, pd.DataFrame(rows)


def route_roi_points_for_vehicle(
    s11a,
    run_dir: Path,
    vehicle_id: int | None,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    mask: np.ndarray,
) -> list[tuple[int, int]]:
    routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
    if vehicle_id is not None and len(routes) > 1:
        routes = [r for r in routes if int(r.get("route_id", -1)) == int(vehicle_id)]
    points = s11a.route_grid_points(routes, lat_hres, lon_hres) if routes else []
    seen: dict[tuple[int, int], None] = {}
    for r, c in points:
        rr = int(r) - ROI_ROW_MIN
        cc = int(c) - ROI_COL_MIN
        if 0 <= rr < mask.shape[0] and 0 <= cc < mask.shape[1] and bool(mask[rr, cc]):
            seen[(rr, cc)] = None
    return list(seen.keys())


def sample_route_metrics(points: list[tuple[int, int]], iqr_norm: np.ndarray, iqr_raw: np.ndarray, top10_threshold: float, length_km: float) -> dict[str, Any]:
    if not points:
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


def add_fleet_baseline_comparison(fleet: pd.DataFrame) -> pd.DataFrame:
    keys = ["case_id", "date", "mission_duration_requested_h"]
    baseline = fleet[fleet["strategy"].eq("baseline_shared_STD")].copy()
    baseline = baseline.drop_duplicates(keys, keep="first")
    baseline = baseline[keys + ["fleet_iqr10_collected_total", "fleet_iqr10_collected_per_km"]].rename(
        columns={
            "fleet_iqr10_collected_total": "baseline_fleet_iqr10_collected_total",
            "fleet_iqr10_collected_per_km": "baseline_fleet_iqr10_collected_per_km",
        }
    )
    out = fleet.merge(baseline, on=keys, how="left")
    out["fleet_IQR10_retention_vs_baseline"] = out["fleet_iqr10_collected_total"] / out["baseline_fleet_iqr10_collected_total"]
    out["fleet_IQR10_gain_vs_baseline"] = out["fleet_iqr10_collected_total"] - out["baseline_fleet_iqr10_collected_total"]
    out["fleet_IQR10_gain_pct_vs_baseline"] = out["fleet_IQR10_gain_vs_baseline"] / out["baseline_fleet_iqr10_collected_total"] * 100.0
    out["iqr10_baseline_comparison_exists"] = out["baseline_fleet_iqr10_collected_total"].notna()
    return out


def make_fleet(vehicle: pd.DataFrame, fleet_existing: pd.DataFrame) -> pd.DataFrame:
    agg = vehicle.groupby(["case_id", "date", "mission_duration_requested_h", "strategy"], as_index=False).agg(
        vehicles_with_iqr10=("iqr10_route_mapped_any", "sum"),
        fleet_iqr10_collected_total=("iqr10_collected_total", "sum"),
        fleet_iqr10_raw_collected_total=("iqr10_raw_collected_total", "sum"),
        fleet_iqr10_route_valid_cells=("iqr10_route_valid_cells", "sum"),
        fleet_trajectory_length=("trajectory_length", "sum"),
        mean_iqr10_collected_mean=("iqr10_collected_mean", "mean"),
        mean_percentage_path_in_top10_IQR10=("percentage_path_in_top10_IQR10", "mean"),
        vehicle_rows=("run_id", "count"),
    )
    agg["fleet_iqr10_collected_per_km"] = agg["fleet_iqr10_collected_total"] / agg["fleet_trajectory_length"]
    cols = [
        "case_id",
        "strategy",
        "base_strategy",
        "mission_duration_requested_h",
        "solver_status",
        "solver_runtime",
        "fleet_collected_STD",
        "STD_retention",
        "fleet_collected_boundary",
        "fleet_region_A_coverage",
        "fleet_region_B_coverage",
        "region_balance",
        "regime_specialization_score",
        "trajectory_overlap_ratio",
        "fleet_total_area_covered",
        "recommendation_score",
    ]
    available = [c for c in cols if c in fleet_existing.columns]
    fleet_existing = fleet_existing[available].copy()
    out = agg.merge(fleet_existing, on=["case_id", "strategy", "mission_duration_requested_h"], how="left")
    return add_fleet_baseline_comparison(out)


def plot_case_bars(fleet: pd.DataFrame, out: Path) -> None:
    cases = list(fleet["case_id"].drop_duplicates())
    fig, axes = plt.subplots(len(cases), 1, figsize=(11, 3.8 * len(cases)), squeeze=False)
    for ax, case_id in zip(axes[:, 0], cases):
        g = fleet[fleet["case_id"].eq(case_id)].sort_values("fleet_IQR10_gain_vs_baseline", ascending=False)
        colors = ["#333333" if s == "baseline_shared_STD" else "#1f77b4" for s in g["strategy"]]
        ax.bar(g["strategy"], g["fleet_IQR10_gain_vs_baseline"], color=colors)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(f"{case_id}: fleet IQR10 gain vs STD baseline")
        ax.set_ylabel("IQR10 gain")
        ax.tick_params(axis="x", labelrotation=35)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def plot_retention_scatter(fleet: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for case_id, g in fleet.groupby("case_id"):
        ax.scatter(g["STD_retention"], g["fleet_IQR10_gain_vs_baseline"], s=55, label=case_id)
        for _, row in g.iterrows():
            if row["strategy"] in {"baseline_shared_STD"} or row["fleet_IQR10_gain_vs_baseline"] == g["fleet_IQR10_gain_vs_baseline"].max():
                ax.annotate(row["strategy"], (row["STD_retention"], row["fleet_IQR10_gain_vs_baseline"]), fontsize=7)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    ax.axvline(1, color="gray", linewidth=0.8, alpha=0.5)
    ax.set_xlabel("STD retention")
    ax.set_ylabel("Fleet IQR10 gain vs baseline")
    ax.set_title("Step12B STD retention vs IQR10 temporal-variability gain")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


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


def make_report(outdir: Path, fleet: pd.DataFrame, vehicle: pd.DataFrame, map_checks: pd.DataFrame, checks: dict[str, Any]) -> None:
    focus = fleet[fleet["case_id"].isin(["C06_representative", "October_control"])].copy()
    best = focus.sort_values(["case_id", "fleet_iqr10_collected_total"], ascending=[True, False]).groupby("case_id").head(5)
    gain = focus.sort_values(["case_id", "fleet_IQR10_gain_vs_baseline"], ascending=[True, False]).groupby("case_id").head(5)
    lines = [
        "# Step12B IQR10 Temporal-Variability Proxy",
        "",
        "This is post-processing only. The planner was not rerun.",
        "",
        "IQR10 is the interquartile range of temperature over the previous 10 available days at each ROI cell. It is a robust temporal-variability proxy, not data assimilation and not evidence of uncertainty reduction.",
        "",
        "The diagnostic indicates whether existing trajectories sample recently variable regions that may be relevant for future model-uncertainty, adaptive-sampling, or assimilation-aware experiments.",
        "",
        "## IQR10 Window Validation",
        md_table(map_checks, ["case_id", "date", "iqr10_previous_days_used", "iqr10_window_start_date", "iqr10_window_end_date", "iqr10_raw_min", "iqr10_raw_max", "iqr10_raw_mean", "iqr10_raw_finite_cells"]),
        "",
        "## Best Fleet Routes by IQR10 Collected",
        md_table(best, ["case_id", "date", "strategy", "fleet_iqr10_collected_total", "fleet_iqr10_collected_per_km", "mean_percentage_path_in_top10_IQR10", "fleet_collected_STD", "STD_retention", "fleet_trajectory_length"]),
        "",
        "## Best Fleet Routes by IQR10 Gain vs Baseline",
        md_table(gain, ["case_id", "date", "strategy", "fleet_IQR10_gain_vs_baseline", "fleet_IQR10_retention_vs_baseline", "fleet_IQR10_gain_pct_vs_baseline", "fleet_iqr10_collected_total", "baseline_fleet_iqr10_collected_total", "STD_retention"]),
        "",
        "## Validation Checks",
        f"- Vehicle rows processed: {checks['vehicle_rows']}",
        f"- Fleet rows produced: {checks['fleet_rows']}",
        f"- Vehicle routes mapped: {checks['vehicle_routes_mapped']}/{checks['vehicle_rows']}",
        f"- Fleet baseline comparisons available: {checks['fleet_baseline_comparisons_available']}/{checks['fleet_rows']}",
        f"- Planner rerun: `{checks['planner_rerun']}`",
    ]
    (outdir / "step12b_iqr10_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add IQR10 post-processing metrics to existing Step12B results.")
    parser.add_argument("--step12b", type=Path, default=DEFAULT_STEP12B)
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    args = parser.parse_args()

    step12b = args.step12b.resolve()
    step00 = args.step00.resolve()
    figdir = step12b / "figures"
    figdir.mkdir(exist_ok=True)

    temp_path, dates_path, mask_path, searched = locate_temperature_inputs(step00)
    temp_stack = np.load(temp_path, mmap_mode="r")
    dates = pd.read_csv(dates_path)
    mask = np.load(mask_path).astype(bool)
    if temp_stack.shape[1:] != ROI_SHAPE or mask.shape != ROI_SHAPE:
        raise ValueError(f"Unexpected ROI shapes: temp={temp_stack.shape}, mask={mask.shape}")

    manifest = pd.read_csv(step12b / "step12b_run_manifest.csv")
    diagnostics = pd.read_csv(step12b / "step12b_solver_diagnostics.csv")
    vehicle = pd.read_csv(step12b / "step12b_vehicle_level_metrics.csv")
    fleet_existing = pd.read_csv(step12b / "step12b_fleet_level_metrics.csv")

    manifest["date"] = pd.to_datetime(manifest["date"]).dt.strftime("%Y-%m-%d")
    case_dates = manifest[["case_id", "date"]].drop_duplicates()
    cases = case_dates.reset_index(drop=True)
    case_maps, map_checks = compute_iqr10_maps(cases, temp_stack, dates, mask, step12b)

    date_by_case = dict(case_dates.values.tolist())
    run_dir_by_id = dict(zip(diagnostics["run_id"].astype(str), diagnostics["run_dir"].astype(str)))
    s11a = load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")
    lat_hres = np.load(HRES / "LAT_hres.npy")
    lon_hres = np.load(HRES / "LON_hres.npy")

    rows = []
    route_counts = []
    for _, row in vehicle.iterrows():
        out = row.to_dict()
        case_id = str(row["case_id"])
        date = date_by_case.get(case_id, "")
        out["date"] = date
        maps = case_maps[(case_id, date)]
        run_dir_text = run_dir_by_id.get(str(row["run_id"]), "")
        run_dir = Path(run_dir_text)
        if run_dir_text and not run_dir.is_absolute():
            run_dir = ROOT / run_dir
        vehicle_id = int(row["vehicle_id"]) if str(row["vehicle_id"]).strip().isdigit() else None
        points = route_roi_points_for_vehicle(s11a, run_dir, vehicle_id, lat_hres, lon_hres, mask) if run_dir_text else []
        route_counts.append(len(points))
        length_km = float(row.get("trajectory_length", float("nan")))
        out.update(sample_route_metrics(points, maps["norm"], maps["raw"], float(maps["meta"]["iqr10_norm_p90"]), length_km))
        out["iqr10_route_points_roi"] = "|".join(f"{r}:{c}" for r, c in points)
        out["run_dir"] = run_dir_text
        out.update({k: v for k, v in maps["meta"].items() if k.startswith("iqr10_") or k in {"planning_time_index"}})
        rows.append(out)

    vehicle_iqr = pd.DataFrame(rows)
    fleet_iqr = make_fleet(vehicle_iqr, fleet_existing)
    focus_summary = (
        fleet_iqr[fleet_iqr["case_id"].isin(["C06_representative", "October_control"])]
        .sort_values(["case_id", "fleet_IQR10_gain_vs_baseline"], ascending=[True, False])
        .reset_index(drop=True)
    )

    vehicle_iqr.to_csv(step12b / "step12b_iqr10_vehicle_metrics.csv", index=False)
    fleet_iqr.to_csv(step12b / "step12b_iqr10_fleet_metrics.csv", index=False)
    focus_summary.to_csv(step12b / "step12b_iqr10_other_days_summary.csv", index=False)
    map_checks.to_csv(step12b / "iqr10_maps" / "step12b_iqr10_map_checks.csv", index=False)

    plot_case_bars(focus_summary, figdir / "step12b_iqr10_gain_vs_baseline_other_days.png")
    plot_retention_scatter(focus_summary, figdir / "step12b_STD_retention_vs_IQR10_gain_other_days.png")

    checks = {
        "planner_rerun": False,
        "step12b": rel(step12b),
        "temperature_stack": rel(temp_path),
        "dates_csv": rel(dates_path),
        "mask": rel(mask_path),
        "searched_files": searched,
        "cases": cases.to_dict(orient="records"),
        "vehicle_rows": int(len(vehicle_iqr)),
        "fleet_rows": int(len(fleet_iqr)),
        "vehicle_routes_mapped": int(np.sum(np.asarray(route_counts) > 0)),
        "min_route_valid_cells": int(np.min(route_counts)) if route_counts else 0,
        "max_route_valid_cells": int(np.max(route_counts)) if route_counts else 0,
        "fleet_baseline_comparisons_available": int(fleet_iqr["iqr10_baseline_comparison_exists"].sum()),
        "outputs": {
            "vehicle_metrics": rel(step12b / "step12b_iqr10_vehicle_metrics.csv"),
            "fleet_metrics": rel(step12b / "step12b_iqr10_fleet_metrics.csv"),
            "other_days_summary": rel(step12b / "step12b_iqr10_other_days_summary.csv"),
            "report": rel(step12b / "step12b_iqr10_report.md"),
            "figures": [
                rel(figdir / "step12b_iqr10_gain_vs_baseline_other_days.png"),
                rel(figdir / "step12b_STD_retention_vs_IQR10_gain_other_days.png"),
            ],
        },
    }
    (step12b / "step12b_iqr10_checks.json").write_text(json.dumps(checks, indent=2, default=json_default), encoding="utf-8")
    make_report(step12b, fleet_iqr, vehicle_iqr, map_checks, checks)
    print(json.dumps(checks, indent=2, default=json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
