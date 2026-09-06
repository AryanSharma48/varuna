import os
import json
import datetime
from sqlalchemy.orm import Session
from db.database import engine, Base, SessionLocal
from db.models import (
    Incident, SatelliteScene, SpillDetection, OriginEstimate,
    Vessel, AISPoint, AISAnomaly, AttributionScore, DriftRun,
    SensitiveAsset, EvidenceItem
)

def seed_demo_data():
    """Initializes database tables and populates the deterministic SIH-2026-001 demo incident."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    try:
        # Check if already seeded
        existing = db.query(Incident).filter(Incident.id == "SIH-2026-001").first()
        if existing:
            print("Demo incident SIH-2026-001 already exists in database. Overwriting...")
            db.query(AttributionScore).filter(AttributionScore.incident_id == "SIH-2026-001").delete()
            db.query(AISAnomaly).filter(AISAnomaly.incident_id == "SIH-2026-001").delete()
            db.query(AISPoint).delete()
            db.query(Vessel).delete()
            db.query(DriftRun).filter(DriftRun.incident_id == "SIH-2026-001").delete()
            db.query(OriginEstimate).filter(OriginEstimate.incident_id == "SIH-2026-001").delete()
            db.query(SpillDetection).filter(SpillDetection.incident_id == "SIH-2026-001").delete()
            db.query(SatelliteScene).filter(SatelliteScene.incident_id == "SIH-2026-001").delete()
            db.query(EvidenceItem).filter(EvidenceItem.incident_id == "SIH-2026-001").delete()
            db.query(Incident).filter(Incident.id == "SIH-2026-001").delete()
            db.commit()

        print("Seeding SIH-2026-001 Maritime Investigation Real DARTIS Demo Data...")
        
        base_dir = os.path.join("demo", "incidents", "incident_001")
        meta_path = os.path.join(base_dir, "metadata.json")
        geo_path = os.path.join(base_dir, "satellite", "georeferencing.json")
        
        with open(meta_path) as f:
            md = json.load(f)
            
        with open(geo_path) as f:
            geo = json.load(f)
        
        # 1. Incident
        incident = Incident(
            id=md["incident_id"],
            title=md["title"],
            description=md["description"],
            status=md["status"],
            created_at=datetime.datetime.now(),
            center_lat=md["center_lat"],
            center_lon=md["center_lon"],
            spill_window_start=datetime.datetime.fromisoformat(md["spill_window_start"].replace("Z", "+00:00")),
            spill_window_end=datetime.datetime.fromisoformat(md["spill_window_end"].replace("Z", "+00:00")),
            provenance=md["provenance"]
        )
        db.add(incident)
        
        # 2. Satellite Scene
        scene = SatelliteScene(
            id=f"SCENE-{md['incident_id']}",
            incident_id=incident.id,
            satellite_name=md["provenance"]["satellite_source"],
            acquisition_time=datetime.datetime.fromisoformat(md["provenance"]["sensing_timestamp"].replace("Z", "+00:00")),
            polarizations=md["provenance"]["polarizations"],
            bbox=[32.7, 31.8, 33.0, 32.1],
            file_path=os.path.join(base_dir, "satellite", "vv.tif"),
            quality_score="HIGH",
            quality_details={
                "georeferencing": geo,
                "reasons": []
            }
        )
        db.add(scene)

        # 3. Spill Detection
        spill_geom_path = os.path.join(base_dir, "derived", "spill_geometry.json")
        if os.path.exists(spill_geom_path):
            with open(spill_geom_path) as f:
                sg = json.load(f)
            if sg.get("status") == "available":
                det = SpillDetection(
                    id=sg["detection_id"],
                    incident_id=incident.id,
                    scene_id=scene.id,
                    detection_time=datetime.datetime.fromisoformat(sg["sensing_time"].replace("Z", "+00:00")),
                    oil_confidence=sg["oil_confidence"],
                    look_alike_risk=sg["look_alike_risk"],
                    look_alike_type=sg["look_alike_type"],
                    decision_state=sg["decision_state"],
                    model_name="unet_oil_segmentation_v1",
                    model_version="1.0.0",
                    area_km2=sg["area_km2"],
                    perimeter_km=sg["perimeter_km"],
                    length_km=sg["length_km"],
                    width_km=sg["width_km"],
                    orientation_deg=sg["orientation_deg"],
                    morphology_type=sg["morphology_type"],
                    geojson_geometry=sg["geojson"]
                )
                db.add(det)

        # 4. Origin Estimate
        origin_path = os.path.join(base_dir, "derived", "origin.json")
        if os.path.exists(origin_path):
            with open(origin_path) as f:
                og = json.load(f)
            if og.get("status") == "available":
                org = OriginEstimate(
                    id=f"ORIGIN-{incident.id}",
                    incident_id=incident.id,
                    calculation_time=datetime.datetime.now(),
                    origin_window_start=datetime.datetime.fromisoformat(og["origin_window_start"].replace("Z", "+00:00")),
                    origin_window_end=datetime.datetime.fromisoformat(og["origin_window_end"].replace("Z", "+00:00")),
                    center_lat=og["origin_center_lat"],
                    center_lon=og["origin_center_lon"],
                    uncertainty_radius_km=og["uncertainty_radius_km"],
                    probability_contour_geojson=og["geojson"],
                    forcing_used=og["forcing_used"]
                )
                db.add(org)

        # 5. Drift Run (Forward Forecast)
        drift_path = os.path.join(base_dir, "derived", "drift.json")
        if os.path.exists(drift_path):
            with open(drift_path) as f:
                dr = json.load(f)
            if dr.get("status") == "available":
                drift_obj = DriftRun(
                    id=f"DRIFT-FWD-{incident.id}",
                    incident_id=incident.id,
                    run_type="FORWARD_FORECAST",
                    start_time=datetime.datetime.fromisoformat(dr["start_time"].replace("Z", "+00:00")),
                    duration_hours=48.0,
                    particle_count=500,
                    forecast_steps=dr["forecast_steps"],
                    environmental_parameters={"wind_speed_ms": 2.56, "current_speed_ms": 0.35}
                )
                db.add(drift_obj)

        # 6. Vessels
        vessels_path = os.path.join(base_dir, "ais", "vessels.json")
        if os.path.exists(vessels_path):
            with open(vessels_path) as f:
                vl = json.load(f)
            for v in vl:
                v_obj = Vessel(
                    mmsi=v["mmsi"],
                    vessel_name=v["vessel_name"],
                    vessel_type=v["vessel_type"],
                    flag=v["flag"],
                    imo=v.get("imo"),
                    length_m=v.get("length_m"),
                    width_m=v.get("beam_m"),
                    source_type=v.get("source_type", "TERRESTRIAL_AIS")
                )
                db.add(v_obj)

        # 7. AIS Points
        points_path = os.path.join(base_dir, "ais", "points.json")
        if os.path.exists(points_path):
            with open(points_path) as f:
                pl = json.load(f)
            for p in pl:
                p_obj = AISPoint(
                    mmsi=p["mmsi"],
                    timestamp=datetime.datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")),
                    latitude=p["latitude"],
                    longitude=p["longitude"],
                    sog=p["sog"],
                    cog=p["cog"],
                    heading=p["heading"],
                    source_type=p.get("source_type", "TERRESTRIAL_AIS")
                )
                db.add(p_obj)

        # 8. AIS Anomalies
        anom_path = os.path.join(base_dir, "ais", "anomalies.json")
        if os.path.exists(anom_path):
            with open(anom_path) as f:
                al = json.load(f)
            for a in al:
                a_obj = AISAnomaly(
                    id=a["id"],
                    incident_id=incident.id,
                    mmsi=a["mmsi"],
                    timestamp=datetime.datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00")),
                    latitude=a["latitude"],
                    longitude=a["longitude"],
                    anomaly_type=a["anomaly_type"],
                    severity=a["severity"],
                    description=a["description"],
                    raw_details=a.get("raw_details")
                )
                db.add(a_obj)

        # 9. Attribution Scores
        attr_path = os.path.join(base_dir, "derived", "attribution.json")
        if os.path.exists(attr_path):
            with open(attr_path) as f:
                ats = json.load(f)
            for s in ats:
                s_obj = AttributionScore(
                    id=f"ATTR-{incident.id}-{s['mmsi']}",
                    incident_id=incident.id,
                    mmsi=s["mmsi"],
                    priority_rank=s["priority_rank"],
                    total_score=s["total_score"],
                    priority_level=s["priority_level"],
                    score_proximity=s["breakdown"]["proximity"],
                    score_timing=s["breakdown"]["timing"],
                    score_trajectory=s["breakdown"]["trajectory"],
                    score_ais_gap=s["breakdown"]["ais_gap"],
                    score_behaviour_anomaly=s["breakdown"]["behaviour_anomaly"],
                    explanation_reasons=s["reasons"],
                    disclaimer=s.get("disclaimer"),
                    calculated_at=datetime.datetime.now()
                )
                db.add(s_obj)

        # 10. Evidence Items
        db.add(EvidenceItem(
            id=f"EV-{incident.id}-1",
            incident_id=incident.id,
            category="SATELLITE",
            title="Copernicus Sentinel-1B SAR Detection",
            content="Verified 14.68 km² oil slick from product S1B_IW_GRDH_1SDV_20190610T154813 near 31.983° N, 32.849° E. Spatial confidence 94%.",
            confidence=0.94
        ))
        db.add(EvidenceItem(
            id=f"EV-{incident.id}-2",
            incident_id=incident.id,
            category="DRIFT",
            title="Lagrangian Reverse Particle Backtrack",
            content="Hydrodynamic reverse drift simulation computed probable spill origin centroid at 31.9815° N, 32.8272° E between 13:45 and 14:45 UTC.",
            confidence=0.89
        ))
        db.add(EvidenceItem(
            id=f"EV-{incident.id}-3",
            incident_id=incident.id,
            category="AIS",
            title="Dark Vessel AIS Anomaly Correlated",
            content="MMSI 636018245 (MT AL NAJAF) exhibited a 22-minute unannounced AIS blackout (14:15–14:37 UTC) directly inside the origin centroid.",
            confidence=0.92
        ))

        db.commit()
        print("Database successfully seeded with complete real Sentinel-1 demo scenario!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
