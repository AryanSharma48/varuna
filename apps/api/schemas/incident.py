from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    center_lat: float
    center_lon: float
    status: str = "INVESTIGATING"

class IncidentCreate(IncidentBase):
    id: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None

class IncidentResponse(IncidentBase):
    id: str
    created_at: datetime
    spill_window_start: Optional[datetime] = None
    spill_window_end: Optional[datetime] = None
    provenance: Dict[str, Any] = {}

    class Config:
        from_attributes = True

class DetectionResponse(BaseModel):
    id: str
    incident_id: str
    scene_id: str
    oil_confidence: float
    look_alike_risk: str
    look_alike_type: Optional[str] = None
    decision_state: str
    model_name: str
    model_version: str
    area_km2: float
    perimeter_km: float
    length_km: float
    width_km: float
    orientation_deg: float
    morphology_type: str
    geojson_geometry: Dict[str, Any]

class OriginResponse(BaseModel):
    id: str
    incident_id: str
    origin_center_lat: float
    origin_center_lon: float
    uncertainty_radius_km: float
    origin_window_start: str
    origin_window_end: str
    contours: List[Dict[str, Any]]
    geojson: Dict[str, Any]
    forcing_used: Dict[str, Any]

class AISQueryRequest(BaseModel):
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    search_radius_km: float = 35.0

class AISReplayRequest(BaseModel):
    target_time: datetime

class AttributionResponse(BaseModel):
    incident_id: str
    ranked_candidates: List[Dict[str, Any]]
    calculated_at: datetime
    disclaimer: str

class AssistantRequest(BaseModel):
    incident_id: str
    query: str

class AssistantResponse(BaseModel):
    answer: str
    tool_used: str
    citations: List[Dict[str, Any]]

class ReportResponse(BaseModel):
    report_id: str
    incident_id: str
    generated_at: str
    content_markdown: str

class TraceOriginRequest(BaseModel):
    slick_lat: Optional[float] = None
    slick_lon: Optional[float] = None
    backtrack_hours: float = 6.0
    wind_speed_ms: Optional[float] = None
    wind_dir_deg: Optional[float] = None
    current_speed_ms: Optional[float] = None
    current_dir_deg: Optional[float] = None

class ForecastSpillRequest(BaseModel):
    slick_lat: Optional[float] = None
    slick_lon: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_dir_deg: Optional[float] = None
    current_speed_ms: Optional[float] = None
    current_dir_deg: Optional[float] = None

class CreateCustomIncidentRequest(BaseModel):
    title: str
    center_lat: float
    center_lon: float
    satellite_name: str = "Sentinel-1A SAR C-Band"
    polarizations: List[str] = ["VV", "VH"]
    wind_speed_ms: float = 6.2
    current_speed_ms: float = 0.35

