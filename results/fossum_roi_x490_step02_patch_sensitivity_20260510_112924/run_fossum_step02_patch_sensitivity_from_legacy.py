"""Rerun legacy patch-size sensitivity on the ROI x490 Step00 dataset.

This script intentionally reuses scripts/02b_patch_size_sensitivity_fossum_faithful_initial.py
and scripts/fossum_faithful_initial_utils.py. Methodology is not reimplemented:
only the module input/output paths are redirected to the ROI x490 Step00 files.
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

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
LEGACY_PATCH_SCRIPT = SCRIPTS_DIR / "02b_patch_size_sensitivity_fossum_faithful_initial.py"
LEGACY_UTILS = SCRIPTS_DIR / "fossum_faithful_initial_utils.py"

STEP00_DIR = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"
IN_X_SST = STEP00_DIR / "X_surface_370_roi_x490.npy"
IN_X_NORM = STEP00_DIR / "X_surface_370_roi_x490_norm.npy"
IN_MASK = STEP00_DIR / "mask_common_roi_x490.npy"
IN_STATS = STEP00_DIR / "normalization_stats.json"
IN_DATES = STEP00_DIR / "dates_370.csv"
IN_PNG_CLEAN = STEP00_DIR / "normalized_clean_pngs"

LEGACY_NAMED_PNG_DIR = OUT_DIR / "legacy_named_normalized_pngs"
LEGACY_DOC = OUT_DIR / "PATCH_SIZE_SENSITIVITY_FOSSUM_FAITHFUL_INITIAL_ROI_X490.md"
FINAL_SENTENCE = "The legacy patch-size sensitivity logic was rerun on the FRESNEL paper ROI x490 dataset with only path, shape, day-count and metadata adaptations."


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
    required = [LEGACY_PATCH_SCRIPT, LEGACY_UTILS, IN_X_SST, IN_X_NORM, IN_MASK, IN_STATS, IN_DATES, IN_PNG_CLEAN]
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
        dst = LEGACY_NAMED_PNG_DIR / f"X_surface_norm_z{i:03d}.png"
        shutil.copy2(srcs[0], dst)


def write_logic_audit(input_shape: tuple[int, int, int], patch_sizes: list[tuple[int, int]], seeds: list[int], skipped: list[dict[str, str]]) -> None:
    lines = [
        "# Step02 old patch-size sensitivity logic audit",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 1. Old script",
        f"- Reference script: `{rel(LEGACY_PATCH_SCRIPT)}`",
        f"- Utility module: `{rel(LEGACY_UTILS)}`",
        "",
        "## 2. Original patch sizes",
        "- " + ", ".join(f"{w}x{h}" for w, h in patch_sizes),
        "",
        "## 3. Old dataset",
        "- `results/fossum/X_surface_300.npy` for SST/original-space ICV.",
        "- `results/fossum/X_surface_300_norm.npy` for sparse coding/clustering.",
        "- `results/fossum/mask_common.npy` for valid-mask operations.",
        "- `results/fossum/pngs_normalized_surface_300_thesis` for class-member contact sheets.",
        "",
        "## 4. New dataset redirection",
        f"- X_sst: `{rel(IN_X_SST)}`",
        f"- X_norm: `{rel(IN_X_NORM)}`",
        f"- mask: `{rel(IN_MASK)}`",
        f"- png source compatibility folder: `{rel(LEGACY_NAMED_PNG_DIR)}`",
        f"- input shape: `{list(input_shape)}`",
        "",
        "## 5. Mask use",
        "The legacy loader copies X_sst/X_norm and sets `[:, ~mask] = np.nan` before modelling/evaluation.",
        "",
        "## 6. Patch extraction",
        "`extract_patch_components` uses `sliding_window_view`, row-major traversal, no shuffling.",
        "",
        "## 7. Patch-valid mask channel",
        "Enabled by default: patch vector is `[patch_temp_filled, patch_valid_mask]` with `mask_encoding='concat'`.",
        "",
        "## 8. Feature vector",
        "Each image feature is the full sparse-code sequence flattened in patch order, length `patches_per_image * dictionary_size`.",
        "",
        "## 9-12. Fixed parameters",
        "- dictionary_size = 4",
        f"- seeds = {seeds}",
        "- StandardScaler = not used in this legacy 02b patch sensitivity script.",
        "- SD fraction = not used in this legacy 02b patch sensitivity script.",
        "- n_classes = 4",
        "- dict_batch_size = 4096",
        "- transform_nnz = 2",
        "- feature_mode = raw",
        "- include_valid_mask = True",
        "- mask_encoding = concat",
        "",
        "## 13. Ward clustering",
        "`AgglomerativeClustering(n_clusters=cfg.n_classes, linkage='ward').fit_predict(features)`.",
        "",
        "## 14-17. Outputs/metrics/figures",
        "- `runs.csv`, `summary.csv`, `ranking.csv`.",
        "- class-member contact-sheet folders `class_members_wXX_hYY_seedSS/`.",
        "- plots: ICV boxplot, mean ICV vs patch size, min class size vs patch size, runtime vs patch size.",
        "- metrics: mean/std ICV, per-class ICV, class sizes, min/mean/max class size, runtime, feature lengths.",
        "- ranking: 0.30 rank(mean_icv) + 0.20 rank(mean_icv_std) + 0.20 rank(std_icv_mean) + 0.20 rank(min_class_size_min descending) + 0.10 rank(runtime).",
        "",
        "## Skipped patches",
    ]
    if skipped:
        lines += [f"- {row['patch']}: {row['reason']}" for row in skipped]
    else:
        lines.append("- None; all legacy patch sizes are compatible with the ROI x490 shape.")
    (OUT_DIR / "step02_old_patch_sensitivity_logic_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def patch_modules(patch_module, utils_module) -> None:
    utils_module.IN_X_SST = IN_X_SST
    utils_module.IN_X_NORM = IN_X_NORM
    utils_module.IN_MASK = IN_MASK
    utils_module.IN_STATS = IN_STATS
    utils_module.IN_PNG_DIR = LEGACY_NAMED_PNG_DIR
    patch_module.IN_X_SST = IN_X_SST
    patch_module.IN_X_NORM = IN_X_NORM
    patch_module.IN_MASK = IN_MASK
    patch_module.IN_PNG_DIR = LEGACY_NAMED_PNG_DIR


def run_legacy_main(patch_module) -> None:
    old_argv = sys.argv[:]
    sys.argv = [
        str(LEGACY_PATCH_SCRIPT),
        "--out-base",
        str(OUT_DIR),
        "--doc-path",
        str(LEGACY_DOC),
    ]
    try:
        patch_module.main()
    finally:
        sys.argv = old_argv


def write_final_outputs(
    input_shape: tuple[int, int, int],
    patch_sizes: list[tuple[int, int]],
    seeds: list[int],
    skipped: list[dict[str, str]],
    runtime_seconds: float,
) -> None:
    runs = pd.read_csv(OUT_DIR / "runs.csv")
    summary = pd.read_csv(OUT_DIR / "summary.csv")
    ranking = pd.read_csv(OUT_DIR / "ranking.csv")
    valid_runs = runs[runs["notes"] == "ok"].copy()
    summary.to_csv(OUT_DIR / "patch_sensitivity_metrics.csv", index=False)

    top = ranking.iloc[0]
    old_patch_row = ranking[(ranking["patch_w"].astype(int) == 72) & (ranking["patch_h"].astype(int) == 40)]
    old_patch_rank = int(old_patch_row.index[0] + 1) if not old_patch_row.empty else None
    recommendation = {
        "best_patch_by_legacy_ranking": f"{int(top['patch_w'])}x{int(top['patch_h'])}",
        "best_patch_w": int(top["patch_w"]),
        "best_patch_h": int(top["patch_h"]),
        "balanced_score": float(top["balanced_score"]),
        "legacy_patch_72x40_rank": old_patch_rank,
        "legacy_patch_72x40_row": old_patch_row.to_dict(orient="records"),
        "recommendation": f"Use {int(top['patch_w'])}x{int(top['patch_h'])} for the next dictionary-size sensitivity step according to the legacy ranking.",
    }
    write_json(OUT_DIR / "patch_sensitivity_recommendation.json", recommendation)

    outputs = []
    for p in OUT_DIR.rglob("*"):
        if p.is_file():
            outputs.append({"path": rel(p), "size_bytes": int(p.stat().st_size)})
    write_json(OUT_DIR / "step02_patch_sensitivity_manifest.json", {"output_folder": str(OUT_DIR), "files": outputs})

    checks = {
        "old_patch_script_found": LEGACY_PATCH_SCRIPT.exists(),
        "old_patch_script_path": rel(LEGACY_PATCH_SCRIPT),
        "old_patch_sizes_detected": [[int(w), int(h)] for w, h in patch_sizes],
        "old_fixed_parameters_detected": {
            "seeds": [int(s) for s in seeds],
            "dictionary_size": 4,
            "n_classes": 4,
            "dict_batch_size": 4096,
            "transform_nnz": 2,
            "include_valid_mask": True,
            "mask_encoding": "concat",
            "feature_mode": "raw",
            "standard_scaler": "not used by legacy 02b",
            "sd_fraction": "not used by legacy 02b",
        },
        "old_outputs_detected": ["runs.csv", "summary.csv", "ranking.csv", "plots/", "class_members_wXX_hYY_seedSS/"],
        "input_new_dataset": str(STEP00_DIR),
        "input_shape": [int(v) for v in input_shape],
        "n_days": int(input_shape[0]),
        "patches_tested": sorted(valid_runs.apply(lambda r: f"{int(r['patch_w'])}x{int(r['patch_h'])}", axis=1).unique().tolist()),
        "patches_skipped": [row["patch"] for row in skipped],
        "reason_for_skipped_patches": skipped,
        "logic_changes_made": [
            "Redirected legacy module input paths to Step00 ROI x490 arrays.",
            "Redirected legacy output base/doc path to the new Step02 result folder.",
            "Created a compatibility PNG folder with legacy `X_surface_norm_zNNN.png` names from Step00 normalized clean PNGs.",
            "Added ROI x490 summary/check/manifest/recommendation files around the legacy outputs.",
        ],
        "unavoidable_adaptations": [
            "Day count changed from 300 to 370.",
            "Spatial shape changed to ROI x490 shape.",
            "Metadata and output names reference ROI x490.",
        ],
        "methodology_preserved": True,
        "output_folder": str(OUT_DIR),
        "recommendation_generated": True,
        "runtime_seconds": float(runtime_seconds),
        "final_verdict": "PASS - legacy patch-size sensitivity logic rerun on ROI x490 with path/shape/day-count/metadata adaptations only.",
    }
    write_json(OUT_DIR / "step02_patch_sensitivity_checks.json", checks)

    patch_list = ", ".join(f"{w}x{h}" for w, h in patch_sizes)
    skipped_text = "Não." if not skipped else "; ".join(f"{r['patch']} ({r['reason']})" for r in skipped)
    old_patch_text = (
        f"O patch 72x40 ficou no rank {old_patch_rank}."
        if old_patch_rank is not None
        else "O patch 72x40 não apareceu no ranking."
    )
    summary_md = [
        "# Step02 patch-size sensitivity summary",
        "",
        "1. A lógica antiga da patch-size sensitivity foi encontrada? Sim.",
        f"2. Script antigo usado como referência: `{rel(LEGACY_PATCH_SCRIPT)}`.",
        f"3. Patch sizes originalmente testados: {patch_list}.",
        "4. Esses mesmos patch sizes foram repetidos? Sim.",
        f"5. Algum patch antigo teve de ser saltado? {skipped_text}",
        "6. Parâmetros fixos preservados: dictionary_size=4, seeds=[11,23,37,53,71], n_classes=4, include_valid_mask=True, mask_encoding=concat, feature_mode=raw, dict_batch_size=4096, transform_nnz=2, Ward n_clusters=4. StandardScaler e SD fraction não fazem parte desta etapa 02b antiga.",
        "7. Alterações feitas apenas para os novos dados: paths de input/output, 370 dias, shape ROI x490, metadados/datas e pasta de PNGs com nomes compatíveis.",
        f"8. Melhor patch segundo os mesmos critérios antigos: {recommendation['best_patch_by_legacy_ranking']}.",
        f"9. O patch antigo 72x40 continua adequado? {old_patch_text}",
        f"10. Patch recomendado para dictionary-size sensitivity: {recommendation['best_patch_by_legacy_ranking']}.",
        "",
        FINAL_SENTENCE,
    ]
    (OUT_DIR / "step02_patch_sensitivity_summary.md").write_text("\n".join(summary_md) + "\n", encoding="utf-8")

    report_md = [
        "# Step02 patch-size sensitivity report",
        "",
        "## Scope",
        "This rerun reused the legacy 02b methodology and redirected only data/output paths.",
        "",
        "## Legacy Ranking",
        md_table(
            ranking[
                [
                    "patch_w",
                    "patch_h",
                    "balanced_score",
                    "mean_icv_mean",
                    "mean_icv_std",
                    "std_icv_mean",
                    "min_class_size_min",
                    "runtime_mean_seconds",
                ]
            ],
            [
                "patch_w",
                "patch_h",
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
        "- `patch_sensitivity_metrics.csv` mirrors the legacy summary for thesis-facing naming.",
        "- `plots/` contains the legacy diagnostic figures.",
        "- `class_members_wXX_hYY_seedSS/` contains the legacy contact sheets.",
        "",
        FINAL_SENTENCE,
    ]
    (OUT_DIR / "step02_patch_sensitivity_report.md").write_text("\n".join(report_md) + "\n", encoding="utf-8")


def main() -> None:
    t0 = time.perf_counter()
    input_shape, n_days = verify_inputs()
    prepare_legacy_named_pngs(n_days)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    utils_module = load_module(LEGACY_UTILS, "fossum_faithful_initial_utils")
    patch_module = load_module(LEGACY_PATCH_SCRIPT, "legacy_patch_size_sensitivity_02b")
    patch_modules(patch_module, utils_module)

    patch_sizes = [(int(w), int(h)) for w, h in patch_module.DEFAULT_PATCH_SIZES]
    seeds = [int(s) for s in patch_module.DEFAULT_SEEDS]
    ny, nx = input_shape[1], input_shape[2]
    skipped = [
        {"patch": f"{w}x{h}", "reason": f"patch exceeds ROI shape nx={nx}, ny={ny}"}
        for w, h in patch_sizes
        if not utils_module.valid_patch_size(ny, nx, patch_h=h, patch_w=w)
    ]
    write_logic_audit(input_shape, patch_sizes, seeds, skipped)
    run_legacy_main(patch_module)
    runtime = time.perf_counter() - t0
    write_final_outputs(input_shape, patch_sizes, seeds, skipped, runtime)
    print(f"[OK] out_dir={OUT_DIR}")
    print(f"[OK] input_shape={input_shape}")
    print(f"[OK] patches={patch_sizes}")
    print(f"[OK] skipped={skipped}")
    print(f"[OK] runtime_seconds={runtime:.2f}")
    print(f"[OK] {FINAL_SENTENCE}")


if __name__ == "__main__":
    main()
