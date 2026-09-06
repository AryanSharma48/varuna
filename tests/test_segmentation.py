import pytest
import os
import numpy as np
import torch
import rasterio
from rasterio.control import GroundControlPoint
from rasterio.crs import CRS
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from ml.segmentation.config import SegmentationConfig
from ml.segmentation.dataset import SceneIterableDataset
from ml.segmentation.unet import UNet
from ml.segmentation.inference import predict_scene_to_tiff

def create_synthetic_tiff_with_gcps(data: np.ndarray, path: str):
    gcps = [
        GroundControlPoint(row=0, col=0, x=76.0, y=12.0),
        GroundControlPoint(row=0, col=100, x=77.0, y=12.0),
        GroundControlPoint(row=100, col=0, x=76.0, y=11.0),
        GroundControlPoint(row=100, col=100, x=77.0, y=11.0)
    ]
    with rasterio.open(
        path, 'w', driver='GTiff',
        height=data.shape[0], width=data.shape[1], count=1,
        dtype=data.dtype, crs=None,
    ) as dst:
        dst.write(data, 1)
        dst.gcps = (gcps, CRS.from_epsg(4326))

@pytest.fixture
def temp_scene_tiffs(tmp_path):
    vv_path = tmp_path / "synthetic_vv_scene.tiff"
    vh_path = tmp_path / "synthetic_vh_scene.tiff"
    
    # 256x256 image
    vv_data = np.random.randint(0, 1000, (256, 256)).astype(np.uint16)
    vh_data = np.random.randint(0, 500, (256, 256)).astype(np.uint16)
    
    create_synthetic_tiff_with_gcps(vv_data, str(vv_path))
    create_synthetic_tiff_with_gcps(vh_data, str(vh_path))
            
    return str(vv_path), str(vh_path)

def test_scene_iterable_dataset(temp_scene_tiffs):
    vv, vh = temp_scene_tiffs
    config = SegmentationConfig(tile_size=128, overlap=0, batch_size=2)
    dataset = SceneIterableDataset(vv, vh, config)
    
    iterator = iter(dataset)
    first_item = next(iterator)
    
    tensor = first_item["tensor"]
    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (2, 128, 128)
    assert "geographic_metadata" in first_item
    assert first_item["geographic_metadata"]["crs"] == "EPSG:4326"

def test_unet_shapes():
    model = UNet(n_channels=2, n_classes=1, bilinear=True)
    # Batch size 2, 2 channels, 128x128
    dummy_input = torch.randn(2, 2, 128, 128)
    output = model(dummy_input)
    assert output.shape == (2, 1, 128, 128)

def test_predict_scene_missing_checkpoint_raises(temp_scene_tiffs, tmp_path):
    vv, vh = temp_scene_tiffs
    out_mask = tmp_path / "output_mask.tiff"
    config = SegmentationConfig(tile_size=128, overlap=32, batch_size=2)
    
    # Missing model path must raise RuntimeError for safety
    with pytest.raises(RuntimeError, match="Missing model checkpoint"):
        predict_scene_to_tiff(vv, vh, str(out_mask), config, model_path=None)

def test_predict_scene_to_tiff_with_checkpoint(temp_scene_tiffs, tmp_path):
    vv, vh = temp_scene_tiffs
    out_mask = tmp_path / "output_mask.tiff"
    model_path = tmp_path / "test_model.pth"
    
    # Create synthetic checkpoint
    model = UNet(n_channels=2, n_classes=1, bilinear=True)
    torch.save(model.state_dict(), str(model_path))
    
    config = SegmentationConfig(tile_size=128, overlap=32, batch_size=2, threshold=0.5)
    result = predict_scene_to_tiff(vv, vh, str(out_mask), config, model_path=str(model_path))
    
    assert result["status"] == "success"
    assert os.path.exists(str(out_mask))
    
    # Verify output TIFF properties
    with rasterio.open(str(out_mask)) as src:
        assert src.width == 256
        assert src.height == 256
        assert src.count == 1
        assert src.dtypes[0] == 'uint8'
        
        # Verify GCP preservation
        gcps, gcp_crs = src.gcps
        assert gcps is not None
        assert len(gcps) == 4
        assert str(gcp_crs) == "EPSG:4326"
        
        data = src.read(1)
        assert data.shape == (256, 256)
        assert np.max(data) <= 1
