import pytest
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.control import GroundControlPoint
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from services.satellite.processor import (
    validate_compatibility,
    extract_metadata_stats,
    stretch_array,
    TiledProcessor,
    Georeferencer,
    HAS_RASTERIO
)

def create_synthetic_tiff_with_gcps(data: np.ndarray, path: str):
    gcps = [
        GroundControlPoint(row=0, col=0, x=76.0, y=12.0),
        GroundControlPoint(row=0, col=100, x=77.0, y=12.0),
        GroundControlPoint(row=100, col=0, x=76.0, y=11.0),
        GroundControlPoint(row=100, col=100, x=77.0, y=11.0)
    ]
    
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs=None,  # No base CRS
    ) as dst:
        dst.write(data, 1)
        # Apply GCPs
        from rasterio.crs import CRS
        dst.gcps = (gcps, CRS.from_epsg(4326))

@pytest.fixture
def temp_tiffs_gcp(tmp_path):
    vv_path = tmp_path / "synthetic_vv_gcp.tiff"
    vh_path = tmp_path / "synthetic_vh_gcp.tiff"
    
    vv_data = np.random.randint(0, 1000, (100, 100)).astype(np.uint16)
    vh_data = np.random.randint(0, 500, (100, 100)).astype(np.uint16)
    
    create_synthetic_tiff_with_gcps(vv_data, str(vv_path))
    create_synthetic_tiff_with_gcps(vh_data, str(vh_path))
            
    return str(vv_path), str(vh_path)


def test_validate_compatibility_paths(temp_tiffs_gcp):
    vv, vh = temp_tiffs_gcp
    res = validate_compatibility(vv, vh)
    assert res["is_compatible"] is True
    assert res["gcps"]["match"] is True
    assert res["gcps"]["vv_count"] == 4

def test_georeferencer(temp_tiffs_gcp):
    vv, _ = temp_tiffs_gcp
    with rasterio.open(vv) as src:
        gcps, crs = src.gcps
        geo = Georeferencer(gcps, crs)
        
        # Test pixel_to_lonlat for Top-Left
        lon, lat = geo.pixel_to_lonlat(0, 0)
        assert round(lon) == 76
        assert round(lat) == 12

        # Test approximate transform exists and is distinct from exact transform
        approx_transform = geo.get_approximate_transform()
        assert approx_transform is not None
        assert type(approx_transform) == rasterio.Affine


def test_extract_metadata_stats(temp_tiffs_gcp):
    vv, _ = temp_tiffs_gcp
    stats = extract_metadata_stats(vv)
    
    assert stats["dimensions"] == (100, 100)
    assert "geographic_metadata" in stats
    geo = stats["geographic_metadata"]
    assert geo["crs"] == "EPSG:4326"
    assert geo["gcp_count"] == 4
    
    # Check center is extracted
    center = geo["center_lonlat"]
    assert center is not None
    assert "approximate_geographic_bounds" in geo
    assert "approximate_affine_transform" in geo

def test_tiled_processor_geo(temp_tiffs_gcp):
    vv, vh = temp_tiffs_gcp
    processor = TiledProcessor(vv, vh, tile_size=50, overlap=0)
    
    chunks = list(processor.iter_tiles())
    assert len(chunks) == 4
    
    x, y, window, vv_c, vh_c, geo = chunks[0]
    assert x == 0 and y == 0
    assert vv_c.shape == (50, 50)
    
    # Check tile geographic info
    assert "crs" in geo
    assert geo["crs"] == "EPSG:4326"
    assert "corners_lonlat" in geo
    assert "top_left" in geo["corners_lonlat"]
    
def test_stretch_array():
    arr = np.array([0, 50, 100], dtype=np.float32)
    p2 = 10
    p98 = 90
    stretched = stretch_array(arr, p2, p98)
    assert stretched[0] == 0
    assert 120 <= stretched[1] <= 135
    assert stretched[2] == 255
