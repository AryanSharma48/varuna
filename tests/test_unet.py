import torch
from ml.segmentation.unet import UNet, DiceBCELoss
from ml.evaluation.metrics import calculate_metrics

def test_unet_forward_pass():
    model = UNet(n_channels=2, n_classes=1, bilinear=True)
    model.eval()
    
    # Batch size 2, 2 channels (VV, VH), 128x128 resolution
    x = torch.randn(2, 2, 128, 128)
    with torch.no_grad():
        out = model(x)
        
    assert out.shape == (2, 1, 128, 128)
    assert (out >= 0.0).all() and (out <= 1.0).all()

def test_dice_bce_loss():
    loss_fn = DiceBCELoss()
    preds = torch.tensor([[[[0.8, 0.9], [0.1, 0.2]]]], dtype=torch.float32)
    targets = torch.tensor([[[[1.0, 1.0], [0.0, 0.0]]]], dtype=torch.float32)
    
    loss = loss_fn(preds, targets)
    assert loss.item() >= 0.0
    assert not torch.isnan(loss)

def test_metrics_calculation():
    preds = torch.tensor([[[[0.9, 0.8], [0.1, 0.2]]]])
    targets = torch.tensor([[[[1.0, 1.0], [0.0, 0.0]]]])
    
    metrics = calculate_metrics(preds, targets, threshold=0.5)
    assert metrics["iou"] > 0.8
    assert metrics["f1"] > 0.8
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
