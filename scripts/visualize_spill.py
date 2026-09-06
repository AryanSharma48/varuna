import os
import argparse
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import rasterio
from rasterio.windows import Window
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from services.satellite.processor import stretch_array


def create_spill_visualization(
    vv_data: np.ndarray,
    vh_data: np.ndarray,
    mask_data: np.ndarray,
    output_path: str,
    title_suffix: str = "",
    threshold_used: Optional[float] = None
):
    """
    Creates a 4-panel diagnostic visualization:
      [ VV SAR ] | [ VH SAR ] | [ Predicted Mask (Model Output) ] | [ Spill Overlay ]
      
    Clearly annotates the output as model prediction.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 1. Percentile stretch for SAR visualizations
    vv_p2, vv_p98 = np.percentile(vv_data, 2.0), np.percentile(vv_data, 98.0)
    vh_p2, vh_p98 = np.percentile(vh_data, 2.0), np.percentile(vh_data, 98.0)

    vv_vis = stretch_array(vv_data, vv_p2, vv_p98)
    vh_vis = stretch_array(vh_data, vh_p2, vh_p98)
    mask_vis = (mask_data > 0).astype(np.uint8)

    # 2. Construct RGB overlay (VV background + red highlight where mask == 1)
    rgb_overlay = np.stack([vv_vis, vv_vis, vv_vis], axis=-1).astype(np.float32)
    # Blend red: RGB = (255, 30, 30) with 0.55 opacity on mask pixels
    mask_indices = mask_vis > 0
    rgb_overlay[mask_indices, 0] = np.clip(rgb_overlay[mask_indices, 0] * 0.45 + 255 * 0.55, 0, 255)
    rgb_overlay[mask_indices, 1] = np.clip(rgb_overlay[mask_indices, 1] * 0.45 + 20 * 0.55, 0, 255)
    rgb_overlay[mask_indices, 2] = np.clip(rgb_overlay[mask_indices, 2] * 0.45 + 20 * 0.55, 0, 255)
    rgb_overlay = rgb_overlay.astype(np.uint8)

    # 3. Plot 4 panels
    fig, axes = plt.subplots(1, 4, figsize=(20, 5), dpi=150)
    fig.patch.set_facecolor('#111827')

    axes[0].imshow(vv_vis, cmap='gray')
    axes[0].set_title("VV SAR Backscatter", color='white', fontsize=12, fontweight='bold')
    axes[0].axis('off')

    axes[1].imshow(vh_vis, cmap='gray')
    axes[1].set_title("VH SAR Cross-Pol", color='white', fontsize=12, fontweight='bold')
    axes[1].axis('off')

    axes[2].imshow(mask_vis, cmap='hot', vmin=0, vmax=1)
    th_label = f" (Threshold={threshold_used:.2f})" if threshold_used is not None else ""
    axes[2].set_title(f"Predicted Mask [MODEL OUTPUT]{th_label}", color='#f87171', fontsize=12, fontweight='bold')
    axes[2].axis('off')

    axes[3].imshow(rgb_overlay)
    axes[3].set_title("Spill Overlay on SAR Background", color='#38bdf8', fontsize=12, fontweight='bold')
    axes[3].axis('off')

    main_title = f"SAR Oil Spill Segmentation & Verification {title_suffix}".strip()
    plt.suptitle(main_title, color='white', fontsize=14, y=1.02, fontweight='bold')
    plt.tight_layout()

    plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Visualization saved to: {output_path}")


def visualize_from_files(
    vv_path: str,
    vh_path: str,
    mask_path: str,
    output_path: str = "artifacts/spill_visualization.png",
    window: Optional[Tuple[int, int, int, int]] = None,
    threshold_used: Optional[float] = None
):
    """Loads window or full raster from files and generates visualization."""
    with rasterio.open(vv_path) as vv_src, rasterio.open(vh_path) as vh_src, rasterio.open(mask_path) as mask_src:
        if window:
            col_off, row_off, width, height = window
            win = Window(col_off, row_off, width, height)
            vv = vv_src.read(1, window=win).astype(np.float32)
            vh = vh_src.read(1, window=win).astype(np.float32)
            mask = mask_src.read(1, window=win).astype(np.uint8)
        else:
            # If large, read a sample or full if small
            target_size = min(1024, vv_src.width, vv_src.height)
            vv = vv_src.read(1, out_shape=(target_size, target_size)).astype(np.float32)
            vh = vh_src.read(1, out_shape=(target_size, target_size)).astype(np.float32)
            mask = mask_src.read(1, out_shape=(target_size, target_size)).astype(np.uint8)

    create_spill_visualization(
        vv_data=vv,
        vh_data=vh,
        mask_data=mask,
        output_path=output_path,
        threshold_used=threshold_used
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 4-panel SAR Oil Spill Diagnostic Visualization")
    parser.add_argument("--vv", type=str, required=True, help="Path to VV TIFF")
    parser.add_argument("--vh", type=str, required=True, help="Path to VH TIFF")
    parser.add_argument("--mask", type=str, required=True, help="Path to Predicted Mask GeoTIFF")
    parser.add_argument("--output", type=str, default="artifacts/spill_visualization.png", help="Output PNG image path")
    parser.add_argument("--threshold", type=float, default=None, help="Calibrated threshold used")
    args = parser.parse_args()

    visualize_from_files(
        vv_path=args.vv,
        vh_path=args.vh,
        mask_path=args.mask,
        output_path=args.output,
        threshold_used=args.threshold
    )
