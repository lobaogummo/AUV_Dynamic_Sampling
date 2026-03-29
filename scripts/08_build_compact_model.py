"""Build the base compact SST regime model from canonical fixed-dictionary outputs.

Scope of this stage:
- Package final global classes into reusable numerical artifacts.
- Save NPZ + JSON manifest + perform integrity validation.

Out of scope for this script:
- CV descriptors, segmentation, inference, top-k, confidence, AUV integration.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from compact_model import load_compact_model


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CANONICAL_SEED = 11
DEFAULT_SD_FRACTION = 0.30
DEFAULT_EXPECTED_CLASSES = 5
DEFAULT_PATCH_W = 72
DEFAULT_PATCH_H = 40
DEFAULT_DICTIONARY_SIZE = 4
DEFAULT_LOCAL_REFINEMENT_CANDIDATE_SPLIT = 2

DEFAULT_OUT_DIR = ROOT / "results" / "fossum" / "compact_model" / "v0_base"
DEFAULT_CANONICAL_DICTIONARY_PATH = ROOT / "results" / "fossum" / "canonical_dictionary" / "canonical_dictionary.npz"
DEFAULT_CANONICAL_DICTIONARY_MANIFEST = (
    ROOT / "results" / "fossum" / "canonical_dictionary" / "canonical_dictionary_manifest.json"
)

HRES_PREFERRED_PATH = "data/HResNew/CMEMSnaza_20241029_HResNew.nc"

CLASS_MEMBERS_RX = re.compile(r"^class_(\d+)_members_list\.csv$", re.IGNORECASE)
CLASS_DISTANCE_RX = re.compile(r"^class_(\d+)_distance_to_prototype\.csv$", re.IGNORECASE)


def log(message: str) -> None:
    print(f"[08-build-compact-model] {message}")


def to_repo_or_abs(path: Path) -> str:
    rp = path.resolve()
    try:
        return rp.relative_to(ROOT).as_posix()
    except ValueError:
        return str(rp)


def from_repo_or_abs(path_like: str | Path) -> Path:
    p = Path(path_like)
    if p.is_absolute():
        return p.resolve()
    return (ROOT / p).resolve()


def first_existing_file(candidates: Sequence[Path]) -> Path | None:
    for p in candidates:
        if p.exists() and p.is_file():
            return p.resolve()
    return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build compact_model_final.npz + compact_model_manifest.json from canonical global clustering outputs."
    )
    p.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR), help="Output directory for compact model artifacts.")
    p.add_argument(
        "--source-run-dir",
        type=str,
        default=None,
        help="Optional explicit path to canonical global run directory (contains class_XX_members_list.csv + runs.csv).",
    )
    p.add_argument(
        "--pipeline-manifest",
        type=str,
        default=None,
        help="Optional explicit pipeline_manifest.json to use for source-run discovery.",
    )
    p.add_argument("--canonical-seed", type=int, default=DEFAULT_CANONICAL_SEED)
    p.add_argument("--sd-fraction", type=float, default=DEFAULT_SD_FRACTION)
    p.add_argument("--expected-classes", type=int, default=DEFAULT_EXPECTED_CLASSES)

    p.add_argument("--patch-w", type=int, default=DEFAULT_PATCH_W)
    p.add_argument("--patch-h", type=int, default=DEFAULT_PATCH_H)
    p.add_argument("--dictionary-size", type=int, default=DEFAULT_DICTIONARY_SIZE)
    p.add_argument("--standard-scaler", action="store_true", default=True, help="Store StandardScaler ON in manifest.")
    p.add_argument(
        "--canonical-dictionary-path",
        type=str,
        default=str(DEFAULT_CANONICAL_DICTIONARY_PATH),
        help="Path to canonical dictionary NPZ.",
    )
    p.add_argument(
        "--canonical-dictionary-manifest",
        type=str,
        default=str(DEFAULT_CANONICAL_DICTIONARY_MANIFEST),
        help="Path to canonical dictionary manifest JSON.",
    )
    p.add_argument("--model-version", type=str, default="v0_base")
    p.add_argument("--model-type", type=str, default="compact_model_base")
    p.add_argument(
        "--local-refinement-candidate-split",
        type=int,
        default=DEFAULT_LOCAL_REFINEMENT_CANDIDATE_SPLIT,
        help="Metadata-only hint for pending C2 refinement split.",
    )
    p.add_argument(
        "--allow-index-grid-fallback",
        action="store_true",
        help="If lat/lon metadata cannot be recovered from results/netcdf_files_summary.csv, fallback to index grids.",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing compact model files in output directory.")
    return p.parse_args()


def resolve_dataset_input_paths() -> Dict[str, Path]:
    paths = {
        "X_sst": first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300.npy",
                ROOT / "results" / "plots" / "X_surface_300.npy",
            ]
        ),
        "X_norm": first_existing_file(
            [
                ROOT / "results" / "fossum" / "X_surface_300_norm.npy",
                ROOT / "results" / "plots" / "X_surface_300_norm.npy",
            ]
        ),
        "mask_common": first_existing_file(
            [
                ROOT / "results" / "fossum" / "mask_common.npy",
                ROOT / "results" / "plots" / "mask_common.npy",
            ]
        ),
        "global_stats": first_existing_file(
            [
                ROOT / "results" / "fossum" / "global_stats.json",
                ROOT / "results" / "plots" / "global_stats.json",
            ]
        ),
    }
    missing = [k for k, v in paths.items() if v is None]
    if missing:
        raise FileNotFoundError(
            "Missing required numeric input files: "
            + ", ".join(missing)
            + " (checked results/fossum and results/plots)."
        )
    return {k: v for k, v in paths.items() if v is not None}


def load_numeric_inputs(paths: Dict[str, Path]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    X_sst = np.load(paths["X_sst"]).astype(np.float32, copy=False)
    X_norm = np.load(paths["X_norm"]).astype(np.float32, copy=False)
    mask_common = np.load(paths["mask_common"]).astype(bool, copy=False)
    stats = json.loads(paths["global_stats"].read_text(encoding="utf-8"))

    if X_sst.ndim != 3 or X_norm.ndim != 3:
        raise RuntimeError(f"Expected 3D arrays. Got X_sst={X_sst.shape}, X_norm={X_norm.shape}.")
    if X_sst.shape != X_norm.shape:
        raise RuntimeError(f"X_sst/X_norm shape mismatch: {X_sst.shape} vs {X_norm.shape}.")
    if mask_common.shape != X_sst.shape[1:]:
        raise RuntimeError(
            f"mask_common shape mismatch: mask={mask_common.shape} vs image spatial={X_sst.shape[1:]}"
        )

    X_sst = X_sst.copy()
    X_norm = X_norm.copy()
    X_sst[:, ~mask_common] = np.nan
    X_norm[:, ~mask_common] = np.nan

    return X_sst, X_norm, mask_common, stats


def parse_iso_datetime(raw: Any) -> datetime:
    text = str(raw or "").strip()
    if not text:
        return datetime.fromtimestamp(0)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.fromtimestamp(0)


def read_runs_row_for_sd(runs_csv: Path, sd_fraction: float) -> Dict[str, Any]:
    if not runs_csv.exists():
        raise FileNotFoundError(f"Missing runs.csv: {runs_csv}")
    runs_df = pd.read_csv(runs_csv)
    if "sd_fraction_of_max" not in runs_df.columns:
        raise RuntimeError(f"Unexpected runs.csv schema in {runs_csv}. Missing 'sd_fraction_of_max'.")
    sd_col = runs_df["sd_fraction_of_max"].astype(float).to_numpy()
    mask = np.isclose(sd_col, float(sd_fraction), atol=1e-9)
    if not np.any(mask):
        raise RuntimeError(f"No row with sd_fraction_of_max={sd_fraction:.2f} in {runs_csv}.")
    return runs_df.loc[mask].iloc[0].to_dict()


def verify_global_run_dir(global_dir: Path, sd_fraction: float, expected_classes: int) -> Dict[str, Any]:
    if not global_dir.exists() or not global_dir.is_dir():
        raise FileNotFoundError(f"Global run directory not found: {global_dir}")

    runs_csv = global_dir / "runs.csv"
    row = read_runs_row_for_sd(runs_csv=runs_csv, sd_fraction=sd_fraction)
    n_classes = int(row.get("number_of_classes"))
    if n_classes != int(expected_classes):
        raise RuntimeError(
            f"Global run at {global_dir} has number_of_classes={n_classes} for sd={sd_fraction:.2f}, "
            f"expected {expected_classes}."
        )

    class_member_files = sorted(global_dir.glob("class_*_members_list.csv"))
    if len(class_member_files) != int(expected_classes):
        raise RuntimeError(
            f"Expected {expected_classes} class_XX_members_list.csv files in {global_dir}, "
            f"found {len(class_member_files)}."
        )

    return {
        "runs_csv": runs_csv,
        "runs_row": row,
        "class_member_files": [f.resolve() for f in class_member_files],
    }

def discover_source_run_dir(
    source_run_dir: str | None,
    pipeline_manifest: str | None,
    canonical_seed: int,
    sd_fraction: float,
    expected_classes: int,
) -> Tuple[Path, Dict[str, Any]]:
    if source_run_dir is not None:
        explicit = from_repo_or_abs(source_run_dir)
        verification = verify_global_run_dir(
            global_dir=explicit,
            sd_fraction=sd_fraction,
            expected_classes=expected_classes,
        )
        return explicit, {
            "selection_mode": "explicit_source_run_dir",
            "source_run_dir": str(explicit),
            "pipeline_manifest_path": "",
            "run_tag": "",
            "verification": verification["runs_row"],
        }

    if pipeline_manifest is not None:
        manifest_paths = [from_repo_or_abs(pipeline_manifest)]
    else:
        manifest_paths = sorted((ROOT / "results" / "fossum" / "final_working_pipeline").glob("*/pipeline_manifest.json"))

    if not manifest_paths:
        raise FileNotFoundError(
            "No pipeline_manifest.json files found under results/fossum/final_working_pipeline/"
        )

    candidates: List[Dict[str, Any]] = []
    skip_reasons: List[str] = []

    for manifest_path in manifest_paths:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            skip_reasons.append(f"{manifest_path}: invalid JSON ({exc})")
            continue

        run_tag = str(payload.get("run_tag", ""))
        runtime_cfg = payload.get("runtime_config", {}) if isinstance(payload, dict) else {}
        use_fixed_dictionary = bool(runtime_cfg.get("use_fixed_dictionary", False))
        seed_outcomes = payload.get("seed_outcomes", []) if isinstance(payload, dict) else []
        if not isinstance(seed_outcomes, list):
            skip_reasons.append(f"{manifest_path}: malformed seed_outcomes")
            continue

        seed_entry = None
        for entry in seed_outcomes:
            try:
                if int(entry.get("seed")) == int(canonical_seed):
                    seed_entry = entry
                    break
            except Exception:
                continue

        if seed_entry is None:
            skip_reasons.append(f"{manifest_path}: seed {canonical_seed} not found")
            continue

        global_stage = seed_entry.get("global_stage", {})
        if str(global_stage.get("status", "")) != "success":
            skip_reasons.append(f"{manifest_path}: seed {canonical_seed} global stage not success")
            continue

        output_dir_raw = global_stage.get("output_dir")
        if not output_dir_raw:
            skip_reasons.append(f"{manifest_path}: seed {canonical_seed} global output_dir missing")
            continue
        global_dir = from_repo_or_abs(str(output_dir_raw))

        try:
            verification = verify_global_run_dir(
                global_dir=global_dir,
                sd_fraction=sd_fraction,
                expected_classes=expected_classes,
            )
        except Exception as exc:
            skip_reasons.append(f"{manifest_path}: {exc}")
            continue

        generated_at = parse_iso_datetime(payload.get("generated_at"))
        overall_success = bool(payload.get("overall_success", False))
        contains_official_tag = "official_fixed_dictionary" in run_tag.lower()

        # Primary: official_fixed_dictionary runs.
        # Secondary: fixed-dictionary mode.
        # Tertiary: latest generated_at.
        score = (
            1 if contains_official_tag else 0,
            1 if use_fixed_dictionary else 0,
            1 if overall_success else 0,
            generated_at.timestamp(),
            manifest_path.stat().st_mtime,
        )

        candidates.append(
            {
                "score": score,
                "manifest_path": manifest_path.resolve(),
                "run_tag": run_tag,
                "global_dir": global_dir.resolve(),
                "generated_at": generated_at.isoformat(),
                "use_fixed_dictionary": use_fixed_dictionary,
                "overall_success": overall_success,
                "verification": verification["runs_row"],
            }
        )

    if not candidates:
        detail = "\n".join(skip_reasons[:20])
        raise RuntimeError(
            "Could not discover canonical source global run for fixed dictionary seed "
            f"{canonical_seed}, sd={sd_fraction:.2f}, classes={expected_classes}.\n"
            f"Checked manifests: {len(manifest_paths)}\n"
            f"Sample reasons:\n{detail}"
        )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = candidates[0]
    return chosen["global_dir"], {
        "selection_mode": "auto_from_pipeline_manifests",
        "source_run_dir": str(chosen["global_dir"]),
        "pipeline_manifest_path": str(chosen["manifest_path"]),
        "run_tag": chosen["run_tag"],
        "generated_at": chosen["generated_at"],
        "use_fixed_dictionary": chosen["use_fixed_dictionary"],
        "overall_success": chosen["overall_success"],
        "verification": chosen["verification"],
        "candidates_considered": len(candidates),
    }


def load_labels_from_class_members(global_dir: Path, n_images: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[np.ndarray]]:
    # Use distance CSVs for full class membership (members_list.csv is panel-limited in 04a).
    class_files = sorted(global_dir.glob("class_*_distance_to_prototype.csv"))
    if not class_files:
        raise FileNotFoundError(f"No class_XX_distance_to_prototype.csv files found in {global_dir}")

    parsed: List[Tuple[int, np.ndarray]] = []
    for f in class_files:
        m = CLASS_DISTANCE_RX.match(f.name)
        if not m:
            continue
        class_id = int(m.group(1))
        df = pd.read_csv(f)
        if "image_idx_0_based" not in df.columns:
            raise RuntimeError(f"Missing 'image_idx_0_based' in {f}")
        idx = df["image_idx_0_based"].astype(int).to_numpy()
        if idx.size == 0:
            raise RuntimeError(f"Class {class_id} has no members in {f}")
        if np.unique(idx).size != idx.size:
            raise RuntimeError(f"Duplicate member indices inside class {class_id} file {f}")
        parsed.append((class_id, np.sort(idx.astype(np.int32, copy=False))))

    if not parsed:
        raise RuntimeError(f"Could not parse class IDs from members-list files in {global_dir}")

    parsed.sort(key=lambda t: t[0])
    class_ids = np.array([int(cid) for cid, _ in parsed], dtype=np.int32)
    class_names = np.array([f"C{int(cid)}" for cid in class_ids.tolist()], dtype="<U16")

    global_labels = np.full((n_images,), -1, dtype=np.int32)
    member_indices_by_class: List[np.ndarray] = []
    for class_id, idx in parsed:
        if np.any(idx < 0) or np.any(idx >= n_images):
            raise RuntimeError(f"Out-of-range image indices in class {class_id} members list.")
        if np.any(global_labels[idx] != -1):
            raise RuntimeError(f"Overlapping member assignments detected at class {class_id}.")
        global_labels[idx] = int(class_id)
        member_indices_by_class.append(idx.astype(np.int32, copy=False))

    if np.any(global_labels == -1):
        missing = int(np.sum(global_labels == -1))
        raise RuntimeError(f"Class member lists do not cover all images. Missing {missing} assignments.")

    class_sizes = np.array([int(v.size) for v in member_indices_by_class], dtype=np.int32)
    return class_ids, class_names, class_sizes, member_indices_by_class


def compute_class_mean_std_maps(
    X: np.ndarray,
    mask_common: np.ndarray,
    member_indices_by_class: Sequence[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
    k = len(member_indices_by_class)
    h, w = int(mask_common.shape[0]), int(mask_common.shape[1])
    mean_maps = np.empty((k, h, w), dtype=np.float32)
    std_maps = np.empty((k, h, w), dtype=np.float32)

    for i, idx in enumerate(member_indices_by_class):
        class_stack = X[idx]
        filled = np.nan_to_num(class_stack, nan=0.0).astype(np.float64, copy=False)
        mu_map = np.mean(filled, axis=0)
        sigma_map = np.sqrt(np.mean((filled - mu_map[None, :, :]) ** 2, axis=0))
        mu_map[~mask_common] = np.nan
        sigma_map[~mask_common] = np.nan
        mean_maps[i] = mu_map.astype(np.float32, copy=False)
        std_maps[i] = sigma_map.astype(np.float32, copy=False)

    return mean_maps, std_maps


def pack_member_indices(member_indices_by_class: Sequence[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    k = len(member_indices_by_class)
    max_size = max(int(idx.size) for idx in member_indices_by_class)
    member_matrix = np.full((k, max_size), -1, dtype=np.int32)
    lengths = np.zeros((k,), dtype=np.int32)
    for i, idx in enumerate(member_indices_by_class):
        n_i = int(idx.size)
        member_matrix[i, :n_i] = idx.astype(np.int32, copy=False)
        lengths[i] = n_i
    return member_matrix, lengths

def build_lat_lon_grids(
    nx: int,
    ny: int,
    allow_index_grid_fallback: bool,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    summary_csv = ROOT / "results" / "netcdf_files_summary.csv"

    if summary_csv.exists():
        df = pd.read_csv(summary_csv)
        if "open_ok" in df.columns:
            open_ok = df["open_ok"].astype(str).str.lower().isin(["true", "1", "yes"])
            df_ok = df.loc[open_ok].copy()
        else:
            df_ok = df.copy()

        preferred = df_ok.loc[df_ok["path"].astype(str) == HRES_PREFERRED_PATH]
        if preferred.empty:
            contains_hres = df_ok["path"].astype(str).str.replace("\\\\", "/").str.contains("/HResNew/", regex=False)
            preferred = df_ok.loc[contains_hres]

        if not preferred.empty:
            row = preferred.iloc[0]
            try:
                lon_min = float(row["lon_min"])
                lon_max = float(row["lon_max"])
                lat_min = float(row["lat_min"])
                lat_max = float(row["lat_max"])
            except Exception as exc:
                raise RuntimeError(
                    f"Invalid lon/lat bounds in {summary_csv} for row {row.to_dict()}"
                ) from exc

            lon_1d = np.linspace(lon_min, lon_max, int(nx), dtype=np.float32)
            lat_1d = np.linspace(lat_min, lat_max, int(ny), dtype=np.float32)
            lon_grid, lat_grid = np.meshgrid(lon_1d, lat_1d)
            meta = {
                "method": "linear_resample_from_hres_bbox",
                "source_csv": to_repo_or_abs(summary_csv),
                "source_row_path": str(row.get("path", "")),
                "hres_lon_min": lon_min,
                "hres_lon_max": lon_max,
                "hres_lat_min": lat_min,
                "hres_lat_max": lat_max,
                "target_nx": int(nx),
                "target_ny": int(ny),
            }
            return lat_grid.astype(np.float32), lon_grid.astype(np.float32), meta

    reason = (
        f"Could not recover physical lat/lon bounds from {summary_csv} "
        "using preferred HResNew row."
    )
    if not allow_index_grid_fallback:
        raise FileNotFoundError(reason + " Use --allow-index-grid-fallback to proceed with index grids.")

    lon_1d = np.arange(int(nx), dtype=np.float32)
    lat_1d = np.arange(int(ny), dtype=np.float32)
    lon_grid, lat_grid = np.meshgrid(lon_1d, lat_1d)
    meta = {
        "method": "index_grid_fallback",
        "reason": reason,
        "target_nx": int(nx),
        "target_ny": int(ny),
    }
    return lat_grid.astype(np.float32), lon_grid.astype(np.float32), meta


def validate_saved_model(
    npz_path: Path,
    manifest_path: Path,
    expected_classes: int,
    expected_seed: int,
    expected_source_run_dir: Path,
    expected_mean_norm: np.ndarray,
    expected_std_norm: np.ndarray,
    expected_mean_orig: np.ndarray,
    expected_std_orig: np.ndarray,
    mask_common: np.ndarray,
) -> Dict[str, Any]:
    bundle = load_compact_model(npz_path=npz_path, manifest_path=manifest_path)

    checks: Dict[str, Any] = {}
    checks["loader_ok"] = True
    checks["class_count_is_expected"] = int(bundle.class_ids.size) == int(expected_classes)
    checks["class_sizes_sum_to_n"] = int(np.sum(bundle.class_sizes)) == int(bundle.global_labels.size)
    checks["member_indices_cover_n"] = int(sum(len(v) for v in bundle.member_indices_by_class)) == int(
        bundle.global_labels.size
    )
    checks["prototype_mean_norm_matches_saved"] = bool(
        np.allclose(bundle.prototype_mean_norm, expected_mean_norm, equal_nan=True)
    )
    checks["prototype_std_norm_matches_saved"] = bool(
        np.allclose(bundle.prototype_std_norm, expected_std_norm, equal_nan=True)
    )
    checks["prototype_mean_orig_matches_saved"] = bool(
        np.allclose(bundle.prototype_mean_orig, expected_mean_orig, equal_nan=True)
    )
    checks["prototype_std_orig_matches_saved"] = bool(
        np.allclose(bundle.prototype_std_orig, expected_std_orig, equal_nan=True)
    )
    checks["std_maps_finite_on_valid_mask_norm"] = bool(np.isfinite(bundle.prototype_std_norm[:, mask_common]).all())
    checks["std_maps_finite_on_valid_mask_orig"] = bool(np.isfinite(bundle.prototype_std_orig[:, mask_common]).all())
    checks["model_usable_without_pngs"] = True

    manifest = bundle.manifest or {}
    checks["manifest_has_expected_seed"] = int(manifest.get("canonical_seed", -1)) == int(expected_seed)
    checks["manifest_has_expected_global_classes"] = int(manifest.get("global_n_classes", -1)) == int(expected_classes)
    manifest_source_path = manifest.get("source_run_path", "")
    checks["manifest_source_run_matches"] = (
        str(from_repo_or_abs(manifest_source_path).resolve()) == str(expected_source_run_dir.resolve())
    )

    checks["all_passed"] = bool(all(bool(v) for v in checks.values() if isinstance(v, bool)))
    return checks


def maybe_load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    if args.expected_classes <= 0:
        raise ValueError("--expected-classes must be > 0.")
    if args.sd_fraction <= 0.0 or args.sd_fraction >= 1.0:
        raise ValueError("--sd-fraction must be in (0, 1).")
    if args.patch_w <= 0 or args.patch_h <= 0:
        raise ValueError("--patch-w and --patch-h must be > 0.")
    if args.dictionary_size <= 0:
        raise ValueError("--dictionary-size must be > 0.")
    if args.local_refinement_candidate_split < 2:
        raise ValueError("--local-refinement-candidate-split must be >= 2.")

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    npz_path = out_dir / "compact_model_final.npz"
    manifest_path = out_dir / "compact_model_manifest.json"

    if not args.overwrite:
        existing = [p for p in [npz_path, manifest_path] if p.exists()]
        if existing:
            raise FileExistsError(
                "Output files already exist. Use --overwrite to replace: "
                + ", ".join(str(p) for p in existing)
            )

    input_paths = resolve_dataset_input_paths()
    log("Loading numeric SST inputs (X_sst, X_norm, mask_common, global_stats).")
    X_sst, X_norm, mask_common, stats = load_numeric_inputs(paths=input_paths)
    n_images, ny, nx = X_norm.shape

    canonical_dict_path = from_repo_or_abs(args.canonical_dictionary_path)
    if not canonical_dict_path.exists():
        raise FileNotFoundError(f"Canonical dictionary not found: {canonical_dict_path}")
    canonical_dict_manifest_path = from_repo_or_abs(args.canonical_dictionary_manifest)
    canonical_dict_manifest = maybe_load_json(canonical_dict_manifest_path)

    source_run_dir, source_selection = discover_source_run_dir(
        source_run_dir=args.source_run_dir,
        pipeline_manifest=args.pipeline_manifest,
        canonical_seed=int(args.canonical_seed),
        sd_fraction=float(args.sd_fraction),
        expected_classes=int(args.expected_classes),
    )
    log(f"Canonical source run selected: {source_run_dir}")

    run_verification = verify_global_run_dir(
        global_dir=source_run_dir,
        sd_fraction=float(args.sd_fraction),
        expected_classes=int(args.expected_classes),
    )

    class_ids, class_names, class_sizes, member_indices_by_class = load_labels_from_class_members(
        global_dir=source_run_dir,
        n_images=int(n_images),
    )
    if class_ids.size != int(args.expected_classes):
        raise RuntimeError(
            f"Parsed class count from members lists is {class_ids.size}, expected {args.expected_classes}."
        )

    global_labels = np.full((n_images,), -1, dtype=np.int32)
    for class_id, idx in zip(class_ids.tolist(), member_indices_by_class):
        global_labels[idx] = int(class_id)
    if np.any(global_labels < 0):
        missing = int(np.sum(global_labels < 0))
        raise RuntimeError(f"Global labels reconstruction incomplete. Missing {missing} entries.")

    log("Computing per-class prototypes and std maps in normalized and original domains.")
    prototype_mean_norm, prototype_std_norm = compute_class_mean_std_maps(
        X=X_norm,
        mask_common=mask_common,
        member_indices_by_class=member_indices_by_class,
    )
    prototype_mean_orig, prototype_std_orig = compute_class_mean_std_maps(
        X=X_sst,
        mask_common=mask_common,
        member_indices_by_class=member_indices_by_class,
    )

    member_matrix, member_lengths = pack_member_indices(member_indices_by_class=member_indices_by_class)

    log("Building lat/lon grids for model spatial support.")
    lat_grid, lon_grid, lat_lon_meta = build_lat_lon_grids(
        nx=int(nx),
        ny=int(ny),
        allow_index_grid_fallback=bool(args.allow_index_grid_fallback),
    )

    mu_global = float(stats.get("mu_global"))
    sigma_global = float(stats.get("sigma_global"))
    if not np.isfinite(mu_global) or not np.isfinite(sigma_global) or sigma_global <= 0.0:
        raise RuntimeError(f"Invalid normalization metadata in global_stats: mu={mu_global}, sigma={sigma_global}")

    log(f"Saving compact model NPZ to: {npz_path}")
    np.savez_compressed(
        npz_path,
        class_ids=class_ids.astype(np.int32, copy=False),
        class_names=class_names.astype("<U16", copy=False),
        class_sizes=class_sizes.astype(np.int32, copy=False),
        global_labels=global_labels.astype(np.int32, copy=False),
        prototype_mean_norm=prototype_mean_norm.astype(np.float32, copy=False),
        prototype_std_norm=prototype_std_norm.astype(np.float32, copy=False),
        prototype_mean_orig=prototype_mean_orig.astype(np.float32, copy=False),
        prototype_std_orig=prototype_std_orig.astype(np.float32, copy=False),
        mask_common=mask_common.astype(bool, copy=False),
        lat_grid=lat_grid.astype(np.float32, copy=False),
        lon_grid=lon_grid.astype(np.float32, copy=False),
        mu_global=np.array(mu_global, dtype=np.float64),
        sigma_global=np.array(sigma_global, dtype=np.float64),
        member_indices_by_class=member_matrix.astype(np.int32, copy=False),
        member_indices_lengths=member_lengths.astype(np.int32, copy=False),
    )

    source_pipeline_manifest_path = source_selection.get("pipeline_manifest_path", "")
    source_pipeline_manifest_abs = from_repo_or_abs(source_pipeline_manifest_path) if source_pipeline_manifest_path else None
    source_pipeline_manifest = (
        maybe_load_json(source_pipeline_manifest_abs) if source_pipeline_manifest_abs and source_pipeline_manifest_abs.exists() else {}
    )

    manifest: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model_version": str(args.model_version),
        "model_type": str(args.model_type),
        "canonical_seed": int(args.canonical_seed),
        "patch_width": int(args.patch_w),
        "patch_height": int(args.patch_h),
        "dictionary_size": int(args.dictionary_size),
        "standard_scaler": bool(args.standard_scaler),
        "sd_fraction": float(args.sd_fraction),
        "global_n_classes": int(class_ids.size),
        "global_classes": [str(v) for v in class_names.tolist()],
        "class_ids": [int(v) for v in class_ids.tolist()],
        "class_sizes": [int(v) for v in class_sizes.tolist()],
        "domains_saved": ["normalized", "original"],
        "canonical_dictionary_path": str(canonical_dict_path),
        "canonical_dictionary_manifest_path": str(canonical_dict_manifest_path),
        "source_run_path": str(source_run_dir),
        "source_pipeline_manifest_path": str(source_pipeline_manifest_abs) if source_pipeline_manifest_abs else "",
        "source_selection": source_selection,
        "source_run_sd_row": run_verification["runs_row"],
        "source_dataset_artifacts": {
            "X_sst": str(input_paths["X_sst"]),
            "X_norm": str(input_paths["X_norm"]),
            "mask_common": str(input_paths["mask_common"]),
            "global_stats": str(input_paths["global_stats"]),
        },
        "normalization_metadata": {
            "mu_global": mu_global,
            "sigma_global": sigma_global,
            "stats_n_images": int(stats.get("n_images", n_images)),
            "stats_ny": int(stats.get("ny", ny)),
            "stats_nx": int(stats.get("nx", nx)),
        },
        "masking_notes": {
            "mask_source": str(input_paths["mask_common"]),
            "mask_policy": "Common valid mask applied to all domains. Pixels outside mask are stored as NaN in prototypes/std maps.",
            "valid_pixel_count": int(np.sum(mask_common)),
            "total_pixel_count": int(mask_common.size),
        },
        "spatial_support": lat_lon_meta,
        "member_indices_storage": {
            "format": "padded_matrix_with_lengths",
            "matrix_field": "member_indices_by_class",
            "lengths_field": "member_indices_lengths",
            "padding_value": -1,
        },
        "shape_summary": {
            "N": int(n_images),
            "H": int(ny),
            "W": int(nx),
            "prototype_shape": [int(class_ids.size), int(ny), int(nx)],
            "global_labels_shape": [int(n_images)],
            "mask_shape": [int(ny), int(nx)],
            "member_indices_matrix_shape": [int(member_matrix.shape[0]), int(member_matrix.shape[1])],
        },
        "local_refinements": {
            "C2": {
                "status": "pending_decision",
                "candidate_split": int(args.local_refinement_candidate_split),
            }
        },
        "scripts_used": {
            "builder": "scripts/08_build_compact_model.py",
            "loader": "scripts/compact_model.py::load_compact_model",
            "source_global_stage": source_pipeline_manifest.get("scripts_used", {}).get("global_stage", ""),
            "source_local_stage": source_pipeline_manifest.get("scripts_used", {}).get("local_stage", ""),
            "source_runner": source_pipeline_manifest.get("scripts_used", {}).get("runner", ""),
        },
        "compact_model_files": {
            "npz_path": str(npz_path),
            "manifest_path": str(manifest_path),
        },
        "canonical_dictionary_context": canonical_dict_manifest.get("fixed_pipeline_config", {}),
        "validation": {},
    }

    log(f"Writing manifest JSON to: {manifest_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    log("Validating saved compact model via loader.")
    validation = validate_saved_model(
        npz_path=npz_path,
        manifest_path=manifest_path,
        expected_classes=int(args.expected_classes),
        expected_seed=int(args.canonical_seed),
        expected_source_run_dir=source_run_dir,
        expected_mean_norm=prototype_mean_norm,
        expected_std_norm=prototype_std_norm,
        expected_mean_orig=prototype_mean_orig,
        expected_std_orig=prototype_std_orig,
        mask_common=mask_common,
    )
    if not bool(validation.get("all_passed", False)):
        failed = [k for k, v in validation.items() if isinstance(v, bool) and not v]
        raise RuntimeError("Compact model validation failed: " + ", ".join(failed))

    manifest["validation"] = validation
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    log("Compact model build completed successfully.")
    log(f"NPZ: {to_repo_or_abs(npz_path)}")
    log(f"Manifest: {to_repo_or_abs(manifest_path)}")


if __name__ == "__main__":
    main()
