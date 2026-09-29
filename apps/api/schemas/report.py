from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ReportMetadata(BaseModel):
    report_id: str
    incident_id: str
    incident_title: str
    target_region: str
    sensing_timestamp: str
    generated_at: str
    system_version: str = "Varuna Maritime Intelligence Engine v1.0"

class SpillVerificationGeometry(BaseModel):
    decision_state: str
    oil_confidence: float
    look_alike_risk: str
    image_quality: str
    area_km2: float
    perimeter_km: float
    length_km: float
    width_km: float
    estimated_metric_tons: float
    morphology_type: str
    geojson_geometry: Dict[str, Any]

class OriginBacktrackData(BaseModel):
    time_window_start: str
    time_window_end: str
    origin_center_lat: float
    origin_center_lon: float
    uncertainty_radius_km: float
    forcing_used: Dict[str, Any]
    geojson_contour: Dict[str, Any]

class VesselAttributionItem(BaseModel):
    priority_rank: int
    vessel_name: str
    mmsi: int
    vessel_type: str
    flag: str
    total_score: float
    priority_level: str
    proximity_score: float
    timing_score: float
    trajectory_score: float
    ais_gap_score: float
    anomaly_score: float
    reasons: List[str]
    anomalies: List[Dict[str, Any]]

class ForwardImpactItem(BaseModel):
    asset_name: str
    category: str
    jurisdiction: str
    vulnerability_index: float
    distance_km: float
    estimated_arrival: str
    severity: str
    resource_at_risk: str

class LegalDisclaimer(BaseModel):
    notice: str
    operational_limitations: List[str]

class TamperEvidentBlock(BaseModel):
    report_id: str
    sha256_fingerprint: str
    verification_algorithm: str = "SHA-256 (Deterministic Canonical JSON)"
    signed_at: str

class CanonicalInvestigationReport(BaseModel):
    metadata: ReportMetadata
    spill_verification: SpillVerificationGeometry
    origin_backtrack: OriginBacktrackData
    vessel_attribution: List[VesselAttributionItem]
    forward_impact: List[ForwardImpactItem]
    legal_disclaimer: LegalDisclaimer
    tamper_evident: TamperEvidentBlock

    class Config:
        populate_by_name = True
