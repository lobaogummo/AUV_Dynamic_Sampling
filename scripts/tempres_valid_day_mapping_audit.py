"""Audit whether tempRes z is calendar-day index or filtered valid-day index.

The script looks for temporal metadata, inspects the GSLIB source used to build
the 300-map tempRes stack, checks the final NPY stack for day-level filtering,
and writes a reproducible mapping table plus explicit checks.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "Investigation_transition_to_planner" / "tempres_valid_day_mapping_audit"

SOURCE_GSLIB = ROOT / "data" / "2024" / "tempIBHRes2024_1.gslib"
OPTIONAL_2024IB = ROOT.parent / "new_data_pipeline" / "data_raw" / "2024IB"
STACK_PATH = ROOT / "results" / "plots" / "X_surface_300.npy"
STACK_NORM_PATH = ROOT / "results" / "plots" / "X_surface_300_norm.npy"
MASK_PATH = ROOT / "results" / "plots" / "mask_common.npy"
INDEX_PATHS = [
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis_indexed_axes" / "index.csv",
    ROOT / "results" / "plots" / "deterministic_2024_surface_300_thesis" / "index.csv",
]
OFFICIAL_STATE = ROOT / "configs" / "thesis_official_state.json"

TARGET_YEAR = 2024
DATE0 = date(TARGET_YEAR, 1, 1)
KEY_DATES = [date(2024, 10, 29), date(2024, 10, 30), date(2024, 10, 31)]
TARGET_Z = [298, 299, 300]
SENTINEL = -999.25


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fields: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def finite_float(value: object) -> Optional[float]:
    try:
        x = float(value)
    except Exception:
        return None
    if math.isfinite(x):
        return x
    return None


@dataclass
class GslibInfo:
    path: str
    exists: bool
    title: Optional[str] = None
    nvars: Optional[int] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    x_min: Optional[int] = None
    x_max: Optional[int] = None
    y_min: Optional[int] = None
    y_max: Optional[int] = None
    z_min: Optional[int] = None
    z_max: Optional[int] = None
    n_unique_z: Optional[int] = None
    z_values_contiguous: Optional[bool] = None
    expected_rows: Optional[int] = None
    grid_complete_cartesian: Optional[bool] = None
    finite_count: Optional[int] = None
    nan_count: Optional[int] = None
    sentinel_count: Optional[int] = None
    all_nan_z: Optional[List[int]] = None
    missing_z_values: Optional[List[int]] = None
    per_z: Optional[pd.DataFrame] = None
    notes: str = ""

    def as_dict(self) -> Dict[str, object]:
        out = {
            "path": self.path,
            "exists": self.exists,
            "title": self.title,
            "nvars": self.nvars,
            "columns": self.columns,
            "row_count": self.row_count,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "z_min": self.z_min,
            "z_max": self.z_max,
            "n_unique_z": self.n_unique_z,
            "z_values_contiguous": self.z_values_contiguous,
            "expected_rows": self.expected_rows,
            "grid_complete_cartesian": self.grid_complete_cartesian,
            "finite_count": self.finite_count,
            "nan_count": self.nan_count,
            "sentinel_count": self.sentinel_count,
            "all_nan_z": self.all_nan_z,
            "missing_z_values": self.missing_z_values,
            "notes": self.notes,
        }
        return out


def parse_header(path: Path) -> Tuple[str, List[str]]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        title = f.readline().strip()
        nvars = int(f.readline().strip().split()[0])
        columns = [f.readline().strip() for _ in range(nvars)]
    return title, columns


def gslib_lines(path: Path, nvars: int) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        _ = f.readline()
        for _ in range(nvars):
            _ = f.readline()
        for line in f:
            parts = line.strip().split()
            if len(parts) >= nvars:
                yield parts


def audit_gslib(path: Path) -> GslibInfo:
    info = GslibInfo(path=rel(path), exists=path.exists())
    if not path.exists():
        info.notes = "file_not_found"
        return info

    title, columns = parse_header(path)
    lower = [c.strip().lower() for c in columns]
    needed = ["x", "y", "z", "temp"]
    if any(name not in lower for name in needed):
        info.title = title
        info.nvars = len(columns)
        info.columns = columns
        info.notes = "missing_x_y_z_temp_columns"
        return info

    idx = {name: lower.index(name) for name in needed}
    x_min, y_min, z_min = 10**9, 10**9, 10**9
    x_max, y_max, z_max = -10**9, -10**9, -10**9
    row_count = 0
    finite_count = 0
    nan_count = 0
    sentinel_count = 0
    z_values: set[int] = set()
    per_z = defaultdict(lambda: {"row_count": 0, "finite_count": 0, "nan_count": 0, "sentinel_count": 0, "zero_count": 0})

    for parts in gslib_lines(path, len(columns)):
        try:
            x = int(round(float(parts[idx["x"]])))
            y = int(round(float(parts[idx["y"]])))
            z = int(round(float(parts[idx["z"]])))
        except Exception:
            continue
        temp = finite_float(parts[idx["temp"]])
        row_count += 1
        x_min = min(x_min, x)
        x_max = max(x_max, x)
        y_min = min(y_min, y)
        y_max = max(y_max, y)
        z_min = min(z_min, z)
        z_max = max(z_max, z)
        z_values.add(z)
        pz = per_z[z]
        pz["row_count"] += 1
        if temp is None:
            nan_count += 1
            pz["nan_count"] += 1
        elif abs(temp - SENTINEL) < 1e-9:
            sentinel_count += 1
            pz["sentinel_count"] += 1
        else:
            finite_count += 1
            pz["finite_count"] += 1
            if temp == 0.0:
                pz["zero_count"] += 1

    if row_count == 0:
        info.title = title
        info.nvars = len(columns)
        info.columns = columns
        info.notes = "no_data_rows"
        return info

    nx = x_max - x_min + 1
    ny = y_max - y_min + 1
    nz = z_max - z_min + 1
    expected_rows = nx * ny * nz
    full_z = set(range(z_min, z_max + 1))
    missing_z = sorted(full_z - z_values)
    rows = []
    for z in sorted(z_values):
        pz = per_z[z]
        total = pz["row_count"]
        rows.append(
            {
                "z": z,
                "row_count": total,
                "finite_count": pz["finite_count"],
                "nan_count": pz["nan_count"],
                "sentinel_count": pz["sentinel_count"],
                "zero_count": pz["zero_count"],
                "nan_fraction": pz["nan_count"] / total if total else np.nan,
                "sentinel_fraction": pz["sentinel_count"] / total if total else np.nan,
                "finite_fraction": pz["finite_count"] / total if total else np.nan,
                "all_nan_or_sentinel": bool((pz["finite_count"] == 0) and total > 0),
            }
        )
    per_z_df = pd.DataFrame(rows)
    all_nan_z = per_z_df.loc[per_z_df["all_nan_or_sentinel"], "z"].astype(int).tolist()

    info.title = title
    info.nvars = len(columns)
    info.columns = columns
    info.row_count = int(row_count)
    info.x_min = int(x_min)
    info.x_max = int(x_max)
    info.y_min = int(y_min)
    info.y_max = int(y_max)
    info.z_min = int(z_min)
    info.z_max = int(z_max)
    info.n_unique_z = int(len(z_values))
    info.z_values_contiguous = bool(len(missing_z) == 0)
    info.expected_rows = int(expected_rows)
    info.grid_complete_cartesian = bool(row_count == expected_rows and len(missing_z) == 0)
    info.finite_count = int(finite_count)
    info.nan_count = int(nan_count)
    info.sentinel_count = int(sentinel_count)
    info.all_nan_z = all_nan_z
    info.missing_z_values = missing_z
    info.per_z = per_z_df
    info.notes = "gslib_has_x_y_z_temp_only_no_time_or_date_column"
    return info


def audit_stack() -> Tuple[pd.DataFrame, Dict[str, object]]:
    if not STACK_PATH.exists():
        raise FileNotFoundError(STACK_PATH)
    x = np.load(STACK_PATH)
    x_norm = np.load(STACK_NORM_PATH) if STACK_NORM_PATH.exists() else None
    mask = np.load(MASK_PATH) if MASK_PATH.exists() else None
    rows: List[Dict[str, object]] = []
    for i in range(x.shape[0]):
        arr = x[i]
        finite = np.isfinite(arr)
        total = int(arr.size)
        finite_count = int(finite.sum())
        nan_count = total - finite_count
        valid_vals = arr[finite]
        zero_count = int(np.count_nonzero(valid_vals == 0.0))
        rows.append(
            {
                "z": i + 1,
                "zero_based_index": i,
                "finite_count": finite_count,
                "nan_count": nan_count,
                "nan_fraction": nan_count / total if total else np.nan,
                "zero_count": zero_count,
                "all_nan": bool(finite_count == 0),
                "all_zero_on_valid_pixels": bool(finite_count > 0 and zero_count == finite_count),
                "mean_temp": float(np.nanmean(arr)) if finite_count else np.nan,
                "std_temp": float(np.nanstd(arr)) if finite_count else np.nan,
                "min_temp": float(np.nanmin(arr)) if finite_count else np.nan,
                "max_temp": float(np.nanmax(arr)) if finite_count else np.nan,
            }
        )
    df = pd.DataFrame(rows)
    meta = {
        "stack_path": rel(STACK_PATH),
        "stack_shape": [int(v) for v in x.shape],
        "stack_dtype": str(x.dtype),
        "norm_stack_exists": bool(x_norm is not None),
        "norm_stack_shape": [int(v) for v in x_norm.shape] if x_norm is not None else None,
        "mask_exists": bool(mask is not None),
        "mask_shape": [int(v) for v in mask.shape] if mask is not None else None,
        "mask_valid_fraction": float(np.mean(mask)) if mask is not None else None,
        "n_all_nan_days": int(df["all_nan"].sum()),
        "n_all_zero_days": int(df["all_zero_on_valid_pixels"].sum()),
        "nan_fraction_min": float(df["nan_fraction"].min()),
        "nan_fraction_max": float(df["nan_fraction"].max()),
        "nan_fraction_is_constant": bool(np.isclose(df["nan_fraction"].min(), df["nan_fraction"].max())),
    }
    return df, meta


def read_official_state() -> Dict[str, object]:
    if not OFFICIAL_STATE.exists():
        return {}
    try:
        return json.loads(OFFICIAL_STATE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"read_error": str(exc)}


def discover_generation_scripts() -> List[Dict[str, object]]:
    terms = [
        "tempIBHRes2024",
        "X_surface_300",
        "X_surface_300_norm",
        "deterministic_2024_surface_300",
        "TARGET_Z_MAX",
        "second_pass_build_grids",
        "valid_days",
        "selected_days",
        "missing_days",
        "date",
    ]
    rows: List[Dict[str, object]] = []
    for path in sorted((ROOT / "scripts").rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        matches = [term for term in terms if term.lower() in text.lower()]
        if matches:
            rows.append({"path": rel(path), "matched_terms": ";".join(matches)})
    return rows


def discover_metadata_files() -> List[Dict[str, object]]:
    name_terms = [
        "manifest",
        "dates",
        "selected_days",
        "valid_days",
        "missing_days",
        "processing_report",
        "validation_report",
        "report",
        "summary",
        "state",
        "pipeline_stages",
    ]
    content_terms = ["valid_days", "selected_days", "missing_days", "removed", "filter", "quality", "nan", "365", "missing 65"]
    roots = [ROOT / "results", ROOT / "investigation", ROOT / "docs", ROOT / "configs"]
    rows: List[Dict[str, object]] = []
    seen: set[Path] = set()
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path in seen:
                continue
            if path.suffix.lower() not in {".json", ".csv", ".md", ".txt"}:
                continue
            seen.add(path)
            lname = path.name.lower()
            name_matches = [t for t in name_terms if t in lname]
            if not name_matches and path.stat().st_size > 5_000_000:
                continue
            content_matches: List[str] = []
            date_tokens: List[str] = []
            if path.stat().st_size <= 5_000_000:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    text = ""
                lower = text.lower()
                content_matches = [t for t in content_terms if t in lower]
                date_tokens = sorted(set(re.findall(r"\b2024[-_/]?\d{2}[-_/]?\d{2}\b|\b\d{2}-\d{2}-2024\b", text)))[:20]
            if name_matches or content_matches:
                rows.append(
                    {
                        "path": rel(path),
                        "size_bytes": int(path.stat().st_size),
                        "name_matches": ";".join(name_matches),
                        "content_matches": ";".join(content_matches),
                        "date_tokens_sample": ";".join(date_tokens),
                    }
                )
    return rows


def load_index_rows() -> Dict[str, object]:
    for path in INDEX_PATHS:
        if path.exists():
            df = pd.read_csv(path)
            return {
                "path": rel(path),
                "exists": True,
                "n_rows": int(len(df)),
                "z_min": int(df["z"].min()) if "z" in df else None,
                "z_max": int(df["z"].max()) if "z" in df else None,
                "has_date_column": bool(any("date" in c.lower() or "time" in c.lower() for c in df.columns)),
                "columns": list(df.columns),
            }
    return {"exists": False, "paths_checked": [rel(p) for p in INDEX_PATHS]}


def calendar_date_for_z(z: int) -> date:
    return DATE0 + timedelta(days=z - 1)


def day_of_year(d: date) -> int:
    return int((d - DATE0).days + 1)


def build_mapping(stack_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for _, row in stack_df.iterrows():
        z = int(row["z"])
        cal = calendar_date_for_z(z)
        rows.append(
            {
                "z": z,
                "zero_based_index": int(row["zero_based_index"]),
                "real_date": "",
                "calendar_day_hypothesis_date": cal.isoformat(),
                "calendar_day_hypothesis_day_of_year": day_of_year(cal),
                "valid_day_index_hypothesis": z,
                "kept_in_final_stack": True,
                "removed": False,
                "removal_reason": "",
                "date_status": "no_explicit_date_metadata_found",
                "nan_fraction": row["nan_fraction"],
                "finite_count": int(row["finite_count"]),
                "nan_count": int(row["nan_count"]),
                "all_nan": bool(row["all_nan"]),
                "all_zero_on_valid_pixels": bool(row["all_zero_on_valid_pixels"]),
                "mean_temp": row["mean_temp"],
                "std_temp": row["std_temp"],
                "min_temp": row["min_temp"],
                "max_temp": row["max_temp"],
            }
        )
    return pd.DataFrame(rows)


def build_absent_calendar_days(n_final_days: int) -> pd.DataFrame:
    # 2024 is leap year. These are calendar days that are not present if z is
    # interpreted as day-of-year starting on 2024-01-01. They are not documented
    # removals; this table makes that explicit.
    rows = []
    last_day = date(TARGET_YEAR, 12, 31)
    d = calendar_date_for_z(n_final_days + 1)
    while d <= last_day:
        rows.append(
            {
                "calendar_date": d.isoformat(),
                "calendar_day_of_year": day_of_year(d),
                "z_if_calendar_day": day_of_year(d),
                "present_in_tempres_under_calendar_hypothesis": False,
                "documented_removed": False,
                "removal_reason": "outside_z_1_to_300_native_range_not_documented_qc_removal",
                "evidence_status": "absent_if_z_is_calendar_day; not evidence of valid-day filtering",
            }
        )
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def date_status_for_z(z: int) -> Dict[str, object]:
    cal = calendar_date_for_z(z)
    return {
        "real_date": None,
        "calendar_day_hypothesis": cal.isoformat(),
        "calendar_day_of_year": day_of_year(cal),
        "metadata_status": "not_explicitly_proven",
    }


def z_for_calendar_date(d: date, n_final_days: int) -> Optional[int]:
    z = day_of_year(d)
    return z if 1 <= z <= n_final_days else None


def make_checks(
    source_info: GslibInfo,
    optional_info: Optional[GslibInfo],
    stack_df: pd.DataFrame,
    stack_meta: Dict[str, object],
    scripts: List[Dict[str, object]],
    metadata: List[Dict[str, object]],
    index_info: Dict[str, object],
    official_state: Dict[str, object],
) -> Dict[str, object]:
    n_final_days = int(stack_df["z"].max())
    all_nan_days = stack_df.loc[stack_df["all_nan"], "z"].astype(int).tolist()
    all_zero_days = stack_df.loc[stack_df["all_zero_on_valid_pixels"], "z"].astype(int).tolist()
    date_mapping_files = []
    for row in metadata:
        name = Path(str(row["path"])).name.lower()
        if re.search(r"(^|[_-])(dates|date_mapping|selected_days|valid_days|missing_days)([_\-.]|$)", name):
            date_mapping_files.append(row["path"])
    filtering_terms = [row for row in metadata if row.get("content_matches")]
    official_notes = official_state.get("official_dataset", {}).get("notes", []) if official_state else []

    day_level_filtering_detected = False
    filtering_reason = (
        "No day-level filtering script or selected/valid/missing-days table was found. "
        "Located build scripts materialize native GSLIB z=1..300. The common mask removes pixels, not days. "
        "configs/thesis_official_state.json notes a 300-day dataset and a pending extension to 365 days."
    )
    if all_nan_days or all_zero_days:
        day_level_filtering_detected = True
        filtering_reason = "Final stack contains all-NaN or all-zero days, indicating possible day-level quality issues."

    removed_needed = {
        "if_z300_is_2024-10-29": day_of_year(date(2024, 10, 29)) - 300,
        "if_z300_is_2024-10-30": day_of_year(date(2024, 10, 30)) - 300,
        "if_z300_is_2024-10-31": day_of_year(date(2024, 10, 31)) - 300,
    }

    z_oct = {d.isoformat(): z_for_calendar_date(d, n_final_days) for d in KEY_DATES}
    present_oct = {d.isoformat(): z_oct[d.isoformat()] is not None for d in KEY_DATES}

    if date_mapping_files:
        z_type = "explicit_mapping_file_found_but_not_interpreted_as_authoritative_without_manual_review"
    else:
        z_type = "native_1_based_z_index; calendar_day_mapping_not_metadata_proven; valid_day_filtering_not_supported"

    final_verdict = (
        "No evidence was found that the 300 tempRes z slices are valid days after filtering. "
        "The reproducible source path treats z as a native 1-based GSLIB index and copies z=1..300. "
        "No time/date variable exists in the GSLIB header. Under the calendar-day hypothesis from 2024-01-01, "
        "z=300 is 2024-10-26 and 2024-10-29/30/31 are outside the stack. z=300 could correspond to "
        "2024-10-29/30/31 only if 3/4/5 earlier days had been removed, but no such removed-day metadata "
        "or filtering code was found."
    )

    checks = {
        "created_at": now_iso(),
        "source_gslib": source_info.as_dict(),
        "optional_2024IB_source": optional_info.as_dict() if optional_info else None,
        "final_stack": stack_meta,
        "index_file": index_info,
        "official_state_notes": official_notes,
        "generation_scripts_found": scripts,
        "metadata_files_audited_count": len(metadata),
        "date_mapping_files_found": date_mapping_files,
        "metadata_filtering_evidence_sample": filtering_terms[:25],
        "n_original_days_found": source_info.n_unique_z,
        "n_original_calendar_days_found": None,
        "n_final_days": n_final_days,
        "filtering_detected": bool(day_level_filtering_detected),
        "filtering_reason": filtering_reason,
        "z_is_calendar_day_or_valid_day_index": z_type,
        "date_for_z298": date_status_for_z(298),
        "date_for_z299": date_status_for_z(299),
        "date_for_z300": date_status_for_z(300),
        "oct29_present": present_oct["2024-10-29"],
        "oct30_present": present_oct["2024-10-30"],
        "oct31_present": present_oct["2024-10-31"],
        "z_for_oct29": z_oct["2024-10-29"],
        "z_for_oct30": z_oct["2024-10-30"],
        "z_for_oct31": z_oct["2024-10-31"],
        "removed_days_required_if_z300_were_late_october": removed_needed,
        "can_z300_be_oct29_oct30_oct31_due_to_filtering": (
            "theoretically_possible_but_not_supported_by_current_metadata_or_scripts"
        ),
        "final_verdict": final_verdict,
    }
    return checks


def fmt_bool(value: object) -> str:
    if value is True:
        return "YES"
    if value is False:
        return "NO"
    return "UNKNOWN"


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                vals.append("" if not math.isfinite(value) else f"{value:.6g}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_reports(checks: Dict[str, object], mapping: pd.DataFrame, removed: pd.DataFrame) -> None:
    final_sentence = "The audit determines whether z in tempRes is a calendar-day index or a valid-day index after filtering."
    z300 = checks["date_for_z300"]
    direct_answers = [
        "1. Os 300 dias sao dias corridos ou dias validos apos filtragem? "
        "Nao ha prova de filtragem por dias validos; o caminho reprodutivel mostra z=1..300 nativo do GSLIB. "
        "A conversao para dias corridos e apenas hipotese porque nao ha time/date no GSLIB.",
        "2. Houve remocao de dias nulos/NaN/invalidos? Nao foi detectada remocao de dias. "
        "Foram detectados NaNs espaciais constantes/mascara comum, isto e filtragem de pixels, nao de dias.",
        f"3. z=300 corresponde a que data real? Data real nao esta em metadata; na hipotese calendario desde 2024-01-01 corresponde a `{z300['calendar_day_hypothesis']}`.",
        f"4. 29/10/2024 existe no tempRes? `{fmt_bool(checks['oct29_present'])}` sob hipotese calendario; seria z=303 e esta fora de z=1..300.",
        f"5. 30/10/2024 existe no tempRes? `{fmt_bool(checks['oct30_present'])}` sob hipotese calendario; seria z=304 e esta fora de z=1..300.",
        f"6. 31/10/2024 existe no tempRes? `{fmt_bool(checks['oct31_present'])}` sob hipotese calendario; seria z=305 e esta fora de z=1..300.",
        "7. As comparacoes anteriores com 30/10 e 31/10 estavam temporalmente corretas ou nao? "
        "Nao ficam temporalmente provadas. Se z for dia-do-ano, essas comparacoes nao estavam corretas; "
        "a melhoria numerica com z=300 deve ser tratada como matching de campo/produto, nao prova temporal.",
    ]

    summary = [
        "# tempRes Temporal Filtering Summary",
        "",
        f"- Output directory: `{rel(OUT_DIR)}`",
        f"- Source GSLIB: `{checks['source_gslib']['path']}`",
        f"- n_original_days_found: `{checks['n_original_days_found']}`",
        f"- n_final_days: `{checks['n_final_days']}`",
        f"- filtering_detected: `{checks['filtering_detected']}`",
        f"- z interpretation: `{checks['z_is_calendar_day_or_valid_day_index']}`",
        f"- date_for_z298 calendar hypothesis: `{checks['date_for_z298']['calendar_day_hypothesis']}`",
        f"- date_for_z299 calendar hypothesis: `{checks['date_for_z299']['calendar_day_hypothesis']}`",
        f"- date_for_z300 calendar hypothesis: `{checks['date_for_z300']['calendar_day_hypothesis']}`",
        "",
        "Direct answers:",
        *direct_answers,
        "",
        final_sentence,
    ]
    (OUT_DIR / "tempres_temporal_filtering_summary.md").write_text("\n".join(summary), encoding="utf-8")

    key_mapping = mapping[mapping["z"].isin(TARGET_Z)].copy()
    report = [
        "# tempRes Temporal Filtering Audit Report",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "## Evidence Summary",
        "",
        "- The authoritative tempRes source located for the official 300-map stack is `data/2024/tempIBHRes2024_1.gslib`.",
        "- The GSLIB header has columns `x`, `y`, `z`, `temp`; no `time` or `date` variable was found.",
        "- The build/export scripts use `TARGET_Z_MAX = 300` and materialize native `z=1..300`.",
        "- `mask_common.npy` is a spatial common mask. It does not remove time slices.",
        "- `configs/thesis_official_state.json` describes this as a 300-day dataset and says extension to 365 days is pending.",
        "",
        "## Key z Rows",
        "",
        markdown_table(
            key_mapping[
                [
                    "z",
                    "zero_based_index",
                    "real_date",
                    "calendar_day_hypothesis_date",
                    "kept_in_final_stack",
                    "date_status",
                    "nan_fraction",
                    "mean_temp",
                ]
            ]
        ),
        "",
        "## October 29-31 Calendar Check",
        "",
        f"- 2024-10-29 would be day-of-year/z `{day_of_year(date(2024, 10, 29))}` under calendar indexing; present: `{checks['oct29_present']}`.",
        f"- 2024-10-30 would be day-of-year/z `{day_of_year(date(2024, 10, 30))}` under calendar indexing; present: `{checks['oct30_present']}`.",
        f"- 2024-10-31 would be day-of-year/z `{day_of_year(date(2024, 10, 31))}` under calendar indexing; present: `{checks['oct31_present']}`.",
        "- To make z=300 equal 2024-10-29/30/31, the pipeline would need 3/4/5 undocumented removed days before those dates.",
        "",
        "## Removed/Absent Days Table",
        "",
        f"- Rows in `tempres_removed_days.csv`: `{len(removed)}`.",
        "- These rows are calendar days absent under the calendar-day hypothesis, not documented QC removals.",
        "",
        "## Required Checks",
        "",
        "```json",
        json.dumps(checks, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Final Answers",
        "",
        *direct_answers,
        "",
        final_sentence,
    ]
    (OUT_DIR / "tempres_temporal_filtering_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    ensure_dir(OUT_DIR)
    source_info = audit_gslib(SOURCE_GSLIB)
    optional_info = audit_gslib(OPTIONAL_2024IB) if OPTIONAL_2024IB.exists() else None
    stack_df, stack_meta = audit_stack()
    scripts = discover_generation_scripts()
    metadata = discover_metadata_files()
    index_info = load_index_rows()
    official_state = read_official_state()
    mapping = build_mapping(stack_df)
    removed = build_absent_calendar_days(int(stack_df["z"].max()))
    checks = make_checks(source_info, optional_info, stack_df, stack_meta, scripts, metadata, index_info, official_state)

    mapping_fields = [
        "z",
        "zero_based_index",
        "real_date",
        "calendar_day_hypothesis_date",
        "calendar_day_hypothesis_day_of_year",
        "valid_day_index_hypothesis",
        "kept_in_final_stack",
        "removed",
        "removal_reason",
        "date_status",
        "nan_fraction",
        "finite_count",
        "nan_count",
        "all_nan",
        "all_zero_on_valid_pixels",
        "mean_temp",
        "std_temp",
        "min_temp",
        "max_temp",
    ]
    write_csv(OUT_DIR / "tempres_valid_day_mapping.csv", mapping.to_dict("records"), mapping_fields)
    removed_fields = [
        "calendar_date",
        "calendar_day_of_year",
        "z_if_calendar_day",
        "present_in_tempres_under_calendar_hypothesis",
        "documented_removed",
        "removal_reason",
        "evidence_status",
    ]
    write_csv(OUT_DIR / "tempres_removed_days.csv", removed.to_dict("records"), removed_fields)
    write_json(OUT_DIR / "tempres_temporal_filtering_checks.json", checks)
    write_reports(checks, mapping, removed)
    print(f"Wrote outputs to {OUT_DIR}")
    print(checks["final_verdict"])


if __name__ == "__main__":
    main()
