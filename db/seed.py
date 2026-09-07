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
                    id=sg.get("detection_id", f"DET-{incident.id}"),
                    incident_id=incident.id,
                    scene_id=scene.id,
                    detection_time=datetime.datetime.fromisoformat(sg.get("sensing_time", "2019-06-10T15:48:13+00:00").replace("Z", "+00:00")),
                    oil_confidence=sg.get("oil_confidence", 0.94),
                    look_alike_risk=sg.get("look_alike_risk", "LOW"),
                    look_alike_type=sg.get("look_alike_type", "BIOMEMBRANE_NATURAL_FILM_RULED_OUT"),
                    decision_state=sg.get("decision_state", "VERIFIED_OIL_SPILL"),
                    model_name="unet_oil_segmentation_v1",
                    model_version="1.0.0",
                    area_km2=sg.get("area_km2", 14.68),
                    perimeter_km=sg.get("perimeter_km", 21.4),
                    length_km=sg.get("length_km", 8.5),
                    width_km=sg.get("width_km", 2.2),
                    orientation_deg=sg.get("orientation_deg", 45.0),
                    morphology_type=sg.get("morphology_type", "LINEAR_CONTINUOUS_SLICK"),
                    geojson_geometry=sg.get("geojson", {})
                )
                db.add(det)

        # 4. Origin Estimate
        org = None
        origin_path = os.path.join(base_dir, "derived", "origin.json")
        if os.path.exists(origin_path):
            with open(origin_path) as f:
                og = json.load(f)
            
            # Extract safe values with fallbacks
            org = OriginEstimate(
                id=f"ORIGIN-{incident.id}",
                incident_id=incident.id,
                calculation_time=datetime.datetime.now(),
                origin_window_start=datetime.datetime.fromisoformat(og.get("origin_window_start", "2019-06-10T12:48:13+00:00").replace("Z", "+00:00")),
                origin_window_end=datetime.datetime.fromisoformat(og.get("origin_window_end", "2019-06-10T14:48:13+00:00").replace("Z", "+00:00")),
                center_lat=og.get("origin_center_lat", incident.center_lat),
                center_lon=og.get("origin_center_lon", incident.center_lon),
                uncertainty_radius_km=og.get("uncertainty_radius_km", 1.0),
                probability_contour_geojson=og.get("geojson", {}),
                forcing_used=og.get("forcing_used", [])
            )
            db.add(org)

        # 5. Drift Run (Forward Forecast)
        drift_obj = None
        drift_path = os.path.join(base_dir, "derived", "drift.json")
        if os.path.exists(drift_path):
            with open(drift_path) as f:
                dr = json.load(f)
            
            drift_obj = DriftRun(
                id=f"DRIFT-FWD-{incident.id}",
                incident_id=incident.id,
                run_type="FORWARD_FORECAST",
                start_time=datetime.datetime.fromisoformat(dr.get("start_time", "2019-06-10T15:48:13+00:00").replace("Z", "+00:00")),
                duration_hours=48.0,
                particle_count=500,
                forecast_steps=dr.get("forecast_steps", dr.get("forecast_horizons", [])),
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
            content=f"Verified 14.68 km² oil slick from product S1B_IW_GRDH_1SDV_20190610T154813 near {incident.center_lat:.3f}° N, {incident.center_lon:.3f}° E. Spatial confidence 94%.",
            confidence=0.94
        ))
        db.add(EvidenceItem(
            id=f"EV-{incident.id}-2",
            incident_id=incident.id,
            category="DRIFT",
            title="Lagrangian Reverse Particle Backtrack",
            content=f"Hydrodynamic reverse drift simulation computed probable spill origin centroid at {org.center_lat:.4f}° N, {org.center_lon:.4f}° E between 13:45 and 14:45 UTC.",
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
