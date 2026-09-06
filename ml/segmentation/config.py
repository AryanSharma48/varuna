from dataclasses import dataclass, field
from typing import Tuple, Optional

@dataclass
class SegmentationConfig:
    """Configuration for SAR Oil Spill Segmentation training and inference."""
    
    # Tiling for inference
    tile_size: int = 1024
    overlap: int = 256
    
    # Training hyperparameters
    batch_size: int = 4
    learning_rate: float = 1e-4
    epochs: int = 20
    num_workers: int = 0
    weight_decay: float = 1e-5
    
    # Calibrated decision threshold (default 0.5 until calibrated)
    threshold: float = 0.5
    
    # Normalization percentiles for SAR stretch
    norm_p2: float = 2.0
    norm_p98: float = 98.0
    
    # Architecture
    in_channels: int = 2
    out_classes: int = 1
    bilinear: bool = True
    
    # Deterministic dataset splitting
    seed: int = 42
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    
    # Paths
    dataset_dir: str = "data/zenodo_oil_spill"
    artifacts_dir: str = "artifacts"
    model_save_path: str = "artifacts/best_model.pth"
    metadata_save_path: str = "artifacts/model_metadata.json"
    metrics_save_path: str = "artifacts/training_metrics.json"
    splits_save_path: str = "artifacts/dataset_splits.json"
