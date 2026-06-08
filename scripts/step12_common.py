from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import threading
import time
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
SCRIPTS = ROOT / "scripts"
PLANNER = ROOT / "OptimalPlanning_Lucrezia"
HRES = RESULTS / "cmems_370_surface_to_hres_20260509_135642"
STEP10F = RESULTS / "fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260519_195022"

ROI_ROW_MIN = 55
ROI_COL_MIN = 47
ROI_SHAPE = (72, 117)
CASE_ORDER = ["C01_representative", "C06_representative", "October_control"]
CASE_LABELS = {
    "C01_representative": "C01 representative",
    "C06_representative": "C06 representative",
    "October_control": "October reference",
}
CASE_JUSTIFICATION = {
    "C01_representative": "C01 preservado, STD alto, bom para testar se descriptors alteram trajetorias.",
    "C06_representative": "C06 estavel e bem classificado, bom como regime robusto.",
    "October_control": "Caso de outubro com predModel oficial validado, usado como referencia controlada.",
}
_PLANNER_SETUP_LOCK = threading.Lock()


def set_step10f(step10f_dir: Path) -> None:
    global STEP10F
    STEP10F = step10f_dir.resolve()


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return None if not math.isfinite(value) else value
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_step11a():
    return load_module("step11a_utils", SCRIPTS / "11a_run_minimal_boundary_planner_comparison.py")


def load_step11z():
    return load_module("step11z_utils", SCRIPTS / "11z_rerun_minimal_prototype_based_planner_tests.py")


def load_step11ab():
    return load_module("step11ab_utils", SCRIPTS / "11ab_c01_region_target_and_vehicle_weight_sweep.py")


def latest_step11y() -> Path:
    candidates = sorted(
        RESULTS.glob("fossum_roi_x490_step11y_prototype_based_planner_input_audit_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No Step11Y prototype-based planner input audit output found.")
    return candidates[0]


def latest_output(prefix: str) -> Path:
    candidates = sorted(RESULTS.glob(f"{prefix}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No output found for prefix {prefix}")
    return candidates[0]


def load_step11y_maps(step11y: Path | None = None) -> tuple[pd.DataFrame, dict[str, np.ndarray], Path]:
    step11y = (step11y or latest_step11y()).resolve()
    z = np.load(step11y / "prototype_based_all_planner_maps.npz", allow_pickle=True)
    cases = pd.DataFrame(
        {
            "case_id": [str(x) for x in z["case_ids"]],
            "date": [str(x) for x in z["dates"]],
            "predicted_class": z["predicted_classes"].astype(int),
        }
    )
    cases["case_order"] = cases["case_id"].map({case: i for i, case in enumerate(CASE_ORDER)})
    cases["case_label"] = cases["case_id"].map(CASE_LABELS).fillna(cases["case_id"])
    cases["case_justification"] = cases["case_id"].map(CASE_JUSTIFICATION).fillna("")
    cases = cases.sort_values("case_order").reset_index(drop=True)
    maps = {k: np.asarray(z[k], dtype=np.float32) for k in z.files if k not in ["case_ids", "dates", "predicted_classes"]}
    return cases, maps, step11y


def load_step10f_temp_mask(step10f_dir: Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    z = np.load((step10f_dir or STEP10F) / "planner_minimal_boundary_input_maps.npz", allow_pickle=True)
    return np.asarray(z["TEMPpred"], dtype=np.float32), np.asarray(z["mask"], dtype=bool)


def load_hres() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return np.load(HRES / "LAT_hres.npy"), np.load(HRES / "LON_hres.npy"), np.load(HRES / "BATHY_hres.npy")


def normalize_map(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    valid = mask & np.isfinite(arr)
    if not np.any(valid):
        return out
    lo = float(np.nanmin(arr[valid]))
    hi = float(np.nanmax(arr[valid]))
    out[valid] = 0.0 if hi <= lo else np.clip((arr[valid] - lo) / (hi - lo), 0.0, 1.0)
    return out


def get_case_index(cases: pd.DataFrame, case_id: str) -> int:
    row = cases[cases["case_id"].eq(case_id)]
    if row.empty:
        raise KeyError(case_id)
    return int(row.iloc[0]["case_order"])


def route_points_for_route(s11a, route: dict[str, Any], lat_hres: np.ndarray, lon_hres: np.ndarray) -> list[tuple[int, int]]:
    return s11a.route_grid_points([route], lat_hres, lon_hres)


def route_points_all(s11a, routes: list[dict[str, Any]], lat_hres: np.ndarray, lon_hres: np.ndarray) -> list[tuple[int, int]]:
    return s11a.route_grid_points(routes, lat_hres, lon_hres)


def route_to_roi(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(int(r) - ROI_ROW_MIN, int(c) - ROI_COL_MIN) for r, c in points]


def unique_valid(points: list[tuple[int, int]], valid_full: np.ndarray) -> list[tuple[int, int]]:
    seen: dict[tuple[int, int], None] = {}
    for r, c in points:
        if 0 <= r < valid_full.shape[0] and 0 <= c < valid_full.shape[1] and bool(valid_full[r, c]):
            seen[(int(r), int(c))] = None
    return list(seen.keys())


def sample_values(points: list[tuple[int, int]], arr: np.ndarray, valid_full: np.ndarray) -> np.ndarray:
    pts = unique_valid(points, valid_full)
    if not pts:
        return np.array([], dtype=float)
    rr = np.array([p[0] for p in pts], dtype=int)
    cc = np.array([p[1] for p in pts], dtype=int)
    vals = arr[rr, cc]
    return vals[np.isfinite(vals)]


def threshold_top10(arr: np.ndarray, valid_full: np.ndarray) -> float:
    vals = arr[valid_full & np.isfinite(arr)]
    return float(np.nanpercentile(vals, 90)) if vals.size else float("nan")


def path_overlap_difference(points: list[tuple[int, int]], baseline_points: list[tuple[int, int]], valid_full: np.ndarray) -> tuple[float, float]:
    a = set(unique_valid(points, valid_full))
    b = set(unique_valid(baseline_points, valid_full))
    if not a or not b:
        return float("nan"), float("nan")
    overlap = len(a & b) / max(len(a | b), 1)
    return float(overlap), float(1.0 - overlap)


def parse_solver_gap(run_dir: Path) -> float:
    texts = []
    for name in ["planner_stdout.txt", "planner_stderr.txt"]:
        path = run_dir / name
        if path.exists():
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(texts)
    patterns = [
        r"\bgap\b[^0-9+-]*([-+]?[0-9]*\.?[0-9]+)",
        r"\boptimality\s+gap\b[^0-9+-]*([-+]?[0-9]*\.?[0-9]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                pass
    return float("nan")


def route_length_duration(routes: list[dict[str, Any]]) -> tuple[float, float]:
    length = float(np.nansum([r.get("length_km", np.nan) for r in routes])) if routes else float("nan")
    durations = []
    for route in routes:
        h = route.get("mission_duration_h")
        m = route.get("mission_duration_m")
        if h is not None:
            durations.append(float(h) + float(m or 0) / 60.0)
    return length, float(np.nanmax(durations)) if durations else float("nan")


def make_region_masks(ab, cold: np.ndarray, warm: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    return ab.descriptor_region_masks(cold, warm, mask)


def boundary_core(boundary: np.ndarray, mask: np.ndarray) -> np.ndarray:
    vals = boundary[mask & np.isfinite(boundary)]
    if vals.size == 0:
        return np.zeros(boundary.shape, dtype=bool)
    return (boundary >= float(np.nanpercentile(vals, 90))) & mask & np.isfinite(boundary)


def md_table(df: pd.DataFrame, cols: list[str] | None = None, max_rows: int = 40, floatfmt: str = ".3f") -> str:
    if df.empty:
        return "_No data available._\n"
    view = df[[c for c in (cols or list(df.columns)) if c in df.columns]].head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else format(float(x), floatfmt))
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join("---" for _ in view.columns) + " |",
    ]
    for row in view.astype(str).values.tolist():
        lines.append("| " + " | ".join(v.replace("|", "\\|") for v in row) + " |")
    return "\n".join(lines) + "\n"


def prepare_outdir(output_root: Path, prefix: str) -> Path:
    outdir = output_root.resolve() / f"{prefix}_{now_tag()}"
    for sub in ["planner_inputs", "planner_runs", "planner_configs", "figures", "masks"]:
        (outdir / sub).mkdir(parents=True, exist_ok=True)
    return outdir


def short_name(run_id: str, max_prefix: int = 24) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in run_id)
    digest = hashlib.sha1(run_id.encode("utf-8")).hexdigest()[:10]
    return f"{safe[:max_prefix].rstrip('_-.')}__{digest}"


def run_planner(
    zutils,
    s11a,
    run_id: str,
    info_roi: np.ndarray,
    mask: np.ndarray,
    lat_hres: np.ndarray,
    lon_hres: np.ndarray,
    bathy_hres: np.ndarray,
    planner: Path,
    config_text: str,
    outdir: Path,
    timeout_s: int,
    skip_existing: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    physical_name = short_name(run_id)
    run_dir = outdir / "planner_runs" / physical_name
    input_nc = outdir / "planner_inputs" / f"{physical_name}.nc"
    run_dir.mkdir(parents=True, exist_ok=True)
    input_nc.parent.mkdir(parents=True, exist_ok=True)

    if skip_existing and (run_dir / "routes_file.txt").exists():
        runtime_s = 0.0
        runtime_source = "reused_existing_no_timestamp"
        route_file = run_dir / "routes_file.txt"
        candidates = [run_dir / input_nc.name, run_dir / "planner_command.txt", run_dir / "Config_file.py"]
        starts = [p.stat().st_mtime for p in candidates if p.exists()]
        if starts:
            runtime_s = max(0.0, float(route_file.stat().st_mtime - min(starts)))
            runtime_source = "estimated_from_file_timestamps"
        routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
        diag = {
            "run_id": run_id,
            "command": "REUSED_EXISTING",
            "returncode": 0,
            "runtime_s": runtime_s,
            "runtime_source": runtime_source,
            "status": "REUSED",
            "error": "",
            "input_nc": str(input_nc),
        }
    else:
        error = ""
        nc_meta: dict[str, Any] = {}
        try:
            # scipy/xarray NetCDF writing is not reliably thread-safe on Windows.
            # Keep setup serialized, then let the expensive planner subprocess run in parallel.
            with _PLANNER_SETUP_LOCK:
                nc_meta = s11a.build_interface_nc(input_nc, info_roi, mask, lat_hres, lon_hres, bathy_hres)
                run_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(input_nc, run_dir / input_nc.name)
                s11a.copy_planner_runtime(planner, run_dir, config_text)
            result = s11a.run_planner(run_dir, input_nc, timeout_s)
            status = "SUCCESS" if result["returncode"] == 0 and (run_dir / "routes_file.txt").exists() else "FAILED"
        except subprocess.TimeoutExpired as exc:
            result = {"command": " ".join(exc.cmd) if isinstance(exc.cmd, list) else str(exc.cmd), "returncode": -999, "runtime_s": timeout_s}
            status = "TIMEOUT"
            error = f"Timeout after {timeout_s}s"
        except Exception as exc:
            result = {"command": f"python OptimalPlanning.py {input_nc}", "returncode": -998, "runtime_s": float("nan")}
            status = "FAILED"
            error = repr(exc)
            try:
                (run_dir / "planner_stderr.txt").write_text(error, encoding="utf-8")
            except Exception:
                pass
        routes = s11a.parse_routes_file(run_dir / "routes_file.txt")
        try:
            s11a.save_trajectory_csv_json(run_dir, routes)
        except Exception:
            pass
        diag = {**result, **nc_meta, "run_id": run_id, "status": status, "error": error, "input_nc": str(input_nc)}
    diag = dict(diag)
    diag["run_id"] = run_id
    diag["solver_status"] = diag.get("status", "")
    diag["solver_runtime_s"] = diag.get("runtime_s", np.nan)
    diag["solver_gap"] = parse_solver_gap(run_dir)
    diag["run_dir"] = rel(run_dir)
    return diag, routes, run_dir


def plot_paths_on_map(
    arr: np.ndarray,
    paths: dict[str, list[tuple[int, int]]],
    out: Path,
    title: str,
    cmap: str = "viridis",
    vmin: float | None = 0.0,
    vmax: float | None = 1.0,
    color_cycle: list[str] | None = None,
    diagnostic_note: str | None = None,
    region_a: np.ndarray | None = None,
    region_b: np.ndarray | None = None,
) -> None:
    color_cycle = color_cycle or ["black", "#f6b300", "#00a9c8", "white", "yellow", "lime"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    if region_a is not None:
        ax.contour(region_a.astype(float), levels=[0.5], colors=["#2b6cb0"], linewidths=0.8, alpha=0.9)
    if region_b is not None:
        ax.contour(region_b.astype(float), levels=[0.5], colors=["#c53030"], linewidths=0.8, alpha=0.9)
    for i, (label, pts_full) in enumerate(paths.items()):
        pts = route_to_roi(pts_full)
        if pts:
            ax.plot([p[1] for p in pts], [p[0] for p in pts], color=color_cycle[i % len(color_cycle)], lw=1.5, marker="o", markersize=1.8, label=label)
    if diagnostic_note:
        ax.text(0.015, 0.02, diagnostic_note, transform=ax.transAxes, fontsize=8, va="bottom", bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none"})
    ax.set_title(title)
    ax.set_xlabel("ROI column")
    ax.set_ylabel("ROI row")
    ax.set_xlim(-1, ROI_SHAPE[1])
    ax.set_ylim(-1, ROI_SHAPE[0])
    ax.legend(fontsize=7, loc="upper right")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label(title.split(" over ")[-1] if " over " in title else "map value")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_grouped_bar(df: pd.DataFrame, x: str, y: str, hue: str | None, out: Path, title: str) -> None:
    if df.empty or x not in df.columns or y not in df.columns:
        return
    data = df.copy()
    data[y] = pd.to_numeric(data[y], errors="coerce")
    fig, ax = plt.subplots(figsize=(12, 5))
    if hue and hue in data.columns:
        labels = list(data[hue].astype(str).dropna().unique())
        xlabels = list(data[x].astype(str).dropna().unique())
        xs = np.arange(len(xlabels))
        width = 0.8 / max(len(labels), 1)
        for i, label in enumerate(labels):
            sub = data[data[hue].astype(str).eq(label)]
            vals = [sub[sub[x].astype(str).eq(lbl)][y].mean() for lbl in xlabels]
            ax.bar(xs + i * width - 0.4 + width / 2, vals, width=width, label=label)
        ax.set_xticks(xs)
        ax.set_xticklabels(xlabels, rotation=35, ha="right")
        ax.legend(fontsize=8)
    else:
        grouped = data.groupby(data[x].astype(str))[y].mean()
        ax.bar(grouped.index, grouped.values)
        ax.tick_params(axis="x", rotation=35)
    ax.set_title(title)
    ax.set_ylabel(y)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_scatter(df: pd.DataFrame, x: str, y: str, color_col: str | None, out: Path, title: str) -> None:
    if df.empty or x not in df.columns or y not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    if color_col and color_col in df.columns:
        labels = list(df[color_col].astype(str).dropna().unique())
        for label in labels:
            sub = df[df[color_col].astype(str).eq(label)]
            ax.scatter(pd.to_numeric(sub[x], errors="coerce"), pd.to_numeric(sub[y], errors="coerce"), label=label, s=45)
        ax.legend(fontsize=8)
    else:
        ax.scatter(pd.to_numeric(df[x], errors="coerce"), pd.to_numeric(df[y], errors="coerce"), s=45)
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
