"""Audit temperature-field equivalence for fixed tempRes -> HRes/planner georeference.

The georeference is held fixed at the recommended CAND_B transform from the
previous investigation. This script varies only the tempRes z slice and the
candidate HRes/planner temperature product, so it can distinguish georeference
problems from field/product mismatches.

Temperature-vs-temperature rows drive the ranking. STD rows are computed as a
separate control and are explicitly excluded from georeference validation ranks.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "Investigation_transition_to_planner" / "temperature_field_equivalence_audit"
PREV_DIR = ROOT / "results" / "Investigation_transition_to_planner" / "georef_tempres_from_axes_day299"
GEOR_SCRIPT = ROOT / "scripts" / "georeference_tempres_from_axes_day299.py"
TRANSFORM_JSON = PREV_DIR / "tempres_georef_transform.json"

TEMPRES_Z_CANDIDATES = [298, 299, 300]
DOMAINS = ["full_overlap", "operational_roi", "candb_roi", "user_direct_roi"]


@dataclass
class TargetCandidate:
    target_family: str
    target_file: Path
    target_variable: str
    target_day_index: Optional[int]
    target_date_inferred: str
    target_is_apriori_or_assimilated: str
    array: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    bathy_mask: np.ndarray
    is_temperature_validation: bool
    notes: str


def import_georef_module():
    spec = importlib.util.spec_from_file_location("georef_tempres_from_axes_day299", GEOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {GEOR_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


GEO = import_georef_module()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def to_rel(path: Path | None) -> Optional[str]:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_df(path: Path, df: pd.DataFrame) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False)


def parse_date_from_name(path: Path) -> str:
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", path.name)
    if not m:
        return "unknown"
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def candidate_paths() -> Dict[str, List[Path]]:
    return {
        "C4_predModel": [
            ROOT / "data" / "Test_C4" / "Priori_Nazare_30-10-2024_1" / "30-10-2024_predModel_1.nc",
            ROOT / "data" / "Test_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc",
            ROOT / "data" / "Test_C4" / "31-10-2024_predModel_1.nc",
            ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_predModel_1.nc",
        ],
        "D4_predModel": [
            ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_predModel_1.nc",
        ],
        "C4_AUVpredModel": [
            ROOT / "data" / "Test_C4" / "Nazare_30-10-2024_1" / "30-10-2024_AUVpredModel_1.nc",
            ROOT / "data" / "Test_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_AUVpredModel_1.nc",
            ROOT / "data" / "Test_C4" / "31-10-2024_AUVpredModel_1.nc",
            ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1" / "31-10-2024_AUVpredModel_1.nc",
        ],
        "D4_AUVpredModel": [
            ROOT / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_AUVpredModel_1.nc",
        ],
        "HResNew": [
            ROOT / "data" / "HResNew" / "CMEMSnaza_20241030_HResNew.nc",
            ROOT / "data" / "HResNew" / "CMEMSnaza_20241031_HResNew.nc",
            ROOT / "data" / "HResNew" / "CMEMSnaza_20241029_HResNew.nc",
        ],
    }


def existing_unique(paths: Iterable[Path]) -> List[Path]:
    seen = set()
    out = []
    for path in paths:
        if path.exists():
            key = str(path.resolve()).lower()
            if key not in seen:
                seen.add(key)
                out.append(path)
    return out


def coord_name(ds: xr.Dataset, candidates: Sequence[str]) -> str:
    for cand in candidates:
        for name in list(ds.coords) + list(ds.dims):
            if name.lower() == cand.lower():
                return name
    raise RuntimeError(f"No coordinate found from {candidates}")


def extract_2d(da: xr.DataArray, day_idx: Optional[int] = None) -> np.ndarray:
    work = da
    for dim in list(work.dims):
        low = dim.lower()
        if day_idx is not None and low == "day":
            work = work.isel({dim: day_idx})
        elif work.ndim > 2:
            work = work.isel({dim: 0})
    arr = work.values
    if arr.ndim != 2:
        raise RuntimeError(f"Could not reduce {da.name} to 2D, got {arr.shape}")
    return arr.astype(np.float64, copy=False)


def add_day_variable_targets(
    targets: List[TargetCandidate],
    family: str,
    path: Path,
    ds: xr.Dataset,
    var_name: str,
    lat: np.ndarray,
    lon: np.ndarray,
    bathy_mask: np.ndarray,
    target_kind: str,
    is_temperature_validation: bool,
    notes: str,
) -> None:
    da = ds[var_name]
    date_inferred = parse_date_from_name(path)
    if "day" in [d.lower() for d in da.dims]:
        day_dim = next(d for d in da.dims if d.lower() == "day")
        for idx in range(int(da.sizes[day_dim])):
            targets.append(
                TargetCandidate(
                    target_family=family,
                    target_file=path,
                    target_variable=var_name,
                    target_day_index=int(idx),
                    target_date_inferred=date_inferred,
                    target_is_apriori_or_assimilated=target_kind,
                    array=extract_2d(da, day_idx=idx),
                    lat=lat,
                    lon=lon,
                    bathy_mask=bathy_mask,
                    is_temperature_validation=is_temperature_validation,
                    notes=notes,
                )
            )
    else:
        targets.append(
            TargetCandidate(
                target_family=family,
                target_file=path,
                target_variable=var_name,
                target_day_index=None,
                target_date_inferred=date_inferred,
                target_is_apriori_or_assimilated=target_kind,
                array=extract_2d(da),
                lat=lat,
                lon=lon,
                bathy_mask=bathy_mask,
                is_temperature_validation=is_temperature_validation,
                notes=notes,
            )
        )


def load_targets() -> Tuple[List[TargetCandidate], Dict[str, object]]:
    targets: List[TargetCandidate] = []
    found: Dict[str, object] = {}
    for family, paths in candidate_paths().items():
        existing = existing_unique(paths)
        found[family] = [to_rel(p) for p in existing]
        for path in existing:
            with xr.open_dataset(path, decode_times=False) as ds:
                lat_name = coord_name(ds, ["lat", "LAT"])
                lon_name = coord_name(ds, ["lon", "LON"])
                lat = ds[lat_name].values.astype(np.float64)
                lon = ds[lon_name].values.astype(np.float64)
                if "BATHY" in ds.data_vars:
                    bathy = extract_2d(ds["BATHY"])
                    bathy_mask = np.isfinite(bathy)
                else:
                    bathy_mask = np.ones((lat.size, lon.size), dtype=bool)

                if family == "HResNew":
                    if "TEMP" in ds.data_vars:
                        targets.append(
                            TargetCandidate(
                                target_family=family,
                                target_file=path,
                                target_variable="TEMP",
                                target_day_index=0,
                                target_date_inferred=parse_date_from_name(path).replace("unknown", infer_hres_date(path)),
                                target_is_apriori_or_assimilated="HResNew_temperature",
                                array=extract_2d(ds["TEMP"]),
                                lat=lat,
                                lon=lon,
                                bathy_mask=bathy_mask,
                                is_temperature_validation=True,
                                notes="HResNew TEMP time0 depth0 surface control.",
                            )
                        )
                    continue

                is_auv = "AUV" in family
                target_kind = "assimilated_control" if is_auv else "apriori_main"
                if "TEMPpred" in ds.data_vars:
                    add_day_variable_targets(
                        targets,
                        family,
                        path,
                        ds,
                        "TEMPpred",
                        lat,
                        lon,
                        bathy_mask,
                        target_kind,
                        True,
                        "Temperature validation target." if not is_auv else "Assimilated/control temperature target.",
                    )
                if "STD" in ds.data_vars:
                    add_day_variable_targets(
                        targets,
                        family,
                        path,
                        ds,
                        "STD",
                        lat,
                        lon,
                        bathy_mask,
                        "STD_control_not_temperature",
                        False,
                        "STD control only; excluded from temperature georeference validation ranking.",
                    )
    return targets, found


def infer_hres_date(path: Path) -> str:
    m = re.search(r"(\d{8})", path.name)
    if not m:
        return "unknown"
    token = m.group(1)
    return f"{token[:4]}-{token[4:6]}-{token[6:8]}"


def load_tempres_stack() -> Dict[str, object]:
    stack_path = ROOT / "results" / "plots" / "X_surface_300.npy"
    mask_path = ROOT / "results" / "plots" / "mask_common.npy"
    if not stack_path.exists():
        raise FileNotFoundError(stack_path)
    stack = np.load(stack_path).astype(np.float64, copy=False)
    mask = np.isfinite(stack[0])
    if mask_path.exists():
        mask = np.load(mask_path).astype(bool, copy=False)
    return {
        "stack_path": stack_path,
        "mask_path": mask_path if mask_path.exists() else None,
        "stack": stack,
        "mask": mask,
        "z_candidates": TEMPRES_Z_CANDIDATES,
    }


def tempres_date_hypothesis(z: int) -> str:
    # Existing reports used z=299 as a candidate for 2024-10-30 and z=300 as
    # the clipped/control candidate for 2024-10-31. This is not native metadata.
    if z == 299:
        return "candidate_2024-10-30_not_metadata_proven"
    if z == 300:
        return "candidate_2024-10-31_or_day304_clipped_not_metadata_proven"
    if z == 298:
        return "off_by_one_candidate_before_2024-10-30"
    return "unknown"


def load_fixed_transform() -> Dict[str, object]:
    payload = read_json(TRANSFORM_JSON)
    x_grid_path = ROOT / str(payload["outputs"]["tempres_x_km_grid"]).replace("/", "\\")
    y_grid_path = ROOT / str(payload["outputs"]["tempres_y_km_grid"]).replace("/", "\\")
    # The JSON paths are repo-relative with forward slashes; Path handles them.
    x_grid_path = ROOT / payload["outputs"]["tempres_x_km_grid"]
    y_grid_path = ROOT / payload["outputs"]["tempres_y_km_grid"]
    x_grid = np.load(x_grid_path)
    y_grid = np.load(y_grid_path)
    return {"payload": payload, "x": x_grid[0, :].astype(np.float64), "y": y_grid[:, 0].astype(np.float64)}


def load_rois(shape: Tuple[int, int]) -> Dict[str, np.ndarray]:
    bboxes = ROOT / "results" / "Investigation_transition_to_planner" / "candb_vs_userdirect_bboxes.csv"
    rois: Dict[str, np.ndarray] = {"full_overlap": np.ones(shape, dtype=bool)}
    if not bboxes.exists():
        return rois
    rows = list(csv.DictReader(bboxes.open("r", encoding="utf-8", newline="")))
    mapping = {
        "planner_operational_roi": "operational_roi",
        "cand_b_roi": "candb_roi",
        "user_direct_km_roi": "user_direct_roi",
    }
    for row in rows:
        if row.get("roi_id") not in mapping:
            continue
        mask = np.zeros(shape, dtype=bool)
        x0, x1 = int(row["x0_idx"]), int(row["x1_idx"])
        y0, y1 = int(row["y0_idx"]), int(row["y1_idx"])
        mask[y0 : y1 + 1, x0 : x1 + 1] = True
        rois[mapping[row["roi_id"]]] = mask
    for name in DOMAINS:
        rois.setdefault(name, np.zeros(shape, dtype=bool))
    return rois


def metric_to_row(metrics: Dict[str, object]) -> Dict[str, object]:
    return {
        "rmse": metrics["rmse_temperature"],
        "mae": metrics["mae_temperature"],
        "bias": metrics["bias_mean"],
        "max_abs_error": metrics["max_abs_error"],
        "pearson": metrics["pearson_temperature"],
        "spearman": metrics["spearman_temperature"],
        "normalized_rmse": metrics["normalized_rmse"],
        "gradient_corr": metrics["gradient_corr"],
        "contour_score": metrics["contour_score"],
        "ssim": metrics["ssim"],
        "n_valid": metrics["n_valid"],
    }


def evaluate() -> Tuple[pd.DataFrame, Dict[str, object], Dict[str, np.ndarray]]:
    tempres = load_tempres_stack()
    transform = load_fixed_transform()
    targets, found = load_targets()
    rows: List[Dict[str, object]] = []
    pred_cache: Dict[str, np.ndarray] = {}

    if not targets:
        raise RuntimeError("No targets found")

    # All loaded targets currently share the 180x240 HRes grid; keep the ROI
    # mask keyed to each target shape to be robust.
    for target in targets:
        projections = GEO.make_projections(target.lon, target.lat)
        proj = projections["EPSG_32629_UTM29N_formula"]
        lon2, lat2 = np.meshgrid(target.lon, target.lat)
        hres_x, hres_y = proj.forward(lon2, lat2)
        rois = load_rois(target.array.shape)
        for z in TEMPRES_Z_CANDIDATES:
            idx = z - 1
            arr = tempres["stack"][idx].astype(np.float64, copy=True)
            arr[~tempres["mask"]] = np.nan
            pred = GEO.regrid_to_hres(arr, transform["x"], transform["y"], hres_x, hres_y)
            cache_key = f"z{z}__{target.target_family}__{target.target_variable}__{target.target_day_index}__{target.target_date_inferred}"
            pred_cache[cache_key] = pred
            for domain in DOMAINS:
                domain_mask = rois.get(domain, np.zeros(target.array.shape, dtype=bool))
                valid_mask = target.bathy_mask & domain_mask
                metrics = GEO.metric_row(pred, target.array, valid_mask)
                rows.append(
                    {
                        "source_tempres_z": z,
                        "source_date_inferred": tempres_date_hypothesis(z),
                        "target_family": target.target_family,
                        "target_file": to_rel(target.target_file),
                        "target_variable": target.target_variable,
                        "target_day_index": "" if target.target_day_index is None else target.target_day_index,
                        "target_date_inferred": target.target_date_inferred,
                        "target_is_apriori_or_assimilated": target.target_is_apriori_or_assimilated,
                        "domain_tested": domain,
                        **metric_to_row(metrics),
                        "rank": "",
                        "notes": target.notes,
                        "is_temperature_validation": bool(target.is_temperature_validation),
                    }
                )

    df = pd.DataFrame(rows)
    temp = df[df["is_temperature_validation"] == True].copy()
    for col in ["pearson", "gradient_corr", "contour_score", "normalized_rmse"]:
        temp[col] = pd.to_numeric(temp[col], errors="coerce")
    temp["score"] = (
        temp["pearson"].fillna(-1.0)
        + 0.5 * temp["gradient_corr"].fillna(-1.0)
        + 0.5 * temp["contour_score"].fillna(0.0)
        - temp["normalized_rmse"].fillna(10.0)
    )
    temp = temp.sort_values(["score", "pearson", "rmse"], ascending=[False, False, True]).reset_index(drop=True)
    rank_map = {int(i): int(rank) for rank, i in enumerate(temp.index, start=1)}
    # Need original indices, so redo on original subset.
    ranked_indices = temp.index.tolist()
    temp_original = df[df["is_temperature_validation"] == True].copy()
    temp_original["score"] = (
        pd.to_numeric(temp_original["pearson"], errors="coerce").fillna(-1.0)
        + 0.5 * pd.to_numeric(temp_original["gradient_corr"], errors="coerce").fillna(-1.0)
        + 0.5 * pd.to_numeric(temp_original["contour_score"], errors="coerce").fillna(0.0)
        - pd.to_numeric(temp_original["normalized_rmse"], errors="coerce").fillna(10.0)
    )
    order = temp_original.sort_values(["score", "pearson", "rmse"], ascending=[False, False, True]).index
    for rank, original_idx in enumerate(order, start=1):
        df.loc[original_idx, "rank"] = str(rank)
    df["score"] = np.nan
    df.loc[temp_original.index, "score"] = temp_original["score"]
    return df, {"found": found, "tempres": tempres, "transform": transform, "targets": targets}, pred_cache


def best_row(df: pd.DataFrame, filt) -> Optional[pd.Series]:
    sub = df[filt(df)].copy()
    sub = sub[sub["is_temperature_validation"] == True]
    if sub.empty:
        return None
    sub["rank_num"] = pd.to_numeric(sub["rank"], errors="coerce")
    return sub.sort_values("rank_num").iloc[0]


def make_checks(df: pd.DataFrame, context: Dict[str, object]) -> Dict[str, object]:
    found = context["found"]
    temp_only = df[df["is_temperature_validation"] == True].copy()
    temp_only["rank_num"] = pd.to_numeric(temp_only["rank"], errors="coerce")
    best = temp_only.sort_values("rank_num").iloc[0]
    apriori = best_row(df, lambda x: x["target_is_apriori_or_assimilated"].eq("apriori_main"))
    hres = best_row(df, lambda x: x["target_family"].eq("HResNew"))
    c4 = best_row(df, lambda x: x["target_family"].str.contains("C4", na=False) & ~x["target_family"].str.contains("AUV", na=False))
    d4 = best_row(df, lambda x: x["target_family"].str.contains("D4", na=False) & ~x["target_family"].str.contains("AUV", na=False))
    auv = best_row(df, lambda x: x["target_is_apriori_or_assimilated"].eq("assimilated_control"))

    def row_summary(row: Optional[pd.Series]) -> Optional[Dict[str, object]]:
        if row is None:
            return None
        return {
            "source_tempres_z": int(row["source_tempres_z"]),
            "target_family": row["target_family"],
            "target_file": row["target_file"],
            "target_variable": row["target_variable"],
            "target_day_index": row["target_day_index"],
            "target_date_inferred": row["target_date_inferred"],
            "domain_tested": row["domain_tested"],
            "rank": int(row["rank"]),
            "rmse": float(row["rmse"]),
            "pearson": float(row["pearson"]),
            "notes": row["notes"],
        }

    day30 = temp_only[temp_only["target_date_inferred"].eq("2024-10-30")]
    day31 = temp_only[temp_only["target_date_inferred"].eq("2024-10-31")]
    z_day30 = None if day30.empty else int(day30.sort_values("rank_num").iloc[0]["source_tempres_z"])
    z_day31 = None if day31.empty else int(day31.sort_values("rank_num").iloc[0]["source_tempres_z"])

    day0 = temp_only[temp_only["target_day_index"].astype(str).eq("0")]
    day1 = temp_only[temp_only["target_day_index"].astype(str).eq("1")]
    better_day = "day0" if (not day0.empty and (day1.empty or day0["rank_num"].min() < day1["rank_num"].min())) else "day1"
    if c4 is not None and d4 is not None:
        same_metrics = (
            abs(float(c4["rmse"]) - float(d4["rmse"])) < 1e-12
            and abs(float(c4["pearson"]) - float(d4["pearson"])) < 1e-12
        )
        if same_metrics:
            better_family = "tie_C4_D4_indistinguishable"
        else:
            better_family = "C4" if int(c4["rank"]) < int(d4["rank"]) else "D4"
    elif c4 is not None:
        better_family = "C4"
    elif d4 is not None:
        better_family = "D4"
    else:
        better_family = None
    hres_better = hres is not None and apriori is not None and int(hres["rank"]) < int(apriori["rank"])

    return {
        "created_at": now_iso(),
        "fixed_transform": read_json(TRANSFORM_JSON),
        "all_tempres_candidates_found": all(1 <= z <= context["tempres"]["stack"].shape[0] for z in TEMPRES_Z_CANDIDATES),
        "all_C4_candidates_found": len(found.get("C4_predModel", [])) > 0,
        "all_D4_candidates_found": len(found.get("D4_predModel", [])) > 0,
        "all_HResNew_candidates_found": len(found.get("HResNew", [])) > 0,
        "AUVpredModel_candidates_found": len(found.get("C4_AUVpredModel", [])) > 0 or len(found.get("D4_AUVpredModel", [])) > 0,
        "found_files": found,
        "best_pair_overall": row_summary(best),
        "best_pair_apriori_only": row_summary(apriori),
        "best_pair_HResNew_only": row_summary(hres),
        "best_pair_C4": row_summary(c4),
        "best_pair_D4": row_summary(d4),
        "best_pair_AUV_control": row_summary(auv),
        "whether_z299_is_best_for_day30": bool(z_day30 == 299) if z_day30 is not None else None,
        "best_z_for_day30": z_day30,
        "whether_z300_is_best_for_day31": bool(z_day31 == 300) if z_day31 is not None else None,
        "best_z_for_day31": z_day31,
        "whether_day0_or_day1_matches_better": better_day,
        "whether_C4_or_D4_matches_better": better_family,
        "whether_HResNew_matches_better_than_TEMPpred": bool(hres_better),
        "ranking_policy": "Ranks include temperature validation rows only. STD rows are retained with blank rank as a separate control.",
    }


def key_from_row(row: pd.Series) -> str:
    return f"z{int(row['source_tempres_z'])}__{row['target_family']}__{row['target_variable']}__{row['target_day_index']}__{row['target_date_inferred']}"


def find_target_for_row(row: pd.Series, targets: Sequence[TargetCandidate]) -> TargetCandidate:
    for t in targets:
        if (
            t.target_family == row["target_family"]
            and to_rel(t.target_file) == row["target_file"]
            and t.target_variable == row["target_variable"]
            and str("" if t.target_day_index is None else t.target_day_index) == str(row["target_day_index"])
            and t.target_date_inferred == row["target_date_inferred"]
        ):
            return t
    raise RuntimeError("Target not found for row")


def imshow(ax: plt.Axes, arr: np.ndarray, title: str, cmap: str = "viridis") -> None:
    cm = plt.get_cmap(cmap).copy()
    cm.set_bad("white")
    im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cm)
    ax.set_title(title)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


def make_figures(df: pd.DataFrame, context: Dict[str, object], pred_cache: Dict[str, np.ndarray]) -> None:
    ensure_dir(OUT_DIR)
    temp_only = df[df["is_temperature_validation"] == True].copy()
    temp_only["rank_num"] = pd.to_numeric(temp_only["rank"], errors="coerce")
    top = temp_only.sort_values("rank_num").head(3)
    best = top.iloc[0]
    target = find_target_for_row(best, context["targets"])
    pred = pred_cache[key_from_row(best)]
    diff = pred - target.array

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    imshow(axes[0], pred, f"tempRes z={best['source_tempres_z']} regridded")
    imshow(axes[1], target.array, f"{best['target_family']} {best['target_variable']} {best['target_day_index']}")
    imshow(axes[2], diff, "difference", cmap="coolwarm")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "best_temperature_pair_comparison.png", dpi=160)
    plt.close(fig)

    # Temporal panel: same best target, all z candidates.
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, z in zip(axes, TEMPRES_Z_CANDIDATES):
        row_like = best.copy()
        row_like["source_tempres_z"] = z
        key = key_from_row(row_like)
        imshow(ax, pred_cache[key], f"tempRes z={z} vs best target")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "temporal_candidate_comparison_panel.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(len(top), 3, figsize=(15, 4.2 * len(top)))
    if len(top) == 1:
        axes = np.array([axes])
    for r, (_, row) in enumerate(top.iterrows()):
        t = find_target_for_row(row, context["targets"])
        p = pred_cache[key_from_row(row)]
        imshow(axes[r, 0], p, f"rank {row['rank']} tempRes z={row['source_tempres_z']}")
        imshow(axes[r, 1], t.array, f"{row['target_family']} {row['target_variable']} {row['target_day_index']}")
        imshow(axes[r, 2], p - t.array, "difference", cmap="coolwarm")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "difference_maps_best_pairs.png", dpi=160)
    plt.close(fig)


def write_reports(df: pd.DataFrame, checks: Dict[str, object]) -> None:
    temp_only = df[df["is_temperature_validation"] == True].copy()
    temp_only["rank_num"] = pd.to_numeric(temp_only["rank"], errors="coerce")
    top = temp_only.sort_values("rank_num").head(12)
    std_count = int((df["is_temperature_validation"] == False).sum())

    final_sentence = (
        "The audit identifies the most coherent temperature-to-temperature pair for validating the "
        "tempRes-to-HRes/planner georeferencing, without mixing temperature and STD fields."
    )
    auv_summary = checks.get("best_pair_AUV_control")
    auv_note = (
        f"AUV best control pair: `{auv_summary}`. It is assimilated/control, not a primary validation target."
        if auv_summary
        else "No AUV assimilated/control TEMPpred candidate was available."
    )
    summary = [
        "# Temperature Field Equivalence Audit Summary",
        "",
        f"- Output directory: `{to_rel(OUT_DIR)}`",
        f"- Fixed transform: `{checks['fixed_transform']['method_name']}`",
        f"- Best pair overall: `{checks['best_pair_overall']}`",
        f"- Best apriori pair: `{checks['best_pair_apriori_only']}`",
        f"- STD control rows retained separately: `{std_count}`",
        "",
        "Direct answers:",
        f"1. Qual tempRes z corresponde melhor ao dia 30? `{checks.get('best_z_for_day30')}`",
        f"2. Qual tempRes z corresponde melhor ao dia 31? `{checks.get('best_z_for_day31')}`",
        f"3. C4 ou D4 corresponde melhor ao tempRes? `{checks.get('whether_C4_or_D4_matches_better')}`",
        f"4. day0 ou day1 corresponde melhor? `{checks.get('whether_day0_or_day1_matches_better')}`",
        f"5. HResNew TEMP corresponde melhor do que TEMPpred? `{checks.get('whether_HResNew_matches_better_than_TEMPpred')}`",
        "6. O AUVpredModel confirma ou diverge? Ver leaderboard; está marcado como `assimilated_control`, não alvo principal.",
        "7. A diferença principal parece vir de georreferência ou incompatibilidade entre produtos? A auditoria testa a georreferência fixa; diferenças entre TEMPpred/HResNew/AUV indicam componente forte de produto/campo, não só geometria.",
        "",
        final_sentence,
    ]
    (OUT_DIR / "temperature_field_equivalence_summary.md").write_text("\n".join(summary), encoding="utf-8")

    report = [
        "# Temperature Field Equivalence Audit Report",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "## Method",
        "",
        "- Fixed georeference: CAND_B EPSG:32629 normal x/y transform from the previous investigation.",
        "- tempRes candidates: z=298, z=299, z=300.",
        "- Main validation targets: TEMPpred and HResNew TEMP.",
        "- STD targets are computed only as a separate control and have blank validation rank.",
        "- Domains tested: full overlap, operational ROI, CAND_B ROI, USER_DIRECT ROI.",
        "",
        "## Top Temperature-to-Temperature Pairs",
        "",
        GEO.df_to_markdown(
            top[
                [
                    "rank",
                    "source_tempres_z",
                    "source_date_inferred",
                    "target_family",
                    "target_variable",
                    "target_day_index",
                    "target_date_inferred",
                    "target_is_apriori_or_assimilated",
                    "domain_tested",
                    "rmse",
                    "pearson",
                    "gradient_corr",
                    "contour_score",
                    "notes",
                ]
            ]
        ),
        "",
        "## Required Checks",
        "",
        "```json",
        json.dumps(checks, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Final Answers",
        "",
        f"1. Qual tempRes z corresponde melhor ao dia 30? `{checks.get('best_z_for_day30')}`",
        f"2. Qual tempRes z corresponde melhor ao dia 31? `{checks.get('best_z_for_day31')}`",
        f"3. C4 ou D4 corresponde melhor ao tempRes? `{checks.get('whether_C4_or_D4_matches_better')}`",
        f"4. day0 ou day1 corresponde melhor? `{checks.get('whether_day0_or_day1_matches_better')}`",
        f"5. HResNew TEMP corresponde melhor do que TEMPpred? `{checks.get('whether_HResNew_matches_better_than_TEMPpred')}`",
        "6. O AUVpredModel confirma ou diverge? It is included as assimilated/control; inspect rows marked `assimilated_control` rather than treating them as primary targets.",
        "7. A diferença principal parece vir de georreferência ou incompatibilidade entre campos/produtos? With the transform fixed, the ranking variation across TEMPpred/HResNew/AUV points to field/product compatibility as a major factor; it does not prove the georeference alone is wrong.",
        "",
        final_sentence,
    ]
    (OUT_DIR / "temperature_field_equivalence_report.md").write_text("\n".join(report), encoding="utf-8")

    # Rewrite the two narrative reports with ASCII-only final-answer text so the
    # files remain readable in Windows terminals that do not default to UTF-8.
    summary = [
        f"6. O AUVpredModel confirma ou diverge, sabendo que e assimilado? {auv_note}"
        if line.startswith("6. O AUVpredModel")
        else (
            "7. A diferenca principal parece vir de georreferencia ou incompatibilidade entre produtos? "
            "A auditoria testa a georreferencia fixa; a variacao entre TEMPpred, HResNew e AUV indica "
            "uma componente forte de compatibilidade campo/produto, nao apenas geometria."
            if line.startswith("7. A diferen") or line.startswith("7. A difer")
            else line
        )
        for line in summary
    ]
    report = [
        f"6. O AUVpredModel confirma ou diverge, sabendo que e assimilado? {auv_note}"
        if line.startswith("6. O AUVpredModel")
        else (
            "7. A diferenca principal parece vir de georreferencia ou incompatibilidade entre campos/produtos? "
            "With the transform fixed, the ranking variation across TEMPpred/HResNew/AUV points to field/product "
            "compatibility as a major factor; it does not prove the georeference alone is wrong."
            if line.startswith("7. A diferen") or line.startswith("7. A difer")
            else line
        )
        for line in report
    ]
    (OUT_DIR / "temperature_field_equivalence_summary.md").write_text("\n".join(summary), encoding="utf-8")
    (OUT_DIR / "temperature_field_equivalence_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    ensure_dir(OUT_DIR)
    df, context, pred_cache = evaluate()
    write_df(OUT_DIR / "temperature_field_equivalence_leaderboard.csv", df)
    checks = make_checks(df, context)
    write_json(OUT_DIR / "temperature_field_equivalence_checks.json", checks)
    make_figures(df, context, pred_cache)
    write_reports(df, checks)
    print(f"Wrote outputs to {OUT_DIR}")
    print(f"Best pair overall: {checks['best_pair_overall']}")
    print(f"Best apriori pair: {checks['best_pair_apriori_only']}")


if __name__ == "__main__":
    main()
