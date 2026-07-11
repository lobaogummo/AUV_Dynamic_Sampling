#!/usr/bin/env python
"""
Step11Y audit and rebuild of prototype-based planner inputs.

This script checks whether planner maps used in Steps 10F/11A/11C/11D came
from Step08 prototype descriptors assigned by predicted class, or from direct
TEMPpred-derived proxies. It then rebuilds the corrected prototype-based maps
for the three planner cases without rerunning the planner or modifying previous
outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = ""

try:
    from scipy import ndimage as ndi
except Exception:  # pragma: no cover
    ndi = None


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

STEP05 = RESULTS / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260514_164854"
STEP09B = RESULTS / "fossum_roi_x490_step09b_top20_c01_c06_temppred_classification_20260519_190144"
STEP10E = RESULTS / "fossum_roi_x490_step10e_top20_class01_class06_roi_x490_20260519_184636"
STEP10F = RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"

STEP11C_OUTPUTS = [
    RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322",
    RESULTS / "fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458",
]
STEP11D_OUTPUTS = [
    RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809",
    RESULTS / "fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_132935",
]

CASE_ORDER = ["C01_representative", "C06_representative", "October_control"]
CASE_DISPLAY = {
    "C01_representative": "C01 representative",
    "C06_representative": "C06 representative",
    "October_control": "October reference",
}
EXPECTED_SHAPE = (72, 117)
BOUNDARY_DISTANCE_RADII_CELLS = [1, 2, 3, 5, 8]


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def require(path: Path, label: str, missing: list[str]) -> Path:
    if not path.exists():
        missing.append(f"{label}: {rel(path)}")
    return path


def latest_step08_dir() -> Path:
    candidates = sorted(
        RESULTS.glob("fossum_roi_x490_step08_final_descriptors_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else STEP08


def boundary_distance_output_key(step08_key: str) -> str:
    return step08_key if step08_key.endswith("_norm") else f"{step08_key}_norm"


def boundary_distance_keys(step08_npz: Any) -> list[str]:
    return sorted(str(key) for key in step08_npz.files if "boundary_distance" in str(key))


def minmax01(arr: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    valid = np.isfinite(a)
    if mask is not None:
        valid &= mask.astype(bool)
    out = np.full(a.shape, np.nan, dtype=np.float32)
    if not np.any(valid):
        return out
    mn = float(np.nanmin(a[valid]))
    mx = float(np.nanmax(a[valid]))
    if mx <= mn:
        out[valid] = 0.0
    else:
        out[valid] = (a[valid] - mn) / (mx - mn)
    return out


def finite_pair(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(a) & np.isfinite(b)
    if mask is not None:
        valid &= mask.astype(bool)
    return a[valid].astype(float), b[valid].astype(float)


def pearson(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None) -> float:
    x, y = finite_pair(a, b, mask)
    if x.size < 3 or np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def compare_arrays(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | bool]:
    x, y = finite_pair(a, b, mask)
    if x.size == 0:
        return {
            "rmse": float("nan"),
            "mae": float("nan"),
            "pearson": float("nan"),
            "max_abs_diff": float("nan"),
            "exact_match": False,
            "near_exact_match": False,
            "valid_cells_compared": 0,
        }
    diff = x - y
    max_abs = float(np.nanmax(np.abs(diff)))
    return {
        "rmse": float(np.sqrt(np.nanmean(diff**2))),
        "mae": float(np.nanmean(np.abs(diff))),
        "pearson": pearson(a, b, mask),
        "max_abs_diff": max_abs,
        "exact_match": bool(max_abs == 0.0),
        "near_exact_match": bool(max_abs <= 1e-6),
        "valid_cells_compared": int(x.size),
    }


def top_mask(arr: np.ndarray, mask: np.ndarray, q: float = 0.90) -> np.ndarray:
    valid = mask & np.isfinite(arr)
    out = np.zeros(arr.shape, dtype=bool)
    if not np.any(valid):
        return out
    thr = float(np.nanquantile(arr[valid], q))
    out[valid & (arr >= thr)] = True
    return out


def hotspot_centroid(arr: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    tm = top_mask(arr, mask)
    rr, cc = np.where(tm)
    if cc.size == 0:
        return float("nan"), float("nan")
    return float(np.mean(cc)), float(np.mean(rr))


def top10_jaccard(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    am = top_mask(a, mask)
    bm = top_mask(b, mask)
    union = int(np.sum(am | bm))
    if union == 0:
        return float("nan")
    return float(np.sum(am & bm) / union)


def hotspot_distance(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    ax, ay = hotspot_centroid(a, mask)
    bx, by = hotspot_centroid(b, mask)
    if not np.isfinite([ax, ay, bx, by]).all():
        return float("nan")
    return float(math.hypot(ax - bx, ay - by))


def compare_maps(case_id: str, map_name: str, old: np.ndarray, new: np.ndarray, mask: np.ndarray, source_old: str, source_new: str) -> dict[str, Any]:
    stats = compare_arrays(old, new, mask)
    return {
        "case_id": case_id,
        "map_name": map_name,
        "old_source": source_old,
        "prototype_source": source_new,
        **stats,
        "top10_jaccard": top10_jaccard(old, new, mask),
        "hotspot_distance_pixels": hotspot_distance(old, new, mask),
    }


def connected_largest(mask: np.ndarray) -> np.ndarray:
    if ndi is None or not np.any(mask):
        return mask.astype(bool)
    labels, count = ndi.label(mask)
    if count == 0:
        return mask.astype(bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def boundary_core(boundary: np.ndarray, mask: np.ndarray) -> np.ndarray:
    vals = boundary[mask & np.isfinite(boundary)]
    if vals.size == 0:
        return np.zeros(boundary.shape, dtype=bool)
    thr = float(np.nanpercentile(vals, 90))
    return connected_largest((boundary >= thr) & mask & np.isfinite(boundary))


def region_masks_from_cold_warm(cold: np.ndarray, warm: np.ndarray, mask: np.ndarray, normalize: bool = True) -> tuple[np.ndarray, np.ndarray]:
    coldn = minmax01(cold, mask) if normalize else np.asarray(cold, dtype=np.float32)
    warmn = minmax01(warm, mask) if normalize else np.asarray(warm, dtype=np.float32)
    region_a = (coldn >= warmn) & mask & np.isfinite(coldn) & np.isfinite(warmn)
    region_b = (warmn > coldn) & mask & np.isfinite(coldn) & np.isfinite(warmn)
    missing = mask & ~(region_a | region_b)
    # For degenerate descriptors, keep a full partition by assigning missing
    # cells to the locally stronger finite descriptor where possible.
    if np.any(missing):
        region_a |= missing & (np.nan_to_num(coldn, nan=-1) >= np.nan_to_num(warmn, nan=-1))
        region_b |= missing & ~region_a
    return region_a.astype(bool), region_b.astype(bool)


def original_step11_region_masks_for_case(
    case: pd.Series,
    case_idx: int,
    data: dict[str, Any],
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Recreate Step11C/11D source-region logic for lineage classification."""
    assignments = data["step09b_assignments"]
    maps = data["step09b_maps"]
    temp = np.asarray(data["step10f_npz"]["TEMPpred"][case_idx], dtype=np.float32)
    date = str(case["date"])
    matches = assignments.index[assignments["date"] == date].tolist()
    if matches:
        j = int(matches[0])
        cold = np.asarray(maps["cold_region"][j], dtype=np.float32)
        warm = np.asarray(maps["warm_region"][j], dtype=np.float32)
        region_a = (cold >= warm) & (cold > 0.0) & mask
        region_b = (warm > cold) & (warm > 0.0) & mask
        if int(region_a.sum()) < 10 or int(region_b.sum()) < 10:
            region_a = (cold >= warm) & mask
            region_b = (warm > cold) & mask
        source = "Step09B_assigned_Step08_cold_warm_raw"
    else:
        region_a, region_b = temp_median_masks(temp, mask)
        source = "TEMPpred_median_fallback"

    if np.any(region_a & region_b):
        region_b = region_b & ~region_a
    missing = mask & ~(region_a | region_b)
    if np.any(missing):
        temp_a, temp_b = temp_median_masks(temp, mask)
        region_a = region_a | (missing & temp_a)
        region_b = region_b | (missing & temp_b)
    return region_a.astype(bool), region_b.astype(bool), source


def temp_median_masks(temp: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valid = mask & np.isfinite(temp)
    thr = float(np.nanmedian(temp[valid])) if np.any(valid) else float("nan")
    return ((temp <= thr) & valid), ((temp > thr) & valid)


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 30, floatfmt: str = ".4f") -> str:
    if df.empty:
        return "_No data available._\n"
    d = df[[c for c in cols if c in df.columns]].head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_numeric_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else format(float(x), floatfmt))
        else:
            d[c] = d[c].fillna("").astype(str)
    headers = list(d.columns)
    lines = [
        "| " + " | ".join(h.replace("|", "\\|") for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in d.astype(str).values.tolist():
        lines.append("| " + " | ".join(v.replace("\n", " ").replace("|", "\\|") for v in row) + " |")
    return "\n".join(lines) + "\n"


def load_inputs(missing: list[str], step08_dir: Path, step10f_dir: Path) -> dict[str, Any]:
    cases_path = require(step10f_dir / "step10f_minimal_boundary_planner_cases.csv", "Step10F cases", missing)
    cases = pd.read_csv(cases_path)
    cases["date"] = pd.to_datetime(cases["date"]).dt.strftime("%Y-%m-%d")
    cases["case_id"] = cases["case_id"].replace({"October_control": "October_control"})
    cases["case_order"] = cases["case_id"].map({case: i for i, case in enumerate(CASE_ORDER)})
    cases = cases[cases["case_id"].isin(CASE_ORDER)].sort_values("case_order").reset_index(drop=True)

    step10f_npz = np.load(require(step10f_dir / "planner_minimal_boundary_input_maps.npz", "Step10F npz", missing), allow_pickle=True)
    step08_npz = np.load(require(step08_dir / "step08_all_descriptor_maps.npz", "Step08 descriptor maps", missing), allow_pickle=True)
    step09b_assignments = pd.read_csv(require(STEP09B / "step09b_classification_assignments.csv", "Step09B assignments", missing))
    step09b_assignments["date"] = pd.to_datetime(step09b_assignments["date"]).dt.strftime("%Y-%m-%d")
    step09b_maps = {
        "boundary": np.load(require(STEP09B / "step09b_assigned_descriptor_boundary_map.npy", "Step09B assigned boundary", missing)),
        "cold_region": np.load(require(STEP09B / "step09b_assigned_descriptor_cold_region_map.npy", "Step09B assigned cold", missing)),
        "warm_region": np.load(require(STEP09B / "step09b_assigned_descriptor_warm_region_map.npy", "Step09B assigned warm", missing)),
        "representative_zone": np.load(require(STEP09B / "step09b_assigned_descriptor_representative_zone_map.npy", "Step09B assigned representative", missing)),
        "interest": np.load(require(STEP09B / "step09b_assigned_descriptor_interest_map.npy", "Step09B assigned interest", missing)),
    }
    return {
        "cases": cases,
        "step10f_npz": step10f_npz,
        "step08_npz": step08_npz,
        "step08_dir": step08_dir,
        "step10f_dir": step10f_dir,
        "step09b_assignments": step09b_assignments,
        "step09b_maps": step09b_maps,
    }


def get_mask(step10f_npz: Any) -> np.ndarray:
    if "mask" in step10f_npz.files:
        return np.asarray(step10f_npz["mask"]).astype(bool)
    arr = np.asarray(step10f_npz["STD_norm"][0])
    return np.isfinite(arr)


def step08_descriptor(step08_npz: Any, descriptor: str, predicted_class: int, mask: np.ndarray) -> np.ndarray:
    key = "interest" if descriptor == "interest_map" else descriptor
    arr = np.asarray(step08_npz[key][predicted_class - 1], dtype=np.float32)
    return minmax01(arr, mask)


def optional_step08_descriptor(step08_npz: Any, descriptor: str, predicted_class: int, mask: np.ndarray) -> np.ndarray | None:
    key = "interest" if descriptor == "interest_map" else descriptor
    if key not in step08_npz.files:
        return None
    return step08_descriptor(step08_npz, descriptor, predicted_class, mask)


def rebuild_prototype_maps(data: dict[str, Any], missing: list[str]) -> tuple[dict[str, np.ndarray], pd.DataFrame, pd.DataFrame]:
    cases = data["cases"]
    z10 = data["step10f_npz"]
    z08 = data["step08_npz"]
    mask = get_mask(z10)

    std_stack = np.asarray(z10["STD_norm"], dtype=np.float32)
    temp_stack = np.asarray(z10["TEMPpred"], dtype=np.float32)
    boundary_step08_keys = boundary_distance_keys(z08)
    boundary_output_keys = [boundary_distance_output_key(key) for key in boundary_step08_keys]

    arrays: dict[str, list[np.ndarray]] = {
        "baseline_STD_norm": [],
        "boundary_score_norm": [],
        "gradient_norm": [],
        "heterogeneity_norm": [],
        "cold_region_norm": [],
        "warm_region_norm": [],
        "representative_zone_norm": [],
        "interest_map_norm": [],
        "enriched_boundary_alpha025": [],
        "enriched_boundary_alpha050": [],
        "AUV1_region_map": [],
        "AUV2_region_map": [],
    }
    for key in boundary_output_keys:
        arrays[key] = []
    lineage_rows: list[dict[str, Any]] = []

    for idx, row in cases.iterrows():
        case_id = str(row["case_id"])
        predicted_class = int(row["predicted_class"])
        std = minmax01(std_stack[idx], mask)
        temp = temp_stack[idx]
        descriptors = {
            "boundary_score": step08_descriptor(z08, "boundary", predicted_class, mask),
            "gradient": step08_descriptor(z08, "gradient", predicted_class, mask),
            "heterogeneity": step08_descriptor(z08, "heterogeneity", predicted_class, mask),
            "cold_region": step08_descriptor(z08, "cold_region", predicted_class, mask),
            "warm_region": step08_descriptor(z08, "warm_region", predicted_class, mask),
            "representative_zone": step08_descriptor(z08, "representative_zone", predicted_class, mask),
            "interest_map": step08_descriptor(z08, "interest_map", predicted_class, mask),
        }
        boundary_distance_descriptors: dict[str, np.ndarray] = {}
        for step08_key, output_key in zip(boundary_step08_keys, boundary_output_keys):
            desc = optional_step08_descriptor(z08, step08_key, predicted_class, mask)
            if desc is not None:
                boundary_distance_descriptors[output_key] = desc
        a_region, b_region = region_masks_from_cold_warm(descriptors["cold_region"], descriptors["warm_region"], mask)
        region_a_reward = minmax01(a_region.astype(np.float32), mask)
        region_b_reward = minmax01(b_region.astype(np.float32), mask)

        arrays["baseline_STD_norm"].append(std)
        arrays["boundary_score_norm"].append(descriptors["boundary_score"])
        arrays["gradient_norm"].append(descriptors["gradient"])
        arrays["heterogeneity_norm"].append(descriptors["heterogeneity"])
        arrays["cold_region_norm"].append(descriptors["cold_region"])
        arrays["warm_region_norm"].append(descriptors["warm_region"])
        arrays["representative_zone_norm"].append(descriptors["representative_zone"])
        arrays["interest_map_norm"].append(descriptors["interest_map"])
        arrays["enriched_boundary_alpha025"].append((0.75 * std + 0.25 * descriptors["boundary_score"]).astype(np.float32))
        arrays["enriched_boundary_alpha050"].append((0.50 * std + 0.50 * descriptors["boundary_score"]).astype(np.float32))
        arrays["AUV1_region_map"].append((0.60 * std + 0.40 * region_a_reward).astype(np.float32))
        arrays["AUV2_region_map"].append((0.60 * std + 0.40 * region_b_reward).astype(np.float32))
        for output_key in boundary_output_keys:
            if output_key in boundary_distance_descriptors:
                arrays[output_key].append(boundary_distance_descriptors[output_key])

        temp_a, temp_b = temp_median_masks(temp, mask)
        lineage_rows.append(
            {
                "case_id": case_id,
                "display_case": CASE_DISPLAY.get(case_id, case_id),
                "date": row["date"],
                "predicted_class": predicted_class,
                "predicted_class_label": row.get("predicted_class_label", f"C{predicted_class:02d}"),
                "correct_descriptor_source": "Step08 prototype descriptor map indexed by predicted_class",
                "prototype_region_A_definition": "cold_region >= warm_region from Step08 predicted-class prototype",
                "prototype_region_B_definition": "warm_region > cold_region from Step08 predicted-class prototype",
                "prototype_region_A_cells": int(np.sum(a_region)),
                "prototype_region_B_cells": int(np.sum(b_region)),
                "TEMPpred_median_region_A_cells": int(np.sum(temp_a)),
                "TEMPpred_median_region_B_cells": int(np.sum(temp_b)),
                "boundary_distance_descriptors_available": bool(boundary_step08_keys),
                "boundary_distance_step08_keys_found": "|".join(boundary_step08_keys),
                "boundary_distance_step11y_keys_written": "|".join(boundary_output_keys),
            }
        )

    stacked = {k: np.stack(v).astype(np.float32) for k, v in arrays.items() if v}
    lineage = pd.DataFrame(lineage_rows)
    return stacked, lineage, cases


def audit_step10f(data: dict[str, Any], corrected: dict[str, np.ndarray]) -> pd.DataFrame:
    z10 = data["step10f_npz"]
    cases = data["cases"]
    mask = get_mask(z10)
    rows: list[dict[str, Any]] = []
    old_map_pairs = {
        "baseline_STD_norm": np.asarray(z10["baseline_STD_norm"], dtype=np.float32),
        "boundary_score_norm": np.asarray(z10["boundary_score_norm"], dtype=np.float32),
        "enriched_boundary_alpha025": np.asarray(z10["enriched_boundary_alpha025"], dtype=np.float32),
        "enriched_boundary_alpha050": np.asarray(z10["enriched_boundary_alpha050"], dtype=np.float32),
    }
    for idx, case in cases.iterrows():
        case_id = str(case["case_id"])
        for name, old_stack in old_map_pairs.items():
            rows.append(
                {
                    "audit_step": "Step10F",
                    "inference": "prototype_based" if name != "baseline_STD_norm" else "day_STD_baseline",
                    **compare_maps(
                        case_id,
                        name,
                        old_stack[idx],
                        corrected[name][idx],
                        mask,
                        f"Step10F {name}",
                        "rebuilt Step08 predicted-class prototype + day STD",
                    ),
                }
            )
    return pd.DataFrame(rows)


def find_case_mask(output: Path, case_id: str, kind: str) -> Path | None:
    candidates = [output / "masks" / f"{case_id}_{kind}.npy"]
    if kind == "region_A_mask":
        candidates += [output / "masks" / f"{case_id}_regime_A_mask.npy"]
    if kind == "region_B_mask":
        candidates += [output / "masks" / f"{case_id}_regime_B_mask.npy"]
    # Top-level files in the original scripts are diagnostic copies for the
    # first/primary case only; avoid attributing them to every case in an output.
    if case_id == "C01_representative":
        candidates += [output / f"{kind}.npy"]
        if kind == "region_A_mask":
            candidates += [output / "step11d_regime_A_mask.npy"]
        if kind == "region_B_mask":
            candidates += [output / "step11d_regime_B_mask.npy"]
        if kind == "boundary_core_mask":
            candidates += [output / "step11d_boundary_core_mask.npy"]
    for p in candidates:
        if p.exists():
            return p
    return None


def audit_region_outputs(
    outputs: list[Path],
    data: dict[str, Any],
    corrected: dict[str, np.ndarray],
    step_name: str,
) -> pd.DataFrame:
    z10 = data["step10f_npz"]
    cases = data["cases"]
    mask = get_mask(z10)
    rows: list[dict[str, Any]] = []
    for output in outputs:
        if not output.exists():
            rows.append({"audit_step": step_name, "source_output": rel(output), "case_id": "", "map_name": "missing_output"})
            continue
        for idx, case in cases.iterrows():
            case_id = str(case["case_id"])
            proto_a, proto_b = region_masks_from_cold_warm(corrected["cold_region_norm"][idx], corrected["warm_region_norm"][idx], mask)
            proto_core = boundary_core(corrected["boundary_score_norm"][idx], mask)
            temp_a, temp_b = temp_median_masks(np.asarray(z10["TEMPpred"][idx], dtype=np.float32), mask)
            original_a, original_b, original_source = original_step11_region_masks_for_case(case, idx, data, mask)
            for kind, proto, temp_proxy in [
                ("region_A_mask", proto_a.astype(np.float32), temp_a.astype(np.float32)),
                ("region_B_mask", proto_b.astype(np.float32), temp_b.astype(np.float32)),
                ("boundary_core_mask", proto_core.astype(np.float32), proto_core.astype(np.float32)),
            ]:
                path = find_case_mask(output, case_id, kind)
                if path is None:
                    continue
                old = np.load(path).astype(np.float32)
                proto_stats = compare_maps(case_id, kind, old, proto, mask, rel(path), "prototype-derived mask")
                temp_stats = compare_arrays(old, temp_proxy, mask)
                if kind == "region_A_mask":
                    source_stats = compare_arrays(old, original_a.astype(np.float32), mask)
                elif kind == "region_B_mask":
                    source_stats = compare_arrays(old, original_b.astype(np.float32), mask)
                else:
                    source_stats = compare_arrays(old, proto_core.astype(np.float32), mask)
                row = {
                    "audit_step": step_name,
                    "source_output": output.name,
                    **proto_stats,
                    "mae_vs_TEMPpred_median_proxy": temp_stats["mae"],
                    "max_abs_diff_vs_TEMPpred_median_proxy": temp_stats["max_abs_diff"],
                    "near_exact_vs_TEMPpred_median_proxy": temp_stats["near_exact_match"],
                    "original_step11_source": original_source if kind in ["region_A_mask", "region_B_mask"] else "Step10F_boundary_p90_core",
                    "near_exact_vs_original_step11_logic": source_stats["near_exact_match"],
                }
                if kind in ["region_A_mask", "region_B_mask"]:
                    if bool(source_stats["near_exact_match"]) and original_source.startswith("Step09B"):
                        row["inference"] = "prototype_region_based_raw_Step09B"
                    elif bool(source_stats["near_exact_match"]) and original_source == "TEMPpred_median_fallback":
                        row["inference"] = "TEMPpred_median_fallback"
                    elif bool(proto_stats["near_exact_match"]):
                        row["inference"] = "prototype_region_based_normalized"
                    else:
                        row["inference"] = "mixed_or_postprocessed"
                else:
                    row["inference"] = "prototype_boundary_core" if bool(proto_stats["near_exact_match"]) else "boundary_core_mismatch"
                rows.append(row)

        if step_name == "Step11D":
            proto_a0, proto_b0 = region_masks_from_cold_warm(corrected["cold_region_norm"][0], corrected["warm_region_norm"][0], mask)
            reward_targets = {
                "step11d_region_A_reward.npy": minmax01(proto_a0.astype(np.float32), mask),
                "step11d_region_B_reward.npy": minmax01(proto_b0.astype(np.float32), mask),
            }
            for reward_name, target in reward_targets.items():
                p = output / reward_name
                if p.exists():
                    old = np.load(p).astype(np.float32)
                    rows.append(
                        {
                            "audit_step": "Step11D",
                            "source_output": output.name,
                            "inference": "top_level_C01_reward_file",
                            **compare_maps(
                                "C01_representative",
                                reward_name,
                                old,
                                target,
                                mask,
                                rel(p),
                                "corrected prototype region reward",
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def audit_step09b_assigned_vs_step08(data: dict[str, Any], corrected: dict[str, np.ndarray]) -> pd.DataFrame:
    cases = data["cases"]
    assignments = data["step09b_assignments"]
    maps = data["step09b_maps"]
    mask = get_mask(data["step10f_npz"])
    rows: list[dict[str, Any]] = []
    for idx, case in cases.iterrows():
        date = str(case["date"])
        case_id = str(case["case_id"])
        matches = assignments.index[assignments["date"] == date].tolist()
        if not matches:
            rows.append(
                {
                    "case_id": case_id,
                    "date": date,
                    "step09b_assignment_found": False,
                    "inference": "Step09B_missing_for_case",
                }
            )
            continue
        j = int(matches[0])
        for desc, corrected_name in [
            ("boundary", "boundary_score_norm"),
            ("cold_region", "cold_region_norm"),
            ("warm_region", "warm_region_norm"),
            ("representative_zone", "representative_zone_norm"),
            ("interest", "interest_map_norm"),
        ]:
            rows.append(
                {
                    "case_id": case_id,
                    "date": date,
                    "descriptor": desc,
                    "step09b_assignment_found": True,
                    "inference": "Step09B_assigned_descriptor_matches_Step08" ,
                    **compare_arrays(minmax01(maps[desc][j], mask), corrected[corrected_name][idx], mask),
                }
            )
    return pd.DataFrame(rows)


def save_arrays(outdir: Path, corrected: dict[str, np.ndarray], cases: pd.DataFrame) -> None:
    np.save(outdir / "prototype_based_baseline_STD_norm.npy", corrected["baseline_STD_norm"])
    np.save(outdir / "prototype_based_boundary_score_norm.npy", corrected["boundary_score_norm"])
    np.save(outdir / "prototype_based_gradient_norm.npy", corrected["gradient_norm"])
    np.save(outdir / "prototype_based_heterogeneity_norm.npy", corrected["heterogeneity_norm"])
    np.save(outdir / "prototype_based_cold_region_norm.npy", corrected["cold_region_norm"])
    np.save(outdir / "prototype_based_warm_region_norm.npy", corrected["warm_region_norm"])
    np.save(outdir / "prototype_based_representative_zone_norm.npy", corrected["representative_zone_norm"])
    np.save(outdir / "prototype_based_interest_map_norm.npy", corrected["interest_map_norm"])
    np.save(outdir / "prototype_based_enriched_boundary_alpha025.npy", corrected["enriched_boundary_alpha025"])
    np.save(outdir / "prototype_based_enriched_boundary_alpha050.npy", corrected["enriched_boundary_alpha050"])
    np.save(outdir / "prototype_based_AUV1_region_map.npy", corrected["AUV1_region_map"])
    np.save(outdir / "prototype_based_AUV2_region_map.npy", corrected["AUV2_region_map"])
    boundary_output_keys = sorted(key for key in corrected if "boundary_distance" in key)
    for key in boundary_output_keys:
        if key in corrected:
            np.save(outdir / f"prototype_based_{key}.npy", corrected[key])
    optional_npz_arrays = {key: corrected[key] for key in boundary_output_keys}
    np.savez_compressed(
        outdir / "prototype_based_all_planner_maps.npz",
        case_ids=cases["case_id"].astype(str).to_numpy(),
        dates=cases["date"].astype(str).to_numpy(),
        predicted_classes=cases["predicted_class"].astype(int).to_numpy(),
        baseline_STD_norm=corrected["baseline_STD_norm"],
        boundary_score_norm=corrected["boundary_score_norm"],
        gradient_norm=corrected["gradient_norm"],
        heterogeneity_norm=corrected["heterogeneity_norm"],
        cold_region_norm=corrected["cold_region_norm"],
        warm_region_norm=corrected["warm_region_norm"],
        representative_zone_norm=corrected["representative_zone_norm"],
        interest_map_norm=corrected["interest_map_norm"],
        enriched_boundary_alpha025=corrected["enriched_boundary_alpha025"],
        enriched_boundary_alpha050=corrected["enriched_boundary_alpha050"],
        AUV1_region_map=corrected["AUV1_region_map"],
        AUV2_region_map=corrected["AUV2_region_map"],
        **optional_npz_arrays,
    )


def plot_maps_panel(out: Path, corrected: dict[str, np.ndarray], cases: pd.DataFrame) -> None:
    if plt is None:
        return
    cols = [
        ("baseline_STD_norm", "STD"),
        ("boundary_score_norm", "Boundary"),
        ("boundary_distance_score_r3_cells_norm", "Dist r3"),
        ("interest_map_norm", "Interest"),
        ("cold_region_norm", "Cold/A"),
        ("warm_region_norm", "Warm/B"),
        ("AUV1_region_map", "AUV1"),
        ("AUV2_region_map", "AUV2"),
    ]
    cols = [(key, title) for key, title in cols if key in corrected]
    fig, axes = plt.subplots(len(cases), len(cols), figsize=(15, 8))
    for r, case in cases.iterrows():
        for c, (key, title) in enumerate(cols):
            ax = axes[r, c]
            im = ax.imshow(corrected[key][r], origin="lower", cmap="viridis", vmin=0, vmax=1, aspect="auto")
            ax.set_xticks([])
            ax.set_yticks([])
            if r == 0:
                ax.set_title(title)
            if c == 0:
                ax.set_ylabel(str(case["case_id"]), fontsize=8)
    fig.suptitle("Prototype-based planner maps")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_old_vs_prototype_boundary(out: Path, data: dict[str, Any], corrected: dict[str, np.ndarray], cases: pd.DataFrame) -> None:
    if plt is None:
        return
    old = np.asarray(data["step10f_npz"]["boundary_score_norm"], dtype=np.float32)
    fig, axes = plt.subplots(len(cases), 3, figsize=(9, 8))
    for r, case in cases.iterrows():
        diff = old[r] - corrected["boundary_score_norm"][r]
        for c, (arr, title, cmap, vmin, vmax) in enumerate(
            [
                (old[r], "Old Step10F", "magma", 0, 1),
                (corrected["boundary_score_norm"][r], "Prototype", "magma", 0, 1),
                (diff, "Old - prototype", "coolwarm", -1, 1),
            ]
        ):
            ax = axes[r, c]
            ax.imshow(arr, origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
            ax.set_xticks([])
            ax.set_yticks([])
            if r == 0:
                ax.set_title(title)
            if c == 0:
                ax.set_ylabel(str(case["case_id"]), fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_region_comparison(out: Path, data: dict[str, Any], corrected: dict[str, np.ndarray], cases: pd.DataFrame) -> None:
    if plt is None:
        return
    mask = get_mask(data["step10f_npz"])
    temp = np.asarray(data["step10f_npz"]["TEMPpred"], dtype=np.float32)
    fig, axes = plt.subplots(len(cases), 4, figsize=(12, 8))
    for r, case in cases.iterrows():
        proto_a, proto_b = region_masks_from_cold_warm(corrected["cold_region_norm"][r], corrected["warm_region_norm"][r], mask)
        temp_a, temp_b = temp_median_masks(temp[r], mask)
        panels = [
            (proto_a, "Prototype A"),
            (proto_b, "Prototype B"),
            (temp_a, "TEMPpred median A"),
            (temp_b, "TEMPpred median B"),
        ]
        for c, (arr, title) in enumerate(panels):
            ax = axes[r, c]
            ax.imshow(arr.astype(float), origin="lower", aspect="auto", cmap="gray", vmin=0, vmax=1)
            ax.set_xticks([])
            ax.set_yticks([])
            if r == 0:
                ax.set_title(title)
            if c == 0:
                ax.set_ylabel(str(case["case_id"]), fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_logic_diagram(out: Path) -> None:
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(13.5, 4.6))
    ax.axis("off")
    boxes = [
        (0.03, 0.58, 0.17, 0.22, "Planning day\nTEMPpred + STD", "#e7f0fa"),
        (0.25, 0.58, 0.17, 0.22, "Classify TEMPpred\nwith Step05 model", "#fff4dc"),
        (0.47, 0.58, 0.16, 0.22, "Assigned class\nC01 / C06 / C02", "#fff4dc"),
        (0.68, 0.58, 0.22, 0.22, "Retrieve Step08\nprototype descriptors", "#e8f4e8"),
        (0.43, 0.16, 0.25, 0.26, "Reward maps\nSTD + descriptors", "#f0f2fb"),
        (0.76, 0.15, 0.18, 0.26, "Lucrezia planner\ntrajectories", "#f8eaf0"),
    ]
    for x, y, w, h, text, face in boxes:
        rect = plt.Rectangle((x, y), w, h, facecolor=face, edgecolor="#39516a", linewidth=1.6)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10, weight="bold")
    arrows = [
        ((0.20, 0.69), (0.25, 0.69)),
        ((0.42, 0.69), (0.47, 0.69)),
        ((0.63, 0.69), (0.68, 0.69)),
        ((0.79, 0.58), (0.58, 0.42)),
        ((0.12, 0.58), (0.43, 0.29)),
        ((0.68, 0.29), (0.76, 0.29)),
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.5})
    ax.text(0.18, 0.36, "STD remains\nday-specific", ha="center", fontsize=9, color="#444444")
    ax.text(0.74, 0.43, "Descriptors remain\nprototype-based", ha="center", fontsize=9, color="#444444")
    ax.text(
        0.50,
        0.04,
        "TEMPpred selects the class; STD remains date-specific; descriptors are loaded from the assigned prototype.",
        ha="center",
        fontsize=9,
        color="#444444",
    )
    ax.set_title("Step11Y audited planner-input logic", fontsize=16, weight="bold", pad=8)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def decide_verdict(step10f_cmp: pd.DataFrame, region_cmp: pd.DataFrame) -> tuple[str, list[str]]:
    rerun_cases: set[str] = set()
    step10f_boundary = step10f_cmp[(step10f_cmp["map_name"] == "boundary_score_norm")]
    step10f_ok = bool((step10f_boundary["near_exact_match"] == True).all()) if not step10f_boundary.empty else False

    problematic = region_cmp[
        region_cmp["map_name"].isin(["region_A_mask", "region_B_mask"])
        & (region_cmp["inference"].astype(str) == "TEMPpred_median_fallback")
    ]
    for case_id in problematic["case_id"].dropna().astype(str):
        if case_id:
            rerun_cases.add(case_id)

    if not step10f_ok and len(rerun_cases) == 0:
        rerun_cases.update(CASE_ORDER)
        return "PROTOTYPE_BASED_INPUTS_REBUILT_RERUN_RECOMMENDED", sorted(rerun_cases)
    if step10f_ok and len(rerun_cases) == 0:
        return "PREVIOUS_PLANNER_INPUTS_ALREADY_PROTOTYPE_BASED", []
    return "MIXED_INPUTS_PARTIAL_RERUN_RECOMMENDED", sorted(rerun_cases)


def make_reports(
    outdir: Path,
    cases: pd.DataFrame,
    step10f_cmp: pd.DataFrame,
    step09b_cmp: pd.DataFrame,
    region_cmp: pd.DataFrame,
    old_vs_new: pd.DataFrame,
    lineage: pd.DataFrame,
    verdict: str,
    rerun_cases: list[str],
    checks: dict[str, Any],
) -> None:
    temp_fallback = region_cmp[region_cmp["inference"].astype(str).eq("TEMPpred_median_fallback")]
    step10f_boundary_ok = step10f_cmp[
        (step10f_cmp["map_name"] == "boundary_score_norm") & (step10f_cmp["near_exact_match"] == True)
    ]["case_id"].astype(str).tolist()
    prototype_cases = sorted(set(step10f_boundary_ok))
    fallback_cases = sorted(set(temp_fallback["case_id"].dropna().astype(str).tolist()))
    boundary_lineage = lineage[["boundary_distance_step08_keys_found", "boundary_distance_step11y_keys_written"]].head(1) if "boundary_distance_step08_keys_found" in lineage.columns else pd.DataFrame()

    summary_lines = [
        "# Step11Y prototype-based planner input audit",
        "",
        f"- Verdict: `{verdict}`",
        f"- Planner rerun performed: `{checks['planner_rerun']}`",
        f"- Corrected arrays created: `{checks['corrected_arrays_created']}`",
        f"- Boundary-distance descriptors available: `{checks['boundary_distance_descriptors_available']}`",
        f"- Step10F boundary maps matching Step08 prototypes: {len(prototype_cases)}/{len(cases)} cases",
        f"- Cases with TEMPpred-derived region fallback in Step11C/11D evidence: {', '.join(fallback_cases) if fallback_cases else 'none'}",
        "",
        "## Direct answers",
        "",
        "1. Previous Step10F boundary inputs used Step08 prototype descriptors by predicted class.",
        "2. TEMPpred-derived maps appear in the Step11C/Step11D region fallback path where Step09B assigned region maps are unavailable.",
        f"3. Correct Step10F cases: {', '.join(prototype_cases) if prototype_cases else 'none confirmed'}.",
        f"4. Cases needing rerun: {', '.join(rerun_cases) if rerun_cases else 'none required by this audit'}.",
        f"5. October fallback issue: {'yes' if 'October_control' in fallback_cases else 'no'}." ,
        "6. Use the new `prototype_based_*` arrays from this Step11Y output going forward.",
        "7. Next step: rerun the minimal affected planner tests with prototype-based regions/maps if the verdict recommends it.",
        "8. If Step08 was rebuilt with explicit boundary-distance maps, Step11Y also exports normalized `boundary_distance_score_r*_cells_norm` maps for Step12A.",
        "",
        "## Step10F boundary comparison",
        md_table(step10f_cmp[step10f_cmp["map_name"].eq("boundary_score_norm")], ["case_id", "map_name", "rmse", "mae", "pearson", "max_abs_diff", "near_exact_match"], 10),
        "",
        "## Region-mask lineage evidence",
        md_table(region_cmp, ["audit_step", "source_output", "case_id", "map_name", "inference", "mae", "max_abs_diff", "near_exact_vs_TEMPpred_median_proxy"], 80),
        "",
        "## Boundary-distance descriptor propagation",
        "",
        f"- Step08 directory used: `{checks.get('step08_dir_used', '')}`",
        f"- Step08 keys found: `{', '.join(checks.get('boundary_distance_step08_keys_found', [])) if checks.get('boundary_distance_step08_keys_found') else 'none'}`",
        f"- Step11Y keys written: `{', '.join(checks.get('boundary_distance_output_keys', [])) if checks.get('boundary_distance_output_keys') else 'none'}`",
        "",
        md_table(boundary_lineage, ["boundary_distance_step08_keys_found", "boundary_distance_step11y_keys_written"], 1),
    ]
    summary = "\n".join(summary_lines)
    write_text(outdir / "step11y_summary.md", summary)

    full = "\n\n".join(
        [
            summary,
            "# Case lineage\n" + md_table(lineage, list(lineage.columns), 20),
            "# Step09B assigned descriptors vs Step08 prototypes\n" + md_table(step09b_cmp, ["case_id", "descriptor", "step09b_assignment_found", "rmse", "max_abs_diff", "near_exact_match", "inference"], 80),
            "# Old vs prototype maps\n" + md_table(old_vs_new, ["audit_step", "source_output", "case_id", "map_name", "inference", "rmse", "mae", "pearson", "top10_jaccard", "hotspot_distance_pixels"], 120),
        ]
    )
    write_text(outdir / "step11y_full_report.md", full)

    rerun = [
        "# Step11Y rerun recommendation",
        "",
        f"Verdict: `{verdict}`",
        "",
    ]
    if rerun_cases:
        rerun += [
            "Rerun recommended because some region/crossing or vehicle-specific maps were derived through a TEMPpred fallback rather than the Step08 prototype descriptors assigned by predicted class.",
            "",
            "## Minimal sequence",
            "",
            "A. Single-AUV:",
            "- 2024-08-24, 12h",
            "- baseline_STD",
            "- prototype_boundary_alpha050",
            "- crossing_gamma025 using prototype regions",
            "",
            "B. Multi-AUV:",
            "- 2024-08-24, 2 AUVs, 12h",
            "- baseline_STD",
            "- prototype_vehicle_specific_maps",
            "",
            "C. Repeat after C01 for:",
            "- 2023-12-22",
            "- 2024-10-30",
        ]
    else:
        rerun += [
            "No rerun is required by the map lineage audit. Existing planner inputs are consistent with prototype-based descriptors.",
            "",
            "Still use the Step11Y arrays for future reproducibility because they make the intended lineage explicit.",
        ]
    write_text(outdir / "step11y_rerun_recommendation.md", "\n".join(rerun))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step11Y audit and rebuild of prototype-based planner inputs.")
    parser.add_argument(
        "--step08-dir",
        type=Path,
        default=None,
        help="Step08 descriptor output directory to use. Defaults to the latest fossum_roi_x490_step08_final_descriptors_* directory.",
    )
    parser.add_argument(
        "--step10f-dir",
        type=Path,
        default=STEP10F,
        help="Step10F minimal planner-input directory to audit. Defaults to the original Step10F output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    step08_dir = (args.step08_dir or latest_step08_dir()).resolve()
    step10f_dir = args.step10f_dir.resolve()
    outdir = RESULTS / f"fossum_roi_x490_step11y_prototype_based_planner_input_audit_{now_stamp()}"
    outdir.mkdir(parents=True, exist_ok=False)
    figdir = outdir / "figures"
    figdir.mkdir()

    missing: list[str] = []
    warnings: list[str] = []
    data = load_inputs(missing, step08_dir, step10f_dir)
    corrected, lineage, cases = rebuild_prototype_maps(data, missing)
    boundary_step08_keys_found = boundary_distance_keys(data["step08_npz"])
    boundary_output_keys = sorted(key for key in corrected if "boundary_distance" in key)
    if not boundary_step08_keys_found:
        warnings.append(f"No boundary_distance maps found in Step08 descriptor NPZ: {rel(step08_dir / 'step08_all_descriptor_maps.npz')}")
    save_arrays(outdir, corrected, cases)

    step10f_cmp = audit_step10f(data, corrected)
    step09b_cmp = audit_step09b_assigned_vs_step08(data, corrected)
    step11c_cmp = audit_region_outputs(STEP11C_OUTPUTS, data, corrected, "Step11C")
    step11d_cmp = audit_region_outputs(STEP11D_OUTPUTS, data, corrected, "Step11D")
    region_cmp = pd.concat([step11c_cmp, step11d_cmp], ignore_index=True)
    old_vs_new = pd.concat([step10f_cmp, region_cmp], ignore_index=True, sort=False)

    verdict, rerun_cases = decide_verdict(step10f_cmp, region_cmp)
    if missing:
        verdict = "AUDIT_FAILED_NEEDS_MANUAL_REVIEW"

    step10f_cmp.to_csv(outdir / "step11y_step10f_boundary_prototype_audit.csv", index=False)
    step09b_cmp.to_csv(outdir / "step11y_step09b_assigned_vs_step08_audit.csv", index=False)
    region_cmp.to_csv(outdir / "step11y_step11c_step11d_region_lineage_audit.csv", index=False)
    old_vs_new.to_csv(outdir / "step11y_old_vs_prototype_maps_comparison.csv", index=False)
    lineage.to_csv(outdir / "step11y_case_lineage.csv", index=False)

    if plt is None:
        warnings.append(f"Matplotlib unavailable: {MATPLOTLIB_ERROR}")
    else:
        plot_maps_panel(figdir / "step11y_prototype_based_maps_panel.png", corrected, cases)
        plot_old_vs_prototype_boundary(figdir / "step11y_old_vs_prototype_boundary_comparison.png", data, corrected, cases)
        plot_region_comparison(figdir / "step11y_old_vs_prototype_region_maps_comparison.png", data, corrected, cases)
        plot_logic_diagram(figdir / "step11y_planner_input_logic_diagram.png")

    checks = {
        "audit_created": True,
        "output_dir": rel(outdir),
        "planner_rerun": False,
        "existing_outputs_modified": False,
        "new_trajectories_generated": False,
        "corrected_arrays_created": True,
        "case_count": int(len(cases)),
        "map_shape": list(corrected["baseline_STD_norm"].shape),
        "step08_dir_used": rel(step08_dir),
        "step10f_dir_used": rel(step10f_dir),
        "boundary_distance_descriptors_available": bool(boundary_step08_keys_found and boundary_output_keys),
        "boundary_distance_step08_keys_found": boundary_step08_keys_found,
        "boundary_distance_output_keys": boundary_output_keys,
        "step10f_boundary_near_exact_cases": int(
            step10f_cmp[(step10f_cmp["map_name"] == "boundary_score_norm") & (step10f_cmp["near_exact_match"] == True)].shape[0]
        ),
        "region_fallback_rows": int(region_cmp[region_cmp["inference"].astype(str).eq("TEMPpred_median_fallback")].shape[0]),
        "rerun_cases": rerun_cases,
        "figures_created": len(list(figdir.glob("*.png"))),
        "missing_inputs_count": len(missing),
        "warnings_count": len(warnings),
        "verdict": verdict,
    }
    metadata = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": rel(Path(__file__)),
        "inputs": {
            "step05": rel(STEP05),
            "step08": rel(step08_dir),
            "step09b": rel(STEP09B),
            "step10e": rel(STEP10E),
            "step10f": rel(step10f_dir),
            "step11c_outputs": [rel(p) for p in STEP11C_OUTPUTS],
            "step11d_outputs": [rel(p) for p in STEP11D_OUTPUTS],
        },
        "missing": missing,
        "warnings": warnings,
        "correct_logic": {
            "TEMPpred": "classification only",
            "STD": "day-specific uncertainty for baseline and blends",
            "descriptors": "Step08 prototype descriptor maps indexed by predicted class",
            "boundary_distance_descriptors": "optional Step08 pure distance/proximity maps, min-max normalized by predicted class when available",
        },
    }
    make_reports(outdir, cases, step10f_cmp, step09b_cmp, region_cmp, old_vs_new, lineage, verdict, rerun_cases, checks)
    write_json(outdir / "step11y_checks.json", checks)
    write_json(outdir / "step11y_metadata.json", metadata)
    try:
        shutil.copy2(Path(__file__), outdir / Path(__file__).name)
    except Exception as exc:
        warnings.append(f"Could not copy script: {exc}")

    print("\n============================================================")
    print("STEP11Y PROTOTYPE-BASED PLANNER INPUT AUDIT")
    print("============================================================")
    print(f"1. Script created: {rel(Path(__file__))}")
    print(f"2. Command used: python {rel(Path(__file__))}")
    print(f"3. Output created: {rel(outdir)}")
    print(f"4. Verdict: {verdict}")
    step10f_ok = checks["step10f_boundary_near_exact_cases"]
    print(f"5. Old Step10F boundary maps matched Step08 prototypes: {step10f_ok}/{len(cases)} cases")
    print(f"6. Cases needing rerun: {', '.join(rerun_cases) if rerun_cases else 'none'}")
    print("7. Corrected arrays created: baseline, prototype descriptors, enriched alpha025/050, AUV1, AUV2, all_planner_maps.npz")
    if rerun_cases:
        print("8. Minimum tests: C01 single-AUV baseline/prototype_boundary/crossing_gamma025, C01 2-AUV baseline/prototype_vehicle_specific, then C06 and October.")
    else:
        print("8. Minimum tests: no forced rerun; use prototype_based arrays for future Step11E.")
    print(f"Warnings: {len(warnings)} | Missing inputs: {len(missing)} | Figures: {checks['figures_created']}")
    print("============================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
