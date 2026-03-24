from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

from fossum_faithful_initial_utils import (
    FaithfulInitialConfig,
    ROOT,
    encode_images_with_full_sparse_features,
    train_dictionary_ordered_stream,
)


PATCH_W = 72
PATCH_H = 40
DICTIONARY_SIZE = 4
SEED = 11


@dataclass(frozen=True)
class PairSpec:
    label: str
    n_classes: int


PAIR_SPECS: Tuple[PairSpec, ...] = (
    PairSpec(label="n5", n_classes=5),
    PairSpec(label="n4", n_classes=4),
)


def parse_args() -> argparse.Namespace:
    default_base = ROOT / "results" / "fossum" / "faithful_initial_sd_autoprobe"
    p = argparse.ArgumentParser(description="Compare scaler vs no-scaler SD probe runs using full image assignments.")
    p.add_argument("--base-dir", type=Path, default=default_base)
    p.add_argument("--run-no-scaler", type=str, default="w72_h40_xds04_seed11_20260322_164245")
    p.add_argument("--run-with-scaler", type=str, default="w72_h40_xds04_seed11_20260322_215325")
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def first_existing(paths: List[Path]) -> Path:
    hit = next((p for p in paths if p.exists()), None)
    if hit is None:
        raise FileNotFoundError("None of these files exist:\n" + "\n".join(str(p) for p in paths))
    return hit


def load_x_norm_mask_with_fallback() -> Tuple[np.ndarray, np.ndarray, float]:
    x_norm_path = first_existing(
        [
            ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
            ROOT / "results" / "plots" / "X_surface_300_norm.npy",
        ]
    )
    mask_path = first_existing(
        [
            ROOT / "results" / "fossum" / "mask_common.npy",
            ROOT / "results" / "plots" / "mask_common.npy",
        ]
    )
    x_norm = np.load(x_norm_path).astype(np.float32, copy=False)
    mask = np.load(mask_path).astype(bool, copy=False)
    if x_norm.ndim != 3:
        raise RuntimeError(f"Expected x_norm ndim=3, got {x_norm.shape}")
    if mask.shape != x_norm.shape[1:]:
        raise RuntimeError(f"Mask mismatch: mask={mask.shape} vs x_norm={x_norm.shape}")
    x_norm = x_norm.copy()
    x_norm[:, ~mask] = np.nan
    valid_vals = x_norm[:, mask]
    vlim = float(np.percentile(np.abs(valid_vals), 98.0))
    if not np.isfinite(vlim) or vlim <= 0:
        vlim = 1.0
    return x_norm, mask, vlim


def read_runs_csv(run_dir: Path) -> pd.DataFrame:
    p = run_dir / "runs.csv"
    if not p.exists():
        raise FileNotFoundError(f"Missing runs.csv: {p}")
    return pd.read_csv(p)


def pick_sd_row_for_n_classes(df: pd.DataFrame, n_classes: int, run_name: str) -> pd.Series:
    sub = df[df["number_of_classes"].astype(int) == int(n_classes)].copy()
    if sub.empty:
        raise RuntimeError(f"{run_name}: no row with number_of_classes={n_classes}")
    # If more than one exists, pick lowest sd_fraction to keep deterministic.
    sub = sub.sort_values("sd_fraction_of_max", ascending=True)
    return sub.iloc[0]


def compute_features_and_linkages() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    x_norm, mask, vlim = load_x_norm_mask_with_fallback()

    cfg = FaithfulInitialConfig(
        include_valid_mask=True,
        mask_encoding="concat",
        feature_mode="raw",
        dict_batch_size=4096,
        transform_nnz=2,
    )

    model = train_dictionary_ordered_stream(
        X=x_norm,
        patch_h=PATCH_H,
        patch_w=PATCH_W,
        seed=SEED,
        dictionary_size=DICTIONARY_SIZE,
        cfg=cfg,
    )
    features, _ppi, _pvl, _fvl = encode_images_with_full_sparse_features(
        X=x_norm,
        model=model,
        patch_h=PATCH_H,
        patch_w=PATCH_W,
        dictionary_size=DICTIONARY_SIZE,
        cfg=cfg,
    )
    f_no = features.astype(np.float64, copy=False)
    f_ws = StandardScaler().fit_transform(f_no)

    z_no = linkage(f_no, method="ward", metric="euclidean")
    z_ws = linkage(f_ws, method="ward", metric="euclidean")
    return x_norm, mask, z_no, z_ws, vlim


def labels_from_distance(z: np.ndarray, separation_distance: float) -> np.ndarray:
    return fcluster(z, t=float(separation_distance), criterion="distance").astype(int)


def partition_from_labels(labels: np.ndarray) -> Dict[int, set]:
    out: Dict[int, set] = {}
    for c in sorted(np.unique(labels).tolist()):
        idx = np.where(labels == c)[0]
        out[int(c)] = set(int(x) for x in idx.tolist())
    return out


def overlap_matrix(no_members: Dict[int, set], ws_members: Dict[int, set]) -> Tuple[np.ndarray, List[int], List[int]]:
    no_ids = sorted(no_members.keys())
    ws_ids = sorted(ws_members.keys())
    mat = np.zeros((len(no_ids), len(ws_ids)), dtype=int)
    for i, cn in enumerate(no_ids):
        for j, cw in enumerate(ws_ids):
            mat[i, j] = len(no_members[cn].intersection(ws_members[cw]))
    return mat, no_ids, ws_ids


def match_classes(overlap: np.ndarray, no_ids: List[int], ws_ids: List[int]) -> Tuple[Dict[int, int], Dict[int, int], List[dict]]:
    rr, cc = linear_sum_assignment(-overlap)
    no_to_ws: Dict[int, int] = {}
    ws_to_no: Dict[int, int] = {}
    rows: List[dict] = []
    for r, c in sorted(zip(rr.tolist(), cc.tolist()), key=lambda t: no_ids[t[0]]):
        cn = no_ids[r]
        cw = ws_ids[c]
        ov = int(overlap[r, c])
        no_to_ws[cn] = cw
        ws_to_no[cw] = cn
        rows.append({"class_no_scaler": cn, "class_with_scaler": cw, "overlap_count": ov})
    return no_to_ws, ws_to_no, rows


def save_overlap_outputs(out_dir: Path, label: str, overlap: np.ndarray, no_ids: List[int], ws_ids: List[int]) -> None:
    df = pd.DataFrame(
        overlap,
        index=[f"no_C{c:02d}" for c in no_ids],
        columns=[f"with_C{c:02d}" for c in ws_ids],
    )
    df.to_csv(out_dir / f"{label}_class_overlap_counts.csv")

    fig, ax = plt.subplots(figsize=(1.5 + 1.25 * len(ws_ids), 1.5 + 1.1 * len(no_ids)))
    im = ax.imshow(overlap, cmap="viridis")
    ax.set_xticks(np.arange(len(ws_ids)))
    ax.set_xticklabels([f"C{c}" for c in ws_ids])
    ax.set_yticks(np.arange(len(no_ids)))
    ax.set_yticklabels([f"C{c}" for c in no_ids])
    ax.set_xlabel("With scaler class")
    ax.set_ylabel("No scaler class")
    ax.set_title(f"{label}: overlap matrix (counts)")
    vmax = max(1, int(overlap.max()))
    for i in range(overlap.shape[0]):
        for j in range(overlap.shape[1]):
            v = int(overlap[i, j])
            color = "white" if v > 0.45 * vmax else "black"
            ax.text(j, i, f"{v}", ha="center", va="center", fontsize=10, color=color)
    fig.colorbar(im, ax=ax, shrink=0.85, label="count")
    fig.tight_layout()
    fig.savefig(out_dir / f"{label}_class_overlap_heatmap.png", dpi=180)
    plt.close(fig)


def build_changed_df(labels_no: np.ndarray, labels_ws: np.ndarray, ws_to_no: Dict[int, int]) -> pd.DataFrame:
    n = int(labels_no.shape[0])
    rows = []
    for idx in range(n):
        old_class = int(labels_no[idx])
        new_raw = int(labels_ws[idx])
        new_mapped = int(ws_to_no[new_raw])
        rows.append(
            {
                "image_idx_0_based": idx,
                "image_z_1_based": idx + 1,
                "old_class_no_scaler": old_class,
                "new_class_with_scaler_raw": new_raw,
                "new_class_with_scaler_mapped_to_no": new_mapped,
                "changed": bool(old_class != new_mapped),
            }
        )
    return pd.DataFrame(rows)


def render_changed_panel(out_png: Path, changed_df: pd.DataFrame, x_norm: np.ndarray, mask: np.ndarray, vlim: float) -> None:
    changed = changed_df[changed_df["changed"]].copy().sort_values("image_idx_0_based")
    if changed.empty:
        fig, ax = plt.subplots(figsize=(8, 2))
        ax.axis("off")
        ax.text(0.5, 0.5, "No changed images", ha="center", va="center", fontsize=14)
        fig.tight_layout()
        fig.savefig(out_png, dpi=180)
        plt.close(fig)
        return

    cols = 8
    n = len(changed)
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.0, rows * 2.3))
    axes = np.array(axes).reshape(rows, cols)

    for k, ax in enumerate(axes.ravel()):
        if k >= n:
            ax.axis("off")
            continue
        rr = changed.iloc[k]
        idx = int(rr["image_idx_0_based"])
        z = int(rr["image_z_1_based"])
        old_c = int(rr["old_class_no_scaler"])
        new_c = int(rr["new_class_with_scaler_mapped_to_no"])
        img = np.where(mask, x_norm[idx], np.nan)
        ax.imshow(img, cmap="coolwarm", vmin=-vlim, vmax=vlim, aspect="auto")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"z={z:03d}\nC{old_c}->C{new_c}", fontsize=8)

    fig.suptitle("Changed images only (full 300-image assignment)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def mean_std_stack(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    return np.nanmean(x, axis=0), np.nanstd(x, axis=0)


def render_prototype_comparison(
    out_png: Path,
    match_rows: List[dict],
    no_members: Dict[int, set],
    ws_members: Dict[int, set],
    x_norm: np.ndarray,
    mask: np.ndarray,
    vlim: float,
) -> List[dict]:
    rows_data: List[dict] = []
    for mr in match_rows:
        cn = int(mr["class_no_scaler"])
        cw = int(mr["class_with_scaler"])
        idx_no = np.array(sorted(no_members[cn]), dtype=int)
        idx_ws = np.array(sorted(ws_members[cw]), dtype=int)
        mean_no, std_no = mean_std_stack(x_norm[idx_no])
        mean_ws, std_ws = mean_std_stack(x_norm[idx_ws])
        diff = mean_ws - mean_no
        std_diff = std_ws - std_no
        ov = int(mr["overlap_count"])
        un = len(no_members[cn].union(ws_members[cw]))
        jac = float(ov / un) if un > 0 else 0.0
        rows_data.append(
            {
                "class_no_scaler": cn,
                "class_with_scaler": cw,
                "n_no_scaler": int(len(idx_no)),
                "n_with_scaler": int(len(idx_ws)),
                "overlap_count": ov,
                "jaccard": jac,
                "prototype_mean_abs_diff": float(np.nanmean(np.abs(diff[mask]))),
                "prototype_max_abs_diff": float(np.nanmax(np.abs(diff[mask]))),
                "spread_mean_abs_diff": float(np.nanmean(np.abs(std_diff[mask]))),
                "spread_max_abs_diff": float(np.nanmax(np.abs(std_diff[mask]))),
                "mean_no": mean_no,
                "mean_ws": mean_ws,
                "mean_diff": diff,
                "std_no": std_no,
                "std_ws": std_ws,
                "std_diff": std_diff,
            }
        )

    diff_vmax = max(float(np.nanmax(np.abs(rd["mean_diff"][mask]))) for rd in rows_data)
    if not np.isfinite(diff_vmax) or diff_vmax <= 0:
        diff_vmax = 1.0

    nrows = len(rows_data)
    fig, axes = plt.subplots(nrows, 3, figsize=(11.5, max(3.0, 2.8 * nrows)))
    if nrows == 1:
        axes = np.array([axes])
    for r, rd in enumerate(rows_data):
        cn = rd["class_no_scaler"]
        cw = rd["class_with_scaler"]
        ov = rd["overlap_count"]
        jac = rd["jaccard"]
        axes[r, 0].imshow(np.where(mask, rd["mean_no"], np.nan), cmap="coolwarm", vmin=-vlim, vmax=vlim, aspect="auto")
        axes[r, 1].imshow(np.where(mask, rd["mean_ws"], np.nan), cmap="coolwarm", vmin=-vlim, vmax=vlim, aspect="auto")
        axes[r, 2].imshow(np.where(mask, rd["mean_diff"], np.nan), cmap="bwr", vmin=-diff_vmax, vmax=diff_vmax, aspect="auto")
        axes[r, 0].set_ylabel(f"no C{cn} vs with C{cw}\nov={ov}, J={jac:.3f}", fontsize=9)
        for c in range(3):
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])
    axes[0, 0].set_title("Prototype (no scaler)")
    axes[0, 1].set_title("Prototype (with scaler)")
    axes[0, 2].set_title("Difference (with - no)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
    return rows_data


def render_spread_comparison(out_png: Path, rows_data: List[dict], mask: np.ndarray) -> None:
    std_vmax = max(
        max(float(np.nanmax(rd["std_no"][mask])), float(np.nanmax(rd["std_ws"][mask])))
        for rd in rows_data
    )
    if not np.isfinite(std_vmax) or std_vmax <= 0:
        std_vmax = 1.0
    diff_vmax = max(float(np.nanmax(np.abs(rd["std_diff"][mask]))) for rd in rows_data)
    if not np.isfinite(diff_vmax) or diff_vmax <= 0:
        diff_vmax = 1.0

    nrows = len(rows_data)
    fig, axes = plt.subplots(nrows, 3, figsize=(11.5, max(3.0, 2.8 * nrows)))
    if nrows == 1:
        axes = np.array([axes])
    for r, rd in enumerate(rows_data):
        cn = rd["class_no_scaler"]
        cw = rd["class_with_scaler"]
        axes[r, 0].imshow(np.where(mask, rd["std_no"], np.nan), cmap="magma", vmin=0, vmax=std_vmax, aspect="auto")
        axes[r, 1].imshow(np.where(mask, rd["std_ws"], np.nan), cmap="magma", vmin=0, vmax=std_vmax, aspect="auto")
        axes[r, 2].imshow(np.where(mask, rd["std_diff"], np.nan), cmap="bwr", vmin=-diff_vmax, vmax=diff_vmax, aspect="auto")
        axes[r, 0].set_ylabel(f"no C{cn} vs with C{cw}", fontsize=9)
        for c in range(3):
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])
    axes[0, 0].set_title("Intra-class std (no scaler)")
    axes[0, 1].set_title("Intra-class std (with scaler)")
    axes[0, 2].set_title("Std diff (with - no)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def analyze_pair(
    out_root: Path,
    pair: PairSpec,
    row_no: pd.Series,
    row_ws: pd.Series,
    threshold_no: float,
    threshold_ws: float,
    used_maxclust_fallback_no: bool,
    used_maxclust_fallback_ws: bool,
    labels_no: np.ndarray,
    labels_ws: np.ndarray,
    x_norm: np.ndarray,
    mask: np.ndarray,
    vlim: float,
) -> dict:
    out_dir = out_root / pair.label
    out_dir.mkdir(parents=True, exist_ok=True)

    no_members = partition_from_labels(labels_no)
    ws_members = partition_from_labels(labels_ws)

    overlap, no_ids, ws_ids = overlap_matrix(no_members, ws_members)
    save_overlap_outputs(out_dir, pair.label, overlap, no_ids, ws_ids)
    _no_to_ws, ws_to_no, match_rows = match_classes(overlap, no_ids, ws_ids)

    for mr in match_rows:
        cn = mr["class_no_scaler"]
        cw = mr["class_with_scaler"]
        ov = int(mr["overlap_count"])
        nn = len(no_members[cn])
        nw = len(ws_members[cw])
        mr["n_no_scaler"] = int(nn)
        mr["n_with_scaler"] = int(nw)
        mr["overlap_pct_of_no"] = float(ov / max(1, nn))
        mr["overlap_pct_of_with"] = float(ov / max(1, nw))
        mr["jaccard"] = float(ov / max(1, len(no_members[cn].union(ws_members[cw]))))

    matched_df = pd.DataFrame(match_rows).sort_values("class_no_scaler")
    matched_df.to_csv(out_dir / f"{pair.label}_matched_classes.csv", index=False)

    changed_df = build_changed_df(labels_no, labels_ws, ws_to_no)
    changed_df.to_csv(out_dir / f"{pair.label}_image_assignment_changes.csv", index=False)
    render_changed_panel(out_dir / f"{pair.label}_changed_images_panel.png", changed_df, x_norm, mask, vlim)

    rows_data = render_prototype_comparison(
        out_png=out_dir / f"{pair.label}_prototype_comparison.png",
        match_rows=match_rows,
        no_members=no_members,
        ws_members=ws_members,
        x_norm=x_norm,
        mask=mask,
        vlim=vlim,
    )
    render_spread_comparison(
        out_png=out_dir / f"{pair.label}_spread_std_comparison.png",
        rows_data=rows_data,
        mask=mask,
    )

    metrics_df = pd.DataFrame(
        [
            {
                "class_no_scaler": rd["class_no_scaler"],
                "class_with_scaler": rd["class_with_scaler"],
                "n_no_scaler": rd["n_no_scaler"],
                "n_with_scaler": rd["n_with_scaler"],
                "overlap_count": rd["overlap_count"],
                "jaccard": rd["jaccard"],
                "prototype_mean_abs_diff": rd["prototype_mean_abs_diff"],
                "prototype_max_abs_diff": rd["prototype_max_abs_diff"],
                "spread_mean_abs_diff": rd["spread_mean_abs_diff"],
                "spread_max_abs_diff": rd["spread_max_abs_diff"],
            }
            for rd in rows_data
        ]
    ).sort_values("class_no_scaler")
    metrics_df.to_csv(out_dir / f"{pair.label}_matched_class_metrics.csv", index=False)

    changed_count = int(changed_df["changed"].sum())
    total_count = int(len(changed_df))
    return {
        "label": pair.label,
        "n_classes": pair.n_classes,
        "no_scaler_sd_fraction": float(row_no["sd_fraction_of_max"]),
        "no_scaler_separation_distance": float(row_no["separation_distance"]),
        "no_scaler_recomputed_threshold": float(threshold_no),
        "no_scaler_used_maxclust_fallback": bool(used_maxclust_fallback_no),
        "with_scaler_sd_fraction": float(row_ws["sd_fraction_of_max"]),
        "with_scaler_separation_distance": float(row_ws["separation_distance"]),
        "with_scaler_recomputed_threshold": float(threshold_ws),
        "with_scaler_used_maxclust_fallback": bool(used_maxclust_fallback_ws),
        "changed_count": changed_count,
        "total_count": total_count,
        "changed_pct": float(changed_count / max(1, total_count)),
        "mean_jaccard": float(matched_df["jaccard"].mean()),
        "min_jaccard": float(matched_df["jaccard"].min()),
        "mean_prototype_mean_abs_diff": float(metrics_df["prototype_mean_abs_diff"].mean()),
        "max_prototype_max_abs_diff": float(metrics_df["prototype_max_abs_diff"].max()),
        "mean_spread_mean_abs_diff": float(metrics_df["spread_mean_abs_diff"].mean()),
        "max_spread_max_abs_diff": float(metrics_df["spread_max_abs_diff"].max()),
    }


def compare_dendrogram_profiles(out_root: Path, run_no: Path, run_ws: Path) -> dict:
    no_vals = pd.read_csv(run_no / "dendrogram" / "merge_distances.csv")["merge_distance"].astype(float).to_numpy()
    ws_vals = pd.read_csv(run_ws / "dendrogram" / "merge_distances.csv")["merge_distance"].astype(float).to_numpy()
    n = min(len(no_vals), len(ws_vals))
    no_vals = no_vals[:n]
    ws_vals = ws_vals[:n]
    idx = np.arange(1, n + 1)
    no_norm = no_vals / max(float(np.max(no_vals)), 1e-12)
    ws_norm = ws_vals / max(float(np.max(ws_vals)), 1e-12)

    pearson = float(np.corrcoef(no_norm, ws_norm)[0, 1])
    spear = float(spearmanr(no_norm, ws_norm).correlation)
    mad = float(np.mean(np.abs(no_norm - ws_norm)))

    pd.DataFrame(
        {
            "merge_index": idx,
            "no_scaler_merge_distance": no_vals,
            "with_scaler_merge_distance": ws_vals,
            "no_scaler_norm": no_norm,
            "with_scaler_norm": ws_norm,
            "norm_abs_diff": np.abs(no_norm - ws_norm),
        }
    ).to_csv(out_root / "dendrogram_merge_distance_profile_comparison.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(idx, no_vals, lw=1.3, label="No scaler")
    axes[0].plot(idx, ws_vals, lw=1.3, label="With scaler")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Merge distance (log)")
    axes[0].set_title("Raw merge-distance profile")
    axes[0].grid(alpha=0.2)
    axes[0].legend(loc="best")

    axes[1].plot(idx, no_norm, lw=1.3, label="No scaler norm")
    axes[1].plot(idx, ws_norm, lw=1.3, label="With scaler norm")
    axes[1].set_xlabel("Merge index")
    axes[1].set_ylabel("Normalized distance")
    axes[1].set_title(f"Normalized profile | Pearson={pearson:.4f}, Spearman={spear:.4f}, MAD={mad:.4f}")
    axes[1].grid(alpha=0.2)
    axes[1].legend(loc="best")

    fig.tight_layout()
    fig.savefig(out_root / "dendrogram_profile_comparison.png", dpi=180)
    plt.close(fig)

    return {
        "n_merges_compared": int(n),
        "pearson_norm": pearson,
        "spearman_norm": spear,
        "mean_abs_diff_norm": mad,
        "no_scaler_max_merge_distance": float(np.max(no_vals)),
        "with_scaler_max_merge_distance": float(np.max(ws_vals)),
    }


def main() -> None:
    args = parse_args()
    base_dir = args.base_dir.resolve()
    run_no = (base_dir / args.run_no_scaler).resolve()
    run_ws = (base_dir / args.run_with_scaler).resolve()
    if args.output_dir is None:
        out_root = (base_dir / f"comparison_fullassign_{args.run_no_scaler}_VS_{args.run_with_scaler}").resolve()
    else:
        out_root = args.output_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    runs_no = read_runs_csv(run_no)
    runs_ws = read_runs_csv(run_ws)

    x_norm, mask, z_no, z_ws, vlim = compute_features_and_linkages()
    n_images = int(x_norm.shape[0])

    # Reproducibility check against stored tree_info max merge distances.
    max_no = float(z_no[-1, 2])
    max_ws = float(z_ws[-1, 2])

    pair_summaries = []
    for pair in PAIR_SPECS:
        row_no = pick_sd_row_for_n_classes(runs_no, pair.n_classes, args.run_no_scaler)
        row_ws = pick_sd_row_for_n_classes(runs_ws, pair.n_classes, args.run_with_scaler)
        frac_no = float(row_no["sd_fraction_of_max"])
        frac_ws = float(row_ws["sd_fraction_of_max"])
        # Use fraction-of-max from each run to stay comparable even if absolute
        # merge distance scale shifts slightly across re-runs.
        t_no = frac_no * float(z_no[-1, 2])
        t_ws = frac_ws * float(z_ws[-1, 2])
        labels_no = labels_from_distance(z_no, t_no)
        labels_ws = labels_from_distance(z_ws, t_ws)

        got_no = int(np.unique(labels_no).size)
        got_ws = int(np.unique(labels_ws).size)
        fallback_no = False
        fallback_ws = False
        if got_no != pair.n_classes:
            labels_no = fcluster(z_no, t=pair.n_classes, criterion="maxclust").astype(int)
            fallback_no = True
            got_no = int(np.unique(labels_no).size)
        if got_ws != pair.n_classes:
            labels_ws = fcluster(z_ws, t=pair.n_classes, criterion="maxclust").astype(int)
            fallback_ws = True
            got_ws = int(np.unique(labels_ws).size)
        if got_no != pair.n_classes or got_ws != pair.n_classes:
            raise RuntimeError(
                f"{pair.label}: unable to recover n={pair.n_classes}. got no_scaler={got_no}, with_scaler={got_ws}."
            )

        summary = analyze_pair(
            out_root=out_root,
            pair=pair,
            row_no=row_no,
            row_ws=row_ws,
            threshold_no=t_no,
            threshold_ws=t_ws,
            used_maxclust_fallback_no=fallback_no,
            used_maxclust_fallback_ws=fallback_ws,
            labels_no=labels_no,
            labels_ws=labels_ws,
            x_norm=x_norm,
            mask=mask,
            vlim=vlim,
        )
        pair_summaries.append(summary)

    dendro = compare_dendrogram_profiles(out_root, run_no, run_ws)

    summary = {
        "run_no_scaler": str(run_no),
        "run_with_scaler": str(run_ws),
        "output_root": str(out_root),
        "n_images": n_images,
        "recomputed_max_merge_distance_no_scaler": max_no,
        "recomputed_max_merge_distance_with_scaler": max_ws,
        "pair_summaries": pair_summaries,
        "dendrogram_summary": dendro,
    }
    with (out_root / "comparison_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Comparison complete. Output: {out_root}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
