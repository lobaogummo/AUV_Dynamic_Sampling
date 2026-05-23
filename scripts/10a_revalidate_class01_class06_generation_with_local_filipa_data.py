"""Revalidate Step10A with local Filipa data for C01/C06 TEMPpred/STD generation.

This script does not rerun Step09, does not retrain Fossum, and does not
generate the 113 C01/C06 days. It audits local Filipa data/scripts, confirms
the previous Step10A date selection, chooses a small pilot list, and reports
whether Step10B can be executed automatically on this machine.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DEFAULT_STEP00 = RESULTS / "fossum_roi_x490_step00_dataset_20260509_232915"
DEFAULT_STEP05 = RESULTS / "fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755"
DEFAULT_STEP08 = RESULTS / "fossum_roi_x490_step08_final_descriptors_20260514_164854"
DEFAULT_STEP09 = RESULTS / "fossum_roi_x490_step09_october_temppred_descriptor_assignment_20260515_165018"
DEFAULT_PREV_STEP10A = RESULTS / "fossum_roi_x490_step10a_class01_class06_temppred_std_generation_plan_20260515_165612"

FILIPA_CANDIDATES = [
    ROOT / "data" / "dadosParaPedro_Fresnel" / "dadosParaPedro_Fresnel",
    ROOT / "data" / "dadosParaPedro_Fresnel",
]

DATA_SUFFIXES = {".nc", ".mat", ".gslib", ".out", ".par", ".txt", ".exe"}
SCRIPT_SUFFIXES = {".m", ".py", ".ipynb", ".mlx", ".bat", ".sh"}
SCRIPT_TERMS = [
    "TEMPpred",
    "STD",
    "predModel",
    "simulations",
    "realizations",
    "geostatistical",
    "kriging",
    "SGS",
    "DSS",
    "write14days",
    "thetao",
    "HRes",
    "HighRes",
    "variogram",
    "covariance",
    "cosgsim",
    "direct sequential simulation",
    "nbrSim",
]


def tag() -> str:
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


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def find_filipa_root() -> Path:
    for candidate in FILIPA_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()
    matches = [p for p in (ROOT / "data").rglob("dadosParaPedro_Fresnel") if p.is_dir()]
    if matches:
        deepest = sorted(matches, key=lambda p: len(p.parts), reverse=True)[0]
        if (deepest / "00.Code").exists() or (deepest / "01.Data").exists():
            return deepest.resolve()
    raise FileNotFoundError("Could not find local dadosParaPedro_Fresnel root.")


def read_previous_step10a(prev: Path) -> dict[str, pd.DataFrame]:
    files = {
        "c01": "step10a_class01_dates.csv",
        "c06": "step10a_class06_dates.csv",
        "selected": "step10a_class01_class06_all_selected_dates.csv",
        "missing": "step10a_selected_dates_missing_temppred_std.csv",
        "priority": "step10a_generation_priority_list.csv",
    }
    return {k: pd.read_csv(require(prev / name, name)) for k, name in files.items()}


def confirm_step10a(prev_frames: dict[str, pd.DataFrame], step00: Path, step05: Path) -> dict[str, Any]:
    selected = prev_frames["selected"].copy()
    dates370 = pd.read_csv(require(step00 / "dates_370.csv", "Step00 dates_370.csv"))
    if "image_idx_0_based" not in dates370.columns and "time_index" in dates370.columns:
        dates370 = dates370.rename(columns={"time_index": "image_idx_0_based"})
    if "image_idx_0_based" not in dates370.columns:
        dates370["image_idx_0_based"] = np.arange(len(dates370), dtype=int)
    assign = pd.read_csv(require(step05 / "canonical_assignments.csv", "Step05 canonical_assignments.csv"))
    c01_count = int((selected["class_id"].astype(int) == 1).sum())
    c06_count = int((selected["class_id"].astype(int) == 6).sum())
    merged = selected.merge(
        dates370[["image_idx_0_based", "date"]].rename(columns={"date": "date_step00"}),
        on="image_idx_0_based",
        how="left",
    )
    merged = merged.merge(
        assign[["image_idx_0_based", "class_id"]].rename(columns={"class_id": "class_id_step05"}),
        on="image_idx_0_based",
        how="left",
    )
    return {
        "class01_count": c01_count,
        "class06_count": c06_count,
        "total": int(len(selected)),
        "counts_match_expected": c01_count == 41 and c06_count == 72 and len(selected) == 113,
        "dates_match_step00": bool((pd.to_datetime(merged["date"]).dt.strftime("%Y-%m-%d") == pd.to_datetime(merged["date_step00"]).dt.strftime("%Y-%m-%d")).all()),
        "classes_match_step05": bool((merged["class_id"].astype(int) == merged["class_id_step05"].astype(int)).all()),
        "date_min": str(selected["date"].min()),
        "date_max": str(selected["date"].max()),
        "october_2024_c01_c06_count": int(selected["date"].astype(str).str.startswith("2024-10").sum()),
    }


def nc_header(path: Path) -> tuple[str, str]:
    try:
        import xarray as xr

        ds = xr.open_dataset(path, decode_times=False)
        dims = dict(ds.sizes)
        vars_ = {name: list(ds[name].shape) for name in ds.variables}
        ds.close()
        return json.dumps(dims), json.dumps(vars_)
    except Exception as exc:
        return "", f"INSPECTION_FAILED: {exc}"


_NC_SIGNATURE_CACHE: dict[str, tuple[str, str]] = {}


def nc_signature_key(path: Path) -> str:
    lower = str(path).lower()
    if "01.data" in lower and "all" in lower and "thetao" in lower:
        return "all_thetao"
    if "01.data" in lower and "october" in lower and "hres" in lower:
        return "october_hres"
    if "02.simulations" in lower and "predmodel" in lower:
        return "predmodel"
    return rel(path)


def classify_data_file(path: Path) -> dict[str, Any]:
    name = path.name.lower()
    parent = str(path.parent).lower()
    ext = path.suffix.lower()
    contains_temppred = "temppred" in name or "predmodel" in name
    contains_std = "std" in name or "predmodel" in name
    contains_100 = "sim_" in name or "predmodel" in name or "02.simulations" in parent
    if "01.data" in parent and "all" in parent and "thetao" in name:
        objective = "CMEMS raw 370-day thetao input."
        role = "input"
    elif "01.data" in parent and ("hres" in parent or "hres" in name):
        objective = "High-resolution CMEMS/HRes input window."
        role = "intermediate_input"
    elif "02.simulations" in parent and "predmodel" in name:
        objective = "Filipa geostatistical simulation output with TEMPpred/STD."
        role = "output"
    elif ext == ".exe":
        objective = "External DSS simulation executable."
        role = "dependency"
    elif ext in {".gslib", ".out", ".par"}:
        objective = "GSLIB/DSS simulation input or output."
        role = "intermediate"
    else:
        objective = "Relevant local Filipa data/dependency file."
        role = "unknown"
    dims, vars_ = ("", "")
    if ext == ".nc":
        key = nc_signature_key(path)
        if key not in _NC_SIGNATURE_CACHE:
            _NC_SIGNATURE_CACHE[key] = nc_header(path)
        dims, vars_ = _NC_SIGNATURE_CACHE[key]
    return {
        "path": rel(path),
        "type": role,
        "extension": ext,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
        "modified": path.stat().st_mtime,
        "modified_iso": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "probable_objective": objective,
        "variables_or_dims": vars_,
        "dimensions": dims,
        "contains_TEMPpred": bool(contains_temppred),
        "contains_STD": bool(contains_std),
        "contains_100_realizations": bool(contains_100),
        "input_or_output": role,
    }


def build_data_inventory(filipa_root: Path) -> pd.DataFrame:
    rows = []
    for path in filipa_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in DATA_SUFFIXES:
            rows.append(classify_data_file(path))
    return pd.DataFrame(rows).sort_values(["type", "path"]).reset_index(drop=True)


def script_confidence(path: Path, text: str) -> str:
    lower = (path.name + "\n" + text).lower()
    if path.name.lower() in {"runsimulations.m", "write14days.m"}:
        return "STRONG_CANDIDATE"
    if any(t in lower for t in ["temppred", "predmodel", "dss", "nbrsim", "write14days"]):
        return "POSSIBLE"
    if any(t in lower for t in ["thetao", "hres", "highres", "kriging", "variogram"]):
        return "WEAK"
    return "NOT_RELEVANT"


def probable_script_objective(path: Path, text: str) -> str:
    lower = (path.name + "\n" + text).lower()
    if path.name.lower() == "write14days.m":
        return "Builds 14-day CMEMS windows and interpolates them to HRes; currently October/hardcoded paths."
    if path.name.lower() == "runsimulations.m":
        return "Runs DSS geostatistical simulations and writes predModel_N.nc with TEMPpred/STD; currently October/hardcoded paths."
    if "readoutput" in path.name.lower():
        return "Reads DSS simulation realizations and computes median/IQD/STD."
    if "givecoordinateinformation" in path.name.lower():
        return "Writes scene.gslib and injects TEMPpred/STD variables into predModel NetCDF."
    if "writealldata" in path.name.lower():
        return "Builds GSLIB real-data coordinates for output days."
    return "Relevant script by keyword match."


def script_inventory(filipa_root: Path) -> pd.DataFrame:
    rows = []
    for path in filipa_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCRIPT_SUFFIXES:
            continue
        text = ""
        if path.stat().st_size < 2_000_000 and path.suffix.lower() not in {".ipynb", ".mlx"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
        searchable = (path.name + "\n" + text).lower()
        matched = [term for term in SCRIPT_TERMS if term.lower() in searchable]
        if not matched and path.suffix.lower() not in {".m", ".py"}:
            continue
        hardcoded = bool(re.search(r"[A-Za-z]:\\|I:\\|F:\\|C:\\|/home/", text))
        october = bool(re.search(r"2024-10|october|outubro|202410|10-2024", searchable))
        matlab_dep = path.suffix.lower() in {".m", ".mlx"} or "projcrs" in searchable or "ncread" in searchable
        exe_dep = "dss.c.64.exe" in searchable or ".exe" in searchable
        arbitrary_dates = bool(re.search(r"preddate|datetime|datestr|daydate|startdate|enddate", searchable))
        creates_temppred = bool(re.search(r"nccreate\s*\([^\n]+['\"]TEMPpred['\"]", text, flags=re.IGNORECASE))
        creates_std = bool(re.search(r"nccreate\s*\([^\n]+['\"]STD['\"]", text, flags=re.IGNORECASE))
        generates_predmodel = "predmodel" in searchable and ("nccreate" in searchable or "copyfile" in searchable)
        generates_temppred_std = creates_temppred and creates_std
        can_run_batch = bool(re.search(r"for .*day|for daydate|for .*i|batch", searchable))
        confidence = script_confidence(path, text)
        rows.append(
            {
                "path": rel(path),
                "language": "MATLAB" if path.suffix.lower() in {".m", ".mlx"} else "Python" if path.suffix.lower() == ".py" else path.suffix.lower().lstrip("."),
                "probable_objective": probable_script_objective(path, text),
                "matched_terms": "|".join(matched),
                "inputs_inferred": "CMEMS/HRes NetCDF, GSLIB hard data, DSS executable" if confidence in {"STRONG_CANDIDATE", "POSSIBLE"} else "",
                "outputs_inferred": "predModel_N.nc with TEMPpred/STD" if generates_predmodel or generates_temppred_std else "",
                "hardcoded_dates": bool(october),
                "hardcoded_paths": bool(hardcoded),
                "depends_on_matlab_or_toolboxes": bool(matlab_dep),
                "depends_on_external_executable": bool(exe_dep),
                "allows_date_selection": bool(arbitrary_dates),
                "generates_predModel_1_nc": bool(generates_predmodel),
                "generates_TEMPpred_STD_directly": bool(generates_temppred_std),
                "can_run_batch": bool(can_run_batch),
                "confidence": confidence,
            }
        )
    order = {"STRONG_CANDIDATE": 0, "POSSIBLE": 1, "WEAK": 2, "NOT_RELEVANT": 3}
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["_order"] = out["confidence"].map(order).fillna(9)
    return out.sort_values(["_order", "path"]).drop(columns=["_order"]).reset_index(drop=True)


def available_dates(filipa_root: Path, selected: pd.DataFrame) -> pd.DataFrame:
    all_nc = filipa_root / "01.Data" / "ALL" / "thetao_20260427.nc"
    hres_dir = filipa_root / "01.Data" / "October" / "HRes"
    pred_root = filipa_root / "02.Simulations" / "HighRes"
    rows = []
    for _, row in selected.iterrows():
        date = pd.to_datetime(row["date"])
        ymd = date.strftime("%Y%m%d")
        next_date = date + pd.Timedelta(days=1)
        ddmmyyyy = next_date.strftime("%d-%m-%Y")
        hres_match = list(hres_dir.glob(f"*{ymd}*HResNew.nc")) if hres_dir.exists() else []
        pred_match = list(pred_root.glob(f"Daily_dpt_{ymd}/{ddmmyyyy}_predModel_1.nc")) if pred_root.exists() else []
        raw_available = all_nc.exists()
        if pred_match:
            status = "predmodel_ready"
            feasible = "READY_TO_EXTRACT_EXISTING_OUTPUT"
        elif hres_match:
            status = "hres_available_requires_simulation"
            feasible = "REQUIRES_MATLAB_DSS_SIMULATION"
        elif raw_available:
            status = "raw_cmems_available_requires_hres_and_simulation"
            feasible = "REQUIRES_WRITE14DAYS_PLUS_MATLAB_DSS_ADAPTATION"
        else:
            status = "missing_raw_input"
            feasible = "NOT_FEASIBLE_WITH_LOCAL_DATA"
        rows.append(
            {
                "date": row["date"],
                "day_index_370": int(row.get("day_index", row.get("image_idx_0_based", -1) + 1)),
                "image_idx_0_based": int(row["image_idx_0_based"]),
                "class_id": int(row["class_id"]),
                "class_label": row.get("class_label", f"C{int(row['class_id']):02d}"),
                "raw_all_thetao_available": bool(raw_available),
                "hres_file_available": bool(hres_match),
                "predmodel_file_available": bool(pred_match),
                "hres_file": rel(hres_match[0]) if hres_match else "",
                "predmodel_file": rel(pred_match[0]) if pred_match else "",
                "input_availability_status": status,
                "generation_feasibility": feasible,
            }
        )
    return pd.DataFrame(rows)


def select_pilot(priority: pd.DataFrame, availability: pd.DataFrame) -> pd.DataFrame:
    merged = priority.merge(
        availability[
            [
                "date",
                "class_id",
                "input_availability_status",
                "generation_feasibility",
                "raw_all_thetao_available",
                "hres_file_available",
                "predmodel_file_available",
            ]
        ],
        on=["date", "class_id"],
        how="left",
    )
    picks = []
    for cls in [1, 6]:
        cls_df = merged[merged["class_id"].astype(int) == cls].sort_values("priority_rank")
        picks.append(cls_df.head(2).copy())
    pilot = pd.concat(picks, ignore_index=True)
    extra = []
    for cls in [1, 6]:
        cls_df = merged[merged["class_id"].astype(int) == cls].sort_values("priority_score", ascending=False)
        cand = cls_df.head(1)
        if not cand.empty:
            extra.append(cand)
    if extra:
        pilot = pd.concat([pilot, *extra], ignore_index=True).drop_duplicates(subset=["date", "class_id"])
    pilot = pilot.sort_values(["class_id", "priority_rank"]).head(6).copy()
    reasons = []
    for _, row in pilot.iterrows():
        cls = int(row["class_id"])
        rank = int(row["priority_rank"])
        reasons.append(f"Top-priority C{cls:02d} pilot candidate from Step10A priority list (rank {rank}); raw CMEMS available locally.")
    pilot["selection_reason"] = reasons
    rename = {"day_index": "day_index_370"}
    pilot = pilot.rename(columns=rename)
    cols = [
        "date",
        "day_index_370",
        "image_idx_0_based",
        "class_id",
        "class_label",
        "selection_reason",
        "input_availability_status",
        "generation_feasibility",
        "priority_rank",
        "priority_score",
    ]
    return pilot[cols].reset_index(drop=True)


def write_reports(
    out: Path,
    checks: dict[str, Any],
    filipa_root: Path,
    data_inv: pd.DataFrame,
    script_inv: pd.DataFrame,
    pilot: pd.DataFrame,
    can_execute_auto: bool,
    matlab_available: bool,
    dss_available: bool,
) -> None:
    strong = script_inv[script_inv["confidence"].eq("STRONG_CANDIDATE")] if not script_inv.empty else pd.DataFrame()
    lines = [
        "# Step10A Revalidation With Local Filipa Data",
        "",
        f"- Filipa root: `{filipa_root}`",
        f"- C01 count: {checks['class01_count']}",
        f"- C06 count: {checks['class06_count']}",
        f"- Total C01+C06: {checks['total']}",
        f"- October C01/C06 rows: {checks['october_2024_c01_c06_count']}",
        f"- Local data inventory rows: {len(data_inv)}",
        f"- Local script inventory rows: {len(script_inv)}",
        f"- Strong scripts: {len(strong)}",
        f"- MATLAB available on PATH: {matlab_available}",
        f"- DSS executable found: {dss_available}",
        f"- Automatic pilot generation now: {'YES' if can_execute_auto else 'NO'}",
        "",
        "## Interpretation",
        "The local repository now contains the original Filipa data tree, including raw `thetao_20260427.nc`, October HRes windows, October predModel outputs, MATLAB scripts, and the DSS executable. However, the selected C01/C06 dates are outside October, while ready HRes/predModel outputs are only materialized for 2024-09-30 to 2024-11-02.",
        "",
        "Generating C01/C06 pilot outputs therefore requires adapting/running the Filipa MATLAB pipeline: first create HRes 14-day windows from the 370-day CMEMS file, then run DSS simulations and write `predModel_N.nc` files with `TEMPpred` and `STD`.",
        "",
        "## Strong Scripts",
    ]
    if strong.empty:
        lines.append("- None.")
    else:
        for _, row in strong.iterrows():
            lines.append(f"- `{row['path']}`: {row['probable_objective']}")
    lines.extend(["", "## Pilot Dates"])
    for _, row in pilot.iterrows():
        lines.append(f"- {row['date']} C{int(row['class_id']):02d}: {row['generation_feasibility']}")
    verdict = "READY_FOR_STEP10B_PILOT_GENERATION" if can_execute_auto else "NEEDS_FILIPA_SCRIPT_OR_INPUTS"
    lines.extend(["", f"Final verdict: **STEP10A_REVALIDATED_WITH_LOCAL_DATA / {verdict}**"])
    (out / "step10a_revalidation_report.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "step10a_revalidation_summary.md").write_text("\n".join(lines[:22]), encoding="utf-8")

    if not can_execute_auto:
        reason = [
            "# Step10B Not Created Reason",
            "",
            "Step10B was not created/executed as an automatic generator because the local ready outputs do not cover C01/C06 dates and the available generation scripts are MATLAB/DSS scripts with hardcoded paths/date ranges.",
            "",
            "Blocking items:",
            f"- MATLAB on PATH: {matlab_available}",
            f"- DSS executable found: {dss_available}",
            "- `write14days.m` is hardcoded to `I:\\dadosParaPedro_Fresnel` and October output paths.",
            "- `runSimulations.m` is hardcoded to `I:\\dadosParaPedro_Fresnel`, `01.Data\\October\\HRes`, and `predDate = datetime('2024-10-30') + dayDate - 1`.",
            "- C01/C06 selected dates are outside October and have no ready HRes/predModel outputs.",
        ]
        (out / "step10b_not_created_reason.md").write_text("\n".join(reason), encoding="utf-8")

    missing = [
        {
            "missing_or_blocking_item": "Adapted MATLAB batch wrapper for arbitrary C01/C06 dates",
            "reason": "Existing scripts contain hardcoded I:/ paths and October-specific date/output folders.",
        },
        {
            "missing_or_blocking_item": "HRes windows for selected C01/C06 pilot dates",
            "reason": "Only October HRes NetCDF files are present; selected C01/C06 dates are 2023-12 to 2024-09.",
        },
    ]
    if not matlab_available:
        missing.append({"missing_or_blocking_item": "MATLAB on PATH", "reason": "Needed to run the original Filipa scripts directly."})
    pd.DataFrame(missing).to_csv(out / "step10a_missing_inputs_for_generation.csv", index=False)

    manual = [
        "# Step10A Manual Execution Instructions",
        "",
        "1. Adapt `write14days.m` so `File`, `outputDataPath`, `outputHresPath`, and the date loop are parameters.",
        "2. For each pilot date D, create the same HRes input window expected by `runSimulations.m`.",
        "3. Adapt `runSimulations.m` so `ProjP`, `DataPath`, `predDate`, and `dayDate` are parameters.",
        "4. Run only the selected pilot dates first, not all 113 C01/C06 dates.",
        "5. Validate that each generated `predModel_1.nc` contains `TEMPpred`, `STD`, `LAT`, `LON`, and `BATHY`.",
        "6. After predModels exist, run a Step10B extraction/ROI script to crop to x490 and produce `[N,72,117]` arrays.",
    ]
    (out / "step10a_manual_execution_instructions.md").write_text("\n".join(manual), encoding="utf-8")

    questions = [
        "# Questions For Filipa",
        "",
        "- Can `write14days.m` and `runSimulations.m` be parameterized for arbitrary dates outside October?",
        "- Is `thetao_20260427.nc` the intended CMEMS source for all 370 canonical days?",
        "- Should Step10B use `TEMPpred(:,:,1)` or `TEMPpred(:,:,2)` when `outputDays = 2` for a target date?",
        "- Are the current variogram values valid for all seasons/classes, or only for the October example?",
        "- Is MATLAB Mapping Toolbox required for `projcrs/projfwd`, and is DSS.C.64.exe the correct executable for this PC?",
    ]
    (out / "step10a_questions_for_filipa.md").write_text("\n".join(questions), encoding="utf-8")

    rec = [
        "# Step10A Next Step Recommendation",
        "",
        "Recommended next step: create a MATLAB dry-run/pilot wrapper for the 4 selected dates, then run Step10B extraction only after the pilot predModel files are generated.",
        "",
        "Do not run all 113 C01/C06 days yet.",
    ]
    (out / "step10a_next_step_recommendation.md").write_text("\n".join(rec), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revalidate Step10A with local Filipa data.")
    parser.add_argument("--step00", type=Path, default=DEFAULT_STEP00)
    parser.add_argument("--step05", type=Path, default=DEFAULT_STEP05)
    parser.add_argument("--step08", type=Path, default=DEFAULT_STEP08)
    parser.add_argument("--step09", type=Path, default=DEFAULT_STEP09)
    parser.add_argument("--previous-step10a", type=Path, default=DEFAULT_PREV_STEP10A)
    parser.add_argument("--output-root", type=Path, default=RESULTS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    step00 = require(args.step00.resolve(), "Step00")
    step05 = require(args.step05.resolve(), "Step05")
    require(args.step08.resolve(), "Step08")
    require(args.step09.resolve(), "Step09")
    prev = require(args.previous_step10a.resolve(), "previous Step10A")
    filipa_root = find_filipa_root()

    out = args.output_root.resolve() / f"fossum_roi_x490_step10a_revalidated_with_local_filipa_data_{tag()}"
    out.mkdir(parents=True, exist_ok=False)

    prev_frames = read_previous_step10a(prev)
    checks = confirm_step10a(prev_frames, step00, step05)
    data_inv = build_data_inventory(filipa_root)
    script_inv = script_inventory(filipa_root)
    availability = available_dates(filipa_root, prev_frames["selected"])
    pilot = select_pilot(prev_frames["priority"], availability)

    matlab_available = shutil.which("matlab") is not None
    dss_available = (filipa_root / "input_all" / "DSS.C.64.exe").exists()
    ready_predmodels = int(availability["predmodel_file_available"].sum())
    hres_available = int(availability["hres_file_available"].sum())
    can_execute_auto = bool(
        matlab_available
        and dss_available
        and ready_predmodels >= len(pilot)
        and bool((pilot["generation_feasibility"] == "READY_TO_EXTRACT_EXISTING_OUTPUT").all())
    )
    checks.update(
        {
            "filipa_root": str(filipa_root),
            "data_inventory_rows": int(len(data_inv)),
            "script_inventory_rows": int(len(script_inv)),
            "matlab_available_on_path": bool(matlab_available),
            "dss_executable_found": bool(dss_available),
            "selected_dates_with_ready_predmodel": ready_predmodels,
            "selected_dates_with_hres": hres_available,
            "pilot_size": int(len(pilot)),
            "can_execute_step10b_automatically_now": bool(can_execute_auto),
            "verdict": "READY_FOR_STEP10B_PILOT_GENERATION" if can_execute_auto else "NEEDS_FILIPA_SCRIPT_OR_INPUTS",
        }
    )

    data_inv.to_csv(out / "step10a_local_filipa_data_inventory.csv", index=False)
    script_inv.to_csv(out / "step10a_local_filipa_script_inventory.csv", index=False)
    availability.to_csv(out / "step10a_c01_c06_input_availability.csv", index=False)
    pilot.to_csv(out / "step10b_pilot_selected_dates.csv", index=False)
    write_json(out / "step10a_revalidation_checks.json", checks)
    write_json(
        out / "step10a_revalidation_metadata.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "root": ROOT,
            "previous_step10a": prev,
            "filipa_root": filipa_root,
            "step09_reused_not_rerun": True,
            "no_retraining": True,
            "no_clustering": True,
            "no_planner": True,
        },
    )
    write_reports(out, checks, filipa_root, data_inv, script_inv, pilot, can_execute_auto, matlab_available, dss_available)

    print(f"Step10A local revalidation complete: {out}")
    print(f"C01={checks['class01_count']} C06={checks['class06_count']} total={checks['total']}")
    print(f"Filipa data inventory rows={len(data_inv)} script rows={len(script_inv)}")
    print(f"Pilot dates={len(pilot)} automatic_step10b={can_execute_auto}")
    print(f"Verdict={checks['verdict']}")


if __name__ == "__main__":
    main()
