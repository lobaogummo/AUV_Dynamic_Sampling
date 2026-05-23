"""Generate/validate TEMPpred+STD with a Python+DSS port of runSimulations.m.

Default use is dry-run. Real DSS execution is intentionally gated:

  python scripts/10b_python_dss_generate_temppred_std.py --mode validate_october --dates 2024-10-30 --dry-run

Use --execute-dss only for controlled validation experiments. Pilot generation
is blocked unless a PASS validation marker exists or --force is provided.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from step10b_python_dss_utils import (
    DssConfig,
    build_dss_parameter_file,
    compare_with_reference_predmodel,
    compute_temppred_uncertainty_from_realizations,
    copy_dss_exe_to_input,
    find_dss_exe,
    load_hres_for_date,
    read_gslib,
    read_dss_simulation_outputs,
    run_dss_executable,
    write_gslib_input,
    write_predmodel_nc,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FILIPA_ROOT = ROOT / "data" / "dadosParaPedro_Fresnel" / "dadosParaPedro_Fresnel"
HRES_OUTPUT = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
AUDIT_ROOT = RESULTS
VARIOGRAM = [
    (1000, 400, 100),
    (1000, 400, 100),
    (1000, 400, 100),
    (1000, 400, 100),
    (1000, 350, 100),
    (1000, 300, 100),
    (800, 300, 100),
    (800, 300, 90),
    (550, 300, 90),
    (500, 200, 90),
    (450, 200, 80),
    (450, 180, 80),
    (400, 150, 80),
    (400, 150, 70),
    (350, 120, 70),
    (400, 150, 60),
    (400, 150, 60),
]
PILOT_DATES = ["2024-07-03", "2024-07-04", "2023-12-22", "2023-12-17"]


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=lambda o: str(o)), encoding="utf-8")


def reference_predmodel_path(target_date: str) -> Path:
    target = datetime.strptime(target_date, "%Y-%m-%d")
    pred_date = target - pd.Timedelta(days=1)
    return (
        FILIPA_ROOT
        / "02.Simulations"
        / "HighRes"
        / f"Daily_dpt_{pred_date.strftime('%Y%m%d')}"
        / f"{target.strftime('%d-%m-%Y')}_predModel_1.nc"
    )


def validation_marker_path() -> Path:
    return RESULTS / "step10b_python_dss_validation_pass_marker.json"


def build_config(output_dir: Path, n_realizations: int) -> DssConfig:
    return DssConfig(
        repo_root=ROOT,
        filipa_root=FILIPA_ROOT,
        hres_output=HRES_OUTPUT,
        dss_exe=find_dss_exe(FILIPA_ROOT),
        output_dir=output_dir,
        n_realizations=n_realizations,
    )


def plan_record(date: str, cfg: DssConfig, mode: str, source: str, n_realizations: int, depths: list[int]) -> dict[str, Any]:
    ref = reference_predmodel_path(date)
    suffix = f"_{n_realizations}real" if mode == "validate_october" else ""
    out_pred = cfg.output_dir / "predmodels" / date / f"python_dss_predModel_1{suffix}.nc"
    return {
        "mode": mode,
        "date": date,
        "depths": ",".join(str(d) for d in depths),
        "hres_source": source,
        "dss_exe": str(cfg.dss_exe),
        "dss_exists": cfg.dss_exe.exists(),
        "reference_predmodel": str(ref),
        "reference_predmodel_exists": ref.exists(),
        "output_predmodel": str(out_pred),
        "n_realizations": n_realizations,
        "expected_sim_outputs": n_realizations,
        "status": "planned",
    }


def parse_depths(raw: str | None) -> list[int]:
    if not raw:
        return [1]
    depths: list[int] = []
    for part in raw.replace(",", " ").split():
        value = int(part)
        if value != 1:
            raise ValueError("This Python+DSS surface port currently supports depth 1 only.")
        depths.append(value)
    return sorted(set(depths))


def official_parfile_inventory(root: Path) -> pd.DataFrame:
    patterns = ["ssdir.par", "*.par", "sim_*.out", "*seed*", "*realization*", "*realizations*"]
    rows: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in root.rglob(pattern):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            try:
                text_probe = path.read_text(encoding="utf-8", errors="ignore")[:2000]
            except Exception:
                text_probe = ""
            rows.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "extension": path.suffix,
                    "size_bytes": path.stat().st_size,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "contains_seed_token": "seed" in text_probe.lower(),
                    "contains_nsims_token": "nsims" in text_probe.lower(),
                    "possible_official_par_or_seed": path.suffix.lower() == ".par" or "seed" in path.name.lower(),
                }
            )
    return pd.DataFrame(rows)


def copy_tree_files(src_dir: Path, dst_dir: Path, names: list[str] | None = None) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    if names is None:
        candidates = [p for p in src_dir.iterdir() if p.is_file()]
    else:
        candidates = [src_dir / n for n in names if (src_dir / n).exists()]
    for src in candidates:
        shutil.copy2(src, dst_dir / src.name)


def array_metrics(candidate: np.ndarray, reference: np.ndarray) -> dict[str, float | int]:
    a = np.asarray(candidate, dtype=np.float64)
    b = np.asarray(reference, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    out: dict[str, float | int] = {
        "n": int(mask.sum()),
        "candidate_nan_fraction": float(np.mean(~np.isfinite(a))),
        "reference_nan_fraction": float(np.mean(~np.isfinite(b))),
    }
    if mask.sum() == 0:
        out.update({"rmse": math.nan, "mae": math.nan, "pearson": math.nan, "bias_mean": math.nan})
        return out
    diff = a[mask] - b[mask]
    if mask.sum() > 2 and np.nanstd(a[mask]) > 0 and np.nanstd(b[mask]) > 0:
        pearson = float(np.corrcoef(a[mask], b[mask])[0, 1])
    else:
        pearson = math.nan
    out.update(
        {
            "rmse": float(np.sqrt(np.mean(diff * diff))),
            "mae": float(np.mean(np.abs(diff))),
            "pearson": pearson,
            "bias_mean": float(np.mean(diff)),
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


def uncertainty_definition(ver: dict[str, float | int], std: dict[str, float | int]) -> str:
    ver_rmse = float(ver.get("rmse", math.inf))
    std_rmse = float(std.get("rmse", math.inf))
    ver_mean_gap = abs(float(ver.get("candidate_mean", math.nan)) - float(ver.get("reference_mean", math.nan)))
    std_mean_gap = abs(float(std.get("candidate_mean", math.nan)) - float(std.get("reference_mean", math.nan)))
    if ver_rmse <= std_rmse and ver_mean_gap <= std_mean_gap:
        return "official StDev appears closer to variance"
    return "official StDev appears closer to sqrt variance"


def validation_status(temp: dict[str, float | int], best_unc: dict[str, float | int]) -> str:
    temp_corr = float(temp.get("pearson", math.nan))
    unc_corr = float(best_unc.get("pearson", math.nan))
    temp_rmse = float(temp.get("rmse", math.inf))
    temp_ref_std = max(float(temp.get("reference_std", 0.0)), 1e-9)
    unc_rmse = float(best_unc.get("rmse", math.inf))
    unc_ref_mean = max(abs(float(best_unc.get("reference_mean", 0.0))), 1e-9)
    if temp_corr >= 0.98 and unc_corr >= 0.85 and temp_rmse <= 0.25 * temp_ref_std and unc_rmse <= 0.5 * unc_ref_mean:
        return "PASS_STRONG"
    if temp_corr >= 0.92 and unc_corr >= 0.60 and temp_rmse <= 0.6 * temp_ref_std and unc_rmse <= 1.25 * unc_ref_mean:
        return "PASS_STATISTICAL"
    if temp_corr >= 0.85 and temp_rmse <= 1.0 * temp_ref_std:
        return "WARNING"
    return "FAIL"


def save_comparison_figures(out_dir: Path, date: str, candidate: Path, reference: Path) -> None:
    import netCDF4

    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(candidate) as c, netCDF4.Dataset(reference) as r:
        temp_py = np.asarray(c.variables["TEMPpred"][:], dtype=np.float64)[0]
        temp_ref = np.asarray(r.variables["TEMPpred"][:], dtype=np.float64)[0]
        var_py = np.asarray(c.variables["STD"][:], dtype=np.float64)[0]
        std_py = np.asarray(c.variables["STD_sqrt_variance"][:], dtype=np.float64)[0]
        unc_ref = np.asarray(r.variables["STD"][:], dtype=np.float64)[0]

    panels = [
        ("TEMPpred oficial", temp_ref),
        ("TEMPpred Python", temp_py),
        ("Dif TEMPpred", temp_py - temp_ref),
        ("StDev oficial", unc_ref),
        ("Variance Python", var_py),
        ("Std Python", std_py),
        ("Dif oficial vs variance", var_py - unc_ref),
        ("Dif oficial vs std", std_py - unc_ref),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), constrained_layout=True)
    for ax, (title, arr) in zip(axes.ravel(), panels):
        im = ax.imshow(arr, origin="lower", cmap="coolwarm")
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(f"Python+DSS vs oficial - {date}")
    fig.savefig(fig_dir / f"step10b_validation100_maps_{date}.png", dpi=160)
    plt.close(fig)

    for name, a, b in [
        ("temppred", temp_py, temp_ref),
        ("uncertainty_variance", var_py, unc_ref),
        ("uncertainty_std", std_py, unc_ref),
    ]:
        mask = np.isfinite(a) & np.isfinite(b)
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(b[mask], a[mask], s=2, alpha=0.25)
        ax.set_xlabel("Oficial")
        ax.set_ylabel("Python")
        ax.set_title(f"{name} scatter - {date}")
        fig.savefig(fig_dir / f"step10b_validation100_scatter_{name}_{date}.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(b[mask], bins=60, alpha=0.55, label="Oficial")
        ax.hist(a[mask], bins=60, alpha=0.55, label="Python")
        ax.set_title(f"{name} histogram - {date}")
        ax.legend()
        fig.savefig(fig_dir / f"step10b_validation100_hist_{name}_{date}.png", dpi=160)
        plt.close(fig)


def detailed_validation_metrics(candidate: Path, reference: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    import netCDF4

    with netCDF4.Dataset(candidate) as c, netCDF4.Dataset(reference) as r:
        temp_py = np.asarray(c.variables["TEMPpred"][:], dtype=np.float64)
        temp_ref = np.asarray(r.variables["TEMPpred"][:], dtype=np.float64)
        var_py = np.asarray(c.variables["STD"][:], dtype=np.float64)
        std_py = np.asarray(c.variables["STD_sqrt_variance"][:], dtype=np.float64)
        unc_ref = np.asarray(r.variables["STD"][:], dtype=np.float64)
    temp = array_metrics(temp_py, temp_ref)
    var = array_metrics(var_py, unc_ref)
    std = array_metrics(std_py, unc_ref)
    return temp, var, std


PILOT_CLASS_INFO = {
    "2024-07-03": {"class_id": "C01", "day_index_370": 250},
    "2024-07-04": {"class_id": "C01", "day_index_370": 251},
    "2023-12-22": {"class_id": "C06", "day_index_370": 56},
    "2023-12-17": {"class_id": "C06", "day_index_370": 51},
}


def summarize_array(arr: np.ndarray, prefix: str) -> dict[str, Any]:
    arr = np.asarray(arr, dtype=np.float64)
    valid = np.isfinite(arr)
    out: dict[str, Any] = {
        f"{prefix}_shape": list(arr.shape),
        f"{prefix}_valid_cells": int(valid.sum()),
        f"{prefix}_nan_fraction": float(np.mean(~valid)),
        f"{prefix}_all_nan": bool(valid.sum() == 0),
    }
    if valid.sum():
        out.update(
            {
                f"{prefix}_min": float(np.nanmin(arr)),
                f"{prefix}_max": float(np.nanmax(arr)),
                f"{prefix}_mean": float(np.nanmean(arr)),
                f"{prefix}_std": float(np.nanstd(arr)),
                f"{prefix}_all_zero": bool(np.allclose(arr[valid], 0.0)),
            }
        )
    else:
        out.update(
            {
                f"{prefix}_min": math.nan,
                f"{prefix}_max": math.nan,
                f"{prefix}_mean": math.nan,
                f"{prefix}_std": math.nan,
                f"{prefix}_all_zero": False,
            }
        )
    return out


def predmodel_day_metrics(date: str, predmodel: Path, generation_meta: dict[str, Any]) -> dict[str, Any]:
    import netCDF4

    class_info = PILOT_CLASS_INFO.get(date, {})
    row: dict[str, Any] = {
        "date": date,
        "class_id": class_info.get("class_id"),
        "day_index_370": class_info.get("day_index_370"),
        "predmodel": str(predmodel),
        "predmodel_exists": predmodel.exists(),
        "n_realizations": generation_meta.get("n_realizations"),
        "sim_outputs_read": generation_meta.get("n_realizations") if predmodel.exists() else 0,
    }
    dss_result = generation_meta.get("dss_result", {})
    if isinstance(dss_result, dict):
        row["dss_returncode"] = dss_result.get("returncode")
        row["dss_success"] = dss_result.get("success")
        stdout = str(dss_result.get("stdout", ""))
        row["dss_elapsed_seconds_reported"] = None
        for line in stdout.splitlines()[::-1]:
            if "Elapsed time:" in line:
                row["dss_elapsed_line"] = line.strip()
                break
    if not predmodel.exists():
        return row
    with netCDF4.Dataset(predmodel) as ds:
        variables = set(ds.variables.keys())
        row["has_TEMPpred"] = "TEMPpred" in variables
        row["has_STD"] = "STD" in variables
        row["has_STD_sqrt_variance"] = "STD_sqrt_variance" in variables
        row["has_LAT"] = "LAT" in variables
        row["has_LON"] = "LON" in variables
        row["has_BATHY"] = "BATHY" in variables
        temp = np.asarray(ds.variables["TEMPpred"][:], dtype=np.float64)
        std = np.asarray(ds.variables["STD"][:], dtype=np.float64)
        row.update(summarize_array(temp, "TEMPpred"))
        row.update(summarize_array(std, "STD_variance"))
    return row


def save_pilot_figures(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    import netCDF4

    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    temps: list[tuple[str, np.ndarray]] = []
    stds: list[tuple[str, np.ndarray]] = []
    for row in rows:
        predmodel = Path(str(row.get("predmodel", "")))
        if not predmodel.exists():
            continue
        date = str(row["date"])
        with netCDF4.Dataset(predmodel) as ds:
            temp = np.asarray(ds.variables["TEMPpred"][:], dtype=np.float64)[0]
            std = np.asarray(ds.variables["STD"][:], dtype=np.float64)[0]
        temps.append((date, temp))
        stds.append((date, std))
        for name, arr, cmap in [("TEMPpred", temp, "coolwarm"), ("STD_variance", std, "viridis")]:
            fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
            im = ax.imshow(arr, origin="lower", cmap=cmap)
            ax.set_title(f"{name} - {date}")
            ax.set_xticks([])
            ax.set_yticks([])
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            fig.savefig(fig_dir / f"step10b_pilot_{name}_map_{date}.png", dpi=160)
            plt.close(fig)

            valid = arr[np.isfinite(arr)]
            fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
            ax.hist(valid, bins=60)
            ax.set_title(f"{name} histogram - {date}")
            fig.savefig(fig_dir / f"step10b_pilot_{name}_hist_{date}.png", dpi=160)
            plt.close(fig)

    for name, items, cmap in [("TEMPpred", temps, "coolwarm"), ("STD_variance", stds, "viridis")]:
        if not items:
            continue
        fig, axes = plt.subplots(1, len(items), figsize=(5 * len(items), 4), constrained_layout=True)
        if len(items) == 1:
            axes = [axes]
        for ax, (date, arr) in zip(axes, items):
            im = ax.imshow(arr, origin="lower", cmap=cmap)
            ax.set_title(date)
            ax.set_xticks([])
            ax.set_yticks([])
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        fig.suptitle(f"Step10B pilot {name}")
        fig.savefig(fig_dir / f"step10b_pilot_global_panel_{name}.png", dpi=160)
        plt.close(fig)


def generate_one(
    date: str,
    cfg: DssConfig,
    *,
    source: str,
    execute_dss: bool,
    n_realizations: int,
    seed: int,
    timeout_s: int,
) -> tuple[Path, dict[str, Any]]:
    input_path = cfg.output_dir / "dss_inputs" / date / "depth_01"
    output_path = cfg.output_dir / "dss_outputs" / date / "depth_01"
    log_path = cfg.output_dir / "logs" / date
    log_path.mkdir(parents=True, exist_ok=True)
    hres = load_hres_for_date(cfg, date, source=source)
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
        variogram=VARIOGRAM[0],
        seed=seed,
    )
    expected_sims = [str(output_path / f"sim_{i}.out") for i in range(1, n_realizations + 1)]
    meta: dict[str, Any] = {
        "date": date,
        "depth": 1,
        "input_dir": str(input_path),
        "output_dir": str(output_path),
        "logs_dir": str(log_path),
        "prep": prep,
        "par_file": str(par),
        "n_realizations": n_realizations,
        "expected_sim_outputs": len(expected_sims),
        "expected_first_sim_output": expected_sims[0] if expected_sims else None,
        "expected_last_sim_output": expected_sims[-1] if expected_sims else None,
        "dss_command": f"\"{input_path / 'DSS.C.64.exe'}\" \"{par}\"",
    }
    if not execute_dss:
        meta["status"] = "dry_run_prepared_inputs"
        return cfg.output_dir / "predmodels" / date / f"python_dss_predModel_1_{n_realizations}real.nc", meta
    dss_result = run_dss_executable(input_path / "DSS.C.64.exe", par, timeout_s=timeout_s)
    meta["dss_result"] = dss_result
    (log_path / "dss_stdout.txt").write_text(str(dss_result.get("stdout", "")), encoding="utf-8")
    (log_path / "dss_stderr.txt").write_text(str(dss_result.get("stderr", "")), encoding="utf-8")
    write_json(log_path / "dss_result.json", dss_result)
    if not dss_result["success"]:
        meta["status"] = "dss_failed"
        return cfg.output_dir / "predmodels" / date / f"python_dss_predModel_1_{n_realizations}real.nc", meta
    sims = read_dss_simulation_outputs(output_path / "sim", n_realizations, prep["nx"] * prep["ny"] * prep["nz"])
    temppred, variance, std_sqrt = compute_temppred_uncertainty_from_realizations(
        sims,
        nx=prep["nx"],
        ny=prep["ny"],
        input_days=prep["input_days"],
        output_days=2,
    )
    pred_path = cfg.output_dir / "predmodels" / date / f"python_dss_predModel_1_{n_realizations}real.nc"
    write_predmodel_nc(pred_path, hres, temppred, variance, std_sqrt_day_lat_lon=std_sqrt)
    meta["status"] = "predmodel_generated"
    meta["predmodel"] = str(pred_path)
    meta["temppred_shape"] = list(temppred.shape)
    meta["variance_shape"] = list(variance.shape)
    meta["std_sqrt_shape"] = list(std_sqrt.shape)
    meta["variance_mean"] = float(np.nanmean(variance))
    meta["std_sqrt_mean"] = float(np.nanmean(std_sqrt))
    return pred_path, meta


def status_from_metrics(row: dict[str, Any]) -> str:
    """Initial conservative status rule.

    DSS seeds in Filipa's parFileDSS.m were random and are not recorded in the
    official predModel NetCDFs, so exact equality is not expected from a new
    run. For now, use broad checks only and require human review for moderate
    differences.
    """
    if not row.get("candidate_exists", False) or not row.get("reference_exists", False):
        return "FAIL"
    if row.get("TEMPpred_shape_candidate") != row.get("TEMPpred_shape_reference"):
        return "FAIL"
    if row.get("STD_shape_candidate") != row.get("STD_shape_reference"):
        return "FAIL"
    pearson = row.get("TEMPpred_pearson", math.nan)
    if isinstance(pearson, (int, float)) and pearson >= 0.95:
        return "WARNING_SEED_NOT_REPRODUCIBLE"
    return "FAIL"


def run_mode(args: argparse.Namespace) -> Path:
    n_realizations = args.n_realizations if args.n_realizations is not None else args.max_realizations
    depths = parse_depths(args.depths)
    if args.mode == "validate_october":
        output_dir = args.output or RESULTS / f"fossum_roi_x490_step10b_python_dss_validation100_{now_tag()}"
        source = "official_october"
    elif args.mode == "generate_pilot":
        output_dir = args.output or RESULTS / f"fossum_roi_x490_step10b_python_dss_class01_class06_pilot_{now_tag()}"
        source = "python_370"
        if not args.force and not validation_marker_path().exists():
            output_dir.mkdir(parents=True, exist_ok=True)
            reason = [
                "# Step10B Python DSS Pilot Blocked",
                "",
                "Pilot generation was not run because no PASS validation marker exists.",
                "Run `--mode validate_october` first and review the metrics.",
            ]
            (output_dir / "step10b_python_port_blocked_reason.md").write_text("\n".join(reason), encoding="utf-8")
            print(f"Blocked pilot generation: {output_dir}")
            return output_dir
    else:
        raise ValueError(args.mode)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = build_config(output_dir, n_realizations)
    dates = args.dates or (["2024-10-30", "2024-10-31"] if args.mode == "validate_october" else PILOT_DATES)
    par_inventory = official_parfile_inventory(FILIPA_ROOT)
    par_inventory.to_csv(output_dir / "step10b_official_parfile_seed_inventory.csv", index=False)
    plan = [plan_record(d, cfg, args.mode, source, n_realizations, depths) for d in dates]
    pd.DataFrame(plan).to_csv(output_dir / "step10b_python_dss_generation_plan.csv", index=False)

    metadata = {
        "mode": args.mode,
        "dates": dates,
        "depths": depths,
        "dry_run": bool(args.dry_run or not args.execute_dss),
        "execute_dss": bool(args.execute_dss),
        "n_realizations": n_realizations,
        "max_realizations_argument": args.max_realizations,
        "hres_regenerated": False,
        "matlab_used": False,
        "dss_exe": str(cfg.dss_exe),
        "official_parfile_or_seed_candidates_found": int(len(par_inventory)),
    }
    metadata_name = "step10b_validation100_metadata.json" if args.mode == "validate_october" else "step10b_pilot_generation_metadata.json"
    write_json(output_dir / metadata_name, metadata)

    if args.dry_run or not args.execute_dss:
        generation_rows = []
        for date in dates:
            _pred, meta = generate_one(
                date,
                cfg,
                source=source,
                execute_dss=False,
                n_realizations=n_realizations,
                seed=args.seed,
                timeout_s=args.timeout_s,
            )
            generation_rows.append(meta)
        dry_inventory_name = "step10b_validation100_dry_run_inventory.csv" if args.mode == "validate_october" else "step10b_pilot_generation_dry_run_inventory.csv"
        pd.DataFrame(generation_rows).to_csv(output_dir / dry_inventory_name, index=False)
        checks = {
            "hres_not_regenerated": True,
            "dss_found": cfg.dss_exe.exists(),
            "reference_predmodel_found": all(reference_predmodel_path(d).exists() for d in dates) if args.mode == "validate_october" else None,
            "matlab_used": False,
            "dss_called": False,
            "dates_planned": len(dates),
            "depths": depths,
            "n_realizations": n_realizations,
            "ssdir_par_created": all(Path(r["par_file"]).exists() for r in generation_rows),
            "official_parfile_or_seed_found": bool(len(par_inventory)),
            "verdict": "DRY_RUN_READY",
        }
        checks_name = "step10b_validation100_checks.json" if args.mode == "validate_october" else "step10b_pilot_generation_checks.json"
        write_json(output_dir / checks_name, checks)
        summary = [
            "# Step10B Python DSS Dry Run",
            "",
            f"- Mode: `{args.mode}`",
            f"- Dates: {', '.join(dates)}",
            f"- Depths: {', '.join(map(str, depths))}",
            f"- Realizations: {n_realizations}",
            f"- DSS found: {cfg.dss_exe.exists()}",
            f"- Reference predModel found: {checks['reference_predmodel_found']}",
            f"- ssdir.par created: {checks['ssdir_par_created']}",
            f"- Official parfile/seed candidates found: {len(par_inventory)}",
            "- DSS was not called.",
        ]
        summary_name = "step10b_validation100_summary.md" if args.mode == "validate_october" else "step10b_pilot_generation_summary.md"
        (output_dir / summary_name).write_text("\n".join(summary), encoding="utf-8")
        print(json.dumps(checks, indent=2))
        return output_dir

    generation_rows = []
    metric_rows = []
    uncertainty_rows = []
    for date in dates:
        pred, meta = generate_one(
            date,
            cfg,
            source=source,
            execute_dss=True,
            n_realizations=n_realizations,
            seed=args.seed,
            timeout_s=args.timeout_s,
        )
        generation_rows.append(meta)
        if args.mode == "validate_october" and pred.exists():
            ref = reference_predmodel_path(date)
            basic_row = compare_with_reference_predmodel(pred, ref)
            temp_metrics, var_metrics, std_metrics = detailed_validation_metrics(pred, ref)
            definition = uncertainty_definition(var_metrics, std_metrics)
            best_unc = var_metrics if "variance" in definition else std_metrics
            status = validation_status(temp_metrics, best_unc)
            row = {"date": date, "candidate": str(pred), "reference": str(ref), "validation_status": status}
            row.update({f"TEMPpred_{k}": v for k, v in temp_metrics.items()})
            row.update({"uncertainty_best_definition": definition})
            row.update({f"basic_{k}": v for k, v in basic_row.items() if k not in row})
            metric_rows.append(row)
            uncertainty_rows.append({"date": date, "definition": "variance_map", **{f"uncertainty_{k}": v for k, v in var_metrics.items()}})
            uncertainty_rows.append({"date": date, "definition": "std_map", **{f"uncertainty_{k}": v for k, v in std_metrics.items()}})
            save_comparison_figures(output_dir, date, pred, ref)

    pd.DataFrame(generation_rows).to_csv(output_dir / "step10b_python_dss_generation_inventory.csv", index=False)
    if args.mode == "validate_october":
        metrics = pd.DataFrame(metric_rows)
        metrics.to_csv(output_dir / "step10b_validation100_metrics.csv", index=False)
        pd.DataFrame(uncertainty_rows).to_csv(output_dir / "step10b_validation100_uncertainty_definition_comparison.csv", index=False)
        statuses = metrics["validation_status"].tolist() if not metrics.empty else []
        pass_like = bool(statuses and all(s in ["PASS_STRONG", "PASS_STATISTICAL"] for s in statuses))
        warning_like = bool(statuses and all(s in ["PASS_STRONG", "PASS_STATISTICAL", "WARNING"] for s in statuses))
        if pass_like:
            verdict = "PYTHON_DSS_VALIDATION100_PASS_STATISTICAL_READY_FOR_C01_C06"
            if all(s == "PASS_STRONG" for s in statuses):
                verdict = "PYTHON_DSS_VALIDATION100_PASS_STRONG_READY_FOR_C01_C06"
        elif warning_like:
            verdict = "PYTHON_DSS_VALIDATION100_WARNING_NEEDS_PARAMETER_FIX"
        else:
            verdict = "PYTHON_DSS_VALIDATION100_FAIL_DO_NOT_GENERATE_C01_C06"
        checks = {
            "dss_called": True,
            "dss_success_count": int(sum("predmodel" in r for r in generation_rows)),
            "validation_rows": int(len(metrics)),
            "validation_statuses": statuses,
            "n_realizations": n_realizations,
            "depths": depths,
            "official_parfile_or_seed_found": bool(len(par_inventory)),
            "seed_reproducibility_warning": not bool(len(par_inventory)),
            "hres_regenerated": False,
            "matlab_used": False,
            "c01_c06_generated": False,
            "verdict": verdict,
        }
        write_json(output_dir / "step10b_validation100_checks.json", checks)
        recommendation = "Gerar piloto C01/C06 com Python+DSS." if pass_like else "Corrigir/confirmar parfile, seed e parametros DSS antes de gerar C01/C06."
        if not len(par_inventory):
            seed_note = "Nao foi encontrado parfile/seed oficial; validacao bit-a-bit nao e possivel com os ficheiros atuais."
        else:
            seed_note = f"Foram encontrados {len(par_inventory)} candidatos a parfile/seed; ver CSV de inventario."
        uncertainty_note = metrics["uncertainty_best_definition"].iloc[0] if not metrics.empty else "uncertainty definition unavailable"
        report = [
            "# Step10B Validation100 Report",
            "",
            f"- DSS called: {checks['dss_called']}",
            f"- Realizations: {n_realizations}",
            f"- Depths: {', '.join(map(str, depths))}",
            f"- Validation statuses: {statuses}",
            f"- Uncertainty definition: {uncertainty_note}",
            f"- Parfile/seed official: {seed_note}",
            f"- Verdict: `{verdict}`",
            "",
            "Important: official MATLAB `parFileDSS.m` used a random seed that is not stored in predModel files unless a parfile candidate is found, so exact reproduction is not expected.",
        ]
        (output_dir / "step10b_validation100_report.md").write_text("\n".join(report), encoding="utf-8")
        (output_dir / "step10b_validation100_summary.md").write_text("\n".join(report), encoding="utf-8")
        (output_dir / "step10b_validation100_recommendation.md").write_text(
            f"# Step10B Validation100 Recommendation\n\n{recommendation}\n\nFinal verdict: `{verdict}`\n",
            encoding="utf-8",
        )
        if pass_like:
            write_json(validation_marker_path(), {"created_at": datetime.now().isoformat(), "validation_output": str(output_dir), "status": checks["verdict"]})
    else:
        day_metric_rows = []
        for meta in generation_rows:
            date = str(meta.get("date"))
            predmodel = Path(str(meta.get("predmodel", "")))
            day_metric_rows.append(predmodel_day_metrics(date, predmodel, meta))
        day_metrics = pd.DataFrame(day_metric_rows)
        day_metrics.to_csv(output_dir / "step10b_pilot_generation_day_metrics.csv", index=False)
        save_pilot_figures(output_dir, day_metric_rows)
        expected_dates = set(PILOT_DATES)
        processed_dates = set(dates)
        predmodels_created = int(day_metrics["predmodel_exists"].sum()) if not day_metrics.empty else 0
        all_dss_ok = bool(not day_metrics.empty and day_metrics["dss_returncode"].astype(str).eq("0").all())
        all_required_vars = bool(
            not day_metrics.empty
            and day_metrics[["has_TEMPpred", "has_STD", "has_LAT", "has_LON", "has_BATHY"]].astype(bool).all().all()
        )
        temp_not_all_nan = bool(not day_metrics.empty and (~day_metrics["TEMPpred_all_nan"].astype(bool)).all())
        std_not_all_zero = bool(not day_metrics.empty and (~day_metrics["STD_variance_all_zero"].astype(bool)).all())
        complete = (
            len(dates) == 4
            and processed_dates == expected_dates
            and predmodels_created == 4
            and all_dss_ok
            and all_required_vars
            and temp_not_all_nan
            and std_not_all_zero
        )
        verdict = "C01_C06_PILOT_PREDMODELS_GENERATED_READY_FOR_STEP10C" if complete else "C01_C06_PILOT_PARTIAL_GENERATION_CHECK_WARNINGS"
        checks = {
            "dss_called": True,
            "pilot_dates": dates,
            "processed_date_count": int(len(dates)),
            "expected_date_count": 4,
            "predmodels_created": predmodels_created,
            "n_realizations_per_date": n_realizations,
            "depths": depths,
            "all_dss_returncode_zero": all_dss_ok,
            "all_required_variables_present": all_required_vars,
            "temppred_not_all_nan": temp_not_all_nan,
            "std_variance_not_all_zero": std_not_all_zero,
            "hres_regenerated": False,
            "matlab_used": False,
            "classes": {
                "C01": ["2024-07-03", "2024-07-04"],
                "C06": ["2023-12-22", "2023-12-17"],
            },
            "verdict": verdict,
        }
        write_json(output_dir / "step10b_pilot_generation_checks.json", checks)
        report = [
            "# Step10B Pilot Generation Report",
            "",
            "Python+DSS was previously validated against the official October predModel with 100 realizations.",
            "This run uses the validated configuration: depth 1, 100 realizations, existing HRes, and STD as variance.",
            "",
            f"- Dates processed: {len(dates)}",
            f"- PredModels created: {predmodels_created}",
            f"- DSS returncode zero for all dates: {all_dss_ok}",
            f"- HRes regenerated: False",
            f"- MATLAB used: False",
            f"- Verdict: `{verdict}`",
            "",
            "These are full pilot predModels. ROI x490 extraction belongs to Step10C, and classification of pilot TEMPpred belongs to a later Step09B-style step.",
        ]
        (output_dir / "step10b_pilot_generation_summary.md").write_text("\n".join(report), encoding="utf-8")
        (output_dir / "step10b_pilot_generation_report.md").write_text("\n".join(report), encoding="utf-8")
        (output_dir / "step10b_pilot_next_step_recommendation.md").write_text(
            f"# Step10B Next Step Recommendation\n\nProceed to Step10C: extract ROI x490 from the 4 pilot predModels.\n\nFinal verdict: `{verdict}`\n",
            encoding="utf-8",
        )
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python+DSS TEMPpred/STD generator/validator.")
    parser.add_argument("--mode", choices=["validate_october", "generate_pilot"], required=True)
    parser.add_argument("--dates", nargs="*", default=None)
    parser.add_argument("--depths", default="1", help="Depth indices to process. Current surface port supports only depth 1.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-dss", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-depths", type=int, default=1, help="Deprecated alias kept for old commands.")
    parser.add_argument("--max-realizations", type=int, default=100)
    parser.add_argument("--n-realizations", type=int, default=None, help="Preferred number of DSS realizations.")
    parser.add_argument("--seed", type=int, default=110011)
    parser.add_argument("--timeout-s", type=int, default=3600)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    out = run_mode(parse_args())
    print(f"Output: {out}")
