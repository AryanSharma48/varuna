#!/usr/bin/env python3
"""
=============================================================================
VARUNA SAR Image Processing & Dark-Feature Candidate Visualization Experiment
=============================================================================

Standalone prototype experiment to process real Sentinel-1 SAR (VH / VV) scenes,
perform radiometric calibration to Decibels (dB), compute robust percentile-based
normalizations, execute multi-polarization fusion, and detect candidate low-backscatter
features using local adaptive thresholding and morphological analysis.

SCIENTIFIC DISCLAIMER:
This script produces a "SAR-based candidate mask / prototype visualization".
It is a physics- and statistics-derived candidate-generation heuristic.
It is NOT an AI / U-Net prediction and NOT a confirmed oil-spill classifier.
"""

import os
import sys
import argparse
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import cv2
import rasterio
from rasterio.windows import Window
from rasterio.control import GroundControlPoint
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

# Ensure root workspace is in sys.path to reuse VARUNA processor functions
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from services.satellite.processor import (
        convert_sar_to_db,
        preprocess_sar_band,
        stretch_array
    )
except ImportError:
    # Standalone fallback matching exact VARUNA specifications
    def convert_sar_to_db(arr: np.ndarray, is_already_db: Optional[bool] = None, eps: float = 1e-5) -> np.ndarray:
        arr_f = arr.astype(np.float32)
        if is_already_db is True or np.any(arr_f < 0.0):
            return arr_f
        return 20.0 * np.log10(np.maximum(arr_f, eps))

    def stretch_array(arr: np.ndarray, p2: float, p98: float) -> np.ndarray:
        clipped = np.clip(arr, p2, p98)
        if (p98 - p2) != 0:
            norm = (clipped - p2) / (p98 - p2)
        else:
            norm = np.zeros_like(clipped)
        return (norm * 255.0).astype(np.uint8)

    def preprocess_sar_band(band_data: np.ndarray, norm_p2: float = 2.0, norm_p98: float = 98.0) -> np.ndarray:
        if band_data.size == 0:
            return band_data.astype(np.float32)
        band_db = convert_sar_to_db(band_data)
        p2 = float(np.percentile(band_db, norm_p2))
        p98 = float(np.percentile(band_db, norm_p98))
        stretched = stretch_array(band_db, p2, p98)
        return stretched.astype(np.float32) / 255.0


def calculate_stats(arr: np.ndarray) -> Dict[str, float]:
    """Calculate min, max, mean, p2, p50, p98 for a 2D numpy array."""
    flat = arr.ravel()
    valid = flat[flat > 0] if np.any(flat > 0) else flat
    return {
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "mean": float(np.mean(valid)),
        "p2": float(np.percentile(valid, 2)),
        "p50": float(np.percentile(valid, 50)),
        "p98": float(np.percentile(valid, 98))
    }


def find_default_sar_files() -> Tuple[str, str]:
    """
    Locates existing Sentinel-1 TIFF files in the workspace.
    Prefers satellite-data/001.tiff (VH) and 002.tiff (VV) or demo incident files.
    """
    candidates_vh = [
        REPO_ROOT / "satellite-data" / "001.tiff",
        REPO_ROOT / "demo" / "incidents" / "incident_001" / "satellite" / "vh.tif",
        Path(r"C:\Users\Aryan Sharma\Desktop\S1B_IW_GRDH_1SDV_20190610T154813_20190610T154838_016636_01F4FD_EE80.SAFE\measurement\s1b-iw-grd-vh-20190610t154813-20190610t154838-016636-01f4fd-002.tiff")
    ]
    candidates_vv = [
        REPO_ROOT / "satellite-data" / "002.tiff",
        REPO_ROOT / "demo" / "incidents" / "incident_001" / "satellite" / "vv.tif",
        Path(r"C:\Users\Aryan Sharma\Desktop\S1B_IW_GRDH_1SDV_20190610T154813_20190610T154838_016636_01F4FD_EE80.SAFE\measurement\s1b-iw-grd-vv-20190610t154813-20190610t154838-016636-01f4fd-001.tiff")
    ]

    vh_path = None
    vv_path = None

    for p in candidates_vh:
        if p.exists():
            vh_path = str(p)
            break

    for p in candidates_vv:
        if p.exists():
            vv_path = str(p)
            break

    if not vh_path or not vv_path:
        raise FileNotFoundError(
            f"Could not find Sentinel-1 VH and VV TIFF files.\n"
            f"Checked paths:\n  VH: {[str(p) for p in candidates_vh]}\n  VV: {[str(p) for p in candidates_vv]}"
        )

    return vh_path, vv_path


def run_experiment(
    vh_path: Optional[str] = None,
    vv_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    top_components: int = 2,
    min_area_pixels: int = 1000
) -> Dict[str, Any]:
    """
    Executes the complete standalone SAR image processing and candidate detection experiment.
    """
    if vh_path is None or vv_path is None:
        def_vh, def_vv = find_default_sar_files()
        vh_path = vh_path or def_vh
        vv_path = vv_path or def_vv

    if output_dir is None:
        out_path = Path(__file__).resolve().parent / "outputs"
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("VARUNA STANDALONE SAR IMAGE PROCESSING & CANDIDATE VISUALIZATION")
    print("=" * 70)
    print(f"[Input VH] {vh_path}")
    print(f"[Input VV] {vv_path}")
    print(f"[Outputs]  {out_path}")
    print("-" * 70)

    # =========================================================================
    # 1. Inspect TIFF Metadata using rasterio
    # =========================================================================
    with rasterio.open(vh_path) as vh_src, rasterio.open(vv_path) as vv_src:
        vh_dim = (vh_src.height, vh_src.width)
        vv_dim = (vv_src.height, vv_src.width)
        vh_dtype = str(vh_src.dtypes[0])
        vv_dtype = str(vv_src.dtypes[0])
        vh_crs = str(vh_src.crs) if vh_src.crs else "None (Sensor Swath Geometry with GCPs)"
        vv_crs = str(vv_src.crs) if vv_src.crs else "None (Sensor Swath Geometry with GCPs)"
        
        vh_gcps, vh_gcps_crs = vh_src.gcps
        vv_gcps, vv_gcps_crs = vv_src.gcps
        gcp_count = len(vh_gcps)
        gcp_crs_str = str(vh_gcps_crs) if vh_gcps_crs else "None"
        
        # Check if full Sentinel-1 scene (e.g., 16685 x 26503) or pre-extracted incident tile (4096 x 4096)
        if vh_src.height > 6000 and vh_src.width > 6000:
            # Full Copernicus GRD scene: target analysis window centered on incident (center_row=7760, center_col=10049)
            center_row, center_col = 7760, 10049
            tile_size = 4096
            row_off = max(0, center_row - tile_size // 2)
            col_off = max(0, center_col - tile_size // 2)
            window = Window(col_off, row_off, tile_size, tile_size)
            print(f"[Window] Extracting analysis window around ({center_row}, {center_col}): row_off={row_off}, col_off={col_off}, size={tile_size}x{tile_size}")
            
            vh_raw = vh_src.read(1, window=window)
            vv_raw = vv_src.read(1, window=window)
            
            # Adjust GCPs for cropped window
            adjusted_gcps = []
            for gcp in vh_gcps:
                adjusted_gcps.append(GroundControlPoint(
                    gcp.row - row_off,
                    gcp.col - col_off,
                    gcp.x, gcp.y, gcp.z,
                    id=gcp.id, info=gcp.info
                ))
            mask_profile = vh_src.profile.copy()
            mask_profile.update({
                "driver": "GTiff",
                "height": tile_size,
                "width": tile_size,
                "count": 1,
                "dtype": "uint8",
                "nodata": 0,
                "transform": None
            })
            effective_gcps = adjusted_gcps
            effective_gcp_crs = vh_gcps_crs
        else:
            # Focused incident tile (e.g. 4096 x 4096)
            row_off, col_off = 0, 0
            vh_raw = vh_src.read(1)
            vv_raw = vv_src.read(1)
            mask_profile = vh_src.profile.copy()
            mask_profile.update({
                "driver": "GTiff",
                "count": 1,
                "dtype": "uint8",
                "nodata": 0
            })
            effective_gcps = vh_gcps
            effective_gcp_crs = vh_gcps_crs

    print(f"Loaded raw bands successfully. Processing array shape: {vh_raw.shape}, dtype: {vh_raw.dtype}")

    # =========================================================================
    # 2. SAR -> dB Conversion
    # SAR_dB = 20 * log10(max(DN, 1e-5))
    # =========================================================================
    vh_stats_raw = calculate_stats(vh_raw)
    vv_stats_raw = calculate_stats(vv_raw)

    vh_db = convert_sar_to_db(vh_raw, is_already_db=False)
    vv_db = convert_sar_to_db(vv_raw, is_already_db=False)

    vh_stats_db = calculate_stats(vh_db)
    vv_stats_db = calculate_stats(vv_db)

    # =========================================================================
    # 3. Robust Normalization
    # 1. Calculate p2 and p98 in dB domain
    # 2. Clip values to [p2, p98]
    # 3. Linearly normalize to [0, 1]
    # =========================================================================
    # Slight gaussian speckle attenuation (sigma=1.2) before normalization preserves spatial structures
    vh_smooth = cv2.GaussianBlur(vh_db, (5, 5), 1.2)
    vv_smooth = cv2.GaussianBlur(vv_db, (5, 5), 1.2)

    vh_p2, vh_p98 = vh_stats_db["p2"], vh_stats_db["p98"]
    vv_p2, vv_p98 = vv_stats_db["p2"], vv_stats_db["p98"]

    vh_norm = np.clip((vh_smooth - vh_p2) / (vh_p98 - vh_p2 + 1e-6), 0.0, 1.0)
    vv_norm = np.clip((vv_smooth - vv_p2) / (vv_p98 - vv_p2 + 1e-6), 0.0, 1.0)

    # =========================================================================
    # 4. VV / VH Fusion & Dark SAR Candidate Heuristic
    # =========================================================================
    # VV is primary co-pol ocean backscatter indicator; VH adds cross-pol dampening coherence
    vv_vh_ratio = (vv_norm + 0.01) / (vh_norm + 0.01)
    vv_vh_diff = vv_norm - vh_norm
    combined_dark_score = 0.65 * (1.0 - vv_norm) + 0.35 * (1.0 - vh_norm)

    # =========================================================================
    # 5. Candidate Dark-Region Detection via Local Adaptive Thresholding
    # =========================================================================
    # Estimate local ocean background using wide spatial box filter (kernel ~81x81 pixels)
    bg_box = cv2.boxFilter(combined_dark_score, -1, (81, 81))
    local_contrast_map = combined_dark_score - bg_box

    # Combined candidate criterion: high dark dampening + significantly darker than local ocean surroundings
    initial_dark_candidate = (combined_dark_score > 0.68) & (local_contrast_map > 0.04)

    # =========================================================================
    # 6. Conservative Morphological Cleanup
    # - Small opening to eliminate speckle noise
    # - Small closing to bridge micro-gaps while preserving natural irregular boundary
    # =========================================================================
    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    cleaned_morph = cv2.morphologyEx(initial_dark_candidate.astype(np.uint8), cv2.MORPH_OPEN, k_open)
    cleaned_morph = cv2.morphologyEx(cleaned_morph, cv2.MORPH_CLOSE, k_close)

    # =========================================================================
    # 7. Connected Component Analysis & Physics-Based Ranking
    # =========================================================================
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned_morph, connectivity=8)

    components = []
    h_img, w_img = cleaned_morph.shape

    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < min_area_pixels:
            continue
        x, y, w, h = stats[label, :4]
        cx, cy = centroids[label]

        comp_mask = (labels == label).astype(np.uint8)

        # Perimeter via external contours
        contours, _ = cv2.findContours(comp_mask[y:y+h, x:x+w], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        perimeter = float(sum(cv2.arcLength(cnt, True) for cnt in contours)) if contours else 1.0

        compactness = float((4.0 * math.pi * area) / (perimeter ** 2 + 1e-6))
        aspect_ratio = float(max(w, h) / max(min(w, h), 1))

        comp_vv_db = vv_db[labels == label]
        mean_backscatter = float(np.mean(comp_vv_db))

        # Local surrounding ring contrast (dilate - original)
        y0, y1 = max(0, y - 10), min(h_img, y + h + 10)
        x0, x1 = max(0, x - 10), min(w_img, x + w + 10)
        sub_mask = comp_mask[y0:y1, x0:x1]
        dilated = cv2.dilate(sub_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        ring = (dilated > 0) & (sub_mask == 0)
        sub_vv_db = vv_db[y0:y1, x0:x1]
        bg_val = float(np.mean(sub_vv_db[ring])) if np.any(ring) else mean_backscatter + 3.0
        local_contrast = float(bg_val - mean_backscatter)

        # Multi-factor ranking: high contrast, elongated structure, irregular boundary
        elongation_factor = min(aspect_ratio, 8.0)
        irregularity = 1.0 / (compactness + 0.05)
        rank_score = float(local_contrast * math.log10(area) * math.sqrt(elongation_factor) * irregularity)

        components.append({
            "label": label,
            "area": area,
            "bbox": (int(y), int(x), int(h), int(w)),
            "centroid": (round(float(cy), 1), round(float(cx), 1)),
            "aspect_ratio": round(aspect_ratio, 2),
            "perimeter": round(perimeter, 1),
            "compactness": round(compactness, 4),
            "mean_backscatter_db": round(mean_backscatter, 2),
            "local_contrast_db": round(local_contrast, 2),
            "rank_score": round(rank_score, 2)
        })

    # Sort components by rank score descending
    components.sort(key=lambda c: c["rank_score"], reverse=True)

    # Select strongest candidate components
    # Retain top candidates or candidates passing rank score threshold >= 300
    top_candidates_list = [c for c in components if c["rank_score"] >= 300.0]
    if len(top_candidates_list) < top_components:
        selected_components = components[:top_components]
    else:
        selected_components = top_candidates_list[:top_components]

    selected_labels = {c["label"] for c in selected_components}

    # Generate final binary candidate mask
    final_mask = np.isin(labels, list(selected_labels)).astype(np.uint8)

    # Compute overall candidate mask statistics
    candidate_pixel_count = int(np.count_nonzero(final_mask))
    valid_ocean_pixels = int(np.count_nonzero(vv_raw > 0))
    candidate_pct = (candidate_pixel_count / max(valid_ocean_pixels, 1)) * 100.0

    if candidate_pixel_count > 0:
        mask_rows, mask_cols = np.where(final_mask > 0)
        overall_bbox = (int(mask_rows.min()), int(mask_cols.min()), int(mask_rows.max()), int(mask_cols.max()))
        overall_centroid = (round(float(mask_rows.mean()), 1), round(float(mask_cols.mean()), 1))
    else:
        overall_bbox = (0, 0, 0, 0)
        overall_centroid = (0.0, 0.0)

    # =========================================================================
    # 8. Save GeoTIFF Candidate Mask (Preserving CRS / GCPs / Dimensions)
    # =========================================================================
    mask_tif_path = out_path / "candidate_mask.tif"
    with rasterio.open(str(mask_tif_path), "w", **mask_profile) as dst:
        dst.write(final_mask, 1)
        if effective_gcps:
            dst.gcps = (effective_gcps, effective_gcp_crs)
    print(f"[GeoTIFF Saved] {mask_tif_path}")

    # =========================================================================
    # 9. Generate Individual Visualizations
    # =========================================================================
    print("Generating individual visual outputs...")

    def save_plot(img_data: np.ndarray, title: str, filename: str, cmap: str = "gray", vmin=None, vmax=None, colorbar_label: Optional[str] = None):
        fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
        im = ax.imshow(img_data, cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=12, pad=10, fontweight="bold")
        ax.set_xlabel("Range / Column (pixels)", fontsize=9)
        ax.set_ylabel("Azimuth / Row (pixels)", fontsize=9)
        ax.tick_params(labelsize=8)
        if colorbar_label:
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label(colorbar_label, fontsize=9)
            cbar.ax.tick_params(labelsize=8)
        plt.tight_layout()
        filepath = out_path / filename
        fig.savefig(str(filepath), bbox_inches="tight")
        plt.close(fig)
        return filepath

    # 01. VH RAW
    save_plot(vh_raw, "01. Sentinel-1 SAR - RAW VH (Linear DN Amplitude)", "01_vh_raw.png", cmap="gray")
    
    # 02. VV RAW
    save_plot(vv_raw, "02. Sentinel-1 SAR - RAW VV (Linear DN Amplitude)", "02_vv_raw.png", cmap="gray")

    # 03. VH dB
    save_plot(vh_db, "03. Sentinel-1 SAR - VH Calibrated (Decibels / dB)", "03_vh_db.png", cmap="viridis",
              vmin=vh_p2, vmax=vh_p98, colorbar_label="Calibrated Backscatter (dB)")

    # 04. VV dB
    save_plot(vv_db, "04. Sentinel-1 SAR - VV Calibrated (Decibels / dB)", "04_vv_db.png", cmap="viridis",
              vmin=vv_p2, vmax=vv_p98, colorbar_label="Calibrated Backscatter (dB)")

    # 05. VH Normalized
    save_plot(vh_norm, "05. Robust Normalized VH [p2-p98 Clipped, 0-1 Range]", "05_vh_normalized.png", cmap="gray", vmin=0, vmax=1)

    # 06. VV Normalized
    save_plot(vv_norm, "06. Robust Normalized VV [p2-p98 Clipped, 0-1 Range]", "06_vv_normalized.png", cmap="gray", vmin=0, vmax=1)

    # 07. Dark Candidate Map
    save_plot(combined_dark_score, "07. Dark-Region Candidate Score Map (VV/VH Fusion Heuristic)", "07_dark_candidate.png",
              cmap="inferno", vmin=0, vmax=1, colorbar_label="Dark Dampening Score [0 - 1]")

    # 08. Cleaned Candidate Mask
    save_plot(final_mask * 255, f"08. Cleaned Dark Candidate Mask ({len(selected_components)} Selected Components)", "08_cleaned_mask.png",
              cmap="bone", vmin=0, vmax=255)

    # 09. Final SAR Image + Mask Overlay
    print("Generating 09_final_overlay.png...")
    fig, ax = plt.subplots(figsize=(10, 10), dpi=180)
    
    base_display = (vv_norm * 255.0).astype(np.uint8)
    rgb_overlay = cv2.cvtColor(base_display, cv2.COLOR_GRAY2RGB)

    # Apply vivid semi-transparent cyan tint over candidate mask pixels
    cyan_tint = np.array([0, 230, 255], dtype=np.uint8)
    mask_bool = final_mask > 0
    alpha = 0.45
    rgb_overlay[mask_bool] = (
        (1.0 - alpha) * rgb_overlay[mask_bool] + alpha * cyan_tint
    ).astype(np.uint8)

    # Draw sharp candidate contour boundaries
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(rgb_overlay, contours, -1, (255, 50, 50), 2)

    ax.imshow(rgb_overlay)

    # Draw bounding boxes and centroids for selected components
    for idx, comp in enumerate(selected_components):
        y, x, h, w = comp["bbox"]
        cy, cx = comp["centroid"]
        rect = Rectangle((x, y), w, h, linewidth=1.5, edgecolor="#00FFAA", facecolor="none", linestyle="--")
        ax.add_patch(rect)
        ax.plot(cx, cy, marker="+", color="#FFFF00", markersize=12, markeredgewidth=2)
        ax.text(
            x, max(0, y - 12),
            f"Candidate #{idx+1} [A={comp['area']:,}px, \u0394={comp['local_contrast_db']}dB, AR={comp['aspect_ratio']}]",
            color="#FFFFFF", fontsize=8, fontweight="bold",
            bbox=dict(facecolor="#102030", edgecolor="#00FFAA", boxstyle="round,pad=0.3", alpha=0.85)
        )

    ax.set_title(
        "VARUNA SAR Analysis: Sentinel-1 VV + Candidate Segmentation Overlay\n"
        "[PROTOTYPE CANDIDATE MASK - NOT AN AI/U-NET PREDICTION]",
        fontsize=11, fontweight="bold", pad=12, color="#111827"
    )
    ax.set_xlabel("Range / Column (pixels)", fontsize=9)
    ax.set_ylabel("Azimuth / Row (pixels)", fontsize=9)

    legend_elements = [
        Line2D([0], [0], color="#FF3232", lw=2, label="Candidate Boundary (Morphological Contour)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#00E6FF", markersize=10, label="Dark Backscatter Dampening Region"),
        Line2D([0], [0], color="#00FFAA", lw=1.5, linestyle="--", label="Component Bounding Box"),
        Line2D([0], [0], marker="+", color="#FFFF00", markersize=10, markeredgewidth=2, lw=0, label="Component Centroid")
    ]
    ax.legend(handles=legend_elements, loc="upper right", framealpha=0.9, facecolor="#1F2937", labelcolor="#F9FAFB", fontsize=8)

    overlay_path = out_path / "09_final_overlay.png"
    fig.savefig(str(overlay_path), bbox_inches="tight")
    plt.close(fig)

    # =========================================================================
    # 10. Composite Pipeline Figure (10_processing_pipeline.png)
    # =========================================================================
    print("Generating 10_processing_pipeline.png...")
    fig = plt.figure(figsize=(16, 20), dpi=150)
    plt.subplots_adjust(hspace=0.25, wspace=0.15)

    gs = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.0, 1.0, 1.35])

    # Row 1: RAW VH | RAW VV
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(vh_raw, cmap="gray")
    ax1.set_title("1. RAW Sentinel-1 VH (Linear DN Amplitude)", fontsize=11, fontweight="bold")
    ax1.tick_params(labelsize=8)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(vv_raw, cmap="gray")
    ax2.set_title("2. RAW Sentinel-1 VV (Linear DN Amplitude)", fontsize=11, fontweight="bold")
    ax2.tick_params(labelsize=8)

    # Row 2: VH dB Normalized | VV dB Normalized
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.imshow(vh_norm, cmap="gray", vmin=0, vmax=1)
    ax3.set_title(f"3. VH \u2192 dB Normalized [p2={vh_p2:.1f}, p98={vh_p98:.1f} dB]", fontsize=11, fontweight="bold")
    ax3.tick_params(labelsize=8)

    ax4 = fig.add_subplot(gs[1, 1])
    ax4.imshow(vv_norm, cmap="gray", vmin=0, vmax=1)
    ax4.set_title(f"4. VV \u2192 dB Normalized [p2={vv_p2:.1f}, p98={vv_p98:.1f} dB]", fontsize=11, fontweight="bold")
    ax4.tick_params(labelsize=8)

    # Row 3: Dark Candidate Score | Cleaned Candidate Mask
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.imshow(combined_dark_score, cmap="inferno", vmin=0, vmax=1)
    ax5.set_title("5. Dark-Region Candidate Score (Adaptive Heuristic)", fontsize=11, fontweight="bold")
    ax5.tick_params(labelsize=8)

    ax6 = fig.add_subplot(gs[2, 1])
    ax6.imshow(final_mask, cmap="bone")
    ax6.set_title(f"6. Cleaned Candidate Mask ({len(selected_components)} Strongest Candidates)", fontsize=11, fontweight="bold")
    ax6.tick_params(labelsize=8)

    # Row 4: Final SAR Image + Mask Overlay (Spanning full width)
    ax7 = fig.add_subplot(gs[3, :])
    ax7.imshow(rgb_overlay)
    for idx, comp in enumerate(selected_components):
        y, x, h, w = comp["bbox"]
        cy, cx = comp["centroid"]
        rect = Rectangle((x, y), w, h, linewidth=1.5, edgecolor="#00FFAA", facecolor="none", linestyle="--")
        ax7.add_patch(rect)
        ax7.plot(cx, cy, marker="+", color="#FFFF00", markersize=10, markeredgewidth=2)
        ax7.text(
            x + 5, y + 25,
            f"Candidate #{idx+1}: Area={comp['area']:,}px | \u0394={comp['local_contrast_db']}dB | AR={comp['aspect_ratio']}",
            color="#FFFFFF", fontsize=9, fontweight="bold",
            bbox=dict(facecolor="#0B132B", edgecolor="#00FFAA", boxstyle="round,pad=0.3", alpha=0.9)
        )

    ax7.set_title(
        "7. Final SAR Image + Candidate Segmentation Mask Overlay\n"
        "[Prototype SAR Candidate Mask - Physics/Texture Derived - NOT an AI / U-Net Prediction]",
        fontsize=12, fontweight="bold", pad=10
    )
    ax7.tick_params(labelsize=8)
    ax7.legend(handles=legend_elements, loc="upper right", framealpha=0.9, facecolor="#1F2937", labelcolor="#F9FAFB", fontsize=9)

    pipeline_path = out_path / "10_processing_pipeline.png"
    fig.savefig(str(pipeline_path), bbox_inches="tight")
    plt.close(fig)
    print(f"[Composite Pipeline Saved] {pipeline_path}")

    # =========================================================================
    # 11. Format & Print Required Statistics Report
    # =========================================================================
    report = f"""
=============================================================================
VARUNA SAR EXPERIMENT: PROCESSING & STATISTICAL REPORT
=============================================================================

INPUT
------
VH dimensions: {vh_dim[1]} x {vh_dim[0]}
VV dimensions: {vv_dim[1]} x {vv_dim[0]}
dtype: {vh_dtype}
CRS: {vh_crs}
GCP count if available: {gcp_count} (CRS: {gcp_crs_str})

VH RAW
------
min:  {vh_stats_raw['min']:.2f}
max:  {vh_stats_raw['max']:.2f}
mean: {vh_stats_raw['mean']:.2f}
p2:   {vh_stats_raw['p2']:.2f}
p50:  {vh_stats_raw['p50']:.2f}
p98:  {vh_stats_raw['p98']:.2f}

VV RAW
------
min:  {vv_stats_raw['min']:.2f}
max:  {vv_stats_raw['max']:.2f}
mean: {vv_stats_raw['mean']:.2f}
p2:   {vv_stats_raw['p2']:.2f}
p50:  {vv_stats_raw['p50']:.2f}
p98:  {vv_stats_raw['p98']:.2f}

VH dB
------
min:  {vh_stats_db['min']:.2f}
max:  {vh_stats_db['max']:.2f}
mean: {vh_stats_db['mean']:.2f}
p2:   {vh_stats_db['p2']:.2f}
p50:  {vh_stats_db['p50']:.2f}
p98:  {vh_stats_db['p98']:.2f}

VV dB
------
min:  {vv_stats_db['min']:.2f}
max:  {vv_stats_db['max']:.2f}
mean: {vv_stats_db['mean']:.2f}
p2:   {vv_stats_db['p2']:.2f}
p50:  {vv_stats_db['p50']:.2f}
p98:  {vv_stats_db['p98']:.2f}

CANDIDATE MASK
--------------
number of connected components: {num_labels - 1}
selected component count:       {len(selected_components)}
candidate pixel count:          {candidate_pixel_count:,}
candidate percentage of valid ocean pixels: {candidate_pct:.3f}%
bounding box:                   {overall_bbox}
centroid:                       {overall_centroid}
"""
    print(report)

    with open(out_path / "summary_report.txt", "w") as f:
        f.write(report)

    return {
        "report": report,
        "selected_components": selected_components,
        "candidate_pixel_count": candidate_pixel_count,
        "candidate_pct": candidate_pct,
        "overall_bbox": overall_bbox,
        "overall_centroid": overall_centroid,
        "outputs": {
            "vh_raw": str(out_path / "01_vh_raw.png"),
            "vv_raw": str(out_path / "02_vv_raw.png"),
            "vh_db": str(out_path / "03_vh_db.png"),
            "vv_db": str(out_path / "04_vv_db.png"),
            "vh_norm": str(out_path / "05_vh_normalized.png"),
            "vv_norm": str(out_path / "06_vv_normalized.png"),
            "dark_candidate": str(out_path / "07_dark_candidate.png"),
            "cleaned_mask": str(out_path / "08_cleaned_mask.png"),
            "final_overlay": str(overlay_path),
            "pipeline": str(pipeline_path),
            "geotiff_mask": str(mask_tif_path)
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="VARUNA SAR Image Processing & Dark-Feature Candidate Visualization Experiment"
    )
    parser.add_argument("--vh", type=str, default=None, help="Path to input VH TIFF (defaults to satellite-data/001.tiff)")
    parser.add_argument("--vv", type=str, default=None, help="Path to input VV TIFF (defaults to satellite-data/002.tiff)")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save output images and GeoTIFF")
    parser.add_argument("--top-candidates", type=int, default=2, help="Number of strongest candidate components to retain")
    parser.add_argument("--min-area", type=int, default=1000, help="Minimum pixel area for connected components")

    args = parser.parse_args()

    run_experiment(
        vh_path=args.vh,
        vv_path=args.vv,
        output_dir=args.output_dir,
        top_components=args.top_candidates,
        min_area_pixels=args.min_area
    )


if __name__ == "__main__":
    main()
