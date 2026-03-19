"""Smoke tests for faithful-initial Fossum pipeline invariants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from fossum_faithful_initial_utils import (
    ROOT,
    FaithfulInitialConfig,
    build_patch_vectors,
    encode_images_with_full_sparse_features,
    ensure_inputs,
    extract_patch_components,
    iterate_ordered_patch_batches,
    load_numeric_inputs,
    parse_patch_sizes,
    train_dictionary_ordered_stream,
)

DEFAULT_OUT_DIR = ROOT / "results" / "fossum" / "faithful_initial_smoke"
DEFAULT_PATCH = "24x16"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Smoke test for faithful-initial Fossum pipeline.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--num-images", type=int, default=6)
    p.add_argument("--patch-size", type=str, default=DEFAULT_PATCH, help="Patch size token WxH")
    p.add_argument("--dictionary-size", type=int, default=4)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--feature-mode", choices=["raw", "abs"], default="raw")
    p.add_argument("--mask-encoding", choices=["concat"], default="concat")
    p.add_argument("--no-valid-mask", action="store_true")
    p.add_argument("--dict-batch-size", type=int, default=1024)
    p.add_argument("--transform-nnz", type=int, default=2)
    p.add_argument("--n-classes", type=int, default=4)
    return p.parse_args()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _collect_first_batch_metas(X: np.ndarray, patch_h: int, patch_w: int, cfg: FaithfulInitialConfig) -> List[Tuple[int, int, int]]:
    metas: List[Tuple[int, int, int]] = []
    for meta, _batch in iterate_ordered_patch_batches(
        X=X,
        patch_h=patch_h,
        patch_w=patch_w,
        batch_size=cfg.dict_batch_size,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
    ):
        metas.append((meta.image_idx, meta.patch_start, meta.patch_end))
        if len(metas) >= 6:
            break
    return metas


def main() -> None:
    args = parse_args()
    if args.num_images < 2:
        raise ValueError("--num-images must be >= 2")
    if args.dictionary_size <= 0:
        raise ValueError("--dictionary-size must be > 0")
    if args.transform_nnz <= 0:
        raise ValueError("--transform-nnz must be > 0")
    if args.n_classes <= 1:
        raise ValueError("--n-classes must be > 1")

    patch_sizes = parse_patch_sizes([args.patch_size], defaults=[])
    patch_w, patch_h = patch_sizes[0]

    cfg = FaithfulInitialConfig(
        n_classes=int(args.n_classes),
        dict_batch_size=int(args.dict_batch_size),
        transform_nnz=int(args.transform_nnz),
        include_valid_mask=not bool(args.no_valid_mask),
        mask_encoding=str(args.mask_encoding),
        feature_mode=str(args.feature_mode),
    )

    ensure_inputs(require_png_dir=False)
    X_sst, X_norm, mask, _stats, _vlim = load_numeric_inputs()
    X_norm_small = X_norm[: args.num_images]
    X_sst_small = X_sst[: args.num_images]

    temp_patches, valid_patches = extract_patch_components(X_norm_small[0], patch_h=patch_h, patch_w=patch_w)
    concat_patches = build_patch_vectors(
        image_2d=X_norm_small[0],
        patch_h=patch_h,
        patch_w=patch_w,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
    )

    patch_area = patch_h * patch_w
    expected_patch_vector_length = patch_area * (2 if cfg.include_valid_mask else 1)
    _assert(concat_patches.shape[1] == expected_patch_vector_length, "Patch vector length mismatch.")

    if cfg.include_valid_mask:
        recovered_valid = concat_patches[:, patch_area:]
        _assert(np.all(np.isin(np.unique(recovered_valid), [0.0, 1.0])), "Patch valid mask must be binary 0/1.")
        missing_any = int(np.count_nonzero(~np.isfinite(X_norm_small[0]))) > 0
        if missing_any:
            missing_positions = np.where(recovered_valid == 0.0)
            _assert(missing_positions[0].size > 0, "Expected missing pixels in patch-valid mask.")
            first_missing_row = int(missing_positions[0][0])
            first_missing_col = int(missing_positions[1][0])
            _assert(
                concat_patches[first_missing_row, first_missing_col] == 0.0,
                "Missing value should remain distinguishable by valid-mask channel.",
            )

    filled = np.nan_to_num(X_norm_small[0], nan=0.0).astype(np.float32, copy=False)
    n_windows_x = X_norm_small.shape[2] - patch_w + 1
    n_windows_y = X_norm_small.shape[1] - patch_h + 1
    _assert(np.allclose(temp_patches[0], filled[0:patch_h, 0:patch_w].reshape(-1)), "First patch order mismatch.")
    if n_windows_x > 1:
        _assert(
            np.allclose(temp_patches[1], filled[0:patch_h, 1 : 1 + patch_w].reshape(-1)),
            "Second patch should be immediate right neighbor.",
        )
    if n_windows_y > 1:
        _assert(
            np.allclose(temp_patches[n_windows_x], filled[1 : 1 + patch_h, 0:patch_w].reshape(-1)),
            "Patch order should continue to next row after row end.",
        )

    first_metas = _collect_first_batch_metas(X_norm_small, patch_h=patch_h, patch_w=patch_w, cfg=cfg)
    _assert(len(first_metas) > 0, "No training batches produced.")
    _assert(first_metas[0][0] == 0 and first_metas[0][1] == 0, "First batch must start on image 0 / patch 0.")
    for i in range(1, len(first_metas)):
        prev = first_metas[i - 1]
        cur = first_metas[i]
        _assert(cur[0] >= prev[0], "Image order must be non-decreasing.")
        if cur[0] == prev[0]:
            _assert(cur[1] == prev[2], "Patch order within image must be contiguous and unshuffled.")

    model_a = train_dictionary_ordered_stream(
        X=X_norm_small,
        patch_h=patch_h,
        patch_w=patch_w,
        seed=int(args.seed),
        dictionary_size=int(args.dictionary_size),
        cfg=cfg,
    )
    features_a, patches_per_image, patch_vector_length, feature_vector_length = encode_images_with_full_sparse_features(
        X=X_norm_small,
        model=model_a,
        patch_h=patch_h,
        patch_w=patch_w,
        dictionary_size=int(args.dictionary_size),
        cfg=cfg,
    )
    labels_a = AgglomerativeClustering(n_clusters=cfg.n_classes, linkage="ward").fit_predict(features_a)
    _ = compute_icv = np.sum([np.var(X_sst_small[labels_a == cls][:, mask], axis=0, ddof=0).sum() for cls in np.unique(labels_a)])

    model_b = train_dictionary_ordered_stream(
        X=X_norm_small,
        patch_h=patch_h,
        patch_w=patch_w,
        seed=int(args.seed),
        dictionary_size=int(args.dictionary_size),
        cfg=cfg,
    )
    features_b, _, _, _ = encode_images_with_full_sparse_features(
        X=X_norm_small,
        model=model_b,
        patch_h=patch_h,
        patch_w=patch_w,
        dictionary_size=int(args.dictionary_size),
        cfg=cfg,
    )

    np.testing.assert_allclose(features_a, features_b, rtol=1e-5, atol=1e-5)
    _assert(feature_vector_length == patches_per_image * int(args.dictionary_size), "Feature vector length formula mismatch.")
    _assert(feature_vector_length > int(args.dictionary_size) * 2, "Feature vector seems collapsed; expected full sparse sequence.")

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "ok",
        "num_images": int(args.num_images),
        "patch_w": int(patch_w),
        "patch_h": int(patch_h),
        "dictionary_size": int(args.dictionary_size),
        "seed": int(args.seed),
        "include_valid_mask": bool(cfg.include_valid_mask),
        "mask_encoding": cfg.mask_encoding,
        "feature_mode": cfg.feature_mode,
        "patch_vector_length": int(patch_vector_length),
        "patches_per_image": int(patches_per_image),
        "feature_vector_length": int(feature_vector_length),
        "first_batch_metas": [{"image_idx": m[0], "patch_start": m[1], "patch_end": m[2]} for m in first_metas],
        "checks": [
            "patch_vector_contains_valid_mask_channel",
            "patch_order_is_left_to_right_then_top_to_bottom",
            "training_batches_follow_deterministic_image_and_patch_order",
            "image_feature_uses_full_sparse_code_sequence",
            "repeat_run_same_seed_produces_same_features_on_smoke_subset",
        ],
    }
    (out_dir / "smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
