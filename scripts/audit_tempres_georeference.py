"""Forensic audit of tempIBHRes georeference evidence.

This script does not modify planner code or transfer descriptors.
It only audits evidence and produces reports/tables/figures.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]

OUT_REPORT = ROOT / "results" / "tempres_georef_report.md"
OUT_SUMMARY = ROOT / "results" / "tempres_georef_summary.md"
OUT_EVIDENCE_CSV = ROOT / "results" / "tempres_georef_evidence_index.csv"
OUT_CANDIDATES_CSV = ROOT / "results" / "tempres_georef_candidate_transforms.csv"
OUT_CHECKS_JSON = ROOT / "results" / "tempres_georef_checks.json"
OUT_OVERLAY_1 = ROOT / "results" / "tempres_georef_candidate_overlay_1.png"
OUT_OVERLAY_2 = ROOT / "results" / "tempres_georef_candidate_overlay_2.png"

TEMP_GSLIB = ROOT / "data" / "2024" / "tempIBHRes2024_1.gslib"
PLANNER_INTERFACE = (
    ROOT
    / "results"
    / "planner_baseline_scenario_c4_predmodel"
    / "inputs"
    / "30-10-2024_predModel_1_planner_interface.nc"
)
NETCDF_SUMMARY = ROOT / "results" / "netcdf_files_summary.csv"
CONFIG_FILE = ROOT / "OptimalPlanning_Lucrezia" / "Config_file.py"

GEOAXES_AUDIT = ROOT / "investigation" / "tempibhres_geoaxes_audit_20260417_171342"
REGISTRATION_DIR = ROOT / "investigation" / "tempibhres_hres_registration_controlled_v4"
REG_MANIFEST = REGISTRATION_DIR / "manifest.json"
REG_REPORT = REGISTRATION_DIR / "TEMPIBHRES_HRES_REGISTRATION_REPORT.md"
REG_BEST_SUMMARY = REGISTRATION_DIR / "tables" / "best_candidate_summary.csv"

RELATIVE_KM_DIRS = [
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_user_style_test_v3",
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1",
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_20260418_0001",
]

ARTIFACT_DIRS = [
    ROOT / "investigation" / "tempibhres_geoaxes_audit_20260417_171342",
    ROOT / "investigation" / "tempibhres_hres_registration_controlled_v4",
    ROOT / "results" / "plots" / "tempibhres_indexed_axes_fix_20260417_185500",
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_20260418_0001",
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_user_style_test_v3",
    ROOT / "results" / "plots" / "tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1",
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes",
    ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis_indexed_axes",
]

MANDATORY_TEXT_FILES = [
    ROOT / "scripts" / "Old_Code" / "physical_coords.py",
    ROOT / "scripts" / "12_fix_tempibhres_indexed_axes.py",
    ROOT / "scripts" / "13_export_tempibhres_relative_km_display_assumed.py",
    ROOT / "scripts" / "14_tempibhres_hres_registration_controlled.py",
    ROOT / "docs" / "THESIS_FIGURE_CONVENTIONS.md",
    ROOT / "docs" / "GRID_AND_COORDS.md",
    ROOT / "results" / "grid_audit_report.md",
    ROOT / "results" / "grid_audit_summary.md",
    ROOT / "results" / "grid_audit_stats.csv",
    ROOT / "results" / "validation_visual_data_branches_20260405_193102" / "tables" / "image_manifest.csv",
    ROOT / "results" / "validation_hres_surface_comparison_20260405_130636" / "REPORT.md",
    ROOT / "results" / "validation_hres_surface_comparison_20260405_130636" / "tables" / "grid_comparison.csv",
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "color_scale.json",
    ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis_indexed_axes" / "color_scale_norm.json",
    ROOT
    / "results"
    / "plots"
    / "tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1"
    / "manifest.json",
    ROOT
    / "results"
    / "plots"
    / "tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1"
    / "RELATIVE_KM_FEASIBILITY.md",
    REG_MANIFEST,
    REG_REPORT,
    REG_BEST_SUMMARY,
    GEOAXES_AUDIT / "AUDIT_TEMPIBHRES_GEOAXES.md",
    GEOAXES_AUDIT / "TRACE_EVIDENCE_COORDS.csv",
]

KEYWORDS = [
    "linear_resample_from_hres_bbox",
    "indexed_from_gslib_xy",
    "x,y,z,temp",
    "not independently verified",
    "not asserted",
    "display mapping",
    "inferred by registration",
    "coord_type",
    "planner_interface",
    "bbox",
    "utm_abs_km",
    "native georeferencing",
    "crop",
]


@dataclass
class TempGridInfo:
    title: str
    ncols_declared: int
    columns: List[str]
    n_rows: int
    nx: int
    ny: int
    nz: int
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
    valid_fraction: float


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def km_per_degree(lat_deg: float) -> Tuple[float, float]:
    phi = math.radians(lat_deg)
    km_deg_lat = (
        111.13292
        - 0.55982 * math.cos(2.0 * phi)
        + 0.001175 * math.cos(4.0 * phi)
        - 0.0000023 * math.cos(6.0 * phi)
    )
    km_deg_lon = 111.41284 * math.cos(phi) - 0.0935 * math.cos(3.0 * phi) + 0.00012 * math.cos(5.0 * phi)
    return km_deg_lat, km_deg_lon


def safe_read_text(path: Path, max_chars: int = 300000) -> str:
    raw = path.read_bytes()[:max_chars]
    try:
        return raw.decode("utf-8")
    except Exception:
        return raw.decode("latin-1", errors="ignore")


def classify_source(path: Path) -> str:
    p = rel(path).lower()
    if "/scripts/" in p:
        return "script"
    if p.endswith(".md"):
        return "report_or_doc"
    if p.endswith(".json"):
        return "manifest_or_json"
    if p.endswith(".csv"):
        return "table_or_index"
    return "other"


def scan_artifact_dirs() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    eid = 1
    for d in ARTIFACT_DIRS:
        if d.exists() and d.is_dir():
            files = [p for p in d.rglob("*") if p.is_file()]
            ext_counts = Counter(p.suffix.lower() for p in files)
            top_ext = "; ".join(f"{k}:{v}" for k, v in sorted(ext_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8])
            fact = f"{len(files)} files; top types -> {top_ext if top_ext else 'none'}"
            conf = "high"
        else:
            fact = "directory not found"
            conf = "medium"
        rows.append(
            {
                "evidence_id": f"DIR{eid:03d}",
                "path": rel(d),
                "source_group": "artifact_directory_inventory",
                "evidence_type": "inventory",
                "fact": fact,
                "confidence": conf,
            }
        )
        eid += 1
    return rows


def collect_text_files() -> List[Path]:
    files: List[Path] = []
    for p in MANDATORY_TEXT_FILES:
        if p.exists() and p.is_file():
            files.append(p)

    roots = [
        ROOT / "investigation" / "tempibhres_geoaxes_audit_20260417_171342",
        ROOT / "investigation" / "tempibhres_hres_registration_controlled_v4",
        ROOT / "results" / "plots",
        ROOT / "scripts",
        ROOT / "docs",
    ]
    exts = {".py", ".md", ".json", ".csv", ".txt"}
    path_tokens = [
        "tempibhres",
        "tempibhres",
        "relative_km",
        "indexed_axes",
        "hres_registration",
        "geoaxes",
        "planner_interface",
        "grid_audit",
    ]
    for base in roots:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in exts:
                continue
            low = str(p).lower()
            if any(tok in low for tok in path_tokens):
                files.append(p)

    dedup = sorted(set(files))
    return dedup


def extract_keyword_rows(paths: Iterable[Path], per_file_cap: int = 20) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    eid = 1
    pattern = re.compile("|".join(re.escape(k) for k in KEYWORDS), flags=re.IGNORECASE)

    for path in paths:
        try:
            text = safe_read_text(path)
        except Exception:
            continue
        hits = 0
        for idx, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                snippet = line.strip()
                if len(snippet) > 260:
                    snippet = snippet[:257] + "..."
                rows.append(
                    {
                        "evidence_id": f"TXT{eid:04d}",
                        "path": rel(path),
                        "source_group": classify_source(path),
                        "evidence_type": "keyword_snippet",
                        "line": idx,
                        "fact": snippet,
                        "confidence": "high" if classify_source(path) in {"script", "manifest_or_json"} else "medium",
                    }
                )
                eid += 1
                hits += 1
                if hits >= per_file_cap:
                    break
    return rows


def parse_temp_gslib(path: Path) -> TempGridInfo:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        title = f.readline().strip()
        ncols_declared = int(f.readline().strip())
        columns = [f.readline().strip() for _ in range(ncols_declared)]

        x_vals = set()
        y_vals = set()
        z_vals = set()
        n_rows = 0
        n_valid = 0
        x_min = float("inf")
        x_max = float("-inf")
        y_min = float("inf")
        y_max = float("-inf")
        z_min = float("inf")
        z_max = float("-inf")

        for line in f:
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            try:
                x = float(parts[0])
                y = float(parts[1])
                z = float(parts[2])
                t = float(parts[3])
            except Exception:
                continue
            n_rows += 1
            if math.isfinite(t):
                n_valid += 1

            xi = int(round(x))
            yi = int(round(y))
            zi = int(round(z))
            x_vals.add(xi)
            y_vals.add(yi)
            z_vals.add(zi)

            x_min = min(x_min, x)
            x_max = max(x_max, x)
            y_min = min(y_min, y)
            y_max = max(y_max, y)
            z_min = min(z_min, z)
            z_max = max(z_max, z)

    if n_rows == 0:
        raise RuntimeError(f"No data rows parsed from {path}")

    return TempGridInfo(
        title=title,
        ncols_declared=ncols_declared,
        columns=columns,
        n_rows=n_rows,
        nx=len(x_vals),
        ny=len(y_vals),
        nz=len(z_vals),
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        z_min=z_min,
        z_max=z_max,
        valid_fraction=float(n_valid / n_rows),
    )


def parse_operation_corners(config_path: Path) -> Tuple[List[float], List[float]]:
    text = safe_read_text(config_path, max_chars=120000)
    ll_match = re.search(r"OPERATION_LL_CORNER\s*=\s*\[\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*\]", text)
    ur_match = re.search(r"OPERATION_UR_CORNER\s*=\s*\[\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*\]", text)
    if ll_match is None or ur_match is None:
        raise RuntimeError("Could not parse OPERATION_LL_CORNER / OPERATION_UR_CORNER from Config_file.py")
    ll = [float(ll_match.group(1)), float(ll_match.group(2))]
    ur = [float(ur_match.group(1)), float(ur_match.group(2))]
    return ll, ur


def _first_gt(arr: np.ndarray, value: float) -> int:
    idx = np.where(arr > value)[0]
    if idx.size == 0:
        raise RuntimeError(f"No value in axis greater than {value}")
    return int(idx[0])


def parse_planner_grid(planner_nc: Path, config_path: Path) -> Dict[str, object]:
    if not planner_nc.exists():
        raise FileNotFoundError(planner_nc)
    ds = xr.open_dataset(planner_nc, decode_times=False)
    try:
        lat_name = next((c for c in ds.coords if c.lower() == "lat"), None)
        lon_name = next((c for c in ds.coords if c.lower() == "lon"), None)
        if lat_name is None or lon_name is None:
            raise RuntimeError("Planner interface is missing lat/lon coords")

        lat = ds[lat_name].values.astype(np.float64, copy=False)
        lon = ds[lon_name].values.astype(np.float64, copy=False)

        ll, ur = parse_operation_corners(config_path)
        lat_start = _first_gt(lat, ll[0])
        lat_stop = _first_gt(lat, ur[0]) - 1
        lon_start = _first_gt(lon, ll[1])
        lon_stop = _first_gt(lon, ur[1]) - 1
        lat_op = lat[lat_start:lat_stop]
        lon_op = lon[lon_start:lon_stop]

        lat_mid = 0.5 * float(lat.min() + lat.max())
        km_deg_lat, km_deg_lon = km_per_degree(lat_mid)
        dlon = float(np.mean(np.diff(lon)))
        dlat = float(np.mean(np.diff(lat)))

        out: Dict[str, object] = {
            "path": rel(planner_nc),
            "lat": lat,
            "lon": lon,
            "nx": int(lon.size),
            "ny": int(lat.size),
            "lon_min": float(lon.min()),
            "lon_max": float(lon.max()),
            "lat_min": float(lat.min()),
            "lat_max": float(lat.max()),
            "dx_deg": float(dlon),
            "dy_deg": float(dlat),
            "dx_m": float(abs(dlon) * km_deg_lon * 1000.0),
            "dy_m": float(abs(dlat) * km_deg_lat * 1000.0),
            "lat_orientation": "increasing" if lat[-1] > lat[0] else "decreasing",
            "lon_orientation": "increasing" if lon[-1] > lon[0] else "decreasing",
            "op_ll": ll,
            "op_ur": ur,
            "op_lat_start": int(lat_start),
            "op_lat_stop": int(lat_stop),
            "op_lon_start": int(lon_start),
            "op_lon_stop": int(lon_stop),
            "op_nx": int(lon_op.size),
            "op_ny": int(lat_op.size),
            "op_lon_min": float(lon_op.min()),
            "op_lon_max": float(lon_op.max()),
            "op_lat_min": float(lat_op.min()),
            "op_lat_max": float(lat_op.max()),
        }

        if "landt" in ds:
            land = ds["landt"].values
            out["land"] = land
            out["land_valid_fraction"] = float(np.mean(land == 1))
        else:
            out["land"] = None
            out["land_valid_fraction"] = None

        return out
    finally:
        ds.close()


def parse_hres_summary_row(summary_csv: Path) -> Dict[str, object]:
    if not summary_csv.exists():
        raise FileNotFoundError(summary_csv)

    preferred = "data/HResNew/CMEMSnaza_20241029_HResNew.nc"
    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    row = next((r for r in rows if (r.get("path") == preferred and r.get("open_ok") == "True")), None)
    if row is None:
        row = next(
            (
                r
                for r in rows
                if "/HResNew/" in (r.get("path") or "").replace("\\", "/") and r.get("open_ok") == "True"
            ),
            None,
        )
    if row is None:
        raise RuntimeError("Could not locate HResNew row in netcdf summary")

    return {
        "source_path": row.get("path"),
        "lon_min": float(row["lon_min"]),
        "lon_max": float(row["lon_max"]),
        "lat_min": float(row["lat_min"]),
        "lat_max": float(row["lat_max"]),
        "lon_res_deg": float(row["lon_res"]),
        "lat_res_deg": float(row["lat_res"]),
    }


def parse_registration(planner_info: Dict[str, object], temp_info: TempGridInfo) -> Optional[Dict[str, object]]:
    if not REG_MANIFEST.exists():
        return None
    payload = json.loads(REG_MANIFEST.read_text(encoding="utf-8"))

    best = payload.get("best_transformation", {})
    metrics = payload.get("best_metrics", {})
    inferred = payload.get("inferred_axes", {})

    try:
        x0 = int(best["x0_0based"])
        y0 = int(best["y0_0based"])
        x1 = int(best["x1_0based"])
        y1 = int(best["y1_0based"])
        w = int(best["w"])
        h = int(best["h"])
    except Exception:
        return None

    lon = planner_info["lon"]
    lat = planner_info["lat"]
    if not (0 <= x0 < lon.size and 0 <= x1 < lon.size and 0 <= y0 < lat.size and 0 <= y1 < lat.size):
        return None

    lon_min = float(min(lon[x0], lon[x1]))
    lon_max = float(max(lon[x0], lon[x1]))
    lat_min = float(min(lat[y0], lat[y1]))
    lat_max = float(max(lat[y0], lat[y1]))

    dx_deg = (lon_max - lon_min) / max(1, temp_info.nx - 1)
    dy_deg = (lat_max - lat_min) / max(1, temp_info.ny - 1)
    lat_mid = 0.5 * (lat_min + lat_max)
    km_deg_lat, km_deg_lon = km_per_degree(lat_mid)

    out = {
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "w": w,
        "h": h,
        "lon_min": lon_min,
        "lon_max": lon_max,
        "lat_min": lat_min,
        "lat_max": lat_max,
        "dx_deg": dx_deg,
        "dy_deg": dy_deg,
        "dx_m": float(abs(dx_deg) * km_deg_lon * 1000.0),
        "dy_m": float(abs(dy_deg) * km_deg_lat * 1000.0),
        "mask_iou": float(metrics.get("mask_iou", np.nan)),
        "pred_mean_corr": float(metrics.get("pred_mean_best_corr", np.nan)),
        "auv_mean_corr": float(metrics.get("auv_mean_best_corr", np.nan)),
        "inferred_axes": inferred,
        "manifest_path": rel(REG_MANIFEST),
    }
    return out


def parse_relative_km_manifests() -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for d in RELATIVE_KM_DIRS:
        mf = d / "manifest.json"
        if not mf.exists():
            continue
        try:
            payload = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        geom = payload.get("relative_km_geometry", {})
        crop = payload.get("crop", {})
        offsets = payload.get("axis_offsets_km", {})
        x_min = float(geom.get("x_km_min", 0.0)) + float(offsets.get("x_offset_km", 0.0))
        x_max = float(geom.get("x_km_max", 0.0)) + float(offsets.get("x_offset_km", 0.0))
        y_min = float(geom.get("y_km_min", 0.0)) + float(offsets.get("y_offset_km", 0.0))
        y_max = float(geom.get("y_km_max", 0.0)) + float(offsets.get("y_offset_km", 0.0))
        out.append(
            {
                "manifest_path": rel(mf),
                "x_km_min": x_min,
                "x_km_max": x_max,
                "y_km_min": y_min,
                "y_km_max": y_max,
                "dx_km_per_cell": float(geom.get("dx_km_per_cell", np.nan)),
                "dy_km_per_cell": float(geom.get("dy_km_per_cell", np.nan)),
                "crop": crop,
                "mode": payload.get("axis_mode", {}).get("mode"),
                "validation_status": payload.get("axis_mode", {}).get("independent_validation_status"),
            }
        )
    return out


def bbox_intersection(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    ax0, ax1, ay0, ay1 = a
    bx0, bx1, by0, by1 = b
    ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    iy = max(0.0, min(ay1, by1) - max(ay0, by0))
    return ix * iy


def bbox_area(b: Tuple[float, float, float, float]) -> float:
    x0, x1, y0, y1 = b
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def bbox_iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    inter = bbox_intersection(a, b)
    union = bbox_area(a) + bbox_area(b) - inter
    return inter / union if union > 0 else 0.0


def build_candidates(
    temp_info: TempGridInfo,
    planner_info: Dict[str, object],
    hres: Dict[str, object],
    reg: Optional[Dict[str, object]],
    rel_km: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    candidates: List[Dict[str, object]] = []

    lat_mid_hres = 0.5 * (hres["lat_min"] + hres["lat_max"])
    km_deg_lat, km_deg_lon = km_per_degree(lat_mid_hres)
    dx_deg_a = (hres["lon_max"] - hres["lon_min"]) / max(1, temp_info.nx - 1)
    dy_deg_a = (hres["lat_max"] - hres["lat_min"]) / max(1, temp_info.ny - 1)
    candidates.append(
        {
            "candidate_id": "CAND_A_DISPLAY_BBOX_HRES",
            "method": "linear_index_to_hres_bbox",
            "frame": "lon_lat",
            "x0": hres["lon_min"],
            "x1": hres["lon_max"],
            "y0": hres["lat_min"],
            "y1": hres["lat_max"],
            "dx_deg": dx_deg_a,
            "dy_deg": dy_deg_a,
            "dx_m": abs(dx_deg_a) * km_deg_lon * 1000.0,
            "dy_m": abs(dy_deg_a) * km_deg_lat * 1000.0,
            "nx": temp_info.nx,
            "ny": temp_info.ny,
            "source_artifacts": "physical_coords.py + netcdf_files_summary.csv + color_scale*.json",
            "evidence_strength": "high",
            "proof_status": "display_mapping_only",
            "notes": "Used in thesis/validation displays; does not prove native tempRes georeference.",
        }
    )

    if reg is not None:
        candidates.append(
            {
                "candidate_id": "CAND_B_REGISTRATION_TO_HRES_SUBAREA",
                "method": "registration_best_axis_aligned_crop_resample",
                "frame": "lon_lat",
                "x0": reg["lon_min"],
                "x1": reg["lon_max"],
                "y0": reg["lat_min"],
                "y1": reg["lat_max"],
                "dx_deg": reg["dx_deg"],
                "dy_deg": reg["dy_deg"],
                "dx_m": reg["dx_m"],
                "dy_m": reg["dy_m"],
                "nx": temp_info.nx,
                "ny": temp_info.ny,
                "source_artifacts": f"{reg['manifest_path']} + top_candidates_temperature_eval.csv",
                "evidence_strength": "high",
                "proof_status": "registration_derived_not_native",
                "mask_iou": reg["mask_iou"],
                "pred_mean_corr": reg["pred_mean_corr"],
                "auv_mean_corr": reg["auv_mean_corr"],
                "x0_hres_idx": reg["x0"],
                "x1_hres_idx": reg["x1"],
                "y0_hres_idx": reg["y0"],
                "y1_hres_idx": reg["y1"],
                "notes": "Strong quantitative alignment to TEST_C4 families; still inferred mapping.",
            }
        )

    for idx, rk in enumerate(rel_km, start=1):
        candidates.append(
            {
                "candidate_id": f"CAND_C{idx}_RELATIVE_KM_DISPLAY",
                "method": "relative_km_display_assumed",
                "frame": "local_km",
                "x0": rk["x_km_min"],
                "x1": rk["x_km_max"],
                "y0": rk["y_km_min"],
                "y1": rk["y_km_max"],
                "dx_km": rk["dx_km_per_cell"],
                "dy_km": rk["dy_km_per_cell"],
                "source_artifacts": rk["manifest_path"],
                "evidence_strength": "high",
                "proof_status": "display_axes_local_frame_only",
                "notes": "Manifest states not independently validated native georeference.",
            }
        )

    full_bbox = (
        float(planner_info["lon_min"]),
        float(planner_info["lon_max"]),
        float(planner_info["lat_min"]),
        float(planner_info["lat_max"]),
    )
    op_bbox = (
        float(planner_info["op_lon_min"]),
        float(planner_info["op_lon_max"]),
        float(planner_info["op_lat_min"]),
        float(planner_info["op_lat_max"]),
    )

    for cand in candidates:
        if cand.get("frame") != "lon_lat":
            cand["inside_planner_full"] = "n/a"
            cand["intersects_operational_roi"] = "n/a"
            cand["operational_iou_bbox"] = "n/a"
            cand["operational_coverage"] = "n/a"
            cand["resolution_ratio_x_vs_planner"] = "n/a"
            cand["resolution_ratio_y_vs_planner"] = "n/a"
            continue

        cb = (float(cand["x0"]), float(cand["x1"]), float(cand["y0"]), float(cand["y1"]))
        inter_full = bbox_intersection(cb, full_bbox)
        inter_op = bbox_intersection(cb, op_bbox)
        cand_area = bbox_area(cb)

        cand["inside_planner_full"] = bool(abs(inter_full - cand_area) < 1e-12)
        cand["intersects_operational_roi"] = bool(inter_op > 0)
        cand["operational_iou_bbox"] = float(bbox_iou(cb, op_bbox))
        cand["operational_coverage"] = float(inter_op / bbox_area(op_bbox)) if bbox_area(op_bbox) > 0 else 0.0

        if "dx_m" in cand and "dy_m" in cand:
            cand["resolution_ratio_x_vs_planner"] = float(cand["dx_m"] / planner_info["dx_m"])
            cand["resolution_ratio_y_vs_planner"] = float(cand["dy_m"] / planner_info["dy_m"])
        else:
            cand["resolution_ratio_x_vs_planner"] = "n/a"
            cand["resolution_ratio_y_vs_planner"] = "n/a"

    return candidates


def draw_overlay(
    planner_info: Dict[str, object],
    candidate: Dict[str, object],
    out_png: Path,
    title: str,
) -> None:
    ensure_parent(out_png)
    fig, ax = plt.subplots(figsize=(9.2, 6.2))

    land = planner_info.get("land")
    if isinstance(land, np.ndarray):
        land_plot = np.where(land == 1, 1.0, np.nan)
        ax.imshow(
            land_plot,
            origin="lower",
            extent=[planner_info["lon_min"], planner_info["lon_max"], planner_info["lat_min"], planner_info["lat_max"]],
            cmap="Greys",
            alpha=0.28,
            interpolation="nearest",
            aspect="auto",
        )

    full_rect = plt.Rectangle(
        (planner_info["lon_min"], planner_info["lat_min"]),
        planner_info["lon_max"] - planner_info["lon_min"],
        planner_info["lat_max"] - planner_info["lat_min"],
        fill=False,
        lw=2.0,
        ec="black",
        label="Planner full grid",
    )
    op_rect = plt.Rectangle(
        (planner_info["op_lon_min"], planner_info["op_lat_min"]),
        planner_info["op_lon_max"] - planner_info["op_lon_min"],
        planner_info["op_lat_max"] - planner_info["op_lat_min"],
        fill=False,
        lw=2.0,
        ls="--",
        ec="#008c6d",
        label="Planner operational ROI",
    )
    ax.add_patch(full_rect)
    ax.add_patch(op_rect)

    cand_rect = plt.Rectangle(
        (candidate["x0"], candidate["y0"]),
        candidate["x1"] - candidate["x0"],
        candidate["y1"] - candidate["y0"],
        fill=False,
        lw=2.3,
        ec="#d22c2c",
        label=f"{candidate['candidate_id']} transformed tempRes",
    )
    ax.add_patch(cand_rect)

    ax.set_xlabel("Longitude (deg)")
    ax.set_ylabel("Latitude (deg)")
    ax.set_title(title)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=8)

    note = []
    if "mask_iou" in candidate:
        note.append(f"mask_iou={candidate['mask_iou']:.6f}")
    if "pred_mean_corr" in candidate:
        note.append(f"pred_corr={candidate['pred_mean_corr']:.4f}")
    if "auv_mean_corr" in candidate:
        note.append(f"auv_corr={candidate['auv_mean_corr']:.4f}")
    if note:
        ax.text(0.01, 0.01, " | ".join(note), transform=ax.transAxes, fontsize=8, ha="left", va="bottom")

    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    ensure_parent(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    seen = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                fields.append(k)
                seen.add(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def summarize_candidate_for_md(cand: Dict[str, object]) -> str:
    cid = cand["candidate_id"]
    method = cand.get("method")
    frame = cand.get("frame")
    proof = cand.get("proof_status")
    if frame == "lon_lat":
        bbox_txt = f"lon[{cand['x0']:.6f},{cand['x1']:.6f}] lat[{cand['y0']:.6f},{cand['y1']:.6f}]"
    else:
        bbox_txt = f"x[{cand['x0']},{cand['x1']}] y[{cand['y0']},{cand['y1']}]"
    return f"- `{cid}`: method={method}; frame={frame}; {bbox_txt}; proof_status={proof}."


def decide_status(native_georef_proven: bool, candidates: List[Dict[str, object]]) -> str:
    if native_georef_proven:
        return "GEOREFERENCE RECOVERED"

    has_plausible = False
    for c in candidates:
        if c.get("frame") != "lon_lat":
            continue
        inside = c.get("inside_planner_full") is True
        ratio_x = c.get("resolution_ratio_x_vs_planner")
        ratio_y = c.get("resolution_ratio_y_vs_planner")
        ratio_ok = False
        if isinstance(ratio_x, (float, int)) and isinstance(ratio_y, (float, int)):
            ratio_ok = (0.75 <= float(ratio_x) <= 1.6) and (0.75 <= float(ratio_y) <= 1.6)
        corr_ok = (
            isinstance(c.get("pred_mean_corr"), (float, int))
            and isinstance(c.get("auv_mean_corr"), (float, int))
            and float(c["pred_mean_corr"]) >= 0.9
            and float(c["auv_mean_corr"]) >= 0.9
        )
        if inside and (ratio_ok or corr_ok):
            has_plausible = True
            break

    if has_plausible:
        return "TRANSFORMATION PLAUSIBLE BUT NOT PROVEN"
    return "NOT ENOUGH EVIDENCE"


def build_reports(
    temp_info: TempGridInfo,
    planner_info: Dict[str, object],
    hres_info: Dict[str, object],
    reg_info: Optional[Dict[str, object]],
    evidence_rows: List[Dict[str, object]],
    candidates: List[Dict[str, object]],
    status: str,
) -> Tuple[str, str]:
    final_sentence = (
        "A tempRes pode ser alinhada de forma plausivel com a grelha do planner, "
        "mas nao pode ser alinhada de forma auditavelmente provada com a evidencia atual."
        if status == "TRANSFORMATION PLAUSIBLE BUT NOT PROVEN"
        else "A tempRes nao pode ser alinhada de forma auditavel com a grelha do planner com base na evidencia atualmente disponivel."
        if status == "NOT ENOUGH EVIDENCE"
        else "A tempRes pode ser alinhada de forma auditavel com a grelha do planner com base na evidencia atualmente disponivel."
    )

    inv_rows = [r for r in evidence_rows if r.get("source_group") == "artifact_directory_inventory"]
    key_rows = [
        r
        for r in evidence_rows
        if isinstance(r.get("fact"), str)
        and (
            "linear_resample_from_hres_bbox" in r["fact"].lower()
            or "not independently verified" in r["fact"].lower()
            or "x,y,z,temp" in r["fact"].lower()
            or "inferred by registration" in r["fact"].lower()
        )
    ]
    key_rows = key_rows[:10]

    report_lines: List[str] = []
    report_lines.append("# tempRes Georeference Forensic Audit")
    report_lines.append("")
    report_lines.append(f"Generated at UTC: `{now_iso()}`")
    report_lines.append("")
    report_lines.append("## 1. Problema")
    report_lines.append(
        "Recuperar ou provar a georreferenciacao da grelha `tempIBHRes2024_1.gslib`, "
        "ou estabelecer transformacoes justificadas para a grelha oficial do planner."
    )
    report_lines.append("")
    report_lines.append("## 2. Evidencia encontrada no repositorio")
    report_lines.append(f"- Registos de evidencia indexados: **{len(evidence_rows)}**")
    report_lines.append(f"- Inventarios de artefactos analisados: **{len(inv_rows)}**")
    report_lines.append(
        "- Evidencia-chave observada: `tempIBHRes` nativo indexado (`x,y,z,temp`), "
        "mapping de display por bbox HRes, e registo quantitativo tempRes->HRes por busca controlada."
    )
    if key_rows:
        report_lines.append("- Trechos-chave:")
        for r in key_rows:
            line_str = f":{r['line']}" if r.get("line") is not None else ""
            report_lines.append(f"  - `{r['path']}{line_str}` -> {r['fact']}")
    report_lines.append("")

    report_lines.append("## 3. Artefactos relevantes localizados")
    for r in inv_rows:
        report_lines.append(f"- `{r['path']}`: {r['fact']}")
    report_lines.append("")

    report_lines.append("## 4. Hipoteses de georreferencia / transformacao")
    for c in candidates:
        report_lines.append(summarize_candidate_for_md(c))
    report_lines.append("")

    report_lines.append("## 5. Testes de alinhamento feitos")
    full_bbox = (
        planner_info["lon_min"],
        planner_info["lon_max"],
        planner_info["lat_min"],
        planner_info["lat_max"],
    )
    op_bbox = (
        planner_info["op_lon_min"],
        planner_info["op_lon_max"],
        planner_info["op_lat_min"],
        planner_info["op_lat_max"],
    )
    report_lines.append(
        f"- Planner full bbox: lon[{full_bbox[0]:.6f},{full_bbox[1]:.6f}] lat[{full_bbox[2]:.6f},{full_bbox[3]:.6f}]"
    )
    report_lines.append(
        f"- Planner ROI bbox: lon[{op_bbox[0]:.6f},{op_bbox[1]:.6f}] lat[{op_bbox[2]:.6f},{op_bbox[3]:.6f}]"
    )
    for c in candidates:
        if c.get("frame") != "lon_lat":
            report_lines.append(
                f"- `{c['candidate_id']}`: frame local_km; nao comparavel diretamente em lon/lat sem passo adicional de CRS."
            )
            continue
        report_lines.append(
            f"- `{c['candidate_id']}`: inside_full={c['inside_planner_full']}; "
            f"intersects_roi={c['intersects_operational_roi']}; "
            f"roi_iou={float(c['operational_iou_bbox']):.4f}; "
            f"roi_coverage={float(c['operational_coverage']):.4f}; "
            f"res_ratio_x={c['resolution_ratio_x_vs_planner']}; res_ratio_y={c['resolution_ratio_y_vs_planner']}"
        )
    report_lines.append(
        f"- Overlays gerados: `{rel(OUT_OVERLAY_1)}` e `{rel(OUT_OVERLAY_2)}`"
    )
    report_lines.append("")

    report_lines.append("## 6. Grau de confianca")
    report_lines.append("- Georreferencia nativa tempRes provada: **nao**.")
    report_lines.append(
        "- Mapeamento de display (bbox HRes -> tempRes): **sim, fortemente documentado** "
        "(codigo, manifests e relatorios)."
    )
    if reg_info is not None:
        report_lines.append(
            "- Transformacao por registo controlado: **forte para plausibilidade espacial**, "
            "mas explicitamente inferida (nao metadata nativa do GSLIB)."
        )
    report_lines.append(
        "- Coerencia espacial com planner: existe para hipoteses candidatas, mas a prova de origem geodesica nativa da tempRes continua ausente."
    )
    report_lines.append("")

    report_lines.append("## 7. Conclusao final")
    report_lines.append(f"`{status}`")
    report_lines.append("")
    report_lines.append(final_sentence)
    report_lines.append("")

    report_lines.append("## 8. Recomendacao para o passo seguinte")
    report_lines.append(
        "Adotar oficialmente a grelha do planner interface como referencia operacional, "
        "e transferir regimes/descriptors apenas com uma transformacao explicitamente etiquetada como inferida "
        "(nao como georreferencia nativa recuperada), preservando rastreabilidade dos artefactos usados."
    )
    report = "\n".join(report_lines) + "\n"

    summary_lines = [
        "# tempRes Georeference Summary",
        "",
        f"- status: `{status}`",
        f"- tempRes native grid: `{temp_info.nx} x {temp_info.ny} x {temp_info.nz}` with columns `{','.join(temp_info.columns)}`",
        (
            "- planner official grid: `results/planner_baseline_scenario_c4_predmodel/inputs/"
            "30-10-2024_predModel_1_planner_interface.nc`"
        ),
        (
            f"- planner resolution: dx={planner_info['dx_m']:.2f} m/cell, dy={planner_info['dy_m']:.2f} m/cell; "
            f"shape={planner_info['nx']}x{planner_info['ny']}"
        ),
        (
            f"- tempRes display-mapped resolution (HRes bbox assumption): "
            f"dx={((hres_info['lon_max']-hres_info['lon_min'])/(max(1,temp_info.nx-1))*km_per_degree(0.5*(hres_info['lat_min']+hres_info['lat_max']))[1]*1000):.2f} m/cell, "
            f"dy={((hres_info['lat_max']-hres_info['lat_min'])/(max(1,temp_info.ny-1))*km_per_degree(0.5*(hres_info['lat_min']+hres_info['lat_max']))[0]*1000):.2f} m/cell"
        ),
        "- georeference_native_proven: `false`",
        "- strongest_supported_mapping: `registration-derived tempRes -> HRes sub-area`",
        "- note: mapping is plausible and auditable as an inferred transform, not as recovered native CRS metadata.",
        "",
        final_sentence,
        "",
        "- generated_files:",
        f"  - `{rel(OUT_REPORT)}`",
        f"  - `{rel(OUT_SUMMARY)}`",
        f"  - `{rel(OUT_EVIDENCE_CSV)}`",
        f"  - `{rel(OUT_CANDIDATES_CSV)}`",
        f"  - `{rel(OUT_CHECKS_JSON)}`",
        f"  - `{rel(OUT_OVERLAY_1)}`",
        f"  - `{rel(OUT_OVERLAY_2)}`",
    ]
    summary = "\n".join(summary_lines) + "\n"
    return report, summary


def main() -> None:
    evidence_rows: List[Dict[str, object]] = []
    evidence_rows.extend(scan_artifact_dirs())

    text_files = collect_text_files()
    evidence_rows.extend(extract_keyword_rows(text_files))

    temp_info = parse_temp_gslib(TEMP_GSLIB)
    planner_info = parse_planner_grid(PLANNER_INTERFACE, CONFIG_FILE)
    hres_info = parse_hres_summary_row(NETCDF_SUMMARY)
    reg_info = parse_registration(planner_info, temp_info)
    rel_km = parse_relative_km_manifests()

    evidence_rows.append(
        {
            "evidence_id": "STR001",
            "path": rel(TEMP_GSLIB),
            "source_group": "structured_extraction",
            "evidence_type": "temp_gslib_shape",
            "fact": f"shape={temp_info.nx}x{temp_info.ny}x{temp_info.nz}; columns={temp_info.columns}; valid_fraction={temp_info.valid_fraction:.6f}",
            "confidence": "high",
        }
    )
    evidence_rows.append(
        {
            "evidence_id": "STR002",
            "path": rel(PLANNER_INTERFACE),
            "source_group": "structured_extraction",
            "evidence_type": "planner_grid",
            "fact": (
                f"shape={planner_info['nx']}x{planner_info['ny']}; bbox=lon[{planner_info['lon_min']:.6f},{planner_info['lon_max']:.6f}] "
                f"lat[{planner_info['lat_min']:.6f},{planner_info['lat_max']:.6f}]; dx={planner_info['dx_m']:.2f}m dy={planner_info['dy_m']:.2f}m"
            ),
            "confidence": "high",
        }
    )
    if reg_info is not None:
        evidence_rows.append(
            {
                "evidence_id": "STR003",
                "path": rel(REG_MANIFEST),
                "source_group": "structured_extraction",
                "evidence_type": "registration_best",
                "fact": (
                    f"x0={reg_info['x0']} x1={reg_info['x1']} y0={reg_info['y0']} y1={reg_info['y1']}; "
                    f"mask_iou={reg_info['mask_iou']:.6f}; pred_corr={reg_info['pred_mean_corr']:.6f}; auv_corr={reg_info['auv_mean_corr']:.6f}"
                ),
                "confidence": "high",
            }
        )

    candidates = build_candidates(temp_info, planner_info, hres_info, reg_info, rel_km)

    cand_lonlat = [c for c in candidates if c.get("frame") == "lon_lat"]
    if cand_lonlat:
        draw_overlay(
            planner_info=planner_info,
            candidate=cand_lonlat[0],
            out_png=OUT_OVERLAY_1,
            title=f"Candidate Overlay 1 - {cand_lonlat[0]['candidate_id']}",
        )
    if len(cand_lonlat) >= 2:
        draw_overlay(
            planner_info=planner_info,
            candidate=cand_lonlat[1],
            out_png=OUT_OVERLAY_2,
            title=f"Candidate Overlay 2 - {cand_lonlat[1]['candidate_id']}",
        )
    elif cand_lonlat:
        draw_overlay(
            planner_info=planner_info,
            candidate=cand_lonlat[0],
            out_png=OUT_OVERLAY_2,
            title=f"Candidate Overlay 2 - {cand_lonlat[0]['candidate_id']} (duplicate fallback)",
        )

    native_georef_proven = False
    status = decide_status(native_georef_proven=native_georef_proven, candidates=candidates)

    report_md, summary_md = build_reports(
        temp_info=temp_info,
        planner_info=planner_info,
        hres_info=hres_info,
        reg_info=reg_info,
        evidence_rows=evidence_rows,
        candidates=candidates,
        status=status,
    )

    checks = {
        "generated_at_utc": now_iso(),
        "inputs": {
            "temp_gslib": rel(TEMP_GSLIB),
            "planner_interface": rel(PLANNER_INTERFACE),
            "netcdf_summary": rel(NETCDF_SUMMARY),
            "registration_manifest": rel(REG_MANIFEST) if REG_MANIFEST.exists() else None,
        },
        "temp_grid": {
            "shape_xyz": [temp_info.nx, temp_info.ny, temp_info.nz],
            "columns": temp_info.columns,
            "bbox_index": {
                "x_min": temp_info.x_min,
                "x_max": temp_info.x_max,
                "y_min": temp_info.y_min,
                "y_max": temp_info.y_max,
                "z_min": temp_info.z_min,
                "z_max": temp_info.z_max,
            },
            "native_georef_proven": False,
        },
        "planner_grid": {
            "shape": [planner_info["nx"], planner_info["ny"]],
            "bbox_lon_lat": [planner_info["lon_min"], planner_info["lon_max"], planner_info["lat_min"], planner_info["lat_max"]],
            "resolution_m": [planner_info["dx_m"], planner_info["dy_m"]],
            "orientation": [planner_info["lon_orientation"], planner_info["lat_orientation"]],
            "op_bbox_lon_lat": [
                planner_info["op_lon_min"],
                planner_info["op_lon_max"],
                planner_info["op_lat_min"],
                planner_info["op_lat_max"],
            ],
        },
        "hres_reference_bbox": hres_info,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "evidence_index_rows": len(evidence_rows),
        "status": status,
        "final_sentence": (
            "A tempRes pode ser alinhada de forma auditavel com a grelha do planner com base na evidencia atualmente disponivel."
            if status == "GEOREFERENCE RECOVERED"
            else "A tempRes pode ser alinhada de forma plausivel com a grelha do planner, mas nao de forma auditavelmente provada com a evidencia atualmente disponivel."
            if status == "TRANSFORMATION PLAUSIBLE BUT NOT PROVEN"
            else "A tempRes nao pode ser alinhada de forma auditavel com a grelha do planner com base na evidencia atualmente disponivel."
        ),
        "official_planning_grid": rel(PLANNER_INTERFACE),
    }

    write_csv(OUT_EVIDENCE_CSV, evidence_rows)
    write_csv(OUT_CANDIDATES_CSV, candidates)
    ensure_parent(OUT_CHECKS_JSON)
    OUT_CHECKS_JSON.write_text(json.dumps(checks, indent=2), encoding="utf-8")
    ensure_parent(OUT_REPORT)
    OUT_REPORT.write_text(report_md, encoding="utf-8")
    ensure_parent(OUT_SUMMARY)
    OUT_SUMMARY.write_text(summary_md, encoding="utf-8")

    print("Generated:")
    print(rel(OUT_REPORT))
    print(rel(OUT_SUMMARY))
    print(rel(OUT_EVIDENCE_CSV))
    print(rel(OUT_CANDIDATES_CSV))
    print(rel(OUT_CHECKS_JSON))
    print(rel(OUT_OVERLAY_1))
    print(rel(OUT_OVERLAY_2))
    print(f"Status: {status}")


if __name__ == "__main__":
    main()

