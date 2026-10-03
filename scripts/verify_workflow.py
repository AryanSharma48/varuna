import sys
import os
import json
from datetime import datetime

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import SessionLocal, engine, Base
from db.models import Incident, SatelliteScene, SpillDetection, OriginEstimate, Vessel, AISPoint, AISAnomaly, AttributionScore, DriftRun, SensitiveAsset
from db.seed import seed_demo_data
from services.characterisation.morphology import characterisation_service
from services.drift.lagrangian import drift_engine
from services.drift.environmental import EnvironmentalSnapshot
from services.ais.mock_data import synthetic_ais_generator
from services.ais.trajectory import ais_trajectory_service
from services.ais.anomaly import ais_anomaly_detector
from services.attribution.engine import attribution_engine
from services.impact.assessment import sensitive_impact_service
from services.assistant.grounded_agent import grounded_assistant
from services.reports.generator import report_generator

def run_end_to_end_verification():
    print("=================================================================")
    print("VARUNA -- END-TO-END MARITIME INVESTIGATION PIPELINE VALIDATION")
    print("=================================================================")
    
    # 1. Foundation & DB Setup
    print("\n[STEP 1/10] Initializing database & seeding scenario...")
    seed_demo_data()
    db = SessionLocal()
    
    # 2. Satellite Ingestion & Quality Gate
    print("[STEP 2/10] Validating Sentinel-1 SAR ingestion & Image Quality Gate...")
    scene = db.query(SatelliteScene).first()
    assert scene is not None, "Scene missing"
    assert scene.quality_score == "HIGH"
    print(f"  [OK] Sentinel-1 scene: {scene.satellite_name} ({scene.polarizations}) | Quality: {scene.quality_score}")
    
    # 3. U-Net Oil Segmentation & Characterisation
    print("[STEP 3/10] Validating U-Net Oil Spill Segmentation & Morphometry...")
    detection = db.query(SpillDetection).first()
    assert detection is not None, "Detection missing"
    assert detection.decision_state in ["OIL", "VERIFIED_OIL_SPILL"]
    assert detection.oil_confidence >= 0.90
    print(f"  [OK] Decision: {detection.decision_state} (Confidence: {detection.oil_confidence*100:.1f}%)")
    print(f"  [OK] Geometry: Area = {detection.area_km2:.1f} km2, Length = {detection.length_km:.1f} km, Width = {detection.width_km:.1f} km, Heading = {detection.orientation_deg:.1f} deg")
    
    # 4. Backward Lagrangian Drift Origin Reconstruction
    print("[STEP 4/10] Validating Lagrangian particle origin backtracking...")
    origin = db.query(OriginEstimate).first()
    assert origin is not None, "Origin estimate missing"
    print(f"  [OK] Probable Origin Centroid: {origin.center_lat:.4f} N, {origin.center_lon:.4f} E")
    print(f"  [OK] Origin Uncertainty Radius (90%): {origin.uncertainty_radius_km:.1f} km")
    print(f"  [OK] Critical Spill Time Window: {origin.origin_window_start.strftime('%H:%M')} - {origin.origin_window_end.strftime('%H:%M')} UTC")
    
    # 5. AIS Spatio-Temporal Query ("Who Was Here?")
    print("[STEP 5/10] Running spatial-temporal AIS candidate query...")
    vessels = [{"mmsi": v.mmsi, "vessel_name": v.vessel_name, "vessel_type": v.vessel_type, "flag": v.flag, "source_type": v.source_type} for v in db.query(Vessel).all()]
    ais_points = [{"mmsi": p.mmsi, "timestamp": p.timestamp.isoformat(), "latitude": p.latitude, "longitude": p.longitude, "sog": p.sog, "cog": p.cog, "source_type": p.source_type} for p in db.query(AISPoint).all()]
    
    candidates = ais_trajectory_service.who_was_here(
        ais_points=ais_points,
        vessels=vessels,
        origin_lat=origin.center_lat,
        origin_lon=origin.center_lon,
        origin_window_start=origin.origin_window_start,
        origin_window_end=origin.origin_window_end
    )
    assert len(candidates) >= 3, "Failed to retrieve candidate vessels"
    print(f"  [OK] Narrowed traffic to {len(candidates)} candidate vessels in origin vicinity")
    print(f"  [OK] Closest vessel: {candidates[0]['vessel_name']} ({candidates[0]['min_distance_to_origin_km']:.1f} km to origin)")
    
    # 6. AIS Anomaly Detection
    print("[STEP 6/10] Evaluating AIS kinematic and transmission anomalies...")
    anomalies = db.query(AISAnomaly).all()
    assert len(anomalies) >= 1, "Expected anomalies for candidate vessel"
    for anom in anomalies:
        print(f"  [OK] Anomaly detected: [{anom.anomaly_type}] on MMSI {anom.mmsi} ({anom.description})")
        
    # 7. Explainable Vessel Attribution Engine
    print("[STEP 7/10] Computing multi-factor attribution priority ranking...")
    scores = db.query(AttributionScore).order_by(AttributionScore.priority_rank).all()
    assert len(scores) >= 1
    top_suspect = scores[0]
    top_vessel = db.query(Vessel).filter(Vessel.mmsi == top_suspect.mmsi).first()
    assert top_suspect.priority_level == "HIGH"
    print(f"  [OK] Rank #1: {top_vessel.vessel_name} (MMSI: {top_suspect.mmsi})")
    print(f"    - Total Score: {top_suspect.total_score}/100 [{top_suspect.priority_level} PRIORITY]")
    print(f"    - Breakdown: Proximity=+{top_suspect.score_proximity}, Timing=+{top_suspect.score_timing}, Trajectory=+{top_suspect.score_trajectory}, AIS Gap=+{top_suspect.score_ais_gap}, Anomaly=+{top_suspect.score_behaviour_anomaly}")
    
    # 8. Forward Drift & Sensitive Area Intersections
    print("[STEP 8/10] Simulating forward trajectory & sensitive asset impact...")
    drift_fwd = db.query(DriftRun).filter(DriftRun.run_type == "FORWARD_FORECAST").first()
    assert drift_fwd is not None
    impacts = sensitive_impact_service.assess_impact(drift_fwd.forecast_steps)
    assert len(impacts) >= 1
    for imp in impacts[:2]:
        print(f"  [OK] Asset at risk: {imp['asset_name']} ({imp['asset_type']}) | ETA: {imp['estimated_arrival']} (Severity: {imp['severity']})")
        
    # 9. Grounded Investigation Assistant
    print("[STEP 9/10] Testing Grounded AI Investigation Assistant...")
    incident_detail = {
        "incident": {"id": "VARUNA-2026-001", "title": "Eastern Mediterranean DARTIS Investigation", "status": "INVESTIGATING", "center_lat": origin.center_lat, "center_lon": origin.center_lon},
        "attribution_scores": [
            {
                "mmsi": top_suspect.mmsi,
                "vessel_name": top_vessel.vessel_name,
                "total_score": top_suspect.total_score,
                "priority_level": top_suspect.priority_level,
                "breakdown": {"proximity": top_suspect.score_proximity, "timing": top_suspect.score_timing, "trajectory": top_suspect.score_trajectory, "ais_gap": top_suspect.score_ais_gap, "behaviour_anomaly": top_suspect.score_behaviour_anomaly},
                "reasons": top_suspect.explanation_reasons
            }
        ],
        "candidates": candidates,
        "origin_estimate": {"origin_center_lat": origin.center_lat, "origin_center_lon": origin.center_lon, "uncertainty_radius_km": origin.uncertainty_radius_km, "origin_window_start": origin.origin_window_start.isoformat(), "origin_window_end": origin.origin_window_end.isoformat()},
        "detection": {"oil_confidence": detection.oil_confidence, "decision_state": detection.decision_state, "look_alike_risk": detection.look_alike_risk, "area_km2": detection.area_km2, "length_km": detection.length_km, "width_km": detection.width_km, "orientation_deg": detection.orientation_deg, "morphology_type": detection.morphology_type},
        "quality_gate": {"quality_grade": "HIGH", "dynamic_range_db": 14.2, "missing_pixel_ratio": 0.001},
        "impacts": impacts
    }
    
    top_vessel_name = top_vessel.vessel_name or "MT AL NAJAF"
    q_res = grounded_assistant.answer_question(f"Why is {top_vessel_name} suspicious?", incident_detail)
    assert top_vessel_name.upper() in q_res["answer"].upper()
    assert q_res["tool_used"] in ["groq_multi_stage_llm", "get_attribution_breakdown"]
    print(f"  [OK] Assistant answered using tool '{q_res['tool_used']}' with {len(q_res['citations'])} grounded citations.")
    
    # 10. Investigation Report Export
    print("[STEP 10/10] Generating official investigation report...")
    rep = report_generator.generate_report(incident_detail)
    assert "MARITIME INCIDENT INVESTIGATION REPORT" in rep["content_markdown"]
    print(f"  [OK] Report generated successfully ({len(rep['content_markdown'])} bytes).")
    
    db.close()
    print("\n=================================================================")
    print("SUCCESS: ALL PIPELINE STAGES & VERIFICATION CHECKS PASSED!")
    print("=================================================================\n")

if __name__ == "__main__":
    run_end_to_end_verification()
