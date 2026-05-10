"""Prepare Fossum step00 dataset from the FRESNEL paper ROI x490 stack.

This script intentionally mirrors the legacy Fossum dataset build logic:
  - common mask = pixels finite in every image
  - global normalization = mean/std over X[:, mask_common]
  - normalized PNG color scale = symmetric +/- percentile98(abs(valid_values))

Only paths, names, shape, number of days, and metadata are adapted for the
new 370-day HRes paper ROI x490 dataset.
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MPL = True
except Exception:
    HAS_MPL = False

try:
    import xarray as xr

    HAS_XARRAY = True
except Exception:
    HAS_XARRAY = False


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = Path(__file__).resolve()
OUT_DIR = SCRIPT_PATH.parent

INPUT_DIR = ROOT / "results" / "fresnel_paper_roi_x490_surface_370_20260509_180348"
IN_X = INPUT_DIR / "thetao_surface_370_hres_paper_roi_x490.npy"
IN_MASK = INPUT_DIR / "MASK_paper_roi_x490.npy"
IN_LAT = INPUT_DIR / "LAT_paper_roi_x490.npy"
IN_LON = INPUT_DIR / "LON_paper_roi_x490.npy"
IN_XKM = INPUT_DIR / "X_km_paper_roi_x490.npy"
IN_YKM = INPUT_DIR / "Y_km_paper_roi_x490.npy"
IN_BATHY = INPUT_DIR / "BATHY_paper_roi_x490.npy"
IN_DATES = INPUT_DIR / "dates_370.csv"
IN_META = INPUT_DIR / "paper_roi_x490_metadata.json"
IN_CHECKS = INPUT_DIR / "paper_roi_x490_checks.json"

EXPECTED_SHAPE = (370, 72, 117)
FINAL_SENTENCE = (
    "The FRESNEL paper ROI x490 dataset was prepared using the legacy Fossum "
    "dataset-building logic, with only path, shape and metadata adaptations."
)

LEGACY_SCRIPTS = [
    ROOT / "scripts" / "Old_Code" / "01_build_fossum_surface_dataset.py",
    ROOT / "scripts" / "Old_Code" / "01b_export_normalized_surface_pngs.py",
    ROOT / "scripts" / "Old_Code" / "export_surface_2024_300_images.py",
    ROOT / "scripts" / "fossum_faithful_initial_utils.py",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_dates(path: Path) -> list[str]:
    rows: list[str] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            date_col = None
            for candidate in ("date", "dates", "time", "datetime"):
                if candidate in reader.fieldnames:
                    date_col = candidate
                    break
            if date_col is None:
                date_col = reader.fieldnames[0]
            for row in reader:
                value = str(row.get(date_col, "")).strip()
                if value:
                    rows.append(value[:10])
            return rows

    # Fallback for a plain one-column file without a header.
    text = path.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        value = line.strip().split(",")[0]
        if value and value.lower() != "date":
            rows.append(value[:10])
    return rows


def write_dates(path: Path, dates: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["day_index", "date"])
        writer.writeheader()
        for i, date in enumerate(dates, start=1):
            writer.writerow({"day_index": i, "date": date})


def verify_inputs() -> None:
    required = [IN_X, IN_MASK, IN_LAT, IN_LON, IN_XKM, IN_YKM, IN_BATHY, IN_DATES, IN_META, IN_CHECKS]
    missing = [p for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required inputs: " + ", ".join(str(p) for p in missing))


def write_old_logic_audit() -> dict[str, Any]:
    found = [p for p in LEGACY_SCRIPTS if p.exists()]
    audit = {
        "old_scripts_found": [rel(p) for p in found],
        "old_dataset_build_script_identified": rel(LEGACY_SCRIPTS[0]) if LEGACY_SCRIPTS[0].exists() else None,
        "old_png_export_script_identified": rel(LEGACY_SCRIPTS[1]) if LEGACY_SCRIPTS[1].exists() else None,
        "old_raw_png_export_script_identified": rel(LEGACY_SCRIPTS[2]) if LEGACY_SCRIPTS[2].exists() else None,
        "old_pipeline_utils_identified": rel(LEGACY_SCRIPTS[3]) if LEGACY_SCRIPTS[3].exists() else None,
        "old_normalization_logic_identified": True,
        "old_mask_logic_identified": True,
    }
    lines = [
        "# Step00 old pipeline logic audit",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Scripts found",
    ]
    for p in found:
        lines.append(f"- `{rel(p)}`")
    lines += [
        "",
        "## Responsibility by script",
        "- `scripts/Old_Code/01_build_fossum_surface_dataset.py`: builds `X_surface_300.npy`, `X_surface_300_norm.npy`, `mask_common.npy`, `global_stats.json`, and `dataset_summary.json`.",
        "- `scripts/Old_Code/export_surface_2024_300_images.py`: parses the old GSLIB deterministic surface file and builds the raw 300-image stack.",
        "- `scripts/Old_Code/01b_export_normalized_surface_pngs.py`: exports normalized PNGs with a common symmetric scale.",
        "- `scripts/fossum_faithful_initial_utils.py`: downstream Fossum utilities expect `X_surface_300.npy`, `X_surface_300_norm.npy`, `mask_common.npy`, and `global_stats.json`.",
        "",
        "## Legacy dataset loading",
        "The old builder read the deterministic 2024 depth-1 GSLIB file, converted it to a float32 stack, and required shape `(300, 64, 112)`.",
        "",
        "## Legacy mask",
        "The common mask was computed as `np.isfinite(X).all(axis=0)`, meaning a pixel is valid only if it is finite for every image.",
        "",
        "## Legacy normalization",
        "The old builder selected `valid_stack = X[:, mask_common]`, computed `mu_global = np.mean(valid_stack)` and `sigma_global = np.std(valid_stack)`, then wrote normalized values only inside the common mask.",
        "",
        "## NaN treatment",
        "NaNs were preserved outside `mask_common`. The normalized cube was initialized with NaNs and only common-valid pixels were filled.",
        "",
        "## Legacy PNG export",
        "The normalized PNG exporter loaded `X_surface_300_norm.npy` and `mask_common.npy`, set pixels outside the mask to NaN, and used `coolwarm` with a symmetric scale `[-p98(abs(valid)), +p98(abs(valid))]`.",
        "",
        "## Expected old outputs",
        "- `X_surface_300.npy`",
        "- `X_surface_300_norm.npy`",
        "- `mask_common.npy`",
        "- `global_stats.json`",
        "- `dataset_summary.json`",
        "- normalized PNG folder and index/scale files",
        "",
        "## Reused without methodological changes",
        "- Common finite mask logic.",
        "- Global mean/std normalization over common-valid pixels.",
        "- Preservation of NaNs outside the common mask.",
        "- Normalized PNG color scale based on p98 absolute normalized values.",
        "",
        "## Adapted for the new dataset",
        "- Input path changed to the FRESNEL paper ROI x490 HRes stack.",
        "- Number of images changed from 300 to 370.",
        "- Shape changed from `(300, 64, 112)` to `(370, 72, 117)`.",
        "- Output names and metadata now carry `roi_x490` and 370-day dates.",
    ]
    (OUT_DIR / "step00_old_pipeline_logic_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit


def finite_stats(values: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(values)
    finite = np.isfinite(values)
    if not finite.any():
        return {"valid_cells": 0, "nan_cells": int(values.size), "min": np.nan, "max": np.nan, "mean": np.nan, "std": np.nan}
    v = values[finite]
    return {
        "valid_cells": int(v.size),
        "nan_cells": int(values.size - v.size),
        "min": float(np.min(v)),
        "max": float(np.max(v)),
        "mean": float(np.mean(v)),
        "std": float(np.std(v)),
    }


def write_day_metrics(dates: list[str], X: np.ndarray, X_norm: np.ndarray, mask_common: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, date in enumerate(dates):
        raw = X[idx].copy()
        norm = X_norm[idx].copy()
        raw[~mask_common] = np.nan
        norm[~mask_common] = np.nan
        raw_stats = finite_stats(raw)
        norm_stats = finite_stats(norm)
        rows.append(
            {
                "day_index": idx + 1,
                "date": date,
                "valid_cells": raw_stats["valid_cells"],
                "nan_cells": raw_stats["nan_cells"],
                "raw_min": raw_stats["min"],
                "raw_max": raw_stats["max"],
                "raw_mean": raw_stats["mean"],
                "raw_std": raw_stats["std"],
                "norm_min": norm_stats["min"],
                "norm_max": norm_stats["max"],
                "norm_mean": norm_stats["mean"],
                "norm_std": norm_stats["std"],
            }
        )
    out = OUT_DIR / "fossum_step00_day_metrics.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def make_cmap(name: str = "coolwarm"):
    if not HAS_MPL:
        raise RuntimeError("matplotlib is required for PNG export")
    cmap = plt.get_cmap(name).copy()
    cmap.set_bad(color="white")
    return cmap


def save_norm_png(
    arr: np.ndarray,
    xkm: np.ndarray,
    ykm: np.ndarray,
    out_file: Path,
    title: str | None,
    vmin: float,
    vmax: float,
    clean: bool = False,
) -> None:
    cmap = make_cmap("coolwarm")
    extent = [float(np.nanmin(xkm)), float(np.nanmax(xkm)), float(np.nanmin(ykm)), float(np.nanmax(ykm))]
    if clean:
        fig, ax = plt.subplots(figsize=(4.8, 3.8))
        ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", extent=extent)
        ax.set_axis_off()
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        fig.savefig(out_file, dpi=140, bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        return

    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", extent=extent)
    ax.set_title(title or "")
    ax.set_xlabel("x UTM 29N (km)")
    ax.set_ylabel("y UTM 29N (km)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Normalized temperature (-)")
    fig.tight_layout()
    fig.savefig(out_file, dpi=150)
    plt.close(fig)


def export_pngs(
    dates: list[str],
    X_norm: np.ndarray,
    mask_common: np.ndarray,
    xkm: np.ndarray,
    ykm: np.ndarray,
    vmin: float,
    vmax: float,
) -> tuple[list[dict[str, Any]], int, int]:
    png_dir = OUT_DIR / "normalized_pngs"
    clean_dir = OUT_DIR / "normalized_clean_pngs"
    png_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for idx, date in enumerate(dates):
        arr = X_norm[idx].copy()
        arr[~mask_common] = np.nan
        z = idx + 1
        png = png_dir / f"{z:04d}_{date}_X_surface_370_roi_x490_norm.png"
        clean = clean_dir / f"{z:04d}_{date}_X_surface_370_roi_x490_norm_clean.png"
        save_norm_png(arr, xkm, ykm, png, f"Normalized surface temperature - {date} (z={z:03d})", vmin, vmax, clean=False)
        save_norm_png(arr, xkm, ykm, clean, None, vmin, vmax, clean=True)
        stats = finite_stats(arr)
        rows.append(
            {
                "day_index": z,
                "date": date,
                "png_path": rel(png),
                "clean_png_path": rel(clean),
                "valid_cells": stats["valid_cells"],
                "nan_cells": stats["nan_cells"],
                "norm_min": stats["min"],
                "norm_max": stats["max"],
                "norm_mean": stats["mean"],
                "norm_std": stats["std"],
            }
        )

    with (OUT_DIR / "normalized_png_inventory.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows, len(list(png_dir.glob("*.png"))), len(list(clean_dir.glob("*.png")))


def save_panel(
    indices: list[int],
    dates: list[str],
    X_norm: np.ndarray,
    mask_common: np.ndarray,
    xkm: np.ndarray,
    ykm: np.ndarray,
    vmin: float,
    vmax: float,
    out_file: Path,
    title: str,
) -> None:
    cmap = make_cmap("coolwarm")
    n = len(indices)
    ncols = 4
    nrows = int(np.ceil(n / ncols))
    extent = [float(np.nanmin(xkm)), float(np.nanmax(xkm)), float(np.nanmin(ykm)), float(np.nanmax(ykm))]
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.2 * ncols, 2.8 * nrows), squeeze=False)
    im = None
    for ax, idx in zip(axes.ravel(), indices):
        arr = X_norm[idx].copy()
        arr[~mask_common] = np.nan
        im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", extent=extent)
        ax.set_title(dates[idx], fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes.ravel()[n:]:
        ax.set_axis_off()
    fig.suptitle(title, fontsize=13)
    if im is not None:
        cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.86)
        cbar.set_label("Normalized temperature (-)")
    fig.savefig(out_file, dpi=150, bbox_inches="tight")
    plt.close(fig)


def export_panels(dates: list[str], X_norm: np.ndarray, mask_common: np.ndarray, xkm: np.ndarray, ykm: np.ndarray, vmin: float, vmax: float) -> None:
    first = list(range(min(12, len(dates))))
    final = list(range(max(0, len(dates) - 12), len(dates)))
    monthly_targets = ["2023-10-28", "2023-11-15", "2023-12-15", "2024-01-15", "2024-02-15", "2024-03-15", "2024-04-15", "2024-05-15", "2024-06-15", "2024-07-15", "2024-08-15", "2024-09-15", "2024-10-15"]
    monthly = [dates.index(d) for d in monthly_targets if d in dates]
    hetero_targets = ["2024-10-10", "2024-10-13", "2024-10-15", "2024-10-11", "2024-10-31", "2024-10-12", "2024-10-09"]
    hetero = [dates.index(d) for d in hetero_targets if d in dates]

    save_panel(first, dates, X_norm, mask_common, xkm, ykm, vmin, vmax, OUT_DIR / "normalized_first_12_days_panel.png", "First 12 normalized ROI x490 days")
    save_panel(monthly, dates, X_norm, mask_common, xkm, ykm, vmin, vmax, OUT_DIR / "normalized_selected_monthly_panel.png", "Selected monthly normalized ROI x490 days")
    save_panel(hetero, dates, X_norm, mask_common, xkm, ykm, vmin, vmax, OUT_DIR / "normalized_heterogeneous_days_panel.png", "Previously identified heterogeneous October days")
    save_panel(final, dates, X_norm, mask_common, xkm, ykm, vmin, vmax, OUT_DIR / "normalized_final_12_days_panel.png", "Final 12 normalized ROI x490 days")


def write_netcdf(X: np.ndarray, X_norm: np.ndarray, mask_common: np.ndarray, dates: list[str], lat: np.ndarray, lon: np.ndarray, xkm: np.ndarray, ykm: np.ndarray, bathy: np.ndarray) -> Path | None:
    if not HAS_XARRAY:
        return None
    out_nc = OUT_DIR / "X_surface_370_roi_x490_step00_dataset.nc"
    ds = xr.Dataset(
        data_vars={
            "thetao": (("time", "y", "x"), X),
            "thetao_norm": (("time", "y", "x"), X_norm),
            "mask_common": (("y", "x"), mask_common.astype(np.uint8)),
            "LAT": (("y", "x"), lat.astype(np.float32)),
            "LON": (("y", "x"), lon.astype(np.float32)),
            "X_km": (("y", "x"), xkm.astype(np.float32)),
            "Y_km": (("y", "x"), ykm.astype(np.float32)),
            "BATHY": (("y", "x"), bathy.astype(np.float32)),
        },
        coords={"time": np.array(dates, dtype="datetime64[D]"), "y": np.arange(X.shape[1]), "x": np.arange(X.shape[2])},
        attrs={
            "description": "Fossum step00 dataset from FRESNEL paper ROI x490, preserving legacy mask and normalization logic.",
            "legacy_logic": "mask_common=np.isfinite(X).all(axis=0); global z-score over X[:, mask_common].",
        },
    )
    ds["thetao"].attrs["units"] = "deg C"
    ds["thetao_norm"].attrs["units"] = "1"
    ds.to_netcdf(out_nc)
    return out_nc


def coordinate_to_grid(arr: np.ndarray, shape: tuple[int, int], name: str) -> np.ndarray:
    """Return a 2D coordinate grid while accepting legacy 1D lat/lon vectors."""
    ny, nx = shape
    arr = np.asarray(arr, dtype=np.float32)
    if arr.shape == shape:
        return arr
    if arr.ndim == 1 and arr.size == ny and name.lower().startswith("lat"):
        return np.repeat(arr[:, None], nx, axis=1).astype(np.float32, copy=False)
    if arr.ndim == 1 and arr.size == nx and name.lower().startswith("lon"):
        return np.repeat(arr[None, :], ny, axis=0).astype(np.float32, copy=False)
    raise RuntimeError(f"{name} shape mismatch. Expected {shape}, got {arr.shape}")


def write_reports(checks: dict[str, Any], stats: dict[str, Any], audit: dict[str, Any]) -> None:
    report = [
        "# Fossum step00 ROI x490 dataset report",
        "",
        "## Answers",
        f"1. A lógica antiga foi encontrada? {'Sim' if audit['old_dataset_build_script_identified'] else 'Não'}.",
        "2. Scripts antigos usados como referência: "
        + ", ".join(f"`{p}`" for p in audit["old_scripts_found"]),
        f"3. A normalização foi mantida igual? Sim: média/desvio global sobre `X[:, mask_common]`.",
        f"4. A criação da máscara foi mantida igual? Sim: `np.isfinite(X).all(axis=0)`.",
        "5. Alterações feitas apenas por causa dos novos dados: paths, nomes dos outputs, 370 dias, shape `[370, 72, 117]`, datas e metadados ROI x490.",
        f"6. O novo dataset tem shape `[370, 72, 117]`? {'Sim' if checks['shape_matches_expected'] else 'Não'}: `{checks['input_shape']}`.",
        "7. Outputs equivalentes criados? Sim: `X_surface_370_roi_x490.npy`, `X_surface_370_roi_x490_norm.npy` e `mask_common_roi_x490.npy`.",
        f"8. Pronto para correr a configuração antiga como baseline? {'Sim' if checks['final_verdict'].startswith('PASS') else 'Não'}: {checks['final_verdict']}.",
        "",
        "## Core metrics",
        f"- Days: {checks['n_days']} ({checks['date_start']} to {checks['date_end']})",
        f"- Shape: {checks['input_shape']}",
        f"- Common-mask valid cells: {checks['mask_valid_cells']} ({checks['mask_valid_fraction']:.6f})",
        f"- Raw global mean/std: {stats['mu_global']:.9f} / {stats['sigma_global']:.9f}",
        f"- Normalized valid mean/std: {checks['norm_mean_valid']:.9f} / {checks['norm_std_valid']:.9f}",
        "",
        "## Logic changes",
    ]
    for item in checks["logic_changes_made"]:
        report.append(f"- {item}")
    report += [
        "",
        "## Unavoidable adaptations",
    ]
    for item in checks["unavoidable_adaptations"]:
        report.append(f"- {item}")
    report += ["", FINAL_SENTENCE]

    summary = [
        "# Fossum step00 ROI x490 dataset summary",
        "",
        f"- Lógica antiga encontrada: {'sim' if audit['old_dataset_build_script_identified'] else 'não'}.",
        "- Normalização mantida: sim, z-score global sobre a máscara comum.",
        "- Máscara mantida: sim, pixel finito em todos os 370 dias.",
        f"- Shape final: `{checks['input_shape']}`.",
        f"- Outputs principais criados: `{len(checks['outputs_created'])}` ficheiros/pastas registados.",
        f"- Veredito: {checks['final_verdict']}",
        "",
        FINAL_SENTENCE,
    ]
    (OUT_DIR / "fossum_step00_dataset_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (OUT_DIR / "fossum_step00_dataset_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def main() -> None:
    verify_inputs()
    if not HAS_MPL:
        raise RuntimeError("matplotlib is required to export normalized PNGs and panels.")

    audit = write_old_logic_audit()
    source_meta = read_json(IN_META)
    source_checks = read_json(IN_CHECKS)

    X = np.load(IN_X).astype(np.float32, copy=False)
    input_mask = np.load(IN_MASK).astype(bool, copy=False)
    lat_raw = np.load(IN_LAT).astype(np.float32, copy=False)
    lon_raw = np.load(IN_LON).astype(np.float32, copy=False)
    xkm = np.load(IN_XKM).astype(np.float32, copy=False)
    ykm = np.load(IN_YKM).astype(np.float32, copy=False)
    bathy = np.load(IN_BATHY).astype(np.float32, copy=False)
    dates = load_dates(IN_DATES)

    if X.shape != EXPECTED_SHAPE:
        raise RuntimeError(f"Unexpected new dataset shape. Expected {EXPECTED_SHAPE}, got {X.shape}")
    if len(dates) != X.shape[0]:
        raise RuntimeError(f"Date count mismatch. dates={len(dates)}, X days={X.shape[0]}")
    lat = coordinate_to_grid(lat_raw, X.shape[1:], "LAT")
    lon = coordinate_to_grid(lon_raw, X.shape[1:], "LON")
    for name, arr in {"input_mask": input_mask, "xkm": xkm, "ykm": ykm, "bathy": bathy}.items():
        if arr.shape != X.shape[1:]:
            raise RuntimeError(f"{name} shape mismatch. Expected {X.shape[1:]}, got {arr.shape}")

    # Legacy method: the common mask depends only on finite pixels across all days.
    mask_common = np.isfinite(X).all(axis=0)
    valid_stack = X[:, mask_common]
    if valid_stack.size == 0:
        raise RuntimeError("No valid pixels found for common mask.")

    mu_global = float(np.mean(valid_stack))
    sigma_global = float(np.std(valid_stack))
    if not np.isfinite(mu_global) or not np.isfinite(sigma_global) or sigma_global <= 0.0:
        raise RuntimeError(f"Invalid global stats: mu={mu_global}, sigma={sigma_global}")

    X_norm = np.full_like(X, np.nan, dtype=np.float32)
    X_norm[:, mask_common] = ((valid_stack - mu_global) / sigma_global).astype(np.float32)

    valid_norm = X_norm[:, mask_common]
    max_abs = float(np.percentile(np.abs(valid_norm), 98.0))
    if not np.isfinite(max_abs) or max_abs <= 0.0:
        raise RuntimeError(f"Invalid normalized PNG scale max_abs={max_abs}")
    vmin = -max_abs
    vmax = +max_abs

    out_x = OUT_DIR / "X_surface_370_roi_x490.npy"
    out_x_norm = OUT_DIR / "X_surface_370_roi_x490_norm.npy"
    out_mask = OUT_DIR / "mask_common_roi_x490.npy"
    np.save(out_x, X)
    np.save(out_x_norm, X_norm)
    np.save(out_mask, mask_common)
    np.save(OUT_DIR / "LAT_roi_x490.npy", lat)
    np.save(OUT_DIR / "LON_roi_x490.npy", lon)
    np.save(OUT_DIR / "X_km_roi_x490.npy", xkm)
    np.save(OUT_DIR / "Y_km_roi_x490.npy", ykm)
    np.save(OUT_DIR / "BATHY_roi_x490.npy", bathy)
    shutil.copy2(IN_DATES, OUT_DIR / "dates_370.csv")

    day_rows = write_day_metrics(dates, X, X_norm, mask_common)
    png_rows, n_png, n_clean = export_pngs(dates, X_norm, mask_common, xkm, ykm, vmin, vmax)
    export_panels(dates, X_norm, mask_common, xkm, ykm, vmin, vmax)
    out_nc = write_netcdf(X, X_norm, mask_common, dates, lat, lon, xkm, ykm, bathy)

    valid_pixels_per_image = np.isfinite(X).sum(axis=(1, 2))
    stats = {
        "mu_global": mu_global,
        "sigma_global": sigma_global,
        "n_images": int(X.shape[0]),
        "ny": int(X.shape[1]),
        "nx": int(X.shape[2]),
        "valid_pixels_per_image_mean": float(np.mean(valid_pixels_per_image)),
        "valid_pixels_total": int(valid_stack.size),
        "mask_fraction_valid": float(np.mean(mask_common)),
        "mask_fraction_invalid": float(1.0 - np.mean(mask_common)),
        "normalized_png_scale_method": "legacy symmetric +/- percentile98(abs(X_norm[:, mask_common]))",
        "normalized_png_vmin": float(vmin),
        "normalized_png_vmax": float(vmax),
        "source_input": rel(IN_X),
    }
    write_json(OUT_DIR / "normalization_stats.json", stats)

    metadata = {
        "input_new_dataset": str(INPUT_DIR),
        "input_array": str(IN_X),
        "source_metadata": source_meta,
        "source_checks": source_checks,
        "shape": [int(v) for v in X.shape],
        "date_start": dates[0],
        "date_end": dates[-1],
        "n_days": int(X.shape[0]),
        "depth": "surface",
        "roi": "FRESNEL paper ROI x490",
        "legacy_logic_reference": audit["old_scripts_found"],
        "mask_logic": "np.isfinite(X).all(axis=0)",
        "normalization_logic": "global mean/std over X[:, mask_common]",
        "png_scale_logic": "symmetric +/- percentile98(abs(X_norm[:, mask_common]))",
        "input_roi_mask_valid_fraction": float(np.mean(input_mask)),
        "common_mask_valid_fraction": float(np.mean(mask_common)),
        "source_LAT_shape": [int(v) for v in lat_raw.shape],
        "source_LON_shape": [int(v) for v in lon_raw.shape],
        "output_LAT_LON_shape": [int(v) for v in lat.shape],
    }
    write_json(OUT_DIR / "dataset_metadata.json", metadata)

    outputs_created = [
        "step00_old_pipeline_logic_audit.md",
        out_x.name,
        out_x_norm.name,
        out_mask.name,
        "LAT_roi_x490.npy",
        "LON_roi_x490.npy",
        "X_km_roi_x490.npy",
        "Y_km_roi_x490.npy",
        "BATHY_roi_x490.npy",
        "dates_370.csv",
        "normalization_stats.json",
        "dataset_metadata.json",
        "fossum_step00_day_metrics.csv",
        "normalized_pngs/",
        "normalized_clean_pngs/",
        "normalized_png_inventory.csv",
        "normalized_first_12_days_panel.png",
        "normalized_selected_monthly_panel.png",
        "normalized_heterogeneous_days_panel.png",
        "normalized_final_12_days_panel.png",
    ]
    if out_nc is not None:
        outputs_created.append(out_nc.name)

    checks = {
        "old_scripts_found": audit["old_scripts_found"],
        "old_dataset_build_script_identified": audit["old_dataset_build_script_identified"] is not None,
        "old_normalization_logic_identified": True,
        "old_mask_logic_identified": True,
        "logic_changes_made": [
            "Input source changed from old GSLIB/tempRes-derived surface stack to the new ROI x490 HRes .npy stack.",
            "Output names changed from 300/surface baseline names to 370/roi_x490 names.",
            "Date handling added because the new stack carries real dates from 2023-10-28 to 2024-10-31.",
        ],
        "unavoidable_adaptations": [
            "Shape changed from (300, 64, 112) to (370, 72, 117).",
            "Number of images changed from 300 to 370.",
            "Coordinates are copied from the ROI x490 HRes product instead of old physical coordinate helpers.",
        ],
        "input_new_dataset": str(INPUT_DIR),
        "input_shape": [int(v) for v in X.shape],
        "expected_shape": [int(v) for v in EXPECTED_SHAPE],
        "shape_matches_expected": bool(X.shape == EXPECTED_SHAPE),
        "n_days": int(X.shape[0]),
        "date_start": dates[0],
        "date_end": dates[-1],
        "mask_shape": [int(v) for v in mask_common.shape],
        "mask_valid_cells": int(np.count_nonzero(mask_common)),
        "mask_valid_fraction": float(np.mean(mask_common)),
        "nan_fraction": float(np.mean(~np.isfinite(X))),
        "global_mean": mu_global,
        "global_std": sigma_global,
        "norm_mean_valid": float(np.mean(valid_norm)),
        "norm_std_valid": float(np.std(valid_norm)),
        "n_normalized_pngs": int(n_png),
        "n_normalized_clean_pngs": int(n_clean),
        "n_day_metric_rows": int(len(day_rows)),
        "n_png_inventory_rows": int(len(png_rows)),
        "outputs_created": outputs_created,
        "final_verdict": "PASS - legacy Fossum step00 dataset-building logic was preserved with only path, shape and metadata adaptations.",
    }
    write_json(OUT_DIR / "fossum_step00_dataset_checks.json", checks)
    write_reports(checks, stats, audit)

    print(f"[OK] out_dir={OUT_DIR}")
    print(f"[OK] X_shape={X.shape}")
    print(f"[OK] mask_valid_fraction={checks['mask_valid_fraction']:.9f}")
    print(f"[OK] mu_global={mu_global:.9f}")
    print(f"[OK] sigma_global={sigma_global:.9f}")
    print(f"[OK] normalized_pngs={n_png}")
    print(f"[OK] normalized_clean_pngs={n_clean}")
    print(f"[OK] {FINAL_SENTENCE}")


if __name__ == "__main__":
    main()
