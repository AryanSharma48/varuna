"""
Pretrained Oil-Spill Segmentation Model Adapter
Target Model: TheArchitect416/oil-spill-segmentation-model (Hugging Face)
Architecture: U-Net (ResNet34 encoder, 4 output classes)

This adapter isolates the pretrained Hugging Face checkpoint inference from our
custom U-Net implementation and extracts oil spill candidate features on Sentinel-1 SAR scenes.
"""

import os
import json
import math
import numpy as np
import cv2
import rasterio
from rasterio.transform import GCPTransformer
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
import torch
import segmentation_models_pytorch as smp

# Preprocessing Constants
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
DEFAULT_MODEL_PATH = os.path.join("models", "pretrained", "oil_spill", "model.pth")

def load_pretrained_model(checkpoint_path: str = DEFAULT_MODEL_PATH, device: str = None) -> torch.nn.Module:
    """
    Safely loads the pretrained U-Net checkpoint from Hugging Face.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Pretrained model checkpoint not found at: {checkpoint_path}")
        
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=3,
        classes=4
    )
    
    # Safe loading using weights_only=True
    state_dict = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model

def preprocess_sar_composite(vv_array: np.ndarray, vh_array: np.ndarray) -> np.ndarray:
    """
    Preprocesses Sentinel-1 SAR VV and VH rasters into a normalized 3-channel
    ImageNet-compatible float32 array (H, W, 3).
    Channel 0: Normalized VV (1st-99th percentile scaling)
    Channel 1: Normalized VH (1st-99th percentile scaling)
    Channel 2: Polarization Ratio VV / (VH + 1e-6) normalized
    """
    vv_float = vv_array.astype(np.float32)
    vh_float = vh_array.astype(np.float32)
    
    # Percentile clipping to remove outliers
    vv_valid = vv_float[vv_float > 0] if np.any(vv_float > 0) else vv_float
    vh_valid = vh_float[vh_float > 0] if np.any(vh_float > 0) else vh_float
    
    p1_vv, p99_vv = np.percentile(vv_valid, (1, 99))
    p1_vh, p99_vh = np.percentile(vh_valid, (1, 99))
    
    vv_norm = np.clip((vv_float - p1_vv) / (p99_vv - p1_vv + 1e-6), 0.0, 1.0)
    vh_norm = np.clip((vh_float - p1_vh) / (p99_vh - p1_vh + 1e-6), 0.0, 1.0)
    ratio_norm = np.clip(vv_norm / (vh_norm + 1e-6), 0.0, 1.0)
    
    rgb = np.stack([vv_norm, vh_norm, ratio_norm], axis=-1).astype(np.float32)
    normalized_rgb = (rgb - IMAGENET_MEAN) / IMAGENET_STD
    return normalized_rgb

def predict_oil_mask(
    vv_array: np.ndarray,
    vh_array: np.ndarray,
    model_path: str = DEFAULT_MODEL_PATH,
    tile_size: int = 256,
    batch_size: int = 16,
    threshold: float = 0.5
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Runs sliding window inference on the full SAR scene and outputs:
    1. prob_mask: 2D float32 array (0.0 to 1.0) representing Oil Spill class (Class 1) probability
    2. binary_mask: 2D uint8 array (0 or 1) at given probability threshold
    3. confidence_stats: dictionary of min, max, mean, p95 probability values
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_pretrained_model(model_path, device=device)
    
    normalized_rgb = preprocess_sar_composite(vv_array, vh_array)
    H, W, _ = normalized_rgb.shape
    
    tiles = []
    coords = []
    
    for r in range(0, H, tile_size):
        for c in range(0, W, tile_size):
            r_end = min(r + tile_size, H)
            c_end = min(c + tile_size, W)
            tile = normalized_rgb[r:r_end, c:c_end]
            
            if tile.shape[0] != tile_size or tile.shape[1] != tile_size:
                tile = cv2.copyMakeBorder(
                    tile, 0, tile_size - tile.shape[0], 0, tile_size - tile.shape[1], cv2.BORDER_REFLECT
                )
                
            tiles.append(tile.transpose(2, 0, 1)) # (3, H, W)
            coords.append((r, r_end, c, c_end))
            
    tiles_arr = np.array(tiles, dtype=np.float32)
    prob_mask = np.zeros((H, W), dtype=np.float32)
    
    with torch.no_grad():
        for i in range(0, len(tiles_arr), batch_size):
            batch = torch.from_numpy(tiles_arr[i : i + batch_size]).to(device)
            logits = model(batch)
            probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy() # Class 1 = Oil Spill
            
            for idx, p in enumerate(probs):
                r, r_end, c, c_end = coords[i + idx]
                prob_mask[r:r_end, c:c_end] = p[0 : (r_end - r), 0 : (c_end - c)]
                
    binary_mask = (prob_mask >= threshold).astype(np.uint8)
    
    stats = {
        "min": float(np.min(prob_mask)),
        "max": float(np.max(prob_mask)),
        "mean": float(np.mean(prob_mask)),
        "p95": float(np.percentile(prob_mask, 95))
    }
    
    return prob_mask, binary_mask, stats

def calculate_haversine_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculates great-circle distance in kilometers between two points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return float(R * c)

def polygonize_mask(binary_mask: np.ndarray, transformer: GCPTransformer, min_area_pixels: int = 50) -> tuple[dict, tuple[float, float], float, dict, int]:
    """
    Converts binary candidate mask into geographic GeoJSON polygon geometry,
    centroid (lon, lat), area (sq km), and bounding box.
    """
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    polygons = []
    total_pixels = 0
    
    for cnt in contours:
        area_px = cv2.contourArea(cnt)
        if area_px < min_area_pixels:
            continue
            
        total_pixels += int(area_px)
        cnt_squeezed = cnt.squeeze()
        if cnt_squeezed.ndim != 2 or len(cnt_squeezed) < 3:
            continue
            
        # Convert pixel coordinates (col, row) to (lon, lat) using GCPTransformer
        geo_coords = []
        for px, py in cnt_squeezed:
            lon, lat = transformer.xy(float(py), float(px))
            geo_coords.append((float(lon), float(lat)))
            
        # Ensure polygon closure
        if geo_coords[0] != geo_coords[-1]:
            geo_coords.append(geo_coords[0])
            
        if len(geo_coords) >= 4:
            poly = Polygon(geo_coords)
            if poly.is_valid:
                polygons.append(poly)
                
    if not polygons:
        # Fallback empty polygon
        empty_poly = Polygon([[0, 0], [0, 0.001], [0.001, 0.001], [0, 0]])
        return mapping(empty_poly), (0.0, 0.0), 0.0, {"min_lon": 0, "min_lat": 0, "max_lon": 0, "max_lat": 0}, 0
        
    combined = unary_union(polygons)
    centroid_lon, centroid_lat = combined.centroid.x, combined.centroid.y
    bounds = combined.bounds # (minx, miny, maxx, maxy) -> (min_lon, min_lat, max_lon, max_lat)
    
    bbox = {
        "min_lon": float(bounds[0]),
        "min_lat": float(bounds[1]),
        "max_lon": float(bounds[2]),
        "max_lat": float(bounds[3])
    }
    
    # Calculate area in sq km (1 deg lat ~ 111 km, 1 deg lon ~ 111 * cos(lat) km)
    mean_lat_rad = math.radians(centroid_lat)
    dx_km = (bounds[2] - bounds[0]) * 111.32 * math.cos(mean_lat_rad)
    dy_km = (bounds[3] - bounds[1]) * 111.32
    area_sqkm = float(abs(combined.area * 111.32 * 111.32 * math.cos(mean_lat_rad)))
    
    return mapping(combined), (centroid_lon, centroid_lat), area_sqkm, bbox, total_pixels

def run_incident_001_inference(
    incident_dir: str = os.path.join("demo", "incidents", "incident_001"),
    threshold: float = 0.5
) -> dict:
    """
    Executes full pretrained U-Net model evaluation on incident_001 Sentinel-1 SAR scene,
    generates GeoTIFF derived mask, JSON candidate metadata, and PNG overlay image.
    """
    vv_path = os.path.join(incident_dir, "satellite", "vv.tif")
    vh_path = os.path.join(incident_dir, "satellite", "vh.tif")
    meta_path = os.path.join(incident_dir, "metadata.json")
    derived_dir = os.path.join(incident_dir, "derived")
    os.makedirs(derived_dir, exist_ok=True)
    
    with open(meta_path, "r") as f:
        metadata = json.load(f)
        
    ref_lon = metadata["provenance"]["published_oil_coordinates"]["lon"]
    ref_lat = metadata["provenance"]["published_oil_coordinates"]["lat"]
    
    with rasterio.open(vv_path) as src_vv, rasterio.open(vh_path) as src_vh:
        vv = src_vv.read(1)
        vh = src_vh.read(1)
        gcps, crs = src_vv.gcps
        if not gcps:
            raise ValueError("No GCPs found in Sentinel-1 raster metadata.")
        transformer = GCPTransformer(gcps)
        raster_meta = src_vv.meta.copy()
        
    print("[Pretrained U-Net] Running inference on Sentinel-1 scene...")
    prob_mask, binary_mask, conf_stats = predict_oil_mask(vv, vh, threshold=threshold)
    
    # Save derived GeoTIFF probability mask
    mask_tif_path = os.path.join(derived_dir, "pretrained_mask.tif")
    raster_meta.update({"dtype": "float32", "count": 1})
    with rasterio.open(mask_tif_path, "w", **raster_meta) as dst:
        dst.write(prob_mask.astype(np.float32), 1)
    print(f"[Pretrained U-Net] Saved GeoTIFF probability mask: {mask_tif_path}")
    
    # Polygonize candidate features
    geojson_geom, (c_lon, c_lat), area_sqkm, bbox, pixel_count = polygonize_mask(binary_mask, transformer)
    
    # Evaluate against DARTIS reference location
    dist_km = calculate_haversine_distance_km(c_lon, c_lat, ref_lon, ref_lat)
    
    # Check if reference point intersects candidate mask
    ref_intersects = False
    if pixel_count > 0:
        poly_shape = Polygon(geojson_geom["coordinates"][0]) if geojson_geom["type"] == "Polygon" else MultiPolygon([Polygon(p[0]) for p in geojson_geom["coordinates"]])
        from shapely.geometry import Point
        ref_intersects = bool(poly_shape.intersects(Point(ref_lon, ref_lat)))
        
    preprocessing_desc = (
        "Dual-pol Sentinel-1 SAR VV & VH rasters normalized using 1st-99th percentile clipping. "
        "Constructed 3-channel composite [VV, VH, VV/VH ratio] followed by ImageNet mean/std normalization. "
        "Inference executed using sliding window 256x256 tile patches on pretrained U-Net (ResNet34 encoder)."
    )
    
    domain_note = (
        "The model (TheArchitect416/oil-spill-segmentation-model) was trained on 256x256 RGB oil-spill benchmark patches. "
        "When evaluated on Sentinel-1 SAR GRD amplitude rasters, raw probability distributions reflect land/sea clutter boundaries. "
        "DARTIS reference coordinate ow-0388 (32.849022 E, 31.982759 N) serves as the ground truth location."
    )
    
    candidate_data = {
        "model_name": "TheArchitect416/oil-spill-segmentation-model",
        "model_architecture": "U-Net (ResNet34 encoder, 4 output classes: Background, Oil Spill, Lookalike, Water/Ship)",
        "threshold": threshold,
        "detected_pixel_count": pixel_count,
        "polygon_geometry": geojson_geom,
        "centroid": {"lon": c_lon, "lat": c_lat},
        "area_sqkm": area_sqkm,
        "bounding_box": bbox,
        "confidence_stats": conf_stats,
        "preprocessing_description": preprocessing_desc,
        "reference_comparison": {
            "reference_name": "DARTIS Reference ow-0388",
            "reference_location": {"lon": ref_lon, "lat": ref_lat},
            "distance_to_predicted_centroid_km": dist_km,
            "reference_intersects_predicted_mask": ref_intersects,
            "domain_compatibility_note": domain_note
        }
    }
    
    json_path = os.path.join(derived_dir, "pretrained_candidate.json")
    with open(json_path, "w") as f:
        json.dump(candidate_data, f, indent=2)
    print(f"[Pretrained U-Net] Saved JSON candidate metadata: {json_path}")
    
    # Save visual debug overlay PNG
    generate_debug_overlay(vv, prob_mask, binary_mask, transformer, (ref_lon, ref_lat), (c_lon, c_lat), derived_dir)
    
    return candidate_data

def generate_debug_overlay(
    vv: np.ndarray,
    prob_mask: np.ndarray,
    binary_mask: np.ndarray,
    transformer: GCPTransformer,
    ref_coords: tuple[float, float],
    pred_coords: tuple[float, float],
    output_dir: str
):
    """
    Generates high-resolution pretrained_overlay.png displaying:
    - Sentinel-1 SAR VV raster background
    - U-Net predicted probability mask contour overlay
    - Labeled DARTIS reference marker and predicted centroid marker
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    ref_lon, ref_lat = ref_coords
    pred_lon, pred_lat = pred_coords
    
    # Convert ref_lon/ref_lat to approximate pixel row/col for overlay display
    best_dist = float("inf")
    ref_r, ref_c = vv.shape[0] / 2.0, vv.shape[1] / 2.0
    for r_i in np.linspace(0, vv.shape[0], 100):
        for c_i in np.linspace(0, vv.shape[1], 100):
            lon, lat = transformer.xy(r_i, c_i)
            d = (lon - ref_lon)**2 + (lat - ref_lat)**2
            if d < best_dist:
                best_dist = d
                ref_r, ref_c = r_i, c_i
                
    p2, p98 = np.percentile(vv[vv > 0], (2, 98))
    vv_norm = np.clip((vv - p2) / (p98 - p2 + 1e-6), 0, 1)
    
    plt.figure(figsize=(12, 10))
    plt.imshow(vv_norm, cmap="gray", origin="upper")
    
    # Overlay probability heatmap
    plt.imshow(prob_mask, cmap="jet", alpha=0.35, origin="upper", vmin=0.0, vmax=1.0)
    
    # Plot contours of binary mask
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.contourArea(cnt) >= 50:
            cnt_sq = cnt.squeeze()
            if cnt_sq.ndim == 2 and len(cnt_sq) >= 3:
                plt.plot(cnt_sq[:, 0], cnt_sq[:, 1], color="red", linewidth=1.2, label="MODEL PREDICTION" if "MODEL PREDICTION" not in plt.gca().get_legend_handles_labels()[1] else "")
                
    # Plot DARTIS reference marker
    plt.plot(ref_c, ref_r, "y*", markersize=14, markeredgecolor="black", label="DARTIS REFERENCE (ow-0388)")
    
    plt.colorbar(label="Pretrained U-Net Oil-Spill Probability")
    plt.title("Incident 001 — Pretrained U-Net (ResNet34) Candidate Detection\nInvestigation priority ≠ proof of responsibility", fontsize=12, pad=12)
    plt.xlabel("Pixel Column")
    plt.ylabel("Pixel Row")
    plt.legend(loc="upper right", framealpha=0.9)
    plt.tight_layout()
    
    overlay_path = os.path.join(output_dir, "pretrained_overlay.png")
    plt.savefig(overlay_path, dpi=200)
    plt.close()
    print(f"[Pretrained U-Net] Saved visual overlay PNG: {overlay_path}")

if __name__ == "__main__":
    run_incident_001_inference()
