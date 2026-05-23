from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
STEP10D = RESULTS / "fossum_roi_x490_step10d_top20_class01_class06_python_dss_20260516_170704"
STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP06 = RESULTS / "october_surface_temppred_std_roi_x490_20260511_155923"
STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260514_164854"
ROI_REF = RESULTS / "fresnel_paper_roi_x490_surface_370_20260509_180348"
SELECTED_DAY_SLICE = 1


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def robust_scale(arrays: list[np.ndarray], p_low: float = 1, p_high: float = 99) -> tuple[float, float]:
    vals = np.concatenate([np.asarray(a, dtype=np.float64)[np.isfinite(a)] for a in arrays if np.isfinite(a).any()])
    if vals.size == 0:
        return 0.0, 1.0
    lo, hi = np.percentile(vals, [p_low, p_high])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo, hi = float(np.nanmin(vals)), float(np.nanmax(vals))
    if lo == hi:
        hi = lo + 1.0
    return float(lo), float(hi)


def roi_slices() -> tuple[slice, slice]:
    meta = json.loads((ROI_REF / "paper_roi_x490_metadata.json").read_text(encoding="utf-8"))
    idx = meta["roi_indices"]
    return slice(int(idx["row_min"]), int(idx["row_max"]) + 1), slice(int(idx["col_min"]), int(idx["col_max"]) + 1)


def apply_roi(arr: np.ndarray, mask: np.ndarray, row_slice: slice, col_slice: slice) -> np.ndarray:
    out = np.asarray(arr[SELECTED_DAY_SLICE, row_slice, col_slice], dtype=np.float32).copy()
    out[~mask] = np.nan
    return out


def load_step10d_maps() -> pd.DataFrame:
    metrics = pd.read_csv(STEP10D / "step10d_generation_day_metrics.csv")
    row_slice, col_slice = roi_slices()
    mask = np.load(ROI_REF / "MASK_paper_roi_x490.npy").astype(bool)
    rows: list[dict[str, Any]] = []
    for _, r in metrics.iterrows():
        pred = Path(str(r["predmodel"]))
        with netCDF4.Dataset(pred) as ds:
            temp = apply_roi(np.asarray(ds.variables["TEMPpred"][:], dtype=np.float64), mask, row_slice, col_slice)
            std = apply_roi(np.asarray(ds.variables["STD"][:], dtype=np.float64), mask, row_slice, col_slice)
        rows.append(
            {
                "date": str(r["date"]),
                "class_label": str(r["class_label"]),
                "day_index_370": int(r["day_index_370"]),
                "predmodel": str(pred),
                "STD_variance_mean": float(r["STD_variance_mean"]),
                "STD_variance_max": float(r["STD_variance_max"]),
                "TEMPpred": temp,
                "STD": std,
            }
        )
    return pd.DataFrame(rows)


def load_october_reference() -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    temp = np.load(STEP06 / "TEMPpred_october_surface_roi_x490.npy").astype(np.float32)
    std = np.load(STEP06 / "STD_october_surface_roi_x490.npy").astype(np.float32)
    dates = pd.read_csv(STEP06 / "dates_october.csv")
    return temp, std, dates


def cmap_with_bad(name: str):
    cmap = plt.get_cmap(name).copy()
    cmap.set_bad("#f2f2f2")
    return cmap


def plot_panel(
    items: list[dict[str, Any]],
    variable: str,
    out: Path,
    *,
    title: str,
    cmap_name: str,
    vmin: float | None,
    vmax: float | None,
    cols: int = 5,
    individual: bool = False,
) -> None:
    n = len(items)
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.4 * cols, 3.0 * rows), constrained_layout=True)
    axes_flat = np.ravel(axes)
    cmap = cmap_with_bad(cmap_name)
    im = None
    for i, ax in enumerate(axes_flat):
        if i >= n:
            ax.axis("off")
            continue
        arr = items[i][variable]
        local_vmin, local_vmax = (robust_scale([arr]) if individual else (vmin, vmax))
        im = ax.imshow(np.ma.masked_invalid(arr), origin="lower", cmap=cmap, vmin=local_vmin, vmax=local_vmax, interpolation="nearest")
        subtitle = f"{items[i]['date']} {items[i]['class_label']}"
        if variable == "STD":
            subtitle += f"\nmean={items[i]['STD_variance_mean']:.4g} max={items[i]['STD_variance_max']:.4g}"
        ax.set_title(subtitle, fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    if im is not None and not individual:
        fig.colorbar(im, ax=axes_flat.tolist(), shrink=0.72, label="TEMPpred (degC)" if variable == "TEMPpred" else "STD/StDev = variance")
    fig.suptitle(title, fontsize=13)
    fig.savefig(out, dpi=170)
    plt.close(fig)


def plot_side_by_side(items: list[dict[str, Any]], out: Path, temp_scale: tuple[float, float], std_scale: tuple[float, float], title: str) -> None:
    fig, axes = plt.subplots(len(items), 2, figsize=(8.8, 2.3 * len(items)), constrained_layout=True)
    if len(items) == 1:
        axes = np.asarray([axes])
    temp_cmap = cmap_with_bad("coolwarm")
    std_cmap = cmap_with_bad("viridis")
    for axrow, item in zip(axes, items):
        im0 = axrow[0].imshow(np.ma.masked_invalid(item["TEMPpred"]), origin="lower", cmap=temp_cmap, vmin=temp_scale[0], vmax=temp_scale[1])
        im1 = axrow[1].imshow(np.ma.masked_invalid(item["STD"]), origin="lower", cmap=std_cmap, vmin=std_scale[0], vmax=std_scale[1])
        axrow[0].set_title(f"{item['date']} {item['class_label']} TEMPpred", fontsize=8)
        axrow[1].set_title(f"{item['date']} STD variance mean={item['STD_variance_mean']:.4g} max={item['STD_variance_max']:.4g}", fontsize=8)
        for ax in axrow:
            ax.set_xticks([])
            ax.set_yticks([])
        fig.colorbar(im0, ax=axrow[0], fraction=0.046, pad=0.04)
        fig.colorbar(im1, ax=axrow[1], fraction=0.046, pad=0.04)
    fig.suptitle(title, fontsize=13)
    fig.savefig(out, dpi=170)
    plt.close(fig)


def plot_october_comparison(items: list[dict[str, Any]], oct_items: list[dict[str, Any]], variable: str, out: Path, scale: tuple[float, float]) -> None:
    all_items = oct_items + items
    cmap = "coolwarm" if variable == "TEMPpred" else "viridis"
    plot_panel(
        all_items,
        variable,
        out,
        title=f"Fixed scale October vs C01/C06 {variable if variable == 'TEMPpred' else 'STD variance'}",
        cmap_name=cmap,
        vmin=scale[0],
        vmax=scale[1],
        cols=4,
    )


def main() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    out_dir = (args.output or RESULTS / f"fossum_roi_x490_step10d_top20_fixed_scale_figures_{now_tag()}").resolve()
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    df = load_step10d_maps()
    temp_oct, std_oct, dates_oct = load_october_reference()
    norm_stats = json.loads((STEP00 / "normalization_stats.json").read_text(encoding="utf-8"))
    mu = float(norm_stats["mu_global"])
    sigma = float(norm_stats["sigma_global"])
    step05_vlim = max(abs(float(norm_stats["normalized_png_vmin"])), abs(float(norm_stats["normalized_png_vmax"])))

    temp_maps = df["TEMPpred"].tolist()
    std_maps = df["STD"].tolist()
    temp10d_scale = robust_scale(temp_maps)
    std10d_scale = robust_scale(std_maps)
    temp_combined_scale = robust_scale(temp_maps + [temp_oct[i] for i in range(temp_oct.shape[0])])
    std_combined_scale = robust_scale(std_maps + [std_oct[i] for i in range(std_oct.shape[0])])
    class_scales: list[dict[str, Any]] = []
    for cls in ["C01", "C06"]:
        part = df[df["class_label"] == cls]
        class_scales.append({"scale_name": f"{cls}_TEMPpred", "vmin": robust_scale(part["TEMPpred"].tolist())[0], "vmax": robust_scale(part["TEMPpred"].tolist())[1]})
        class_scales.append({"scale_name": f"{cls}_STD_variance", "vmin": robust_scale(part["STD"].tolist())[0], "vmax": robust_scale(part["STD"].tolist())[1]})

    norm_maps = [(arr - mu) / sigma for arr in temp_maps]
    norm_vlim_data = float(np.percentile(np.abs(np.concatenate([m[np.isfinite(m)] for m in norm_maps])), 98))
    norm_vlim = step05_vlim if np.isfinite(step05_vlim) else norm_vlim_data
    df["TEMPpred_norm"] = norm_maps

    rows = df.to_dict("records")
    rows_sorted = sorted(rows, key=lambda r: (r["class_label"], r["date"]))
    top_c01_mean = sorted([r for r in rows if r["class_label"] == "C01"], key=lambda r: r["STD_variance_mean"], reverse=True)
    top_c06_mean = sorted([r for r in rows if r["class_label"] == "C06"], key=lambda r: r["STD_variance_mean"], reverse=True)
    top_c01_max = sorted([r for r in rows if r["class_label"] == "C01"], key=lambda r: r["STD_variance_max"], reverse=True)
    top_c06_max = sorted([r for r in rows if r["class_label"] == "C06"], key=lambda r: r["STD_variance_max"], reverse=True)
    top_global = sorted(rows, key=lambda r: (r["STD_variance_mean"], r["STD_variance_max"]), reverse=True)[:12]

    # Fixed global combined-with-October scale panels.
    plot_panel(rows_sorted, "TEMPpred", fig_dir / "fixed_global_top20_TEMPpred_panel.png", title="Top20 TEMPpred fixed scale: Step10D + October p1-p99", cmap_name="coolwarm", vmin=temp_combined_scale[0], vmax=temp_combined_scale[1])
    plot_panel(rows_sorted, "STD", fig_dir / "fixed_global_top20_STD_variance_panel.png", title="Top20 STD/StDev variance fixed scale: Step10D + October p1-p99", cmap_name="viridis", vmin=std_combined_scale[0], vmax=std_combined_scale[1])
    plot_side_by_side(top_global, fig_dir / "fixed_global_top20_TEMPpred_STD_side_by_side.png", temp_combined_scale, std_combined_scale, "Top candidates fixed global scales")
    for cls in ["C01", "C06"]:
        part = [r for r in rows_sorted if r["class_label"] == cls]
        plot_panel(part, "TEMPpred", fig_dir / f"fixed_global_{cls}_TEMPpred_panel.png", title=f"{cls} TEMPpred fixed global scale", cmap_name="coolwarm", vmin=temp_combined_scale[0], vmax=temp_combined_scale[1])
        plot_panel(part, "STD", fig_dir / f"fixed_global_{cls}_STD_variance_panel.png", title=f"{cls} STD/StDev variance fixed global scale", cmap_name="viridis", vmin=std_combined_scale[0], vmax=std_combined_scale[1])

    # Top/ranking fixed scales.
    plot_side_by_side(top_c01_mean[:10], fig_dir / "fixed_global_top_C01_by_STD_mean.png", temp_combined_scale, std_combined_scale, "C01 top by STD mean - fixed scales")
    plot_side_by_side(top_c06_mean[:10], fig_dir / "fixed_global_top_C06_by_STD_mean.png", temp_combined_scale, std_combined_scale, "C06 top by STD mean - fixed scales")
    plot_side_by_side(top_c01_max[:10], fig_dir / "fixed_global_top_C01_by_STD_max.png", temp_combined_scale, std_combined_scale, "C01 top by STD max - fixed scales")
    plot_side_by_side(top_c06_max[:10], fig_dir / "fixed_global_top_C06_by_STD_max.png", temp_combined_scale, std_combined_scale, "C06 top by STD max - fixed scales")
    plot_side_by_side(top_global, fig_dir / "fixed_global_top_candidates_TEMPpred_STD_side_by_side.png", temp_combined_scale, std_combined_scale, "Global top candidates - fixed scales")

    # Class-specific scale versions.
    for cls in ["C01", "C06"]:
        part = [r for r in rows_sorted if r["class_label"] == cls]
        t_scale = robust_scale([r["TEMPpred"] for r in part])
        s_scale = robust_scale([r["STD"] for r in part])
        plot_panel(part, "TEMPpred", fig_dir / f"fixed_class_{cls}_TEMPpred_panel.png", title=f"{cls} TEMPpred fixed class scale", cmap_name="coolwarm", vmin=t_scale[0], vmax=t_scale[1])
        plot_panel(part, "STD", fig_dir / f"fixed_class_{cls}_STD_variance_panel.png", title=f"{cls} STD variance fixed class scale", cmap_name="viridis", vmin=s_scale[0], vmax=s_scale[1])

    # Individual diagnostic versions.
    plot_panel(rows_sorted, "TEMPpred", fig_dir / "individual_scale_top20_TEMPpred_panel.png", title="DIAGNOSTIC ONLY: individual scale TEMPpred, not comparable across days", cmap_name="coolwarm", vmin=None, vmax=None, individual=True)
    plot_panel(rows_sorted, "STD", fig_dir / "individual_scale_top20_STD_variance_panel.png", title="DIAGNOSTIC ONLY: individual scale STD variance, not comparable across days", cmap_name="viridis", vmin=None, vmax=None, individual=True)

    # October comparison.
    oct_choice_dates = ["2024-10-30", "2024-10-31", "2024-10-14", "2024-10-20"]
    oct_items = []
    date_col = next((c for c in dates_oct.columns if "date" in c.lower()), None)
    oct_dates = dates_oct[date_col].astype(str).str[:10].tolist() if date_col else [f"2024-10-{i+1:02d}" for i in range(31)]
    for d in oct_choice_dates:
        if d in oct_dates:
            i = oct_dates.index(d)
            oct_items.append({"date": d, "class_label": "Oct", "TEMPpred": temp_oct[i], "STD": std_oct[i], "STD_variance_mean": float(np.nanmean(std_oct[i])), "STD_variance_max": float(np.nanmax(std_oct[i]))})
    top_mix = top_c01_mean[:3] + top_c06_mean[:3]
    plot_october_comparison(top_mix, oct_items, "STD", fig_dir / "fixed_scale_october_vs_C01_C06_STD_comparison.png", std_combined_scale)
    plot_october_comparison(top_mix, oct_items, "TEMPpred", fig_dir / "fixed_scale_october_vs_C01_C06_TEMPpred_comparison.png", temp_combined_scale)

    # Normalized/anomaly comparable to Step05.
    plot_panel(rows_sorted, "TEMPpred_norm", fig_dir / "fixed_norm_top20_TEMPpred_anomaly_panel.png", title=f"Top20 normalized TEMPpred anomaly fixed +/-{norm_vlim:.3f}", cmap_name="coolwarm", vmin=-norm_vlim, vmax=norm_vlim)
    for cls in ["C01", "C06"]:
        part = [r for r in rows_sorted if r["class_label"] == cls]
        plot_panel(part, "TEMPpred_norm", fig_dir / f"fixed_norm_{cls}_TEMPpred_anomaly_panel.png", title=f"{cls} normalized TEMPpred anomaly fixed +/-{norm_vlim:.3f}", cmap_name="coolwarm", vmin=-norm_vlim, vmax=norm_vlim)

    scale_rows = [
        {"scale_name": "Step10D_only_TEMPpred_p1_p99", "vmin": temp10d_scale[0], "vmax": temp10d_scale[1], "recommended": False},
        {"scale_name": "Step10D_only_STD_variance_p1_p99", "vmin": std10d_scale[0], "vmax": std10d_scale[1], "recommended": False},
        {"scale_name": "Combined_October_Step10D_TEMPpred_p1_p99", "vmin": temp_combined_scale[0], "vmax": temp_combined_scale[1], "recommended": True},
        {"scale_name": "Combined_October_Step10D_STD_variance_p1_p99", "vmin": std_combined_scale[0], "vmax": std_combined_scale[1], "recommended": True},
        {"scale_name": "Normalized_TEMPpred_anomaly_legacy_step05", "vmin": -norm_vlim, "vmax": norm_vlim, "recommended": True},
        {"scale_name": "Normalized_TEMPpred_anomaly_data_p98_abs", "vmin": -norm_vlim_data, "vmax": norm_vlim_data, "recommended": False},
    ] + class_scales
    pd.DataFrame(scale_rows).to_csv(out_dir / "step10d_fixed_scale_values.csv", index=False)
    config = {
        "input_step10d": str(STEP10D),
        "input_step06": str(STEP06),
        "input_step00": str(STEP00),
        "figures_only": True,
        "dss_executed": False,
        "predmodels_regenerated": False,
        "std_definition": "variance",
        "selected_day_slice": SELECTED_DAY_SLICE,
        "recommended_temp_scale": {"vmin": temp_combined_scale[0], "vmax": temp_combined_scale[1], "source": "Step10D top20 + Step06 October p1-p99"},
        "recommended_std_scale": {"vmin": std_combined_scale[0], "vmax": std_combined_scale[1], "source": "Step10D top20 + Step06 October p1-p99"},
        "normalized_scale": {"vmin": -norm_vlim, "vmax": norm_vlim, "source": "Step00/Step05 legacy normalized_png_vlim"},
    }
    write_json(out_dir / "step10d_fixed_scale_visual_config.json", config)
    figs = sorted([p.name for p in fig_dir.glob("*.png")])
    checks = {
        "predmodels_regenerated": False,
        "dss_executed": False,
        "matlab_used": False,
        "figures_created": len(figs),
        "all_top_panels_fixed_scale": True,
        "std_is_variance": True,
        "physical_and_normalized_separated": True,
        "verdict": "FIXED_SCALE_FIGURES_READY_FOR_VISUAL_SELECTION" if figs else "FIXED_SCALE_FIGURES_FAILED",
    }
    write_json(out_dir / "step10d_fixed_scale_checks.json", checks)
    summary = [
        "# Step10D Fixed-Scale Visual Panels",
        "",
        f"- Figures created: {len(figs)}",
        f"- Recommended TEMPpred scale: `{temp_combined_scale[0]:.6g}` to `{temp_combined_scale[1]:.6g}`",
        f"- Recommended STD variance scale: `{std_combined_scale[0]:.6g}` to `{std_combined_scale[1]:.6g}`",
        f"- Normalized anomaly scale: `{-norm_vlim:.6g}` to `{norm_vlim:.6g}`",
        "- DSS executed: `False`",
        "- PredModels regenerated: `False`",
        f"- Verdict: `{checks['verdict']}`",
        "",
        "Use the `fixed_global_*` panels for fair cross-day and October comparison. Use `fixed_norm_*` panels for visual comparison with Step05-style normalized prototypes. Individual-scale panels are diagnostic only.",
    ]
    (out_dir / "step10d_fixed_scale_summary.md").write_text("\n".join(summary), encoding="utf-8")
    (out_dir / "step10d_fixed_scale_report.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"Output: {out_dir}")
    return out_dir


if __name__ == "__main__":
    main()
