#!/usr/bin/env python
"""Step11AA: prepare final planner figures for interpretation.

This step does not rerun the planner and does not alter previous outputs. It
copies the trusted/regenerated Step11W figures into a single final folder and
creates one compact Step11Z summary figure from saved prototype-based metrics.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DEFAULT_STEP11W = RESULTS / "fossum_roi_x490_step11w_planner_figure_path_audit_20260526_145609"
DEFAULT_STEP11Z = RESULTS / "fossum_roi_x490_step11z_minimal_prototype_based_rerun_20260525_220614"


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_No data available._\n"
    view = df[[c for c in columns if c in df.columns]].head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.3f}")
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join("---" for _ in view.columns) + " |",
    ]
    for row in view.astype(str).values.tolist():
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
    return "\n".join(lines) + "\n"


def make_step11z_summary(step11z: Path, out_png: Path) -> dict[str, Any]:
    single_path = step11z / "step11z_single_auv_metrics.csv"
    multi_path = step11z / "step11z_multi_auv_metrics.csv"
    single = pd.read_csv(single_path) if single_path.exists() else pd.DataFrame()
    multi = pd.read_csv(multi_path) if multi_path.exists() else pd.DataFrame()
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle("Step11Z prototype-based planner results summary", fontsize=14)

    if not single.empty:
        c01 = single[single["case_id"].eq("C01_representative")].copy()
        labels = c01["run_name"].astype(str).str.replace("prototype_", "", regex=False).str.replace("_", "\n", regex=False)
        x = np.arange(len(c01))
        axes[0, 0].bar(x, pd.to_numeric(c01["regions_visited"], errors="coerce"), color="#4c78a8")
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(labels, fontsize=8)
        axes[0, 0].set_title("C01 single-AUV regions visited")
        axes[0, 0].set_ylim(0, 2.2)
        axes[0, 0].grid(axis="y", alpha=0.25)

        width = 0.38
        axes[0, 1].bar(x - width / 2, pd.to_numeric(c01["fraction_path_region_A"], errors="coerce"), width, label="region A", color="#4c78a8")
        axes[0, 1].bar(x + width / 2, pd.to_numeric(c01["fraction_path_region_B"], errors="coerce"), width, label="region B", color="#f58518")
        axes[0, 1].set_xticks(x)
        axes[0, 1].set_xticklabels(labels, fontsize=8)
        axes[0, 1].set_ylim(0, 1.05)
        axes[0, 1].set_title("C01 single-AUV path fractions")
        axes[0, 1].legend(fontsize=8)
        axes[0, 1].grid(axis="y", alpha=0.25)
    else:
        axes[0, 0].text(0.5, 0.5, "single metrics missing", ha="center")
        axes[0, 1].text(0.5, 0.5, "single metrics missing", ha="center")

    if not multi.empty:
        c01m = multi[multi["case_id"].eq("C01_representative")].copy()
        labels = c01m["strategy"].astype(str).str.replace("prototype_", "", regex=False).str.replace("_", "\n", regex=False)
        x = np.arange(len(c01m))
        width = 0.38
        axes[1, 0].bar(x - width / 2, pd.to_numeric(c01m["fleet_region_A_coverage"], errors="coerce"), width, label="region A", color="#4c78a8")
        axes[1, 0].bar(x + width / 2, pd.to_numeric(c01m["fleet_region_B_coverage"], errors="coerce"), width, label="region B", color="#f58518")
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(labels, fontsize=8)
        axes[1, 0].set_title("C01 multi-AUV regime coverage")
        axes[1, 0].legend(fontsize=8)
        axes[1, 0].grid(axis="y", alpha=0.25)

        baseline = c01m[c01m["strategy"].eq("baseline_STD")]
        baseline_std = float(baseline["fleet_collected_STD"].iloc[0]) if not baseline.empty else np.nan
        std_ratio = pd.to_numeric(c01m["fleet_collected_STD"], errors="coerce") / baseline_std if np.isfinite(baseline_std) and baseline_std else np.nan
        axes[1, 1].bar(x, std_ratio, color="#54a24b")
        axes[1, 1].axhline(0.85, color="red", linestyle="--", linewidth=1, label="85% baseline")
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels(labels, fontsize=8)
        axes[1, 1].set_ylim(0, 1.15)
        axes[1, 1].set_title("C01 multi-AUV STD retained")
        axes[1, 1].legend(fontsize=8)
        axes[1, 1].grid(axis="y", alpha=0.25)
    else:
        axes[1, 0].text(0.5, 0.5, "multi metrics missing", ha="center")
        axes[1, 1].text(0.5, 0.5, "multi metrics missing", ha="center")

    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
    return {
        "single_metrics": rel(single_path),
        "multi_metrics": rel(multi_path),
        "single_rows": int(len(single)),
        "multi_rows": int(len(multi)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare final planner figures for interpretation.")
    parser.add_argument("--step11w", type=Path, default=DEFAULT_STEP11W)
    parser.add_argument("--step11z", type=Path, default=DEFAULT_STEP11Z)
    parser.add_argument("--output-root", type=Path, default=RESULTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outdir = args.output_root.resolve() / f"fossum_roi_x490_step11aa_final_planner_figures_for_interpretation_{now_tag()}"
    final_dir = outdir / "final_planner_figures_for_interpretation"
    final_dir.mkdir(parents=True, exist_ok=False)

    sources = [
        (
            "01_step11b_information_map_objectives.png",
            args.step11w / "figures_regenerated" / "step11b_each_descriptor_over_information_map.png",
            "Step11B actual saved information_map objectives",
            "information_map",
        ),
        (
            "02_step11c_path_colored_by_region.png",
            args.step11w / "figures_regenerated" / "step11c_path_colored_by_region.png",
            "Step11C path colored by saved region masks",
            "region_A/region_B",
        ),
        (
            "03_step11d_clean_multi_auv_overlay.png",
            args.step11w / "figures_regenerated_standardized" / "step11d_standardized_region_overlay.png",
            "Step11D clean multi-AUV overlay over region masks",
            "region_A/region_B",
        ),
        (
            "04_step11d_overlap_and_distance_metrics.png",
            args.step11w / "figures_regenerated" / "step11d_overlay_vs_true_distance_panel.png",
            "Step11D overlap and distance metrics",
            "metrics",
        ),
    ]
    manifest_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for filename, src, description, background in sources:
        dst = final_dir / filename
        if src.exists():
            shutil.copy2(src, dst)
            status = "copied"
        else:
            warnings.append(f"Missing source figure: {src}")
            status = "missing_source"
        manifest_rows.append(
            {
                "final_figure": filename,
                "source_file": rel(src),
                "status": status,
                "background_type": background,
                "interpretation": description,
            }
        )

    summary_png = final_dir / "05_step11z_prototype_based_results_summary.png"
    summary_meta = make_step11z_summary(args.step11z, summary_png)
    manifest_rows.append(
        {
            "final_figure": summary_png.name,
            "source_file": f"{summary_meta['single_metrics']}; {summary_meta['multi_metrics']}",
            "status": "generated_from_metrics",
            "background_type": "metrics",
            "interpretation": "Step11Z prototype-based single/multi-AUV summary",
        }
    )

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(outdir / "final_planner_figures_manifest.csv", index=False)
    report = [
        "# Step11AA final planner figures for interpretation",
        "",
        f"Output: `{rel(outdir)}`",
        "",
        "## Interpretation rules",
        "",
        "- Step11B final figure uses actual saved information_map objectives, not old diagnostic backgrounds.",
        "- Step11C final figure uses path-colored-by-region because crossing_count alone can count small boundary-side switches.",
        "- Step11D final figures pair clean overlays with overlap/distance metrics; low literal overlap should not be overread as full regime separation.",
        "- Step11Z summary is the prototype-based methodological reference after the Step11Y correction.",
        "",
        "## Figure manifest",
        "",
        md_table(manifest, ["final_figure", "background_type", "status", "interpretation"], 10),
    ]
    if warnings:
        report += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    (outdir / "final_planner_figures_interpretation.md").write_text("\n".join(report), encoding="utf-8")

    checks = {
        "verdict": "STEP11AA_FINAL_FIGURES_READY" if not warnings else "STEP11AA_COMPLETED_WITH_WARNINGS",
        "output_dir": rel(outdir),
        "final_figures_dir": rel(final_dir),
        "figures_expected": 5,
        "figures_present": len(list(final_dir.glob("*.png"))),
        "warnings": warnings,
    }
    write_json(outdir / "step11aa_checks.json", checks)
    write_json(
        outdir / "step11aa_metadata.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "script": rel(Path(__file__)),
            "step11w_source": rel(args.step11w),
            "step11z_source": rel(args.step11z),
        },
    )
    shutil.copy2(Path(__file__), outdir / Path(__file__).name)

    print("STEP11AA FINAL FIGURES")
    print(f"Output: {rel(outdir)}")
    print(f"Figures present: {checks['figures_present']}/5")
    print(f"Verdict: {checks['verdict']}")
    return 0 if not warnings else 1


if __name__ == "__main__":
    raise SystemExit(main())
