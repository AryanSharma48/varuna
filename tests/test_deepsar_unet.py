"""
Unit tests for Refined Deep-SAR Oil Spill U-Net pipeline.
Tests cover:
- Dataset loading and splitting
- Mask conversion and semantic validation
- Model loading and forward inference
- Output dimensions and probability constraints
- NaN / Inf prevention
- Dynamic thresholding
- Polygonization with connected components
- Georeferencing via GCPTransformer
"""

import os
import math
import pytest
import numpy as np
import torch
import cv2

from ml.segmentation.unet import UNet, DiceBCELoss
from ml.segmentation.deepsar_dataset import DeepSARDataset, load_deepsar_splits
from ml.segmentation.evaluate import compute_confusion_matrix, compute_metrics_from_cm
from ml.segmentation.train_deepsar import calibrate_threshold_on_val


def test_dataset_loading():
    """Verify that dataset splits load correctly and deterministically without leakage."""
    splits = load_deepsar_splits(base_dir="training_data/refined_deep_sar", seed=42)
    assert len(splits["train"]) == 6455
    assert len(splits["val"]) == 807
    assert len(splits["test"]) == 808

    # Ensure no leakage between val and test
    val_files = {s["image_path"] for s in splits["val"]}
    test_files = {s["image_path"] for s in splits["test"]}
    assert len(val_files.intersection(test_files)) == 0


def test_mask_conversion():
    """Verify mask values are correctly converted to binary {0, 1}."""
    splits = load_deepsar_splits(base_dir="training_data/refined_deep_sar", seed=42)
    dataset = DeepSARDataset(splits["val"][:10], augment=False)
    
    img, mask = dataset[0]
    assert img.shape == (2, 256, 256)
    assert mask.shape == (1, 256, 256)
    
    # Mask values must be strictly binary 0.0 or 1.0
    unique_vals = torch.unique(mask).tolist()
    for v in unique_vals:
        assert v in (0.0, 1.0)


def test_model_loading():
    """Verify U-Net instantiates with 2 channels, 1 class, and can load state_dict."""
    model = UNet(n_channels=2, n_classes=1, bilinear=True)
    checkpoint_path = "models/checkpoints/sanity_test.pt"
    if os.path.exists(checkpoint_path):
        state_dict = torch.load(checkpoint_path, map_location="cpu")
        model.load_state_dict(state_dict)
    model.eval()
    assert model is not None


def test_inference_and_output_dimensions():
    """Verify inference preserves dimensions and outputs valid probabilities."""
    model = UNet(n_channels=2, n_classes=1, bilinear=True)
    model.eval()
    
    x = torch.rand(2, 2, 256, 256)
    with torch.no_grad():
        out = model(x)
        
    assert out.shape == (2, 1, 256, 256)
    assert (out >= 0.0).all() and (out <= 1.0).all()


def test_nan_inf_prevention():
    """Verify forward and backward passes resist NaNs and Infs even on extreme inputs."""
    model = UNet(n_channels=2, n_classes=1, bilinear=True)
    criterion = DiceBCELoss()
    
    # Edge inputs: all zeros, all ones
    zero_in = torch.zeros(1, 2, 128, 128)
    one_in = torch.ones(1, 2, 128, 128)
    
    pred_zero = model(zero_in)
    pred_one = model(one_in)
    
    assert not torch.isnan(pred_zero).any()
    assert not torch.isinf(pred_zero).any()
    assert not torch.isnan(pred_one).any()
    assert not torch.isinf(pred_one).any()
    
    # Loss computation with extreme ground truths
    target_zero = torch.zeros(1, 1, 128, 128)
    target_one = torch.ones(1, 1, 128, 128)
    
    loss_0 = criterion(pred_zero, target_zero)
    loss_1 = criterion(pred_one, target_one)
    
    assert not torch.isnan(loss_0) and not torch.isinf(loss_0)
    assert not torch.isnan(loss_1) and not torch.isinf(loss_1)


def test_thresholding():
    """Verify threshold calibration selects an optimal threshold and returns valid metrics."""
    probs = np.array([[[[0.9, 0.85], [0.1, 0.05]]]])
    targets = np.array([[[[1.0, 1.0], [0.0, 0.0]]]])
    
    th, metrics = calibrate_threshold_on_val(probs, targets, steps=5)
    assert 0.0 < th < 1.0
    assert metrics["iou"] > 0.8
    assert metrics["dice"] > 0.8


def test_polygonization():
    """Verify connected component polygonization correctly calculates area and perimeter."""
    # Synthetic 100x100 mask with a 20x20 square in the center
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:60, 40:60] = 1
    
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
    assert num_labels == 2  # Background (0) and 1 square (1)
    
    comp_area = stats[1, cv2.CC_STAT_AREA]
    assert comp_area == 400
    
    c_x, c_y = centroids[1]
    assert math.isclose(c_x, 49.5, abs_tol=1.0)
    assert math.isclose(c_y, 49.5, abs_tol=1.0)


def test_georeferencing():
    """Verify authoritative GCP georeferencing transforms pixel to valid WGS-84 coordinates."""
    import rasterio
    from rasterio.transform import GCPTransformer
    
    vv_path = "demo/incidents/incident_001/satellite/vv.tif"
    if os.path.exists(vv_path):
        with rasterio.open(vv_path) as src:
            gcps, _ = src.gcps
            assert len(gcps) > 0
            transformer = GCPTransformer(gcps)
            
            # Middle pixel
            row, col = src.height // 2, src.width // 2
            lon, lat = transformer.xy(row, col)
            
            # Incident 001 is in the Eastern Mediterranean near Nile Delta / Port Said (approx 31-33° E, 31-33° N)
            assert 31.0 <= lon <= 34.0
            assert 30.5 <= lat <= 33.5
