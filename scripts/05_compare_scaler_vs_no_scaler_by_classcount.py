from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr


@dataclass(frozen=True)
class PairSpec:
    label: str
    no_scaler_sd_dir: str
    with_scaler_sd_dir: str
    expected_n_classes: int


PAIR_SPECS: Tuple[PairSpec, ...] = (
    PairSpec(label="n5", no_scaler_sd_dir="sd_20pct", with_scaler_sd_dir="sd_30pct", expected_n_classes=5),
    PairSpec(label="n4", no_scaler_sd_dir="sd_30pct", with_scaler_sd_dir="sd_40pct", expected_n_classes=4),
)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    default_base = project_root / "results" / "fossum" / "faithful_initial_sd_autoprobe"
    p = argparse.ArgumentParser(description="Strong visual comparison between no-scaler and with-scaler SD probe runs.")
    p.add_argument("--project-root", type=Path, default=project_root)
    p.add_argument("--base-dir", type=Path, default=default_base)
    p.add_argument("--run-no-scaler", type=str, default="w72_h40_xds04_seed11_20260322_164245")
    p.add_argument("--run-with-scaler", type=str, default="w72_h40_xds04_seed11_20260322_215325")
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def find_numeric_paths(project_root: Path) -> Dict[str, Path]:
    candidates = {
        "X_norm": [
            project_root / "results" / "fossum" / "X_surface_300_norm.npy",
            project_root / "results" / "plots" / "X_surface_300_norm.npy",
        ],
        "mask": [
            project_root / "results" / "fossum" / "mask_common.npy",
            project_root / "results" / "plots" / "mask_common.npy",
        ],
    }
    out: Dict[str, Path] = {}
    missing: List[str] = []
    for k, paths in candidates.items():
        hit = next((pp for pp in paths if pp.exists()), None)
        if hit is None:
            missing.append(k)
        else:
            out[k] = hit
    if missing:
        raise FileNotFoundError(f"Missing numeric inputs: {missing}")
    return out


def load_numeric_inputs(project_root: Path) -> Tuple[np.ndarray, np.ndarray, float]:
    paths = find_numeric_paths(project_root)
    x_norm = np.load(paths["X_norm"]).astype(np.float32, copy=False)
    mask = np.load(paths["mask"]).astype(bool, copy=False)
    if x_norm.ndim != 3:
        raise RuntimeError(f"Expected x_norm ndim=3, got {x_norm.shape}")
    if mask.shape != x_norm.shape[1:]:
        raise RuntimeError(f"Mask shape mismatch: mask={mask.shape} vs x_norm={x_norm.shape}")
    x_norm = x_norm.copy()
    x_norm[:, ~mask] = np.nan
    valid_vals = x_norm[:, mask]
    vlim = float(np.percentile(np.abs(valid_vals), 98.0))
    if not np.isfinite(vlim) or vlim <= 0:
        vlim = 1.0
    return x_norm, mask, vlim


def parse_class_id_from_file_name(name: str) -> int:
    m = re.fullmatch(r"class_(\d+)_members_list\.csv", name)
    if m is None:
        raise ValueError(f"Unexpected class members file: {name}")
    return int(m.group(1))


def load_partition(sd_dir: Path) -> Tuple[Dict[int, set], Dict[int, int], Dict[int, dict]]:
    class_files = sorted(sd_dir.glob("class_*_members_list.csv"))
    if not class_files:
        raise FileNotFoundError(f"No class members list CSV found in {sd_dir}")

    class_members: Dict[int, set] = {}
    assignments: Dict[int, int] = {}
    image_meta: Dict[int, dict] = {}

    for csv_path in class_files:
        class_id = parse_class_id_from_file_name(csv_path.name)
        df = pd.read_csv(csv_path)
        if "image_idx_0_based" not in df.columns:
            raise RuntimeError(f"Missing image_idx_0_based in {csv_path}")
        idxs = df["image_idx_0_based"].astype(int).to_numpy()
        if len(np.unique(idxs)) != len(idxs):
            raise RuntimeError(f"Duplicate image indices in {csv_path}")
        class_members[class_id] = set(int(x) for x in idxs.tolist())

        for _, row in df.iterrows():
            idx = int(row["image_idx_0_based"])
            if idx in assignments:
                raise RuntimeError(f"Image idx {idx} repeated across classes in {sd_dir}")
            assignments[idx] = class_id
            image_meta[idx] = {
                "image_z_1_based": int(row["image_z_1_based"]),
                "png_path": str(row["png_path"]),
            }

    return class_members, assignments, image_meta


def build_overlap_matrix(no_members: Dict[int, set], with_members: Dict[int, set]) -> Tuple[np.ndarray, List[int], List[int]]:
    no_ids = sorted(no_members.keys())
    with_ids = sorted(with_members.keys())
    mat = np.zeros((len(no_ids), len(with_ids)), dtype=int)
    for i, c_no in enumerate(no_ids):
        for j, c_ws in enumerate(with_ids):
            mat[i, j] = len(no_members[c_no].intersection(with_members[c_ws]))
    return mat, no_ids, with_ids


def optimal_overlap_matching(
    overlap_counts: np.ndarray, no_ids: List[int], with_ids: List[int]
) -> Tuple[Dict[int, int], Dict[int, int], List[dict]]:
    row_ind, col_ind = linear_sum_assignment(-overlap_counts)
    no_to_with: Dict[int, int] = {}
    with_to_no: Dict[int, int] = {}
    pairs: List[dict] = []

    for rr, cc in sorted(zip(row_ind.tolist(), col_ind.tolist()), key=lambda x: no_ids[x[0]]):
        c_no = no_ids[rr]
        c_ws = with_ids[cc]
        ov = int(overlap_counts[rr, cc])
        no_to_with[c_no] = c_ws
        with_to_no[c_ws] = c_no
        pairs.append({"class_no_scaler": c_no, "class_with_scaler": c_ws, "overlap_count": ov})
    return no_to_with, with_to_no, pairs


def save_overlap_table_and_heatmap(
    out_dir: Path,
    label: str,
    overlap_counts: np.ndarray,
    no_ids: List[int],
    with_ids: List[int],
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        overlap_counts,
        index=[f"no_C{cid:02d}" for cid in no_ids],
        columns=[f"with_C{cid:02d}" for cid in with_ids],
    )
    csv_path = out_dir / f"{label}_class_overlap_counts.csv"
    df.to_csv(csv_path, index=True)

    fig, ax = plt.subplots(figsize=(1.6 + 1.3 * len(with_ids), 1.6 + 1.2 * len(no_ids)))
    im = ax.imshow(overlap_counts, cmap="viridis")
    ax.set_xticks(np.arange(len(with_ids)))
    ax.set_xticklabels([f"C{cid}" for cid in with_ids])
    ax.set_yticks(np.arange(len(no_ids)))
    ax.set_yticklabels([f"C{cid}" for cid in no_ids])
    ax.set_xlabel("With scaler class")
    ax.set_ylabel("Without scaler class")
    ax.set_title(f"{label}: class overlap counts")
    for i in range(overlap_counts.shape[0]):
        for j in range(overlap_counts.shape[1]):
            val = int(overlap_counts[i, j])
            ax.text(j, i, f"{val}", ha="center", va="center", color="white" if val > overlap_counts.max() * 0.5 else "black")
    fig.colorbar(im, ax=ax, shrink=0.85, label="Overlap count")
    fig.tight_layout()
    png_path = out_dir / f"{label}_class_overlap_heatmap.png"
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    return csv_path


def build_changed_assignments(
    assignments_no: Dict[int, int],
    assignments_ws: Dict[int, int],
    with_to_no: Dict[int, int],
    image_meta: Dict[int, dict],
) -> pd.DataFrame:
    shared = sorted(set(assignments_no.keys()).intersection(assignments_ws.keys()))
    rows = []
    for idx in shared:
        old_class = int(assignments_no[idx])
        new_raw = int(assignments_ws[idx])
        new_mapped = int(with_to_no[new_raw])
        changed = old_class != new_mapped
        meta = image_meta.get(idx, {})
        rows.append(
            {
                "image_idx_0_based": idx,
                "image_z_1_based": int(meta.get("image_z_1_based", idx + 1)),
                "png_path": str(meta.get("png_path", "")),
                "old_class_no_scaler": old_class,
                "new_class_with_scaler_raw": new_raw,
                "new_class_with_scaler_mapped_to_no": new_mapped,
                "changed": bool(changed),
            }
        )
    df = pd.DataFrame(rows)
    return df.sort_values("image_idx_0_based").reset_index(drop=True)


def render_changed_panel(
    out_png: Path,
    changed_df: pd.DataFrame,
    x_norm: np.ndarray,
    mask: np.ndarray,
    vlim: float,
) -> None:
    changed = changed_df[changed_df["changed"]].copy()
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
    axes_arr = np.array(axes).reshape(rows, cols)
    masked = np.where(mask, 1.0, np.nan)

    for ai, ax in enumerate(axes_arr.ravel()):
        if ai >= n:
            ax.axis("off")
            continue
        row = changed.iloc[ai]
        idx = int(row["image_idx_0_based"])
        z = int(row["image_z_1_based"])
        old_c = int(row["old_class_no_scaler"])
        new_c = int(row["new_class_with_scaler_mapped_to_no"])
        img = np.where(masked == 1.0, x_norm[idx], np.nan)
        im = ax.imshow(img, cmap="coolwarm", vmin=-vlim, vmax=vlim, aspect="auto")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"z={z:03d}\nC{old_c} -> C{new_c}", fontsize=8)

    fig.suptitle("Changed images only (labels mapped by max-overlap matching)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def _safe_mean_std(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    return np.nanmean(x, axis=0), np.nanstd(x, axis=0)


def render_matched_prototype_comparison(
    out_png: Path,
    pair_rows: List[dict],
    no_members: Dict[int, set],
    with_members: Dict[int, set],
    x_norm: np.ndarray,
    mask: np.ndarray,
    vlim: float,
) -> List[dict]:
    rows_data: List[dict] = []
    proto_diffs: List[np.ndarray] = []

    for pr in pair_rows:
        c_no = int(pr["class_no_scaler"])
        c_ws = int(pr["class_with_scaler"])
        idx_no = np.array(sorted(no_members[c_no]), dtype=int)
        idx_ws = np.array(sorted(with_members[c_ws]), dtype=int)
        mean_no, std_no = _safe_mean_std(x_norm[idx_no])
        mean_ws, std_ws = _safe_mean_std(x_norm[idx_ws])
        diff = mean_ws - mean_no
        std_diff = std_ws - std_no
        proto_diffs.append(diff[mask])

        overlap = int(pr["overlap_count"])
        union = len(no_members[c_no].union(with_members[c_ws]))
        jaccard = float(overlap / union) if union > 0 else 0.0
        rows_data.append(
            {
                "class_no_scaler": c_no,
                "class_with_scaler": c_ws,
                "n_no_scaler": int(len(idx_no)),
                "n_with_scaler": int(len(idx_ws)),
                "overlap_count": overlap,
                "jaccard": jaccard,
                "prototype_mean_abs_diff": float(np.nanmean(np.abs(diff[mask]))),
                "prototype_max_abs_diff": float(np.nanmax(np.abs(diff[mask]))),
                "spread_mean_abs_diff": float(np.nanmean(np.abs(std_diff[mask]))),
                "spread_max_abs_diff": float(np.nanmax(np.abs(std_diff[mask]))),
                "mean_no": mean_no,
                "mean_ws": mean_ws,
                "diff": diff,
                "std_no": std_no,
                "std_ws": std_ws,
                "std_diff": std_diff,
            }
        )

    diff_vmax = max(float(np.nanmax(np.abs(v))) for v in proto_diffs) if proto_diffs else 1.0
    if not np.isfinite(diff_vmax) or diff_vmax <= 0:
        diff_vmax = 1.0

    n_rows = len(rows_data)
    fig, axes = plt.subplots(n_rows, 3, figsize=(11.5, max(2.8 * n_rows, 3.0)))
    if n_rows == 1:
        axes = np.array([axes])

    for r, row in enumerate(rows_data):
        c_no = row["class_no_scaler"]
        c_ws = row["class_with_scaler"]
        ov = row["overlap_count"]
        jac = row["jaccard"]
        m_no = np.where(mask, row["mean_no"], np.nan)
        m_ws = np.where(mask, row["mean_ws"], np.nan)
        m_df = np.where(mask, row["diff"], np.nan)
        axes[r, 0].imshow(m_no, cmap="coolwarm", vmin=-vlim, vmax=vlim, aspect="auto")
        axes[r, 1].imshow(m_ws, cmap="coolwarm", vmin=-vlim, vmax=vlim, aspect="auto")
        axes[r, 2].imshow(m_df, cmap="bwr", vmin=-diff_vmax, vmax=diff_vmax, aspect="auto")
        axes[r, 0].set_ylabel(f"no C{c_no} / with C{c_ws}\nov={ov}, J={jac:.3f}", fontsize=9)
        for c in range(3):
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])

    axes[0, 0].set_title("Prototype mean (no scaler)")
    axes[0, 1].set_title("Prototype mean (with scaler)")
    axes[0, 2].set_title("Difference (with - no)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)

    return rows_data


def render_matched_spread_comparison(
    out_png: Path,
    rows_data: List[dict],
    mask: np.ndarray,
) -> None:
    if not rows_data:
        return
    std_vmax = max(
        float(np.nanmax(np.where(mask, rd["std_no"], np.nan)))
        for rd in rows_data
    )
    std_vmax = max(
        std_vmax,
        max(float(np.nanmax(np.where(mask, rd["std_ws"], np.nan))) for rd in rows_data),
    )
    if not np.isfinite(std_vmax) or std_vmax <= 0:
        std_vmax = 1.0

    std_diff_vmax = max(float(np.nanmax(np.abs(rd["std_diff"][mask]))) for rd in rows_data)
    if not np.isfinite(std_diff_vmax) or std_diff_vmax <= 0:
        std_diff_vmax = 1.0

    n_rows = len(rows_data)
    fig, axes = plt.subplots(n_rows, 3, figsize=(11.5, max(2.8 * n_rows, 3.0)))
    if n_rows == 1:
        axes = np.array([axes])

    for r, row in enumerate(rows_data):
        c_no = row["class_no_scaler"]
        c_ws = row["class_with_scaler"]
        s_no = np.where(mask, row["std_no"], np.nan)
        s_ws = np.where(mask, row["std_ws"], np.nan)
        s_df = np.where(mask, row["std_diff"], np.nan)
        axes[r, 0].imshow(s_no, cmap="magma", vmin=0.0, vmax=std_vmax, aspect="auto")
        axes[r, 1].imshow(s_ws, cmap="magma", vmin=0.0, vmax=std_vmax, aspect="auto")
        axes[r, 2].imshow(s_df, cmap="bwr", vmin=-std_diff_vmax, vmax=std_diff_vmax, aspect="auto")
        axes[r, 0].set_ylabel(f"no C{c_no} / with C{c_ws}", fontsize=9)
        for c in range(3):
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])

    axes[0, 0].set_title("Std map (no scaler)")
    axes[0, 1].set_title("Std map (with scaler)")
    axes[0, 2].set_title("Std diff (with - no)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def analyze_pair(
    out_root: Path,
    pair: PairSpec,
    run_no_dir: Path,
    run_ws_dir: Path,
    x_norm: np.ndarray,
    mask: np.ndarray,
    vlim: float,
) -> dict:
    no_sd_dir = run_no_dir / pair.no_scaler_sd_dir
    ws_sd_dir = run_ws_dir / pair.with_scaler_sd_dir
    out_dir = out_root / pair.label
    out_dir.mkdir(parents=True, exist_ok=True)

    no_members, no_assign, no_meta = load_partition(no_sd_dir)
    ws_members, ws_assign, ws_meta = load_partition(ws_sd_dir)

    if len(no_members) != pair.expected_n_classes:
        raise RuntimeError(f"{pair.label}: expected {pair.expected_n_classes} classes in no-scaler, got {len(no_members)}")
    if len(ws_members) != pair.expected_n_classes:
        raise RuntimeError(f"{pair.label}: expected {pair.expected_n_classes} classes in with-scaler, got {len(ws_members)}")

    overlap_counts, no_ids, ws_ids = build_overlap_matrix(no_members=no_members, with_members=ws_members)
    overlap_csv = save_overlap_table_and_heatmap(out_dir=out_dir, label=pair.label, overlap_counts=overlap_counts, no_ids=no_ids, with_ids=ws_ids)
    no_to_with, with_to_no, match_rows = optimal_overlap_matching(overlap_counts=overlap_counts, no_ids=no_ids, with_ids=ws_ids)

    for row in match_rows:
        c_no = row["class_no_scaler"]
        c_ws = row["class_with_scaler"]
        overlap = row["overlap_count"]
        row["n_no_scaler"] = int(len(no_members[c_no]))
        row["n_with_scaler"] = int(len(ws_members[c_ws]))
        row["overlap_pct_of_no"] = float(overlap / max(1, row["n_no_scaler"]))
        row["overlap_pct_of_with"] = float(overlap / max(1, row["n_with_scaler"]))
        row["jaccard"] = float(overlap / max(1, len(no_members[c_no].union(ws_members[c_ws]))))

    match_df = pd.DataFrame(match_rows).sort_values("class_no_scaler")
    match_df.to_csv(out_dir / f"{pair.label}_matched_classes.csv", index=False)

    merged_meta = dict(no_meta)
    merged_meta.update(ws_meta)
    changed_df = build_changed_assignments(
        assignments_no=no_assign,
        assignments_ws=ws_assign,
        with_to_no=with_to_no,
        image_meta=merged_meta,
    )
    changed_df.to_csv(out_dir / f"{pair.label}_image_assignment_changes.csv", index=False)
    render_changed_panel(
        out_png=out_dir / f"{pair.label}_changed_images_panel.png",
        changed_df=changed_df,
        x_norm=x_norm,
        mask=mask,
        vlim=vlim,
    )

    rows_data = render_matched_prototype_comparison(
        out_png=out_dir / f"{pair.label}_prototype_comparison.png",
        pair_rows=match_rows,
        no_members=no_members,
        with_members=ws_members,
        x_norm=x_norm,
        mask=mask,
        vlim=vlim,
    )
    render_matched_spread_comparison(
        out_png=out_dir / f"{pair.label}_spread_std_comparison.png",
        rows_data=rows_data,
        mask=mask,
    )

    metrics_rows = []
    for rd in rows_data:
        metrics_rows.append(
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
        )
    metrics_df = pd.DataFrame(metrics_rows).sort_values("class_no_scaler")
    metrics_df.to_csv(out_dir / f"{pair.label}_matched_class_metrics.csv", index=False)

    changed_count = int(changed_df["changed"].sum())
    total_count = int(len(changed_df))
    unchanged_count = int(total_count - changed_count)

    return {
        "label": pair.label,
        "no_scaler_sd_dir": pair.no_scaler_sd_dir,
        "with_scaler_sd_dir": pair.with_scaler_sd_dir,
        "n_classes": pair.expected_n_classes,
        "changed_count": changed_count,
        "unchanged_count": unchanged_count,
        "total_count": total_count,
        "changed_pct": float(changed_count / max(1, total_count)),
        "mean_jaccard": float(match_df["jaccard"].mean()),
        "min_jaccard": float(match_df["jaccard"].min()),
        "mean_overlap_pct_of_no": float(match_df["overlap_pct_of_no"].mean()),
        "mean_overlap_pct_of_with": float(match_df["overlap_pct_of_with"].mean()),
        "overlap_csv": str(overlap_csv),
        "matched_classes_csv": str(out_dir / f"{pair.label}_matched_classes.csv"),
        "changes_csv": str(out_dir / f"{pair.label}_image_assignment_changes.csv"),
    }


def compare_dendrogram_profiles(out_root: Path, run_no_dir: Path, run_ws_dir: Path) -> dict:
    no_csv = run_no_dir / "dendrogram" / "merge_distances.csv"
    ws_csv = run_ws_dir / "dendrogram" / "merge_distances.csv"
    if not no_csv.exists() or not ws_csv.exists():
        raise FileNotFoundError("Missing dendrogram merge_distances.csv in one or both runs.")

    no_vals = pd.read_csv(no_csv)["merge_distance"].astype(float).to_numpy()
    ws_vals = pd.read_csv(ws_csv)["merge_distance"].astype(float).to_numpy()
    n = min(len(no_vals), len(ws_vals))
    no_vals = no_vals[:n]
    ws_vals = ws_vals[:n]
    idx = np.arange(1, n + 1)
    no_norm = no_vals / max(float(np.max(no_vals)), 1e-12)
    ws_norm = ws_vals / max(float(np.max(ws_vals)), 1e-12)

    pearson = float(np.corrcoef(no_norm, ws_norm)[0, 1])
    spear = float(spearmanr(no_norm, ws_norm).correlation)
    mad_norm = float(np.mean(np.abs(no_norm - ws_norm)))

    out_csv = out_root / "dendrogram_merge_distance_profile_comparison.csv"
    pd.DataFrame(
        {
            "merge_index": idx,
            "no_scaler_merge_distance": no_vals,
            "with_scaler_merge_distance": ws_vals,
            "no_scaler_norm": no_norm,
            "with_scaler_norm": ws_norm,
            "norm_abs_diff": np.abs(no_norm - ws_norm),
        }
    ).to_csv(out_csv, index=False)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(idx, no_vals, label="No scaler", lw=1.5)
    axes[0].plot(idx, ws_vals, label="With scaler", lw=1.5)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Merge distance (log scale)")
    axes[0].set_title("Dendrogram merge-distance profile (raw)")
    axes[0].legend(loc="best")
    axes[0].grid(alpha=0.2)

    axes[1].plot(idx, no_norm, label="No scaler (normalized)", lw=1.5)
    axes[1].plot(idx, ws_norm, label="With scaler (normalized)", lw=1.5)
    axes[1].set_xlabel("Merge index")
    axes[1].set_ylabel("Normalized merge distance")
    axes[1].set_title(f"Normalized profile | Pearson={pearson:.4f}, Spearman={spear:.4f}, MAD={mad_norm:.4f}")
    axes[1].legend(loc="best")
    axes[1].grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(out_root / "dendrogram_profile_comparison.png", dpi=180)
    plt.close(fig)

    return {
        "n_merges_compared": int(n),
        "pearson_norm": pearson,
        "spearman_norm": spear,
        "mean_abs_diff_norm": mad_norm,
        "no_scaler_max_merge_distance": float(np.max(no_vals)),
        "with_scaler_max_merge_distance": float(np.max(ws_vals)),
        "profile_csv": str(out_csv),
    }


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    base_dir = args.base_dir.resolve()
    run_no_dir = (base_dir / args.run_no_scaler).resolve()
    run_ws_dir = (base_dir / args.run_with_scaler).resolve()
    if args.output_dir is None:
        out_root = (base_dir / f"comparison_{args.run_no_scaler}_VS_{args.run_with_scaler}_by_nclass").resolve()
    else:
        out_root = args.output_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    x_norm, mask, vlim = load_numeric_inputs(project_root=project_root)

    pair_summaries = []
    for pair in PAIR_SPECS:
        summary = analyze_pair(
            out_root=out_root,
            pair=pair,
            run_no_dir=run_no_dir,
            run_ws_dir=run_ws_dir,
            x_norm=x_norm,
            mask=mask,
            vlim=vlim,
        )
        pair_summaries.append(summary)

    dendro_summary = compare_dendrogram_profiles(out_root=out_root, run_no_dir=run_no_dir, run_ws_dir=run_ws_dir)

    summary = {
        "run_no_scaler": str(run_no_dir),
        "run_with_scaler": str(run_ws_dir),
        "output_root": str(out_root),
        "pair_summaries": pair_summaries,
        "dendrogram_summary": dendro_summary,
    }
    with (out_root / "comparison_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Comparison complete. Output: {out_root}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
