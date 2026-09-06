import pytest
import os
import hashlib
import numpy as np
import torch
import rasterio
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from services.satellite.processor import convert_sar_to_db, preprocess_sar_band, stretch_array
from ml.segmentation.config import SegmentationConfig
from ml.segmentation.dataset import (
    ZenodoSARDataset,
    SceneIterableDataset,
    pair_zenodo_dataset
)


def get_file_quick_hash(path: str) -> str:
    """Calculates MD5 hash of header and footer chunks to detect any modification."""
    with open(path, "rb") as f:
        head = f.read(1024 * 1024)
        f.seek(-min(1024 * 1024, os.path.getsize(path)), 2)
        tail = f.read(1024 * 1024)
        return hashlib.md5(head + tail).hexdigest()


# =========================================================================
# 1. Radiometric Equivalence: Linear DN vs Decibel (dB) Preprocessing
# =========================================================================

def test_radiometric_mathematical_equivalence():
    """
    Proves that converting linear DN to dB before percentile stretching
    yields mathematically identical normalized output as processing pre-calibrated dB data.
    """
    # Create synthetic dB data (Zenodo-style: negative dB values)
    synthetic_db = np.linspace(-30.0, -5.0, 10000).reshape(100, 100).astype(np.float32)
    
    # Calculate corresponding linear amplitude DN values: DN = 10^(dB / 20)
    synthetic_dn = np.power(10.0, synthetic_db / 20.0).astype(np.float32)
    
    # Process both with the unified preprocessing pipeline
    norm_from_db = preprocess_sar_band(synthetic_db, norm_p2=2.0, norm_p98=98.0, is_already_db=True)
    norm_from_dn = preprocess_sar_band(synthetic_dn, norm_p2=2.0, norm_p98=98.0, is_already_db=False)
    
    # Assert values are strictly identical within float precision
    np.testing.assert_allclose(norm_from_dn, norm_from_db, atol=1e-5)
    assert norm_from_dn.min() >= 0.0
    assert norm_from_dn.max() <= 1.0


def test_no_accidental_double_db_conversion():
    """
    Proves that pre-calibrated dB data (e.g. Zenodo Sigma0 in dB with negative numbers)
    is NOT subjected to an accidental second log10 conversion.
    """
    zenodo_db_patch = np.array([[-25.4, -18.2], [-14.5, -9.1]], dtype=np.float32)
    
    # Auto-detection mode
    converted = convert_sar_to_db(zenodo_db_patch)
    np.testing.assert_array_equal(converted, zenodo_db_patch)
    
    # Explicit flag mode
    converted_explicit = convert_sar_to_db(zenodo_db_patch, is_already_db=True)
    np.testing.assert_array_equal(converted_explicit, zenodo_db_patch)


def test_raw_copernicus_dn_conversion():
    """
    Tests that raw Sentinel-1 GRD uint16 DN values are correctly converted to dB.
    """
    raw_dn = np.array([[100, 200], [300, 400]], dtype=np.uint16)
    expected_db = 20.0 * np.log10(raw_dn.astype(np.float32))
    
    converted = convert_sar_to_db(raw_dn)
    np.testing.assert_allclose(converted, expected_db, rtol=1e-5)


def test_power_vs_amplitude_db_equivalence():
    """
    Tests that 10*log10(Intensity = DN^2) is mathematically and physically identical
    to 20*log10(Amplitude = DN) for detected SAR signals.
    """
    raw_amplitude_dn = np.array([21.0, 100.0, 282.0, 500.0, 1200.0, 2099.0], dtype=np.float32)
    power_intensity = np.square(raw_amplitude_dn)
    
    db_from_power = 10.0 * np.log10(power_intensity)
    db_from_amplitude = 20.0 * np.log10(raw_amplitude_dn)
    
    np.testing.assert_allclose(db_from_power, db_from_amplitude, rtol=1e-6)


def test_calibration_lut_offset_invariance():
    """
    Proves that the radiometric calibration offset C_sigma = 20*log10(A_sigma) between
    calibrated Sigma0 (dB) and raw measurement amplitude (dB) cancels out completely
    under percentile stretch normalization, ensuring physical consistency with Zenodo data.
    """
    # Simulate a scene with ocean background and an oil slick (6 dB damping)
    # in calibrated Sigma0 dB (Zenodo representation)
    ocean_sigma0_db = -12.0
    slick_sigma0_db = -18.0
    
    zenodo_patch_db = np.full((50, 50), ocean_sigma0_db, dtype=np.float32)
    zenodo_patch_db[20:30, 20:30] = slick_sigma0_db
    # Add speckle
    zenodo_patch_db += np.random.normal(0, 0.5, (50, 50)).astype(np.float32)
    
    # Real Sentinel-1 IW calibration factor A_sigma (nominal ~400)
    A_sigma = 400.0
    
    # Corresponding raw GRD DN amplitude: DN = sqrt(sigma0_linear * A_sigma^2) = 10^(sigma0_db/20) * A_sigma
    copernicus_raw_dn = np.power(10.0, zenodo_patch_db / 20.0) * A_sigma
    
    # Preprocess both
    norm_zenodo = preprocess_sar_band(zenodo_patch_db, norm_p2=2.0, norm_p98=98.0, is_already_db=True)
    norm_copernicus = preprocess_sar_band(copernicus_raw_dn, norm_p2=2.0, norm_p98=98.0, is_already_db=False)
    
    # Verify outputs are identical within float precision
    np.testing.assert_allclose(norm_copernicus, norm_zenodo, atol=1e-5)
    
    # Relative damping ratio (slick vs background) in normalized space
    slick_mean_z = np.mean(norm_zenodo[20:30, 20:30])
    bg_mean_z = np.mean(norm_zenodo[:10, :10])
    slick_mean_c = np.mean(norm_copernicus[20:30, 20:30])
    bg_mean_c = np.mean(norm_copernicus[:10, :10])
    
    np.testing.assert_allclose(slick_mean_c, slick_mean_z, atol=1e-4)
    np.testing.assert_allclose(bg_mean_c, bg_mean_z, atol=1e-4)


# =========================================================================
# 2. Zenodo Part I Real Directory Name Discovery
# =========================================================================

def test_pair_zenodo_part_i_directory_structure(tmp_path):
    """
    Proves that pair_zenodo_dataset directly recognizes the actual Zenodo Part I
    archive directory names without manual renaming:
      - 01_Train_Val_Oil_Spill_images/
      - 01_Train_Val_Oil_Spill_mask/
    """
    dataset_dir = tmp_path / "zenodo_part_i"
    img_dir = dataset_dir / "01_Train_Val_Oil_Spill_images"
    mask_dir = dataset_dir / "01_Train_Val_Oil_Spill_mask"
    img_dir.mkdir(parents=True)
    mask_dir.mkdir(parents=True)
    
    # Create 2-channel 2048x2048-like TIFFs
    for i in range(1, 4):
        stem = f"{i:04d}"
        img_path = img_dir / f"{stem}.tif"
        mask_path = mask_dir / f"{stem}.tif"
        
        with rasterio.open(
            str(img_path), 'w', driver='GTiff',
            height=32, width=32, count=2, dtype='float32'
        ) as dst:
            # Band 1: VV (in dB), Band 2: VH (in dB)
            dst.write(np.random.uniform(-30, -5, (32, 32)).astype(np.float32), 1)
            dst.write(np.random.uniform(-35, -10, (32, 32)).astype(np.float32), 2)
            
        with rasterio.open(
            str(mask_path), 'w', driver='GTiff',
            height=32, width=32, count=1, dtype='uint8'
        ) as dst:
            dst.write(np.zeros((32, 32), dtype=np.uint8), 1)

    samples = pair_zenodo_dataset(str(dataset_dir))
    assert len(samples) == 3
    for s in samples:
        assert os.path.exists(s["image_path"])
        assert os.path.exists(s["mask_path"])
        assert Path(s["image_path"]).name == Path(s["mask_path"]).name


def test_pair_zenodo_part_ii_multi_category_directory_structure(tmp_path):
    """
    Proves that pair_zenodo_dataset directly recognizes multi-category Part II folders:
      - 01_Train_Val_No_Oil_Images / 01_Train_Val_No_Oil_mask
      - 01_Train_Val_Lookalike_images / 01_Train_Val_Lookalike_mask
    """
    dataset_dir = tmp_path / "zenodo_part_ii"
    no_oil_img = dataset_dir / "01_Train_Val_No_Oil_Images"
    no_oil_mask = dataset_dir / "01_Train_Val_No_Oil_mask"
    look_img = dataset_dir / "01_Train_Val_Lookalike_images"
    look_mask = dataset_dir / "01_Train_Val_Lookalike_mask"
    
    for d in [no_oil_img, no_oil_mask, look_img, look_mask]:
        d.mkdir(parents=True)
        
    for d_img, d_mask in [(no_oil_img, no_oil_mask), (look_img, look_mask)]:
        for i in range(1, 3):
            stem = f"{i:04d}"
            img_path = d_img / f"{stem}.tif"
            mask_path = d_mask / f"{stem}.tif"
            with rasterio.open(str(img_path), 'w', driver='GTiff', height=16, width=16, count=2, dtype='float32') as dst:
                dst.write(np.zeros((16, 16), dtype=np.float32), 1)
                dst.write(np.zeros((16, 16), dtype=np.float32), 2)
            with rasterio.open(str(mask_path), 'w', driver='GTiff', height=16, width=16, count=1, dtype='uint8') as dst:
                dst.write(np.zeros((16, 16), dtype=np.uint8), 1)

    samples = pair_zenodo_dataset(str(dataset_dir))
    assert len(samples) == 4


# =========================================================================
# 3. Preservation of Copernicus Original Rasters (Integrity Check)
# =========================================================================

def test_original_copernicus_tiffs_remain_untouched():
    """
    Verifies that satellite-data TIFFs are never modified in place during preprocessing / dataset reads.
    """
    vv_file = "satellite-data/002.tiff"
    vh_file = "satellite-data/001.tiff"
    
    if os.path.exists(vv_file) and os.path.exists(vh_file):
        hash_vv_before = get_file_quick_hash(vv_file)
        hash_vh_before = get_file_quick_hash(vh_file)
        
        config = SegmentationConfig(tile_size=512, overlap=0)
        dataset = SceneIterableDataset(vv_file, vh_file, config)
        
        # Read a few tiles
        iterator = iter(dataset)
        tile1 = next(iterator)
        assert tile1["tensor"].shape == (2, 512, 512)
        assert tile1["tensor"].min() >= 0.0
        assert tile1["tensor"].max() <= 1.0
        
        hash_vv_after = get_file_quick_hash(vv_file)
        hash_vh_after = get_file_quick_hash(vh_file)
        
        assert hash_vv_before == hash_vv_after, "VV TIFF was modified!"
        assert hash_vh_before == hash_vh_after, "VH TIFF was modified!"
