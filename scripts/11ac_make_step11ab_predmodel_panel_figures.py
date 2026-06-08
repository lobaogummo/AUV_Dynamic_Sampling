#!/usr/bin/env python
"""Step11AC: regenerate Step11AB visual panels over day-specific predModel.

This is a light diagnostic/visual post-process. It does not rerun the planner.
It reads the Step11AB route JSON files and plots each method in a separate
panel over the C01 TEMPpred map from Step10F.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
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
DEFAULT_STEP11AB = RESULTS / "fossum_roi_x490_step11ab_c01_region_target_vehicle_sweep_20260526_172106"
CASE_ID = "C01_representative"
CASE_DATE = "2024-08-24"
ROI_ROW_MIN = 55
ROI_COL_MIN = 47
ROI_SHAPE = (72, 117)


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
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


def load_temppred(step10f_dir: Path = STEP10F) -> np.ndarray:
    z = np.load(step10f_dir / "planner_minimal_boundary_input_maps.npz", allow_pickle=True)
    case_ids = [str(x) for x in z["case_ids"]]
    idx = case_ids.index(CASE_ID)
    return np.asarray(z["TEMPpred"][idx], dtype=float)


def load_routes(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "trajectory_routes.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("routes", [])


def routes_to_roi_points(s11a, routes: list[dict[str, Any]], lat_hres: np.ndarray, lon_hres: np.ndarray) -> dict[int, list[tuple[int, int]]]:
    out: dict[int, list[tuple[int, int]]] = {}
    for i, route in enumerate(routes, start=1):
        rid = int(route.get("route_id", i))
        pts = s11a.route_grid_points([route], lat_hres, lon_hres)
        out[rid] = [(r - ROI_ROW_MIN, c - ROI_COL_MIN) for r, c in pts]
    return out


def plot_panel(
    panels: list[dict[str, Any]],
    background: np.ndarray,
    out_path: Path,
    title: str,
    ncols: int,
    targets: pd.DataFrame | None = None,
    region_a: np.ndarray | None = None,
    region_b: np.ndarray | None = None,
) -> None:
    n = len(panels)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.8 * ncols, 4.3 * nrows), squeeze=False)
    vmin = float(np.nanpercentile(background, 2))
    vmax = float(np.nanpercentile(background, 98))
    for ax in axes.ravel():
        ax.axis("off")
    for ax, panel in zip(axes.ravel(), panels):
        im = ax.imshow(background, origin="lower", aspect="auto", cmap="coolwarm", vmin=vmin, vmax=vmax)
        if region_a is not None and np.any(region_a):
            ax.contour(region_a.astype(float), levels=[0.5], colors=["#2b6cb0"], linewidths=0.8, alpha=0.85)
        if region_b is not None and np.any(region_b):
            ax.contour(region_b.astype(float), levels=[0.5], colors=["#c53030"], linewidths=0.8, alpha=0.85)
        for label, pts, color, linestyle in panel["paths"]:
            if pts:
                ax.plot([p[1] for p in pts], [p[0] for p in pts], color=color, linestyle=linestyle, marker="o", markersize=2.2, linewidth=1.7, label=label)
        if targets is not None and not targets.empty and panel.get("show_targets", False):
            ax.scatter(targets["roi_col"], targets["roi_row"], s=110, c="yellow", marker="*", edgecolor="black", linewidth=0.6, label="targets")
        metric_lines = panel.get("metrics", [])
        if metric_lines:
            ax.text(
                0.015,
                0.02,
                "\n".join(metric_lines),
                transform=ax.transAxes,
                fontsize=8,
                color="black",
                bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none", "pad": 4},
                va="bottom",
            )
        ax.set_title(panel["title"], fontsize=10)
        ax.set_xlim(-1, ROI_SHAPE[1])
        ax.set_ylim(-1, ROI_SHAPE[0])
        ax.set_xlabel("ROI column")
        ax.set_ylabel("ROI row")
        ax.legend(fontsize=7, loc="upper right")
    fig.suptitle(title, fontsize=15)
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.025, pad=0.012)
    cbar.set_label("TEMPpred, degC")
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make Step11AB predModel panel figures.")
    parser.add_argument("--step11ab", type=Path, default=DEFAULT_STEP11AB)
    parser.add_argument("--step10f-dir", type=Path, default=STEP10F)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    step11ab = args.step11ab.resolve()
    out_dir = args.output_dir.resolve() if args.output_dir else step11ab / "figures_predmodel_panels"
    out_dir.mkdir(parents=True, exist_ok=True)

    s11a = load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")
    zutils = load_module("step11z_utils", SCRIPTS / "11z_rerun_minimal_prototype_based_planner_tests.py")
    lat_hres = np.load(HRES / "LAT_hres.npy")
    lon_hres = np.load(HRES / "LON_hres.npy")
    temp = load_temppred(args.step10f_dir)
    single = pd.read_csv(step11ab / "step11ab_single_auv_metrics.csv")
    multi = pd.read_csv(step11ab / "step11ab_multi_auv_metrics.csv")
    vehicle = pd.read_csv(step11ab / "step11ab_vehicle_metrics.csv")
    targets = pd.read_csv(step11ab / "step11ab_target_points.csv") if (step11ab / "step11ab_target_points.csv").exists() else pd.DataFrame()
    region_a = np.load(step11ab / "masks" / "C01_region_A_mask.npy") if (step11ab / "masks" / "C01_region_A_mask.npy").exists() else None
    region_b = np.load(step11ab / "masks" / "C01_region_B_mask.npy") if (step11ab / "masks" / "C01_region_B_mask.npy").exists() else None

    def route_dir_for(run_id: str) -> Path:
        return step11ab / "planner_runs" / zutils.short_name(run_id)

    single_panels = []
    for _, row in single.iterrows():
        run_id = str(row["run_id"])
        pts_by_route = routes_to_roi_points(s11a, load_routes(route_dir_for(run_id)), lat_hres, lon_hres)
        pts = next(iter(pts_by_route.values()), [])
        run_name = str(row["run_name"])
        single_panels.append(
            {
                "title": run_name,
                "paths": [(run_name, pts, "black" if run_name == "baseline_STD" else ("#f6ad00" if "boundary" in run_name else "#00a3c4"), "-")],
                "show_targets": run_name == "cross_region_targets",
                "metrics": [
                    f"regions={int(row['regions_visited'])}, cross={int(row['crossing_count'])}",
                    f"frac A={float(row['fraction_path_region_A']):.2f}, B={float(row['fraction_path_region_B']):.2f}",
                    f"STD={float(row['collected_STD']):.1f}",
                ],
            }
        )
    plot_panel(
        single_panels,
        temp,
        out_dir / "single_auv_c01_predmodel_panel_by_method.png",
        f"C01 single-AUV methods over day-specific predModel TEMPpred ({CASE_DATE})",
        ncols=3,
        targets=targets,
        region_a=region_a,
        region_b=region_b,
    )

    multi_panels = []
    auv_colors = {1: "white", 2: "yellow"}
    for _, row in multi.iterrows():
        strategy = str(row["strategy"])
        paths = []
        if str(row.get("scope", "")) == "":
            pass
        if strategy in ["baseline_STD", "prototype_boundary_alpha050"]:
            run_id = str(row["run_id"])
            pts_by_route = routes_to_roi_points(s11a, load_routes(route_dir_for(run_id)), lat_hres, lon_hres)
            for vid, pts in sorted(pts_by_route.items()):
                paths.append((f"AUV{vid}", pts, auv_colors.get(vid, "white"), "-"))
        else:
            for vid in [1, 2]:
                run_id = f"{CASE_ID}__multi_auv_12h__{strategy}__AUV{vid}"
                pts_by_route = routes_to_roi_points(s11a, load_routes(route_dir_for(run_id)), lat_hres, lon_hres)
                pts = next(iter(pts_by_route.values()), [])
                paths.append((f"AUV{vid}", pts, auv_colors.get(vid, "white"), "-"))
        v = vehicle[vehicle["strategy"].eq(strategy)]
        spec = []
        for vid in [1, 2]:
            vv = v[v["vehicle_id"].eq(vid)]
            if not vv.empty:
                spec.append(f"AUV{vid}: A={float(vv.iloc[0]['fraction_path_region_A']):.2f}, B={float(vv.iloc[0]['fraction_path_region_B']):.2f}")
        multi_panels.append(
            {
                "title": strategy,
                "paths": paths,
                "show_targets": False,
                "metrics": [
                    f"Bcov={float(row['fleet_region_B_coverage']):.3f}, STD={float(row['fleet_collected_STD']):.1f}",
                    f"overlap={float(row['trajectory_overlap_ratio']):.3f}, meanD={float(row['inter_vehicle_mean_distance']):.1f}",
                    *spec,
                ],
            }
        )
    plot_panel(
        multi_panels,
        temp,
        out_dir / "multi_auv_c01_predmodel_panel_by_method.png",
        f"C01 multi-AUV methods over day-specific predModel TEMPpred ({CASE_DATE})",
        ncols=3,
        region_a=region_a,
        region_b=region_b,
    )

    # A compact thesis-friendly version with only the baseline and best tradeoff.
    compact = [p for p in multi_panels if p["title"] in ["baseline_STD", "vehicle_specific_balanced", "vehicle_specific_strong_regime"]]
    plot_panel(
        compact,
        temp,
        out_dir / "multi_auv_c01_predmodel_panel_selected_methods.png",
        f"C01 selected multi-AUV methods over day-specific predModel TEMPpred ({CASE_DATE})",
        ncols=3,
        region_a=region_a,
        region_b=region_b,
    )

    # Replace the Step11AB overloaded/region-background figures with
    # interpretation-safe predModel panel versions, while preserving originals.
    main_fig_dir = step11ab / "figures"
    main_fig_dir.mkdir(exist_ok=True)
    deprecated_dir = step11ab / "figures_deprecated_region_background"
    deprecated_dir.mkdir(exist_ok=True)
    replacements = [
        {
            "deprecated_figure": "single_auv_c01_paths_over_regions.png",
            "replacement_source": "single_auv_c01_predmodel_panel_by_method.png",
            "reason": "old figure used prototype region RGB as background and overlaid all single-AUV methods",
        },
        {
            "deprecated_figure": "single_auv_c01_path_colored_by_region.png",
            "replacement_source": "single_auv_c01_predmodel_panel_by_method.png",
            "reason": "old figure used region background; new panel uses TEMPpred background and region contours",
        },
        {
            "deprecated_figure": "multi_auv_c01_weight_sweep_paths.png",
            "replacement_source": "multi_auv_c01_predmodel_panel_by_method.png",
            "reason": "old figure overlaid all multi-AUV methods in one axes over region RGB background",
        },
    ]
    for item in replacements:
        deprecated = main_fig_dir / item["deprecated_figure"]
        if deprecated.exists():
            shutil.copy2(deprecated, deprecated_dir / item["deprecated_figure"])
        replacement = out_dir / item["replacement_source"]
        if replacement.exists():
            shutil.copy2(replacement, main_fig_dir / item["deprecated_figure"])
            item["replacement_status"] = "replaced_in_figures_dir_and_original_backed_up"
        else:
            item["replacement_status"] = "replacement_source_missing"

    manifest = pd.DataFrame(
        [
            {
                "figure": "single_auv_c01_predmodel_panel_by_method.png",
                "background": "Step10F TEMPpred for C01_representative / 2024-08-24",
                "layout": "one panel per single-AUV method",
                "source_routes": rel(step11ab / "planner_runs"),
            },
            {
                "figure": "multi_auv_c01_predmodel_panel_by_method.png",
                "background": "Step10F TEMPpred for C01_representative / 2024-08-24",
                "layout": "one panel per multi-AUV method",
                "source_routes": rel(step11ab / "planner_runs"),
            },
            {
                "figure": "multi_auv_c01_predmodel_panel_selected_methods.png",
                "background": "Step10F TEMPpred for C01_representative / 2024-08-24",
                "layout": "baseline, balanced, strong-regime selected comparison",
                "source_routes": rel(step11ab / "planner_runs"),
            },
            {
                "figure": "single_auv_c01_paths_over_regions.png",
                "background": "Step10F TEMPpred for C01_representative / 2024-08-24",
                "layout": "replacement alias for old region-background figure; one panel per single-AUV method",
                "source_routes": rel(step11ab / "planner_runs"),
            },
            {
                "figure": "single_auv_c01_path_colored_by_region.png",
                "background": "Step10F TEMPpred for C01_representative / 2024-08-24",
                "layout": "replacement alias for old region-background figure; one panel per single-AUV method",
                "source_routes": rel(step11ab / "planner_runs"),
            },
            {
                "figure": "multi_auv_c01_weight_sweep_paths.png",
                "background": "Step10F TEMPpred for C01_representative / 2024-08-24",
                "layout": "replacement alias for old all-method overlay; one panel per multi-AUV method",
                "source_routes": rel(step11ab / "planner_runs"),
            },
        ]
    )
    manifest.to_csv(out_dir / "step11ac_predmodel_panel_manifest.csv", index=False)
    pd.DataFrame(replacements).to_csv(out_dir / "step11ac_deprecated_and_replacement_figures.csv", index=False)
    write_json(
        out_dir / "step11ac_checks.json",
        {
            "verdict": "STEP11AC_PREDMODEL_PANEL_FIGURES_READY",
            "step11ab_source": rel(step11ab),
            "output_dir": rel(out_dir),
            "background": "TEMPpred",
            "step10f_source": rel(args.step10f_dir),
            "case_id": CASE_ID,
            "date": CASE_DATE,
            "figures_created": len(list(out_dir.glob("*.png"))),
            "deprecated_region_background_figures_backed_up_to": rel(deprecated_dir),
            "replacement_rows": len(replacements),
        },
    )
    for png in out_dir.glob("*.png"):
        shutil.copy2(png, main_fig_dir / png.name)
    (out_dir / "step11ac_predmodel_panel_notes.md").write_text(
        "\n".join(
            [
                "# Step11AC predModel panel figures",
                "",
                "These figures replace the overloaded all-method overlay view.",
                "",
                "- Each method is shown in its own panel.",
                "- The background is the day-specific Step10F TEMPpred predModel for C01 / 2024-08-24.",
                "- Region A/B are only contour overlays, not the background.",
                "- AUV1/AUV2 are shown with distinct colors inside each method panel.",
                "- The old overloaded/region-background Step11AB figures were backed up under `figures_deprecated_region_background/` and replaced in `figures/` by predModel panel versions.",
            ]
        ),
        encoding="utf-8",
    )
    shutil.copy2(Path(__file__), out_dir / Path(__file__).name)
    print("STEP11AC PREDMODEL PANEL FIGURES")
    print(f"Output: {rel(out_dir)}")
    print(f"Copied to: {rel(main_fig_dir)}")
    print("Figures:")
    for png in sorted(out_dir.glob("*.png")):
        print(f"- {png.name}")
    print("Verdict: STEP11AC_PREDMODEL_PANEL_FIGURES_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
