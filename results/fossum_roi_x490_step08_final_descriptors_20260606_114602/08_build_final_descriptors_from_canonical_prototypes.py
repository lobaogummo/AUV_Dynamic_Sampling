"""Step08: build final descriptor library from canonical ROI x490 prototypes.

This stage is intentionally downstream-only:
- audits the older descriptor logic before producing current outputs;
- reads Step00, Step05 and existing Step07-CV outputs;
- computes descriptors only on canonical class prototypes and class members;
- does not use October TEMPpred/STD to build descriptors;
- does not rerun clustering, CV, planner, or model training.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from scipy import ndimage as ndi

try:
    from skimage.filters import threshold_otsu

    HAS_SKIMAGE = True
except Exception:
    threshold_otsu = None
    HAS_SKIMAGE = False


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"
DEFAULT_STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_STEP05 = RESULTS_ROOT / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
DEFAULT_STEP06 = RESULTS_ROOT / "october_surface_temppred_std_roi_x490_20260511_155923"

EXPECTED_CLASSES = 6
EXPECTED_SHAPE = (72, 117)
EXPECTED_VALID_CELLS = 8004
EXPECTED_CLASS_SIZES = [41, 70, 50, 107, 30, 72]

INTEREST_WEIGHTS = {"boundary": 0.4, "gradient": 0.4, "heterogeneity": 0.2}
BOUNDARY_DISTANCE_RADII_CELLS = [1, 2, 3, 5, 8]


@dataclass(frozen=True)
class Inputs:
    step00: Path
    step05: Path
    step06: Path
    step07: Path
    output_dir: Path


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return None if not math.isfinite(value) else value
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finite_float(value: Any, default: float = float("nan")) -> float:
    try:
        return float(value)
    except Exception:
        return default


def find_latest_step07(results_root: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        step07 = explicit.expanduser().resolve()
        if not step07.exists():
            raise FileNotFoundError(f"Explicit Step07 path does not exist: {step07}")
        return step07

    patterns = [
        "fossum_roi_x490_step07_cv_analysis_*",
        "fossum_roi_x490_step07_cv_notebook_faithful_*",
    ]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend([p for p in results_root.glob(pattern) if p.is_dir()])
    if not candidates:
        raise FileNotFoundError("No Step07-CV output folder found under results/.")

    def score(path: Path) -> tuple[float, str]:
        csvs = [
            path / "cv_features_global_seed11_image_only.csv",
            path / "tables" / "cv_features_global_seed11_image_only.csv",
            path / "step07_cv_prototype_metrics.csv",
        ]
        has_core = any(p.exists() for p in csvs)
        return (path.stat().st_mtime + (1_000_000 if has_core else 0), path.name)

    candidates.sort(key=score, reverse=True)
    return candidates[0].resolve()


def required_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing required {label}: {path}")
    return path


def maybe_file(path: Path) -> Path | None:
    return path if path.exists() else None


def csv_first_existing(step07: Path, names: list[str]) -> Path | None:
    for name in names:
        for candidate in [step07 / name, step07 / "tables" / name]:
            if candidate.exists():
                return candidate
    return None


def load_step07_bundle(step07: Path) -> dict[str, Any]:
    files = {
        "image_only_global": csv_first_existing(
            step07,
            ["step07_cv_prototype_metrics.csv", "cv_features_global_seed11_image_only.csv"],
        ),
        "simple_global": csv_first_existing(step07, ["cv_features_global_seed11_simple.csv"]),
        "class_metrics_summary": csv_first_existing(step07, ["step07_cv_class_metrics_summary.csv"]),
        "prototype_similarity": csv_first_existing(step07, ["step07_cv_prototype_similarity.csv"]),
        "member_residuals": csv_first_existing(step07, ["step07_cv_member_to_prototype_residuals.csv"]),
        "substructure": csv_first_existing(step07, ["step07_cv_substructure_diagnostics.csv"]),
        "report": maybe_file(step07 / "step07_cv_report.md")
        or maybe_file(step07 / "step07_cv_notebook_faithful_report.md"),
        "summary": maybe_file(step07 / "step07_cv_summary.md")
        or maybe_file(step07 / "step07_cv_notebook_faithful_summary.md"),
        "checks": maybe_file(step07 / "step07_cv_notebook_faithful_checks.json")
        or maybe_file(step07 / "step07_cv_checks.json"),
    }
    data: dict[str, Any] = {"dir": step07, "files": {k: str(v) if v else "" for k, v in files.items()}}
    if files["image_only_global"]:
        data["image_only_global_df"] = pd.read_csv(files["image_only_global"])
    else:
        data["image_only_global_df"] = pd.DataFrame()
    if files["simple_global"]:
        data["simple_global_df"] = pd.read_csv(files["simple_global"])
    else:
        data["simple_global_df"] = pd.DataFrame()
    if files["checks"]:
        data["checks_payload"] = read_json(files["checks"])
    else:
        data["checks_payload"] = {}
    data["available_optional_outputs"] = {k: bool(v) for k, v in files.items()}
    return data


def normalize_regime_label(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "homogeneo": "homogeneous",
        "homogeneous": "homogeneous",
        "gradiente_unico": "single_gradient",
        "single_gradient": "single_gradient",
        "multi_regime": "multi_regime",
        "multiregime": "multi_regime",
    }
    return aliases.get(text, text if text else "unknown")


def old_descriptor_logic_audit(output_dir: Path) -> dict[str, Any]:
    """Summarize older descriptor code and outputs found in this repository."""
    search_roots = [ROOT / "scripts", ROOT / "notebooks", ROOT / "results"]
    keywords = [
        "descriptor",
        "boundary_score",
        "gradient_magnitude",
        "heterogeneity",
        "representative",
        "interest_map",
        "boundary_map",
        "gradient_map",
        "image_only",
        "hsl",
        "gmm",
        "segmentation",
        "member_to_prototype",
        "residuals",
    ]
    suffixes = {".py", ".ipynb", ".md", ".json", ".csv", ".txt"}
    hits: list[dict[str, Any]] = []
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            lower = str(path.relative_to(ROOT)).lower()
            if any(k.lower() in lower for k in keywords):
                hits.append({"path": str(path.relative_to(ROOT)), "reason": "name_match"})
                continue
            if path.suffix.lower() in {".py", ".md", ".json"} and path.stat().st_size < 2_000_000:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore").lower()
                except Exception:
                    continue
                matched = [k for k in keywords if k.lower() in text]
                if matched:
                    hits.append(
                        {
                            "path": str(path.relative_to(ROOT)),
                            "reason": "content_match",
                            "keywords": matched[:8],
                        }
                    )

    important_paths = [
        "scripts/09_export_cv_prototypes.py",
        "scripts/10_seed11_cv_analysis.py",
        "scripts/cv_seed11_utils.py",
        "scripts/11_prototype_characterization.py",
        "scripts/prototype_characterization_utils.py",
        "notebooks/seed11_computer_vision_colab.ipynb",
        "notebooks/seed11_computer_vision_colab.localrun.ipynb",
        "results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/run_report.md",
        "results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/pixel_descriptors_all.csv",
        "results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/region_descriptors_all.csv",
        "results/validation_descriptor_audit_v2_20260403_215918/AUDIT_REPORT.md",
    ]
    important_found = [p for p in important_paths if (ROOT / p).exists()]
    components = [
        {
            "component": "CV prototype export",
            "where": "scripts/09_export_cv_prototypes.py",
            "old_inputs": "compact/final-working prototype arrays, mask_common, clean PNG export settings",
            "old_outputs": "prototype .npy, _mask.npy and clean PNGs under computer_vision_exports_seed11",
            "logic": "exported prototype arrays and alpha-masked clean PNGs for downstream image-only CV.",
            "decision": "REUSE_WITH_ADAPTATION",
            "adaptation": "Step08 reads Step05 canonical_prototypes directly; clean PNG export remains methodological reference via Step07.",
        },
        {
            "component": "Image-only CV labels",
            "where": "scripts/10_seed11_cv_analysis.py, scripts/cv_seed11_utils.py, notebooks/seed11_computer_vision_colab.ipynb",
            "old_inputs": "clean PNGs and R-B color score; optional simple array metrics.",
            "old_outputs": "cv_features_global_seed11_image_only.csv and local image-only CSVs.",
            "logic": "Otsu on R-B score, region balance/coherence, gradient p90 and image-only regime labels.",
            "decision": "REUSE_WITH_ADAPTATION",
            "adaptation": "Step08 consumes the latest Step07-CV image-only CSV; it does not rerun CV.",
        },
        {
            "component": "Pixel-wise prototype descriptors",
            "where": "scripts/11_prototype_characterization.py, scripts/prototype_characterization_utils.py",
            "old_inputs": "compact_model prototype_mean_norm/prototype_std_norm, lat/lon grids, mask_common, image-only regime labels.",
            "old_outputs": "pixel_descriptors_all.csv, region_descriptors_all.csv, per-class rasters boundary_score/gradient_magnitude/region_id.",
            "logic": "multi_regime classes only: Otsu segmentation + interface boundary + distance-to-boundary + 0.65 gradient/0.35 proximity boundary_score; homogeneous classes: single region with zero boundary.",
            "decision": "REUSE_WITH_ADAPTATION",
            "adaptation": "Same segmentation/boundary backbone, adapted to 6 ROI x490 canonical classes, X/Y km grids, normalized maps, planner-ready interest map.",
        },
        {
            "component": "Descriptor validation audit",
            "where": "results/validation_descriptor_audit_v2_20260403_215918",
            "old_inputs": "old pixel/region descriptors.",
            "old_outputs": "descriptor usefulness, discriminative scores, proxy top-k figures.",
            "logic": "boundary score, n_regions and region entropy were most discriminative; proxy top-k favored gradient/boundary-enriched maps.",
            "decision": "REUSE_AS_IS",
            "adaptation": "Use as evidence for retaining boundary, gradient, segmentation and entropy in final descriptors.",
        },
        {
            "component": "TEMPpred/tempRes old branches",
            "where": "legacy validation branches and tempRes-related outputs",
            "old_inputs": "old tempRes/HRes/October branches.",
            "old_outputs": "diagnostic comparisons, not final canonical descriptor library.",
            "logic": "useful for historical validation only.",
            "decision": "DO_NOT_REUSE",
            "adaptation": "Step08 does not use tempRes, TEMPpred, or STD for descriptor construction.",
        },
        {
            "component": "Interest map",
            "where": "No final reusable interest_map implementation found in scripts.",
            "old_inputs": "Validation audit had proxy top-k maps, but no canonical interest_map raster.",
            "old_outputs": "proxy diagnostics only.",
            "logic": "No stable old production logic found.",
            "decision": "REUSE_WITH_ADAPTATION",
            "adaptation": "Initial documented map: 0.4 boundary + 0.4 gradient + 0.2 heterogeneity; weights are not optimized.",
        },
    ]
    answers = {
        "1_where_logic_was_implemented": [
            "scripts/11_prototype_characterization.py",
            "scripts/prototype_characterization_utils.py",
            "scripts/10_seed11_cv_analysis.py",
            "scripts/cv_seed11_utils.py",
            "notebooks/seed11_computer_vision_colab.ipynb",
        ],
        "2_scripts_notebooks": important_found,
        "3_old_inputs": [
            "compact_model_final.npz prototype_mean_norm/prototype_std_norm",
            "mask_common and lat/lon grids",
            "clean PNG prototype exports",
            "image-only CV CSVs",
        ],
        "4_old_outputs": [
            "pixel_descriptors_all.csv",
            "region_descriptors_all.csv",
            "boundary_score.npy",
            "gradient_magnitude.npy",
            "region_label_id.npy",
            "distance_to_boundary.npy",
            "prototype_summary.csv",
        ],
        "5_descriptors_calculated": [
            "temp_mean/temp_std",
            "region labels and connected region ids",
            "gradient_magnitude and gradient_direction",
            "boundary_mask, distance_to_boundary, boundary_score",
            "region aggregates such as temp contrast and area entropy in validation audit",
        ],
        "6_calculation_summary": {
            "gradient_magnitude": "np.gradient on prototype field using coordinate axes when available; magnitude hypot(gx, gy).",
            "boundary_score": "multi-regime 0.65*gradient_norm + 0.35*boundary_proximity; homogeneous zero.",
            "heterogeneity": "not a standalone raster in old production; approximated through temp_std/region entropy/audit diagnostics.",
            "prototype_similarity": "old pipeline stored similarity matrices and validation audits; not a core pixel descriptor.",
            "segmentation": "label-driven: homogeneous single region; multi-regime Otsu low/high regions.",
            "representative_zones": "old validation used proxy top-k; no stable named representative_zone raster found.",
            "interest_priority_maps": "proxy top-k diagnostics existed; no canonical interest_map output found.",
        },
        "7_applied_to": "Mostly prototypes and local subclass prototypes; not new images in the final descriptor characterization stage.",
        "8_thresholds": [
            "Otsu threshold for multi-regime prototype segmentation",
            "gradient normalization p95",
            "boundary proximity distance p75",
            "no boundary proxy for homogeneous classes",
        ],
        "9_normalizations": "Old boundary_score normalized to [0,1] by p95 gradient and p75 distance proximity; Step08 min-max normalizes final maps per class over valid mask.",
        "10_tempres_dependencies": "No reusable final descriptor logic requires tempRes; tempRes branches are diagnostic and excluded.",
        "11_reusable_directly": ["label-driven segmentation", "gradient map", "boundary score formula", "pixel/region descriptor pattern"],
        "12_needs_adaptation": ["ROI x490 paths/shapes/classes", "X/Y km coordinates", "6 class sizes", "planner-ready map stack", "residual representativity from Step05 assignments"],
    }
    audit = {
        "generated_at": datetime.now().isoformat(),
        "search_roots": [str(p) for p in search_roots],
        "important_found": important_found,
        "n_name_or_content_hits": len(hits),
        "sample_hits": hits[:120],
        "components": components,
        "answers": answers,
    }
    write_json(output_dir / "step08_old_descriptor_logic_audit.json", audit)
    lines = [
        "# Step08 Old Descriptor Logic Audit",
        "",
        "## Found Core Sources",
    ]
    lines.extend([f"- `{p}`" for p in important_found])
    lines.extend(["", "## Decisions"])
    for c in components:
        lines.extend(
            [
                f"### {c['component']}",
                f"- Where: `{c['where']}`",
                f"- Decision: **{c['decision']}**",
                f"- Logic: {c['logic']}",
                f"- Adaptation: {c['adaptation']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Direct Answers",
            "",
            f"- Logic location: {', '.join(answers['1_where_logic_was_implemented'])}",
            f"- Old outputs: {', '.join(answers['4_old_outputs'])}",
            f"- Thresholds: {', '.join(answers['8_thresholds'])}",
            f"- tempRes dependency: {answers['10_tempres_dependencies']}",
            "",
            "## Reuse Verdict",
            "- REUSE_AS_IS: validation audit evidence that boundary/region entropy are useful.",
            "- REUSE_WITH_ADAPTATION: image-only labels, Otsu segmentation, boundary score and gradient descriptors.",
            "- DO_NOT_REUSE: tempRes/TEMPpred/STD/planner branches for this descriptor-library step.",
        ]
    )
    (output_dir / "step08_old_descriptor_logic_audit.md").write_text("\n".join(lines), encoding="utf-8")
    return audit


def axis_from_grid(grid: np.ndarray, axis: int) -> np.ndarray:
    values = np.nanmean(grid, axis=1 if axis == 0 else 0)
    if values.ndim != 1 or values.size < 2 or not np.all(np.isfinite(np.diff(values))):
        return np.arange(grid.shape[axis], dtype=np.float32)
    if np.any(np.abs(np.diff(values)) < 1e-12):
        return np.arange(grid.shape[axis], dtype=np.float32)
    return values.astype(np.float32, copy=False)


def compute_gradient(field: np.ndarray, valid: np.ndarray, x_km: np.ndarray, y_km: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    grad_mag = np.full(field.shape, np.nan, dtype=np.float32)
    grad_dir = np.full(field.shape, np.nan, dtype=np.float32)
    if not np.any(valid):
        return grad_mag, grad_dir
    fill_value = float(np.nanmean(field[valid]))
    filled = np.where(valid, field, fill_value).astype(np.float32, copy=False)
    y_axis = axis_from_grid(y_km, axis=0)
    x_axis = axis_from_grid(x_km, axis=1)
    try:
        gy, gx = np.gradient(filled, y_axis, x_axis, edge_order=1)
    except Exception:
        gy, gx = np.gradient(filled)
    grad_mag = np.hypot(gx, gy).astype(np.float32)
    grad_dir = np.arctan2(gy, gx).astype(np.float32)
    grad_mag[~valid] = np.nan
    grad_dir[~valid] = np.nan
    return grad_mag, grad_dir


def minmax01(arr: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    vals = arr[valid & np.isfinite(arr)]
    if vals.size == 0:
        out[valid] = 0.0
        return out, {"min": float("nan"), "max": float("nan"), "constant": 1.0}
    mn = float(np.nanmin(vals))
    mx = float(np.nanmax(vals))
    if mx - mn <= 1e-12:
        out[valid] = 0.0
        return out, {"min": mn, "max": mx, "constant": 1.0}
    out[valid] = ((arr[valid] - mn) / (mx - mn)).astype(np.float32)
    return out, {"min": mn, "max": mx, "constant": 0.0}


def percentile_threshold(arr: np.ndarray, valid: np.ndarray, pct: float) -> float:
    vals = arr[valid & np.isfinite(arr)]
    if vals.size == 0:
        return float("nan")
    return float(np.nanpercentile(vals, pct))


def otsu_threshold(field: np.ndarray, valid: np.ndarray) -> tuple[float, str]:
    vals = field[valid & np.isfinite(field)].astype(np.float32, copy=False)
    if vals.size == 0:
        return float("nan"), "empty"
    threshold = float(np.nanmean(vals))
    method = "mean_fallback"
    if HAS_SKIMAGE and threshold_otsu is not None and np.unique(vals).size > 1:
        try:
            threshold = float(threshold_otsu(vals))
            method = "otsu"
        except Exception:
            method = "mean_fallback"
    return threshold, method


def segment_cold_warm_neutral(field: np.ndarray, valid: np.ndarray, regime_label: str) -> dict[str, Any]:
    vals = field[valid & np.isfinite(field)]
    labels = np.full(field.shape, -1, dtype=np.int16)
    if vals.size == 0:
        return {"labels": labels, "thresholds": [], "method": "empty"}
    if regime_label == "homogeneous":
        labels[valid] = 1
        return {"labels": labels, "thresholds": [], "method": "homogeneous_single_region"}
    p33, p67 = np.nanpercentile(vals, [33.333, 66.667])
    if regime_label == "multi_regime":
        t, method = otsu_threshold(field, valid)
        if np.isfinite(t):
            low_vals = vals[vals < t]
            high_vals = vals[vals >= t]
            p33 = float(np.nanmedian(low_vals)) if low_vals.size else float(p33)
            p67 = float(np.nanmedian(high_vals)) if high_vals.size else float(p67)
            method = f"otsu_guided_tertiles:{method}"
        else:
            method = "tertiles"
    else:
        method = "tertiles"
    labels[valid & (field <= p33)] = 0
    labels[valid & (field > p33) & (field < p67)] = 1
    labels[valid & (field >= p67)] = 2
    return {"labels": labels, "thresholds": [float(p33), float(p67)], "method": method}


def boundary_mask_from_binary(labels: np.ndarray, valid: np.ndarray) -> np.ndarray:
    boundary = np.zeros(labels.shape, dtype=bool)
    for dy, dx in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        shifted_lbl = np.roll(labels, shift=(dy, dx), axis=(0, 1))
        shifted_valid = np.roll(valid, shift=(dy, dx), axis=(0, 1))
        diff = (labels != shifted_lbl) & valid & shifted_valid & (labels >= 0) & (shifted_lbl >= 0)
        if dy > 0:
            diff[:dy, :] = False
        elif dy < 0:
            diff[dy:, :] = False
        if dx > 0:
            diff[:, :dx] = False
        elif dx < 0:
            diff[:, dx:] = False
        boundary |= diff
    return boundary


def distance_to_boundary(boundary: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.full(boundary.shape, np.nan, dtype=np.float32)
    if not np.any(boundary):
        return out
    dist = ndi.distance_transform_edt(~boundary).astype(np.float32)
    dist[~valid] = np.nan
    return dist


def robust_grid_spacing_km(x_km: np.ndarray, y_km: np.ndarray) -> tuple[float, float, bool, dict[str, Any]]:
    """Estimate regular ROI grid spacing in km for distance-transform sampling."""

    def axis_spacing(grid: np.ndarray, axis: int) -> tuple[float, float, bool]:
        axis_values = axis_from_grid(grid, axis=axis)
        diffs = np.abs(np.diff(axis_values.astype(float)))
        diffs = diffs[np.isfinite(diffs) & (diffs > 1e-9)]
        if diffs.size == 0:
            return float("nan"), float("nan"), False
        med = float(np.nanmedian(diffs))
        rel_mad = float(np.nanmedian(np.abs(diffs - med)) / max(med, 1e-9))
        return med, rel_mad, bool(rel_mad <= 0.05)

    dx, dx_rel_mad, ok_x = axis_spacing(x_km, axis=1)
    dy, dy_rel_mad, ok_y = axis_spacing(y_km, axis=0)
    ok = bool(ok_x and ok_y and np.isfinite(dx) and np.isfinite(dy) and dx > 0 and dy > 0)
    meta = {
        "dx_km": dx,
        "dy_km": dy,
        "dx_relative_mad": dx_rel_mad,
        "dy_relative_mad": dy_rel_mad,
        "reliable": ok,
        "method": "median adjacent X_km/Y_km spacing; reliable if relative MAD <= 0.05 on both axes",
    }
    return dy, dx, ok, meta


def boundary_distance_descriptors(
    boundary: np.ndarray,
    valid: np.ndarray,
    x_km: np.ndarray,
    y_km: np.ndarray,
    radii_cells: list[int],
) -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray], dict[str, Any]]:
    """Pure boundary-distance descriptors using the existing boundary mask.

    Scores are reward-like proximity bands. They are intentionally separate
    from the older blended `boundary_score`, which mixes gradient intensity
    with boundary proximity.
    """
    dist_cells = np.full(boundary.shape, np.nan, dtype=np.float32)
    dist_km = np.full(boundary.shape, np.nan, dtype=np.float32)
    scores: dict[int, np.ndarray] = {}
    dy_km, dx_km, spacing_ok, spacing_meta = robust_grid_spacing_km(x_km, y_km)
    has_boundary = bool(np.any(boundary & valid))
    if has_boundary:
        dist_cells = ndi.distance_transform_edt(~boundary).astype(np.float32)
        dist_cells[~valid] = np.nan
        if spacing_ok:
            dist_km = ndi.distance_transform_edt(~boundary, sampling=(dy_km, dx_km)).astype(np.float32)
            dist_km[~valid] = np.nan
    for radius in radii_cells:
        score = np.full(boundary.shape, np.nan, dtype=np.float32)
        if has_boundary:
            score[valid] = np.exp(-((dist_cells[valid] ** 2) / (2.0 * float(radius) ** 2))).astype(np.float32)
        else:
            score[valid] = 0.0
        score[~valid] = np.nan
        scores[int(radius)] = score
    radius_km = {str(r): float(r * np.mean([dx_km, dy_km])) for r in radii_cells} if spacing_ok else {}
    meta = {
        "has_boundary": has_boundary,
        "radii_cells": [int(r) for r in radii_cells],
        "radii_km_equivalent": radius_km,
        "distance_cells_unit": "grid cells / pixels",
        "distance_km_available": bool(spacing_ok),
        "grid_spacing": spacing_meta,
        "score_formula": "exp(-(distance_cells**2)/(2*radius_cells**2))",
    }
    return dist_cells, dist_km, scores, meta


def old_style_boundary_score(grad_mag: np.ndarray, boundary: np.ndarray, valid: np.ndarray, regime_label: str) -> tuple[np.ndarray, dict[str, float]]:
    out = np.full(grad_mag.shape, np.nan, dtype=np.float32)
    gvals = grad_mag[valid & np.isfinite(grad_mag)]
    grad_p95 = max(float(np.nanpercentile(gvals, 95)) if gvals.size else 0.0, 1e-6)
    grad_norm = np.clip(grad_mag / grad_p95, 0.0, 1.0).astype(np.float32)
    if regime_label == "homogeneous":
        out[valid] = 0.0
        return out, {"gradient_p95": grad_p95, "distance_p75": float("nan"), "mode": "old_homogeneous_zero_boundary"}
    if regime_label == "single_gradient":
        out[valid] = np.clip(grad_norm[valid] * 0.35, 0.0, 1.0)
        return out, {"gradient_p95": grad_p95, "distance_p75": float("nan"), "mode": "old_single_gradient_capped_gradient_proxy"}
    dist = distance_to_boundary(boundary, valid)
    dvals = dist[valid & np.isfinite(dist)]
    d75 = max(float(np.nanpercentile(dvals, 75)) if dvals.size else 0.0, 1e-6)
    proximity = np.exp(-dist / d75).astype(np.float32)
    out[valid] = np.clip((0.65 * grad_norm[valid]) + (0.35 * proximity[valid]), 0.0, 1.0)
    return out, {"gradient_p95": grad_p95, "distance_p75": d75, "mode": "old_multi_regime_065_gradient_035_proximity"}


def local_variance_map(field: np.ndarray, valid: np.ndarray, size: int = 5) -> np.ndarray:
    fill = float(np.nanmean(field[valid])) if np.any(valid) else 0.0
    arr = np.where(valid, field, fill).astype(np.float32)
    mean = ndi.uniform_filter(arr, size=size, mode="nearest")
    mean2 = ndi.uniform_filter(arr * arr, size=size, mode="nearest")
    var = np.maximum(mean2 - mean * mean, 0.0).astype(np.float32)
    var[~valid] = np.nan
    return var


def entropy_score(field: np.ndarray, valid: np.ndarray, bins: int = 16) -> float:
    vals = field[valid & np.isfinite(field)]
    if vals.size < 2:
        return 0.0
    hist, _ = np.histogram(vals, bins=bins)
    p = hist.astype(np.float64)
    p = p[p > 0] / max(float(p.sum()), 1.0)
    ent = -float(np.sum(p * np.log2(p)))
    return ent / math.log2(bins)


def region_label_from_centroid(cx: float, cy: float, valid: np.ndarray, x_km: np.ndarray, y_km: np.ndarray) -> str:
    if not (math.isfinite(cx) and math.isfinite(cy)):
        return "mixed"
    xv = x_km[valid]
    yv = y_km[valid]
    x1, x2 = np.nanpercentile(xv, [33.333, 66.667])
    y1, y2 = np.nanpercentile(yv, [33.333, 66.667])
    x_mid = x1 <= cx <= x2
    y_mid = y1 <= cy <= y2
    if x_mid and y_mid:
        return "central"
    if not x_mid and y_mid:
        return "west" if cx < x1 else "east"
    if x_mid and not y_mid:
        return "south" if cy < y1 else "north"
    return "mixed"


def centroid_xy(mask: np.ndarray, x_km: np.ndarray, y_km: np.ndarray) -> tuple[float, float]:
    if not np.any(mask):
        return float("nan"), float("nan")
    return float(np.nanmean(x_km[mask])), float(np.nanmean(y_km[mask]))


def orientation_proxy(mask: np.ndarray, x_km: np.ndarray, y_km: np.ndarray) -> str:
    if int(np.sum(mask)) < 3:
        return "none"
    xs = x_km[mask].astype(np.float64)
    ys = y_km[mask].astype(np.float64)
    coords = np.c_[xs - np.nanmean(xs), ys - np.nanmean(ys)]
    cov = np.cov(coords, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    v = vecs[:, int(np.argmax(vals))]
    angle = abs(math.degrees(math.atan2(float(v[1]), float(v[0]))))
    if angle > 90:
        angle = 180 - angle
    if angle < 22.5:
        return "east_west"
    if angle > 67.5:
        return "north_south"
    return "diagonal"


def component_stats(mask: np.ndarray) -> tuple[int, float]:
    labeled, n = ndi.label(mask)
    if n == 0:
        return 0, 0.0
    counts = np.bincount(labeled.ravel())
    largest = int(counts[1:].max()) if counts.size > 1 else 0
    denom = int(np.sum(mask))
    return int(n), float(largest / denom) if denom else 0.0


def qualitative_label(mean: float, std: float, regime: str) -> str:
    thermal = "cold" if mean < -0.25 else "warm" if mean > 0.25 else "neutral"
    if regime == "homogeneous":
        return f"{thermal}_homogeneous"
    if regime == "multi_regime":
        return "frontal" if std > 0.25 else "mixed"
    if std > 0.35:
        return "heterogeneous"
    return "transition"


def class_label(class_id: int, regime: str) -> str:
    return f"class_{class_id:02d}_{regime}"


def representative_members(
    X_norm: np.ndarray,
    assignments: pd.DataFrame,
    class_id: int,
    prototype: np.ndarray,
    valid: np.ndarray,
) -> dict[str, Any]:
    cls = assignments[assignments["class_id"].astype(int) == int(class_id)].copy()
    rows = []
    for _, row in cls.iterrows():
        idx = int(row["image_idx_0_based"])
        arr = X_norm[idx]
        diff = arr[valid] - prototype[valid]
        rmse = float(np.sqrt(np.nanmean(diff * diff)))
        rows.append({"image_idx_0_based": idx, "day_index": int(row.get("day_index", idx + 1)), "date": str(row.get("date", "")), "rmse": rmse})
    df = pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)
    if df.empty:
        return {"df": df, "mean": float("nan"), "std": float("nan"), "max": float("nan"), "rep": [], "out": []}
    return {
        "df": df,
        "mean": float(df["rmse"].mean()),
        "std": float(df["rmse"].std(ddof=0)),
        "max": float(df["rmse"].max()),
        "rep": df.head(min(5, len(df)))["image_idx_0_based"].astype(int).tolist(),
        "out": df.tail(min(5, len(df)))["image_idx_0_based"].astype(int).tolist(),
    }


def build_representative_zone_map(
    field: np.ndarray,
    grad_norm: np.ndarray,
    boundary_norm: np.ndarray,
    hetero_norm: np.ndarray,
    valid: np.ndarray,
) -> np.ndarray:
    vals = field[valid & np.isfinite(field)]
    out = np.full(field.shape, np.nan, dtype=np.float32)
    if vals.size == 0:
        out[valid] = 0.0
        return out
    med = float(np.nanmedian(vals))
    mad = float(np.nanmedian(np.abs(vals - med)))
    scale = max(mad * 1.4826, 1e-6)
    centrality = np.exp(-np.abs(field - med) / scale).astype(np.float32)
    calm = 1.0 - np.clip(0.4 * grad_norm + 0.3 * boundary_norm + 0.3 * hetero_norm, 0.0, 1.0)
    out[valid] = np.clip(centrality[valid] * calm[valid], 0.0, 1.0)
    return out


def save_panel(maps: np.ndarray, titles: list[str], out_path: Path, cmap: str, vmin: float | None = 0, vmax: float | None = 1) -> None:
    n = maps.shape[0]
    cols = 3
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 3.8 * rows), squeeze=False)
    for i, ax in enumerate(axes.ravel()):
        if i >= n:
            ax.axis("off")
            continue
        im = ax.imshow(maps[i], origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(titles[i])
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_multimap_panel(
    prototypes: np.ndarray,
    gradient: np.ndarray,
    boundary: np.ndarray,
    boundary_distance_score: np.ndarray,
    heterogeneity: np.ndarray,
    segmentation: np.ndarray,
    repzone: np.ndarray,
    interest: np.ndarray,
    out_path: Path,
) -> None:
    n = prototypes.shape[0]
    labels = ["prototype", "gradient", "boundary", "boundary_dist_r3", "heterogeneity", "segmentation", "representative", "interest"]
    fig, axes = plt.subplots(n, len(labels), figsize=(3.1 * len(labels), 2.45 * n), squeeze=False)
    cmaps = ["coolwarm", "viridis", "magma", "magma", "plasma", "coolwarm", "Greens", "inferno"]
    arrays = [prototypes, gradient, boundary, boundary_distance_score, heterogeneity, segmentation, repzone, interest]
    proto_vlim = float(np.nanmax(np.abs(prototypes[np.isfinite(prototypes)])))
    for i in range(n):
        for j, label in enumerate(labels):
            ax = axes[i, j]
            arr = arrays[j][i]
            if label == "prototype":
                im = ax.imshow(arr, origin="lower", cmap=cmaps[j], vmin=-proto_vlim, vmax=proto_vlim, aspect="auto")
            elif label == "segmentation":
                im = ax.imshow(arr, origin="lower", cmap=ListedColormap(["#3A86FF", "#DDDDDD", "#FF8C42"]), vmin=0, vmax=2, aspect="auto")
            else:
                im = ax.imshow(arr, origin="lower", cmap=cmaps[j], vmin=0, vmax=1, aspect="auto")
            if i == 0:
                ax.set_title(label)
            ax.set_ylabel(f"class {i+1:02d}" if j == 0 else "")
            ax.set_xticks([])
            ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_rankings_figure(df: pd.DataFrame, out_path: Path) -> None:
    metrics = ["gradient_mean", "boundary_score", "heterogeneity_score", "interest_mean"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), squeeze=False)
    for ax, metric in zip(axes.ravel(), metrics):
        s = df.sort_values(metric, ascending=False)
        ax.bar(s["class_id"].astype(str), s[metric], color="#4C78A8")
        ax.set_title(metric)
        ax.set_xlabel("class")
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_parallel_coordinates(df: pd.DataFrame, out_path: Path) -> None:
    metrics = ["gradient_mean", "boundary_score", "heterogeneity_score", "cold_fraction", "warm_fraction", "interest_mean"]
    values = df[metrics].astype(float).copy()
    for col in metrics:
        mn, mx = values[col].min(), values[col].max()
        values[col] = 0.0 if mx - mn <= 1e-12 else (values[col] - mn) / (mx - mn)
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(metrics))
    for i, row in values.iterrows():
        ax.plot(x, row[metrics].to_numpy(), marker="o", label=f"class {int(df.loc[i, 'class_id']):02d}")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=25, ha="right")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(alpha=0.25)
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def make_descriptor_definitions() -> pd.DataFrame:
    rows = [
        ("gradient_mean/p90/p95/max", "Gradient intensity over canonical prototype", "old gradient_magnitude"),
        ("boundary_score", "Mean normalized boundary/front score", "old boundary_score adapted"),
        ("boundary_distance_cells", "Nearest-boundary Euclidean distance in grid cells", "new pure distance-to-boundary descriptor"),
        ("boundary_distance_km", "Nearest-boundary Euclidean distance in km when grid spacing is reliable", "new pure distance-to-boundary descriptor"),
        ("boundary_distance_score_r{radius}_cells", "Gaussian boundary proximity band exp(-(distance_cells^2)/(2*radius_cells^2))", "new radius-sensitive boundary band descriptor"),
        ("heterogeneity_score", "Mean of local variance and entropy-derived roughness", "new aggregation from old temp_std/entropy diagnostics"),
        ("cold/warm/neutral_fraction", "Fractions from prototype segmentation", "adapted Otsu/tertile segmentation"),
        ("representative_zone_map", "Calm central prototype zones", "adapted from old proxy top-k/representativity idea"),
        ("interest_map", "Planner-ready priority map", "new documented 0.4 boundary + 0.4 gradient + 0.2 heterogeneity"),
    ]
    return pd.DataFrame(rows, columns=["descriptor", "meaning", "old_logic_relation"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Step08 final descriptor library from ROI x490 canonical prototypes.")
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--step05", type=Path, default=DEFAULT_STEP05)
    parser.add_argument("--step06", type=Path, default=DEFAULT_STEP06)
    parser.add_argument("--step07", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    step00 = args.step00.resolve()
    step05 = args.step05.resolve()
    step06 = args.step06.resolve()
    step07 = find_latest_step07(args.output_root.resolve(), args.step07)
    out_dir = (args.output_root.resolve() / f"fossum_roi_x490_step08_final_descriptors_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    figures_dir = out_dir / "figures"
    figures_dir.mkdir()

    inputs = Inputs(step00=step00, step05=step05, step06=step06, step07=step07, output_dir=out_dir)
    audit = old_descriptor_logic_audit(out_dir)
    step07_bundle = load_step07_bundle(step07)

    prototypes_path = required_file(step05 / "canonical_prototypes.npy", "Step05 canonical_prototypes.npy")
    assignments_path = required_file(step05 / "canonical_assignments.csv", "Step05 canonical_assignments.csv")
    class_sizes_path = required_file(step05 / "canonical_class_sizes.csv", "Step05 canonical_class_sizes.csv")
    mask_path = required_file(step00 / "mask_common_roi_x490.npy", "Step00 mask_common_roi_x490.npy")
    lat_path = required_file(step00 / "LAT_roi_x490.npy", "Step00 LAT_roi_x490.npy")
    lon_path = required_file(step00 / "LON_roi_x490.npy", "Step00 LON_roi_x490.npy")
    x_path = required_file(step00 / "X_km_roi_x490.npy", "Step00 X_km_roi_x490.npy")
    y_path = required_file(step00 / "Y_km_roi_x490.npy", "Step00 Y_km_roi_x490.npy")
    bathy_path = required_file(step00 / "BATHY_roi_x490.npy", "Step00 BATHY_roi_x490.npy")
    norm_stats_path = required_file(step00 / "normalization_stats.json", "Step00 normalization_stats.json")
    x_norm_path = required_file(step00 / "X_surface_370_roi_x490_norm.npy", "Step00 X_surface_370_roi_x490_norm.npy")

    prototypes = np.load(prototypes_path).astype(np.float32)
    class_std_maps = np.load(step05 / "canonical_class_std_maps.npy").astype(np.float32) if (step05 / "canonical_class_std_maps.npy").exists() else np.zeros_like(prototypes)
    mask = np.load(mask_path).astype(bool)
    lat = np.load(lat_path).astype(np.float32)
    lon = np.load(lon_path).astype(np.float32)
    x_km = np.load(x_path).astype(np.float32)
    y_km = np.load(y_path).astype(np.float32)
    bathy = np.load(bathy_path).astype(np.float32)
    X_norm = np.load(x_norm_path).astype(np.float32)
    assignments = pd.read_csv(assignments_path)
    class_sizes_df = pd.read_csv(class_sizes_path)
    norm_stats = read_json(norm_stats_path)

    if prototypes.shape[0] != EXPECTED_CLASSES:
        raise ValueError(f"Expected {EXPECTED_CLASSES} prototypes, got {prototypes.shape}")
    if tuple(prototypes.shape[1:]) != EXPECTED_SHAPE:
        raise ValueError(f"Expected prototype shape {EXPECTED_SHAPE}, got {prototypes.shape[1:]}")
    if mask.shape != EXPECTED_SHAPE or int(mask.sum()) != EXPECTED_VALID_CELLS:
        raise ValueError(f"Unexpected mask shape/count: shape={mask.shape}, valid={int(mask.sum())}")
    sizes = class_sizes_df.sort_values("class_id")["n_days"].astype(int).tolist()
    if sizes != EXPECTED_CLASS_SIZES:
        raise ValueError(f"Unexpected class sizes: {sizes} != {EXPECTED_CLASS_SIZES}")

    image_df: pd.DataFrame = step07_bundle["image_only_global_df"]
    cv_by_name: dict[str, dict[str, Any]] = {}
    if not image_df.empty and "prototype_name" in image_df.columns:
        for _, row in image_df.iterrows():
            cv_by_name[str(row["prototype_name"])] = row.to_dict()

    n_classes, h, w = prototypes.shape
    gradient_maps = np.full((n_classes, h, w), np.nan, dtype=np.float32)
    boundary_maps = np.full_like(gradient_maps, np.nan)
    boundary_distance_cells_maps = np.full_like(gradient_maps, np.nan)
    boundary_distance_km_maps = np.full_like(gradient_maps, np.nan)
    boundary_distance_score_maps = {
        int(radius): np.full_like(gradient_maps, np.nan) for radius in BOUNDARY_DISTANCE_RADII_CELLS
    }
    heterogeneity_maps = np.full_like(gradient_maps, np.nan)
    cold_maps = np.full_like(gradient_maps, np.nan)
    warm_maps = np.full_like(gradient_maps, np.nan)
    representative_maps = np.full_like(gradient_maps, np.nan)
    interest_maps = np.full_like(gradient_maps, np.nan)
    segmentation_maps = np.full_like(gradient_maps, np.nan)

    descriptor_rows: list[dict[str, Any]] = []
    zone_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    thresholds_by_class: dict[str, Any] = {}
    all_residual_rows: list[pd.DataFrame] = []

    for i in range(n_classes):
        class_id = i + 1
        name = f"prototype_class_{class_id:02d}"
        proto = prototypes[i].astype(np.float32, copy=False)
        std_map = class_std_maps[i].astype(np.float32, copy=False)
        valid = mask & np.isfinite(proto)
        cv_row = cv_by_name.get(name, {})
        cv_regime = normalize_regime_label(cv_row.get("regime_label", "unknown"))
        # Thesis regime definition: only C01 and C06 contain two regimes.
        # C02-C05 are homogeneous, so smooth gradients must not be converted
        # into boundary proxies.
        regime = "multi_regime" if class_id in {1, 6} else "homogeneous"

        grad_mag, grad_dir = compute_gradient(proto, valid, x_km, y_km)
        grad_norm, grad_norm_meta = minmax01(grad_mag, valid)
        gradient_maps[i] = grad_norm
        high_grad_thr = percentile_threshold(grad_mag, valid, 90)
        high_grad_mask = valid & np.isfinite(grad_mag) & (grad_mag >= high_grad_thr)
        gx, gy = centroid_xy(high_grad_mask, x_km, y_km)

        seg = segment_cold_warm_neutral(proto, valid, regime)
        seg_labels = seg["labels"]
        segmentation_maps[i] = np.where(seg_labels >= 0, seg_labels.astype(np.float32), np.nan)
        cold_mask = valid & (seg_labels == 0)
        neutral_mask = valid & (seg_labels == 1)
        warm_mask = valid & (seg_labels == 2)
        cold_maps[i] = np.where(cold_mask, 1.0, np.where(valid, 0.0, np.nan)).astype(np.float32)
        warm_maps[i] = np.where(warm_mask, 1.0, np.where(valid, 0.0, np.nan)).astype(np.float32)

        if regime == "multi_regime":
            t, t_method = otsu_threshold(proto, valid)
            binary_labels = np.full(proto.shape, -1, dtype=np.int16)
            binary_labels[valid & (proto < t)] = 0
            binary_labels[valid & (proto >= t)] = 1
            boundary_mask = boundary_mask_from_binary(binary_labels, valid)
            boundary_threshold = t
            boundary_method = t_method
        else:
            boundary_mask = np.zeros(proto.shape, dtype=bool)
            boundary_threshold = float("nan")
            boundary_method = "homogeneous_zero_boundary"
        boundary_score_raw, boundary_meta = old_style_boundary_score(grad_mag, boundary_mask, valid, regime)
        boundary_norm, boundary_norm_meta = minmax01(boundary_score_raw, valid)
        boundary_maps[i] = boundary_norm
        distance_cells, distance_km, distance_scores, distance_meta = boundary_distance_descriptors(
            boundary_mask,
            valid,
            x_km,
            y_km,
            BOUNDARY_DISTANCE_RADII_CELLS,
        )
        boundary_distance_cells_maps[i] = distance_cells
        boundary_distance_km_maps[i] = distance_km
        for radius, score in distance_scores.items():
            boundary_distance_score_maps[int(radius)][i] = score

        local_var = local_variance_map(proto, valid, size=5)
        local_var_norm, local_var_meta = minmax01(local_var, valid)
        roughness_raw = np.abs(ndi.laplace(np.where(valid, proto, float(np.nanmean(proto[valid]))))).astype(np.float32)
        roughness_raw[~valid] = np.nan
        rough_norm, rough_meta = minmax01(roughness_raw, valid)
        std_norm, std_meta = minmax01(std_map, valid)
        hetero = np.full(proto.shape, np.nan, dtype=np.float32)
        hetero_stack = np.stack([local_var_norm, rough_norm, std_norm], axis=0)
        hetero[valid] = np.nanmean(hetero_stack[:, valid], axis=0).astype(np.float32)
        heterogeneity_maps[i] = hetero

        representative = build_representative_zone_map(proto, grad_norm, boundary_norm, hetero, valid)
        representative_maps[i] = representative
        interest = (
            INTEREST_WEIGHTS["boundary"] * np.nan_to_num(boundary_norm, nan=0.0)
            + INTEREST_WEIGHTS["gradient"] * np.nan_to_num(grad_norm, nan=0.0)
            + INTEREST_WEIGHTS["heterogeneity"] * np.nan_to_num(hetero, nan=0.0)
        ).astype(np.float32)
        interest[~valid] = np.nan
        interest_norm, interest_meta = minmax01(interest, valid)
        interest_maps[i] = interest_norm

        boundary_components, largest_boundary_fraction = component_stats(boundary_mask)
        bx, by = centroid_xy(boundary_mask, x_km, y_km)
        cold_x, cold_y = centroid_xy(cold_mask, x_km, y_km)
        warm_x, warm_y = centroid_xy(warm_mask, x_km, y_km)
        rep_mask = valid & np.isfinite(representative) & (representative >= percentile_threshold(representative, valid, 80))
        rep_x, rep_y = centroid_xy(rep_mask, x_km, y_km)
        res = representative_members(X_norm, assignments, class_id, proto, valid)
        res_df = res["df"].copy()
        if not res_df.empty:
            res_df.insert(0, "class_id", class_id)
            all_residual_rows.append(res_df)

        vals = proto[valid]
        grad_vals = grad_mag[valid & np.isfinite(grad_mag)]
        boundary_vals = boundary_norm[valid & np.isfinite(boundary_norm)]
        hetero_vals = hetero[valid & np.isfinite(hetero)]
        interest_vals = interest_norm[valid & np.isfinite(interest_norm)]
        distance_vals = distance_cells[valid & np.isfinite(distance_cells)]
        cold_fraction = float(cold_mask.sum() / valid.sum())
        warm_fraction = float(warm_mask.sum() / valid.sum())
        neutral_fraction = float(neutral_mask.sum() / valid.sum())
        entropy = entropy_score(proto, valid)
        local_var_vals = local_var[valid & np.isfinite(local_var)]
        texture = float(np.nanmean(rough_norm[valid]))
        spatial_roughness = float(np.nanmean(roughness_raw[valid]))
        interface = float(boundary_mask.sum() / valid.sum())
        hetero_score = float(np.nanmean(hetero_vals)) if hetero_vals.size else 0.0

        descriptor_rows.append(
            {
                "class_id": class_id,
                "class_label": class_label(class_id, regime),
                "class_size": int(sizes[i]),
                "cv_regime_label": regime,
                "cv_regime_label_raw": cv_regime,
                "qualitative_regime_label": qualitative_label(float(np.nanmean(vals)), float(np.nanstd(vals)), regime),
                "prototype_mean": float(np.nanmean(vals)),
                "prototype_std": float(np.nanstd(vals)),
                "prototype_min": float(np.nanmin(vals)),
                "prototype_max": float(np.nanmax(vals)),
                "prototype_p05": float(np.nanpercentile(vals, 5)),
                "prototype_p50": float(np.nanpercentile(vals, 50)),
                "prototype_p95": float(np.nanpercentile(vals, 95)),
                "gradient_mean": float(np.nanmean(grad_vals)),
                "gradient_median": float(np.nanmedian(grad_vals)),
                "gradient_p90": float(np.nanpercentile(grad_vals, 90)),
                "gradient_p95": float(np.nanpercentile(grad_vals, 95)),
                "gradient_max": float(np.nanmax(grad_vals)),
                "high_gradient_threshold": high_grad_thr,
                "high_gradient_fraction": float(high_grad_mask.sum() / valid.sum()),
                "gradient_concentration_score": float(np.nanmean(grad_norm[high_grad_mask])) if np.any(high_grad_mask) else 0.0,
                "dominant_gradient_region": region_label_from_centroid(gx, gy, valid, x_km, y_km),
                "gradient_centroid_x_km": gx,
                "gradient_centroid_y_km": gy,
                "boundary_score": float(np.nanmean(boundary_vals)) if boundary_vals.size else 0.0,
                "boundary_threshold": boundary_threshold,
                "boundary_fraction": float(boundary_mask.sum() / valid.sum()),
                "boundary_component_count": boundary_components,
                "largest_boundary_component_fraction": largest_boundary_fraction,
                "boundary_length_proxy": int(boundary_mask.sum()),
                "boundary_orientation_proxy": orientation_proxy(boundary_mask, x_km, y_km),
                "boundary_region_label": region_label_from_centroid(bx, by, valid, x_km, y_km),
                "boundary_distance_mean_cells": float(np.nanmean(distance_vals)) if distance_vals.size else float("nan"),
                "boundary_distance_p90_cells": float(np.nanpercentile(distance_vals, 90)) if distance_vals.size else float("nan"),
                **{
                    f"boundary_distance_score_r{radius}_mean": float(np.nanmean(boundary_distance_score_maps[int(radius)][i][valid]))
                    for radius in BOUNDARY_DISTANCE_RADII_CELLS
                },
                "heterogeneity_score": hetero_score,
                "local_variance_mean": float(np.nanmean(local_var_vals)) if local_var_vals.size else 0.0,
                "local_variance_p90": float(np.nanpercentile(local_var_vals, 90)) if local_var_vals.size else 0.0,
                "entropy_score": entropy,
                "texture_score": texture,
                "spatial_roughness": spatial_roughness,
                "unimodal_or_bimodal_flag": "bimodal" if regime == "multi_regime" else "unimodal_or_gradient",
                "substructure_flag": bool(regime == "multi_regime" or entropy > 0.72 or hetero_score > 0.45),
                "cold_fraction": cold_fraction,
                "warm_fraction": warm_fraction,
                "neutral_fraction": neutral_fraction,
                "cold_warm_ratio": float(cold_fraction / max(warm_fraction, 1e-9)),
                "segmentation_thresholds": "|".join(f"{x:.6g}" for x in seg["thresholds"]),
                "segmentation_method": seg["method"],
                "cold_region_centroid_x_km": cold_x,
                "cold_region_centroid_y_km": cold_y,
                "warm_region_centroid_x_km": warm_x,
                "warm_region_centroid_y_km": warm_y,
                "segment_interface_score": interface,
                "mean_member_to_prototype_rmse": res["mean"],
                "std_member_to_prototype_rmse": res["std"],
                "max_member_to_prototype_rmse": res["max"],
                "representative_member_ids": "|".join(str(x) for x in res["rep"]),
                "outlier_member_ids": "|".join(str(x) for x in res["out"]),
                "intra_class_variability_score": float(res["mean"] / max(float(np.nanstd(vals)), 1e-9)) if math.isfinite(res["mean"]) else float("nan"),
                "compactness_score": float(1.0 / (1.0 + res["mean"])) if math.isfinite(res["mean"]) else float("nan"),
                "interest_mean": float(np.nanmean(interest_vals)) if interest_vals.size else 0.0,
                "interest_p90": float(np.nanpercentile(interest_vals, 90)) if interest_vals.size else 0.0,
            }
        )
        zone_rows.append(
            {
                "class_id": class_id,
                "zone_type": "representative_top20pct",
                "n_pixels": int(rep_mask.sum()),
                "fraction_valid": float(rep_mask.sum() / valid.sum()),
                "centroid_x_km": rep_x,
                "centroid_y_km": rep_y,
                "region_label": region_label_from_centroid(rep_x, rep_y, valid, x_km, y_km),
            }
        )
        quality_flags = []
        if regime == "unknown":
            quality_flags.append("missing_cv_label")
        if hetero_score > 0.6:
            quality_flags.append("high_heterogeneity")
        if boundary_vals.size and float(np.nanmean(boundary_vals)) < 1e-6 and regime != "homogeneous":
            quality_flags.append("unexpected_zero_boundary")
        if np.nanmax(interest_norm[valid]) <= 0:
            quality_flags.append("zero_interest_map")
        if not quality_flags:
            quality_flags.append("ok")
        quality_rows.append({"class_id": class_id, "quality_flags": "|".join(quality_flags), "unstable_or_low_interpretability": bool(set(quality_flags) - {"ok"})})
        thresholds_by_class[str(class_id)] = {
            "regime": regime,
            "gradient_norm": grad_norm_meta,
            "boundary_norm": boundary_norm_meta,
            "heterogeneity_local_var_norm": local_var_meta,
            "heterogeneity_roughness_norm": rough_meta,
            "heterogeneity_std_norm": std_meta,
            "interest_norm": interest_meta,
            "boundary": {"threshold": boundary_threshold, "method": boundary_method, **boundary_meta},
            "boundary_distance": distance_meta,
            "segmentation": {"thresholds": seg["thresholds"], "method": seg["method"]},
        }

    descriptor_df = pd.DataFrame(descriptor_rows)
    zone_df = pd.DataFrame(zone_rows)
    quality_df = pd.DataFrame(quality_rows)
    residual_df = pd.concat(all_residual_rows, ignore_index=True) if all_residual_rows else pd.DataFrame()

    outputs = {
        "gradient": out_dir / "step08_descriptor_gradient_map.npy",
        "boundary": out_dir / "step08_descriptor_boundary_map.npy",
        "boundary_distance_cells": out_dir / "step08_descriptor_boundary_distance_cells.npy",
        "boundary_distance_km": out_dir / "step08_descriptor_boundary_distance_km.npy",
        "heterogeneity": out_dir / "step08_descriptor_heterogeneity_map.npy",
        "cold": out_dir / "step08_descriptor_cold_region_map.npy",
        "warm": out_dir / "step08_descriptor_warm_region_map.npy",
        "representative": out_dir / "step08_descriptor_representative_zone_map.npy",
        "interest": out_dir / "step08_descriptor_interest_map.npy",
    }
    for radius in BOUNDARY_DISTANCE_RADII_CELLS:
        outputs[f"boundary_distance_score_r{radius}_cells"] = out_dir / f"step08_descriptor_boundary_distance_score_r{radius}_cells.npy"
    np.save(outputs["gradient"], gradient_maps)
    np.save(outputs["boundary"], boundary_maps)
    np.save(outputs["boundary_distance_cells"], boundary_distance_cells_maps)
    np.save(outputs["boundary_distance_km"], boundary_distance_km_maps)
    for radius in BOUNDARY_DISTANCE_RADII_CELLS:
        np.save(outputs[f"boundary_distance_score_r{radius}_cells"], boundary_distance_score_maps[int(radius)])
    np.save(outputs["heterogeneity"], heterogeneity_maps)
    np.save(outputs["cold"], cold_maps)
    np.save(outputs["warm"], warm_maps)
    np.save(outputs["representative"], representative_maps)
    np.save(outputs["interest"], interest_maps)
    np.savez_compressed(
        out_dir / "step08_all_descriptor_maps.npz",
        gradient=gradient_maps,
        boundary=boundary_maps,
        boundary_distance_cells=boundary_distance_cells_maps,
        boundary_distance_km=boundary_distance_km_maps,
        heterogeneity=heterogeneity_maps,
        cold_region=cold_maps,
        warm_region=warm_maps,
        representative_zone=representative_maps,
        interest=interest_maps,
        segmentation=segmentation_maps,
        mask=mask,
        x_km=x_km,
        y_km=y_km,
        lat=lat,
        lon=lon,
        bathy=bathy,
        **{f"boundary_distance_score_r{radius}_cells": boundary_distance_score_maps[int(radius)] for radius in BOUNDARY_DISTANCE_RADII_CELLS},
    )

    descriptor_df.to_csv(out_dir / "step08_final_class_descriptors.csv", index=False)
    make_descriptor_definitions().to_csv(out_dir / "step08_descriptor_definitions.csv", index=False)
    pd.DataFrame([INTEREST_WEIGHTS]).to_csv(out_dir / "step08_descriptor_weights.csv", index=False)
    descriptor_df[
        [
            "class_id",
            "cv_regime_label",
            "cv_regime_label_raw",
            "qualitative_regime_label",
            "gradient_mean",
            "boundary_score",
            "heterogeneity_score",
            "cold_fraction",
            "warm_fraction",
            "interest_mean",
        ]
    ].to_csv(out_dir / "step08_prototype_descriptor_summary.csv", index=False)
    zone_df.to_csv(out_dir / "step08_representative_zones.csv", index=False)
    quality_df.to_csv(out_dir / "step08_descriptor_quality_flags.csv", index=False)
    if not residual_df.empty:
        residual_df.to_csv(out_dir / "step08_member_to_prototype_residuals.csv", index=False)

    titles = [f"class {i+1:02d}" for i in range(n_classes)]
    save_multimap_panel(
        prototypes,
        gradient_maps,
        boundary_maps,
        boundary_distance_score_maps[3],
        heterogeneity_maps,
        segmentation_maps,
        representative_maps,
        interest_maps,
        figures_dir / "step08_descriptor_maps_by_class_panel.png",
    )
    save_panel(gradient_maps, titles, figures_dir / "step08_gradient_maps_by_class_panel.png", "viridis")
    save_panel(boundary_maps, titles, figures_dir / "step08_boundary_maps_by_class_panel.png", "magma")
    save_panel(heterogeneity_maps, titles, figures_dir / "step08_heterogeneity_maps_by_class_panel.png", "plasma")
    save_panel(segmentation_maps, titles, figures_dir / "step08_segmentation_maps_by_class_panel.png", "coolwarm", vmin=0, vmax=2)
    save_panel(interest_maps, titles, figures_dir / "step08_interest_maps_by_class_panel.png", "inferno")
    save_rankings_figure(descriptor_df, figures_dir / "step08_descriptor_ranking_barplots.png")
    save_parallel_coordinates(descriptor_df, figures_dir / "step08_class_descriptor_radar_or_parallel_coordinates.png")
    qmap = np.zeros((n_classes, h, w), dtype=np.float32)
    for i, row in quality_df.iterrows():
        qmap[int(row["class_id"]) - 1][mask] = 0.0 if row["quality_flags"] == "ok" else 1.0
        qmap[int(row["class_id"]) - 1][~mask] = np.nan
    save_panel(qmap, titles, figures_dir / "step08_descriptor_quality_flags_panel.png", "Reds")
    for p in figures_dir.glob("*.png"):
        shutil.copy2(p, out_dir / p.name)

    checks = {
        "old_descriptor_logic_audit_done": (out_dir / "step08_old_descriptor_logic_audit.md").exists(),
        "old_scripts_notebooks_listed": len(audit["important_found"]) > 0,
        "reuse_adapt_discard_documented": all("decision" in c for c in audit["components"]),
        "n_prototypes": int(prototypes.shape[0]),
        "all_descriptor_map_shapes": {k: list(np.load(v).shape) for k, v in outputs.items()},
        "mask_is_step00_mask_common": True,
        "mask_valid_cells": int(mask.sum()),
        "descriptors_only_canonical_prototypes": True,
        "october_temppred_used": False,
        "std_used": False,
        "std_note": "Step05 class std maps used only for canonical class heterogeneity; Step06 STD not used.",
        "maps_normalized_0_1_valid": {},
        "nonzero_maps": {},
        "step07_reports_used_if_exist": bool(step07_bundle["available_optional_outputs"].get("report") or step07_bundle["available_optional_outputs"].get("summary")),
        "all_classes_complete": int(len(descriptor_df)) == EXPECTED_CLASSES,
        "unstable_descriptors": quality_df[quality_df["unstable_or_low_interpretability"]]["class_id"].astype(int).tolist(),
        "step07_used": str(step07),
        "step06_reference_only_exists": step06.exists(),
    }
    for key, path in outputs.items():
        arr = np.load(path)
        vals = arr[:, mask]
        finite = vals[np.isfinite(vals)]
        raw_distance_map = key in {"boundary_distance_cells", "boundary_distance_km"}
        checks["maps_normalized_0_1_valid"][key] = bool(
            raw_distance_map or (finite.size and np.nanmin(finite) >= -1e-6 and np.nanmax(finite) <= 1.0 + 1e-6)
        )
        checks["nonzero_maps"][key] = bool(finite.size and np.nanmax(finite) > 1e-9)

    config = {
        "roi": "FRESNEL_PAPER_ROI_X490",
        "classes": EXPECTED_CLASSES,
        "expected_class_sizes": EXPECTED_CLASS_SIZES,
        "shape": list(EXPECTED_SHAPE),
        "mask_valid_cells": EXPECTED_VALID_CELLS,
        "patch": "40x24",
        "dictionary_size": 4,
        "sd": 0.25,
        "seed": 11,
        "interest_weights": INTEREST_WEIGHTS,
        "boundary_distance_radii_cells": BOUNDARY_DISTANCE_RADII_CELLS,
        "old_logic_backbone": "prototype_characterization_utils.py label-driven segmentation and boundary_score",
    }
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "script": str(Path(__file__).resolve()),
        "inputs": {
            "step00": str(step00),
            "step05": str(step05),
            "step06_reference_only": str(step06),
            "step07": str(step07),
        },
        "files": {
            "canonical_prototypes": str(prototypes_path),
            "canonical_assignments": str(assignments_path),
            "canonical_class_sizes": str(class_sizes_path),
            "mask": str(mask_path),
            "normalization_stats": str(norm_stats_path),
        },
        "normalization_stats": norm_stats,
        "step07_bundle": step07_bundle["files"],
        "thresholds_by_class": thresholds_by_class,
        "outputs": {k: str(v) for k, v in outputs.items()},
    }
    write_json(out_dir / "step08_descriptor_metadata.json", metadata)
    write_json(out_dir / "step08_descriptor_checks.json", checks)
    write_json(out_dir / "step08_descriptor_config.json", config)

    rankings = {
        "gradient": descriptor_df.sort_values("gradient_mean", ascending=False)["class_id"].astype(int).tolist(),
        "boundary": descriptor_df.sort_values("boundary_score", ascending=False)["class_id"].astype(int).tolist(),
        "heterogeneity": descriptor_df.sort_values("heterogeneity_score", ascending=False)["class_id"].astype(int).tolist(),
        "interest": descriptor_df.sort_values("interest_mean", ascending=False)["class_id"].astype(int).tolist(),
        "cold_fraction": descriptor_df.sort_values("cold_fraction", ascending=False)["class_id"].astype(int).tolist(),
        "warm_fraction": descriptor_df.sort_values("warm_fraction", ascending=False)["class_id"].astype(int).tolist(),
    }
    verdict = "READY_FOR_STEP09_TEMPRED_CLASSIFICATION_AND_DESCRIPTOR_ASSIGNMENT"
    if not all(checks["maps_normalized_0_1_valid"].values()) or not checks["all_classes_complete"]:
        verdict = "NOT_READY_FOR_STEP09_TEMPRED_CLASSIFICATION_AND_DESCRIPTOR_ASSIGNMENT"

    summary_lines = [
        "# Step08 Descriptor Summary",
        "",
        f"- Output: `{out_dir}`",
        f"- Step07-CV used: `{step07}`",
        f"- Verdict: **{verdict}**",
        "",
        "## Rankings",
    ]
    for key, order in rankings.items():
        summary_lines.append(f"- {key}: {order}")
    summary_lines.extend(
        [
            "",
            "## Main Outputs",
            "- `step08_final_class_descriptors.csv`",
            "- `step08_all_descriptor_maps.npz`",
            "- `step08_descriptor_report.md`",
            "- descriptor map panels in `figures/` and root copies",
        ]
    )
    (out_dir / "step08_descriptor_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    report_lines = [
        "# Step08 Final Descriptor Report",
        "",
        "## A. Old Logic Audit",
        "The old production descriptor logic was found in `scripts/11_prototype_characterization.py` and `scripts/prototype_characterization_utils.py`, with upstream CV labels from `scripts/10_seed11_cv_analysis.py`/`scripts/cv_seed11_utils.py` and notebook references. The reusable backbone is label-driven segmentation, gradient magnitude, boundary score, and pixel/region descriptor tables.",
        "",
        "## B. Inputs Used",
        f"- Step00: `{step00}`",
        f"- Step05: `{step05}`",
        f"- Step07-CV: `{step07}`",
        f"- Step06: `{step06}` reference only, not used for calculations.",
        "",
        "## C. Final Descriptor Definitions",
        "- Regime/class descriptors summarize prototype distribution and CV regime label.",
        "- Gradient descriptors measure spatial temperature transitions on the canonical prototype.",
        "- Boundary/front descriptors reuse the old boundary-score idea only for multi-regime classes; homogeneous classes have zero boundary.",
        "- Heterogeneity descriptors combine local variance, roughness and canonical class std maps.",
        "- Explicit boundary-distance descriptors preserve the old boundary mask but separate pure distance/proximity from gradient intensity.",
        "- Cold/warm/neutral segmentation uses Otsu-guided tertiles for multi-regime and tertiles otherwise.",
        "- Residual descriptors use Step05 class members versus the class prototype.",
        "- Planner maps are normalized to [0,1] over the Step00 mask.",
        "",
        "## D. Ranking Classes",
    ]
    for key, order in rankings.items():
        report_lines.append(f"- {key}: {order}")
    report_lines.extend(
        [
            "",
            "## E. Recommended Step09 Use",
            "Classify October TEMPpred with the Step05 canonical model, assign each day the descriptor library of the predicted class, optionally compute direct TEMPpred descriptors as diagnostics, then combine STD with `step08_descriptor_interest_map.npy` in the planner step.",
            "",
            "## F. Verdict",
            verdict,
        ]
    )
    (out_dir / "step08_descriptor_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    boundary_distance_report = [
        "# Step08 Boundary Distance Descriptor Report",
        "",
        "## Purpose",
        "The previous `boundary_score` is retained unchanged, but it is a blended front score rather than a pure distance descriptor. This report documents the new explicit boundary-distance maps.",
        "",
        "## Old blended boundary score",
        "`boundary_score` combines gradient intensity with boundary proximity for multi-regime classes:",
        "",
        "```text",
        "boundary_score = clip(0.65 * grad_norm + 0.35 * exp(-distance_cells / p75(distance_cells)), 0, 1)",
        "```",
        "",
        "For homogeneous classes it is zero; smooth gradients are not treated as boundaries.",
        "",
        "## Pure distance-to-boundary maps",
        "`boundary_distance_cells` is the raw nearest-boundary Euclidean distance computed by `scipy.ndimage.distance_transform_edt` on the existing boundary mask.",
        "`boundary_distance_km` is saved only when `X_km`/`Y_km` spacing is regular enough; otherwise it remains NaN and metadata marks the conversion as unavailable.",
        "",
        "## Radius/band boundary scores",
        "For each radius in cells, the new score maps are:",
        "",
        "```text",
        "boundary_distance_score_r{radius}_cells = exp(-(boundary_distance_cells ** 2) / (2 * radius ** 2))",
        "```",
        "",
        f"Radii tested in cells: {BOUNDARY_DISTANCE_RADII_CELLS}.",
        "",
        "These are reward-like proximity bands: cells on the boundary have score near 1, nearby cells decay smoothly, and far cells approach 0.",
        "",
        "## Regime-specific boundary mask source",
        "- `multi_regime`: cold/warm Otsu boundary mask.",
        "- `homogeneous`: no boundary; score maps are zero over valid cells.",
        "",
        "## Planner use",
        "Step11Y extracts these maps by predicted prototype class and Step12A can use the `boundary_distance_score_r*_cells_norm` maps in the same alpha sweep as the existing descriptors.",
        "Lucrezia's planner objective is not changed; these maps only change the `information_map` written as NetCDF `temperr`.",
    ]
    (out_dir / "step08_boundary_distance_descriptor_report.md").write_text("\n".join(boundary_distance_report), encoding="utf-8")
    next_step = [
        "# Step08 Next Step Recommendation",
        "",
        "1. Run Step09 to classify October TEMPpred against the Step05 canonical classes.",
        "2. Attach Step08 descriptor rows/maps by predicted class.",
        "3. Keep direct TEMPpred descriptor extraction as diagnostic only.",
        "4. Use Step10/planner to combine STD with `interest_map`; do not optimize weights until validation.",
        "",
        verdict,
    ]
    (out_dir / "step08_next_step_recommendation.md").write_text("\n".join(next_step), encoding="utf-8")

    shutil.copy2(Path(__file__).resolve(), out_dir / Path(__file__).name)
    print(f"Step08 complete: {out_dir}")
    print(f"Step07 used: {step07}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
