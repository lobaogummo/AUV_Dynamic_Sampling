"""Export 300 deterministic 2024 surface TEMP maps from GSLIB depth=1 source."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from physical_coords import load_physical_lon_lat
from pil_geo_plot import save_geo_heatmap_png

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MPL = True
except Exception:
    HAS_MPL = False


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "2024"
EXACT_SOURCE = DATA_DIR / "tempIBHRes2024_1.gslib"
SOURCE_GLOB = "tempIBHRes2024_1*.gslib"

OUT_DIR = ROOT / "results" / "plots" / "deterministic_2024_surface_300"
OUT_SCALE = OUT_DIR / "color_scale.json"
OUT_INDEX = OUT_DIR / "index.csv"

NX = 112
NY = 64
TARGET_Z_MIN = 1
TARGET_Z_MAX = 300


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export thesis-ready deterministic 2024 surface TEMP maps.")
    parser.add_argument("--z-start", type=int, default=TARGET_Z_MIN, help="First z (1-based, inclusive).")
    parser.add_argument("--z-end", type=int, default=TARGET_Z_MAX, help="Last z (1-based, inclusive).")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help="Output folder for PNGs and index.")
    parser.add_argument(
        "--fixed-scale-json",
        type=Path,
        default=None,
        help="Optional JSON containing vmin/vmax to enforce exact pre-existing color scale.",
    )
    return parser.parse_args()


def resolve_source_file() -> Path:
    if EXACT_SOURCE.exists():
        return EXACT_SOURCE
    matches = sorted(DATA_DIR.glob(SOURCE_GLOB))
    if not matches:
        raise FileNotFoundError(f"No source matched {DATA_DIR / SOURCE_GLOB}")
    return matches[0]


def parse_header(path: Path) -> Tuple[str, List[str]]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        title = f.readline().strip()
        if not title:
            raise ValueError("Empty GSLIB title line")
        nvars_line = f.readline().strip()
        if not nvars_line:
            raise ValueError("Missing nvars line")
        try:
            nvars = int(nvars_line.split()[0])
        except Exception as exc:
            raise ValueError(f"Invalid nvars line: {nvars_line}") from exc
        if nvars <= 0:
            raise ValueError(f"Invalid nvars value: {nvars}")
        varnames = []
        for i in range(nvars):
            line = f.readline()
            if not line:
                raise ValueError(f"Unexpected EOF while reading var names (expected {nvars}, got {i})")
            varnames.append(line.strip())
    return title, varnames


def _validate_columns(varnames: List[str]) -> Dict[str, int]:
    lowered = [v.strip().lower() for v in varnames]
    required = {"x", "y", "z", "temp"}
    missing = [name for name in required if name not in lowered]
    if missing:
        raise ValueError(f"Missing required columns in GSLIB header: {missing}. Found: {varnames}")
    return {name: lowered.index(name) for name in required}


def _data_line_iter(path: Path, nvars: int):
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


def first_pass(
    path: Path,
    nvars: int,
    idx: Dict[str, int],
) -> Tuple[int, int, int, int, int, int, np.ndarray]:
    x_min = np.iinfo(np.int32).max
    x_max = np.iinfo(np.int32).min
    y_min = np.iinfo(np.int32).max
    y_max = np.iinfo(np.int32).min
    z_min = np.iinfo(np.int32).max
    z_max = np.iinfo(np.int32).min

    temps_for_scale: List[float] = []
    for parts in _data_line_iter(path, nvars):
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

        if TARGET_Z_MIN <= z <= TARGET_Z_MAX and np.isfinite(temp):
            temps_for_scale.append(temp)

    if z_min == np.iinfo(np.int32).max:
        raise RuntimeError("No valid data rows read from GSLIB")
    if z_max < TARGET_Z_MAX:
        raise RuntimeError(f"z_max < {TARGET_Z_MAX}. Found z_max={z_max}")
    if x_min != 1 or x_max != NX or y_min != 1 or y_max != NY:
        raise RuntimeError(
            f"Unexpected grid extents. Found x={x_min}..{x_max}, y={y_min}..{y_max}. Expected x=1..{NX}, y=1..{NY}"
        )
    if not temps_for_scale:
        raise RuntimeError("No finite temp values found for z=1..300")

    return x_min, x_max, y_min, y_max, z_min, z_max, np.asarray(temps_for_scale, dtype=np.float64)


def second_pass_build_grids(
    path: Path,
    nvars: int,
    idx: Dict[str, int],
) -> np.ndarray:
    grids = np.full((TARGET_Z_MAX, NY, NX), np.nan, dtype=np.float32)
    for parts in _data_line_iter(path, nvars):
        try:
            x = int(round(float(parts[idx["x"]])))
            y = int(round(float(parts[idx["y"]])))
            z = int(round(float(parts[idx["z"]])))
            temp = float(parts[idx["temp"]])
        except Exception:
            continue
        if not (TARGET_Z_MIN <= z <= TARGET_Z_MAX):
            continue
        if not (1 <= x <= NX and 1 <= y <= NY):
            continue
        grids[z - 1, y - 1, x - 1] = temp
    return grids


def write_color_scale(source_file: Path, vmin: float, vmax: float, z_min: int, z_max: int, out_scale: Path, coord_meta: Dict[str, object]) -> None:
    payload = {
        "vmin": float(vmin),
        "vmax": float(vmax),
        "nx": NX,
        "ny": NY,
        "z_min": int(z_min),
        "z_max": int(z_max),
        "source_file": str(source_file.relative_to(ROOT)).replace("\\", "/"),
        "coord_source": coord_meta,
    }
    out_scale.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def render_pngs_and_index(
    grids: np.ndarray,
    vmin: float,
    vmax: float,
    lon: np.ndarray,
    lat: np.ndarray,
    z_start: int,
    z_end: int,
    out_dir: Path,
) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    extent = [float(np.nanmin(lon)), float(np.nanmax(lon)), float(np.nanmin(lat)), float(np.nanmax(lat))]
    for z in range(z_start, z_end + 1):
        arr = grids[z - 1]
        out_file = out_dir / f"TEMP_surface_2024_z{z:03d}.png"

        title = f"Surface temperature - 2024 day z={z:03d}"
        if HAS_MPL:
            fig, ax = plt.subplots(figsize=(7.0, 4.2))
            cmap = plt.get_cmap("viridis").copy()
            cmap.set_bad(color="white")
            im = ax.imshow(arr, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", extent=extent)
            ax.set_title(title)
            ax.set_xlabel("Longitude (degrees)")
            ax.set_ylabel("Latitude (degrees)")
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label("Temperature (°C)")
            fig.tight_layout()
            fig.savefig(out_file, dpi=150)
            plt.close(fig)
        else:
            save_geo_heatmap_png(
                arr=arr,
                lon=lon,
                lat=lat,
                vmin=vmin,
                vmax=vmax,
                title=title,
                xlabel="Longitude (degrees)",
                ylabel="Latitude (degrees)",
                cbar_label="Temperature (°C)",
                out_path=out_file,
                cmap_name="viridis",
            )

        finite = np.isfinite(arr)
        missing_fraction = 1.0 - (float(np.count_nonzero(finite)) / float(arr.size))
        rows.append(
            {
                "z": z,
                "filepath": str(out_file.relative_to(ROOT)).replace("\\", "/"),
                "lon_min": extent[0],
                "lon_max": extent[1],
                "lat_min": extent[2],
                "lat_max": extent[3],
                "mean_temp": float(np.nanmean(arr)),
                "std_temp": float(np.nanstd(arr)),
                "min_temp": float(np.nanmin(arr)),
                "max_temp": float(np.nanmax(arr)),
                "missing_fraction": float(missing_fraction),
            }
        )
    return rows


def write_index(rows: List[Dict[str, float]]) -> None:
    fields = [
        "z",
        "filepath",
        "lon_min",
        "lon_max",
        "lat_min",
        "lat_max",
        "mean_temp",
        "std_temp",
        "min_temp",
        "max_temp",
        "missing_fraction",
    ]
    with OUT_INDEX.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    z_start = max(TARGET_Z_MIN, int(args.z_start))
    z_end = min(TARGET_Z_MAX, int(args.z_end))
    if z_start > z_end:
        raise RuntimeError(f"Invalid z range: z_start={z_start}, z_end={z_end}")

    out_dir = args.out_dir.resolve()
    out_scale = out_dir / OUT_SCALE.name
    out_index = out_dir / OUT_INDEX.name

    source_file = resolve_source_file()
    title, varnames = parse_header(source_file)
    idx = _validate_columns(varnames)
    nvars = len(varnames)

    x_min, x_max, y_min, y_max, z_min, z_max, temps_for_scale = first_pass(source_file, nvars, idx)
    if args.fixed_scale_json is not None:
        scale_path = args.fixed_scale_json.resolve()
        payload = json.loads(scale_path.read_text(encoding="utf-8"))
        vmin = float(payload["vmin"])
        vmax = float(payload["vmax"])
    else:
        vmin = float(np.percentile(temps_for_scale, 2.0))
        vmax = float(np.percentile(temps_for_scale, 98.0))
        if not np.isfinite(vmin) or not np.isfinite(vmax):
            raise RuntimeError(f"Invalid color scale bounds: vmin={vmin}, vmax={vmax}")
        if vmin == vmax:
            vmax = vmin + 1e-12

    out_dir.mkdir(parents=True, exist_ok=True)
    lon, lat, coord_meta = load_physical_lon_lat(ROOT, NX, NY)
    write_color_scale(source_file, vmin, vmax, z_min, z_max, out_scale, coord_meta)

    grids = second_pass_build_grids(source_file, nvars, idx)
    index_rows = render_pngs_and_index(grids, vmin, vmax, lon, lat, z_start, z_end, out_dir)
    with out_index.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "z",
            "filepath",
            "lon_min",
            "lon_max",
            "lat_min",
            "lat_max",
            "mean_temp",
            "std_temp",
            "min_temp",
            "max_temp",
            "missing_fraction",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(index_rows)

    missing_pct_mean = float(np.mean([row["missing_fraction"] for row in index_rows]) * 100.0)

    sample_map = {int(r["z"]): r for r in index_rows}
    print(f"[OK] source_file={source_file}")
    print(f"[OK] title={title}")
    print(f"[OK] columns={varnames}")
    print(f"[OK] x_range={x_min}..{x_max}, y_range={y_min}..{y_max}, z_range={z_min}..{z_max}")
    print(f"[OK] color_scale_p2_p98 vmin={vmin:.6f}, vmax={vmax:.6f}")
    print(f"[OK] coord_source_method={coord_meta.get('method')}")
    print(f"[OK] images_generated={len(index_rows)}")
    print(f"[OK] average_nan_percent={missing_pct_mean:.6f}%")
    for z in sorted({z_start, (z_start + z_end) // 2, z_end}):
        if z in sample_map:
            row = sample_map[z]
            print(
                "[OK] z={z} mean={mean:.6f} std={std:.6f} min={mn:.6f} max={mx:.6f} missing_fraction={miss:.6f}".format(
                    z=z,
                    mean=row["mean_temp"],
                    std=row["std_temp"],
                    mn=row["min_temp"],
                    mx=row["max_temp"],
                    miss=row["missing_fraction"],
                )
            )


if __name__ == "__main__":
    main()
