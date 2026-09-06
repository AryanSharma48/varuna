import os
import re
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import torch
from torch.utils.data import Dataset, IterableDataset

try:
    import rasterio
    from rasterio.windows import Window
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from services.satellite.processor import (
    stretch_array,
    TiledProcessor,
    convert_sar_to_db,
    preprocess_sar_band
)
from ml.segmentation.config import SegmentationConfig


def extract_group_id(filename_or_stem: str) -> str:
    """
    Extracts scene / acquisition / event group identifier from a filename or stem.
    Prevents data leakage when multiple tiles/patches originate from the same scene.
    Examples:
      - 'S1A_IW_GRDH_1SDV_20260904T151022_tile_01' -> 'S1A_IW_GRDH_1SDV_20260904T151022'
      - 'scene42_patch_05' -> 'scene42'
      - 'sample_001' -> 'sample_001' (if no multi-patch delimiter)
    """
    stem = Path(filename_or_stem).stem
    # Remove common mask suffixes first
    stem = re.sub(r'(_mask|_label|_gt)$', '', stem, flags=re.IGNORECASE)
    
    # Check for standard Sentinel-1 SAFE scene naming pattern (e.g. S1A_IW_GRDH_...)
    s1_match = re.match(r'(S1[AB]_[A-Z0-9_]+_\d{8}T\d{6})', stem)
    if s1_match:
        return s1_match.group(1)
        
    # Check for common patch / tile / slice delimiters: e.g. prefix_tile_XX, prefix_patch_XX, prefix_XX
    parts = re.split(r'_(?:tile|patch|slice|crop|part)_|\b(?:tile|patch|crop)_', stem, flags=re.IGNORECASE)
    if len(parts) > 1 and parts[0]:
        return parts[0]
        
    # Fallback: if filename has multiple underscore tokens, group by first token if there is a numbering suffix
    tokens = stem.split('_')
    if len(tokens) > 2 and tokens[-1].isdigit():
        return "_".join(tokens[:-1])
        
    return stem


def pair_zenodo_dataset(dataset_dir: str) -> List[Dict[str, Any]]:
    """
    Discovers and validates strict image/mask pairs in a Zenodo Sentinel-1 dataset directory.
    
    Supported structures:
      1. Official Zenodo Part I/II/III naming:
         - e.g. '01_Train_Val_Oil_Spill_images' paired with '01_Train_Val_Oil_Spill_mask'
         - '01_Train_Val_No_Oil_Images' paired with '01_Train_Val_No_Oil_mask'
         - '01_Train_Val_Lookalike_images' paired with '01_Train_Val_Lookalike_mask'
      2. Standard subdirectories:
         - 'images/' paired with 'masks/' (or 'Images/' and 'Mask/')
      3. Separate polarization folders:
         - 'vv/', 'vh/', and 'masks/'
      4. Flat directory:
         - dataset_dir/ with paired images and masks (e.g., xxx.tif and xxx_mask.png)
      
    Strict Validation Rules:
      - Every image MUST have exactly one matching mask.
      - Every mask MUST correspond to an existing image.
      - 2-channel SAR input (VV, VH) must be present (either 2-band raster or distinct VV/VH files).
      - Raises ValueError on missing, ambiguous, or unmatched pairs.
    """
    root = Path(dataset_dir)
    if not root.exists():
        raise FileNotFoundError(f"Zenodo dataset directory does not exist: {dataset_dir}")
        
    # Guard against using Copernicus real-scene inference directory as training dataset
    if "satellite-data" in str(root.resolve()).lower():
        raise ValueError(
            "Separation violation: 'satellite-data' is the unlabelled Copernicus inference scene "
            "and cannot be used as a supervised Zenodo training dataset."
        )

    samples: List[Dict[str, Any]] = []
    
    # 1. Check for separate vv/, vh/, masks/ directories
    vv_dir = root / "vv"
    vh_dir = root / "vh"
    masks_dir_candidate = root / "masks"
    
    if vv_dir.is_dir() and vh_dir.is_dir() and masks_dir_candidate.is_dir():
        vv_files = {p.stem: p for p in sorted(vv_dir.glob("*")) if p.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]}
        vh_files = {p.stem: p for p in sorted(vh_dir.glob("*")) if p.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]}
        mask_files = {p.stem: p for p in sorted(masks_dir_candidate.glob("*")) if p.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]}
        
        all_keys = sorted(set(vv_files.keys()) | set(vh_files.keys()) | set(mask_files.keys()))
        for key in all_keys:
            if key not in vv_files or key not in vh_files or key not in mask_files:
                raise ValueError(
                    f"Strict pairing failed: Incomplete triplet for '{key}'. "
                    f"Present: VV={key in vv_files}, VH={key in vh_files}, Mask={key in mask_files}"
                )
            samples.append({
                "sample_id": key,
                "group_id": extract_group_id(key),
                "vv_path": str(vv_files[key]),
                "vh_path": str(vh_files[key]),
                "image_path": None,
                "mask_path": str(mask_files[key])
            })
        return samples

    # 2. Discover image and mask directory pairs (including actual Zenodo 01_Train_Val_* naming)
    subdirs = [d for d in root.iterdir() if d.is_dir()]
    image_dirs = [d for d in subdirs if re.search(r'(?:^|_)images?$', d.name, flags=re.IGNORECASE) or d.name.lower() in ["images", "image"]]
    
    if image_dirs:
        for img_dir in image_dirs:
            # Find corresponding mask directory
            if img_dir.name.lower() in ["images", "image"]:
                matching_masks = [d for d in subdirs if d.name.lower() in ["masks", "mask"]]
            else:
                expected_mask_name = re.sub(r'images?$', 'mask', img_dir.name, flags=re.IGNORECASE)
                expected_masks_name = re.sub(r'images?$', 'masks', img_dir.name, flags=re.IGNORECASE)
                matching_masks = [d for d in subdirs if d.name.lower() in [expected_mask_name.lower(), expected_masks_name.lower()]]
                if not matching_masks:
                    prefix = re.sub(r'images?$', '', img_dir.name, flags=re.IGNORECASE)
                    matching_masks = [d for d in subdirs if 'mask' in d.name.lower() and (prefix.lower() in d.name.lower() or not prefix)]
            
            if not matching_masks:
                raise ValueError(f"Strict pairing failed: Could not find matching mask directory for image directory '{img_dir.name}' in {dataset_dir}")
                
            mask_dir = matching_masks[0]
            
            img_candidates = sorted([p for p in img_dir.glob("*") if p.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]])
            mask_candidates = sorted([p for p in mask_dir.glob("*") if p.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]])
            
            if not img_candidates:
                raise ValueError(f"Strict pairing failed: No image files found in {img_dir}")
            if not mask_candidates:
                raise ValueError(f"Strict pairing failed: No mask files found in {mask_dir}")
                
            # Build lookup table for masks by normalized stem
            def normalize_name(s: str) -> str:
                return re.sub(r'(_mask|_label|_gt)$', '', Path(s).stem, flags=re.IGNORECASE)
                
            mask_map: Dict[str, Path] = {}
            for m in mask_candidates:
                norm = normalize_name(m.name)
                if norm in mask_map:
                    raise ValueError(f"Strict pairing failed: Ambiguous masks found for identifier '{norm}': {m.name} and {mask_map[norm].name}")
                mask_map[norm] = m
                
            matched_mask_keys = set()
            for img in img_candidates:
                norm_img = normalize_name(img.name)
                if norm_img not in mask_map:
                    raise ValueError(f"Strict pairing failed: Missing mask for image '{img.name}' in {mask_dir}")
                
                mask_path = mask_map[norm_img]
                matched_mask_keys.add(norm_img)
                
                sample_id = f"{img_dir.name}_{norm_img}" if len(image_dirs) > 1 else norm_img
                samples.append({
                    "sample_id": sample_id,
                    "group_id": extract_group_id(norm_img),
                    "image_path": str(img),
                    "vv_path": None,
                    "vh_path": None,
                    "mask_path": str(mask_path)
                })
                
            unmatched_masks = set(mask_map.keys()) - matched_mask_keys
            if unmatched_masks:
                raise ValueError(f"Strict pairing failed: Unmatched mask files with no corresponding images in {mask_dir}: {sorted(list(unmatched_masks))}")
                
        return samples

    # 3. Flat directory pairing fallback
    all_files = sorted([p for p in root.glob("*") if p.is_file() and p.suffix.lower() in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]])
    mask_files_list = [p for p in all_files if re.search(r'(_mask|_label|_gt)\b', p.stem, flags=re.IGNORECASE)]
    image_files_list = [p for p in all_files if p not in mask_files_list]
    
    if not image_files_list or not mask_files_list:
        raise ValueError(
            f"Could not discover paired images and masks in {dataset_dir}. "
            "Expected image/mask directories (e.g. '01_Train_Val_Oil_Spill_images' / '01_Train_Val_Oil_Spill_mask' "
            "or 'images/' / 'masks/'), 'vv/', 'vh/', and 'masks/' directories, "
            "or flat paired files with '_mask' suffixes."
        )
        
    mask_lookup = {re.sub(r'(_mask|_label|_gt)$', '', m.stem, flags=re.IGNORECASE): m for m in mask_files_list}
    matched_masks = set()
    for img in image_files_list:
        stem = img.stem
        if stem not in mask_lookup:
            raise ValueError(f"Strict pairing failed: No matching mask found for image '{img.name}'")
        matched_masks.add(stem)
        samples.append({
            "sample_id": stem,
            "group_id": extract_group_id(stem),
            "image_path": str(img),
            "vv_path": None,
            "vh_path": None,
            "mask_path": str(mask_lookup[stem])
        })
        
    unmatched = set(mask_lookup.keys()) - matched_masks
    if unmatched:
        raise ValueError(f"Strict pairing failed: Unmatched masks found in flat directory: {sorted(list(unmatched))}")
        
    return samples


def create_splits(
    samples: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Performs deterministic, group-aware train/validation/test splitting.
    Groups are preserved entirely within a single split to avoid spatial/scene leakage.
    """
    if not samples:
        raise ValueError("Cannot split an empty sample list.")
        
    total_ratio = train_ratio + val_ratio + test_ratio
    if not np.isclose(total_ratio, 1.0, atol=1e-3):
        raise ValueError(f"Split ratios must sum to 1.0, got {total_ratio:.3f}")

    # Group samples by group_id
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for s in samples:
        gid = s["group_id"]
        groups.setdefault(gid, []).append(s)
        
    sorted_group_keys = sorted(list(groups.keys()))
    
    # Deterministic shuffle
    rng = random.Random(seed)
    rng.shuffle(sorted_group_keys)
    
    num_groups = len(sorted_group_keys)
    if num_groups == 1:
        # If there's only 1 group (e.g. single scene with multiple patches), split by sample
        sorted_samples = sorted(samples, key=lambda x: x["sample_id"])
        rng.shuffle(sorted_samples)
        n = len(sorted_samples)
        n_train = max(1, int(round(n * train_ratio))) if n >= 3 else 1
        n_val = max(1, int(round(n * val_ratio))) if (n - n_train) >= 2 else (1 if n >= 2 else 0)
        
        train_samples = sorted_samples[:n_train]
        val_samples = sorted_samples[n_train:n_train + n_val]
        test_samples = sorted_samples[n_train + n_val:]
        if not test_samples and len(val_samples) > 1:
            test_samples = [val_samples.pop()]
            
        return {"train": train_samples, "val": val_samples, "test": test_samples}

    # Group-based split
    n_train_g = max(1, int(round(num_groups * train_ratio)))
    n_val_g = max(1, int(round(num_groups * val_ratio))) if (num_groups - n_train_g) >= 2 else (1 if num_groups >= 2 else 0)
    
    train_groups = set(sorted_group_keys[:n_train_g])
    val_groups = set(sorted_group_keys[n_train_g:n_train_g + n_val_g])
    test_groups = set(sorted_group_keys[n_train_g + n_val_g:])
    
    if not test_groups and len(val_groups) > 1:
        moved_group = list(val_groups)[-1]
        val_groups.remove(moved_group)
        test_groups.add(moved_group)

    train_list = [s for gid in sorted(train_groups) for s in groups[gid]]
    val_list = [s for gid in sorted(val_groups) for s in groups[gid]]
    test_list = [s for gid in sorted(test_groups) for s in groups[gid]]

    return {
        "train": train_list,
        "val": val_list,
        "test": test_list
    }


def save_splits_to_json(splits: Dict[str, List[Dict[str, Any]]], output_path: str, seed: int = 42):
    """Persists deterministic split lists to a JSON artifact."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        "seed": seed,
        "counts": {k: len(v) for k, v in splits.items()},
        "splits": {
            k: [
                {
                    "sample_id": s["sample_id"],
                    "group_id": s["group_id"],
                    "image_path": s.get("image_path"),
                    "vv_path": s.get("vv_path"),
                    "vh_path": s.get("vh_path"),
                    "mask_path": s["mask_path"]
                }
                for s in v
            ]
            for k, v in splits.items()
        }
    }
    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)


class ZenodoSARDataset(Dataset):
    """
    Supervised PyTorch Dataset for Zenodo Sentinel-1 Oil Spill dataset.
    Validates VV/VH 2-channel SAR input and 1-channel binary ground-truth masks.
    Applies unified radiometric dB scaling and percentile normalization.
    """
    def __init__(
        self,
        samples: Optional[List[Dict[str, Any]]] = None,
        dataset_dir: Optional[str] = None,
        split: Optional[str] = None,
        config: Optional[SegmentationConfig] = None
    ):
        self.config = config or SegmentationConfig()
        
        if samples is not None:
            self.samples = samples
        elif dataset_dir is not None:
            all_samples = pair_zenodo_dataset(dataset_dir)
            if split is not None:
                splits = create_splits(
                    all_samples,
                    train_ratio=self.config.train_ratio,
                    val_ratio=self.config.val_ratio,
                    test_ratio=self.config.test_ratio,
                    seed=self.config.seed
                )
                self.samples = splits[split]
            else:
                self.samples = all_samples
        else:
            self.samples = []

    def __len__(self) -> int:
        return len(self.samples)

    def _read_raster(self, path: str) -> np.ndarray:
        if HAS_RASTERIO:
            with rasterio.open(path) as src:
                data = src.read()
                return data.astype(np.float32)
        elif HAS_PIL:
            img = Image.open(path)
            arr = np.array(img, dtype=np.float32)
            if arr.ndim == 2:
                return arr[np.newaxis, ...]
            elif arr.ndim == 3:
                return np.transpose(arr, (2, 0, 1))
        raise RuntimeError("Neither rasterio nor PIL is available to read image/mask files.")

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        
        # 1. Read SAR Image (VV + VH)
        if sample.get("image_path"):
            img_data = self._read_raster(sample["image_path"])
            if img_data.shape[0] >= 2:
                vv_band = img_data[0]
                vh_band = img_data[1]
            elif img_data.shape[0] == 1:
                raise ValueError(
                    f"Image '{sample['image_path']}' has only 1 band. "
                    "Sentinel-1 SAR segmentation requires 2 bands (VV, VH)."
                )
            else:
                raise ValueError(f"Invalid band count {img_data.shape[0]} in '{sample['image_path']}'")
        elif sample.get("vv_path") and sample.get("vh_path"):
            vv_data = self._read_raster(sample["vv_path"])
            vh_data = self._read_raster(sample["vh_path"])
            vv_band = vv_data[0] if vv_data.ndim == 3 else vv_data
            vh_band = vh_data[0] if vh_data.ndim == 3 else vh_data
        else:
            raise ValueError(f"Incomplete image path definition in sample: {sample}")

        # 2. Read Mask
        mask_data = self._read_raster(sample["mask_path"])
        mask_band = mask_data[0] if mask_data.ndim == 3 else mask_data

        # 3. Validate Dimensions
        if vv_band.shape != vh_band.shape:
            raise ValueError(
                f"Dimension mismatch between VV {vv_band.shape} and VH {vh_band.shape} "
                f"in sample '{sample['sample_id']}'"
            )
        if vv_band.shape != mask_band.shape:
            raise ValueError(
                f"Dimension mismatch between SAR image {vv_band.shape} and mask {mask_band.shape} "
                f"in sample '{sample['sample_id']}'"
            )

        # 4. Scientifically consistent SAR preprocessing (dB conversion + percentile normalization)
        vv_norm = preprocess_sar_band(vv_band, norm_p2=self.config.norm_p2, norm_p98=self.config.norm_p98)
        vh_norm = preprocess_sar_band(vh_band, norm_p2=self.config.norm_p2, norm_p98=self.config.norm_p98)

        # Stack into [2, H, W]
        img_tensor = torch.from_numpy(np.stack([vv_norm, vh_norm], axis=0)).float()

        # Binary ground truth mask [1, H, W] (0.0 or 1.0)
        binary_mask = (mask_band > 0).astype(np.float32)
        mask_tensor = torch.from_numpy(binary_mask).unsqueeze(0).float()

        return img_tensor, mask_tensor


class SceneIterableDataset(IterableDataset):
    """
    Memory-safe IterableDataset wrapping TiledProcessor for Copernicus scene inference.
    Yields normalized [2, H, W] tensors and geospatial window metadata using the exact same
    radiometric dB conversion and percentile normalization as Zenodo training.
    """
    def __init__(self, vv_path: str, vh_path: str, config: SegmentationConfig):
        self.vv_path = vv_path
        self.vh_path = vh_path
        self.config = config
        
    def _normalize(self, chunk: np.ndarray) -> np.ndarray:
        return preprocess_sar_band(chunk, norm_p2=self.config.norm_p2, norm_p98=self.config.norm_p98)

    def __iter__(self):
        processor = TiledProcessor(
            vv_path=self.vv_path, 
            vh_path=self.vh_path, 
            tile_size=self.config.tile_size, 
            overlap=self.config.overlap
        )
        
        for x, y, window, vv_chunk, vh_chunk, geo in processor.iter_tiles():
            if vv_chunk.shape[0] == 0 or vv_chunk.shape[1] == 0:
                continue
                
            vv_norm = self._normalize(vv_chunk)
            vh_norm = self._normalize(vh_chunk)
            
            # Pad if chunk is smaller than tile_size (at edges)
            h, w = vv_norm.shape
            th, tw = self.config.tile_size, self.config.tile_size
            
            if h < th or w < tw:
                vv_pad = np.zeros((th, tw), dtype=np.float32)
                vh_pad = np.zeros((th, tw), dtype=np.float32)
                vv_pad[:h, :w] = vv_norm
                vh_pad[:h, :w] = vh_norm
                vv_norm, vh_norm = vv_pad, vh_pad
                
            tensor = torch.from_numpy(np.stack([vv_norm, vh_norm], axis=0)).float()
            
            yield {
                "tensor": tensor,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "window": (window.col_off, window.row_off, window.width, window.height),
                "geographic_metadata": geo
            }
