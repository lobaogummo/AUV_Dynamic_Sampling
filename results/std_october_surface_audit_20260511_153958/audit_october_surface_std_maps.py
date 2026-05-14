from __future__ import annotations

import json
import math
import warnings
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd


INPUT_ROOT = Path(
    r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel\02.Simulations\HighRes"
)
OUTPUT_DIR = Path(
    r"C:\Users\pedro\Documents\Filipa_dados\results\std_october_surface_audit_20260511_153958"
)
DAILY_DIR = OUTPUT_DIR / "std_surface_fullgrid_daily"
CLEAN_DAILY_DIR = OUTPUT_DIR / "std_surface_fullgrid_daily_clean"

EXPECTED_SHAPE = (180, 240)
EXPECTED_DAYS = [date(2024, 10, 1) + timedelta(days=i) for i in range(31)]
DEPTH_INDEX_USED = 1
PREDMODEL_SUFFIX = "predModel_1.nc"
NEAR_ZERO_ABS_STD = 1e-12
NEAR_ZERO_REL_STD = 1e-9


@dataclass
class DayData:
    day: date
    path: Path | None
    std: np.ndarray | None
    temppred: np.ndarray | None
    lat: np.ndarray | None
    lon: np.ndarray | None
    bathy: np.ndarray | None
    dept: np.ndarray | None
    dims: dict[str, int]
    variables: list[str]
    time_values: list[float]
    day_values: list[float]
    inventory: dict[str, Any]


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)):
            return None
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def masked_to_nan(array: Any) -> np.ndarray:
    arr = np.asanyarray(array)
    if np.ma.isMaskedArray(arr):
        return np.ma.filled(arr.astype(float), np.nan)
    return arr.astype(float, copy=False)


def var_shape(ds: netCDF4.Dataset, name: str) -> tuple[int, ...] | None:
    return tuple(ds.variables[name].shape) if name in ds.variables else None


def var_dims(ds: netCDF4.Dataset, name: str) -> tuple[str, ...] | None:
    return tuple(ds.variables[name].dimensions) if name in ds.variables else None


def read_var(ds: netCDF4.Dataset, name: str) -> np.ndarray | None:
    if name not in ds.variables:
        return None
    return masked_to_nan(ds.variables[name][:])


def find_expected_file(day: date) -> Path | None:
    expected_name = f"{day:%d-%m-%Y}_{PREDMODEL_SUFFIX}"
    matches = sorted(INPUT_ROOT.rglob(expected_name))
    if not matches:
        return None
    return matches[0]


def read_day(day: date) -> DayData:
    path = find_expected_file(day)
    base_inventory: dict[str, Any] = {
        "date": day.isoformat(),
        "expected_filename": f"{day:%d-%m-%Y}_{PREDMODEL_SUFFIX}",
        "file_found": path is not None,
        "path": str(path) if path else "",
    }
    if path is None:
        base_inventory.update(
            {
                "variables": "",
                "dimensions": "{}",
                "STD_shape": "",
                "TEMPpred_shape": "",
                "LAT_shape": "",
                "LON_shape": "",
                "BATHY_shape": "",
                "STD_dims": "",
                "TEMPpred_dims": "",
                "day_values": "",
                "time_values": "",
                "depth_value_m": np.nan,
            }
        )
        return DayData(
            day,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            {},
            [],
            [],
            [],
            base_inventory,
        )

    with netCDF4.Dataset(path) as ds:
        dims = {name: len(dim) for name, dim in ds.dimensions.items()}
        variables = list(ds.variables.keys())
        std = read_var(ds, "STD")
        temppred = read_var(ds, "TEMPpred")
        lat = read_var(ds, "LAT")
        lon = read_var(ds, "LON")
        bathy = read_var(ds, "BATHY")
        dept = read_var(ds, "DEPT")

        day_values: list[float] = []
        time_values: list[float] = []
        if "day" in ds.variables:
            day_values = masked_to_nan(ds.variables["day"][:]).ravel().tolist()
        if "TIME" in ds.variables:
            time_values = masked_to_nan(ds.variables["TIME"][:]).ravel().tolist()
        elif "time" in ds.variables:
            time_values = masked_to_nan(ds.variables["time"][:]).ravel().tolist()

        depth_value = np.nan
        if dept is not None and dept.size >= DEPTH_INDEX_USED:
            depth_value = float(np.ravel(dept)[DEPTH_INDEX_USED - 1])

        base_inventory.update(
            {
                "variables": ";".join(variables),
                "dimensions": json.dumps(dims, sort_keys=True),
                "STD_shape": str(var_shape(ds, "STD") or ""),
                "TEMPpred_shape": str(var_shape(ds, "TEMPpred") or ""),
                "LAT_shape": str(var_shape(ds, "LAT") or ""),
                "LON_shape": str(var_shape(ds, "LON") or ""),
                "BATHY_shape": str(var_shape(ds, "BATHY") or ""),
                "STD_dims": str(var_dims(ds, "STD") or ""),
                "TEMPpred_dims": str(var_dims(ds, "TEMPpred") or ""),
                "day_values": json.dumps(day_values),
                "time_values": json.dumps(time_values),
                "depth_value_m": depth_value,
            }
        )

    return DayData(
        day,
        path,
        std,
        temppred,
        lat,
        lon,
        bathy,
        dept,
        dims,
        variables,
        time_values,
        day_values,
        base_inventory,
    )


def slice_count(std: np.ndarray | None) -> int:
    if std is None:
        return 0
    if std.ndim == 2:
        return 1
    return int(std.shape[0])


def get_slice(std: np.ndarray, idx: int) -> np.ndarray:
    if std.ndim == 2:
        if idx != 0:
            raise IndexError(idx)
        return std
    return std[idx, :, :]


def is_degenerate(mean_value: float, std_value: float, p1: float, p99: float) -> bool:
    if not np.isfinite(std_value):
        return True
    tol = max(NEAR_ZERO_ABS_STD, abs(mean_value) * NEAR_ZERO_REL_STD)
    return std_value <= tol or (np.isfinite(p1) and np.isfinite(p99) and abs(p99 - p1) <= tol)


def compute_slice_stats(day: date, idx: int, arr: np.ndarray) -> dict[str, Any]:
    total = int(arr.size)
    finite = np.isfinite(arr)
    finite_vals = arr[finite]
    nan_count = int(np.isnan(arr).sum())
    zero_count = int(np.sum(finite & (arr == 0)))
    finite_count = int(finite.sum())
    all_nan = finite_count == 0
    all_zero = finite_count > 0 and zero_count == finite_count

    if finite_count:
        min_v = float(np.min(finite_vals))
        max_v = float(np.max(finite_vals))
        mean_v = float(np.mean(finite_vals))
        std_v = float(np.std(finite_vals))
        p1, p50, p99 = [float(x) for x in np.percentile(finite_vals, [1, 50, 99])]
    else:
        min_v = max_v = mean_v = std_v = p1 = p50 = p99 = np.nan

    near_zero_variance = is_degenerate(mean_v, std_v, p1, p99)
    has_positive_variance = bool(finite_count > 1 and not near_zero_variance)
    usable_candidate = bool(
        finite_count > 0
        and not all_nan
        and not all_zero
        and not near_zero_variance
        and has_positive_variance
    )

    return {
        "date": day.isoformat(),
        "slice_index": idx,
        "shape": str(tuple(arr.shape)),
        "min": min_v,
        "max": max_v,
        "mean": mean_v,
        "std": std_v,
        "p1": p1,
        "p50": p50,
        "p99": p99,
        "nan_pct": 100.0 * nan_count / total if total else np.nan,
        "zero_pct": 100.0 * zero_count / total if total else np.nan,
        "finite_count": finite_count,
        "valid_count": finite_count,
        "total_cells": total,
        "finite_fraction": finite_count / total if total else np.nan,
        "valid_fraction": finite_count / total if total else np.nan,
        "zero_count": zero_count,
        "nan_count": nan_count,
        "all_zero": all_zero,
        "all_nan": all_nan,
        "near_zero_variance": bool(near_zero_variance),
        "has_positive_spatial_variance": has_positive_variance,
        "usable_candidate": usable_candidate,
    }


def choose_slice(stats_for_day: list[dict[str, Any]]) -> int | None:
    candidates = [s for s in stats_for_day if s["usable_candidate"]]
    if not candidates:
        return None
    candidates = sorted(
        candidates,
        key=lambda s: (
            int(s["finite_count"]),
            float(s["std"]) if np.isfinite(s["std"]) else -np.inf,
            float(s["max"]) if np.isfinite(s["max"]) else -np.inf,
        ),
        reverse=True,
    )
    return int(candidates[0]["slice_index"])


def robust_outliers(values: pd.Series, z_threshold: float = 3.5) -> set[str]:
    series = values.dropna()
    if len(series) < 5:
        return set()
    median = float(series.median())
    mad = float(np.median(np.abs(series - median)))
    if mad <= 0:
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = float(q3 - q1)
        if iqr <= 0:
            return set()
        lower = float(q1 - 3.0 * iqr)
        upper = float(q3 + 3.0 * iqr)
        return set(series[(series < lower) | (series > upper)].index)
    modified_z = 0.6745 * (series - median) / mad
    return set(series[np.abs(modified_z) > z_threshold].index)


def arrays_consistent(reference: np.ndarray | None, arr: np.ndarray | None) -> bool:
    if reference is None or arr is None:
        return False
    if reference.shape != arr.shape:
        return False
    return bool(np.allclose(reference, arr, equal_nan=True))


def add_map(ax: plt.Axes, arr: np.ndarray, title: str, vmin: float, vmax: float, cmap: str = "viridis") -> None:
    cm = plt.get_cmap(cmap).copy()
    cm.set_bad("#f2f2f2")
    image = ax.imshow(np.ma.masked_invalid(arr), origin="lower", cmap=cm, vmin=vmin, vmax=vmax)
    ax.set_title(title, fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])
    return image


def save_panel(
    selected_maps: dict[str, np.ndarray],
    outfile: Path,
    vmin: float,
    vmax: float,
    title: str,
    clean: bool = False,
) -> None:
    n = len(selected_maps)
    cols = 6
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 2.45), constrained_layout=True)
    axes_flat = np.ravel(axes)
    image = None
    for ax, (day_label, arr) in zip(axes_flat, selected_maps.items()):
        plot_arr = arr.copy()
        if clean:
            plot_arr[~np.isfinite(plot_arr)] = np.nan
        image = add_map(ax, plot_arr, day_label[-2:], vmin, vmax)
    for ax in axes_flat[n:]:
        ax.axis("off")
    if image is not None:
        fig.colorbar(image, ax=axes_flat.tolist(), shrink=0.72, label="STD")
    fig.suptitle(title, fontsize=13)
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def save_daily_maps(selected_maps: dict[str, np.ndarray], vmin: float, vmax: float) -> None:
    for day_label, arr in selected_maps.items():
        for directory, clean in [(DAILY_DIR, False), (CLEAN_DAILY_DIR, True)]:
            fig, ax = plt.subplots(figsize=(6.2, 4.8), constrained_layout=True)
            plot_arr = arr.copy()
            if clean:
                plot_arr[~np.isfinite(plot_arr)] = np.nan
            image = add_map(ax, plot_arr, f"STD surface {day_label}", vmin, vmax)
            fig.colorbar(image, ax=ax, shrink=0.85, label="STD")
            suffix = "clean" if clean else "fullgrid"
            fig.savefig(directory / f"STD_surface_{day_label}_{suffix}.png", dpi=180)
            plt.close(fig)


def save_timeseries(df: pd.DataFrame, metric: str, outfile: Path, ylabel: str, suspicious: set[str]) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5), constrained_layout=True)
    x = pd.to_datetime(df["date"])
    ax.plot(x, df[metric], marker="o", linewidth=1.6)
    if suspicious:
        mask = df["date"].isin(suspicious)
        ax.scatter(pd.to_datetime(df.loc[mask, "date"]), df.loc[mask, metric], color="crimson", zorder=5)
    ax.set_title(ylabel)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("October 2024")
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def save_slice_comparison(days: list[DayData], outfile: Path) -> None:
    available = [d for d in days if d.std is not None and slice_count(d.std) >= 2]
    if not available:
        return
    indices = sorted(set([0, len(available) // 2, len(available) - 1]))
    examples = [available[i] for i in indices]
    all_vals = []
    for d in examples:
        for idx in [0, 1]:
            vals = get_slice(d.std, idx)
            vals = vals[np.isfinite(vals)]
            if vals.size:
                all_vals.append(vals)
    if all_vals:
        vals = np.concatenate(all_vals)
        vmin, vmax = np.percentile(vals, [1, 99])
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
            vmin, vmax = float(np.nanmin(vals)), float(np.nanmax(vals))
            if vmin == vmax:
                vmax = vmin + 1.0
    else:
        vmin, vmax = 0.0, 1.0

    fig, axes = plt.subplots(len(examples), 2, figsize=(8.8, 3.2 * len(examples)), constrained_layout=True)
    axes = np.asarray(axes).reshape(len(examples), 2)
    image = None
    for row, d in enumerate(examples):
        for col, idx in enumerate([0, 1]):
            image = add_map(axes[row, col], get_slice(d.std, idx), f"{d.day.isoformat()} slice {idx}", vmin, vmax)
    if image is not None:
        fig.colorbar(image, ax=axes.ravel().tolist(), shrink=0.75, label="STD")
    fig.suptitle("STD day-slice comparison examples", fontsize=13)
    fig.savefig(outfile, dpi=180)
    plt.close(fig)


def write_markdown(summary_path: Path, report_path: Path, checks: dict[str, Any], day_df: pd.DataFrame) -> None:
    suspicious_days = checks["suspicious_days"]
    top_mean = day_df.sort_values("selected_mean", ascending=False).head(5)
    top_max = day_df.sort_values("selected_max", ascending=False).head(5)

    def fmt_days(days: list[str]) -> str:
        return ", ".join(days) if days else "Nenhum"

    top_mean_text = "\n".join(
        f"- {row.date}: mean={row.selected_mean:.6g}, max={row.selected_max:.6g}, p99={row.selected_p99:.6g}"
        for row in top_mean.itertuples()
    )
    top_max_text = "\n".join(
        f"- {row.date}: max={row.selected_max:.6g}, mean={row.selected_mean:.6g}, p99={row.selected_p99:.6g}"
        for row in top_max.itertuples()
    )

    ready = checks["final_verdict"].startswith("READY")
    recommendation = (
        "Sim, numericamente parecem prontos para aplicar o ROI x490, mantendo a convencao de slice identificada."
        if ready
        else "Ainda nao: rever os dias suspeitos antes de aplicar o ROI x490."
    )

    summary = f"""# October Surface STD Audit Summary

Output folder: `{OUTPUT_DIR}`

1. Existem 31 mapas STD surface para outubro?
   - {'Sim' if checks['days_found'] == checks['expected_days'] else 'Nao'}: foram encontrados {checks['days_found']} de {checks['expected_days']}.
2. Todos os ficheiros predModel_1 foram encontrados?
   - {'Sim' if checks['all_files_found'] else 'Nao'}.
3. A variavel STD existe em todos?
   - {'Sim' if checks['std_variable_found_all_days'] else 'Nao'}.
4. Qual slice do eixo day contem o STD valido?
   - Slice `{checks['selected_valid_day_slice']}`.
5. O primeiro slice esta realmente zero/degenarado?
   - {'Sim' if checks['slice0_degenerate_count'] == checks['days_found'] else 'Parcialmente'}: {checks['slice0_degenerate_count']} de {checks['days_found']} dias estao degenerados/zero no slice 0.
6. O segundo slice esta valido?
   - {'Sim' if checks['slice1_valid_count'] == checks['days_found'] else 'Parcialmente'}: {checks['slice1_valid_count']} de {checks['days_found']} dias validos no slice 1.
7. O mesmo slice valido e usado em todos os dias?
   - {'Sim' if checks['same_valid_slice_all_days'] else 'Nao'}.
8. Os STD tem shape 180 x 240?
   - {'Sim' if checks['all_shapes_match'] else 'Nao'}.
9. Ha mapas em branco?
   - {fmt_days(checks['blank_std_days'])}.
10. Ha mapas STD totalmente zero?
   - {fmt_days(checks['zero_std_days'])}.
11. Ha dias suspeitos?
   - {fmt_days(suspicious_days)}.
12. Quais dias tem maior STD media/maxima?
   - Maior media:
{top_mean_text}
   - Maior maxima:
{top_max_text}
13. Os mapas STD estao prontos para aplicar o ROI x490?
   - {recommendation}
14. Que pontos ainda devem ser confirmados com a Filipa?
   - Confirmar formalmente que `predModel_1` corresponde sempre a surface (~{checks['depth_value_m']:.6g} m).
   - Confirmar que o slice `{checks['selected_valid_day_slice']}` do eixo `day` e a convencao correta para todos os mapas STD de outubro.
   - Confirmar se zeros no slice 0 sao preenchimento/placeholder esperado e nao informacao fisica.

Final verdict: {checks['final_verdict']}

The October surface STD maps were audited and the valid day-slice convention was identified before applying the FRESNEL x490 ROI.
"""
    summary_path.write_text(summary, encoding="utf-8")

    report = f"""# October Surface STD Audit Report

## Scope

- Input root: `{checks['input_predmodel_root']}`
- Depth: predModel_{checks['depth_index_used']} / {checks['depth_value_m']:.6g} m
- Expected dates: 2024-10-01 to 2024-10-31
- No ROI was applied. Original NetCDF files were only read.

## Main Checks

- Files found: {checks['n_files_found']} / {checks['expected_days']}
- Missing days: {fmt_days(checks['days_missing'])}
- STD found all days: {checks['std_variable_found_all_days']}
- TEMPpred found all days: {checks['temppred_variable_found_all_days']}
- LAT/LON/BATHY found all days: {checks['lat_lon_bathy_found_all_days']}
- Expected STD shape: {checks['expected_shape']}
- Shapes match: {checks['all_shapes_match']}
- Day slices detected: {checks['day_slices_detected']}
- Selected valid day slice: {checks['selected_valid_day_slice']}
- Same valid slice all days: {checks['same_valid_slice_all_days']}
- Slice 0 degenerate count: {checks['slice0_degenerate_count']}
- Slice 1 valid count: {checks['slice1_valid_count']}
- Global plotting scale: vmin={checks['global_std_vmin']:.6g}, vmax={checks['global_std_vmax']:.6g}

## Suspicious Days

{fmt_days(suspicious_days)}

Detailed reasons are available in `std_october_surface_suspicious_days.csv`.

## Temporal Diagnostics

The CSV `std_october_surface_day_metrics.csv` contains daily mean, max, p99, valid fraction and nan fraction for the selected STD slice.

### Highest Mean STD

{top_mean_text}

### Highest Max STD

{top_max_text}

## Figures

- `october_STD_surface_fullgrid_panel.png`
- `october_STD_surface_fullgrid_clean_panel.png`
- `STD_mean_timeseries.png`
- `STD_max_timeseries.png`
- `STD_p99_timeseries.png`
- `STD_valid_fraction_timeseries.png`
- `STD_nan_fraction_timeseries.png`
- `STD_day_slice_comparison_examples.png`
- `STD_suspect_days_panel.png` when suspicious days exist
- Individual maps in `std_surface_fullgrid_daily/` and `std_surface_fullgrid_daily_clean/`

## Recommendation

{recommendation}

The slice convention should be carried forward explicitly when applying the FRESNEL x490 ROI.
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DAILY_DIR.mkdir(parents=True, exist_ok=True)

    days = [read_day(d) for d in EXPECTED_DAYS]
    inventory_rows = [d.inventory for d in days]

    slice_rows: list[dict[str, Any]] = []
    preliminary_selected: dict[str, int | None] = {}
    for d in days:
        if d.std is None:
            preliminary_selected[d.day.isoformat()] = None
            continue
        stats_for_day: list[dict[str, Any]] = []
        for idx in range(slice_count(d.std)):
            row = compute_slice_stats(d.day, idx, get_slice(d.std, idx))
            stats_for_day.append(row)
            slice_rows.append(row)
        preliminary_selected[d.day.isoformat()] = choose_slice(stats_for_day)

    selected_values = [v for v in preliminary_selected.values() if v is not None]
    selected_valid_day_slice = Counter(selected_values).most_common(1)[0][0] if selected_values else None
    same_valid_slice_all_days = bool(
        selected_values
        and len(selected_values) == len([d for d in days if d.path is not None])
        and len(set(selected_values)) == 1
    )

    day_rows: list[dict[str, Any]] = []
    selected_maps: dict[str, np.ndarray] = {}
    suspicious: dict[str, list[str]] = {}

    first_lat = next((d.lat for d in days if d.lat is not None), None)
    first_lon = next((d.lon for d in days if d.lon is not None), None)
    first_bathy = next((d.bathy for d in days if d.bathy is not None), None)
    first_nan_mask: np.ndarray | None = None

    for d in days:
        reasons: list[str] = []
        date_label = d.day.isoformat()
        selected_slice = preliminary_selected.get(date_label)
        if d.path is None:
            reasons.append("file_missing")
        if d.std is None:
            reasons.append("STD_missing")
        if d.temppred is None:
            reasons.append("TEMPpred_missing")
        if d.lat is None or d.lon is None or d.bathy is None:
            reasons.append("LAT_LON_BATHY_missing")

        std_shape_ok = False
        temppred_shape_ok = False
        selected_arr: np.ndarray | None = None
        selected_stats = None
        if d.std is not None:
            std_shape_ok = tuple(d.std.shape[-2:]) == EXPECTED_SHAPE
            if not std_shape_ok:
                reasons.append("STD_shape_mismatch")
            if selected_slice is None:
                reasons.append("STD_valid_slice_not_found")
            else:
                selected_arr = get_slice(d.std, selected_slice)
                selected_maps[date_label] = selected_arr
                selected_stats = compute_slice_stats(d.day, selected_slice, selected_arr)
                if selected_stats["all_zero"]:
                    reasons.append("STD_all_zero")
                if selected_stats["all_nan"]:
                    reasons.append("STD_all_nan")
                if selected_stats["nan_pct"] > 50:
                    reasons.append("STD_more_than_50pct_nan")
                if selected_stats["near_zero_variance"]:
                    reasons.append("STD_near_zero_variance")
                if selected_valid_day_slice is not None and selected_slice != selected_valid_day_slice:
                    reasons.append("valid_slice_inconsistent")

                if first_nan_mask is None:
                    first_nan_mask = np.isnan(selected_arr)
                elif not np.array_equal(first_nan_mask, np.isnan(selected_arr)):
                    reasons.append("STD_nan_mask_inconsistent")

        if d.temppred is not None:
            temppred_shape_ok = tuple(d.temppred.shape[-2:]) == EXPECTED_SHAPE
            if not temppred_shape_ok:
                reasons.append("TEMPpred_shape_mismatch")

        if first_lat is not None and d.lat is not None and not arrays_consistent(first_lat, d.lat):
            reasons.append("LAT_inconsistent")
        if first_lon is not None and d.lon is not None and not arrays_consistent(first_lon, d.lon):
            reasons.append("LON_inconsistent")
        if first_bathy is not None and d.bathy is not None and not arrays_consistent(first_bathy, d.bathy):
            reasons.append("BATHY_inconsistent")

        if reasons:
            suspicious[date_label] = reasons

        row = {
            "date": date_label,
            "path": str(d.path) if d.path else "",
            "selected_slice": selected_slice if selected_slice is not None else np.nan,
            "n_slices": slice_count(d.std),
            "std_shape": str(tuple(d.std.shape)) if d.std is not None else "",
            "temppred_shape": str(tuple(d.temppred.shape)) if d.temppred is not None else "",
            "std_shape_ok": std_shape_ok,
            "temppred_shape_ok": temppred_shape_ok,
            "lat_consistent": arrays_consistent(first_lat, d.lat) if d.lat is not None else False,
            "lon_consistent": arrays_consistent(first_lon, d.lon) if d.lon is not None else False,
            "bathy_consistent": arrays_consistent(first_bathy, d.bathy) if d.bathy is not None else False,
            "suspicious": bool(reasons),
            "suspicious_reasons": ";".join(reasons),
        }
        if selected_stats:
            row.update({f"selected_{k}": v for k, v in selected_stats.items() if k not in {"date", "slice_index", "shape"}})
            row["selected_mean"] = selected_stats["mean"]
            row["selected_max"] = selected_stats["max"]
            row["selected_p99"] = selected_stats["p99"]
            row["selected_valid_fraction"] = selected_stats["valid_fraction"]
            row["selected_nan_fraction"] = selected_stats["nan_pct"] / 100.0
        else:
            row.update(
                {
                    "selected_mean": np.nan,
                    "selected_max": np.nan,
                    "selected_p99": np.nan,
                    "selected_valid_fraction": np.nan,
                    "selected_nan_fraction": np.nan,
                }
            )
        day_rows.append(row)

    day_df = pd.DataFrame(day_rows)
    day_df = day_df.set_index("date", drop=False)
    mean_outliers = robust_outliers(day_df["selected_mean"])
    max_outliers = robust_outliers(day_df["selected_max"])
    for outlier_day in sorted(mean_outliers):
        suspicious.setdefault(outlier_day, []).append("STD_mean_temporal_outlier")
    for outlier_day in sorted(max_outliers):
        suspicious.setdefault(outlier_day, []).append("STD_max_temporal_outlier")
    day_df["suspicious_reasons"] = day_df["date"].map(lambda x: ";".join(sorted(set(suspicious.get(x, [])))))
    day_df["suspicious"] = day_df["suspicious_reasons"].astype(bool)
    day_df = day_df.reset_index(drop=True)

    finite_all = []
    for arr in selected_maps.values():
        vals = arr[np.isfinite(arr)]
        if vals.size:
            finite_all.append(vals)
    if finite_all:
        all_values = np.concatenate(finite_all)
        global_vmin, global_vmax = [float(x) for x in np.percentile(all_values, [1, 99])]
        if not np.isfinite(global_vmin) or not np.isfinite(global_vmax) or global_vmin == global_vmax:
            global_vmin = float(np.nanmin(all_values))
            global_vmax = float(np.nanmax(all_values))
        if global_vmin == global_vmax:
            global_vmax = global_vmin + 1.0
    else:
        global_vmin, global_vmax = 0.0, 1.0

    inventory_df = pd.DataFrame(inventory_rows)
    slice_df = pd.DataFrame(slice_rows)
    suspicious_df = pd.DataFrame(
        [{"date": k, "reasons": ";".join(sorted(set(v)))} for k, v in sorted(suspicious.items())]
    )
    if suspicious_df.empty:
        suspicious_df = pd.DataFrame(columns=["date", "reasons"])

    inventory_df.to_csv(OUTPUT_DIR / "std_october_surface_inventory.csv", index=False)
    slice_df.to_csv(OUTPUT_DIR / "std_october_surface_slice_stats.csv", index=False)
    day_df.to_csv(OUTPUT_DIR / "std_october_surface_day_metrics.csv", index=False)
    suspicious_df.to_csv(OUTPUT_DIR / "std_october_surface_suspicious_days.csv", index=False)

    if selected_maps:
        save_panel(
            selected_maps,
            OUTPUT_DIR / "october_STD_surface_fullgrid_panel.png",
            global_vmin,
            global_vmax,
            "October 2024 STD surface full grid",
            clean=False,
        )
        save_panel(
            selected_maps,
            OUTPUT_DIR / "october_STD_surface_fullgrid_clean_panel.png",
            global_vmin,
            global_vmax,
            "October 2024 STD surface full grid clean",
            clean=True,
        )
        if suspicious:
            suspect_maps = {k: selected_maps[k] for k in sorted(suspicious) if k in selected_maps}
            if suspect_maps:
                save_panel(
                    suspect_maps,
                    OUTPUT_DIR / "STD_suspect_days_panel.png",
                    global_vmin,
                    global_vmax,
                    "Suspicious STD surface days",
                    clean=True,
                )
        save_daily_maps(selected_maps, global_vmin, global_vmax)

    save_slice_comparison(days, OUTPUT_DIR / "STD_day_slice_comparison_examples.png")
    suspicious_day_set = set(suspicious)
    save_timeseries(day_df, "selected_mean", OUTPUT_DIR / "STD_mean_timeseries.png", "STD mean", suspicious_day_set)
    save_timeseries(day_df, "selected_max", OUTPUT_DIR / "STD_max_timeseries.png", "STD max", suspicious_day_set)
    save_timeseries(day_df, "selected_p99", OUTPUT_DIR / "STD_p99_timeseries.png", "STD p99", suspicious_day_set)
    save_timeseries(
        day_df,
        "selected_valid_fraction",
        OUTPUT_DIR / "STD_valid_fraction_timeseries.png",
        "STD valid fraction",
        suspicious_day_set,
    )
    save_timeseries(
        day_df,
        "selected_nan_fraction",
        OUTPUT_DIR / "STD_nan_fraction_timeseries.png",
        "STD nan fraction",
        suspicious_day_set,
    )

    days_found = int(sum(d.path is not None for d in days))
    days_missing = [d.day.isoformat() for d in days if d.path is None]
    std_variable_found_all_days = all(d.path is not None and d.std is not None for d in days)
    temppred_variable_found_all_days = all(d.path is not None and d.temppred is not None for d in days)
    lat_lon_bathy_found_all_days = all(
        d.path is not None and d.lat is not None and d.lon is not None and d.bathy is not None for d in days
    )
    all_shapes_match = bool(
        all(d.std is not None and tuple(d.std.shape[-2:]) == EXPECTED_SHAPE for d in days)
        and all(d.temppred is not None and tuple(d.temppred.shape[-2:]) == EXPECTED_SHAPE for d in days)
    )
    detected_slice_indices: set[int] = set()
    for n_slices in day_df["n_slices"].dropna().astype(int):
        detected_slice_indices.update(range(n_slices))
    day_slices_detected = sorted(detected_slice_indices)
    slice0_degenerate_count = int(
        slice_df[(slice_df["slice_index"] == 0) & ((slice_df["all_zero"]) | (slice_df["near_zero_variance"]))].shape[0]
    )
    slice1_valid_count = int(slice_df[(slice_df["slice_index"] == 1) & (slice_df["usable_candidate"])].shape[0])
    blank_std_days = sorted(
        set(
            day_df.loc[
                day_df["suspicious_reasons"].str.contains("STD_all_nan|STD_near_zero_variance", regex=True, na=False),
                "date",
            ]
        )
    )
    zero_std_days = sorted(
        set(day_df.loc[day_df["suspicious_reasons"].str.contains("STD_all_zero", regex=False, na=False), "date"])
    )
    nan_problem_days = sorted(
        set(
            day_df.loc[
                day_df["suspicious_reasons"].str.contains("STD_all_nan|STD_more_than_50pct_nan", regex=True, na=False),
                "date",
            ]
        )
    )
    shape_mismatch_days = sorted(
        set(
            day_df.loc[
                day_df["suspicious_reasons"].str.contains("shape_mismatch", regex=False, na=False),
                "date",
            ]
        )
    )

    final_ready = bool(
        days_found == len(EXPECTED_DAYS)
        and std_variable_found_all_days
        and temppred_variable_found_all_days
        and lat_lon_bathy_found_all_days
        and all_shapes_match
        and selected_valid_day_slice is not None
        and same_valid_slice_all_days
        and not suspicious
    )
    final_verdict = (
        "READY_FOR_ROI_X490: all October surface STD maps passed the audit."
        if final_ready
        else "REVIEW_BEFORE_ROI_X490: one or more audit checks require attention."
    )

    depth_values = [float(d.inventory.get("depth_value_m", np.nan)) for d in days if d.path is not None]
    depth_value = float(np.nanmedian(depth_values)) if depth_values else np.nan

    checks = {
        "input_predmodel_root": str(INPUT_ROOT),
        "depth_index_used": DEPTH_INDEX_USED,
        "depth_value_m": depth_value,
        "expected_days": len(EXPECTED_DAYS),
        "days_found": days_found,
        "days_missing": days_missing,
        "n_files_found": days_found,
        "all_files_found": days_found == len(EXPECTED_DAYS),
        "std_variable_found_all_days": std_variable_found_all_days,
        "temppred_variable_found_all_days": temppred_variable_found_all_days,
        "lat_lon_bathy_found_all_days": lat_lon_bathy_found_all_days,
        "std_shape_all_days": sorted(set(day_df["std_shape"].dropna().astype(str))),
        "expected_shape": list(EXPECTED_SHAPE),
        "all_shapes_match": all_shapes_match,
        "day_slices_detected": day_slices_detected,
        "selected_valid_day_slice": selected_valid_day_slice,
        "same_valid_slice_all_days": same_valid_slice_all_days,
        "slice0_degenerate_count": slice0_degenerate_count,
        "slice1_valid_count": slice1_valid_count,
        "blank_std_days": blank_std_days,
        "zero_std_days": zero_std_days,
        "nan_problem_days": nan_problem_days,
        "shape_mismatch_days": shape_mismatch_days,
        "suspicious_days": sorted(suspicious.keys()),
        "n_suspicious_days": len(suspicious),
        "global_std_vmin": global_vmin,
        "global_std_vmax": global_vmax,
        "final_verdict": final_verdict,
    }

    (OUTPUT_DIR / "std_october_surface_audit_checks.json").write_text(
        json.dumps(checks, indent=2, sort_keys=True, default=to_jsonable),
        encoding="utf-8",
    )
    write_markdown(
        OUTPUT_DIR / "std_october_surface_audit_summary.md",
        OUTPUT_DIR / "std_october_surface_audit_report.md",
        checks,
        day_df,
    )

    print(json.dumps(checks, indent=2, sort_keys=True, default=to_jsonable))


if __name__ == "__main__":
    main()
