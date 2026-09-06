import os
import json
import rasterio
from rasterio.transform import GCPTransformer

def verify_demo():
    print("Verifying Demonstration Incident SIH-2026-001...")
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo", "incidents", "incident_001")
    
    # 1. Source SAFE exists
    safe_dir = r"C:\Users\Aryan Sharma\Desktop\S1B_IW_GRDH_1SDV_20190610T154813_20190610T154838_016636_01F4FD_EE80.SAFE"
    assert os.path.exists(safe_dir), "Source SAFE directory not found."
    
    # 2. VV/VH exist in demo folder
    vv_path = os.path.join(base_dir, "satellite", "vv.tif")
    vh_path = os.path.join(base_dir, "satellite", "vh.tif")
    assert os.path.exists(vv_path), "Extracted VV tile missing."
    assert os.path.exists(vh_path), "Extracted VH tile missing."
    
    # 3. Dimensions match 4096x4096
    with rasterio.open(vv_path) as src:
        assert src.width == 4096 and src.height == 4096, f"VV dimensions are {src.width}x{src.height}, expected 4096x4096."
        
        # 4. GCPs exist and GCP CRS = EPSG:4326
        gcps, gcps_crs = src.gcps
        assert len(gcps) > 0, "No GCPs found in extracted tile."
        assert "4326" in str(gcps_crs), f"GCP CRS is {gcps_crs}, expected EPSG:4326."
        
        # 5. Coordinate maps to valid pixel and is inside scene
        target_lat = 31.982759
        target_lon = 32.849022
        transformer = GCPTransformer(gcps)
        row, col = transformer.rowcol(target_lon, target_lat)
        assert 0 <= row < 4096 and 0 <= col < 4096, f"Reference pixel ({row}, {col}) is outside the extracted tile."
        
        # In the tile's coordinate system (which has been shifted by row_off/col_off),
        # 7760 maps to the center of the 4096 crop -> 2048
        # Let's just ensure it falls close to the center
        assert 2040 <= row <= 2056, f"Reference row is {row}, expected ~2048"
        assert 2040 <= col <= 2056, f"Reference col is {col}, expected ~2048"
        
    # 6. Annotation exists and metadata is consistent
    ann_readme = os.path.join(base_dir, "annotation", "README.md")
    assert os.path.exists(ann_readme), "Annotation README.md missing."
    with open(ann_readme) as f:
        content = f.read()
        assert "Published Reference Oil-Slick Annotation" in content
        assert "ow-0388" in content
        
    metadata_path = os.path.join(base_dir, "metadata.json")
    assert os.path.exists(metadata_path), "metadata.json missing."
    with open(metadata_path) as f:
        md = json.load(f)
        assert md["incident_id"] == "SIH-2026-001"
        assert md["provenance"]["annotation_id"] == "ow-0388"
        
    # 7. No fake vessel data
    attr_path = os.path.join(base_dir, "derived", "attribution.json")
    with open(attr_path) as f:
        attr = json.load(f)
        assert attr["status"] == "not_available"
        
    drift_path = os.path.join(base_dir, "derived", "drift.json")
    with open(drift_path) as f:
        drift = json.load(f)
        assert drift["status"] == "not_available"
        
    print("Verification completed successfully. Real Sentinel-1 + DARTIS incident is verified.")

if __name__ == "__main__":
    verify_demo()
