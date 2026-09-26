# VARUNA SAR Image Processing & Dark-Feature Candidate Visualization Experiment

## Overview

This is a **standalone SAR image processing and candidate detection experiment** for Project **VARUNA**.

> **SCIENTIFIC DISCLAIMER:**
> - This script generates a **SAR-based candidate mask / prototype visualization**.
> - It is **NOT** a U-Net prediction and does **NOT** use deep-learning inference.
> - It is **NOT** a confirmed oil-spill classifier.
> - The output is an empirical candidate detection heuristic derived from Sentinel-1 radar backscatter physics and local spatial texture.

---

## 1. Input Data

The experiment uses the Copernicus Sentinel-1 Ground Range Detected (GRD) Interferometric Wide (IW) swath scene:
- `001.tiff`: **VH** polarization (linear DN amplitude, `uint16`)
- `002.tiff`: **VV** polarization (linear DN amplitude, `uint16`)

Georeferencing is preserved using the 210 Ground Control Points (GCPs) referenced to EPSG:4326.

---

## 2. Processing Pipeline

The experiment executes the following steps in sequence:

1. **TIFF Metadata Inspection**:
   - Inspects dimensions, bit depth, coordinate system, GCPs, nodata, and band counts using `rasterio`.
2. **SAR &rarr; dB Calibration**:
   - Applies standard radiometric conversion: $\text{SAR}_{\text{dB}} = 20 \cdot \log_{10}(\max(\text{DN}, 10^{-5}))$.
   - Reuses `services.satellite.processor.convert_sar_to_db` from the VARUNA pipeline.
3. **Robust Normalization**:
   - Calculates 2nd and 98th percentiles ($p_2, p_{98}$) in the dB domain.
   - Clips values to $[p_2, p_{98}]$ to eliminate speckle spikes and normalizes linearly to $[0.0, 1.0]$.
4. **Multi-Polarization VV/VH Fusion**:
   - Combines co-polarized VV (primary surface roughness indicator) with cross-polarized VH (volume dampening coherence).
   - Generates a combined dark-feature score heuristic: $S_{\text{dark}} = 0.65 \cdot (1 - \text{VV}_{\text{norm}}) + 0.35 \cdot (1 - \text{VH}_{\text{norm}})$.
5. **Local Adaptive Thresholding**:
   - Estimates ambient sea clutter using a wide spatial kernel ($81 \times 81$ pixels).
   - Computes local backscatter contrast $\Delta_{\text{contrast}} = S_{\text{dark}} - S_{\text{ambient}}$.
   - Detects candidate dark regions exhibiting both high dampening and statistically significant local contrast.
6. **Conservative Morphological Cleanup**:
   - Applies morphological opening with a $3 \times 3$ elliptical kernel to eliminate isolated speckle noise.
   - Applies morphological closing with a $5 \times 5$ elliptical kernel to bridge micro-gaps while preserving natural irregular boundaries.
7. **Connected-Component Analysis & Physics-Based Ranking**:
   - Evaluates each connected region for:
     - Area ($A$)
     - Bounding box $(y, x, h, w)$
     - Centroid $(\bar{y}, \bar{x})$
     - Aspect ratio ($\text{AR} = \max(w, h) / \min(w, h)$)
     - Boundary perimeter ($P$)
     - Compactness ($C = 4\pi A / P^2$)
     - Mean backscatter in Decibels
     - Local ambient contrast ($\Delta_{\text{dB}}$)
   - Ranks candidate regions favoring large, elongated, high-contrast irregular features typical of marine slicks.
8. **Visualization & Output Generation**:
   - Saves individual high-resolution PNGs for each pipeline step.
   - Generates a full composite pipeline diagram (`10_processing_pipeline.png`).
   - Exports the georeferenced binary mask as a GeoTIFF (`candidate_mask.tif`).

---

## 3. Directory Structure

```
tools/sar_mask_experiment/
├── process_sar_demo.py     # Main standalone execution script
├── README.md               # Scientific & operational documentation
└── outputs/                # Generated visualizations & GeoTIFF
    ├── 01_vh_raw.png
    ├── 02_vv_raw.png
    ├── 03_vh_db.png
    ├── 04_vv_db.png
    ├── 05_vh_normalized.png
    ├── 06_vv_normalized.png
    ├── 07_dark_candidate.png
    ├── 08_cleaned_mask.png
    ├── 09_final_overlay.png
    ├── 10_processing_pipeline.png
    ├── candidate_mask.tif
    └── summary_report.txt
```

---

## 4. How to Run

Execute from the repository root using the virtual environment:

```bash
.venv\Scripts\python tools/sar_mask_experiment/process_sar_demo.py
```

### Optional Arguments:
- `--vh PATH`: Explicit path to VH TIFF (defaults to `satellite-data/001.tiff`)
- `--vv PATH`: Explicit path to VV TIFF (defaults to `satellite-data/002.tiff`)
- `--output-dir PATH`: Target output directory (defaults to `tools/sar_mask_experiment/outputs`)
- `--top-candidates N`: Number of top candidate components to select (default: `2`)
- `--min-area N`: Minimum pixel count to filter speckle artifacts (default: `1000`)
