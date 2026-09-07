export interface IncidentData {
  incident: {
    id: string;
    title: string;
    description: string;
    status: string;
    center_lat: number;
    center_lon: number;
    spill_window_start: string | null;
    spill_window_end: string | null;
    provenance: Record<string, any>;
  };
  scene: {
    id: string;
    satellite_name: string;
    acquisition_time: string;
    polarizations: string[];
    quality_score: string;
    quality_details: {
      missing_pixel_ratio: number;
      dynamic_range_db: number;
      wind_status: string;
      wind_speed_ms: number;
      coastal_distance_km: number;
      reasons: string[];
    };
    bbox: number[];
  } | null;
  detection: {
    id: string;
    oil_confidence: number;
    look_alike_risk: string;
    look_alike_type: string | null;
    decision_state: string;
    area_km2: number;
    perimeter_km: number;
    length_km: number;
    width_km: number;
    orientation_deg: number;
    morphology_type: string;
    geojson: any;
  } | null;
  unet_prediction?: any;
  dartis_reference?: any;
  backtrack_particles?: any;
  origin_corridor?: any;
  backtrack_snapshots?: Record<string, {
    hours: number;
    t_index: number;
    active_particles: number;
    centroid: { lon: number; lat: number };
    point_cloud: any;
    hull: any;
  }>;
  forward_particles?: any;
  forward_corridor?: any;
  forward_snapshots?: Record<string, {
    hours: number;
    t_index: number;
    active_particles: number;
    centroid: { lon: number; lat: number };
    point_cloud: any;
    hull: any;
  }>;
  origin_estimate: {
    id: string;
    origin_center_lat: number;
    origin_center_lon: number;
    uncertainty_radius_km: number;
    origin_window_start: string;
    origin_window_end: string;
    geojson: any;
    forcing_used: {
      status?: string;
      wind_speed_ms?: number;
      wind_direction_deg?: number;
      current_speed_ms?: number;
      current_direction_deg?: number;
      source_name?: string;
    };
  } | null;
  attribution_scores: CandidateVessel[];
  anomalies: AISAnomalyItem[];
  forward_forecast: ForecastStep[];
  impacts: SensitiveImpactItem[];
  evidence_items: EvidenceItem[];
}

export interface CandidateVessel {
  mmsi: number;
  vessel_name: string;
  vessel_type: string;
  flag: string;
  priority_rank: number;
  total_score: number;
  priority_level: 'HIGH' | 'MEDIUM' | 'LOW';
  last_known_lat?: number;
  last_known_lon?: number;
  sog?: number;
  cog?: number;
  lat?: number;
  lon?: number;
  isDark?: boolean;
  trajectory?: number[][];
  ais_points?: {
    timestamp: string;
    lat: number;
    lon: number;
    sog: number;
    cog: number;
  }[];
  breakdown: {
    proximity: number;
    timing: number;
    trajectory: number;
    ais_gap: number;
    behaviour_anomaly: number;
  };
  reasons: string[];
  disclaimer: string;
}

export interface AISAnomalyItem {
  id: string;
  mmsi: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  anomaly_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
  raw_details: Record<string, any>;
}

export interface ForecastStep {
  horizon_hours: number;
  step_label: string;
  timestamp: string;
  center_lat: number;
  center_lon: number;
  spread_radius_km: number;
  geojson: any;
}

export interface SensitiveImpactItem {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  vulnerability_index: number;
  description: string;
  estimated_arrival: string;
  estimated_timestamp: string | null;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  distance_to_core_km: number;
  geojson: any;
}

export interface EvidenceItem {
  id: string;
  category: string;
  title: string;
  content: string;
  confidence: number | null;
}
