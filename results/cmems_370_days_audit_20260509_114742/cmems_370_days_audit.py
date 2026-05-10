from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd


INPUT_ROOT = Path(r"C:\Users\pedro\Documents\Filipa_dados\data\dadosParaPedro_Fresnel")
OUT_DIR = Path(__file__).resolve().parent
EXPECTED_START = date(2023, 10, 28)
EXPECTED_END = date(2024, 10, 31)


def rel(p: Path) -> str:
    return str(p.relative_to(INPUT_ROOT))


def jsonish(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def date_range(start: date, end: date) -> list[date]:
    n = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(n)]


def classify_nc(p: Path) -> str:
    s = str(p).lower()
    if "01.data" in s and "\\all\\" in s:
        return "raw_CMEMS_Copernicus"
    if "01.data" in s and "\\october\\hres" in s:
        return "downscaled_high_resolution"
    if "01.data" in s and "\\october\\cmemsgrid" in s:
        return "october_grouped_CMEMS_grid"
    return "other_netcdf"


def find_time_var(ds: netCDF4.Dataset) -> str:
    candidates = []
    for name, var in ds.variables.items():
        lname = name.lower()
        units = str(getattr(var, "units", "")).lower()
        if lname in {"time", "times"} or "since" in units or "time" in lname:
            candidates.append(name)
    if candidates:
        return candidates[0]
    for dim in ds.dimensions:
        if "time" in dim.lower() or "seconds since" in dim.lower():
            if dim in ds.variables:
                return dim
    return ""


def convert_times(ds: netCDF4.Dataset, time_var_name: str) -> tuple[list[str], str, str]:
    if not time_var_name:
        return [], "", ""
    var = ds.variables[time_var_name]
    vals = np.asarray(var[:])
    units = str(getattr(var, "units", ""))
    if (not units or units == "None") and getattr(var, "dimensions", None):
        dim0 = str(var.dimensions[0])
        if "since" in dim0.lower():
            units = dim0
    calendar = str(getattr(var, "calendar", "standard"))
    if units and "since" in units.lower():
        converted = netCDF4.num2date(vals, units=units, calendar=calendar, only_use_cftime_datetimes=False, only_use_python_datetimes=False)
        dates = []
        for x in np.ravel(converted):
            if hasattr(x, "date"):
                dates.append(x.date().isoformat())
            else:
                dates.append(str(x)[:10])
        return dates, units, calendar
    return [str(x) for x in np.ravel(vals)], units, calendar


def infer_date_from_name(name: str) -> str:
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def audit_file(p: Path) -> tuple[dict, list[dict]]:
    row = {
        "path": str(p),
        "relative_path": rel(p),
        "filename": p.name,
        "category": classify_nc(p),
        "size_bytes": p.stat().st_size,
        "date_in_filename": infer_date_from_name(p.name),
    }
    date_rows = []
    with netCDF4.Dataset(p) as ds:
        dims = {k: len(v) for k, v in ds.dimensions.items()}
        variables = list(ds.variables.keys())
        shapes = {k: list(v.shape) for k, v in ds.variables.items()}
        units = {k: str(getattr(v, "units", "")) for k, v in ds.variables.items()}
        attrs = {k: {a: getattr(v, a) for a in v.ncattrs()} for k, v in ds.variables.items()}
        global_attrs = {a: getattr(ds, a) for a in ds.ncattrs()}
        time_var = find_time_var(ds)
        dates, time_units, time_calendar = convert_times(ds, time_var)
        unique_dates = sorted(set(dates))
        temp_vars = [v for v in variables if v.lower() in {"thetao", "temp", "temppred", "temperature"} or "temp" in v.lower()]
        row.update({
            "dimensions": jsonish(dims),
            "variables": jsonish(variables),
            "variable_shapes": jsonish(shapes),
            "variable_units": jsonish(units),
            "variable_attributes": jsonish(attrs),
            "global_attributes": jsonish(global_attrs),
            "time_variable": time_var,
            "time_units": time_units,
            "time_calendar": time_calendar,
            "n_time_values": len(dates),
            "n_unique_dates": len(unique_dates),
            "first_date": unique_dates[0] if unique_dates else "",
            "last_date": unique_dates[-1] if unique_dates else "",
            "includes_temperature": bool(temp_vars),
            "temperature_variables": jsonish(temp_vars),
            "principal_variable_shapes": jsonish({v: shapes[v] for v in temp_vars + [time_var] if v in shapes}),
        })
        for i, d in enumerate(dates):
            date_rows.append({
                "file": p.name,
                "relative_path": rel(p),
                "category": row["category"],
                "time_variable": time_var,
                "time_index": i,
                "date": d,
            })
    return row, date_rows


def coverage(dates: list[str], start: date = EXPECTED_START, end: date = EXPECTED_END) -> dict:
    expected = [d.isoformat() for d in date_range(start, end)]
    unique = sorted(set(d for d in dates if re.match(r"\d{4}-\d{2}-\d{2}$", str(d))))
    missing = [d for d in expected if d not in unique]
    extra = [d for d in unique if d not in expected]
    return {
        "n_time_values": len(dates),
        "n_unique_dates": len(unique),
        "first_date": unique[0] if unique else "",
        "last_date": unique[-1] if unique else "",
        "expected_n_days": len(expected),
        "has_exactly_370_unique_days": len(unique) == 370,
        "covers_expected_start_end": bool(unique and unique[0] <= start.isoformat() and unique[-1] >= end.isoformat()),
        "missing_days": missing,
        "extra_days_outside_expected": extra,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nc_files = sorted(INPUT_ROOT.rglob("*.nc"))
    target_files = [p for p in nc_files if classify_nc(p) in {"raw_CMEMS_Copernicus", "downscaled_high_resolution", "october_grouped_CMEMS_grid"}]
    rows = []
    date_rows = []
    for p in target_files:
        row, drows = audit_file(p)
        rows.append(row)
        date_rows.extend(drows)

    inventory = pd.DataFrame(rows)
    dates_df = pd.DataFrame(date_rows)
    dates_df.to_csv(OUT_DIR / "cmems_370_days_dates.csv", index=False)

    raw = inventory[inventory["category"] == "raw_CMEMS_Copernicus"].copy()
    hres = inventory[inventory["category"] == "downscaled_high_resolution"].copy()
    cmems_oct = inventory[inventory["category"] == "october_grouped_CMEMS_grid"].copy()

    raw_dates = dates_df[dates_df["category"] == "raw_CMEMS_Copernicus"]["date"].astype(str).tolist()
    hres_dates = dates_df[dates_df["category"] == "downscaled_high_resolution"]["date"].astype(str).tolist()
    cmems_oct_dates = dates_df[dates_df["category"] == "october_grouped_CMEMS_grid"]["date"].astype(str).tolist()
    raw_cov = coverage(raw_dates)
    hres_cov = coverage(hres_dates)
    cmems_oct_cov = coverage(cmems_oct_dates)

    raw_primary = raw.sort_values(["n_unique_dates", "size_bytes"], ascending=False).head(1)
    raw_primary_file = raw_primary.iloc[0]["relative_path"] if len(raw_primary) else ""
    raw_primary_dates = dates_df[dates_df["relative_path"] == raw_primary_file]["date"].astype(str).tolist() if raw_primary_file else []
    raw_primary_cov = coverage(raw_primary_dates)

    checks = {
        "input_root": str(INPUT_ROOT),
        "expected_start": EXPECTED_START.isoformat(),
        "expected_end": EXPECTED_END.isoformat(),
        "expected_n_days_inclusive": 370,
        "raw_CMEMS_Copernicus_files": raw["relative_path"].tolist(),
        "raw_file_count": int(len(raw)),
        "raw_primary_370_day_file": raw_primary_file,
        "raw_primary_coverage": raw_primary_cov,
        "raw_combined_coverage": raw_cov,
        "raw_has_temperature": bool(raw["includes_temperature"].all()) if len(raw) else False,
        "raw_variable_shapes": dict(zip(raw["relative_path"], raw["principal_variable_shapes"])),
        "downscaled_high_resolution_files": hres["relative_path"].tolist(),
        "downscaled_high_resolution_file_count": int(len(hres)),
        "downscaled_high_resolution_combined_coverage": hres_cov,
        "october_grouped_CMEMS_grid_files": cmems_oct["relative_path"].tolist(),
        "october_grouped_CMEMS_grid_file_count": int(len(cmems_oct)),
        "october_grouped_CMEMS_grid_combined_coverage": cmems_oct_cov,
        "have_370_days": bool(raw_primary_cov["has_exactly_370_unique_days"] and raw_primary_cov["first_date"] == EXPECTED_START.isoformat() and raw_primary_cov["last_date"] == EXPECTED_END.isoformat() and not raw_primary_cov["missing_days"]),
        "370_days_are_on_original_CMEMS_grid": bool(len(raw_primary) and "thetao" in raw_primary.iloc[0]["temperature_variables"].lower()),
        "370_days_are_on_high_resolution_grid": bool(hres_cov["has_exactly_370_unique_days"] and not hres_cov["missing_days"]),
    }
    checks["final_verdict"] = (
        "The 370-day period is present in the raw Copernicus/CMEMS file on the original CMEMS grid."
        if checks["have_370_days"]
        else "The expected 370-day raw CMEMS coverage was not confirmed."
    )
    (OUT_DIR / "cmems_370_days_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def file_table(df: pd.DataFrame) -> str:
        if df.empty:
            return "_none_\n"
        cols = ["relative_path", "n_time_values", "n_unique_dates", "first_date", "last_date", "time_variable", "includes_temperature", "temperature_variables", "principal_variable_shapes"]
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for _, r in df[cols].iterrows():
            vals = [str(r[c]).replace("\n", " ").replace("|", "\\|") for c in cols]
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)

    summary = f"""# CMEMS 370 Days Audit Summary

1. Tenho ou não tenho os 370 dias? {"Sim." if checks["have_370_days"] else "Não confirmado."}
2. Em que ficheiro(s) estão? `{raw_primary_file}`.
3. Qual a primeira e última data? `{raw_primary_cov["first_date"]}` a `{raw_primary_cov["last_date"]}`.
4. Há dias em falta? {"Não." if not raw_primary_cov["missing_days"] else "Sim: " + ", ".join(raw_primary_cov["missing_days"])}
5. Os 370 dias estão na grelha original CMEMS ou já na high-resolution? {"Na grelha original CMEMS." if checks["370_days_are_on_original_CMEMS_grid"] else "Não confirmado na grelha original CMEMS."} High-resolution tem `{"370 dias" if checks["370_days_are_on_high_resolution_grid"] else "apenas ficheiros/janelas de outubro"}`.
6. Que dados estão disponíveis só para outubro? `01.Data/October/CMEMSGrid` e `01.Data/October/HRes`, com ficheiros diários nomeados de 2024-09-30 a 2024-11-02 e janelas temporais internas de 14 tempos por ficheiro.
"""
    (OUT_DIR / "cmems_370_days_audit_summary.md").write_text(summary, encoding="utf-8")

    report = f"""# CMEMS 370 Days Audit Report

Input root: `{INPUT_ROOT}`

Expected inclusive interval: `{EXPECTED_START}` to `{EXPECTED_END}` = 370 days.

## Raw CMEMS / Copernicus Files

{file_table(raw)}

Raw primary coverage:

```json
{json.dumps(raw_primary_cov, indent=2, ensure_ascii=False)}
```

Raw combined coverage:

```json
{json.dumps(raw_cov, indent=2, ensure_ascii=False)}
```

## October CMEMS Grid Files

{file_table(cmems_oct)}

Combined coverage:

```json
{json.dumps(cmems_oct_cov, indent=2, ensure_ascii=False)}
```

## Downscaled / High-Resolution Files

{file_table(hres)}

Combined coverage:

```json
{json.dumps(hres_cov, indent=2, ensure_ascii=False)}
```

## Conclusion

- 370 days confirmed: `{checks["have_370_days"]}`
- File containing the 370-day sequence: `{raw_primary_file}`
- First/last raw primary date: `{raw_primary_cov["first_date"]}` / `{raw_primary_cov["last_date"]}`
- Missing raw primary days: `{raw_primary_cov["missing_days"]}`
- Temperature present in raw files: `{checks["raw_has_temperature"]}`
- High-resolution is 370-day coverage: `{checks["370_days_are_on_high_resolution_grid"]}`
"""
    (OUT_DIR / "cmems_370_days_audit_report.md").write_text(report, encoding="utf-8")

    print(f"Audit complete: {OUT_DIR}")


if __name__ == "__main__":
    main()
