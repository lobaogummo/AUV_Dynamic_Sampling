from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_planner_core(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    (dst_dir / "plots").mkdir(parents=True, exist_ok=True)
    for name in ["Config_file.py", "OptimalPlanning.py", "Utils.py", "README.txt"]:
        shutil.copy2(src_dir / name, dst_dir / name)


def build_surface_day1_interface(source_nc: Path, interface_nc: Path) -> dict[str, Any]:
    ds = xr.open_dataset(source_nc, decode_times=False)

    lat = np.asarray(ds["LAT"].values, dtype=np.float64)
    lon = np.asarray(ds["LON"].values, dtype=np.float64)
    std = np.asarray(ds["STD"].values, dtype=np.float32)
    bathy = np.asarray(ds["BATHY"].values, dtype=np.float32)

    if std.ndim != 3 or std.shape[0] < 2:
        raise RuntimeError(f"Expected STD with day dimension (>=2). Got shape={std.shape}")

    day_index = 1
    temperr = std[day_index].copy()
    tbath = -bathy.copy()
    landt = (np.isfinite(temperr) & np.isfinite(tbath)).astype(np.int8)

    temperr[landt == 0] = -np.inf
    tbath[landt == 0] = np.nan

    out_ds = xr.Dataset(
        data_vars={
            "temperr": (("lat", "lon"), temperr),
            "tbath": (("lat", "lon"), tbath),
            "landt": (("lat", "lon"), landt),
        },
        coords={
            "lat": ("lat", lat),
            "lon": ("lon", lon),
        },
        attrs={
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_nc": str(source_nc),
            "surface_policy": "surface-only",
            "temperr_rule": "STD[day=1,:,:]",
            "tbath_rule": "tbath=-BATHY",
            "assimilated_source_used": "false",
        },
    )
    out_ds["temperr"].attrs.update(
        {"long_name": "temperature_uncertainty", "source_var": "STD", "source_slice": "STD[day=1,LAT,LON]"}
    )
    out_ds["tbath"].attrs.update({"long_name": "bathymetry_for_planner", "source_var": "BATHY", "transform": "tbath=-BATHY"})
    out_ds["landt"].attrs.update({"long_name": "land_sea_mask", "convention": "1=sea(valid), 0=land/invalid"})

    interface_nc.parent.mkdir(parents=True, exist_ok=True)
    out_ds.to_netcdf(interface_nc)
    out_ds.close()
    ds.close()

    finite_mask = np.isfinite(temperr)
    return {
        "path": str(interface_nc),
        "source_nc": str(source_nc),
        "source_slice": "STD[day=1,LAT,LON]",
        "shape": [int(temperr.shape[0]), int(temperr.shape[1])],
        "finite_fraction": float(np.mean(finite_mask)),
        "temperr_min": float(np.nanmin(temperr[finite_mask])),
        "temperr_max": float(np.nanmax(temperr[finite_mask])),
    }


def parse_solver_blocks(log_text: str) -> list[dict[str, Any]]:
    pat = re.compile(
        r"Solution results\s*=+\s*"
        r"# routes:\s*(\d+)\s*"
        r"# clients:\s*(\d+)\s*"
        r"objective:\s*([0-9]+)\s*"
        r"distance:\s*([0-9]+)\s*"
        r"duration:\s*([0-9]+)\s*"
        r"# iterations:\s*([0-9]+)\s*"
        r"run-time:\s*([0-9]+(?:\.[0-9]+)?)\s*seconds",
        re.MULTILINE,
    )
    blocks = []
    for m in pat.finditer(log_text):
        blocks.append(
            {
                "n_routes": int(m.group(1)),
                "n_clients": int(m.group(2)),
                "objective": int(m.group(3)),
                "distance": int(m.group(4)),
                "duration": int(m.group(5)),
                "iterations": int(m.group(6)),
                "solver_runtime_s": float(m.group(7)),
            }
        )
    return blocks


def parse_candidate_clients(log_text: str) -> int | None:
    m = re.search(r"Solving an instance with:\s*\n\s*\d+\s+depots\s*\n\s*(\d+)\s+clients", log_text, re.MULTILINE)
    if m:
        return int(m.group(1))
    return None


def parse_total_prize(log_text: str) -> dict[str, float | None]:
    wp = re.search(r"Total WP Routes Temperr .*?\n([0-9]+(?:\.[0-9]+)?)", log_text)
    allv = re.search(r"Total All Routes Temperr .*?\n([0-9]+(?:\.[0-9]+)?)", log_text)
    return {
        "total_wp_temperr": float(wp.group(1)) if wp else None,
        "total_all_temperr": float(allv.group(1)) if allv else None,
    }


def parse_routes_file(routes_path: Path) -> dict[str, Any]:
    if not routes_path.exists():
        return {"exists": False}

    lines = routes_path.read_text(encoding="utf-8", errors="replace").splitlines()
    route_specs = []
    waypoint_counts = []

    pat_spec = re.compile(
        r"#length_2D:\s*([0-9.]+)\s*\[km\]\s*travel_duration:\s*(\d+)\s*\[h\]\s*(\d+)\s*\[m\]\s*"
        r"mission_duration:\s*(\d+)\s*\[h\]\s*(\d+)\s*\[m\]\s*minimum_depth:\s*([0-9.]+)\s*\[m\]"
    )

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = pat_spec.match(line)
        if m:
            route_specs.append(
                {
                    "length_km": float(m.group(1)),
                    "travel_h": int(m.group(2)),
                    "travel_m": int(m.group(3)),
                    "mission_h": int(m.group(4)),
                    "mission_m": int(m.group(5)),
                    "minimum_depth_m": float(m.group(6)),
                }
            )
            # next non-empty non-comment line should be waypoints
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j < len(lines):
                wp_line = lines[j]
                waypoints = [seg.strip() for seg in wp_line.split(";") if seg.strip()]
                waypoint_counts.append(len(waypoints))
                i = j
        i += 1

    return {
        "exists": True,
        "route_specs": route_specs,
        "route_waypoint_counts_including_start_end": waypoint_counts,
    }


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_csv_comparison(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)


def main() -> None:
    scenario_dir = Path(__file__).resolve().parent
    repo_root = scenario_dir.parents[1]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    source_nc = repo_root / "data" / "TEST_D4" / "HighRes" / "Daily_dpt_20241029_NewTest_1" / "30-10-2024_predModel_1.nc"
    baseline_metrics_json = scenario_dir / "outputs" / "planner_run" / "run_metrics.json"
    baseline_plot = scenario_dir / "outputs" / "planner_run" / "20260418T171719Z_wt.png"
    planner_src = scenario_dir / "planner_snapshot"

    rerun_root = scenario_dir / "outputs" / f"final_rerun_surface_day1_{ts}"
    inputs_dir = rerun_root / "inputs"
    planner_run_dir = rerun_root / "planner_run"
    planner_work = rerun_root / "planner_snapshot"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    planner_run_dir.mkdir(parents=True, exist_ok=True)

    interface_nc = inputs_dir / "30-10-2024_surface_day1_planner_interface.nc"
    log_file = planner_run_dir / "planner_stdout_surface_day1_final.log"
    runtime_file = planner_run_dir / "planner_runtime_surface_day1_final.txt"
    routes_file_dst = planner_run_dir / "routes_file_surface_day1_final.txt"
    routes_est_dst = planner_run_dir / "routes_file_node_estimation_surface_day1_final.txt"
    plot_dst = planner_run_dir / "planner_plot_surface_day1_final.png"
    vrp_dst = planner_run_dir / "VRP_instance_problem_surface_day1_final.vrp"
    metrics_json = planner_run_dir / "run_metrics_surface_day1_final.json"
    comparison_json = planner_run_dir / "final_rerun_comparison.json"
    comparison_csv = planner_run_dir / "final_rerun_comparison.csv"
    report_md = planner_run_dir / "final_rerun_report.md"
    summary_md = planner_run_dir / "final_rerun_summary.md"
    manifest_json = planner_run_dir / "final_rerun_manifest.json"

    # 1) Build final interface (strict day=1 from prior model file).
    interface_info = build_surface_day1_interface(source_nc=source_nc, interface_nc=interface_nc)

    # 2) Run planner in isolated snapshot copy.
    copy_planner_core(planner_src, planner_work)
    cmd = [sys.executable, "OptimalPlanning.py", str(interface_nc)]
    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=planner_work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "MPLBACKEND": "Agg"},
    )
    elapsed = time.perf_counter() - start

    full_log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    log_file.write_text(full_log, encoding="utf-8")
    runtime_file.write_text(f"elapsed_seconds={elapsed:.6f}\nexit_code={proc.returncode}\n", encoding="utf-8")

    # Copy raw planner outputs if present.
    routes_file_src = planner_work / "routes_file.txt"
    routes_est_src = planner_work / "routes_file_node_estimation.txt"
    vrp_src = planner_work / "VRP_instance_problem.vrp"
    if routes_file_src.exists():
        shutil.copy2(routes_file_src, routes_file_dst)
    if routes_est_src.exists():
        shutil.copy2(routes_est_src, routes_est_dst)
    if vrp_src.exists():
        shutil.copy2(vrp_src, vrp_dst)

    plot_src = None
    plots_dir = planner_work / "plots"
    if plots_dir.exists():
        wt_plots = sorted(plots_dir.glob("*_wt.png"), key=lambda p: p.stat().st_mtime)
        if wt_plots:
            plot_src = wt_plots[-1]
            shutil.copy2(plot_src, plot_dst)

    # 3) Parse run metrics.
    solver_blocks = parse_solver_blocks(full_log)
    final_block = solver_blocks[-1] if solver_blocks else None
    candidate_clients = parse_candidate_clients(full_log)
    prize_info = parse_total_prize(full_log)
    routes_info = parse_routes_file(routes_file_dst)

    current_metrics = {
        "exit_code": proc.returncode,
        "elapsed_seconds_total": elapsed,
        "candidate_clients": candidate_clients,
        "solver_blocks": solver_blocks,
        "final_solver_block": final_block,
        "route_specs_final": routes_info.get("route_specs", []) if routes_info.get("exists") else [],
        "route_waypoint_counts_including_start_end": routes_info.get("route_waypoint_counts_including_start_end", [])
        if routes_info.get("exists")
        else [],
        **prize_info,
    }
    metrics_json.write_text(json.dumps(current_metrics, indent=2), encoding="utf-8")

    # 4) Compare with previous baseline (31-10).
    baseline_metrics = {}
    if baseline_metrics_json.exists():
        baseline_metrics = json.loads(baseline_metrics_json.read_text(encoding="utf-8"))
    prev_final = baseline_metrics.get("final_solver_block", {})
    prev_candidate = None
    prev_blocks = baseline_metrics.get("solver_blocks", [])
    if prev_blocks:
        prev_candidate = prev_blocks[0].get("n_clients")  # this is visited in first solve; not candidate
    # Candidate clients are not in previous JSON, so try parsing previous log:
    prev_log_text = read_text_if_exists(scenario_dir / "outputs" / "planner_run" / "planner_stdout_final.log")
    prev_candidate_from_log = parse_candidate_clients(prev_log_text)
    if prev_candidate_from_log is not None:
        prev_candidate = prev_candidate_from_log

    cur_final = final_block or {}
    comparison = {
        "baseline_label": "previous_31-10_input",
        "rerun_label": "surface_day1_30-10_prior_input",
        "baseline_candidate_clients": prev_candidate,
        "rerun_candidate_clients": candidate_clients,
        "baseline_visited_points_final": prev_final.get("n_clients"),
        "rerun_visited_points_final": cur_final.get("n_clients"),
        "baseline_final_objective": prev_final.get("objective"),
        "rerun_final_objective": cur_final.get("objective"),
        "baseline_n_routes_final": prev_final.get("n_routes"),
        "rerun_n_routes_final": cur_final.get("n_routes"),
        "baseline_plot": str(baseline_plot) if baseline_plot.exists() else None,
        "rerun_plot": str(plot_dst) if plot_dst.exists() else None,
        "visual_note": "Both plots keep same PC-VRP layout; rerun uses prior 30-10 day=1 uncertainty field and may shift sampled hotspots/routes.",
    }

    # Add numeric deltas where possible.
    if comparison["baseline_final_objective"] is not None and comparison["rerun_final_objective"] is not None:
        comparison["delta_objective"] = int(comparison["rerun_final_objective"]) - int(comparison["baseline_final_objective"])
    else:
        comparison["delta_objective"] = None
    if comparison["baseline_visited_points_final"] is not None and comparison["rerun_visited_points_final"] is not None:
        comparison["delta_visited_points"] = int(comparison["rerun_visited_points_final"]) - int(
            comparison["baseline_visited_points_final"]
        )
    else:
        comparison["delta_visited_points"] = None
    if comparison["baseline_n_routes_final"] is not None and comparison["rerun_n_routes_final"] is not None:
        comparison["delta_n_routes"] = int(comparison["rerun_n_routes_final"]) - int(comparison["baseline_n_routes_final"])
    else:
        comparison["delta_n_routes"] = None
    if comparison["baseline_candidate_clients"] is not None and comparison["rerun_candidate_clients"] is not None:
        comparison["delta_candidate_clients"] = int(comparison["rerun_candidate_clients"]) - int(comparison["baseline_candidate_clients"])
    else:
        comparison["delta_candidate_clients"] = None

    comparison_json.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    write_csv_comparison(
        comparison_csv,
        [
            {
                "metric": "candidate_clients",
                "baseline": comparison["baseline_candidate_clients"],
                "rerun": comparison["rerun_candidate_clients"],
                "delta_rerun_minus_baseline": comparison["delta_candidate_clients"],
            },
            {
                "metric": "visited_points_final",
                "baseline": comparison["baseline_visited_points_final"],
                "rerun": comparison["rerun_visited_points_final"],
                "delta_rerun_minus_baseline": comparison["delta_visited_points"],
            },
            {
                "metric": "final_objective",
                "baseline": comparison["baseline_final_objective"],
                "rerun": comparison["rerun_final_objective"],
                "delta_rerun_minus_baseline": comparison["delta_objective"],
            },
            {
                "metric": "n_routes_final",
                "baseline": comparison["baseline_n_routes_final"],
                "rerun": comparison["rerun_n_routes_final"],
                "delta_rerun_minus_baseline": comparison["delta_n_routes"],
            },
        ],
    )

    # 5) Final report and summary.
    run_ok = proc.returncode == 0 and final_block is not None
    report_lines = [
        "# final_rerun_report",
        "",
        "## Input used",
        f"- source file: `{source_nc}`",
        "- source type: `predModel` (a priori), no AUVpredModel fallback",
        "- surface policy: `surface-only`",
        f"- slice used: `{interface_info['source_slice']}`",
        "- tbath transform: `tbath = -BATHY`",
        f"- interface file: `{interface_nc}`",
        "",
        "## Audit context",
        "- day=1 was selected by numeric/visual evidence (day=0 nearly null), not by explicit semantic metadata in NetCDF.",
        "",
        "## Planner execution",
        f"- command: `python OptimalPlanning.py {interface_nc}`",
        f"- planner workspace: `{planner_work}`",
        f"- exit code: `{proc.returncode}`",
        f"- elapsed seconds: `{elapsed:.6f}`",
        f"- stdout/stderr log: `{log_file}`",
        f"- runtime file: `{runtime_file}`",
        "",
        "## Core outputs",
        f"- routes file: `{routes_file_dst}`",
        f"- node estimation routes file: `{routes_est_dst}`",
        f"- VRP instance file: `{vrp_dst}`",
        f"- final plot: `{plot_dst}`",
        "",
        "## Final metrics",
        f"- candidate clients: `{candidate_clients}`",
        f"- visited points (final): `{cur_final.get('n_clients') if cur_final else None}`",
        f"- final objective: `{cur_final.get('objective') if cur_final else None}`",
        f"- number of routes: `{cur_final.get('n_routes') if cur_final else None}`",
        "",
        "## Comparison vs previous baseline",
        f"- comparison json: `{comparison_json}`",
        f"- comparison csv: `{comparison_csv}`",
        f"- candidate clients: baseline `{comparison['baseline_candidate_clients']}` vs rerun `{comparison['rerun_candidate_clients']}`",
        f"- visited points: baseline `{comparison['baseline_visited_points_final']}` vs rerun `{comparison['rerun_visited_points_final']}`",
        f"- objective: baseline `{comparison['baseline_final_objective']}` vs rerun `{comparison['rerun_final_objective']}`",
        f"- routes: baseline `{comparison['baseline_n_routes_final']}` vs rerun `{comparison['rerun_n_routes_final']}`",
        f"- visual note: {comparison['visual_note']}",
        "",
        "## Execution status",
        f"- success: `{run_ok}`",
    ]
    report_md.write_text("\n".join(report_lines), encoding="utf-8")

    summary_lines = [
        "# final_rerun_summary",
        "",
        f"- status: {'RERUN SUCCESS' if run_ok else 'RERUN FAILED'}",
        f"- input file: `{source_nc.name}`",
        f"- slice: `{interface_info['source_slice']}`",
        f"- final objective: `{cur_final.get('objective') if cur_final else None}`",
        f"- visited points: `{cur_final.get('n_clients') if cur_final else None}`",
        f"- routes: `{cur_final.get('n_routes') if cur_final else None}`",
        f"- final plot: `{plot_dst}`",
    ]
    summary_md.write_text("\n".join(summary_lines), encoding="utf-8")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_dir": str(scenario_dir),
        "rerun_root": str(rerun_root),
        "input": interface_info,
        "planner": {
            "workspace": str(planner_work),
            "command": cmd,
            "exit_code": proc.returncode,
            "elapsed_seconds": elapsed,
            "log_file": str(log_file),
            "runtime_file": str(runtime_file),
        },
        "outputs": {
            "routes_file": str(routes_file_dst),
            "routes_node_estimation_file": str(routes_est_dst),
            "vrp_instance_file": str(vrp_dst),
            "plot_file": str(plot_dst),
            "metrics_json": str(metrics_json),
            "comparison_json": str(comparison_json),
            "comparison_csv": str(comparison_csv),
            "report_md": str(report_md),
            "summary_md": str(summary_md),
        },
        "integrity": {
            "source_nc_sha256": sha256_file(source_nc),
            "interface_nc_sha256": sha256_file(interface_nc),
        },
        "run_ok": run_ok,
    }
    manifest_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("[OK] rerun_root:", rerun_root)
    print("[OK] interface:", interface_nc)
    print("[OK] exit_code:", proc.returncode)
    print("[OK] elapsed_seconds:", f"{elapsed:.6f}")
    print("[OK] metrics:", metrics_json)
    print("[OK] comparison:", comparison_json)
    print("[OK] report:", report_md)
    print("[OK] summary:", summary_md)


if __name__ == "__main__":
    main()
