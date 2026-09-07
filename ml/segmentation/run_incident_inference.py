"""
End-to-End Inference, Polygonization, and DARTIS Comparison for incident_001
using the trained Refined Deep-SAR Oil Spill U-Net.
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import torch
import cv2
import rasterio
from rasterio.transform import GCPTransformer
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.segmentation.unet import UNet


def run_incident_inference(
    incident_dir: str = "demo/incidents/incident_001",
    model_checkpoint: str = "models/checkpoints/oil_spill_unet_best.pt",
    metadata_path: str = "models/checkpoints/oil_spill_unet_metadata.json",
    tile_size: int = 256,
    overlap: int = 64,
    min_area_pixels: int = 150
) -> Dict[str, Any]:
    print("=" * 65)
    print("RUNNING U-NET INFERENCE ON INCIDENT 001")
    print("=" * 65)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Device] Using {device}")

    # 1. Load Model and Calibrated Threshold
    if not os.path.exists(model_checkpoint):
        raise FileNotFoundError(f"Model checkpoint not found: {model_checkpoint}")

    calibrated_th = 0.5
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            meta = json.load(f)
            calibrated_th = meta.get("calibrated_threshold", 0.5)
            print(f"[Metadata] Using validation calibrated threshold: {calibrated_th:.4f}")

    model = UNet(n_channels=2, n_classes=1, bilinear=True).to(device)
    model.load_state_dict(torch.load(model_checkpoint, map_location=device))
    model.eval()

    # 2. Read Copernicus Sentinel-1 VV Scene
    vv_path = os.path.join(incident_dir, "satellite", "vv.tif")
    if not os.path.exists(vv_path):
        raise FileNotFoundError(f"Sentinel-1 VV raster not found at {vv_path}")

    with rasterio.open(vv_path) as src:
        vv_raw = src.read(1).astype(np.float32)
        h, w = vv_raw.shape
        gcps, gcps_crs = src.gcps
        profile = src.profile.copy()

    if not gcps:
        raise ValueError("Authoritative GCPs missing from vv.tif")
    transformer = GCPTransformer(gcps)

    # 3. Apply Scientifically Consistent Radiometric Preprocessing
    # Percentile stretch mapping Sentinel-1 backscatter to [0.0, 1.0]
    valid_mask = vv_raw > 0
    p2, p98 = np.percentile(vv_raw[valid_mask], (2, 98))
    vv_norm = np.clip((vv_raw - p2) / (p98 - p2 + 1e-7), 0.0, 1.0)
    print(f"[Preprocessing] 2-98% radiometric stretch: p2={p2:.1f}, p98={p98:.1f} -> [0.0, 1.0]")

    # 4. Tiled Memory-Safe Inference with Overlap Blending
    print(f"[Inference] Sliding window tiling: tile_size={tile_size}, overlap={overlap}...")
    prob_accum = np.zeros((h, w), dtype=np.float32)
    weight_accum = np.zeros((h, w), dtype=np.float32)

    step = tile_size - overlap
    rows = list(range(0, h - tile_size + 1, step))
    if rows[-1] + tile_size < h:
        rows.append(h - tile_size)
    cols = list(range(0, w - tile_size + 1, step))
    if cols[-1] + tile_size < w:
        cols.append(w - tile_size)

    # Hanning window for smooth tile blending in overlap regions
    hann_1d = np.hanning(tile_size)
    hann_2d = np.outer(hann_1d, hann_1d).astype(np.float32) + 1e-3

    with torch.no_grad():
        for r in rows:
            for c in cols:
                tile = vv_norm[r:r+tile_size, c:c+tile_size]
                # Skip pure black border background tiles
                if tile.max() == 0:
                    continue

                # Prepare 2-channel input [1, 2, H, W]
                t_in = torch.from_numpy(np.stack([tile, tile], axis=0)).unsqueeze(0).float().to(device)
                pred = model(t_in)
                pred_prob = pred[0, 0].cpu().numpy()

                prob_accum[r:r+tile_size, c:c+tile_size] += pred_prob * hann_2d
                weight_accum[r:r+tile_size, c:c+tile_size] += hann_2d

    weight_accum[weight_accum == 0] = 1.0
    full_prob = prob_accum / weight_accum
    full_prob[~valid_mask] = 0.0

    derived_dir = os.path.join(incident_dir, "derived")
    os.makedirs(derived_dir, exist_ok=True)

    # 5. Save unet_probability.tif
    prob_profile = profile.copy()
    prob_profile.update(dtype=rasterio.float32, count=1, nodata=0.0)
    prob_tif_path = os.path.join(derived_dir, "unet_probability.tif")
    with rasterio.open(prob_tif_path, "w", **prob_profile) as dst:
        dst.write(full_prob, 1)
    print(f"[Output] Saved unet_probability.tif: {prob_tif_path}")

    # 6. Apply Calibrated Threshold & Save unet_mask.tif
    binary_mask = (full_prob >= calibrated_th).astype(np.uint8)
    mask_profile = profile.copy()
    mask_profile.update(dtype=rasterio.uint8, count=1, nodata=0)
    mask_tif_path = os.path.join(derived_dir, "unet_mask.tif")
    with rasterio.open(mask_tif_path, "w", **mask_profile) as dst:
        dst.write(binary_mask, 1)
    print(f"[Output] Saved unet_mask.tif: {mask_tif_path}")

    # 7. Polygonize Connected Components (Remove tiny noise < min_area_pixels)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask)
    print(f"[Polygonization] Total components detected: {num_labels - 1}")

    valid_polygons = []
    features = []

    m_per_deg_lat = 111320.0

    for i in range(1, num_labels):
        area_px = stats[i, cv2.CC_STAT_AREA]
        if area_px < min_area_pixels:
            continue

        comp_mask = (labels == i).astype(np.uint8)
        contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        cnt = contours[0]
        # Approximate contour to reduce vertices while preserving geometry
        epsilon = 0.003 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        # Geographic coordinates conversion via authoritative GCPTransformer
        geo_coords = []
        for pt in approx:
            col, row = pt[0]
            lon_c, lat_c = transformer.xy(row, col)
            geo_coords.append([round(lon_c, 6), round(lat_c, 6)])

        # Close polygon ring
        if len(geo_coords) > 2:
            if geo_coords[0] != geo_coords[-1]:
                geo_coords.append(geo_coords[0])

        c_col, c_row = centroids[i]
        c_lon, c_lat = transformer.xy(c_row, c_col)
        m_per_deg_lon = 111320.0 * math.cos(math.radians(c_lat))

        # Real geographic area (km²) from pixel area (10m x 10m Sentinel-1 GRDH pixel ≈ 100 m²)
        area_km2 = (area_px * 100.0) / 1e6
        perimeter_km = (cv2.arcLength(cnt, True) * 10.0) / 1000.0
        mean_prob = float(np.mean(full_prob[labels == i]))

        poly_props = {
            "component_id": i,
            "area_km2": round(area_km2, 3),
            "area_pixels": int(area_px),
            "perimeter_km": round(perimeter_km, 3),
            "centroid": [round(c_lon, 6), round(c_lat, 6)],
            "mean_probability": round(mean_prob, 4),
            "vertex_count": len(geo_coords)
        }

        features.append({
            "type": "Feature",
            "properties": poly_props,
            "geometry": {
                "type": "Polygon",
                "coordinates": [geo_coords]
            }
        })
        valid_polygons.append(poly_props)

    # Sort by area descending (largest component = primary slick)
    features.sort(key=lambda x: x["properties"]["area_km2"], reverse=True)
    valid_polygons.sort(key=lambda x: x["area_km2"], reverse=True)

    geojson_data = {
        "type": "FeatureCollection",
        "name": "U-Net Oil-Spill Prediction",
        "calibrated_threshold": calibrated_th,
        "features": features
    }

    geojson_path = os.path.join(derived_dir, "unet_prediction.geojson")
    with open(geojson_path, "w") as f:
        json.dump(geojson_data, f, indent=2)
    print(f"[Output] Saved unet_prediction.geojson ({len(features)} valid polygons): {geojson_path}")

    # 8. Compare with DARTIS Reference Region
    dartis_ref_path = os.path.join(derived_dir, "dartis_reference.json")
    dartis_comparison = {"overlap_found": False}
    if os.path.exists(dartis_ref_path):
        with open(dartis_ref_path) as f:
            dartis_ref = json.load(f)

        ref_lon = dartis_ref["reference_location"]["longitude"]
        ref_lat = dartis_ref["reference_location"]["latitude"]

        if valid_polygons:
            primary = valid_polygons[0]
            p_lon, p_lat = primary["centroid"]
            dist_km = math.sqrt(
                ((p_lon - ref_lon) * 111.32 * math.cos(math.radians(ref_lat)))**2 +
                ((p_lat - ref_lat) * 111.32)**2
            )

            dartis_comparison = {
                "overlap_found": True,
                "dartis_reference_location": [ref_lon, ref_lat],
                "primary_unet_centroid": [p_lon, p_lat],
                "distance_to_reference_km": round(dist_km, 3),
                "predicted_area_km2": primary["area_km2"],
                "status": "CONCORDANT" if dist_km < 15.0 else "OFFSET"
            }
            print(f"[DARTIS Comparison] Primary predicted slick is {dist_km:.2f} km from DARTIS reference point.")

    eval_json_path = os.path.join(derived_dir, "unet_evaluation.json")
    with open(eval_json_path, "w") as f:
        json.dump(dartis_comparison, f, indent=2)

    # 9. Generate Visual Overlay PNG
    overlay_path = os.path.join(derived_dir, "unet_overlay.png")
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(vv_norm, cmap="gray")

    # Draw U-Net predicted masks in translucent cyan
    if binary_mask.max() > 0:
        colored_mask = np.zeros((h, w, 4), dtype=np.float32)
        colored_mask[binary_mask > 0] = [0.0, 0.9, 1.0, 0.45] # Cyan overlay
        ax.imshow(colored_mask)

    # Plot DARTIS reference location
    if os.path.exists(dartis_ref_path):
        # Convert ref_lon, ref_lat to pixel row, col
        best_d = float("inf")
        best_r, best_c = 0, 0
        for r in np.linspace(0, h-1, 100):
            for c in np.linspace(0, w-1, 100):
                l_on, l_at = transformer.xy(r, c)
                d = (l_on - ref_lon)**2 + (l_at - ref_lat)**2
                if d < best_d:
                    best_d = d
                    best_r, best_c = r, c
        ax.plot(best_c, best_r, "y*", markersize=14, markeredgecolor="black", label=f"DARTIS Reference ({ref_lon:.4f}° E, {ref_lat:.4f}° N)")

    if valid_polygons:
        # Plot predicted centroid
        p_lon, p_lat = valid_polygons[0]["centroid"]
        ax.plot(centroids[1][0], centroids[1][1], "ro", markersize=8, markeredgecolor="white", label=f"U-Net Predicted Centroid ({p_lon:.4f}° E, {p_lat:.4f}° N)")

    ax.set_title("Incident 001 — Real Sentinel-1 SAR U-Net Prediction\nInvestigation priority ≠ proof of responsibility", fontsize=11, pad=12)
    ax.legend(loc="upper right", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(overlay_path, dpi=200)
    plt.close()
    print(f"[Output] Saved visual overlay: {overlay_path}")

    return {
        "calibrated_threshold": calibrated_th,
        "polygons_count": len(features),
        "primary_slick": valid_polygons[0] if valid_polygons else None,
        "dartis_comparison": dartis_comparison,
        "probability_tif": prob_tif_path,
        "mask_tif": mask_tif_path,
        "geojson": geojson_path,
        "overlay_png": overlay_path
    }


if __name__ == "__main__":
    run_incident_inference()
