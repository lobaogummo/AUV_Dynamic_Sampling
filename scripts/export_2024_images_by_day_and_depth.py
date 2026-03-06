"""Export deterministic 2024 TEMP images by day (z) and depth (1..17) from GSLIB."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "2024"
OUT_ROOT = ROOT / "results" / "plots" / "deterministic_2024_by_depth"
INDEX_CSV = OUT_ROOT / "index.csv"

FILE_RE = re.compile(r"^tempIBHRes2024_(\d+)\.gslib$")
EXPECTED_DEPTHS = list(range(1, 18))
START_DATE = date(2024, 1, 1)
TARGET_MIN_Z = 300
HIST_BINS = 4096


@dataclass
class DepthPass1:
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    z_min: int
    z_max: int
    temp_min: float
    temp_max: float
    n_values: int
    nvars: int
    varnames: List[str]
    title: str
    idx: Dict[str, int]


def parse_header(path: Path) -> Tuple[str, int, List[str]]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        title = f.readline().strip()
        if not title:
            raise ValueError(f"Empty title in {path}")
        nvars_line = f.readline().strip()
        try:
            nvars = int(nvars_line.split()[0])
        except Exception as exc:
            raise ValueError(f"Invalid nvars line in {path}: {nvars_line}") from exc
        if nvars <= 0:
            raise ValueError(f"Invalid nvars in {path}: {nvars}")
        varnames = [f.readline().strip() for _ in range(nvars)]
    return title, nvars, varnames


def iter_data_rows(path: Path, nvars: int) -> Iterator[List[str]]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        _ = f.readline()
        for _ in range(nvars):
            _ = f.readline()
        for line in f:
            s = line.strip()
            if not s:
                continue
            parts = s.split()
            if len(parts) < nvars:
                continue
            yield parts


def list_depth_files() -> Dict[int, Path]:
    depth_files: Dict[int, Path] = {}
    for p in sorted(DATA_DIR.glob("tempIBHRes2024_*.gslib")):
        m = FILE_RE.match(p.name)
        if not m:
            continue
        depth = int(m.group(1))
        depth_files[depth] = p
    return depth_files


def require_exact_columns(path: Path, varnames: Iterable[str]) -> Dict[str, int]:
    expected = ["x", "y", "z", "temp"]
    found = [v.strip() for v in varnames]
    if found != expected:
        raise ValueError(f"Header columns must be exact {expected} in {path}, got {found}")
    return {name: i for i, name in enumerate(found)}


def run_first_pass(path: Path) -> DepthPass1:
    title, nvars, varnames = parse_header(path)
    idx = require_exact_columns(path, varnames)

    x_min = np.iinfo(np.int32).max
    x_max = np.iinfo(np.int32).min
    y_min = np.iinfo(np.int32).max
    y_max = np.iinfo(np.int32).min
    z_min = np.iinfo(np.int32).max
    z_max = np.iinfo(np.int32).min
    temp_min = np.inf
    temp_max = -np.inf
    n_values = 0

    for parts in iter_data_rows(path, nvars):
        try:
            x = int(round(float(parts[idx["x"]])))
            y = int(round(float(parts[idx["y"]])))
            z = int(round(float(parts[idx["z"]])))
            temp = float(parts[idx["temp"]])
        except Exception:
            continue

        x_min = min(x_min, x)
        x_max = max(x_max, x)
        y_min = min(y_min, y)
        y_max = max(y_max, y)
        z_min = min(z_min, z)
        z_max = max(z_max, z)

        if np.isfinite(temp):
            temp_min = min(temp_min, temp)
            temp_max = max(temp_max, temp)
            n_values += 1

    if z_min == np.iinfo(np.int32).max:
        raise RuntimeError(f"No valid rows found in {path}")
    if n_values == 0:
        raise RuntimeError(f"No finite temp values found in {path}")

    return DepthPass1(
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        z_min=z_min,
        z_max=z_max,
        temp_min=float(temp_min),
        temp_max=float(temp_max),
        n_values=n_values,
        nvars=nvars,
        varnames=varnames,
        title=title,
        idx=idx,
    )


def percentile_from_hist(hist: np.ndarray, edges: np.ndarray, q: float) -> float:
    total = int(hist.sum())
    if total <= 0:
        raise RuntimeError("Histogram is empty")
    target = q * total
    csum = np.cumsum(hist)
    idx = int(np.searchsorted(csum, target, side="left"))
    idx = max(0, min(idx, len(hist) - 1))
    left_edge = edges[idx]
    right_edge = edges[idx + 1]
    prev = int(csum[idx - 1]) if idx > 0 else 0
    count = int(hist[idx])
    if count <= 0:
        return float(left_edge)
    frac = (target - prev) / count
    frac = float(max(0.0, min(1.0, frac)))
    return float(left_edge + frac * (right_edge - left_edge))


def write_color_scale(
    out_path: Path,
    depth: int,
    source_file: Path,
    nx: int,
    ny: int,
    z_max: int,
    vmin: float,
    vmax: float,
) -> None:
    payload = {
        "depth": depth,
        "vmin": float(vmin),
        "vmax": float(vmax),
        "nx": int(nx),
        "ny": int(ny),
        "z_max": int(z_max),
        "source_file": str(source_file.relative_to(ROOT)).replace("\\", "/"),
        "percentiles": {"low": 2, "high": 98},
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_depth_products(depth: int, path: Path) -> Tuple[Dict, List[Dict]]:
    pass1 = run_first_pass(path)
    nx = pass1.x_max
    ny = pass1.y_max
    z_max = pass1.z_max
    export_z_max = z_max if z_max < TARGET_MIN_Z else TARGET_MIN_Z

    if pass1.x_min != 1 or pass1.y_min != 1:
        raise RuntimeError(f"Unexpected coordinate start in {path}: x_min={pass1.x_min}, y_min={pass1.y_min}")
    if pass1.z_min > 1:
        raise RuntimeError(f"Unexpected z_min in {path}: {pass1.z_min}")

    print(f"[DEPTH {depth:02d}] header={pass1.varnames} dims x=1..{nx} y=1..{ny} z=1..{z_max}")
    if z_max < TARGET_MIN_Z:
        print(f"[DEPTH {depth:02d}] z_max={z_max} < 300, exporting only z=1..{z_max}")

    depth_dir = OUT_ROOT / f"depth_{depth:02d}"
    depth_dir.mkdir(parents=True, exist_ok=True)

    grids = np.full((export_z_max, ny, nx), np.nan, dtype=np.float32)
    edges = np.linspace(pass1.temp_min, pass1.temp_max, HIST_BINS + 1, dtype=np.float64)
    hist = np.zeros(HIST_BINS, dtype=np.int64)

    for parts in iter_data_rows(path, pass1.nvars):
        try:
            x = int(round(float(parts[pass1.idx["x"]])))
            y = int(round(float(parts[pass1.idx["y"]])))
            z = int(round(float(parts[pass1.idx["z"]])))
            temp = float(parts[pass1.idx["temp"]])
        except Exception:
            continue

        if not (1 <= x <= nx and 1 <= y <= ny and 1 <= z <= export_z_max):
            continue
        grids[z - 1, y - 1, x - 1] = temp

        if np.isfinite(temp):
            if pass1.temp_max == pass1.temp_min:
                bin_id = 0
            else:
                scaled = (temp - pass1.temp_min) / (pass1.temp_max - pass1.temp_min)
                bin_id = int(np.floor(scaled * HIST_BINS))
                bin_id = max(0, min(HIST_BINS - 1, bin_id))
            hist[bin_id] += 1

    vmin = percentile_from_hist(hist, edges, 0.02)
    vmax = percentile_from_hist(hist, edges, 0.98)
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        raise RuntimeError(f"Invalid color scale in depth {depth}: vmin={vmin}, vmax={vmax}")
    if vmin == vmax:
        vmax = vmin + 1e-12

    scale_path = OUT_ROOT / f"color_scale_depth{depth:02d}.json"
    write_color_scale(scale_path, depth, path, nx, ny, export_z_max, vmin, vmax)

    rows: List[Dict] = []
    for z in range(1, export_z_max + 1):
        arr = grids[z - 1]
        out_file = depth_dir / f"TEMP_depth{depth:02d}_z{z:03d}.png"
        plt.imsave(out_file, arr, cmap="viridis", vmin=vmin, vmax=vmax, origin="lower")

        missing = float(np.isnan(arr).sum()) / float(arr.size)
        row = {
            "depth": depth,
            "z": z,
            "date_iso": (START_DATE + timedelta(days=z - 1)).isoformat(),
            "filepath": str(out_file.relative_to(ROOT)).replace("\\", "/"),
            "mean_temp": float(np.nanmean(arr)),
            "std_temp": float(np.nanstd(arr)),
            "min_temp": float(np.nanmin(arr)),
            "max_temp": float(np.nanmax(arr)),
            "missing_fraction": missing,
        }
        rows.append(row)

    summary = {
        "depth": depth,
        "nx": nx,
        "ny": ny,
        "z_max": export_z_max,
        "vmin": vmin,
        "vmax": vmax,
        "generated": len(rows),
    }
    print(
        f"[DEPTH {depth:02d}] generated={len(rows)} images, "
        f"scale(p2/p98)=({vmin:.6f}, {vmax:.6f}), avg_missing={np.mean([r['missing_fraction'] for r in rows]) * 100:.4f}%"
    )
    return summary, rows


def write_index(all_rows: List[Dict]) -> None:
    fields = [
        "depth",
        "z",
        "date_iso",
        "filepath",
        "mean_temp",
        "std_temp",
        "min_temp",
        "max_temp",
        "missing_fraction",
    ]
    with INDEX_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)


def print_final_checks(summaries: List[Dict], all_rows: List[Dict]) -> None:
    total_images = sum(s["generated"] for s in summaries)
    dims = {(s["nx"], s["ny"], s["z_max"]) for s in summaries}
    avg_missing = float(np.mean([r["missing_fraction"] for r in all_rows]) * 100.0) if all_rows else np.nan
    print(f"[FINAL] total_pngs={total_images}")
    for s in summaries:
        print(f"[FINAL] depth={s['depth']:02d} pngs={s['generated']}")
    if len(dims) == 1:
        nx, ny, z_max = next(iter(dims))
        print(f"[FINAL] nx={nx}, ny={ny}, z_max={z_max}")
    else:
        print(f"[FINAL] dims vary by depth: {sorted(dims)}")
    print(f"[FINAL] average_nan_percent={avg_missing:.6f}%")

    rows_map = {(int(r["depth"]), int(r["z"])): r for r in all_rows}
    for depth in (1, 17):
        z_max_depth = max(int(r["z"]) for r in all_rows if int(r["depth"]) == depth)
        probe_z = [1, max(1, z_max_depth // 2), z_max_depth]
        for z in probe_z:
            r = rows_map[(depth, z)]
            print(
                "[FINAL] depth={d} z={z} mean={mean:.6f} std={std:.6f} min={mn:.6f} max={mx:.6f} missing={miss:.6f}".format(
                    d=depth,
                    z=z,
                    mean=r["mean_temp"],
                    std=r["std_temp"],
                    mn=r["min_temp"],
                    mx=r["max_temp"],
                    miss=r["missing_fraction"],
                )
            )


def main() -> None:
    depth_files = list_depth_files()
    print("[CHECK] Found GSLIB files:")
    for d in sorted(depth_files):
        print(f"[CHECK] depth={d:02d} file={depth_files[d].relative_to(ROOT)}")

    missing_depths = [d for d in EXPECTED_DEPTHS if d not in depth_files]
    if missing_depths:
        raise RuntimeError(f"Missing expected depths: {missing_depths}")

    # Required pre-check on 2-3 files.
    for d in (1, 2, 17):
        title, _nvars, varnames = parse_header(depth_files[d])
        _ = require_exact_columns(depth_files[d], varnames)
        print(f"[CHECK] depth={d:02d} title={title} header={varnames}")

    print("[CHECK] date_iso uses rule: 2024-01-01 + (z-1) days (no explicit date column in GSLIB)")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict] = []
    summaries: List[Dict] = []
    for depth in EXPECTED_DEPTHS:
        summary, rows = build_depth_products(depth, depth_files[depth])
        summaries.append(summary)
        all_rows.extend(rows)

    all_rows.sort(key=lambda r: (int(r["depth"]), int(r["z"])))
    write_index(all_rows)
    print(f"[FINAL] index_csv={INDEX_CSV.relative_to(ROOT)}")
    print_final_checks(summaries, all_rows)


if __name__ == "__main__":
    main()
