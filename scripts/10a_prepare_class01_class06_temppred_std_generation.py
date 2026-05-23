"""Step10A: prepare C01/C06 TEMPpred/STD generation plan.

This stage does not generate TEMPpred/STD. It identifies canonical C01/C06
days, checks whether they already exist in Step06 October outputs, inventories
Filipa generation-related scripts/files, and writes a feasibility report plus
a prioritized generation plan.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = ROOT / "results"
DEFAULT_STEP00 = RESULTS_ROOT / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_STEP05 = RESULTS_ROOT / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
DEFAULT_STEP06 = RESULTS_ROOT / "october_surface_temppred_std_roi_x490_20260511_155923"
DEFAULT_STEP08 = RESULTS_ROOT / "fossum_roi_x490_step08_final_descriptors_20260514_164854"
DEFAULT_FILIPA_DATA = ROOT / "data" / "dadosParaPedro_Fresnel"

TARGET_CLASSES = [1, 6]
EXPECTED_COUNTS = {1: 41, 6: 72}
EXPECTED_TOTAL = 113
TERMS = [
    "TEMPpred",
    "STD",
    "predModel",
    "simulations",
    "realizations",
    "SGS",
    "DSS",
    "kriging",
    "geostatistical",
    "write14days",
    "HighRes",
    "HRes",
    "thetao",
    "BATHY",
    "LAT",
    "LON",
    "NetCDF",
    "ncread",
    "ncwrite",
]


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return None if not math.isfinite(value) else value
    return str(obj)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return path


def latest_step09() -> Path | None:
    candidates = [p for p in RESULTS_ROOT.glob("fossum_roi_x490_step09_october_temppred_descriptor_assignment_*") if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].resolve()


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out


def load_selected_dates(step00: Path, step05: Path, step06: Path, step08: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    assignments = normalize_dates(pd.read_csv(require(step05 / "canonical_assignments.csv", "Step05 canonical assignments")))
    dates370 = normalize_dates(pd.read_csv(require(step00 / "dates_370.csv", "Step00 dates_370")))
    if "time_index" in dates370.columns and "image_idx_0_based" not in dates370.columns:
        dates370 = dates370.rename(columns={"time_index": "image_idx_0_based"})
    if "day_index" not in dates370.columns:
        dates370["day_index"] = dates370["image_idx_0_based"].astype(int) + 1

    step06_dates = normalize_dates(pd.read_csv(require(step06 / "dates_october.csv", "Step06 dates_october")))
    descriptors = pd.read_csv(require(step08 / "step08_final_class_descriptors.csv", "Step08 descriptors"))
    descriptors = descriptors[["class_id", "class_label", "gradient_mean", "boundary_score", "interest_mean", "qualitative_regime_label"]].copy()

    selected = assignments[assignments["class_id"].astype(int).isin(TARGET_CLASSES)].copy()
    selected = selected.merge(
        dates370[["image_idx_0_based", "date"]].rename(columns={"date": "date_from_step00"}),
        on="image_idx_0_based",
        how="left",
    )
    selected["date_match_step00"] = selected["date"] == selected["date_from_step00"]
    selected = selected.merge(descriptors, on="class_id", how="left")
    selected["month"] = pd.to_datetime(selected["date"]).dt.strftime("%Y-%m")
    selected["is_october_2024"] = selected["date"].str.startswith("2024-10")
    selected["available_in_step06"] = selected["date"].isin(set(step06_dates["date"]))
    selected["needs_temppred_std_generation"] = ~selected["available_in_step06"]
    selected["class_label"] = selected["class_id"].map(lambda c: f"C{int(c):02d}") + "_" + selected["qualitative_regime_label"].astype(str)
    return selected, step06_dates, descriptors, dates370


def period_bucket(date: str) -> str:
    month = pd.to_datetime(date).month
    if month in [12, 1, 2]:
        return "winter"
    if month in [3, 4, 5]:
        return "spring"
    if month in [6, 7, 8]:
        return "summer"
    return "autumn"


def priority_list(selected: pd.DataFrame, step08: Path) -> pd.DataFrame:
    residual_path = step08 / "step08_member_to_prototype_residuals.csv"
    residuals = pd.read_csv(residual_path) if residual_path.exists() else pd.DataFrame()
    out = selected.copy()
    if not residuals.empty:
        residuals = residuals[["class_id", "image_idx_0_based", "rmse"]].copy()
        out = out.merge(residuals, on=["class_id", "image_idx_0_based"], how="left")
    else:
        out["rmse"] = np.nan
    out["period_bucket"] = out["date"].apply(period_bucket)
    out["class_interest_rank_score"] = (
        out["interest_mean"].astype(float) * 0.45
        + out["gradient_mean"].astype(float) * 0.30
        + out["boundary_score"].astype(float) * 0.25
    )
    rmse = out["rmse"].astype(float)
    if rmse.notna().any():
        mn, mx = rmse.min(), rmse.max()
        out["representative_score"] = 1.0 - ((rmse - mn) / (mx - mn if mx > mn else 1.0))
    else:
        out["representative_score"] = 0.5
    out["october_bonus"] = out["is_october_2024"].astype(int) * 2.0
    out["priority_score"] = out["october_bonus"] + out["class_interest_rank_score"] + 0.25 * out["representative_score"]
    out = out.sort_values(["priority_score", "class_id", "date"], ascending=[False, True, True]).reset_index(drop=True)
    out.insert(0, "priority_rank", np.arange(1, len(out) + 1))
    return out


def infer_language(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".m": "MATLAB",
        ".mlx": "MATLAB Live Script",
        ".py": "Python",
        ".ipynb": "Jupyter",
        ".json": "JSON",
        ".txt": "Text",
        ".par": "parameter",
    }.get(suffix, suffix.lstrip(".") or "unknown")


def probable_objective(path: Path, text: str, matched: list[str]) -> str:
    lower = (str(path.name) + "\n" + text).lower()
    if "write14days" in lower:
        return "Writes/exports multi-day simulation or prediction NetCDF outputs."
    if "predmodel" in lower or "temppred" in lower:
        return "Handles prediction model TEMPpred outputs."
    if "std" in lower and ("sim" in lower or "realization" in lower):
        return "Computes STD from simulation realizations."
    if "dss" in lower or "sgs" in lower or "kriging" in lower:
        return "Geostatistical simulation/kriging support."
    if "roi_x490" in lower:
        return "Applies ROI x490 crop to existing outputs."
    if "thetao" in lower or "hres" in lower:
        return "Reads or transforms HRes/CMEMS thetao fields."
    return "Relevant by keyword match; objective requires manual inspection."


def inventory_filipa_scripts(extra_roots: list[Path]) -> pd.DataFrame:
    roots = [ROOT / "scripts", ROOT / "data", *extra_roots]
    seen: set[Path] = set()
    rows: list[dict[str, Any]] = []
    suffixes = {".m", ".mlx", ".py", ".ipynb", ".txt", ".json", ".par", ".bat", ".sh"}
    for root in roots:
        if not root.exists():
            rows.append(
                {
                    "path": str(root),
                    "language": "missing_directory",
                    "probable_objective": "Requested search root does not exist in this clone.",
                    "matched_terms": "",
                    "matched_term_count": 0,
                    "generates_temppred": False,
                    "generates_std": False,
                    "limited_to_october": False,
                    "accepts_arbitrary_dates": False,
                    "hardcoded_paths": False,
                    "depends_on_matlab_or_toolboxes": False,
                    "can_run_batch": False,
                    "auto_generation_candidate": False,
                    "risk_or_limitation": "Missing directory.",
                }
            )
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            rp = path.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            lower_name = str(path).lower()
            text = ""
            if path.stat().st_size < 2_000_000 and path.suffix.lower() not in {".ipynb", ".mlx"}:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    text = ""
            raw_searchable = lower_name + "\n" + text
            searchable = raw_searchable.lower()
            matched = [term for term in TERMS if term.lower() in searchable]
            if not matched:
                continue
            lang = infer_language(path)
            hardcoded = bool(re.search(r"[A-Za-z]:\\|/home/|C:/|C:\\\\|Users\\", text))
            limited_oct = bool(re.search(r"2024[-_]?10|october|outubro|31-10|30-10|10-2024", searchable))
            arbitrary = bool(re.search(r"date|dates|day|daily|datetime|datenum", searchable)) and not limited_oct
            generates_temppred = bool(re.search(r"temppred|predmodel_?1|predmodel", searchable))
            generates_std = bool(re.search(r"\bSTD\b|StDev|stdev|standard deviation|STD_", raw_searchable))
            matlab_dep = lang.startswith("MATLAB") or "DSS.C.64.exe".lower() in searchable or ".exe" in searchable
            batch = bool(re.search(r"for .*date|for .*day|for .*i|batch|daily|loop", searchable))
            risk = []
            if hardcoded:
                risk.append("hardcoded paths")
            if limited_oct:
                risk.append("appears October-specific")
            if matlab_dep:
                risk.append("MATLAB/external executable dependency")
            if not generates_temppred and not generates_std:
                risk.append("may not generate TEMPpred/STD directly")
            rows.append(
                {
                    "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                    "language": lang,
                    "probable_objective": probable_objective(path, text, matched),
                    "matched_terms": "|".join(matched),
                    "matched_term_count": int(len(matched)),
                    "generates_temppred": bool(generates_temppred),
                    "generates_std": bool(generates_std),
                    "limited_to_october": bool(limited_oct),
                    "accepts_arbitrary_dates": bool(arbitrary),
                    "hardcoded_paths": bool(hardcoded),
                    "depends_on_matlab_or_toolboxes": bool(matlab_dep),
                    "can_run_batch": bool(batch),
                    "auto_generation_candidate": bool(
                        generates_temppred
                        and generates_std
                        and batch
                        and arbitrary
                        and not hardcoded
                        and not matlab_dep
                        and not limited_oct
                    ),
                    "risk_or_limitation": "; ".join(risk) if risk else "Needs manual validation before execution.",
                }
            )
    return pd.DataFrame(rows).drop_duplicates(subset=["path"]).sort_values(
        ["auto_generation_candidate", "generates_temppred", "generates_std", "matched_term_count", "path"],
        ascending=[False, False, False, False, True],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Step10A C01/C06 TEMPpred/STD generation plan.")
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--step05", type=Path, default=DEFAULT_STEP05)
    parser.add_argument("--step06", type=Path, default=DEFAULT_STEP06)
    parser.add_argument("--step08", type=Path, default=DEFAULT_STEP08)
    parser.add_argument("--filipa-data", type=Path, default=DEFAULT_FILIPA_DATA)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    step00 = args.step00.resolve()
    step05 = args.step05.resolve()
    step06 = args.step06.resolve()
    step08 = args.step08.resolve()
    filipa_data = args.filipa_data.resolve()
    out_dir = (args.output_root.resolve() / f"fossum_roi_x490_step10a_class01_class06_temppred_std_generation_plan_{now_tag()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)

    selected, step06_dates, descriptors, dates370 = load_selected_dates(step00, step05, step06, step08)
    c01 = selected[selected["class_id"].astype(int) == 1].copy()
    c06 = selected[selected["class_id"].astype(int) == 6].copy()
    available = selected[selected["available_in_step06"]].copy()
    missing = selected[selected["needs_temppred_std_generation"]].copy()
    priority = priority_list(selected, step08)

    c01.to_csv(out_dir / "step10a_class01_dates.csv", index=False)
    c06.to_csv(out_dir / "step10a_class06_dates.csv", index=False)
    selected.to_csv(out_dir / "step10a_class01_class06_all_selected_dates.csv", index=False)
    available.to_csv(out_dir / "step10a_selected_dates_already_available_in_step06.csv", index=False)
    missing.to_csv(out_dir / "step10a_selected_dates_missing_temppred_std.csv", index=False)
    priority.to_csv(out_dir / "step10a_generation_priority_list.csv", index=False)

    inventory = inventory_filipa_scripts(
        [
            filipa_data,
            filipa_data / "01.Data",
            filipa_data / "02.Simulations",
        ]
    )
    inventory.to_csv(out_dir / "step10a_filipa_scripts_inventory.csv", index=False)

    strong_candidates = inventory[inventory["auto_generation_candidate"].astype(bool)].copy()
    missing_inputs = []
    if not filipa_data.exists():
        missing_inputs.append({"missing_input": str(filipa_data), "reason": "Requested dadosParaPedro_Fresnel root is absent in this clone."})
    source_missing = []
    if "source_file" in step06_dates.columns:
        for src in step06_dates["source_file"].dropna().astype(str).head(31):
            if src and not Path(src).exists():
                source_missing.append(src)
    if source_missing:
        missing_inputs.append({"missing_input": "Step06 source NetCDF paths", "reason": f"{len(source_missing)} source files listed in dates_october.csv are not present at their recorded absolute paths."})
    missing_inputs_df = pd.DataFrame(missing_inputs)
    missing_inputs_df.to_csv(out_dir / "step10a_required_inputs_missing.csv", index=False)

    ready = bool(len(strong_candidates) > 0 and missing_inputs_df.empty)
    verdict = "READY_FOR_CLASS01_CLASS06_TEMPRED_STD_GENERATION" if ready else "NEEDS_FILIPA_SCRIPT_OR_INPUTS"

    checks = {
        "class01_count": int(len(c01)),
        "class06_count": int(len(c06)),
        "total_class01_class06": int(len(selected)),
        "expected_class01_count": 41,
        "expected_class06_count": 72,
        "expected_total": 113,
        "counts_match_expected": int(len(c01)) == 41 and int(len(c06)) == 72 and int(len(selected)) == 113,
        "dates_mapped_with_dates_370": bool(selected["date_match_step00"].all()),
        "already_available_in_step06_count": int(len(available)),
        "missing_temppred_std_count": int(len(missing)),
        "filipa_requested_root_exists": bool(filipa_data.exists()),
        "inventory_rows": int(len(inventory)),
        "strong_auto_generation_candidates": int(len(strong_candidates)),
        "dependencies_or_inputs_missing": int(len(missing_inputs_df)),
        "verdict": verdict,
    }
    write_json(out_dir / "step10a_checks.json", checks)

    step09 = latest_step09()
    step09_summary = ""
    if step09 and (step09 / "step09_temppred_classification_assignments.csv").exists():
        df09 = pd.read_csv(step09 / "step09_temppred_classification_assignments.csv")
        counts09 = df09["assigned_class_id"].value_counts().sort_index().to_dict()
        step09_summary = f"Latest Step09: `{step09}`. October assignment counts: {counts09}."

    feasible_lines = [
        "# Step10A Generation Feasibility Report",
        "",
        f"- Verdict: **{verdict}**",
        f"- Requested Filipa data root exists: {filipa_data.exists()}",
        f"- Inventory rows: {len(inventory)}",
        f"- Strong automatic candidates: {len(strong_candidates)}",
        f"- Missing input/dependency rows: {len(missing_inputs_df)}",
        "",
        "## Interpretation",
    ]
    if ready:
        feasible_lines.append("At least one candidate appears to support batch TEMPpred/STD generation for arbitrary dates, and no required inputs were flagged missing. Run a dry-run wrapper before actual generation.")
    else:
        feasible_lines.append("Automatic generation is not confirmed. The requested `data/dadosParaPedro_Fresnel` root is absent and/or Step06 source NetCDF paths are absolute paths from another machine. Use the inventory to request the missing Filipa scripts/inputs or validate equivalent local paths.")
    feasible_lines.extend(["", "## Strong Candidates"])
    if strong_candidates.empty:
        feasible_lines.append("- None found.")
    else:
        feasible_lines.extend([f"- `{p}`" for p in strong_candidates["path"].head(20)])
    (out_dir / "step10a_generation_feasibility_report.md").write_text("\n".join(feasible_lines), encoding="utf-8")

    plan_lines = [
        "# Step10A Generation Plan",
        "",
        "## Options",
        "- Complete generation: all 113 C01/C06 days.",
        "- Priority generation: start with top N rows from `step10a_generation_priority_list.csv`, especially any October rows and the most representative/high-interest C01/C06 days.",
        "",
        "## Safe Execution",
        "Do not run generation directly until the Filipa source scripts and NetCDF inputs are confirmed. Use a dry-run wrapper first, then generate a small pilot set.",
        "",
        f"Verdict: **{verdict}**",
    ]
    (out_dir / "step10a_generation_plan.md").write_text("\n".join(plan_lines), encoding="utf-8")
    manual_lines = [
        "# Step10A Manual Or MATLAB Execution Instructions",
        "",
        "1. Restore or map `data/dadosParaPedro_Fresnel` with `01.Data` and `02.Simulations`.",
        "2. Verify scripts that produce `*_predModel_1.nc` and STD from realizations.",
        "3. Confirm whether date inputs are hardcoded or parameterized.",
        "4. Run one dry-run/pilot day before batch generation.",
        "5. Crop generated TEMPpred/STD to ROI x490 using the Step06 ROI logic.",
    ]
    (out_dir / "step10a_manual_or_matlab_execution_instructions.md").write_text("\n".join(manual_lines), encoding="utf-8")

    summary_lines = [
        "# Step10A Summary",
        "",
        f"- C01 days: {len(c01)}",
        f"- C06 days: {len(c06)}",
        f"- Total selected: {len(selected)}",
        f"- Already available in Step06: {len(available)}",
        f"- Missing TEMPpred/STD: {len(missing)}",
        f"- Verdict: **{verdict}**",
        f"- {step09_summary}" if step09_summary else "- Step09 output not found.",
    ]
    (out_dir / "step10a_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    report_lines = [
        "# Step10A C01/C06 TEMPpred/STD Generation Preparation Report",
        "",
        "## A. Step09 Context",
        step09_summary or "No Step09 output was found.",
        "",
        "## B. C01/C06 Selection",
        f"- C01: {len(c01)} days",
        f"- C06: {len(c06)} days",
        f"- Total: {len(selected)} days",
        f"- Available in Step06: {len(available)}",
        f"- Missing generation: {len(missing)}",
        "",
        "## C. Filipa Script Inventory",
        f"- Inventory rows: {len(inventory)}",
        f"- Strong automatic generation candidates: {len(strong_candidates)}",
        "",
        "## D. Generation Feasibility",
        f"- Verdict: **{verdict}**",
        "- Reason: automatic generation requires confirmed Filipa source tree/scripts and source NetCDF inputs. This clone does not contain the requested `data/dadosParaPedro_Fresnel` directory.",
        "",
        "## E. Recommended Next Step",
        "Run a pilot generation only after restoring/confirming Filipa scripts and inputs. Until then, continue STD+descriptor fusion only for the already available October Step06 days.",
    ]
    (out_dir / "step10a_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    integrated = [
        "# Integrated Step09 Step10A Report",
        "",
        "## Step09",
        step09_summary or "Step09 not found.",
        "",
        "## Step10A",
        f"C01={len(c01)}, C06={len(c06)}, available_in_step06={len(available)}, missing={len(missing)}.",
        "",
        "## Verdicts",
        "- Step09: READY_FOR_STD_DESCRIPTOR_FUSION_FOR_OCTOBER" if step09_summary else "- Step09: NOT_VERIFIED",
        f"- Step10A: {verdict}",
    ]
    (out_dir / "step09_step10a_integrated_report.md").write_text("\n".join(integrated), encoding="utf-8")

    metadata = {
        "generated_at": datetime.now().isoformat(),
        "script": str(Path(__file__).resolve()),
        "inputs": {"step00": str(step00), "step05": str(step05), "step06": str(step06), "step08": str(step08), "filipa_data": str(filipa_data), "latest_step09": str(step09) if step09 else ""},
        "checks": checks,
    }
    write_json(out_dir / "step10a_metadata.json", metadata)
    print(f"Step10A complete: {out_dir}")
    print(f"C01={len(c01)} C06={len(c06)} total={len(selected)} available_step06={len(available)} missing={len(missing)}")
    print(f"Verdict: {verdict}")


if __name__ == "__main__":
    main()
