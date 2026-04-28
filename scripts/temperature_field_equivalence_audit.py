"""Audit temperature-field equivalence for tempRes z candidates.

The georeferencing transform is fixed to the recommended CAND_B UTM transform
from the previous forensic audit. This script varies only:
- tempRes z candidate: 298, 299, 300
- target field candidate: TEMP/TEMPpred for georeference validation

STD fields are evaluated in a separate block and are not ranked as temperature
georeferencing targets.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

import georeference_tempres_from_axes_day299 as georef


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "Investigation_transition_to_planner" / "temperature_field_equivalence_audit"
GEOREF_DIR = ROOT / "results" / "Investigation_transition_to_planner" / "georef_tempres_from_axes_day299"
TRANSFORM_JSON = GEOREF_DIR / "tempres_georef_transform.json"
TEMPRES_Z_CANDIDATES = [298, 299, 300]
EPS = 1e-12


@dataclass
class TempResCandidate:
    z: int
    idx0: int
    array: np.ndarray
    mask: np.ndarray
    source_date_inferred: str
    date_audit_notes: str


@dataclass
class TargetCandidate:
    name: str
    family: str
    file_path: Path
    variable: str
    variable_kind: str
    day_index: str
    date_inferred: str
    apriori_or_assimilated: str
    array: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    bathy_mask: np.ndarray
    notes: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def to_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_df(path: Path, df: pd.DataFrame) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False)


def first_existing(paths: Sequence[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def parse_date_from_name(path: Path) -> Optional[str]:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", str(path))
    if not m:
        m2 = re.search(r"(2024)(\d{2})(\d{2})", path.name)
        if not m2:
            return None
        return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    return f"{yyyy}-{mm}-{dd}"


def load_tempres_candidates() -> Tuple[List[TempResCandidate], Dict[str, object]]:
    stack_path = first_existing([ROOT / "results" / "plots" / "X_surface_300.npy", ROOT / "results" / "fossum" / "X_surface_300.npy"])
    if stack_path is None:
        raise FileNotFoundError("Missing X_surface_300.npy")
    mask_path = first_existing([ROOT / "results" / "plots" / "mask_common.npy", ROOT / "results" / "fossum" / "mask_common.npy"])
    stack = np.load(stack_path).astype(np.float64, copy=False)
    if stack.ndim != 3:
        raise RuntimeError(f"Expected stack nz,ny,nx, got {stack.shape}")
    mask_common = np.isfinite(stack[0])
    if mask_path:
        mask_common = np.load(mask_path).astype(bool, copy=False)

    # No native date metadata has been found in tempIBHRes. This is the
    # operational hypothesis under test, not proof.
    legacy_dates = {298: "2024-10-29", 299: "2024-10-30", 300: "2024-10-31"}
    notes = (
        "No explicit tempIBHRes date metadata found. z/date mapping is audited numerically. "
        "Operational hypothesis: z=299 -> 2024-10-30, z=300 -> 2024-10-31. "
        "Direct DOY mapping for 2024-10-30/31 would exceed nz=300 and clip to z=300."
    )
    out: List[TempResCandidate] = []
    for z in TEMPRES_Z_CANDIDATES:
        idx0 = z - 1
        arr = stack[idx0].astype(np.float64, copy=True)
        arr[~mask_common] = np.nan
        out.append(
            TempResCandidate(
                z=z,
                idx0=idx0,
                array=arr,
                mask=mask_common,
                source_date_inferred=legacy_dates.get(z, "UNKNOWN"),
                date_audit_notes=notes,
            )
        )

    audit = {
        "stack_path": to_rel(stack_path),
        "mask_path": to_rel(mask_path) if mask_path else None,
        "shape_nz_ny_nx": [int(stack.shape[0]), int(stack.shape[1]), int(stack.shape[2])],
        "z_candidates": TEMPRES_Z_CANDIDATES,
        "date_mapping_status": "not metadata-proven; tested numerically",
        "legacy_operational_hypothesis": legacy_dates,
        "calendar_doy_check": {
            "2024-10-30_doy": date(2024, 10, 30).timetuple().tm_yday,
            "2024-10-31_doy": date(2024, 10, 31).timetuple().tm_yday,
            "nz_available": int(stack.shape[0]),
            "direct_doy_mapping_status": "out_of_range_for_both_dates; would clip to z=300 in old display code",
        },
        "notes": notes,
    }
    return out, audit


def coord_name(ds: xr.Dataset, names: Sequence[str]) -> str:
    for wanted in names:
        for n in list(ds.coords) + list(ds.dims):
            if n.lower() == wanted.lower():
                return n
    raise RuntimeError(f"Missing coordinate among {names}")


def reduce_2d(da: xr.DataArray, selectors: Optional[Dict[str, int]] = None) -> np.ndarray:
    work = da
    selectors = selectors or {}
    for dim in list(work.dims):
        dim_low = dim.lower()
        if dim in selectors:
            work = work.isel({dim: selectors[dim]})
        elif dim_low in selectors:
            work = work.isel({dim: selectors[dim_low]})
        elif work.ndim > 2:
            work = work.isel({dim: 0})
    arr = work.values
    if arr.ndim != 2:
        raise RuntimeError(f"Could not reduce {da.name} to 2D, got {arr.shape}")
    return arr.astype(np.float64, copy=False)


def add_day_slices(
    targets: List[TargetCandidate],
    ds: xr.Dataset,
    path: Path,
    family: str,
    var_name: str,
    variable_kind: str,
    apriori_or_assimilated: str,
    notes: str,
) -> None:
    if var_name not in ds.data_vars:
        return
    lat_name = coord_name(ds, ["lat", "LAT"])
    lon_name = coord_name(ds, ["lon", "LON"])
    lat = ds[lat_name].values.astype(np.float64)
    lon = ds[lon_name].values.astype(np.float64)
    bathy = reduce_2d(ds["BATHY"]) if "BATHY" in ds.data_vars else np.ones((lat.size, lon.size), dtype=np.float64)
    bathy_mask = np.isfinite(bathy)
    base_date = parse_date_from_name(path) or "UNKNOWN"
    da = ds[var_name]
    if da.ndim == 2:
        targets.append(
            TargetCandidate(
                name=f"{family}_{var_name}",
                family=family,
                file_path=path,
                variable=var_name,
                variable_kind=variable_kind,
                day_index="none_2d",
                date_inferred=base_date,
                apriori_or_assimilated=apriori_or_assimilated,
                array=da.values.astype(np.float64),
                lat=lat,
                lon=lon,
                bathy_mask=bathy_mask,
                notes=notes,
            )
        )
    elif da.ndim == 3 and da.dims[0].lower() == "day":
        for idx in range(int(da.shape[0])):
            targets.append(
                TargetCandidate(
                    name=f"{family}_{var_name}_day{idx}",
                    family=family,
                    file_path=path,
                    variable=var_name,
                    variable_kind=variable_kind,
                    day_index=f"day{idx}",
                    date_inferred=base_date,
                    apriori_or_assimilated=apriori_or_assimilated,
                    array=da.isel({da.dims[0]: idx}).values.astype(np.float64),
                    lat=lat,
                    lon=lon,
                    bathy_mask=bathy_mask,
                    notes=f"{notes}; NetCDF day dimension index {idx}",
                )
            )
    else:
        arr = reduce_2d(da, {"TIME": 0, "DEPT": 0, "time": 0, "depth": 0})
        targets.append(
            TargetCandidate(
                name=f"{family}_{var_name}_surface0",
                family=family,
                file_path=path,
                variable=var_name,
                variable_kind=variable_kind,
                day_index="surface0",
                date_inferred=base_date,
                apriori_or_assimilated=apriori_or_assimilated,
                array=arr,
                lat=lat,
                lon=lon,
                bathy_mask=bathy_mask,
                notes=f"{notes}; reduced to first available surface slice",
            )
        )


def load_targets() -> Tuple[List[TargetCandidate], Dict[str, object]]:
    targets: List[TargetCandidate] = []
    inventory: Dict[str, object] = {"candidate_files": []}

    explicit = [
        (
            "C4_predModel_20241031",
            [
                ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc",
                ROOT / "data" / "Test_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc",
                ROOT / "data" / "Test_C4" / "31-10-2024_predModel_1.nc",
            ],
            "apriori",
        ),
        (
            "C4_predModel_20241030",
            [
                ROOT / "data" / "Test_C4" / "Priori_Nazare_30-10-2024_1" / "30-10-2024_predModel_1.nc",
            ],
            "apriori",
        ),
        (
            "D4_predModel_20241030",
            [
                ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_predModel_1.nc",
                ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "Priori_Nazare_30-10-2024_1" / "30-10-2024_predModel_1.nc",
            ],
            "apriori",
        ),
        (
            "C4_AUVpredModel_20241031",
            [
                ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_AUVpredModel_1.nc",
                ROOT / "data" / "Test_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_AUVpredModel_1.nc",
                ROOT / "data" / "Test_C4" / "31-10-2024_AUVpredModel_1.nc",
            ],
            "assimilated/control",
        ),
        (
            "C4_AUVpredModel_20241030",
            [
                ROOT / "data" / "Test_C4" / "Nazare_30-10-2024_1" / "30-10-2024_AUVpredModel_1.nc",
            ],
            "assimilated/control",
        ),
        (
            "D4_AUVpredModel_20241030",
            [
                ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_AUVpredModel_1.nc",
                ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "Nazare_30-10-2024_1" / "30-10-2024_AUVpredModel_1.nc",
            ],
            "assimilated/control",
        ),
    ]

    for family, paths, class_name in explicit:
        path = first_existing(paths)
        inventory["candidate_files"].append(
            {"family": family, "found": path is not None, "path": to_rel(path) if path else None, "checked": [to_rel(p) for p in paths]}
        )
        if path is None:
            continue
        with xr.open_dataset(path, decode_times=False) as ds:
            inv = {
                "family": family,
                "path": to_rel(path),
                "dims": {k: int(v) for k, v in ds.sizes.items()},
                "data_vars": list(ds.data_vars),
                "coords": list(ds.coords),
            }
            inventory.setdefault("opened_files", []).append(inv)
            add_day_slices(targets, ds, path, family, "TEMPpred", "temperature", class_name, "TEMPpred temperature target")
            add_day_slices(targets, ds, path, family, "STD", "STD", f"{class_name}; STD separate", "STD uncertainty/control field; not ranked as temperature validation")

    for hres_date in ["20241030", "20241031"]:
        path = ROOT / "data" / "HResNew" / f"CMEMSnaza_{hres_date}_HResNew.nc"
        inventory["candidate_files"].append(
            {"family": f"HResNew_{hres_date}", "found": path.exists(), "path": to_rel(path) if path.exists() else None, "checked": [to_rel(path)]}
        )
        if not path.exists():
            continue
        with xr.open_dataset(path, decode_times=False) as ds:
            lat_name = coord_name(ds, ["lat", "LAT"])
            lon_name = coord_name(ds, ["lon", "LON"])
            lat = ds[lat_name].values.astype(np.float64)
            lon = ds[lon_name].values.astype(np.float64)
            bathy = reduce_2d(ds["BATHY"]) if "BATHY" in ds.data_vars else np.ones((lat.size, lon.size), dtype=np.float64)
            bathy_mask = np.isfinite(bathy)
            inventory.setdefault("opened_files", []).append(
                {
                    "family": f"HResNew_{hres_date}",
                    "path": to_rel(path),
                    "dims": {k: int(v) for k, v in ds.sizes.items()},
                    "data_vars": list(ds.data_vars),
                    "coords": list(ds.coords),
                }
            )
            if "TEMP" in ds.data_vars:
                arr0 = reduce_2d(ds["TEMP"], {"TIME": 0, "DEPT": 0, "time": 0, "depth": 0})
                targets.append(
                    TargetCandidate(
                        name=f"HResNew_{hres_date}_TEMP_time0_depth0",
                        family=f"HResNew_{hres_date}",
                        file_path=path,
                        variable="TEMP[TIME=0,DEPT=0]",
                        variable_kind="temperature",
                        day_index="TIME0_DEPT0",
                        date_inferred=parse_date_from_name(path) or f"{hres_date[:4]}-{hres_date[4:6]}-{hres_date[6:8]}",
                        apriori_or_assimilated="HResNew/control",
                        array=arr0,
                        lat=lat,
                        lon=lon,
                        bathy_mask=bathy_mask,
                        notes="HResNew TEMP surface first time/depth.",
                    )
                )
                da = ds["TEMP"]
                if da.ndim == 4:
                    surf = da.isel({da.dims[1]: 0}).mean(dim=da.dims[0], skipna=True).values.astype(np.float64)
                    targets.append(
                        TargetCandidate(
                            name=f"HResNew_{hres_date}_TEMP_time_mean_depth0",
                            family=f"HResNew_{hres_date}",
                            file_path=path,
                            variable="TEMP[mean_TIME,DEPT=0]",
                            variable_kind="temperature",
                            day_index="TIMEmean_DEPT0",
                            date_inferred=parse_date_from_name(path) or f"{hres_date[:4]}-{hres_date[4:6]}-{hres_date[6:8]}",
                            apriori_or_assimilated="HResNew/control",
                            array=surf,
                            lat=lat,
                            lon=lon,
                            bathy_mask=bathy_mask,
                            notes="HResNew TEMP surface time mean control.",
                        )
                    )
    return targets, inventory


def load_transform_axes() -> Tuple[np.ndarray, np.ndarray, Dict[str, object]]:
    payload = json.loads(TRANSFORM_JSON.read_text(encoding="utf-8"))
    x_grid_path = ROOT / payload["outputs"]["tempres_x_km_grid"]
    y_grid_path = ROOT / payload["outputs"]["tempres_y_km_grid"]
    xg = np.load(x_grid_path)
    yg = np.load(y_grid_path)
    return xg[0, :].astype(np.float64), yg[:, 0].astype(np.float64), payload


def roi_from_old_bboxes(target: TargetCandidate) -> Dict[str, Dict[str, object]]:
    rows: Dict[str, Dict[str, object]] = {}
    path = ROOT / "results" / "Investigation_transition_to_planner" / "candb_vs_userdirect_bboxes.csv"
    if path.exists():
        for row in csv.DictReader(path.open("r", encoding="utf-8", newline="")):
            rows[row["roi_id"]] = row
    rois: Dict[str, Dict[str, object]] = {"operational_roi": georef.parse_config_roi(target.lat, target.lon)}
    mapping = {"candb_roi": "cand_b_roi", "user_direct_roi": "user_direct_km_roi"}
    for out_name, row_id in mapping.items():
        row = rows.get(row_id)
        if row:
            rois[out_name] = {
                "x0": int(row["x0_idx"]),
                "x1": int(row["x1_idx"]),
                "y0": int(row["y0_idx"]),
                "y1": int(row["y1_idx"]),
                "source": to_rel(path),
            }
    return rois


def roi_mask(shape: Tuple[int, int], roi: Dict[str, object]) -> np.ndarray:
    out = np.zeros(shape, dtype=bool)
    out[int(roi["y0"]) : int(roi["y1"]) + 1, int(roi["x0"]) : int(roi["x1"]) + 1] = True
    return out


def metric_score(row: Dict[str, object]) -> float:
    pear = float(row.get("pearson", np.nan))
    grad = float(row.get("gradient_corr", np.nan))
    contour = float(row.get("contour_score", np.nan))
    nrmse = float(row.get("normalized_rmse", np.nan))
    return (
        (pear if np.isfinite(pear) else -1.0)
        + 0.35 * (grad if np.isfinite(grad) else -1.0)
        + 0.35 * (contour if np.isfinite(contour) else 0.0)
        - (nrmse if np.isfinite(nrmse) else 10.0)
    )


def compare_all(tempres: Sequence[TempResCandidate], targets: Sequence[TargetCandidate]) -> Tuple[pd.DataFrame, Dict[str, np.ndarray]]:
    x_coords, y_coords, transform = load_transform_axes()
    projection = georef.Projection(
        name="EPSG_32629_UTM29N_formula",
        units="km",
        forward=georef.utm_zone29n_forward,
        inverse=georef.utm_zone29n_inverse,
        notes="Imported from previous recommended transform.",
    )
    rows: List[Dict[str, object]] = []
    pred_cache: Dict[str, np.ndarray] = {}
    for target in targets:
        lon2, lat2 = np.meshgrid(target.lon, target.lat)
        hx, hy = projection.forward(lon2, lat2)
        rois = roi_from_old_bboxes(target)
        domain_masks = {"full_overlap": np.ones_like(target.array, dtype=bool)}
        for name, roi in rois.items():
            domain_masks[name] = roi_mask(target.array.shape, roi)
        for tr in tempres:
            pred = georef.regrid_to_hres(tr.array, x_coords, y_coords, hx, hy)
            support = georef.regrid_to_hres(tr.mask.astype(float), x_coords, y_coords, hx, hy) >= 0.5
            cache_key = f"z{tr.z}__{target.name}"
            pred_cache[cache_key] = pred
            for domain, dmask in domain_masks.items():
                valid_mask = dmask & target.bathy_mask & support
                m = georef.metric_row(pred, target.array, valid_mask)
                row = {
                    "source_tempres_z": tr.z,
                    "source_date_inferred": tr.source_date_inferred,
                    "target_family": target.family,
                    "target_file": to_rel(target.file_path),
                    "target_variable": target.variable,
                    "target_variable_kind": target.variable_kind,
                    "target_day_index": target.day_index,
                    "target_date_inferred": target.date_inferred,
                    "target_is_apriori_or_assimilated": target.apriori_or_assimilated,
                    "domain_tested": domain,
                    "rmse": m["rmse_temperature"],
                    "mae": m["mae_temperature"],
                    "bias": m["bias_mean"],
                    "max_abs_error": m["max_abs_error"],
                    "pearson": m["pearson_temperature"],
                    "spearman": m["spearman_temperature"],
                    "normalized_rmse": m["normalized_rmse"],
                    "gradient_corr": m["gradient_corr"],
                    "contour_score": m["contour_score"],
                    "ssim": m["ssim"],
                    "n_valid": m["n_valid"],
                    "score": np.nan,
                    "rank": "",
                    "notes": f"{tr.date_audit_notes} | {target.notes}",
                }
                if target.variable_kind == "temperature":
                    row["score"] = metric_score(row)
                else:
                    row["notes"] += " | STD separate block: not ranked as temperature validation."
                rows.append(row)

    df = pd.DataFrame(rows)
    temp_idx = df["target_variable_kind"] == "temperature"
    ranked = df[temp_idx].sort_values(["score", "pearson", "rmse"], ascending=[False, False, True]).copy()
    rank_map = {idx: rank for rank, idx in enumerate(ranked.index, start=1)}
    df.loc[temp_idx, "rank"] = [rank_map[idx] for idx in df[temp_idx].index]
    df = df.sort_values(["target_variable_kind", "rank", "score"], ascending=[True, True, False], na_position="last")
    return df, pred_cache


def best_row(df: pd.DataFrame, mask: pd.Series) -> Optional[pd.Series]:
    sub = df[mask & (df["target_variable_kind"] == "temperature")].copy()
    if sub.empty:
        return None
    sub["rank_num"] = pd.to_numeric(sub["rank"], errors="coerce")
    return sub.sort_values(["rank_num", "score"], ascending=[True, False]).iloc[0]


def summarize_checks(df: pd.DataFrame, target_inventory: Dict[str, object], tempres_audit: Dict[str, object]) -> Dict[str, object]:
    full = df[df["domain_tested"] == "full_overlap"].copy()
    temp_full = full[full["target_variable_kind"] == "temperature"].copy()
    temp_full["rank_num"] = pd.to_numeric(temp_full["rank"], errors="coerce")
    temp_full = temp_full.sort_values(["rank_num", "score"], ascending=[True, False])

    def row_payload(row: Optional[pd.Series]) -> Optional[Dict[str, object]]:
        if row is None:
            return None
        return {
            "source_tempres_z": int(row["source_tempres_z"]),
            "source_date_inferred": row["source_date_inferred"],
            "target_family": row["target_family"],
            "target_variable": row["target_variable"],
            "target_day_index": row["target_day_index"],
            "target_date_inferred": row["target_date_inferred"],
            "domain_tested": row["domain_tested"],
            "rank": int(row["rank"]),
            "rmse": float(row["rmse"]),
            "pearson": float(row["pearson"]),
            "score": float(row["score"]),
        }

    overall = temp_full.iloc[0] if not temp_full.empty else None
    apriori = best_row(full, full["target_is_apriori_or_assimilated"].eq("apriori"))
    hres = best_row(full, full["target_is_apriori_or_assimilated"].eq("HResNew/control"))
    c4 = best_row(full, full["target_family"].str.contains("C4", case=False, na=False))
    d4 = best_row(full, full["target_family"].str.contains("D4", case=False, na=False))
    auv = best_row(full, full["target_is_apriori_or_assimilated"].str.contains("assimilated", case=False, na=False))

    day30_rows = temp_full[temp_full["target_date_inferred"].eq("2024-10-30")]
    day31_rows = temp_full[temp_full["target_date_inferred"].eq("2024-10-31")]
    best_day30 = day30_rows.iloc[0] if not day30_rows.empty else None
    best_day31 = day31_rows.iloc[0] if not day31_rows.empty else None

    day0 = best_row(full, full["target_day_index"].eq("day0"))
    day1 = best_row(full, full["target_day_index"].eq("day1"))

    file_records = target_inventory.get("candidate_files", [])
    checks = {
        "created_at": now_iso(),
        "all_tempres_candidates_found": len(tempres_audit["z_candidates"]) == 3,
        "all_C4_candidates_found": all(r["found"] for r in file_records if r["family"].startswith("C4_predModel")),
        "all_D4_candidates_found": all(r["found"] for r in file_records if r["family"].startswith("D4_predModel")),
        "all_HResNew_candidates_found": all(r["found"] for r in file_records if r["family"].startswith("HResNew")),
        "AUVpredModel_candidates_found": any(r["found"] for r in file_records if "AUVpredModel" in r["family"]),
        "best_pair_overall": row_payload(overall),
        "best_pair_apriori_only": row_payload(apriori),
        "best_pair_HResNew_only": row_payload(hres),
        "best_pair_C4": row_payload(c4),
        "best_pair_D4": row_payload(d4),
        "best_pair_AUV_assimilated_control": row_payload(auv),
        "whether_z299_is_best_for_day30": bool(best_day30 is not None and int(best_day30["source_tempres_z"]) == 299),
        "whether_z300_is_best_for_day31": bool(best_day31 is not None and int(best_day31["source_tempres_z"]) == 300),
        "best_day30_pair": row_payload(best_day30),
        "best_day31_pair": row_payload(best_day31),
        "whether_day0_or_day1_matches_better": (
            "day0"
            if day0 is not None and (day1 is None or int(day0["rank"]) < int(day1["rank"]))
            else "day1"
            if day1 is not None
            else "unavailable"
        ),
        "best_day0_pair": row_payload(day0),
        "best_day1_pair": row_payload(day1),
        "whether_C4_or_D4_matches_better": (
            "C4"
            if c4 is not None and (d4 is None or int(c4["rank"]) < int(d4["rank"]))
            else "D4"
            if d4 is not None
            else "unavailable"
        ),
        "whether_HResNew_matches_better_than_TEMPpred": bool(
            hres is not None and apriori is not None and int(hres["rank"]) < int(apriori["rank"])
        ),
        "tempres_date_audit": tempres_audit,
        "target_inventory": target_inventory,
        "ranking_policy": "Ranks are assigned only to temperature targets. STD rows are kept as separate-control rows and not ranked.",
    }
    return checks


def imshow(ax: plt.Axes, arr: np.ndarray, title: str, cmap: str = "viridis") -> None:
    cm = plt.get_cmap(cmap).copy()
    cm.set_bad("white")
    im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cm)
    ax.set_title(title, fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


def make_figures(
    df: pd.DataFrame,
    tempres: Sequence[TempResCandidate],
    targets: Sequence[TargetCandidate],
    pred_cache: Dict[str, np.ndarray],
) -> None:
    temp_df = df[(df["target_variable_kind"] == "temperature") & (df["domain_tested"] == "full_overlap")].copy()
    temp_df["rank_num"] = pd.to_numeric(temp_df["rank"], errors="coerce")
    best = temp_df.sort_values("rank_num").iloc[0]
    tr = next(t for t in tempres if int(t.z) == int(best["source_tempres_z"]))
    target = next(t for t in targets if t.name == str(best["target_family"] + "_" + best["target_variable"]).replace("[", "_").replace("]", ""))
    # The generated target name is easier to match through row metadata.
    target = next(
        t
        for t in targets
        if t.family == best["target_family"]
        and t.variable == best["target_variable"]
        and t.day_index == best["target_day_index"]
        and t.variable_kind == "temperature"
    )
    pred = pred_cache[f"z{tr.z}__{target.name}"]
    diff = pred - target.array

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    imshow(axes[0], pred, f"tempRes z={tr.z} regridded")
    imshow(axes[1], target.array, f"{target.name}")
    imshow(axes[2], diff, "difference", "coolwarm")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "best_temperature_pair_comparison.png", dpi=160)
    plt.close(fig)

    pivot = temp_df.pivot_table(index="source_tempres_z", columns="target_family", values="pearson", aggfunc="max")
    fig, ax = plt.subplots(figsize=(10, 4.5))
    im = ax.imshow(pivot.values.astype(float), cmap="viridis", aspect="auto")
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([f"z={z}" for z in pivot.index])
    ax.set_title("Best Pearson by tempRes z and target family")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            ax.text(j, i, "" if pd.isna(val) else f"{val:.2f}", ha="center", va="center", color="white", fontsize=8)
    plt.colorbar(im, ax=ax, label="Pearson")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "temporal_candidate_comparison_panel.png", dpi=160)
    plt.close(fig)

    top = temp_df.sort_values("rank_num").head(4)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, (_, row) in zip(axes.ravel(), top.iterrows()):
        tr2 = next(t for t in tempres if int(t.z) == int(row["source_tempres_z"]))
        target2 = next(
            t
            for t in targets
            if t.family == row["target_family"]
            and t.variable == row["target_variable"]
            and t.day_index == row["target_day_index"]
            and t.variable_kind == "temperature"
        )
        pred2 = pred_cache[f"z{tr2.z}__{target2.name}"]
        imshow(ax, pred2 - target2.array, f"rank {row['rank']}: z={tr2.z} vs {target2.name}", "coolwarm")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "difference_maps_best_pairs.png", dpi=160)
    plt.close(fig)


def answer_questions(checks: Dict[str, object]) -> List[str]:
    def fmt_pair(key: str) -> str:
        row = checks.get(key)
        if not row:
            return "unavailable"
        return (
            f"z={row['source_tempres_z']} vs {row['target_family']} {row['target_variable']} "
            f"{row['target_day_index']} ({row['target_date_inferred']}), "
            f"rank={row['rank']}, Pearson={row['pearson']:.6f}, RMSE={row['rmse']:.6f}"
        )

    c4d4 = checks["whether_C4_or_D4_matches_better"]
    day01 = checks["whether_day0_or_day1_matches_better"]
    hres_better = "YES" if checks["whether_HResNew_matches_better_than_TEMPpred"] else "NO"
    auv = fmt_pair("best_pair_AUV_assimilated_control")
    return [
        "1. Qual tempRes z corresponde melhor ao dia 30?",
        f"   {fmt_pair('best_day30_pair')}",
        "2. Qual tempRes z corresponde melhor ao dia 31?",
        f"   {fmt_pair('best_day31_pair')}",
        "3. C4 ou D4 corresponde melhor ao tempRes?",
        f"   {c4d4}",
        "4. day0 ou day1 corresponde melhor?",
        f"   {day01}",
        "5. HResNew TEMP corresponde melhor do que TEMPpred?",
        f"   {hres_better}",
        "6. O AUVpredModel confirma ou diverge, sabendo que é assimilado?",
        f"   Best assimilated/control pair: {auv}",
        "7. A diferença principal parece vir de georreferência ou de incompatibilidade entre campos/produtos?",
        "   The fixed-transform audit tests field/product compatibility; if the best coherent pair remains weak, the residual is likely a mixture of georeferencing uncertainty and product/temporal mismatch rather than STD contamination.",
    ]


def write_reports(df: pd.DataFrame, checks: Dict[str, object]) -> None:
    temp_df = df[df["target_variable_kind"] == "temperature"].copy()
    temp_df["rank_num"] = pd.to_numeric(temp_df["rank"], errors="coerce")
    top = temp_df.sort_values("rank_num").head(15)
    std_count = int((df["target_variable_kind"] == "STD").sum())
    answers = answer_questions(checks)
    summary = [
        "# Temperature Field Equivalence Summary",
        "",
        f"- Output directory: `{to_rel(OUT_DIR)}`",
        f"- Temperature rows ranked: `{len(temp_df)}`",
        f"- STD/control rows kept separate: `{std_count}`",
        f"- Best overall: `{checks['best_pair_overall']}`",
        f"- Best apriori only: `{checks['best_pair_apriori_only']}`",
        f"- Best HResNew only: `{checks['best_pair_HResNew_only']}`",
        "",
        *answers,
        "",
        'The audit identifies the most coherent temperature-to-temperature pair for validating the tempRes-to-HRes/planner georeferencing, without mixing temperature and STD fields.',
    ]
    (OUT_DIR / "temperature_field_equivalence_summary.md").write_text("\n".join(summary), encoding="utf-8")

    report = [
        "# Temperature Field Equivalence Audit",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "## Method",
        "",
        "- Fixed transform: CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal.",
        "- Compared tempRes z=298, z=299, z=300 against available TEMP/TEMPpred targets.",
        "- STD fields are computed only as a separate block and are not ranked as temperature georeferencing targets.",
        "- Domains: full overlap, operational ROI, CAND_B ROI, USER_DIRECT ROI.",
        "",
        "## Date Audit",
        "",
        json.dumps(checks["tempres_date_audit"], indent=2),
        "",
        "## Top Temperature Leaderboard",
        "",
        georef.df_to_markdown(top.drop(columns=["rank_num"], errors="ignore")),
        "",
        "## Required Checks",
        "",
        json.dumps({k: v for k, v in checks.items() if k not in {"target_inventory", "tempres_date_audit"}}, indent=2),
        "",
        "## Direct Answers",
        "",
        *answers,
        "",
        'The audit identifies the most coherent temperature-to-temperature pair for validating the tempRes-to-HRes/planner georeferencing, without mixing temperature and STD fields.',
    ]
    (OUT_DIR / "temperature_field_equivalence_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    ensure_dir(OUT_DIR)
    tempres, tempres_audit = load_tempres_candidates()
    targets, target_inventory = load_targets()
    if not targets:
        raise RuntimeError("No target candidates found.")
    df, pred_cache = compare_all(tempres, targets)
    checks = summarize_checks(df, target_inventory, tempres_audit)

    write_df(OUT_DIR / "temperature_field_equivalence_leaderboard.csv", df)
    write_json(OUT_DIR / "temperature_field_equivalence_checks.json", checks)
    make_figures(df, tempres, targets, pred_cache)
    write_reports(df, checks)
    print(f"Wrote temperature field equivalence audit to {OUT_DIR}")
    print(f"Best overall: {checks['best_pair_overall']}")


if __name__ == "__main__":
    main()
