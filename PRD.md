# VARUNA — AI-Powered Maritime Oil Spill Investigation & Attribution Platform
## Technical Architecture & Product Requirements Document (PRD)

**Version:** 1.1  
**Target:** Maritime Environmental Protection & Autonomous Polluter Identification  
**Problem Statement:** Leveraging satellite SAR imagery to determine oil spills at sea along with AIS trajectory correlations to identify vessels responsible for marine spills  
**Primary objective:** Build a reliable, demonstrable end-to-end investigation workflow for maritime surveillance and polluter attribution.

---

# 0. Document Status and Source-of-Truth Rules

This PRD is the implementation source of truth for the platform MVP.

## 0.1 System Domain & Mission Scope

The operational mission specifies:
- satellite imagery for oil-spill detection;
- AIS data correlation;
- MarineCadastre sample AIS data as the AIS-format reference;
- real AIS may be used if available;
- synthetic AIS may be prepared for the spill region if real AIS is unavailable;
- Sentinel-1 SAR Oil Spill Dataset on Zenodo as the satellite-imagery dataset reference.

## 0.2 Important dataset interpretation rule

Do NOT claim that a particular train/validation/test split, a particular Zenodo subset, a particular AIS provider beyond the stated MarineCadastre reference, or a particular environmental dataset is mandated unless the source explicitly specifies so.

The detailed dataset structure described elsewhere in this PRD is an **implementation plan**.

## 0.3 Product positioning

The product is not merely an oil-spill classifier and is not an automatic legal accusation engine.

The internal-round MVP is an **uncertainty-aware maritime investigation platform** connecting:

> Satellite evidence → oil/look-alike verification → spill characterisation → origin reconstruction → AIS investigation → vessel attribution → future drift → impact assessment → investigator explanation → report

Central positioning:

> **From “Possible Spill” to “Actionable Investigation.”**

The system ranks vessels for investigation. It must never claim that a top-ranked vessel is legally proven to be responsible.

---

# 1. Problem Definition

VARUNA provides an automated system that uses satellite SAR/EO imagery to detect and characterise marine oil slicks, uses oceanographic and meteorological information to trace slicks backward toward their likely origin and forward toward future movement, and correlates historic AIS traffic to identify/rank potential responsible vessels. The platform also provides an intuitive geospatial visual interface.

The stronger product framing is:

> **Evidence correlation under uncertainty.**

The investigator should be able to move from:

```text
Possible dark feature
        ↓
Is it oil?
        ↓
When did it appear?
        ↓
Where did it originate?
        ↓
Who was there?
        ↓
Why is a vessel suspicious?
        ↓
Where will the slick go?
        ↓
What may be affected?
        ↓
What evidence supports the case?
        ↓
Investigation report
```

---

# 2. Internal-Round Success Definition

The MVP is successful when one controlled incident can be taken through the complete workflow:

1. Load satellite scene.
2. Run image-quality assessment.
3. Detect candidate slick.
4. Distinguish oil from look-alike/no-oil conditions.
5. Characterise spill geometry.
6. Compare temporal observations.
7. Estimate a spill-age/time range.
8. Backtrack toward a probable origin region.
9. Query AIS during the origin window.
10. Filter irrelevant traffic.
11. Replay relevant vessel trajectories.
12. Detect AIS/behaviour anomalies.
13. Rank candidate vessels.
14. Explain the ranking.
15. Forecast forward movement.
16. Identify potentially affected sensitive areas.
17. Answer investigator questions from structured evidence.
18. Generate an auditable report.

The final judge experience should be one continuous investigation, not a collection of unrelated AI features.

---

# 3. Core MVP Product Flow

```text
                    SENTINEL-1 SAR
                          |
                          v
                 IMAGE QUALITY GATE
                          |
                          v
          OIL SEGMENTATION + LOOK-ALIKE
                          |
                          v
            SPILL CHARACTERISATION
                          |
                          v
             TEMPORAL ANALYSIS
                          |
                          v
             BACKWARD DRIFT / ORIGIN
                          |
              +-----------+-----------+
              |                       |
              v                       v
        ENVIRONMENTAL DATA          AIS DATA
              |                       |
              v                       v
        DRIFT MODEL             AIS QUERY/REPLAY
              |                       |
              +-----------+-----------+
                          |
                          v
                    EVIDENCE FUSION
                          |
                          v
                 VESSEL ATTRIBUTION
                          |
                  +-------+-------+
                  |               |
                  v               v
            FORWARD DRIFT      IMPACT
                  |               |
                  +-------+-------+
                          |
                          v
                 INVESTIGATOR UI
                    /         \
                   v           v
                ASK SYSTEM   REPORT
```

---

# 4. Exact Technology Stack

Do not introduce alternative frameworks without a concrete engineering reason and team approval.

## 4.1 Frontend

- React
- TypeScript
- Vite
- MapLibre GL JS
- WebSocket or SSE for progress updates

Primary purpose:
- investigation dashboard;
- geospatial visualisation;
- timeline;
- evidence panels;
- vessel replay;
- forecast visualisation.

## 4.2 Backend

- Python
- FastAPI
- Pydantic
- Uvicorn
- Celery
- Redis

FastAPI is the single primary API framework.

Celery is the selected background-job framework.

Redis is the queue/cache backend.

Do not introduce multiple competing job systems.

## 4.3 Database

- PostgreSQL
- PostGIS

PostGIS is authoritative for:
- spatial AIS queries;
- trajectory data;
- incident geometry;
- origin regions;
- sensitive-area intersections.

## 4.4 Machine Learning

- PyTorch
- U-Net for the first oil-spill segmentation baseline
- CNN-based oil/look-alike/no-oil classifier
- pretrained encoders/backbones may be used
- Isolation Forest or autoencoder only as a later anomaly-detection experiment
- grounded LLM for natural-language investigation only

Do not build a custom foundation model.

Do not replace U-Net with another architecture merely because it is newer. First establish the baseline, measure it, then experiment if necessary.

## 4.5 Geospatial/scientific stack

Use established libraries:

- NumPy
- SciPy
- pandas
- GeoPandas
- Shapely
- rasterio
- pyproj

Do not manually implement mature geospatial operations.

## 4.6 Drift modelling

Use an established Lagrangian particle approach.

Prefer a GNOME/PyGNOME-compatible implementation where practical.

Do not create a new ocean circulation model.

For the controlled hackathon demonstration, cached environmental forcing is acceptable.

## 4.7 Data formats

- GeoTIFF / COG where appropriate for raster data
- GeoJSON for vector/map outputs
- Parquet for large tabular intermediate data where useful
- PostgreSQL/PostGIS for indexed operational data

## 4.8 Deployment

- Docker
- Docker Compose for MVP
- CPU/GPU depending on actual workload
- basic observability only if time permits

---

# 5. Dataset Strategy — Operational Data Standards

## 5.1 AIS data — what the specification actually establishes

The standard dataset section states that the AIS format can be obtained from sample AIS data available through MarineCadastre.

It further states:

1. Real AIS may be used if available.
2. If real AIS is unavailable, synthetic AIS can be prepared for the oil-spill region to demonstrate the algorithm.

Therefore the MVP must support **both real and synthetic AIS as valid inputs**.

## 5.2 AIS source hierarchy

Use:

```text
Real AIS available?
       |
   +---+---+
   |       |
  YES      NO
   |       |
   v       v
Real AIS  Synthetic AIS
   |       |
   +---+---+
       |
       v
 SAME CLEANING / QUERY /
 REPLAY / ANOMALY / ATTRIBUTION PIPELINE
```

Synthetic AIS must not be treated as inferior from an engineering perspective. It is explicitly permitted by the PS and is particularly valuable for controlled ground-truth demonstrations.

## 5.3 Synthetic AIS requirements

If synthetic AIS is used, generate a controlled scenario with:
- realistic timestamps;
- geographic coordinates;
- vessel identities/MMSIs;
- speeds/courses;
- normal traffic;
- plausible vessels;
- controlled anomaly events;
- a known ground-truth candidate for evaluation.

The synthetic generator must be deterministic from a seed.

Never present synthetic data as real-world AIS.

The UI/report must identify the data source appropriately.

## 5.4 Satellite imagery — what the PS specifies

The PS references:

> **Zenodo — Sentinel-1 SAR Oil Spill Dataset**

This is the authoritative satellite dataset reference for the MVP.

Do not silently replace it with another satellite dataset.

Additional satellite sources can be introduced after the internal round as an explicit expansion.

## 5.5 Dataset-specific implementation

The detailed master document notes publicly available Sentinel-1 oil-spill/look-alike material and discusses event/region-aware evaluation.

Use the actual dataset files and metadata available to the team.

Do not assume that the PS itself mandates:
- exact train/test counts;
- exact dataset partitions;
- exact class definitions beyond what the selected dataset actually provides.

Those are implementation details and must be recorded in the project dataset manifest.

## 5.6 Environmental data

The PS requires oceanographic/meteorological information for tracing and prediction.

For the internal demo:
- use a fixed/cached environmental snapshot;
- document the source and timestamp;
- keep the scenario reproducible.

Do not build a global live environmental-data ingestion system before the internal round.

---

# 6. Core Data Model

Minimum entities:

```text
Incident
SatelliteScene
SpillDetection
SpillGeometry
TemporalObservation
OriginEstimate
EnvironmentalSnapshot
Vessel
AISPoint
AISSegment
AISAnomaly
AttributionScore
DriftRun
SensitiveAsset
EvidenceItem
InvestigationQuestion
InvestigationReport
```

Every derived conclusion must be traceable to evidence.

Every model inference should store:
- model name;
- model version;
- preprocessing version;
- dataset version;
- inference timestamp.

---

# 7. PHASE 0 — Initial Setup and Foundation

## Objective

Create a stable, reproducible engineering environment before implementing advanced functionality.

## 7.1 Repository

Use one main repository:

```text
/
├── apps/
│   ├── web/
│   └── api/
├── ml/
│   ├── segmentation/
│   ├── lookalike/
│   └── evaluation/
├── services/
│   ├── ais/
│   ├── drift/
│   └── reports/
├── data/
│   ├── raw/
│   ├── processed/
│   └── manifests/
├── db/
│   ├── migrations/
│   └── seeds/
├── scripts/
├── tests/
├── docs/
└── docker/
```

Before creating a new module, search the repository for an existing implementation.

## 7.2 Infrastructure

Set up:
- PostgreSQL + PostGIS;
- Redis;
- FastAPI;
- React/Vite;
- Docker Compose.

All services must start from a clean checkout.

## 7.3 Database migrations

Create versioned migrations for the schema.

Never rely on manual database edits.

## 7.4 API contracts

Define Pydantic request/response models before frontend integration.

Initial API surface:

```text
GET    /incidents
GET    /incidents/{id}
POST   /incidents
POST   /incidents/{id}/detect
POST   /incidents/{id}/origin
POST   /incidents/{id}/ais/query
POST   /incidents/{id}/attribution
POST   /incidents/{id}/forecast
GET    /incidents/{id}/evidence
POST   /investigation/ask
POST   /reports/{incident_id}
```

Exact naming may change, but functionality and contracts must remain explicit.

## 7.5 Seed incident

Create one synthetic/dummy incident solely for integration testing.

It must be clearly labelled as test data.

## Phase 0 exit criterion

A clean checkout starts all services and displays an incident page using real frontend/API/database communication.

---

# 8. PHASE 1 — Satellite Data Pipeline

## Objective

Load and process real Sentinel-1 SAR imagery correctly.

## 8.1 Dataset manifest

Create a machine-readable manifest containing:

```text
image_id
filepath
dataset_source
split
class
has_mask
polarizations
width
height
georeferencing_available
```

Do not invent metadata that is absent.

## 8.2 Validation

Validate:
- file readability;
- dimensions;
- VV/VH availability;
- NaNs/infinite values;
- mask dimensions;
- expected numerical ranges;
- georeferencing where required.

## 8.3 Preprocessing

Define one shared preprocessing pipeline for training and inference.

Explicitly document:
- channel order;
- normalisation;
- clipping;
- tiling/resizing;
- missing-value handling.

Training and inference must not silently use different preprocessing.

## 8.4 Scene visualisation

Display:
- VV;
- VH;
- metadata;
- geographic footprint where georeferencing is available.

## Exit criterion

A real Sentinel-1 scene can be selected, validated, preprocessed and displayed.

---

# 9. PHASE 2 — Oil-Spill Segmentation ML

## Objective

Build the first real ML component.

## 9.1 Baseline model

Use:

> **U-Net**

Input:

```text
VV + VH
```

Output:

```text
per-pixel oil probability
```

Threshold the probability map into a binary spill mask.

## 9.2 Training

Implement:
- dataset loader;
- augmentation;
- train loop;
- validation loop;
- checkpointing;
- reproducibility;
- metric calculation;
- prediction visualisation.

## 9.3 Loss

Start with:

```text
Dice Loss + Binary Cross Entropy
```

Do not create a custom loss unless the baseline has been measured and there is a demonstrated need.

## 9.4 Evaluation

Track:
- IoU;
- precision;
- recall;
- F1;
- false-positive examples.

## 9.5 Model registry

Store:
- checkpoint;
- model configuration;
- dataset version;
- preprocessing version;
- evaluation metrics.

## 9.6 Inference

The backend must call the actual model.

Example response:

```json
{
  "model_name": "unet_oil_segmentation",
  "model_version": "v1",
  "confidence": 0.93,
  "processing_time_ms": 0
}
```

Do not generate fake masks or fake confidence values.

## Exit criterion

Held-out data produces reproducible segmentation results and recorded metrics.

---

# 10. PHASE 3 — Look-Alike Intelligence + Confidence

## Objective

Prevent the system from treating every dark SAR feature as oil.

The master specification identifies dark spots/look-alikes as a critical challenge, including natural slicks, low-wind effects, rain cells, ship wakes and internal-wave/current features.

## 10.1 Classifier

Build/use a separate model capable of distinguishing:

```text
OIL
LOOK-ALIKE / NO-OIL
UNCERTAIN
```

Use the actual available dataset material rather than inventing a dataset.

## 10.2 Image-quality gate

Implement transparent rules for:
- missing pixels;
- artefacts;
- contrast;
- environmental suitability;
- coastal interference;
- coverage.

## 10.3 Confidence

Combine evidence from:
- segmentation;
- look-alike classifier;
- image quality;
- environmental conditions;
- temporal evidence where available.

Do not average arbitrary percentages.

## 10.4 Abstention

Support:

```text
INSUFFICIENT EVIDENCE
```

when the evidence does not justify a confident decision.

## 10.5 UI

Example:

```text
Oil confidence:       93%
Look-alike risk:       LOW
Image quality:         HIGH
Overall evidence:      HIGH
```

Or:

```text
Oil confidence:       52%
Look-alike risk:       HIGH
Image quality:         MEDIUM

INSUFFICIENT EVIDENCE
```

## Exit criterion

The system can distinguish likely oil, likely look-alike and insufficient-evidence cases with visible reasoning.

---

# 11. PHASE 4 — Spill Characterisation

## Objective

Convert the segmentation mask into useful geometry.

Calculate:
- area;
- perimeter;
- length;
- width;
- bounding box;
- orientation;
- morphology.

Use:
- rasterio;
- Shapely;
- GeoPandas;
- pyproj.

Do not manually implement geospatial geometry when a mature library handles it.

## Important

Only convert pixel measurements to geographic units when the scene's georeferencing supports that conversion.

Never invent spatial scale.

## Exit criterion

Every detected spill produces reproducible geometry.

---

# 12. PHASE 5 — Temporal Analysis and Spill Age

## Objective

Determine whether the feature is new, persistent or evolving.

## MVP strategy

Use a controlled incident containing multiple observations:

```text
T-24h → normal
T-6h  → faint anomaly
T0    → candidate slick
T+6h  → spread
T+12h → evolution
```

## Implementation

Store:
- acquisition time;
- image;
- detection;
- mask;
- confidence.

Compare observations across time.

Estimate an **age/time range**, not an exact age.

Example:

```text
Likely spill window:
14:20–14:47
```

## Exit criterion

The incident page can display before/during/after evidence and a defensible time range.

---

# 13. PHASE 6 — Environmental Data + Drift Engine

## Objective

Use environmental forcing to reconstruct likely origin and future movement.

## Scope rule

Do not build a new ocean circulation model.

Use established Lagrangian particle modelling.

Prefer GNOME/PyGNOME-compatible methods where practical.

## 13.1 Environmental snapshot

For the controlled scenario, cache:
- wind;
- current;
- optionally waves if required.

Record:
- source;
- time;
- geographic extent;
- resolution where available.

## 13.2 Particle simulation

Represent oil as particles.

Particles are moved according to environmental forcing with appropriate dispersion/stochastic treatment.

## 13.3 Backward drift

Start from the observed slick and simulate backward.

Output:

```text
probable origin region
+
probable origin time window
+
confidence/uncertainty
```

Never convert a probability field into an exact origin point without evidence.

## 13.4 Forward drift

From the origin distribution simulate:

```text
+6h
+12h
+24h
+48h
```

Show probability/intensity fields rather than false exact boundaries.

## Exit criterion

The system can reproducibly animate backward origin reconstruction and forward spread for the controlled incident.

---

# 14. PHASE 7 — AIS Infrastructure

## Objective

Transform AIS data into queryable spatio-temporal vessel trajectories.

## 14.1 AIS fields

Minimum:
- MMSI;
- timestamp;
- latitude;
- longitude;
- speed;
- course;
- heading where available;
- vessel metadata where available.

## 14.2 Cleaning

Implement:
- invalid coordinate removal;
- timestamp validation;
- deduplication;
- unrealistic speed flagging;
- grouping by MMSI;
- trajectory construction;
- explicit AIS gap representation.

## 14.3 Database

Store processed AIS in PostgreSQL/PostGIS.

Use spatial and temporal indexes.

## 14.4 Who Was Here?

Input:

```text
origin region
time window
radius
```

Output:

```text
candidate vessels
```

Then filter according to relevance.

## Exit criterion

The system reliably retrieves historical vessel traffic around a supplied origin region/time window.

---

# 15. PHASE 8 — Vessel Replay

## Objective

Turn AIS trajectories into an understandable investigation visualisation.

## Implementation

Create:
- time-indexed trajectories;
- timeline slider;
- animated vessel positions;
- highlighted spill window;
- highlighted origin region;
- candidate vessel highlighting.

Example:

```text
12:00 ─── 13:00 ─── 14:00 ─── 15:00
                          ^
                     spill window
```

## Exit criterion

A judge can visually follow relevant vessels through the critical window.

---

# 16. PHASE 9 — AIS Anomaly Detection

## MVP

Use explainable rules first.

Detect:
- impossible speed;
- unrealistic acceleration;
- teleport-like jumps;
- AIS gaps;
- abrupt course changes;
- disappearance/reappearance.

Every anomaly must reference the underlying AIS observations.

## Later experiment

After the rule-based system works, evaluate:
- Isolation Forest;
- autoencoder;
- sequence models.

Do not block the MVP on ML anomaly detection.

## Critical interpretation rule

An AIS anomaly is:

> **supporting evidence**

not proof of illegal dumping.

## Exit criterion

The system can show understandable anomaly events for candidate vessels.

---

# 17. PHASE 10 — Vessel Attribution Engine

## Objective

Rank candidate vessels using independent evidence.

## 17.1 MVP method

Use an interpretable scoring engine.

Candidate evidence:
- proximity to origin;
- timing;
- trajectory intersection;
- heading alignment;
- AIS anomaly;
- AIS gap;
- drift consistency;
- historical association if available.

## 17.2 Example

```text
Vessel X — 91/100

Proximity           +27
Timing              +24
Trajectory          +18
AIS gap             +12
Behaviour anomaly   +07
Historical pattern  +03
```

Weights must be centrally configured.

Do not scatter weights throughout application code.

## 17.3 Explainability

Every score must be decomposable.

The UI must answer:

> Why is Vessel X ranked first?

## 17.4 Legal wording

Never output:

```text
Vessel X caused the spill.
```

Output:

```text
Vessel X is the highest-priority candidate for investigation.
```

## Exit criterion

The ranking is deterministic for the same inputs and every contribution is explainable.

---

# 18. PHASE 11 — Evidence Fusion

## Objective

Connect all evidence into one auditable investigation.

Evidence categories:

```text
Satellite
Image quality
Oil/look-alike
Temporal consistency
Spill geometry
Origin
Environmental drift
AIS presence
AIS trajectory
AIS anomalies
Attribution
Future drift
Impact
```

## Implementation

Use structured database relationships and evidence objects.

Do not introduce a graph database unless the team demonstrates a real requirement for one.

Every evidence item should have:
- type;
- source;
- timestamp where applicable;
- confidence where applicable;
- relationship to the incident;
- optional visual/map reference.

## Exit criterion

A user can select an important conclusion and inspect the evidence supporting it.

---

# 19. PHASE 12 — Forward Prediction + Impact Assessment

## Objective

Translate predicted spill movement into operational impact.

## GIS layers

Minimum:
- fishing areas;
- coastline/beaches;
- ports;
- protected/sensitive areas.

## Processing

```text
predicted spill region
        ∩
sensitive asset geometry
        ↓
potential impact
```

Example:

```text
Fishing Zone A
Potentially affected in ~6h

Protected Area B
Potentially affected in ~12h

Coastal Region C
Potentially affected in ~18h
```

Always communicate uncertainty.

## Exit criterion

The judge can see where the spill may go and what sensitive assets may be affected.

---

# 20. PHASE 13 — Investigator Dashboard

## 20.1 Main dashboard

Must include:
- incident map;
- satellite layer;
- spill overlay;
- vessel overlay;
- drift layers;
- timeline;
- confidence panel;
- evidence panel;
- priority information.

## 20.2 Incident page

Must include:
- before/during/after imagery;
- spill geometry;
- estimated age;
- origin probability;
- candidate vessels;
- vessel replay;
- AIS anomalies;
- predicted spread;
- impact assessment;
- investigation assistant;
- report export.

Do not build many disconnected dashboards.

One strong incident investigation interface is preferred.

---

# 21. PHASE 14 — Grounded Investigation Assistant

## Objective

Allow natural-language investigation while preventing hallucinated evidence.

## Tool functions

Implement structured functions such as:

```text
get_incident
get_detection
get_origin
find_vessels_near_origin
get_vessel_track
get_vessel_anomalies
get_attribution
get_forecast
get_impact
```

## Flow

```text
Judge question
      ↓
LLM intent interpretation
      ↓
structured tool call
      ↓
database/model result
      ↓
LLM explanation
```

## Example questions

```text
Who was within 10 km of the origin?

Why is Vessel X suspicious?

What was the estimated spill window?

Which sensitive areas could be affected in 12 hours?
```

## Hard rule

The LLM must never invent:
- vessel identities;
- coordinates;
- AIS events;
- confidence values;
- scientific conclusions.

The LLM is an interface to evidence, not the source of evidence.

## Exit criterion

All factual answers can be traced to retrieved structured evidence.

---

# 22. PHASE 15 — One-Click Investigation Report

Generate a structured report containing:

## Incident
- incident ID;
- location;
- satellite scene;
- acquisition time.

## Detection
- spill mask;
- geometry;
- oil confidence;
- look-alike assessment;
- image quality.

## Reconstruction
- estimated spill window;
- probable origin;
- uncertainty.

## AIS investigation
- candidate vessels;
- relevant trajectories;
- anomalies;
- attribution ranking.

## Prediction
- 6h;
- 12h;
- 24h;
- 48h spread.

## Impact
- potentially affected sensitive assets.

## Limitations
- image uncertainty;
- look-alike risk;
- origin uncertainty;
- AIS gaps;
- drift uncertainty;
- model limitations.

The report must explicitly distinguish investigation priority from legal responsibility.

## Exit criterion

One button produces a coherent, evidence-backed incident report.

---

# 23. PHASE 16 — Super-Resolution Research Spike

Super-resolution is **not a core MVP dependency**.

Do not allow it to delay:
- segmentation;
- origin reconstruction;
- AIS;
- attribution;
- prediction.

After the baseline CV pipeline works, optionally evaluate:

```text
Raw SAR → U-Net

versus

Raw SAR → Super Resolution → U-Net
```

Compare:
- IoU;
- F1;
- precision;
- recall;
- small-spill detection;
- boundary quality.

Only promote super-resolution into the internal product if it produces a meaningful downstream improvement.

## Scientific rule

AI-enhanced imagery must never be treated as additional observed satellite information.

The original SAR remains authoritative.

If SR is used in the UI, label it as:

> **AI-enhanced representation — not additional observed satellite information.**

---

# 24. PHASE 17 — Internal-Round Demo Hardening

## Controlled scenario

Build one deterministic incident.

The scenario should contain:
- known satellite scene;
- known environmental snapshot;
- known AIS dataset;
- known origin/time ground truth for evaluation;
- known candidate vessels;
- controlled anomalies.

## Demo flow

### Step 1 — Detect

Load satellite scene.

### Step 2 — Verify

Show:

```text
Oil confidence: HIGH
Image quality: HIGH
Look-alike risk: LOW
```

### Step 3 — Characterise

Show:
- area;
- length;
- width;
- morphology;
- estimated age.

### Step 4 — Backtrack

Animate probable origin.

### Step 5 — AIS

Show narrowing:

```text
47 nearby
→ 18 relevant
→ 6 plausible
→ 3 high priority
```

The actual numbers must come from the demo dataset; they must not be hardcoded unless explicitly designated as controlled seed data.

### Step 6 — Replay

Animate vessels during the critical window.

### Step 7 — Explain

Open the top candidate:

```text
Vessel X — 91/100

Proximity
Timing
Trajectory
AIS gap
Behaviour
History
```

### Step 8 — Forecast

Show:
- +6h;
- +12h;
- +24h;
- +48h.

### Step 9 — Impact

Show sensitive assets.

### Step 10 — Ask

Ask:

> Why is Vessel X suspicious?

### Step 11 — Report

Generate the incident report.

## Final story

```text
UNCERTAINTY
     ↓
EVIDENCE
     ↓
NARROWING
     ↓
ATTRIBUTION PRIORITY
     ↓
PREDICTION
     ↓
ACTION
```

---

# 25. Explicit Internal-Round MUST-HAVE List

## Detection
- [ ] Sentinel-1 ingestion
- [ ] U-Net segmentation
- [ ] actual model inference
- [ ] spill mask
- [ ] geometry

## Verification
- [ ] look-alike/no-oil classification
- [ ] image-quality gate
- [ ] confidence
- [ ] insufficient-evidence state

## Reconstruction
- [ ] temporal comparison
- [ ] spill age/time range
- [ ] backward drift
- [ ] origin probability region

## AIS
- [ ] MarineCadastre-compatible AIS format handling
- [ ] real AIS OR clearly-labelled synthetic AIS
- [ ] cleaning
- [ ] PostGIS
- [ ] Who Was Here
- [ ] replay
- [ ] anomaly rules
- [ ] attribution score

## Prediction
- [ ] forward drift
- [ ] 6/12/24/48h
- [ ] sensitive-area overlays

## Investigation
- [ ] evidence panel
- [ ] grounded Ask System
- [ ] report generation

## Product
- [ ] polished map
- [ ] timeline
- [ ] coherent investigation page
- [ ] deterministic demo scenario
- [ ] failure states
- [ ] uncertainty states

---

# 26. Explicitly AFTER Clearing the Internal Round

Only after the internal round should the team expand into:

## Data expansion
- broader Indian coastal coverage;
- additional Sentinel-1/other EO sources;
- additional AIS sources;
- larger environmental datasets.

## ML expansion
- stronger segmentation architectures;
- learned confidence calibration;
- advanced look-alike modelling;
- ML-based AIS anomaly detection;
- learned/calibrated evidence fusion;
- validated task-specific SAR super-resolution.

## Ocean modelling
- larger domains;
- ensemble simulations;
- uncertainty propagation;
- more sophisticated weathering processes.

## Attribution expansion
- fleet/operator pattern analysis;
- cross-incident similarity;
- historical incident search;
- richer behavioural modelling.

## Infrastructure
- live satellite ingestion;
- scalable AIS ingestion;
- cloud/GPU infrastructure;
- agency APIs;
- authentication and audit infrastructure;
- production observability.

## Product
- priority queue;
- fleet pattern detection;
- “What Changed?”;
- cross-incident intelligence;
- field/mobile interface;
- agency dashboards;
- alerts.

---

# 27. What We Must NOT Build Before Internal Round

Do not spend MVP time on:
- global live satellite ingestion;
- global live AIS ingestion;
- perfect universal detection;
- a custom foundation model;
- a new ocean circulation model;
- a giant graph database;
- autonomous legal enforcement;
- mobile application;
- full agency integrations;
- commercial-scale infrastructure;
- guaranteed culprit identification.

The project should demonstrate depth through integration and evidence reasoning, not through unnecessary scope.

---

# 28. What We Must Reuse Instead of Reinventing

Before implementing any capability, check whether an established tool/model/library/dataset already exists.

| Requirement | Preferred existing technology |
|---|---|
| Satellite oil dataset | Copernicus Sentinel-1 SAR Oil Spill Dataset (Zenodo) |
| AIS format reference | MarineCadastre sample AIS |
| Oil segmentation baseline | U-Net |
| Deep learning framework | PyTorch |
| Spatial database | PostgreSQL + PostGIS |
| Raster processing | rasterio |
| Geometry | Shapely / GeoPandas |
| Coordinate transformations | pyproj |
| Dataframes | pandas |
| Numerical operations | NumPy / SciPy |
| Oil transport | GNOME/PyGNOME-compatible Lagrangian approach |
| API | FastAPI |
| Map | MapLibre GL JS |
| Background jobs | Celery |
| Queue/cache | Redis |
| Containerisation | Docker |
| Natural-language investigation | grounded tool-calling LLM |

If a mature component solves the problem, reuse it.

---

# 29. AI Coding-Agent Guardrails

These rules are mandatory when implementing from this PRD.

## Rule 1 — Do not invent datasets

If a dataset is named:
- use it;
- verify its actual structure;
- record its version/source.

If a required dataset is not specified, do not fabricate one.

## Rule 2 — Do not invent scientific values

Never fabricate:
- wind;
- current;
- coordinates;
- vessel position;
- spill age;
- confidence;
- attribution score.

Controlled demo values may exist only in clearly-labelled seed data.

## Rule 3 — Do not fake ML

Never create:
- random masks;
- random confidence;
- fake model outputs

and label them as inference.

If a model is unavailable:

```text
MODEL_NOT_READY
```

or another explicit state must be returned.

## Rule 4 — Do not silently replace technologies

If this PRD specifies U-Net, PostGIS, FastAPI, MapLibre, etc., do not silently substitute alternatives.

Propose the change and document the reason first.

## Rule 5 — Do not duplicate existing code

Search the repository before creating:
- services;
- utility functions;
- data models;
- API clients;
- database helpers;
- preprocessing logic.

## Rule 6 — Keep model provenance

Every ML inference should be traceable to:
- model;
- version;
- dataset;
- preprocessing.

## Rule 7 — Preserve uncertainty

Never convert:
- probability regions into exact points;
- ranges into exact timestamps;
- rankings into guilt;
- anomalies into proof.

## Rule 8 — Preserve original evidence

Do not overwrite original satellite imagery with enhanced/processed imagery.

Derived outputs must remain distinguishable from source evidence.

## Rule 9 — Ground the LLM

The LLM must call structured tools for factual investigation.

No unsupported factual generation.

## Rule 10 — Fail explicitly

If a component is unavailable, return an explicit failure/unavailable state rather than inventing a result.

---

# 30. Testing and Evaluation

## 30.1 Satellite segmentation

Measure:
- precision;
- recall;
- F1;
- IoU;
- false positives on look-alikes/no-oil.

Use event/region-aware splits where possible.

## 30.2 Confidence

Measure:
- calibration;
- quality of abstention;
- insufficient-evidence decisions.

## 30.3 Drift

Measure:
- origin reconstruction error;
- forward trajectory/spread error;
- sensitivity to environmental uncertainty.

## 30.4 Attribution

Measure:
- top-k suspect recall;
- ranking quality;
- false-positive/false-accusation rate;
- controlled ground-truth performance.

Synthetic AIS is particularly useful here because ground truth can be known by construction.

## 30.5 System

Measure:
- end-to-end time to actionable result;
- Who Was Here query latency;
- replay smoothness;
- report generation time.

---

# 31. Required Failure States

## Poor imagery

```text
LOW IMAGE QUALITY

Confidence reduced.
```

## Likely look-alike

```text
LIKELY LOOK-ALIKE

Attribution not performed.
```

## Insufficient evidence

```text
INSUFFICIENT EVIDENCE

Corroborating imagery or verification required.
```

## AIS unavailable

```text
AIS DATA INSUFFICIENT

Attribution unavailable for this window.
```

## Drift uncertainty

```text
HIGH FORECAST UNCERTAINTY

Displayed region represents a probability distribution.
```

## Model unavailable

```text
MODEL UNAVAILABLE

No fabricated result will be displayed.
```

---

# 32. Security and Reliability Baseline for the MVP

Security is not the judging headline, but the application must not be built carelessly.

Minimum:
- validate all API inputs;
- restrict file types/sizes for uploads;
- do not expose database credentials to frontend;
- use environment variables for secrets;
- use parameterised queries/ORM-safe database access;
- restrict CORS;
- implement authentication if the application is remotely accessible;
- rate-limit expensive endpoints where appropriate;
- isolate long-running ML/drift jobs from request handlers;
- prevent arbitrary filesystem access;
- log important investigation actions;
- never expose raw credentials in logs;
- make background jobs idempotent where possible.

Production-grade DDoS protection, WAF, distributed rate limiting and full security hardening are **post-internal infrastructure work**, not reasons to delay the core MVP.

---

# 33. Recommended Team Workstreams

## Workstream A — Computer Vision / ML

Own:

```text
Sentinel-1
 ↓
Preprocessing
 ↓
Segmentation
 ↓
Look-alike
 ↓
Confidence
```

## Workstream B — Ocean / Drift

Own:

```text
Environmental data
 ↓
Lagrangian drift
 ↓
Backward origin
 ↓
Forward prediction
```

## Workstream C — AIS / Attribution

Own:

```text
AIS ingestion
 ↓
Cleaning
 ↓
PostGIS
 ↓
Who Was Here
 ↓
Replay
 ↓
Anomalies
 ↓
Attribution
```

## Workstream D — Full Stack / Product

Own:

```text
React
 ↓
Map
 ↓
Incident UI
 ↓
Evidence
 ↓
Timeline
 ↓
Report
```

## Optional Workstream E — Investigation Assistant / Integration

Own:
- tool-calling;
- structured evidence retrieval;
- integration;
- evaluation;
- demo orchestration.

---

# 34. Dependency-Aware Build Order

Do not build features randomly.

```text
PHASE 0
Foundation
   ↓
PHASE 1
Satellite ingestion
   ↓
PHASE 2
Oil segmentation
   ↓
PHASE 3
Look-alike + confidence
   ↓
PHASE 4
Characterisation
   ↓
PHASE 5
Temporal analysis
   ↓
PHASE 6
Drift / origin
   ↓
PHASE 7
AIS infrastructure
   ↓
PHASE 8
Vessel replay
   ↓
PHASE 9
AIS anomalies
   ↓
PHASE 10
Attribution
   ↓
PHASE 11
Evidence fusion
   ↓
PHASE 12
Prediction + impact
   ↓
PHASE 13
Investigator dashboard
   ↓
PHASE 14
Grounded assistant
   ↓
PHASE 15
Report
   ↓
PHASE 16
Optional SR experiment
   ↓
PHASE 17
Demo hardening
```

Core rule:

> Do not add another feature if DETECT → ORIGIN → AIS → ATTRIBUTE → PREDICT is not reliable enough to demonstrate.

---

# 35. Final Product Definition

The internal-round MVP takes:

> **one suspicious satellite observation**

and produces:

> **one explainable, evidence-backed investigation.**

It must answer:

### 1. IS IT OIL?

Satellite segmentation + look-alike analysis + quality/uncertainty.

### 2. WHERE / WHEN DID IT ORIGINATE?

Temporal evidence + environmental drift + probability region.

### 3. WHO WAS THERE?

Historical AIS query + spatial/temporal filtering + replay.

### 4. WHY IS A VESSEL SUSPICIOUS?

Explainable attribution based on multiple independent evidence signals.

### 5. WHAT WILL BE AFFECTED NEXT?

Forward drift + sensitive-area intersection.

The final product is:

> **An uncertainty-aware evidence-fusion and investigation layer that turns a possible oil spill into an actionable case.**

It does not replace existing satellite, oceanographic or maritime-surveillance systems.

It connects them.

---

# 36. Internal-Round Definition of Done

The project is ready for internal judging only when:

```text
[✓] Real Sentinel-1 scene
[✓] Actual segmentation inference
[✓] Look-alike verification
[✓] Quality/confidence state
[✓] Spill geometry
[✓] Temporal evidence
[✓] Backward origin reconstruction
[✓] AIS query
[✓] Vessel replay
[✓] AIS anomaly evidence
[✓] Explainable attribution
[✓] Forward drift
[✓] Sensitive-area impact
[✓] Evidence panel
[✓] Grounded investigation assistant
[✓] Report generation
[✓] Failure states
[✓] One deterministic end-to-end demo
```

The goal is not to demonstrate the largest number of technologies.

The goal is to demonstrate the strongest complete investigation.

---

# 37. One-Minute Product Pitch

Marine oil-spill response is not only a detection problem.

Existing satellite, AIS and ocean-modelling capabilities provide valuable pieces of the puzzle, but investigators still have to correlate uncertain observations, environmental conditions, vessel histories and behavioural anomalies to understand what happened.

Our platform connects that fragmented workflow.

We detect and characterise candidate slicks, distinguish possible oil from look-alikes, reconstruct where and when the spill most likely originated, identify and replay vessels in the critical area, detect suspicious AIS behaviour, rank potential vessels using multiple evidence signals, predict future spread, identify potentially affected sensitive areas, answer investigator questions from the underlying evidence, and generate an auditable incident report.

We do not claim that AI can prove guilt from one image.

We turn a possible spill into an actionable investigation.
