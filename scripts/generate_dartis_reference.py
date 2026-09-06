"""
Pipeline to parse and process the published DARTIS reference annotation (ow-0388)
for incident_001 Sentinel-1 SAR scene (S1B_IW_GRDH_1SDV_20190610T154813_20190610T154838_016636_01F4FD_EE80).
"""

import os
import json
import numpy as np
import rasterio
from rasterio.transform import GCPTransformer
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def generate_dartis_reference():
    base_dir = os.path.join("demo", "incidents", "incident_001")
    vv_path = os.path.join(base_dir, "satellite", "vv.tif")
    derived_dir = os.path.join(base_dir, "derived")
    os.makedirs(derived_dir, exist_ok=True)
    
    tab_path = "DARTIS_2019.tab"
    if not os.path.exists(tab_path):
        raise FileNotFoundError(f"DARTIS dataset table not found at {tab_path}")

    # Read DARTIS_2019.tab for ow-0388
    record_found = False
    ref_data = {}
    
    with open(tab_path, "r", encoding="utf-8", errors="ignore") as f:
        headers = []
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith("/*") or line_str.startswith("*/"):
                continue
            if "IMAGE (jpg_file)" in line_str:
                headers = line_str.split("\t")
                continue
            if "ow-0388" in line_str:
                vals = line_str.split("\t")
                if len(vals) == len(headers):
                    row_dict = dict(zip(headers, vals))
                    # Tag ow-0388-02-000994 corresponds to the main slick feature
                    if "ow-0388-02" in row_dict.get("ID (tag)", ""):
                        ref_data = row_dict
                        record_found = True
                        break

    if not record_found or not ref_data:
        raise ValueError("Could not locate DARTIS record ow-0388 in DARTIS_2019.tab")

    sentinel_id = ref_data["ID (Sentinel_ID)"]
    ref_lon = float(ref_data["Longitude (obj_ul_lon)"]) # 32.8490217560092
    ref_lat = float(ref_data["Latitude (obj_ul_lat)"])  # 31.9827590094738
    
    # 4 corners of DARTIS object bounding quadrilateral
    ul_lon, ul_lat = float(ref_data["Longitude (obj_ul_lon)"]), float(ref_data["Latitude (obj_ul_lat)"])
    ur_lon, ur_lat = float(ref_data["Longitude (obj_ur_lon)"]), float(ref_data["Latitude (obj_ur_lat)"])
    br_lon, br_lat = float(ref_data["Longitude (obj_br_lon)"]), float(ref_data["Latitude (obj_br_lat)"])
    bl_lon, bl_lat = float(ref_data["Longitude (obj_bl_lon)"]), float(ref_data["Latitude (obj_bl_lat)"])
    
    poly_coords = [
        [ul_lon, ul_lat],
        [ur_lon, ur_lat],
        [br_lon, br_lat],
        [bl_lon, bl_lat],
        [ul_lon, ul_lat]
    ]
    
    output_json_data = {
        "source": "DARTIS",
        "record_id": "ow-0388",
        "sentinel1_product": sentinel_id,
        "reference_location": {
            "longitude": ref_lon,
            "latitude": ref_lat
        },
        "geometry_type": "Polygon",
        "geometry": {
            "type": "Polygon",
            "coordinates": [poly_coords]
        },
        "coordinate_system": "EPSG:4326",
        "provenance": "Published DARTIS reference annotation (DLR PANGAEA DOI: 10.1594/PANGAEA.980773)"
    }
    
    json_path = os.path.join(derived_dir, "dartis_reference.json")
    with open(json_path, "w") as f:
        json.dump(output_json_data, f, indent=2)
    print(f"[DARTIS Pipeline] Saved reference JSON: {json_path}")
    
    # Transform coordinates to pixel row/col using GCPTransformer
    with rasterio.open(vv_path) as src_vv:
        vv = src_vv.read(1)
        gcps, _ = src_vv.gcps
        if not gcps:
            raise ValueError("No GCPs in raster source")
        transformer = GCPTransformer(gcps)
        
    # Convert lat/lon to pixel (col, row) on Sentinel-1 scene
    scene_pixels = []
    for lon, lat in poly_coords:
        # High resolution grid lookup using GCPTransformer
        best_d = float("inf")
        best_r, best_c = 0, 0
        for r in np.linspace(0, vv.shape[0] - 1, 300):
            for c in np.linspace(0, vv.shape[1] - 1, 300):
                l_on, l_at = transformer.xy(r, c)
                d = (l_on - lon)**2 + (l_at - lat)**2
                if d < best_d:
                    best_d = d
                    best_r, best_c = r, c
        scene_pixels.append((best_c, best_r))
        
    scene_pixels = np.array(scene_pixels)
    
    # Generate Overlay PNG
    p2, p98 = np.percentile(vv[vv > 0], (2, 98))
    vv_norm = np.clip((vv - p2) / (p98 - p2 + 1e-6), 0, 1)
    
    plt.figure(figsize=(10, 10))
    plt.imshow(vv_norm, cmap="gray", origin="upper")
    
    # Draw reference bounding quadrilateral
    plt.plot(scene_pixels[:, 0], scene_pixels[:, 1], "y--", linewidth=2.5, label="DARTIS REFERENCE BOUNDING QUADRILATERAL (ow-0388)")
    plt.plot(scene_pixels[0, 0], scene_pixels[0, 1], "r*", markersize=14, markeredgecolor="black", label=f"PUBLISHED REFERENCE LOCATION ({ref_lon:.6f}° E, {ref_lat:.6f}° N)")
    
    plt.title("Incident 001 — Published DARTIS Reference Annotation (ow-0388)\nInvestigation priority ≠ proof of responsibility", fontsize=11, pad=12)
    plt.xlabel("Pixel Column")
    plt.ylabel("Pixel Row")
    plt.legend(loc="upper right", framealpha=0.95)
    plt.tight_layout()
    
    overlay_path = os.path.join(derived_dir, "dartis_reference_overlay.png")
    plt.savefig(overlay_path, dpi=200)
    plt.close()
    print(f"[DARTIS Pipeline] Saved reference overlay PNG: {overlay_path}")
    
    return output_json_data

if __name__ == "__main__":
    generate_dartis_reference()
