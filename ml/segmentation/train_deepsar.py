"""
Training, Validation, and Evaluation Pipeline for Refined Deep-SAR Oil Spill (SOS) U-Net.
"""

import os
import sys
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from PIL import Image
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import CosineAnnealingLR
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.segmentation.unet import UNet, DiceBCELoss
from ml.segmentation.deepsar_dataset import DeepSARDataset, load_deepsar_splits
from ml.segmentation.evaluate import compute_confusion_matrix, compute_metrics_from_cm


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: Optional[torch.cuda.amp.GradScaler],
    device: torch.device
) -> float:
    model.train()
    running_loss = 0.0
    num_batches = 0

    use_amp = (scaler is not None) and (device.type == "cuda")

    for images, masks in dataloader:
        images = images.to(device, non_blocking=True)
        masks = masks.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        if use_amp:
            with torch.amp.autocast("cuda"):
                preds = model(images)
            loss = criterion(preds.float(), masks.float())
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            preds = model(images)
            loss = criterion(preds, masks)
            loss.backward()
            optimizer.step()

        running_loss += loss.item()
        num_batches += 1

    return running_loss / max(1, num_batches)


def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, np.ndarray, np.ndarray]:
    model.eval()
    running_loss = 0.0
    num_batches = 0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, masks in dataloader:
            images = images.to(device, non_blocking=True)
            masks = masks.to(device, non_blocking=True)

            preds = model(images)
            loss = criterion(preds, masks)
            running_loss += loss.item()
            num_batches += 1

            all_preds.append(preds.cpu().numpy())
            all_targets.append(masks.cpu().numpy())

    val_loss = running_loss / max(1, num_batches)
    preds_concat = np.concatenate(all_preds, axis=0) if all_preds else np.empty((0,))
    targets_concat = np.concatenate(all_targets, axis=0) if all_targets else np.empty((0,))
    return val_loss, preds_concat, targets_concat


def calibrate_threshold_on_val(
    val_probs: np.ndarray,
    val_targets: np.ndarray,
    steps: int = 19
) -> Tuple[float, Dict[str, float]]:
    thresholds = np.linspace(0.10, 0.90, steps)
    best_iou = -1.0
    best_th = 0.5
    best_metrics = {}

    for th in thresholds:
        bin_preds = (val_probs >= th).astype(np.uint8)
        bin_targets = (val_targets >= 0.5).astype(np.uint8)
        cm = compute_confusion_matrix(bin_preds, bin_targets)
        metrics = compute_metrics_from_cm(cm)
        if metrics["iou"] > best_iou:
            best_iou = metrics["iou"]
            best_th = float(th)
            best_metrics = metrics

    return best_th, best_metrics


def run_training(
    epochs: int = 15,
    batch_size: int = 16,
    lr: float = 1e-4,
    seed: int = 42,
    sanity_only: bool = False,
    checkpoint_dir: str = "models/checkpoints"
) -> Dict[str, Any]:
    set_seed(seed)
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs("artifacts/segmentation/evaluation", exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Training] Using compute device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # 1. Load Dataset Splits
    splits = load_deepsar_splits()
    print(f"[Dataset] Splits loaded: {len(splits['train'])} train, {len(splits['val'])} val, {len(splits['test'])} test")

    train_dataset = DeepSARDataset(splits["train"], augment=True)
    val_dataset = DeepSARDataset(splits["val"], augment=False)
    test_dataset = DeepSARDataset(splits["test"], augment=False)

    num_workers = 2 if device.type == "cuda" else 0
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=(device.type == "cuda"))
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=(device.type == "cuda"))
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=(device.type == "cuda"))

    # 2. Instantiate Model
    model = UNet(n_channels=2, n_classes=1, bilinear=True).to(device)
    criterion = DiceBCELoss(bce_weight=0.5)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    scaler = torch.amp.GradScaler("cuda") if device.type == "cuda" else None

    best_checkpoint_path = os.path.join(checkpoint_dir, "oil_spill_unet_best.pt")

    if sanity_only:
        print("[Sanity Run] Executing 1 sanity epoch...")
        t0 = time.time()
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, scaler, device)
        val_loss, val_probs, val_targets = evaluate_model(model, val_loader, criterion, device)
        dt = time.time() - t0

        print(f"[Sanity Run] Finished in {dt:.1f}s | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        assert not np.isnan(train_loss) and not np.isnan(val_loss), "Loss is NaN!"

        sanity_pt = os.path.join(checkpoint_dir, "sanity_test.pt")
        torch.save(model.state_dict(), sanity_pt)
        assert os.path.exists(sanity_pt), "Sanity checkpoint save failed!"
        print(f"[Sanity Run] Checkpoint verified at {sanity_pt}. Sanity test PASSED.")
        return {"status": "SANITY_PASSED", "train_loss": train_loss, "val_loss": val_loss}

    # 3. Full Training Loop
    print(f"[Training] Starting training for up to {epochs} epochs (patience=3)...", flush=True)
    best_val_loss = float("inf")
    best_val_iou = 0.0
    epochs_without_improvement = 0
    history = []

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, scaler, device)
        val_loss, val_probs, val_targets = evaluate_model(model, val_loader, criterion, device)
        scheduler.step()
        dt = time.time() - t0

        # Calibrate threshold on validation probabilities
        val_th, val_metrics = calibrate_threshold_on_val(val_probs, val_targets)
        val_iou = val_metrics["iou"]

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_iou": val_iou,
            "val_dice": val_metrics["dice"],
            "val_threshold": val_th,
            "time_sec": round(dt, 2)
        })

        improved = False
        if val_loss < best_val_loss or val_iou > best_val_iou:
            best_val_loss = min(val_loss, best_val_loss)
            best_val_iou = max(val_iou, best_val_iou)
            torch.save(model.state_dict(), best_checkpoint_path)
            improved = True
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        print(
            f"Epoch [{epoch:02d}/{epochs:02d}] ({dt:.1f}s) "
            f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | "
            f"Val IoU: {val_iou:.4f} | Val Dice: {val_metrics['dice']:.4f} (th={val_th:.2f})"
            f"{' [SAVED BEST]' if improved else ''}",
            flush=True
        )

        if epochs_without_improvement >= 3 and epoch >= 5:
            print(f"[Training] Early stopping triggered after {epoch} epochs (validation metric plateaued).", flush=True)
            break

    # 4. Load Best Model Checkpoint for Final Untouched Test Evaluation
    print(f"\n[Evaluation] Loading best checkpoint for final evaluation on UNTOUCHED test split...")
    model.load_state_dict(torch.load(best_checkpoint_path, map_location=device))
    model.eval()

    # Calibrate optimal threshold strictly on validation set
    _, val_probs, val_targets = evaluate_model(model, val_loader, criterion, device)
    calibrated_th, best_val_metrics = calibrate_threshold_on_val(val_probs, val_targets)
    print(f"[Evaluation] Optimal Calibrated Threshold from Validation: {calibrated_th:.4f}")
    print(f"[Evaluation] Validation Metrics @ th={calibrated_th:.4f}: IoU={best_val_metrics['iou']:.4f}, Dice={best_val_metrics['dice']:.4f}, F1={best_val_metrics['dice']:.4f}")

    # Evaluate on untouched test split
    test_loss, test_probs, test_targets = evaluate_model(model, test_loader, criterion, device)
    test_cm = compute_confusion_matrix((test_probs >= calibrated_th).astype(np.uint8), (test_targets >= 0.5).astype(np.uint8))
    test_metrics = compute_metrics_from_cm(test_cm)
    print(
        f"[Evaluation] Untouched Test Set Metrics:\n"
        f"  IoU:       {test_metrics['iou']:.4f}\n"
        f"  Dice (F1): {test_metrics['dice']:.4f}\n"
        f"  Precision: {test_metrics['precision']:.4f}\n"
        f"  Recall:    {test_metrics['recall']:.4f}\n"
        f"  Accuracy:  {test_metrics['accuracy']:.4f}\n"
        f"  Confusion Matrix: TP={test_cm['tp']}, FP={test_cm['fp']}, TN={test_cm['tn']}, FN={test_cm['fn']}"
    )

    # 5. Generate Test Set Prediction-vs-Ground-Truth Overlays
    print("[Evaluation] Generating visual overlays on test samples...")
    for i in range(min(6, len(splits["test"]))):
        sample = splits["test"][i]
        with Image.open(sample["image_path"]) as img_pil:
            arr_img = np.array(img_pil)
            sar_img = arr_img[:, :, 0] if arr_img.ndim == 3 else arr_img
        with Image.open(sample["mask_path"]) as msk_pil:
            arr_msk = np.array(msk_pil)
            msk_2d = arr_msk[:, :, 0] if arr_msk.ndim == 3 else arr_msk
            gt_mask = (msk_2d >= 128).astype(np.float32)

        pred_prob = test_probs[i, 0]
        pred_bin = (pred_prob >= calibrated_th).astype(np.float32)

        fig, axes = plt.subplots(1, 4, figsize=(16, 4))
        axes[0].imshow(sar_img, cmap="gray")
        axes[0].set_title(f"SAR Input\n{sample['filename']}", fontsize=10)
        axes[0].axis("off")

        axes[1].imshow(gt_mask, cmap="hot", vmin=0, vmax=1)
        axes[1].set_title("Ground Truth Mask", fontsize=10)
        axes[1].axis("off")

        axes[2].imshow(pred_prob, cmap="viridis", vmin=0, vmax=1)
        axes[2].set_title("U-Net Probability Map", fontsize=10)
        axes[2].axis("off")

        axes[3].imshow(pred_bin, cmap="hot", vmin=0, vmax=1)
        axes[3].set_title(f"Predicted Binary Mask (th={calibrated_th:.2f})", fontsize=10)
        axes[3].axis("off")

        plt.tight_layout()
        overlay_out = f"artifacts/segmentation/evaluation/test_sample_{i+1}_{sample['filename']}"
        plt.savefig(overlay_out, dpi=150)
        plt.close()

    # 6. Save Model Metadata JSON
    metadata = {
        "dataset": "Refined Deep-SAR Oil Spill (SOS) - Zenodo 15298010",
        "image_channels": "2 (Dual SAR representation [sar_norm, sar_norm])",
        "input_resolution": [256, 256],
        "preprocessing": "Normalized linear stretch [0.0, 1.0] (sar_band / 255.0)",
        "architecture": "U-Net (Standard 4-level encoder-decoder with bilinear upsampling)",
        "encoder": "DoubleConv (64 -> 128 -> 256 -> 512 -> 512)",
        "loss": "DiceBCELoss (0.5 * BCE + 0.5 * Dice)",
        "optimizer": "AdamW",
        "learning_rate": lr,
        "batch_size": batch_size,
        "epochs": epochs,
        "seed": seed,
        "device": str(device),
        "calibrated_threshold": calibrated_th,
        "validation_metrics": best_val_metrics,
        "test_metrics": test_metrics,
        "training_history": history,
        "checkpoint_file": best_checkpoint_path
    }

    metadata_path = os.path.join(checkpoint_dir, "oil_spill_unet_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Metadata] Saved full training metadata to {metadata_path}")

    return metadata


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--sanity", action="store_true")
    args = parser.parse_args()

    run_training(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, sanity_only=args.sanity)
