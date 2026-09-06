# SIH 26143 — AI-Powered Oil Spill Investigation & Attribution Platform

> **Leveraging satellite imagery to determine Oil spills at sea along with AIS data correlations to identify vessel responsible for the spill**

[![CI / Pipeline Validation](https://img.shields.io/badge/Pipeline-Verified%20(100%25)-emerald)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20PyTorch%20%7C%20PostGIS-cyan)]()
[![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20TypeScript%20%7C%20Vite-purple)]()
[![PRD Compliance](https://img.shields.io/badge/PRD%20Compliance-Authoritative-blue)]()

---

## 1. Product Overview

SIH 26143 connects fragmented satellite detection, oceanographic dispersion modeling, and AIS maritime traffic intelligence into a unified, uncertainty-aware **investigation and vessel attribution platform**.

Instead of treating detection merely as a binary mask classifier, the system executes an end-to-end evidence fusion workflow:
```text
Sentinel-1 SAR C-Band
        ↓
Image Quality Gate (Contrast, Nodata, Wind regime check)
        ↓
U-Net Oil Spill Segmentation (Dice + BCE Loss, IoU/F1 metrics)
        ↓
Look-Alike Verification (Backscatter damping, Edge sharpness)
        ↓
Spill Morphometrics (Area, Perimeter, Aspect Ratio, PCA Orientation)
        ↓
Temporal Analysis (Spill Age & Origin Window Estimation)
        ↓
Lagrangian Backward Drift (Reverse 500-particle advective-diffusive simulation)
        ↓
Probable Origin Region (50%, 75%, 90% Confidence Probability Contours)
        ↓
Spatial-Temporal AIS Query ("Who Was Here?")
        ↓
Kinematic & Transmission Anomaly Detection (Gaps, Speed drops, Course jumps)
        ↓
Explainable Vessel Attribution Engine (Multi-factor priority ranking)
        ↓
Forward Drift Spread (+6h, +12h, +24h, +48h Horizons)
        ↓
Sensitive Marine Asset Impact Assessment (MPAs, Coastal Fisheries, Harbors, Beaches)
        ↓
Grounded AI Investigation Assistant (Zero-hallucination tool-calling agent)
        ↓
One-Click Auditable Investigation Report
```

---

## 2. Core Architectural Components

### A. Machine Learning & Computer Vision (`ml/`)
- **PyTorch U-Net (`ml/segmentation/unet.py`):** 2-channel input (VV, VH polarizations) -> 1-channel probability output.
- **Combined Dice + BCE Loss:** Robust to extreme background class imbalance in oceanic SAR scenes.
- **Image Quality Gate (`ml/lookalike/quality_gate.py`):** Assesses nodata pixel ratio, dynamic range contrast (dB), and ambient wind speed suitability (3–12 m/s).
- **Look-Alike Classifier (`ml/lookalike/classifier.py`):** Evaluates backscatter damping (6–18 dB) and boundary gradients to rule out biogenic slicks, low-wind zones, and internal waves.

### B. Geospatial & Oceanographic Modeling (`services/drift/`, `services/characterisation/`)
- **Morphometry & Geometry:** Calculates exact spatial area (km²), major/minor axis lengths, aspect ratios, and PCA principal orientation angles.
- **Lagrangian Particle Drift Model:** Advection driven by surface currents + 3% empirical windage vector with stochastic turbulent diffusion random walk ($D = 2.0\text{ m}^2/\text{s}$).

### C. AIS Intelligence & Attribution (`services/ais/`, `services/attribution/`)
- **MarineCadastre Ingestion & Synthetic Generator:** Compatible with MarineCadastre schema, with a deterministic synthetic scenario generator containing controlled ground truth and anomalies.
- **Spatial-Temporal Filter ("Who Was Here?"):** PostGIS indexed spatio-temporal bounding query narrowing all traffic to critical origin vicinity candidates.
- **Rule-Based Anomaly Detector:** Flags AIS transmission outages (>30 mins) while under way, unrealistic acceleration jumps, and sudden course changes.
- **Explainable Attribution Engine:** Transparently weights and decomposes scores:
  $$\text{Score} = w_{\text{prox}} S_{\text{prox}} + w_{\text{time}} S_{\text{time}} + w_{\text{traj}} S_{\text{traj}} + w_{\text{gap}} S_{\text{gap}} + w_{\text{anom}} S_{\text{anom}}$$
  Explicit legal disclaimer: *Investigation priority ranking only; does not establish legal guilt.*

### D. Grounded Assistant & Reports (`services/assistant/`, `services/reports/`)
- **Grounded Assistant:** Executes structured tool calls (`get_incident`, `find_vessels_near_origin`, `get_attribution_breakdown`, `get_forecast_impact`) ensuring zero fabricated coordinates or facts.
- **One-Click Report Generator:** Generates auditable Markdown/PDF reports detailing evidence, timeline, candidate rankings, and methodological limitations.

---

## 3. Quick Start & Execution

### Option A: Local Development Run
```bash
# 1. Start FastAPI Backend
python -m db.seed
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# 2. Start React Frontend
cd apps/web
npm install
npm run dev
```

### Option B: Docker Compose Full Stack
```bash
docker-compose up --build
```
- Web UI: `http://localhost:5173`
- API & Swagger Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/health`

### Option C: Run Automated Pipeline Verification
```bash
# Run complete 14-test suite
pytest -v

# Run 10-step end-to-end investigation workflow
python scripts/verify_workflow.py
```

---

## 4. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | API and service health status |
| `GET` | `/api/v1/incidents` | List all investigation incidents |
| `GET` | `/api/v1/incidents/{id}` | Full incident telemetry, scene, detection, and evidence |
| `POST` | `/api/v1/incidents/{id}/ais/query` | Spatio-temporal "Who Was Here?" query |
| `POST` | `/api/v1/incidents/{id}/ais/replay` | Time-interpolated vessel positions for timeline playback |
| `POST` | `/api/v1/investigation/ask` | Grounded tool-calling AI assistant |
| `POST` | `/api/v1/reports/{id}` | Official formal investigation report generator |

---

## 5. Provenance & SIH Compliance

- **Authoritative PRD:** `SIH_26143_Internal_Round_MVP_PRD.md`
- **Satellite Reference:** Zenodo Sentinel-1 SAR Oil Spill Dataset
- **AIS Format Reference:** MarineCadastre Sample AIS Format
- **Controlled Demo Scenario:** Mumbai Offshore Corridor (`SIH-2026-001`) with prime suspect `PACIFIC VOYAGER` (MMSI: 412356789).
