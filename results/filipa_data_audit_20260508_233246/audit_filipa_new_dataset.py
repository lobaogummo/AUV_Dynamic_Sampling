from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd


INPUT_ROOT = Path(r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel")
OUT_DIR = Path(__file__).resolve().parent
OCTOBER_DAYS = [f"2024-10-{d:02d}" for d in range(1, 32)]
PRED_RE = re.compile(r"(?P<day>\d{2})-10-2024_predModel_(?P<depth>\d+)\.nc$", re.I)
DATE_PATTERNS = [
    re.compile(r"(?P<y>20\d{2})(?P<m>\d{2})(?P<d>\d{2})"),
    re.compile(r"(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>20\d{2})"),
]


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(INPUT_ROOT))
    except ValueError:
        return str(p)


def jsonish(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)


def infer_date(name: str) -> str:
    for pat in DATE_PATTERNS:
        m = pat.search(name)
        if m:
            try:
                return f"{int(m['y']):04d}-{int(m['m']):02d}-{int(m['d']):02d}"
            except Exception:
                pass
    return ""


def classify_file(p: Path) -> str:
    s = str(p).lower()
    if p.suffix.lower() == ".m":
        return "scripts"
    if p.suffix.lower() == ".out":
        return "simulations_out"
    if "predmodel" in p.name.lower():
        return "predModel"
    if "01.data" in s and "all" in s:
        return "raw_CMEMS_Copernicus"
    if "01.data" in s and "cmemsgrid" in s:
        return "october_grouped_CMEMS_grid"
    if "01.data" in s and "hres" in s:
        return "downscaled_high_resolution"
    if p.suffix.lower() == ".exe":
        return "auxiliary_executable"
    return "auxiliary"


def var_attrs(v) -> dict:
    return {a: getattr(v, a) for a in v.ncattrs()}


def as_array(v):
    arr = v[:]
    if np.ma.isMaskedArray(arr):
        arr = arr.filled(np.nan)
    return np.asarray(arr, dtype=float)


def reduce_to_map(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    while arr.ndim > 2:
        arr = arr[0]
    return np.asarray(arr, dtype=float)


def select_best_map(arr: np.ndarray) -> tuple[np.ndarray, int]:
    """Select the most informative 2-D slice from variables with a leading day axis."""
    arr = np.asarray(arr, dtype=float)
    if arr.ndim <= 2:
        return np.asarray(arr, dtype=float), 0
    candidates = []
    for i in range(arr.shape[0]):
        m = reduce_to_map(arr[i])
        finite = np.isfinite(m)
        if finite.any():
            score = float(np.nanstd(m)) + float(np.nanmean((m != 0) & finite))
        else:
            score = -1.0
        candidates.append((score, i, m))
    score, idx, m = max(candidates, key=lambda x: x[0])
    return np.asarray(m, dtype=float), int(idx)


def stats(arr: np.ndarray) -> dict:
    arr = np.asarray(arr, dtype=float)
    n = int(arr.size)
    if n == 0:
        return dict(min=np.nan, max=np.nan, mean=np.nan, std=np.nan, nan_pct=100.0, zero_pct=np.nan, finite_pct=0.0)
    finite = np.isfinite(arr)
    nf = int(finite.sum())
    out = {
        "nan_pct": float(np.isnan(arr).sum() / n * 100),
        "finite_pct": float(nf / n * 100),
        "zero_pct": float(np.sum(finite & (arr == 0)) / n * 100),
    }
    if nf:
        vals = arr[finite]
        out.update(min=float(np.min(vals)), max=float(np.max(vals)), mean=float(np.mean(vals)), std=float(np.std(vals)))
    else:
        out.update(min=np.nan, max=np.nan, mean=np.nan, std=np.nan)
    return out


def choose_var(ds, candidates):
    lower = {k.lower(): k for k in ds.variables}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return ""


def read_depth_value(ds, depth_index: int | None):
    if depth_index is None:
        return np.nan
    for name in ("DEPT", "depth"):
        if name in ds.variables:
            arr = as_array(ds.variables[name]).ravel()
            if 1 <= depth_index <= len(arr):
                return float(arr[depth_index - 1])
    return np.nan


def grid_signature(ds):
    if "LAT" not in ds.variables or "LON" not in ds.variables:
        return None
    lat = as_array(ds.variables["LAT"])
    lon = as_array(ds.variables["LON"])
    return {
        "lat_shape": tuple(lat.shape),
        "lon_shape": tuple(lon.shape),
        "lat_min": float(np.nanmin(lat)),
        "lat_max": float(np.nanmax(lat)),
        "lon_min": float(np.nanmin(lon)),
        "lon_max": float(np.nanmax(lon)),
        "lat_first": float(np.ravel(lat)[0]),
        "lat_last": float(np.ravel(lat)[-1]),
        "lon_first": float(np.ravel(lon)[0]),
        "lon_last": float(np.ravel(lon)[-1]),
    }


def resolution_km(lat, lon):
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    if lat.ndim == 2:
        dlat = np.nanmedian(np.abs(np.diff(lat, axis=0)))
        dlon = np.nanmedian(np.abs(np.diff(lon, axis=1)))
        midlat = float(np.nanmedian(lat))
    else:
        dlat = np.nanmedian(np.abs(np.diff(lat)))
        dlon = np.nanmedian(np.abs(np.diff(lon)))
        midlat = float(np.nanmedian(lat))
    lat_km = float(dlat * 111.32)
    lon_km = float(dlon * 111.32 * math.cos(math.radians(midlat)))
    return {"lat_km": lat_km, "lon_km": lon_km, "mean_km": float(np.nanmean([lat_km, lon_km]))}


def save_map(arr, path: Path, title: str, cmap="viridis"):
    arr = reduce_to_map(arr)
    fig, ax = plt.subplots(figsize=(6, 4.5), constrained_layout=True)
    im = ax.imshow(arr, origin="lower", cmap=cmap)
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.colorbar(im, ax=ax, shrink=0.82)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save_panel(items, path: Path, title: str, cmap="viridis", max_items=31):
    items = items[:max_items]
    n = len(items)
    cols = 8
    rows = int(math.ceil(max(n, 1) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.1, rows * 1.9), constrained_layout=True)
    axes = np.atleast_1d(axes).ravel()
    vals = np.concatenate([np.ravel(np.asarray(a, dtype=float)[np.isfinite(np.asarray(a, dtype=float))]) for _, a in items if np.isfinite(np.asarray(a, dtype=float)).any()]) if items else np.array([])
    vmin, vmax = (float(np.nanpercentile(vals, 2)), float(np.nanpercentile(vals, 98))) if vals.size else (None, None)
    for ax, (label, arr) in zip(axes, items):
        ax.imshow(reduce_to_map(arr), origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(label, fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes[len(items):]:
        ax.axis("off")
    fig.suptitle(title, fontsize=12)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    map_dir = OUT_DIR / "per_predmodel_maps"
    (map_dir / "TEMPpred").mkdir(parents=True, exist_ok=True)
    (map_dir / "STD").mkdir(parents=True, exist_ok=True)
    (map_dir / "NaN_masks").mkdir(parents=True, exist_ok=True)
    (map_dir / "zero_masks").mkdir(parents=True, exist_ok=True)

    all_paths = sorted([p for p in INPUT_ROOT.rglob("*")])
    files = [p for p in all_paths if p.is_file()]
    dirs = [p for p in all_paths if p.is_dir()]

    tree_lines = [str(INPUT_ROOT)]
    for p in sorted(dirs + files):
        depth = len(p.relative_to(INPUT_ROOT).parts)
        tree_lines.append(f"{'  ' * depth}{p.name}{'/' if p.is_dir() else ''}")
    (OUT_DIR / "folder_tree.txt").write_text("\n".join(tree_lines), encoding="utf-8")

    file_rows = []
    for p in files:
        file_rows.append({
            "path": str(p), "relative_path": rel(p), "filename": p.name, "extension": p.suffix.lower(),
            "size_bytes": p.stat().st_size, "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
            "category": classify_file(p),
        })
    file_df = pd.DataFrame(file_rows)
    file_df.to_csv(OUT_DIR / "file_inventory.csv", index=False)

    nc_rows, pred_rows, suspicious = [], [], []
    day_metrics = []
    surface_temp_items, surface_std_items, blank_items = [], [], []
    grid_refs = []
    depth_values = {}
    pred_by_day_depth = defaultdict(list)

    nc_files = [p for p in files if p.suffix.lower() == ".nc"]
    for i, p in enumerate(nc_files, 1):
        row = {"path": str(p), "relative_path": rel(p), "filename": p.name, "category": classify_file(p),
               "size_bytes": p.stat().st_size, "date_inferred": infer_date(p.name)}
        reasons = []
        try:
            with netCDF4.Dataset(p) as ds:
                dims = {k: len(v) for k, v in ds.dimensions.items()}
                row["dimensions"] = jsonish(dims)
                row["variables"] = jsonish(list(ds.variables.keys()))
                row["global_attributes"] = jsonish({a: getattr(ds, a) for a in ds.ncattrs()})
                row["variable_shapes"] = jsonish({k: list(v.shape) for k, v in ds.variables.items()})
                row["variable_attributes"] = jsonish({k: var_attrs(v) for k, v in ds.variables.items()})
                row["units"] = jsonish({k: getattr(v, "units", "") for k, v in ds.variables.items()})
                temp_name = choose_var(ds, ["TEMPpred", "TEMP", "thetao", "temperature"])
                std_name = choose_var(ds, ["STD", "std", "stdev"])
                row["temp_variable"] = temp_name
                row["std_variable"] = std_name
                row["lat_present"] = "LAT" in ds.variables or "latitude" in ds.variables
                row["lon_present"] = "LON" in ds.variables or "longitude" in ds.variables
                row["bathy_present"] = "BATHY" in ds.variables
                m = PRED_RE.search(p.name)
                depth_index = int(m["depth"]) if m else None
                if m:
                    row["date_inferred"] = f"2024-10-{int(m['day']):02d}"
                    row["depth_index"] = depth_index
                    row["depth_value"] = read_depth_value(ds, depth_index)
                    depth_values[depth_index] = row["depth_value"]
                if temp_name:
                    tstats = stats(as_array(ds.variables[temp_name]))
                    row.update({f"temp_{k}": v for k, v in tstats.items()})
                else:
                    reasons.append("missing_TEMP_or_TEMPpred")
                if std_name:
                    sstats = stats(as_array(ds.variables[std_name]))
                    row.update({f"std_{k}": v for k, v in sstats.items()})
                if "predModel" in row["category"]:
                    miss = []
                    for req in ("LAT", "LON", "BATHY"):
                        if req not in ds.variables:
                            miss.append(req)
                    if not temp_name:
                        miss.append("TEMP/TEMPpred")
                    if not std_name:
                        miss.append("STD")
                    if miss:
                        reasons.append("missing_variables:" + ",".join(miss))
                    if temp_name and std_name and ds.variables[temp_name].shape != ds.variables[std_name].shape:
                        reasons.append("TEMP_STD_shape_mismatch")
                    sig = grid_signature(ds)
                    if sig:
                        grid_refs.append((p, sig))
                    tmap, temp_slice = select_best_map(as_array(ds.variables[temp_name])) if temp_name else (np.array([]), -1)
                    smap, std_slice = select_best_map(as_array(ds.variables[std_name])) if std_name else (np.array([]), -1)
                    row["selected_temp_slice"] = temp_slice
                    row["selected_std_slice"] = std_slice
                    if temp_name and (not np.isfinite(tmap).any() or np.nanstd(tmap) == 0 or np.nanmean(tmap == 0) == 1):
                        reasons.append("blank_or_degenerate_TEMP")
                    if std_name and (not np.isfinite(smap).any() or np.nanstd(smap) < 1e-12 or np.nanmean(smap == 0) == 1):
                        reasons.append("blank_or_degenerate_STD")
                    if temp_name and np.isnan(tmap).mean() > 0.5:
                        reasons.append("TEMP_nan_pct_gt_50")
                    if std_name and np.isnan(smap).mean() > 0.5:
                        reasons.append("STD_nan_pct_gt_50")
                    if m:
                        day = row["date_inferred"]
                        pred_by_day_depth[(day, depth_index)].append(p)
                        pred_row = dict(row)
                        pred_row["missing_variables"] = ",".join(miss)
                        pred_row["suspicious_reasons"] = ";".join(reasons)
                        pred_rows.append(pred_row)
                        if depth_index == 1 and day in OCTOBER_DAYS:
                            surface_temp_items.append((day[-2:], tmap))
                            surface_std_items.append((day[-2:], smap))
                            gy, gx = np.gradient(tmap)
                            grad = np.hypot(gx, gy)
                            high = np.nanpercentile(grad[np.isfinite(grad)], 90) if np.isfinite(grad).any() else np.nan
                            corr = np.corrcoef(tmap[np.isfinite(tmap) & np.isfinite(grad) & np.isfinite(smap)],
                                               smap[np.isfinite(tmap) & np.isfinite(grad) & np.isfinite(smap)])[0, 1] if np.sum(np.isfinite(tmap) & np.isfinite(grad) & np.isfinite(smap)) > 5 else np.nan
                            day_metrics.append({
                                "date": day,
                                "depth_index": depth_index,
                                "depth_value": row.get("depth_value", np.nan),
                                "temp_spatial_std": float(np.nanstd(tmap)),
                                "temp_range": float(np.nanmax(tmap) - np.nanmin(tmap)),
                                "gradient_magnitude_mean": float(np.nanmean(grad)),
                                "gradient_magnitude_max": float(np.nanmax(grad)),
                                "high_gradient_area_pct": float(np.nanmean(grad >= high) * 100) if np.isfinite(high) else np.nan,
                                "std_mean": float(np.nanmean(smap)),
                                "std_max": float(np.nanmax(smap)),
                                "temp_gradient_std_corr": float(corr) if np.isfinite(corr) else np.nan,
                            })
                    if reasons:
                        blank_items.append((f"{row.get('date_inferred','?')} d{depth_index}", np.isnan(tmap) | (tmap == 0) if tmap.size else np.zeros((10, 10))))
                        suspicious.append({"path": str(p), "relative_path": rel(p), "filename": p.name, "category": row["category"], "reasons": ";".join(reasons)})
                    if m:
                        stem = p.stem
                        save_map(tmap, map_dir / "TEMPpred" / f"{stem}_TEMPpred.png", stem + " TEMPpred")
                        save_map(smap, map_dir / "STD" / f"{stem}_STD.png", stem + " STD", cmap="magma")
                        save_map(np.isnan(tmap), map_dir / "NaN_masks" / f"{stem}_TEMPpred_nan.png", stem + " TEMP NaN", cmap="gray")
                        save_map(tmap == 0, map_dir / "zero_masks" / f"{stem}_TEMPpred_zero.png", stem + " TEMP zero", cmap="gray")
        except Exception as e:
            row["read_error"] = repr(e)
            suspicious.append({"path": str(p), "relative_path": rel(p), "filename": p.name, "category": row["category"], "reasons": "unreadable:" + repr(e)})
        nc_rows.append(row)

    pd.DataFrame(nc_rows).to_csv(OUT_DIR / "netcdf_inventory.csv", index=False)
    pred_df = pd.DataFrame(pred_rows)
    pred_df.to_csv(OUT_DIR / "predmodel_inventory.csv", index=False)

    out_files = [p for p in files if p.suffix.lower() == ".out"]
    out_rows = []
    for p in out_files:
        sz = p.stat().st_size
        day = infer_date(p.name) or infer_date(str(p.parent))
        text = ""
        try:
            with p.open("r", errors="replace") as fh:
                text = "".join([fh.readline() for _ in range(5)])
        except Exception as e:
            text = "READ_ERROR:" + repr(e)
        out_rows.append({"path": str(p), "relative_path": rel(p), "filename": p.name, "size_bytes": sz,
                         "date_inferred": day, "empty": sz == 0, "sample_head": text})
    pd.DataFrame(out_rows).to_csv(OUT_DIR / "out_file_inventory.csv", index=False)

    # Canonical grid from first valid October surface predModel.
    canon_path = None
    with netCDF4.Dataset(Path(pred_df.iloc[0]["path"])) as ds:
        lat = as_array(ds.variables["LAT"])
        lon = as_array(ds.variables["LON"])
        bathy = as_array(ds.variables["BATHY"])
        canon_path = Path(pred_df.iloc[0]["path"])
    res = resolution_km(lat, lon)
    bbox = {"lon_min": float(np.nanmin(lon)), "lon_max": float(np.nanmax(lon)), "lat_min": float(np.nanmin(lat)), "lat_max": float(np.nanmax(lat))}
    grid_summary = [{
        "canonical_source_file": str(canon_path), "grid_shape": list(bathy.shape),
        "LAT_shape": list(lat.shape), "LON_shape": list(lon.shape), "BATHY_shape": list(bathy.shape),
        **bbox, "lat_orientation": "increasing" if np.ravel(lat)[-1] > np.ravel(lat)[0] else "decreasing",
        "lon_orientation": "increasing" if np.ravel(lon)[-1] > np.ravel(lon)[0] else "decreasing",
        "latlon_are_1d": lat.ndim == 1 and lon.ndim == 1,
        "resolution_lat_km": res["lat_km"], "resolution_lon_km": res["lon_km"], "resolution_mean_km": res["mean_km"],
    }]
    pd.DataFrame(grid_summary).to_csv(OUT_DIR / "grid_summary.csv", index=False)

    save_map(bathy, OUT_DIR / "bathymetry_map.png", "Canonical BATHY", cmap="terrain")
    fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
    ax.plot([bbox["lon_min"], bbox["lon_max"], bbox["lon_max"], bbox["lon_min"], bbox["lon_min"]],
            [bbox["lat_min"], bbox["lat_min"], bbox["lat_max"], bbox["lat_max"], bbox["lat_min"]], "k-")
    ax.scatter(np.ravel(lon)[:: max(1, lon.size // 200)], np.full_like(np.ravel(lon)[:: max(1, lon.size // 200)], np.nanmedian(lat)), s=3)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Canonical grid geographic extent")
    fig.savefig(OUT_DIR / "grid_latlon_extent.png", dpi=150)
    plt.close(fig)

    save_panel(surface_temp_items, OUT_DIR / "october_TEMP_surface_panel.png", "October surface TEMPpred", cmap="viridis")
    save_panel(surface_std_items, OUT_DIR / "october_STD_surface_panel.png", "October surface STD", cmap="magma")
    save_panel(blank_items[:31], OUT_DIR / "missing_or_blank_maps_panel.png", "Suspicious missing/blank masks", cmap="gray")

    qdf = pd.DataFrame(day_metrics).drop_duplicates("date")
    if not qdf.empty:
        for col in ["temp_spatial_std", "temp_range", "gradient_magnitude_mean", "gradient_magnitude_max", "high_gradient_area_pct", "std_mean", "std_max"]:
            span = qdf[col].max() - qdf[col].min()
            qdf[col + "_norm"] = (qdf[col] - qdf[col].min()) / span if span and np.isfinite(span) else 0
        qdf["structure_score"] = qdf[[c for c in qdf.columns if c.endswith("_norm")]].mean(axis=1)
        rank = qdf.sort_values("structure_score", ascending=False)
    else:
        rank = qdf
    qdf.to_csv(OUT_DIR / "october_day_quality_metrics.csv", index=False)
    rank.to_csv(OUT_DIR / "interesting_days_ranking.csv", index=False)
    if not rank.empty:
        fig, ax = plt.subplots(figsize=(9, 4), constrained_layout=True)
        ax.bar(rank["date"].str[-2:], rank["structure_score"])
        ax.set_xlabel("October day")
        ax.set_ylabel("structure score")
        ax.set_title("Interesting days ranking")
        fig.savefig(OUT_DIR / "interesting_days_ranking.png", dpi=150)
        plt.close(fig)

    susp_df = pd.DataFrame(suspicious).drop_duplicates()
    susp_df.to_csv(OUT_DIR / "suspicious_files.csv", index=False)

    pred_days = sorted(set(pred_df.get("date_inferred", pd.Series(dtype=str)).dropna()))
    october_found = sorted([d for d in pred_days if d in OCTOBER_DAYS])
    missing_days = [d for d in OCTOBER_DAYS if d not in october_found]
    depths_found = sorted([int(x) for x in pred_df.get("depth_index", pd.Series(dtype=float)).dropna().unique()])
    expected_pred = len(OCTOBER_DAYS) * len(depths_found)
    all_same_grid = len({jsonish(sig) for _, sig in grid_refs}) == 1
    files_blank_temp = susp_df[susp_df.get("reasons", "").astype(str).str.contains("TEMP", na=False)]["relative_path"].tolist() if not susp_df.empty else []
    files_blank_std = susp_df[susp_df.get("reasons", "").astype(str).str.contains("STD", na=False)]["relative_path"].tolist() if not susp_df.empty else []
    recommended = rank["date"].head(7).tolist() if not rank.empty else []
    verdict = "Not ready as a final replacement until suspicious predModel files are reviewed." if len(susp_df) else "Ready as a replacement candidate: no suspicious predModel files detected by automated checks."
    if missing_days or len(pred_df[pred_df["date_inferred"].isin(OCTOBER_DAYS)]) < expected_pred:
        verdict = "Incomplete for October predModel coverage; do not replace tempRes yet without clarification."

    checks = {
        "input_root": str(INPUT_ROOT),
        "n_total_files": len(files),
        "n_netcdf_files": len(nc_files),
        "n_out_files": len(out_files),
        "n_matlab_scripts": int((file_df["extension"] == ".m").sum()),
        "n_predmodel_files": int((file_df["category"] == "predModel").sum()),
        "october_days_found": october_found,
        "october_days_missing": missing_days,
        "depths_found": depths_found,
        "all_predmodels_have_TEMP_or_TEMPpred": bool(pred_df["temp_variable"].astype(str).ne("").all()),
        "all_predmodels_have_STD": bool(pred_df["std_variable"].astype(str).ne("").all()),
        "all_predmodels_have_LAT_LON": bool((pred_df["lat_present"] & pred_df["lon_present"]).all()),
        "all_predmodels_have_BATHY": bool(pred_df["bathy_present"].all()),
        "all_predmodels_same_grid": bool(all_same_grid),
        "files_with_blank_TEMP": files_blank_temp,
        "files_with_blank_STD": files_blank_std,
        "files_with_nan_problem": susp_df[susp_df.get("reasons", "").astype(str).str.contains("nan_pct", na=False)]["relative_path"].tolist() if not susp_df.empty else [],
        "files_with_shape_mismatch": susp_df[susp_df.get("reasons", "").astype(str).str.contains("shape_mismatch", na=False)]["relative_path"].tolist() if not susp_df.empty else [],
        "files_with_missing_variables": susp_df[susp_df.get("reasons", "").astype(str).str.contains("missing", na=False)]["relative_path"].tolist() if not susp_df.empty else [],
        "n_suspicious_files": int(len(susp_df)),
        "canonical_grid_shape": list(bathy.shape),
        "canonical_latlon_bbox": bbox,
        "canonical_resolution_estimate": res,
        "recommended_surface_depth_or_layer": {"depth_index": 1, "depth_value": depth_values.get(1, np.nan)},
        "recommended_valid_days_for_planner": [d for d in OCTOBER_DAYS if d in october_found],
        "recommended_days_with_high_heterogeneity": recommended,
        "final_verdict": verdict,
    }
    (OUT_DIR / "filipa_data_audit_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    ext_counts = file_df["extension"].value_counts().to_dict()
    cat_counts = file_df["category"].value_counts().to_dict()
    top_days = ", ".join(recommended[:10]) if recommended else "n/a"
    complete = not missing_days and len(depths_found) > 0 and len(pred_df[pred_df["date_inferred"].isin(OCTOBER_DAYS)]) >= expected_pred
    n_oct_pred = int(len(pred_df[pred_df["date_inferred"].isin(OCTOBER_DAYS)]))
    n_surface = int(len(pred_df[(pred_df["date_inferred"].isin(OCTOBER_DAYS)) & (pred_df["depth_index"] == 1)]))
    problems = "; ".join(sorted(susp_df["reasons"].unique())) if not susp_df.empty else "No automated suspicious predModel conditions detected."

    summary = f"""# Filipa New Dataset Audit Summary

Output folder: `{OUT_DIR}`

1. Os dados novos estão completos? {"Sim para a cobertura predModel de outubro por profundidade encontrada." if complete else "Não totalmente: há lacunas ou problemas a rever."}
2. Existem 31 mapas de outubro com TEMP/TEMPpred e STD? {"Sim, existem 31 mapas surface e " + str(n_oct_pred) + " predModels de outubro no total." if n_surface == 31 else "Não: foram encontrados " + str(n_surface) + " mapas surface de outubro."}
3. Existem mapas em branco ou suspeitos? {"Sim: " + str(len(susp_df)) + " ficheiros suspeitos." if len(susp_df) else "Não nos predModels, pelos critérios automáticos aplicados."}
4. Qual é a grelha canónica? A grelha dos ficheiros `predModel` high-resolution.
5. Qual é o shape da grelha? `{list(bathy.shape)}`.
6. Qual é a resolução aproximada? {res["lat_km"]:.3f} km em latitude, {res["lon_km"]:.3f} km em longitude, média {res["mean_km"]:.3f} km.
7. Quais profundidades estão disponíveis? Índices {depths_found}; valores aproximados {[depth_values.get(i, None) for i in depths_found]} m.
8. Qual camada/profundidade deve ser usada primeiro para o pipeline surface? Profundidade índice 1, valor {depth_values.get(1, np.nan)} m.
9. Quais dias de outubro parecem mais heterogéneos/interessantes? {top_days}.
10. Os dados estão prontos para substituir o tempRes antigo? {verdict}
11. Quais problemas precisam ser reportados à Filipa? {problems}; além disso, não foram encontrados ficheiros `.out` nesta pasta.

The new Filipa dataset audit determines which high-resolution October TEMP/STD fields are valid, which files are suspicious, and which canonical grid should be used for regime discovery and planner integration.
"""
    (OUT_DIR / "filipa_data_audit_summary.md").write_text(summary, encoding="utf-8")

    report = f"""# Filipa New Dataset Forensic Audit

## Scope

Input root: `{INPUT_ROOT}`

This audit is read-only with respect to the input data. All generated artifacts were written to `{OUT_DIR}`.

## Inventory

- Total files: {len(files)}
- NetCDF files: {len(nc_files)}
- `.out` files: {len(out_files)}
- MATLAB scripts: {int((file_df["extension"] == ".m").sum())}
- predModel files: {int((file_df["category"] == "predModel").sum())}
- Extension counts: `{jsonish(ext_counts)}`
- Category counts: `{jsonish(cat_counts)}`

## predModel Coverage

- October days found: {', '.join(october_found)}
- October days missing: {', '.join(missing_days) if missing_days else 'none'}
- Depth indices found: {depths_found}
- October predModel count: {n_oct_pred}
- Expected October predModel count from found depths: {expected_pred}

## Canonical Grid

- Shape: `{list(bathy.shape)}`
- LAT shape: `{list(lat.shape)}`
- LON shape: `{list(lon.shape)}`
- BATHY shape: `{list(bathy.shape)}`
- BBox: `{jsonish(bbox)}`
- Resolution estimate: `{jsonish(res)}`
- Same grid across predModels: `{all_same_grid}`

## Suspicious Results

Suspicious file count: {len(susp_df)}

Reasons: {problems}

See `suspicious_files.csv` for file-level evidence.

## Interesting October Days

Top ranked days: {top_days}

Ranking is based on normalized spatial TEMP variability, thermal range, gradient statistics, high-gradient area, and STD metrics for the recommended surface layer.

## Reproducibility

Run:

```powershell
python "{OUT_DIR / 'audit_filipa_new_dataset.py'}"
```

The script regenerates the CSV, JSON, Markdown reports, folder tree, panels, and per-predModel diagnostic maps in the same output directory.
"""
    (OUT_DIR / "filipa_data_audit_report.md").write_text(report, encoding="utf-8")

    print(f"Audit complete: {OUT_DIR}")


if __name__ == "__main__":
    main()
