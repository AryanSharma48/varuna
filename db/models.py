import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.database import Base

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="INVESTIGATING")  # INVESTIGATING, CONFIRMED_OIL, LOOK_ALIKE, RESOLVED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    center_lat = Column(Float, nullable=False)
    center_lon = Column(Float, nullable=False)
    spill_window_start = Column(DateTime, nullable=True)
    spill_window_end = Column(DateTime, nullable=True)
    provenance = Column(JSON, default=dict)
    
    # Relationships
    scenes = relationship("SatelliteScene", back_populates="incident", cascade="all, delete-orphan")
    detections = relationship("SpillDetection", back_populates="incident", cascade="all, delete-orphan")
    origin_estimates = relationship("OriginEstimate", back_populates="incident", cascade="all, delete-orphan")
    attribution_scores = relationship("AttributionScore", back_populates="incident", cascade="all, delete-orphan")
    drift_runs = relationship("DriftRun", back_populates="incident", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="incident", cascade="all, delete-orphan")
    reports = relationship("InvestigationReport", back_populates="incident", cascade="all, delete-orphan")

class SatelliteScene(Base):
    __tablename__ = "satellite_scenes"
    
    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    satellite_name = Column(String, default="Sentinel-1 SAR")
    acquisition_time = Column(DateTime, nullable=False)
    polarizations = Column(JSON, default=["VV", "VH"])
    bbox = Column(JSON, nullable=False)  # [min_lon, min_lat, max_lon, max_lat]
    file_path = Column(String, nullable=True)
    quality_score = Column(String, default="HIGH")  # HIGH, MEDIUM, LOW
    quality_details = Column(JSON, default=dict)
    
    incident = relationship("Incident", back_populates="scenes")
    detections = relationship("SpillDetection", back_populates="scene")

class SpillDetection(Base):
    __tablename__ = "spill_detections"
    
    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    scene_id = Column(String, ForeignKey("satellite_scenes.id"), nullable=False)
    detection_time = Column(DateTime, default=datetime.datetime.utcnow)
    oil_confidence = Column(Float, nullable=False)  # 0.0 - 1.0
    look_alike_risk = Column(String, default="LOW")  # LOW, MEDIUM, HIGH
    look_alike_type = Column(String, nullable=True)  # Low-wind, Biogenic, Wake, etc.
    decision_state = Column(String, default="OIL")   # OIL, LOOK_ALIKE, UNCERTAIN, INSUFFICIENT_EVIDENCE
    model_name = Column(String, default="unet_oil_segmentation_v1")
    model_version = Column(String, default="1.0.0")
    
    # Spill Geometry & Morphometry
    area_km2 = Column(Float, nullable=False)
    perimeter_km = Column(Float, nullable=False)
    length_km = Column(Float, nullable=False)
    width_km = Column(Float, nullable=False)
    orientation_deg = Column(Float, nullable=False)
    morphology_type = Column(String, default="LINEAR_SLICK") # LINEAR_SLICK, PATCHY, FEATHERED, PLUME
    geojson_geometry = Column(JSON, nullable=False)
    
    incident = relationship("Incident", back_populates="detections")
    scene = relationship("SatelliteScene", back_populates="detections")

class OriginEstimate(Base):
    __tablename__ = "origin_estimates"
    
    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    calculation_time = Column(DateTime, default=datetime.datetime.utcnow)
    origin_window_start = Column(DateTime, nullable=False)
    origin_window_end = Column(DateTime, nullable=False)
    center_lat = Column(Float, nullable=False)
    center_lon = Column(Float, nullable=False)
    uncertainty_radius_km = Column(Float, nullable=False)
    probability_contour_geojson = Column(JSON, nullable=False)
    forcing_used = Column(JSON, default=dict)
    
    incident = relationship("Incident", back_populates="origin_estimates")

class Vessel(Base):
    __tablename__ = "vessels"
    
    mmsi = Column(Integer, primary_key=True, index=True)
    vessel_name = Column(String, nullable=True)
    vessel_type = Column(String, default="Tanker / Cargo")
    flag = Column(String, nullable=True)
    imo = Column(Integer, nullable=True)
    length_m = Column(Float, nullable=True)
    width_m = Column(Float, nullable=True)
    source_type = Column(String, default="real")  # real or synthetic

class AISPoint(Base):
    __tablename__ = "ais_points"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mmsi = Column(Integer, ForeignKey("vessels.mmsi"), index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    sog = Column(Float, nullable=False)  # Speed Over Ground in knots
    cog = Column(Float, nullable=False)  # Course Over Ground in degrees
    heading = Column(Float, nullable=True)
    nav_status = Column(String, default="Under way using engine")
    source_type = Column(String, default="synthetic")  # synthetic or real

class AISAnomaly(Base):
    __tablename__ = "ais_anomalies"
    
    id = Column(String, primary_key=True, index=True)
    mmsi = Column(Integer, ForeignKey("vessels.mmsi"), nullable=False)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    anomaly_type = Column(String, nullable=False)  # AIS_GAP, SPEED_JUMP, COURSE_DEVIATION, DARK_SHIP_MANOEUVRE
    severity = Column(String, default="MEDIUM")   # LOW, MEDIUM, HIGH
    description = Column(Text, nullable=False)
    raw_details = Column(JSON, default=dict)

class AttributionScore(Base):
    __tablename__ = "attribution_scores"
    
    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    mmsi = Column(Integer, ForeignKey("vessels.mmsi"), nullable=False)
    priority_rank = Column(Integer, nullable=False)
    total_score = Column(Float, nullable=False) # 0.0 - 100.0
    priority_level = Column(String, default="HIGH") # HIGH, MEDIUM, LOW
    
    # Feature score breakdown
    score_proximity = Column(Float, default=0.0)
    score_timing = Column(Float, default=0.0)
    score_trajectory = Column(Float, default=0.0)
    score_ais_gap = Column(Float, default=0.0)
    score_behaviour_anomaly = Column(Float, default=0.0)
    
    explanation_reasons = Column(JSON, default=list)
    calculated_at = Column(DateTime, default=datetime.datetime.utcnow)
    disclaimer = Column(String, default="Investigation priority rank only. Does not constitute legal proof of liability.")
    
    incident = relationship("Incident", back_populates="attribution_scores")
    vessel = relationship("Vessel")

class DriftRun(Base):
    __tablename__ = "drift_runs"
    
    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    run_type = Column(String, nullable=False)  # BACKWARD_ORIGIN or FORWARD_FORECAST
    start_time = Column(DateTime, nullable=False)
    duration_hours = Column(Float, nullable=False)
    particle_count = Column(Integer, default=500)
    forecast_steps = Column(JSON, default=list) # [{step: "+6h", time: "...", polygon: {...}}, ...]
    environmental_parameters = Column(JSON, default=dict)
    
    incident = relationship("Incident", back_populates="drift_runs")

class SensitiveAsset(Base):
    __tablename__ = "sensitive_assets"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    asset_type = Column(String, nullable=False) # MARINE_PROTECTED_AREA, FISHING_ZONE, CORAL_REEF, PORT, BEACH
    geojson_geometry = Column(JSON, nullable=False)
    vulnerability_index = Column(Float, default=0.8) # 0 - 1.0

class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    
    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    category = Column(String, nullable=False) # SATELLITE, QUALITY, SEGMENTATION, LOOK_ALIKE, ORIGIN, AIS, ANOMALY, IMPACT
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    incident = relationship("Incident", back_populates="evidence_items")

class InvestigationReport(Base):
    __tablename__ = "investigation_reports"
    
    id = Column(String, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sha256_fingerprint = Column(String(64), nullable=False, index=True)
    canonical_payload = Column(Text, nullable=False)
    status = Column(String, default="OFFICIAL") # OFFICIAL, DRAFT
    
    incident = relationship("Incident", back_populates="reports")

