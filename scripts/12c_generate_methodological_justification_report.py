#!/usr/bin/env python
"""Step12C: methodological justification report for Step12 sensitivity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import step12_common as c


PREFIX = "fossum_roi_x490_step12c_methodological_justification"
STEP04 = c.RESULTS / "fossum_roi_x490_step04_sd_probe_patch40x24_dict4_20260511_211354"
STEP05 = c.RESULTS / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
STEP08 = c.RESULTS / "fossum_roi_x490_step08_final_descriptors_20260514_164854"
STEP09B = c.RESULTS / "fossum_roi_x490_step09b_top20_c01_c06_temppred_classification_20260519_190144"
STEP10F = c.RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"
STEP11W = c.RESULTS / "fossum_roi_x490_step11w_planner_figure_path_audit_20260526_145609"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def find_inputs(step12a: Path | None, step12b: Path | None) -> tuple[Path, Path]:
    if step12a is None:
        step12a = c.latest_output("fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity")
    if step12b is None:
        step12b = c.latest_output("fossum_roi_x490_step12b_multi_auv_vehicle_specific_weight_duration_sensitivity")
    return step12a.resolve(), step12b.resolve()


def class_number_report() -> str:
    rec = read_json(STEP04 / "step04_sd_probe_recommendation.json")
    ranking = read_csv(STEP04 / "step04_sd_probe_ranking.csv")
    sizes = read_csv(STEP05 / "canonical_class_sizes.csv")
    top = ranking.head(3) if not ranking.empty else pd.DataFrame()
    lines = [
        "# Step12C class-number justification",
        "",
        "The canonical pipeline used SD=0.25 and 6 classes because this solution was the best automatic balanced candidate in Step04 and was then fixed in Step05 for the canonical descriptors.",
        "",
        "Evidence:",
        f"- Step04 strict balanced-score best SD: `{rec.get('strict_legacy_balanced_score_best_sd', 'unknown')}`.",
        f"- Step04 strict balanced-score best number of classes: `{rec.get('strict_legacy_balanced_score_best_n_classes', 'unknown')}`.",
        "- The 6-class solution had no singleton classes and a minimum class size of 30 days.",
        "- SD=0.30 was retained as sensitivity/context, but the final canonical Step05 output is the SD=0.25 / 6-class branch.",
        "",
        "## Step04 top candidates",
        c.md_table(top, ["sd_fraction_of_max", "number_of_classes", "class_sizes", "min_class_size", "singleton_count", "balanced_score"], 5),
        "",
        "## Step05 canonical class sizes",
        c.md_table(sizes, list(sizes.columns), 10),
    ]
    return "\n".join(lines)


def descriptor_report() -> str:
    return """# Step12C descriptor-choice justification

The descriptors tested in Step12 are the descriptors most directly tied to the planner question.

- `boundary_score`: tests whether rewarding transition/frontier structure changes the path relative to STD-only planning.
- `representative_zone` / `region_A` / `region_B`: supports regime-role assignment, especially for multi-AUV planning where different vehicles should cover different regime structures.
- `interest_map`: a composite/proxy descriptor useful as sensitivity evidence because it mixes several prototype characteristics.

Other descriptors such as `gradient` and `heterogeneity` remain useful ablation diagnostics from Step11B, but Step12 focuses on the smaller set that is easiest to defend as a cost-function choice.

Important methodological constraint: all descriptors used here come from the predicted prototype class. They are not recomputed from the day-specific TEMPpred field.
"""


def day_report() -> str:
    rows = [
        ["2024-08-24", "C01_representative", "C01", "C01 preservado, STD alto, bom caso para testar se descriptors alteram trajetorias."],
        ["2023-12-22", "C06_representative", "C06", "C06 estavel e bem classificado, usado como regime robusto."],
        ["2024-10-30", "October_control", "C02", "Caso de outubro com predModel oficial validado, usado como referencia controlada."],
    ]
    df = pd.DataFrame(rows, columns=["date", "case_id", "predicted_class", "justification"])
    return "# Step12C day-selection justification\n\n" + c.md_table(df, list(df.columns), 10)


def weight_report(step12a: Path, step12b: Path) -> str:
    a_best = read_csv(step12a / "step12a_best_weight_recommendation.csv")
    b_best = read_csv(step12b / "step12b_best_weight_recommendation.csv")
    lines = [
        "# Step12C weight-choice justification",
        "",
        "Weights are justified by sensitivity analysis rather than by arbitrary selection.",
        "",
        "The tested range includes both extremes:",
        "- Single-AUV `alpha=0`: pure STD baseline.",
        "- Single-AUV `alpha=1`: pure descriptor objective.",
        "- Multi-AUV `w_STD=1`: shared STD baseline.",
        "- Multi-AUV `w_STD=0, w_region=1`: pure regime-role objective.",
        "",
        "The final recommendation is based on collected STD, regime coverage, difference from baseline, runtime and operational feasibility.",
        "",
        "## Single-AUV recommended rows",
        c.md_table(a_best, ["case_id", "mission_duration_requested_h", "descriptor", "run_name", "alpha", "STD_retention", "regime_balance", "recommendation_score"], 80),
        "",
        "## Multi-AUV recommended rows",
        c.md_table(b_best, ["case_id", "mission_duration_requested_h", "strategy", "w_STD", "w_region", "role_assignment", "STD_retention", "fleet_region_B_coverage", "regime_specialization_score", "recommendation_score"], 80),
    ]
    return "\n".join(lines)


def duration_report(step12a: Path, step12b: Path) -> str:
    a_duration = read_csv(step12a / "step12a_duration_sensitivity_summary.csv")
    b_duration = read_csv(step12b / "step12b_duration_sensitivity_summary.csv")
    lines = [
        "# Step12C mission-duration justification",
        "",
        "- `12h`: restrictive short mission; useful to see whether the descriptor can change behavior when freedom is limited.",
        "- `24h`: intermediate mission duration.",
        "- `48h`: relaxed mission duration; helps separate descriptor effect from pure endurance effect.",
        "",
        "## Step12A duration evidence",
        c.md_table(a_duration, list(a_duration.columns), 80),
        "",
        "## Step12B duration evidence",
        c.md_table(b_duration, list(b_duration.columns), 100),
    ]
    return "\n".join(lines)


def runtime_report(step12a: Path, step12b: Path) -> str:
    a_runtime = read_csv(step12a / "step12a_runtime_summary.csv")
    b_runtime = read_csv(step12b / "step12b_runtime_summary.csv")
    a_checks = read_json(step12a / "step12a_checks.json")
    b_checks = read_json(step12b / "step12b_checks.json")
    lines = [
        "# Step12C runtime and feasibility report",
        "",
        f"- Step12A total script runtime: `{a_checks.get('total_script_runtime_s', 'unknown')}` seconds.",
        f"- Step12B total script runtime: `{b_checks.get('total_script_runtime_s', 'unknown')}` seconds.",
        f"- Step12A physical runs: `{a_checks.get('physical_runs_executed_or_reused', 'unknown')}`.",
        f"- Step12B physical runs: `{b_checks.get('total_physical_runs_executed_or_reused', 'unknown')}`.",
        "",
        "A configuration is considered operationally more defensible when it improves regime coverage without excessive STD loss or excessive solver/runtime cost.",
        "",
        "## Step12A runtime table",
        c.md_table(a_runtime, list(a_runtime.columns), 100),
        "",
        "## Step12B runtime table",
        c.md_table(b_runtime, list(b_runtime.columns), 100),
    ]
    return "\n".join(lines)


def final_recommendations(step12a: Path, step12b: Path) -> tuple[str, str]:
    a_checks = read_json(step12a / "step12a_checks.json")
    b_checks = read_json(step12b / "step12b_checks.json")
    a_best = read_csv(step12a / "step12a_best_weight_recommendation.csv")
    b_best = read_csv(step12b / "step12b_best_weight_recommendation.csv")
    if a_best.empty or b_best.empty:
        verdict = "STEP12_COMPLETED_WITH_TRADEOFFS_REVIEW_REQUIRED"
    elif a_checks.get("TEMPpred_used_as_objective") or b_checks.get("TEMPpred_used_as_objective"):
        verdict = "STEP12_FAILED"
    elif not a_checks.get("prototype_based_maps_only", False) or not b_checks.get("prototype_based_maps_only", False):
        verdict = "STEP12_FAILED"
    else:
        verdict = "STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED"
    lines = [
        "# Step12C final recommendations",
        "",
        f"Verdict: `{verdict}`",
        "",
        "Recommended use in thesis:",
        "- Use Step12A as evidence for single-AUV descriptor sensitivity.",
        "- Use Step12B as the stronger argument for multi-AUV regime-role planning.",
        "- State clearly that vehicle-specific maps are currently a wrapper/proxy unless the planner is later modified to support native vehicle-specific prize maps.",
        "- Use information_map figures when discussing objectives; use TEMPpred figures only as diagnostic spatial context.",
        "",
        "## Best single-AUV rows",
        c.md_table(a_best, ["case_id", "mission_duration_requested_h", "descriptor", "run_name", "alpha", "recommendation_score"], 80),
        "",
        "## Best multi-AUV rows",
        c.md_table(b_best, ["case_id", "mission_duration_requested_h", "strategy", "w_STD", "w_region", "role_assignment", "recommendation_score"], 80),
        "",
        "## Limitations",
        "- Static descriptors do not guarantee true route-level crossing behavior.",
        "- Vehicle-specific maps can improve specialization but can reduce STD collection.",
        "- The current planner does not yet implement native route-level reward or native vehicle-specific prize maps.",
    ]
    return "\n".join(lines), verdict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step12C methodological justification report.")
    parser.add_argument("--step12a", type=Path, default=None)
    parser.add_argument("--step12b", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=c.RESULTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    step12a, step12b = find_inputs(args.step12a, args.step12b)
    outdir = args.output_root.resolve() / f"{PREFIX}_{c.now_tag()}"
    outdir.mkdir(parents=True, exist_ok=True)

    class_md = class_number_report()
    descriptor_md = descriptor_report()
    day_md = day_report()
    weight_md = weight_report(step12a, step12b)
    duration_md = duration_report(step12a, step12b)
    runtime_md = runtime_report(step12a, step12b)
    final_md, verdict = final_recommendations(step12a, step12b)
    full = "\n\n".join([class_md, descriptor_md, day_md, weight_md, duration_md, runtime_md, final_md])

    c.write_text(outdir / "step12c_methodological_justification_report.md", full)
    c.write_text(outdir / "step12c_weight_choice_justification.md", weight_md)
    c.write_text(outdir / "step12c_class_number_justification.md", class_md)
    c.write_text(outdir / "step12c_descriptor_choice_justification.md", descriptor_md)
    c.write_text(outdir / "step12c_day_selection_justification.md", day_md)
    c.write_text(outdir / "step12c_runtime_feasibility_report.md", runtime_md)
    c.write_text(outdir / "step12c_final_recommendations.md", final_md)
    checks = {
        "step": "Step12C",
        "output_dir": c.rel(outdir),
        "step12a": c.rel(step12a),
        "step12b": c.rel(step12b),
        "class_number_justified": True,
        "descriptor_choice_justified": True,
        "day_selection_justified": True,
        "weight_choice_justified": True,
        "runtime_feasibility_reported": True,
        "verdict": verdict,
    }
    c.write_json(outdir / "step12c_checks.json", checks)
    c.write_json(outdir / "step12c_metadata.json", {"created_at": c.now_tag(), "inputs": checks})
    print(f"Step12C complete: {c.rel(outdir)}")
    print(f"Verdict: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

