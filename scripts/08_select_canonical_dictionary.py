"""Seed sweep to select and persist a canonical dictionary for faithful SST clustering.

Selection uses multiple criteria (ICV + MPD + SSIM) and persists the chosen
dictionary for fixed-dictionary official runs.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist

from fossum_faithful_initial_utils import ROOT, load_dictionary_artifact


SCRIPT_DIR = Path(__file__).resolve().parent
GLOBAL_STAGE_SCRIPT = SCRIPT_DIR / "04a_separation_distance_probe_fossum_faithful_initial.py"

DEFAULT_OUT_BASE = ROOT / "results" / "fossum" / "canonical_dictionary_seed_sweep"
DEFAULT_CANONICAL_OUT_DIR = ROOT / "results" / "fossum" / "canonical_dictionary"
DEFAULT_RUN_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")

DEFAULT_SEEDS = [11, 23, 37, 53, 71, 7, 19, 41, 83, 97]
DEFAULT_FRACTIONS = [0.30]
DEFAULT_RANKING_TARGET_CLASSES = 5

PATCH_W = 72
PATCH_H = 40
DICTIONARY_SIZE = 4
STANDARD_SCALER_ON = True
OFFICIAL_SD_FRACTION = 0.30
MIN_CLASS_SIZE_THRESHOLD = 20

K1 = 0.01
K2 = 0.03


def log(msg: str) -> None:
    print(f"[canonical-dict-select] {msg}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run seed sweep and select canonical dictionary for faithful SST pipeline.")
    p.add_argument("--out-base", type=Path, default=DEFAULT_OUT_BASE)
    p.add_argument("--run-tag", type=str, default=DEFAULT_RUN_TAG)
    p.add_argument("--seeds", type=int, nargs="*", default=None)
    p.add_argument("--fractions", type=float, nargs="*", default=None)
    p.add_argument("--ranking-target-classes", type=int, default=DEFAULT_RANKING_TARGET_CLASSES)
    p.add_argument("--min-class-size-threshold", type=int, default=MIN_CLASS_SIZE_THRESHOLD)
    p.add_argument("--tie-epsilon", type=float, default=0.02, help="Composite-score tie threshold.")
    p.add_argument("--canonical-out-dir", type=Path, default=DEFAULT_CANONICAL_OUT_DIR)
    p.add_argument("--no-pca", action="store_true", help="Pass --no-pca to stage 04a during sweep.")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing run-tag output and canonical artifact paths.")
    return p.parse_args()


def first_existing_file(candidates: Sequence[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def first_existing_dir(candidates: Sequence[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return None


def to_repo_or_abs(path: Path) -> str:
    rp = path.resolve()
    try:
        return rp.relative_to(ROOT).as_posix()
    except Exception:
        return str(rp)


def normalize_seeds(values: Sequence[int] | None) -> List[int]:
    seeds = DEFAULT_SEEDS if not values else [int(v) for v in values]
    uniq: List[int] = []
    seen = set()
    for s in seeds:
        if s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    return uniq


def validate_fractions(values: Sequence[float] | None) -> List[float]:
    fractions = DEFAULT_FRACTIONS if not values else [float(v) for v in values]
    out: List[float] = []
    seen = set()
    for f in fractions:
        if f <= 0.0 or f >= 1.0:
            raise ValueError(f"Invalid fraction {f}. Expected (0, 1).")
        key = round(float(f), 12)
        if key in seen:
            continue
        seen.add(key)
        out.append(float(f))
    out.sort()
    if not any(np.isclose(v, OFFICIAL_SD_FRACTION, atol=1e-9) for v in out):
        raise ValueError(f"--fractions must include {OFFICIAL_SD_FRACTION:.2f} for canonical selection.")
    return out


def resolve_input_paths() -> Dict[str, Path]:
    if not GLOBAL_STAGE_SCRIPT.exists():
        raise FileNotFoundError(f"Missing global stage script: {GLOBAL_STAGE_SCRIPT}")
    paths = {
        "X_sst": first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300.npy",
                ROOT / "results" / "plots" / "X_surface_300.npy",
            ]
        ),
        "X_norm": first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
                ROOT / "results" / "plots" / "X_surface_300_norm.npy",
            ]
        ),
        "mask": first_existing_file(
            [
                ROOT / "results" / "fossum" / "mask_common.npy",
                ROOT / "results" / "plots" / "mask_common.npy",
            ]
        ),
        "png_dir": first_existing_dir(
            [
                ROOT / "results" / "fossum" / "pngs_normalized_surface_300_thesis",
                ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis",
            ]
        ),
    }
    missing = [k for k, v in paths.items() if v is None]
    if missing:
        raise FileNotFoundError(
            "Missing required inputs for canonical dictionary sweep: "
            + ", ".join(missing)
            + " (checked results/fossum and results/plots)"
        )
    return {k: v for k, v in paths.items() if v is not None}


def load_metric_inputs(paths: Dict[str, Path]) -> Tuple[np.ndarray, np.ndarray, float, float, float]:
    X_norm = np.load(paths["X_norm"]).astype(np.float32, copy=False)
    mask = np.load(paths["mask"]).astype(bool, copy=False)

    if X_norm.ndim != 3:
        raise RuntimeError(f"Expected 3D X_norm, got {X_norm.shape}")
    if mask.shape != X_norm.shape[1:]:
        raise RuntimeError(f"Mask shape mismatch: {mask.shape} vs {X_norm.shape[1:]}")

    X_norm = X_norm.copy()
    X_norm[:, ~mask] = np.nan
    flat = np.nan_to_num(X_norm[:, mask], nan=0.0).astype(np.float64, copy=False)

    valid_vals = X_norm[:, mask]
    data_min = float(np.nanmin(valid_vals))
    data_max = float(np.nanmax(valid_vals))
    data_range = float(data_max - data_min)
    if not np.isfinite(data_range) or data_range <= 0.0:
        data_range = 1.0
    return X_norm, flat, data_range, data_min, data_max


def run_command(cmd: Sequence[str], label: str) -> None:
    cmd_text = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    log(f"[{label}] Running command: {cmd_text}")
    proc = subprocess.Popen(
        list(cmd),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    tail: List[str] = []
    for line in proc.stdout:
        clean = line.rstrip("\n")
        print(clean)
        tail.append(clean)
        if len(tail) > 60:
            tail.pop(0)
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"Command failed ({label}) with exit code {rc}.\n" + "\n".join(tail[-20:]))


def parse_class_members_from_sd_dir(sd_dir: Path) -> List[Tuple[int, np.ndarray]]:
    rx = re.compile(r"^class_(\d+)_distance_to_prototype\.csv$", re.IGNORECASE)
    files = sorted(sd_dir.glob("class_*_distance_to_prototype.csv"))
    if not files:
        raise FileNotFoundError(f"No class distance CSV files found in {sd_dir}")

    out: List[Tuple[int, np.ndarray]] = []
    for f in files:
        m = rx.match(f.name)
        if not m:
            continue
        class_id = int(m.group(1))
        df = pd.read_csv(f)
        if "image_idx_0_based" not in df.columns:
            raise RuntimeError(f"Unexpected class distance columns in {f}: {list(df.columns)}")
        idx = df["image_idx_0_based"].astype(int).to_numpy()
        out.append((class_id, np.sort(idx)))
    if not out:
        raise RuntimeError(f"Could not parse class IDs from class distance files in {sd_dir}")
    return sorted(out, key=lambda x: x[0])


def class_pairwise_metrics(X_class: np.ndarray, c1: float, c2: float) -> Dict[str, float]:
    n = int(X_class.shape[0])
    if n < 2:
        return {
            "pair_count": 0.0,
            "mean_mpd": float("nan"),
            "p95_mpd": float("nan"),
            "mean_pairwise_ssim": float("nan"),
            "median_pairwise_ssim": float("nan"),
            "p05_pairwise_ssim": float("nan"),
            "min_pairwise_ssim": float("nan"),
        }

    pairwise_dist = pdist(X_class, metric="euclidean")
    mean_mpd = float(np.mean(pairwise_dist))
    p95_mpd = float(np.percentile(pairwise_dist, 95.0))

    n_pix = float(X_class.shape[1])
    means = np.mean(X_class, axis=1)
    centered = X_class - means[:, None]
    variances = np.mean(centered * centered, axis=1)
    cov = (centered @ centered.T) / n_pix

    mu_i2_plus_mu_j2 = (means[:, None] * means[:, None]) + (means[None, :] * means[None, :])
    num1 = (2.0 * means[:, None] * means[None, :]) + c1
    den1 = mu_i2_plus_mu_j2 + c1
    num2 = (2.0 * cov) + c2
    den2 = (variances[:, None] + variances[None, :]) + c2
    ssim_matrix = (num1 * num2) / np.maximum(den1 * den2, 1e-12)
    ssim_matrix = np.clip(ssim_matrix, -1.0, 1.0)
    pairwise_ssim = ssim_matrix[np.triu_indices(n, k=1)]

    return {
        "pair_count": float(pairwise_dist.size),
        "mean_mpd": mean_mpd,
        "p95_mpd": p95_mpd,
        "mean_pairwise_ssim": float(np.mean(pairwise_ssim)),
        "median_pairwise_ssim": float(np.median(pairwise_ssim)),
        "p05_pairwise_ssim": float(np.percentile(pairwise_ssim, 5.0)),
        "min_pairwise_ssim": float(np.min(pairwise_ssim)),
    }


def weighted_average(values: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not np.any(valid):
        return float("nan")
    return float(np.sum(values[valid] * weights[valid]) / np.sum(weights[valid]))


def evaluate_seed(
    seed: int,
    run_root: Path,
    fractions: Sequence[float],
    ranking_target_classes: int,
    no_pca: bool,
    flat_images: np.ndarray,
    data_range: float,
    python_exe: str,
) -> Tuple[dict, List[dict]]:
    raw_seed_out = run_root / "raw_global_runs" / f"seed{seed:03d}"
    raw_seed_out.mkdir(parents=True, exist_ok=True)
    dict_artifact_path = run_root / "seed_dictionaries" / f"seed{seed:03d}_dictionary.npz"
    if dict_artifact_path.exists():
        dict_artifact_path.unlink()

    label = f"seed{seed:03d}"
    run_tag = f"canonical_probe_seed{seed:03d}"
    cmd = [
        python_exe,
        str(GLOBAL_STAGE_SCRIPT.resolve()),
        "--out-base",
        str(raw_seed_out),
        "--run-tag",
        run_tag,
        "--seed",
        str(seed),
        "--patch-w",
        str(PATCH_W),
        "--patch-h",
        str(PATCH_H),
        "--dictionary-size",
        str(DICTIONARY_SIZE),
        "--fractions",
        *[f"{v:.12g}" for v in fractions],
        "--ranking-target-classes",
        str(ranking_target_classes),
        "--apply-standard-scaler",
        "--save-dictionary-path",
        str(dict_artifact_path),
    ]
    if no_pca:
        cmd.append("--no-pca")
    run_command(cmd=cmd, label=label)

    run_dirs = sorted([p for p in raw_seed_out.iterdir() if p.is_dir()])
    if len(run_dirs) != 1:
        raise RuntimeError(f"Expected one run dir for seed {seed} in {raw_seed_out}, found {len(run_dirs)}")
    run_dir = run_dirs[0]
    runs_csv = run_dir / "runs.csv"
    if not runs_csv.exists():
        raise FileNotFoundError(f"Missing runs.csv for seed {seed}: {runs_csv}")

    runs_df = pd.read_csv(runs_csv)
    if "sd_fraction_of_max" not in runs_df.columns:
        raise RuntimeError(f"Unexpected runs.csv schema for seed {seed}: {list(runs_df.columns)}")
    frac_mask = np.isclose(runs_df["sd_fraction_of_max"].astype(float).to_numpy(), OFFICIAL_SD_FRACTION, atol=1e-9)
    if not np.any(frac_mask):
        raise RuntimeError(f"Seed {seed} runs.csv has no SD fraction {OFFICIAL_SD_FRACTION:.2f} row.")
    row = runs_df.loc[frac_mask].iloc[0]

    sd_dir = run_dir / f"sd_{int(round(OFFICIAL_SD_FRACTION * 100)):02d}pct"
    if not sd_dir.exists():
        raise FileNotFoundError(f"Missing SD directory for seed {seed}: {sd_dir}")
    class_members = parse_class_members_from_sd_dir(sd_dir)

    c1 = (K1 * data_range) ** 2
    c2 = (K2 * data_range) ** 2
    class_rows: List[dict] = []
    for class_id, idx in class_members:
        metrics = class_pairwise_metrics(flat_images[idx], c1=c1, c2=c2)
        class_rows.append(
            {
                "seed": int(seed),
                "class_id": int(class_id),
                "class_size": int(idx.size),
                "pair_count": float(metrics["pair_count"]),
                "mean_mpd": float(metrics["mean_mpd"]),
                "p95_mpd": float(metrics["p95_mpd"]),
                "mean_pairwise_ssim": float(metrics["mean_pairwise_ssim"]),
                "median_pairwise_ssim": float(metrics["median_pairwise_ssim"]),
                "p05_pairwise_ssim": float(metrics["p05_pairwise_ssim"]),
                "min_pairwise_ssim": float(metrics["min_pairwise_ssim"]),
            }
        )

    class_df = pd.DataFrame(class_rows).sort_values("class_id").reset_index(drop=True)
    w = class_df["pair_count"].to_numpy(dtype=np.float64)
    summary_row = {
        "seed": int(seed),
        "status": "success",
        "error": "",
        "run_dir": to_repo_or_abs(run_dir),
        "sd_dir": to_repo_or_abs(sd_dir),
        "dictionary_artifact_path": str(dict_artifact_path.resolve()),
        "number_of_classes": int(row["number_of_classes"]),
        "singleton_count": int(row["singleton_count"]),
        "min_class_size": int(row["min_class_size"]),
        "mean_class_size": float(row["mean_class_size"]),
        "max_class_size": int(row["max_class_size"]),
        "mean_icv": float(row["mean_icv"]),
        "std_icv": float(row["std_icv"]),
        "behavior_label": str(row["behavior_label"]),
        "behavior_reason": str(row["behavior_reason"]),
        "weighted_mean_MPD": weighted_average(class_df["mean_mpd"].to_numpy(dtype=np.float64), w),
        "weighted_p95_MPD": weighted_average(class_df["p95_mpd"].to_numpy(dtype=np.float64), w),
        "weighted_mean_pairwise_SSIM": weighted_average(class_df["mean_pairwise_ssim"].to_numpy(dtype=np.float64), w),
        "weighted_median_pairwise_SSIM": weighted_average(class_df["median_pairwise_ssim"].to_numpy(dtype=np.float64), w),
        "weighted_p05_pairwise_SSIM": weighted_average(class_df["p05_pairwise_ssim"].to_numpy(dtype=np.float64), w),
        "min_pairwise_SSIM_overall": float(np.nanmin(class_df["min_pairwise_ssim"].to_numpy(dtype=np.float64))),
        "class_metrics_json": class_df.to_json(orient="records"),
    }
    return summary_row, class_rows


def add_selection_ranks(
    summary_df: pd.DataFrame,
    target_classes: int,
    min_class_size_threshold: int,
    tie_epsilon: float,
) -> Tuple[pd.DataFrame, int | None, str]:
    df = summary_df.copy()
    ok = df["status"] == "success"
    df["eligible_target_classes"] = ok & (df["number_of_classes"] == int(target_classes))
    df["eligible_no_singletons"] = ok & (df["singleton_count"] == 0)
    df["eligible_min_class_size"] = ok & (df["min_class_size"] >= int(min_class_size_threshold))
    df["eligible_structure"] = df["eligible_target_classes"] & df["eligible_no_singletons"]
    df["eligible_for_selection"] = df["eligible_structure"] & df["eligible_min_class_size"]

    selection_note = f"Selection filter: n_classes=={target_classes}, singleton_count==0, min_class_size>={min_class_size_threshold}."
    if int(df["eligible_for_selection"].sum()) == 0 and int(df["eligible_structure"].sum()) > 0:
        df["eligible_for_selection"] = df["eligible_structure"]
        selection_note = (
            f"No seed met min_class_size>={min_class_size_threshold}; fallback used structure-only filter "
            f"(n_classes=={target_classes}, singleton_count==0)."
        )

    rank_cols = [
        "rank_mean_icv",
        "rank_weighted_MPD",
        "rank_weighted_pairwise_SSIM",
        "rank_min_class_size",
        "composite_score",
    ]
    for c in rank_cols:
        df[c] = np.nan

    sel = df["eligible_for_selection"]
    if int(sel.sum()) > 0:
        work = df.loc[sel].copy()
        work["rank_mean_icv"] = work["mean_icv"].rank(method="min", ascending=True)
        work["rank_weighted_MPD"] = work["weighted_mean_MPD"].rank(method="min", ascending=True)
        work["rank_weighted_pairwise_SSIM"] = work["weighted_mean_pairwise_SSIM"].rank(method="min", ascending=False)
        work["rank_min_class_size"] = work["min_class_size"].rank(method="min", ascending=False)
        work["composite_score"] = (
            0.30 * work["rank_mean_icv"]
            + 0.30 * work["rank_weighted_MPD"]
            + 0.30 * work["rank_weighted_pairwise_SSIM"]
            + 0.10 * work["rank_min_class_size"]
        )
        for c in rank_cols:
            df.loc[work.index, c] = work[c]

    df = df.sort_values(
        by=["eligible_for_selection", "composite_score", "weighted_mean_MPD", "mean_icv", "seed"],
        ascending=[False, True, True, True, True],
    ).reset_index(drop=True)

    selected_seed: int | None = None
    if int(df["eligible_for_selection"].sum()) > 0:
        cand = df[df["eligible_for_selection"]].copy()
        best_score = float(cand["composite_score"].min())
        tie = cand[np.abs(cand["composite_score"].astype(float) - best_score) <= float(tie_epsilon)].copy()
        if len(tie) > 1:
            tie = tie.sort_values(
                by=[
                    "weighted_mean_pairwise_SSIM",
                    "weighted_mean_MPD",
                    "mean_icv",
                    "min_class_size",
                    "seed",
                ],
                ascending=[False, True, True, False, True],
            )
            selection_note += (
                f" Tie-break applied within composite +/-{tie_epsilon:.4f}: "
                "higher weighted_mean_pairwise_SSIM, then lower weighted_mean_MPD, lower mean_icv, higher min_class_size."
            )
        selected_seed = int(tie.iloc[0]["seed"])
    return df, selected_seed, selection_note


def dataframe_to_md_table(df: pd.DataFrame, cols: Sequence[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body: List[str] = []
    for _, row in df.iterrows():
        vals: List[str] = []
        for c in cols:
            value = row[c]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{float(value):.6f}")
            else:
                vals.append(str(value))
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + body)


def build_report(
    report_path: Path,
    run_root: Path,
    seeds: Sequence[int],
    fractions: Sequence[float],
    ranked_df: pd.DataFrame,
    selected_seed: int | None,
    selection_note: str,
    canonical_dict_path: Path | None,
    canonical_manifest_path: Path | None,
    min_class_size_threshold: int,
) -> None:
    lines: List[str] = []
    lines.append("# Canonical Dictionary Selection Report")
    lines.append("")
    lines.append("## Sweep Configuration")
    lines.append(f"- patch size: {PATCH_W}x{PATCH_H}")
    lines.append(f"- dictionary size: {DICTIONARY_SIZE}")
    lines.append(f"- StandardScaler: {STANDARD_SCALER_ON}")
    lines.append(f"- SD fraction evaluated: {OFFICIAL_SD_FRACTION:.2f}")
    lines.append(f"- ranking_target_classes (04a): {DEFAULT_RANKING_TARGET_CLASSES}")
    lines.append(f"- seeds tested: {[int(s) for s in seeds]}")
    lines.append(f"- fractions passed to 04a: {[float(v) for v in fractions]}")
    lines.append(f"- run root: `{to_repo_or_abs(run_root)}`")
    lines.append("")
    lines.append("## Metric Definitions")
    lines.append("- `mean_icv`: from current 04a output (SST-space ICV diagnostics).")
    lines.append("- `weighted_mean_MPD`: pair-count-weighted mean of within-class pairwise Euclidean distances on normalized SST vectors over the common valid mask.")
    lines.append("- `weighted_mean_pairwise_SSIM`: pair-count-weighted mean of within-class pairwise SSIM (global SSIM formula per image pair on normalized SST vectors over the common valid mask).")
    lines.append("- Mask/NaN handling: only common-mask pixels are used; masked pixels are excluded from MPD/SSIM vectors.")
    lines.append("")
    lines.append("## Selection Policy")
    lines.append(f"- Primary eligibility: `number_of_classes == 5`, `singleton_count == 0`, `min_class_size >= {min_class_size_threshold}`.")
    lines.append("- Composite ranking on eligible seeds: 0.30 rank(mean_icv) + 0.30 rank(weighted_mean_MPD) + 0.30 rank(weighted_mean_pairwise_SSIM, descending) + 0.10 rank(min_class_size, descending).")
    lines.append(f"- {selection_note}")
    lines.append("")
    lines.append("## Per-Seed Results")
    cols = [
        "seed",
        "status",
        "number_of_classes",
        "singleton_count",
        "min_class_size",
        "mean_icv",
        "weighted_mean_MPD",
        "weighted_mean_pairwise_SSIM",
        "eligible_for_selection",
        "composite_score",
    ]
    lines.append(dataframe_to_md_table(ranked_df[cols], cols))
    lines.append("")
    if selected_seed is None:
        lines.append("## Canonical Seed")
        lines.append("- No canonical seed selected (no eligible successful seed).")
    else:
        sel_row = ranked_df[ranked_df["seed"] == int(selected_seed)].iloc[0]
        lines.append("## Canonical Seed")
        lines.append(f"- selected seed: {selected_seed}")
        lines.append(f"- number_of_classes: {int(sel_row['number_of_classes'])}")
        lines.append(f"- singleton_count: {int(sel_row['singleton_count'])}")
        lines.append(f"- min_class_size: {int(sel_row['min_class_size'])}")
        lines.append(f"- mean_icv: {float(sel_row['mean_icv']):.6f}")
        lines.append(f"- weighted_mean_MPD: {float(sel_row['weighted_mean_MPD']):.6f}")
        lines.append(f"- weighted_mean_pairwise_SSIM: {float(sel_row['weighted_mean_pairwise_SSIM']):.6f}")
        if canonical_dict_path is not None:
            lines.append(f"- canonical dictionary: `{canonical_dict_path}`")
        if canonical_manifest_path is not None:
            lines.append(f"- canonical manifest: `{canonical_manifest_path}`")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    seeds = normalize_seeds(args.seeds)
    fractions = validate_fractions(args.fractions)
    if int(args.ranking_target_classes) <= 0:
        raise ValueError("--ranking-target-classes must be > 0.")
    if int(args.min_class_size_threshold) <= 0:
        raise ValueError("--min-class-size-threshold must be > 0.")
    if float(args.tie_epsilon) < 0:
        raise ValueError("--tie-epsilon must be >= 0.")

    input_paths = resolve_input_paths()
    _X_norm, flat_images, data_range, data_min, data_max = load_metric_inputs(input_paths)
    out_base = args.out_base.resolve()
    run_root = out_base / args.run_tag
    if run_root.exists():
        if not args.overwrite:
            raise FileExistsError(f"Run folder exists: {run_root}. Use a new --run-tag or --overwrite.")
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "raw_global_runs").mkdir(parents=True, exist_ok=True)
    (run_root / "seed_dictionaries").mkdir(parents=True, exist_ok=True)

    python_exe = str(Path(sys.executable).resolve())
    log("Starting canonical dictionary seed sweep.")
    log(f"Run root: {run_root}")
    log(f"Seeds: {seeds}")

    summary_rows: List[dict] = []
    per_class_rows: List[dict] = []

    for seed in seeds:
        try:
            log(f"=== Evaluating seed {seed} ===")
            seed_summary, seed_class_rows = evaluate_seed(
                seed=seed,
                run_root=run_root,
                fractions=fractions,
                ranking_target_classes=int(args.ranking_target_classes),
                no_pca=bool(args.no_pca),
                flat_images=flat_images,
                data_range=data_range,
                python_exe=python_exe,
            )
            summary_rows.append(seed_summary)
            per_class_rows.extend(seed_class_rows)
            log(
                f"Seed {seed} -> classes={seed_summary['number_of_classes']} "
                f"singletons={seed_summary['singleton_count']} "
                f"mean_icv={seed_summary['mean_icv']:.6f} "
                f"wMPD={seed_summary['weighted_mean_MPD']:.6f} "
                f"wSSIM={seed_summary['weighted_mean_pairwise_SSIM']:.6f}"
            )
        except Exception as exc:
            log(f"Seed {seed} failed: {exc}")
            summary_rows.append(
                {
                    "seed": int(seed),
                    "status": "failed",
                    "error": str(exc),
                    "run_dir": "",
                    "sd_dir": "",
                    "dictionary_artifact_path": "",
                    "number_of_classes": np.nan,
                    "singleton_count": np.nan,
                    "min_class_size": np.nan,
                    "mean_class_size": np.nan,
                    "max_class_size": np.nan,
                    "mean_icv": np.nan,
                    "std_icv": np.nan,
                    "behavior_label": "",
                    "behavior_reason": "",
                    "weighted_mean_MPD": np.nan,
                    "weighted_p95_MPD": np.nan,
                    "weighted_mean_pairwise_SSIM": np.nan,
                    "weighted_median_pairwise_SSIM": np.nan,
                    "weighted_p05_pairwise_SSIM": np.nan,
                    "min_pairwise_SSIM_overall": np.nan,
                    "class_metrics_json": "[]",
                }
            )

    summary_df = pd.DataFrame(summary_rows).sort_values("seed").reset_index(drop=True)
    per_class_df = (
        pd.DataFrame(per_class_rows).sort_values(["seed", "class_id"]).reset_index(drop=True)
        if per_class_rows
        else pd.DataFrame()
    )
    ranked_df, selected_seed, selection_note = add_selection_ranks(
        summary_df=summary_df,
        target_classes=int(args.ranking_target_classes),
        min_class_size_threshold=int(args.min_class_size_threshold),
        tie_epsilon=float(args.tie_epsilon),
    )

    summary_csv = run_root / "canonical_dictionary_seed_sweep_summary.csv"
    ranked_csv = run_root / "canonical_dictionary_seed_sweep_ranked.csv"
    per_class_csv = run_root / "canonical_dictionary_seed_sweep_per_class_metrics.csv"
    summary_df.to_csv(summary_csv, index=False)
    ranked_df.to_csv(ranked_csv, index=False)
    if not per_class_df.empty:
        per_class_df.to_csv(per_class_csv, index=False)
    else:
        pd.DataFrame(
            columns=[
                "seed",
                "class_id",
                "class_size",
                "pair_count",
                "mean_mpd",
                "p95_mpd",
                "mean_pairwise_ssim",
                "median_pairwise_ssim",
                "p05_pairwise_ssim",
                "min_pairwise_ssim",
            ]
        ).to_csv(per_class_csv, index=False)

    canonical_dict_path: Path | None = None
    canonical_manifest_path: Path | None = None
    if selected_seed is not None:
        selected_row = ranked_df[ranked_df["seed"] == int(selected_seed)].iloc[0]
        source_dict_path = Path(str(selected_row["dictionary_artifact_path"])).resolve()
        if not source_dict_path.exists():
            raise FileNotFoundError(f"Selected seed dictionary artifact missing: {source_dict_path}")

        canonical_out_dir = args.canonical_out_dir.resolve()
        canonical_out_dir.mkdir(parents=True, exist_ok=True)
        canonical_dict_path = canonical_out_dir / "canonical_dictionary.npz"
        canonical_manifest_path = canonical_out_dir / "canonical_dictionary_manifest.json"
        if canonical_dict_path.exists() and not args.overwrite:
            raise FileExistsError(
                f"Canonical dictionary exists: {canonical_dict_path}. Use --overwrite to replace it."
            )
        if canonical_manifest_path.exists() and not args.overwrite:
            raise FileExistsError(
                f"Canonical dictionary manifest exists: {canonical_manifest_path}. Use --overwrite to replace it."
            )

        shutil.copy2(source_dict_path, canonical_dict_path)
        components, source_meta = load_dictionary_artifact(source_dict_path)
        canonical_manifest = {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "canonical_seed": int(selected_seed),
            "canonical_dictionary_path": str(canonical_dict_path.resolve()),
            "source_dictionary_artifact_path": str(source_dict_path.resolve()),
            "selection_basis": {
                "target_classes": int(args.ranking_target_classes),
                "singleton_required": 0,
                "min_class_size_threshold": int(args.min_class_size_threshold),
                "composite_formula": "0.30*rank(mean_icv) + 0.30*rank(weighted_mean_MPD) + 0.30*rank(weighted_mean_pairwise_SSIM, desc) + 0.10*rank(min_class_size, desc)",
                "selection_note": selection_note,
            },
            "selected_seed_metrics": {
                "number_of_classes": int(selected_row["number_of_classes"]),
                "singleton_count": int(selected_row["singleton_count"]),
                "min_class_size": int(selected_row["min_class_size"]),
                "mean_icv": float(selected_row["mean_icv"]),
                "weighted_mean_MPD": float(selected_row["weighted_mean_MPD"]),
                "weighted_mean_pairwise_SSIM": float(selected_row["weighted_mean_pairwise_SSIM"]),
                "composite_score": float(selected_row["composite_score"]),
            },
            "fixed_pipeline_config": {
                "patch_w": PATCH_W,
                "patch_h": PATCH_H,
                "dictionary_size": int(components.shape[0]),
                "patch_vector_length": int(components.shape[1]),
                "standard_scaler": True,
                "sd_fraction": OFFICIAL_SD_FRACTION,
                "ranking_target_classes": int(args.ranking_target_classes),
                "feature_mode": source_meta.get("feature_mode", "raw"),
                "transform_algo": source_meta.get("transform_algo", "omp"),
                "transform_nnz": source_meta.get("transform_nnz", 2),
                "feature_vector_length": source_meta.get("feature_vector_length"),
                "patches_per_image": source_meta.get("patches_per_image"),
            },
            "source_dataset_artifacts": {k: str(v.resolve()) for k, v in input_paths.items()},
            "source_dictionary_metadata": source_meta,
            "seed_sweep_outputs": {
                "run_root": to_repo_or_abs(run_root),
                "summary_csv": to_repo_or_abs(summary_csv),
                "ranked_csv": to_repo_or_abs(ranked_csv),
                "per_class_csv": to_repo_or_abs(per_class_csv),
            },
        }
        canonical_manifest_path.write_text(json.dumps(canonical_manifest, indent=2), encoding="utf-8")
        log(f"Saved canonical dictionary: {canonical_dict_path}")
        log(f"Saved canonical manifest: {canonical_manifest_path}")

    report_path = run_root / "CANONICAL_DICTIONARY_REPORT.md"
    build_report(
        report_path=report_path,
        run_root=run_root,
        seeds=seeds,
        fractions=fractions,
        ranked_df=ranked_df,
        selected_seed=selected_seed,
        selection_note=selection_note,
        canonical_dict_path=canonical_dict_path,
        canonical_manifest_path=canonical_manifest_path,
        min_class_size_threshold=int(args.min_class_size_threshold),
    )

    sweep_manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_root": to_repo_or_abs(run_root),
        "seeds_tested": [int(s) for s in seeds],
        "fractions": [float(v) for v in fractions],
        "data_range_for_ssim": float(data_range),
        "data_min": float(data_min),
        "data_max": float(data_max),
        "selected_seed": None if selected_seed is None else int(selected_seed),
        "summary_csv": to_repo_or_abs(summary_csv),
        "ranked_csv": to_repo_or_abs(ranked_csv),
        "per_class_csv": to_repo_or_abs(per_class_csv),
        "report_md": to_repo_or_abs(report_path),
        "canonical_dictionary_path": "" if canonical_dict_path is None else str(canonical_dict_path.resolve()),
        "canonical_manifest_path": "" if canonical_manifest_path is None else str(canonical_manifest_path.resolve()),
    }
    (run_root / "seed_sweep_manifest.json").write_text(json.dumps(sweep_manifest, indent=2), encoding="utf-8")

    log(f"Wrote summary: {summary_csv}")
    log(f"Wrote ranked: {ranked_csv}")
    log(f"Wrote report: {report_path}")
    if selected_seed is None:
        raise RuntimeError("No canonical seed selected. Check ranked summary/report for failed eligibility.")
    log(f"Selected canonical seed: {selected_seed}")


if __name__ == "__main__":
    main()
