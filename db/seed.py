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
    """Initializes database tables and populates the deterministic SIH-26143 demo incident."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    try:
        # Check if already seeded
        existing = db.query(Incident).filter(Incident.id == "SIH-2026-001").first()
        if existing:
            print("Demo incident SIH-2026-001 already exists in database.")
            return

        print("Seeding SIH-26143 Maritime Investigation Demo Data...")
        
        # Load from disk
        base_dir = os.path.join("demo", "incidents", "incident_001")
        meta_path = os.path.join(base_dir, "metadata.json")
        geo_path = os.path.join(base_dir, "satellite", "georeferencing.json")
        
        if not os.path.exists(meta_path) or not os.path.exists(geo_path):
            print(f"Warning: Demo incident files not found in {base_dir}. Run scripts/prepare_demo_incident.py first.")
            return
            
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
            bbox=[32.7, 31.8, 33.0, 32.1], # Approximate bbox around target
            file_path=os.path.join(base_dir, "satellite", "vv.tif"),
            quality_score="HIGH",
            quality_details={
                "georeferencing": geo,
                "reasons": []
            }
        )
        db.add(scene)
        
        # We leave the rest blank since it's a demo mode relying on actual processing or explicitly marking as unavailable
        db.commit()
        print("Database successfully seeded with real Sentinel-1 demo scenario!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
