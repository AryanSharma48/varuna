import os
import re
import math
from pathlib import Path
from typing import Dict, Any, Tuple, Generator, Optional, List, Callable
import numpy as np

try:
    import rasterio
    from rasterio.windows import Window
    from rasterio.enums import Resampling
    from rasterio.transform import from_gcps, GCPTransformer
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def discover_polarizations(directory: str) -> Tuple[Optional[str], Optional[str]]:
    directory_path = Path(directory)
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory {directory} does not exist.")

    tiffs = list(directory_path.rglob("*.tiff")) + list(directory_path.rglob("*.tif"))
    
    vv_path = None
    vh_path = None

    for tiff in tiffs:
        name_lower = tiff.name.lower()
        if re.search(r'\bvv\b', name_lower) or '_vv' in name_lower or '-vv' in name_lower:
            vv_path = str(tiff)
        elif re.search(r'\bvh\b', name_lower) or '_vh' in name_lower or '-vh' in name_lower:
            vh_path = str(tiff)

    if vv_path and vh_path:
        return vv_path, vh_path

    if not vv_path:
        for tiff in tiffs:
            if '002' in tiff.name:
                vv_path = str(tiff)
                break
    if not vh_path:
        for tiff in tiffs:
            if '001' in tiff.name:
                vh_path = str(tiff)
                break

    return vv_path, vh_path

def validate_compatibility(vv_path: str, vh_path: str) -> Dict[str, Any]:
    if not HAS_RASTERIO:
        raise ImportError("rasterio is required for this operation.")
        
    with rasterio.open(vv_path) as vv_src, rasterio.open(vh_path) as vh_src:
        dim_match = (vv_src.width == vh_src.width) and (vv_src.height == vh_src.height)
        crs_match = (vv_src.crs == vh_src.crs)
        transform_match = (vv_src.transform == vh_src.transform)
        bounds_match = (vv_src.bounds == vh_src.bounds)
        res_match = (vv_src.res == vh_src.res)
        
        # Check GCP match
        vv_gcps, vv_gcp_crs = vv_src.gcps
        vh_gcps, vh_gcp_crs = vh_src.gcps
        
        gcp_match = (len(vv_gcps) == len(vh_gcps)) and (vv_gcp_crs == vh_gcp_crs)
        
        is_compatible = dim_match and crs_match and transform_match and bounds_match and res_match and gcp_match

        return {
            "is_compatible": is_compatible,
            "dimensions": {"vv": (vv_src.width, vv_src.height), "vh": (vh_src.width, vh_src.height), "match": dim_match},
            "crs": {"vv": str(vv_src.crs), "vh": str(vh_src.crs), "match": crs_match},
            "resolution": {"vv": vv_src.res, "vh": vh_src.res, "match": res_match},
            "bounds": {"vv": list(vv_src.bounds), "vh": list(vh_src.bounds), "match": bounds_match},
            "gcps": {
                "vv_count": len(vv_gcps), 
                "vh_count": len(vh_gcps), 
                "vv_crs": str(vv_gcp_crs), 
                "vh_crs": str(vh_gcp_crs), 
                "match": gcp_match
            }
        }

class Georeferencer:
    """Provides authoritative pixel-to-geographic transformations based on rasterio GCPTransformer."""
    def __init__(self, gcps: List[Any], crs: Any):
        self.gcps = gcps
        self.crs = crs
        self.transformer = GCPTransformer(gcps) if gcps else None

    def pixel_to_lonlat(self, row: float, col: float) -> Tuple[Optional[float], Optional[float]]:
        """Authoritative pixel to (longitude, latitude) conversion."""
        if not self.transformer:
            return None, None
        return self.transformer.xy(row, col)
        
    def get_approximate_transform(self):
        """Returns an approximate affine transform, for compatibility only."""
        if not self.gcps:
            return None
        return from_gcps(self.gcps)

def extract_metadata_stats(path: str) -> Dict[str, Any]:
    if not HAS_RASTERIO:
        raise ImportError("rasterio is required.")
        
    with rasterio.open(path) as src:
        # Block-wise exact min/max
        exact_min = float('inf')
        exact_max = float('-inf')
        
        for ji, window in src.block_windows(1):
            block = src.read(1, window=window)
            if src.nodata is not None:
                block = block[block != src.nodata]
            if block.size > 0:
                b_min = float(block.min())
                b_max = float(block.max())
                if b_min < exact_min: exact_min = b_min
                if b_max > exact_max: exact_max = b_max

        # Decimated sample
        target_size = 1024
        ratio = min(target_size / src.height, target_size / src.width, 1.0)
        out_shape = (int(src.count), max(1, int(src.height * ratio)), max(1, int(src.width * ratio)))
        sample = src.read(1, out_shape=out_shape[1:], resampling=Resampling.nearest)
        
        if src.nodata is not None:
            sample = sample[sample != src.nodata]
            
        estimated_p2 = float(np.percentile(sample, 2)) if sample.size > 0 else 0.0
        estimated_p98 = float(np.percentile(sample, 98)) if sample.size > 0 else 0.0
        estimated_mean = float(np.mean(sample)) if sample.size > 0 else 0.0
        estimated_std = float(np.std(sample)) if sample.size > 0 else 0.0
        
        # Geolocation via GCPs
        gcps, gcp_crs = src.gcps
        geo_info = None
        
        if gcps:
            geo = Georeferencer(gcps, gcp_crs)
            h, w = src.height, src.width
            tl = geo.pixel_to_lonlat(0, 0)
            tr = geo.pixel_to_lonlat(0, w)
            bl = geo.pixel_to_lonlat(h, 0)
            br = geo.pixel_to_lonlat(h, w)
            center = geo.pixel_to_lonlat(h/2, w/2)
            
            lons = [c[0] for c in (tl, tr, bl, br) if c[0] is not None]
            lats = [c[1] for c in (tl, tr, bl, br) if c[1] is not None]
            
            approx_bounds = (min(lons), min(lats), max(lons), max(lats)) if lons else None
            
            geo_info = {
                "gcp_count": len(gcps),
                "crs": str(gcp_crs),
                "corners_lonlat": {
                    "top_left": tl,
                    "top_right": tr,
                    "bottom_left": bl,
                    "bottom_right": br
                },
                "center_lonlat": center,
                "approximate_geographic_bounds": approx_bounds,
                "approximate_affine_transform": tuple(geo.get_approximate_transform())[:6] if geo.get_approximate_transform() else None
            }
        
        return {
            "dimensions": (src.width, src.height),
            "pixel_crs": str(src.crs),
            "pixel_resolution": src.res,
            "pixel_bounds": list(src.bounds),
            "dtype": src.dtypes[0],
            "nodata": src.nodata,
            "exact_min": exact_min,
            "exact_max": exact_max,
            "estimated_p2": estimated_p2,
            "estimated_p98": estimated_p98,
            "estimated_mean": estimated_mean,
            "estimated_std": estimated_std,
            "geographic_metadata": geo_info
        }

def convert_sar_to_db(arr: np.ndarray, is_already_db: Optional[bool] = None, eps: float = 1e-5) -> np.ndarray:
    """
    Converts SAR pixel values to Decibels (dB).
    
    If data is raw linear Sentinel-1 GRD Digital Numbers (DN amplitude):
        SAR_dB = 20 * log10(max(DN, eps))
        
    If data is already in dB (e.g. Zenodo Sigma0 in dB):
        Leaves values unchanged and prevents accidental double-dB conversion.
    """
    arr_f = arr.astype(np.float32)
    if is_already_db is True:
        return arr_f
    if is_already_db is False:
        return 20.0 * np.log10(np.maximum(arr_f, eps))
        
    # Auto-detection heuristic:
    # 1. Negative values -> already in dB (raw Sentinel-1 DN is strictly non-negative uint16).
    # 2. Float values with typical dB ranges (mean < 15.0 and min < 5.0 with float dtype).
    if np.any(arr_f < 0.0) or (arr.dtype != np.uint16 and arr.dtype != np.uint32 and np.min(arr_f) < 5.0 and np.mean(arr_f) < 15.0):
        return arr_f
        
    # Standard raw Sentinel-1 GRD DN amplitude -> dB
    return 20.0 * np.log10(np.maximum(arr_f, eps))

def preprocess_sar_band(
    band_data: np.ndarray,
    norm_p2: float = 2.0,
    norm_p98: float = 98.0,
    is_already_db: Optional[bool] = None
) -> np.ndarray:
    """
    Unified, scientifically consistent SAR preprocessing pipeline.
    Applies:
      1. Radiometric dB conversion (converts raw DN to dB, preserves existing dB)
      2. Configurable percentile clipping [p2, p98]
      3. Min-Max normalization to [0.0, 1.0]
      
    Works identically for both Zenodo training patches and Copernicus inference scenes.
    """
    if band_data.size == 0:
        return band_data.astype(np.float32)
        
    band_db = convert_sar_to_db(band_data, is_already_db=is_already_db)
    p2 = float(np.percentile(band_db, norm_p2))
    p98 = float(np.percentile(band_db, norm_p98))
    
    stretched = stretch_array(band_db, p2, p98)
    return stretched.astype(np.float32) / 255.0

def stretch_array(arr: np.ndarray, p2: float, p98: float) -> np.ndarray:
    clipped = np.clip(arr, p2, p98)
    if (p98 - p2) != 0:
        norm = (clipped - p2) / (p98 - p2)
    else:
        norm = np.zeros_like(clipped)
    return (norm * 255.0).astype(np.uint8)

def generate_previews(vv_path: str, vh_path: str, output_dir: str):
    if not HAS_RASTERIO or not HAS_PIL:
        raise ImportError("rasterio and Pillow are required.")
        
    os.makedirs(output_dir, exist_ok=True)
    
    with rasterio.open(vv_path) as vv_src, rasterio.open(vh_path) as vh_src:
        target_size = 1024
        ratio = min(target_size / vv_src.height, target_size / vv_src.width, 1.0)
        
        out_shape = (max(1, int(vv_src.height * ratio)), max(1, int(vv_src.width * ratio)))
        
        vv_sample = vv_src.read(1, out_shape=out_shape, resampling=Resampling.nearest)
        vh_sample = vh_src.read(1, out_shape=out_shape, resampling=Resampling.nearest)
        
        vv_p2, vv_p98 = np.percentile(vv_sample, 2), np.percentile(vv_sample, 98)
        vh_p2, vh_p98 = np.percentile(vh_sample, 2), np.percentile(vh_sample, 98)
        
        vv_img_arr = stretch_array(vv_sample, vv_p2, vv_p98)
        vh_img_arr = stretch_array(vh_sample, vh_p2, vh_p98)
        
        Image.fromarray(vv_img_arr).save(os.path.join(output_dir, "preview_vv.png"))
        Image.fromarray(vh_img_arr).save(os.path.join(output_dir, "preview_vh.png"))
        
        b_arr = ((vv_img_arr.astype(np.uint16) + vh_img_arr.astype(np.uint16)) // 2).astype(np.uint8)
        rgb_arr = np.stack([vv_img_arr, vh_img_arr, b_arr], axis=-1)
        
        Image.fromarray(rgb_arr, mode="RGB").save(os.path.join(output_dir, "preview_combined.png"))
        
    return {
        "vv_preview": os.path.join(output_dir, "preview_vv.png"),
        "vh_preview": os.path.join(output_dir, "preview_vh.png"),
        "combined_preview": os.path.join(output_dir, "preview_combined.png")
    }

class TiledProcessor:
    def __init__(self, vv_path: str, vh_path: str, tile_size: int = 1024, overlap: int = 0):
        self.vv_path = vv_path
        self.vh_path = vh_path
        self.tile_size = tile_size
        self.overlap = overlap
        
    def iter_tiles(self) -> Generator[Tuple[int, int, Any, np.ndarray, np.ndarray, Dict[str, Any]], None, None]:
        with rasterio.open(self.vv_path) as vv_src, rasterio.open(self.vh_path) as vh_src:
            width = vv_src.width
            height = vv_src.height
            
            gcps, gcp_crs = vv_src.gcps
            geo = Georeferencer(gcps, gcp_crs) if gcps else None
            
            step = self.tile_size - self.overlap
            if step <= 0:
                raise ValueError("Overlap must be smaller than tile_size.")
                
            for y in range(0, height, step):
                for x in range(0, width, step):
                    w = min(self.tile_size, width - x)
                    h = min(self.tile_size, height - y)
                    window = Window(col_off=x, row_off=y, width=w, height=h)
                    
                    vv_chunk = vv_src.read(1, window=window)
                    vh_chunk = vh_src.read(1, window=window)
                    
                    geographic_metadata = {}
                    if geo:
                        tl = geo.pixel_to_lonlat(y, x)
                        tr = geo.pixel_to_lonlat(y, x + w)
                        bl = geo.pixel_to_lonlat(y + h, x)
                        br = geo.pixel_to_lonlat(y + h, x + w)
                        
                        lons = [c[0] for c in (tl, tr, bl, br) if c[0] is not None]
                        lats = [c[1] for c in (tl, tr, bl, br) if c[1] is not None]
                        
                        geographic_metadata = {
                            "crs": str(gcp_crs),
                            "corners_lonlat": {
                                "top_left": tl,
                                "top_right": tr,
                                "bottom_left": bl,
                                "bottom_right": br
                            },
                            "approximate_geographic_bounds": (min(lons), min(lats), max(lons), max(lats)) if lons else None
                        }
                    
                    yield x, y, window, vv_chunk, vh_chunk, geographic_metadata
