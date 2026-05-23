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
ROI_REF = RESULTS / "fresnel_paper_roi_x490_surface_370_20260509_180348"
FIXED = RESULTS / "fossum_roi_x490_step10d_top20_fixed_scale_figures_20260516_192930"
SELECTED_SLICE = 1
ROI_SHAPE = (72, 117)
TEMP_SCALE = (16.1942, 19.6822)
STD_SCALE = (0.006523, 0.203208)
NORM_SCALE = (-1.95039, 1.95039)


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def finite_stats(arr: np.ndarray, prefix: str) -> dict[str, Any]:
    a = np.asarray(arr, dtype=np.float64)
    vals = a[np.isfinite(a)]
    out: dict[str, Any] = {
        f"{prefix}_valid_count": int(vals.size),
        f"{prefix}_nan_fraction": float(np.mean(~np.isfinite(a))),
    }
    if vals.size:
        out.update(
            {
                f"{prefix}_min": float(np.min(vals)),
                f"{prefix}_max": float(np.max(vals)),
                f"{prefix}_mean": float(np.mean(vals)),
                f"{prefix}_std": float(np.std(vals)),
                f"{prefix}_p05": float(np.percentile(vals, 5)),
                f"{prefix}_p50": float(np.percentile(vals, 50)),
                f"{prefix}_p95": float(np.percentile(vals, 95)),
                f"{prefix}_all_zero": bool(np.allclose(vals, 0.0)),
            }
        )
    else:
        out.update({f"{prefix}_{k}": math.nan for k in ["min", "max", "mean", "std", "p05", "p50", "p95"]})
        out[f"{prefix}_all_zero"] = False
    return out


def compare_arrays(candidate: np.ndarray, reference: np.ndarray) -> dict[str, Any]:
    a = np.asarray(candidate, dtype=np.float64)
    b = np.asarray(reference, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() == 0:
        return {"n": 0, "rmse": math.nan, "mae": math.nan, "pearson": math.nan, "bias": math.nan}
    diff = a[mask] - b[mask]
    pearson = np.corrcoef(a[mask], b[mask])[0, 1] if mask.sum() > 2 and np.std(a[mask]) > 0 and np.std(b[mask]) > 0 else math.nan
    return {
        "n": int(mask.sum()),
        "rmse": float(np.sqrt(np.mean(diff * diff))),
        "mae": float(np.mean(np.abs(diff))),
        "pearson": float(pearson) if np.isfinite(pearson) else math.nan,
        "bias": float(np.mean(diff)),
        "mean_difference": float(np.nanmean(a) - np.nanmean(b)),
        "std_difference": float(np.nanstd(a) - np.nanstd(b)),
    }


def roi_slices() -> tuple[slice, slice, dict[str, int]]:
    meta = json.loads((ROI_REF / "paper_roi_x490_metadata.json").read_text(encoding="utf-8"))
    idx = {k: int(v) for k, v in meta["roi_indices"].items()}
    return slice(idx["row_min"], idx["row_max"] + 1), slice(idx["col_min"], idx["col_max"] + 1), idx


def class_id_from_label(label: str) -> int:
    return 1 if "C01" in label else 6


def load_inputs() -> tuple[pd.DataFrame, dict[str, np.ndarray], dict[str, Any]]:
    metrics = pd.read_csv(STEP10D / "step10d_generation_day_metrics.csv")
    metrics = metrics.sort_values(["class_label", "date"]).reset_index(drop=True)
    step00 = {
        "LAT": np.load(STEP00 / "LAT_roi_x490.npy").astype(np.float32),
        "LON": np.load(STEP00 / "LON_roi_x490.npy").astype(np.float32),
        "X_km": np.load(STEP00 / "X_km_roi_x490.npy").astype(np.float32),
        "Y_km": np.load(STEP00 / "Y_km_roi_x490.npy").astype(np.float32),
        "BATHY": np.load(STEP00 / "BATHY_roi_x490.npy").astype(np.float32),
        "MASK": np.load(STEP00 / "mask_common_roi_x490.npy").astype(bool),
        "X370": np.load(STEP00 / "X_surface_370_roi_x490.npy", mmap_mode="r"),
        "dates370": pd.read_csv(STEP00 / "dates_370.csv"),
    }
    norm = json.loads((STEP00 / "normalization_stats.json").read_text(encoding="utf-8"))
    return metrics, step00, norm


def extract() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
    metrics, step00, _norm = load_inputs()
    row_slice, col_slice, idx = roi_slices()
    mask = step00["MASK"]
    temp_stack: list[np.ndarray] = []
    std_stack: list[np.ndarray] = []
    inventory: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    indexing_rows: list[dict[str, Any]] = []
    for _, r in metrics.iterrows():
        pred = Path(str(r["predmodel"]))
        with netCDF4.Dataset(pred) as ds:
            variables = set(ds.variables.keys())
            temp = np.asarray(ds.variables["TEMPpred"][:], dtype=np.float64)
            std = np.asarray(ds.variables["STD"][:], dtype=np.float64)
            lat = np.asarray(ds.variables["LAT"][:], dtype=np.float64)
            lon = np.asarray(ds.variables["LON"][:], dtype=np.float64)
            bathy = np.asarray(ds.variables["BATHY"][:], dtype=np.float64)
            inv = {
                "date": str(r["date"]),
                "predModel_path": str(pred),
                "has_TEMPpred": "TEMPpred" in variables,
                "has_STD": "STD" in variables,
                "has_LAT": "LAT" in variables,
                "has_LON": "LON" in variables,
                "has_BATHY": "BATHY" in variables,
                "TEMPpred_shape": list(temp.shape),
                "STD_shape": list(std.shape),
                "LAT_shape": list(lat.shape),
                "LON_shape": list(lon.shape),
                "BATHY_shape": list(bathy.shape),
                "std_slice0_all_zero": bool(np.allclose(std[0][np.isfinite(std[0])], 0.0)),
                "std_slice1_all_zero": bool(np.allclose(std[SELECTED_SLICE][np.isfinite(std[SELECTED_SLICE])], 0.0)),
            }
        temp_roi = temp[SELECTED_SLICE, row_slice, col_slice].astype(np.float32)
        std_roi = std[SELECTED_SLICE, row_slice, col_slice].astype(np.float32)
        bathy_roi = bathy[row_slice, col_slice].astype(np.float32)
        lat_2d = np.repeat(lat[row_slice][:, None], len(lon[col_slice]), axis=1).astype(np.float32)
        lon_2d = np.repeat(lon[col_slice][None, :], len(lat[row_slice]), axis=0).astype(np.float32)
        temp_roi[~mask] = np.nan
        std_roi[~mask] = np.nan
        temp_stack.append(temp_roi)
        std_stack.append(std_roi)
        inventory.append(inv)
        selected.append(
            {
                "date": str(r["date"]),
                "day_index_370": int(r["day_index_370"]),
                "expected_class": class_id_from_label(str(r["class_label"])),
                "class_label": str(r["class_label"]),
                "predModel_path": str(pred),
                "selected_slice": SELECTED_SLICE,
                "roi_shape": list(temp_roi.shape),
                "valid_cells": int(mask.sum()),
            }
        )
        indexing_rows.append(
            {
                "date": str(r["date"]),
                **idx,
                "selected_slice": SELECTED_SLICE,
                "temp_roi_shape": list(temp_roi.shape),
                "std_roi_shape": list(std_roi.shape),
                "lat_matches_step00": bool(np.allclose(lat_2d, step00["LAT"], rtol=0, atol=1e-4)),
                "lon_matches_step00": bool(np.allclose(lon_2d, step00["LON"], rtol=0, atol=1e-4)),
                "bathy_matches_step00": bool(np.allclose(bathy_roi, step00["BATHY"], equal_nan=True, rtol=0, atol=1e-3)),
            }
        )
    return pd.DataFrame(selected), np.stack(temp_stack), np.stack(std_stack), inventory, indexing_rows


def write_netcdf(out: Path, selected: pd.DataFrame, temp: np.ndarray, std: np.ndarray, step00: dict[str, np.ndarray]) -> None:
    path = out / "top20_class01_class06_surface_TEMPpred_STD_roi_x490.nc"
    if path.exists():
        path.unlink()
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("time", temp.shape[0])
        ds.createDimension("y", temp.shape[1])
        ds.createDimension("x", temp.shape[2])
        ds.ROI = "FRESNEL_PAPER_ROI_X490"
        ds.STD_definition = "variance"
        ds.selected_slice = SELECTED_SLICE
        ds.source = "Python+DSS Step10D predModels"
        ds.mask_source = "Step00 mask_common_roi_x490"
        ds.valid_cells = int(step00["MASK"].sum())
        ds.createVariable("TEMPpred", "f4", ("time", "y", "x"), zlib=True, complevel=4, fill_value=np.nan)[:] = temp
        ds.createVariable("STD_variance", "f4", ("time", "y", "x"), zlib=True, complevel=4, fill_value=np.nan)[:] = std
        ds.createVariable("LAT", "f4", ("y", "x"))[:] = step00["LAT"]
        ds.createVariable("LON", "f4", ("y", "x"))[:] = step00["LON"]
        ds.createVariable("X_km", "f4", ("y", "x"))[:] = step00["X_km"]
        ds.createVariable("Y_km", "f4", ("y", "x"))[:] = step00["Y_km"]
        ds.createVariable("BATHY", "f4", ("y", "x"))[:] = step00["BATHY"]
        ds.createVariable("MASK", "i1", ("y", "x"))[:] = step00["MASK"].astype(np.int8)
        datev = ds.createVariable("date", str, ("time",))
        clsv = ds.createVariable("expected_class", "i4", ("time",))
        for i, row in selected.iterrows():
            datev[i] = str(row["date"])
            clsv[i] = int(row["expected_class"])


def plot_panel(items: list[dict[str, Any]], variable: str, out: Path, vmin: float, vmax: float, cmap_name: str, title: str, cols: int = 5) -> None:
    rows = int(math.ceil(len(items) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.4 * cols, 3.0 * rows), constrained_layout=True)
    axes_flat = np.ravel(axes)
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad("#f2f2f2")
    im = None
    for i, ax in enumerate(axes_flat):
        if i >= len(items):
            ax.axis("off")
            continue
        arr = items[i][variable]
        im = ax.imshow(np.ma.masked_invalid(arr), origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title(f"{items[i]['date']} {items[i]['class_label']}", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    if im is not None:
        fig.colorbar(im, ax=axes_flat.tolist(), shrink=0.72)
    fig.suptitle(title, fontsize=13)
    fig.savefig(out, dpi=170)
    plt.close(fig)


def plot_side_by_side(items: list[dict[str, Any]], out: Path, title: str) -> None:
    fig, axes = plt.subplots(len(items), 2, figsize=(9, 2.3 * len(items)), constrained_layout=True)
    if len(items) == 1:
        axes = np.asarray([axes])
    for axrow, item in zip(axes, items):
        im0 = axrow[0].imshow(np.ma.masked_invalid(item["TEMPpred"]), origin="lower", cmap="coolwarm", vmin=TEMP_SCALE[0], vmax=TEMP_SCALE[1])
        im1 = axrow[1].imshow(np.ma.masked_invalid(item["STD"]), origin="lower", cmap="viridis", vmin=STD_SCALE[0], vmax=STD_SCALE[1])
        axrow[0].set_title(f"{item['date']} {item['class_label']} TEMPpred", fontsize=8)
        axrow[1].set_title(f"{item['date']} STD variance", fontsize=8)
        for ax in axrow:
            ax.set_xticks([])
            ax.set_yticks([])
        fig.colorbar(im0, ax=axrow[0], fraction=0.046, pad=0.04)
        fig.colorbar(im1, ax=axrow[1], fraction=0.046, pad=0.04)
    fig.suptitle(title, fontsize=13)
    fig.savefig(out, dpi=170)
    plt.close(fig)


def main() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    out = (args.output or RESULTS / f"fossum_roi_x490_step10e_top20_class01_class06_roi_x490_{now_tag()}").resolve()
    fig_dir = out / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    selected, temp, std, inventory, indexing_rows = extract()
    metrics, step00, norm = load_inputs()
    mask = step00["MASK"]
    temp[:, ~mask] = np.nan
    std[:, ~mask] = np.nan

    np.save(out / "TEMPpred_top20_roi_x490.npy", temp.astype(np.float32))
    np.save(out / "STD_variance_top20_roi_x490.npy", std.astype(np.float32))
    for name in ["LAT", "LON", "X_km", "Y_km", "BATHY"]:
        np.save(out / f"{name}_top20_roi_x490.npy", step00[name].astype(np.float32))
    np.save(out / "MASK_top20_roi_x490.npy", mask.astype(bool))

    selected.to_csv(out / "selected_dates_top20_class01_class06.csv", index=False)
    pd.DataFrame(inventory).to_csv(out / "step10e_predmodel_inventory.csv", index=False)
    pd.DataFrame(indexing_rows).to_csv(out / "step10e_roi_extraction_indexing.csv", index=False)

    day_rows = []
    compare_rows = []
    dates370 = step00["dates370"].copy()
    dates370["date"] = dates370["date"].astype(str).str[:10]
    for i, row in selected.iterrows():
        day = {"date": row["date"], "class_id": row["expected_class"], "class_label": row["class_label"], "valid_count": int(mask.sum())}
        day.update(finite_stats(temp[i], "TEMPpred"))
        day.update(finite_stats(std[i], "STD_variance"))
        day_rows.append(day)
        idx = int(dates370.index[dates370["date"] == row["date"]][0])
        original = np.asarray(step00["X370"][idx], dtype=np.float32).copy()
        original[~mask] = np.nan
        cmp = {"date": row["date"], "day_index_370": row["day_index_370"], "class_label": row["class_label"], "x_surface_370_index": idx}
        cmp.update(compare_arrays(temp[i], original))
        compare_rows.append(cmp)
    day_metrics = pd.DataFrame(day_rows)
    comparison = pd.DataFrame(compare_rows)
    day_metrics.to_csv(out / "step10e_day_metrics.csv", index=False)
    comparison.to_csv(out / "step10e_comparison_to_original_370.csv", index=False)

    grid_rows = []
    for name, arr in [("LAT", step00["LAT"]), ("LON", step00["LON"]), ("BATHY", step00["BATHY"]), ("MASK", mask)]:
        saved = np.load(out / f"{name}_top20_roi_x490.npy" if name != "MASK" else out / "MASK_top20_roi_x490.npy")
        if name == "MASK":
            ok = bool(np.array_equal(saved.astype(bool), mask))
            maxdiff = int(np.sum(saved.astype(bool) != mask))
        else:
            ok = bool(np.allclose(saved, arr, equal_nan=True, rtol=0, atol=1e-4 if name != "BATHY" else 1e-3))
            maxdiff = float(np.nanmax(np.abs(saved.astype(float) - arr.astype(float))))
        grid_rows.append({"item": name, "shape": list(saved.shape), "matches_step00": ok, "max_diff_or_count": maxdiff})
    pd.DataFrame(grid_rows).to_csv(out / "step10e_grid_comparison_with_step00.csv", index=False)

    write_netcdf(out, selected, temp.astype(np.float32), std.astype(np.float32), step00)

    items = []
    mu, sigma = float(norm["mu_global"]), float(norm["sigma_global"])
    for i, row in selected.iterrows():
        items.append({"date": row["date"], "class_label": row["class_label"], "TEMPpred": temp[i], "STD": std[i], "NORM": (temp[i] - mu) / sigma})
    plot_panel(items, "TEMPpred", fig_dir / "step10e_top20_TEMPpred_roi_fixed_scale_panel.png", TEMP_SCALE[0], TEMP_SCALE[1], "coolwarm", "Step10E top20 TEMPpred ROI fixed scale")
    plot_panel(items, "STD", fig_dir / "step10e_top20_STD_variance_roi_fixed_scale_panel.png", STD_SCALE[0], STD_SCALE[1], "viridis", "Step10E top20 STD/StDev variance ROI fixed scale")
    plot_side_by_side(items, fig_dir / "step10e_top20_TEMPpred_STD_side_by_side_fixed_scale.png", "Step10E top20 TEMPpred/STD fixed scale")
    for cls in ["C01", "C06"]:
        part = [x for x in items if x["class_label"] == cls]
        plot_side_by_side(part, fig_dir / f"step10e_{cls}_TEMPpred_STD_side_by_side_fixed_scale.png", f"Step10E {cls} TEMPpred/STD fixed scale")
    plot_panel(items, "NORM", fig_dir / "step10e_norm_anomaly_top20_panel.png", NORM_SCALE[0], NORM_SCALE[1], "coolwarm", "Step10E normalized TEMPpred anomaly fixed Step05 scale")
    # Comparison examples.
    examples = items[:3] + items[-3:]
    original_items = []
    diff_items = []
    for ex in examples:
        idx = int(dates370.index[dates370["date"] == ex["date"]][0])
        original = np.asarray(step00["X370"][idx], dtype=np.float32).copy()
        original[~mask] = np.nan
        original_items.append({"date": ex["date"], "class_label": "X370", "TEMPpred": original})
        diff_items.append({"date": ex["date"], "class_label": "TEMPpred-X370", "TEMPpred": ex["TEMPpred"] - original})
    plot_panel(original_items + examples, "TEMPpred", fig_dir / "step10e_TEMPpred_vs_original_370_examples.png", TEMP_SCALE[0], TEMP_SCALE[1], "coolwarm", "TEMPpred vs original X_surface_370 examples", cols=3)
    plot_panel(diff_items, "TEMPpred", fig_dir / "step10e_TEMPpred_minus_original_370_examples.png", -1.0, 1.0, "coolwarm", "TEMPpred minus original X_surface_370 examples", cols=3)

    figures = sorted(p.name for p in fig_dir.glob("*.png"))
    class_summary = day_metrics.groupby("class_label").agg(
        n=("date", "count"),
        temp_mean=("TEMPpred_mean", "mean"),
        std_mean=("STD_variance_mean", "mean"),
        std_max=("STD_variance_max", "max"),
    ).reset_index()
    class_summary.to_csv(out / "step10e_class_metric_summary.csv", index=False)

    checks = {
        "predmodels_found": len(inventory),
        "dates_processed": int(temp.shape[0]),
        "c01_count": int((selected["class_label"] == "C01").sum()),
        "c06_count": int((selected["class_label"] == "C06").sum()),
        "selected_slice": SELECTED_SLICE,
        "std_definition": "variance",
        "TEMPpred_shape": list(temp.shape),
        "STD_variance_shape": list(std.shape),
        "LAT_shape": list(step00["LAT"].shape),
        "LON_shape": list(step00["LON"].shape),
        "BATHY_shape": list(step00["BATHY"].shape),
        "mask_valid_cells": int(mask.sum()),
        "mask_equals_step00": bool(np.array_equal(np.load(out / "MASK_top20_roi_x490.npy").astype(bool), mask)),
        "lat_lon_bathy_match_step00": bool(all(r["matches_step00"] for r in grid_rows if r["item"] in ["LAT", "LON", "BATHY"])),
        "temppred_not_all_nan": bool(not np.isnan(temp).all()),
        "std_not_all_zero": bool(not np.allclose(std[np.isfinite(std)], 0.0)),
        "netcdf_created": bool((out / "top20_class01_class06_surface_TEMPpred_STD_roi_x490.nc").exists()),
        "figures_created": len(figures),
        "dss_executed": False,
        "predmodels_regenerated": False,
    }
    checks["verdict"] = (
        "READY_FOR_STEP09B_CLASSIFY_TOP20_C01_C06_TEMPRED"
        if checks["predmodels_found"] == 20
        and checks["dates_processed"] == 20
        and checks["c01_count"] == 10
        and checks["c06_count"] == 10
        and checks["TEMPpred_shape"] == [20, 72, 117]
        and checks["STD_variance_shape"] == [20, 72, 117]
        and checks["mask_valid_cells"] == 8004
        and checks["mask_equals_step00"]
        and checks["lat_lon_bathy_match_step00"]
        and checks["netcdf_created"]
        else "STEP10E_COMPLETED_WITH_WARNINGS_REVIEW_BEFORE_STEP09B"
    )
    write_json(out / "step10e_checks.json", checks)
    write_json(
        out / "step10e_metadata.json",
        {"step10d": str(STEP10D), "step00": str(STEP00), "roi_ref": str(ROI_REF), "figures": figures, "fixed_scales_source": str(FIXED)},
    )
    write_json(
        out / "step10e_config.json",
        {"selected_slice": SELECTED_SLICE, "std_definition": "variance", "mask": "Step00 mask_common_roi_x490", "roi_shape": ROI_SHAPE},
    )
    summary = [
        "# Step10E Top20 C01/C06 ROI x490 Summary",
        "",
        f"- TEMPpred shape: `{list(temp.shape)}`",
        f"- STD variance shape: `{list(std.shape)}`",
        f"- Mask valid cells: `{int(mask.sum())}`",
        f"- NetCDF created: `{checks['netcdf_created']}`",
        f"- Figures created: `{len(figures)}`",
        f"- Verdict: `{checks['verdict']}`",
    ]
    (out / "step10e_summary.md").write_text("\n".join(summary), encoding="utf-8")
    (out / "step10e_report.md").write_text("\n".join(summary), encoding="utf-8")
    (out / "step10e_next_step_recommendation.md").write_text(
        "# Step10E Next Step Recommendation\n\nProceed to Step09B: classify/diagnose the top20 C01/C06 TEMPpred ROI arrays against the Step05 canonical model.\n",
        encoding="utf-8",
    )
    print(f"Output: {out}")
    return out


if __name__ == "__main__":
    main()
