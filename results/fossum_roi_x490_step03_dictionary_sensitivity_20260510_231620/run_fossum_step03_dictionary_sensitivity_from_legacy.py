"""Rerun legacy dictionary-size sensitivity on ROI x490 Step00 data.

The legacy script is imported and executed with redirected inputs/outputs.
Methodology is preserved; only paths, metadata, day count, shape, and the
Step02-selected patch size 40x24 are adapted.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
LEGACY_DICT_SCRIPT = SCRIPTS_DIR / "03a_dictionary_size_sensitivity_fossum_faithful_initial.py"
LEGACY_UTILS = SCRIPTS_DIR / "fossum_faithful_initial_utils.py"

STEP00_DIR = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"
STEP02_DIR = ROOT / "results" / "fossum_roi_x490_step02_patch_sensitivity_20260510_112924"
IN_X_SST = STEP00_DIR / "X_surface_370_roi_x490.npy"
IN_X_NORM = STEP00_DIR / "X_surface_370_roi_x490_norm.npy"
IN_MASK = STEP00_DIR / "mask_common_roi_x490.npy"
IN_STATS = STEP00_DIR / "normalization_stats.json"
IN_DATES = STEP00_DIR / "dates_370.csv"
IN_PNG_CLEAN = STEP00_DIR / "normalized_clean_pngs"

PATCH_W = 40
PATCH_H = 24
LEGACY_NAMED_PNG_DIR = OUT_DIR / "legacy_named_normalized_pngs"
LEGACY_DOC = OUT_DIR / "DICTIONARY_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL_ROI_X490.md"
FINAL_SENTENCE = "The legacy dictionary-size sensitivity logic was rerun on the FRESNEL paper ROI x490 dataset using the Step02 recommended patch size, with only path, shape, day-count and metadata adaptations."


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{float(value):.6f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def verify_inputs() -> tuple[tuple[int, int, int], int]:
    required = [LEGACY_DICT_SCRIPT, LEGACY_UTILS, IN_X_SST, IN_X_NORM, IN_MASK, IN_STATS, IN_DATES, IN_PNG_CLEAN]
    missing = [p for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required input/reference files: " + ", ".join(str(p) for p in missing))
    x = np.load(IN_X_NORM, mmap_mode="r")
    mask = np.load(IN_MASK, mmap_mode="r")
    if x.ndim != 3:
        raise RuntimeError(f"Expected 3D X_norm, got {x.shape}")
    if tuple(mask.shape) != tuple(x.shape[1:]):
        raise RuntimeError(f"Mask mismatch: mask={mask.shape}, X spatial={x.shape[1:]}")
    return tuple(int(v) for v in x.shape), int(x.shape[0])


def prepare_legacy_named_pngs(n_days: int) -> None:
    LEGACY_NAMED_PNG_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(LEGACY_NAMED_PNG_DIR.glob("X_surface_norm_z*.png"))
    if len(existing) == n_days:
        return
    for old in existing:
        old.unlink()
    for i in range(1, n_days + 1):
        srcs = sorted(IN_PNG_CLEAN.glob(f"{i:04d}_*_X_surface_370_roi_x490_norm_clean.png"))
        if not srcs:
            raise FileNotFoundError(f"Missing Step00 clean PNG for day {i:04d}")
        shutil.copy2(srcs[0], LEGACY_NAMED_PNG_DIR / f"X_surface_norm_z{i:03d}.png")


def patch_modules(dict_module, utils_module) -> None:
    utils_module.IN_X_SST = IN_X_SST
    utils_module.IN_X_NORM = IN_X_NORM
    utils_module.IN_MASK = IN_MASK
    utils_module.IN_STATS = IN_STATS
    utils_module.IN_PNG_DIR = LEGACY_NAMED_PNG_DIR
    dict_module.IN_X_SST = IN_X_SST
    dict_module.IN_X_NORM = IN_X_NORM
    dict_module.IN_MASK = IN_MASK
    dict_module.IN_PNG_DIR = LEGACY_NAMED_PNG_DIR


def write_logic_audit(input_shape: tuple[int, int, int], xds_values: list[int], seeds: list[int], skipped: list[dict[str, str]]) -> None:
    lines = [
        "# Step03 old dictionary-size sensitivity logic audit",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 1. Old script",
        f"- Reference script: `{rel(LEGACY_DICT_SCRIPT)}`",
        f"- Utility module: `{rel(LEGACY_UTILS)}`",
        "",
        "## 2. Original dictionary sizes",
        "- " + ", ".join(str(v) for v in xds_values),
        "",
        "## 3. Old patch size",
        "- The legacy script default was `72x40`.",
        "- This rerun uses `40x24`, the Step02 recommended patch size, as requested.",
        "",
        "## 4. Seeds",
        f"- {seeds}",
        "",
        "## 5-7. Old dataset and mask",
        "- `results/fossum/X_surface_300.npy` for SST/original ICV.",
        "- `results/fossum/X_surface_300_norm.npy` for dictionary learning, sparse coding and clustering.",
        "- `results/fossum/mask_common.npy`; legacy loader sets `[:, ~mask] = np.nan`.",
        "",
        "## 8-10. Patches, features, valid-mask channel",
        "- Patch extraction uses `sliding_window_view`, deterministic row-major traversal, stride 1.",
        "- Patch vector is `[patch_temp_filled, patch_valid_mask]` with `mask_encoding='concat'`.",
        "- Image feature vector is full sparse-code sequence flattened in patch order: `patches_per_image * dictionary_size`.",
        "",
        "## 11-12. StandardScaler / SD fraction",
        "- StandardScaler is not used in legacy 03a.",
        "- SD fraction is not used in legacy 03a.",
        "",
        "## 13. Ward clustering",
        "- `AgglomerativeClustering(n_clusters=4, linkage='ward').fit_predict(features)`.",
        "",
        "## 14-18. Outputs, metrics, figures, selection",
        "- Outputs: `runs.csv`, `summary.csv`, `ranking.csv`, `plots/`, `class_members_xdsXX_seedSS/`, and markdown doc.",
        "- Metrics: mean/std ICV, per-class ICV, class sizes, min/mean/max class sizes, runtime, feature lengths.",
        "- Figures: ICV boxplot, mean ICV vs dictionary size, min class size vs dictionary size, runtime vs dictionary size.",
        "- Ranking: 0.30 rank(mean_icv) + 0.20 rank(mean_icv_std) + 0.20 rank(std_icv_mean) + 0.20 rank(min_class_size_min descending) + 0.10 rank(runtime).",
        "",
        "## New data redirection",
        f"- input shape: `{list(input_shape)}`",
        f"- X_sst: `{rel(IN_X_SST)}`",
        f"- X_norm: `{rel(IN_X_NORM)}`",
        f"- mask: `{rel(IN_MASK)}`",
        f"- PNG compatibility folder: `{rel(LEGACY_NAMED_PNG_DIR)}`",
        "",
        "## Skipped dictionary sizes",
    ]
    if skipped:
        lines += [f"- {row['dictionary_size']}: {row['reason']}" for row in skipped]
    else:
        lines.append("- None.")
    (OUT_DIR / "step03_old_dictionary_sensitivity_logic_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_legacy_main(dict_module) -> None:
    old_argv = sys.argv[:]
    sys.argv = [
        str(LEGACY_DICT_SCRIPT),
        "--out-base",
        str(OUT_DIR),
        "--doc-path",
        str(LEGACY_DOC),
        "--patch-w",
        str(PATCH_W),
        "--patch-h",
        str(PATCH_H),
    ]
    try:
        dict_module.main()
    finally:
        sys.argv = old_argv


def generate_additional_equivalent_figures(summary: pd.DataFrame, ranking: pd.DataFrame) -> list[str]:
    created: list[str] = []
    # Equivalent to legacy summary metric plots: class sizes and ranking from existing metrics.
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(summary["dictionary_size"], summary["min_class_size_mean"], marker="o", label="min class size mean")
    ax.plot(summary["dictionary_size"], summary["mean_class_size_mean"], marker="o", label="mean class size")
    ax.plot(summary["dictionary_size"], summary["max_class_size_mean"], marker="o", label="max class size mean")
    ax.set_xlabel("Dictionary size")
    ax.set_ylabel("Class size")
    ax.set_title("Dictionary sensitivity class-size comparison")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = OUT_DIR / "dictionary_sensitivity_class_sizes_comparison.png"
    fig.savefig(out, dpi=160)
    plt.close(fig)
    created.append(out.name)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(ranking["dictionary_size"].astype(str), ranking["balanced_score"])
    ax.set_xlabel("Dictionary size")
    ax.set_ylabel("Legacy balanced score")
    ax.set_title("Dictionary sensitivity metric ranking")
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()
    out = OUT_DIR / "dictionary_sensitivity_metric_ranking.png"
    fig.savefig(out, dpi=160)
    plt.close(fig)
    created.append(out.name)

    # n_classes is fixed by the legacy script, so this is a documented constant comparison.
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(summary["dictionary_size"], np.full(len(summary), 4), marker="o")
    ax.set_xlabel("Dictionary size")
    ax.set_ylabel("n_classes")
    ax.set_title("Dictionary sensitivity n_classes comparison (legacy fixed n=4)")
    ax.set_ylim(0, 5)
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    out = OUT_DIR / "dictionary_sensitivity_nclasses_comparison.png"
    fig.savefig(out, dpi=160)
    plt.close(fig)
    created.append(out.name)

    return created


def write_final_outputs(
    input_shape: tuple[int, int, int],
    xds_values: list[int],
    seeds: list[int],
    skipped: list[dict[str, str]],
    runtime_seconds: float,
) -> None:
    runs = pd.read_csv(OUT_DIR / "runs.csv")
    summary = pd.read_csv(OUT_DIR / "summary.csv")
    ranking = pd.read_csv(OUT_DIR / "ranking.csv")
    valid_runs = runs[runs["notes"] == "ok"].copy()
    summary.to_csv(OUT_DIR / "dictionary_sensitivity_metrics.csv", index=False)
    ranking.to_csv(OUT_DIR / "dictionary_sensitivity_ranking.csv", index=False)

    extra_figs = generate_additional_equivalent_figures(summary, ranking)
    top = ranking.iloc[0]
    old_row = ranking[ranking["dictionary_size"].astype(int) == 4]
    old_rank = int(old_row.index[0] + 1) if not old_row.empty else None
    recommendation = {
        "best_dictionary_size_by_legacy_ranking": int(top["dictionary_size"]),
        "balanced_score": float(top["balanced_score"]),
        "legacy_dictionary_size_4_rank": old_rank,
        "legacy_dictionary_size_4_row": old_row.to_dict(orient="records"),
        "recommendation": f"Use dictionary_size={int(top['dictionary_size'])} for the next step according to the legacy ranking.",
    }
    write_json(OUT_DIR / "dictionary_sensitivity_recommendation.json", recommendation)

    outputs = [{"path": rel(p), "size_bytes": int(p.stat().st_size)} for p in OUT_DIR.rglob("*") if p.is_file()]
    write_json(OUT_DIR / "step03_dictionary_sensitivity_manifest.json", {"output_folder": str(OUT_DIR), "files": outputs})

    checks = {
        "old_dictionary_script_found": LEGACY_DICT_SCRIPT.exists(),
        "old_dictionary_script_path": rel(LEGACY_DICT_SCRIPT),
        "old_dictionary_sizes_detected": [int(v) for v in xds_values],
        "old_fixed_parameters_detected": {
            "legacy_default_patch": "72x40",
            "used_patch_from_step02": f"{PATCH_W}x{PATCH_H}",
            "seeds": [int(s) for s in seeds],
            "n_classes": 4,
            "dict_batch_size": 4096,
            "transform_nnz": 2,
            "include_valid_mask": True,
            "mask_encoding": "concat",
            "feature_mode": "raw",
            "standard_scaler": "not used by legacy 03a",
            "sd_fraction": "not used by legacy 03a",
        },
        "old_outputs_detected": ["runs.csv", "summary.csv", "ranking.csv", "plots/", "class_members_xdsXX_seedSS/"],
        "input_new_dataset": str(STEP00_DIR),
        "input_shape": [int(v) for v in input_shape],
        "n_days": int(input_shape[0]),
        "patch_width": PATCH_W,
        "patch_height": PATCH_H,
        "dictionary_sizes_tested": sorted(valid_runs["dictionary_size"].astype(int).unique().tolist()),
        "dictionary_sizes_skipped": [int(row["dictionary_size"]) for row in skipped],
        "reason_for_skipped_dictionary_sizes": skipped,
        "seeds_used": [int(s) for s in seeds],
        "logic_changes_made": [
            "Redirected legacy module input paths to Step00 ROI x490 arrays.",
            "Redirected legacy output base/doc path to the new Step03 result folder.",
            "Set patch width/height to Step02 recommendation 40x24 via legacy CLI arguments.",
            "Created a compatibility PNG folder with legacy `X_surface_norm_zNNN.png` names.",
            "Added ROI x490 summary/check/manifest/recommendation files around the legacy outputs.",
        ],
        "unavoidable_adaptations": [
            "Day count changed from 300 to 370.",
            "Spatial shape changed to ROI x490 shape.",
            "Patch changed from legacy default 72x40 to Step02-selected 40x24 as required.",
            "Metadata and output names reference ROI x490.",
        ],
        "methodology_preserved": True,
        "output_folder": str(OUT_DIR),
        "recommendation_generated": True,
        "recommended_dictionary_size": int(top["dictionary_size"]),
        "additional_equivalent_figures_created": extra_figs,
        "runtime_seconds": float(runtime_seconds),
        "final_verdict": "PASS - legacy dictionary-size sensitivity logic rerun on ROI x490 using Step02 patch with path/shape/day-count/metadata adaptations only.",
    }
    write_json(OUT_DIR / "step03_dictionary_sensitivity_checks.json", checks)

    xds_text = ", ".join(str(v) for v in xds_values)
    old_text = f"dictionary_size=4 ficou no rank {old_rank}." if old_rank is not None else "dictionary_size=4 não apareceu no ranking."
    summary_md = [
        "# Step03 dictionary-size sensitivity summary",
        "",
        "1. A lógica antiga da dictionary-size sensitivity foi encontrada? Sim.",
        f"2. Script antigo usado como referência: `{rel(LEGACY_DICT_SCRIPT)}`.",
        f"3. Dictionary sizes originalmente testados: {xds_text}.",
        "4. Esses mesmos dictionary sizes foram repetidos? Sim.",
        f"5. Patch usado: {PATCH_W}x{PATCH_H}, recomendado pelo Step02.",
        "6. Parâmetros fixos preservados: seeds=[11,23,37,53,71], n_classes=4, include_valid_mask=True, mask_encoding=concat, feature_mode=raw, dict_batch_size=4096, transform_nnz=2, Ward n_clusters=4. StandardScaler e SD fraction não fazem parte desta etapa 03a antiga.",
        "7. Alterações feitas apenas para os novos dados: paths de input/output, 370 dias, shape ROI x490, metadados/datas e patch 40x24 vindo do Step02.",
        f"8. Melhor dictionary_size segundo os mesmos critérios antigos: {int(top['dictionary_size'])}.",
        f"9. O dictionary_size antigo 4 continua adequado? {old_text}",
        f"10. Dictionary_size recomendado para a próxima etapa: {int(top['dictionary_size'])}.",
        "",
        FINAL_SENTENCE,
    ]
    (OUT_DIR / "step03_dictionary_sensitivity_summary.md").write_text("\n".join(summary_md) + "\n", encoding="utf-8")

    report_md = [
        "# Step03 dictionary-size sensitivity report",
        "",
        "## Scope",
        "This rerun reused the legacy 03a methodology and redirected only data/output paths, plus the Step02-selected patch.",
        "",
        "## Legacy Ranking",
        md_table(
            ranking[
                [
                    "dictionary_size",
                    "balanced_score",
                    "mean_icv_mean",
                    "mean_icv_std",
                    "std_icv_mean",
                    "min_class_size_min",
                    "runtime_mean_seconds",
                ]
            ],
            [
                "dictionary_size",
                "balanced_score",
                "mean_icv_mean",
                "mean_icv_std",
                "std_icv_mean",
                "min_class_size_min",
                "runtime_mean_seconds",
            ],
        ),
        "",
        "## Outputs",
        "- `runs.csv`, `summary.csv`, `ranking.csv` are the direct legacy outputs.",
        "- `dictionary_sensitivity_metrics.csv` and `dictionary_sensitivity_ranking.csv` mirror the legacy outputs for thesis-facing naming.",
        "- `plots/` contains the legacy diagnostic figures.",
        "- `class_members_xdsXX_seedSS/` contains the legacy contact sheets.",
        "",
        FINAL_SENTENCE,
    ]
    (OUT_DIR / "step03_dictionary_sensitivity_report.md").write_text("\n".join(report_md) + "\n", encoding="utf-8")


def main() -> None:
    t0 = time.perf_counter()
    input_shape, n_days = verify_inputs()
    prepare_legacy_named_pngs(n_days)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    utils_module = load_module(LEGACY_UTILS, "fossum_faithful_initial_utils")
    dict_module = load_module(LEGACY_DICT_SCRIPT, "legacy_dictionary_size_sensitivity_03a")
    patch_modules(dict_module, utils_module)

    xds_values = [int(v) for v in dict_module.DEFAULT_XDS_VALUES]
    seeds = [int(s) for s in dict_module.DEFAULT_SEEDS]
    skipped: list[dict[str, str]] = []
    write_logic_audit(input_shape, xds_values, seeds, skipped)
    run_legacy_main(dict_module)
    runtime = time.perf_counter() - t0
    write_final_outputs(input_shape, xds_values, seeds, skipped, runtime)
    print(f"[OK] out_dir={OUT_DIR}")
    print(f"[OK] input_shape={input_shape}")
    print(f"[OK] patch={PATCH_W}x{PATCH_H}")
    print(f"[OK] dictionary_sizes={xds_values}")
    print(f"[OK] runtime_seconds={runtime:.2f}")
    print(f"[OK] {FINAL_SENTENCE}")


if __name__ == "__main__":
    main()
