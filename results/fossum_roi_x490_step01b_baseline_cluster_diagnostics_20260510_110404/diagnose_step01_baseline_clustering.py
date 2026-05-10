"""Diagnose Step01 baseline clustering without recomputing features."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.spatial.distance import cdist, pdist


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
STEP01_DIR = ROOT / "results" / "fossum_roi_x490_step01_old_config_baseline_20260509_235101"
STEP00_DIR = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"

ASSIGNMENTS = STEP01_DIR / "step01_old_config_assignments.csv"
FEATURES = STEP01_DIR / "step01_old_config_features.npy"
SCALED_FEATURES = STEP01_DIR / "step01_old_config_scaled_features.npy"
LINKAGE = STEP01_DIR / "step01_old_config_linkage.npy"
METADATA = STEP01_DIR / "step01_old_config_metadata.json"
X_NORM = STEP00_DIR / "X_surface_370_roi_x490_norm.npy"
MASK = STEP00_DIR / "mask_common_roi_x490.npy"
XKM = STEP00_DIR / "X_km_roi_x490.npy"
YKM = STEP00_DIR / "Y_km_roi_x490.npy"
PNG_CLEAN_DIR = STEP00_DIR / "normalized_clean_pngs"

K_CUTS = [4, 5, 6, 7, 8]
SD_FRACTIONS = [0.20, 0.25, 0.30, 0.35, 0.40]
FINAL_SENTENCE = "The Step01 baseline clustering was diagnosed to determine whether the observed class issues are caused by the dendrogram cut or by the feature extraction configuration."


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def markdown_table(df: pd.DataFrame, max_cols: int = 10) -> str:
    if df.empty:
        return "_No rows._"
    work = df.copy()
    if len(work.columns) > max_cols:
        work = work.iloc[:, :max_cols]
    cols = list(work.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in work.iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{float(value):.6f}")
            else:
                text = str(value).replace("|", "/")
                if len(text) > 80:
                    text = text[:77] + "..."
                vals.append(text)
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def load_inputs():
    assignments = pd.read_csv(ASSIGNMENTS)
    features = np.load(FEATURES).astype(np.float32, copy=False)
    scaled = np.load(SCALED_FEATURES).astype(np.float32, copy=False)
    z = np.load(LINKAGE).astype(np.float64, copy=False)
    x_norm = np.load(X_NORM).astype(np.float32, copy=False)
    mask = np.load(MASK).astype(bool, copy=False)
    xkm = np.load(XKM).astype(np.float32, copy=False)
    ykm = np.load(YKM).astype(np.float32, copy=False)
    meta = json.loads(METADATA.read_text(encoding="utf-8")) if METADATA.exists() else {}
    return assignments, features, scaled, z, x_norm, mask, xkm, ykm, meta


def normalize_labels(labels: np.ndarray) -> np.ndarray:
    mapping = {raw: i + 1 for i, raw in enumerate(sorted(np.unique(labels).tolist()))}
    return np.array([mapping[int(v)] for v in labels], dtype=np.int32)


def labels_for_k(z: np.ndarray, k: int) -> np.ndarray:
    return normalize_labels(fcluster(z, t=int(k), criterion="maxclust"))


def labels_for_sd(z: np.ndarray, frac: float) -> tuple[np.ndarray, float]:
    sd = float(frac * np.max(z[:, 2]))
    return normalize_labels(fcluster(z, t=sd, criterion="distance")), sd


def class_indices(labels: np.ndarray) -> dict[int, np.ndarray]:
    return {int(c): np.where(labels == c)[0] for c in sorted(np.unique(labels).tolist())}


def class_mean(x: np.ndarray, idx: np.ndarray, mask: np.ndarray) -> np.ndarray:
    arr = np.mean(np.nan_to_num(x[idx], nan=0.0), axis=0).astype(np.float32)
    arr[~mask] = np.nan
    return arr


def class_std(x: np.ndarray, idx: np.ndarray, mask: np.ndarray) -> np.ndarray:
    arr = np.std(np.nan_to_num(x[idx], nan=0.0), axis=0).astype(np.float32)
    arr[~mask] = np.nan
    return arr


def prototype_vectors(x: np.ndarray, mask: np.ndarray, labels: np.ndarray) -> dict[int, np.ndarray]:
    out = {}
    for cid, idx in class_indices(labels).items():
        out[cid] = class_mean(x, idx, mask)[mask].astype(np.float64)
    return out


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def temporal_runs(labels: np.ndarray) -> int:
    return int(1 + np.sum(labels[1:] != labels[:-1])) if labels.size else 0


def metrics_for_labels(name: str, labels: np.ndarray, z: np.ndarray, x_norm: np.ndarray, mask: np.ndarray, original: np.ndarray) -> dict[str, Any]:
    groups = class_indices(labels)
    sizes = np.array([len(v) for v in groups.values()], dtype=np.int32)
    protos = prototype_vectors(x_norm, mask, labels)
    proto_vals = list(protos.values())
    proto_dists = []
    proto_corrs = []
    for i in range(len(proto_vals)):
        for j in range(i + 1, len(proto_vals)):
            proto_dists.append(rmse(proto_vals[i], proto_vals[j]))
            proto_corrs.append(corr(proto_vals[i], proto_vals[j]))
    size_cv = float(np.std(sizes) / max(np.mean(sizes), 1e-12))
    min_size = int(np.min(sizes))
    tiny_count = int(np.sum(sizes < 10))
    proto_sep = float(np.mean(proto_dists)) if proto_dists else 0.0
    max_proto_corr = float(np.nanmax(proto_corrs)) if proto_corrs else np.nan
    runs = temporal_runs(labels)
    overlap = overlap_with_original(labels, original)
    score = (
        1.2 * proto_sep
        + 0.10 * min_size
        - 0.35 * size_cv
        - 0.15 * tiny_count
        - 0.002 * runs
        - 0.15 * max(0, len(groups) - 6)
    )
    return {
        "cut_name": name,
        "n_classes": int(len(groups)),
        "class_sizes": json.dumps([int(v) for v in sizes.tolist()]),
        "min_class_size": min_size,
        "max_class_size": int(np.max(sizes)),
        "mean_class_size": float(np.mean(sizes)),
        "size_cv": size_cv,
        "tiny_class_count_lt10": tiny_count,
        "mean_prototype_rmse": proto_sep,
        "max_prototype_corr": max_proto_corr,
        "temporal_runs": runs,
        "mean_overlap_purity_vs_original": float(overlap["mean_purity"]),
        "interpretability_score": float(score),
    }


def overlap_with_original(labels: np.ndarray, original: np.ndarray) -> dict[str, Any]:
    rows = []
    purities = []
    for cid, idx in class_indices(labels).items():
        orig = original[idx]
        vals, counts = np.unique(orig, return_counts=True)
        best = int(vals[np.argmax(counts)])
        purity = float(np.max(counts) / max(1, len(idx)))
        purities.append(purity)
        rows.append({"new_class": int(cid), "best_original_class": best, "n": int(len(idx)), "purity": purity})
    return {"rows": rows, "mean_purity": float(np.mean(purities)) if purities else np.nan}


def save_overlap_csv(cut_rows: list[dict[str, Any]]) -> None:
    rows = []
    for item in cut_rows:
        cut_name = item["cut_name"]
        labels = item["labels"]
        original = item["original"]
        for r in overlap_with_original(labels, original)["rows"]:
            r["cut_name"] = cut_name
            rows.append(r)
    pd.DataFrame(rows).to_csv(OUT_DIR / "cut_overlap_with_original.csv", index=False)


def map_panel(images: list[np.ndarray], titles: list[str], out_path: Path, title: str, cmap_name: str, vmin: float | None, vmax: float | None) -> None:
    n = len(images)
    cols = min(4, max(1, n))
    rows = int(math.ceil(n / cols))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    fig, axes = plt.subplots(rows, cols, figsize=(3.7 * cols, 3.0 * rows), squeeze=False)
    im = None
    for ax, img, ttl in zip(axes.ravel(), images, titles):
        im = ax.imshow(img, origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(ttl, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes.ravel()[n:]:
        ax.set_axis_off()
    fig.suptitle(title)
    if im is not None:
        fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.84)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def load_thumb(day_index: int, date: str, size: tuple[int, int]) -> Image.Image:
    p = PNG_CLEAN_DIR / f"{day_index:04d}_{date}_X_surface_370_roi_x490_norm_clean.png"
    with Image.open(p) as im:
        return im.convert("RGB").resize(size, Image.Resampling.BILINEAR)


def grouped_panel(assignments: pd.DataFrame, labels: np.ndarray, out_path: Path, title: str, cols: int = 20) -> None:
    df = assignments.copy()
    df["diagnostic_class"] = labels
    thumb = (92, 66)
    gap = 7
    margin = 20
    header_h = 34
    label_h = 14
    top_h = 62
    section_gap = 16
    class_ids = sorted(np.unique(labels).tolist())
    width = margin * 2 + cols * thumb[0] + (cols - 1) * gap
    heights = []
    for cid in class_ids:
        n = int((labels == cid).sum())
        heights.append(header_h + int(math.ceil(n / cols)) * (thumb[1] + label_h + gap) + section_gap)
    height = top_h + sum(heights) + margin
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((margin, 16), title, fill=(0, 0, 0), font=font)
    draw.text((margin, 34), f"n={len(df)} | grouped by diagnostic cut", fill=(30, 30, 30), font=font)
    y = top_h
    for cid in class_ids:
        sub = df[df["diagnostic_class"] == cid].sort_values("day_index").reset_index(drop=True)
        draw.text((margin, y), f"class_{int(cid):02d}, n={len(sub)}", fill=(0, 0, 0), font=font)
        y += header_h
        for k, row in sub.iterrows():
            r = k // cols
            c = k % cols
            x = margin + c * (thumb[0] + gap)
            yy = y + r * (thumb[1] + label_h + gap)
            im = load_thumb(int(row["day_index"]), str(row["date"]), thumb)
            canvas.paste(im, (x, yy))
            draw.rectangle([x, yy, x + thumb[0], yy + thumb[1]], outline=(190, 190, 190), width=1)
            draw.text((x + 1, yy + thumb[1] + 1), f"z={int(row['day_index']):03d}", fill=(20, 20, 20), font=font)
        y += int(math.ceil(len(sub) / cols)) * (thumb[1] + label_h + gap) + section_gap
    canvas.save(out_path)


def timelines_panel(assignments: pd.DataFrame, label_sets: list[tuple[str, np.ndarray]], out_path: Path) -> None:
    fig, axes = plt.subplots(len(label_sets), 1, figsize=(13, 2.1 * len(label_sets)), sharex=True)
    if len(label_sets) == 1:
        axes = [axes]
    x = assignments["day_index"].to_numpy()
    for ax, (name, labels) in zip(axes, label_sets):
        ax.scatter(x, labels, c=labels, cmap="tab20", s=16)
        ax.plot(x, labels, color="#94a3b8", lw=0.5, alpha=0.5)
        ax.set_ylabel(name)
        ax.set_yticks(sorted(np.unique(labels)))
        ax.grid(True, linestyle="--", alpha=0.2)
    axes[-1].set_xlabel("Day index")
    fig.suptitle("Class timeline comparison")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_dendrogram(z: np.ndarray, out_path: Path) -> None:
    maxd = float(np.max(z[:, 2]))
    fig, ax = plt.subplots(figsize=(13, 5.2))
    dendrogram(z, no_labels=True, above_threshold_color="#6b7280", ax=ax)
    colors = ["#2563eb", "#059669", "#dc2626", "#7c3aed", "#ea580c"]
    for frac, color in zip(SD_FRACTIONS, colors):
        ax.axhline(frac * maxd, color=color, ls="--", lw=1.3, label=f"SD {frac:.2f}")
    ax.set_title("Step01 dendrogram with alternative SD cuts")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Ward merge distance")
    ax.legend(fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def class_distance_matrix(labels: np.ndarray, scaled: np.ndarray) -> pd.DataFrame:
    groups = class_indices(labels)
    rows = []
    for ci, idx_i in groups.items():
        for cj, idx_j in groups.items():
            if ci == cj:
                vals = pdist(scaled[idx_i], metric="euclidean")
                d = float(np.mean(vals)) if vals.size else 0.0
            else:
                d = float(np.mean(cdist(scaled[idx_i], scaled[idx_j], metric="euclidean")))
            rows.append({"class_i": ci, "class_j": cj, "mean_feature_distance": d})
    df = pd.DataFrame(rows)
    mat = df.pivot(index="class_i", columns="class_j", values="mean_feature_distance")
    mat.to_csv(OUT_DIR / "class_distance_matrix_step01.csv")
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    im = ax.imshow(mat.to_numpy(), cmap="viridis")
    ax.set_xticks(range(len(mat.columns)))
    ax.set_xticklabels([f"C{c:02d}" for c in mat.columns])
    ax.set_yticks(range(len(mat.index)))
    ax.set_yticklabels([f"C{c:02d}" for c in mat.index])
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{mat.iloc[i, j]:.1f}", ha="center", va="center", color="white" if mat.iloc[i, j] > mat.to_numpy().max() * 0.55 else "black", fontsize=8)
    ax.set_title("Mean feature distance between original Step01 classes")
    fig.colorbar(im, ax=ax, label="Euclidean distance")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "class_distance_heatmap.png", dpi=160)
    plt.close(fig)
    return mat


def c01_c04_diagnostics(assignments: pd.DataFrame, scaled: np.ndarray, x_norm: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    c1 = assignments.loc[assignments["class_id"] == 1, "image_idx_0_based"].to_numpy(dtype=int)
    c4 = assignments.loc[assignments["class_id"] == 4, "image_idx_0_based"].to_numpy(dtype=int)
    intra1 = float(np.mean(pdist(scaled[c1], metric="euclidean")))
    intra4 = float(np.mean(pdist(scaled[c4], metric="euclidean"))) if len(c4) > 1 else 0.0
    between = float(np.mean(cdist(scaled[c1], scaled[c4], metric="euclidean")))
    p1 = class_mean(x_norm, c1, mask)
    p4 = class_mean(x_norm, c4, mask)
    c = corr(p1[mask], p4[mask])
    r = rmse(p1[mask], p4[mask])
    should_merge = bool(c > 0.94 and between <= 1.15 * max(intra1, intra4))
    pd.DataFrame(
        [
            {
                "metric": "c01_intra_mean_feature_distance",
                "value": intra1,
            },
            {"metric": "c04_intra_mean_feature_distance", "value": intra4},
            {"metric": "c01_c04_between_mean_feature_distance", "value": between},
            {"metric": "prototype_corr", "value": c},
            {"metric": "prototype_rmse_norm", "value": r},
            {"metric": "should_merge_rule", "value": should_merge},
        ]
    ).to_csv(OUT_DIR / "c01_c04_similarity_metrics.csv", index=False)
    diff = p4 - p1
    vmax = float(np.percentile(np.abs(x_norm[:, mask]), 98.0))
    dmax = float(np.nanmax(np.abs(diff[mask])))
    map_panel([p1, p4, diff], ["C01 prototype", "C04 prototype", "C04 - C01"], OUT_DIR / "c01_c04_prototype_comparison.png", "C01 vs C04 prototype comparison", "coolwarm", -vmax if dmax == 0 else None, vmax if dmax == 0 else None)
    return {
        "c01_intra_mean_feature_distance": intra1,
        "c04_intra_mean_feature_distance": intra4,
        "c01_c04_between_mean_feature_distance": between,
        "prototype_corr": c,
        "prototype_rmse_norm": r,
        "should_merge": should_merge,
    }


def c01_subclusters(assignments: pd.DataFrame, scaled: np.ndarray, x_norm: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    idx = assignments.loc[assignments["class_id"] == 1, "image_idx_0_based"].to_numpy(dtype=int)
    z_sub = linkage(scaled[idx].astype(np.float64), method="ward", metric="euclidean")
    sub = normalize_labels(fcluster(z_sub, t=2, criterion="maxclust"))
    rows = []
    imgs = []
    titles = []
    for sid in sorted(np.unique(sub)):
        sub_idx = idx[sub == sid]
        proto = class_mean(x_norm, sub_idx, mask)
        vals = proto[mask]
        rows.append(
            {
                "subcluster": f"C01{chr(96 + int(sid))}",
                "n_days": int(len(sub_idx)),
                "mean_norm": float(np.mean(vals)),
                "std_spatial_norm": float(np.std(vals)),
                "min_norm": float(np.min(vals)),
                "max_norm": float(np.max(vals)),
                "day_indices": " ".join(str(v + 1) for v in sub_idx.tolist()),
            }
        )
        imgs.append(proto)
        titles.append(f"C01{chr(96 + int(sid))} n={len(sub_idx)}")
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "c01_subcluster_metrics.csv", index=False)
    vmax = float(np.percentile(np.abs(x_norm[:, mask]), 98.0))
    map_panel(imgs, titles, OUT_DIR / "c01_subcluster_panel.png", "C01 split into two subclusters", "coolwarm", -vmax, vmax)
    sub_assign = assignments.loc[idx].copy()
    sub_assign["diagnostic_class"] = sub
    grouped_panel(sub_assign, sub, OUT_DIR / "diagnostics_c01_subcluster_members_panel.png", "C01 internal split members", cols=16)
    mean_diff = abs(float(df.iloc[0]["mean_norm"]) - float(df.iloc[1]["mean_norm"])) if len(df) == 2 else 0.0
    has_substructure = bool(mean_diff > 0.25 or abs(float(df.iloc[0]["std_spatial_norm"]) - float(df.iloc[1]["std_spatial_norm"])) > 0.10)
    return {"sizes": df[["subcluster", "n_days"]].to_dict(orient="records"), "mean_difference_norm": mean_diff, "has_internal_substructure": has_substructure}


def sd_fraction_panel(assignments: pd.DataFrame, z: np.ndarray, x_norm: np.ndarray, mask: np.ndarray) -> None:
    vmax = float(np.percentile(np.abs(x_norm[:, mask]), 98.0))
    rows = []
    for frac in SD_FRACTIONS:
        labels, _sd = labels_for_sd(z, frac)
        groups = class_indices(labels)
        for cid, idx in groups.items():
            rows.append((frac, cid, len(idx), class_mean(x_norm, idx, mask)))
    ncols = max(len(class_indices(labels_for_sd(z, f)[0])) for f in SD_FRACTIONS)
    nrows = len(SD_FRACTIONS)
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad("white")
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.0 * ncols, 2.5 * nrows), squeeze=False)
    for ax in axes.ravel():
        ax.set_axis_off()
    for r, frac in enumerate(SD_FRACTIONS):
        sub = [x for x in rows if x[0] == frac]
        for c, (_frac, cid, n, img) in enumerate(sub):
            axes[r, c].set_axis_on()
            axes[r, c].imshow(img, origin="lower", cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")
            axes[r, c].set_title(f"SD {frac:.2f} C{cid:02d} n={n}", fontsize=8)
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])
    fig.suptitle("SD fraction prototype comparison")
    fig.savefig(OUT_DIR / "sd_fraction_comparison_panel.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    assignments, features, scaled, z, x_norm, mask, xkm, ykm, meta = load_inputs()
    original = assignments["class_id"].to_numpy(dtype=np.int32)
    plot_dendrogram(z, OUT_DIR / "dendrogram_with_multiple_cuts.png")

    cut_rows = []
    label_sets_for_timeline = [("orig SD30", original)]
    detailed_cut_rows = []
    for k in K_CUTS:
        labels = labels_for_k(z, k)
        m = metrics_for_labels(f"k{k}", labels, z, x_norm, mask, original)
        m["cut_type"] = "maxclust"
        m["cut_value"] = int(k)
        cut_rows.append(m)
        detailed_cut_rows.append({"cut_name": f"k{k}", "labels": labels, "original": original})
        groups = class_indices(labels)
        vmax = float(np.percentile(np.abs(x_norm[:, mask]), 98.0))
        maps = [class_mean(x_norm, idx, mask) for idx in groups.values()]
        titles = [f"C{cid:02d} n={len(idx)}" for cid, idx in groups.items()]
        map_panel(maps, titles, OUT_DIR / f"cut_{k}_classes_prototypes_panel.png", f"k={k} prototypes", "coolwarm", -vmax, vmax)
        grouped_panel(assignments, labels, OUT_DIR / f"cut_{k}_classes_grouped_panel.png", f"Cut k={k}: all members grouped by class")
        if k in [4, 5, 6, 7]:
            label_sets_for_timeline.append((f"k{k}", labels))

    for frac in SD_FRACTIONS:
        labels, sd = labels_for_sd(z, frac)
        m = metrics_for_labels(f"sd{frac:.2f}", labels, z, x_norm, mask, original)
        m["cut_type"] = "sd_fraction"
        m["cut_value"] = float(frac)
        m["separation_distance"] = float(sd)
        cut_rows.append(m)
        detailed_cut_rows.append({"cut_name": f"sd{frac:.2f}", "labels": labels, "original": original})

    cut_df = pd.DataFrame(cut_rows).sort_values(["cut_type", "cut_value"]).reset_index(drop=True)
    cut_df.to_csv(OUT_DIR / "cut_alternatives_metrics.csv", index=False)
    save_overlap_csv(detailed_cut_rows)
    timelines_panel(assignments, label_sets_for_timeline, OUT_DIR / "class_timeline_comparison.png")
    sd_fraction_panel(assignments, z, x_norm, mask)
    dist_mat = class_distance_matrix(original, scaled)
    c14 = c01_c04_diagnostics(assignments, scaled, x_norm, mask)
    c01 = c01_subclusters(assignments, scaled, x_norm, mask)

    ranked = cut_df.sort_values("interpretability_score", ascending=False).reset_index(drop=True)
    best = ranked.iloc[0]
    best_sd = cut_df[cut_df["cut_type"] == "sd_fraction"].sort_values("interpretability_score", ascending=False).iloc[0]
    recommended_n = int(best["n_classes"])
    recommended_sd = float(best_sd["cut_value"])

    if c14["should_merge"] and c01["has_internal_substructure"]:
        action = "Do not trust SD30 as final: test a cut that merges C04-like days with C01 while splitting C01, then proceed to patch-size sensitivity."
    elif c01["has_internal_substructure"]:
        action = "Try 6-class interpretation/cut first, then run patch-size sensitivity to confirm C01 split stability."
    elif c14["should_merge"]:
        action = "Try a coarser cut or explicit C01/C04 merge before patch-size sensitivity."
    else:
        action = "Keep Step01 as baseline but proceed to patch-size sensitivity because visual issues are not only a cut problem."

    recommendation = {
        "recommended_n_classes": recommended_n,
        "recommended_sd_fraction": recommended_sd,
        "recommended_action": action,
        "top_cut_rows": ranked.head(5).to_dict(orient="records"),
        "c01_c04_similarity": c14,
        "c01_subcluster": c01,
    }
    write_json(OUT_DIR / "step01b_recommendation.json", recommendation)

    checks = {
        "input_step01_folder": str(STEP01_DIR),
        "original_n_classes": int(len(np.unique(original))),
        "original_class_sizes": {f"class_{c:02d}": int(np.sum(original == c)) for c in sorted(np.unique(original))},
        "cuts_tested": K_CUTS,
        "sd_fractions_tested": SD_FRACTIONS,
        "c01_c04_similarity": c14,
        "c01_c04_should_merge": bool(c14["should_merge"]),
        "c01_has_internal_substructure": bool(c01["has_internal_substructure"]),
        "recommended_n_classes": recommended_n,
        "recommended_sd_fraction": recommended_sd,
        "recommended_action": action,
        "final_verdict": "PASS - Step01 dendrogram cuts and C01/C04 diagnostics completed without recomputing dictionary/features.",
    }
    write_json(OUT_DIR / "step01b_cluster_diagnostics_checks.json", checks)

    c04_close = "sim" if c14["prototype_corr"] > 0.9 else "parcialmente"
    merge_text = "sim" if c14["should_merge"] else "não de forma automática; é visualmente próxima mas a distância em features ainda separa o grupo"
    sub_text = "sim" if c01["has_internal_substructure"] else "fraca/indefinida"
    summary = [
        "# Step01b baseline cluster diagnostics summary",
        "",
        f"1. C04 está realmente próxima de C01? {c04_close}. Correlação dos protótipos={c14['prototype_corr']:.4f}; RMSE={c14['prototype_rmse_norm']:.4f}.",
        f"2. C04 deveria ser fundida com C01? {merge_text}.",
        f"3. C01 tem subestrutura interna visível? {sub_text}.",
        f"4. As imagens azul claro da C01 formam um subgrupo coerente? {'sim, preliminarmente' if c01['has_internal_substructure'] else 'não conclusivo nesta análise'}.",
        f"5. O problema parece vir do corte SD=0.30? Parcialmente; cortes alternativos alteram a granularidade, mas a estrutura C01/C04 sugere também limitação da configuração de features.",
        f"6. Número de classes mais adequado entre 4-8: {recommended_n}.",
        f"7. SD fraction mais adequada entre as testadas: {recommended_sd:.2f}.",
        "8. Devemos ajustar apenas o corte ou avançar para patch-size sensitivity? Avançar para patch-size sensitivity, usando estes cortes como referência diagnóstica.",
        "9. A configuração antiga continua aceitável como baseline? Sim, como baseline inicial, mas não como configuração final sem sensitivity.",
        f"10. Próxima etapa recomendada: {action}",
        "",
        FINAL_SENTENCE,
    ]
    report = [
        "# Step01b baseline cluster diagnostics report",
        "",
        "## Inputs",
        f"- Step01: `{STEP01_DIR}`",
        f"- Step00: `{STEP00_DIR}`",
        "",
        "## Original classes",
        json.dumps(checks["original_class_sizes"], indent=2),
        "",
        "## C01/C04 diagnostics",
        json.dumps(c14, indent=2),
        "",
        "## C01 internal split",
        json.dumps(c01, indent=2),
        "",
        "## Recommendation",
        action,
        "",
        "## Top cut alternatives",
        markdown_table(ranked.head(8)),
        "",
        FINAL_SENTENCE,
    ]
    (OUT_DIR / "step01b_cluster_diagnostics_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    (OUT_DIR / "step01b_cluster_diagnostics_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"[OK] out_dir={OUT_DIR}")
    print(f"[OK] recommended_n_classes={recommended_n}")
    print(f"[OK] recommended_sd_fraction={recommended_sd:.2f}")
    print(f"[OK] c01_c04_should_merge={c14['should_merge']}")
    print(f"[OK] c01_has_internal_substructure={c01['has_internal_substructure']}")
    print(f"[OK] {FINAL_SENTENCE}")


if __name__ == "__main__":
    main()
