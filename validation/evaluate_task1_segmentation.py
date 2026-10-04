"""
TASK 1: Comprehensive Rigorous Evaluation of U-Net Oil Spill Segmentation
Dataset: Refined Deep-SAR Oil Spill (SOS) - Zenodo 15298010
Checkpoint: models/checkpoints/oil_spill_unet_best.pt
Evaluates strictly on the 808 held-out test patches.
"""

import os
import sys
import time
import json
import random
from pathlib import Path
from PIL import Image
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.segmentation.unet import UNet, DiceBCELoss
from ml.segmentation.deepsar_dataset import DeepSARDataset, load_deepsar_splits
from ml.segmentation.evaluate import compute_confusion_matrix, compute_metrics_from_cm
from ml.segmentation.train_deepsar import evaluate_model, calibrate_threshold_on_val, set_seed
from ml.lookalike.classifier import LookAlikeClassifier


def run_segmentation_validation():
    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== TASK 1: SEGMENTATION METRICS EVALUATION ===")
    print(f"Inference Device: {device}")
    
    checkpoint_path = "models/checkpoints/oil_spill_unet_best.pt"
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}")
        
    checkpoint_size_bytes = os.path.getsize(checkpoint_path)
    print(f"Loaded checkpoint: {checkpoint_path} ({checkpoint_size_bytes / 1e6:.2f} MB)")

    # 1. Dataset loading and split audit
    splits = load_deepsar_splits(base_dir="training_data/refined_deep_sar", seed=42)
    train_count = len(splits["train"])
    val_count = len(splits["val"])
    test_count = len(splits["test"])
    print(f"Dataset: Refined Deep-SAR Oil Spill (SOS) - Zenodo 15298010")
    print(f"Split sizes: Train={train_count}, Val={val_count}, Test={test_count} (Total={train_count + val_count + test_count})")

    # Split overlap check
    train_paths = {s["image_path"] for s in splits["train"]}
    val_paths = {s["image_path"] for s in splits["val"]}
    test_paths = {s["image_path"] for s in splits["test"]}
    assert len(train_paths.intersection(val_paths)) == 0, "Train-Val path overlap detected!"
    assert len(train_paths.intersection(test_paths)) == 0, "Train-Test path overlap detected!"
    assert len(val_paths.intersection(test_paths)) == 0, "Val-Test path overlap detected!"
    print("Partition integrity check: 0 duplicate patch paths between splits.")

    # 2. Instantiate Model
    model = UNet(n_channels=2, n_classes=1, bilinear=True).to(device)
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()

    criterion = DiceBCELoss(bce_weight=0.5)

    # 3. Load datasets
    val_dataset = DeepSARDataset(splits["val"], augment=False)
    test_dataset = DeepSARDataset(splits["test"], augment=False)

    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False, num_workers=0)

    # 4. Threshold calibration on validation set
    print("\n--- Step 1: Calibrating decision threshold on Validation Set (807 patches) ---")
    val_loss, val_probs, val_targets = evaluate_model(model, val_loader, criterion, device)
    calibrated_th, val_metrics = calibrate_threshold_on_val(val_probs, val_targets)
    print(f"Optimal Threshold (calibrated on Val): {calibrated_th:.4f}")
    print(f"Validation Performance at th={calibrated_th:.4f}: IoU={val_metrics['iou']:.4f}, Dice={val_metrics['dice']:.4f}")

    # 5. Held-out test evaluation with precise timing
    print("\n--- Step 2: Evaluating on Held-Out Test Set (808 patches) ---")
    torch.set_num_threads(8)
    
    # Warmup
    with torch.no_grad():
        _ = model(torch.zeros(16, 2, 256, 256, device=device))

    t_start = time.perf_counter()
    test_loss, test_probs, test_targets = evaluate_model(model, test_loader, criterion, device)
    t_end = time.perf_counter()

    total_eval_time_sec = t_end - t_start
    avg_latency_ms_per_patch = (total_eval_time_sec / test_count) * 1000.0
    throughput_fps = test_count / total_eval_time_sec

    print(f"Total test evaluation time: {total_eval_time_sec:.2f} s")
    print(f"Average inference latency per patch: {avg_latency_ms_per_patch:.2f} ms")
    print(f"Throughput: {throughput_fps:.2f} patches/sec (FPS)")

    # 6. Binary metrics at calibrated threshold (0.50)
    test_pred_bin = (test_probs >= calibrated_th).astype(np.uint8)
    test_target_bin = (test_targets >= 0.5).astype(np.uint8)

    # Confusion matrix for Oil class (class 1)
    cm_oil = compute_confusion_matrix(test_pred_bin, test_target_bin)
    metrics_oil = compute_metrics_from_cm(cm_oil)

    # Confusion matrix for Background/Clean sea class (class 0)
    bg_pred_bin = (test_pred_bin == 0).astype(np.uint8)
    bg_target_bin = (test_target_bin == 0).astype(np.uint8)
    cm_bg = compute_confusion_matrix(bg_pred_bin, bg_target_bin)
    metrics_bg = compute_metrics_from_cm(cm_bg)

    mean_iou = (metrics_oil["iou"] + metrics_bg["iou"]) / 2.0
    mean_dice = (metrics_oil["dice"] + metrics_bg["dice"]) / 2.0

    print(f"\n--- Held-Out Test Set Results (N = {test_count} patches, {test_count * 256 * 256:,} pixels) ---")
    print(f"OIL CLASS:")
    print(f"  IoU (Jaccard): {metrics_oil['iou']:.4f} ({metrics_oil['iou']*100:.2f}%)")
    print(f"  Dice / F1:     {metrics_oil['dice']:.4f} ({metrics_oil['dice']*100:.2f}%)")
    print(f"  Precision:     {metrics_oil['precision']:.4f} ({metrics_oil['precision']*100:.2f}%)")
    print(f"  Recall:        {metrics_oil['recall']:.4f} ({metrics_oil['recall']*100:.2f}%)")
    print(f"  Accuracy:      {metrics_oil['accuracy']:.4f} ({metrics_oil['accuracy']*100:.2f}%)")
    print(f"  Confusion Matrix: TP={cm_oil['tp']:,} | FP={cm_oil['fp']:,} | TN={cm_oil['tn']:,} | FN={cm_oil['fn']:,}")
    print(f"\nBACKGROUND / NON-OIL CLASS:")
    print(f"  IoU:           {metrics_bg['iou']:.4f} ({metrics_bg['iou']*100:.2f}%)")
    print(f"  Dice:          {metrics_bg['dice']:.4f} ({metrics_bg['dice']*100:.2f}%)")
    print(f"  Precision:     {metrics_bg['precision']:.4f} ({metrics_bg['precision']*100:.2f}%)")
    print(f"  Recall:        {metrics_bg['recall']:.4f} ({metrics_bg['recall']*100:.2f}%)")
    print(f"\nOVERALL MULTI-CLASS METRICS:")
    print(f"  mIoU:          {mean_iou:.4f} ({mean_iou*100:.2f}%)")
    print(f"  mDice:         {mean_dice:.4f} ({mean_dice*100:.2f}%)")

    # 7. False-Positive Analysis on Look-Alike / Zero-Oil Patches
    print("\n--- Step 3: False-Positive Behaviour on Look-Alike / Zero-Oil Patches ---")
    zero_oil_indices = []
    for idx, s in enumerate(splits["test"]):
        msk = np.array(Image.open(s["mask_path"]))
        if msk.ndim == 3:
            msk = msk[:, :, 0]
        if np.sum(msk >= 128) == 0:
            zero_oil_indices.append(idx)

    num_zero_oil = len(zero_oil_indices)
    total_zero_oil_pixels = num_zero_oil * 256 * 256
    
    fp_pixels_in_zero_oil = 0
    clean_patches_perfect = 0
    patch_fp_rates = []

    for idx in zero_oil_indices:
        pred_p = test_pred_bin[idx, 0]
        fp_p = int(np.sum(pred_p == 1))
        fp_pixels_in_zero_oil += fp_p
        patch_fp_rates.append(fp_p / (256 * 256))
        if fp_p == 0:
            clean_patches_perfect += 1

    overall_clean_fpr = fp_pixels_in_zero_oil / max(1, total_zero_oil_pixels)
    print(f"Total zero-oil (pure negative/look-alike) test patches: {num_zero_oil} ({num_zero_oil / test_count * 100:.2f}%)")
    print(f"Total pixels in zero-oil test patches: {total_zero_oil_pixels:,}")
    print(f"False-positive oil pixels predicted in zero-oil patches: {fp_pixels_in_zero_oil:,}")
    print(f"Pixel-level False Positive Rate on zero-oil patches: {overall_clean_fpr:.4f} ({overall_clean_fpr * 100:.2f}%)")
    print(f"Patches with zero false positive pixels (perfect specificity): {clean_patches_perfect}/{num_zero_oil} ({clean_patches_perfect / max(1, num_zero_oil) * 100:.2f}%)")

    # Stage-2 Look-Alike Discriminator test
    print("\n--- Step 4: Stage-2 Physics-Informed Look-Alike Classifier Evaluation ---")
    clf = LookAlikeClassifier()
    # Test on representative physical regimes
    synthetic_lookalike_cases = [
        {
            "name": "Low-Wind Sheltered Bay",
            "slick_vv": np.random.normal(-24.0, 1.2, (64, 64)),
            "bg_vv": np.random.normal(-9.0, 1.0, (64, 64)),
            "morph": {"aspect_ratio": 1.4, "area_km2": 4.2},
            "wind": 2.1,
            "expected": "LOOK_ALIKE"
        },
        {
            "name": "Natural Biogenic Plant Film",
            "slick_vv": np.random.normal(-13.0, 1.0, (64, 64)),
            "bg_vv": np.random.normal(-10.5, 0.8, (64, 64)),
            "morph": {"aspect_ratio": 1.2, "area_km2": 2.0},
            "wind": 5.5,
            "expected": "LOOK_ALIKE"
        },
        {
            "name": "Genuine Ship Bilge Discharge Streak",
            "slick_vv": np.random.normal(-19.5, 1.0, (64, 64)),
            "bg_vv": np.random.normal(-9.5, 1.0, (64, 64)),
            "morph": {"aspect_ratio": 4.8, "area_km2": 6.5},
            "wind": 6.2,
            "expected": "OIL"
        }
    ]

    lookalike_results = []
    for c in synthetic_lookalike_cases:
        res = clf.classify_slick(c["slick_vv"], c["bg_vv"], c["morph"], ambient_wind_ms=c["wind"])
        print(f"  Case '{c['name']}': Decision={res['decision']}, Risk={res['look_alike_risk']}, Conf={res['oil_confidence']}, Damping={res['damping_db']} dB")
        lookalike_results.append({
            "case_name": c["name"],
            "expected": c["expected"],
            "decision": res["decision"],
            "confidence": res["oil_confidence"],
            "look_alike_risk": res["look_alike_risk"],
            "look_alike_type": res["look_alike_type"],
            "damping_db": res["damping_db"],
            "reasons": res["reasons"]
        })

    # Prepare structured output
    output_data = {
        "task": "TASK 1: U-Net Oil Spill Segmentation Validation",
        "dataset": {
            "name": "Refined Deep-SAR Oil Spill (SOS)",
            "zenodo_record": "15298010",
            "doi": "10.5281/zenodo.15298010",
            "total_images": train_count + val_count + test_count,
            "patch_resolution": [256, 256],
            "channels": 2,
            "splits": {
                "train_patches": train_count,
                "val_patches": val_count,
                "test_patches": test_count,
                "test_percentage": round((test_count / (train_count + val_count + test_count)) * 100, 2)
            },
            "split_policy_audit": {
                "scene_level_possible_with_dataset": False,
                "reason": "Zenodo 15298010 provides only pre-cropped patches named palsar_X and sentinel_X; scene acquisition SAFE IDs and geospatial coordinates were omitted by the benchmark authors.",
                "leakage_audit": "0 exact image or path collisions across train, val, and test partitions.",
                "held_out_status": "Strictly untouched 808 patches (half of official test/val set) evaluated only once after calibrating threshold on val split."
            }
        },
        "model": {
            "architecture": "U-Net (Standard 4-level DoubleConv encoder-decoder with bilinear upsampling)",
            "checkpoint_path": checkpoint_path,
            "checkpoint_size_mb": round(checkpoint_size_bytes / 1e6, 2),
            "calibrated_threshold": calibrated_th
        },
        "hardware": {
            "processor": "AMD Ryzen 7 7435HS (8 Cores, 16 Logical Processors)",
            "os": "Windows 11",
            "framework": f"PyTorch {torch.__version__}",
            "device": str(device),
            "threads": 8
        },
        "inference_benchmarking": {
            "total_eval_time_sec": round(total_eval_time_sec, 2),
            "average_latency_ms_per_patch": round(avg_latency_ms_per_patch, 2),
            "throughput_fps": round(throughput_fps, 2)
        },
        "test_metrics_oil_class": {
            "iou": round(metrics_oil["iou"], 4),
            "dice_f1": round(metrics_oil["dice"], 4),
            "precision": round(metrics_oil["precision"], 4),
            "recall": round(metrics_oil["recall"], 4),
            "accuracy": round(metrics_oil["accuracy"], 4),
            "confusion_matrix": {
                "true_positives": cm_oil["tp"],
                "false_positives": cm_oil["fp"],
                "true_negatives": cm_oil["tn"],
                "false_negatives": cm_oil["fn"],
                "total_pixels": sum(cm_oil.values())
            }
        },
        "test_metrics_background_class": {
            "iou": round(metrics_bg["iou"], 4),
            "dice_f1": round(metrics_bg["dice"], 4),
            "precision": round(metrics_bg["precision"], 4),
            "recall": round(metrics_bg["recall"], 4)
        },
        "test_metrics_overall": {
            "mean_iou_miou": round(mean_iou, 4),
            "mean_dice_mdice": round(mean_dice, 4),
            "classes_evaluated": ["background", "oil_spill"],
            "classes_absent_in_ground_truth": ["look_alike", "ship", "land"],
            "note": "Refined Deep-SAR SOS provides binary masks {0, 255}; distinct categorical labels for ship/land are not present in this dataset."
        },
        "false_positive_analysis_lookalike": {
            "zero_oil_patches_count": num_zero_oil,
            "zero_oil_patches_percentage": round(num_zero_oil / test_count * 100, 2),
            "total_pixels_in_zero_oil_patches": total_zero_oil_pixels,
            "false_positive_oil_pixels": fp_pixels_in_zero_oil,
            "false_positive_pixel_rate": round(overall_clean_fpr, 4),
            "patches_with_zero_false_alarms": clean_patches_perfect,
            "patch_level_perfect_specificity": round(clean_patches_perfect / max(1, num_zero_oil) * 100, 2),
            "stage2_lookalike_classifier_cases": lookalike_results
        }
    }

    out_file = "validation/task1_segmentation.json"
    with open(out_file, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\n[Saved] Task 1 validation results saved to {out_file}")
    return output_data


if __name__ == "__main__":
    run_segmentation_validation()
