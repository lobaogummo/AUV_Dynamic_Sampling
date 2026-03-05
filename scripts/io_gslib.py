"""GSLIB readers and schema extraction helpers."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from utils import to_rel


COORD_KEYWORDS = {"x", "y", "z", "lat", "latitude", "lon", "long", "longitude", "depth", "deph"}
VALUE_KEYWORDS = {"temp", "temperature", "std", "stdev", "median", "mean", "bathy", "mask", "iqd"}


def parse_gslib_header(path: Path) -> Dict:
    result = {
        "title": None,
        "n_columns": None,
        "columns": [],
        "data_start_line": None,
        "header_ok": False,
        "notes": None,
    }
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            title = f.readline().strip()
            ncols_line = f.readline().strip()
            if not title:
                result["notes"] = "empty_title_line"
                return result
            result["title"] = title
            try:
                ncols = int(ncols_line.split()[0])
            except Exception:
                result["notes"] = f"invalid_n_columns_line: {ncols_line}"
                return result
            if ncols < 1:
                result["notes"] = f"invalid_n_columns_value: {ncols}"
                return result
            cols: List[str] = []
            for _ in range(ncols):
                c = f.readline()
                if not c:
                    result["notes"] = "unexpected_eof_while_reading_columns"
                    return result
                cols.append(c.strip() or f"col_{len(cols)+1}")
            result["n_columns"] = ncols
            result["columns"] = cols
            result["data_start_line"] = 2 + ncols
            result["header_ok"] = True
            return result
    except Exception as exc:
        result["notes"] = f"header_read_error: {exc}"
        return result


def _classify_columns(columns: List[str]) -> Tuple[List[str], List[str], List[str]]:
    coord_cols: List[str] = []
    value_cols: List[str] = []
    unknown_cols: List[str] = []
    for c in columns:
        lc = c.lower()
        if any(k in lc for k in COORD_KEYWORDS):
            coord_cols.append(c)
        elif any(k in lc for k in VALUE_KEYWORDS):
            value_cols.append(c)
        else:
            unknown_cols.append(c)
    return coord_cols, value_cols, unknown_cols


def sample_gslib_rows(path: Path, n_columns: int, columns: List[str], data_start_line: int, nrows: int = 100) -> pd.DataFrame:
    try:
        df = pd.read_csv(
            path,
            sep=r"\s+",
            header=None,
            names=columns,
            skiprows=data_start_line,
            nrows=nrows,
            engine="python",
            encoding="utf-8",
        )
        return df
    except Exception:
        # Fallback: manual line split for harder files.
        rows = []
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in range(data_start_line):
                _ = f.readline()
            for _ in range(nrows):
                line = f.readline()
                if not line:
                    break
                parts = line.strip().split()
                if not parts:
                    continue
                if len(parts) < n_columns:
                    parts = parts + [None] * (n_columns - len(parts))
                rows.append(parts[:n_columns])
        if not rows:
            return pd.DataFrame(columns=columns)
        return pd.read_csv(io.StringIO("\n".join(["\t".join(map(str, r)) for r in rows])), sep=r"\s+", names=columns, engine="python")


def summarize_gslib_files(files: List[Path], root: Path, logger, sample_rows: int = 100) -> Tuple[pd.DataFrame, pd.DataFrame]:
    schema_rows: List[Dict] = []
    sample_frames: List[pd.DataFrame] = []

    for idx, path in enumerate(files, start=1):
        rel = to_rel(path, root)
        logger.info("GSLIB %d/%d: %s", idx, len(files), rel)
        header = parse_gslib_header(path)
        coord_cols, value_cols, unknown_cols = _classify_columns(header["columns"])
        schema_rows.append(
            {
                "path": rel,
                "title": header["title"],
                "n_columns": header["n_columns"],
                "columns_json": json.dumps(header["columns"]),
                "coord_columns_json": json.dumps(coord_cols),
                "value_columns_json": json.dumps(value_cols),
                "unknown_columns_json": json.dumps(unknown_cols),
                "header_ok": header["header_ok"],
                "notes": header["notes"],
            }
        )

        if not header["header_ok"]:
            continue
        sample_df = sample_gslib_rows(
            path,
            n_columns=header["n_columns"],
            columns=header["columns"],
            data_start_line=header["data_start_line"],
            nrows=sample_rows,
        )
        if sample_df.empty:
            continue
        sample_df.insert(0, "sample_row_number", range(1, len(sample_df) + 1))
        sample_df.insert(0, "path", rel)
        sample_frames.append(sample_df)

    schema_df = pd.DataFrame(schema_rows)
    samples_df = pd.concat(sample_frames, ignore_index=True, sort=False) if sample_frames else pd.DataFrame(columns=["path", "sample_row_number"])
    return schema_df, samples_df

