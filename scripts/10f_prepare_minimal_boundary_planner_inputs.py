"""Prepare a minimal Step10F planner-input round with boundary enrichment.

Cases:
- C01 representative: 2024-08-24, using Step09B predicted class.
- C06 representative: 2023-12-22, using Step09B predicted class.
- October control: 2024-10-30, using Step09 predicted class.

Maps:
- Baseline: information_map = STD_norm
- Enriched: information_map = (1 - alpha) * STD_norm + alpha * boundary_score_norm

Only boundary descriptor maps are used in this first minimal planner round.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"

DEFAULT_STEP10E = RESULTS_ROOT / "fossum_roi_x490_step10e_top20_class01_class06_roi_x490_20260519_184636"
DEFAULT_STEP09B = RESULTS_ROOT / "fossum_roi_x490_step09b_top20_c01_c06_temppred_classification_20260519_190144"
DEFAULT_STEP06 = RESULTS_ROOT / "october_surface_temppred_std_roi_x490_20260511_155923"
DEFAULT_STEP09 = RESULTS_ROOT / "fossum_roi_x490_step09_october_temppred_descriptor_assignment_20260515_165018"
DEFAULT_STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_STEP08 = RESULTS_ROOT / "fossum_roi_x490_step08_final_descriptors_20260514_164854"

CASES = [
    {"case_id": "C01_representative", "date": "2024-08-24", "source": "top20_step10e"},
    {"case_id": "C06_representative", "date": "2023-12-22", "source": "top20_step10e"},
    {"case_id": "October_control", "date": "2024-10-30", "source": "october_step06"},
]
ALPHAS = [0.25, 0.50]
EXPECTED_SHAPE = (72, 117)
EXPECTED_VALID_CELLS = 8004

TEMP_VMIN = 16.1942
TEMP_VMAX = 19.6822
STD_VMIN = 0.0
STD_VMAX = 1.0
BOUNDARY_VMIN = 0.0
BOUNDARY_VMAX = 1.0


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
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return path


def class_label(class_id: int) -> str:
    return f"C{int(class_id):02d}"


def minmax01(arr: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    vals = arr[mask & np.isfinite(arr)]
    if vals.size == 0:
        out[mask] = 0.0
        return out, {"vmin": float("nan"), "vmax": float("nan")}
    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))
    if vmax - vmin <= 1e-12:
        out[mask] = 0.0
    else:
        out[mask] = ((arr[mask] - vmin) / (vmax - vmin)).astype(np.float32)
    return out, {"vmin": vmin, "vmax": vmax}


def masked_stats(prefix: str, arr: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    vals = arr[mask & np.isfinite(arr)]
    if vals.size == 0:
        return {
            f"{prefix}_min": float("nan"),
            f"{prefix}_max": float("nan"),
            f"{prefix}_mean": float("nan"),
            f"{prefix}_p90": float("nan"),
            f"{prefix}_p95": float("nan"),
            f"{prefix}_nan_fraction": 1.0,
        }
    return {
        f"{prefix}_min": float(np.nanmin(vals)),
        f"{prefix}_max": float(np.nanmax(vals)),
        f"{prefix}_mean": float(np.nanmean(vals)),
        f"{prefix}_p90": float(np.nanpercentile(vals, 90)),
        f"{prefix}_p95": float(np.nanpercentile(vals, 95)),
        f"{prefix}_nan_fraction": float(np.mean(~np.isfinite(arr))),
    }


def top_overlap(a: np.ndarray, b: np.ndarray, mask: np.ndarray, percentile: float = 90.0) -> float:
    valid = mask & np.isfinite(a) & np.isfinite(b)
    if not np.any(valid):
        return float("nan")
    av = a[valid]
    bv = b[valid]
    return float(np.mean((av >= np.nanpercentile(av, percentile)) & (bv >= np.nanpercentile(bv, percentile))))


def load_top20_case(date: str, step10e: Path, step09b: Path) -> dict[str, Any]:
    selected = pd.read_csv(require(step10e / "selected_dates_top20_class01_class06.csv", "Step10E selected dates"))
    assignments = pd.read_csv(require(step09b / "step09b_classification_assignments.csv", "Step09B assignments"))
    selected["date"] = pd.to_datetime(selected["date"]).dt.strftime("%Y-%m-%d")
    assignments["date"] = pd.to_datetime(assignments["date"]).dt.strftime("%Y-%m-%d")
    match = selected.index[selected["date"] == date].tolist()
    if len(match) != 1:
        raise ValueError(f"Expected one Step10E case for {date}, found {len(match)}")
    idx = int(match[0])
    pred_row = assignments.loc[assignments["date"] == date]
    if len(pred_row) != 1:
        raise ValueError(f"Expected one Step09B assignment for {date}, found {len(pred_row)}")
    temp = np.load(require(step10e / "TEMPpred_top20_roi_x490.npy", "Step10E TEMPpred"))[idx].astype(np.float32)
    std = np.load(require(step10e / "STD_variance_top20_roi_x490.npy", "Step10E STD variance"))[idx].astype(np.float32)
    return {
        "array_index": idx,
        "TEMPpred": temp,
        "STD_variance": std,
        "expected_class": int(selected.loc[idx, "expected_class"]),
        "predicted_class": int(pred_row.iloc[0]["predicted_class"]),
        "classification_source": "Step09B",
        "classification_confidence": float(pred_row.iloc[0]["confidence_score"]),
    }


def load_october_case(date: str, step06: Path, step09: Path) -> dict[str, Any]:
    dates = pd.read_csv(require(step06 / "dates_october.csv", "Step06 October dates"))
    assignments = pd.read_csv(require(step09 / "step09_temppred_classification_assignments.csv", "Step09 October assignments"))
    dates["date"] = pd.to_datetime(dates["date"]).dt.strftime("%Y-%m-%d")
    assignments["date"] = pd.to_datetime(assignments["date"]).dt.strftime("%Y-%m-%d")
    match = dates.index[dates["date"] == date].tolist()
    if len(match) != 1:
        raise ValueError(f"Expected one Step06 October case for {date}, found {len(match)}")
    idx = int(match[0])
    pred_row = assignments.loc[assignments["date"] == date]
    if len(pred_row) != 1:
        raise ValueError(f"Expected one Step09 assignment for {date}, found {len(pred_row)}")
    temp = np.load(require(step06 / "TEMPpred_october_surface_roi_x490.npy", "Step06 TEMPpred"))[idx].astype(np.float32)
    std = np.load(require(step06 / "STD_october_surface_roi_x490.npy", "Step06 STD"))[idx].astype(np.float32)
    return {
        "array_index": idx,
        "TEMPpred": temp,
        "STD_variance": std,
        "expected_class": None,
        "predicted_class": int(pred_row.iloc[0]["assigned_class_id"]),
        "classification_source": "Step09",
        "classification_confidence": float(pred_row.iloc[0]["confidence_score"]),
    }


def save_case_comparison_panel(cases_df: pd.DataFrame, arrays: dict[str, np.ndarray], out_path: Path) -> None:
    cols = [
        ("TEMPpred", arrays["TEMPpred"], "coolwarm", TEMP_VMIN, TEMP_VMAX),
        ("STD_norm", arrays["STD_norm"], "viridis", 0.0, 1.0),
        ("boundary_score_norm", arrays["boundary_score_norm"], "magma", 0.0, 1.0),
        ("enriched alpha=0.25", arrays["enriched_alpha025"], "viridis", 0.0, 1.0),
        ("enriched alpha=0.50", arrays["enriched_alpha050"], "viridis", 0.0, 1.0),
    ]
    fig, axes = plt.subplots(len(cases_df), len(cols), figsize=(15.5, 2.9 * len(cases_df)), squeeze=False)
    for r, row in cases_df.reset_index(drop=True).iterrows():
        for c, (title, arr, cmap, vmin, vmax) in enumerate(cols):
            ax = axes[r, c]
            im = ax.imshow(arr[r], origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
            ax.set_title(f"{row['case_id']} | {title}", fontsize=8)
            ax.set_ylabel(f"{row['date']}\n{row['predicted_class_label']}", fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
            if r == len(cases_df) - 1:
                plt.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("Minimal planner inputs: baseline vs boundary-enriched maps", y=0.995)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def save_information_maps_panel(cases_df: pd.DataFrame, maps: np.ndarray, title: str, out_path: Path) -> None:
    fig, axes = plt.subplots(1, len(cases_df), figsize=(4.4 * len(cases_df), 3.5), squeeze=False)
    for i, row in cases_df.reset_index(drop=True).iterrows():
        ax = axes[0, i]
        im = ax.imshow(maps[i], origin="lower", cmap="viridis", vmin=0.0, vmax=1.0, aspect="auto")
        ax.set_title(f"{row['case_id']}\n{row['date']} {row['predicted_class_label']}", fontsize=9)
        ax.axis("off")
    plt.colorbar(im, ax=axes.ravel().tolist(), fraction=0.025, pad=0.02)
    fig.suptitle(title)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare minimal boundary-only planner inputs for 3 cases.")
    parser.add_argument("--step10e", type=Path, default=DEFAULT_STEP10E)
    parser.add_argument("--step09b", type=Path, default=DEFAULT_STEP09B)
    parser.add_argument("--step06", type=Path, default=DEFAULT_STEP06)
    parser.add_argument("--step09", type=Path, default=DEFAULT_STEP09)
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--step08", type=Path, default=DEFAULT_STEP08)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    step10e = args.step10e.resolve()
    step09b = args.step09b.resolve()
    step06 = args.step06.resolve()
    step09 = args.step09.resolve()
    step00 = args.step00.resolve()
    step08 = args.step08.resolve()
    out_dir = (args.output_root.resolve() / f"fossum_roi_x490_step10f_minimal_boundary_planner_inputs_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir()

    mask = np.load(require(step00 / "mask_common_roi_x490.npy", "Step00 mask")).astype(bool)
    boundary_maps = np.load(require(step08 / "step08_descriptor_boundary_map.npy", "Step08 boundary maps")).astype(np.float32)
    descriptors = pd.read_csv(require(step08 / "step08_final_class_descriptors.csv", "Step08 class descriptors"))
    descriptors["class_id"] = descriptors["class_id"].astype(int)
    if mask.shape != EXPECTED_SHAPE or int(mask.sum()) != EXPECTED_VALID_CELLS:
        raise ValueError(f"Unexpected mask: shape={mask.shape}, valid_cells={int(mask.sum())}")
    if boundary_maps.shape != (6, *EXPECTED_SHAPE):
        raise ValueError(f"Unexpected boundary map shape: {boundary_maps.shape}")

    case_rows: list[dict[str, Any]] = []
    temp_list = []
    std_list = []
    std_norm_list = []
    boundary_norm_list = []
    baseline_list = []
    enriched_by_alpha = {alpha: [] for alpha in ALPHAS}

    for case in CASES:
        if case["source"] == "top20_step10e":
            loaded = load_top20_case(case["date"], step10e, step09b)
        else:
            loaded = load_october_case(case["date"], step06, step09)
        temp = loaded["TEMPpred"].astype(np.float32)
        std = loaded["STD_variance"].astype(np.float32)
        temp[~mask] = np.nan
        std[~mask] = np.nan
        std_norm, std_scale = minmax01(std, mask)
        boundary = boundary_maps[int(loaded["predicted_class"]) - 1].astype(np.float32)
        boundary_norm, boundary_scale = minmax01(boundary, mask)
        baseline = std_norm.copy()
        baseline[~mask] = np.nan

        for alpha in ALPHAS:
            enriched = ((1.0 - alpha) * std_norm + alpha * boundary_norm).astype(np.float32)
            enriched[~mask] = np.nan
            enriched_by_alpha[alpha].append(enriched)

        desc = descriptors.loc[descriptors["class_id"] == int(loaded["predicted_class"])].iloc[0]
        row = {
            "case_id": case["case_id"],
            "date": case["date"],
            "source": case["source"],
            "array_index": int(loaded["array_index"]),
            "expected_class": loaded["expected_class"],
            "expected_class_label": "" if loaded["expected_class"] is None else class_label(int(loaded["expected_class"])),
            "predicted_class": int(loaded["predicted_class"]),
            "predicted_class_label": class_label(int(loaded["predicted_class"])),
            "classification_source": loaded["classification_source"],
            "classification_confidence": float(loaded["classification_confidence"]),
            "step08_descriptor_class_label": str(desc.get("class_label", "")),
            "step08_boundary_score": float(desc.get("boundary_score", np.nan)),
            "std_norm_scale_min": std_scale["vmin"],
            "std_norm_scale_max": std_scale["vmax"],
            "boundary_norm_scale_min": boundary_scale["vmin"],
            "boundary_norm_scale_max": boundary_scale["vmax"],
            **masked_stats("TEMPpred", temp, mask),
            **masked_stats("STD_variance", std, mask),
            **masked_stats("STD_norm", std_norm, mask),
            **masked_stats("boundary_score_norm", boundary_norm, mask),
            "overlap_top10_STD_boundary": top_overlap(std_norm, boundary_norm, mask, 90.0),
        }
        for alpha in ALPHAS:
            enriched = enriched_by_alpha[alpha][-1]
            suffix = f"alpha{int(alpha * 100):03d}"
            row.update(masked_stats(f"enriched_{suffix}", enriched, mask))
            row[f"overlap_top10_enriched_{suffix}_boundary"] = top_overlap(enriched, boundary_norm, mask, 90.0)
        case_rows.append(row)

        temp_list.append(temp)
        std_list.append(std)
        std_norm_list.append(std_norm)
        boundary_norm_list.append(boundary_norm)
        baseline_list.append(baseline)

    cases_df = pd.DataFrame(case_rows)
    temp_arr = np.stack(temp_list).astype(np.float32)
    std_arr = np.stack(std_list).astype(np.float32)
    std_norm_arr = np.stack(std_norm_list).astype(np.float32)
    boundary_norm_arr = np.stack(boundary_norm_list).astype(np.float32)
    baseline_arr = np.stack(baseline_list).astype(np.float32)
    enriched025 = np.stack(enriched_by_alpha[0.25]).astype(np.float32)
    enriched050 = np.stack(enriched_by_alpha[0.50]).astype(np.float32)

    np.save(out_dir / "planner_cases_TEMPpred_roi_x490.npy", temp_arr)
    np.save(out_dir / "planner_cases_STD_variance_roi_x490.npy", std_arr)
    np.save(out_dir / "planner_cases_STD_norm_roi_x490.npy", std_norm_arr)
    np.save(out_dir / "planner_cases_boundary_score_norm_roi_x490.npy", boundary_norm_arr)
    np.save(out_dir / "planner_information_map_baseline_STD_norm.npy", baseline_arr)
    np.save(out_dir / "planner_information_map_enriched_boundary_alpha025.npy", enriched025)
    np.save(out_dir / "planner_information_map_enriched_boundary_alpha050.npy", enriched050)
    np.savez_compressed(
        out_dir / "planner_minimal_boundary_input_maps.npz",
        TEMPpred=temp_arr,
        STD_variance=std_arr,
        STD_norm=std_norm_arr,
        boundary_score_norm=boundary_norm_arr,
        baseline_STD_norm=baseline_arr,
        enriched_boundary_alpha025=enriched025,
        enriched_boundary_alpha050=enriched050,
        mask=mask,
        dates=cases_df["date"].astype(str).to_numpy(),
        case_ids=cases_df["case_id"].astype(str).to_numpy(),
        predicted_classes=cases_df["predicted_class"].astype(int).to_numpy(),
    )

    cases_df.to_csv(out_dir / "step10f_minimal_boundary_planner_cases.csv", index=False)
    weights_df = pd.DataFrame(
        [
            {"formulation": "baseline", "alpha": 0.0, "STD_norm_weight": 1.0, "boundary_score_norm_weight": 0.0},
            {"formulation": "enriched_alpha025", "alpha": 0.25, "STD_norm_weight": 0.75, "boundary_score_norm_weight": 0.25},
            {"formulation": "enriched_alpha050", "alpha": 0.50, "STD_norm_weight": 0.50, "boundary_score_norm_weight": 0.50},
        ]
    )
    weights_df.to_csv(out_dir / "step10f_minimal_boundary_planner_weights.csv", index=False)

    arrays_for_panel = {
        "TEMPpred": temp_arr,
        "STD_norm": std_norm_arr,
        "boundary_score_norm": boundary_norm_arr,
        "enriched_alpha025": enriched025,
        "enriched_alpha050": enriched050,
    }
    save_case_comparison_panel(cases_df, arrays_for_panel, fig_dir / "step10f_three_cases_boundary_baseline_vs_enriched_panel.png")
    save_information_maps_panel(cases_df, baseline_arr, "Baseline information map = STD_norm", fig_dir / "step10f_baseline_STD_norm_three_cases.png")
    save_information_maps_panel(cases_df, enriched025, "Enriched information map: alpha=0.25 boundary", fig_dir / "step10f_enriched_boundary_alpha025_three_cases.png")
    save_information_maps_panel(cases_df, enriched050, "Enriched information map: alpha=0.50 boundary", fig_dir / "step10f_enriched_boundary_alpha050_three_cases.png")

    for p in fig_dir.glob("*.png"):
        shutil.copy2(p, out_dir / p.name)

    planner_order = cases_df.sort_values(
        ["classification_confidence", "STD_variance_mean", "overlap_top10_STD_boundary"],
        ascending=[False, False, False],
    )
    first_case = planner_order.iloc[0]
    recommendation = (
        f"Use {first_case['case_id']} ({first_case['date']}, {first_case['predicted_class_label']}) first: "
        f"it has the strongest classification confidence among the three selected cases. "
        "Then compare against the high-STD C01 case to test whether boundary enrichment changes planner behavior."
    )

    checks = {
        "n_cases": int(len(cases_df)),
        "cases": cases_df[["case_id", "date", "predicted_class_label"]].to_dict(orient="records"),
        "mask_shape": list(mask.shape),
        "mask_valid_cells": int(mask.sum()),
        "TEMPpred_shape": list(temp_arr.shape),
        "STD_variance_shape": list(std_arr.shape),
        "STD_norm_shape": list(std_norm_arr.shape),
        "boundary_score_norm_shape": list(boundary_norm_arr.shape),
        "baseline_shape": list(baseline_arr.shape),
        "enriched_alpha025_shape": list(enriched025.shape),
        "enriched_alpha050_shape": list(enriched050.shape),
        "uses_only_boundary_descriptor": True,
        "uses_gradient": False,
        "uses_heterogeneity": False,
        "uses_composite_interest_map": False,
        "std_used_for_classification": False,
        "classification_changed": False,
        "ready_for_planner_interface_test": True,
    }
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "script": str(Path(__file__).resolve()),
        "inputs": {
            "step10e": str(step10e),
            "step09b": str(step09b),
            "step06": str(step06),
            "step09": str(step09),
            "step00": str(step00),
            "step08": str(step08),
        },
        "formulae": {
            "baseline": "information_map = STD_norm",
            "enriched": "information_map = (1 - alpha) * STD_norm + alpha * boundary_score_norm",
            "alphas": ALPHAS,
        },
        "recommendation": recommendation,
        "verdict": "MINIMAL_BOUNDARY_PLANNER_INPUTS_READY",
    }
    write_json(out_dir / "step10f_minimal_boundary_planner_config.json", metadata["formulae"])
    write_json(out_dir / "step10f_minimal_boundary_planner_checks.json", checks)
    write_json(out_dir / "step10f_minimal_boundary_planner_metadata.json", metadata)

    summary_lines = [
        "# Step10F Minimal Boundary Planner Inputs",
        "",
        f"- Output: `{out_dir}`",
        "- Baseline: `information_map = STD_norm`",
        "- Enriched alpha 0.25: `0.75 * STD_norm + 0.25 * boundary_score_norm`",
        "- Enriched alpha 0.50: `0.50 * STD_norm + 0.50 * boundary_score_norm`",
        "- Descriptor used: boundary only",
        "",
        "## Cases",
    ]
    for row in cases_df.itertuples():
        summary_lines.append(
            f"- {row.case_id}: {row.date}, predicted {row.predicted_class_label}, confidence={row.classification_confidence:.3f}, STD_mean={row.STD_variance_mean:.5f}"
        )
    summary_lines.extend(["", "## Recommendation", recommendation, "", "MINIMAL_BOUNDARY_PLANNER_INPUTS_READY"])
    (out_dir / "step10f_minimal_boundary_planner_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    (out_dir / "step10f_minimal_boundary_planner_report.md").write_text("\n".join(summary_lines), encoding="utf-8")
    (out_dir / "step10f_minimal_boundary_next_step_recommendation.md").write_text(
        "\n".join(["# Next Step", "", recommendation, "", "Run the planner in baseline, alpha=0.25, and alpha=0.50 modes for these three cases."]),
        encoding="utf-8",
    )
    shutil.copy2(Path(__file__).resolve(), out_dir / Path(__file__).name)

    print(f"Step10F minimal boundary planner inputs complete: {out_dir}")
    print(cases_df[["case_id", "date", "predicted_class_label", "classification_confidence", "STD_variance_mean"]].to_string(index=False))
    print(recommendation)
    print("Verdict: MINIMAL_BOUNDARY_PLANNER_INPUTS_READY")


if __name__ == "__main__":
    main()
