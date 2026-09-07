"""
Evaluate the trained oil_spill_unet_best.pt checkpoint on the untouched test split,
generate evaluation overlays, and save oil_spill_unet_metadata.json.
"""

import os
import sys
import json
from pathlib import Path
from PIL import Image
import numpy as np
import torch
from torch.utils.data import DataLoader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.segmentation.unet import UNet, DiceBCELoss
from ml.segmentation.deepsar_dataset import DeepSARDataset, load_deepsar_splits
from ml.segmentation.evaluate import compute_confusion_matrix, compute_metrics_from_cm
from ml.segmentation.train_deepsar import evaluate_model, calibrate_threshold_on_val, set_seed


def main():
    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Evaluation] Device: {device}")

    checkpoint_path = "models/checkpoints/oil_spill_unet_best.pt"
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}")

    splits = load_deepsar_splits()
    print(f"[Dataset] Test split: {len(splits['test'])} samples | Val split: {len(splits['val'])} samples")

    val_dataset = DeepSARDataset(splits["val"], augment=False)
    test_dataset = DeepSARDataset(splits["test"], augment=False)

    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False, num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False, num_workers=2, pin_memory=True)

    model = UNet(n_channels=2, n_classes=1, bilinear=True).to(device)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.eval()

    criterion = DiceBCELoss(bce_weight=0.5)

    # 1. Calibrate threshold strictly on validation split
    print("[Evaluation] Calibrating optimal threshold on validation set...")
    val_loss, val_probs, val_targets = evaluate_model(model, val_loader, criterion, device)
    calibrated_th, best_val_metrics = calibrate_threshold_on_val(val_probs, val_targets)
    print(f"[Evaluation] Optimal Calibrated Threshold: {calibrated_th:.4f}")
    print(f"[Evaluation] Validation Metrics: IoU={best_val_metrics['iou']:.4f}, Dice={best_val_metrics['dice']:.4f}")

    # 2. Evaluate on untouched test split
    print("[Evaluation] Evaluating on untouched test split...")
    test_loss, test_probs, test_targets = evaluate_model(model, test_loader, criterion, device)
    test_bin = (test_probs >= calibrated_th).astype(np.uint8)
    target_bin = (test_targets >= 0.5).astype(np.uint8)

    test_cm = compute_confusion_matrix(test_bin, target_bin)
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

    # 3. Generate Visual Overlays
    os.makedirs("artifacts/segmentation/evaluation", exist_ok=True)
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
        print(f"  -> Saved overlay: {overlay_out}")

    # 4. Save metadata JSON
    metadata = {
        "dataset": "Refined Deep-SAR Oil Spill (SOS) - Zenodo 15298010",
        "image_channels": "2 (Dual SAR representation [sar_norm, sar_norm])",
        "input_resolution": [256, 256],
        "preprocessing": "Normalized linear stretch [0.0, 1.0] (sar_band / 255.0)",
        "architecture": "U-Net (Standard 4-level encoder-decoder with bilinear upsampling)",
        "encoder": "DoubleConv (64 -> 128 -> 256 -> 512 -> 512)",
        "loss": "DiceBCELoss (0.5 * BCE + 0.5 * Dice)",
        "optimizer": "AdamW",
        "learning_rate": 1e-4,
        "batch_size": 16,
        "epochs_trained": 6,
        "seed": 42,
        "device": str(device),
        "calibrated_threshold": calibrated_th,
        "validation_metrics": best_val_metrics,
        "test_metrics": test_metrics,
        "checkpoint_file": checkpoint_path
    }

    metadata_path = "models/checkpoints/oil_spill_unet_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Metadata] Saved full training metadata to {metadata_path}")


if __name__ == "__main__":
    main()
