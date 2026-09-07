"""
Unit tests for the pretrained oil-spill segmentation model adapter.
Model: TheArchitect416/oil-spill-segmentation-model (U-Net with ResNet34 encoder)
"""

import os
import pytest
import numpy as np
import rasterio
from rasterio.transform import GCPTransformer
from ml.segmentation.pretrained_oilspill import (
    load_pretrained_model,
    predict_oil_mask,
    polygonize_mask,
    preprocess_sar_composite,
    DEFAULT_MODEL_PATH
)

@pytest.mark.skipif(not os.path.exists(DEFAULT_MODEL_PATH), reason="Pretrained RGB checkpoint not downloaded")
def test_pretrained_checkpoint_loads():
    """Verify that the pretrained model checkpoint exists and loads without error."""
    assert os.path.exists(DEFAULT_MODEL_PATH), f"Checkpoint not found at {DEFAULT_MODEL_PATH}"
    model = load_pretrained_model(DEFAULT_MODEL_PATH, device="cpu")
    assert model is not None
    param_count = sum(p.numel() for p in model.parameters())
    assert param_count > 20_000_000, f"Unexpected parameter count: {param_count}"

def test_sar_preprocessing():
    """Verify 3-channel composite construction and normalization."""
    vv = np.random.uniform(10, 200, (256, 256)).astype(np.float32)
    vh = np.random.uniform(5, 100, (256, 256)).astype(np.float32)
    
    composite = preprocess_sar_composite(vv, vh)
    assert composite.shape == (256, 256, 3)
    assert composite.dtype == np.float32
    assert not np.isnan(composite).any(), "Preprocessing generated NaNs"
    assert not np.isinf(composite).any(), "Preprocessing generated Infs"

@pytest.mark.skipif(not os.path.exists(DEFAULT_MODEL_PATH), reason="Pretrained RGB checkpoint not downloaded")
def test_pretrained_inference_and_mask():
    """Verify inference on small patch produces valid probability mask matching input dimensions."""
    vv = np.random.uniform(10, 200, (256, 256)).astype(np.float32)
    vh = np.random.uniform(5, 100, (256, 256)).astype(np.float32)
    
    prob_mask, binary_mask, stats = predict_oil_mask(vv, vh, model_path=DEFAULT_MODEL_PATH, tile_size=256, threshold=0.5)
    
    # Check shape match
    assert prob_mask.shape == (256, 256), f"Expected shape (256, 256), got {prob_mask.shape}"
    assert binary_mask.shape == (256, 256), f"Expected shape (256, 256), got {binary_mask.shape}"
    
    # Check value bounds & absence of NaN/Inf
    assert not np.isnan(prob_mask).any(), "Prob mask contains NaNs"
    assert not np.isinf(prob_mask).any(), "Prob mask contains Infs"
    assert 0.0 <= np.min(prob_mask) <= 1.0, f"Min prob out of bounds: {np.min(prob_mask)}"
    assert 0.0 <= np.max(prob_mask) <= 1.0, f"Max prob out of bounds: {np.max(prob_mask)}"
    
    assert "min" in stats and "max" in stats and "mean" in stats

def test_polygonization_succeeds():
    """Verify polygonization succeeds on a non-empty binary mask."""
    vv_path = os.path.join("demo", "incidents", "incident_001", "satellite", "vv.tif")
    assert os.path.exists(vv_path), "Demo incident raster not found"
    
    with rasterio.open(vv_path) as src:
        gcps, _ = src.gcps
        transformer = GCPTransformer(gcps)
        
    binary_mask = np.zeros((500, 500), dtype=np.uint8)
    binary_mask[100:200, 100:200] = 1 # 10,000 px box
    
    geojson_geom, (c_lon, c_lat), area_sqkm, bbox, pixel_count = polygonize_mask(binary_mask, transformer, min_area_pixels=50)
    
    assert geojson_geom is not None
    assert geojson_geom["type"] in ("Polygon", "MultiPolygon")
    assert pixel_count > 0
    assert c_lon != 0.0 and c_lat != 0.0
    assert area_sqkm > 0.0
    assert "min_lon" in bbox and "max_lon" in bbox
