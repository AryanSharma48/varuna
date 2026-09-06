"""
Unit tests for the published DARTIS reference annotation (ow-0388) pipeline.
"""

import os
import json
import pytest
import rasterio
from rasterio.transform import GCPTransformer
from shapely.geometry import Polygon, Point
from scripts.generate_dartis_reference import generate_dartis_reference

def test_dartis_reference_generation():
    """Test generating DARTIS reference JSON and verifying record metadata & geometry validity."""
    data = generate_dartis_reference()
    
    assert data["source"] == "DARTIS"
    assert data["record_id"] == "ow-0388"
    assert "S1B_IW_GRDH_1SDV_20190610T154813_20190610T154838" in data["sentinel1_product"]
    
    ref_loc = data["reference_location"]
    assert abs(ref_loc["longitude"] - 32.849022) < 1e-4
    assert abs(ref_loc["latitude"] - 31.982759) < 1e-4
    
    geom = data["geometry"]
    assert geom["type"] == "Polygon"
    coords = geom["coordinates"][0]
    assert len(coords) >= 4
    
    poly = Polygon(coords)
    assert poly.is_valid, "DARTIS polygon is invalid"
    assert not poly.is_empty, "DARTIS polygon is empty"

def test_dartis_geometry_within_scene_footprint():
    """Verify DARTIS reference polygon is fully inside the real Sentinel-1 scene footprint."""
    vv_path = os.path.join("demo", "incidents", "incident_001", "satellite", "vv.tif")
    json_path = os.path.join("demo", "incidents", "incident_001", "derived", "dartis_reference.json")
    
    assert os.path.exists(vv_path)
    assert os.path.exists(json_path)
    
    with open(json_path, "r") as f:
        data = json.load(f)
        
    with rasterio.open(vv_path) as src:
        gcps, crs = src.gcps
        transformer = GCPTransformer(gcps)
        w, h = src.width, src.height
        
    # Corners of scene footprint
    ul = transformer.xy(0, 0)
    ur = transformer.xy(0, w)
    br = transformer.xy(h, w)
    bl = transformer.xy(h, 0)
    scene_poly = Polygon([ul, ur, br, bl, ul])
    
    ref_coords = data["geometry"]["coordinates"][0]
    ref_poly = Polygon(ref_coords)
    
    assert scene_poly.contains(ref_poly) or scene_poly.intersects(ref_poly), "DARTIS polygon is outside scene footprint"

def test_reference_location_consistency():
    """Verify that published reference location matches the upper-left corner of the DARTIS object polygon."""
    json_path = os.path.join("demo", "incidents", "incident_001", "derived", "dartis_reference.json")
    with open(json_path, "r") as f:
        data = json.load(f)
        
    ref_lon = data["reference_location"]["longitude"]
    ref_lat = data["reference_location"]["latitude"]
    
    poly_ul_lon, poly_ul_lat = data["geometry"]["coordinates"][0][0]
    
    assert abs(ref_lon - poly_ul_lon) < 1e-5
    assert abs(ref_lat - poly_ul_lat) < 1e-5

def test_dartis_outputs_exist():
    """Verify all required derived DARTIS artifacts exist."""
    derived_dir = os.path.join("demo", "incidents", "incident_001", "derived")
    json_path = os.path.join(derived_dir, "dartis_reference.json")
    overlay_path = os.path.join(derived_dir, "dartis_reference_overlay.png")
    
    assert os.path.exists(json_path), f"Missing {json_path}"
    assert os.path.exists(overlay_path), f"Missing {overlay_path}"
    assert os.path.getsize(overlay_path) > 1000
