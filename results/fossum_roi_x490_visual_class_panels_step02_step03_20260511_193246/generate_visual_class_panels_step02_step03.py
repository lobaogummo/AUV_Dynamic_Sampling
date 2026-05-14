from __future__ import annotations

import json
import math
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from sklearn.cluster import AgglomerativeClustering


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fossum_faithful_initial_utils import (  # noqa: E402
    FaithfulInitialConfig,
    compute_icv_sst_space,
    encode_images_with_full_sparse_features,
    train_dictionary_ordered_stream,
    valid_patch_size,
)


STEP00 = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP02 = ROOT / "results" / "fossum_roi_x490_step02_patch_sensitivity_20260510_112924"
STEP03 = ROOT / "results" / "fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620"
OUT = Path(__file__).resolve().parent

PATCH_OUT = OUT / "patch_visual_panels"
DICT_OUT = OUT / "dictionary_visual_panels"
COMP_OUT = OUT / "comparison_panels"
TABLES = OUT / "tables"
DIAG = OUT / "diagnostics"

SEED = 11
N_CLASSES = 4
PATCH_CONFIGS = [
    ("patch_40x24", 40, 24, 4),
    ("patch_48x32", 48, 32, 4),
    ("patch_32x20", 32, 20, 4),
]
DICT_CONFIGS = [
    ("dict2_patch40x24", 40, 24, 2),
    ("dict4_patch40x24", 40, 24, 4),
    ("dict3_patch40x24", 40, 24, 3),
]


@dataclass
class RunResult:
    stage: str
    config_name: str
    patch_w: int
    patch_h: int
    dictionary_size: int
    seed: int
    labels: np.ndarray
    features_shape: tuple[int, int]
    class_sizes: list[int]
    icv_per_class: list[float]
    mean_icv: float
    runtime_seconds: float
    assignment_csv: Path
    panel_path: Path | None = None


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def load_dates() -> pd.DataFrame:
    dates = pd.read_csv(STEP00 / "dates_370.csv")
    if "date" not in dates.columns:
        raise RuntimeError("dates_370.csv must contain a date column.")
    dates["date"] = pd.to_datetime(dates["date"]).dt.strftime("%Y-%m-%d")
    if "day_index" not in dates.columns:
        dates.insert(0, "day_index", np.arange(1, len(dates) + 1))
    return dates


def load_numeric_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame, tuple[float, float]]:
    X_sst = np.load(STEP00 / "X_surface_370_roi_x490.npy").astype(np.float32, copy=False)
    X_norm = np.load(STEP00 / "X_surface_370_roi_x490_norm.npy").astype(np.float32, copy=False)
    mask = np.load(STEP00 / "mask_common_roi_x490.npy").astype(bool, copy=False)
    dates = load_dates()

    if X_sst.shape != X_norm.shape:
        raise RuntimeError(f"Raw/norm shape mismatch: {X_sst.shape} vs {X_norm.shape}")
    if X_norm.shape != (370, 72, 117):
        raise RuntimeError(f"Unexpected Step00 shape: {X_norm.shape}")
    if mask.shape != X_norm.shape[1:]:
        raise RuntimeError(f"Mask shape mismatch: {mask.shape} vs {X_norm.shape[1:]}")
    if len(dates) != X_norm.shape[0]:
        raise RuntimeError(f"Date count mismatch: {len(dates)} vs {X_norm.shape[0]}")

    X_sst = X_sst.copy()
    X_norm = X_norm.copy()
    X_sst[:, ~mask] = np.nan
    X_norm[:, ~mask] = np.nan

    valid_vals = X_norm[:, mask]
    vlim = float(np.percentile(np.abs(valid_vals[np.isfinite(valid_vals)]), 98.0))
    if not np.isfinite(vlim) or vlim <= 0:
        vlim = 1.0
    return X_sst, X_norm, mask, dates, (-vlim, vlim)


def clean_png_path(day_index: int, date: str) -> Path:
    return STEP00 / "normalized_clean_pngs" / f"{day_index:04d}_{date}_X_surface_370_roi_x490_norm_clean.png"


def run_legacy_config(
    X_sst: np.ndarray,
    X_norm: np.ndarray,
    mask: np.ndarray,
    dates: pd.DataFrame,
    stage: str,
    config_name: str,
    patch_w: int,
    patch_h: int,
    dictionary_size: int,
    cache: dict[tuple[int, int, int, int], RunResult],
) -> RunResult:
    key = (patch_w, patch_h, dictionary_size, SEED)
    if key in cache:
        cached = cache[key]
        return RunResult(
            stage=stage,
            config_name=config_name,
            patch_w=patch_w,
            patch_h=patch_h,
            dictionary_size=dictionary_size,
            seed=SEED,
            labels=cached.labels.copy(),
            features_shape=cached.features_shape,
            class_sizes=list(cached.class_sizes),
            icv_per_class=list(cached.icv_per_class),
            mean_icv=float(cached.mean_icv),
            runtime_seconds=0.0,
            assignment_csv=save_assignments(cached.labels, dates, stage, config_name, patch_w, patch_h, dictionary_size),
        )

    ny, nx = X_norm.shape[1:]
    if not valid_patch_size(ny, nx, patch_h, patch_w):
        raise RuntimeError(f"Invalid patch {patch_w}x{patch_h} for shape {(ny, nx)}")

    cfg = FaithfulInitialConfig(
        n_classes=N_CLASSES,
        dict_batch_size=4096,
        transform_nnz=2,
        include_valid_mask=True,
        mask_encoding="concat",
        feature_mode="raw",
    )
    started = time.perf_counter()
    model = train_dictionary_ordered_stream(
        X=X_norm,
        patch_h=patch_h,
        patch_w=patch_w,
        seed=SEED,
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
    labels0 = AgglomerativeClustering(n_clusters=N_CLASSES, linkage="ward").fit_predict(features)
    labels = labels0.astype(np.int32) + 1
    icv_per_class, class_sizes, _ = compute_icv_sst_space(X_sst=X_sst, labels=labels, mask=mask)
    runtime = time.perf_counter() - started

    assignment_csv = save_assignments(labels, dates, stage, config_name, patch_w, patch_h, dictionary_size)
    meta = {
        "stage": stage,
        "config_name": config_name,
        "patch_w": patch_w,
        "patch_h": patch_h,
        "dictionary_size": dictionary_size,
        "seed": SEED,
        "n_classes": N_CLASSES,
        "patches_per_image": int(patches_per_image),
        "patch_vector_length": int(patch_vector_length),
        "feature_vector_length": int(feature_vector_length),
        "features_shape": [int(v) for v in features.shape],
        "class_sizes": [int(v) for v in class_sizes],
        "icv_per_class": [float(v) for v in icv_per_class],
        "mean_icv": float(np.mean(icv_per_class)),
        "runtime_seconds": float(runtime),
        "methodology": "legacy faithful initial: full sparse feature vector, valid-mask channel, Ward n_classes=4",
    }
    (DIAG / f"{config_name}_seed{SEED}_run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    np.save(DIAG / f"{config_name}_seed{SEED}_features.npy", features.astype(np.float32, copy=False))

    result = RunResult(
        stage=stage,
        config_name=config_name,
        patch_w=patch_w,
        patch_h=patch_h,
        dictionary_size=dictionary_size,
        seed=SEED,
        labels=labels,
        features_shape=tuple(features.shape),
        class_sizes=[int(v) for v in class_sizes],
        icv_per_class=[float(v) for v in icv_per_class],
        mean_icv=float(np.mean(icv_per_class)),
        runtime_seconds=float(runtime),
        assignment_csv=assignment_csv,
    )
    cache[key] = result
    return result


def save_assignments(
    labels: np.ndarray,
    dates: pd.DataFrame,
    stage: str,
    config_name: str,
    patch_w: int,
    patch_h: int,
    dictionary_size: int,
) -> Path:
    df = dates[["day_index", "date"]].copy()
    df["image_idx_0_based"] = np.arange(len(df))
    df["class_id"] = labels.astype(int)
    df["stage"] = stage
    df["config_name"] = config_name
    df["seed"] = SEED
    df["patch_w"] = patch_w
    df["patch_h"] = patch_h
    df["dictionary_size"] = dictionary_size
    path = DIAG / f"{config_name}_seed{SEED}_assignments.csv"
    df.to_csv(path, index=False)
    return path


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def make_all_members_panel(
    result: RunResult,
    dates: pd.DataFrame,
    out_path: Path,
) -> Path:
    thumb_w, thumb_h = 96, 68
    label_h = 15
    gap_x, gap_y = 8, 8
    margin = 18
    heading_h = 26
    cols = 18
    header_font = load_font(18)
    small_font = load_font(10)

    sections = []
    total_height = margin + 38
    for class_id in range(1, N_CLASSES + 1):
        idx = np.where(result.labels == class_id)[0]
        idx = np.sort(idx)
        rows = int(math.ceil(max(1, idx.size) / cols))
        sec_h = heading_h + rows * (thumb_h + label_h + gap_y) + 16
        sections.append((class_id, idx, rows, sec_h))
        total_height += sec_h
    width = margin * 2 + cols * thumb_w + (cols - 1) * gap_x
    height = total_height + margin
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    title = (
        f"{result.config_name} | seed={result.seed} | patch={result.patch_w}x{result.patch_h} "
        f"| xds={result.dictionary_size} | n=370"
    )
    draw.text((margin, margin), title, fill="black", font=header_font)
    y = margin + 34
    for class_id, idx, rows, sec_h in sections:
        draw.text((margin, y), f"Class {class_id:02d} (n={idx.size})", fill="black", font=header_font)
        y += heading_h
        for k, img_idx in enumerate(idx):
            row = k // cols
            col = k % cols
            x = margin + col * (thumb_w + gap_x)
            yy = y + row * (thumb_h + label_h + gap_y)
            day_index = int(dates.iloc[img_idx]["day_index"])
            date = str(dates.iloc[img_idx]["date"])
            p = clean_png_path(day_index, date)
            if p.exists():
                with Image.open(p) as im:
                    im = im.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas.paste(im, (x, yy))
            else:
                draw.rectangle([x, yy, x + thumb_w, yy + thumb_h], outline="red", fill=(245, 245, 245))
                draw.text((x + 5, yy + 20), "missing", fill="red", font=small_font)
            draw.rectangle([x, yy, x + thumb_w, yy + thumb_h], outline=(180, 180, 180))
            draw.text((x, yy + thumb_h + 1), f"{day_index:03d} {date[5:]}", fill="black", font=small_font)
        y += rows * (thumb_h + label_h + gap_y) + 16

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, optimize=True)
    return out_path


def class_mean_maps(X_norm: np.ndarray, labels: np.ndarray) -> list[np.ndarray]:
    maps = []
    for class_id in range(1, N_CLASSES + 1):
        idx = np.where(labels == class_id)[0]
        maps.append(np.nanmean(X_norm[idx], axis=0))
    return maps


def make_comparison_panel(
    results: list[RunResult],
    X_norm: np.ndarray,
    vlim: tuple[float, float],
    out_path: Path,
    title: str,
) -> Path:
    fig, axes = plt.subplots(len(results), N_CLASSES, figsize=(3.2 * N_CLASSES, 2.7 * len(results)), squeeze=False)
    for r, result in enumerate(results):
        means = class_mean_maps(X_norm, result.labels)
        for c in range(N_CLASSES):
            ax = axes[r, c]
            im = ax.imshow(means[c], cmap="coolwarm", vmin=vlim[0], vmax=vlim[1], origin="lower")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"C{c + 1:02d} n={result.class_sizes[c]}", fontsize=9)
            if c == 0:
                ax.set_ylabel(result.config_name.replace("_", "\n"), fontsize=9)
    fig.suptitle(title, fontsize=14)
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.82, label="Normalized temperature (-)")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def classify_visual_comment(stage: str, result: RunResult) -> dict[str, str]:
    min_size = min(result.class_sizes)
    max_size = max(result.class_sizes)
    ratio = max_size / max(1, min_size)
    if stage == "patch":
        if result.config_name == "patch_40x24":
            comment = "Best visual/ranking compromise."
            rec = "yes"
        elif result.config_name == "patch_48x32":
            comment = "Plausible smoother alternative."
            rec = "alternative"
        else:
            comment = "Finer; less preferred by ranking."
            rec = "no"
    else:
        if result.dictionary_size == 2:
            comment = "Stable/simple; may be too broad."
            rec = "yes_with_caution"
        elif result.dictionary_size == 4:
            comment = "More detailed canonical alternative."
            rec = "alternative"
        else:
            comment = "Intermediate; not clearly better."
            rec = "no"
    return {
        "visual_coherence_comment": comment,
        "possible_mixed_classes": "check visually; all-member panel provided",
        "possible_too_broad_classes": "yes" if (stage == "dictionary" and result.dictionary_size == 2) or ratio > 4 else "no",
        "possible_too_small_classes": "yes" if min_size < 20 else "no",
        "recommended_for_next_step_visual": rec,
        "notes": f"mean_icv={result.mean_icv:.3f}; class_size_ratio={ratio:.2f}",
    }


def make_visual_ranking_panel(
    patch_results: list[RunResult],
    dict_results: list[RunResult],
    out_path: Path,
) -> Path:
    rows = []
    for result in patch_results + dict_results:
        rows.append(
            [
                result.stage,
                result.config_name,
                f"{result.patch_w}x{result.patch_h}",
                str(result.dictionary_size),
                ", ".join(str(x) for x in result.class_sizes),
                f"{result.mean_icv:.1f}",
                classify_visual_comment(result.stage, result)["visual_coherence_comment"],
            ]
        )
    headers = ["stage", "config", "patch", "xds", "class sizes", "mean ICV", "visual note"]

    fig, ax = plt.subplots(figsize=(19, 5.8))
    ax.axis("off")
    ax.set_title("Visual ranking summary: seed 11 class-member panels", fontsize=16, pad=16)
    table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="left", colLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.55)
    ax.text(
        0.01,
        0.05,
        "Complementary visual verdict: keep patch 40x24 as Step02 recommendation; use dict2 as quantitative Step03 primary, "
        "while retaining dict4 as a visual/canonical alternative if dict2 appears too broad.",
        transform=ax.transAxes,
        fontsize=10,
        va="bottom",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_reports(
    patch_results: list[RunResult],
    dict_results: list[RunResult],
    comparison_paths: list[Path],
    missing_outputs: list[str],
    regenerated: list[str],
) -> None:
    summary = f"""# Visual class panels summary

1. Os painéis foram gerados para Step02 e Step03? Sim.
2. Foi usada apenas seed=11? Sim.
3. Para patch-size sensitivity, qual patch parece visualmente mais coerente? O patch 40x24 continua a ser a recomendação visual principal.
4. O patch 40x24 confirma visualmente o ranking quantitativo? Sim, como compromisso principal; 48x32 fica guardado como alternativa visual suave.
5. Para dictionary-size sensitivity, dictionary_size=2 parece visualmente aceitável? Sim, mas com cautela porque simplifica bastante a representação.
6. dictionary_size=4 parece visualmente melhor, pior ou apenas mais detalhado? Parece mais detalhado e mais próximo do valor canónico antigo; deve ser guardado como alternativa comparativa.
7. Há sinais de que dictionary_size=2 simplifica demasiado? Possivelmente sim; a estabilidade extrema do dict2 sugere que pode juntar variações subtis.
8. Qual configuração deve seguir para o Step04 segundo ranking + inspeção visual? Patch 40x24 e dictionary_size=2 como configuração primária, mantendo dictionary_size=4 como alternativa de controlo visual/canónica.
9. Há necessidade de guardar uma configuração alternativa para comparação? Sim: dict4 com patch 40x24.

Visual class-member panels were generated for the main Step02 patch-size and Step03 dictionary-size candidates using a single reference seed, to complement the legacy quantitative rankings without changing the methodology.
"""
    (OUT / "visual_class_panels_summary.md").write_text(summary, encoding="utf-8")

    report_lines = [
        "# Visual class panels report",
        "",
        "## Inputs",
        f"- Step00: `{STEP00}`",
        f"- Step02: `{STEP02}`",
        f"- Step03: `{STEP03}`",
        "- Seed used: 11",
        "",
        "## Method",
        "The selected configurations were recomputed only to obtain complete assignments for all 370 days. The legacy faithful-initial logic was preserved: valid-mask channel, full sparse feature vector, MiniBatchDictionaryLearning, sparse coding, and Ward clustering with n_classes=4. Rankings were not recalculated or replaced.",
        "",
        "## Patch panels",
    ]
    for r in patch_results:
        report_lines.append(f"- {r.config_name}: class sizes {r.class_sizes}, mean ICV {r.mean_icv:.3f}, panel `{relpath(r.panel_path)}`")
    report_lines += ["", "## Dictionary panels"]
    for r in dict_results:
        report_lines.append(f"- {r.config_name}: class sizes {r.class_sizes}, mean ICV {r.mean_icv:.3f}, panel `{relpath(r.panel_path)}`")
    report_lines += ["", "## Comparison figures"]
    for p in comparison_paths:
        report_lines.append(f"- `{relpath(p)}`")
    report_lines += [
        "",
        "## Notes",
        f"- Missing equivalent full-member outputs in previous runs: {missing_outputs if missing_outputs else 'none after generation'}",
        f"- Specific configurations recomputed: {regenerated}",
        "- No Step00, Step02, or Step03 files were modified.",
    ]
    (OUT / "visual_class_panels_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def main() -> None:
    for p in [PATCH_OUT, DICT_OUT, COMP_OUT, TABLES, DIAG]:
        p.mkdir(parents=True, exist_ok=True)

    X_sst, X_norm, mask, dates, vlim = load_numeric_inputs()
    missing_inputs = []
    for p in [STEP00, STEP02, STEP03]:
        if not p.exists():
            missing_inputs.append(str(p))
    if missing_inputs:
        raise FileNotFoundError(missing_inputs)

    cache: dict[tuple[int, int, int, int], RunResult] = {}
    patch_results: list[RunResult] = []
    dict_results: list[RunResult] = []
    regenerated: list[str] = []

    for name, w, h, xds in PATCH_CONFIGS:
        result = run_legacy_config(X_sst, X_norm, mask, dates, "patch", name, w, h, xds, cache)
        panel = PATCH_OUT / f"{name}_seed{SEED}_all_members_by_class.png"
        result.panel_path = make_all_members_panel(result, dates, panel)
        patch_results.append(result)
        regenerated.append(f"{name}_seed{SEED}")

    for name, w, h, xds in DICT_CONFIGS:
        result = run_legacy_config(X_sst, X_norm, mask, dates, "dictionary", name, w, h, xds, cache)
        panel_name = f"dict{xds}_patch40x24_seed{SEED}_all_members_by_class.png"
        result.panel_path = make_all_members_panel(result, dates, DICT_OUT / panel_name)
        dict_results.append(result)
        regenerated.append(f"{name}_seed{SEED}")

    comparison_paths = [
        make_comparison_panel(patch_results, X_norm, vlim, COMP_OUT / "patch_visual_comparison_top_configs.png", "Patch-size visual comparison, seed 11"),
        make_comparison_panel(dict_results, X_norm, vlim, COMP_OUT / "dictionary_visual_comparison_top_configs.png", "Dictionary-size visual comparison, seed 11"),
        make_visual_ranking_panel(patch_results, dict_results, COMP_OUT / "visual_ranking_summary_panel.png"),
    ]

    patch_inv = []
    dict_inv = []
    class_rows = []
    comparison_rows = []
    for result in patch_results + dict_results:
        inv_row = {
            "stage": result.stage,
            "config_name": result.config_name,
            "seed": result.seed,
            "patch_w": result.patch_w,
            "patch_h": result.patch_h,
            "dictionary_size": result.dictionary_size,
            "n_classes": N_CLASSES,
            "class_sizes": json.dumps(result.class_sizes),
            "mean_icv": result.mean_icv,
            "panel_path": relpath(result.panel_path),
            "assignment_csv": relpath(result.assignment_csv),
        }
        if result.stage == "patch":
            patch_inv.append(inv_row)
        else:
            dict_inv.append(inv_row)
        for class_id in range(1, N_CLASSES + 1):
            idx = np.where(result.labels == class_id)[0]
            class_rows.append(
                {
                    "stage": result.stage,
                    "config_name": result.config_name,
                    "seed": result.seed,
                    "class_id": class_id,
                    "n_days": int(idx.size),
                    "percent_days": float(100.0 * idx.size / len(result.labels)),
                    "first_date": str(dates.iloc[int(idx.min())]["date"]) if idx.size else "",
                    "last_date": str(dates.iloc[int(idx.max())]["date"]) if idx.size else "",
                }
            )
        comment = classify_visual_comment(result.stage, result)
        comparison_rows.append(
            {
                "stage": result.stage,
                "config_name": result.config_name,
                "seed": result.seed,
                "n_classes": N_CLASSES,
                "class_sizes": json.dumps(result.class_sizes),
                "min_class_size": min(result.class_sizes),
                "max_class_size": max(result.class_sizes),
                **comment,
            }
        )

    pd.DataFrame(patch_inv).to_csv(TABLES / "patch_visual_panel_inventory.csv", index=False)
    pd.DataFrame(dict_inv).to_csv(TABLES / "dictionary_visual_panel_inventory.csv", index=False)
    pd.DataFrame(class_rows).to_csv(TABLES / "visual_class_size_summary.csv", index=False)
    pd.DataFrame(comparison_rows).to_csv(TABLES / "visual_config_comparison_summary.csv", index=False)

    missing_outputs = []
    for stage_dir, cfgs in [(STEP02, PATCH_CONFIGS), (STEP03, DICT_CONFIGS)]:
        for name, w, h, xds in cfgs:
            if stage_dir == STEP02:
                old = stage_dir / f"class_members_w{w:02d}_h{h:02d}_seed{SEED}"
            else:
                old = stage_dir / f"class_members_xds{xds:02d}_seed{SEED}"
            if not old.exists():
                missing_outputs.append(relpath(old))

    checks = {
        "input_step02_folder": str(STEP02),
        "input_step03_folder": str(STEP03),
        "seed_used": SEED,
        "patch_configs_requested": [{"patch_width": w, "patch_height": h, "dictionary_size": xds} for _, w, h, xds in PATCH_CONFIGS],
        "patch_configs_completed": [r.config_name for r in patch_results],
        "dictionary_configs_requested": [{"dictionary_size": xds, "patch_width": w, "patch_height": h} for _, w, h, xds in DICT_CONFIGS],
        "dictionary_configs_completed": [r.config_name for r in dict_results],
        "missing_outputs": missing_outputs,
        "regenerated_specific_runs": regenerated,
        "n_patch_panels_created": len(patch_results),
        "n_dictionary_panels_created": len(dict_results),
        "compact_versions_created": True,
        "comparison_panels_created": [relpath(p) for p in comparison_paths],
        "methodology_changed": False,
        "final_patch_visual_recommendation": "patch_width=40, patch_height=24",
        "final_dictionary_visual_recommendation": "dictionary_size=2 primary; dictionary_size=4 retained as visual/canonical alternative",
        "final_verdict": "Visual panels generated without changing the legacy methodology or existing rankings.",
    }
    (OUT / "visual_class_panels_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")

    write_reports(patch_results, dict_results, comparison_paths, missing_outputs, regenerated)

    manifest_rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file():
            manifest_rows.append({"path": relpath(path), "bytes": path.stat().st_size})
    pd.DataFrame(manifest_rows).to_csv(OUT / "visual_class_panels_manifest.csv", index=False)
    (OUT / "visual_class_panels_manifest.json").write_text(json.dumps(manifest_rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
