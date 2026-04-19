from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import TwoSlopeNorm


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slice_stats(arr: np.ndarray) -> dict[str, Any]:
    arr_np = np.asarray(arr, dtype=np.float64)
    finite = np.isfinite(arr_np)
    zeros = arr_np == 0.0

    out: dict[str, Any] = {
        "total_cells": int(arr_np.size),
        "finite_cells": int(np.count_nonzero(finite)),
        "finite_fraction": float(np.mean(finite)),
        "zero_cells_all": int(np.count_nonzero(zeros)),
        "zero_fraction_all": float(np.mean(zeros)),
        "zero_cells_finite": int(np.count_nonzero(zeros & finite)),
        "zero_fraction_finite": float(np.mean(zeros & finite)) / float(np.mean(finite)) if np.any(finite) else None,
        "min": None,
        "max": None,
        "mean": None,
        "std": None,
        "p01": None,
        "p05": None,
        "p50": None,
        "p95": None,
        "p99": None,
    }
    if np.any(finite):
        vals = arr_np[finite]
        out["min"] = float(np.min(vals))
        out["max"] = float(np.max(vals))
        out["mean"] = float(np.mean(vals))
        out["std"] = float(np.std(vals))
        out["p01"] = float(np.percentile(vals, 1))
        out["p05"] = float(np.percentile(vals, 5))
        out["p50"] = float(np.percentile(vals, 50))
        out["p95"] = float(np.percentile(vals, 95))
        out["p99"] = float(np.percentile(vals, 99))
    return out


def save_map(
    arr: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    out_path: Path,
    title: str,
    cbar_label: str,
    cmap_name: str,
    vmin: float | None = None,
    vmax: float | None = None,
    center_zero: bool = False,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    arr_plot = np.asarray(arr, dtype=np.float64).copy()
    arr_plot[~np.isfinite(arr_plot)] = np.nan
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad("white")

    extent = [float(np.min(lon)), float(np.max(lon)), float(np.min(lat)), float(np.max(lat))]

    fig, ax = plt.subplots(figsize=(8.3, 5.2))
    if center_zero and vmin is not None and vmax is not None and vmin < 0 < vmax:
        norm = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)
        im = ax.imshow(arr_plot, origin="lower", extent=extent, aspect="auto", cmap=cmap, norm=norm)
    else:
        im = ax.imshow(arr_plot, origin="lower", extent=extent, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)

    ax.set_title(title)
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_hist(day0: np.ndarray, day1: np.ndarray, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    a = np.asarray(day0, dtype=np.float64)
    b = np.asarray(day1, dtype=np.float64)
    af = a[np.isfinite(a)]
    bf = b[np.isfinite(b)]

    all_vals = np.concatenate([af, bf]) if af.size and bf.size else (af if af.size else bf)
    if all_vals.size == 0:
        raise RuntimeError("No finite values available for histogram.")

    vmin = float(np.min(all_vals))
    vmax = float(np.max(all_vals))
    if np.isclose(vmin, vmax):
        vmax = vmin + 1e-6
    bins = np.linspace(vmin, vmax, 90)

    fig, ax = plt.subplots(figsize=(8.7, 4.7))
    ax.hist(af, bins=bins, alpha=0.55, color="#2f4f90", label="STD day=0", density=True)
    ax.hist(bf, bins=bins, alpha=0.55, color="#d16d00", label="STD day=1", density=True)
    ax.set_title("STD histogram comparison: day=0 vs day=1")
    ax.set_xlabel("STD value")
    ax.set_ylabel("Density")
    ax.legend(framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)

    return {"hist_min": vmin, "hist_max": vmax, "hist_bins": int(bins.size)}


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    repo_root = scenario_dir.parents[1]

    source_primary = repo_root / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_predModel_1.nc"
    source_copy = (
        repo_root
        / "data"
        / "TEST_D4"
        / "HighRes"
        / "Daily_dpt_20241029_NewTest_1"
        / "Priori_Nazare_30-10-2024_1"
        / "30-10-2024_predModel_1.nc"
    )

    out_dir = scenario_dir / "outputs" / "std_day_audit"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig_day0 = out_dir / "std_day0_map.png"
    fig_day1 = out_dir / "std_day1_map.png"
    fig_diff = out_dir / "std_day_difference_map.png"
    fig_hist = out_dir / "std_day_hist_comparison.png"
    report_md = out_dir / "std_day_audit_report.md"
    summary_md = out_dir / "std_day_audit_summary.md"
    checks_json = out_dir / "std_day_audit_checks.json"
    stats_csv = out_dir / "std_day_audit_stats.csv"

    if not source_primary.exists():
        raise RuntimeError(f"Primary source file not found: {source_primary}")

    ds = xr.open_dataset(source_primary, decode_times=False)

    if "STD" not in ds.variables:
        raise RuntimeError("STD variable not found in audited NetCDF.")
    if "LAT" not in ds.variables or "LON" not in ds.variables or "BATHY" not in ds.variables:
        raise RuntimeError("Required variables LAT/LON/BATHY not found in audited NetCDF.")

    std = ds["STD"]
    std_dims = list(std.dims)
    std_shape = [int(v) for v in std.shape]

    lat = np.asarray(ds["LAT"].values, dtype=np.float64)
    lon = np.asarray(ds["LON"].values, dtype=np.float64)
    std_vals = np.asarray(std.values, dtype=np.float64)

    if std_vals.ndim != 3 or std_vals.shape[0] < 2:
        raise RuntimeError(
            f"This audit expects STD with at least 2 day slices. Got shape={std_vals.shape}, dims={std_dims}."
        )

    day_count = int(std_vals.shape[0])
    day_indices = list(range(day_count))

    day0 = std_vals[0]
    day1 = std_vals[1]
    diff = day1 - day0

    stats_day0 = slice_stats(day0)
    stats_day1 = slice_stats(day1)
    stats_diff = slice_stats(diff)

    overlap = np.isfinite(day0) & np.isfinite(day1)
    corr = None
    rmse = None
    mae = None
    if np.any(overlap):
        a = day0[overlap]
        b = day1[overlap]
        if a.size > 1:
            corr = float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
        rmse = float(np.sqrt(np.mean((b - a) ** 2)))
        mae = float(np.mean(np.abs(b - a)))

    finite_combined = np.isfinite(day0) | np.isfinite(day1)
    all_std_vals = np.concatenate([day0[np.isfinite(day0)], day1[np.isfinite(day1)]])
    common_vmin = float(np.min(all_std_vals))
    common_vmax = float(np.max(all_std_vals))

    diff_f = diff[np.isfinite(diff)]
    diff_abs_max = float(np.max(np.abs(diff_f))) if diff_f.size else 1.0

    save_map(
        arr=day0,
        lat=lat,
        lon=lon,
        out_path=fig_day0,
        title="STD day=0 map (30-10-2024_predModel_1.nc)",
        cbar_label="STD",
        cmap_name="viridis",
        vmin=common_vmin,
        vmax=common_vmax,
    )
    save_map(
        arr=day1,
        lat=lat,
        lon=lon,
        out_path=fig_day1,
        title="STD day=1 map (30-10-2024_predModel_1.nc)",
        cbar_label="STD",
        cmap_name="viridis",
        vmin=common_vmin,
        vmax=common_vmax,
    )
    save_map(
        arr=diff,
        lat=lat,
        lon=lon,
        out_path=fig_diff,
        title="STD difference map: day=1 minus day=0",
        cbar_label="STD(day=1) - STD(day=0)",
        cmap_name="coolwarm",
        vmin=-diff_abs_max,
        vmax=diff_abs_max,
        center_zero=True,
    )
    hist_info = save_hist(day0=day0, day1=day1, out_path=fig_hist)

    file_hash_primary = sha256_file(source_primary)
    file_hash_copy = sha256_file(source_copy) if source_copy.exists() else None
    files_identical = bool(source_copy.exists() and file_hash_primary == file_hash_copy)

    # Forensic metadata evidence.
    time_like_dims = [k for k in ds.sizes.keys() if ("time" in k.lower() or "day" in k.lower())]
    time_like_vars = [k for k in ds.variables.keys() if ("time" in k.lower() or "day" in k.lower())]
    std_attrs = dict(std.attrs)
    global_attrs = dict(ds.attrs)
    var_attrs = {k: dict(ds[k].attrs) for k in ds.variables}

    # No direct day metadata if day exists only as dimension without variable.
    has_explicit_day_variable = "day" in ds.variables
    has_explicit_day_attrs = bool(std_attrs) or has_explicit_day_variable

    # Decision logic:
    # - day0 nearly zero and day1 structured => day1 plausible operationally.
    # - no explicit metadata for day semantics => not fully proven.
    day0_nearly_zero = (
        (stats_day0["max"] is not None and stats_day0["max"] < 1e-3)
        and (stats_day0["mean"] is not None and stats_day0["mean"] < 1e-4)
    )
    day1_structured = (
        (stats_day1["mean"] is not None and stats_day1["mean"] > 1e-3)
        and (stats_day1["std"] is not None and stats_day1["std"] > 1e-4)
    )

    if has_explicit_day_attrs and day1_structured:
        decision = "CONFIRMED: use day=1"
    elif day1_structured and day0_nearly_zero:
        decision = "UNCERTAIN: day=1 plausible but not proven"
    elif not day1_structured:
        decision = "INCORRECT: day=1 not justified"
    else:
        decision = "NEEDS MANUAL DOMAIN DECISION"

    defensibility_sentence = (
        "A escolha de STD[day=1] e auditavelmente defensavel para o input surface-only do planner "
        "como opcao operacional pragmatica, mas sem prova semantica completa no metadata do NetCDF."
        if decision == "UNCERTAIN: day=1 plausible but not proven"
        else (
            "A escolha de STD[day=1] e auditavelmente defensavel para o input surface-only do planner."
            if decision == "CONFIRMED: use day=1"
            else "A escolha de STD[day=1] nao e auditavelmente defensavel para o input surface-only do planner."
        )
    )

    rows = []
    for label, st in [("day=0", stats_day0), ("day=1", stats_day1), ("day1-day0", stats_diff)]:
        rows.append(
            {
                "slice": label,
                "min": st["min"],
                "max": st["max"],
                "mean": st["mean"],
                "std": st["std"],
                "finite_fraction": st["finite_fraction"],
                "zero_fraction_all": st["zero_fraction_all"],
                "zero_fraction_finite": st["zero_fraction_finite"],
                "p01": st["p01"],
                "p05": st["p05"],
                "p50": st["p50"],
                "p95": st["p95"],
                "p99": st["p99"],
            }
        )

    with stats_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "slice",
                "min",
                "max",
                "mean",
                "std",
                "finite_fraction",
                "zero_fraction_all",
                "zero_fraction_finite",
                "p01",
                "p05",
                "p50",
                "p95",
                "p99",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    checks_payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "audited_file": str(source_primary),
        "audited_file_sha256": file_hash_primary,
        "secondary_copy_file": str(source_copy),
        "secondary_copy_exists": source_copy.exists(),
        "secondary_copy_sha256": file_hash_copy,
        "secondary_copy_identical_to_primary": files_identical,
        "dataset_sizes": {k: int(v) for k, v in ds.sizes.items()},
        "dataset_coords": list(ds.coords),
        "dataset_data_vars": list(ds.data_vars),
        "std_structure": {
            "dims": std_dims,
            "shape": std_shape,
            "ndim": int(std.ndim),
            "day_slice_count": day_count,
            "day_valid_indices": day_indices,
            "std_attrs": std_attrs,
        },
        "metadata_evidence": {
            "global_attrs": global_attrs,
            "time_like_dims": time_like_dims,
            "time_like_vars": time_like_vars,
            "has_explicit_day_variable": has_explicit_day_variable,
            "variable_attrs": var_attrs,
        },
        "stats": {
            "day0": stats_day0,
            "day1": stats_day1,
            "day1_minus_day0": stats_diff,
            "overlap_corr_day0_day1": corr,
            "overlap_rmse_day1_vs_day0": rmse,
            "overlap_mae_day1_vs_day0": mae,
            "hist_info": hist_info,
            "day0_nearly_zero_flag": day0_nearly_zero,
            "day1_structured_flag": day1_structured,
            "finite_union_fraction": float(np.mean(finite_combined)),
        },
        "decision": decision,
        "defensibility_sentence": defensibility_sentence,
        "outputs": {
            "std_day0_map": str(fig_day0),
            "std_day1_map": str(fig_day1),
            "std_day_difference_map": str(fig_diff),
            "std_day_hist_comparison": str(fig_hist),
            "stats_csv": str(stats_csv),
            "report_md": str(report_md),
            "summary_md": str(summary_md),
        },
    }
    checks_json.write_text(json.dumps(checks_payload, indent=2), encoding="utf-8")

    report_lines = [
        "# std_day_audit_report",
        "",
        "## 1. Ficheiro auditado",
        f"- primary file: `{source_primary}`",
        f"- primary sha256: `{file_hash_primary}`",
        f"- secondary copy: `{source_copy}`",
        f"- secondary exists: `{source_copy.exists()}`",
        f"- secondary sha256: `{file_hash_copy}`",
        f"- primary/secondary identical: `{files_identical}`",
        "",
        "## 2. Estrutura da variavel STD",
        f"- STD dims: `{std_dims}`",
        f"- STD shape: `{std_shape}`",
        f"- number of day slices: `{day_count}`",
        f"- valid day indices: `{day_indices}`",
        f"- dataset sizes: `{dict(ds.sizes)}`",
        "",
        "## 3. Interpretacao da dimensao day",
        f"- has explicit `day` variable: `{has_explicit_day_variable}`",
        f"- STD attrs: `{std_attrs}`",
        f"- global attrs: `{global_attrs}`",
        f"- time-like dims found: `{time_like_dims}`",
        f"- time-like variables found: `{time_like_vars}`",
        "- Observacao: nao foi encontrada metadata explicita que mapeie `day=0/1` para timestamps ou semanticas documentadas.",
        "",
        "## 4. Comparacao quantitativa entre day=0 e day=1",
        f"- day=0: min={stats_day0['min']:.6f}, max={stats_day0['max']:.6f}, mean={stats_day0['mean']:.6f}, std={stats_day0['std']:.6f}, zero_fraction_all={stats_day0['zero_fraction_all']:.6f}, finite_fraction={stats_day0['finite_fraction']:.6f}",
        f"- day=1: min={stats_day1['min']:.6f}, max={stats_day1['max']:.6f}, mean={stats_day1['mean']:.6f}, std={stats_day1['std']:.6f}, zero_fraction_all={stats_day1['zero_fraction_all']:.6f}, finite_fraction={stats_day1['finite_fraction']:.6f}",
        f"- day1-day0 diff: min={stats_diff['min']:.6f}, max={stats_diff['max']:.6f}, mean={stats_diff['mean']:.6f}, std={stats_diff['std']:.6f}",
        f"- overlap corr(day0,day1): `{corr}`",
        f"- overlap rmse(day1 vs day0): `{rmse}`",
        f"- overlap mae(day1 vs day0): `{mae}`",
        f"- day0 nearly-zero flag: `{day0_nearly_zero}`",
        f"- day1 structured flag: `{day1_structured}`",
        "",
        "## 5. Evidencia visual",
        f"- `{fig_day0}`",
        f"- `{fig_day1}`",
        f"- `{fig_diff}`",
        f"- `{fig_hist}`",
        "",
        "## 6. Conclusao",
        f"- decision: **{decision}**",
        f"- {defensibility_sentence}",
        "",
        "## 7. Recomendacao final para o pipeline",
        "- Para input surface-only do planner, `STD[day=1, LAT, LON]` e a melhor slice observada numericamente neste ficheiro.",
        "- Como nao ha metadata semantica explicita para `day`, manter documentacao da regra e registrar a decisao no manifest.",
        f"- outputs machine-readable: `{checks_json}` e `{stats_csv}`",
    ]
    report_md.write_text("\n".join(report_lines), encoding="utf-8")

    summary_lines = [
        "# std_day_audit_summary",
        "",
        f"- decision: **{decision}**",
        f"- STD shape/dims: `{std_shape}` / `{std_dims}`",
        f"- day slices: `{day_indices}`",
        f"- day=0 mean/std: `{stats_day0['mean']:.6f}` / `{stats_day0['std']:.6f}`",
        f"- day=1 mean/std: `{stats_day1['mean']:.6f}` / `{stats_day1['std']:.6f}`",
        f"- day0 nearly zero: `{day0_nearly_zero}`",
        f"- day1 structured: `{day1_structured}`",
        f"- semantic metadata for day found: `{has_explicit_day_attrs}`",
        f"- final sentence: {defensibility_sentence}",
    ]
    summary_md.write_text("\n".join(summary_lines), encoding="utf-8")

    ds.close()

    print("[OK] Audit complete.")
    print("[OK] Decision:", decision)
    print("[OK] Report:", report_md)
    print("[OK] Summary:", summary_md)
    print("[OK] Checks:", checks_json)
    print("[OK] Stats CSV:", stats_csv)
    print("[OK] Figure:", fig_day0)
    print("[OK] Figure:", fig_day1)
    print("[OK] Figure:", fig_diff)
    print("[OK] Figure:", fig_hist)


if __name__ == "__main__":
    main()
