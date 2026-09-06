import torch
import numpy as np

def calculate_metrics(preds: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5, smooth: float = 1e-6) -> dict[str, float]:
    """
    Calculate IoU, Precision, Recall, F1 Score, and Dice coefficient.
    preds: tensor of shape (B, 1, H, W) or (B, H, W), values in [0, 1]
    targets: tensor of shape (B, 1, H, W) or (B, H, W), binary values 0 or 1
    """
    preds_bin = (preds > threshold).float().view(-1)
    targets_bin = targets.float().view(-1)
    
    true_positive = (preds_bin * targets_bin).sum().item()
    false_positive = (preds_bin * (1.0 - targets_bin)).sum().item()
    false_negative = ((1.0 - preds_bin) * targets_bin).sum().item()
    true_negative = ((1.0 - preds_bin) * (1.0 - targets_bin)).sum().item()
    
    precision = (true_positive + smooth) / (true_positive + false_positive + smooth)
    recall = (true_positive + smooth) / (true_positive + false_negative + smooth)
    f1 = (2 * precision * recall) / (precision + recall + smooth)
    
    intersection = true_positive
    union = true_positive + false_positive + false_negative
    iou = (intersection + smooth) / (union + smooth)
    dice = (2.0 * intersection + smooth) / (preds_bin.sum().item() + targets_bin.sum().item() + smooth)
    
    return {
        "iou": float(iou),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "dice": float(dice),
        "tp": int(true_positive),
        "fp": int(false_positive),
        "fn": int(false_negative),
        "tn": int(true_negative)
    }
