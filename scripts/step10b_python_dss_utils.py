"""Utilities for a cautious Python port of Filipa's MATLAB+DSS layer.

This module ports the file-preparation and readback parts of runSimulations.m
closely enough to run controlled validation experiments. It intentionally does
not touch the existing HRes pipeline: callers load already-generated HRes
surface maps and use DSS.C.64.exe only for the geostatistical TEMPpred/STD
layer.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import netCDF4
import numpy as np


NULL_VALUE = -999.25


@dataclass
class DssConfig:
    repo_root: Path
    filipa_root: Path
    hres_output: Path
    dss_exe: Path
    output_dir: Path
    n_realizations: int = 100
    input_days: int = 14
    output_days: int = 2
    seed: int = 110011

    @property
    def hres_array_path(self) -> Path:
        return self.hres_output / "thetao_surface_370_hres.npy"

    @property
    def hres_dates_path(self) -> Path:
        return self.hres_output / "dates_370.csv"

    @property
    def lat_path(self) -> Path:
        return self.hres_output / "LAT_hres.npy"

    @property
    def lon_path(self) -> Path:
        return self.hres_output / "LON_hres.npy"

    @property
    def bathy_path(self) -> Path:
        return self.hres_output / "BATHY_hres.npy"

    @property
    def mask_path(self) -> Path:
        return self.hres_output / "MASK_hres.npy"


def read_dates_csv(path: Path) -> list[str]:
    import pandas as pd

    df = pd.read_csv(path)
    return [str(x)[:10] for x in df["date"].tolist()]


def target_to_pred_date(target_date: str) -> str:
    d = datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _seconds_since_epoch(date_str: str) -> int:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return int((d - datetime(1970, 1, 1)).total_seconds())


def load_hres_for_date(
    cfg: DssConfig,
    target_date: str,
    *,
    source: str = "python_370",
) -> dict[str, Any]:
    """Load the 14-day HRes window ending at target_date - 1 day.

    Returns arrays in MATLAB/DSS working orientation:
    TEMP_xy_t: [nx_lon, ny_lat, input_days]
    BATH_xy: [nx_lon, ny_lat]
    """
    pred_date = target_to_pred_date(target_date)
    if source == "official_october":
        ymd = pred_date.replace("-", "")
        path = cfg.filipa_root / "01.Data" / "October" / "HRes" / f"CMEMSnaza_{ymd}_HResNew.nc"
        if not path.exists():
            raise FileNotFoundError(f"Missing official HRes file for {pred_date}: {path}")
        with netCDF4.Dataset(path) as ds:
            temp = np.asarray(ds.variables["TEMP"][:], dtype=np.float64)
            # Python/netCDF reads this file as [TIME, DEPT, LAT, LON].
            if temp.ndim != 4:
                raise ValueError(f"Unexpected TEMP ndim in {path}: {temp.shape}")
            surface_t_lat_lon = temp[:, 0, :, :]
            lat = np.asarray(ds.variables["LAT"][:], dtype=np.float64)
            lon = np.asarray(ds.variables["LON"][:], dtype=np.float64)
            bathy_lat_lon = np.asarray(ds.variables["BATHY"][:], dtype=np.float64)
            time_seconds = np.asarray(ds.variables["TIME"][:], dtype=np.float64)
        if surface_t_lat_lon.shape[0] != cfg.input_days:
            raise ValueError(f"Expected {cfg.input_days} time slices, got {surface_t_lat_lon.shape}")
    elif source == "python_370":
        dates = read_dates_csv(cfg.hres_dates_path)
        pred_idx = dates.index(pred_date)
        start_idx = pred_idx - cfg.input_days + 1
        if start_idx < 0:
            raise ValueError(f"Not enough lookback days for {target_date}")
        cube = np.load(cfg.hres_array_path, mmap_mode="r")
        surface_t_lat_lon = np.asarray(cube[start_idx : pred_idx + 1], dtype=np.float64)
        lat = np.asarray(np.load(cfg.lat_path), dtype=np.float64)
        lon = np.asarray(np.load(cfg.lon_path), dtype=np.float64)
        bathy_lat_lon = np.asarray(np.load(cfg.bathy_path), dtype=np.float64)
        time_seconds = np.array([_seconds_since_epoch(d) for d in dates[start_idx : pred_idx + 1]], dtype=np.float64)
        path = cfg.hres_array_path
    else:
        raise ValueError(f"Unknown HRes source: {source}")

    # Convert [time, lat, lon] to MATLAB working [lon, lat, time].
    temp_xy_t = np.transpose(surface_t_lat_lon, (2, 1, 0))
    bathy_xy = bathy_lat_lon.T
    return {
        "source_path": str(path),
        "target_date": target_date,
        "pred_date": pred_date,
        "TEMP_xy_t": temp_xy_t,
        "LAT": lat,
        "LON": lon,
        "BATHY_xy": bathy_xy,
        "BATHY_lat_lon": bathy_lat_lon,
        "TIME": time_seconds,
    }


def save_gslib(values: np.ndarray, path: Path, header_name: str = "variable_from_python") -> None:
    arr = np.asarray(values)
    if arr.ndim == 1:
        arr2 = arr.reshape(-1, 1)
    else:
        arr2 = arr.reshape(arr.shape[0], -1)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"{header_name}\n")
        f.write(f"{arr2.shape[1]}\n")
        for i in range(arr2.shape[1]):
            f.write(f"Model{i + 1}\n")
        np.savetxt(f, arr2, fmt="%.6f", delimiter="\t")


def read_gslib(path: Path) -> tuple[list[str], np.ndarray]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        _title = f.readline()
        ncol = int(float(f.readline().strip()))
        header = [f.readline().strip() for _ in range(ncol)]
        data = np.loadtxt(f)
    if data.ndim == 1:
        data = data.reshape(-1, ncol)
    return header, data


def grid2gslib_matlab_order(grid: np.ndarray, path: Path) -> None:
    # MATLAB var_in(:) uses column-major order.
    flat = np.asarray(grid).reshape(-1, order="F")
    save_gslib(flat, path)


def gslib_to_grid_matlab_order(values: np.ndarray, nx: int, ny: int, nz: int) -> np.ndarray:
    return np.asarray(values).reshape((nx, ny, nz), order="F")


def write_gslib_input(input_path: Path, output_path: Path, temp_xy_t: np.ndarray, bathy_xy: np.ndarray) -> dict[str, Any]:
    input_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    nx, ny, input_days = temp_xy_t.shape
    nz = input_days + 2
    hard_rows: list[list[float]] = []
    for y in range(ny):
        for x in range(nx):
            for z in range(input_days):
                value = temp_xy_t[x, y, z]
                if np.isfinite(value):
                    hard_rows.append([x + 1, y + 1, z + 1, float(value)])
    hardata = np.asarray(hard_rows, dtype=np.float64)
    seconddata = hardata.copy()
    seconddata[:, 0] += 10000
    seconddata[:, 1] += 10000

    mask = np.zeros((nx, ny, nz), dtype=np.float64)
    invalid = ~np.isfinite(temp_xy_t[:, :, 0])
    for z in range(nz):
        mask[:, :, z][invalid] = -1
    grid2gslib_matlab_order(mask, input_path / "mask.out")
    grid2gslib_matlab_order(bathy_xy, output_path / "Bath.gslib")
    write_harddata(input_path / "temp.gslib", hardata)
    write_harddata(input_path / "auxi.gslib", seconddata)
    return {
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "input_days": input_days,
        "harddata_rows": int(hardata.shape[0]),
        "bounds": [float(np.nanmin(hardata[:, 3])), float(np.nanmax(hardata[:, 3]))],
    }


def write_harddata(path: Path, data: np.ndarray) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("seasurftemp\n")
        f.write("4\n")
        f.write("x\n")
        f.write("y\n")
        f.write("z\n")
        f.write("temp\n")
        np.savetxt(f, data, fmt="%.6f", delimiter="\t")


def _fmt_matrix_rows(rows: Iterable[str]) -> str:
    return "\n".join(rows) + "\n"


def build_dss_parameter_file(
    input_path: Path,
    output_file_prefix: Path,
    *,
    nx: int,
    ny: int,
    nz: int,
    bounds: tuple[float, float],
    n_realizations: int,
    variogram: tuple[float, float, float],
    seed: int,
) -> Path:
    """Write ssdir.par following parFileDSS.m for the simple GEOEAS case."""
    input_path.mkdir(parents=True, exist_ok=True)
    range_x, range_y, range_z = variogram
    par = input_path / "ssdir.par"
    temp_gslib = input_path / "temp.gslib"
    aux_gslib = input_path / "auxi.gslib"
    zone_file = input_path / "mask.out"
    bmin, bmax = bounds
    lines = [
        "#*************************************************************************************#",
        "#             PARALLEL DIRECT SEQUENCIAL SIMULATION PARAMETER FILE                    #",
        "#*************************************************************************************#",
        "",
        "[ZONES]",
        f"ZONESFILE = {zone_file}         # File with zones",
        "NZONES = 2    # Number of zones",
        "",
    ]
    for idx, datafile in enumerate([temp_gslib, aux_gslib], start=1):
        lines.extend(
            [
                f"[HARDDATA{idx}]",
                f"DATAFILE  ={datafile}   # Hard Data file",
                "COLUMNS   = 4",
                "XCOLUMN   = 1",
                "YCOLUMN   = 2",
                "ZCOLUMN   = 3",
                "VARCOLUMN = 4",
                "WTCOLUMN  = 0",
                f"MINVAL   = {bmin}",
                f"MAXVAL   = {bmax}",
                "USETRANS  = 1",
                "TRANSFILE = Cluster.trn",
                "",
            ]
        )
    lines.extend(
        [
            "[HARDDATA]",
            f"ZMIN     = {bmin}",
            f"ZMAX     = {bmax}",
            "LTAIL     = 1",
            f"LTPAR    = {bmin}",
            "UTAIL     = 1",
            f"UTPAR    = {bmax}",
            "",
            "[SIMULATION]",
            f"OUTFILE   = {output_file_prefix}",
            f"NSIMS     = {n_realizations}",
            "NTRY       = 20",
            "AVGCORR   = 0",
            "VARCORR   = 0",
            "",
            "[GRID]",
            f"NX        = {nx}",
            f"NY        = {ny}",
            f"NZ        = {nz}",
            "ORIGX     = 1",
            "ORIGY     = 1",
            "ORIGZ     = 1",
            "SIZEX     = 1",
            "SIZEY     = 1",
            "SIZEZ     = 1",
            "",
            "[GENERAL]",
            f"NULLVAL       = {NULL_VALUE}",
            f"SEED         = {int(seed)}",
            "USEHEADERS    = 1",
            "FILETYPE     = GEOEAS",
            "",
            "[SEARCH]",
            "NDMIN   = 8",
            "NDMAX   = 32",
            "NODMAX  = 12",
            "SSTRAT  = 1",
            "MULTS   = 0",
            "NMULTS  = 1",
            "NOCT    = 0",
            f"RADIUS1 = {range_x * 2}",
            f"RADIUS2 = {range_y * 2}",
            f"RADIUS3 = {range_z * 2}",
            "SANG1   = 0",
            "SANG2   = 0",
            "SANG3   = 0",
            "",
            "[KRIGING]",
            "KTYPE        = 0",
            "COLOCORR     = 0",
            "SOFTFILE     = no file",
            "LVMFILE      = no file",
            "NVARIL        = 1",
            "ICOLLVM       = 1",
            "CCFILE       = no file",
            "RESCALE      = 0",
            "",
        ]
    )
    for zone in [1, 2]:
        lines.extend(
            [
                f"[VARIOGRAMZ{zone}]",
                "NSTRUCT  = 1",
                "NUGGET    =0.1",
                f"[VARIOGRAMZ{zone}S1]",
                "TYPE =1",
                "COV  =0.9",
                "ANG1 =0",
                "ANG2 =0",
                "ANG3 =0",
                f"AA   ={range_x}",
                f"AA1  ={range_y}",
                f"AA2  ={range_z}",
                "",
            ]
        )
    for zone in [1, 2]:
        lines.extend(
            [
                f"[BIHIST{zone}]",
                "USEBIHIST        = 0 #Use Bihist? 1-yes 0-no",
                "BIHISTFILE       = no file",
                "NCLASSES         = 10",
                "AUXILIARYFILE    = no file",
                "",
            ]
        )
    lines.extend(
        [
            "[DEBUG]",
            "DBGLEVEL  = 1",
            "DBGFILE   = debug.dbg",
            "",
            "[COVTAB]",
            "MAXCTX = 200",
            "MAXCTY = 200",
            "MAXCTZ = 200",
            "",
            "[BLOCKS]",
            "USEBLOCKS  = 0",
            "BLOCKSFILE = no file",
            "MAXBLOCKS  = 100",
            "[PSEUDOHARD]",
            "USEPSEUDO  = 0",
            "PSEUDOFILE = no file",
            "PSEUDOCORR = 0",
        ]
    )
    par.write_text(_fmt_matrix_rows(lines), encoding="utf-8")
    return par


def run_dss_executable(dss_exe: Path, par_file: Path, *, timeout_s: int = 3600) -> dict[str, Any]:
    if not dss_exe.exists():
        raise FileNotFoundError(dss_exe)
    cmd = [str(dss_exe), str(par_file)]
    proc = subprocess.run(cmd, cwd=str(par_file.parent), capture_output=True, text=True, timeout=timeout_s)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "success": proc.returncode == 0,
    }


def read_dss_simulation_outputs(output_prefix: Path, n_realizations: int, expected_nodes: int) -> np.ndarray:
    sims = np.empty((expected_nodes, n_realizations), dtype=np.float64)
    for i in range(1, n_realizations + 1):
        path = output_prefix.parent / f"{output_prefix.name}_{i}.out"
        if not path.exists():
            raise FileNotFoundError(path)
        _, data = read_gslib(path)
        vals = data[:, 0] if data.ndim == 2 else data
        if vals.shape[0] != expected_nodes:
            raise ValueError(f"{path} nodes {vals.shape[0]} != expected {expected_nodes}")
        sims[:, i - 1] = vals
    sims[sims == NULL_VALUE] = np.nan
    return sims


def compute_temppred_uncertainty_from_realizations(
    sims: np.ndarray,
    *,
    nx: int,
    ny: int,
    input_days: int,
    output_days: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return TEMPpred, variance, and sqrt-variance arrays as [day, lat, lon].

    MATLAB readoutput_AUV names this field StDev, but computes var(...), not
    std(...). The validation script keeps both definitions so the official
    predModel can decide which one it matches better.
    """
    median = np.nanmedian(sims, axis=1)
    variance = np.nanvar(sims, axis=1, ddof=0)
    std = np.sqrt(variance)
    start = nx * ny * (input_days - 1)
    end = nx * ny * (input_days + 1)
    median_sel = median[start:end]
    var_sel = variance[start:end]
    std_sel = std[start:end]
    med_grid = gslib_to_grid_matlab_order(median_sel, nx, ny, output_days)
    var_grid = gslib_to_grid_matlab_order(var_sel, nx, ny, output_days)
    std_grid = gslib_to_grid_matlab_order(std_sel, nx, ny, output_days)
    # Convert [lon, lat, day] to [day, lat, lon].
    return (
        np.transpose(med_grid, (2, 1, 0)),
        np.transpose(var_grid, (2, 1, 0)),
        np.transpose(std_grid, (2, 1, 0)),
    )


def compute_temppred_std_from_realizations(
    sims: np.ndarray,
    *,
    nx: int,
    ny: int,
    input_days: int,
    output_days: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Backward-compatible wrapper returning TEMPpred and MATLAB-style variance."""
    temppred, variance, _std = compute_temppred_uncertainty_from_realizations(
        sims,
        nx=nx,
        ny=ny,
        input_days=input_days,
        output_days=output_days,
    )
    return temppred, variance


def write_predmodel_nc(
    path: Path,
    hres: dict[str, Any],
    temppred_day_lat_lon: np.ndarray,
    std_day_lat_lon: np.ndarray,
    *,
    std_sqrt_day_lat_lon: np.ndarray | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    temp_day_depth_lat_lon = np.asarray(hres["TEMP_xy_t"]).transpose(2, 1, 0)[:, None, :, :]
    lat = np.asarray(hres["LAT"], dtype=np.float64)
    lon = np.asarray(hres["LON"], dtype=np.float64)
    bathy_lat_lon = np.asarray(hres["BATHY_lat_lon"], dtype=np.float64)
    time = np.asarray(hres["TIME"], dtype=np.float64)
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.createDimension("TIME", temp_day_depth_lat_lon.shape[0])
        ds.createDimension("DEPT", 1)
        ds.createDimension("LAT", lat.shape[0])
        ds.createDimension("LON", lon.shape[0])
        ds.createDimension("day", temppred_day_lat_lon.shape[0])
        tv = ds.createVariable("TEMP", "f8", ("TIME", "DEPT", "LAT", "LON"))
        latv = ds.createVariable("LAT", "f8", ("LAT",))
        lonv = ds.createVariable("LON", "f8", ("LON",))
        bv = ds.createVariable("BATHY", "f8", ("LAT", "LON"))
        dv = ds.createVariable("DEPT", "f8", ("DEPT",))
        timev = ds.createVariable("TIME", "f8", ("TIME",))
        stdv = ds.createVariable("STD", "f8", ("day", "LAT", "LON"))
        predv = ds.createVariable("TEMPpred", "f8", ("day", "LAT", "LON"))
        if std_sqrt_day_lat_lon is not None:
            stdsqrtv = ds.createVariable("STD_sqrt_variance", "f8", ("day", "LAT", "LON"))
        tv[:] = temp_day_depth_lat_lon
        latv[:] = lat
        lonv[:] = lon
        bv[:] = bathy_lat_lon
        dv[:] = [0.4940253794193268]
        timev[:] = time
        stdv[:] = std_day_lat_lon
        predv[:] = temppred_day_lat_lon
        if std_sqrt_day_lat_lon is not None:
            stdsqrtv[:] = std_sqrt_day_lat_lon


def compare_with_reference_predmodel(candidate: Path, reference: Path) -> dict[str, Any]:
    def metrics(a: np.ndarray, b: np.ndarray) -> dict[str, float | int]:
        a = np.asarray(a, dtype=np.float64)
        b = np.asarray(b, dtype=np.float64)
        mask = np.isfinite(a) & np.isfinite(b)
        if mask.sum() == 0:
            return {"n": 0, "rmse": math.nan, "mae": math.nan, "pearson": math.nan}
        diff = a[mask] - b[mask]
        pearson = np.corrcoef(a[mask], b[mask])[0, 1] if mask.sum() > 2 and np.std(a[mask]) > 0 and np.std(b[mask]) > 0 else math.nan
        return {
            "n": int(mask.sum()),
            "rmse": float(np.sqrt(np.mean(diff * diff))),
            "mae": float(np.mean(np.abs(diff))),
            "pearson": float(pearson) if np.isfinite(pearson) else math.nan,
            "candidate_mean": float(np.nanmean(a)),
            "reference_mean": float(np.nanmean(b)),
            "candidate_std": float(np.nanstd(a)),
            "reference_std": float(np.nanstd(b)),
        }

    with netCDF4.Dataset(candidate) as c, netCDF4.Dataset(reference) as r:
        out = {
            "candidate": str(candidate),
            "reference": str(reference),
            "candidate_exists": candidate.exists(),
            "reference_exists": reference.exists(),
            "TEMPpred_shape_candidate": list(c.variables["TEMPpred"].shape),
            "TEMPpred_shape_reference": list(r.variables["TEMPpred"].shape),
            "STD_shape_candidate": list(c.variables["STD"].shape),
            "STD_shape_reference": list(r.variables["STD"].shape),
        }
        out.update({f"TEMPpred_{k}": v for k, v in metrics(c.variables["TEMPpred"][:], r.variables["TEMPpred"][:]).items()})
        out.update({f"STD_{k}": v for k, v in metrics(c.variables["STD"][:], r.variables["STD"][:]).items()})
    return out


def find_dss_exe(filipa_root: Path) -> Path:
    matches = list(filipa_root.rglob("DSS.C.64.exe"))
    if not matches:
        raise FileNotFoundError(f"DSS.C.64.exe not found under {filipa_root}")
    return matches[0]


def copy_dss_exe_to_input(dss_exe: Path, input_path: Path) -> Path:
    input_path.mkdir(parents=True, exist_ok=True)
    target = input_path / "DSS.C.64.exe"
    if dss_exe.resolve() != target.resolve():
        shutil.copy2(dss_exe, target)
    return target
