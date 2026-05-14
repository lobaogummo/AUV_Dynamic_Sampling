"""Check whether the required Filipa/Fossum data assets are present locally.

This script is intentionally read-only. It is meant to be run after cloning or
pulling the Git repository on another PC, after copying/restoring the large
data/results folders by OneDrive, external disk, network share, or Git LFS.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_PATHS = [
    ("raw_filipa_root", "data/dadosParaPedro_Fresnel", "dir"),
    ("raw_cmems_370_file", "data/dadosParaPedro_Fresnel/01.Data/ALL/thetao_20260427.nc", "file"),
    ("predmodel_highres_root", "data/dadosParaPedro_Fresnel/02.Simulations/HighRes", "dir"),
    ("step00_root", "results/fossum_roi_x490_step00_dataset_20260509_232915", "dir"),
    ("step00_raw_array", "results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490.npy", "file"),
    ("step00_norm_array", "results/fossum_roi_x490_step00_dataset_20260509_232915/X_surface_370_roi_x490_norm.npy", "file"),
    ("step00_mask", "results/fossum_roi_x490_step00_dataset_20260509_232915/mask_common_roi_x490.npy", "file"),
    ("step00_dates", "results/fossum_roi_x490_step00_dataset_20260509_232915/dates_370.csv", "file"),
    ("step05_root", "results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755", "dir"),
    ("step05_assignments", "results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_assignments.csv", "file"),
    ("step05_prototypes", "results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_prototypes.npy", "file"),
    ("step05_feature_matrix", "results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_feature_matrix.npy", "file"),
    ("step05_dictionary", "results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_dictionary.npz", "file"),
    ("step05_sparse_codes", "results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755/canonical_sparse_codes.npz", "file"),
    ("step06_root", "results/october_surface_temppred_std_roi_x490_20260511_155923", "dir"),
    ("step06_temppred", "results/october_surface_temppred_std_roi_x490_20260511_155923/TEMPpred_october_surface_roi_x490.npy", "file"),
    ("step06_std", "results/october_surface_temppred_std_roi_x490_20260511_155923/STD_october_surface_roi_x490.npy", "file"),
    ("step06_dates", "results/october_surface_temppred_std_roi_x490_20260511_155923/dates_october.csv", "file"),
    ("pipeline_status_audit", "results/pipeline_status_audit_20260512_222930", "dir"),
    ("step07_cv_notebook_faithful", "results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154", "dir"),
]


OPTIONAL_GLOBS = [
    ("any_step07_cv_output", "results/fossum_roi_x490_step07_cv*"),
    ("any_descriptor_output", "results/*descriptor*"),
    ("any_step08_output", "results/*step08*"),
]


def path_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def main() -> int:
    rows = []
    ok = True
    for label, rel, kind in REQUIRED_PATHS:
        path = ROOT / rel
        exists = path.exists()
        type_ok = (path.is_dir() if kind == "dir" else path.is_file()) if exists else False
        size_bytes = path_size_bytes(path) if exists else 0
        passed = bool(exists and type_ok)
        ok = ok and passed
        rows.append(
            {
                "label": label,
                "required": "yes",
                "kind": kind,
                "relative_path": rel,
                "exists": str(exists).lower(),
                "type_ok": str(type_ok).lower(),
                "size_mb": f"{size_bytes / (1024 * 1024):.2f}",
                "status": "OK" if passed else "MISSING",
            }
        )

    for label, pattern in OPTIONAL_GLOBS:
        matches = sorted(ROOT.glob(pattern))
        rows.append(
            {
                "label": label,
                "required": "no",
                "kind": "glob",
                "relative_path": pattern,
                "exists": str(bool(matches)).lower(),
                "type_ok": str(bool(matches)).lower(),
                "size_mb": "",
                "status": f"{len(matches)} match(es)",
            }
        )

    out_csv = ROOT / "required_data_check.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(f"{row['status']:>10}  {row['label']}: {row['relative_path']}")

    print(f"\nWrote: {out_csv}")
    if ok:
        print("\nREADY: all required data/results are present.")
        return 0
    print("\nNOT READY: one or more required data/results paths are missing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
