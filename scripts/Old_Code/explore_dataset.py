"""End-to-end explorer for FRESNEL / Nazare C4-D4 dataset."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from io_auv import summarize_auv_files
from io_gslib import parse_gslib_header, summarize_gslib_files
from io_netcdf import summarize_netcdf_files
from io_simout import sim_out_markdown, summarize_sim_out_files
from utils import file_extension, guess_date, guess_test_id, guess_type, setup_logging, to_rel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explore and document the Nazare C4/D4 dataset.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Project root")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Data directory relative to root")
    parser.add_argument("--results-dir", type=Path, default=Path("results"), help="Results directory relative to root")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"), help="Docs directory relative to root")
    parser.add_argument("--max-tree-depth", type=int, default=5, help="Max depth for tree output")
    parser.add_argument("--gslib-sample-rows", type=int, default=100, help="Sample rows per GSLIB")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    return parser.parse_args()


def list_files(root: Path, include_root: Path) -> List[Path]:
    files = []
    for p in include_root.rglob("*"):
        if p.is_file():
            files.append(p)
    return sorted(files)


def inventory_notes(path: Path) -> Optional[str]:
    s = str(path).replace("\\", "/")
    notes: List[str] = []
    if "Priori_Nazare_" in s:
        notes.append("prior_model_artifact")
    if re.search(r"/Nazare_\d{2}-\d{2}-\d{4}_", s):
        notes.append("post_assimilation_artifact")
    if "AUVpredModel" in s:
        notes.append("assimilated_netcdf")
    if "predModel" in s and "AUVpredModel" not in s:
        notes.append("prior_or_background_netcdf")
    if "/HResNew/" in s:
        notes.append("interpolated_cmems")
    if re.search(r"/202410(29|30)/", s):
        notes.append("original_cmems_download_day")
    if "/AUVdata/" in s:
        notes.append("auv_observations")
    if path.name.lower().startswith("sim_") and path.suffix.lower() == ".out":
        notes.append("simulation_realization")
    return ";".join(notes) if notes else None


def build_inventory(files: Sequence[Path], root: Path) -> pd.DataFrame:
    rows = []
    for p in files:
        rel = to_rel(p, root)
        rows.append(
            {
                "path": rel,
                "size_bytes": int(p.stat().st_size),
                "ext": file_extension(p),
                "guessed_type": guess_type(p),
                "test_id_if_any": guess_test_id(rel) or "None",
                "date_if_any": guess_date(rel),
                "notes": inventory_notes(p),
            }
        )
    return pd.DataFrame(rows)


def tree_lines(base: Path, root: Path, max_depth: int = 5, max_entries_per_dir: int = 120) -> List[str]:
    lines = [f"{to_rel(base, root)}/"]

    def _walk(path: Path, prefix: str, depth: int) -> None:
        if depth >= max_depth:
            return
        children = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        display = children[:max_entries_per_dir]
        for idx, child in enumerate(display):
            is_last = idx == len(display) - 1
            branch = "└── " if is_last else "├── "
            label = child.name + ("/" if child.is_dir() else "")
            lines.append(f"{prefix}{branch}{label}")
            if child.is_dir():
                ext = "    " if is_last else "│   "
                _walk(child, prefix + ext, depth + 1)
        if len(children) > max_entries_per_dir:
            hidden = len(children) - max_entries_per_dir
            lines.append(f"{prefix}└── ... ({hidden} entries truncated)")

    _walk(base, "", 0)
    return lines


def count_by_folder(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["folder", "n_files", "total_bytes"])
    tmp = df.copy()
    tmp["folder"] = tmp["path"].str.rsplit("/", n=1).str[0]
    return (
        tmp.groupby("folder", as_index=False)
        .agg(n_files=("path", "count"), total_bytes=("size_bytes", "sum"))
        .sort_values(["n_files", "total_bytes"], ascending=[False, False])
    )


def _choose_coord(ds: xr.Dataset, names: Iterable[str]) -> Optional[str]:
    cmap = {c.lower(): c for c in ds.coords}
    for n in names:
        if n.lower() in cmap:
            return cmap[n.lower()]
    return None


def _coord_info(ds: xr.Dataset, coord_name: Optional[str]) -> Dict[str, Optional[float]]:
    out = {"name": coord_name, "min": None, "max": None, "res": None, "n": None}
    if not coord_name:
        return out
    try:
        arr = np.asarray(ds[coord_name].values, dtype=float).ravel()
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return out
        out["min"] = float(np.nanmin(arr))
        out["max"] = float(np.nanmax(arr))
        out["n"] = int(arr.size)
        uniq = np.unique(arr)
        if uniq.size > 1:
            diffs = np.diff(uniq)
            diffs = diffs[np.isfinite(diffs) & (diffs != 0)]
            if diffs.size:
                out["res"] = float(np.nanmedian(diffs))
    except Exception:
        return out
    return out


def nc_grid_info(path: Path, root: Path) -> Dict:
    rel = to_rel(path, root)
    out = {"path": rel, "open_ok": False, "error": None}
    try:
        ds = xr.open_dataset(path, decode_times=False, engine="netcdf4")
    except Exception as exc:
        out["error"] = str(exc)
        return out
    lat = _choose_coord(ds, ["LAT", "lat", "latitude"])
    lon = _choose_coord(ds, ["LON", "lon", "longitude"])
    depth = _choose_coord(ds, ["DEPT", "depth", "deph", "z"])
    time = _choose_coord(ds, ["TIME", "time", "t"])
    out.update(
        {
            "open_ok": True,
            "dims": dict(ds.sizes),
            "lat": _coord_info(ds, lat),
            "lon": _coord_info(ds, lon),
            "depth": _coord_info(ds, depth),
            "time": _coord_info(ds, time),
            "crs": str(ds.attrs.get("crs") or ds.attrs.get("grid_mapping")) if (ds.attrs.get("crs") or ds.attrs.get("grid_mapping")) else None,
            "data_vars": list(ds.data_vars),
            "coords": list(ds.coords),
        }
    )
    ds.close()
    return out


def gslib_grid_info(path: Path, root: Path) -> Dict:
    rel = to_rel(path, root)
    out = {"path": rel, "open_ok": False, "error": None}
    header = parse_gslib_header(path)
    if not header["header_ok"]:
        out["error"] = header["notes"]
        return out
    cols = header["columns"]
    if not all(c in cols for c in ["x", "y"]):
        out["error"] = "missing_x_or_y_columns"
        return out
    try:
        df = pd.read_csv(
            path,
            sep=r"\s+",
            names=cols,
            header=None,
            skiprows=header["data_start_line"],
            engine="python",
            encoding="utf-8",
        )
    except Exception as exc:
        out["error"] = str(exc)
        return out

    out["open_ok"] = True
    out["n_rows"] = int(len(df))
    for c in ["x", "y", "z"]:
        if c in df.columns:
            v = pd.to_numeric(df[c], errors="coerce").dropna()
            if v.empty:
                continue
            uniq = np.unique(v.values)
            res = None
            if len(uniq) > 1:
                diffs = np.diff(uniq)
                diffs = diffs[np.isfinite(diffs) & (diffs != 0)]
                if len(diffs) > 0:
                    res = float(np.nanmedian(diffs))
            out[c] = {
                "min": float(v.min()),
                "max": float(v.max()),
                "n_unique": int(len(uniq)),
                "res": res,
            }
    return out


def _dim_index(da: xr.DataArray, dim_candidates: Sequence[str]) -> Optional[Tuple[str, int]]:
    for candidate in dim_candidates:
        for dim in da.dims:
            if dim.lower() == candidate.lower():
                return dim, 0
    return None


def pick_2d_slice(da: xr.DataArray) -> xr.DataArray:
    work = da
    for candidates in (["time", "TIME", "t"], ["depth", "DEPT", "deph", "z"]):
        found = _dim_index(work, candidates)
        if found:
            work = work.isel({found[0]: found[1]})

    while len(work.dims) > 2:
        work = work.isel({work.dims[0]: 0})
    return work


def plot_field(path: Path, var_name: str, out_png: Path, title: str, logger) -> bool:
    try:
        ds = xr.open_dataset(path, decode_times=False, engine="netcdf4")
    except Exception as exc:
        logger.warning("Plot skip %s (%s)", path, exc)
        return False
    if var_name not in ds:
        ds.close()
        return False

    da = pick_2d_slice(ds[var_name])
    try:
        arr = np.asarray(da.values, dtype=float)
    except Exception:
        ds.close()
        return False

    plt.figure(figsize=(8, 4.5))
    if arr.ndim == 2:
        if {"LAT", "LON"}.issubset(ds.coords):
            lat = np.asarray(ds["LAT"].values, dtype=float)
            lon = np.asarray(ds["LON"].values, dtype=float)
            extent = [float(np.nanmin(lon)), float(np.nanmax(lon)), float(np.nanmin(lat)), float(np.nanmax(lat))]
            plt.imshow(arr, origin="lower", aspect="auto", extent=extent)
            plt.xlabel("Longitude")
            plt.ylabel("Latitude")
        else:
            plt.imshow(arr, origin="lower", aspect="auto")
            if len(da.dims) >= 2:
                plt.xlabel(da.dims[-1])
                plt.ylabel(da.dims[-2])
        plt.colorbar(label=var_name)
        plt.title(title)
        plt.tight_layout()
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png, dpi=150)
        plt.close()
        ds.close()
        return True

    plt.close()
    ds.close()
    return False


def first_existing_var(path: Path, candidates: Sequence[str]) -> Optional[str]:
    try:
        ds = xr.open_dataset(path, decode_times=False, engine="netcdf4")
    except Exception:
        return None
    existing = list(ds.data_vars)
    ds.close()
    for c in candidates:
        if c in existing:
            return c
    return None


def create_file_map_doc(docs_path: Path, inventory_df: pd.DataFrame) -> None:
    folder_counts = count_by_folder(inventory_df)
    top_folders = folder_counts[folder_counts["folder"].str.count("/") <= 2].head(25)
    glossary = [
        ("Variograma", "Funcao que descreve a continuidade espacial em funcao da distancia."),
        ("Sill", "Patamar do variograma associado a variancia total."),
        ("Range", "Distancia a partir da qual a correlacao espacial e fraca."),
        ("Nugget", "Componente de variancia a distancia zero (ruido/microescala)."),
        ("Realizacao", "Uma simulacao possivel do campo aleatorio condicionado."),
        ("Ensemble", "Conjunto de realizacoes para quantificar incerteza."),
        ("Assimilacao", "Atualizacao do estado do modelo com observacoes."),
        ("A priori", "Estimativa antes de incorporar observacoes AUV."),
        ("A posteriori", "Estimativa apos incorporar observacoes AUV."),
        ("Kriging", "Estimador linear que minimiza variancia do erro."),
        ("Simulacao sequencial", "Geracao de realizacoes preservando estatisticas locais."),
        ("Grade", "Malha espacial onde variaveis sao representadas."),
        ("Bounding box", "Extremos min/max de latitude e longitude."),
        ("Resolucao", "Espacamento entre pontos de grade."),
        ("Pointwise std", "Desvio padrao por celula da grade."),
        ("Mediana", "Estatistica robusta do ensemble por celula."),
        ("Bathymetry/BATHY", "Profundidade do fundo oceânico."),
        ("TEMP", "Temperatura da agua do mar."),
        ("PSAL", "Salinidade pratica."),
        ("DEPT/Depth", "Nivel de profundidade vertical."),
        ("TIME", "Dimensao temporal do produto/modelo."),
        ("CMEMS", "Servico Copernicus de dados marinhos."),
        ("HRes", "Grade de maior resolucao para simulacao local."),
        ("Mask", "Indicador de celulas ativas/inativas."),
        ("IQD", "Produto derivado usado no pos-processamento geoestatistico."),
        ("scene_*.gslib", "Cenas/quadros usados para visualizacao ou etapas internas."),
        ("sim_*.out", "Realizacoes individuais da simulacao."),
        ("TEMPpred", "Campo de temperatura previsto no NetCDF de simulacao."),
        ("STD", "Incerteza (desvio padrao) por celula."),
        ("AUV track", "Trajetoria georreferenciada do veiculo."),
    ]

    lines: List[str] = []
    lines.append("# FILE MAP - FRESNEL / Nazare (C4 e D4)")
    lines.append("")
    lines.append("## Pipeline (alto nivel)")
    lines.append("")
    lines.append("```text")
    lines.append("CMEMS original (20241029/20241030) -> HResNew (interpolado)")
    lines.append("                                    -> Priori_Nazare_* (modelo a priori)")
    lines.append("AUVdata (observacoes) -------------/ ")
    lines.append("                                    -> Nazare_* (apos assimilacao)")
    lines.append("                                    -> sim_*.out (realizacoes)")
    lines.append("                                    -> GSLIB derivados (Median, StDev, IQD, scene_*)")
    lines.append("                                    -> NetCDF predModel/AUVpredModel")
    lines.append("```")
    lines.append("")
    lines.append("## Pastas e papeis")
    lines.append("")
    lines.append("| Pasta | Papel esperado |")
    lines.append("|---|---|")
    lines.append("| `data/20241029`, `data/20241030` | CMEMS original (grade maior, produto de download). |")
    lines.append("| `data/HResNew` | CMEMS interpolado para a grade de simulacao local. |")
    lines.append("| `data/TEST_C4`, `data/TEST_D4` | Estrutura dos testes, com pastas `Priori_Nazare_*` e `Nazare_*`. |")
    lines.append("| `Nazare_*` | Resultado pos-assimilacao com observacoes AUV. |")
    lines.append("| `Priori_Nazare_*` | Estado a priori / fundo antes de assimilacao. |")
    lines.append("| `sim_*.out` | Realizacoes individuais (ASCII estilo GSLIB simplificado). |")
    lines.append("| `*.gslib` | Grades e produtos derivados (temp, median, std, bathy, mask, scene). |")
    lines.append("| `*_predModel_*.nc` | Versao NetCDF do modelo de previsao/background. |")
    lines.append("| `*_AUVpredModel_*.nc` | Versao NetCDF apos assimilacao com AUV. |")
    lines.append("")
    lines.append("## Convencoes de nomes")
    lines.append("")
    lines.append("- `Nazare_DD-MM-YYYY_k`: caso/realizacao pos-assimilacao `k`.")
    lines.append("- `Priori_Nazare_DD-MM-YYYY_k`: caso/realizacao a priori `k`.")
    lines.append("- `sim_n.out`: realizacao `n` da simulacao.")
    lines.append("- `DD-MM-YYYY_predModel_k.nc`: NetCDF de previsao/base.")
    lines.append("- `DD-MM-YYYY_AUVpredModel_k.nc`: NetCDF atualizado por assimilacao AUV.")
    lines.append("")
    lines.append("## Tabela rapida por pasta (contagens)")
    lines.append("")
    lines.append("| Pasta | n_files | total_bytes |")
    lines.append("|---|---:|---:|")
    for _, row in top_folders.iterrows():
        lines.append(f"| `{row['folder']}` | {int(row['n_files'])} | {int(row['total_bytes'])} |")
    lines.append("")
    lines.append("## Glossario")
    lines.append("")
    for term, definition in glossary:
        lines.append(f"- **{term}**: {definition}")
    lines.append("")

    docs_path.write_text("\n".join(lines), encoding="utf-8")


def create_grid_doc(docs_path: Path, comparison: Dict) -> None:
    lines: List[str] = []
    lines.append("# GRID AND COORDS")
    lines.append("")
    lines.append("## Resumo")
    lines.append("")

    for key in ["cmems_original", "hresnew", "pred_model", "auv_pred_model", "sim_gslib"]:
        item = comparison.get(key)
        if not item:
            continue
        lines.append(f"### {key}")
        lines.append(f"- path: `{item.get('path')}`")
        lines.append(f"- open_ok: `{item.get('open_ok')}`")
        if item.get("error"):
            lines.append(f"- error: `{item.get('error')}`")
            continue
        if "dims" in item:
            lines.append(f"- dims: `{json.dumps(item.get('dims'))}`")
        for coord_key in ["lat", "lon", "depth", "time", "x", "y", "z"]:
            if coord_key in item and item[coord_key]:
                lines.append(f"- {coord_key}: `{json.dumps(item[coord_key])}`")
        lines.append(f"- crs: `{item.get('crs')}`")
        lines.append("")

    lines.append("## Diferencas observadas")
    lines.append("")
    for diff in comparison.get("differences", []):
        lines.append(f"- {diff}")
    lines.append("")

    docs_path.write_text("\n".join(lines), encoding="utf-8")


def create_dataset_guide(
    path: Path,
    results_dir: Path,
    docs_dir: Path,
    generated_files: Sequence[Path],
) -> None:
    files_rel = [str(p).replace("\\", "/") for p in generated_files]
    lines: List[str] = []
    lines.append("# DATASET GUIDE - FRESNEL / Nazare C4-D4")
    lines.append("")
    lines.append("## Visao geral")
    lines.append("")
    lines.append(
        "Este dataset combina campos CMEMS, interpolacao para grade de alta resolucao, "
        "modelos geoestatisticos a priori, assimilacao com observacoes AUV e produtos derivados "
        "em GSLIB/NetCDF para os testes C4 e D4."
    )
    lines.append("")
    lines.append("## Como comecar")
    lines.append("")
    lines.append("```bash")
    lines.append("python scripts/explore_dataset.py")
    lines.append("```")
    lines.append("")
    lines.append("Se tiveres um ambiente virtual com dependencias:")
    lines.append("```bash")
    lines.append("C:/.../.venv/Scripts/python.exe scripts/explore_dataset.py")
    lines.append("```")
    lines.append("")
    lines.append("## Onde esta o que")
    lines.append("")
    lines.append("- `data/20241029`, `data/20241030`: CMEMS original.")
    lines.append("- `data/HResNew`: CMEMS interpolado para grade local.")
    lines.append("- `data/TEST_C4`, `data/TEST_D4`: casos de teste com `Priori_` e `Nazare_`.")
    lines.append("- `data/AUVdata`: observacoes dos AUV.")
    lines.append("")
    lines.append("## Data dictionary gerado")
    lines.append("")
    lines.append(f"- `{results_dir.as_posix()}/dataset_inventory.csv`")
    lines.append(f"- `{results_dir.as_posix()}/netcdf_summary.csv`")
    lines.append(f"- `{results_dir.as_posix()}/netcdf_files_summary.csv`")
    lines.append(f"- `{results_dir.as_posix()}/gslib_schema.csv`")
    lines.append(f"- `{results_dir.as_posix()}/gslib_samples.csv`")
    lines.append(f"- `{results_dir.as_posix()}/sim_out_schema.csv`")
    lines.append(f"- `{results_dir.as_posix()}/auv_schema.csv`")
    lines.append(f"- `{results_dir.as_posix()}/auv_quickstats.csv`")
    lines.append("")
    lines.append("## Exemplos minimos em Python")
    lines.append("")
    lines.append("```python")
    lines.append("import xarray as xr")
    lines.append("import pandas as pd")
    lines.append("")
    lines.append("ds = xr.open_dataset('data/HResNew/CMEMSnaza_20241030_HResNew.nc')")
    lines.append("print(ds.data_vars)")
    lines.append("")
    lines.append("g = pd.read_csv('results/gslib_samples.csv').query(\"path.str.contains('temp.gslib')\", engine='python')")
    lines.append("print(g.head())")
    lines.append("")
    lines.append("auv = xr.open_dataset('data/AUVdata/lauv-xplore-2_2024_10_29.nc')")
    lines.append("print(auv[['TIME','LATITUDE','LONGITUDE','DEPH','TEMP']])")
    lines.append("")
    lines.append("# cruzamento simples AUV com grid: comparar bbox")
    lines.append("print(float(auv.LATITUDE.min()), float(auv.LATITUDE.max()))")
    lines.append("print(float(ds.LAT.min()), float(ds.LAT.max()))")
    lines.append("```")
    lines.append("")
    lines.append("## Artefactos adicionais")
    lines.append("")
    for f in sorted(files_rel):
        lines.append(f"- `{f}`")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    data_dir = (root / args.data_dir).resolve()
    results_dir = (root / args.results_dir).resolve()
    docs_dir = (root / args.docs_dir).resolve()
    plots_dir = results_dir / "plots"

    logger = setup_logging(args.log_level)
    logger.info("Root: %s", root)
    logger.info("Data dir: %s", data_dir)

    results_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 1) INVENTARIO
    all_files = list_files(root, data_dir)
    inventory_df = build_inventory(all_files, root)
    inventory_csv = results_dir / "dataset_inventory.csv"
    inventory_df.to_csv(inventory_csv, index=False)

    ext_counts = (
        inventory_df.groupby("ext", as_index=False)
        .agg(n_files=("path", "count"), total_bytes=("size_bytes", "sum"))
        .sort_values(["n_files", "total_bytes"], ascending=[False, False])
    )
    ext_counts_csv = results_dir / "file_count_by_extension.csv"
    ext_counts.to_csv(ext_counts_csv, index=False)

    folder_counts = count_by_folder(inventory_df)
    folder_counts_csv = results_dir / "file_count_by_folder.csv"
    folder_counts.to_csv(folder_counts_csv, index=False)

    tree_txt = results_dir / "tree_depth5.txt"
    tree_txt.write_text("\n".join(tree_lines(data_dir, root, max_depth=args.max_tree_depth)), encoding="utf-8")

    # 2.1) NetCDF
    nc_files = [p for p in all_files if p.suffix.lower() == ".nc"]
    nc_var_df, nc_file_df = summarize_netcdf_files(nc_files, root, logger)
    nc_var_csv = results_dir / "netcdf_summary.csv"
    nc_file_csv = results_dir / "netcdf_files_summary.csv"
    nc_var_df.to_csv(nc_var_csv, index=False)
    nc_file_df.to_csv(nc_file_csv, index=False)

    # 2.2) GSLIB
    gslib_files = [p for p in all_files if p.suffix.lower() == ".gslib"]
    gslib_schema_df, gslib_samples_df = summarize_gslib_files(
        gslib_files, root, logger, sample_rows=args.gslib_sample_rows
    )
    gslib_schema_csv = results_dir / "gslib_schema.csv"
    gslib_samples_csv = results_dir / "gslib_samples.csv"
    gslib_schema_df.to_csv(gslib_schema_csv, index=False)
    gslib_samples_df.to_csv(gslib_samples_csv, index=False)

    # 2.3) sim_X.out
    sim_files = [p for p in all_files if p.name.lower().startswith("sim_") and p.suffix.lower() == ".out"]
    sim_schema_df = summarize_sim_out_files(sim_files, root, n_inspect=5)
    sim_schema_csv = results_dir / "sim_out_schema.csv"
    sim_schema_df.to_csv(sim_schema_csv, index=False)
    sim_doc = docs_dir / "FORMATS_sim_out.md"
    sim_doc.write_text(sim_out_markdown(sim_schema_df), encoding="utf-8")

    # 2.4) AUV
    auv_files = sorted((data_dir / "AUVdata").glob("*")) if (data_dir / "AUVdata").exists() else []
    auv_schema_df, auv_quick_df = summarize_auv_files(auv_files, root, logger)
    auv_schema_csv = results_dir / "auv_schema.csv"
    auv_quick_csv = results_dir / "auv_quickstats.csv"
    auv_schema_df.to_csv(auv_schema_csv, index=False)
    auv_quick_df.to_csv(auv_quick_csv, index=False)

    # 3) FILE MAP
    file_map_md = docs_dir / "FILE_MAP.md"
    create_file_map_doc(file_map_md, inventory_df)

    # 4) Grid consistency checks
    original_nc = next((p for p in nc_files if "/20241030/" in to_rel(p, root)), None) or next(
        (p for p in nc_files if "/20241029/" in to_rel(p, root)),
        None,
    )
    hres_nc = next((p for p in nc_files if "/HResNew/" in to_rel(p, root)), None)
    pred_nc = next((p for p in nc_files if re.search(r"_predModel_\d+\.nc$", p.name) and "AUVpredModel" not in p.name), None)
    auv_pred_nc = next((p for p in nc_files if "AUVpredModel" in p.name), None)
    sim_gslib = next((p for p in gslib_files if p.name.lower() == "auxi.gslib" and "Nazare_" in str(p)), None)

    grid_comparison: Dict[str, Dict] = {}
    if original_nc:
        grid_comparison["cmems_original"] = nc_grid_info(original_nc, root)
    if hres_nc:
        grid_comparison["hresnew"] = nc_grid_info(hres_nc, root)
    if pred_nc:
        grid_comparison["pred_model"] = nc_grid_info(pred_nc, root)
    if auv_pred_nc:
        grid_comparison["auv_pred_model"] = nc_grid_info(auv_pred_nc, root)
    if sim_gslib:
        grid_comparison["sim_gslib"] = gslib_grid_info(sim_gslib, root)

    diffs: List[str] = []
    if "cmems_original" in grid_comparison and "hresnew" in grid_comparison:
        oc = grid_comparison["cmems_original"]
        hr = grid_comparison["hresnew"]
        if oc.get("lat", {}).get("res") and hr.get("lat", {}).get("res"):
            ratio = oc["lat"]["res"] / hr["lat"]["res"] if hr["lat"]["res"] else math.nan
            diffs.append(f"Resolucao lat: CMEMS original ~{oc['lat']['res']:.6f} vs HResNew ~{hr['lat']['res']:.6f} (ratio {ratio:.2f}x).")
        if oc.get("lon", {}).get("res") and hr.get("lon", {}).get("res"):
            ratio = oc["lon"]["res"] / hr["lon"]["res"] if hr["lon"]["res"] else math.nan
            diffs.append(f"Resolucao lon: CMEMS original ~{oc['lon']['res']:.6f} vs HResNew ~{hr['lon']['res']:.6f} (ratio {ratio:.2f}x).")
        diffs.append(
            "Bounding box HResNew e subdominio do CMEMS original."
            if (
                hr.get("lat", {}).get("min") is not None
                and oc.get("lat", {}).get("min") is not None
                and hr["lat"]["min"] >= oc["lat"]["min"]
                and hr["lat"]["max"] <= oc["lat"]["max"]
                and hr["lon"]["min"] >= oc["lon"]["min"]
                and hr["lon"]["max"] <= oc["lon"]["max"]
            )
            else "Bounding boxes nao parecem em relacao simples de subdominio."
        )
    if "pred_model" in grid_comparison and "hresnew" in grid_comparison:
        pr = grid_comparison["pred_model"]
        hr = grid_comparison["hresnew"]
        same_dims = pr.get("dims") == hr.get("dims")
        diffs.append(f"predModel vs HResNew dims iguais: {same_dims}.")
    if "sim_gslib" in grid_comparison:
        sg = grid_comparison["sim_gslib"]
        if sg.get("open_ok"):
            x = sg.get("x", {})
            y = sg.get("y", {})
            if (
                x.get("res") == 1.0
                and y.get("res") == 1.0
                and x.get("max") is not None
                and y.get("max") is not None
                and (x["max"] > 500 or y["max"] > 500)
            ):
                diffs.append("GSLIB usa coordenadas de grade/index (passo 1), nao lat/lon em graus.")
    crs_flags = []
    for k, v in grid_comparison.items():
        if isinstance(v, dict) and "crs" in v:
            crs_flags.append(f"{k}: {v.get('crs')}")
    if crs_flags:
        diffs.append("CRS explicito nos NetCDF: " + "; ".join(crs_flags))
    grid_comparison["differences"] = diffs

    grid_json = results_dir / "grid_comparison.json"
    grid_json.write_text(json.dumps(grid_comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    grid_md = docs_dir / "GRID_AND_COORDS.md"
    create_grid_doc(grid_md, grid_comparison)

    # 5) Quick plots
    generated_plots: List[Path] = []
    if hres_nc:
        out = plots_dir / "hres_temp_surface.png"
        if plot_field(hres_nc, "TEMP", out, "HResNew TEMP (surface/first depth)", logger):
            generated_plots.append(out)
    if pred_nc:
        prior_var = first_existing_var(pred_nc, ["TEMPpred", "TEMP"])
        out_mean = plots_dir / "prior_predmodel_temp_surface.png"
        if prior_var and plot_field(pred_nc, prior_var, out_mean, "Prior predModel TEMP/TEMPpred", logger):
            generated_plots.append(out_mean)
        out_std = plots_dir / "prior_predmodel_std_surface.png"
        if plot_field(pred_nc, "STD", out_std, "Prior predModel STD", logger):
            generated_plots.append(out_std)
    if auv_pred_nc:
        post_var = first_existing_var(auv_pred_nc, ["TEMPpred", "TEMP"])
        out_mean = plots_dir / "post_auvpredmodel_temp_surface.png"
        if post_var and plot_field(auv_pred_nc, post_var, out_mean, "Post AUVpredModel TEMP/TEMPpred", logger):
            generated_plots.append(out_mean)
        out_std = plots_dir / "post_auvpredmodel_std_surface.png"
        if plot_field(auv_pred_nc, "STD", out_std, "Post AUVpredModel STD", logger):
            generated_plots.append(out_std)

    if auv_files:
        auv_path = auv_files[0]
        try:
            ds = xr.open_dataset(auv_path, decode_times=False, engine="netcdf4")
            if "LATITUDE" in ds and "LONGITUDE" in ds:
                lat = np.asarray(ds["LATITUDE"].values, dtype=float)
                lon = np.asarray(ds["LONGITUDE"].values, dtype=float)
                step = max(1, len(lat) // 6000)
                plt.figure(figsize=(6.5, 6.0))
                plt.plot(lon[::step], lat[::step], linewidth=0.8)
                plt.xlabel("Longitude")
                plt.ylabel("Latitude")
                plt.title(f"AUV track - {auv_path.name}")
                plt.grid(alpha=0.2)
                plt.tight_layout()
                out_track = plots_dir / "auv_track_day1.png"
                plt.savefig(out_track, dpi=150)
                plt.close()
                generated_plots.append(out_track)
            if "TEMP" in ds and "DEPH" in ds:
                temp = np.asarray(ds["TEMP"].values, dtype=float)
                depth = np.asarray(ds["DEPH"].values, dtype=float)
                step = max(1, len(temp) // 6000)
                plt.figure(figsize=(5.8, 6.0))
                plt.scatter(temp[::step], depth[::step], s=4, alpha=0.6)
                plt.gca().invert_yaxis()
                plt.xlabel("Temperature (deg C)")
                plt.ylabel("Depth (m)")
                plt.title(f"AUV profile - {auv_path.name}")
                plt.grid(alpha=0.2)
                plt.tight_layout()
                out_profile = plots_dir / "auv_temp_vs_depth_day1.png"
                plt.savefig(out_profile, dpi=150)
                plt.close()
                generated_plots.append(out_profile)
            ds.close()
        except Exception as exc:
            logger.warning("AUV plots skipped: %s", exc)

    # 6) Dataset guide
    generated_core_files: List[Path] = [
        inventory_csv,
        ext_counts_csv,
        folder_counts_csv,
        tree_txt,
        nc_var_csv,
        nc_file_csv,
        gslib_schema_csv,
        gslib_samples_csv,
        sim_schema_csv,
        auv_schema_csv,
        auv_quick_csv,
        grid_json,
    ] + generated_plots + [sim_doc, file_map_md, grid_md]

    guide_md = docs_dir / "DATASET_GUIDE.md"
    create_dataset_guide(guide_md, results_dir.relative_to(root), docs_dir.relative_to(root), [p.relative_to(root) for p in generated_core_files + [guide_md]])

    logger.info("Exploration complete. Generated %d artifacts.", len(generated_core_files) + 1)


if __name__ == "__main__":
    main()
