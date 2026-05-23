from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd

from step10b_python_dss_utils import (
    DssConfig,
    build_dss_parameter_file,
    compute_temppred_uncertainty_from_realizations,
    copy_dss_exe_to_input,
    find_dss_exe,
    load_hres_for_date,
    read_dss_simulation_outputs,
    run_dss_executable,
    write_gslib_input,
    write_predmodel_nc,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP05 = RESULTS / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260514_164854"
HRES_OUTPUT = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
FILIPA_ROOT = ROOT / "data" / "dadosParaPedro_Fresnel" / "dadosParaPedro_Fresnel"
PASS_MARKER = RESULTS / "step10b_python_dss_validation_pass_marker.json"

VARIOGRAM_SURFACE = (1000, 400, 100)
EXPECTED_COUNTS = {"C01": 41, "C06": 72}
CLASS_LABELS = {1: "C01", 6: "C06"}


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def finite_stats(arr: np.ndarray, prefix: str) -> dict[str, Any]:
    arr = np.asarray(arr, dtype=np.float64)
    valid = np.isfinite(arr)
    out: dict[str, Any] = {
        f"{prefix}_valid_count": int(valid.sum()),
        f"{prefix}_nan_fraction": float(np.mean(~valid)),
        f"{prefix}_all_nan": bool(valid.sum() == 0),
    }
    if valid.sum():
        vals = arr[valid]
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


def gradient_mean(arr: np.ndarray) -> float:
    temp = np.asarray(arr, dtype=np.float64)
    gy, gx = np.gradient(temp)
    mag = np.sqrt(gx * gx + gy * gy)
    vals = mag[np.isfinite(mag)]
    return float(np.mean(vals)) if vals.size else math.nan


def read_selected_dates() -> pd.DataFrame:
    assignments = pd.read_csv(STEP05 / "canonical_assignments.csv")
    dates = pd.read_csv(STEP00 / "dates_370.csv")
    df = assignments[assignments["class_id"].isin([1, 6])].copy()
    df["date"] = df["date"].astype(str).str[:10]
    df["day_index_370"] = df["image_idx_0_based"].astype(int) + 1
    df["class_label"] = df["class_id"].map(CLASS_LABELS)
    date_check = dates.copy()
    date_check["date"] = date_check["date"].astype(str).str[:10]
    merged = df.merge(date_check.rename(columns={"time_index": "step00_time_index"}), on="date", how="left")
    return merged[["date", "day_index_370", "step00_time_index", "class_id", "class_label"]].sort_values(["class_id", "date"])


def load_priority() -> pd.DataFrame:
    candidates = sorted(RESULTS.glob("fossum_roi_x490_step10a*_*/step10a_generation_priority_list.csv"))
    if not candidates:
        return pd.DataFrame(columns=["date", "priority_rank", "priority_score", "representative_score", "rmse"])
    df = pd.read_csv(candidates[-1])
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col is None:
        return pd.DataFrame(columns=["date", "priority_rank", "priority_score", "representative_score", "rmse"])
    out = pd.DataFrame({"date": df[date_col].astype(str).str[:10]})
    for col in ["priority_rank", "priority_score", "representative_score", "rmse"]:
        if col in df.columns:
            out[col] = df[col]
    if "priority_rank" not in out.columns:
        out["priority_rank"] = np.arange(1, len(out) + 1)
    return out


def build_config(output_dir: Path, n_realizations: int) -> DssConfig:
    return DssConfig(
        repo_root=ROOT,
        filipa_root=FILIPA_ROOT,
        hres_output=HRES_OUTPUT,
        dss_exe=find_dss_exe(FILIPA_ROOT),
        output_dir=output_dir,
        n_realizations=n_realizations,
    )


def expected_predmodel(output_dir: Path, date: str, n_realizations: int) -> Path:
    return output_dir / "predmodels" / date / f"python_dss_predModel_1_{n_realizations}real.nc"


def create_manifest(output_dir: Path, n_realizations: int, resume: bool, top_per_class: int | None = None) -> pd.DataFrame:
    df = read_selected_dates()
    priority = load_priority()
    df = df.merge(priority, on="date", how="left")
    df["priority_rank"] = df["priority_rank"].astype("Int64")
    if "priority_score" not in df.columns:
        df["priority_score"] = np.nan
    if "representative_score" not in df.columns:
        df["representative_score"] = np.nan
    if "rmse" not in df.columns:
        df["rmse"] = np.nan
    if top_per_class is not None:
        selected = []
        for class_label in ["C01", "C06"]:
            part = df[df["class_label"] == class_label].copy()
            part["_rank_sort"] = part["priority_rank"].fillna(10**9).astype(float)
            part["_score_sort"] = part["priority_score"].fillna(-np.inf).astype(float)
            part = part.sort_values(["_rank_sort", "_score_sort", "date"], ascending=[True, False, True]).head(top_per_class)
            selected.append(part.drop(columns=["_rank_sort", "_score_sort"]))
        df = pd.concat(selected, ignore_index=True).sort_values(["class_label", "priority_rank", "date"])
    dates_available = pd.read_csv(HRES_OUTPUT / "dates_370.csv")
    available_set = set(dates_available["date"].astype(str).str[:10])
    pred_dates = []
    hres_available = []
    for date in df["date"]:
        pred = (datetime.strptime(date, "%Y-%m-%d") - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        pred_dates.append(pred)
        hres_available.append(pred in available_set)
    df["hres_window_end_date"] = pred_dates
    df["hres_available"] = hres_available
    df["predmodel_path"] = [str(expected_predmodel(output_dir, d, n_realizations)) for d in df["date"]]
    df["predmodel_already_exists"] = [Path(p).exists() for p in df["predmodel_path"]]
    df["generation_status"] = np.where(df["predmodel_already_exists"] & resume, "already_done", "pending")
    return df


def disk_estimate(manifest: pd.DataFrame, output_dir: Path, n_realizations: int) -> dict[str, Any]:
    validation_sim = next(RESULTS.glob("fossum_roi_x490_step10b_python_dss_validation100_*/dss_outputs/*/depth_01/sim_1.out"), None)
    sim_size = validation_sim.stat().st_size if validation_sim and validation_sim.exists() else 6_800_000
    pred_size = 7_300_000
    input_size = 39_000_000
    n_pending = int((manifest["generation_status"] != "already_done").sum())
    total = n_pending * (n_realizations * sim_size + pred_size + input_size)
    usage = shutil.disk_usage(output_dir.anchor or ROOT.anchor)
    return {
        "n_pending_days": n_pending,
        "n_realizations_per_day": n_realizations,
        "sim_size_bytes_assumed": int(sim_size),
        "estimated_total_bytes": int(total),
        "estimated_total_gb": round(total / 1024**3, 2),
        "free_bytes": int(usage.free),
        "free_gb": round(usage.free / 1024**3, 2),
        "sufficient_space_with_15_percent_margin": bool(usage.free > total * 1.15),
        "note": "Estimate includes sim_*.out, predModel and GSLIB inputs. It intentionally keeps sim outputs as requested.",
    }


def generate_one_day(
    date: str,
    cfg: DssConfig,
    *,
    n_realizations: int,
    seed: int,
    timeout_s: int,
    overwrite: bool,
) -> tuple[Path | None, dict[str, Any], list[str]]:
    warnings: list[str] = []
    pred_path = expected_predmodel(cfg.output_dir, date, n_realizations)
    if pred_path.exists() and not overwrite:
        return pred_path, {"date": date, "status": "already_done", "predmodel": str(pred_path), "dss_returncode": None}, warnings

    input_path = cfg.output_dir / "dss_inputs" / date / "depth_01"
    output_path = cfg.output_dir / "dss_outputs" / date / "depth_01"
    log_path = cfg.output_dir / "logs" / date
    log_path.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        hres = load_hres_for_date(cfg, date, source="python_370")
        prep = write_gslib_input(input_path, output_path, hres["TEMP_xy_t"], hres["BATHY_xy"])
        copy_dss_exe_to_input(cfg.dss_exe, input_path)
        par = build_dss_parameter_file(
            input_path,
            output_path / "sim",
            nx=prep["nx"],
            ny=prep["ny"],
            nz=prep["nz"],
            bounds=tuple(prep["bounds"]),
            n_realizations=n_realizations,
            variogram=VARIOGRAM_SURFACE,
            seed=seed,
        )
        dss_result = run_dss_executable(input_path / "DSS.C.64.exe", par, timeout_s=timeout_s)
        write_json(log_path / "dss_result.json", dss_result)
        (log_path / "dss_stdout.txt").write_text(str(dss_result.get("stdout", "")), encoding="utf-8")
        (log_path / "dss_stderr.txt").write_text(str(dss_result.get("stderr", "")), encoding="utf-8")
        if not dss_result["success"]:
            return None, {
                "date": date,
                "status": "dss_failed",
                "dss_returncode": dss_result.get("returncode"),
                "runtime_seconds": round(time.time() - t0, 2),
            }, warnings
        sims = read_dss_simulation_outputs(output_path / "sim", n_realizations, prep["nx"] * prep["ny"] * prep["nz"])
        temppred, variance, std_sqrt = compute_temppred_uncertainty_from_realizations(
            sims,
            nx=prep["nx"],
            ny=prep["ny"],
            input_days=prep["input_days"],
            output_days=2,
        )
        write_predmodel_nc(pred_path, hres, temppred, variance, std_sqrt_day_lat_lon=std_sqrt)
        sim_count = len(list(output_path.glob("sim_*.out")))
        meta = {
            "date": date,
            "status": "success",
            "predmodel": str(pred_path),
            "dss_returncode": dss_result.get("returncode"),
            "runtime_seconds": round(time.time() - t0, 2),
            "sim_outputs": sim_count,
            "n_realizations": n_realizations,
            "par_file": str(par),
        }
        return pred_path, meta, warnings
    except Exception as exc:
        return None, {"date": date, "status": "exception", "error": repr(exc), "runtime_seconds": round(time.time() - t0, 2)}, warnings


def predmodel_metrics(path: Path, date: str, class_label: str, day_index_370: int, status_meta: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "date": date,
        "class_label": class_label,
        "day_index_370": day_index_370,
        "predmodel": str(path),
        "predmodel_exists": path.exists(),
    }
    row.update(status_meta)
    if not path.exists():
        return row
    with netCDF4.Dataset(path) as ds:
        vars_present = set(ds.variables.keys())
        row.update(
            {
                "has_TEMPpred": "TEMPpred" in vars_present,
                "has_STD": "STD" in vars_present,
                "has_LAT": "LAT" in vars_present,
                "has_LON": "LON" in vars_present,
                "has_BATHY": "BATHY" in vars_present,
            }
        )
        temp = np.asarray(ds.variables["TEMPpred"][:], dtype=np.float64)[1]
        std = np.asarray(ds.variables["STD"][:], dtype=np.float64)[1]
    row.update(finite_stats(temp, "TEMPpred"))
    row.update(finite_stats(std, "STD_variance"))
    row["TEMPpred_gradient_mean"] = gradient_mean(temp)
    return row


def load_metrics_for_plot(metrics_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in metrics_df.iterrows():
        p = Path(str(r["predmodel"]))
        if not p.exists():
            continue
        with netCDF4.Dataset(p) as ds:
            rows.append(
                {
                    "date": r["date"],
                    "class_label": r["class_label"],
                    "TEMPpred": np.asarray(ds.variables["TEMPpred"][:], dtype=np.float64)[1],
                    "STD": np.asarray(ds.variables["STD"][:], dtype=np.float64)[1],
                    "std_mean": float(r["STD_variance_mean"]),
                    "std_max": float(r["STD_variance_max"]),
                    "gradient_mean": float(r.get("TEMPpred_gradient_mean", np.nan)),
                }
            )
    return rows


def plot_pages(rows: list[dict[str, Any]], output_dir: Path, class_label: str, variable: str, values: tuple[float, float], page_size: int = 12) -> list[str]:
    paths: list[str] = []
    subset = [r for r in rows if r["class_label"] == class_label]
    vmin, vmax = values
    for start in range(0, len(subset), page_size):
        page = subset[start : start + page_size]
        cols = 4
        nrows = int(math.ceil(len(page) / cols))
        fig, axes = plt.subplots(nrows, cols, figsize=(14, 3.2 * nrows), constrained_layout=True)
        axes_flat = np.ravel(axes)
        cmap = "coolwarm" if variable == "TEMPpred" else "viridis"
        im = None
        for i, ax in enumerate(axes_flat):
            if i >= len(page):
                ax.axis("off")
                continue
            arr = page[i][variable if variable == "TEMPpred" else "STD"]
            im = ax.imshow(np.ma.masked_invalid(arr), origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
            ax.set_title(page[i]["date"], fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        if im is not None:
            fig.colorbar(im, ax=axes_flat.tolist(), shrink=0.75, label=variable if variable == "TEMPpred" else "STD variance")
        out = output_dir / "figures" / f"step10d_{class_label}_{'STD_variance' if variable != 'TEMPpred' else 'TEMPpred'}_pages_{start // page_size + 1:02d}.png"
        fig.savefig(out, dpi=160)
        plt.close(fig)
        paths.append(str(out))
    return paths


def plot_top(rows: list[dict[str, Any]], output_dir: Path, class_label: str, by: str, outfile: str) -> str | None:
    subset = [r for r in rows if r["class_label"] == class_label]
    if not subset:
        return None
    subset = sorted(subset, key=lambda r: r[by], reverse=True)[:12]
    fig, axes = plt.subplots(len(subset), 2, figsize=(9, 2.2 * len(subset)), constrained_layout=True)
    for axrow, r in zip(axes, subset):
        im0 = axrow[0].imshow(np.ma.masked_invalid(r["TEMPpred"]), origin="lower", cmap="coolwarm")
        axrow[0].set_title(f"{r['date']} TEMPpred")
        im1 = axrow[1].imshow(np.ma.masked_invalid(r["STD"]), origin="lower", cmap="viridis")
        axrow[1].set_title(f"{r['date']} STD variance {by}={r[by]:.4g}")
        for ax in axrow:
            ax.set_xticks([])
            ax.set_yticks([])
        fig.colorbar(im0, ax=axrow[0], fraction=0.046, pad=0.04)
        fig.colorbar(im1, ax=axrow[1], fraction=0.046, pad=0.04)
    out = output_dir / "figures" / outfile
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return str(out)


def create_figures_and_rankings(output_dir: Path, metrics_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)
    rows = load_metrics_for_plot(metrics_df)
    if not rows:
        return pd.DataFrame(), []
    temp_vals = np.concatenate([r["TEMPpred"][np.isfinite(r["TEMPpred"])] for r in rows])
    std_vals = np.concatenate([r["STD"][np.isfinite(r["STD"])] for r in rows])
    temp_scale = tuple(np.percentile(temp_vals, [1, 99]))
    std_scale = tuple(np.percentile(std_vals, [1, 99]))
    figs: list[str] = []
    for cls in ["C01", "C06"]:
        figs += plot_pages(rows, output_dir, cls, "TEMPpred", temp_scale)
        figs += plot_pages(rows, output_dir, cls, "STD", std_scale)
        figs.append(plot_top(rows, output_dir, cls, "std_mean", f"step10d_top_{cls}_by_STD_mean.png") or "")
        figs.append(plot_top(rows, output_dir, cls, "std_max", f"step10d_top_{cls}_by_STD_max.png") or "")
    rank = metrics_df.copy()
    rank["std_mean_rank"] = rank["STD_variance_mean"].rank(ascending=False, method="min")
    rank["std_max_rank"] = rank["STD_variance_max"].rank(ascending=False, method="min")
    rank["std_p95_rank"] = rank["STD_variance_p95"].rank(ascending=False, method="min")
    rank["gradient_rank"] = rank["TEMPpred_gradient_mean"].rank(ascending=False, method="min")
    rank["candidate_score"] = (
        0.35 / rank["std_mean_rank"] + 0.25 / rank["std_max_rank"] + 0.2 / rank["std_p95_rank"] + 0.2 / rank["gradient_rank"]
    )
    rank = rank.sort_values("candidate_score", ascending=False)
    top_global = rank.head(12)
    top_rows = []
    for _, r in top_global.iterrows():
        pred = Path(str(r["predmodel"]))
        if not pred.exists():
            continue
        with netCDF4.Dataset(pred) as ds:
            top_rows.append(
                {
                    "date": r["date"],
                    "class_label": r["class_label"],
                    "TEMPpred": np.asarray(ds.variables["TEMPpred"][:], dtype=np.float64)[1],
                    "STD": np.asarray(ds.variables["STD"][:], dtype=np.float64)[1],
                    "std_mean": float(r["STD_variance_mean"]),
                }
            )
    if top_rows:
        fig, axes = plt.subplots(len(top_rows), 2, figsize=(9, 2.2 * len(top_rows)), constrained_layout=True)
        for axrow, r in zip(axes, top_rows):
            im0 = axrow[0].imshow(np.ma.masked_invalid(r["TEMPpred"]), origin="lower", cmap="coolwarm")
            im1 = axrow[1].imshow(np.ma.masked_invalid(r["STD"]), origin="lower", cmap="viridis")
            axrow[0].set_title(f"{r['date']} {r['class_label']} TEMPpred")
            axrow[1].set_title(f"{r['date']} STD mean={r['std_mean']:.4g}")
            for ax in axrow:
                ax.set_xticks([])
                ax.set_yticks([])
            fig.colorbar(im0, ax=axrow[0], fraction=0.046, pad=0.04)
            fig.colorbar(im1, ax=axrow[1], fraction=0.046, pad=0.04)
        out = output_dir / "figures" / "step10d_top_candidates_TEMPpred_STD_side_by_side.png"
        fig.savefig(out, dpi=160)
        plt.close(fig)
        figs.append(str(out))
    return rank, [f for f in figs if f]


def main() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-dss", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--n-realizations", type=int, default=100)
    parser.add_argument("--depths", default="1")
    parser.add_argument("--timeout-s", type=int, default=7200)
    parser.add_argument("--seed", type=int, default=110011)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--ignore-disk-warning", action="store_true")
    parser.add_argument("--top-per-class", type=int, default=None, help="Select top N priority-ranked days from C01 and C06 instead of all 113.")
    args = parser.parse_args()

    if args.depths.replace(",", " ").split() != ["1"]:
        raise ValueError("Step10D currently supports depth=1 only, matching validation.")
    output_dir = (args.output or RESULTS / f"fossum_roi_x490_step10d_all_class01_class06_python_dss_{now_tag()}").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)
    cfg = build_config(output_dir, args.n_realizations)
    manifest = create_manifest(output_dir, args.n_realizations, args.resume, args.top_per_class)
    manifest.to_csv(output_dir / "step10d_all_class01_class06_dates.csv", index=False)
    manifest.to_csv(output_dir / "step10d_batch_manifest.csv", index=False)
    manifest.to_csv(output_dir / "step10d_expected_outputs.csv", index=False)
    disk = disk_estimate(manifest, output_dir, args.n_realizations)
    write_json(output_dir / "step10d_disk_space_estimate.json", disk)
    config = {
        "depths": [1],
        "n_realizations": args.n_realizations,
        "seed": args.seed,
        "timeout_s": args.timeout_s,
        "std_definition": "variance",
        "top_per_class": args.top_per_class,
        "matlab_used": False,
        "hres_regenerated": False,
        "validation_marker": str(PASS_MARKER),
    }
    write_json(output_dir / "step10d_config.json", config)

    c01_count = int((manifest["class_label"] == "C01").sum())
    c06_count = int((manifest["class_label"] == "C06").sum())
    expected_c01 = args.top_per_class if args.top_per_class is not None else 41
    expected_c06 = args.top_per_class if args.top_per_class is not None else 72
    hres_ok = bool(manifest["hres_available"].all())
    dry_ready = c01_count == expected_c01 and c06_count == expected_c06 and hres_ok and cfg.dss_exe.exists()
    disk_ok = bool(disk["sufficient_space_with_15_percent_margin"])

    if args.dry_run or not args.execute_dss:
        checks = {
            "c01_days": c01_count,
            "c06_days": c06_count,
            "total_days": int(len(manifest)),
            "hres_available_all": hres_ok,
            "dss_found": cfg.dss_exe.exists(),
            "n_realizations_per_day": args.n_realizations,
            "expected_sim_outputs": int(len(manifest) * args.n_realizations),
            "expected_predmodels": int(len(manifest)),
            "top_per_class": args.top_per_class,
            "disk_space_sufficient": disk_ok,
            "matlab_used": False,
            "hres_regenerated": False,
            "verdict": "BATCH_DRY_RUN_READY_EXECUTE_REAL" if dry_ready and disk_ok else "BATCH_DRY_RUN_READY_BUT_DISK_SPACE_WARNING",
        }
        write_json(output_dir / "step10d_checks.json", checks)
        report = [
            "# Step10D Batch Dry Run Report",
            "",
            f"- C01 days: {c01_count}",
            f"- C06 days: {c06_count}",
            f"- Total days: {len(manifest)}",
            f"- Top per class: {args.top_per_class}",
            f"- Expected sim_*.out: {len(manifest) * args.n_realizations}",
            f"- Estimated disk: {disk['estimated_total_gb']} GB",
            f"- Free disk: {disk['free_gb']} GB",
            f"- Disk sufficient with margin: {disk_ok}",
            f"- Verdict: `{checks['verdict']}`",
        ]
        (output_dir / "step10d_batch_dry_run_report.md").write_text("\n".join(report), encoding="utf-8")
        (output_dir / "step10d_summary.md").write_text("\n".join(report), encoding="utf-8")
        (output_dir / "step10d_report.md").write_text("\n".join(report), encoding="utf-8")
        (output_dir / "step10d_next_step_recommendation.md").write_text(
            "# Step10D Recommendation\n\nDo not execute the full batch while keeping all sim_*.out unless enough disk is available.\n",
            encoding="utf-8",
        )
        print(f"Output: {output_dir}")
        return output_dir

    if not disk_ok and not args.ignore_disk_warning:
        checks = {
            "c01_days": c01_count,
            "c06_days": c06_count,
            "total_days": int(len(manifest)),
            "top_per_class": args.top_per_class,
            "disk_space_sufficient": False,
            "estimated_total_gb": disk["estimated_total_gb"],
            "free_gb": disk["free_gb"],
            "verdict": "BATCH_GENERATION_FAILED",
            "reason": "Insufficient disk space to keep all requested sim_*.out files.",
        }
        write_json(output_dir / "step10d_checks.json", checks)
        pd.DataFrame().to_csv(output_dir / "step10d_generation_status.csv", index=False)
        (output_dir / "step10d_report.md").write_text(
            f"# Step10D Batch Not Started\n\nEstimated {disk['estimated_total_gb']} GB but only {disk['free_gb']} GB free. The real run was not started.\n",
            encoding="utf-8",
        )
        print(f"Output: {output_dir}")
        return output_dir

    status_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    warning_rows: list[dict[str, Any]] = []
    for _, row in manifest.iterrows():
        date = str(row["date"])
        if not bool(row["hres_available"]):
            status = {"date": date, "status": "missing_hres"}
            status_rows.append(status)
            warning_rows.append({"date": date, "warning": "missing_hres"})
            continue
        pred, status, warns = generate_one_day(
            date,
            cfg,
            n_realizations=args.n_realizations,
            seed=args.seed,
            timeout_s=args.timeout_s,
            overwrite=args.overwrite,
        )
        status_rows.append(status)
        for w in warns:
            warning_rows.append({"date": date, "warning": w})
        if pred and pred.exists():
            metric_rows.append(predmodel_metrics(pred, date, str(row["class_label"]), int(row["day_index_370"]), status))
        pd.DataFrame(status_rows).to_csv(output_dir / "step10d_generation_status.csv", index=False)
        pd.DataFrame(metric_rows).to_csv(output_dir / "step10d_generation_day_metrics.csv", index=False)
        pd.DataFrame(warning_rows).to_csv(output_dir / "step10d_warnings.csv", index=False)

    status_df = pd.DataFrame(status_rows)
    metrics_df = pd.DataFrame(metric_rows)
    failed = status_df[~status_df["status"].isin(["success", "already_done"])] if not status_df.empty else pd.DataFrame()
    failed.to_csv(output_dir / "step10d_failed_days.csv", index=False)
    if warning_rows:
        pd.DataFrame(warning_rows).to_csv(output_dir / "step10d_warnings.csv", index=False)
    else:
        pd.DataFrame(columns=["date", "warning"]).to_csv(output_dir / "step10d_warnings.csv", index=False)
    if not metrics_df.empty:
        rank, figs = create_figures_and_rankings(output_dir, metrics_df)
        rank.to_csv(output_dir / "step10d_candidate_ranking.csv", index=False)
        rec_visual = pd.concat([rank[rank["class_label"] == "C01"].head(12), rank[rank["class_label"] == "C06"].head(12), rank.head(12)]).drop_duplicates("date")
        rec_visual.to_csv(output_dir / "step10d_recommended_days_for_visual_review.csv", index=False)
        rec_planner = pd.concat([rank[rank["class_label"] == "C01"].head(5), rank[rank["class_label"] == "C06"].head(5), rank.head(5)]).drop_duplicates("date")
        rec_planner.to_csv(output_dir / "step10d_recommended_days_for_planner_pilot.csv", index=False)
    else:
        figs = []
        pd.DataFrame().to_csv(output_dir / "step10d_candidate_ranking.csv", index=False)
        pd.DataFrame().to_csv(output_dir / "step10d_recommended_days_for_visual_review.csv", index=False)
        pd.DataFrame().to_csv(output_dir / "step10d_recommended_days_for_planner_pilot.csv", index=False)

    success_count = int(status_df["status"].isin(["success", "already_done"]).sum()) if not status_df.empty else 0
    verdict = "ALL_C01_C06_PREDMODELS_GENERATED_READY_FOR_ROI_EXTRACTION" if success_count == len(manifest) and failed.empty else "PARTIAL_C01_C06_PREDMODELS_GENERATED_REVIEW_FAILURES"
    checks = {
        "c01_days": c01_count,
        "c06_days": c06_count,
        "total_days": int(len(manifest)),
        "top_per_class": args.top_per_class,
        "predmodels_success_or_already_done": success_count,
        "failed_days": int(len(failed)),
        "n_realizations_per_day": args.n_realizations,
        "std_definition": "variance",
        "matlab_used": False,
        "hres_regenerated": False,
        "figures_created": len(figs),
        "verdict": verdict,
    }
    write_json(output_dir / "step10d_checks.json", checks)
    write_json(output_dir / "step10d_metadata.json", {"output_dir": str(output_dir), "dss_exe": str(cfg.dss_exe), "figures": figs})
    summary = [
        "# Step10D C01/C06 Python+DSS Batch Summary",
        "",
        f"- C01 days: {c01_count}",
        f"- C06 days: {c06_count}",
        f"- Total days: {len(manifest)}",
        f"- Successful/already done: {success_count}",
        f"- Failed: {len(failed)}",
        f"- Verdict: `{verdict}`",
    ]
    (output_dir / "step10d_summary.md").write_text("\n".join(summary), encoding="utf-8")
    (output_dir / "step10d_report.md").write_text("\n".join(summary), encoding="utf-8")
    (output_dir / "step10d_next_step_recommendation.md").write_text(
        "# Step10D Next Step Recommendation\n\nProceed to ROI x490 extraction for successful predModels.\n",
        encoding="utf-8",
    )
    print(f"Output: {output_dir}")
    return output_dir


if __name__ == "__main__":
    main()
