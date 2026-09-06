import os
import sys
import json
import argparse
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.segmentation.config import SegmentationConfig
from ml.segmentation.dataset import (
    ZenodoSARDataset,
    pair_zenodo_dataset,
    create_splits,
    save_splits_to_json
)
from ml.segmentation.unet import UNet, DiceBCELoss
from ml.segmentation.evaluate import (
    evaluate_dataset,
    save_model_metadata,
    collect_predictions_and_targets,
    calibrate_threshold,
    compute_confusion_matrix,
    compute_metrics_from_cm
)


def set_seed(seed: int):
    """Sets random seeds across Python, NumPy, and PyTorch for deterministic training."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device
) -> float:
    """Runs a single training epoch and returns the average batch loss."""
    model.train()
    running_loss = 0.0
    num_batches = 0

    for images, masks in dataloader:
        images = images.to(device)
        masks = masks.to(device)

        optimizer.zero_grad()
        preds = model(images)
        loss = criterion(preds, masks)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        num_batches += 1

    return running_loss / max(1, num_batches)


def validate_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    threshold: float = 0.5
) -> Tuple[float, Dict[str, float]]:
    """Runs validation, computing loss and segmentation metrics."""
    model.eval()
    running_loss = 0.0
    num_batches = 0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, masks in dataloader:
            images = images.to(device)
            masks = masks.to(device)

            preds = model(images)
            loss = criterion(preds, masks)
            running_loss += loss.item()
            num_batches += 1

            all_preds.append(preds.cpu().numpy())
            all_targets.append(masks.cpu().numpy())

    val_loss = running_loss / max(1, num_batches)
    if all_preds:
        probs = np.concatenate(all_preds, axis=0)
        targets = np.concatenate(all_targets, axis=0)
        bin_preds = (probs >= threshold).astype(np.uint8)
        cm = compute_confusion_matrix(bin_preds, targets)
        metrics = compute_metrics_from_cm(cm)
    else:
        metrics = {"iou": 0.0, "dice": 0.0, "precision": 0.0, "recall": 0.0, "accuracy": 0.0}

    return val_loss, metrics


def train_segmentation(
    config: SegmentationConfig,
    samples: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main training execution function.
    Trains U-Net, saves checkpoints, calibrates decision threshold, and exports metadata.
    """
    set_seed(config.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Discover and pair samples
    if samples is None:
        if not os.path.exists(config.dataset_dir):
            raise FileNotFoundError(
                f"Zenodo dataset directory does not exist: {config.dataset_dir}. "
                "Please download the Zenodo Sentinel-1 dataset or provide a valid path."
            )
        samples = pair_zenodo_dataset(config.dataset_dir)

    if not samples:
        raise ValueError("No valid sample pairs found for training.")

    print(f"Total discovered samples: {len(samples)}")

    # 2. Split dataset deterministically
    splits = create_splits(
        samples,
        train_ratio=config.train_ratio,
        val_ratio=config.val_ratio,
        test_ratio=config.test_ratio,
        seed=config.seed
    )
    print(f"Splits -> Train: {len(splits['train'])}, Val: {len(splits['val'])}, Test: {len(splits['test'])}")

    save_splits_to_json(splits, config.splits_save_path, seed=config.seed)

    # 3. Create datasets and dataloaders
    train_ds = ZenodoSARDataset(samples=splits["train"], config=config)
    val_ds = ZenodoSARDataset(samples=splits["val"], config=config)
    test_ds = ZenodoSARDataset(samples=splits["test"], config=config)

    train_loader = DataLoader(
        train_ds,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers
    )

    # 4. Initialize model, loss, optimizer
    model = UNet(
        n_channels=config.in_channels,
        n_classes=config.out_classes,
        bilinear=config.bilinear
    ).to(device)

    criterion = DiceBCELoss(bce_weight=0.5)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=3
    )

    best_val_loss = float('inf')
    best_val_iou = -1.0
    history: List[Dict[str, Any]] = []

    Path(config.model_save_path).parent.mkdir(parents=True, exist_ok=True)

    # 5. Training Loop
    print(f"Beginning training for {config.epochs} epochs...")
    for epoch in range(1, config.epochs + 1):
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_metrics = validate_epoch(model, val_loader, criterion, device, threshold=config.threshold)

        scheduler.step(val_loss)

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_loss, 5),
            "val_iou": round(val_metrics["iou"], 4),
            "val_dice": round(val_metrics["dice"], 4),
            "val_precision": round(val_metrics["precision"], 4),
            "val_recall": round(val_metrics["recall"], 4)
        }
        history.append(epoch_record)

        print(
            f"Epoch [{epoch:02d}/{config.epochs:02d}] "
            f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | "
            f"Val IoU: {val_metrics['iou']:.4f} | Val Dice: {val_metrics['dice']:.4f}"
        )

        # Save best model based on validation IoU (or loss)
        if val_metrics["iou"] > best_val_iou:
            best_val_iou = val_metrics["iou"]
            best_val_loss = val_loss
            torch.save(model.state_dict(), config.model_save_path)
            print(f"  -> Best model saved to {config.model_save_path} (Val IoU: {best_val_iou:.4f})")

    # If best_model was never saved (e.g., all 0 IoU), save final weights
    if not os.path.exists(config.model_save_path):
        torch.save(model.state_dict(), config.model_save_path)

    # 6. Load Best Model & Calibrate Decision Threshold
    model.load_state_dict(torch.load(config.model_save_path, map_location=device))
    model.eval()

    print("Calibrating decision threshold on validation set...")
    val_probs, val_targets = collect_predictions_and_targets(model, val_loader, device)
    if val_probs.size > 0:
        optimal_th, best_val_calibrated_metrics, sweep = calibrate_threshold(val_probs, val_targets)
    else:
        optimal_th = 0.5
        best_val_calibrated_metrics = val_metrics
        sweep = []

    print(f"Optimal Calibrated Threshold: {optimal_th:.4f} (Calibrated Val IoU: {best_val_calibrated_metrics['iou']:.4f})")

    # 7. Evaluate on unseen Test Split
    test_metrics = None
    if len(test_ds) > 0:
        test_metrics, _, _ = evaluate_dataset(model, test_ds, config, device, threshold=optimal_th)
        print(f"Unseen Test Set Evaluation (Threshold={optimal_th:.4f}):")
        print(f"  IoU: {test_metrics['iou']:.4f} | Dice: {test_metrics['dice']:.4f} | Precision: {test_metrics['precision']:.4f} | Recall: {test_metrics['recall']:.4f}")

    # 8. Save Metrics & Metadata
    save_model_metadata(
        output_path=config.metadata_save_path,
        optimal_threshold=optimal_th,
        val_metrics=best_val_calibrated_metrics,
        test_metrics=test_metrics,
        threshold_sweep=sweep,
        config=config
    )

    metrics_output = {
        "history": history,
        "best_val_iou": best_val_iou,
        "best_val_loss": best_val_loss,
        "calibrated_threshold": optimal_th,
        "final_val_metrics": best_val_calibrated_metrics,
        "test_metrics": test_metrics
    }
    with open(config.metrics_save_path, "w") as f:
        json.dump(metrics_output, f, indent=2)

    print("Training pipeline completed successfully.")
    return metrics_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train U-Net on Sentinel-1 SAR Oil Spill Dataset")
    parser.add_argument("--dataset-dir", type=str, default="data/zenodo_oil_spill", help="Path to Zenodo dataset directory")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-model", type=str, default="artifacts/best_model.pth", help="Path to save best checkpoint")
    args = parser.parse_args()

    cfg = SegmentationConfig(
        dataset_dir=args.dataset_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed,
        model_save_path=args.output_model
    )

    try:
        train_segmentation(cfg)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Note: The real Zenodo Sentinel-1 dataset has not been downloaded yet.")
        print("To train on real data, download the dataset into data/zenodo_oil_spill/ and rerun.")
        sys.exit(1)
