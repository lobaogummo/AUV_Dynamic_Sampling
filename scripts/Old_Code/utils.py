"""Utility helpers for dataset exploration scripts."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence


LOGGER_NAME = "dataset_explorer"


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def to_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def guess_test_id(path_str: str) -> Optional[str]:
    upper = path_str.upper()
    if "TEST_C4" in upper or re.search(r"\bC4\b", upper):
        return "C4"
    if "TEST_D4" in upper or re.search(r"\bD4\b", upper):
        return "D4"
    return None


def _parse_date_token(token: str) -> Optional[str]:
    formats = ("%Y%m%d", "%Y_%m_%d", "%d-%m-%Y", "%Y-%m-%d", "%Y%m%d_")
    for fmt in formats:
        try:
            return datetime.strptime(token.strip("_"), fmt.strip("_")).date().isoformat()
        except ValueError:
            continue
    return None


def guess_date(path_str: str) -> Optional[str]:
    candidates = re.findall(r"\d{8}|\d{4}_\d{2}_\d{2}|\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}", path_str)
    for token in candidates:
        parsed = _parse_date_token(token)
        if parsed:
            return parsed
    return None


def guess_type(path: Path) -> str:
    name = path.name.lower()
    ext = path.suffix.lower()
    if ext == ".nc":
        if "auv" in name or "lauv" in name:
            return "auv_netcdf"
        if "hres" in name:
            return "cmems_hres_netcdf"
        if "predmodel" in name:
            return "simulation_netcdf"
        return "netcdf"
    if ext == ".gslib":
        if "variogram" in name:
            return "variogram_input"
        if "median" in name:
            return "post_median_grid"
        if "stdev" in name or "std" in name:
            return "post_std_grid"
        if "scene" in name:
            return "scene_gslib"
        return "gslib_grid"
    if ext == ".out":
        if name.startswith("sim_"):
            return "simulation_realization"
        if "mask" in name:
            return "mask_output"
        return "ascii_output"
    if ext == ".par":
        return "parameter_file"
    if ext == ".mat":
        return "matlab_workspace"
    if ext in {".png", ".fig", ".pptx"}:
        return "visualization_asset"
    if ext == ".zip":
        return "archive"
    if ext == ".txt":
        return "text_notes"
    if ext == ".csv":
        return "table_csv"
    if ext == ".exe":
        return "executable"
    if ext == "":
        return "no_extension_file"
    return "other"


def file_extension(path: Path) -> str:
    return path.suffix.lower() if path.suffix else "<none>"


def chunked(seq: Sequence[Path], size: int) -> Iterable[Sequence[Path]]:
    for idx in range(0, len(seq), size):
        yield seq[idx : idx + size]

