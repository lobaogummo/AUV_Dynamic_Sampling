"""End-to-end orchestrator for the frozen faithful clustering working config.

This runner keeps the existing pipeline modular by invoking the current stage
scripts (`04a` and `06`) and then normalizing outputs into a single clean
directory tree per seed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

GLOBAL_STAGE_SCRIPT = SCRIPTS_DIR / "04a_separation_distance_probe_fossum_faithful_initial.py"
LOCAL_STAGE_SCRIPT = SCRIPTS_DIR / "06_class02_local_refinement_sd30.py"

DEFAULT_OUT_BASE = ROOT / "results" / "fossum" / "final_working_pipeline"
DEFAULT_RUN_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")
DEFAULT_OFFICIAL_SEEDS = [11, 23, 37, 53, 71]
DEFAULT_FRACTIONS = [0.30]
DEFAULT_RANKING_TARGET_CLASSES = 5
DEFAULT_LOCAL_K_VALUES = [2]

FROZEN_PATCH_W = 72
FROZEN_PATCH_H = 40
FROZEN_DICTIONARY_SIZE = 4
FROZEN_STANDARD_SCALER_ON = True
FROZEN_GLOBAL_TARGET_CLASSES = 5
FROZEN_OFFICIAL_SD_FRACTION = 0.30
FROZEN_LOCAL_CLASS_ID = 2


@dataclass
class StageOutcome:
    status: str
    output_dir: str | None = None
    error: str | None = None
    checks: Dict[str, bool] = field(default_factory=dict)
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class SeedOutcome:
    seed: int
    seed_dir: str
    global_stage: StageOutcome
    local_stage: StageOutcome


def log(msg: str) -> None:
    print(f"[faithful-e2e-runner] {msg}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run frozen faithful working config end-to-end: global SD30 clustering + local class_02 refinement."
    )
    p.add_argument("--out-base", type=Path, default=DEFAULT_OUT_BASE)
    p.add_argument("--run-tag", type=str, default=DEFAULT_RUN_TAG)

    seed_group = p.add_mutually_exclusive_group()
    seed_group.add_argument("--seed", type=int, default=None, help="Run one seed.")
    seed_group.add_argument("--seeds", type=int, nargs="+", default=None, help="Run explicit seed list.")

    p.add_argument("--fractions", type=float, nargs="*", default=None, help="SD fractions for stage 04a (default: 0.30).")
    p.add_argument("--ranking-target-classes", type=int, default=DEFAULT_RANKING_TARGET_CLASSES)
    p.add_argument("--enable-local-class02-refinement", dest="run_local_refinement", action="store_true")
    p.add_argument("--disable-local-class02-refinement", dest="run_local_refinement", action="store_false")
    p.set_defaults(run_local_refinement=True)
    p.add_argument("--local-k-values", type=int, nargs="+", default=DEFAULT_LOCAL_K_VALUES)
    p.add_argument("--no-pca", action="store_true", help="Pass --no-pca to both global and local stage scripts.")
    p.add_argument(
        "--use-fixed-dictionary",
        action="store_true",
        help="Use a pre-saved dictionary artifact for both global and local stages.",
    )
    p.add_argument(
        "--dictionary-path",
        type=Path,
        default=None,
        help="Path to dictionary artifact (.npz). If provided, fixed-dictionary mode is enabled.",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite an existing run-tag output directory.")
    return p.parse_args()


def first_existing_file(candidates: Sequence[Path]) -> Path | None:
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def first_existing_dir(candidates: Sequence[Path]) -> Path | None:
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    return None


def path_to_repo_or_abs(path: Path) -> str:
    rp = path.resolve()
    try:
        return rp.relative_to(ROOT).as_posix()
    except Exception:
        return str(rp)


def normalize_seeds(seed: int | None, seeds: Sequence[int] | None) -> List[int]:
    if seed is not None:
        out = [int(seed)]
    elif seeds:
        out = [int(s) for s in seeds]
    else:
        out = [int(s) for s in DEFAULT_OFFICIAL_SEEDS]

    seen = set()
    uniq: List[int] = []
    for s in out:
        if s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    return uniq


def validate_fractions(values: Sequence[float] | None) -> List[float]:
    candidates = DEFAULT_FRACTIONS if not values else values
    out: List[float] = []
    seen = set()
    for frac in candidates:
        f = float(frac)
        if f <= 0.0 or f >= 1.0:
            raise ValueError(f"Invalid fraction {f}. Expected values in (0, 1).")
        key = round(f, 12)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    out.sort()
    return out


def validate_local_k_values(values: Sequence[int]) -> List[int]:
    uniq = sorted(set(int(v) for v in values))
    if not uniq:
        raise ValueError("At least one --local-k-values entry is required.")
    if any(v < 2 for v in uniq):
        raise ValueError("--local-k-values must be >= 2.")
    if any(v > 3 for v in uniq):
        raise ValueError("Please keep local refinement controlled: max local k=3.")
    return uniq


def validate_required_inputs() -> Dict[str, str]:
    missing_script_paths = [p for p in [GLOBAL_STAGE_SCRIPT, LOCAL_STAGE_SCRIPT] if not p.exists()]
    if missing_script_paths:
        raise FileNotFoundError(
            "Missing required script(s): " + ", ".join(str(p.resolve()) for p in missing_script_paths)
        )

    x_sst = first_existing_file(
        [
            ROOT / "results" / "fossum" / "X_surface_300.npy",
            ROOT / "results" / "plots" / "X_surface_300.npy",
        ]
    )
    x_norm = first_existing_file(
        [
            ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
            ROOT / "results" / "plots" / "X_surface_300_norm.npy",
        ]
    )
    mask = first_existing_file(
        [
            ROOT / "results" / "fossum" / "mask_common.npy",
            ROOT / "results" / "plots" / "mask_common.npy",
        ]
    )
    png_dir = first_existing_dir(
        [
            ROOT / "results" / "fossum" / "pngs_normalized_surface_300_thesis",
            ROOT / "results" / "plots" / "pngs_normalized_surface_300_thesis",
        ]
    )
    missing_inputs: List[str] = []
    if x_sst is None:
        missing_inputs.append("X_surface_300.npy")
    if x_norm is None:
        missing_inputs.append("X_surface_300_norm.npy")
    if mask is None:
        missing_inputs.append("mask_common.npy")
    if png_dir is None:
        missing_inputs.append("pngs_normalized_surface_300_thesis/")
    if missing_inputs:
        raise FileNotFoundError(
            "Missing required dataset input(s): "
            + ", ".join(missing_inputs)
            + ". Checked under results/fossum and results/plots."
        )

    return {
        "global_script": str(GLOBAL_STAGE_SCRIPT.resolve()),
        "local_script": str(LOCAL_STAGE_SCRIPT.resolve()),
        "X_sst": str(x_sst.resolve()),
        "X_norm": str(x_norm.resolve()),
        "mask": str(mask.resolve()),
        "png_dir": str(png_dir.resolve()),
    }


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
        cleaned = line.rstrip("\n")
        print(cleaned)
        tail.append(cleaned)
        if len(tail) > 40:
            tail.pop(0)
    return_code = proc.wait()
    if return_code != 0:
        raise RuntimeError(
            f"Command failed for {label} with exit code {return_code}.\n"
            + "\n".join(tail[-15:])
        )


def copy_contents(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        dst_path = dst_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dst_path, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst_path)


def fraction_slug(frac: float) -> str:
    return f"sd_{int(round(frac * 100)):02d}pct"


def build_local_summary_row(runs_csv: Path, seed: int, global_dir: Path, run_dir_name: str) -> pd.DataFrame:
    df = pd.read_csv(runs_csv)
    if "sd_fraction_of_max" not in df.columns:
        raise RuntimeError(f"Unexpected runs.csv columns in {runs_csv}: {list(df.columns)}")

    mask = np.isclose(df["sd_fraction_of_max"].astype(float).to_numpy(), FROZEN_OFFICIAL_SD_FRACTION, atol=1e-9)
    if not np.any(mask):
        raise RuntimeError(
            f"Could not find SD fraction {FROZEN_OFFICIAL_SD_FRACTION:.2f} row in {runs_csv} for local refinement."
        )
    row = df.loc[mask].iloc[0].to_dict()
    row["seed"] = int(seed)
    row["run_dir"] = str(run_dir_name)
    row["output_dir"] = path_to_repo_or_abs(global_dir)
    out = pd.DataFrame([row])
    return out


def verify_global_artifacts(global_dir: Path, include_pca: bool) -> Dict[str, bool]:
    checks: Dict[str, bool] = {}
    checks["runs.csv"] = (global_dir / "runs.csv").exists()
    checks["ranking.csv"] = (global_dir / "ranking.csv").exists()
    checks["REPORT.md"] = (global_dir / "REPORT.md").exists()
    checks["dendrogram_cut.png"] = (global_dir / "dendrogram_cut.png").exists()
    checks["pca2d_classes.png"] = (global_dir / "pca2d_classes.png").exists() if include_pca else True
    checks["prototypes_panel.png"] = (global_dir / "prototypes_panel.png").exists()
    checks["prototype_class_XX.png"] = len(list(global_dir.glob("prototype_class_*.png"))) > 0
    checks["class_XX_members_list.csv"] = len(list(global_dir.glob("class_*_members_list.csv"))) > 0
    checks["class_XX_members_panel.png"] = len(list(global_dir.glob("class_*_members_panel.png"))) > 0
    checks["class_XX_pixel_std_map.png"] = len(list(global_dir.glob("class_*_pixel_std_map.png"))) > 0
    checks["class_XX_distance_to_prototype.csv"] = len(list(global_dir.glob("class_*_distance_to_prototype.csv"))) > 0
    checks["class_XX_closest_to_prototype_panel.png"] = len(
        list(global_dir.glob("class_*_closest_to_prototype_panel.png"))
    ) > 0
    checks["class_XX_farthest_from_prototype_panel.png"] = len(
        list(global_dir.glob("class_*_farthest_from_prototype_panel.png"))
    ) > 0
    checks["dendrogram_probe/tree_info.json"] = (global_dir / "dendrogram_probe" / "tree_info.json").exists()
    return checks


def verify_local_artifacts(local_dir: Path, k_values: Sequence[int], include_pca: bool) -> Dict[str, bool]:
    checks: Dict[str, bool] = {}
    checks["refined_class02_summary.csv"] = (local_dir / "refined_class02_summary.csv").exists()
    checks["refined_class02_subclass_metrics.csv"] = (local_dir / "refined_class02_subclass_metrics.csv").exists()
    checks["refined_class02_aggregate_by_k.csv"] = (local_dir / "refined_class02_aggregate_by_k.csv").exists()
    checks["COMPACT_REPORT.md"] = (local_dir / "COMPACT_REPORT.md").exists()
    checks["class02_local_dendrogram.png"] = (local_dir / "class02_local_dendrogram.png").exists()
    for k in k_values:
        k_dir = local_dir / f"k{k}"
        checks[f"k{k}/compact_report.md"] = (k_dir / "compact_report.md").exists()
        checks[f"k{k}/subclass_prototypes_panel.png"] = (k_dir / "subclass_prototypes_panel.png").exists()
        checks[f"k{k}/subclass_prototype_XX.png"] = len(list(k_dir.glob("subclass_prototype_*.png"))) > 0
        checks[f"k{k}/subclass_XX_members_list.csv"] = len(list(k_dir.glob("subclass_*_members_list.csv"))) > 0
        checks[f"k{k}/subclass_XX_members_panel.png"] = len(list(k_dir.glob("subclass_*_members_panel.png"))) > 0
        checks[f"k{k}/subclass_XX_pixel_std_map.png"] = len(list(k_dir.glob("subclass_*_pixel_std_map.png"))) > 0
        checks[f"k{k}/subclass_XX_distance_to_prototype.csv"] = len(
            list(k_dir.glob("subclass_*_distance_to_prototype.csv"))
        ) > 0
        checks[f"k{k}/subclass_XX_closest_to_prototype_panel.png"] = len(
            list(k_dir.glob("subclass_*_closest_to_prototype_panel.png"))
        ) > 0
        checks[f"k{k}/subclass_XX_farthest_from_prototype_panel.png"] = len(
            list(k_dir.glob("subclass_*_farthest_from_prototype_panel.png"))
        ) > 0
        pca_key = f"k{k}/class02_local_pca2d_subclasses.png"
        checks[pca_key] = (k_dir / "class02_local_pca2d_subclasses.png").exists() if include_pca else True
    return checks


def all_checks_pass(checks: Dict[str, bool]) -> bool:
    return all(bool(v) for v in checks.values())


def run_global_stage_for_seed(
    seed: int,
    seed_dir: Path,
    fractions: Sequence[float],
    ranking_target_classes: int,
    no_pca: bool,
    python_exe: str,
    tmp_root: Path,
    use_fixed_dictionary: bool,
    dictionary_path: Path | None,
) -> tuple[Path, Path]:
    label = f"global-seed{seed:02d}"
    global_dir = seed_dir / "global"
    tmp_out_base = tmp_root / f"seed{seed:02d}" / "global_stage_out"
    if tmp_out_base.exists():
        shutil.rmtree(tmp_out_base)
    tmp_out_base.mkdir(parents=True, exist_ok=True)

    global_stage_tag = f"official_sd30_seed{seed:02d}"
    cmd = [
        python_exe,
        str(GLOBAL_STAGE_SCRIPT.resolve()),
        "--out-base",
        str(tmp_out_base),
        "--run-tag",
        global_stage_tag,
        "--seed",
        str(seed),
        "--patch-w",
        str(FROZEN_PATCH_W),
        "--patch-h",
        str(FROZEN_PATCH_H),
        "--dictionary-size",
        str(FROZEN_DICTIONARY_SIZE),
        "--fractions",
        *[f"{frac:.12g}" for frac in fractions],
        "--ranking-target-classes",
        str(ranking_target_classes),
        "--apply-standard-scaler",
    ]
    if use_fixed_dictionary:
        assert dictionary_path is not None
        cmd.extend(["--use-fixed-dictionary", "--dictionary-path", str(dictionary_path)])
    if no_pca:
        cmd.append("--no-pca")
    run_command(cmd=cmd, label=label)

    run_dirs = sorted([p for p in tmp_out_base.iterdir() if p.is_dir()])
    if len(run_dirs) != 1:
        raise RuntimeError(f"Expected exactly one global run directory in {tmp_out_base}, found {len(run_dirs)}.")
    raw_run_dir = run_dirs[0]
    runs_csv = raw_run_dir / "runs.csv"
    ranking_csv = raw_run_dir / "ranking.csv"
    report_md = raw_run_dir / "REPORT.md"
    for required in [runs_csv, ranking_csv, report_md]:
        if not required.exists():
            raise FileNotFoundError(f"Missing expected global artifact: {required}")

    official_sd_dir = raw_run_dir / fraction_slug(FROZEN_OFFICIAL_SD_FRACTION)
    if not official_sd_dir.exists():
        raise FileNotFoundError(
            f"Missing official SD folder {official_sd_dir}. "
            f"Make sure --fractions includes {FROZEN_OFFICIAL_SD_FRACTION:.2f}."
        )

    global_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runs_csv, global_dir / "runs.csv")
    shutil.copy2(ranking_csv, global_dir / "ranking.csv")
    shutil.copy2(report_md, global_dir / "REPORT.md")
    copy_contents(official_sd_dir, global_dir)
    dendro_src = raw_run_dir / "dendrogram"
    if dendro_src.exists():
        copy_contents(dendro_src, global_dir / "dendrogram_probe")

    metadata = {
        "global_stage_script": path_to_repo_or_abs(GLOBAL_STAGE_SCRIPT),
        "raw_run_dir": path_to_repo_or_abs(raw_run_dir),
        "official_sd_dir_in_raw_run": path_to_repo_or_abs(official_sd_dir),
        "final_global_dir": path_to_repo_or_abs(global_dir),
        "official_sd_fraction": FROZEN_OFFICIAL_SD_FRACTION,
        "dictionary_mode": "fixed" if use_fixed_dictionary else "trained",
        "dictionary_path": str(dictionary_path.resolve()) if dictionary_path is not None else "",
    }
    (global_dir / "_global_stage_sources.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    summary_df = build_local_summary_row(runs_csv=runs_csv, seed=seed, global_dir=global_dir, run_dir_name=raw_run_dir.name)
    summary_csv = global_dir / "_summary_for_local_refinement.csv"
    summary_df.to_csv(summary_csv, index=False)
    return global_dir, summary_csv


def run_local_stage_for_seed(
    seed: int,
    seed_dir: Path,
    summary_csv: Path,
    k_values: Sequence[int],
    no_pca: bool,
    python_exe: str,
    use_fixed_dictionary: bool,
    dictionary_path: Path | None,
) -> Path:
    label = f"local-seed{seed:02d}"
    local_dir = seed_dir / "local_class02"
    local_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        python_exe,
        str(LOCAL_STAGE_SCRIPT.resolve()),
        "--summary-csv",
        str(summary_csv),
        "--out-dir",
        str(local_dir),
        "--seeds",
        str(seed),
        "--k-values",
        *[str(k) for k in k_values],
    ]
    if use_fixed_dictionary:
        assert dictionary_path is not None
        cmd.extend(["--use-fixed-dictionary", "--dictionary-path", str(dictionary_path)])
    if no_pca:
        cmd.append("--no-pca")
    run_command(cmd=cmd, label=label)

    nested_seed_dir = local_dir / f"seed_{seed:02d}"
    if nested_seed_dir.exists() and nested_seed_dir.is_dir():
        for item in nested_seed_dir.iterdir():
            dst = local_dir / item.name
            if dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.move(str(item), str(dst))
        nested_seed_dir.rmdir()

    metadata = {
        "local_stage_script": path_to_repo_or_abs(LOCAL_STAGE_SCRIPT),
        "summary_csv_used": path_to_repo_or_abs(summary_csv),
        "final_local_dir": path_to_repo_or_abs(local_dir),
        "local_k_values": [int(v) for v in k_values],
        "local_target_class_id": FROZEN_LOCAL_CLASS_ID,
        "dictionary_mode": "fixed" if use_fixed_dictionary else "trained",
        "dictionary_path": str(dictionary_path.resolve()) if dictionary_path is not None else "",
    }
    (local_dir / "_local_stage_sources.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return local_dir


def build_pipeline_report_md(
    report_path: Path,
    manifest_path: Path,
    run_root: Path,
    seeds: Sequence[int],
    fractions: Sequence[float],
    ranking_target_classes: int,
    run_local_refinement: bool,
    k_values: Sequence[int],
    use_fixed_dictionary: bool,
    dictionary_path: Path | None,
    seed_outcomes: Sequence[SeedOutcome],
) -> None:
    lines: List[str] = []
    lines.append("# Faithful Pipeline End-to-End Report")
    lines.append("")
    lines.append("## Frozen Working Configuration")
    lines.append(f"- patch size: {FROZEN_PATCH_W}x{FROZEN_PATCH_H}")
    lines.append(f"- dictionary size: {FROZEN_DICTIONARY_SIZE}")
    lines.append(f"- StandardScaler before Ward: {FROZEN_STANDARD_SCALER_ON}")
    lines.append(f"- official global SD fraction: {FROZEN_OFFICIAL_SD_FRACTION:.2f}")
    lines.append(f"- official global class structure target: {FROZEN_GLOBAL_TARGET_CLASSES}")
    lines.append(f"- local refinement target class: class_{FROZEN_LOCAL_CLASS_ID:02d}")
    lines.append(f"- local refinement default split: {DEFAULT_LOCAL_K_VALUES[0]} subclasses")
    lines.append("")
    lines.append("## Runtime Parameters")
    lines.append(f"- seeds requested: {[int(s) for s in seeds]}")
    lines.append(f"- fractions passed to global stage: {[float(v) for v in fractions]}")
    lines.append(f"- ranking_target_classes: {ranking_target_classes}")
    lines.append(f"- local refinement enabled: {bool(run_local_refinement)}")
    lines.append(f"- local k values: {[int(v) for v in k_values] if run_local_refinement else 'n/a'}")
    lines.append(f"- run root: `{path_to_repo_or_abs(run_root)}`")
    lines.append(f"- manifest: `{path_to_repo_or_abs(manifest_path)}`")
    lines.append(f"- dictionary mode: {'fixed' if use_fixed_dictionary else 'trained-per-run'}")
    lines.append(
        f"- dictionary path: `{dictionary_path.resolve()}`"
        if dictionary_path is not None
        else "- dictionary path: n/a (training mode)"
    )
    lines.append("")
    lines.append("## Stage Status By Seed")
    lines.append("| seed | global status | local status | global dir | local dir |")
    lines.append("| --- | --- | --- | --- | --- |")
    for outcome in seed_outcomes:
        gdir = outcome.global_stage.output_dir or "-"
        ldir = outcome.local_stage.output_dir or "-"
        lines.append(
            f"| {outcome.seed} | {outcome.global_stage.status} | {outcome.local_stage.status} | `{gdir}` | `{ldir}` |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("- `global/` contains promoted SD30 artifacts plus `runs.csv`, `ranking.csv`, and `REPORT.md`.")
    lines.append("- `local_class02/` contains class_02 refinement outputs from script 06.")
    lines.append("- If any stage failed, check `pipeline_manifest.json` for error details and missing-artifact checks.")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    seeds = normalize_seeds(seed=args.seed, seeds=args.seeds)
    fractions = validate_fractions(args.fractions)
    k_values = validate_local_k_values(args.local_k_values)
    use_fixed_dictionary = bool(args.use_fixed_dictionary or args.dictionary_path is not None)
    dictionary_path = Path(args.dictionary_path).resolve() if args.dictionary_path is not None else None
    if use_fixed_dictionary and dictionary_path is None:
        raise ValueError("--dictionary-path is required when --use-fixed-dictionary is enabled.")
    if dictionary_path is not None and not dictionary_path.exists():
        raise FileNotFoundError(f"Dictionary artifact not found: {dictionary_path}")
    if args.run_local_refinement and not any(np.isclose(f, FROZEN_OFFICIAL_SD_FRACTION, atol=1e-9) for f in fractions):
        raise ValueError(
            f"Local refinement requires SD fraction {FROZEN_OFFICIAL_SD_FRACTION:.2f} in --fractions."
        )
    if int(args.ranking_target_classes) <= 0:
        raise ValueError("--ranking-target-classes must be > 0.")

    input_paths = validate_required_inputs()
    out_base = args.out_base.resolve()
    run_root = out_base / args.run_tag
    if run_root.exists():
        if not args.overwrite:
            raise FileExistsError(
                f"Output folder already exists: {run_root}. Use a new --run-tag or pass --overwrite."
            )
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    tmp_root = run_root / "_tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)

    python_exe = str(Path(sys.executable).resolve())
    log("Starting frozen faithful pipeline end-to-end run.")
    log(f"Run root: {run_root}")
    log(f"Seeds: {seeds}")
    log(f"Fractions: {fractions}")
    log(f"Local refinement enabled: {args.run_local_refinement}")
    log(f"Dictionary mode: {'fixed' if use_fixed_dictionary else 'trained-per-run'}")
    if dictionary_path is not None:
        log(f"Dictionary path: {dictionary_path}")

    seed_outcomes: List[SeedOutcome] = []

    for seed in seeds:
        seed_dir = run_root / f"seed{seed:02d}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        log(f"=== Seed {seed} ===")

        global_stage = StageOutcome(status="pending")
        local_stage = StageOutcome(status="skipped")
        summary_csv: Path | None = None

        try:
            global_dir, summary_csv = run_global_stage_for_seed(
                seed=seed,
                seed_dir=seed_dir,
                fractions=fractions,
                ranking_target_classes=int(args.ranking_target_classes),
                no_pca=bool(args.no_pca),
                python_exe=python_exe,
                tmp_root=tmp_root,
                use_fixed_dictionary=use_fixed_dictionary,
                dictionary_path=dictionary_path,
            )
            global_checks = verify_global_artifacts(global_dir=global_dir, include_pca=not bool(args.no_pca))
            global_stage = StageOutcome(
                status="success" if all_checks_pass(global_checks) else "failed",
                output_dir=path_to_repo_or_abs(global_dir),
                checks=global_checks,
                details={"summary_for_local": path_to_repo_or_abs(summary_csv)},
            )
            if global_stage.status == "failed":
                missing = [k for k, ok in global_checks.items() if not ok]
                global_stage.error = "Missing global artifacts: " + ", ".join(missing)
        except Exception as exc:
            global_stage = StageOutcome(status="failed", error=str(exc))
            log(f"Seed {seed} global stage failed: {exc}")

        if args.run_local_refinement and global_stage.status == "success" and summary_csv is not None:
            try:
                local_dir = run_local_stage_for_seed(
                    seed=seed,
                    seed_dir=seed_dir,
                    summary_csv=summary_csv,
                    k_values=k_values,
                    no_pca=bool(args.no_pca),
                    python_exe=python_exe,
                    use_fixed_dictionary=use_fixed_dictionary,
                    dictionary_path=dictionary_path,
                )
                local_checks = verify_local_artifacts(local_dir=local_dir, k_values=k_values, include_pca=not bool(args.no_pca))
                local_stage = StageOutcome(
                    status="success" if all_checks_pass(local_checks) else "failed",
                    output_dir=path_to_repo_or_abs(local_dir),
                    checks=local_checks,
                )
                if local_stage.status == "failed":
                    missing = [k for k, ok in local_checks.items() if not ok]
                    local_stage.error = "Missing local artifacts: " + ", ".join(missing)
            except Exception as exc:
                local_stage = StageOutcome(status="failed", error=str(exc))
                log(f"Seed {seed} local stage failed: {exc}")
        elif args.run_local_refinement and global_stage.status != "success":
            local_stage = StageOutcome(status="skipped", error="Skipped because global stage failed.")
        elif not args.run_local_refinement:
            local_stage = StageOutcome(status="skipped", error="Local refinement disabled by CLI flag.")

        seed_outcomes.append(
            SeedOutcome(
                seed=seed,
                seed_dir=path_to_repo_or_abs(seed_dir),
                global_stage=global_stage,
                local_stage=local_stage,
            )
        )

    if tmp_root.exists():
        shutil.rmtree(tmp_root)

    any_failed = False
    for outcome in seed_outcomes:
        if outcome.global_stage.status != "success":
            any_failed = True
        if args.run_local_refinement and outcome.local_stage.status != "success":
            any_failed = True

    manifest = {
        "pipeline": "faithful_frozen_working_config_end_to_end",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_tag": args.run_tag,
        "output_root": path_to_repo_or_abs(run_root),
        "inputs": input_paths,
        "scripts_used": {
            "global_stage": path_to_repo_or_abs(GLOBAL_STAGE_SCRIPT),
            "local_stage": path_to_repo_or_abs(LOCAL_STAGE_SCRIPT),
            "runner": path_to_repo_or_abs(Path(__file__).resolve()),
        },
        "frozen_config": {
            "patch_size": [FROZEN_PATCH_W, FROZEN_PATCH_H],
            "dictionary_size": FROZEN_DICTIONARY_SIZE,
            "standard_scaler": FROZEN_STANDARD_SCALER_ON,
            "official_global_sd_fraction": FROZEN_OFFICIAL_SD_FRACTION,
            "official_global_target_classes": FROZEN_GLOBAL_TARGET_CLASSES,
            "local_refinement_target_class_id": FROZEN_LOCAL_CLASS_ID,
            "default_local_split_k": DEFAULT_LOCAL_K_VALUES[0],
            "label": "patch72x40_dict4_scalerON_sd30_class02split2",
        },
        "runtime_config": {
            "seeds_requested": [int(s) for s in seeds],
            "fractions": [float(v) for v in fractions],
            "ranking_target_classes": int(args.ranking_target_classes),
            "run_local_refinement": bool(args.run_local_refinement),
            "local_k_values": [int(v) for v in k_values],
            "no_pca": bool(args.no_pca),
            "use_fixed_dictionary": bool(use_fixed_dictionary),
            "dictionary_path": str(dictionary_path) if dictionary_path is not None else "",
            "overwrite": bool(args.overwrite),
        },
        "seed_outcomes": [
            {
                "seed": so.seed,
                "seed_dir": so.seed_dir,
                "global_stage": {
                    "status": so.global_stage.status,
                    "output_dir": so.global_stage.output_dir,
                    "error": so.global_stage.error,
                    "checks": so.global_stage.checks,
                    "details": so.global_stage.details,
                },
                "local_stage": {
                    "status": so.local_stage.status,
                    "output_dir": so.local_stage.output_dir,
                    "error": so.local_stage.error,
                    "checks": so.local_stage.checks,
                    "details": so.local_stage.details,
                },
            }
            for so in seed_outcomes
        ],
        "overall_success": not any_failed,
    }

    manifest_path = run_root / "pipeline_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    report_path = run_root / "PIPELINE_REPORT.md"
    build_pipeline_report_md(
        report_path=report_path,
        manifest_path=manifest_path,
        run_root=run_root,
        seeds=seeds,
        fractions=fractions,
        ranking_target_classes=int(args.ranking_target_classes),
        run_local_refinement=bool(args.run_local_refinement),
        k_values=k_values,
        use_fixed_dictionary=use_fixed_dictionary,
        dictionary_path=dictionary_path,
        seed_outcomes=seed_outcomes,
    )

    log(f"Wrote manifest: {manifest_path}")
    log(f"Wrote report: {report_path}")
    if any_failed:
        raise RuntimeError(
            "One or more stages failed. Check pipeline_manifest.json and PIPELINE_REPORT.md in the run output."
        )
    log("Pipeline completed successfully for all requested seeds.")


if __name__ == "__main__":
    main()
