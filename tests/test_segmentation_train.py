import pytest
import os
import json
import numpy as np
import torch
import rasterio
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from ml.segmentation.config import SegmentationConfig
from ml.segmentation.dataset import (
    ZenodoSARDataset,
    pair_zenodo_dataset,
    create_splits,
    save_splits_to_json,
    extract_group_id
)
from ml.segmentation.unet import UNet, DiceBCELoss
from ml.segmentation.train import train_segmentation, train_epoch, validate_epoch, set_seed
from ml.segmentation.evaluate import (
    compute_confusion_matrix,
    compute_metrics_from_cm,
    calibrate_threshold,
    evaluate_dataset,
    save_model_metadata
)
from scripts.visualize_spill import create_spill_visualization


def create_synthetic_multiband_tiff(path: str, shape=(64, 64), bands=2, dtype=np.float32):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, 'w', driver='GTiff',
        height=shape[0], width=shape[1], count=bands,
        dtype=dtype
    ) as dst:
        for b in range(1, bands + 1):
            data = np.random.uniform(10, 500, shape).astype(dtype)
            dst.write(data, b)


def create_synthetic_mask_tiff(path: str, shape=(64, 64), has_slick=True):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    mask = np.zeros(shape, dtype=np.uint8)
    if has_slick:
        # Create a small circular synthetic slick
        cy, cx = shape[0] // 2, shape[1] // 2
        y, x = np.ogrid[:shape[0], :shape[1]]
        mask_idx = ((x - cx)**2 + (y - cy)**2) <= (shape[0] // 4)**2
        mask[mask_idx] = 1

    with rasterio.open(
        path, 'w', driver='GTiff',
        height=shape[0], width=shape[1], count=1,
        dtype=np.uint8
    ) as dst:
        dst.write(mask, 1)


@pytest.fixture
def synthetic_zenodo_dir(tmp_path):
    """Creates a tiny synthetic Zenodo dataset structure with multiple scenes/patches."""
    dataset_dir = tmp_path / "synthetic_zenodo"
    images_dir = dataset_dir / "images"
    masks_dir = dataset_dir / "masks"
    images_dir.mkdir(parents=True)
    masks_dir.mkdir(parents=True)

    # 4 scenes, 2 patches each -> 8 total samples
    scenes = ["S1A_SCENE1_20260901T120000", "S1A_SCENE2_20260902T130000", "S1B_SCENE3_20260903T140000", "S1B_SCENE4_20260904T150000"]
    for scene in scenes:
        for p in [1, 2]:
            name = f"{scene}_patch_{p:02d}"
            img_path = images_dir / f"{name}.tif"
            mask_path = masks_dir / f"{name}_mask.tif"

            create_synthetic_multiband_tiff(str(img_path), shape=(64, 64), bands=2)
            create_synthetic_mask_tiff(str(mask_path), shape=(64, 64), has_slick=(p == 1))

    return dataset_dir


# ==========================================
# 1. Dataset & Pairing Tests
# ==========================================

def test_pair_zenodo_dataset_success(synthetic_zenodo_dir):
    samples = pair_zenodo_dataset(str(synthetic_zenodo_dir))
    assert len(samples) == 8
    for s in samples:
        assert os.path.exists(s["image_path"])
        assert os.path.exists(s["mask_path"])
        assert s["group_id"].startswith("S1")


def test_strict_pairing_missing_mask_fails(tmp_path):
    dataset_dir = tmp_path / "broken_dataset"
    images_dir = dataset_dir / "images"
    masks_dir = dataset_dir / "masks"
    images_dir.mkdir(parents=True)
    masks_dir.mkdir(parents=True)

    create_synthetic_multiband_tiff(str(images_dir / "sample_01.tif"), shape=(32, 32), bands=2)
    create_synthetic_multiband_tiff(str(images_dir / "sample_02.tif"), shape=(32, 32), bands=2)
    # Only create mask for sample_01
    create_synthetic_mask_tiff(str(masks_dir / "sample_01_mask.tif"), shape=(32, 32))

    with pytest.raises(ValueError, match="Strict pairing failed: Missing mask for image 'sample_02.tif'"):
        pair_zenodo_dataset(str(dataset_dir))


def test_strict_pairing_empty_masks_dir_fails(tmp_path):
    dataset_dir = tmp_path / "empty_masks_dataset"
    images_dir = dataset_dir / "images"
    masks_dir = dataset_dir / "masks"
    images_dir.mkdir(parents=True)
    masks_dir.mkdir(parents=True)

    create_synthetic_multiband_tiff(str(images_dir / "sample_01.tif"), shape=(32, 32), bands=2)
    # Mask dir is empty

    with pytest.raises(ValueError, match="Strict pairing failed: No mask files found"):
        pair_zenodo_dataset(str(dataset_dir))


def test_strict_pairing_unmatched_mask_fails(tmp_path):
    dataset_dir = tmp_path / "broken_dataset_unmatched_mask"
    images_dir = dataset_dir / "images"
    masks_dir = dataset_dir / "masks"
    images_dir.mkdir(parents=True)
    masks_dir.mkdir(parents=True)

    create_synthetic_multiband_tiff(str(images_dir / "sample_01.tif"), shape=(32, 32), bands=2)
    create_synthetic_mask_tiff(str(masks_dir / "sample_01_mask.tif"), shape=(32, 32))
    create_synthetic_mask_tiff(str(masks_dir / "orphan_mask.tif"), shape=(32, 32))

    with pytest.raises(ValueError, match="Strict pairing failed: Unmatched mask files"):
        pair_zenodo_dataset(str(dataset_dir))


def test_copernicus_separation_guard(tmp_path):
    fake_copernicus = tmp_path / "satellite-data"
    fake_copernicus.mkdir()
    with pytest.raises(ValueError, match="Separation violation"):
        pair_zenodo_dataset(str(fake_copernicus))


def test_zenodo_dataset_dimension_mismatch_fails(tmp_path):
    dataset_dir = tmp_path / "dim_mismatch"
    images_dir = dataset_dir / "images"
    masks_dir = dataset_dir / "masks"
    images_dir.mkdir(parents=True)
    masks_dir.mkdir(parents=True)

    create_synthetic_multiband_tiff(str(images_dir / "sample_01.tif"), shape=(64, 64), bands=2)
    create_synthetic_mask_tiff(str(masks_dir / "sample_01_mask.tif"), shape=(32, 32))

    samples = pair_zenodo_dataset(str(dataset_dir))
    ds = ZenodoSARDataset(samples=samples)
    with pytest.raises(ValueError, match="Dimension mismatch"):
        _ = ds[0]


def test_zenodo_dataset_single_band_fails(tmp_path):
    dataset_dir = tmp_path / "single_band"
    images_dir = dataset_dir / "images"
    masks_dir = dataset_dir / "masks"
    images_dir.mkdir(parents=True)
    masks_dir.mkdir(parents=True)

    create_synthetic_multiband_tiff(str(images_dir / "sample_01.tif"), shape=(32, 32), bands=1)
    create_synthetic_mask_tiff(str(masks_dir / "sample_01_mask.tif"), shape=(32, 32))

    samples = pair_zenodo_dataset(str(dataset_dir))
    ds = ZenodoSARDataset(samples=samples)
    with pytest.raises(ValueError, match="only 1 band"):
        _ = ds[0]


# ==========================================
# 2. Group Extraction & Splitting Tests
# ==========================================

def test_extract_group_id():
    assert extract_group_id("S1A_IW_GRDH_1SDV_20260904T151022_tile_01.tif") == "S1A_IW_GRDH_1SDV_20260904T151022"
    assert extract_group_id("scene42_patch_05_mask.png") == "scene42"
    assert extract_group_id("mumbai_offshore_01.tif") == "mumbai_offshore"


def test_deterministic_and_group_aware_splitting(synthetic_zenodo_dir, tmp_path):
    samples = pair_zenodo_dataset(str(synthetic_zenodo_dir))
    splits1 = create_splits(samples, train_ratio=0.50, val_ratio=0.25, test_ratio=0.25, seed=42)
    splits2 = create_splits(samples, train_ratio=0.50, val_ratio=0.25, test_ratio=0.25, seed=42)

    # 1. Determinism
    assert [s["sample_id"] for s in splits1["train"]] == [s["sample_id"] for s in splits2["train"]]
    assert [s["sample_id"] for s in splits1["val"]] == [s["sample_id"] for s in splits2["val"]]
    assert [s["sample_id"] for s in splits1["test"]] == [s["sample_id"] for s in splits2["test"]]

    # 2. No Group Leakage
    train_groups = {s["group_id"] for s in splits1["train"]}
    val_groups = {s["group_id"] for s in splits1["val"]}
    test_groups = {s["group_id"] for s in splits1["test"]}

    assert len(train_groups.intersection(val_groups)) == 0
    assert len(train_groups.intersection(test_groups)) == 0
    assert len(val_groups.intersection(test_groups)) == 0

    # 3. Persistence
    splits_json = tmp_path / "splits.json"
    save_splits_to_json(splits1, str(splits_json), seed=42)
    assert os.path.exists(str(splits_json))

    with open(splits_json) as f:
        loaded = json.load(f)
        assert loaded["seed"] == 42
        assert "train" in loaded["splits"]


# ==========================================
# 3. Tensor Shapes & Normalization Tests
# ==========================================

def test_zenodo_dataset_tensor_shapes(synthetic_zenodo_dir):
    samples = pair_zenodo_dataset(str(synthetic_zenodo_dir))
    dataset = ZenodoSARDataset(samples=samples)

    img, mask = dataset[0]
    assert isinstance(img, torch.Tensor)
    assert isinstance(mask, torch.Tensor)

    # Input: [2, H, W]
    assert img.shape == (2, 64, 64)
    # Target: [1, H, W]
    assert mask.shape == (1, 64, 64)

    # Normalized ranges
    assert img.min() >= 0.0 and img.max() <= 1.0
    assert set(mask.unique().numpy().tolist()).issubset({0.0, 1.0})


# ==========================================
# 4. Loss & Backpropagation Tests
# ==========================================

def test_loss_and_backprop():
    model = UNet(n_channels=2, n_classes=1, bilinear=True)
    criterion = DiceBCELoss(bce_weight=0.5)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    inputs = torch.randn(2, 2, 64, 64)
    targets = torch.randint(0, 2, (2, 1, 64, 64)).float()

    optimizer.zero_grad()
    preds = model(inputs)
    loss = criterion(preds, targets)

    assert loss.item() > 0.0
    loss.backward()

    # Verify gradients computed
    has_grads = any(p.grad is not None and torch.norm(p.grad) > 0 for p in model.parameters())
    assert has_grads is True


# ==========================================
# 5. Metrics & Threshold Calibration Tests
# ==========================================

def test_metrics_calculation():
    # Perfect match
    preds = np.array([[[[1, 1], [0, 0]]]])
    targets = np.array([[[[1, 1], [0, 0]]]])
    cm = compute_confusion_matrix(preds, targets)
    assert cm == {"tp": 2, "fp": 0, "tn": 2, "fn": 0}

    metrics = compute_metrics_from_cm(cm)
    assert np.isclose(metrics["iou"], 1.0, atol=1e-3)
    assert np.isclose(metrics["dice"], 1.0, atol=1e-3)
    assert np.isclose(metrics["accuracy"], 1.0, atol=1e-3)


def test_threshold_calibration():
    # Continuous probabilities: slick is at > 0.7
    probs = np.array([[[[0.8, 0.9], [0.1, 0.2]]]])
    targets = np.array([[[[1.0, 1.0], [0.0, 0.0]]]])

    best_th, best_metrics, sweep = calibrate_threshold(probs, targets, steps=10)
    assert 0.2 < best_th < 0.8
    assert np.isclose(best_metrics["iou"], 1.0, atol=1e-2)
    assert len(sweep) == 10


# ==========================================
# 6. Complete End-to-End Training & Checkpoint Creation
# ==========================================

def test_train_segmentation_pipeline(synthetic_zenodo_dir, tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    model_path = artifacts_dir / "best_model.pth"
    metadata_path = artifacts_dir / "model_metadata.json"
    metrics_path = artifacts_dir / "training_metrics.json"
    splits_path = artifacts_dir / "dataset_splits.json"

    cfg = SegmentationConfig(
        dataset_dir=str(synthetic_zenodo_dir),
        epochs=2,
        batch_size=2,
        learning_rate=1e-3,
        model_save_path=str(model_path),
        metadata_save_path=str(metadata_path),
        metrics_save_path=str(metrics_path),
        splits_save_path=str(splits_path)
    )

    results = train_segmentation(cfg)

    # 1. Check outputs exist
    assert os.path.exists(str(model_path))
    assert os.path.exists(str(metadata_path))
    assert os.path.exists(str(metrics_path))
    assert os.path.exists(str(splits_path))

    # 2. Check metadata contents
    with open(metadata_path) as f:
        meta = json.load(f)
        assert "calibrated_threshold" in meta
        assert "validation_metrics" in meta
        assert "normalization_percentiles" in meta
        assert meta["input_channels"] == 2

    # 3. Verify checkpoint is loadable
    loaded_model = UNet(n_channels=2, n_classes=1, bilinear=True)
    loaded_model.load_state_dict(torch.load(str(model_path)))
    assert loaded_model is not None


# ==========================================
# 7. Visualization Test
# ==========================================

def test_create_spill_visualization(tmp_path):
    vv = np.random.uniform(10, 200, (64, 64)).astype(np.float32)
    vh = np.random.uniform(5, 100, (64, 64)).astype(np.float32)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[20:40, 20:40] = 1

    out_png = tmp_path / "vis_test.png"
    create_spill_visualization(vv, vh, mask, str(out_png), threshold_used=0.45)

    assert os.path.exists(str(out_png))
    assert os.path.getsize(str(out_png)) > 1000
