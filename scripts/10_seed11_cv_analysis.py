"""Run seed11 computer-vision analysis as a reproducible downstream pipeline stage.

This stage consumes official prototype exports produced upstream by:
`scripts/09_export_cv_prototypes.py`.

It does not run clustering and does not modify existing prototype artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import matplotlib
import pandas as pd

matplotlib.use("Agg")

import cv_seed11_utils as cvu


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OFFICIAL_STATE_CONFIG = ROOT / "configs" / "thesis_official_state.json"


SIMPLE_RULE_KEYS = [
    "homogeneous_std_max",
    "homogeneous_p90_grad_max",
    "homogeneous_front_area_max",
    "multi_min_region_ratio_min",
    "multi_inter_region_diff_min",
    "multi_coherence_min",
    "multi_front_area_ratio_min",
    "multi_p90_grad_min",
]

IMAGE_RULE_KEYS = [
    "homogeneous_std_low_max",
    "homogeneous_min_region_tiny_max",
    "homogeneous_inter_diff_low_max",
    "homogeneous_std_mid_max",
    "homogeneous_min_region_mid_max",
    "homogeneous_inter_diff_mid_min",
    "homogeneous_inter_diff_mid_max",
    "homogeneous_p90_grad_mid_max",
    "multi_min_region_ratio_min",
    "multi_inter_region_diff_min",
    "multi_coherence_min",
    "multi_p90_grad_min",
]


def log(msg: str) -> None:
    print(f"[seed11-cv-analysis] {msg}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert seed11 CV notebook logic into a deterministic local script stage."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "cv_seed11_config.json",
        help="JSON config with defaults and thresholds.",
    )
    p.add_argument(
        "--project-root",
        type=Path,
        default=ROOT,
        help="Repository root.",
    )
    p.add_argument(
        "--cv-export-root",
        type=Path,
        default=None,
        help="Explicit computer_vision_exports root. If omitted, auto-discovery is used.",
    )
    p.add_argument(
        "--official-state-config",
        type=Path,
        default=DEFAULT_OFFICIAL_STATE_CONFIG,
        help=(
            "Optional central official-state JSON. "
            "When present, default CV source/output roots are resolved from it."
        ),
    )
    p.add_argument("--seed", type=int, default=None, help="Seed id (default: config value).")
    p.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Base output directory for CV analysis runs (default resolved from official state config).",
    )
    p.add_argument("--run-tag", type=str, default=None, help="Optional run tag subfolder.")
    p.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow overwriting files in output dir.",
    )
    p.add_argument(
        "--save-figures",
        action="store_true",
        help="Save validation and visualization figures to output dir/figures.",
    )
    p.add_argument(
        "--enable-optional-hsl",
        action="store_true",
        help="Enable optional HSL exploratory block.",
    )
    p.add_argument(
        "--enable-simple",
        action="store_true",
        help="Run optional simple analysis (disabled by default).",
    )
    p.add_argument(
        "--disable-image-only",
        action="store_true",
        help="Skip image-only analysis.",
    )
    return p.parse_args()


def _require_rule_keys(name: str, rules: Mapping[str, Any], keys: list[str]) -> None:
    missing = [k for k in keys if k not in rules]
    if missing:
        raise ValueError(f"Missing {name} rule keys in config: {missing}")


def _config_block(cfg: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = cfg.get(key, {})
    if not isinstance(value, Mapping):
        raise ValueError(f"Config key '{key}' must be an object.")
    return value


def _resolve_repo_or_abs(project_root: Path, path_value: str | Path | None) -> Path | None:
    if path_value is None:
        return None
    p = Path(path_value).expanduser()
    if not p.is_absolute():
        p = project_root / p
    return p.resolve()


def _load_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    cfg_path = path.expanduser().resolve()
    if not cfg_path.exists():
        return {}
    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Official state config must be a JSON object: {cfg_path}")
    return payload


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    cfg = cvu.load_cv_config(config_path)
    official_state = _load_optional_json(args.official_state_config)
    official_artifacts = official_state.get("official_artifacts", {})
    if not isinstance(official_artifacts, Mapping):
        official_artifacts = {}

    seed_id = int(args.seed) if args.seed is not None else int(cfg.get("seed_id", 11))
    expected_vmin = float(cfg.get("expected_vmin", -2.025433))
    expected_vmax = float(cfg.get("expected_vmax", 2.025433))
    expected_cmap = str(cfg.get("expected_cmap", "coolwarm"))
    expected_mask_true_is_valid = bool(cfg.get("expected_mask_true_is_valid", True))

    simple_cfg = _config_block(cfg, "simple")
    simple_enabled_default = bool(simple_cfg.get("enabled", False))
    run_simple = bool(args.enable_simple) or simple_enabled_default
    simple_sigma = float(simple_cfg.get("sigma", 1.0))
    simple_rules = simple_cfg.get("rules", {})
    if not isinstance(simple_rules, Mapping):
        raise ValueError("Config key 'simple.rules' must be an object.")
    if run_simple:
        _require_rule_keys("simple", simple_rules, SIMPLE_RULE_KEYS)

    image_cfg = _config_block(cfg, "image_only")
    image_only_enabled_default = bool(image_cfg.get("enabled", True))
    run_image_only = image_only_enabled_default and (not args.disable_image_only)
    image_grad_sigma = float(image_cfg.get("grad_sigma", 1.0))
    image_rules = image_cfg.get("rules", {})
    if not isinstance(image_rules, Mapping):
        raise ValueError("Config key 'image_only.rules' must be an object.")
    if run_image_only:
        _require_rule_keys("image_only", image_rules, IMAGE_RULE_KEYS)

    hsl_cfg = _config_block(cfg, "optional_hsl")
    hsl_enabled = bool(hsl_cfg.get("enabled", False)) or bool(args.enable_optional_hsl)
    hsl_max_items = int(hsl_cfg.get("max_items", 4))

    project_root = args.project_root.resolve()
    cv_export_root = args.cv_export_root
    if cv_export_root is None:
        cv_export_cfg = official_artifacts.get("cv_export_root")
        cv_export_root = _resolve_repo_or_abs(project_root, str(cv_export_cfg)) if cv_export_cfg else None
    cv_paths = cvu.resolve_seed_export_paths(
        project_root=project_root,
        seed_id=seed_id,
        cv_export_root=cv_export_root,
    )
    log(f"project_root={project_root}")
    log(f"cv_export_root={cv_paths.cv_export_root}")
    log(f"seed_root={cv_paths.seed_root}")

    global_records = cvu.discover_global_prototypes(cv_paths.global_dir)
    local_records = cvu.discover_local_class02_prototypes(cv_paths.local_class02_dir)
    if len(global_records) == 0:
        raise RuntimeError("No global prototypes discovered.")
    if len(local_records) == 0:
        raise RuntimeError("No local class_02 prototypes discovered.")
    require_clean_png = run_image_only or hsl_enabled
    cvu.validate_record_files(global_records, require_clean_png=require_clean_png)
    cvu.validate_record_files(local_records, require_clean_png=require_clean_png)

    global_data, local_data, validation_df, data_meta = cvu.load_datasets_with_validation(
        global_records=global_records,
        local_records=local_records,
        expected_mask_true_is_valid=expected_mask_true_is_valid,
    )

    features_global_df, features_local_df = cvu.build_basic_feature_tables(
        global_data=global_data,
        local_data=local_data,
        seed_id=seed_id,
    )
    if run_simple:
        simple_global_df, simple_local_df, simple_global_aux, simple_local_aux = cvu.run_simple_analysis(
            global_data=global_data,
            local_data=local_data,
            seed_id=seed_id,
            sigma=simple_sigma,
            rules=simple_rules,
        )
    else:
        simple_global_df = pd.DataFrame()
        simple_local_df = pd.DataFrame()
        simple_global_aux: dict[str, dict[str, Any]] = {}
        simple_local_aux: dict[str, dict[str, Any]] = {}

    if not run_image_only:
        image_global_df = pd.DataFrame()
        image_local_df = pd.DataFrame()
        image_global_aux: dict[str, dict[str, Any]] = {}
        image_local_aux: dict[str, dict[str, Any]] = {}
    else:
        image_global_df, image_local_df, image_global_aux, image_local_aux = cvu.run_image_only_analysis(
            global_records=global_records,
            local_records=local_records,
            seed_id=seed_id,
            grad_sigma=image_grad_sigma,
            rules=image_rules,
        )

    if args.output_root is not None:
        output_root = args.output_root.resolve()
    else:
        output_cfg = official_artifacts.get("cv_downstream_root")
        output_root = (
            _resolve_repo_or_abs(project_root, str(output_cfg))
            if output_cfg
            else (project_root / "results" / "computer_vision_seed11").resolve()
        )

    output_dir = cvu.ensure_output_dir(
        output_root=output_root,
        run_tag=args.run_tag,
        seed_id=seed_id,
        allow_overwrite=args.allow_overwrite,
    )
    log(f"output_dir={output_dir}")

    csv_paths = {
        "global_features": output_dir / f"cv_features_global_seed{seed_id}.csv",
        "local_features": output_dir / f"cv_features_local_class02_seed{seed_id}.csv",
        "validation": output_dir / f"cv_validation_seed{seed_id}.csv",
    }
    if run_simple:
        csv_paths["simple_global"] = output_dir / f"cv_features_global_seed{seed_id}_simple.csv"
        csv_paths["simple_local"] = output_dir / f"cv_features_local_class02_seed{seed_id}_simple.csv"
    if run_image_only:
        csv_paths["image_global"] = output_dir / f"cv_features_global_seed{seed_id}_image_only.csv"
        csv_paths["image_local"] = output_dir / f"cv_features_local_class02_seed{seed_id}_image_only.csv"

    cvu.write_csv(features_global_df, csv_paths["global_features"], allow_overwrite=args.allow_overwrite)
    cvu.write_csv(features_local_df, csv_paths["local_features"], allow_overwrite=args.allow_overwrite)
    cvu.write_csv(validation_df, csv_paths["validation"], allow_overwrite=args.allow_overwrite)
    if run_simple:
        cvu.write_csv(simple_global_df, csv_paths["simple_global"], allow_overwrite=args.allow_overwrite)
        cvu.write_csv(simple_local_df, csv_paths["simple_local"], allow_overwrite=args.allow_overwrite)
    if run_image_only:
        cvu.write_csv(image_global_df, csv_paths["image_global"], allow_overwrite=args.allow_overwrite)
        cvu.write_csv(image_local_df, csv_paths["image_local"], allow_overwrite=args.allow_overwrite)

    figure_paths: dict[str, Path] = {}
    optional_hsl_meta: dict[str, Any] = {"status": "disabled"}
    if args.save_figures:
        fig_dir = output_dir / "figures"
        fig_global = cvu.build_masked_overview_figure(
            data=global_data,
            title=f"Global prototypes | seed {seed_id} | fixed scale [{expected_vmin}, {expected_vmax}]",
            cols_max=3,
            vmin=expected_vmin,
            vmax=expected_vmax,
            cmap=expected_cmap,
        )
        path = fig_dir / "global_prototypes_fixed_scale.png"
        cvu.save_figure(fig_global, path, allow_overwrite=args.allow_overwrite)
        figure_paths["global_overview"] = path

        fig_local = cvu.build_masked_overview_figure(
            data=local_data,
            title=f"Local class_02 prototypes | seed {seed_id} | fixed scale [{expected_vmin}, {expected_vmax}]",
            cols_max=2,
            vmin=expected_vmin,
            vmax=expected_vmax,
            cmap=expected_cmap,
        )
        path = fig_dir / "local_class02_prototypes_fixed_scale.png"
        cvu.save_figure(fig_local, path, allow_overwrite=args.allow_overwrite)
        figure_paths["local_overview"] = path

        fig_halves, fig_quads = cvu.build_example_splits_figure(
            global_data=global_data,
            vmin=expected_vmin,
            vmax=expected_vmax,
            cmap=expected_cmap,
        )
        path = fig_dir / "example_halves.png"
        cvu.save_figure(fig_halves, path, allow_overwrite=args.allow_overwrite)
        figure_paths["example_halves"] = path
        path = fig_dir / "example_quadrants.png"
        cvu.save_figure(fig_quads, path, allow_overwrite=args.allow_overwrite)
        figure_paths["example_quadrants"] = path

        if run_simple:
            fig_simple_global = cvu.build_simple_cv_grid_figure(
                df=simple_global_df,
                data_dict=global_data,
                aux_dict=simple_global_aux,
                key_col="prototype_name",
                figure_title=f"Global prototypes | seed {seed_id} | original (top) vs final CV (bottom)",
                vmin=expected_vmin,
                vmax=expected_vmax,
                cmap=expected_cmap,
            )
            path = fig_dir / "simple_global_grid.png"
            cvu.save_figure(fig_simple_global, path, allow_overwrite=args.allow_overwrite)
            figure_paths["simple_global"] = path

            fig_simple_local = cvu.build_simple_cv_grid_figure(
                df=simple_local_df,
                data_dict=local_data,
                aux_dict=simple_local_aux,
                key_col="key",
                figure_title=f"Local class_02 prototypes | seed {seed_id} | original (top) vs final CV (bottom)",
                vmin=expected_vmin,
                vmax=expected_vmax,
                cmap=expected_cmap,
            )
            path = fig_dir / "simple_local_grid.png"
            cvu.save_figure(fig_simple_local, path, allow_overwrite=args.allow_overwrite)
            figure_paths["simple_local"] = path

        if run_image_only:
            fig_image_global = cvu.build_image_only_grid_figure(
                df=image_global_df,
                aux_dict=image_global_aux,
                key_col="prototype_name",
                figure_title=f"Image-only | global prototypes | seed {seed_id} | original (top) vs result (bottom)",
            )
            path = fig_dir / "image_only_global_grid.png"
            cvu.save_figure(fig_image_global, path, allow_overwrite=args.allow_overwrite)
            figure_paths["image_only_global"] = path

            fig_image_local = cvu.build_image_only_grid_figure(
                df=image_local_df,
                aux_dict=image_local_aux,
                key_col="key",
                figure_title=f"Image-only | local class_02 prototypes | seed {seed_id} | original (top) vs result (bottom)",
            )
            path = fig_dir / "image_only_local_grid.png"
            cvu.save_figure(fig_image_local, path, allow_overwrite=args.allow_overwrite)
            figure_paths["image_only_local"] = path

    if hsl_enabled:
        hsl_fig, optional_hsl_meta = cvu.build_optional_hsl_figure(global_records, max_items=hsl_max_items)
        if args.save_figures and hsl_fig is not None:
            path = output_dir / "figures" / "optional_hsl_exploration.png"
            cvu.save_figure(hsl_fig, path, allow_overwrite=args.allow_overwrite)
            figure_paths["optional_hsl"] = path
        else:
            cvu.close_figures([hsl_fig])

    manifest = cvu.build_manifest(
        seed_id=seed_id,
        config_path=config_path,
        cv_paths=cv_paths,
        output_dir=output_dir,
        csv_paths=csv_paths,
        figure_paths=figure_paths,
        data_meta=data_meta,
        simple_sigma=simple_sigma,
        simple_rules=simple_rules,
        image_grad_sigma=image_grad_sigma,
        image_rules=image_rules,
        optional_hsl_meta=optional_hsl_meta,
        simple_global_df=simple_global_df,
        simple_local_df=simple_local_df,
        image_global_df=image_global_df,
        image_local_df=image_local_df,
    )
    report = cvu.build_run_report_markdown(
        seed_id=seed_id,
        cv_paths=cv_paths,
        output_dir=output_dir,
        validation_df=validation_df,
        simple_global_df=simple_global_df,
        simple_local_df=simple_local_df,
        image_global_df=image_global_df,
        image_local_df=image_local_df,
        data_meta=data_meta,
    )
    cvu.write_json(manifest, output_dir / "manifest.json", allow_overwrite=args.allow_overwrite)
    cvu.write_text(report, output_dir / "run_report.md", allow_overwrite=args.allow_overwrite)

    log("analysis complete")
    log(f"run_simple={run_simple}")
    log(f"run_image_only={run_image_only}")
    for key, path in csv_paths.items():
        log(f"{key}: {path}")
    log(f"manifest: {output_dir / 'manifest.json'}")
    log(f"report: {output_dir / 'run_report.md'}")


if __name__ == "__main__":
    main()
