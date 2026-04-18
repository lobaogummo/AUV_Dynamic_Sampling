"""Controlled registration of tempIBHRes2024_* to physically anchored HRes references.

This script is investigation-only:
- no edits to clustering/prototypes/compact model/planner/cost function
- no overwrite of official outputs
- all artifacts are written to a new versioned folder under investigation/
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
import xarray as xr

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]

TEMP_STACK_CANDIDATES = [
    ROOT / "results" / "plots" / "X_surface_300.npy",
    ROOT / "results" / "fossum" / "X_surface_300.npy",
]
TEMP_NORM_CANDIDATES = [
    ROOT / "results" / "plots" / "X_surface_300_norm.npy",
    ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
]
TEMP_MASK_CANDIDATES = [
    ROOT / "results" / "plots" / "mask_common.npy",
    ROOT / "results" / "fossum" / "mask_common.npy",
]

TEMP_SCALE_CANDIDATES = [
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis" / "color_scale.json",
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "color_scale.json",
]
TEMP_NORM_SCALE_CANDIDATES = [
    ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis" / "color_scale_norm.json",
    ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis_indexed_axes" / "color_scale_norm.json",
]

TEST_C4_DIR = ROOT / "data" / "TEST_C4" / "HighRes" / "Daily_dpt_20241030_NewTest_1"
PRED_GLOB = "31-10-2024_predModel_*.nc"
AUV_GLOB = "31-10-2024_AUVpredModel_*.nc"
PREFERRED_HRES_REL = "data/HResNew/CMEMSnaza_20241029_HResNew.nc"
NETCDF_SUMMARY_CSV = ROOT / "results" / "netcdf_files_summary.csv"

EPS = 1e-12


@dataclass(frozen=True)
class TransformCandidate:
    x0: int
    y0: int
    w: int
    h: int

    @property
    def x1(self) -> int:
        return self.x0 + self.w - 1

    @property
    def y1(self) -> int:
        return self.y0 + self.h - 1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Controlled registration tempIBHRes <-> HRes")
    p.add_argument("--tag", type=str, default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    p.add_argument("--export-full-inferred-figures", action="store_true", default=True)
    p.add_argument(
        "--inferred-axis-mode",
        type=str,
        default="utm_abs_km",
        choices=["utm_abs_km", "local_rel_km"],
        help="Axis construction for inferred figures: absolute UTM km (default) or local relative km.",
    )
    p.add_argument("--coarse-width-step", type=int, default=8)
    p.add_argument("--coarse-height-step", type=int, default=8)
    p.add_argument("--topk-refine", type=int, default=8)
    p.add_argument("--topk-temp-eval", type=int, default=10)
    p.add_argument("--viability-mask-iou", type=float, default=0.90)
    p.add_argument("--viability-pred-mean-corr", type=float, default=0.80)
    p.add_argument("--viability-auv-mean-corr", type=float, default=0.80)
    p.add_argument("--viability-min-corr", type=float, default=0.70)
    return p.parse_args()


def to_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve())


def resolve_existing(candidates: Iterable[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("None of these candidates exist: " + ", ".join(str(x) for x in candidates))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def numeric_suffix(path: Path) -> int:
    m = re.search(r"_(\d+)\.nc$", path.name)
    return int(m.group(1)) if m else 10**9


def load_temp_inputs() -> Dict[str, np.ndarray]:
    x_path = resolve_existing(TEMP_STACK_CANDIDATES)
    x_norm_path = resolve_existing(TEMP_NORM_CANDIDATES)
    mask_path = resolve_existing(TEMP_MASK_CANDIDATES)

    x = np.load(x_path).astype(np.float32, copy=False)
    x_norm = np.load(x_norm_path).astype(np.float32, copy=False)
    mask = np.load(mask_path).astype(bool, copy=False)

    if x.ndim != 3 or x_norm.ndim != 3:
        raise RuntimeError(f"Expected 3D stacks, got x={x.shape}, x_norm={x_norm.shape}")
    if x.shape != x_norm.shape:
        raise RuntimeError(f"Shape mismatch x={x.shape} vs x_norm={x_norm.shape}")
    if mask.shape != x.shape[1:]:
        raise RuntimeError(f"Mask shape mismatch mask={mask.shape} vs spatial={x.shape[1:]}")

    x = x.copy()
    x_norm = x_norm.copy()
    x[:, ~mask] = np.nan
    x_norm[:, ~mask] = np.nan

    return {
        "x": x,
        "x_norm": x_norm,
        "mask": mask,
        "x_path": np.array(str(x_path)),
        "x_norm_path": np.array(str(x_norm_path)),
        "mask_path": np.array(str(mask_path)),
    }


def _extract_2d(da: xr.DataArray) -> np.ndarray:
    arr = da.values
    if arr.ndim == 2:
        return arr.astype(np.float64, copy=False)
    if arr.ndim == 3:
        return arr[0].astype(np.float64, copy=False)
    if arr.ndim == 4:
        return arr[0, 0].astype(np.float64, copy=False)
    raise RuntimeError(f"Unsupported ndarray rank for reference map: {arr.ndim}")


def load_reference_family(glob_pattern: str, family_label: str, value_var: str = "TEMPpred") -> Dict[str, object]:
    files = sorted(TEST_C4_DIR.glob(glob_pattern), key=numeric_suffix)
    if not files:
        raise FileNotFoundError(f"No files for {family_label} with pattern {glob_pattern} in {TEST_C4_DIR}")

    maps: List[np.ndarray] = []
    steps: List[int] = []
    refs: List[str] = []
    hres_lat = None
    hres_lon = None
    bathy_mask = None

    for path in files:
        ds = xr.open_dataset(path, decode_times=False)
        if value_var in ds.data_vars:
            arr2d = _extract_2d(ds[value_var])
        elif "TEMP" in ds.data_vars:
            arr2d = _extract_2d(ds["TEMP"])
        else:
            ds.close()
            raise RuntimeError(f"Neither {value_var} nor TEMP exists in {path}")

        if bathy_mask is None and "BATHY" in ds.data_vars:
            bathy_mask = np.isfinite(_extract_2d(ds["BATHY"]))
        if hres_lat is None:
            lat_name = next((n for n in ds.coords if n.lower() == "lat"), None)
            lon_name = next((n for n in ds.coords if n.lower() == "lon"), None)
            if lat_name is None or lon_name is None:
                ds.close()
                raise RuntimeError(f"Could not find LAT/LON coords in {path}")
            hres_lat = ds[lat_name].values.astype(np.float64, copy=False)
            hres_lon = ds[lon_name].values.astype(np.float64, copy=False)
        ds.close()

        maps.append(arr2d.astype(np.float32, copy=False))
        steps.append(numeric_suffix(path))
        refs.append(to_rel(path))

    if bathy_mask is None:
        bathy_mask = np.isfinite(maps[0])

    return {
        "family": family_label,
        "maps": maps,
        "steps": steps,
        "paths": refs,
        "lat": hres_lat,
        "lon": hres_lon,
        "bathy_mask": bathy_mask,
    }


def linspace_indices(in_size: int, out_size: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if out_size < 1:
        raise RuntimeError("Invalid out_size")
    if in_size < 1:
        raise RuntimeError("Invalid in_size")
    coord = np.linspace(0.0, float(in_size - 1), out_size, dtype=np.float64)
    i0 = np.floor(coord).astype(np.int32)
    i1 = np.minimum(i0 + 1, in_size - 1).astype(np.int32)
    w = (coord - i0).astype(np.float32)
    return i0, i1, w


def bilinear_resize(arr: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    in_h, in_w = int(arr.shape[0]), int(arr.shape[1])
    if in_h == out_h and in_w == out_w:
        return arr.astype(np.float32, copy=False).copy()

    y0, y1, wy = linspace_indices(in_h, out_h)
    x0, x1, wx = linspace_indices(in_w, out_w)

    base = arr.astype(np.float32, copy=False)
    ia = base[y0[:, None], x0[None, :]]
    ib = base[y0[:, None], x1[None, :]]
    ic = base[y1[:, None], x0[None, :]]
    idv = base[y1[:, None], x1[None, :]]

    wx2 = wx[None, :]
    wy2 = wy[:, None]
    top = (1.0 - wx2) * ia + wx2 * ib
    bot = (1.0 - wx2) * ic + wx2 * idv
    out = (1.0 - wy2) * top + wy2 * bot
    return out.astype(np.float32, copy=False)


def resize_mask(mask: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    if mask.shape == (out_h, out_w):
        return mask.astype(bool, copy=False).copy()
    f = bilinear_resize(mask.astype(np.float32, copy=False), out_h=out_h, out_w=out_w)
    return f >= 0.5


def resize_nanaware(field: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    if field.shape == (out_h, out_w):
        return field.astype(np.float32, copy=False).copy()
    valid = np.isfinite(field).astype(np.float32, copy=False)
    base = np.nan_to_num(field, nan=0.0).astype(np.float32, copy=False)
    num = bilinear_resize(base, out_h=out_h, out_w=out_w)
    den = bilinear_resize(valid, out_h=out_h, out_w=out_w)
    out = np.full((out_h, out_w), np.nan, dtype=np.float32)
    ok = den > 1e-6
    out[ok] = num[ok] / den[ok]
    return out


def transform_mask(hres_mask: np.ndarray, cand: TransformCandidate, out_h: int, out_w: int) -> np.ndarray:
    crop = hres_mask[cand.y0 : cand.y0 + cand.h, cand.x0 : cand.x0 + cand.w]
    return resize_mask(crop, out_h=out_h, out_w=out_w)


def transform_field(field: np.ndarray, cand: TransformCandidate, out_h: int, out_w: int) -> np.ndarray:
    crop = field[cand.y0 : cand.y0 + cand.h, cand.x0 : cand.x0 + cand.w]
    return resize_nanaware(crop, out_h=out_h, out_w=out_w)


def mask_metrics(target: np.ndarray, pred: np.ndarray) -> Dict[str, float]:
    inter = int(np.logical_and(target, pred).sum())
    union = int(np.logical_or(target, pred).sum())
    target_sum = int(target.sum())
    pred_sum = int(pred.sum())
    iou = float(inter / union) if union > 0 else 0.0
    dice = float((2.0 * inter) / (target_sum + pred_sum)) if (target_sum + pred_sum) > 0 else 0.0
    hamming = float(np.mean(target != pred))
    return {
        "iou": iou,
        "dice": dice,
        "hamming": hamming,
        "intersection": inter,
        "union": union,
        "target_sum": target_sum,
        "pred_sum": pred_sum,
    }


def candidate_positions(max_start: int, step: int) -> List[int]:
    if max_start <= 0:
        return [0]
    step = max(1, int(step))
    vals = list(range(0, max_start + 1, step))
    if vals[-1] != max_start:
        vals.append(max_start)
    return vals


def stage1_search(
    hres_mask: np.ndarray,
    temp_mask: np.ndarray,
    width_step: int,
    height_step: int,
) -> pd.DataFrame:
    out_h, out_w = int(temp_mask.shape[0]), int(temp_mask.shape[1])
    hres_h, hres_w = int(hres_mask.shape[0]), int(hres_mask.shape[1])
    rows: List[Dict[str, object]] = []

    widths = list(range(out_w, hres_w + 1, max(1, width_step)))
    if widths[-1] != hres_w:
        widths.append(hres_w)
    heights = list(range(out_h, hres_h + 1, max(1, height_step)))
    if heights[-1] != hres_h:
        heights.append(hres_h)

    for w in widths:
        for h in heights:
            x_step = max(1, w // 20)
            y_step = max(1, h // 20)
            x0_vals = candidate_positions(max_start=hres_w - w, step=x_step)
            y0_vals = candidate_positions(max_start=hres_h - h, step=y_step)
            for y0 in y0_vals:
                for x0 in x0_vals:
                    cand = TransformCandidate(x0=x0, y0=y0, w=w, h=h)
                    mapped = transform_mask(hres_mask=hres_mask, cand=cand, out_h=out_h, out_w=out_w)
                    mm = mask_metrics(target=temp_mask, pred=mapped)
                    rows.append(
                        {
                            "stage": "stage1",
                            "x0": cand.x0,
                            "y0": cand.y0,
                            "w": cand.w,
                            "h": cand.h,
                            "x1": cand.x1,
                            "y1": cand.y1,
                            "scale_x_idx_per_outpix": float((cand.w - 1) / max(1, out_w - 1)),
                            "scale_y_idx_per_outpix": float((cand.h - 1) / max(1, out_h - 1)),
                            **mm,
                        }
                    )

    df = pd.DataFrame(rows)
    df = df.sort_values(["iou", "dice", "hamming"], ascending=[False, False, True], ignore_index=True)
    return df


def stage2_refine(hres_mask: np.ndarray, temp_mask: np.ndarray, seeds: pd.DataFrame) -> pd.DataFrame:
    out_h, out_w = int(temp_mask.shape[0]), int(temp_mask.shape[1])
    hres_h, hres_w = int(hres_mask.shape[0]), int(hres_mask.shape[1])

    unique_cands: Dict[Tuple[int, int, int, int], TransformCandidate] = {}
    for row in seeds.itertuples(index=False):
        w_values = range(max(out_w, int(row.w) - 12), min(hres_w, int(row.w) + 12) + 1, 3)
        h_values = range(max(out_h, int(row.h) - 12), min(hres_h, int(row.h) + 12) + 1, 3)
        for w in w_values:
            for h in h_values:
                x_min = max(0, int(row.x0) - 12)
                x_max = min(hres_w - w, int(row.x0) + 12)
                y_min = max(0, int(row.y0) - 12)
                y_max = min(hres_h - h, int(row.y0) + 12)
                for x0 in range(x_min, x_max + 1, 2):
                    for y0 in range(y_min, y_max + 1, 2):
                        key = (x0, y0, w, h)
                        unique_cands[key] = TransformCandidate(x0=x0, y0=y0, w=w, h=h)

    rows: List[Dict[str, object]] = []
    for cand in unique_cands.values():
        mapped = transform_mask(hres_mask=hres_mask, cand=cand, out_h=out_h, out_w=out_w)
        mm = mask_metrics(target=temp_mask, pred=mapped)
        rows.append(
            {
                "stage": "stage2",
                "x0": cand.x0,
                "y0": cand.y0,
                "w": cand.w,
                "h": cand.h,
                "x1": cand.x1,
                "y1": cand.y1,
                "scale_x_idx_per_outpix": float((cand.w - 1) / max(1, out_w - 1)),
                "scale_y_idx_per_outpix": float((cand.h - 1) / max(1, out_h - 1)),
                **mm,
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values(["iou", "dice", "hamming"], ascending=[False, False, True], ignore_index=True)
    return df


def stage3_local(hres_mask: np.ndarray, temp_mask: np.ndarray, seed: TransformCandidate) -> pd.DataFrame:
    out_h, out_w = int(temp_mask.shape[0]), int(temp_mask.shape[1])
    hres_h, hres_w = int(hres_mask.shape[0]), int(hres_mask.shape[1])

    rows: List[Dict[str, object]] = []
    for dw in range(-4, 5):
        for dh in range(-4, 5):
            w = int(np.clip(seed.w + dw, out_w, hres_w))
            h = int(np.clip(seed.h + dh, out_h, hres_h))
            x0_min = max(0, seed.x0 - 4)
            x0_max = min(hres_w - w, seed.x0 + 4)
            y0_min = max(0, seed.y0 - 4)
            y0_max = min(hres_h - h, seed.y0 + 4)
            for x0 in range(x0_min, x0_max + 1):
                for y0 in range(y0_min, y0_max + 1):
                    cand = TransformCandidate(x0=x0, y0=y0, w=w, h=h)
                    mapped = transform_mask(hres_mask=hres_mask, cand=cand, out_h=out_h, out_w=out_w)
                    mm = mask_metrics(target=temp_mask, pred=mapped)
                    rows.append(
                        {
                            "stage": "stage3",
                            "x0": cand.x0,
                            "y0": cand.y0,
                            "w": cand.w,
                            "h": cand.h,
                            "x1": cand.x1,
                            "y1": cand.y1,
                            "scale_x_idx_per_outpix": float((cand.w - 1) / max(1, out_w - 1)),
                            "scale_y_idx_per_outpix": float((cand.h - 1) / max(1, out_h - 1)),
                            **mm,
                        }
                    )

    df = pd.DataFrame(rows).drop_duplicates(subset=["x0", "y0", "w", "h"], keep="first")
    df = df.sort_values(["iou", "dice", "hamming"], ascending=[False, False, True], ignore_index=True)
    return df


def best_match_for_reference(temp_stack: np.ndarray, temp_mask: np.ndarray, ref_map: np.ndarray) -> Dict[str, object]:
    idx = np.isfinite(ref_map) & temp_mask
    n_valid = int(idx.sum())
    if n_valid < 128:
        return {
            "matched_temp_day_1based": None,
            "best_corr": np.nan,
            "second_corr": np.nan,
            "corr_margin": np.nan,
            "rmse_raw": np.nan,
            "rmse_linear_fit": np.nan,
            "nrmse_linear_fit": np.nan,
            "linear_fit_a": np.nan,
            "linear_fit_b": np.nan,
            "n_valid": n_valid,
        }

    ref_vec = ref_map[idx].astype(np.float64, copy=False)
    temp_mat = temp_stack[:, idx].astype(np.float64, copy=False)

    ref_center = ref_vec - np.mean(ref_vec)
    ref_std = float(np.std(ref_center))
    if not np.isfinite(ref_std) or ref_std < EPS:
        return {
            "matched_temp_day_1based": None,
            "best_corr": np.nan,
            "second_corr": np.nan,
            "corr_margin": np.nan,
            "rmse_raw": np.nan,
            "rmse_linear_fit": np.nan,
            "nrmse_linear_fit": np.nan,
            "linear_fit_a": np.nan,
            "linear_fit_b": np.nan,
            "n_valid": n_valid,
        }
    ref_z = ref_center / ref_std

    temp_center = temp_mat - np.mean(temp_mat, axis=1, keepdims=True)
    temp_std = np.std(temp_center, axis=1, keepdims=True) + EPS
    temp_z = temp_center / temp_std
    corr = (temp_z @ ref_z) / float(ref_z.size)

    best_idx = int(np.argmax(corr))
    sorted_idx = np.argsort(corr)
    second_idx = int(sorted_idx[-2]) if corr.size > 1 else best_idx
    best_corr = float(corr[best_idx])
    second_corr = float(corr[second_idx])

    y = temp_mat[best_idx]
    rmse_raw = float(np.sqrt(np.mean((y - ref_vec) ** 2)))
    A = np.column_stack([ref_vec, np.ones_like(ref_vec)])
    coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    y_hat = coef[0] * ref_vec + coef[1]
    rmse_lin = float(np.sqrt(np.mean((y - y_hat) ** 2)))
    rng = float(np.nanmax(y) - np.nanmin(y))
    nrmse_lin = float(rmse_lin / (rng + EPS))

    return {
        "matched_temp_day_1based": int(best_idx + 1),
        "best_corr": best_corr,
        "second_corr": second_corr,
        "corr_margin": float(best_corr - second_corr),
        "rmse_raw": rmse_raw,
        "rmse_linear_fit": rmse_lin,
        "nrmse_linear_fit": nrmse_lin,
        "linear_fit_a": float(coef[0]),
        "linear_fit_b": float(coef[1]),
        "n_valid": n_valid,
    }


def evaluate_candidate_summary(
    cand: TransformCandidate,
    temp_stack: np.ndarray,
    temp_mask: np.ndarray,
    family_maps: Sequence[np.ndarray],
) -> Dict[str, float]:
    out_h, out_w = int(temp_mask.shape[0]), int(temp_mask.shape[1])
    per_corr: List[float] = []
    per_margin: List[float] = []
    per_nrmse: List[float] = []
    valid_steps = 0

    for m in family_maps:
        mapped = transform_field(field=m, cand=cand, out_h=out_h, out_w=out_w)
        match = best_match_for_reference(temp_stack=temp_stack, temp_mask=temp_mask, ref_map=mapped)
        if np.isfinite(match["best_corr"]):
            valid_steps += 1
            per_corr.append(float(match["best_corr"]))
            per_margin.append(float(match["corr_margin"]))
            per_nrmse.append(float(match["nrmse_linear_fit"]))

    if valid_steps == 0:
        return {
            "valid_steps": 0,
            "mean_best_corr": np.nan,
            "median_best_corr": np.nan,
            "min_best_corr": np.nan,
            "p25_best_corr": np.nan,
            "mean_corr_margin": np.nan,
            "mean_nrmse_linear_fit": np.nan,
        }

    arr = np.array(per_corr, dtype=np.float64)
    mar = np.array(per_margin, dtype=np.float64)
    nrm = np.array(per_nrmse, dtype=np.float64)
    return {
        "valid_steps": int(valid_steps),
        "mean_best_corr": float(np.mean(arr)),
        "median_best_corr": float(np.median(arr)),
        "min_best_corr": float(np.min(arr)),
        "p25_best_corr": float(np.percentile(arr, 25)),
        "mean_corr_margin": float(np.mean(mar)),
        "mean_nrmse_linear_fit": float(np.mean(nrm)),
    }


def evaluate_top_candidates(
    ranked_df: pd.DataFrame,
    top_k: int,
    temp_stack: np.ndarray,
    temp_mask: np.ndarray,
    pred_maps: Sequence[np.ndarray],
    auv_maps: Sequence[np.ndarray],
) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    subset = ranked_df.head(top_k)
    for row in subset.itertuples(index=False):
        cand = TransformCandidate(x0=int(row.x0), y0=int(row.y0), w=int(row.w), h=int(row.h))
        pred = evaluate_candidate_summary(cand=cand, temp_stack=temp_stack, temp_mask=temp_mask, family_maps=pred_maps)
        auv = evaluate_candidate_summary(cand=cand, temp_stack=temp_stack, temp_mask=temp_mask, family_maps=auv_maps)

        combined = (
            0.45 * float(row.iou)
            + 0.35 * (pred["mean_best_corr"] if np.isfinite(pred["mean_best_corr"]) else 0.0)
            + 0.20 * (auv["mean_best_corr"] if np.isfinite(auv["mean_best_corr"]) else 0.0)
        )
        rows.append(
            {
                "x0": cand.x0,
                "y0": cand.y0,
                "w": cand.w,
                "h": cand.h,
                "x1": cand.x1,
                "y1": cand.y1,
                "mask_iou": float(row.iou),
                "mask_dice": float(row.dice),
                "mask_hamming": float(row.hamming),
                "pred_valid_steps": pred["valid_steps"],
                "pred_mean_best_corr": pred["mean_best_corr"],
                "pred_median_best_corr": pred["median_best_corr"],
                "pred_min_best_corr": pred["min_best_corr"],
                "pred_p25_best_corr": pred["p25_best_corr"],
                "pred_mean_corr_margin": pred["mean_corr_margin"],
                "pred_mean_nrmse_linear_fit": pred["mean_nrmse_linear_fit"],
                "auv_valid_steps": auv["valid_steps"],
                "auv_mean_best_corr": auv["mean_best_corr"],
                "auv_median_best_corr": auv["median_best_corr"],
                "auv_min_best_corr": auv["min_best_corr"],
                "auv_p25_best_corr": auv["p25_best_corr"],
                "auv_mean_corr_margin": auv["mean_corr_margin"],
                "auv_mean_nrmse_linear_fit": auv["mean_nrmse_linear_fit"],
                "combined_score": float(combined),
            }
        )
    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["combined_score", "mask_iou", "pred_mean_best_corr", "auv_mean_best_corr"],
        ascending=[False, False, False, False],
        ignore_index=True,
    )
    return out


def detailed_family_matches(
    cand: TransformCandidate,
    family_name: str,
    family_steps: Sequence[int],
    family_paths: Sequence[str],
    family_maps: Sequence[np.ndarray],
    temp_stack: np.ndarray,
    temp_mask: np.ndarray,
) -> pd.DataFrame:
    out_h, out_w = int(temp_mask.shape[0]), int(temp_mask.shape[1])
    rows: List[Dict[str, object]] = []
    for step, path, ref_map in zip(family_steps, family_paths, family_maps):
        mapped = transform_field(field=ref_map, cand=cand, out_h=out_h, out_w=out_w)
        m = best_match_for_reference(temp_stack=temp_stack, temp_mask=temp_mask, ref_map=mapped)
        rows.append(
            {
                "family": family_name,
                "step": int(step),
                "reference_path": path,
                "matched_temp_day_1based": m["matched_temp_day_1based"],
                "best_corr": m["best_corr"],
                "second_corr": m["second_corr"],
                "corr_margin": m["corr_margin"],
                "rmse_raw": m["rmse_raw"],
                "rmse_linear_fit": m["rmse_linear_fit"],
                "nrmse_linear_fit": m["nrmse_linear_fit"],
                "linear_fit_a": m["linear_fit_a"],
                "linear_fit_b": m["linear_fit_b"],
                "n_valid": m["n_valid"],
            }
        )
    df = pd.DataFrame(rows).sort_values("step", ignore_index=True)
    return df


def corr_two_maps(temp_map: np.ndarray, ref_map: np.ndarray, mask: np.ndarray) -> float:
    idx = np.isfinite(temp_map) & np.isfinite(ref_map) & mask
    if int(idx.sum()) < 128:
        return np.nan
    a = temp_map[idx].astype(np.float64, copy=False)
    b = ref_map[idx].astype(np.float64, copy=False)
    a = a - np.mean(a)
    b = b - np.mean(b)
    sa = float(np.std(a))
    sb = float(np.std(b))
    if sa < EPS or sb < EPS:
        return np.nan
    return float(np.mean((a / sa) * (b / sb)))


def local_stability_by_step(
    best_cand: TransformCandidate,
    family_steps: Sequence[int],
    family_maps: Sequence[np.ndarray],
    detailed_matches: pd.DataFrame,
    temp_stack: np.ndarray,
    temp_mask: np.ndarray,
) -> pd.DataFrame:
    out_h, out_w = int(temp_mask.shape[0]), int(temp_mask.shape[1])
    rows: List[Dict[str, object]] = []

    for step, ref_map in zip(family_steps, family_maps):
        row = detailed_matches.loc[detailed_matches["step"] == int(step)]
        if row.empty:
            continue
        matched_day = row.iloc[0]["matched_temp_day_1based"]
        if pd.isna(matched_day):
            continue
        day_idx = int(matched_day) - 1
        temp_map = temp_stack[day_idx]

        best_local_corr = -1.0
        best_local = best_cand

        for dx in range(-4, 5):
            for dy in range(-4, 5):
                x0 = int(np.clip(best_cand.x0 + dx, 0, 240 - best_cand.w))
                y0 = int(np.clip(best_cand.y0 + dy, 0, 180 - best_cand.h))
                cand = TransformCandidate(x0=x0, y0=y0, w=best_cand.w, h=best_cand.h)
                mapped = transform_field(field=ref_map, cand=cand, out_h=out_h, out_w=out_w)
                c = corr_two_maps(temp_map=temp_map, ref_map=mapped, mask=temp_mask)
                if np.isfinite(c) and c > best_local_corr:
                    best_local_corr = float(c)
                    best_local = cand

        rows.append(
            {
                "step": int(step),
                "matched_temp_day_1based": int(matched_day),
                "global_x0": int(best_cand.x0),
                "global_y0": int(best_cand.y0),
                "local_best_x0": int(best_local.x0),
                "local_best_y0": int(best_local.y0),
                "delta_x0": int(best_local.x0 - best_cand.x0),
                "delta_y0": int(best_local.y0 - best_cand.y0),
                "local_best_corr": float(best_local_corr),
            }
        )
    return pd.DataFrame(rows).sort_values("step", ignore_index=True)


def save_plot_top_iou(df_ranked: pd.DataFrame, out_png: Path, top_n: int = 25) -> None:
    top = df_ranked.head(top_n).copy()
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    ax.plot(np.arange(1, len(top) + 1), top["iou"].to_numpy(), marker="o", linewidth=1.5)
    ax.set_xlabel("Candidate rank")
    ax.set_ylabel("Mask IoU")
    ax.set_title("Top registration candidates by mask IoU")
    ax.grid(alpha=0.3, linestyle="--")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def save_plot_mask_overlay(temp_mask: np.ndarray, mapped_mask: np.ndarray, out_png: Path) -> None:
    xor_mask = np.logical_xor(temp_mask, mapped_mask)
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.8))
    axes[0].imshow(temp_mask, origin="lower", cmap="gray_r")
    axes[0].set_title("tempIBHRes mask")
    axes[1].imshow(mapped_mask, origin="lower", cmap="gray_r")
    axes[1].set_title("Mapped HRes mask")
    axes[2].imshow(xor_mask, origin="lower", cmap="magma")
    axes[2].set_title("XOR mismatch")
    for ax in axes:
        ax.set_xlabel("x index")
        ax.set_ylabel("y index")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def save_plot_corr_by_step(df: pd.DataFrame, family: str, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 4.2))
    ax.plot(df["step"], df["best_corr"], marker="o", linewidth=1.6, label="best corr")
    ax.plot(df["step"], df["corr_margin"], marker="s", linewidth=1.2, label="corr margin")
    ax.set_xlabel("Reference step")
    ax.set_ylabel("Metric value")
    ax.set_title(f"{family}: registration quality by step")
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend(loc="best")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def save_plot_match_examples(
    cand: TransformCandidate,
    family_name: str,
    family_steps: Sequence[int],
    family_maps: Sequence[np.ndarray],
    detailed_df: pd.DataFrame,
    temp_stack: np.ndarray,
    temp_mask: np.ndarray,
    out_png: Path,
) -> None:
    if len(family_steps) < 1:
        return
    out_h, out_w = temp_mask.shape
    n_show = min(5, len(family_steps))
    idx_show = np.linspace(0, len(family_steps) - 1, n_show, dtype=int)

    rows = []
    for idx in idx_show:
        step = int(family_steps[idx])
        row = detailed_df.loc[detailed_df["step"] == step]
        if row.empty or pd.isna(row.iloc[0]["matched_temp_day_1based"]):
            continue
        day = int(row.iloc[0]["matched_temp_day_1based"])
        ref_mapped = transform_field(field=family_maps[idx], cand=cand, out_h=out_h, out_w=out_w)
        temp_m = temp_stack[day - 1]
        diff = temp_m - ref_mapped
        rows.append((step, day, ref_mapped, temp_m, diff, float(row.iloc[0]["best_corr"])))

    if not rows:
        return

    v_all = np.concatenate([np.ravel(r[2][np.isfinite(r[2])]) for r in rows] + [np.ravel(r[3][np.isfinite(r[3])]) for r in rows])
    vmin = float(np.percentile(v_all, 2.0))
    vmax = float(np.percentile(v_all, 98.0))
    d_all = np.concatenate([np.ravel(r[4][np.isfinite(r[4])]) for r in rows])
    dlim = float(np.percentile(np.abs(d_all), 98.0))

    fig, axes = plt.subplots(len(rows), 3, figsize=(11.5, 2.8 * len(rows)))
    if len(rows) == 1:
        axes = np.asarray([axes])
    for rr, (step, day, ref_mapped, temp_m, diff, corr) in enumerate(rows):
        im0 = axes[rr, 0].imshow(ref_mapped, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
        axes[rr, 0].set_title(f"{family_name} step {step} mapped")
        im1 = axes[rr, 1].imshow(temp_m, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
        axes[rr, 1].set_title(f"tempIBHRes day z={day:03d}")
        im2 = axes[rr, 2].imshow(diff, origin="lower", cmap="coolwarm", vmin=-dlim, vmax=dlim)
        axes[rr, 2].set_title(f"Diff (corr={corr:.3f})")
        for cc in range(3):
            axes[rr, cc].set_xlabel("x index")
            axes[rr, cc].set_ylabel("y index")
        fig.colorbar(im0, ax=axes[rr, 0], fraction=0.046, pad=0.02)
        fig.colorbar(im1, ax=axes[rr, 1], fraction=0.046, pad=0.02)
        fig.colorbar(im2, ax=axes[rr, 2], fraction=0.046, pad=0.02)

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def find_hres_bbox(summary_csv: Path) -> Dict[str, float]:
    if not summary_csv.exists():
        raise FileNotFoundError(f"Missing summary CSV: {summary_csv}")
    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    preferred = next((r for r in rows if r.get("path") == PREFERRED_HRES_REL and r.get("open_ok") == "True"), None)
    if preferred is None:
        preferred = next(
            (r for r in rows if "/HResNew/" in (r.get("path") or "").replace("\\", "/") and r.get("open_ok") == "True"),
            None,
        )
    if preferred is None:
        raise RuntimeError("No valid HRes row available in netcdf_files_summary.csv")

    return {
        "source_path": preferred["path"],
        "lon_min": float(preferred["lon_min"]),
        "lon_max": float(preferred["lon_max"]),
        "lat_min": float(preferred["lat_min"]),
        "lat_max": float(preferred["lat_max"]),
    }


def km_per_degree(lat_deg: float) -> Tuple[float, float]:
    phi = math.radians(float(lat_deg))
    km_deg_lat = 111.13292 - 0.55982 * math.cos(2.0 * phi) + 0.001175 * math.cos(4.0 * phi) - 0.0000023 * math.cos(6.0 * phi)
    km_deg_lon = 111.41284 * math.cos(phi) - 0.0935 * math.cos(3.0 * phi) + 0.00012 * math.cos(5.0 * phi)
    return float(km_deg_lat), float(km_deg_lon)


def utm_zone_from_lon(lon_deg: float) -> int:
    zone = int(math.floor((float(lon_deg) + 180.0) / 6.0) + 1)
    return int(min(60, max(1, zone)))


def latlon_to_utm_wgs84(lat_deg: np.ndarray, lon_deg: np.ndarray, zone_number: int) -> Tuple[np.ndarray, np.ndarray]:
    # WGS84 ellipsoid constants.
    a = 6378137.0
    f = 1.0 / 298.257223563
    e2 = f * (2.0 - f)
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996

    lat = np.asarray(lat_deg, dtype=np.float64)
    lon = np.asarray(lon_deg, dtype=np.float64)
    if lat.shape != lon.shape:
        raise RuntimeError(f"lat/lon shape mismatch for UTM conversion: {lat.shape} vs {lon.shape}")

    lat_rad = np.deg2rad(lat)
    lon_rad = np.deg2rad(lon)
    lon0_deg = (float(zone_number) - 1.0) * 6.0 - 180.0 + 3.0
    lon0_rad = math.radians(lon0_deg)

    sin_lat = np.sin(lat_rad)
    cos_lat = np.cos(lat_rad)
    tan_lat = np.tan(lat_rad)

    n = a / np.sqrt(1.0 - e2 * (sin_lat**2))
    t = tan_lat**2
    c = ep2 * (cos_lat**2)
    a_term = cos_lat * (lon_rad - lon0_rad)

    m = a * (
        (1.0 - e2 / 4.0 - 3.0 * (e2**2) / 64.0 - 5.0 * (e2**3) / 256.0) * lat_rad
        - (3.0 * e2 / 8.0 + 3.0 * (e2**2) / 32.0 + 45.0 * (e2**3) / 1024.0) * np.sin(2.0 * lat_rad)
        + (15.0 * (e2**2) / 256.0 + 45.0 * (e2**3) / 1024.0) * np.sin(4.0 * lat_rad)
        - (35.0 * (e2**3) / 3072.0) * np.sin(6.0 * lat_rad)
    )

    easting = k0 * n * (
        a_term
        + (1.0 - t + c) * (a_term**3) / 6.0
        + (5.0 - 18.0 * t + t**2 + 72.0 * c - 58.0 * ep2) * (a_term**5) / 120.0
    ) + 500000.0

    northing = k0 * (
        m
        + n
        * tan_lat
        * (
            (a_term**2) / 2.0
            + (5.0 - t + 9.0 * c + 4.0 * (c**2)) * (a_term**4) / 24.0
            + (61.0 - 58.0 * t + t**2 + 600.0 * c - 330.0 * ep2) * (a_term**6) / 720.0
        )
    )

    southern = lat < 0.0
    if np.any(southern):
        northing = northing.copy()
        northing[southern] += 10000000.0

    return easting.astype(np.float64, copy=False), northing.astype(np.float64, copy=False)


def inferred_axes_from_registration(
    cand: TransformCandidate,
    hres_lat: np.ndarray,
    hres_lon: np.ndarray,
    out_h: int,
    out_w: int,
    axis_mode: str,
) -> Dict[str, np.ndarray]:
    lat_crop = np.asarray(hres_lat[cand.y0 : cand.y0 + cand.h], dtype=np.float64)
    lon_crop = np.asarray(hres_lon[cand.x0 : cand.x0 + cand.w], dtype=np.float64)
    if lat_crop.size != cand.h or lon_crop.size != cand.w:
        raise RuntimeError("Invalid crop while building inferred axes")

    src_y = np.arange(cand.h, dtype=np.float64)
    src_x = np.arange(cand.w, dtype=np.float64)
    tgt_y = np.linspace(0.0, float(cand.h - 1), out_h, dtype=np.float64)
    tgt_x = np.linspace(0.0, float(cand.w - 1), out_w, dtype=np.float64)
    lat_inf = np.interp(tgt_y, src_y, lat_crop)
    lon_inf = np.interp(tgt_x, src_x, lon_crop)

    lat_mid = float(0.5 * (lat_inf[0] + lat_inf[-1]))
    km_deg_lat, km_deg_lon = km_per_degree(lat_mid)
    lon_mid = float(0.5 * (lon_inf[0] + lon_inf[-1]))

    if axis_mode == "local_rel_km":
        x_km = (lon_inf - lon_inf[0]) * km_deg_lon
        y_km = (lat_inf - lat_inf[0]) * km_deg_lat
        axis_mode_used = "local_rel_km"
        utm_zone = np.array([np.nan], dtype=np.float64)
        utm_hemisphere = np.array(["N" if lat_mid >= 0.0 else "S"], dtype=object)
    elif axis_mode == "utm_abs_km":
        zone = utm_zone_from_lon(lon_mid)
        x_east_m, _ = latlon_to_utm_wgs84(
            lat_deg=np.full_like(lon_inf, lat_mid, dtype=np.float64),
            lon_deg=lon_inf,
            zone_number=zone,
        )
        _, y_north_m = latlon_to_utm_wgs84(
            lat_deg=lat_inf,
            lon_deg=np.full_like(lat_inf, lon_mid, dtype=np.float64),
            zone_number=zone,
        )
        x_km = x_east_m / 1000.0
        y_km = y_north_m / 1000.0
        axis_mode_used = "utm_abs_km"
        utm_zone = np.array([float(zone)], dtype=np.float64)
        utm_hemisphere = np.array(["N" if lat_mid >= 0.0 else "S"], dtype=object)
    else:
        raise RuntimeError(f"Unsupported axis_mode={axis_mode}")

    return {
        "lat_inferred": lat_inf.astype(np.float64, copy=False),
        "lon_inferred": lon_inf.astype(np.float64, copy=False),
        "x_km_inferred": x_km.astype(np.float64, copy=False),
        "y_km_inferred": y_km.astype(np.float64, copy=False),
        "lat_mid_deg": np.array([lat_mid], dtype=np.float64),
        "km_per_deg_lat": np.array([km_deg_lat], dtype=np.float64),
        "km_per_deg_lon": np.array([km_deg_lon], dtype=np.float64),
        "lon_mid_deg": np.array([lon_mid], dtype=np.float64),
        "axis_mode_used": np.array([axis_mode_used], dtype=object),
        "utm_zone": utm_zone,
        "utm_hemisphere": utm_hemisphere,
    }


def load_scale_bounds() -> Dict[str, float]:
    temp_scale_path = resolve_existing(TEMP_SCALE_CANDIDATES)
    norm_scale_path = resolve_existing(TEMP_NORM_SCALE_CANDIDATES)
    temp_payload = json.loads(temp_scale_path.read_text(encoding="utf-8"))
    norm_payload = json.loads(norm_scale_path.read_text(encoding="utf-8"))
    return {
        "temp_vmin": float(temp_payload["vmin"]),
        "temp_vmax": float(temp_payload["vmax"]),
        "norm_vmin": float(norm_payload["vmin"]),
        "norm_vmax": float(norm_payload["vmax"]),
        "temp_scale_path": to_rel(temp_scale_path),
        "norm_scale_path": to_rel(norm_scale_path),
    }


def render_inferred_map(
    arr: np.ndarray,
    extent: Sequence[float],
    out_png: Path,
    title: str,
    cbar_label: str,
    vmin: float,
    vmax: float,
    cmap_name: str,
    x_label: str,
    y_label: str,
) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, extent=extent, aspect="auto")
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def export_inferred_figures(
    out_root: Path,
    x_stack: np.ndarray,
    x_norm_stack: np.ndarray,
    mask: np.ndarray,
    axes_meta: Dict[str, np.ndarray],
    scale_bounds: Dict[str, float],
) -> Dict[str, object]:
    x_km = axes_meta["x_km_inferred"]
    y_km = axes_meta["y_km_inferred"]
    extent = [float(np.min(x_km)), float(np.max(x_km)), float(np.min(y_km)), float(np.max(y_km))]
    axis_mode_used = str(axes_meta["axis_mode_used"][0])

    det_dir = out_root / "figures_inferred_axes_km" / "deterministic_tempibhres"
    norm_dir = out_root / "figures_inferred_axes_km" / "normalized_tempibhres"
    ensure_dir(det_dir)
    ensure_dir(norm_dir)

    if axis_mode_used == "utm_abs_km":
        x_label = "x"
        y_label = "y"
    else:
        x_label = "x"
        y_label = "y"

    det_rows: List[Dict[str, object]] = []
    norm_rows: List[Dict[str, object]] = []
    nz = int(x_stack.shape[0])
    for z in range(1, nz + 1):
        arr = x_stack[z - 1]
        out_png = det_dir / f"TEMP_surface_2024_z{z:03d}.png"
        render_inferred_map(
            arr=arr,
            extent=extent,
            out_png=out_png,
            title=f"TEMP surface z={z:03d} (inferred physical axes)",
            cbar_label="Temperature (degC)",
            vmin=scale_bounds["temp_vmin"],
            vmax=scale_bounds["temp_vmax"],
            cmap_name="viridis",
            x_label=x_label,
            y_label=y_label,
        )
        det_rows.append(
            {
                "z": z,
                "filepath": to_rel(out_png),
                "x_km_min": extent[0],
                "x_km_max": extent[1],
                "y_km_min": extent[2],
                "y_km_max": extent[3],
                "x_axis_label": x_label,
                "y_axis_label": y_label,
                "axes_note": "inferred by registration to physically anchored HRes grid",
            }
        )

        arr_n = x_norm_stack[z - 1].copy()
        arr_n[~mask] = np.nan
        out_png_n = norm_dir / f"X_surface_norm_z{z:03d}.png"
        render_inferred_map(
            arr=arr_n,
            extent=extent,
            out_png=out_png_n,
            title=f"Normalized TEMP z={z:03d} (inferred physical axes)",
            cbar_label="Normalized temperature (-)",
            vmin=scale_bounds["norm_vmin"],
            vmax=scale_bounds["norm_vmax"],
            cmap_name="coolwarm",
            x_label=x_label,
            y_label=y_label,
        )
        norm_rows.append(
            {
                "z": z,
                "filepath": to_rel(out_png_n),
                "x_km_min": extent[0],
                "x_km_max": extent[1],
                "y_km_min": extent[2],
                "y_km_max": extent[3],
                "x_axis_label": x_label,
                "y_axis_label": y_label,
                "axes_note": "inferred by registration to physically anchored HRes grid",
            }
        )

    pd.DataFrame(det_rows).to_csv(det_dir / "index.csv", index=False)
    pd.DataFrame(norm_rows).to_csv(norm_dir / "index.csv", index=False)

    axes_csv = out_root / "figures_inferred_axes_km" / "inferred_axes_1d.csv"
    df_axes = pd.DataFrame(
        {
            "x_index_1based": np.arange(1, x_km.size + 1, dtype=int),
            "lon_inferred": axes_meta["lon_inferred"],
            "x_km_inferred": x_km,
        }
    )
    df_axes_y = pd.DataFrame(
        {
            "y_index_1based": np.arange(1, y_km.size + 1, dtype=int),
            "lat_inferred": axes_meta["lat_inferred"],
            "y_km_inferred": y_km,
        }
    )
    df_axes.to_csv(axes_csv, index=False)
    df_axes_y.to_csv(out_root / "figures_inferred_axes_km" / "inferred_axes_y_1d.csv", index=False)
    np.savez(
        out_root / "figures_inferred_axes_km" / "inferred_axes_arrays.npz",
        lat_inferred=axes_meta["lat_inferred"],
        lon_inferred=axes_meta["lon_inferred"],
        x_km_inferred=axes_meta["x_km_inferred"],
        y_km_inferred=axes_meta["y_km_inferred"],
    )

    return {
        "deterministic_dir": to_rel(det_dir),
        "normalized_dir": to_rel(norm_dir),
        "deterministic_count": len(det_rows),
        "normalized_count": len(norm_rows),
        "extent_km": extent,
        "x_label": x_label,
        "y_label": y_label,
        "axis_mode_used": axis_mode_used,
    }


def viability_decision(
    best_eval: pd.Series,
    mask_threshold: float,
    pred_mean_threshold: float,
    auv_mean_threshold: float,
    min_corr_threshold: float,
) -> Dict[str, object]:
    mask_ok = float(best_eval["mask_iou"]) >= float(mask_threshold)
    pred_ok = float(best_eval["pred_mean_best_corr"]) >= float(pred_mean_threshold)
    auv_ok = float(best_eval["auv_mean_best_corr"]) >= float(auv_mean_threshold)
    min_ok = min(float(best_eval["pred_min_best_corr"]), float(best_eval["auv_min_best_corr"])) >= float(min_corr_threshold)
    overall = bool(mask_ok and pred_ok and auv_ok and min_ok)
    return {
        "overall_pass": overall,
        "mask_ok": bool(mask_ok),
        "pred_ok": bool(pred_ok),
        "auv_ok": bool(auv_ok),
        "min_ok": bool(min_ok),
        "thresholds": {
            "mask_iou": float(mask_threshold),
            "pred_mean_corr": float(pred_mean_threshold),
            "auv_mean_corr": float(auv_mean_threshold),
            "min_corr": float(min_corr_threshold),
        },
    }


def write_report(
    out_root: Path,
    dataset_info: Dict[str, object],
    best_cand: TransformCandidate,
    best_eval: pd.Series,
    viability: Dict[str, object],
    pred_df: pd.DataFrame,
    auv_df: pd.DataFrame,
    pred_stability: pd.DataFrame,
    auv_stability: pd.DataFrame,
    inferred_export: Dict[str, object] | None,
) -> None:
    lines: List[str] = []
    lines.append("# TEMPIBHRES_HRES_REGISTRATION_REPORT")
    lines.append("")
    lines.append(f"Generated at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## 1) Executive summary")
    lines.append(
        "- Objective: infer a physically defensible spatial registration from `tempIBHRes2024_*` to physically anchored HRes references before creating physical-axis figures."
    )
    lines.append(
        f"- Outcome: {'viable' if viability['overall_pass'] else 'not robust enough'} for inferred physical-axis labeling under the configured criteria."
    )
    lines.append(
        f"- Best transformation (0-based HRes indices): x0={best_cand.x0}, x1={best_cand.x1}, y0={best_cand.y0}, y1={best_cand.y1}, w={best_cand.w}, h={best_cand.h}."
    )
    lines.append(
        f"- Best candidate metrics: mask IoU={float(best_eval['mask_iou']):.6f}, "
        f"pred mean corr={float(best_eval['pred_mean_best_corr']):.6f}, "
        f"auv mean corr={float(best_eval['auv_mean_best_corr']):.6f}."
    )
    lines.append("")
    lines.append("## 2) Datasets and references")
    lines.append("- tempIBHRes source stack: `results/plots/X_surface_300.npy` (shape 300x64x112).")
    lines.append("- Physically anchored reference family A: `TEST_C4 predModel_*` using `TEMPpred` (17 steps).")
    lines.append("- Physically anchored reference family B: `TEST_C4 AUVpredModel_*` using `TEMPpred` (17 steps).")
    lines.append("- Physical frame comes from TEST_C4 NetCDF LAT/LON coordinates and HRes mask (`BATHY`).")
    lines.append("")
    lines.append("## 3) Method")
    lines.append("- Stage 1: deterministic coarse search over axis-aligned crop+resample transforms, scored by mask overlap.")
    lines.append("- Stage 2: local refinement around top mask candidates.")
    lines.append("- Stage 3: local fine search around best refined candidate.")
    lines.append("- Temperature validation: for each reference step, transform to tempIBHRes grid and match against all 300 tempIBHRes days by max Pearson correlation.")
    lines.append("- Additional metrics per match: second-best correlation, correlation margin, RMSE(raw), RMSE(linear-fit), NRMSE(linear-fit).")
    lines.append("- Stability check: per-step local offset re-optimization around the global best transformation.")
    lines.append("")
    lines.append("## 4) Key results")
    lines.append("- Candidate ranking and search traces are in `tables/` CSV files.")
    lines.append(
        f"- Best candidate (1-based HRes indices): x={best_cand.x0 + 1}..{best_cand.x1 + 1}, "
        f"y={best_cand.y0 + 1}..{best_cand.y1 + 1}."
    )
    lines.append(
        f"- predModel summary: mean={pred_df['best_corr'].mean():.6f}, median={pred_df['best_corr'].median():.6f}, min={pred_df['best_corr'].min():.6f}, p25={pred_df['best_corr'].quantile(0.25):.6f}."
    )
    lines.append(
        f"- AUVpredModel summary: mean={auv_df['best_corr'].mean():.6f}, median={auv_df['best_corr'].median():.6f}, min={auv_df['best_corr'].min():.6f}, p25={auv_df['best_corr'].quantile(0.25):.6f}."
    )
    if not pred_stability.empty:
        lines.append(
            f"- Pred local stability (|delta| means): |dx|={pred_stability['delta_x0'].abs().mean():.3f}, |dy|={pred_stability['delta_y0'].abs().mean():.3f}."
        )
    if not auv_stability.empty:
        lines.append(
            f"- AUV local stability (|delta| means): |dx|={auv_stability['delta_x0'].abs().mean():.3f}, |dy|={auv_stability['delta_y0'].abs().mean():.3f}."
        )
    lines.append("")
    lines.append("## 5) Decision on inferred physical axes")
    lines.append(f"- Viability decision: `{viability['overall_pass']}`")
    lines.append(
        f"- Criteria checks: mask_ok={viability['mask_ok']}, pred_ok={viability['pred_ok']}, "
        f"auv_ok={viability['auv_ok']}, min_ok={viability['min_ok']}."
    )
    if viability["overall_pass"] and inferred_export is not None:
        lines.append("- Inferred-axis figures were exported with explicit inferred labeling (not native tempIBHRes georeferencing).")
        lines.append(f"- Axis mode used: `{inferred_export.get('axis_mode_used', 'unknown')}`")
        lines.append(f"- Deterministic inferred figures: `{inferred_export['deterministic_dir']}`")
        lines.append(f"- Normalized inferred figures: `{inferred_export['normalized_dir']}`")
    else:
        lines.append("- Inferred-axis figure export was skipped to avoid forcing a weak transformation.")
    lines.append("")
    lines.append("## 6) Facts, inferences, limitations")
    lines.append("### Facts observed")
    lines.append("- tempIBHRes grid is 64x112 with index-based columns (`x`,`y`,`z`,`temp`).")
    lines.append("- TEST_C4 pred/AUV NetCDF grids are physically anchored and include LAT/LON coordinates.")
    lines.append("- Registration search produced a top candidate with metrics reported above.")
    lines.append("### Inferences")
    lines.append("- The best transformation is interpreted as a plausible spatial correspondence between tempIBHRes and a sub-area of the HRes physical grid.")
    lines.append("- Inferred axes are therefore registration-derived, not native to tempIBHRes.")
    lines.append("### Limitations")
    lines.append("- Transformation family is restricted to axis-aligned crop + linear resampling (no rotation/shear/nonlinear warp).")
    lines.append("- Temporal pairing uses max-correlation matching; high similarity fields can reduce uniqueness of matched day indices.")
    lines.append("- This investigation does not prove native georeferencing metadata exists inside tempIBHRes.")
    lines.append("")
    lines.append("## 7) Output inventory")
    lines.append("- `tables/`: candidate search traces, top-candidate evaluations, per-step match metrics, stability checks.")
    lines.append("- `plots/`: mask overlays, ranking curves, per-step quality curves, side-by-side diagnostics.")
    lines.append("- `manifest.json`: full traceability of inputs, parameters, thresholds, and decision.")
    if inferred_export is not None:
        lines.append("- `figures_inferred_axes_km/`: inferred-axis figure exports and inferred axis arrays.")
    lines.append("")
    (out_root / "TEMPIBHRES_HRES_REGISTRATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_root = ROOT / "investigation" / f"tempibhres_hres_registration_{args.tag}"
    tables_dir = out_root / "tables"
    plots_dir = out_root / "plots"
    ensure_dir(out_root)
    ensure_dir(tables_dir)
    ensure_dir(plots_dir)

    temp = load_temp_inputs()
    x = temp["x"]
    x_norm = temp["x_norm"]
    temp_mask = temp["mask"]

    pred = load_reference_family(PRED_GLOB, family_label="predModel", value_var="TEMPpred")
    auv = load_reference_family(AUV_GLOB, family_label="AUVpredModel", value_var="TEMPpred")
    hres_mask = np.asarray(pred["bathy_mask"], dtype=bool)

    # Search stage A/B/C on mask alignment.
    stage1 = stage1_search(
        hres_mask=hres_mask,
        temp_mask=temp_mask,
        width_step=args.coarse_width_step,
        height_step=args.coarse_height_step,
    )
    stage1.to_csv(tables_dir / "mask_search_stage1.csv", index=False)
    seeds = stage1.head(max(1, int(args.topk_refine)))

    stage2 = stage2_refine(hres_mask=hres_mask, temp_mask=temp_mask, seeds=seeds)
    stage2.to_csv(tables_dir / "mask_search_stage2.csv", index=False)

    combined = pd.concat([stage1, stage2], ignore_index=True)
    combined = combined.drop_duplicates(subset=["x0", "y0", "w", "h"], keep="first")
    combined = combined.sort_values(["iou", "dice", "hamming"], ascending=[False, False, True], ignore_index=True)

    best_seed = TransformCandidate(
        x0=int(combined.iloc[0]["x0"]),
        y0=int(combined.iloc[0]["y0"]),
        w=int(combined.iloc[0]["w"]),
        h=int(combined.iloc[0]["h"]),
    )
    stage3 = stage3_local(hres_mask=hres_mask, temp_mask=temp_mask, seed=best_seed)
    stage3.to_csv(tables_dir / "mask_search_stage3.csv", index=False)

    ranked_all = pd.concat([combined, stage3], ignore_index=True)
    ranked_all = ranked_all.drop_duplicates(subset=["x0", "y0", "w", "h"], keep="first")
    ranked_all = ranked_all.sort_values(["iou", "dice", "hamming"], ascending=[False, False, True], ignore_index=True)
    ranked_all.to_csv(tables_dir / "mask_search_ranked_all.csv", index=False)

    # Candidate temperature validation.
    top_eval = evaluate_top_candidates(
        ranked_df=ranked_all,
        top_k=max(1, int(args.topk_temp_eval)),
        temp_stack=x,
        temp_mask=temp_mask,
        pred_maps=pred["maps"],
        auv_maps=auv["maps"],
    )
    top_eval.to_csv(tables_dir / "top_candidates_temperature_eval.csv", index=False)

    if top_eval.empty:
        raise RuntimeError("No candidate survived top-candidate evaluation.")

    best_eval = top_eval.iloc[0]
    best_cand = TransformCandidate(
        x0=int(best_eval["x0"]),
        y0=int(best_eval["y0"]),
        w=int(best_eval["w"]),
        h=int(best_eval["h"]),
    )

    # Detailed per-step matching for best candidate.
    pred_detailed = detailed_family_matches(
        cand=best_cand,
        family_name="predModel",
        family_steps=pred["steps"],
        family_paths=pred["paths"],
        family_maps=pred["maps"],
        temp_stack=x,
        temp_mask=temp_mask,
    )
    auv_detailed = detailed_family_matches(
        cand=best_cand,
        family_name="AUVpredModel",
        family_steps=auv["steps"],
        family_paths=auv["paths"],
        family_maps=auv["maps"],
        temp_stack=x,
        temp_mask=temp_mask,
    )
    pred_detailed.to_csv(tables_dir / "best_candidate_matches_predModel.csv", index=False)
    auv_detailed.to_csv(tables_dir / "best_candidate_matches_AUVpredModel.csv", index=False)

    # Local stability by step.
    pred_stability = local_stability_by_step(
        best_cand=best_cand,
        family_steps=pred["steps"],
        family_maps=pred["maps"],
        detailed_matches=pred_detailed,
        temp_stack=x,
        temp_mask=temp_mask,
    )
    auv_stability = local_stability_by_step(
        best_cand=best_cand,
        family_steps=auv["steps"],
        family_maps=auv["maps"],
        detailed_matches=auv_detailed,
        temp_stack=x,
        temp_mask=temp_mask,
    )
    pred_stability.to_csv(tables_dir / "best_candidate_local_stability_predModel.csv", index=False)
    auv_stability.to_csv(tables_dir / "best_candidate_local_stability_AUVpredModel.csv", index=False)

    # Diagnostics plots.
    mapped_mask = transform_mask(hres_mask=hres_mask, cand=best_cand, out_h=temp_mask.shape[0], out_w=temp_mask.shape[1])
    save_plot_top_iou(df_ranked=ranked_all, out_png=plots_dir / "top_mask_candidates_iou.png", top_n=25)
    save_plot_mask_overlay(temp_mask=temp_mask, mapped_mask=mapped_mask, out_png=plots_dir / "mask_overlay_best_candidate.png")
    save_plot_corr_by_step(df=pred_detailed, family="predModel", out_png=plots_dir / "predModel_corr_by_step.png")
    save_plot_corr_by_step(df=auv_detailed, family="AUVpredModel", out_png=plots_dir / "AUVpredModel_corr_by_step.png")
    save_plot_match_examples(
        cand=best_cand,
        family_name="predModel",
        family_steps=pred["steps"],
        family_maps=pred["maps"],
        detailed_df=pred_detailed,
        temp_stack=x,
        temp_mask=temp_mask,
        out_png=plots_dir / "predModel_match_examples.png",
    )
    save_plot_match_examples(
        cand=best_cand,
        family_name="AUVpredModel",
        family_steps=auv["steps"],
        family_maps=auv["maps"],
        detailed_df=auv_detailed,
        temp_stack=x,
        temp_mask=temp_mask,
        out_png=plots_dir / "AUVpredModel_match_examples.png",
    )

    # Decision gate for inferred physical-axis export.
    viability = viability_decision(
        best_eval=best_eval,
        mask_threshold=args.viability_mask_iou,
        pred_mean_threshold=args.viability_pred_mean_corr,
        auv_mean_threshold=args.viability_auv_mean_corr,
        min_corr_threshold=args.viability_min_corr,
    )

    inferred_export = None
    axes_meta_payload: Dict[str, object] | None = None
    if viability["overall_pass"] and bool(args.export_full_inferred_figures):
        axes_meta = inferred_axes_from_registration(
            cand=best_cand,
            hres_lat=np.asarray(pred["lat"], dtype=np.float64),
            hres_lon=np.asarray(pred["lon"], dtype=np.float64),
            out_h=temp_mask.shape[0],
            out_w=temp_mask.shape[1],
            axis_mode=str(args.inferred_axis_mode),
        )
        axes_meta_payload = {
            "axis_mode_used": str(axes_meta["axis_mode_used"][0]),
            "lat_mid_deg": float(axes_meta["lat_mid_deg"][0]),
            "lon_mid_deg": float(axes_meta["lon_mid_deg"][0]),
            "km_per_deg_lat": float(axes_meta["km_per_deg_lat"][0]),
            "km_per_deg_lon": float(axes_meta["km_per_deg_lon"][0]),
            "utm_zone": float(axes_meta["utm_zone"][0]) if np.isfinite(float(axes_meta["utm_zone"][0])) else None,
            "utm_hemisphere": str(axes_meta["utm_hemisphere"][0]),
            "lon_min_inferred": float(np.min(axes_meta["lon_inferred"])),
            "lon_max_inferred": float(np.max(axes_meta["lon_inferred"])),
            "lat_min_inferred": float(np.min(axes_meta["lat_inferred"])),
            "lat_max_inferred": float(np.max(axes_meta["lat_inferred"])),
            "x_km_min_inferred": float(np.min(axes_meta["x_km_inferred"])),
            "x_km_max_inferred": float(np.max(axes_meta["x_km_inferred"])),
            "y_km_min_inferred": float(np.min(axes_meta["y_km_inferred"])),
            "y_km_max_inferred": float(np.max(axes_meta["y_km_inferred"])),
        }
        scales = load_scale_bounds()
        inferred_export = export_inferred_figures(
            out_root=out_root,
            x_stack=x,
            x_norm_stack=x_norm,
            mask=temp_mask,
            axes_meta=axes_meta,
            scale_bounds=scales,
        )

    # Write compact best-candidate table.
    pd.DataFrame(
        [
            {
                "x0": best_cand.x0,
                "y0": best_cand.y0,
                "w": best_cand.w,
                "h": best_cand.h,
                "x1": best_cand.x1,
                "y1": best_cand.y1,
                "mask_iou": float(best_eval["mask_iou"]),
                "pred_mean_best_corr": float(best_eval["pred_mean_best_corr"]),
                "pred_min_best_corr": float(best_eval["pred_min_best_corr"]),
                "auv_mean_best_corr": float(best_eval["auv_mean_best_corr"]),
                "auv_min_best_corr": float(best_eval["auv_min_best_corr"]),
                "combined_score": float(best_eval["combined_score"]),
                "viability_overall_pass": bool(viability["overall_pass"]),
            }
        ]
    ).to_csv(tables_dir / "best_candidate_summary.csv", index=False)

    # Main report.
    dataset_info = {
        "temp_stack_path": to_rel(Path(str(temp["x_path"]))),
        "temp_norm_path": to_rel(Path(str(temp["x_norm_path"]))),
        "temp_mask_path": to_rel(Path(str(temp["mask_path"]))),
    }
    write_report(
        out_root=out_root,
        dataset_info=dataset_info,
        best_cand=best_cand,
        best_eval=best_eval,
        viability=viability,
        pred_df=pred_detailed,
        auv_df=auv_detailed,
        pred_stability=pred_stability,
        auv_stability=auv_stability,
        inferred_export=inferred_export,
    )

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "output_root": to_rel(out_root),
        "script": to_rel(Path(__file__)),
        "inputs": {
            "temp_stack": to_rel(Path(str(temp["x_path"]))),
            "temp_norm_stack": to_rel(Path(str(temp["x_norm_path"]))),
            "temp_mask": to_rel(Path(str(temp["mask_path"]))),
            "pred_family_pattern": str(TEST_C4_DIR / PRED_GLOB),
            "auv_family_pattern": str(TEST_C4_DIR / AUV_GLOB),
            "netcdf_summary_csv": to_rel(NETCDF_SUMMARY_CSV),
            "hres_bbox_reference": find_hres_bbox(NETCDF_SUMMARY_CSV),
        },
        "method": {
            "search_family": "axis_aligned_crop_plus_linear_resample",
            "stage1_width_step": int(args.coarse_width_step),
            "stage1_height_step": int(args.coarse_height_step),
            "stage2_topk_refine": int(args.topk_refine),
            "temperature_topk_eval": int(args.topk_temp_eval),
            "matching_rule": "best Pearson correlation across 300 tempIBHRes days per reference step",
            "inferred_axis_mode_requested": str(args.inferred_axis_mode),
        },
        "best_transformation": {
            "x0_0based": int(best_cand.x0),
            "y0_0based": int(best_cand.y0),
            "w": int(best_cand.w),
            "h": int(best_cand.h),
            "x1_0based": int(best_cand.x1),
            "y1_0based": int(best_cand.y1),
            "x_range_1based": [int(best_cand.x0 + 1), int(best_cand.x1 + 1)],
            "y_range_1based": [int(best_cand.y0 + 1), int(best_cand.y1 + 1)],
        },
        "best_metrics": {
            "mask_iou": float(best_eval["mask_iou"]),
            "mask_dice": float(best_eval["mask_dice"]),
            "pred_mean_best_corr": float(best_eval["pred_mean_best_corr"]),
            "pred_min_best_corr": float(best_eval["pred_min_best_corr"]),
            "auv_mean_best_corr": float(best_eval["auv_mean_best_corr"]),
            "auv_min_best_corr": float(best_eval["auv_min_best_corr"]),
            "combined_score": float(best_eval["combined_score"]),
        },
        "viability": viability,
        "inferred_axes": axes_meta_payload,
        "outputs": {
            "tables_dir": to_rel(tables_dir),
            "plots_dir": to_rel(plots_dir),
            "report_md": to_rel(out_root / "TEMPIBHRES_HRES_REGISTRATION_REPORT.md"),
            "inferred_export": inferred_export,
        },
        "notes": {
            "native_tempibhres_georef_claim": "not asserted",
            "axes_labeling_policy": "inferred axes are explicitly labeled as inferred from HRes registration",
            "core_pipeline_modified": False,
        },
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[OK] out_root={out_root}")
    print(
        "[OK] best_transform="
        f"x0={best_cand.x0},y0={best_cand.y0},w={best_cand.w},h={best_cand.h},"
        f"mask_iou={float(best_eval['mask_iou']):.6f},"
        f"pred_mean_corr={float(best_eval['pred_mean_best_corr']):.6f},"
        f"auv_mean_corr={float(best_eval['auv_mean_best_corr']):.6f}"
    )
    print(f"[OK] viability_overall_pass={viability['overall_pass']}")


if __name__ == "__main__":
    main()
