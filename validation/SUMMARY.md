# VARUNA Validation Summary: Real Metrics & Benchmark Audit

**Project:** VARUNA — Automated Sentinel-1 Oil Spill Detection, Lagrangian Backtracking & Vessel Attribution  
**Commit Hash:** `55b3bf873f055259c5bb7568ba54a02ab7d446d8`  
**Execution Timestamp:** 2026-10-05T20:47:00+05:30  
**Hardware Used:** AMD Ryzen 7 7435HS (8 Cores, 16 Logical Processors, Windows 11)  
**Software Stack:** PyTorch 2.12.0+cpu, OpenDrift 1.14.11, Python 3.14  
**Raw Metrics Output File:** [`validation/metrics.json`](file:///c:/Users/Aryan%20Sharma/Desktop/sih/validation/metrics.json)

---

## 1. Reproduction Commands

To reproduce every metric reported below from scratch on any machine:

```bash
# 1. Evaluate U-Net segmentation on the clean held-out test set
python validation/evaluate_task1_segmentation.py

# 2. Run OpenDrift synthetic forward-backward recovery test (20 runs)
python validation/run_drift_synthetic_test.py

# 3. Run AIS ranking sanity check & dark vessel ablation
python validation/run_task3_ais_sanity_check.py
```

---

## 2. TASK 1: U-Net Segmentation Metrics

### Dataset & Checkpoint Metadata
* **Dataset:** Refined Deep-SAR Oil Spill (SOS) — [Zenodo Record 15298010](https://doi.org/10.5281/zenodo.15298010)
* **Sensor Sources:** Dual-sensor SAR patches (Sentinel-1 C-band & ALOS PALSAR L-band)
* **Input Channels:** 2 channels (Dual SAR representation `[sar_norm, sar_norm]` from VV backscatter stretched `[0.0, 1.0]`)
* **Resolution:** $256 \times 256$ pixels
* **Checkpoint Evaluated:** [`models/checkpoints/oil_spill_unet_best.pt`](file:///c:/Users/Aryan%20Sharma/Desktop/sih/models/checkpoints/oil_spill_unet_best.pt) (53.63 MB, 4-level DoubleConv U-Net with bilinear upsampling)
* **Decision Threshold:** $\tau = 0.5000$ (Optimal threshold calibrated strictly on validation split)

### Data Leakage & Split Audit
* **Total Patches in Benchmark:** 8,070 patches
  * Train Split: 6,455 patches (80.0%)
  * Validation Split: 807 patches (10.0%)
  * Held-Out Test Split: 808 patches (10.0%)
* **Leakage Verification:** 
  * Path and exact MD5 file collision between `train`, `val`, and `test`: **0 duplicate images**.
  * **Scene-Level Splitting Audit:** The Zenodo 15298010 benchmark package contains pre-extracted $256 \times 256$ PNG tiles renamed sequentially (`palsar_X.png`, `sentinel_X.png`). The dataset authors **did not publish** the underlying raw Sentinel-1/PALSAR acquisition SAFE product identifiers, orbit numbers, or geospatial tile footprints. Therefore, strict geographic scene-level partitioning is impossible to reconstruct from this public benchmark. The test set evaluated is an **untouched held-out patch partition** (half of the official test/val set) evaluated only once.

### Held-Out Test Set Performance (808 Patches, 52,953,088 Pixels)
| Class | Metric | Real Value | Notes / Slide Formulation |
| :--- | :--- | :--- | :--- |
| **Oil Spill** | **IoU (Jaccard Index)** | **70.77%** (0.7077) | Primary segmentation overlap on true oil slick pixels |
| **Oil Spill** | **Dice / F1 Score** | **82.88%** (0.8288) | Harmonic mean of precision and recall |
| **Oil Spill** | **Precision** | **80.86%** (0.8086) | 12,111,751 True Positives vs 2,866,486 False Positives |
| **Oil Spill** | **Recall** | **85.01%** (0.8501) | Detected 85% of ground-truth oil pixels across 808 test scenes |
| **Oil Spill** | **Pixel Accuracy** | **90.55%** (0.9055) | Pixel-level classification accuracy |
| **Background (Water)**| **IoU** | **87.75%** (0.8775) | Non-oil marine background overlap |
| **Background (Water)**| **Dice / F1** | **93.48%** (0.9348) | Background pixel identification |
| **Overall Multi-Class**| **mIoU** | **79.26%** (0.7926) | Mean IoU across both classes |
| **Overall Multi-Class**| **mDice** | **88.18%** (0.8818) | Mean Dice across both classes |

### Confusion Matrix (Pixel-Level)
* **True Positives (TP):** 12,111,751 pixels
* **False Positives (FP):** 2,866,486 pixels
* **True Negatives (TN):** 35,839,068 pixels
* **False Negatives (FN):** 2,135,783 pixels
* **Total Evaluated Pixels:** 52,953,088 pixels

### False-Positive Behavior on Look-Alike / Zero-Oil Patches
* **Zero-Oil (Pure Negative / Look-Alike) Test Patches:** 29 patches (3.59% of test set, 1,900,544 pixels)
* **False-Positive Oil Pixels in Zero-Oil Patches:** 960 pixels out of 1,900,544 total pixels
* **Pixel-Level False Positive Rate (FPR):** **0.05%** ($0.0005$)
* **Patch-Level Specificity:** 22 out of 29 zero-oil patches (75.86%) had **zero false alarms** (perfect 100% specificity).
* **Multi-Class Mask Labels:** Refined Deep-SAR masks are binary $\{0, 255\}$. Distinct categorical labels for ship, land, and look-alikes are **absent** from this ground-truth dataset; look-alike discrimination is handled via the Stage-2 physical gating engine.

### Inference Speed & Hardware
* **Hardware:** AMD Ryzen 7 7435HS (8 Cores / 16 Threads, CPU mode)
* **Total Test Evaluation Time (808 patches):** 223.82 s
* **Average Inference Latency:** **277.00 ms / patch** (Throughput: **3.61 FPS**)

---

## 3. TASK 2: OpenDrift Backtracking Recovery Test

### OpenDrift Configuration
* **Engine:** OpenDrift `OpenOil` v1.14.11
* **Environmental Forcing:** Copernicus Marine CMEMS (`uo`, `vo` hourly surface currents) + ECMWF ERA5 (`u10`, `v10` hourly 10m wind fields)
* **Ensemble Configuration:** $N = 100$ Lagrangian oil particles per simulation, 15-minute advection timestep, turbulent horizontal diffusion random walk.

### Synthetic Recovery Test Protocol (Clearly Labeled: SYNTHETIC VALIDATION)
* **Test Architecture:** 
  1. Forward simulation of oil release from known ground-truth coordinates $(lon_0, lat_0)$ at $t_0$ for 6 hours under dynamic current and wind forcing.
  2. The resulting drifted slick particles at $t_0 + 6\text{h}$ are extracted as the "observed satellite slick".
  3. The ensemble is backtracked backward in time (negative time-step $\Delta t = -15\text{ min}$) for 6 hours to recover the release location at $t_0$.
  4. Centroid error and containment within the 50% and 90% ensemble probability contours are recorded.
* **Repetitions:** 20 distinct randomized spatial points and release timestamps across the Mediterranean Sea domain.

### Synthetic Test Results (20 Runs)
| Metric | Real Output | Note |
| :--- | :--- | :--- |
| **Mean Centroid Error** | **0.2065 km (206.5 m)** | Mean distance between true origin and ensemble centroid |
| **Median Centroid Error** | **0.2038 km (203.8 m)** | Robust median tracking error |
| **Worst-Case Error** | **0.4494 km (449.4 m)** | Maximum error encountered across all 20 scenarios |
| **Best-Case Error** | **0.0575 km (57.5 m)** | Minimum recovery error |
| **Standard Deviation** | **0.1044 km (104.4 m)** | Error consistency across diverse current/wind regimes |
| **50% Confidence Containment** | **18 / 20 (90.0%)** | True origin fell inside the 50% probability contour |
| **90% Confidence Containment** | **20 / 20 (100.0%)** | True origin fell inside the 90% probability contour in every single run |
| **Average Net Drift Distance** | **2.82 km** | Forward advection distance before recovery |

### Real-Case Backtest (Ennore Collision, Jan 2017)
> [!IMPORTANT]
> **Data Availability Audit:** As mandated by strict empirical verification standards, **no synthetic or guessed inputs were used for Ennore 2017**. To run this historic case, the following external data must be supplied:
> 1. **Incident Ground Truth:** Collision time (Jan 28, 2017 ~03:45–04:00 AM IST / Jan 27 22:15 UTC) and location off Kamarajar Port (13.26° N, 80.36° E) involving MT *Dawn Kanchipuram* and *BW Maple*.
> 2. **Sentinel-1 SAR Scene:** Sentinel-1 C-SAR IW GRDH product (SAFE archive) covering Ennore/Chennai coast post-collision (e.g. Jan 28 or Jan 29, 2017). *(Current repo only contains Eastern Med demo scenes).*
> 3. **Copernicus Marine CMEMS Forcing:** Bay of Bengal hourly surface current reanalysis (`GLOBAL_MULTIYEAR_PHY_001_030`) for Jan 26–Feb 5, 2017.
> 4. **ECMWF ERA5 Atmospheric Forcing:** ERA5 hourly 10m wind vector components (`u10`, `v10`) for 12.0°–14.5° N, 79.5°–82.0° E.
> 5. **Historical AIS Records:** Bay of Bengal vessel tracking feeds with MMSI, coordinates, SOG, COG, and timestamps.
> 
> **Can the code run with them?** **YES.** `scripts/simulate_origin_backtrack.py` and `validation/run_drift_synthetic_test.py` accept standard CF NetCDF files (`currents.nc`, `winds.nc`) and AIS GeoJSON directly. Once these 5 files are placed in an incident folder, the pipeline executes end-to-end.

---

## 4. TASK 3: AIS Ranking Sanity Check

Evaluated the multi-evidence attribution ranking engine (`VesselAttributionEngine` in `services/attribution/engine.py`) across two test cases:

### Case A: Planted Source Vessel Benchmark (`PACIFIC VOYAGER`)
A synthetic busy shipping lane scenario where crude oil tanker `PACIFIC VOYAGER` (MMSI 412356789) is planted as the true discharging vessel with an intentional 40-minute AIS transmission blackout, speed drop (14.2 to 6.1 kts), and 45° course deviation:

| Rank | Vessel Name | Vessel Type | Total Score (/100) | Priority Level | Proximity (30) | Timing (25) | Trajectory (20) | AIS Gap (15) | Anomaly (10) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **#1** | **PACIFIC VOYAGER** *(Planted Source)* | Crude Oil Tanker | **74.8** | **HIGH** | **30.0** (1.4 km) | 0.0 | **19.8** (aligned 48.8°) | **15.0** (outage) | **10.0** (speed/course) |
| #2 | SAGAR RATNA | Offshore Supply | 35.2 | LOW | 1.7 | 21.4 | 12.1 | 0.0 | 0.0 |
| #3 | NORDIC TRADER | Container Ship | 19.7 | LOW | 10.8 | 0.0 | 8.9 | 0.0 | 0.0 |
| #4 | OCEAN EXPLORER | Bulk Carrier | 13.4 | LOW | 5.2 | 0.0 | 8.2 | 0.0 | 0.0 |
| #5 | MATSYA RANI | Fishing Vessel | 12.7 | LOW | 0.0 | 2.6 | 10.1 | 0.0 | 0.0 |

* **Planted Source Identification:** Identified at **Rank #1** with a clear score margin of +39.6 points over the nearest candidate.

### Case B: AIS Gap Ablation Analysis
* `PACIFIC VOYAGER` Score **WITH** AIS Gap: **74.8 / 100**
* `PACIFIC VOYAGER` Score **WITHOUT** AIS Gap: **59.8 / 100**
* **Score Delta:** Exactly **+15.0 points** assigned by the unannounced AIS blackout anomaly, elevating the vessel from MEDIUM to HIGH investigation priority.

### Case C: Incident 001 Real Demonstration Sample AIS
In the demonstration incident (Eastern Mediterranean DARTIS ow-0388), tanker `MT AL NAJAF` (MMSI 636018245) exhibits a 22-minute AIS blackout:
* **Rank #1:** `MT AL NAJAF` — Score: **78.8 / 100 [HIGH]** (Prox=18.9, Time=25.0, Traj=19.9, AIS Gap=15.0)
* **Rank #2:** `MT LEVANT STAR` — Score: **72.7 / 100 [HIGH]** (Prox=30.0, Time=25.0, Traj=12.7, Anom=5.0)
* **Rank #3:** `MV MEDITERRANEAN EXPRESS` — Score: **47.5 / 100 [MEDIUM]** (Prox=10.7, Time=25.0, Traj=11.8)

---

## 5. Slide-Ready Numbers vs. Missing Data

| Category | Real Number Safe For Slides | Status / Source | What Was Missing / Honest Limitation |
| :--- | :--- | :--- | :--- |
| **Segmentation IoU** | **70.77%** (Oil Class) | Verified | Evaluated on 808 held-out test patches |
| **Segmentation Dice / F1** | **82.88%** (Oil Class) | Verified | Harmonic mean of 80.86% precision, 85.01% recall |
| **Segmentation Precision** | **80.86%** | Verified | 12.11M True Positive pixels / 2.87M False Positive pixels |
| **Segmentation Recall** | **85.01%** | Verified | 12.11M True Positive pixels / 2.14M False Negative pixels |
| **Mean IoU (mIoU)** | **79.26%** | Verified | Mean of Oil IoU (70.77%) and Background IoU (87.75%) |
| **Look-Alike False Alarms**| **0.05%** pixel FPR (75.9% patch specificity)| Verified | 960 false-alarm pixels across 1.90M zero-oil pixels |
| **Inference Latency** | **277.0 ms / patch** (3.61 FPS) | Verified | Measured on AMD Ryzen 7 7435HS (8 Cores, CPU mode) |
| **Drift Recovery Centroid Error** | **206.5 m (Mean)** / **203.8 m (Median)** | Verified (Synthetic) | Evaluated over 20 random OpenOil simulations |
| **Drift Worst-Case Error** | **449.4 m** | Verified (Synthetic) | Maximum error over 20 randomized runs |
| **Drift 90% Probability Region** | **100.0% Containment** (20/20 runs) | Verified (Synthetic) | True release point inside 90% contour in all runs |
| **AIS Source Identification**| **Rank #1 (74.8/100 score)** | Verified | Planted tanker identified with +39.6 pt margin |
| **AIS Gap Attribution Impact**| **+15.0 points** score delta | Verified | Direct penalty for unannounced blackout |
| *Categorical Ship/Land IoU* | *Could NOT produce* | Missing in Data | Refined Deep-SAR SOS only has binary $\{0, 255\}$ masks |
| *True Scene-Level Partition*| *Could NOT produce* | Missing in Data | Zenodo 15298010 omitted acquisition SAFE IDs and coordinates |
| *Ennore 2017 Real Backtest* | *Could NOT produce* | Missing in Data | Bay of Bengal Jan 2017 S-1, CMEMS, ERA5, AIS not in repo |
