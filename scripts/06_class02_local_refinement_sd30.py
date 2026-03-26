from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from fossum_faithful_initial_utils import (
    FaithfulInitialConfig,
    ROOT,
    deterministic_spread_order,
    encode_images_with_full_sparse_features,
    image_icv_proxy,
    train_dictionary_ordered_stream,
)


PATCH_W = 72
PATCH_H = 40
DICTIONARY_SIZE = 4
WORKING_SD_DIR = "sd_30pct"
WORKING_CLASS_ID = 2
MAX_CONTACT_IMAGES_PER_CLASS = 50
MAX_DISTANCE_PANEL_IMAGES = 30


@dataclass(frozen=True)
class SeedRun:
    seed: int
    sd_dir: Path
    run_dir: str
    number_of_classes: int


def log(msg: str) -> None:
    print(f"[class02-local-refinement] {msg}")


def parse_args() -> argparse.Namespace:
    default_summary = ROOT / "results" / "fossum" / "faithful_initial_sd_working_config" / "summary_final_sd30_all_seeds_20260325.csv"
    default_out = ROOT / "results" / "fossum" / f"class02_local_refinement_sd30_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p = argparse.ArgumentParser(description="Targeted local refinement for class_02 from official SD=0.30 runs.")
    p.add_argument("--summary-csv", type=Path, default=default_summary)
    p.add_argument("--out-dir", type=Path, default=default_out)
    p.add_argument("--seeds", type=int, nargs="*", default=[11, 23, 37, 53, 71])
    p.add_argument("--k-values", type=int, nargs="*", default=[2, 3], help="Local subclass counts to test (max 3 recommended).")
    p.add_argument("--dict-batch-size", type=int, default=4096)
    p.add_argument("--transform-nnz", type=int, default=2)
    p.add_argument("--no-pca", action="store_true")
    return p.parse_args()


def parse_seed_runs(summary_csv: Path, seeds: Sequence[int]) -> List[SeedRun]:
    if not summary_csv.exists():
        raise FileNotFoundError(f"Missing summary CSV: {summary_csv}")
    df = pd.read_csv(summary_csv)
    want = set(int(s) for s in seeds)
    out: List[SeedRun] = []
    for _, row in df.iterrows():
        seed = int(row["seed"])
        if seed not in want:
            continue
        sd_dir = ROOT / str(row["output_dir"])
        out.append(
            SeedRun(
                seed=seed,
                sd_dir=sd_dir,
                run_dir=str(row["run_dir"]),
                number_of_classes=int(row["number_of_classes"]),
            )
        )
    out.sort(key=lambda r: r.seed)
    found = {r.seed for r in out}
    missing = sorted(want.difference(found))
    if missing:
        raise FileNotFoundError(f"Missing seeds in summary: {missing}")
    return out


def class_mean_image(class_stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    mean_img = np.mean(np.nan_to_num(class_stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    mean_img[~mask] = np.nan
    return mean_img


def class_std_image(class_stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    std_img = np.std(np.nan_to_num(class_stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    std_img[~mask] = np.nan
    return std_img


def compute_member_distances_to_prototype(class_stack: np.ndarray, prototype: np.ndarray, mask: np.ndarray) -> np.ndarray:
    valid = mask.reshape(-1)
    members_flat = class_stack.reshape(class_stack.shape[0], -1)[:, valid]
    proto_flat = prototype.reshape(-1)[valid]
    diffs = members_flat - proto_flat[np.newaxis, :]
    return np.sqrt(np.nanmean(diffs * diffs, axis=1)).astype(np.float64, copy=False)


def make_contact_sheet_from_pngs(
    png_paths: List[Path],
    labels: List[str],
    out_path: Path,
    title: str,
    cols: int = 10,
    thumb_size: Tuple[int, int] = (180, 120),
) -> None:
    n = len(png_paths)
    rows = int(math.ceil(n / cols)) if n > 0 else 1
    pad = 8
    title_h = 28
    label_h = 14
    cell_w = thumb_size[0]
    cell_h = thumb_size[1] + label_h
    w = pad + cols * (cell_w + pad)
    h = title_h + pad + rows * (cell_h + pad) + pad

    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    tw = draw.textlength(title, font=font)
    draw.text(((w - tw) / 2, 6), title, fill=(0, 0, 0), font=font)

    for i, (png_path, label) in enumerate(zip(png_paths, labels)):
        r = i // cols
        c = i % cols
        x = pad + c * (cell_w + pad)
        y = title_h + pad + r * (cell_h + pad)
        with Image.open(png_path) as im:
            rgb = im.convert("RGB").resize(thumb_size, Image.Resampling.BILINEAR)
        canvas.paste(rgb, (x, y))
        draw.rectangle([x, y, x + thumb_size[0], y + thumb_size[1]], outline=(120, 120, 120), width=1)
        draw.text((x, y + thumb_size[1] + 1), label, fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")


def build_png_map() -> Dict[int, Path]:
    png_dir = ROOT / "results" / "fossum" / "pngs_normalized_surface_300_thesis"
    if not png_dir.exists():
        png_dir = ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis"
    if not png_dir.exists():
        raise FileNotFoundError("Missing PNG directory for contact sheets.")

    files = sorted(png_dir.glob("X_surface_norm_z*.png"))
    if not files:
        raise RuntimeError(f"No PNGs in {png_dir}")
    out: Dict[int, Path] = {}
    for p in files:
        stem = p.stem.lower()
        if "_z" not in stem:
            continue
        try:
            z = int(stem.split("_z")[-1])
        except Exception:
            continue
        out[z] = p
    return out


def _first_existing_file(candidates: Sequence[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def _first_existing_dir(candidates: Sequence[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return None


def resolve_input_paths() -> Dict[str, Path]:
    paths = {
        "X_sst": _first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300.npy",
                ROOT / "results" / "plots" / "X_surface_300.npy",
            ]
        ),
        "X_norm": _first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
                ROOT / "results" / "plots" / "X_surface_300_norm.npy",
            ]
        ),
        "mask": _first_existing_file(
            [
                ROOT / "results" / "fossum" / "mask_common.npy",
                ROOT / "results" / "plots" / "mask_common.npy",
            ]
        ),
        "png_dir": _first_existing_dir(
            [
                ROOT / "results" / "fossum" / "pngs_normalized_surface_300_thesis",
                ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis",
            ]
        ),
    }
    missing = [k for k, v in paths.items() if v is None]
    if missing:
        raise FileNotFoundError(f"Missing required inputs: {', '.join(missing)}")
    return {k: v for k, v in paths.items() if v is not None}


def load_numeric_inputs_with_fallback(paths: Dict[str, Path]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[float, float]]:
    X_sst = np.load(paths["X_sst"]).astype(np.float32, copy=False)
    X_norm = np.load(paths["X_norm"]).astype(np.float32, copy=False)
    mask = np.load(paths["mask"]).astype(bool, copy=False)

    if X_sst.ndim != 3 or X_norm.ndim != 3:
        raise RuntimeError(f"Expected 3D arrays, got X_sst={X_sst.shape}, X_norm={X_norm.shape}")
    if X_sst.shape != X_norm.shape:
        raise RuntimeError(f"Shape mismatch: X_sst={X_sst.shape}, X_norm={X_norm.shape}")
    if mask.shape != X_norm.shape[1:]:
        raise RuntimeError(f"Mask mismatch: mask={mask.shape}, grid={X_norm.shape[1:]}")

    X_sst = X_sst.copy()
    X_norm = X_norm.copy()
    X_sst[:, ~mask] = np.nan
    X_norm[:, ~mask] = np.nan

    valid_vals = X_norm[:, mask]
    vlim = float(np.percentile(np.abs(valid_vals), 98.0))
    if not np.isfinite(vlim) or vlim <= 0:
        vlim = 1.0
    return X_sst, X_norm, mask, (-vlim, +vlim)


def parse_class02_members(sd_dir: Path) -> np.ndarray:
    # Use distance CSV because it contains the full class membership.
    # members_list.csv is limited to panel samples (max 50) in the global script.
    distance_csv = sd_dir / f"class_{WORKING_CLASS_ID:02d}_distance_to_prototype.csv"
    if distance_csv.exists():
        df = pd.read_csv(distance_csv)
        if "image_idx_0_based" not in df.columns:
            raise RuntimeError(f"Unexpected distance CSV columns: {list(df.columns)}")
        idx = df["image_idx_0_based"].astype(int).to_numpy()
    else:
        member_csv = sd_dir / f"class_{WORKING_CLASS_ID:02d}_members_list.csv"
        if not member_csv.exists():
            raise FileNotFoundError(f"Missing both class_02 distance and members CSV in {sd_dir}")
        df = pd.read_csv(member_csv)
        if "image_idx_0_based" not in df.columns:
            raise RuntimeError(f"Unexpected member CSV columns: {list(df.columns)}")
        idx = df["image_idx_0_based"].astype(int).to_numpy()

    if idx.size == 0:
        raise RuntimeError(f"class_02 has no members in {sd_dir}")
    return np.sort(idx)


def save_local_prototypes(
    out_dir: Path,
    X_norm_subset: np.ndarray,
    mask: np.ndarray,
    subclass_indices_local: List[np.ndarray],
    seed: int,
    k: int,
    vmin: float,
    vmax: float,
) -> List[np.ndarray]:
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad(color="white")
    protos: List[np.ndarray] = []
    for ci, idx_local in enumerate(subclass_indices_local, start=1):
        proto = class_mean_image(X_norm_subset[idx_local], mask=mask)
        protos.append(proto)
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"Seed {seed} class_02 local C{ci:02d} (n={len(idx_local)}) | k={k}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Normalized temperature (-)")
        fig.tight_layout()
        fig.savefig(out_dir / f"subclass_prototype_{ci:02d}.png", dpi=150)
        plt.close(fig)

    fig, axes = plt.subplots(1, len(protos), figsize=(4.0 * len(protos), 4.0), squeeze=False)
    for j, (ax, proto, idx_local) in enumerate(zip(axes[0], protos, subclass_indices_local), start=1):
        im = ax.imshow(proto, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(f"SC{j} (n={len(idx_local)})")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    fig.suptitle(f"Seed {seed} class_02 local prototypes | k={k}")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85)
    cbar.set_label("Normalized temperature (-)")
    fig.subplots_adjust(left=0.04, right=0.97, bottom=0.08, top=0.86, wspace=0.20)
    fig.savefig(out_dir / "subclass_prototypes_panel.png", dpi=160)
    plt.close(fig)
    return protos


def save_local_member_and_homogeneity_artifacts(
    out_dir: Path,
    X_norm_subset: np.ndarray,
    mask: np.ndarray,
    subclass_indices_local: List[np.ndarray],
    subclass_prototypes: Sequence[np.ndarray],
    global_indices: np.ndarray,
    image_proxy_global: np.ndarray,
    png_map: Dict[int, Path],
    seed: int,
    k: int,
) -> pd.DataFrame:
    out_rows: List[dict] = []
    std_maps: List[np.ndarray] = []
    std_values: List[np.ndarray] = []

    for idx_local in subclass_indices_local:
        std_map = class_std_image(X_norm_subset[idx_local], mask=mask)
        std_maps.append(std_map)
        vals = std_map[mask]
        if vals.size > 0:
            std_values.append(vals.astype(np.float64, copy=False))

    std_vmax = float(np.percentile(np.concatenate(std_values), 98.0)) if std_values else 1.0
    if not np.isfinite(std_vmax) or std_vmax <= 0:
        std_vmax = 1.0
    std_cmap = plt.get_cmap("magma").copy()
    std_cmap.set_bad(color="white")

    for ci, (idx_local, proto, std_map) in enumerate(zip(subclass_indices_local, subclass_prototypes, std_maps), start=1):
        class_stack = X_norm_subset[idx_local]
        distances = compute_member_distances_to_prototype(class_stack=class_stack, prototype=proto, mask=mask)
        order_asc = np.argsort(distances)

        # Members list ordered by deterministic spread (using global ICV proxy).
        global_idx = global_indices[idx_local]
        spread_local_order = deterministic_spread_order(indices=np.arange(idx_local.size), proxy_values=image_proxy_global[global_idx])
        spread_local_order = spread_local_order[:MAX_CONTACT_IMAGES_PER_CLASS]
        panel_pngs: List[Path] = []
        panel_labels: List[str] = []
        member_rows: List[dict] = []
        for local_pos in spread_local_order:
            gidx = int(global_idx[int(local_pos)])
            z = gidx + 1
            png_path = png_map.get(z)
            if png_path is None:
                continue
            panel_pngs.append(png_path)
            panel_labels.append(f"z={z:03d}")
            member_rows.append(
                {
                    "subclass_id": ci,
                    "global_image_idx_0_based": gidx,
                    "global_image_z_1_based": z,
                    "image_icv_proxy": float(image_proxy_global[gidx]),
                    "png_path": str(png_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
        pd.DataFrame(member_rows).to_csv(out_dir / f"subclass_{ci:02d}_members_list.csv", index=False)
        make_contact_sheet_from_pngs(
            png_paths=panel_pngs,
            labels=panel_labels,
            out_path=out_dir / f"subclass_{ci:02d}_members_panel.png",
            title=f"Seed {seed} class_02 local subclass {ci:02d} (n={idx_local.size}, shown={len(panel_pngs)}) | k={k}",
            cols=10,
            thumb_size=(180, 120),
        )

        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        im = ax.imshow(std_map, origin="lower", cmap=std_cmap, vmin=0.0, vmax=std_vmax, aspect="auto")
        ax.set_title(f"Seed {seed} class_02 subclass {ci:02d} pixel std (n={idx_local.size}) | k={k}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Std on normalized temperature (-)")
        fig.tight_layout()
        fig.savefig(out_dir / f"subclass_{ci:02d}_pixel_std_map.png", dpi=150)
        plt.close(fig)

        dist_rows: List[dict] = []
        for rank_pos, local_pos in enumerate(order_asc, start=1):
            gidx = int(global_idx[int(local_pos)])
            z = gidx + 1
            png_path = png_map.get(z)
            dist_rows.append(
                {
                    "distance_rank_asc": int(rank_pos),
                    "global_image_idx_0_based": gidx,
                    "global_image_z_1_based": z,
                    "distance_to_prototype_rmse_norm": float(distances[int(local_pos)]),
                    "png_path": str(png_path.relative_to(ROOT)).replace("\\", "/") if png_path is not None else "",
                }
            )
        dist_df = pd.DataFrame(dist_rows)
        dist_df.to_csv(out_dir / f"subclass_{ci:02d}_distance_to_prototype.csv", index=False)

        def build_panel_inputs(local_positions: np.ndarray) -> Tuple[List[Path], List[str]]:
            panel_paths: List[Path] = []
            panel_labs: List[str] = []
            for local_pos in local_positions:
                gidx = int(global_idx[int(local_pos)])
                z = gidx + 1
                png_path = png_map.get(z)
                if png_path is None:
                    continue
                panel_paths.append(png_path)
                panel_labs.append(f"z={z:03d} d={float(distances[int(local_pos)]):.4f}")
            return panel_paths, panel_labs

        closest_local = order_asc[:MAX_DISTANCE_PANEL_IMAGES]
        farthest_local = order_asc[::-1][:MAX_DISTANCE_PANEL_IMAGES]
        closest_pngs, closest_labels = build_panel_inputs(closest_local)
        farthest_pngs, farthest_labels = build_panel_inputs(farthest_local)

        make_contact_sheet_from_pngs(
            png_paths=closest_pngs,
            labels=closest_labels,
            out_path=out_dir / f"subclass_{ci:02d}_closest_to_prototype_panel.png",
            title=f"Seed {seed} class_02 subclass {ci:02d} closest | k={k}",
            cols=8,
            thumb_size=(180, 120),
        )
        make_contact_sheet_from_pngs(
            png_paths=farthest_pngs,
            labels=farthest_labels,
            out_path=out_dir / f"subclass_{ci:02d}_farthest_from_prototype_panel.png",
            title=f"Seed {seed} class_02 subclass {ci:02d} farthest | k={k}",
            cols=8,
            thumb_size=(180, 120),
        )

        sorted_dist = np.sort(distances)
        n = int(sorted_dist.size)
        q90 = float(sorted_dist[int(round(0.9 * (n - 1)))]) if n > 1 else float(sorted_dist[0])
        out_rows.append(
            {
                "seed": seed,
                "k": int(k),
                "subclass_id": int(ci),
                "subclass_size": n,
                "distance_mean": float(np.mean(sorted_dist)),
                "distance_std": float(np.std(sorted_dist)),
                "distance_q90": q90,
                "distance_max": float(sorted_dist[-1]),
                "distance_min": float(sorted_dist[0]),
                "distance_range": float(sorted_dist[-1] - sorted_dist[0]),
            }
        )

    return pd.DataFrame(out_rows)


def save_local_dendrogram(linkage_matrix: np.ndarray, out_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(11.0, 4.8))
    from scipy.cluster.hierarchy import dendrogram

    dendrogram(
        linkage_matrix,
        no_labels=True,
        color_threshold=None,
        above_threshold_color="#6b7280",
        ax=ax,
    )
    ax.set_title(title)
    ax.set_xlabel("class_02 samples")
    ax.set_ylabel("Merge distance")
    ax.grid(True, linestyle="--", alpha=0.25)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_local_pca(coords: np.ndarray, labels: np.ndarray, out_path: Path, title: str) -> None:
    uniq = np.unique(labels)
    cmap = plt.get_cmap("tab20")
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    for i, cls in enumerate(uniq):
        idx = labels == cls
        ax.scatter(coords[idx, 0], coords[idx, 1], s=24, alpha=0.85, color=cmap(i % 20), label=f"SC{int(cls):02d} (n={int(np.sum(idx))})")
    ax.set_title(title)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="best", fontsize=8, frameon=True)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def normalized_prototype_distance(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    valid = mask.reshape(-1)
    da = a.reshape(-1)[valid]
    db = b.reshape(-1)[valid]
    d = da - db
    return float(np.sqrt(np.nanmean(d * d)))


def main() -> None:
    args = parse_args()
    k_values = sorted(set(int(k) for k in args.k_values))
    if any(k < 2 for k in k_values):
        raise ValueError("All k-values must be >= 2.")
    if any(k > 3 for k in k_values):
        raise ValueError("Please keep local refinement controlled: max k=3.")

    seed_runs = parse_seed_runs(summary_csv=args.summary_csv, seeds=args.seeds)
    out_root = args.out_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    log(f"Output root: {out_root}")

    in_paths = resolve_input_paths()
    X_sst, X_norm, mask, vlim = load_numeric_inputs_with_fallback(in_paths)
    png_map = build_png_map()
    image_proxy = image_icv_proxy(X_sst=X_sst, mask=mask)

    cfg = FaithfulInitialConfig(
        n_classes=5,
        dict_batch_size=int(args.dict_batch_size),
        transform_nnz=int(args.transform_nnz),
        include_valid_mask=True,
        mask_encoding="concat",
        feature_mode="raw",
    )

    run_rows: List[dict] = []
    subclass_rows: List[pd.DataFrame] = []

    for sr in seed_runs:
        seed_dir = out_root / f"seed_{sr.seed:02d}"
        seed_dir.mkdir(parents=True, exist_ok=True)

        class02_idx_global = parse_class02_members(sr.sd_dir)
        n_class02 = int(class02_idx_global.size)
        baseline_dist_csv = sr.sd_dir / "class_02_distance_to_prototype.csv"
        baseline_dist_df = pd.read_csv(baseline_dist_csv) if baseline_dist_csv.exists() else pd.DataFrame()

        log(f"Seed {sr.seed}: training dictionary/features (global representation) to refine class_02 only...")
        model = train_dictionary_ordered_stream(
            X=X_norm,
            patch_h=PATCH_H,
            patch_w=PATCH_W,
            seed=sr.seed,
            dictionary_size=DICTIONARY_SIZE,
            cfg=cfg,
        )
        features, _ppi, _pvl, _fvl = encode_images_with_full_sparse_features(
            X=X_norm,
            model=model,
            patch_h=PATCH_H,
            patch_w=PATCH_W,
            dictionary_size=DICTIONARY_SIZE,
            cfg=cfg,
        )
        features_scaled = StandardScaler().fit_transform(features.astype(np.float64, copy=False))
        local_features = features_scaled[class02_idx_global]
        X_norm_local = X_norm[class02_idx_global]

        linkage_local = linkage(local_features, method="ward", metric="euclidean")
        save_local_dendrogram(
            linkage_matrix=linkage_local,
            out_path=seed_dir / "class02_local_dendrogram.png",
            title=f"Seed {sr.seed} class_02 local Ward dendrogram (SD30 baseline subset)",
        )
        pca_coords = None if args.no_pca else PCA(n_components=2, random_state=0).fit_transform(local_features)

        if baseline_dist_df.empty:
            baseline_mean = float("nan")
            baseline_q90 = float("nan")
            baseline_max = float("nan")
        else:
            vals = np.sort(baseline_dist_df["distance_to_prototype_rmse_norm"].astype(float).to_numpy())
            baseline_mean = float(np.mean(vals))
            baseline_q90 = float(vals[int(round(0.9 * (len(vals) - 1)))]) if len(vals) > 1 else float(vals[0])
            baseline_max = float(vals[-1])

        for k in k_values:
            k_dir = seed_dir / f"k{k}"
            k_dir.mkdir(parents=True, exist_ok=True)
            labels = fcluster(linkage_local, t=k, criterion="maxclust").astype(np.int32, copy=False)
            unique_labels = np.unique(labels)
            subclass_indices_local = [np.where(labels == cls)[0] for cls in sorted(unique_labels)]

            protos = save_local_prototypes(
                out_dir=k_dir,
                X_norm_subset=X_norm_local,
                mask=mask,
                subclass_indices_local=subclass_indices_local,
                seed=sr.seed,
                k=k,
                vmin=float(vlim[0]),
                vmax=float(vlim[1]),
            )
            subclass_df = save_local_member_and_homogeneity_artifacts(
                out_dir=k_dir,
                X_norm_subset=X_norm_local,
                mask=mask,
                subclass_indices_local=subclass_indices_local,
                subclass_prototypes=protos,
                global_indices=class02_idx_global,
                image_proxy_global=image_proxy,
                png_map=png_map,
                seed=sr.seed,
                k=k,
            )
            subclass_rows.append(subclass_df.copy())

            if pca_coords is not None:
                save_local_pca(
                    coords=pca_coords,
                    labels=labels,
                    out_path=k_dir / "class02_local_pca2d_subclasses.png",
                    title=f"Seed {sr.seed} class_02 local PCA | k={k}",
                )

            size_values = np.array([len(x) for x in subclass_indices_local], dtype=np.int32)
            mean_values = subclass_df["distance_mean"].astype(float).to_numpy()
            weighted_mean = float(np.sum(mean_values * size_values) / np.sum(size_values))

            pairwise_proto_dist: List[float] = []
            for i in range(len(protos)):
                for j in range(i + 1, len(protos)):
                    pairwise_proto_dist.append(normalized_prototype_distance(protos[i], protos[j], mask=mask))
            min_proto_dist = float(np.min(pairwise_proto_dist)) if pairwise_proto_dist else 0.0
            mean_proto_dist = float(np.mean(pairwise_proto_dist)) if pairwise_proto_dist else 0.0

            try:
                sil = float(silhouette_score(local_features, labels, metric="euclidean"))
            except Exception:
                sil = float("nan")

            run_rows.append(
                {
                    "seed": sr.seed,
                    "run_dir": sr.run_dir,
                    "global_number_of_classes_at_sd30": sr.number_of_classes,
                    "global_class_id": WORKING_CLASS_ID,
                    "global_class_size": n_class02,
                    "local_k": int(k),
                    "local_n_subclasses": int(len(subclass_indices_local)),
                    "subclass_sizes": json.dumps([int(v) for v in size_values.tolist()]),
                    "subclass_min_size": int(np.min(size_values)),
                    "subclass_max_size": int(np.max(size_values)),
                    "subclass_size_ratio_max_over_min": float(np.max(size_values) / max(1, np.min(size_values))),
                    "baseline_class02_mean_distance": baseline_mean,
                    "baseline_class02_q90_distance": baseline_q90,
                    "baseline_class02_max_distance": baseline_max,
                    "local_weighted_mean_distance": weighted_mean,
                    "local_mean_minus_baseline_mean": float(weighted_mean - baseline_mean),
                    "min_pairwise_subclass_prototype_rmse_norm": min_proto_dist,
                    "mean_pairwise_subclass_prototype_rmse_norm": mean_proto_dist,
                    "silhouette_score": sil,
                    "output_dir": str(k_dir.relative_to(ROOT)).replace("\\", "/"),
                }
            )

            # Compact text summary per seed/k.
            compact_report = [
                f"# Seed {sr.seed} class_02 local refinement (k={k})",
                "",
                f"- global run dir: `{sr.run_dir}`",
                f"- global SD dir: `{sr.sd_dir.relative_to(ROOT).as_posix()}`",
                f"- global class_02 size: {n_class02}",
                f"- subclass sizes: {size_values.tolist()}",
                f"- baseline class_02 mean/q90/max distance: {baseline_mean:.6f} / {baseline_q90:.6f} / {baseline_max:.6f}",
                f"- local weighted mean distance: {weighted_mean:.6f}",
                f"- min/mean pairwise prototype RMSE: {min_proto_dist:.6f} / {mean_proto_dist:.6f}",
                f"- silhouette score: {sil:.6f}" if np.isfinite(sil) else "- silhouette score: NaN",
                "",
                "Artifacts in this folder:",
                "- `subclass_prototypes_panel.png`",
                "- `subclass_prototype_XX.png`",
                "- `subclass_XX_members_list.csv`",
                "- `subclass_XX_members_panel.png`",
                "- `subclass_XX_pixel_std_map.png`",
                "- `subclass_XX_distance_to_prototype.csv`",
                "- `subclass_XX_closest_to_prototype_panel.png`",
                "- `subclass_XX_farthest_from_prototype_panel.png`",
                "- `class02_local_pca2d_subclasses.png` (if PCA enabled)",
            ]
            (k_dir / "compact_report.md").write_text("\n".join(compact_report), encoding="utf-8")

    refined_summary = pd.DataFrame(run_rows).sort_values(["seed", "local_k"]).reset_index(drop=True)
    refined_summary.to_csv(out_root / "refined_class02_summary.csv", index=False)

    if subclass_rows:
        subclasses_all = pd.concat(subclass_rows, axis=0, ignore_index=True)
    else:
        subclasses_all = pd.DataFrame(
            columns=[
                "seed",
                "k",
                "subclass_id",
                "subclass_size",
                "distance_mean",
                "distance_std",
                "distance_q90",
                "distance_max",
                "distance_min",
                "distance_range",
            ]
        )
    subclasses_all.to_csv(out_root / "refined_class02_subclass_metrics.csv", index=False)

    aggregate_rows = []
    for k in sorted(refined_summary["local_k"].unique().tolist()):
        sub = refined_summary[refined_summary["local_k"] == k]
        aggregate_rows.append(
            {
                "local_k": int(k),
                "n_seeds": int(len(sub)),
                "mean_global_class02_size": float(sub["global_class_size"].mean()),
                "mean_local_weighted_mean_distance": float(sub["local_weighted_mean_distance"].mean()),
                "mean_baseline_class02_mean_distance": float(sub["baseline_class02_mean_distance"].mean()),
                "mean_delta_local_minus_baseline": float(sub["local_mean_minus_baseline_mean"].mean()),
                "mean_min_pairwise_subclass_prototype_rmse_norm": float(sub["min_pairwise_subclass_prototype_rmse_norm"].mean()),
                "mean_silhouette_score": float(sub["silhouette_score"].mean(skipna=True)),
            }
        )
    pd.DataFrame(aggregate_rows).to_csv(out_root / "refined_class02_aggregate_by_k.csv", index=False)

    top_report = [
        "# class_02 local refinement summary",
        "",
        f"- source summary: `{args.summary_csv.resolve()}`",
        f"- seeds analyzed: {[int(s) for s in args.seeds]}",
        f"- k values tested: {k_values}",
        f"- output root: `{out_root}`",
        "",
        "Main files:",
        "- `refined_class02_summary.csv`",
        "- `refined_class02_subclass_metrics.csv`",
        "- `refined_class02_aggregate_by_k.csv`",
        "- `seed_XX/class02_local_dendrogram.png`",
        "- `seed_XX/kY/compact_report.md` and subclass artifacts",
    ]
    (out_root / "COMPACT_REPORT.md").write_text("\n".join(top_report), encoding="utf-8")

    log(f"Wrote: {out_root / 'refined_class02_summary.csv'}")
    log(f"Wrote: {out_root / 'refined_class02_subclass_metrics.csv'}")
    log(f"Wrote: {out_root / 'refined_class02_aggregate_by_k.csv'}")
    log(f"Wrote: {out_root / 'COMPACT_REPORT.md'}")
    log("Done.")


if __name__ == "__main__":
    main()
