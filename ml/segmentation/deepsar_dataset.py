"""
Refined Deep-SAR Oil Spill (SOS) Dataset Adapter.
Connects the Zenodo Refined Deep-SAR SOS dataset to the existing 2-channel U-Net architecture.

Dataset characteristics:
- Images: 256x256 single-band SAR backscatter normalized and duplicated across 3 channels (RGB, R=G=B).
- Masks: 256x256 binary ground truth (0 = non-oil / background, 255 = oil spill).
- Official splits: 6,455 train, 1,615 val.
- Split policy: Preserves 6,455 train, deterministically splits val into 807 validation and 808 test (seed 42).
"""

import os
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image

class DeepSARDataset(Dataset):
    """
    Adapter dataset for Refined Deep-SAR SOS SAR images and masks.
    Yields [2, 256, 256] input tensors (matching UNet in_channels=2)
    and [1, 256, 256] binary target masks.
    """
    def __init__(self, samples: List[Dict[str, str]], augment: bool = False):
        self.samples = samples
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        img_path = sample["image_path"]
        mask_path = sample["mask_path"]

        # 1. Load image (RGB where R=G=B)
        with Image.open(img_path) as pil_img:
            img_arr = np.array(pil_img, dtype=np.float32)
            if img_arr.ndim == 3:
                sar_band = img_arr[:, :, 0]
            else:
                sar_band = img_arr

        # 2. SAR Preprocessing: Linear stretch from [0, 255] to [0.0, 1.0]
        sar_norm = np.clip(sar_band / 255.0, 0.0, 1.0)

        # 3. Load Mask
        with Image.open(mask_path) as pil_mask:
            mask_arr = np.array(pil_mask)
            if mask_arr.ndim == 3:
                mask_arr = mask_arr[:, :, 0]

        # 4. Binary conversion: 0 = non-oil, 1 = oil
        mask_bin = (mask_arr >= 128).astype(np.float32)

        # 5. Optional geometric augmentations for training
        if self.augment:
            # Random horizontal flip
            if random.random() > 0.5:
                sar_norm = np.fliplr(sar_norm).copy()
                mask_bin = np.fliplr(mask_bin).copy()
            # Random vertical flip
            if random.random() > 0.5:
                sar_norm = np.flipud(sar_norm).copy()
                mask_bin = np.flipud(mask_bin).copy()
            # Random 90-degree rotations
            k = random.randint(0, 3)
            if k > 0:
                sar_norm = np.rot90(sar_norm, k).copy()
                mask_bin = np.rot90(mask_bin, k).copy()

        # 6. Convert to PyTorch Tensors
        # Match UNet in_channels=2 by stacking [sar_norm, sar_norm]
        img_tensor = torch.from_numpy(np.stack([sar_norm, sar_norm], axis=0)).float()
        mask_tensor = torch.from_numpy(mask_bin).unsqueeze(0).float()

        return img_tensor, mask_tensor


def load_deepsar_splits(
    base_dir: str = "training_data/refined_deep_sar",
    seed: int = 42,
    save_splits_path: Optional[str] = "artifacts/segmentation/refined_deep_sar_splits.json"
) -> Dict[str, List[Dict[str, str]]]:
    """
    Loads all image/mask pairs and deterministically builds train, val, and test splits.
    Preserves all 6,455 train pairs, and splits 1,615 val pairs into 807 val and 808 test.
    """
    root = Path(base_dir)
    train_img_dir = root / "images" / "train"
    train_mask_dir = root / "masks" / "train"
    val_img_dir = root / "images" / "val"
    val_mask_dir = root / "masks" / "val"

    if not train_img_dir.exists() or not val_img_dir.exists():
        raise FileNotFoundError(f"Dataset directories not found under {base_dir}")

    train_files = sorted([f for f in os.listdir(train_img_dir) if f.endswith(".png")])
    val_files = sorted([f for f in os.listdir(val_img_dir) if f.endswith(".png")])

    train_samples = [
        {
            "sample_id": f"train_{f.replace('.png', '')}",
            "filename": f,
            "image_path": str(train_img_dir / f),
            "mask_path": str(train_mask_dir / f)
        }
        for f in train_files
    ]

    raw_val_samples = [
        {
            "sample_id": f"val_{f.replace('.png', '')}",
            "filename": f,
            "image_path": str(val_img_dir / f),
            "mask_path": str(val_mask_dir / f)
        }
        for f in val_files
    ]

    # Deterministic split of val set into validation and test
    rng = random.Random(seed)
    indices = list(range(len(raw_val_samples)))
    rng.shuffle(indices)

    val_cutoff = len(raw_val_samples) // 2  # 807
    val_indices = indices[:val_cutoff]
    test_indices = indices[val_cutoff:]

    val_samples = [raw_val_samples[i] for i in val_indices]
    test_samples = [raw_val_samples[i] for i in test_indices]

    splits = {
        "train": train_samples,
        "val": val_samples,
        "test": test_samples
    }

    if save_splits_path:
        Path(save_splits_path).parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            "dataset": "Refined Deep-SAR Oil Spill (SOS)",
            "seed": seed,
            "counts": {k: len(v) for k, v in splits.items()},
            "splits": splits
        }
        with open(save_splits_path, "w") as f:
            json.dump(serializable, f, indent=2)

    return splits
