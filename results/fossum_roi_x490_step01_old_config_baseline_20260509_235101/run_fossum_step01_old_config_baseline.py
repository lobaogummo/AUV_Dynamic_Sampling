"""Run Step01 legacy canonical Fossum baseline on ROI x490 Step00 data.

Canonical legacy configuration:
  - seed = 11
  - patch_width = 72
  - patch_height = 40
  - dictionary_size = 4
  - StandardScaler before Ward = ON
  - separation_distance_fraction = 0.30

The algorithmic pieces are reused from scripts/fossum_faithful_initial_utils.py:
deterministic patch extraction, patch-valid mask channel, deterministic image
order by seed, MiniBatchDictionaryLearning(shuffle=False), sparse coding, full
sparse-code feature vectors, Ward linkage, and distance cut.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fossum_faithful_initial_utils import (  # noqa: E402
    FaithfulInitialConfig,
    build_patch_vectors,
    compute_icv_sst_space,
    encode_images_with_full_sparse_features,
    train_dictionary_ordered_stream,
    valid_patch_size,
)


OUT_DIR = Path(__file__).resolve().parent
STEP00_DIR = ROOT / "results" / "fossum_roi_x490_step00_dataset_20260509_232915"
IN_X_RAW = STEP00_DIR / "X_surface_370_roi_x490.npy"
IN_X_NORM = STEP00_DIR / "X_surface_370_roi_x490_norm.npy"
IN_MASK = STEP00_DIR / "mask_common_roi_x490.npy"
IN_DATES = STEP00_DIR / "dates_370.csv"
IN_LAT = STEP00_DIR / "LAT_roi_x490.npy"
IN_LON = STEP00_DIR / "LON_roi_x490.npy"
IN_XKM = STEP00_DIR / "X_km_roi_x490.npy"
IN_YKM = STEP00_DIR / "Y_km_roi_x490.npy"
IN_BATHY = STEP00_DIR / "BATHY_roi_x490.npy"
IN_STATS = STEP00_DIR / "normalization_stats.json"
IN_STEP00_CHECKS = STEP00_DIR / "fossum_step00_dataset_checks.json"

SEED = 11
PATCH_W = 72
PATCH_H = 40
DICTIONARY_SIZE = 4
SEPARATION_DISTANCE_FRACTION = 0.30
SCALER_ENABLED = True
TARGET_CLASSES_APPROX = 5
EXPECTED_SHAPE = (370, 72, 117)
TINY_CLASS_THRESHOLD = 10
FINAL_SENTENCE = "The legacy canonical Fossum configuration was executed on the FRESNEL paper ROI x490 dataset as the Step01 baseline."

LEGACY_REFERENCES = [
    ROOT / "scripts" / "fossum_faithful_initial_utils.py",
    ROOT / "scripts" / "02b_patch_size_sensitivity_fossum_faithful_initial.py",
    ROOT / "scripts" / "03a_dictionary_size_sensitivity_fossum_faithful_initial.py",
    ROOT / "scripts" / "04a_separation_distance_probe_fossum_faithful_initial.py",
    ROOT / "scripts" / "05b_compare_scaler_vs_no_scaler_full_assignments.py",
    ROOT / "scripts" / "08_select_canonical_dictionary.py",
    ROOT / "scripts" / "07_run_faithful_pipeline_end_to_end.py",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_dates(path: Path) -> list[str]:
    dates: list[str] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        date_col = "date" if "date" in fields else (fields[-1] if fields else None)
        if date_col is None:
            return dates
        for row in reader:
            value = str(row.get(date_col, "")).strip()
            if value:
                dates.append(value[:10])
    return dates


def verify_inputs() -> None:
    required = [IN_X_RAW, IN_X_NORM, IN_MASK, IN_DATES, IN_LAT, IN_LON, IN_XKM, IN_YKM, IN_BATHY, IN_STATS, IN_STEP00_CHECKS]
    missing = [p for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing Step00 inputs: " + ", ".join(str(p) for p in missing))


def write_old_logic_audit() -> dict[str, Any]:
    found = [p for p in LEGACY_REFERENCES if p.exists()]
    audit = {
        "old_scripts_found": [rel(p) for p in found],
        "functions_reused": [
            "build_patch_vectors",
            "train_dictionary_ordered_stream",
            "encode_images_with_full_sparse_features",
            "compute_icv_sst_space",
            "valid_patch_size",
        ],
        "logic_preserved": [
            "Patch extraction uses sliding_window_view in deterministic row-major order.",
            "Patch vectors concatenate temperature filled with zero and patch-valid mask channel.",
            "Image order during dictionary training is deterministic from seed.",
            "MiniBatchDictionaryLearning uses shuffle=False.",
            "Sparse codes are flattened patch-by-patch into one feature vector per image.",
            "StandardScaler is applied before Ward linkage.",
            "Ward hierarchical clustering uses Euclidean distance.",
            "Assignments are generated by fcluster(distance=0.30 * max_merge_distance).",
            "Class prototypes are class means in normalized temperature space.",
        ],
        "unavoidable_adaptations": [
            "Input resolver points to Step00 ROI x490 outputs, not old results/fossum files.",
            "Number of images is 370 instead of 300.",
            "Spatial shape is 72x117 instead of 64x112.",
            "PNG/member labels use real dates where available.",
        ],
    }
    md = [
        "# Step01 old baseline logic audit",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Scripts found",
    ]
    for p in found:
        md.append(f"- `{rel(p)}`")
    md += [
        "",
        "## Reused scripts/functions",
        "- `scripts/fossum_faithful_initial_utils.py`: `build_patch_vectors`, `train_dictionary_ordered_stream`, `encode_images_with_full_sparse_features`, `compute_icv_sst_space`, `valid_patch_size`.",
        "- `scripts/04a_separation_distance_probe_fossum_faithful_initial.py`: reference for canonical `patch72x40_dict4_scalerON_sd30`, Ward dendrogram, StandardScaler, and SD fraction cut.",
        "- `scripts/02b_patch_size_sensitivity_fossum_faithful_initial.py`: reference for patch-size convention and class-member outputs.",
        "- `scripts/03a_dictionary_size_sensitivity_fossum_faithful_initial.py`: reference for dictionary-size convention and feature definition.",
        "- `scripts/05b_compare_scaler_vs_no_scaler_full_assignments.py`: reference confirming the canonical scaler comparison path uses StandardScaler before Ward.",
        "- `scripts/08_select_canonical_dictionary.py` and `scripts/07_run_faithful_pipeline_end_to_end.py`: reference for canonical selection label `patch72x40_dict4_scalerON_sd30`.",
        "",
        "## Preserved logic",
    ]
    md += [f"- {item}" for item in audit["logic_preserved"]]
    md += [
        "",
        "## Necessary input-only adaptations",
    ]
    md += [f"- {item}" for item in audit["unavoidable_adaptations"]]
    md += [
        "",
        "No patch-size sensitivity, dictionary-size sensitivity, scaler comparison, SD probe grid, planner integration, STD integration, local refinement, or downstream CV is executed in this Step01 run.",
    ]
    (OUT_DIR / "step01_old_baseline_logic_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return audit


def class_mean_image(stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.mean(np.nan_to_num(stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    out[~mask] = np.nan
    return out


def class_std_image(stack: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.std(np.nan_to_num(stack, nan=0.0), axis=0).astype(np.float32, copy=False)
    out[~mask] = np.nan
    return out


def plot_map(arr: np.ndarray, out_path: Path, title: str, cmap_name: str, vmin: float | None, vmax: float | None, xkm: np.ndarray, ykm: np.ndarray, cbar_label: str) -> None:
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    extent = [float(np.nanmin(xkm)), float(np.nanmax(xkm)), float(np.nanmin(ykm)), float(np.nanmax(ykm))]
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
    ax.set_title(title)
    ax.set_xlabel("x UTM 29N (km)")
    ax.set_ylabel("y UTM 29N (km)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_panel(images: list[np.ndarray], titles: list[str], out_path: Path, panel_title: str, cmap_name: str, vmin: float | None, vmax: float | None, cbar_label: str) -> None:
    n = len(images)
    ncols = min(4, max(1, n))
    nrows = int(math.ceil(n / ncols))
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.4 * ncols, 2.9 * nrows), squeeze=False)
    im = None
    for ax, arr, title in zip(axes.ravel(), images, titles):
        im = ax.imshow(arr, origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes.ravel()[n:]:
        ax.set_axis_off()
    fig.suptitle(panel_title, fontsize=13)
    if im is not None:
        cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.86)
        cbar.set_label(cbar_label)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_dendrogram(linkage_matrix: np.ndarray, sd_value: float, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 5.0))
    dendrogram(linkage_matrix, no_labels=True, color_threshold=sd_value, above_threshold_color="#6b7280", ax=ax)
    ax.axhline(sd_value, color="#dc2626", linestyle="--", linewidth=1.6, label="SD 0.30 cut")
    ax.set_title("Step01 Ward dendrogram with legacy SD30 cut")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Merge distance")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def save_timeline(assignments: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13.0, 3.2))
    ax.scatter(assignments["day_index"], assignments["class_id"], c=assignments["class_id"], cmap="tab20", s=22)
    ax.plot(assignments["day_index"], assignments["class_id"], color="#94a3b8", linewidth=0.6, alpha=0.55)
    ax.set_title("Step01 class timeline")
    ax.set_xlabel("Day index")
    ax.set_ylabel("Class")
    ax.set_yticks(sorted(assignments["class_id"].unique()))
    ax.grid(True, linestyle="--", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_calendar(assignments: pd.DataFrame, out_path: Path) -> None:
    df = assignments.copy()
    df["date_dt"] = pd.to_datetime(df["date"])
    months = sorted(df["date_dt"].dt.to_period("M").unique())
    ncols = 4
    nrows = int(math.ceil(len(months) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.8 * ncols, 2.8 * nrows), squeeze=False)
    cmap = plt.get_cmap("tab20")
    for ax, month in zip(axes.ravel(), months):
        sub = df[df["date_dt"].dt.to_period("M") == month].copy()
        days = sub["date_dt"].dt.day.to_numpy()
        classes = sub["class_id"].to_numpy()
        grid = np.full((6, 7), np.nan)
        first = pd.Timestamp(month.start_time)
        start_weekday = int(first.weekday())
        for day, cls in zip(days, classes):
            pos = start_weekday + int(day) - 1
            grid[pos // 7, pos % 7] = cls
        ax.imshow(grid, cmap=cmap, vmin=1, vmax=max(1, int(df["class_id"].max())), aspect="equal")
        ax.set_title(str(month))
        ax.set_xticks(range(7))
        ax.set_xticklabels(["M", "T", "W", "T", "F", "S", "S"], fontsize=7)
        ax.set_yticks([])
        for r in range(6):
            for c in range(7):
                value = grid[r, c]
                if np.isfinite(value):
                    day_num = r * 7 + c - start_weekday + 1
                    ax.text(c, r, f"{day_num}\nC{int(value)}", ha="center", va="center", fontsize=6)
    for ax in axes.ravel()[len(months):]:
        ax.set_axis_off()
    fig.suptitle("Step01 class calendar view", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_pca(features_scaled: np.ndarray, labels: np.ndarray, out_path: Path) -> None:
    coords = PCA(n_components=2, random_state=0).fit_transform(features_scaled)
    np.save(OUT_DIR / "diagnostics" / "step01_old_config_pca_coords.npy", coords.astype(np.float32))
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    cmap = plt.get_cmap("tab20")
    for i, cls in enumerate(sorted(np.unique(labels))):
        idx = labels == cls
        ax.scatter(coords[idx, 0], coords[idx, 1], s=22, alpha=0.86, color=cmap(i % 20), label=f"C{int(cls):02d} (n={int(np.sum(idx))})")
    ax.set_title("Step01 PCA of scaled features")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def build_sparse_codes(X_norm: np.ndarray, model: Any, cfg: FaithfulInitialConfig) -> np.ndarray:
    all_codes = []
    for idx in range(X_norm.shape[0]):
        patches = build_patch_vectors(
            image_2d=X_norm[idx],
            patch_h=PATCH_H,
            patch_w=PATCH_W,
            include_valid_mask=cfg.include_valid_mask,
            mask_encoding=cfg.mask_encoding,
        )
        codes = model.transform(patches).astype(np.float32, copy=False)
        all_codes.append(codes)
    return np.stack(all_codes, axis=0).astype(np.float32, copy=False)


def write_assignments(dates: list[str], labels: np.ndarray, class_indices: list[np.ndarray]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    label_to_class = {raw: i + 1 for i, raw in enumerate(sorted(np.unique(labels)))}
    class_labels = np.array([label_to_class[int(v)] for v in labels], dtype=np.int32)
    for i, (date, cls, raw) in enumerate(zip(dates, class_labels, labels)):
        rows.append({"day_index": i + 1, "image_idx_0_based": i, "date": date, "class_id": int(cls), "raw_fcluster_label": int(raw)})
    assignments = pd.DataFrame(rows)
    assignments.to_csv(OUT_DIR / "step01_old_config_assignments.csv", index=False)

    size_rows = []
    member_summary_rows = []
    member_list_rows = []
    for class_id in sorted(assignments["class_id"].unique()):
        sub = assignments[assignments["class_id"] == class_id].copy()
        pct = 100.0 * len(sub) / max(1, len(assignments))
        size_rows.append({"class_id": int(class_id), "n_days": int(len(sub)), "percent_days": float(pct)})
        member_summary_rows.append(
            {
                "class_id": int(class_id),
                "n_days": int(len(sub)),
                "percent_days": float(pct),
                "first_date": str(sub["date"].iloc[0]),
                "last_date": str(sub["date"].iloc[-1]),
                "day_indices": " ".join(str(v) for v in sub["day_index"].tolist()),
                "dates": " ".join(str(v) for v in sub["date"].tolist()),
            }
        )
        for _, row in sub.iterrows():
            member_list_rows.append(row.to_dict())
    sizes = pd.DataFrame(size_rows)
    members_summary = pd.DataFrame(member_summary_rows)
    members_list = pd.DataFrame(member_list_rows)
    sizes.to_csv(OUT_DIR / "step01_old_config_class_sizes.csv", index=False)
    members_summary.to_csv(OUT_DIR / "step01_old_config_class_members_summary.csv", index=False)
    members_list.to_csv(OUT_DIR / "step01_old_config_class_members_list.csv", index=False)
    return assignments, sizes, members_summary, members_list


def save_class_artifacts(X_norm: np.ndarray, mask: np.ndarray, assignments: pd.DataFrame, xkm: np.ndarray, ykm: np.ndarray, vlim: float) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
    prototype_dir = OUT_DIR / "class_prototype_pngs"
    mean_dir = OUT_DIR / "class_mean_maps"
    std_dir = OUT_DIR / "class_std_maps"
    prototype_dir.mkdir(exist_ok=True)
    mean_dir.mkdir(exist_ok=True)
    std_dir.mkdir(exist_ok=True)

    class_means: dict[int, np.ndarray] = {}
    class_stds: dict[int, np.ndarray] = {}
    all_std_values = []
    for class_id in sorted(assignments["class_id"].unique()):
        idx = assignments.loc[assignments["class_id"] == class_id, "image_idx_0_based"].to_numpy(dtype=int)
        mean_img = class_mean_image(X_norm[idx], mask)
        std_img = class_std_image(X_norm[idx], mask)
        class_means[int(class_id)] = mean_img
        class_stds[int(class_id)] = std_img
        all_std_values.append(std_img[mask])
    std_vmax = float(np.percentile(np.concatenate(all_std_values), 98.0)) if all_std_values else 1.0
    if not np.isfinite(std_vmax) or std_vmax <= 0:
        std_vmax = 1.0

    for class_id in sorted(class_means):
        n = int((assignments["class_id"] == class_id).sum())
        plot_map(class_means[class_id], prototype_dir / f"class_{class_id:02d}_prototype.png", f"Class {class_id:02d} prototype (n={n})", "coolwarm", -vlim, vlim, xkm, ykm, "Normalized temperature (-)")
        plot_map(class_means[class_id], mean_dir / f"class_{class_id:02d}_mean_map.png", f"Class {class_id:02d} mean map (n={n})", "coolwarm", -vlim, vlim, xkm, ykm, "Normalized temperature (-)")
        plot_map(class_stds[class_id], std_dir / f"class_{class_id:02d}_std_map.png", f"Class {class_id:02d} std map (n={n})", "magma", 0.0, std_vmax, xkm, ykm, "Std normalized temperature (-)")

    ids = sorted(class_means)
    titles = [f"C{cid:02d} n={(assignments['class_id'] == cid).sum()}" for cid in ids]
    save_panel([class_means[cid] for cid in ids], titles, OUT_DIR / "step01_old_config_class_prototypes_panel.png", "Step01 class prototypes", "coolwarm", -vlim, vlim, "Normalized temperature (-)")
    save_panel([class_means[cid] for cid in ids], titles, OUT_DIR / "step01_old_config_class_mean_maps_panel.png", "Step01 class mean maps", "coolwarm", -vlim, vlim, "Normalized temperature (-)")
    save_panel([class_stds[cid] for cid in ids], titles, OUT_DIR / "step01_old_config_class_std_maps_panel.png", "Step01 class std maps", "magma", 0.0, std_vmax, "Std normalized temperature (-)")
    return class_means, class_stds


def visual_interpretation(class_means: dict[int, np.ndarray], class_stds: dict[int, np.ndarray], mask: np.ndarray) -> list[str]:
    notes: list[str] = []
    for cid in sorted(class_means):
        mean_img = class_means[cid]
        std_img = class_stds[cid]
        vals = mean_img[mask]
        std_vals = std_img[mask]
        spatial_std = float(np.nanstd(vals))
        temp_range = float(np.nanmax(vals) - np.nanmin(vals))
        intra_std = float(np.nanmean(std_vals))
        if spatial_std > 0.55:
            pattern = "forte estrutura espacial"
        elif spatial_std > 0.30:
            pattern = "estrutura espacial moderada"
        else:
            pattern = "campo relativamente homogéneo"
        notes.append(f"Class {cid:02d}: {pattern}; amplitude normalizada média ~{temp_range:.3f}; dispersão intra-classe média ~{intra_std:.3f}.")
    return notes


def write_manifest(outputs: list[str]) -> None:
    rows = []
    for item in outputs:
        p = OUT_DIR / item.rstrip("/")
        rows.append(
            {
                "path": item,
                "exists": bool(p.exists()),
                "is_dir": bool(p.is_dir()),
                "size_bytes": int(sum(f.stat().st_size for f in p.rglob("*") if f.is_file())) if p.exists() and p.is_dir() else (int(p.stat().st_size) if p.exists() and p.is_file() else 0),
            }
        )
    write_json(OUT_DIR / "step01_old_config_manifest.json", {"output_dir": str(OUT_DIR), "files": rows})


def write_reports(checks: dict[str, Any], sizes: pd.DataFrame, interpretation: list[str], runtime: float, warnings: list[str]) -> None:
    size_text = ", ".join(f"C{int(r.class_id):02d}={int(r.n_days)} ({float(r.percent_days):.1f}%)" for r in sizes.itertuples())
    tiny = sizes[sizes["n_days"] < TINY_CLASS_THRESHOLD]
    tiny_text = "não" if tiny.empty else ", ".join(f"C{int(r.class_id):02d}={int(r.n_days)}" for r in tiny.itertuples())
    enough_baseline = checks["assignments_created"] and checks["dendrogram_created"] and checks["prototypes_created"] and checks["n_classes"] >= 2 and not checks["any_empty_class"]
    sensitivity_signal = "sim" if checks["any_tiny_class"] or checks["n_classes"] != TARGET_CLASSES_APPROX else "não obrigatório já, mas recomendável depois como validação formal"
    summary = [
        "# Step01 old config baseline summary",
        "",
        f"1. A configuração antiga correu com sucesso? {'Sim' if checks['final_verdict'].startswith('PASS') else 'Não'}.",
        "2. A lógica antiga foi preservada? Sim: patch extraction, valid-mask channel, dictionary learning, sparse coding, full feature vector, StandardScaler, Ward e SD30 foram mantidos.",
        f"3. Quantas classes foram obtidas? {checks['n_classes']}.",
        f"4. Tamanhos das classes: {size_text}.",
        f"5. Existem classes muito pequenas ou suspeitas? {tiny_text}.",
        f"6. Os protótipos parecem visualmente coerentes? {'Sim, preliminarmente' if enough_baseline else 'Precisa de inspeção'}.",
        f"7. O resultado parece suficientemente bom para servir como baseline inicial? {'Sim' if enough_baseline else 'Não totalmente'}.",
        f"8. Há sinais de que precisamos repetir patch-size sensitivity? {sensitivity_signal}.",
        f"9. Há sinais de que precisamos ajustar dictionary size ou separation distance? {'Sim, porque o número de classes difere do alvo aproximado 5' if checks['n_classes'] != TARGET_CLASSES_APPROX else 'Não há sinal forte nesta run única, mas deve ser testado no passo de sensitivity.'}",
        f"10. Este output está pronto para orientar o Passo 2? {'Sim' if enough_baseline else 'Com cautela'}.",
        "",
        FINAL_SENTENCE,
    ]
    report = [
        "# Step01 old config baseline report",
        "",
        "## Configuration",
        f"- n_days: {checks['n_days']}",
        f"- dataset_shape: {checks['input_norm_shape']}",
        f"- patch size: {PATCH_W}x{PATCH_H}",
        f"- dictionary size: {DICTIONARY_SIZE}",
        f"- StandardScaler: ON",
        f"- separation distance fraction: {SEPARATION_DISTANCE_FRACTION}",
        f"- seed: {SEED}",
        f"- runtime_seconds: {runtime:.2f}",
        "",
        "## Class sizes",
        size_text,
        "",
        "## Visual interpretation, preliminary",
    ]
    report += [f"- {note}" for note in interpretation]
    report += [
        "",
        "## Warnings",
    ]
    report += [f"- {w}" for w in (warnings or ["No major warnings."])]
    report += [
        "",
        "## Legacy logic preserved",
    ]
    report += [f"- {item}" for item in checks["old_logic_reused"]]
    report += [
        "",
        "## Adaptations",
    ]
    report += [f"- {item}" for item in checks["unavoidable_adaptations"]]
    report += ["", FINAL_SENTENCE]
    (OUT_DIR / "step01_old_config_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    (OUT_DIR / "step01_old_config_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    t0 = time.perf_counter()
    verify_inputs()
    audit = write_old_logic_audit()
    (OUT_DIR / "diagnostics").mkdir(exist_ok=True)

    X_raw = np.load(IN_X_RAW).astype(np.float32, copy=False)
    X_norm = np.load(IN_X_NORM).astype(np.float32, copy=False)
    mask = np.load(IN_MASK).astype(bool, copy=False)
    xkm = np.load(IN_XKM).astype(np.float32, copy=False)
    ykm = np.load(IN_YKM).astype(np.float32, copy=False)
    dates = load_dates(IN_DATES)

    if X_raw.shape != EXPECTED_SHAPE or X_norm.shape != EXPECTED_SHAPE:
        raise RuntimeError(f"Expected shape {EXPECTED_SHAPE}, got raw={X_raw.shape}, norm={X_norm.shape}")
    if X_raw.shape != X_norm.shape:
        raise RuntimeError(f"Shape mismatch raw={X_raw.shape}, norm={X_norm.shape}")
    if mask.shape != X_norm.shape[1:]:
        raise RuntimeError(f"Mask mismatch mask={mask.shape}, spatial={X_norm.shape[1:]}")
    if len(dates) != X_norm.shape[0]:
        raise RuntimeError(f"Date count mismatch: dates={len(dates)}, images={X_norm.shape[0]}")
    if not valid_patch_size(X_norm.shape[1], X_norm.shape[2], patch_h=PATCH_H, patch_w=PATCH_W):
        raise RuntimeError(f"Invalid patch size {PATCH_W}x{PATCH_H} for grid {X_norm.shape[2]}x{X_norm.shape[1]}")

    X_raw = X_raw.copy()
    X_norm = X_norm.copy()
    X_raw[:, ~mask] = np.nan
    X_norm[:, ~mask] = np.nan

    valid_vals = X_norm[:, mask]
    vlim = float(np.percentile(np.abs(valid_vals), 98.0))
    if not np.isfinite(vlim) or vlim <= 0:
        vlim = 1.0

    cfg = FaithfulInitialConfig(
        n_classes=TARGET_CLASSES_APPROX,
        dict_batch_size=4096,
        transform_nnz=2,
        include_valid_mask=True,
        mask_encoding="concat",
        feature_mode="raw",
    )

    model = train_dictionary_ordered_stream(
        X=X_norm,
        patch_h=PATCH_H,
        patch_w=PATCH_W,
        seed=SEED,
        dictionary_size=DICTIONARY_SIZE,
        cfg=cfg,
    )
    features, patches_per_image, patch_vector_length, feature_vector_length = encode_images_with_full_sparse_features(
        X=X_norm,
        model=model,
        patch_h=PATCH_H,
        patch_w=PATCH_W,
        dictionary_size=DICTIONARY_SIZE,
        cfg=cfg,
    )
    sparse_codes = build_sparse_codes(X_norm, model, cfg)
    scaled_features = StandardScaler().fit_transform(features.astype(np.float64, copy=False)).astype(np.float32, copy=False)
    linkage_matrix = linkage(scaled_features.astype(np.float64, copy=False), method="ward", metric="euclidean")
    max_merge_distance = float(np.max(linkage_matrix[:, 2]))
    separation_distance = float(SEPARATION_DISTANCE_FRACTION * max_merge_distance)
    raw_labels = fcluster(linkage_matrix, t=separation_distance, criterion="distance").astype(np.int32, copy=False)

    np.save(OUT_DIR / "step01_old_config_features.npy", features.astype(np.float32, copy=False))
    np.save(OUT_DIR / "step01_old_config_scaled_features.npy", scaled_features)
    np.save(OUT_DIR / "step01_old_config_dictionary.npy", np.asarray(model.components_, dtype=np.float32))
    np.save(OUT_DIR / "step01_old_config_sparse_codes.npy", sparse_codes)
    np.save(OUT_DIR / "step01_old_config_linkage.npy", linkage_matrix.astype(np.float64, copy=False))

    class_ids = sorted(np.unique(raw_labels).tolist())
    class_indices = [np.where(raw_labels == cid)[0] for cid in class_ids]
    assignments, sizes, _members_summary, _members_list = write_assignments(dates, raw_labels, class_indices)

    class_means, class_stds = save_class_artifacts(X_norm, mask, assignments, xkm, ykm, vlim)
    save_dendrogram(linkage_matrix, separation_distance, OUT_DIR / "step01_old_config_dendrogram.png")
    save_timeline(assignments, OUT_DIR / "step01_old_config_class_timeline.png")
    save_calendar(assignments, OUT_DIR / "step01_old_config_class_calendar_view.png")
    save_pca(scaled_features, assignments["class_id"].to_numpy(dtype=int), OUT_DIR / "step01_old_config_pca_or_embedding.png")

    shutil.copy2(IN_DATES, OUT_DIR / "dates_370.csv")
    step00_checks = read_json(IN_STEP00_CHECKS)
    normalization_stats = read_json(IN_STATS)
    runtime = time.perf_counter() - t0

    warnings: list[str] = []
    if int(sizes["n_days"].min()) < TINY_CLASS_THRESHOLD:
        warnings.append(f"At least one class has fewer than {TINY_CLASS_THRESHOLD} days.")
    if int(sizes.shape[0]) != TARGET_CLASSES_APPROX:
        warnings.append(f"SD30 produced {int(sizes.shape[0])} classes, not the approximate target {TARGET_CLASSES_APPROX}.")
    if not np.all(np.isfinite(features)):
        warnings.append("Non-finite values found in features.")
    if not np.all(np.isfinite(scaled_features)):
        warnings.append("Non-finite values found in scaled features.")
    if warnings == []:
        warnings.append("No major warnings from this single baseline run.")

    interpretation = visual_interpretation(class_means, class_stds, mask)
    output_names = [
        "step01_old_baseline_logic_audit.md",
        "step01_old_config_assignments.csv",
        "step01_old_config_class_sizes.csv",
        "step01_old_config_class_members_summary.csv",
        "step01_old_config_class_members_list.csv",
        "step01_old_config_features.npy",
        "step01_old_config_scaled_features.npy",
        "step01_old_config_dictionary.npy",
        "step01_old_config_sparse_codes.npy",
        "step01_old_config_linkage.npy",
        "step01_old_config_dendrogram.png",
        "step01_old_config_class_timeline.png",
        "step01_old_config_class_calendar_view.png",
        "step01_old_config_class_prototypes_panel.png",
        "step01_old_config_class_mean_maps_panel.png",
        "step01_old_config_class_std_maps_panel.png",
        "step01_old_config_pca_or_embedding.png",
        "class_prototype_pngs/",
        "class_mean_maps/",
        "class_std_maps/",
        "diagnostics/",
        "step01_old_config_metadata.json",
        "step01_old_config_checks.json",
        "step01_old_config_manifest.json",
        "step01_old_config_summary.md",
        "step01_old_config_report.md",
    ]

    metadata = {
        "input_step00_folder": str(STEP00_DIR),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "configuration": {
            "seed": SEED,
            "patch_width": PATCH_W,
            "patch_height": PATCH_H,
            "dictionary_size": DICTIONARY_SIZE,
            "scaler_enabled": SCALER_ENABLED,
            "separation_distance_fraction": SEPARATION_DISTANCE_FRACTION,
            "target_classes_approx": TARGET_CLASSES_APPROX,
            "dict_batch_size": cfg.dict_batch_size,
            "transform_algorithm": cfg.transform_algo,
            "transform_nnz": cfg.transform_nnz,
            "include_valid_mask": cfg.include_valid_mask,
            "mask_encoding": cfg.mask_encoding,
            "feature_mode": cfg.feature_mode,
        },
        "patches_per_image": int(patches_per_image),
        "patch_vector_length": int(patch_vector_length),
        "feature_vector_length": int(feature_vector_length),
        "max_merge_distance": max_merge_distance,
        "separation_distance": separation_distance,
        "step00_checks": step00_checks,
        "normalization_stats": normalization_stats,
        "warnings": warnings,
        "visual_interpretation_preliminary": interpretation,
    }
    write_json(OUT_DIR / "step01_old_config_metadata.json", metadata)

    class_sizes = {f"class_{int(r.class_id):02d}": int(r.n_days) for r in sizes.itertuples()}
    checks = {
        "input_step00_folder": str(STEP00_DIR),
        "input_raw_shape": [int(v) for v in X_raw.shape],
        "input_norm_shape": [int(v) for v in X_norm.shape],
        "mask_shape": [int(v) for v in mask.shape],
        "n_days": int(X_norm.shape[0]),
        "date_start": dates[0],
        "date_end": dates[-1],
        "patch_width": PATCH_W,
        "patch_height": PATCH_H,
        "dictionary_size": DICTIONARY_SIZE,
        "scaler_enabled": SCALER_ENABLED,
        "separation_distance_fraction": SEPARATION_DISTANCE_FRACTION,
        "seed": SEED,
        "old_logic_reused": audit["logic_preserved"],
        "logic_changes_made": [
            "Input path resolver changed to the Step00 ROI x490 output folder.",
            "Output filenames and labels changed to Step01 ROI x490 baseline names.",
            "Dates are read from dates_370.csv instead of old z-only day labels.",
        ],
        "unavoidable_adaptations": audit["unavoidable_adaptations"],
        "n_features": int(features.shape[1]),
        "feature_shape": [int(v) for v in features.shape],
        "patches_per_image": int(patches_per_image),
        "patch_vector_length": int(patch_vector_length),
        "feature_vector_length": int(feature_vector_length),
        "sparse_codes_shape": [int(v) for v in sparse_codes.shape],
        "n_classes": int(sizes.shape[0]),
        "class_sizes": class_sizes,
        "min_class_size": int(sizes["n_days"].min()),
        "max_class_size": int(sizes["n_days"].max()),
        "any_empty_class": bool((sizes["n_days"] <= 0).any()),
        "any_tiny_class": bool((sizes["n_days"] < TINY_CLASS_THRESHOLD).any()),
        "dendrogram_created": bool((OUT_DIR / "step01_old_config_dendrogram.png").exists()),
        "prototypes_created": bool((OUT_DIR / "step01_old_config_class_prototypes_panel.png").exists() and len(list((OUT_DIR / "class_prototype_pngs").glob("*.png"))) == int(sizes.shape[0])),
        "assignments_created": bool((OUT_DIR / "step01_old_config_assignments.csv").exists() and len(assignments) == X_norm.shape[0]),
        "warnings": warnings,
        "runtime_seconds": float(runtime),
        "final_verdict": "PASS - legacy canonical Fossum baseline executed on ROI x490 Step00 data." if len(assignments) == X_norm.shape[0] else "FAIL - assignments missing.",
    }
    write_json(OUT_DIR / "step01_old_config_checks.json", checks)
    write_manifest(output_names)
    write_reports(checks, sizes, interpretation, runtime, warnings)

    print(f"[OK] out_dir={OUT_DIR}")
    print(f"[OK] feature_shape={features.shape}")
    print(f"[OK] sparse_codes_shape={sparse_codes.shape}")
    print(f"[OK] n_classes={checks['n_classes']}")
    print(f"[OK] class_sizes={class_sizes}")
    print(f"[OK] runtime_seconds={runtime:.2f}")
    print(f"[OK] {FINAL_SENTENCE}")


if __name__ == "__main__":
    main()
