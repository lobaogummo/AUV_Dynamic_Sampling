from __future__ import annotations

import argparse
import json
import math
import subprocess
from datetime import datetime, timedelta
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
FILIPA_ROOT = ROOT / "data" / "dadosParaPedro_Fresnel" / "dadosParaPedro_Fresnel"
STEP06 = RESULTS / "october_surface_temppred_std_roi_x490_20260511_155923"
STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
ROI_REF = RESULTS / "fresnel_paper_roi_x490_surface_370_20260509_180348"
VALIDATION100 = RESULTS / "fossum_roi_x490_step10b_python_dss_validation100_20260516_150917"
PILOT10B = RESULTS / "fossum_roi_x490_step10b_python_dss_class01_class06_pilot_20260516_152421"
SELECTED_DAY_SLICE = 1


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def masked_to_nan(value: Any) -> np.ndarray:
    arr = np.asanyarray(value)
    if np.ma.isMaskedArray(arr):
        return np.ma.filled(arr.astype(np.float64), np.nan)
    return arr.astype(np.float64, copy=False)


def target_to_pred_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)


def official_predmodel_path(date_str: str) -> Path:
    target = datetime.strptime(date_str, "%Y-%m-%d")
    pred = target_to_pred_date(date_str)
    return (
        FILIPA_ROOT
        / "02.Simulations"
        / "HighRes"
        / f"Daily_dpt_{pred:%Y%m%d}"
        / f"{target:%d-%m-%Y}_predModel_1.nc"
    )


def python_predmodel_path(date_str: str) -> Path:
    expected = VALIDATION100 / "predmodels" / date_str / "python_dss_predModel_1_100real.nc"
    if expected.exists():
        return expected
    matches = sorted(RESULTS.glob(f"fossum_roi_x490_step10b_python_dss_validation100_*/predmodels/{date_str}/python_dss_predModel_1_100real.nc"))
    return matches[-1] if matches else expected


def run_python_dss(date_str: str, out_dir: Path) -> Path:
    cmd = [
        "python",
        "scripts\\10b_python_dss_generate_temppred_std.py",
        "--mode",
        "validate_october",
        "--dates",
        date_str,
        "--depths",
        "1",
        "--n-realizations",
        "100",
        "--execute-dss",
        "--timeout-s",
        "7200",
        "--output",
        str(out_dir / "python_dss_generation"),
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=7500000)
    (out_dir / "python_dss_generation_command.txt").write_text(" ".join(cmd), encoding="utf-8")
    write_json(
        out_dir / "python_dss_generation_subprocess.json",
        {"returncode": result.returncode, "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]},
    )
    pred = out_dir / "python_dss_generation" / "predmodels" / date_str / "python_dss_predModel_1_100real.nc"
    if result.returncode != 0 or not pred.exists():
        raise RuntimeError(f"Python+DSS generation failed for {date_str}; see {out_dir}")
    return pred


def load_predmodel(path: Path) -> dict[str, Any]:
    with netCDF4.Dataset(path) as ds:
        variables = {name: list(var.shape) for name, var in ds.variables.items()}
        out = {
            "path": str(path),
            "variables": variables,
            "TEMPpred": masked_to_nan(ds.variables["TEMPpred"][:]),
            "STD": masked_to_nan(ds.variables["STD"][:]),
            "LAT": masked_to_nan(ds.variables["LAT"][:]),
            "LON": masked_to_nan(ds.variables["LON"][:]),
            "BATHY": masked_to_nan(ds.variables["BATHY"][:]),
        }
        if "STD_sqrt_variance" in ds.variables:
            out["STD_sqrt_variance"] = masked_to_nan(ds.variables["STD_sqrt_variance"][:])
        else:
            out["STD_sqrt_variance"] = np.sqrt(np.maximum(out["STD"], 0))
    return out


def metrics(candidate: np.ndarray, reference: np.ndarray) -> dict[str, Any]:
    a = np.asarray(candidate, dtype=np.float64)
    b = np.asarray(reference, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    out: dict[str, Any] = {
        "n": int(mask.sum()),
        "candidate_nan_fraction": float(np.mean(~np.isfinite(a))),
        "reference_nan_fraction": float(np.mean(~np.isfinite(b))),
    }
    if mask.sum() == 0:
        out.update({"rmse": math.nan, "mae": math.nan, "pearson": math.nan, "bias": math.nan})
        return out
    diff = a[mask] - b[mask]
    pearson = np.corrcoef(a[mask], b[mask])[0, 1] if mask.sum() > 2 and np.std(a[mask]) > 0 and np.std(b[mask]) > 0 else math.nan
    out.update(
        {
            "rmse": float(np.sqrt(np.mean(diff * diff))),
            "mae": float(np.mean(np.abs(diff))),
            "pearson": float(pearson) if np.isfinite(pearson) else math.nan,
            "bias": float(np.mean(diff)),
            "candidate_min": float(np.nanmin(a)),
            "candidate_max": float(np.nanmax(a)),
            "candidate_mean": float(np.nanmean(a)),
            "candidate_std": float(np.nanstd(a)),
            "reference_min": float(np.nanmin(b)),
            "reference_max": float(np.nanmax(b)),
            "reference_mean": float(np.nanmean(b)),
            "reference_std": float(np.nanstd(b)),
        }
    )
    return out


def prefixed(row_prefix: dict[str, Any], met: dict[str, Any]) -> dict[str, Any]:
    out = dict(row_prefix)
    out.update(met)
    return out


def roi_slices() -> tuple[slice, slice, dict[str, Any]]:
    meta = json.loads((ROI_REF / "paper_roi_x490_metadata.json").read_text(encoding="utf-8"))
    idx = meta["roi_indices"]
    return slice(int(idx["row_min"]), int(idx["row_max"]) + 1), slice(int(idx["col_min"]), int(idx["col_max"]) + 1), idx


def apply_roi(arr: np.ndarray, mask: np.ndarray, row_slice: slice, col_slice: slice, day_slice: int | None = None) -> np.ndarray:
    src = arr[day_slice] if day_slice is not None and arr.ndim == 3 else arr
    out = np.asarray(src[row_slice, col_slice], dtype=np.float32).copy()
    out[~mask] = np.nan
    return out


def step06_index(date_str: str) -> int:
    df = pd.read_csv(STEP06 / "dates_october.csv")
    for col in ["date", "target_date", "day", "datetime"]:
        if col in df.columns:
            vals = [str(x)[:10] for x in df[col].tolist()]
            if date_str in vals:
                return vals.index(date_str)
    # Fallback: October 1 is index 0.
    target = datetime.strptime(date_str, "%Y-%m-%d")
    return target.day - 1


def save_map(ax: plt.Axes, arr: np.ndarray, title: str, cmap_name: str = "coolwarm") -> None:
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad("#f2f2f2")
    im = ax.imshow(np.ma.masked_invalid(arr), origin="lower", cmap=cmap, interpolation="nearest")
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


def save_fullgrid_figure(out_dir: Path, date_str: str, py: dict[str, Any], off: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), constrained_layout=True)
    ds = SELECTED_DAY_SLICE
    panels = [
        (off["TEMPpred"][ds], "TEMPpred oficial", "coolwarm"),
        (py["TEMPpred"][ds], "TEMPpred Python", "coolwarm"),
        (py["TEMPpred"][ds] - off["TEMPpred"][ds], "Diff TEMPpred", "coolwarm"),
        (off["STD"][ds], "StDev oficial", "viridis"),
        (py["STD"][ds], "Variance Python", "viridis"),
        (py["STD"][ds] - off["STD"][ds], "Diff variance", "coolwarm"),
        (py["STD_sqrt_variance"][ds], "Sqrt variance Python", "viridis"),
        (py["STD_sqrt_variance"][ds] - off["STD"][ds], "Diff sqrt", "coolwarm"),
    ]
    for ax, (arr, title, cmap) in zip(axes.ravel(), panels):
        save_map(ax, arr, title, cmap)
    fig.suptitle(f"Full grid control - {date_str}")
    fig.savefig(out_dir / "figures" / f"step10b_control_fullgrid_{date_str}.png", dpi=160)
    plt.close(fig)


def save_roi_figure(out_dir: Path, date_str: str, arrays: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), constrained_layout=True)
    panels = [
        (arrays["TEMPpred_step06"], "TEMPpred Step06", "coolwarm"),
        (arrays["TEMPpred_python"], "TEMPpred Python ROI", "coolwarm"),
        (arrays["TEMPpred_python"] - arrays["TEMPpred_step06"], "Diff TEMPpred", "coolwarm"),
        (arrays["TEMPpred_official"], "TEMPpred oficial ROI", "coolwarm"),
        (arrays["STD_step06"], "STD Step06", "viridis"),
        (arrays["STD_variance_python"], "Variance Python ROI", "viridis"),
        (arrays["STD_variance_python"] - arrays["STD_step06"], "Diff STD", "coolwarm"),
        (arrays["STD_sqrt_python"], "Sqrt variance Python", "viridis"),
    ]
    for ax, (arr, title, cmap) in zip(axes.ravel(), panels):
        save_map(ax, arr, title, cmap)
    fig.suptitle(f"ROI x490 control - {date_str}")
    fig.savefig(out_dir / "figures" / f"step10b_control_roi_{date_str}.png", dpi=160)
    plt.close(fig)


def save_slice_audit_figure(out_dir: Path, date_str: str, py: dict[str, Any], off: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    panels = [
        (off["STD"][0], "Oficial STD slice 0"),
        (off["STD"][1], "Oficial STD slice 1"),
        (py["STD"][0], "Python variance slice 0"),
        (py["STD"][1], "Python variance slice 1"),
    ]
    for ax, (arr, title) in zip(axes.ravel(), panels):
        save_map(ax, arr, title, "viridis")
    fig.suptitle(f"STD slice audit - {date_str}")
    fig.savefig(out_dir / "figures" / f"step10b_control_slice_audit_{date_str}.png", dpi=160)
    plt.close(fig)


def save_histograms(out_dir: Path, date_str: str, py: dict[str, Any], off: dict[str, Any]) -> None:
    ds = SELECTED_DAY_SLICE
    items = [
        ("TEMPpred oficial", off["TEMPpred"][ds], "TEMPpred Python", py["TEMPpred"][ds], "temppred"),
        ("STD oficial", off["STD"][ds], "Variance Python", py["STD"][ds], "std_vs_variance"),
        ("STD oficial", off["STD"][ds], "Sqrt variance Python", py["STD_sqrt_variance"][ds], "std_vs_sqrt"),
    ]
    for label_a, a, label_b, b, name in items:
        mask_a = np.isfinite(a)
        mask_b = np.isfinite(b)
        fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
        ax.hist(a[mask_a], bins=60, alpha=0.55, label=label_a)
        ax.hist(b[mask_b], bins=60, alpha=0.55, label=label_b)
        ax.legend()
        ax.set_title(f"{name} histogram - {date_str}")
        fig.savefig(out_dir / "figures" / f"step10b_control_hist_{name}_{date_str}.png", dpi=160)
        plt.close(fig)


def save_c01_c06_panel(out_dir: Path, row_slice: slice, col_slice: slice, mask: np.ndarray, october_arrays: dict[str, np.ndarray]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    pilot_paths = sorted(PILOT10B.glob("predmodels/*/python_dss_predModel_1_100real.nc"))
    fig, axes = plt.subplots(2, max(4, len(pilot_paths)), figsize=(5 * max(4, len(pilot_paths)), 7), constrained_layout=True)
    if axes.ndim == 1:
        axes = axes.reshape(2, -1)
    save_map(axes[0, 0], october_arrays["STD_official"], "October official STD ROI", "viridis")
    save_map(axes[0, 1], october_arrays["STD_python"], "October Python STD ROI", "viridis")
    for ax in axes[0, 2:]:
        ax.axis("off")
    for i, path in enumerate(pilot_paths):
        date = path.parent.name
        data = load_predmodel(path)
        std_roi = apply_roi(data["STD"], mask, row_slice, col_slice, SELECTED_DAY_SLICE)
        rows.append({"date": date, **metrics(std_roi, october_arrays["STD_step06"])})
        save_map(axes[1, i], std_roi, f"C01/C06 STD {date}", "viridis")
    for ax in axes[1, len(pilot_paths) :]:
        ax.axis("off")
    fig.suptitle("STD visual control: October vs C01/C06 pilot")
    fig.savefig(out_dir / "figures" / "step10b_control_c01_c06_std_visual_diagnosis.png", dpi=160)
    plt.close(fig)
    return pd.DataFrame(rows)


def main() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2024-10-30")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--regenerate-python-dss", action="store_true")
    args = parser.parse_args()

    out_dir = (args.output or RESULTS / f"fossum_roi_x490_step10b_control_october_python_vs_official_{now_tag()}").resolve()
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)

    config = {
        "date": args.date,
        "depth": 1,
        "n_realizations": 100,
        "selected_day_slice": SELECTED_DAY_SLICE,
        "step06": str(STEP06),
        "step00": str(STEP00),
        "roi_ref": str(ROI_REF),
        "regenerate_python_dss": args.regenerate_python_dss,
    }
    write_json(out_dir / "step10b_control_config.json", config)

    py_pred = python_predmodel_path(args.date)
    if args.regenerate_python_dss or not py_pred.exists():
        py_pred = run_python_dss(args.date, out_dir)
    off_pred = official_predmodel_path(args.date)

    py = load_predmodel(py_pred)
    off = load_predmodel(off_pred)
    row_slice, col_slice, roi_idx = roi_slices()
    mask = np.load(ROI_REF / "MASK_paper_roi_x490.npy").astype(bool)

    idx06 = step06_index(args.date)
    temp06 = np.load(STEP06 / "TEMPpred_october_surface_roi_x490.npy")[idx06].astype(np.float32)
    std06 = np.load(STEP06 / "STD_october_surface_roi_x490.npy")[idx06].astype(np.float32)

    temp_py_roi = apply_roi(py["TEMPpred"], mask, row_slice, col_slice, SELECTED_DAY_SLICE)
    std_var_py_roi = apply_roi(py["STD"], mask, row_slice, col_slice, SELECTED_DAY_SLICE)
    std_sqrt_py_roi = apply_roi(py["STD_sqrt_variance"], mask, row_slice, col_slice, SELECTED_DAY_SLICE)
    temp_off_roi = apply_roi(off["TEMPpred"], mask, row_slice, col_slice, SELECTED_DAY_SLICE)
    std_off_roi = apply_roi(off["STD"], mask, row_slice, col_slice, SELECTED_DAY_SLICE)

    np.save(out_dir / "TEMPpred_python_roi_x490.npy", temp_py_roi)
    np.save(out_dir / "STD_variance_python_roi_x490.npy", std_var_py_roi)
    np.save(out_dir / "STD_sqrt_python_roi_x490.npy", std_sqrt_py_roi)
    np.save(out_dir / "TEMPpred_official_roi_x490.npy", temp_off_roi)
    np.save(out_dir / "STD_official_roi_x490.npy", std_off_roi)
    np.save(out_dir / "TEMPpred_step06_roi_x490.npy", temp06)
    np.save(out_dir / "STD_step06_roi_x490.npy", std06)

    full_rows = [
        prefixed({"domain": "full_grid_all_slices", "variable": "TEMPpred_python_vs_official"}, metrics(py["TEMPpred"], off["TEMPpred"])),
        prefixed({"domain": "full_grid_slice1", "variable": "TEMPpred_python_vs_official"}, metrics(py["TEMPpred"][1], off["TEMPpred"][1])),
        prefixed({"domain": "full_grid_slice1", "variable": "STD_variance_python_vs_official"}, metrics(py["STD"][1], off["STD"][1])),
        prefixed({"domain": "full_grid_slice1", "variable": "STD_sqrt_python_vs_official"}, metrics(py["STD_sqrt_variance"][1], off["STD"][1])),
    ]
    pd.DataFrame(full_rows).to_csv(out_dir / "step10b_control_fullgrid_metrics.csv", index=False)

    roi_rows = [
        prefixed({"domain": "roi_x490", "variable": "TEMPpred_python_vs_official"}, metrics(temp_py_roi, temp_off_roi)),
        prefixed({"domain": "roi_x490", "variable": "STD_variance_python_vs_official"}, metrics(std_var_py_roi, std_off_roi)),
        prefixed({"domain": "roi_x490", "variable": "STD_sqrt_python_vs_official"}, metrics(std_sqrt_py_roi, std_off_roi)),
        prefixed({"domain": "roi_x490", "variable": "TEMPpred_python_vs_step06"}, metrics(temp_py_roi, temp06)),
        prefixed({"domain": "roi_x490", "variable": "STD_variance_python_vs_step06"}, metrics(std_var_py_roi, std06)),
    ]
    pd.DataFrame(roi_rows).to_csv(out_dir / "step10b_control_roi_metrics.csv", index=False)

    step06_rows = [
        prefixed({"comparison": "TEMPpred_official_predmodel_roi_vs_step06"}, metrics(temp_off_roi, temp06)),
        prefixed({"comparison": "STD_official_predmodel_roi_vs_step06"}, metrics(std_off_roi, std06)),
        prefixed({"comparison": "TEMPpred_python_roi_vs_step06"}, metrics(temp_py_roi, temp06)),
        prefixed({"comparison": "STD_variance_python_roi_vs_step06"}, metrics(std_var_py_roi, std06)),
    ]
    pd.DataFrame(step06_rows).to_csv(out_dir / "step10b_control_step06_consistency_metrics.csv", index=False)

    slice_rows = []
    for s in range(off["STD"].shape[0]):
        slice_rows.append(prefixed({"slice": s, "comparison": "official_STD_slice_vs_step06"}, metrics(apply_roi(off["STD"], mask, row_slice, col_slice, s), std06)))
        slice_rows.append(prefixed({"slice": s, "comparison": "python_variance_slice_vs_step06"}, metrics(apply_roi(py["STD"], mask, row_slice, col_slice, s), std06)))
        slice_rows.append(prefixed({"slice": s, "comparison": "python_sqrt_slice_vs_step06"}, metrics(apply_roi(py["STD_sqrt_variance"], mask, row_slice, col_slice, s), std06)))
    slice_df = pd.DataFrame(slice_rows)
    slice_df.to_csv(out_dir / "step10b_control_slice_variable_audit.csv", index=False)

    save_fullgrid_figure(out_dir, args.date, py, off)
    roi_arrays = {
        "TEMPpred_step06": temp06,
        "TEMPpred_python": temp_py_roi,
        "TEMPpred_official": temp_off_roi,
        "STD_step06": std06,
        "STD_variance_python": std_var_py_roi,
        "STD_sqrt_python": std_sqrt_py_roi,
    }
    save_roi_figure(out_dir, args.date, roi_arrays)
    save_slice_audit_figure(out_dir, args.date, py, off)
    save_histograms(out_dir, args.date, py, off)
    c01_df = save_c01_c06_panel(out_dir, row_slice, col_slice, mask, {"STD_official": std_off_roi, "STD_python": std_var_py_roi, "STD_step06": std06})

    best_uncertainty = "variance" if full_rows[2]["rmse"] <= full_rows[3]["rmse"] else "sqrt_variance"
    best_slice = int(slice_df.sort_values("rmse").iloc[0]["slice"])
    off_vs_step06_temp = step06_rows[0]
    off_vs_step06_std = step06_rows[1]
    control_pass = (
        off_pred.exists()
        and py_pred.exists()
        and list(temp_py_roi.shape) == [72, 117]
        and best_uncertainty == "variance"
        and best_slice == SELECTED_DAY_SLICE
        and float(off_vs_step06_temp["rmse"]) < 1e-5
        and float(off_vs_step06_std["rmse"]) < 1e-5
        and float(roi_rows[0]["pearson"]) >= 0.99
        and float(roi_rows[1]["rmse"]) <= 0.02
        and abs(float(roi_rows[1]["candidate_mean"]) - float(roi_rows[1]["reference_mean"])) <= 0.01
    )
    c01_means = c01_df["candidate_mean"].astype(float).tolist() if not c01_df.empty else []
    october_std_mean = float(np.nanmean(std06))
    c01_c06_low_real = bool(c01_means and min(c01_means) < 0.5 * october_std_mean)
    if control_pass and c01_c06_low_real:
        verdict = "CONTROL_PASS_BUT_C01_C06_LOW_UNCERTAINTY_REAL"
    elif control_pass:
        verdict = "CONTROL_PASS_PYTHON_DSS_AND_STEP06_CONSISTENT"
    elif best_uncertainty != "variance" or best_slice != SELECTED_DAY_SLICE:
        verdict = "CONTROL_WARNING_SLICE_OR_VARIABLE_MISMATCH"
    else:
        verdict = "CONTROL_FAIL_DO_NOT_ADVANCE_STEP10C"

    plotting_diag = pd.DataFrame(
        [
            {
                "item": "STD_variable",
                "diagnosis": "Use predModel STD as variance; STD_sqrt_variance is diagnostic only.",
                "status": "OK" if best_uncertainty == "variance" else "WARNING",
            },
            {
                "item": "day_slice",
                "diagnosis": f"Use slice {SELECTED_DAY_SLICE}; best Step06 match slice is {best_slice}.",
                "status": "OK" if best_slice == SELECTED_DAY_SLICE else "WARNING",
            },
            {
                "item": "C01_C06_STD_panel",
                "diagnosis": "Pilot C01/C06 STD panel uses the same slice and variance variable as October control.",
                "status": "LOW_UNCERTAINTY_REAL" if c01_c06_low_real else "OK",
            },
        ]
    )
    plotting_diag.to_csv(out_dir / "step10b_control_plotting_diagnosis.csv", index=False)

    checks = {
        "date": args.date,
        "official_predmodel_found": off_pred.exists(),
        "python_predmodel_found": py_pred.exists(),
        "python_predmodel_generated_now": args.regenerate_python_dss,
        "n_realizations": 100,
        "selected_day_slice": SELECTED_DAY_SLICE,
        "best_step06_slice": best_slice,
        "std_official_closer_to": best_uncertainty,
        "roi_shape_python": list(temp_py_roi.shape),
        "roi_shape_official": list(temp_off_roi.shape),
        "step06_matches_official_temppred": float(off_vs_step06_temp["rmse"]) < 1e-5,
        "step06_matches_official_std": float(off_vs_step06_std["rmse"]) < 1e-5,
        "matlab_used": False,
        "hres_regenerated": False,
        "c01_c06_generated": False,
        "verdict": verdict,
    }
    write_json(out_dir / "step10b_control_checks.json", checks)
    metadata = {
        "official_predmodel": str(off_pred),
        "python_predmodel": str(py_pred),
        "official_variables": off["variables"],
        "python_variables": py["variables"],
        "roi_indices": roi_idx,
        "step06_index": idx06,
    }
    write_json(out_dir / "step10b_control_metadata.json", metadata)

    summary = [
        "# Step10B Control October Python vs Official",
        "",
        f"- Date: `{args.date}`",
        f"- Official predModel: `{off_pred}`",
        f"- Python predModel: `{py_pred}`",
        f"- ROI shape: `{list(temp_py_roi.shape)}`",
        f"- Correct STD variable: `{best_uncertainty}`",
        f"- Correct day slice: `{best_slice}`",
        f"- Step06 TEMPpred matches official predModel ROI: `{checks['step06_matches_official_temppred']}`",
        f"- Step06 STD matches official predModel ROI: `{checks['step06_matches_official_std']}`",
        f"- Verdict: `{verdict}`",
    ]
    (out_dir / "step10b_control_summary.md").write_text("\n".join(summary), encoding="utf-8")
    report = summary + [
        "",
        "The control uses existing HRes and does not use MATLAB. C01/C06 pilot predModels were only read for visual diagnosis; no new pilot dates were generated.",
    ]
    (out_dir / "step10b_control_report.md").write_text("\n".join(report), encoding="utf-8")
    recommendation = "Advance to Step10C for the C01/C06 pilot predModels." if verdict != "CONTROL_FAIL_DO_NOT_ADVANCE_STEP10C" else "Do not advance to Step10C until slice/variable differences are fixed."
    (out_dir / "step10b_control_next_step_recommendation.md").write_text(
        f"# Next Step Recommendation\n\n{recommendation}\n\nFinal verdict: `{verdict}`\n",
        encoding="utf-8",
    )
    print(f"Output: {out_dir}")
    return out_dir


if __name__ == "__main__":
    main()
