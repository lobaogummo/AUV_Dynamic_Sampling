#!/usr/bin/env python
"""Step11AD: predModel panel figures for legacy Step11 planner outputs.

Read-only post-process for Step11A/B/C/D. It does not rerun the planner and
does not alter previous outputs. It creates new panel figures where each method
or strategy gets its own panel over the day-specific Step10F TEMPpred predModel.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SCRIPTS = ROOT / "scripts"
HRES = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
STEP10F = RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
STEP11A = RESULTS / "fossum_roi_x490_step11a_minimal_boundary_planner_runs_20260520_102117"
STEP11B_OUTPUTS = [
    RESULTS / "fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_160652",
    RESULTS / "fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_165239",
    RESULTS / "fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_194733",
]
STEP11C = RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322"
STEP11D = RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809"
ROI_ROW_MIN = 55
ROI_COL_MIN = 47
ROI_SHAPE = (72, 117)


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int = 40) -> str:
    if df.empty:
        return "_No data available._\n"
    view = df[[c for c in columns if c in df.columns]].head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.3f}")
        else:
            view[col] = view[col].fillna("").astype(str)
    out = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join("---" for _ in view.columns) + " |"]
    for row in view.astype(str).values.tolist():
        out.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
    return "\n".join(out) + "\n"


def load_step10f() -> tuple[dict[str, int], np.ndarray, np.ndarray]:
    z = np.load(STEP10F / "planner_minimal_boundary_input_maps.npz", allow_pickle=True)
    case_ids = [str(x) for x in z["case_ids"]]
    return {case: i for i, case in enumerate(case_ids)}, np.asarray(z["TEMPpred"], dtype=float), np.asarray(z["mask"], dtype=bool)


def load_routes(route_json: Path) -> list[dict[str, Any]]:
    if not route_json.exists():
        return []
    try:
        return json.loads(route_json.read_text(encoding="utf-8")).get("routes", [])
    except Exception:
        return []


def routes_to_roi_points(s11a, routes: list[dict[str, Any]], lat: np.ndarray, lon: np.ndarray) -> dict[int, list[tuple[int, int]]]:
    out: dict[int, list[tuple[int, int]]] = {}
    for i, route in enumerate(routes, start=1):
        rid = int(route.get("route_id", i))
        pts = s11a.route_grid_points([route], lat, lon)
        out[rid] = [(r - ROI_ROW_MIN, c - ROI_COL_MIN) for r, c in pts]
    return out


def route_dir_from_manifest(base: Path, run_dir_text: Any, fallback_name: str = "") -> Path:
    text = "" if pd.isna(run_dir_text) else str(run_dir_text)
    p = Path(text)
    if p.exists():
        return p
    marker = "planner_runs"
    if marker in text:
        tail = text.split(marker, 1)[1].lstrip("\\/")
        candidate = base / "planner_runs" / tail
        if candidate.exists():
            return candidate
    if fallback_name:
        return base / "planner_runs" / fallback_name
    return p


def plot_panel(
    panels: list[dict[str, Any]],
    background: np.ndarray,
    out_path: Path,
    title: str,
    ncols: int,
    contours: list[tuple[np.ndarray, str, str]] | None = None,
) -> None:
    if not panels:
        return
    nrows = int(math.ceil(len(panels) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.6 * ncols, 4.15 * nrows), squeeze=False)
    vmin = float(np.nanpercentile(background, 2))
    vmax = float(np.nanpercentile(background, 98))
    im = None
    for ax in axes.ravel():
        ax.axis("off")
    for ax, panel in zip(axes.ravel(), panels):
        im = ax.imshow(background, origin="lower", aspect="auto", cmap="coolwarm", vmin=vmin, vmax=vmax)
        if contours:
            for arr, color, label in contours:
                if arr is not None and np.any(arr):
                    ax.contour(arr.astype(float), levels=[0.5], colors=[color], linewidths=0.8, alpha=0.85)
        for label, pts, color, style in panel.get("paths", []):
            if pts:
                ax.plot([p[1] for p in pts], [p[0] for p in pts], marker="o", markersize=2, linewidth=1.5, color=color, linestyle=style, label=label)
        if panel.get("metrics"):
            ax.text(
                0.015,
                0.02,
                "\n".join(panel["metrics"]),
                transform=ax.transAxes,
                fontsize=8,
                bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none", "pad": 3},
                va="bottom",
            )
        ax.set_title(panel["title"], fontsize=10)
        ax.set_xlim(-1, ROI_SHAPE[1])
        ax.set_ylim(-1, ROI_SHAPE[0])
        ax.set_xlabel("ROI column")
        ax.set_ylabel("ROI row")
        if panel.get("paths"):
            ax.legend(fontsize=7, loc="upper right")
        ax.axis("on")
    fig.suptitle(title, fontsize=15)
    if im is not None:
        cbar = fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.025, pad=0.012)
        cbar.set_label("TEMPpred, degC")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def case_temp(case_idx: dict[str, int], temp: np.ndarray, case_id: str) -> np.ndarray:
    return temp[case_idx[case_id]]


def panel_paths_from_route_dir(s11a, route_dir: Path, lat: np.ndarray, lon: np.ndarray) -> dict[int, list[tuple[int, int]]]:
    return routes_to_roi_points(s11a, load_routes(route_dir / "trajectory_routes.json"), lat, lon)


def make_step11a(s11a, lat: np.ndarray, lon: np.ndarray, case_idx: dict[str, int], temp: np.ndarray, out_fig: Path, manifest_rows: list[dict[str, Any]]) -> None:
    metrics = pd.read_csv(STEP11A / "step11a_run_metrics.csv")
    colors = {"baseline_STD": "black", "enriched_boundary_alpha025": "#f6ad00", "enriched_boundary_alpha050": "#00a3c4"}
    for case_id, grp in metrics.groupby("case_id", sort=False):
        panels = []
        for _, row in grp.iterrows():
            run = str(row["formulation"])
            route_dir = STEP11A / "planner_runs" / f"{case_id}__{run}"
            pts = next(iter(panel_paths_from_route_dir(s11a, route_dir, lat, lon).values()), [])
            panels.append(
                {
                    "title": run,
                    "paths": [(run, pts, colors.get(run, "black"), "-")],
                    "metrics": [
                        f"STD={float(row['collected_STD_score']):.1f}",
                        f"boundary={float(row['collected_boundary_score']):.1f}",
                        f"diff={float(row['trajectory_difference_from_baseline']):.2f}",
                    ],
                }
            )
        fname = f"step11a_{case_id}_predmodel_panel_by_method.png"
        plot_panel(panels, case_temp(case_idx, temp, case_id), out_fig / fname, f"Step11A {case_id}: baseline vs boundary-enriched over day predModel", 3)
        manifest_rows.append({"step": "Step11A", "case_id": case_id, "figure": fname, "methods_included": ",".join(grp["formulation"].astype(str)), "background": "TEMPpred"})


def make_step11b(s11a, lat: np.ndarray, lon: np.ndarray, case_idx: dict[str, int], temp: np.ndarray, out_fig: Path, manifest_rows: list[dict[str, Any]]) -> None:
    for base in STEP11B_OUTPUTS:
        metrics = pd.read_csv(base / "step11b_run_metrics.csv")
        case_id = str(metrics["case_id"].dropna().iloc[0])
        panels = []
        for _, row in metrics.iterrows():
            descriptor = str(row["descriptor"])
            alpha = float(row["alpha"])
            run_name = "baseline_STD" if descriptor == "none" else f"{descriptor}_alpha{int(round(alpha * 100)):03d}"
            route_dir = base / "planner_runs" / f"{case_id}__{run_name}"
            pts_by_route = panel_paths_from_route_dir(s11a, route_dir, lat, lon)
            pts = next(iter(pts_by_route.values()), [])
            status = str(row["solver_status"])
            title = run_name
            panels.append(
                {
                    "title": title,
                    "paths": [(run_name, pts, "black" if descriptor == "none" else "#00a3c4", "-")],
                    "metrics": [
                        f"status={status}",
                        f"desc={descriptor}, a={alpha:.2f}",
                        f"cross={int(row.get('boundary_crossing_count_proxy', 0))}, regimes={int(row.get('number_of_distinct_regime_zones_visited_proxy', 0))}",
                        f"diff={float(row.get('trajectory_difference_from_baseline', np.nan)):.2f}",
                    ],
                }
            )
        fname = f"step11b_{case_id}_predmodel_panel_by_method_{base.name[-15:]}.png"
        plot_panel(panels, case_temp(case_idx, temp, case_id), out_fig / fname, f"Step11B {case_id}: descriptor ablation paths over day predModel", 4)
        manifest_rows.append({"step": "Step11B", "case_id": case_id, "figure": fname, "methods_included": ",".join(metrics.apply(lambda r: "baseline_STD" if r["descriptor"] == "none" else f"{r['descriptor']}_alpha{int(round(float(r['alpha'])*100)):03d}", axis=1)), "background": "TEMPpred", "source_output": rel(base)})


def make_step11c(s11a, lat: np.ndarray, lon: np.ndarray, case_idx: dict[str, int], temp: np.ndarray, out_fig: Path, manifest_rows: list[dict[str, Any]]) -> None:
    metrics = pd.read_csv(STEP11C / "step11c_crossing_metrics.csv")
    case_id = "C01_representative"
    contours = []
    ra = STEP11C / "region_A_mask.npy"
    rb = STEP11C / "region_B_mask.npy"
    if ra.exists() and rb.exists():
        contours = [(np.load(ra), "#2b6cb0", "region_A"), (np.load(rb), "#c53030", "region_B")]
    for duration, grp in metrics.groupby("mission_duration_requested_h", sort=False):
        panels = []
        for _, row in grp.iterrows():
            run = str(row["run_name"])
            route_dir = STEP11C / "planner_runs" / str(row["run_id"])
            pts = next(iter(panel_paths_from_route_dir(s11a, route_dir, lat, lon).values()), [])
            panels.append(
                {
                    "title": run,
                    "paths": [(run, pts, "#00a3c4" if "crossing" in run else ("#f6ad00" if "boundary" in run else "black"), "-")],
                    "metrics": [
                        f"regions={int(row['number_of_distinct_regions_visited'])}, cross={int(row['boundary_crossing_count'])}",
                        f"frac A={float(row['fraction_path_region_A']):.2f}, B={float(row['fraction_path_region_B']):.2f}",
                        f"core={float(row['fraction_path_boundary_core']):.2f}",
                    ],
                }
            )
        fname = f"step11c_C01_{int(duration)}h_predmodel_panel_by_method.png"
        plot_panel(panels, case_temp(case_idx, temp, case_id), out_fig / fname, f"Step11C C01 {int(duration)}h: crossing proxy over day predModel", 4 if len(panels) > 3 else 3, contours)
        manifest_rows.append({"step": "Step11C", "case_id": case_id, "figure": fname, "methods_included": ",".join(grp["run_name"].astype(str)), "background": "TEMPpred"})


def candidate_route_lookup(s11a, lat: np.ndarray, lon: np.ndarray) -> dict[str, list[tuple[int, int]]]:
    lookup: dict[str, list[tuple[int, int]]] = {}
    cand = pd.read_csv(STEP11D / "step11d_candidate_trajectories.csv")
    for _, row in cand.iterrows():
        name = str(row["candidate_name"])
        src = str(row["source_run_dir"])
        if "step11c_single_auv_boundary_crossing_reward_20260523_200322" in src:
            tail = src.split("planner_runs", 1)[1].lstrip("\\/")
            route_dir = STEP11C / "planner_runs" / tail
        elif "step11d_multi_auv_regime_separation_20260524_114809" in src:
            tail = src.split("planner_runs", 1)[1].lstrip("\\/")
            route_dir = STEP11D / "planner_runs" / tail
        else:
            route_dir = Path(src)
        pts = next(iter(panel_paths_from_route_dir(s11a, route_dir, lat, lon).values()), [])
        lookup[name] = pts
    return lookup


def make_step11d(s11a, lat: np.ndarray, lon: np.ndarray, case_idx: dict[str, int], temp: np.ndarray, out_fig: Path, manifest_rows: list[dict[str, Any]]) -> None:
    fleet = pd.read_csv(STEP11D / "step11d_fleet_level_metrics.csv")
    case_id = "C01_representative"
    lookup = candidate_route_lookup(s11a, lat, lon)
    panels = []
    for _, row in fleet.iterrows():
        strategy = str(row["strategy"])
        paths = []
        if strategy in {"multi_baseline_STD", "multi_boundary_alpha050"}:
            run_id = str(row["run_id"])
            pts_by_route = panel_paths_from_route_dir(s11a, STEP11D / "planner_runs" / run_id, lat, lon)
            for vid, pts in sorted(pts_by_route.items()):
                paths.append((f"AUV{vid}", pts, "white" if vid == 1 else "yellow", "-"))
        elif strategy == "vehicle_specific_regime_maps":
            paths = [("AUV1 region_A", lookup.get("region_A", []), "white", "-"), ("AUV2 region_B", lookup.get("region_B", []), "yellow", "-")]
        elif strategy == "vehicle_specific_with_crossing_proxy":
            paths = [("AUV1 A+cross", lookup.get("region_A_with_crossing", []), "white", "-"), ("AUV2 B+cross", lookup.get("region_B_with_crossing", []), "yellow", "-")]
        elif strategy == "sequential_overlap_reduction":
            paths = [("AUV1 region_A", lookup.get("region_A", []), "white", "-"), ("AUV2 B seq", lookup.get("region_B_sequential_penalized", []), "yellow", "-")]
        elif strategy == "post_solver_selected_pair":
            selected = pd.read_csv(STEP11D / "step11d_selected_pair_summary.csv").iloc[0]
            paths = [(f"AUV1 {selected['selected_AUV1_candidate']}", lookup.get(str(selected["selected_AUV1_candidate"]), []), "white", "-"), (f"AUV2 {selected['selected_AUV2_candidate']}", lookup.get(str(selected["selected_AUV2_candidate"]), []), "yellow", "-")]
        panels.append(
            {
                "title": strategy,
                "paths": paths,
                "metrics": [
                    f"Bcov={float(row['fleet_region_B_coverage']):.3f}, STD={float(row['fleet_collected_STD']):.1f}",
                    f"overlap={float(row['trajectory_overlap_ratio']):.3f}, meanD={float(row['inter_vehicle_mean_distance']):.1f}",
                    f"comp={float(row['fleet_complementarity_score']):.3f}",
                ],
            }
        )
    contours = []
    ra = STEP11D / "step11d_regime_A_mask.npy"
    rb = STEP11D / "step11d_regime_B_mask.npy"
    if ra.exists() and rb.exists():
        contours = [(np.load(ra), "#2b6cb0", "region_A"), (np.load(rb), "#c53030", "region_B")]
    fname = "step11d_C01_multi_predmodel_panel_by_strategy.png"
    plot_panel(panels, case_temp(case_idx, temp, case_id), out_fig / fname, "Step11D C01 multi-AUV strategies over day predModel", 3, contours)
    manifest_rows.append({"step": "Step11D", "case_id": case_id, "figure": fname, "methods_included": ",".join(fleet["strategy"].astype(str)), "background": "TEMPpred"})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make predModel panel figures for legacy Step11 outputs.")
    parser.add_argument("--output-root", type=Path, default=RESULTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outdir = args.output_root.resolve() / f"fossum_roi_x490_step11ad_legacy_planner_predmodel_panels_{now_tag()}"
    figdir = outdir / "figures_predmodel_panels"
    figdir.mkdir(parents=True, exist_ok=False)
    s11a = load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")
    lat = np.load(HRES / "LAT_hres.npy")
    lon = np.load(HRES / "LON_hres.npy")
    case_idx, temp, _mask = load_step10f()
    manifest_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for label, fn in [
        ("Step11A", make_step11a),
        ("Step11B", make_step11b),
        ("Step11C", make_step11c),
        ("Step11D", make_step11d),
    ]:
        try:
            fn(s11a, lat, lon, case_idx, temp, figdir, manifest_rows)
        except Exception as exc:
            warnings.append(f"{label} failed: {exc!r}")

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(outdir / "step11ad_predmodel_panel_manifest.csv", index=False)
    write_json(
        outdir / "step11ad_checks.json",
        {
            "verdict": "STEP11AD_LEGACY_PREDMODEL_PANELS_READY" if not warnings else "STEP11AD_COMPLETED_WITH_WARNINGS",
            "output_dir": rel(outdir),
            "figures_created": len(list(figdir.glob("*.png"))),
            "warnings": warnings,
            "background_for_path_figures": "Step10F TEMPpred for each case/date",
        },
    )
    write_json(
        outdir / "step11ad_metadata.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "script": rel(Path(__file__)),
            "inputs": {
                "step11a": rel(STEP11A),
                "step11b": [rel(p) for p in STEP11B_OUTPUTS],
                "step11c": rel(STEP11C),
                "step11d": rel(STEP11D),
                "step10f_predmodel": rel(STEP10F),
            },
        },
    )
    report = [
        "# Step11AD legacy Step11 predModel panel figures",
        "",
        "These figures are generated from existing routes only. No planner rerun was performed.",
        "",
        "## Visual rule",
        "",
        "- One panel per method/strategy.",
        "- Background is the day-specific `TEMPpred` predModel from Step10F.",
        "- Regime masks are contour overlays only where useful.",
        "- Old STD/descriptor/region backgrounds should be treated as diagnostic unless explicitly captioned.",
        "",
        "## Figures",
        "",
        md_table(manifest, ["step", "case_id", "figure", "methods_included", "background"], 30),
        "",
        "## Interpretation notes",
        "",
        "- Step11A: first baseline vs boundary-enriched test; use panels to see that boundary-only often changes little against baseline.",
        "- Step11B: descriptors were used in the objective; old figures could look like STD/diagnostic backgrounds. These panels show all descriptor runs over the same day predModel for path comparison.",
        "- Step11C: 12h boundary/crossing runs do visit two labelled regions in metrics, but the panel helps show whether this is broad exploration or mostly boundary-adjacent motion.",
        "- Step11D: low exact overlap in metrics means the issue is mostly same-zone behaviour, not literal path overlay. Use the per-strategy panels plus distance/overlap metrics.",
    ]
    if warnings:
        report += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    (outdir / "step11ad_legacy_logic_report.md").write_text("\n".join(report), encoding="utf-8")
    shutil.copy2(Path(__file__), outdir / Path(__file__).name)

    print("STEP11AD LEGACY PREDMODEL PANELS")
    print(f"Output: {rel(outdir)}")
    print(f"Figures created: {len(list(figdir.glob('*.png')))}")
    print(f"Warnings: {len(warnings)}")
    print(f"Verdict: {'STEP11AD_LEGACY_PREDMODEL_PANELS_READY' if not warnings else 'STEP11AD_COMPLETED_WITH_WARNINGS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
