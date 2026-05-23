"""Check Step10B pilot predModels after MATLAB generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def latest_output() -> Path:
    candidates = sorted(RESULTS.glob("fossum_roi_x490_step10b_matlab_pilot_generation_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No Step10B MATLAB pilot output folder found.")
    return candidates[0]


def inspect_nc(path: Path) -> dict:
    import xarray as xr

    out = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return out
    ds = xr.open_dataset(path, decode_times=False)
    out["dims"] = dict(ds.sizes)
    out["variables"] = list(ds.variables)
    for name in ["TEMPpred", "STD", "LAT", "LON", "BATHY"]:
        out[f"has_{name}"] = name in ds.variables
    if "TEMPpred" in ds:
        arr = ds["TEMPpred"].values
        out["TEMPpred_shape"] = list(arr.shape)
        out["TEMPpred_all_nan"] = bool(np.isnan(arr).all())
        out["TEMPpred_valid_fraction"] = float(np.isfinite(arr).mean())
    if "STD" in ds:
        arr = ds["STD"].values
        out["STD_shape"] = list(arr.shape)
        out["STD_all_zero_or_nan"] = bool(np.nanmax(np.abs(arr)) == 0) if np.isfinite(arr).any() else True
        out["STD_valid_fraction"] = float(np.isfinite(arr).mean())
    ds.close()
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    out_dir = args.output.resolve() if args.output else latest_output().resolve()
    expected = pd.read_csv(out_dir / "step10b_expected_outputs.csv")
    pred = expected[expected["kind"].eq("predmodel")].copy()
    rows = []
    for _, row in pred.iterrows():
        info = inspect_nc(Path(row["expected_path"]))
        info.update({"date": row["date"], "class_id": row["class_id"], "depth": row["depth"]})
        rows.append(info)
    inv = pd.DataFrame(rows)
    inv.to_csv(out_dir / "step10b_pilot_predmodel_inventory.csv", index=False)
    checks = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(out_dir),
        "expected_predmodels": int(len(pred)),
        "existing_predmodels": int(inv["exists"].sum()) if not inv.empty else 0,
        "pilot_dates_complete": bool(inv.groupby("date")["exists"].all().all()) if not inv.empty else False,
        "all_existing_have_TEMPpred": bool(inv[inv["exists"]]["has_TEMPpred"].all()) if "has_TEMPpred" in inv else False,
        "all_existing_have_STD": bool(inv[inv["exists"]]["has_STD"].all()) if "has_STD" in inv else False,
        "std_not_all_zero_for_existing": bool((~inv[inv["exists"]]["STD_all_zero_or_nan"]).all()) if "STD_all_zero_or_nan" in inv and inv["exists"].any() else False,
    }
    (out_dir / "step10b_pilot_predmodel_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    summary = [
        "# Step10B Pilot PredModel Check Summary",
        "",
        f"- Output: `{out_dir}`",
        f"- Expected predModels: {checks['expected_predmodels']}",
        f"- Existing predModels: {checks['existing_predmodels']}",
        f"- Pilot dates complete: {checks['pilot_dates_complete']}",
        f"- All existing have TEMPpred: {checks['all_existing_have_TEMPpred']}",
        f"- All existing have STD: {checks['all_existing_have_STD']}",
    ]
    (out_dir / "step10b_pilot_predmodel_check_summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
