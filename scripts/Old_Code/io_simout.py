"""Inspect sim_*.out format and produce schema notes."""

from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Dict, List

import pandas as pd

from io_gslib import parse_gslib_header
from utils import to_rel


PRINTABLE = set(bytes(string.printable, encoding="ascii"))


def _ascii_score(raw: bytes) -> float:
    if not raw:
        return 0.0
    printable = sum(1 for b in raw if b in PRINTABLE or b in {9, 10, 13})
    return printable / len(raw)


def inspect_sim_out_file(path: Path, root: Path) -> Dict:
    rel = to_rel(path, root)
    out: Dict = {
        "path": rel,
        "format_type": None,
        "ascii_ratio": None,
        "contains_null_byte": None,
        "header_ok": None,
        "title": None,
        "n_columns": None,
        "columns_json": None,
        "notes": None,
    }

    try:
        raw = path.read_bytes()[:8192]
    except Exception as exc:
        out["notes"] = f"read_error: {exc}"
        return out

    ascii_ratio = _ascii_score(raw)
    has_null = b"\x00" in raw
    out["ascii_ratio"] = ascii_ratio
    out["contains_null_byte"] = has_null

    if has_null or ascii_ratio < 0.85:
        out["format_type"] = "binary_or_mixed"
        out["notes"] = "null_bytes_or_low_ascii_ratio"
        return out

    header = parse_gslib_header(path)
    if header["header_ok"]:
        out["format_type"] = "ascii_gslib_like"
        out["header_ok"] = True
        out["title"] = header["title"]
        out["n_columns"] = header["n_columns"]
        out["columns_json"] = json.dumps(header["columns"])
        out["notes"] = header["notes"]
    else:
        out["format_type"] = "ascii_unknown"
        out["header_ok"] = False
        out["notes"] = header["notes"]

    return out


def summarize_sim_out_files(files: List[Path], root: Path, n_inspect: int = 5) -> pd.DataFrame:
    subset = sorted(files)[:n_inspect]
    rows = [inspect_sim_out_file(p, root) for p in subset]
    return pd.DataFrame(rows)


def sim_out_markdown(schema_df: pd.DataFrame) -> str:
    if schema_df.empty:
        return "# FORMATS sim_*.out\n\nNao foram encontrados ficheiros `sim_*.out`.\n"

    lines: List[str] = []
    lines.append("# FORMATS sim_*.out")
    lines.append("")
    lines.append("## Resumo")
    lines.append("")
    counts = schema_df["format_type"].value_counts(dropna=False)
    for name, count in counts.items():
        lines.append(f"- `{name}`: {int(count)} ficheiro(s) inspecionado(s)")
    lines.append("")
    lines.append("## Observacoes")
    lines.append("")

    for _, row in schema_df.iterrows():
        lines.append(f"### `{row['path']}`")
        lines.append(f"- format_type: `{row['format_type']}`")
        lines.append(f"- ascii_ratio: `{row['ascii_ratio']}`")
        lines.append(f"- contains_null_byte: `{row['contains_null_byte']}`")
        if pd.notna(row.get("title")):
            lines.append(f"- title: `{row['title']}`")
        if pd.notna(row.get("n_columns")):
            lines.append(f"- n_columns: `{int(row['n_columns'])}`")
        if pd.notna(row.get("columns_json")):
            lines.append(f"- columns_json: `{row['columns_json']}`")
        if pd.notna(row.get("notes")) and row["notes"]:
            lines.append(f"- notes: `{row['notes']}`")
        lines.append("")

    lines.append("## Inferencia")
    lines.append("")
    lines.append(
        "Os `sim_*.out` inspecionados seguem um cabecalho estilo GSLIB (titulo, numero de colunas e nomes), "
        "com uma coluna `temp` por realizacao."
    )
    lines.append("")
    return "\n".join(lines)

