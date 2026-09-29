from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import os
import json
import math
import numpy as np

from db.database import get_db
from db.models import (
    Incident, SatelliteScene, SpillDetection, OriginEstimate,
    Vessel, AISPoint, AISAnomaly, AttributionScore, DriftRun,
    SensitiveAsset, EvidenceItem
)
from apps.api.schemas.incident import (
    IncidentResponse, IncidentCreate, DetectionResponse, OriginResponse,
    AISQueryRequest, AISReplayRequest, AttributionResponse,
    AssistantRequest, AssistantResponse, ReportResponse,
    TraceOriginRequest, ForecastSpillRequest, CustomSpillRequest
)
from services.characterisation.morphology import characterisation_service
from services.drift.lagrangian import drift_engine
from services.drift.environmental import EnvironmentalSnapshot
from services.ais.trajectory import ais_trajectory_service
from services.ais.mock_data import synthetic_ais_generator
from services.ais.anomaly import ais_anomaly_detector
from services.attribution.engine import attribution_engine
from services.impact.assessment import sensitive_impact_service
from services.assistant.grounded_agent import grounded_assistant
from services.reports.generator import report_generator
from services.satellite.geotiff import geotiff_parser
from ml.segmentation.pipeline import satellite_ml_pipeline

router = APIRouter()

@router.get("/incidents", response_model=List[IncidentResponse])
def list_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).all()

@router.get("/incidents/{incident_id}")
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    scene = db.query(SatelliteScene).filter(SatelliteScene.incident_id == incident_id).first()
    detection = db.query(SpillDetection).filter(SpillDetection.incident_id == incident_id).first()
    origin = db.query(OriginEstimate).filter(OriginEstimate.incident_id == incident_id).first()
    scores = db.query(AttributionScore).filter(AttributionScore.incident_id == incident_id).order_by(AttributionScore.priority_rank).all()
    drift_fwd = db.query(DriftRun).filter(DriftRun.incident_id == incident_id, DriftRun.run_type == "FORWARD_FORECAST").first()
    evidence = db.query(EvidenceItem).filter(EvidenceItem.incident_id == incident_id).all()
    anomalies = db.query(AISAnomaly).filter(AISAnomaly.incident_id == incident_id).all()
    
    # Format attribution candidates
    vessels = {v.mmsi: v for v in db.query(Vessel).all()}
    ais_pts = db.query(AISPoint).order_by(AISPoint.timestamp).all()
    tracks_by_mmsi = {}
    for p in ais_pts:
        if p.mmsi not in tracks_by_mmsi:
            tracks_by_mmsi[p.mmsi] = []
        tracks_by_mmsi[p.mmsi].append(p)

    formatted_scores = []
    for s in scores:
        v = vessels.get(s.mmsi)
        pts = tracks_by_mmsi.get(s.mmsi, [])
        last_pt = pts[-1] if pts else None
        formatted_scores.append({
            "mmsi": s.mmsi,
            "vessel_name": v.vessel_name if v else f"MMSI {s.mmsi}",
            "vessel_type": v.vessel_type if v else "Unknown",
            "flag": v.flag if v else "Unknown",
            "priority_rank": s.priority_rank,
            "total_score": s.total_score,
            "priority_level": s.priority_level,
            "last_known_lat": last_pt.latitude if last_pt else None,
            "last_known_lon": last_pt.longitude if last_pt else None,
            "sog": last_pt.sog if last_pt else None,
            "cog": last_pt.cog if last_pt else None,
            "trajectory": [[p.longitude, p.latitude] for p in pts],
            "ais_points": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "lat": p.latitude,
                    "lon": p.longitude,
                    "sog": p.sog,
                    "cog": p.cog
                } for p in pts
            ],
            "breakdown": {
                "proximity": s.score_proximity,
                "timing": s.score_timing,
                "trajectory": s.score_trajectory,
                "ais_gap": s.score_ais_gap,
                "behaviour_anomaly": s.score_behaviour_anomaly
            },
            "reasons": s.explanation_reasons,
            "disclaimer": s.disclaimer
        })
        
    # Format impacts
    forecast_steps = drift_fwd.forecast_steps if drift_fwd else []
    impacts = sensitive_impact_service.assess_impact(forecast_steps)
    
    return {
        "incident": {
            "id": inc.id,
            "title": inc.title,
            "description": inc.description,
            "status": inc.status,
            "center_lat": inc.center_lat,
            "center_lon": inc.center_lon,
            "spill_window_start": inc.spill_window_start.isoformat() if inc.spill_window_start else None,
            "spill_window_end": inc.spill_window_end.isoformat() if inc.spill_window_end else None,
            "provenance": inc.provenance
        },
        "scene": {
            "id": scene.id,
            "satellite_name": scene.satellite_name,
            "acquisition_time": scene.acquisition_time.isoformat(),
            "polarizations": scene.polarizations,
            "quality_score": scene.quality_score,
            "quality_details": scene.quality_details,
            "bbox": scene.bbox
        } if scene else None,
        "detection": {
            "id": detection.id,
            "oil_confidence": detection.oil_confidence,
            "look_alike_risk": detection.look_alike_risk,
            "look_alike_type": detection.look_alike_type,
            "decision_state": detection.decision_state,
            "area_km2": detection.area_km2,
            "perimeter_km": detection.perimeter_km,
            "length_km": detection.length_km,
            "width_km": detection.width_km,
            "orientation_deg": detection.orientation_deg,
            "morphology_type": detection.morphology_type,
            "geojson": detection.geojson_geometry
        } if detection else None,
        "unet_prediction": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "unet_prediction.geojson"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "unet_prediction.geojson"))
            else None
        ),
        "dartis_reference": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "dartis_reference.json"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "dartis_reference.json"))
            else None
        ),
        "backtrack_particles": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "backtrack_particles.geojson"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "backtrack_particles.geojson"))
            else None
        ),
        "origin_corridor": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "origin_corridor.geojson"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "origin_corridor.geojson"))
            else None
        ),
        "backtrack_snapshots": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "backtrack_snapshots.json"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "backtrack_snapshots.json"))
            else None
        ),
        "forward_particles": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "forward_particles.geojson"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "forward_particles.geojson"))
            else None
        ),
        "forward_corridor": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "forward_corridor.geojson"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "forward_corridor.geojson"))
            else None
        ),
        "forward_snapshots": (
            json.load(open(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "forward_snapshots.json"), "r"))
            if os.path.exists(os.path.join("demo", "incidents", "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id, "derived", "forward_snapshots.json"))
            else None
        ),
        "origin_estimate": {
            "id": origin.id,
            "origin_center_lat": origin.center_lat,
            "origin_center_lon": origin.center_lon,
            "uncertainty_radius_km": origin.uncertainty_radius_km,
            "origin_window_start": origin.origin_window_start.isoformat(),
            "origin_window_end": origin.origin_window_end.isoformat(),
            "geojson": origin.probability_contour_geojson,
            "forcing_used": origin.forcing_used
        } if origin else None,
        "attribution_scores": formatted_scores,
        "anomalies": [
            {
                "id": a.id,
                "mmsi": a.mmsi,
                "timestamp": a.timestamp.isoformat(),
                "latitude": a.latitude,
                "longitude": a.longitude,
                "anomaly_type": a.anomaly_type,
                "severity": a.severity,
                "description": a.description,
                "raw_details": a.raw_details
            } for a in anomalies
        ],
        "forward_forecast": forecast_steps,
        "impacts": impacts,
        "evidence_items": [
            {
                "id": e.id,
                "category": e.category,
                "title": e.title,
                "content": e.content,
                "confidence": e.confidence
            } for e in evidence
        ]
    }

@router.post("/incidents/{incident_id}/ais/query")
def query_ais_traffic(incident_id: str, req: AISQueryRequest, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    origin = db.query(OriginEstimate).filter(OriginEstimate.incident_id == incident_id).first()
    if not origin:
        raise HTTPException(status_code=400, detail="Origin estimate required before AIS querying")
        
    vessels = [
        {"mmsi": v.mmsi, "vessel_name": v.vessel_name, "vessel_type": v.vessel_type, "flag": v.flag, "source_type": v.source_type}
        for v in db.query(Vessel).all()
    ]
    
    ais_points = [
        {
            "mmsi": p.mmsi,
            "timestamp": p.timestamp.isoformat(),
            "latitude": p.latitude,
            "longitude": p.longitude,
            "sog": p.sog,
            "cog": p.cog,
            "heading": p.heading,
            "source_type": p.source_type
        } for p in db.query(AISPoint).all()
    ]
    
    candidates = ais_trajectory_service.who_was_here(
        ais_points=ais_points,
        vessels=vessels,
        origin_lat=req.origin_lat or origin.center_lat,
        origin_lon=req.origin_lon or origin.center_lon,
        origin_window_start=origin.origin_window_start,
        origin_window_end=origin.origin_window_end,
        search_radius_km=req.search_radius_km
    )
    
    return {"incident_id": incident_id, "candidates_count": len(candidates), "candidates": candidates}

@router.post("/incidents/{incident_id}/ais/replay")
def replay_ais_positions(incident_id: str, req: AISReplayRequest, db: Session = Depends(get_db)):
    ais_points = [
        {
            "mmsi": p.mmsi,
            "timestamp": p.timestamp.isoformat(),
            "latitude": p.latitude,
            "longitude": p.longitude,
            "sog": p.sog,
            "cog": p.cog,
            "heading": p.heading
        } for p in db.query(AISPoint).all()
    ]
    trajectories = ais_trajectory_service.build_trajectories(ais_points)
    positions = ais_trajectory_service.get_interpolated_positions_at_time(trajectories, req.target_time)
    
    return {"target_time": req.target_time.isoformat(), "active_vessels": positions}

@router.post("/investigation/ask", response_model=AssistantResponse)
def ask_grounded_assistant(req: AssistantRequest, db: Session = Depends(get_db)):
    incident_detail = get_incident_detail(req.incident_id, db)
    
    # Query candidates near origin for assistant grounding
    vessels = [
        {"mmsi": v.mmsi, "vessel_name": v.vessel_name, "vessel_type": v.vessel_type, "flag": v.flag, "source_type": v.source_type}
        for v in db.query(Vessel).all()
    ]
    ais_points = [
        {"mmsi": p.mmsi, "timestamp": p.timestamp.isoformat(), "latitude": p.latitude, "longitude": p.longitude, "sog": p.sog, "cog": p.cog, "source_type": p.source_type}
        for p in db.query(AISPoint).all()
    ]
    origin = incident_detail.get("origin_estimate", {})
    if origin:
        candidates = ais_trajectory_service.who_was_here(
            ais_points=ais_points,
            vessels=vessels,
            origin_lat=origin.get("origin_center_lat", 18.85),
            origin_lon=origin.get("origin_center_lon", 72.72),
            origin_window_start=datetime.fromisoformat(origin.get("origin_window_start")),
            origin_window_end=datetime.fromisoformat(origin.get("origin_window_end"))
        )
        incident_detail["candidates"] = candidates
        
    incident_detail["quality_gate"] = incident_detail.get("scene", {}).get("quality_details", {})
    
    res = grounded_assistant.answer_question(req.query, incident_detail, req.history)
    if "model_used" not in res:
        res["model_used"] = "groq-openai/gpt-oss-120b"
    return res

@router.post("/incidents/{incident_id}/analyze-sar")
def analyze_satellite_sar(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    scene = db.query(SatelliteScene).filter(SatelliteScene.incident_id == incident_id).first()
    if not scene:
        raise HTTPException(status_code=400, detail="No satellite scene associated with this incident.")
        
    # Read actual files
    import os
    import rasterio
    import numpy as np
    
    base_dir = os.path.join("demo", "incidents", "incident_001")
    vv_path = os.path.join(base_dir, "satellite", "vv.tif")
    vh_path = os.path.join(base_dir, "satellite", "vh.tif")
    
    if incident_id not in ("VARUNA-2026-001", "SIH-2026-001") and scene.file_path and os.path.exists(scene.file_path):
        vv_path = scene.file_path
        vh_path = scene.file_path # For dual pol in one file, simplified here
        
    if not os.path.exists(vv_path):
        raise HTTPException(status_code=404, detail="SAR raster files not found.")
        
    # Window read central 512x512 for quick analysis (or 256x256)
    try:
        from rasterio.windows import Window
        with rasterio.open(vv_path) as src:
            w, h = src.width, src.height
            window = Window(max(0, w//2 - 128), max(0, h//2 - 128), min(256, w), min(256, h))
            sar_vv_raw = src.read(1, window=window).astype(np.float32)
        with rasterio.open(vh_path) as src:
            sar_vh_raw = src.read(1, window=window).astype(np.float32)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read raster: {e}")

    # Inspect and verify Sentinel-1 calibration
    # DO NOT blindly apply 20*log10(). Do not double convert.
    def smart_db_conversion(arr):
        arr_valid = arr[arr > 0]
        if len(arr_valid) == 0:
            return arr
        # If mean is negative, likely already dB
        if np.nanmean(arr_valid) < 0:
            return arr
        # If max is small (e.g. <= 10), likely linear power (Sigma0)
        if np.nanmax(arr_valid) <= 10.0:
            return 10 * np.log10(arr + 1e-7)
        # Otherwise, assume DN Amplitude (GRDH raw product)
        return 20 * np.log10(arr + 1e-7)

    sar_vv = smart_db_conversion(sar_vv_raw)
    sar_vh = smart_db_conversion(sar_vh_raw)
    
    ml_result = satellite_ml_pipeline.run_inference(
        sar_tensor_vv=sar_vv,
        sar_tensor_vh=sar_vh,
        center_lat=inc.center_lat,
        center_lon=inc.center_lon,
        wind_speed_ms=6.2,
        coastal_distance_km=18.4,
        threshold=0.5
    )
    
    # Add provenance to result
    ml_result["provenance"] = {
        "calibration_note": "Verified array domain (Linear/DN/dB) prior to processing.",
        "input_dimensions": sar_vv.shape
    }
    
    return ml_result

@router.post("/incidents/{incident_id}/trace-origin")
def trace_origin_live(incident_id: str, req: TraceOriginRequest, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    detection = db.query(SpillDetection).filter(SpillDetection.incident_id == incident_id).first()
    c_lat = req.slick_lat or (detection.geojson_geometry.get("properties", {}).get("center_lat") if detection else inc.center_lat) or inc.center_lat
    c_lon = req.slick_lon or inc.center_lon
    
    env = EnvironmentalSnapshot(
        wind_speed_ms=req.wind_speed_ms or 6.2,
        wind_direction_deg=req.wind_dir_deg or 240.0,
        current_speed_ms=req.current_speed_ms or 0.35,
        current_direction_deg=req.current_dir_deg or 75.0
    )
    
    result = drift_engine.simulate_backward_origin(
        slick_center_lat=c_lat,
        slick_center_lon=c_lon,
        detection_time=datetime.now(timezone.utc),
        backtrack_hours=req.backtrack_hours,
        particle_count=500,
        env=env
    )
    
    try:
        w_start = datetime.fromisoformat(result["origin_window_start"]) if isinstance(result["origin_window_start"], str) else result["origin_window_start"]
        w_end = datetime.fromisoformat(result["origin_window_end"]) if isinstance(result["origin_window_end"], str) else result["origin_window_end"]
        origin_rec = db.query(OriginEstimate).filter(OriginEstimate.incident_id == incident_id).first()
        if origin_rec:
            origin_rec.center_lat = result["origin_center_lat"]
            origin_rec.center_lon = result["origin_center_lon"]
            origin_rec.uncertainty_radius_km = result["uncertainty_radius_km"]
            origin_rec.origin_window_start = w_start
            origin_rec.origin_window_end = w_end
            origin_rec.probability_contour_geojson = result["geojson"]
            origin_rec.forcing_used = result["forcing_used"]
        else:
            origin_rec = OriginEstimate(
                id=f"ORIGIN-{incident_id}",
                incident_id=incident_id,
                calculation_time=datetime.now(timezone.utc),
                origin_window_start=w_start,
                origin_window_end=w_end,
                center_lat=result["origin_center_lat"],
                center_lon=result["origin_center_lon"],
                uncertainty_radius_km=result["uncertainty_radius_km"],
                probability_contour_geojson=result["geojson"],
                forcing_used=result["forcing_used"]
            )
            db.add(origin_rec)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error persisting origin estimate: {e}")
    
    return result

@router.post("/incidents/{incident_id}/forecast-spill")
def forecast_spill_live(incident_id: str, req: ForecastSpillRequest, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    c_lat = req.slick_lat or inc.center_lat
    c_lon = req.slick_lon or inc.center_lon
    
    env = EnvironmentalSnapshot(
        wind_speed_ms=req.wind_speed_ms or 6.2,
        wind_direction_deg=req.wind_dir_deg or 240.0,
        current_speed_ms=req.current_speed_ms or 0.35,
        current_direction_deg=req.current_dir_deg or 75.0
    )
    
    forecast_steps = drift_engine.simulate_forward_forecast(
        slick_center_lat=c_lat,
        slick_center_lon=c_lon,
        start_time=datetime.now(timezone.utc),
        forecast_horizons_hours=[6.0, 12.0, 24.0, 48.0],
        particle_count=500,
        env=env
    )
    
    try:
        drift_rec = db.query(DriftRun).filter(DriftRun.incident_id == incident_id, DriftRun.run_type == "FORWARD_FORECAST").first()
        if drift_rec:
            drift_rec.forecast_steps = forecast_steps
            drift_rec.environmental_parameters = env.__dict__
        else:
            drift_rec = DriftRun(
                id=f"DRIFT-FWD-{incident_id}",
                incident_id=incident_id,
                run_type="FORWARD_FORECAST",
                start_time=datetime.now(timezone.utc),
                duration_hours=48.0,
                particle_count=500,
                forecast_steps=forecast_steps,
                environmental_parameters=env.__dict__
            )
            db.add(drift_rec)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error persisting drift run: {e}")
    
    impacts = sensitive_impact_service.assess_impact(forecast_steps)
    return {
        "forecast_steps": forecast_steps,
        "impacts": impacts
    }

@router.post("/incidents/{incident_id}/custom-spill-geometry")
def apply_custom_spill_geometry(incident_id: str, req: CustomSpillRequest, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    geom = req.geojson.get("geometry", {})
    coords = geom.get("coordinates", [[]])[0]
    if not coords or len(coords) < 3:
        raise HTTPException(status_code=400, detail="Invalid polygon coordinates: at least 3 points required.")
        
    # Ensure closed ring
    if coords[0] != coords[-1]:
        coords = list(coords) + [coords[0]]
        
    # Compute centroid
    lons = [c[0] for c in coords[:-1]]
    lats = [c[1] for c in coords[:-1]]
    c_lon = round(float(sum(lons) / len(lons)), 6)
    c_lat = round(float(sum(lats) / len(lats)), 6)
    
    # Compute planar geodesic area (km2)
    avg_lat_rad = math.radians(c_lat)
    m_per_deg_lat = 111132.95
    m_per_deg_lon = 111132.95 * math.cos(avg_lat_rad)
    area_m2 = 0.0
    for i in range(len(coords) - 1):
        x1 = coords[i][0] * m_per_deg_lon
        y1 = coords[i][1] * m_per_deg_lat
        x2 = coords[i+1][0] * m_per_deg_lon
        y2 = coords[i+1][1] * m_per_deg_lat
        area_m2 += (x1 * y2 - x2 * y1)
    calc_area_km2 = round(abs(area_m2) / 2.0 / 1e6, 2)
    area_km2 = req.area_km2 or calc_area_km2
    if area_km2 <= 0.0:
        area_km2 = 1.0
    
    # Compute perimeter (km)
    perim_km = 0.0
    for i in range(len(coords) - 1):
        dx = (coords[i+1][0] - coords[i][0]) * m_per_deg_lon
        dy = (coords[i+1][1] - coords[i][1]) * m_per_deg_lat
        perim_km += math.sqrt(dx * dx + dy * dy) / 1000.0
    perim_km = round(perim_km, 2)

    # 1. Update Incident record
    inc.center_lat = c_lat
    inc.center_lon = c_lon

    # 2. Update SpillDetection record
    custom_geom_data = {
        "type": "Feature",
        "properties": {
            "id": f"CUSTOM-{incident_id}",
            "center_lat": c_lat,
            "center_lon": c_lon,
            "area_km2": area_km2,
            "perimeter_km": perim_km,
            "confidence": 0.98,
            "source": "user_manual_trace",
            "name": "User-Traced Spill Area",
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords]
        }
    }
    
    detection = db.query(SpillDetection).filter(SpillDetection.incident_id == incident_id).first()
    if detection:
        detection.geojson_geometry = custom_geom_data
        detection.area_km2 = area_km2
        detection.perimeter_km = perim_km
        detection.morphology_type = "USER_DEFINED_SLICK"
        detection.decision_state = "VERIFIED_OIL_SPILL"
    else:
        detection = SpillDetection(
            id=f"DET-CUSTOM-{incident_id}",
            incident_id=incident_id,
            scene_id=f"SCENE-{incident_id}",
            oil_confidence=0.98,
            look_alike_risk="LOW",
            look_alike_type="BIOMEMBRANE_RULED_OUT",
            decision_state="VERIFIED_OIL_SPILL",
            model_name="Manual User Annotation",
            model_version="1.0",
            area_km2=area_km2,
            perimeter_km=perim_km,
            length_km=round(math.sqrt(area_km2) * 1.5, 2),
            width_km=round(math.sqrt(area_km2) / 1.5, 2),
            orientation_deg=45.0,
            morphology_type="USER_DEFINED_SLICK",
            geojson_geometry=custom_geom_data
        )
        db.add(detection)
    
    # 3. Save to disk in demo folder for persistent storage
    target_folder = "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id
    derived_dir = os.path.join("demo", "incidents", target_folder, "derived")
    os.makedirs(derived_dir, exist_ok=True)
    
    with open(os.path.join(derived_dir, "custom_user_spill.geojson"), "w") as f:
        json.dump(custom_geom_data, f, indent=2)
    with open(os.path.join(derived_dir, "spill_geometry.json"), "w") as f:
        json.dump({
            "status": "available",
            "detection_id": f"DET-CUSTOM-{incident_id}",
            "sensing_time": "2019-06-10T15:48:13+00:00",
            "oil_confidence": 0.96,
            "look_alike_risk": "LOW",
            "look_alike_type": "USER_MANUAL_DELINEATION",
            "decision_state": "VERIFIED_OIL_SPILL",
            "area_km2": area_km2,
            "perimeter_km": perim_km,
            "length_km": round(math.sqrt(max(0.1, area_km2)) * 1.5, 2),
            "width_km": round(area_km2 / max(0.1, math.sqrt(max(0.1, area_km2)) * 1.5), 2),
            "orientation_deg": 45.0,
            "morphology_type": "USER_DRAWN_POLYGON",
            "geojson": custom_geom_data
        }, f, indent=2)
        
    # 4. Recalculate Lagrangian Backward Origin Drift from new centroid
    env = EnvironmentalSnapshot(wind_speed_ms=2.56, wind_direction_deg=325.0, current_speed_ms=0.35, current_direction_deg=75.0, sea_surface_temp_c=24.5)
    env_file = os.path.join("demo", "incidents", target_folder, "environment", "snapshot.json")
    if os.path.exists(env_file):
        try:
            e_dat = json.load(open(env_file))
            env = EnvironmentalSnapshot(
                wind_speed_ms=e_dat.get("wind_speed_ms", 2.56),
                wind_direction_deg=e_dat.get("wind_direction_deg", 325.0),
                current_speed_ms=e_dat.get("current_speed_ms", 0.35),
                current_direction_deg=e_dat.get("current_direction_deg", 75.0),
                sea_surface_temp_c=e_dat.get("sea_surface_temp_c", 24.5)
            )
        except Exception:
            pass

    origin_res = drift_engine.simulate_backward_origin(
        slick_center_lat=c_lat,
        slick_center_lon=c_lon,
        detection_time=datetime(2019, 6, 10, 15, 48, 13, tzinfo=timezone.utc),
        backtrack_hours=2.0,
        particle_count=500,
        env=env
    )
    with open(os.path.join(derived_dir, "origin.json"), "w") as f:
        json.dump(origin_res, f, indent=2)
        
    origin_rec = db.query(OriginEstimate).filter(OriginEstimate.incident_id == incident_id).first()
    w_start = datetime.fromisoformat(origin_res["origin_window_start"]) if isinstance(origin_res["origin_window_start"], str) else origin_res["origin_window_start"]
    w_end = datetime.fromisoformat(origin_res["origin_window_end"]) if isinstance(origin_res["origin_window_end"], str) else origin_res["origin_window_end"]
    if origin_rec:
        origin_rec.center_lat = origin_res["origin_center_lat"]
        origin_rec.center_lon = origin_res["origin_center_lon"]
        origin_rec.uncertainty_radius_km = origin_res["uncertainty_radius_km"]
        origin_rec.origin_window_start = w_start
        origin_rec.origin_window_end = w_end
        origin_rec.probability_contour_geojson = origin_res["geojson"]
        origin_rec.forcing_used = origin_res["forcing_used"]
    else:
        origin_rec = OriginEstimate(
            id=f"ORIGIN-{incident_id}",
            incident_id=incident_id,
            calculation_time=datetime.now(timezone.utc),
            origin_window_start=w_start,
            origin_window_end=w_end,
            center_lat=origin_res["origin_center_lat"],
            center_lon=origin_res["origin_center_lon"],
            uncertainty_radius_km=origin_res["uncertainty_radius_km"],
            probability_contour_geojson=origin_res["geojson"],
            forcing_used=origin_res["forcing_used"]
        )
        db.add(origin_rec)

    # 5. Recalculate forward drift forecast
    forecast_steps = drift_engine.simulate_forward_forecast(
        slick_center_lat=c_lat,
        slick_center_lon=c_lon,
        start_time=datetime(2019, 6, 10, 15, 48, 13, tzinfo=timezone.utc),
        forecast_horizons_hours=[6.0, 12.0, 24.0, 48.0],
        particle_count=500,
        env=env
    )
    with open(os.path.join(derived_dir, "drift.json"), "w") as f:
        json.dump({"forecast_horizons": forecast_steps, "forcing_used": origin_res.get("forcing_used")}, f, indent=2)
        
    drift_rec = db.query(DriftRun).filter(DriftRun.incident_id == incident_id, DriftRun.run_type == "FORWARD_FORECAST").first()
    if drift_rec:
        drift_rec.forecast_steps = forecast_steps

    # 6. Recalculate AIS vessel attribution
    all_vessels = db.query(Vessel).all()
    all_points = db.query(AISPoint).all()
    all_anomalies = db.query(AISAnomaly).all()
    vessels_list = [{"mmsi": v.mmsi, "vessel_name": v.vessel_name, "vessel_type": v.vessel_type, "flag": v.flag, "source_type": v.source_type} for v in all_vessels]
    ais_points_list = [{"mmsi": p.mmsi, "timestamp": p.timestamp.isoformat(), "latitude": p.latitude, "longitude": p.longitude, "sog": p.sog, "cog": p.cog, "heading": p.heading, "source_type": p.source_type} for p in all_points]
    anomalies_list = [{"mmsi": a.mmsi, "latitude": a.latitude, "longitude": a.longitude, "anomaly_type": a.anomaly_type, "severity": a.severity, "description": a.description} for a in all_anomalies]

    who = ais_trajectory_service.who_was_here(
        ais_points=ais_points_list,
        vessels=vessels_list,
        origin_lat=origin_res["origin_center_lat"],
        origin_lon=origin_res["origin_center_lon"],
        origin_window_start=w_start,
        origin_window_end=w_end,
        search_radius_km=35.0
    )

    trajectories = ais_trajectory_service.build_trajectories(ais_points_list)
    candidates = attribution_engine.rank_all_candidates(
        candidates=who,
        trajectories=trajectories,
        anomalies=anomalies_list,
        origin_lat=origin_res["origin_center_lat"],
        origin_lon=origin_res["origin_center_lon"],
        origin_window_start=w_start,
        origin_window_end=w_end,
        slick_orientation_deg=45.0
    )
    db.query(AttributionScore).filter(AttributionScore.incident_id == incident_id).delete()
    for c in candidates:
        attr = AttributionScore(
            id=f"ATTR-{incident_id}-{c['mmsi']}",
            incident_id=incident_id,
            mmsi=c["mmsi"],
            priority_rank=c["priority_rank"],
            priority_level=c["priority_level"],
            total_score=c["total_score"],
            score_proximity=c["breakdown"]["proximity"],
            score_timing=c["breakdown"]["timing"],
            score_trajectory=c["breakdown"]["trajectory"],
            score_ais_gap=c["breakdown"]["ais_gap"],
            score_behaviour_anomaly=c["breakdown"]["behaviour_anomaly"],
            explanation_reasons=c["reasons"],
            calculated_at=datetime.now(timezone.utc),
            disclaimer=c.get("disclaimer", "Investigation priority rank only. Does not constitute legal proof of liability.")
        )
        db.add(attr)
    with open(os.path.join(derived_dir, "attribution.json"), "w") as f:
        json.dump(candidates, f, indent=2)

    db.commit()
    return get_incident_detail(incident_id, db)

@router.post("/incidents/{incident_id}/revert-spill-geometry")
def revert_spill_geometry(incident_id: str, db: Session = Depends(get_db)):
    target_folder = "incident_001" if incident_id in ("VARUNA-2026-001", "SIH-2026-001", "incident_001") else incident_id
    derived_dir = os.path.join("demo", "incidents", target_folder, "derived")
    default_backup = os.path.join(derived_dir, "spill_geometry_default.json")
    if os.path.exists(default_backup):
        import shutil
        shutil.copyfile(default_backup, os.path.join(derived_dir, "spill_geometry.json"))
        default_data = json.load(open(default_backup))
        
        c_lat = 32.006759
        c_lon = 32.815022
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if inc:
            inc.center_lat = c_lat
            inc.center_lon = c_lon
        
        detection = db.query(SpillDetection).filter(SpillDetection.incident_id == incident_id).first()
        if detection:
            detection.geojson_geometry = default_data.get("geojson", {})
            detection.area_km2 = default_data.get("area_km2", 14.68)
            detection.perimeter_km = default_data.get("perimeter_km", 21.4)
            detection.morphology_type = "LINEAR_CONTINUOUS_SLICK"
            
        db.commit()
    return get_incident_detail(incident_id, db)

@router.post("/reports/{incident_id}", response_model=ReportResponse)
def generate_incident_report(incident_id: str, db: Session = Depends(get_db)):
    from apps.api.routes.reports import create_investigation_report
    res = create_investigation_report(incident_id, db)
    return {
        "report_id": res["report_id"],
        "incident_id": incident_id,
        "generated_at": res["report"]["metadata"]["generated_at"],
        "sha256_fingerprint": res["sha256_fingerprint"],
        "pdf_download_url": res["pdf_download_url"],
        "content_markdown": res.get("content_markdown"),
        "report": res["report"]
    }

@router.post("/incidents/inspect-raster")
async def inspect_sar_raster(file: UploadFile = File(...)):
    """
    Directly extracts geospatial coordinates, bounding box, and CRS
    from uploaded GeoTIFF or EXIF-tagged satellite imagery.
    """
    try:
        content = await file.read()
        metadata = geotiff_parser.inspect_metadata(content)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to inspect satellite image: {str(e)}")

@router.post("/incidents/upload-sar")
async def upload_and_process_sar(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    wind_speed_ms: Optional[float] = Form(6.2),
    current_speed_ms: Optional[float] = Form(0.35),
    db: Session = Depends(get_db)
):
    """
    Uploads a real SAR raster (GeoTIFF / TIFF / PNG / JPG).
    1. Extracts real-world WGS-84 coordinates directly from the image geokeys/EXIF.
    2. Feeds extracted dual-pol VV/VH arrays directly into the PyTorch U-Net & Look-Alike classifier.
    3. Triggers Lagrangian reverse drift to find source probability contour.
    4. Correlates maritime AIS traffic.
    5. Saves full incident investigation record into the database and returns incident ID.
    """
    try:
        content = await file.read()
        extracted = geotiff_parser.extract_metadata_and_array(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded image: {str(e)}")

    # Use coordinates extracted directly from the picture metadata unless manually overridden
    center_lat = lat if (lat is not None and lat != 0.0) else extracted["center_lat"]
    center_lon = lon if (lon is not None and lon != 0.0) else extracted["center_lon"]
    bbox = extracted["bbox"]

    now = datetime.now(timezone.utc)
    ts_str = now.strftime("%Y%m%d%H%M%S")
    incident_id = f"VARUNA-{ts_str}"
    
    # 1. Run Satellite ML Pipeline on real extracted pixel arrays
    ml_result = satellite_ml_pipeline.run_inference(
        sar_tensor_vv=extracted["array_vv"],
        sar_tensor_vh=extracted["array_vh"],
        center_lat=center_lat,
        center_lon=center_lon,
        wind_speed_ms=wind_speed_ms or 6.2,
        coastal_distance_km=18.4,
        threshold=0.5
    )

    # 2. Persist Incident
    inc_title = title.strip() if title and title.strip() else f"Observation {incident_id} — SAR Attribution"
    incident = Incident(
        id=incident_id,
        title=inc_title,
        description=f"SAR Observation processed via Varuna. Spatial source: {extracted.get('source', 'Satellite Raster')}. Georeference verified: {extracted['has_georeference']}.",
        status="INVESTIGATING",
        created_at=now,
        center_lat=center_lat,
        center_lon=center_lon,
        spill_window_start=now - timedelta(hours=8),
        spill_window_end=now,
        provenance={
            "sensor": "Sentinel-1 SAR C-Band",
            "crs": extracted["crs"],
            "has_georeference": extracted["has_georeference"],
            "metadata_source": extracted.get("source", "Satellite Raster"),
            "width": extracted["width"],
            "height": extracted["height"],
            "band_count": extracted["band_count"],
            "original_filename": file.filename
        }
    )
    db.add(incident)

    # 3. Persist Satellite Scene
    scene = SatelliteScene(
        id=f"SCENE-{ts_str}",
        incident_id=incident.id,
        satellite_name="Sentinel-1 SAR",
        acquisition_time=now,
        polarizations=["VV", "VH"] if extracted["band_count"] > 1 else ["VV"],
        bbox=bbox,
        quality_score=ml_result["quality_gate"].get("quality_grade", "HIGH"),
        quality_details=ml_result["quality_gate"]
    )
    db.add(scene)

    # 4. Persist Spill Detection
    morph = ml_result.get("morphometrics", {})
    oil_confidence = float(ml_result.get("oil_confidence", 0.92))
    look_alike_risk = str(ml_result.get("look_alike_risk", "LOW"))
    look_alike_type = ml_result.get("look_alike_type")
    decision_state = str(ml_result.get("decision_state", "OIL"))

    detection = SpillDetection(
        id=f"DET-{ts_str}",
        incident_id=incident.id,
        scene_id=scene.id,
        detection_time=now,
        oil_confidence=oil_confidence,
        look_alike_risk=look_alike_risk,
        look_alike_type=look_alike_type,
        decision_state=decision_state,
        model_name="unet_oil_segmentation_v1",
        model_version="1.0.0",
        area_km2=morph.get("area_km2", 10.0),
        perimeter_km=morph.get("perimeter_km", 20.0),
        length_km=morph.get("length_km", 8.0),
        width_km=morph.get("width_km", 2.0),
        orientation_deg=morph.get("orientation_deg", 45.0),
        morphology_type=morph.get("morphology_type", "LINEAR_SLICK"),
        geojson_geometry=morph.get("geojson", {})
    )
    db.add(detection)

    # 5. Run Lagrangian Backward Drift Simulation
    env = EnvironmentalSnapshot(
        wind_speed_ms=wind_speed_ms or 6.2,
        wind_direction_deg=240.0,
        current_speed_ms=current_speed_ms or 0.35,
        current_direction_deg=75.0
    )
    origin_res = drift_engine.simulate_backward_origin(
        slick_center_lat=center_lat,
        slick_center_lon=center_lon,
        detection_time=now,
        backtrack_hours=6.0,
        particle_count=500,
        env=env
    )
    origin_est = OriginEstimate(
        id=f"ORIGIN-{ts_str}",
        incident_id=incident.id,
        calculation_time=now,
        origin_window_start=datetime.fromisoformat(origin_res["origin_window_start"]),
        origin_window_end=datetime.fromisoformat(origin_res["origin_window_end"]),
        center_lat=origin_res["origin_center_lat"],
        center_lon=origin_res["origin_center_lon"],
        uncertainty_radius_km=origin_res["uncertainty_radius_km"],
        probability_contour_geojson=origin_res["geojson"],
        forcing_used=origin_res["forcing_used"]
    )
    db.add(origin_est)

    # 6. Correlate with AIS & rank candidates
    all_vessels = db.query(Vessel).all()
    all_points = db.query(AISPoint).all()
    all_anomalies = db.query(AISAnomaly).all()

    vessels_list = [
        {"mmsi": v.mmsi, "vessel_name": v.vessel_name, "vessel_type": v.vessel_type, "flag": v.flag, "source_type": v.source_type}
        for v in all_vessels
    ]
    ais_points_list = [
        {
            "mmsi": p.mmsi,
            "timestamp": p.timestamp.isoformat(),
            "latitude": p.latitude,
            "longitude": p.longitude,
            "sog": p.sog,
            "cog": p.cog,
            "heading": p.heading,
            "source_type": p.source_type
        } for p in all_points
    ]
    anomalies_list = [
        {
            "mmsi": a.mmsi,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "anomaly_type": a.anomaly_type,
            "severity": a.severity,
            "description": a.description,
            "raw_details": a.raw_details
        } for a in all_anomalies
    ]

    candidates = ais_trajectory_service.who_was_here(
        ais_points=ais_points_list,
        vessels=vessels_list,
        origin_lat=origin_res["origin_center_lat"],
        origin_lon=origin_res["origin_center_lon"],
        origin_window_start=origin_est.origin_window_start,
        origin_window_end=origin_est.origin_window_end,
        search_radius_km=35.0
    )

    trajectories = ais_trajectory_service.build_trajectories(ais_points_list)
    ranked_scores = attribution_engine.rank_all_candidates(
        candidates=candidates,
        trajectories=trajectories,
        anomalies=anomalies_list,
        origin_lat=origin_res["origin_center_lat"],
        origin_lon=origin_res["origin_center_lon"],
        origin_window_start=origin_est.origin_window_start,
        origin_window_end=origin_est.origin_window_end,
        slick_orientation_deg=morph["orientation_deg"]
    )

    for sc in ranked_scores:
        attr_obj = AttributionScore(
            id=f"ATTR-{incident.id}-{sc['mmsi']}",
            incident_id=incident.id,
            mmsi=sc["mmsi"],
            priority_rank=sc["priority_rank"],
            total_score=sc["total_score"],
            priority_level=sc["priority_level"],
            score_proximity=sc["breakdown"]["proximity"],
            score_timing=sc["breakdown"]["timing"],
            score_trajectory=sc["breakdown"]["trajectory"],
            score_ais_gap=sc["breakdown"]["ais_gap"],
            score_behaviour_anomaly=sc["breakdown"]["behaviour_anomaly"],
            explanation_reasons=sc["reasons"],
            calculated_at=now
        )
        db.add(attr_obj)

    # 7. Run Forward Drift
    forecast_steps = drift_engine.simulate_forward_forecast(
        slick_center_lat=center_lat,
        slick_center_lon=center_lon,
        start_time=now,
        forecast_horizons_hours=[6.0, 12.0, 24.0, 48.0],
        particle_count=500,
        env=env
    )
    drift_fwd = DriftRun(
        id=f"DRIFT-FWD-{ts_str}",
        incident_id=incident.id,
        run_type="FORWARD_FORECAST",
        start_time=now,
        duration_hours=48.0,
        particle_count=500,
        forecast_steps=forecast_steps,
        environmental_parameters={"wind_speed_ms": wind_speed_ms, "current_speed_ms": current_speed_ms}
    )
    db.add(drift_fwd)

    # 8. Add initial Evidence Items
    db.add(EvidenceItem(
        id=f"EV-{ts_str}-1",
        incident_id=incident.id,
        category="SATELLITE",
        title="SAR Detection & Quality Gate Verification",
        content=f"Sensor: Sentinel-1 SAR. Coordinates: {center_lat}° N, {center_lon}° E. Spatial Source: {extracted.get('source', 'SAR Raster')}. Decision: {decision_state} (Confidence: {oil_confidence*100:.1f}%).",
        confidence=oil_confidence
    ))
    db.add(EvidenceItem(
        id=f"EV-{ts_str}-2",
        incident_id=incident.id,
        category="DRIFT",
        title="Lagrangian Reverse Particle Backtrack",
        content=f"Reverse simulation computed origin centroid at {origin_res['origin_center_lat']}° N, {origin_res['origin_center_lon']}° E with uncertainty radius {origin_res['uncertainty_radius_km']} km.",
        confidence=0.88
    ))

    db.commit()

    return {
        "status": "SUCCESS",
        "incident_id": incident.id,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "has_georeference": extracted["has_georeference"],
        "metadata_source": extracted.get("source"),
        "message": extracted.get("message"),
        "detection": {
            "decision_state": decision_state,
            "oil_confidence": oil_confidence,
            "area_km2": morph.get("area_km2", 10.0)
        },
        "redirect_url": f"/investigation/{incident.id}/overview"
    }



from fastapi.responses import StreamingResponse
import io

@router.get("/incidents/{incident_id}/satellite/image")
def get_satellite_image(incident_id: str, overlay: bool = False, db: Session = Depends(get_db)):
    import os
    import rasterio
    import numpy as np
    from PIL import Image
    
    base_dir = os.path.join("demo", "incidents", "incident_001")
    custom_path = os.path.join(base_dir, "satellite", "final-mark.png")
    if overlay and os.path.exists(custom_path):
        from fastapi.responses import FileResponse
        return FileResponse(custom_path, media_type="image/png")

    vv_path = os.path.join(base_dir, "satellite", "vv.tif")
        
    if not os.path.exists(vv_path):
        raise HTTPException(status_code=404, detail="SAR raster files not found.")
        
    try:
        with rasterio.open(vv_path) as src_vv:
            from rasterio.enums import Resampling
            sar_vv = src_vv.read(1, out_shape=(1, 1024, 1024), resampling=Resampling.bilinear).astype(np.float32)
            
            # Normal Grayscale SAR image visualization using 2nd-98th percentile stretch
            valid_pixels = sar_vv[sar_vv > 0]
            if len(valid_pixels) > 0:
                p2, p98 = np.percentile(valid_pixels, (2, 98))
            else:
                p2, p98 = np.percentile(sar_vv, (2, 98))
                
            norm_vv = np.clip((sar_vv - p2) / (p98 - p2 + 1e-7), 0.0, 1.0)
            gray_array = (norm_vv * 255.0).astype(np.uint8)
            
            img = Image.fromarray(gray_array, mode='L')
            buf = io.BytesIO()
            img.save(buf, format='PNG', optimize=True)
            buf.seek(0)
            
            return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read raster: {e}")

@router.get("/incidents/{incident_id}/satellite/bounds")
def get_satellite_bounds(incident_id: str, overlay: bool = False, db: Session = Depends(get_db)):
    import os
    import rasterio
    
    base_dir = os.path.join("demo", "incidents", "incident_001")
    final_mark_path = os.path.join(base_dir, "satellite", "final-mark.png")
    if overlay and os.path.exists(final_mark_path):
        # Precise GCP-derived coordinates for final-mark.png [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
        return {
            "coordinates": [
                [32.790459, 32.001234],
                [33.037687, 32.039857],
                [33.080393, 31.858586],
                [32.826188, 31.816656]
            ]
        }

    vv_path = os.path.join(base_dir, "satellite", "vv.tif")
        
    if os.path.exists(vv_path):
        with rasterio.open(vv_path) as src:
            gcps, gcps_crs = src.gcps
            if len(gcps) > 0:
                from rasterio.transform import GCPTransformer
                transformer = GCPTransformer(gcps)
                w, h = src.width, src.height
                # MapLibre image source expects coordinates in [top-left, top-right, bottom-right, bottom-left]
                # In SAR raster space (row 0 = South, row h = North):
                # top-left (North-West) = (h, 0)
                # top-right (North-East) = (h, w)
                # bottom-right (South-East) = (0, w)
                # bottom-left (South-West) = (0, 0)
                tl = transformer.xy(h, 0)
                tr = transformer.xy(h, w)
                br = transformer.xy(0, w)
                bl = transformer.xy(0, 0)
                return {"coordinates": [[tl[0], tl[1]], [tr[0], tr[1]], [br[0], br[1]], [bl[0], bl[1]]]}
            else:
                bounds = src.bounds
                tl = [bounds.left, bounds.top]
                tr = [bounds.right, bounds.top]
                br = [bounds.right, bounds.bottom]
                bl = [bounds.left, bounds.bottom]
                return {"coordinates": [tl, tr, br, bl]}
    raise HTTPException(status_code=404, detail="Bounds not found")
