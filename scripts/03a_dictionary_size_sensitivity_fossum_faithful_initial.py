"""Dictionary-size sensitivity for the faithful-initial Fossum pipeline."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering

from fossum_faithful_initial_utils import (
    IN_MASK,
    IN_X_NORM,
    IN_X_SST,
    ROOT,
    FaithfulInitialConfig,
    compute_icv_sst_space,
    encode_images_with_full_sparse_features,
    ensure_inputs,
    load_numeric_inputs,
    make_md_table,
    parse_positive_int_values,
    train_dictionary_ordered_stream,
    valid_patch_size,
)

DEFAULT_OUT_BASE = ROOT / "results" / "fossum" / "faithful_initial_dictionary_size_sensitivity"
DEFAULT_DOC = ROOT / "docs" / "DICTIONARY_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL.md"
DEFAULT_XDS_VALUES = [2, 4, 6, 8, 10, 12]
DEFAULT_SEEDS = [11, 23]
DEFAULT_PATCH_W = 72
DEFAULT_PATCH_H = 40


@dataclass
class RunResult:
    dictionary_size: int
    patch_w: int
    patch_h: int
    seed: int
    include_valid_mask: bool
    mask_encoding: str
    feature_mode: str
    patches_per_image: int
    total_patches: int
    patch_vector_length: int
    feature_vector_length: int
    number_of_classes: int
    class_sizes: str
    icv_class_01: float
    icv_class_02: float
    icv_class_03: float
    icv_class_04: float
    mean_icv: float
    std_icv: float
    min_class_size: int
    mean_class_size: float
    max_class_size: int
    runtime_seconds: float
    notes: str


def log(msg: str) -> None:
    print(f"[faithful-dict] {msg}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dictionary-size sensitivity for faithful Fossum initial classification.")
    p.add_argument("--out-base", type=Path, default=DEFAULT_OUT_BASE)
    p.add_argument("--doc-path", type=Path, default=DEFAULT_DOC)
    p.add_argument("--xds-values", nargs="*", type=int, default=None)
    p.add_argument("--seeds", nargs="*", type=int, default=None)
    p.add_argument("--patch-w", type=int, default=DEFAULT_PATCH_W)
    p.add_argument("--patch-h", type=int, default=DEFAULT_PATCH_H)
    p.add_argument("--feature-mode", choices=["raw", "abs"], default="raw")
    p.add_argument("--mask-encoding", choices=["concat"], default="concat")
    p.add_argument("--no-valid-mask", action="store_true")
    p.add_argument("--dict-batch-size", type=int, default=4096)
    p.add_argument("--transform-nnz", type=int, default=2)
    p.add_argument("--n-classes", type=int, default=4)
    p.add_argument("--no-resume", action="store_true")
    return p.parse_args()


def save_runs_csv(rows: Iterable[RunResult], out_runs: Path) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in rows])
    out_runs.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_runs, index=False)
    return df


def load_existing_runs(out_runs: Path) -> List[RunResult]:
    if not out_runs.exists():
        return []
    rows: List[RunResult] = []
    df = pd.read_csv(out_runs)
    for _, r in df.iterrows():
        rows.append(
            RunResult(
                dictionary_size=int(r["dictionary_size"]),
                patch_w=int(r["patch_w"]),
                patch_h=int(r["patch_h"]),
                seed=int(r["seed"]),
                include_valid_mask=bool(r["include_valid_mask"]),
                mask_encoding=str(r["mask_encoding"]),
                feature_mode=str(r["feature_mode"]),
                patches_per_image=int(r["patches_per_image"]),
                total_patches=int(r["total_patches"]),
                patch_vector_length=int(r["patch_vector_length"]),
                feature_vector_length=int(r["feature_vector_length"]),
                number_of_classes=int(r["number_of_classes"]),
                class_sizes=str(r["class_sizes"]),
                icv_class_01=float(r["icv_class_01"]),
                icv_class_02=float(r["icv_class_02"]),
                icv_class_03=float(r["icv_class_03"]),
                icv_class_04=float(r["icv_class_04"]),
                mean_icv=float(r["mean_icv"]),
                std_icv=float(r["std_icv"]),
                min_class_size=int(r["min_class_size"]),
                mean_class_size=float(r["mean_class_size"]),
                max_class_size=int(r["max_class_size"]),
                runtime_seconds=float(r["runtime_seconds"]),
                notes=str(r["notes"]),
            )
        )
    return rows


def build_summary(runs_df: pd.DataFrame, requested_runs: int) -> pd.DataFrame:
    grouped = runs_df.groupby(["dictionary_size"], as_index=False)
    summary = grouped.agg(
        executed_runs=("seed", "count"),
        patch_w=("patch_w", "first"),
        patch_h=("patch_h", "first"),
        include_valid_mask=("include_valid_mask", "first"),
        mask_encoding=("mask_encoding", "first"),
        feature_mode=("feature_mode", "first"),
        patches_per_image=("patches_per_image", "first"),
        total_patches=("total_patches", "first"),
        patch_vector_length=("patch_vector_length", "first"),
        feature_vector_length=("feature_vector_length", "first"),
        mean_icv_mean=("mean_icv", "mean"),
        mean_icv_std=("mean_icv", "std"),
        std_icv_mean=("std_icv", "mean"),
        std_icv_std=("std_icv", "std"),
        min_class_size_mean=("min_class_size", "mean"),
        min_class_size_min=("min_class_size", "min"),
        mean_class_size_mean=("mean_class_size", "mean"),
        max_class_size_mean=("max_class_size", "mean"),
        runtime_mean_seconds=("runtime_seconds", "mean"),
        runtime_std_seconds=("runtime_seconds", "std"),
    )
    summary["requested_runs"] = requested_runs
    summary["reduced_seed_count"] = summary["executed_runs"] < requested_runs
    return summary.sort_values(["dictionary_size"]).reset_index(drop=True)


def label_from_xds(xds: int) -> str:
    return f"xds={xds}"


def plot_boxplot_icv(runs_df: pd.DataFrame, out_plots: Path) -> None:
    ordered = runs_df.sort_values(["dictionary_size"])
    labels: List[str] = []
    values: List[np.ndarray] = []
    for xds, sub in ordered.groupby("dictionary_size"):
        labels.append(label_from_xds(int(xds)))
        values.append(sub["mean_icv"].to_numpy(dtype=float))
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    ax.boxplot(values, tick_labels=labels, showmeans=True)
    ax.set_title("Faithful initial: mean ICV spread by dictionary size")
    ax.set_xlabel("Dictionary size (xds)")
    ax.set_ylabel("Mean ICV (SST/original space)")
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_plots / "icv_boxplot_dictionarysize_faithful_initial.png", dpi=170)
    plt.close(fig)


def plot_summary_metric(
    summary_df: pd.DataFrame,
    y_col: str,
    yerr_col: str | None,
    out_path: Path,
    title: str,
    ylabel: str,
) -> None:
    labels = [label_from_xds(int(r["dictionary_size"])) for _, r in summary_df.iterrows()]
    x = np.arange(len(summary_df))
    y = summary_df[y_col].to_numpy(dtype=float)
    yerr = summary_df[yerr_col].to_numpy(dtype=float) if yerr_col else None
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    if yerr_col:
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, linewidth=1.6)
    else:
        ax.plot(x, y, marker="o", linewidth=1.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_xlabel("Dictionary size (xds)")
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def build_ranking(summary_df: pd.DataFrame) -> pd.DataFrame:
    ranked = summary_df.copy()
    ranked["rank_mean_icv"] = ranked["mean_icv_mean"].rank(method="min", ascending=True)
    ranked["rank_icv_spread"] = ranked["mean_icv_std"].rank(method="min", ascending=True)
    ranked["rank_std_icv"] = ranked["std_icv_mean"].rank(method="min", ascending=True)
    ranked["rank_min_class"] = ranked["min_class_size_min"].rank(method="min", ascending=False)
    ranked["rank_runtime"] = ranked["runtime_mean_seconds"].rank(method="min", ascending=True)
    ranked["balanced_score"] = (
        0.30 * ranked["rank_mean_icv"]
        + 0.20 * ranked["rank_icv_spread"]
        + 0.20 * ranked["rank_std_icv"]
        + 0.20 * ranked["rank_min_class"]
        + 0.10 * ranked["rank_runtime"]
    )
    return ranked.sort_values("balanced_score").reset_index(drop=True)


def write_report(
    doc_path: Path,
    out_base: Path,
    summary_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    xds_values: Sequence[int],
    seeds: Sequence[int],
    patch_w: int,
    patch_h: int,
    cfg: FaithfulInitialConfig,
) -> None:
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    top = ranking_df.head(min(3, len(ranking_df)))
    md = [
        "# DICTIONARY_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL",
        "",
        "## Scope",
        "- This is a new faithful-initial pipeline, separate from baseline historical scripts.",
        "- Only initial classification is included in this phase.",
        "",
        "## Faithful initial changes",
        f"- patch vector uses `[patch_temp_filled, patch_valid_mask]` (mask_encoding={cfg.mask_encoding})",
        f"- include_valid_mask={cfg.include_valid_mask}",
        "- patch extraction order is deterministic (left-to-right, top-to-bottom)",
        "- no patch-order shuffle and no image-order shuffle during dictionary training",
        "- MiniBatchDictionaryLearning uses `shuffle=False`; variability comes from `random_state=seed`",
        "- feature per image is the full sparse-code sequence (no mean/std reduction)",
        f"- feature_mode={cfg.feature_mode}",
        "",
        "## Feature vector definition",
        "- Let `P = patches_per_image` and `K = dictionary_size`.",
        "- Sparse codes per image: shape `(P, K)`.",
        "- Final image feature vector: flatten sparse codes in patch order -> length `P * K`.",
        "",
        "## Inputs",
        f"- clustering/sparse coding: `{IN_X_NORM.relative_to(ROOT).as_posix()}`",
        f"- ICV: `{IN_X_SST.relative_to(ROOT).as_posix()}`",
        f"- mask: `{IN_MASK.relative_to(ROOT).as_posix()}`",
        "",
        "## Configuration",
        f"- fixed patch size: ({patch_w},{patch_h})",
        f"- dictionary sizes: {', '.join(str(v) for v in xds_values)}",
        f"- seeds: {', '.join(str(s) for s in seeds)}",
        f"- n_classes={cfg.n_classes}",
        "",
        "## Summary",
        make_md_table(
            summary_df[
                [
                    "dictionary_size",
                    "executed_runs",
                    "patch_vector_length",
                    "feature_vector_length",
                    "mean_icv_mean",
                    "mean_icv_std",
                    "min_class_size_min",
                    "runtime_mean_seconds",
                ]
            ],
            [
                "dictionary_size",
                "executed_runs",
                "patch_vector_length",
                "feature_vector_length",
                "mean_icv_mean",
                "mean_icv_std",
                "min_class_size_min",
                "runtime_mean_seconds",
            ],
        ),
        "",
        "## Top candidates (balanced score)",
        make_md_table(
            top[
                [
                    "dictionary_size",
                    "balanced_score",
                    "mean_icv_mean",
                    "mean_icv_std",
                    "min_class_size_min",
                    "runtime_mean_seconds",
                ]
            ],
            [
                "dictionary_size",
                "balanced_score",
                "mean_icv_mean",
                "mean_icv_std",
                "min_class_size_min",
                "runtime_mean_seconds",
            ],
        ),
        "",
        "## Outputs",
        f"- runs: `{(out_base / 'runs.csv').relative_to(ROOT).as_posix()}`",
        f"- summary: `{(out_base / 'summary.csv').relative_to(ROOT).as_posix()}`",
        f"- ranking: `{(out_base / 'ranking.csv').relative_to(ROOT).as_posix()}`",
        f"- plots: `{(out_base / 'plots').relative_to(ROOT).as_posix()}`",
    ]
    doc_path.write_text("\n".join(md), encoding="utf-8")


def run_single(
    X_norm: np.ndarray,
    X_sst: np.ndarray,
    mask: np.ndarray,
    patch_w: int,
    patch_h: int,
    dictionary_size: int,
    seed: int,
    cfg: FaithfulInitialConfig,
) -> RunResult:
    t0 = time.perf_counter()
    n_images, ny, nx = X_norm.shape

    if not valid_patch_size(ny, nx, patch_h=patch_h, patch_w=patch_w):
        dt = time.perf_counter() - t0
        return RunResult(
            dictionary_size=dictionary_size,
            patch_w=patch_w,
            patch_h=patch_h,
            seed=seed,
            include_valid_mask=cfg.include_valid_mask,
            mask_encoding=cfg.mask_encoding,
            feature_mode=cfg.feature_mode,
            patches_per_image=0,
            total_patches=0,
            patch_vector_length=0,
            feature_vector_length=0,
            number_of_classes=0,
            class_sizes="[]",
            icv_class_01=float("nan"),
            icv_class_02=float("nan"),
            icv_class_03=float("nan"),
            icv_class_04=float("nan"),
            mean_icv=float("nan"),
            std_icv=float("nan"),
            min_class_size=0,
            mean_class_size=float("nan"),
            max_class_size=0,
            runtime_seconds=float(dt),
            notes="skipped invalid patch size",
        )

    model = train_dictionary_ordered_stream(
        X=X_norm,
        patch_h=patch_h,
        patch_w=patch_w,
        seed=seed,
        dictionary_size=dictionary_size,
        cfg=cfg,
    )
    features, patches_per_image, patch_vector_length, feature_vector_length = encode_images_with_full_sparse_features(
        X=X_norm,
        model=model,
        patch_h=patch_h,
        patch_w=patch_w,
        dictionary_size=dictionary_size,
        cfg=cfg,
    )
    labels = AgglomerativeClustering(n_clusters=cfg.n_classes, linkage="ward").fit_predict(features)
    icv_per_class, class_sizes, _class_indices = compute_icv_sst_space(X_sst=X_sst, labels=labels, mask=mask)
    padded_icv = icv_per_class + [float("nan")] * max(0, cfg.n_classes - len(icv_per_class))
    dt = time.perf_counter() - t0
    return RunResult(
        dictionary_size=dictionary_size,
        patch_w=patch_w,
        patch_h=patch_h,
        seed=seed,
        include_valid_mask=cfg.include_valid_mask,
        mask_encoding=cfg.mask_encoding,
        feature_mode=cfg.feature_mode,
        patches_per_image=patches_per_image,
        total_patches=int(n_images * patches_per_image),
        patch_vector_length=patch_vector_length,
        feature_vector_length=feature_vector_length,
        number_of_classes=int(len(class_sizes)),
        class_sizes=json.dumps(class_sizes),
        icv_class_01=float(padded_icv[0]),
        icv_class_02=float(padded_icv[1]),
        icv_class_03=float(padded_icv[2]),
        icv_class_04=float(padded_icv[3]),
        mean_icv=float(np.mean(icv_per_class)),
        std_icv=float(np.std(icv_per_class)),
        min_class_size=int(np.min(class_sizes)),
        mean_class_size=float(np.mean(class_sizes)),
        max_class_size=int(np.max(class_sizes)),
        runtime_seconds=float(dt),
        notes="ok",
    )


def main() -> None:
    args = parse_args()
    xds_values = parse_positive_int_values(args.xds_values, defaults=DEFAULT_XDS_VALUES, label="dictionary_size")
    seeds = args.seeds if args.seeds else DEFAULT_SEEDS.copy()
    patch_w = int(args.patch_w)
    patch_h = int(args.patch_h)
    if patch_w <= 0 or patch_h <= 0:
        raise ValueError("--patch-w and --patch-h must be > 0")
    if args.transform_nnz <= 0:
        raise ValueError("--transform-nnz must be > 0")
    if args.n_classes <= 0:
        raise ValueError("--n-classes must be > 0")

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
    _n_images, ny, nx = X_norm.shape
    if not valid_patch_size(ny, nx, patch_h=patch_h, patch_w=patch_w):
        raise ValueError(f"Invalid patch size ({patch_w},{patch_h}) for grid ({nx},{ny}).")

    out_base = args.out_base.resolve()
    out_runs = out_base / "runs.csv"
    out_summary = out_base / "summary.csv"
    out_ranking = out_base / "ranking.csv"
    out_plots = out_base / "plots"
    out_base.mkdir(parents=True, exist_ok=True)
    out_plots.mkdir(parents=True, exist_ok=True)

    runs = [] if args.no_resume else load_existing_runs(out_runs)
    done = {
        (
            r.dictionary_size,
            r.seed,
            r.patch_w,
            r.patch_h,
            r.include_valid_mask,
            r.mask_encoding,
            r.feature_mode,
        )
        for r in runs
        if r.notes == "ok"
    }

    log(
        "Faithful initial config: "
        f"n_classes={cfg.n_classes}, dict_batch_size={cfg.dict_batch_size}, transform_nnz={cfg.transform_nnz}, "
        f"include_valid_mask={cfg.include_valid_mask}, mask_encoding={cfg.mask_encoding}, feature_mode={cfg.feature_mode}"
    )
    log(
        "Methodological lock: deterministic patch extraction + no shuffle in image/patch order; "
        "seed only controls dictionary randomness."
    )
    log(f"Fixed patch size={patch_w}x{patch_h}")
    log(f"Dictionary sizes={xds_values}")
    log(f"Seeds={seeds}")
    log(f"Resume={not args.no_resume}; existing_ok_runs={len(done)}")

    for xds in xds_values:
        log(f"Dictionary size xds={xds}")
        for seed in seeds:
            key = (
                int(xds),
                int(seed),
                patch_w,
                patch_h,
                cfg.include_valid_mask,
                cfg.mask_encoding,
                cfg.feature_mode,
            )
            if key in done:
                log(f"  skip existing xds={xds} seed={seed}")
                continue
            log(f"  run start xds={xds} seed={seed}")
            result = run_single(
                X_norm=X_norm,
                X_sst=X_sst,
                mask=mask,
                patch_w=patch_w,
                patch_h=patch_h,
                dictionary_size=int(xds),
                seed=int(seed),
                cfg=cfg,
            )
            runs.append(result)
            save_runs_csv(runs, out_runs)
            log(
                f"  run done xds={xds} seed={seed}: "
                f"mean_icv={result.mean_icv:.6f} std_icv={result.std_icv:.6f} "
                f"feature_len={result.feature_vector_length} patch_vec_len={result.patch_vector_length} "
                f"runtime={result.runtime_seconds:.2f}s"
            )

    runs_df = save_runs_csv(runs, out_runs)
    valid_runs = runs_df[runs_df["notes"] == "ok"].copy()
    if valid_runs.empty:
        raise RuntimeError("No valid runs were executed.")

    summary_df = build_summary(valid_runs, requested_runs=len(seeds))
    summary_df.to_csv(out_summary, index=False)
    ranking_df = build_ranking(summary_df)
    ranking_df.to_csv(out_ranking, index=False)

    plot_boxplot_icv(valid_runs, out_plots)
    plot_summary_metric(
        summary_df=summary_df,
        y_col="mean_icv_mean",
        yerr_col="mean_icv_std",
        out_path=out_plots / "icv_mean_vs_dictionarysize_faithful_initial.png",
        title="Faithful initial mean ICV vs dictionary size",
        ylabel="Mean ICV (SST/original space)",
    )
    plot_summary_metric(
        summary_df=summary_df,
        y_col="min_class_size_mean",
        yerr_col=None,
        out_path=out_plots / "min_class_size_vs_dictionarysize_faithful_initial.png",
        title="Faithful initial min class size vs dictionary size",
        ylabel="Min class size (mean over runs)",
    )
    plot_summary_metric(
        summary_df=summary_df,
        y_col="runtime_mean_seconds",
        yerr_col="runtime_std_seconds",
        out_path=out_plots / "runtime_vs_dictionarysize_faithful_initial.png",
        title="Faithful initial runtime vs dictionary size",
        ylabel="Runtime (seconds)",
    )

    write_report(
        doc_path=args.doc_path.resolve(),
        out_base=out_base,
        summary_df=summary_df,
        ranking_df=ranking_df,
        xds_values=xds_values,
        seeds=seeds,
        patch_w=patch_w,
        patch_h=patch_h,
        cfg=cfg,
    )

    top = ranking_df.head(min(3, len(ranking_df)))
    log("Top dictionary-size candidates (balanced):")
    for i, row in top.iterrows():
        log(
            f"  #{i+1} xds={int(row['dictionary_size'])} "
            f"score={row['balanced_score']:.4f} mean_icv={row['mean_icv_mean']:.6f} "
            f"spread={row['mean_icv_std']:.6f}"
        )
    log(f"Wrote runs: {out_runs}")
    log(f"Wrote summary: {out_summary}")
    log(f"Wrote ranking: {out_ranking}")
    log(f"Wrote plots: {out_plots}")
    log(f"Wrote doc: {args.doc_path.resolve()}")


if __name__ == "__main__":
    main()
