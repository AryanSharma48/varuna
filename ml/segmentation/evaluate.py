import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.segmentation.config import SegmentationConfig
from ml.segmentation.dataset import ZenodoSARDataset, create_splits, pair_zenodo_dataset
from ml.segmentation.unet import UNet, DiceBCELoss


def compute_confusion_matrix(preds_bin: np.ndarray, targets_bin: np.ndarray) -> Dict[str, int]:
    """Computes exact pixel-level True Positives, False Positives, True Negatives, False Negatives."""
    preds_b = (preds_bin > 0).astype(bool)
    targets_b = (targets_bin > 0).astype(bool)
    
    tp = int(np.sum(preds_b & targets_b))
    fp = int(np.sum(preds_b & (~targets_b)))
    fn = int(np.sum((~preds_b) & targets_b))
    tn = int(np.sum((~preds_b) & (~targets_b)))
    
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def compute_metrics_from_cm(cm: Dict[str, int], smooth: float = 1e-6) -> Dict[str, float]:
    """Computes IoU, Dice/F1, Precision, Recall, and Accuracy from confusion matrix counts."""
    tp = cm["tp"]
    fp = cm["fp"]
    tn = cm["tn"]
    fn = cm["fn"]
    
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / max(1, total)
    precision = (tp + smooth) / (tp + fp + smooth)
    recall = (tp + smooth) / (tp + fn + smooth)
    iou = (tp + smooth) / (tp + fp + fn + smooth)
    dice = (2.0 * tp + smooth) / (2.0 * tp + fp + fn + smooth)
    
    return {
        "iou": float(iou),
        "dice": float(dice),
        "precision": float(precision),
        "recall": float(recall),
        "accuracy": float(accuracy),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn
    }


def collect_predictions_and_targets(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device
) -> Tuple[np.ndarray, np.ndarray]:
    """Runs model forward pass over dataloader and returns continuous probability maps and binary targets."""
    model.eval()
    all_probs = []
    all_targets = []
    
    with torch.no_grad():
        for images, masks in dataloader:
            images = images.to(device)
            # Output is sigmoid probability [B, 1, H, W]
            probs = model(images)
            all_probs.append(probs.cpu().numpy())
            all_targets.append(masks.numpy())
            
    if not all_probs:
        return np.empty((0,)), np.empty((0,))
        
    probs_concat = np.concatenate(all_probs, axis=0) # [N, 1, H, W]
    targets_concat = np.concatenate(all_targets, axis=0) # [N, 1, H, W]
    return probs_concat, targets_concat


def calibrate_threshold(
    val_probs: np.ndarray,
    val_targets: np.ndarray,
    threshold_min: float = 0.05,
    threshold_max: float = 0.95,
    steps: int = 19
) -> Tuple[float, Dict[str, float], List[Dict[str, Any]]]:
    """
    Sweeps probability thresholds over validation set to find the optimal threshold that maximizes IoU.
    Does not assume 0.5 is optimal.
    """
    thresholds = np.linspace(threshold_min, threshold_max, steps)
    best_iou = -1.0
    best_threshold = 0.5
    best_metrics = {}
    sweep_results = []
    
    for th in thresholds:
        preds_bin = (val_probs >= th).astype(np.uint8)
        cm = compute_confusion_matrix(preds_bin, val_targets)
        metrics = compute_metrics_from_cm(cm)
        sweep_record = {
            "threshold": round(float(th), 4),
            "iou": round(metrics["iou"], 4),
            "dice": round(metrics["dice"], 4),
            "precision": round(metrics["precision"], 4),
            "recall": round(metrics["recall"], 4),
            "accuracy": round(metrics["accuracy"], 4)
        }
        sweep_results.append(sweep_record)
        
        # Primary objective: maximize IoU (or Dice)
        if metrics["iou"] > best_iou:
            best_iou = metrics["iou"]
            best_threshold = float(th)
            best_metrics = metrics

    return best_threshold, best_metrics, sweep_results


def evaluate_dataset(
    model: nn.Module,
    dataset: ZenodoSARDataset,
    config: SegmentationConfig,
    device: torch.device,
    threshold: Optional[float] = None
) -> Tuple[Dict[str, float], Optional[float], Optional[List[Dict[str, Any]]]]:
    """
    Evaluates dataset. If threshold is None, automatically calibrates threshold.
    Returns (metrics, calibrated_threshold, sweep_results).
    """
    dataloader = DataLoader(dataset, batch_size=config.batch_size, shuffle=False, num_workers=config.num_workers)
    probs, targets = collect_predictions_and_targets(model, dataloader, device)
    
    if probs.size == 0:
        return {}, None, None
        
    if threshold is None:
        best_th, best_metrics, sweep = calibrate_threshold(probs, targets)
        return best_metrics, best_th, sweep
    else:
        preds_bin = (probs >= threshold).astype(np.uint8)
        cm = compute_confusion_matrix(preds_bin, targets)
        metrics = compute_metrics_from_cm(cm)
        return metrics, threshold, None


def save_model_metadata(
    output_path: str,
    optimal_threshold: float,
    val_metrics: Dict[str, Any],
    test_metrics: Optional[Dict[str, Any]],
    threshold_sweep: Optional[List[Dict[str, Any]]],
    config: SegmentationConfig
):
    """Saves model calibration, evaluation metrics, and configuration to metadata JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "metadata_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_architecture": "UNet",
        "input_channels": config.in_channels,
        "polarizations": ["VV", "VH"],
        "output_classes": config.out_classes,
        "calibrated_threshold": optimal_threshold,
        "normalization_percentiles": {
            "p2": config.norm_p2,
            "p98": config.norm_p98
        },
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "threshold_calibration_sweep": threshold_sweep,
        "training_hyperparameters": {
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "epochs": config.epochs,
            "seed": config.seed,
            "split_ratios": {
                "train": config.train_ratio,
                "val": config.val_ratio,
                "test": config.test_ratio
            }
        }
    }
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate SAR Oil Spill Segmentation U-Net & Calibrate Threshold")
    parser.add_argument("--model-path", type=str, default="artifacts/best_model.pth", help="Path to trained .pth model checkpoint")
    parser.add_argument("--dataset-dir", type=str, default="data/zenodo_oil_spill", help="Path to Zenodo dataset directory")
    parser.add_argument("--output-metadata", type=str, default="artifacts/model_metadata.json", help="Path to save metadata JSON")
    args = parser.parse_args()

    config = SegmentationConfig(
        dataset_dir=args.dataset_dir,
        model_save_path=args.model_path,
        metadata_save_path=args.output_metadata
    )

    if not os.path.exists(args.model_path):
        raise FileNotFoundError(f"Model checkpoint not found: {args.model_path}")
    if not os.path.exists(args.dataset_dir):
        raise FileNotFoundError(f"Zenodo dataset directory not found: {args.dataset_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = UNet(n_channels=config.in_channels, n_classes=config.out_classes, bilinear=config.bilinear)
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.to(device)

    all_samples = pair_zenodo_dataset(args.dataset_dir)
    splits = create_splits(all_samples, seed=config.seed)

    val_dataset = ZenodoSARDataset(samples=splits["val"], config=config)
    test_dataset = ZenodoSARDataset(samples=splits["test"], config=config)

    print("Calibrating decision threshold on validation set...")
    val_metrics, best_th, sweep = evaluate_dataset(model, val_dataset, config, device, threshold=None)
    print(f"Optimal Calibrated Threshold: {best_th:.4f} (Validation IoU: {val_metrics['iou']:.4f})")

    print(f"Evaluating test set with calibrated threshold {best_th:.4f}...")
    test_metrics, _, _ = evaluate_dataset(model, test_dataset, config, device, threshold=best_th)
    print(f"Test IoU: {test_metrics['iou']:.4f} | Test Dice: {test_metrics['dice']:.4f}")

    save_model_metadata(args.output_metadata, best_th, val_metrics, test_metrics, sweep, config)
    print(f"Saved evaluation metadata to {args.output_metadata}")
