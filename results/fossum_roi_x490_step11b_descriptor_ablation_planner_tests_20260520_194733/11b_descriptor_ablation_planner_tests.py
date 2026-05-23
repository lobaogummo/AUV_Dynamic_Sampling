"""Step11B: descriptor ablation tests in Lucrezia planner.

Runs one descriptor at a time:
- baseline STD only
- STD + boundary
- STD + gradient
- STD + heterogeneity
- STD + representative_zone
- STD + interest

Formula:
information_map = (1 - alpha) * STD_norm + alpha * descriptor_norm

Default execution is the mandatory first case only:
2024-08-24 / C01_representative / 1 AUV / 12h.
Use --cases all to repeat for C06 and October.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"
SCRIPTS_ROOT = ROOT / "scripts"

DEFAULT_STEP10F = RESULTS_ROOT / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
DEFAULT_STEP09B = RESULTS_ROOT / "fossum_roi_x490_step09b_top20_c01_c06_temppred_classification_20260519_190144"
DEFAULT_STEP09 = RESULTS_ROOT / "fossum_roi_x490_step09_october_temppred_descriptor_assignment_20260515_165018"
DEFAULT_STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_HRES = RESULTS_ROOT / "cmems_370_surface_to_hres_20260509_135642"
DEFAULT_PLANNER = ROOT / "OptimalPlanning_Lucrezia"

DESCRIPTORS = ["boundary", "gradient", "heterogeneity", "representative_zone", "interest"]
ALPHAS = [0.25, 0.50]
CASE_ORDER = ["C01_representative", "C06_representative", "October_control"]
CASE_ALIASES = {"c01": ["C01_representative"], "c06": ["C06_representative"], "october": ["October_control"], "all": CASE_ORDER}
EXPECTED_SHAPE = (72, 117)
EXPECTED_VALID_CELLS = 8004


def load_step11a_module():
    path = SCRIPTS_ROOT / "11a_run_minimal_boundary_planner_comparison.py"
    spec = importlib.util.spec_from_file_location("step11a_utils", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import Step11A utilities from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return None if not math.isfinite(value) else value
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return path


def safe_name(text: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def minmax01(arr: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    vals = arr[mask & np.isfinite(arr)]
    if vals.size == 0:
        out[mask] = 0.0
        return out, {"vmin": float("nan"), "vmax": float("nan")}
    mn = float(np.nanmin(vals))
    mx = float(np.nanmax(vals))
    if mx - mn <= 1e-12:
        out[mask] = 0.0
    else:
        out[mask] = ((arr[mask] - mn) / (mx - mn)).astype(np.float32)
    return out, {"vmin": mn, "vmax": mx}


def top_overlap(a: np.ndarray, b: np.ndarray, mask: np.ndarray, percentile: float = 90.0) -> float:
    valid = mask & np.isfinite(a) & np.isfinite(b)
    if not np.any(valid):
        return float("nan")
    av = a[valid]
    bv = b[valid]
    return float(np.mean((av >= np.nanpercentile(av, percentile)) & (bv >= np.nanpercentile(bv, percentile))))


def area_covered(points: list[tuple[int, int]]) -> int:
    return int(len(set(points)))


def mean_distance_between_paths(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> float:
    if not a or not b:
        return float("nan")
    aa = np.array(list(set(a)), dtype=float)
    bb = np.array(list(set(b)), dtype=float)
    sample = aa if len(aa) <= 300 else aa[np.linspace(0, len(aa) - 1, 300).astype(int)]
    d = np.sqrt(((sample[:, None, :] - bb[None, :, :]) ** 2).sum(axis=2))
    return float(np.mean(np.min(d, axis=1)))


def crossing_count(points: list[tuple[int, int]], descriptor_full: np.ndarray) -> int:
    if len(points) < 2:
        return 0
    vals = []
    for r, c in points:
        if 0 <= r < descriptor_full.shape[0] and 0 <= c < descriptor_full.shape[1]:
            vals.append(descriptor_full[r, c])
    vals = np.array(vals, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size < 2:
        return 0
    thr = float(np.nanpercentile(descriptor_full[np.isfinite(descriptor_full)], 90))
    high = vals >= thr
    return int(np.sum(high[1:] != high[:-1]))


def load_cases_and_maps(step10f: Path, step09b: Path, step09: Path, mask: np.ndarray) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    cases = pd.read_csv(require(step10f / "step10f_minimal_boundary_planner_cases.csv", "Step10F cases"))
    cases["date"] = pd.to_datetime(cases["date"]).dt.strftime("%Y-%m-%d")
    cases["case_order"] = cases["case_id"].map({case: i for i, case in enumerate(CASE_ORDER)})
    cases = cases.sort_values("case_order").reset_index(drop=True)
    maps: dict[str, np.ndarray] = {
        "TEMPpred": np.load(require(step10f / "planner_cases_TEMPpred_roi_x490.npy", "Step10F TEMPpred")).astype(np.float32),
        "STD_norm": np.load(require(step10f / "planner_cases_STD_norm_roi_x490.npy", "Step10F STD_norm")).astype(np.float32),
    }
    descriptor_case_maps = {name: [] for name in DESCRIPTORS}
    step09b_assign = pd.read_csv(require(step09b / "step09b_classification_assignments.csv", "Step09B assignments"))
    step09b_assign["date"] = pd.to_datetime(step09b_assign["date"]).dt.strftime("%Y-%m-%d")
    step09_assign = pd.read_csv(require(step09 / "step09_temppred_classification_assignments.csv", "Step09 assignments"))
    step09_assign["date"] = pd.to_datetime(step09_assign["date"]).dt.strftime("%Y-%m-%d")
    step09b_maps = {name: np.load(require(step09b / f"step09b_assigned_descriptor_{name}_map.npy", f"Step09B {name}")) for name in DESCRIPTORS}
    step09_maps = {name: np.load(require(step09 / f"step09_assigned_descriptor_{name}_map.npy", f"Step09 {name}")) for name in DESCRIPTORS}
    for _, row in cases.iterrows():
        date = str(row["date"])
        if str(row["source"]) == "top20_step10e":
            idx = int(step09b_assign.index[step09b_assign["date"] == date][0])
            source_maps = step09b_maps
        else:
            idx = int(step09_assign.index[step09_assign["date"] == date][0])
            source_maps = step09_maps
        for name in DESCRIPTORS:
            arr, _scale = minmax01(source_maps[name][idx].astype(np.float32), mask)
            descriptor_case_maps[name].append(arr)
    for name in DESCRIPTORS:
        maps[name] = np.stack(descriptor_case_maps[name]).astype(np.float32)
    return cases, maps


def save_descriptor_panel(case_id: str, maps: dict[str, np.ndarray], case_idx: int, run_points: dict[str, list[tuple[int, int]]], out_path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.2), squeeze=False)
    panels = ["STD_norm", "boundary", "gradient", "heterogeneity", "representative_zone", "interest"]
    colors = {
        "baseline_STD": "white",
        "boundary_alpha050": "#ffea00",
        "gradient_alpha050": "#00e5ff",
        "heterogeneity_alpha050": "#ff66cc",
        "representative_zone_alpha050": "#00ff66",
        "interest_alpha050": "#ff8c00",
    }
    for ax, name in zip(axes.ravel(), panels):
        arr = maps[name][case_idx]
        im = ax.imshow(arr, origin="lower", cmap="viridis", vmin=0, vmax=1, aspect="auto")
        for run_name, points in run_points.items():
            if run_name == "baseline_STD" or run_name.endswith("alpha050"):
                roi_points = [(r - 55, c - 47) for r, c in points if 55 <= r <= 126 and 47 <= c <= 163]
                if len(roi_points) > 1:
                    yy = [p[0] for p in roi_points]
                    xx = [p[1] for p in roi_points]
                    ax.plot(xx, yy, color=colors.get(run_name, "black"), linewidth=1.2, label=run_name)
        ax.set_title(name)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    axes[0, 0].legend(loc="lower left", fontsize=6)
    fig.suptitle(f"Step11B descriptor ablation trajectories | {case_id}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_bar(df: pd.DataFrame, metric: str, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4.5))
    labels = [f"{r.descriptor}\n{r.alpha_label}" for r in df.itertuples()]
    ax.bar(np.arange(len(df)), df[metric].astype(float))
    ax.set_xticks(np.arange(len(df)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step11B descriptor ablation planner tests.")
    parser.add_argument("--cases", choices=["c01", "c06", "october", "all"], default="c01")
    parser.add_argument("--step10f", type=Path, default=DEFAULT_STEP10F)
    parser.add_argument("--step09b", type=Path, default=DEFAULT_STEP09B)
    parser.add_argument("--step09", type=Path, default=DEFAULT_STEP09)
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--hres", type=Path, default=DEFAULT_HRES)
    parser.add_argument("--planner", type=Path, default=DEFAULT_PLANNER)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--mission-duration-hours", type=float, default=12.0)
    parser.add_argument("--auv-number", type=int, default=1)
    parser.add_argument("--timeout-s", type=int, default=1800)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    s11a = load_step11a_module()
    out_dir = (args.output_root.resolve() / f"fossum_roi_x490_step11b_descriptor_ablation_planner_tests_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    for sub in ["planner_inputs", "planner_configs", "planner_runs", "figures"]:
        (out_dir / sub).mkdir()
    fig_dir = out_dir / "figures"

    mask = np.load(require(args.step00 / "mask_common_roi_x490.npy", "Step00 mask")).astype(bool)
    lat_hres = np.load(require(args.hres / "LAT_hres.npy", "HRes LAT"))
    lon_hres = np.load(require(args.hres / "LON_hres.npy", "HRes LON"))
    bathy_hres = np.load(require(args.hres / "BATHY_hres.npy", "HRes BATHY"))
    if int(mask.sum()) != EXPECTED_VALID_CELLS:
        raise ValueError(f"Unexpected mask valid cells: {int(mask.sum())}")

    cases, maps = load_cases_and_maps(args.step10f, args.step09b, args.step09, mask)
    selected_cases = CASE_ALIASES[args.cases]
    cases = cases[cases["case_id"].isin(selected_cases)].copy().reset_index(drop=True)
    original_cases, _all_maps = load_cases_and_maps(args.step10f, args.step09b, args.step09, mask)
    case_global_idx = {row.case_id: int(row.case_order) for row in original_cases.itertuples()}

    original_config = s11a.read_config_text(require(args.planner / "Config_file.py", "Lucrezia Config_file.py"))
    runtime_config = s11a.generated_config(
        original_config,
        single_auv=args.auv_number == 1,
        mission_duration_hours=args.mission_duration_hours,
        auv_number=args.auv_number,
    )
    config_name = f"Config_file_step11b_{args.auv_number}auv_{args.mission_duration_hours:g}h.py"
    (out_dir / "planner_configs" / config_name).write_text(runtime_config, encoding="utf-8")

    run_specs = [("baseline_STD", "baseline", "none", 0.0, "STD_norm")]
    for descriptor in DESCRIPTORS:
        for alpha in ALPHAS:
            run_specs.append((f"{descriptor}_alpha{int(alpha*100):03d}", "descriptor", descriptor, alpha, descriptor))

    all_info_maps = {}
    manifest_rows = []
    metrics_rows = []
    solver_rows = []
    comparison_rows = []
    ranking_source_rows = []
    run_points_by_case: dict[str, dict[str, list[tuple[int, int]]]] = {case: {} for case in selected_cases}
    baseline_points_by_case: dict[str, set[tuple[int, int]]] = {}

    for _, case in cases.iterrows():
        case_id = str(case["case_id"])
        global_idx = case_global_idx[case_id]
        std_roi = maps["STD_norm"][global_idx].astype(np.float32)
        for run_name, run_kind, descriptor, alpha, descriptor_map_name in run_specs:
            if run_kind == "baseline":
                info_roi = std_roi.copy()
                descriptor_roi = np.zeros_like(std_roi)
            else:
                descriptor_roi = maps[descriptor][global_idx].astype(np.float32)
                info_roi = ((1 - alpha) * std_roi + alpha * descriptor_roi).astype(np.float32)
                info_roi[~mask] = np.nan
            all_info_maps[f"{case_id}__{run_name}"] = info_roi
            run_id = f"{case_id}__{run_name}"
            run_dir = out_dir / "planner_runs" / safe_name(run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            input_nc = out_dir / "planner_inputs" / f"{safe_name(run_id)}_planner_interface.nc"
            nc_meta = s11a.build_interface_nc(input_nc, info_roi, mask, lat_hres, lon_hres, bathy_hres)
            shutil.copy2(input_nc, run_dir / input_nc.name)
            s11a.copy_planner_runtime(args.planner, run_dir, runtime_config)
            (run_dir / "run_config.json").write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "case_id": case_id,
                        "date": str(case["date"]),
                        "descriptor": descriptor,
                        "alpha": alpha,
                        "mission_duration_hours": args.mission_duration_hours,
                        "auv_number": args.auv_number,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            status = "NOT_RUN"
            error = ""
            try:
                run_result = s11a.run_planner(run_dir, input_nc, args.timeout_s)
                status = "SUCCESS" if run_result["returncode"] == 0 and (run_dir / "routes_file.txt").exists() else "FAILED"
            except Exception as exc:
                run_result = {"command": f"{sys.executable} OptimalPlanning.py {input_nc}", "returncode": -998, "runtime_s": float("nan")}
                status = "FAILED"
                error = repr(exc)
                (run_dir / "planner_stderr.txt").write_text(error, encoding="utf-8", errors="replace")
            routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
            s11a.save_trajectory_csv_json(run_dir, routes)
            info_full = s11a.embed_roi_to_hres(info_roi, mask, fill=np.nan)
            std_full = s11a.embed_roi_to_hres(std_roi, mask, fill=np.nan)
            descriptor_full = s11a.embed_roi_to_hres(descriptor_roi if run_kind != "baseline" else maps["boundary"][global_idx], mask, fill=np.nan)
            baseline_set = baseline_points_by_case.get(case_id)
            run_metrics = s11a.path_metrics(routes, lat_hres, lon_hres, info_full, std_full, descriptor_full, baseline_set)
            points = s11a.route_grid_points(routes, lat_hres, lon_hres)
            run_points_by_case[case_id][run_name] = points
            if run_name == "baseline_STD":
                baseline_points_by_case[case_id] = set(points)
                run_metrics["trajectory_overlap_ratio_with_baseline"] = 1.0 if points else float("nan")
                run_metrics["trajectory_difference_from_baseline"] = 0.0 if points else float("nan")
            total_length = float(np.nansum([r["length_km"] for r in routes])) if routes else float("nan")
            mission_duration = float(np.nansum([(r.get("mission_duration_h") or 0) + (r.get("mission_duration_m") or 0) / 60 for r in routes])) if routes else float("nan")
            descriptor_top10 = s11a.embed_roi_to_hres(descriptor_roi, mask, fill=np.nan)
            boundary_full = s11a.embed_roi_to_hres(maps["boundary"][global_idx], mask, fill=np.nan)
            manifest_rows.append(
                {
                    "run_id": run_id,
                    "case_id": case_id,
                    "date": str(case["date"]),
                    "descriptor": descriptor,
                    "alpha": alpha,
                    "alpha_label": "baseline" if alpha == 0 else f"alpha{int(alpha*100):03d}",
                    "status": status,
                    "returncode": run_result["returncode"],
                    "input_nc": str(input_nc),
                    "run_dir": str(run_dir),
                }
            )
            extra_metrics = {
                "trajectory_length_km": total_length,
                "mission_duration_h": mission_duration,
                "solver_runtime_s": run_result["runtime_s"],
                "trajectory_area_covered": area_covered(points),
                "mean_distance_from_baseline": mean_distance_between_paths(points, list(baseline_points_by_case.get(case_id, set()))) if run_name != "baseline_STD" else 0.0,
                "percentage_path_in_top10_descriptor": run_metrics.get("percentage_path_in_top10_boundary", float("nan")),
                "boundary_crossing_count_proxy": crossing_count(points, boundary_full),
                "number_of_distinct_regime_zones_visited_proxy": int(len(np.unique(np.digitize([descriptor_top10[p] for p in points if 0 <= p[0] < 180 and 0 <= p[1] < 240 and np.isfinite(descriptor_top10[p])], [0.33, 0.66])))) if points else 0,
            }
            row_metrics = {
                "run_id": run_id,
                "case_id": case_id,
                "date": str(case["date"]),
                "descriptor": descriptor,
                "alpha": alpha,
                "alpha_label": "baseline" if alpha == 0 else f"alpha{int(alpha*100):03d}",
                "solver_status": status,
                **extra_metrics,
                **run_metrics,
            }
            metrics_rows.append(row_metrics)
            solver_rows.append({"run_id": run_id, "case_id": case_id, "descriptor": descriptor, "alpha": alpha, "status": status, "returncode": run_result["returncode"], "runtime_s": run_result["runtime_s"], "error": error, **nc_meta})

    metrics_df = pd.DataFrame(metrics_rows)
    manifest_df = pd.DataFrame(manifest_rows)
    solver_df = pd.DataFrame(solver_rows)
    for case_id in selected_cases:
        base = metrics_df[(metrics_df.case_id == case_id) & (metrics_df.descriptor == "none")]
        if base.empty:
            continue
        base = base.iloc[0]
        for _, row in metrics_df[(metrics_df.case_id == case_id) & (metrics_df.descriptor != "none")].iterrows():
            comparison_rows.append(
                {
                    "case_id": case_id,
                    "date": row["date"],
                    "descriptor": row["descriptor"],
                    "alpha": row["alpha"],
                    "overlap_ratio_with_baseline": row["trajectory_overlap_ratio_with_baseline"],
                    "trajectory_difference_from_baseline": row["trajectory_difference_from_baseline"],
                    "mean_distance_from_baseline": row["mean_distance_from_baseline"],
                    "delta_collected_descriptor_score": row["collected_boundary_score"] - base["collected_boundary_score"],
                    "delta_collected_STD_score": row["collected_STD_score"] - base["collected_STD_score"],
                    "trajectory_area_covered": row["trajectory_area_covered"],
                    "percentage_path_in_top10_descriptor": row["percentage_path_in_top10_descriptor"],
                }
            )
    comparison_df = pd.DataFrame(comparison_rows)
    ranking_df = (
        comparison_df.groupby("descriptor", as_index=False)
        .agg(
            mean_trajectory_difference=("trajectory_difference_from_baseline", "mean"),
            mean_distance_from_baseline=("mean_distance_from_baseline", "mean"),
            mean_delta_descriptor_score=("delta_collected_descriptor_score", "mean"),
            mean_area_covered=("trajectory_area_covered", "mean"),
            mean_top10_descriptor_path=("percentage_path_in_top10_descriptor", "mean"),
        )
        .sort_values(["mean_trajectory_difference", "mean_delta_descriptor_score"], ascending=False)
    )

    manifest_df.to_csv(out_dir / "step11b_run_manifest.csv", index=False)
    metrics_df.to_csv(out_dir / "step11b_run_metrics.csv", index=False)
    comparison_df.to_csv(out_dir / "step11b_descriptor_ablation_comparison.csv", index=False)
    ranking_df.to_csv(out_dir / "step11b_descriptor_ranking.csv", index=False)
    solver_df.to_csv(out_dir / "step11b_solver_diagnostics.csv", index=False)
    np.savez_compressed(out_dir / "step11b_information_maps_by_descriptor.npz", **all_info_maps)

    for case_id in selected_cases:
        global_idx = case_global_idx[case_id]
        save_descriptor_panel(case_id, maps, global_idx, run_points_by_case[case_id], fig_dir / f"step11b_{case_id}_descriptor_trajectories_panel.png")
    if selected_cases:
        plot_bar(metrics_df[metrics_df.descriptor != "none"], "collected_boundary_score", "Collected descriptor score proxy", fig_dir / "step11b_collected_scores_barplot.png")
        plot_bar(metrics_df[metrics_df.descriptor != "none"], "trajectory_difference_from_baseline", "Trajectory difference from baseline", fig_dir / "step11b_distance_from_baseline_barplot.png")
    for p in fig_dir.glob("*.png"):
        shutil.copy2(p, out_dir / p.name)

    successful = int((manifest_df.status == "SUCCESS").sum())
    failed = int(len(manifest_df) - successful)
    verdict = "STEP11B_DESCRIPTOR_ABLATION_COMPLETED" if failed == 0 else "STEP11B_COMPLETED_WITH_WARNINGS"
    checks = {
        "cases": selected_cases,
        "planned_runs": int(len(manifest_df)),
        "successful_runs": successful,
        "failed_runs": failed,
        "descriptors_tested": DESCRIPTORS,
        "alphas": ALPHAS,
        "mission_duration_hours": args.mission_duration_hours,
        "auv_number": args.auv_number,
        "verdict": verdict,
    }
    write_json(out_dir / "step11b_checks.json", checks)

    top_descriptor = str(ranking_df.iloc[0]["descriptor"]) if not ranking_df.empty else "none"
    ranking_lines = [
        f"- {r.descriptor}: mean trajectory diff={float(r.mean_trajectory_difference):.3f}, mean delta descriptor={float(r.mean_delta_descriptor_score):.3f}, mean area={float(r.mean_area_covered):.1f}"
        for r in ranking_df.itertuples()
    ]
    summary = [
        "# Step11B Descriptor Ablation Planner Tests",
        "",
        f"- Output: `{out_dir}`",
        f"- Cases: {', '.join(selected_cases)}",
        f"- Runtime: {args.auv_number} AUV(s), {args.mission_duration_hours:g}h",
        f"- Runs: {successful}/{len(manifest_df)} successful",
        f"- Best single-AUV descriptor in this run: `{top_descriptor}`",
        "",
        "## Descriptor Ranking",
        *ranking_lines,
        "",
        "## Interpretation",
        "- Each descriptor was tested separately; no descriptor mixing beyond STD + one descriptor.",
        "- Boundary redundancy with STD can be assessed by comparing boundary rank and overlap/difference metrics.",
        "- Multi-AUV recommendation is not inferred from this single-AUV ablation unless --auv-number 2 is used.",
        "",
        "## Verdict",
        verdict,
    ]
    (out_dir / "step11b_summary.md").write_text("\n".join(summary), encoding="utf-8")
    (out_dir / "step11b_report.md").write_text("\n".join(summary), encoding="utf-8")
    (out_dir / "step11b_next_step_recommendation.md").write_text(
        "\n".join(["# Step11B Next Step", "", f"Carry `{top_descriptor}` into Step11C for targeted comparison, then repeat the ablation for C06 and October if not already run.", "", verdict]),
        encoding="utf-8",
    )
    shutil.copy2(Path(__file__).resolve(), out_dir / Path(__file__).name)
    print(f"Step11B complete: {out_dir}")
    print(f"Runs successful: {successful}/{len(manifest_df)}")
    print(f"Top descriptor: {top_descriptor}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
