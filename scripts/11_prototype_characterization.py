"""Strong pixel-wise spatial characterization of official seed11 prototypes.

This stage is strictly downstream:
- reads official compact model and official local class_02 artifacts
- does not re-run clustering or change class memberships
- exports per-pixel descriptors and map rasters for thesis integration
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

import prototype_characterization_utils as pcu


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OFFICIAL_STATE_CONFIG = ROOT / "configs" / "thesis_official_state.json"


def log(msg: str) -> None:
    print(f"[prototype-characterization] {msg}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build strong per-pixel spatial descriptors from official seed11 prototype artifacts."
    )
    p.add_argument(
        "--official-state-config",
        type=Path,
        default=DEFAULT_OFFICIAL_STATE_CONFIG,
        help="Central official-state JSON with canonical roots/artifact paths.",
    )
    p.add_argument("--project-root", type=Path, default=ROOT, help="Repository root.")
    p.add_argument("--seed", type=int, default=None, help="Seed id (default from official-state config).")
    p.add_argument(
        "--local-k",
        type=int,
        default=None,
        help="Local class_02 refinement k to characterize (default from official-state config).",
    )
    p.add_argument(
        "--compact-model-npz",
        type=Path,
        default=None,
        help="Explicit compact model NPZ path.",
    )
    p.add_argument(
        "--compact-model-manifest",
        type=Path,
        default=None,
        help="Optional compact model manifest path for traceability.",
    )
    p.add_argument(
        "--official-pipeline-root",
        type=Path,
        default=None,
        help="Official pipeline root containing seedXX/global and seedXX/local_class02.",
    )
    p.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Base output root for characterization runs.",
    )
    p.add_argument(
        "--cv-downstream-root",
        type=Path,
        default=None,
        help="Base root containing CV analysis runs (image_only outputs).",
    )
    p.add_argument(
        "--image-only-run-dir",
        type=Path,
        default=None,
        help="Explicit CV run directory with image_only CSVs.",
    )
    p.add_argument(
        "--image-only-global-csv",
        type=Path,
        default=None,
        help="Explicit global image_only CSV path.",
    )
    p.add_argument(
        "--image-only-local-csv",
        type=Path,
        default=None,
        help="Explicit local class_02 image_only CSV path.",
    )
    p.add_argument("--run-tag", type=str, default=None, help="Optional output subfolder tag.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow overwrite in existing output files.")
    p.add_argument(
        "--skip-local-class02",
        action="store_true",
        help="Characterize only global prototypes from compact model.",
    )
    p.add_argument(
        "--skip-map-figures",
        action="store_true",
        help="Skip PNG map generation (arrays and CSVs are still exported).",
    )
    return p.parse_args()


def _resolve_with_fallback(
    *,
    project_root: Path,
    explicit: Path | None,
    cfg_value: Any,
    fallback: Path,
) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    resolved = pcu.resolve_repo_or_abs(project_root, cfg_value)
    if resolved is not None:
        return resolved
    return fallback.resolve()


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_dir_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    state_cfg_path = args.official_state_config.expanduser().resolve()
    state = pcu.load_optional_json(state_cfg_path)
    official_pipeline = _mapping_or_empty(state.get("official_pipeline"))
    official_artifacts = _mapping_or_empty(state.get("official_artifacts"))
    frozen_cfg = _mapping_or_empty(official_pipeline.get("frozen_config"))

    seed_id = int(args.seed) if args.seed is not None else int(official_pipeline.get("seed_id", 11))
    local_k = int(args.local_k) if args.local_k is not None else int(frozen_cfg.get("local_default_k", 2))

    compact_model_npz = _resolve_with_fallback(
        project_root=project_root,
        explicit=args.compact_model_npz,
        cfg_value=official_artifacts.get("compact_model_npz"),
        fallback=project_root / "results" / "fossum" / "compact_model" / "v0_base" / "compact_model_final.npz",
    )
    compact_model_manifest = _resolve_with_fallback(
        project_root=project_root,
        explicit=args.compact_model_manifest,
        cfg_value=official_artifacts.get("compact_model_manifest"),
        fallback=compact_model_npz.with_name("compact_model_manifest.json"),
    )
    official_pipeline_root = _resolve_with_fallback(
        project_root=project_root,
        explicit=args.official_pipeline_root,
        cfg_value=official_pipeline.get("results_root"),
        fallback=project_root / "results" / "fossum" / "final_working_pipeline" / "official_fixed_dictionary_20260328",
    )
    output_root = _resolve_with_fallback(
        project_root=project_root,
        explicit=args.output_root,
        cfg_value=official_artifacts.get("prototype_characterization_root"),
        fallback=project_root / "results" / "prototype_characterization_seed11",
    )
    cv_downstream_root = _resolve_with_fallback(
        project_root=project_root,
        explicit=args.cv_downstream_root,
        cfg_value=official_artifacts.get("cv_downstream_root"),
        fallback=project_root / "results" / "computer_vision_seed11",
    )

    if not compact_model_npz.exists():
        raise FileNotFoundError(f"compact_model npz not found: {compact_model_npz}")
    if not official_pipeline_root.exists():
        raise FileNotFoundError(f"official pipeline root not found: {official_pipeline_root}")

    output_dir = pcu.ensure_output_dir(
        output_root=output_root,
        run_tag=args.run_tag,
        allow_overwrite=args.allow_overwrite,
    )

    log(f"state_config={state_cfg_path}")
    log(f"official_pipeline_root={official_pipeline_root}")
    log(f"compact_model_npz={compact_model_npz}")
    log(f"seed={seed_id} local_k={local_k}")
    log(f"output_dir={output_dir}")
    log(f"cv_downstream_root={cv_downstream_root}")

    global_payloads, lat_grid, lon_grid, compact_mask = pcu.load_compact_model_global_payloads(compact_model_npz)
    payloads = list(global_payloads)

    dataset_paths = pcu.discover_dataset_arrays(project_root=project_root)
    X_norm = np.load(dataset_paths["X_norm"]).astype(np.float32, copy=False)
    mask_common = np.load(dataset_paths["mask_common"]).astype(bool, copy=False)
    if mask_common.shape != compact_mask.shape or not np.array_equal(mask_common, compact_mask):
        raise RuntimeError(
            "mask_common mismatch between compact model and dataset arrays. "
            f"compact={compact_mask.shape}, dataset={mask_common.shape}"
        )

    if not args.skip_local_class02:
        local_payloads = pcu.discover_local_payloads(
            official_pipeline_root=official_pipeline_root,
            seed_id=seed_id,
            local_k=local_k,
            X_norm=X_norm,
            mask_common=mask_common,
            lat_grid=lat_grid,
            lon_grid=lon_grid,
        )
        payloads.extend(local_payloads)
        log(f"local_payloads={len(local_payloads)}")
    else:
        log("local payloads skipped by --skip-local-class02")

    if len(payloads) == 0:
        raise RuntimeError("No prototype payloads found to characterize.")

    image_only_bundle = pcu.load_image_only_label_bundle(
        cv_downstream_root=cv_downstream_root,
        seed_id=seed_id,
        explicit_run_dir=args.image_only_run_dir,
        explicit_global_csv=args.image_only_global_csv,
        explicit_local_csv=args.image_only_local_csv,
    )
    payloads = pcu.assign_image_only_labels(payloads, image_only_bundle)
    log(f"image_only_run_dir={image_only_bundle.run_dir}")
    log(f"image_only_global_csv={image_only_bundle.global_csv.name}")
    log(f"image_only_local_csv={image_only_bundle.local_csv.name}")

    all_pixel_tables: list[pd.DataFrame] = []
    all_region_tables: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    prototype_records: list[dict[str, Any]] = []

    for payload in payloads:
        scope_dir = output_dir / payload.scope / _safe_dir_name(payload.key)
        char = pcu.characterize_prototype(payload)

        pixel_csv = scope_dir / "pixel_descriptors.csv"
        region_csv = scope_dir / "region_descriptors.csv"
        raster_dir = scope_dir / "rasters"
        figure_dir = scope_dir / "figures"

        pcu.save_csv(char.pixel_df, pixel_csv, allow_overwrite=args.allow_overwrite)
        pcu.save_csv(char.region_df, region_csv, allow_overwrite=args.allow_overwrite)
        raster_paths = pcu.save_map_arrays(char.maps, raster_dir, allow_overwrite=args.allow_overwrite)
        figure_paths: dict[str, Path] = {}
        if not args.skip_map_figures:
            figure_paths = pcu.save_map_figures(
                maps=char.maps,
                out_dir=figure_dir,
                allow_overwrite=args.allow_overwrite,
            )

        all_pixel_tables.append(char.pixel_df)
        all_region_tables.append(char.region_df)
        valid_pixels = int(len(char.pixel_df))
        n_regions = int(char.pixel_df["region_id"].nunique()) if not char.pixel_df.empty else 0
        summary_rows.append(
            {
                "scope": payload.scope,
                "prototype_key": payload.key,
                "prototype_name": payload.prototype_name,
                "prototype_regime_label": char.regime_label,
                "segmentation_mode": char.segmentation_mode,
                "n_valid_pixels": valid_pixels,
                "n_regions": n_regions,
                "threshold": float(char.threshold),
                "threshold_method": char.threshold_method,
                "pixel_csv": str(pixel_csv.resolve()),
                "region_csv": str(region_csv.resolve()),
            }
        )
        prototype_records.append(
            {
                "scope": payload.scope,
                "prototype_key": payload.key,
                "prototype_name": payload.prototype_name,
                "prototype_regime_label": char.regime_label,
                "segmentation_mode": char.segmentation_mode,
                "metadata": dict(payload.metadata),
                "threshold": float(char.threshold),
                "threshold_method": char.threshold_method,
                "pixel_csv": str(pixel_csv.resolve()),
                "region_csv": str(region_csv.resolve()),
                "rasters": {k: str(v.resolve()) for k, v in raster_paths.items()},
                "figures": {k: str(v.resolve()) for k, v in figure_paths.items()},
            }
        )
        log(f"characterized {payload.scope}/{payload.key}: valid_pixels={valid_pixels}, regions={n_regions}")

    summary_df = pd.DataFrame(summary_rows).sort_values(["scope", "prototype_key"]).reset_index(drop=True)
    pixel_df = pd.concat(all_pixel_tables, axis=0, ignore_index=True) if all_pixel_tables else pd.DataFrame()
    region_df = pd.concat(all_region_tables, axis=0, ignore_index=True) if all_region_tables else pd.DataFrame()

    summary_csv = output_dir / "prototype_summary.csv"
    pixel_csv_all = output_dir / "pixel_descriptors_all.csv"
    region_csv_all = output_dir / "region_descriptors_all.csv"
    pcu.save_csv(summary_df, summary_csv, allow_overwrite=args.allow_overwrite)
    pcu.save_csv(pixel_df, pixel_csv_all, allow_overwrite=args.allow_overwrite)
    pcu.save_csv(region_df, region_csv_all, allow_overwrite=args.allow_overwrite)

    manifest = pcu.build_manifest(
        state_config_path=state_cfg_path,
        seed_id=seed_id,
        local_k=local_k,
        compact_model_npz=compact_model_npz,
        compact_model_manifest=compact_model_manifest if compact_model_manifest.exists() else None,
        official_pipeline_root=official_pipeline_root,
        output_dir=output_dir,
        summary_df=summary_df,
        pixel_csv_path=pixel_csv_all,
        region_csv_path=region_csv_all,
        dataset_paths=dataset_paths,
        records=prototype_records,
        image_only_bundle=image_only_bundle,
    )
    report = pcu.build_run_report_markdown(
        seed_id=seed_id,
        output_dir=output_dir,
        summary_df=summary_df,
        pixel_df=pixel_df,
        region_df=region_df,
        image_only_bundle=image_only_bundle,
    )
    pcu.save_json(manifest, output_dir / "manifest.json", allow_overwrite=args.allow_overwrite)
    pcu.save_text(report, output_dir / "run_report.md", allow_overwrite=args.allow_overwrite)

    log("characterization complete")
    log(f"summary_csv={summary_csv}")
    log(f"pixel_csv_all={pixel_csv_all}")
    log(f"region_csv_all={region_csv_all}")
    log(f"manifest={output_dir / 'manifest.json'}")
    log(f"report={output_dir / 'run_report.md'}")


if __name__ == "__main__":
    main()
