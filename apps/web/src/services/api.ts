import { IncidentData, InvestigationReportResponse, CanonicalInvestigationReport } from '../types';

const API_BASE = '/api/v1';

export async function fetchIncident(incidentId: string = 'VARUNA-2026-001'): Promise<IncidentData> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch incident: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSatelliteBounds(incidentId: string = 'VARUNA-2026-001'): Promise<{ coordinates: [[number, number], [number, number], [number, number], [number, number]] }> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/satellite/bounds`);
  if (!res.ok) {
    throw new Error(`Failed to fetch satellite bounds: ${res.statusText}`);
  }
  return res.json();
}

export async function queryAIS(incidentId: string, searchRadiusKm: number = 35.0): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/ais/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ search_radius_km: searchRadiusKm })
  });
  if (!res.ok) throw new Error('Failed to query AIS');
  return res.json();
}

export async function replayAIS(incidentId: string, targetTime: string): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/ais/replay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_time: targetTime })
  });
  if (!res.ok) throw new Error('Failed to replay AIS');
  return res.json();
}

export async function askAssistant(
  incidentId: string, 
  query: string,
  history?: { role: string; content: string }[]
): Promise<{ answer: string; tool_used: string; citations: any[]; model_used?: string }> {
  const res = await fetch(`${API_BASE}/investigation/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ incident_id: incidentId, query, history })
  });
  if (!res.ok) throw new Error('Failed to query assistant');
  return res.json();
}

export async function generateReport(incidentId: string = 'VARUNA-2026-001'): Promise<InvestigationReportResponse> {
  const res = await fetch(`${API_BASE}/reports/${incidentId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate report' }));
    throw new Error(err.detail || 'Failed to generate report');
  }
  return res.json();
}

export async function fetchReportById(reportId: string): Promise<{
  report_id: string;
  incident_id: string;
  created_at: string;
  sha256_fingerprint: string;
  status: string;
  report: CanonicalInvestigationReport;
}> {
  const res = await fetch(`${API_BASE}/reports/${reportId}`);
  if (!res.ok) throw new Error(`Failed to fetch report ${reportId}`);
  return res.json();
}

export function getReportPdfUrl(reportId: string): string {
  return `${API_BASE}/reports/${reportId}/pdf`;
}

export async function traceOrigin(incidentId: string, params: any = {}): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/trace-origin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) throw new Error('Failed to run origin backtrack');
  return res.json();
}

export async function forecastSpill(incidentId: string, params: any = {}): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/forecast-spill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) throw new Error('Failed to run forward forecast');
  return res.json();
}

export async function analyzeSAR(incidentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/analyze-sar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!res.ok) throw new Error('Failed to run satellite SAR ML analysis');
  return res.json();
}

export async function inspectRaster(file: File): Promise<{
  has_georeference: boolean;
  source: string;
  center_lat: number;
  center_lon: number;
  bbox: number[];
  width: number;
  height: number;
  band_count: number;
  crs: string | null;
  message: string;
}> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/incidents/inspect-raster`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) throw new Error('Failed to inspect satellite image');
  return res.json();
}

export async function uploadSAR(formData: FormData): Promise<{
  status: string;
  incident_id: string;
  center_lat: number;
  center_lon: number;
  has_georeference: boolean;
  metadata_source: string;
  message: string;
  detection: any;
  redirect_url: string;
}> {
  const res = await fetch(`${API_BASE}/incidents/upload-sar`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Failed to process SAR upload');
  }
  return res.json();
}

export async function applyCustomSpillGeometry(incidentId: string, payload: {
  geojson: any;
  area_km2?: number;
  center_lat?: number;
  center_lon?: number;
}): Promise<IncidentData> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/custom-spill-geometry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update custom spill geometry' }));
    throw new Error(err.detail || 'Failed to update custom spill geometry');
  }
  return res.json();
}

export async function revertSpillGeometry(incidentId: string): Promise<IncidentData> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/revert-spill-geometry`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to revert spill geometry');
  return res.json();
}
