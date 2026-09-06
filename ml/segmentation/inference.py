import os
import json
import argparse
from pathlib import Path
from typing import Optional, Any, Dict
import numpy as np
import torch
import rasterio
from rasterio.windows import Window
from torch.utils.data import DataLoader

from ml.segmentation.config import SegmentationConfig
from ml.segmentation.dataset import SceneIterableDataset
from ml.segmentation.unet import UNet


def predict_scene_to_tiff(
    vv_path: str,
    vh_path: str,
    out_mask_path: str,
    config: Optional[SegmentationConfig] = None,
    model_path: Optional[str] = None,
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Runs memory-safe end-to-end inference on the massive Copernicus SAR scene.
    Reads chunk by chunk, passes through trained U-Net, and writes to disk immediately.
    
    SAFETY REQUIREMENT:
      A valid, trained model checkpoint is strictly MANDATORY.
      Untrained or random weights will raise a clear RuntimeError.
    """
    cfg = config or SegmentationConfig()
    
    # 1. Enforce Mandatory Trained Checkpoint
    if not model_path or not os.path.exists(model_path):
        raise RuntimeError(
            f"Missing model checkpoint: '{model_path}'. "
            "A valid trained model checkpoint (.pth) is mandatory for Copernicus scene inference. "
            "Never execute untrained or random weights on real satellite scenes."
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 2. Determine Decision Threshold (use calibrated threshold if metadata exists)
    applied_threshold = threshold if threshold is not None else cfg.threshold
    metadata_candidates = [
        Path(model_path).parent / "model_metadata.json",
        Path(cfg.metadata_save_path)
    ]
    for meta_file in metadata_candidates:
        if threshold is None and meta_file.exists():
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                    if "calibrated_threshold" in meta:
                        applied_threshold = float(meta["calibrated_threshold"])
                        print(f"Loaded calibrated threshold {applied_threshold:.4f} from {meta_file}")
                        break
            except Exception:
                pass

    # 3. Load Trained U-Net Model
    model = UNet(
        n_channels=cfg.in_channels,
        n_classes=cfg.out_classes,
        bilinear=cfg.bilinear
    )
    
    try:
        state_dict = torch.load(model_path, map_location=device)
        model.load_state_dict(state_dict)
    except Exception as e:
        raise RuntimeError(f"Failed to load trained model checkpoint from '{model_path}': {e}")
        
    model.to(device)
    model.eval()

    # 4. Verify input rasters exist
    if not os.path.exists(vv_path):
        raise FileNotFoundError(f"VV TIFF not found: {vv_path}")
    if not os.path.exists(vh_path):
        raise FileNotFoundError(f"VH TIFF not found: {vh_path}")

    # 5. Create dataset and loader
    dataset = SceneIterableDataset(vv_path, vh_path, cfg)
    dataloader = DataLoader(dataset, batch_size=cfg.batch_size, shuffle=False)

    # 6. Extract source metadata to preserve exact geolocation (GCPs, CRS, dimensions)
    with rasterio.open(vv_path) as vv_src:
        profile = vv_src.profile.copy()
        gcps, gcp_crs = vv_src.gcps
        src_width = vv_src.width
        src_height = vv_src.height

    # Update profile for binary output mask GeoTIFF
    profile.update(
        dtype=rasterio.uint8,
        count=1,
        compress='lzw',
        nodata=0
    )

    Path(out_mask_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"Executing disk-backed scene inference writing to: {out_mask_path}")

    # Create destination file and write GCPs
    with rasterio.open(out_mask_path, 'w', **profile) as out_dst:
        if gcps and gcp_crs:
            out_dst.gcps = (gcps, gcp_crs)

    total_slick_pixels = 0

    # 7. Tiled memory-safe forward pass and disk writing
    with rasterio.open(out_mask_path, 'r+') as out_dst:
        with torch.no_grad():
            for batch in dataloader:
                # Shape: [B, 2, H, W]
                tensors = batch["tensor"].to(device)
                b_size = tensors.size(0)

                # Shape: [B, 1, H, W]
                probs = model(tensors)

                # Apply calibrated threshold
                binary_masks = (probs >= applied_threshold).squeeze(1).cpu().numpy().astype(np.uint8)

                # Overlap-aware disk-backed update
                for i in range(b_size):
                    col_off = int(batch["window"][0][i])
                    row_off = int(batch["window"][1][i])
                    width = int(batch["window"][2][i])
                    height = int(batch["window"][3][i])

                    valid_mask = binary_masks[i, :height, :width]
                    write_window = Window(col_off=col_off, row_off=row_off, width=width, height=height)

                    existing_data = out_dst.read(1, window=write_window)
                    combined_mask = np.maximum(existing_data, valid_mask)
                    out_dst.write(combined_mask, 1, window=write_window)

    # Compute quick non-zero pixel count from block reads
    with rasterio.open(out_mask_path, 'r') as mask_check:
        for _, win in mask_check.block_windows(1):
            block = mask_check.read(1, window=win)
            total_slick_pixels += int(np.count_nonzero(block))

    print(f"Scene inference complete. Total detected spill pixels: {total_slick_pixels}")

    return {
        "status": "success",
        "output_mask_path": out_mask_path,
        "total_slick_pixels": total_slick_pixels,
        "applied_threshold": applied_threshold,
        "model_path": model_path,
        "dimensions": (src_width, src_height),
        "device": str(device)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Memory-Safe Supervised U-Net Inference on Copernicus SAR Scene")
    parser.add_argument("--vv", type=str, required=True, help="Path to Sentinel-1 VV GeoTIFF")
    parser.add_argument("--vh", type=str, required=True, help="Path to Sentinel-1 VH GeoTIFF")
    parser.add_argument("--model-path", type=str, required=True, help="Path to trained .pth U-Net checkpoint")
    parser.add_argument("--output-mask", type=str, default="artifacts/copernicus_spill_mask.tiff", help="Output GeoTIFF mask path")
    parser.add_argument("--threshold", type=float, default=None, help="Optional decision threshold override")
    args = parser.parse_args()

    cfg = SegmentationConfig()
    try:
        result = predict_scene_to_tiff(
            vv_path=args.vv,
            vh_path=args.vh,
            out_mask_path=args.output_mask,
            config=cfg,
            model_path=args.model_path,
            threshold=args.threshold
        )
        print("Inference completed:", result)
    except Exception as e:
        print(f"INFERENCE ERROR: {e}")
        exit(1)
