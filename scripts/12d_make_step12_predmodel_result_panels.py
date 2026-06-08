#!/usr/bin/env python
"""Create Step12 trajectory result panels over day-specific predModel/TEMPpred.

This is a read-only visualization pass over existing Step12A/Step12B outputs.
It does not rerun the planner. It groups related runs that share the same cost
logic into one panel and draws their real planner paths over TEMPpred.
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

import step12_common as c


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEP12A = ROOT / "results" / "fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260529_175726"
DEFAULT_STEP12B = ROOT / "results" / "fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity_20260529_221108"
DEFAULT_OUTROOT = ROOT / "docs" / "lucid_trajectory_results"

ALPHA_COLORS = {
    0.00: "black",
    0.25: "#f6b300",
    0.50: "#00a9c8",
    0.75: "#7a3db8",
    1.00: "#33a02c",
}
STRATEGY_COLORS = {
    "baseline_shared_STD": ("white", "yellow"),
    "vehicle_specific_9010": ("#ffffff", "#ffff00"),
    "vehicle_specific_8020": ("#dbeafe", "#fde047"),
    "vehicle_specific_7030": ("#bfdbfe", "#facc15"),
    "vehicle_specific_6040": ("#93c5fd", "#eab308"),
    "vehicle_specific_5050": ("#60a5fa", "#ca8a04"),
    "vehicle_specific_2575": ("#38bdf8", "#fb923c"),
    "vehicle_specific_00100": ("#22d3ee", "#f97316"),
    "role_swap_of_vehicle_specific_00100": ("#f97316", "#22d3ee"),
}


def safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text).strip("_")


def alpha_label(alpha: float) -> str:
    return f"alpha={alpha:.2f}"


def load_routes(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    routes = payload.get("routes", [])
    return routes if isinstance(routes, list) else []


def route_points_from_run(
    s11a: Any,
    run_dir: Path,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    route_index: int | None = None,
) -> list[tuple[int, int]]:
    routes = load_routes(run_dir / "trajectory_routes.json")
    if not routes:
        return []
    if route_index is None:
        return c.route_points_all(s11a, routes, lat_hres, lon_hres)
    if 0 <= route_index < len(routes):
        return c.route_points_for_route(s11a, routes[route_index], lat_hres, lon_hres)
    return []


def run_dir_from_physical(outdir: Path, physical_run_id: str) -> Path:
    direct = outdir / "planner_runs" / physical_run_id
    if direct.exists():
        return direct
    return outdir / "planner_runs" / c.short_name(physical_run_id)


def plot_temp_background(
    ax: plt.Axes,
    temp_roi: np.ndarray,
    region_a: np.ndarray | None,
    region_b: np.ndarray | None,
    vmin: float,
    vmax: float,
) -> None:
    ax.imshow(temp_roi, origin="lower", aspect="auto", cmap="coolwarm", vmin=vmin, vmax=vmax)
    if region_a is not None:
        ax.contour(region_a.astype(float), levels=[0.5], colors=["#2b6cb0"], linewidths=0.8, alpha=0.9)
    if region_b is not None:
        ax.contour(region_b.astype(float), levels=[0.5], colors=["#c53030"], linewidths=0.8, alpha=0.9)
    ax.set_xlim(-1, c.ROI_SHAPE[1])
    ax.set_ylim(-1, c.ROI_SHAPE[0])
    ax.set_xlabel("ROI column", fontsize=8)
    ax.set_ylabel("ROI row", fontsize=8)
    ax.tick_params(labelsize=7)


def plot_path(ax: plt.Axes, points_full: list[tuple[int, int]], color: str, label: str, lw: float = 1.6) -> None:
    pts = c.route_to_roi(points_full)
    if not pts:
        return
    ax.plot(
        [p[1] for p in pts],
        [p[0] for p in pts],
        color=color,
        lw=lw,
        marker="o",
        markersize=1.5,
        label=label,
    )


def metric_text(row: pd.Series, cols: list[tuple[str, str]]) -> str:
    lines = []
    for label, col in cols:
        if col not in row:
            continue
        val = row[col]
        if pd.isna(val):
            continue
        if isinstance(val, str):
            shown = val
        else:
            shown = f"{float(val):.2f}"
        lines.append(f"{label}={shown}")
    return "\n".join(lines)


def add_metric_box(ax: plt.Axes, text: str) -> None:
    if not text:
        return
    ax.text(
        0.015,
        0.02,
        text,
        transform=ax.transAxes,
        fontsize=7,
        va="bottom",
        bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none", "pad": 2.5},
    )


def save_fig(fig: plt.Figure, png: Path, svg: bool) -> None:
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(png, dpi=180)
    if svg:
        fig.savefig(png.with_suffix(".svg"))
    plt.close(fig)


def make_step12a_panels(
    step12a: Path,
    outdir: Path,
    s11a: Any,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    temp: np.ndarray,
    svg: bool,
) -> list[dict[str, Any]]:
    metrics = pd.read_csv(step12a / "step12a_single_auv_metrics.csv")
    panels: list[dict[str, Any]] = []
    figdir = outdir / "step12a_single_auv"

    for case_id in c.CASE_ORDER:
        case_rows = metrics[metrics["case_id"].eq(case_id)]
        if case_rows.empty:
            continue
        case_index = c.CASE_ORDER.index(case_id)
        region_a = np.load(step12a / "masks" / f"{case_id}_region_A_mask.npy")
        region_b = np.load(step12a / "masks" / f"{case_id}_region_B_mask.npy")
        temp_roi = temp[case_index]
        vmin = float(np.nanmin(temp_roi))
        vmax = float(np.nanmax(temp_roi))
        for duration in sorted(case_rows["mission_duration_requested_h"].dropna().unique()):
            for descriptor in sorted(case_rows["descriptor"].dropna().unique()):
                sub = case_rows[
                    case_rows["mission_duration_requested_h"].eq(duration)
                    & case_rows["descriptor"].eq(descriptor)
                ].sort_values("alpha")
                if sub.empty:
                    continue
                fig, axes = plt.subplots(1, len(sub), figsize=(4.2 * len(sub), 3.8), squeeze=False)
                fig.suptitle(
                    f"Step12A {case_id} {duration:g}h: {descriptor} weight sensitivity over day predModel",
                    fontsize=15,
                )
                for ax, (_, row) in zip(axes.ravel(), sub.iterrows()):
                    plot_temp_background(ax, temp_roi, region_a, region_b, vmin, vmax)
                    run_dir = Path(str(row["run_dir"]))
                    if not run_dir.is_absolute():
                        run_dir = ROOT / run_dir
                    points = route_points_from_run(s11a, run_dir, lat_hres, lon_hres)
                    alpha = float(row["alpha"])
                    plot_path(ax, points, ALPHA_COLORS.get(round(alpha, 2), "#00a9c8"), str(row["run_name"]))
                    ax.set_title(alpha_label(alpha), fontsize=10)
                    add_metric_box(
                        ax,
                        metric_text(
                            row,
                            [
                                ("STD", "collected_STD"),
                                ("desc", "collected_descriptor"),
                                ("diff", "path_difference_from_baseline"),
                                ("A", "fraction_path_region_A"),
                                ("B", "fraction_path_region_B"),
                            ],
                        ),
                    )
                    ax.legend(fontsize=6, loc="upper right")
                png = figdir / f"step12a_{safe_name(case_id)}_{duration:g}h_{safe_name(descriptor)}_all_alphas_over_predmodel.png"
                save_fig(fig, png, svg)
                panels.append(
                    {
                        "step": "Step12A",
                        "case_id": case_id,
                        "duration_h": duration,
                        "group_logic": descriptor,
                        "panel_png": c.rel(png),
                        "panel_svg": c.rel(png.with_suffix(".svg")) if svg else "",
                        "rows": len(sub),
                    }
                )
    return panels


def get_step12b_paths_for_fleet_row(
    step12b: Path,
    manifest: pd.DataFrame,
    row: pd.Series,
    s11a: Any,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
) -> dict[int, list[tuple[int, int]]]:
    run_id = str(row["run_id"])
    strategy = str(row["strategy"])
    if strategy.startswith("role_swap_of_"):
        base_strategy = strategy.replace("role_swap_of_", "", 1)
        base_row = row.copy()
        base_row["strategy"] = base_strategy
        base_paths = get_step12b_paths_for_fleet_row(step12b, manifest, base_row, s11a, lat_hres, lon_hres)
        return {1: base_paths.get(2, []), 2: base_paths.get(1, [])}

    if strategy == "baseline_shared_STD":
        physical = str(manifest.loc[manifest["physical_run_id"].eq(run_id), "physical_run_id"].head(1).squeeze())
        if not physical or physical == "nan":
            physical = run_id
        run_dir = run_dir_from_physical(step12b, physical)
        return {
            1: route_points_from_run(s11a, run_dir, lat_hres, lon_hres, route_index=0),
            2: route_points_from_run(s11a, run_dir, lat_hres, lon_hres, route_index=1),
        }

    rows = manifest[
        manifest["case_id"].eq(row["case_id"])
        & manifest["mission_duration_requested_h"].eq(row["mission_duration_requested_h"])
        & manifest["strategy"].eq(strategy)
    ].copy()
    paths: dict[int, list[tuple[int, int]]] = {}
    for _, mrow in rows.iterrows():
        vehicle = int(float(mrow["vehicle_id"]))
        run_dir = run_dir_from_physical(step12b, str(mrow["physical_run_id"]))
        paths[vehicle] = route_points_from_run(s11a, run_dir, lat_hres, lon_hres, route_index=0)
    return paths


def make_step12b_panels(
    step12b: Path,
    outdir: Path,
    s11a: Any,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    temp: np.ndarray,
    svg: bool,
) -> list[dict[str, Any]]:
    fleet = pd.read_csv(step12b / "step12b_fleet_level_metrics.csv")
    manifest = pd.read_csv(step12b / "step12b_run_manifest.csv")
    panels: list[dict[str, Any]] = []
    figdir = outdir / "step12b_multi_auv"

    for case_id in c.CASE_ORDER:
        case_rows = fleet[fleet["case_id"].eq(case_id)]
        if case_rows.empty:
            continue
        case_index = c.CASE_ORDER.index(case_id)
        region_a = np.load(step12b / "masks" / f"{case_id}_region_A_mask.npy")
        region_b = np.load(step12b / "masks" / f"{case_id}_region_B_mask.npy")
        temp_roi = temp[case_index]
        vmin = float(np.nanmin(temp_roi))
        vmax = float(np.nanmax(temp_roi))
        for duration in sorted(case_rows["mission_duration_requested_h"].dropna().unique()):
            sub = case_rows[case_rows["mission_duration_requested_h"].eq(duration)].copy()
            if sub.empty:
                continue
            sub["sort_key"] = sub["strategy"].map(
                {
                    "baseline_shared_STD": 0,
                    "vehicle_specific_9010": 1,
                    "vehicle_specific_8020": 2,
                    "vehicle_specific_7030": 3,
                    "vehicle_specific_6040": 4,
                    "vehicle_specific_5050": 5,
                    "vehicle_specific_2575": 6,
                    "vehicle_specific_00100": 7,
                    "role_swap_of_vehicle_specific_00100": 8,
                }
            ).fillna(99)
            sub = sub.sort_values(["sort_key", "strategy"])
            ncols = 3
            nrows = int(math.ceil(len(sub) / ncols))
            fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 3.9 * nrows), squeeze=False)
            fig.suptitle(
                f"Step12B {case_id} {duration:g}h: vehicle-specific weight strategies over day predModel",
                fontsize=15,
            )
            for ax in axes.ravel():
                ax.axis("off")
            for ax, (_, row) in zip(axes.ravel(), sub.iterrows()):
                ax.axis("on")
                plot_temp_background(ax, temp_roi, region_a, region_b, vmin, vmax)
                paths = get_step12b_paths_for_fleet_row(step12b, manifest, row, s11a, lat_hres, lon_hres)
                colors = STRATEGY_COLORS.get(str(row["strategy"]), ("white", "yellow"))
                plot_path(ax, paths.get(1, []), colors[0], "AUV1", lw=1.7)
                plot_path(ax, paths.get(2, []), colors[1], "AUV2", lw=1.7)
                ax.set_title(str(row["strategy"]), fontsize=9)
                add_metric_box(
                    ax,
                    metric_text(
                        row,
                        [
                            ("STD", "fleet_collected_STD"),
                            ("Bcov", "fleet_region_B_coverage"),
                            ("spec", "regime_specialization_score"),
                            ("overlap", "trajectory_overlap_ratio"),
                            ("comp", "complementarity_score"),
                        ],
                    ),
                )
                ax.legend(fontsize=6, loc="upper right")
            png = figdir / f"step12b_{safe_name(case_id)}_{duration:g}h_all_strategies_over_predmodel.png"
            save_fig(fig, png, svg)
            panels.append(
                {
                    "step": "Step12B",
                    "case_id": case_id,
                    "duration_h": duration,
                    "group_logic": "vehicle_specific_weight_strategies",
                    "panel_png": c.rel(png),
                    "panel_svg": c.rel(png.with_suffix(".svg")) if svg else "",
                    "rows": len(sub),
                }
            )
    return panels


def write_index(outdir: Path, panels: list[dict[str, Any]], step12a: Path, step12b: Path) -> None:
    df = pd.DataFrame(panels)
    df.to_csv(outdir / "step12_predmodel_panel_manifest.csv", index=False)
    lines = [
        "# Step12 predModel trajectory panels",
        "",
        "These panels redraw existing Step12A and Step12B planner routes over the day-specific predModel/TEMPpred background.",
        "",
        "Important: predModel/TEMPpred is a diagnostic background here. It is not the objective map. The objective logic is grouped by descriptor/alpha for Step12A and vehicle-specific weights for Step12B.",
        "",
        f"- Step12A source: `{c.rel(step12a)}`",
        f"- Step12B source: `{c.rel(step12b)}`",
        f"- Panels created: {len(df)}",
        "",
        "## Manifest",
        c.md_table(df, ["step", "case_id", "duration_h", "group_logic", "rows", "panel_png", "panel_svg"], 200),
    ]
    c.write_text(outdir / "README.md", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step12a", type=Path, default=DEFAULT_STEP12A)
    parser.add_argument("--step12b", type=Path, default=DEFAULT_STEP12B)
    parser.add_argument("--step10f-dir", type=Path, default=c.STEP10F)
    parser.add_argument("--outroot", type=Path, default=DEFAULT_OUTROOT)
    parser.add_argument("--svg", action="store_true", help="Also save SVG versions of every panel.")
    args = parser.parse_args()
    c.set_step10f(args.step10f_dir)

    outdir = args.outroot / f"step12_predmodel_result_panels_{c.now_tag()}"
    outdir.mkdir(parents=True, exist_ok=False)

    s11a = c.load_step11a()
    lat_hres, lon_hres, _ = c.load_hres()
    temp, _mask = c.load_step10f_temp_mask()

    panels: list[dict[str, Any]] = []
    panels.extend(make_step12a_panels(args.step12a.resolve(), outdir, s11a, lat_hres, lon_hres, temp, args.svg))
    panels.extend(make_step12b_panels(args.step12b.resolve(), outdir, s11a, lat_hres, lon_hres, temp, args.svg))
    write_index(outdir, panels, args.step12a.resolve(), args.step12b.resolve())

    checks = {
        "output_dir": c.rel(outdir),
        "step12a_source": c.rel(args.step12a.resolve()),
        "step12b_source": c.rel(args.step12b.resolve()),
        "step10f_source": c.rel(args.step10f_dir.resolve()),
        "panels_created": len(panels),
        "svg_created": bool(args.svg),
        "TEMPpred_used_as_objective": False,
        "planner_rerun": False,
    }
    c.write_json(outdir / "step12_predmodel_panel_checks.json", checks)
    print(json.dumps(checks, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
