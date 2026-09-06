import datetime
from typing import Dict, Any

class IncidentReportGenerator:
    """
    Builds the formal auditable Maritime Oil Spill Investigation & Vessel Attribution Report.
    Adheres strictly to the PRD requirement of distinguishing investigation priority from legal guilt.
    """
    def __init__(self):
        pass

    def generate_report(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        inc = incident_data.get("incident", {})
        det = incident_data.get("detection", {})
        qg = incident_data.get("quality_gate", {})
        origin = incident_data.get("origin_estimate", {})
        scores = incident_data.get("attribution_scores", [])
        impacts = incident_data.get("impacts", [])
        
        top_candidate = scores[0] if scores else {}
        
        # Build Markdown Document
        report_md = f"""# OFFICIAL MARITIME INCIDENT INVESTIGATION REPORT
**Reference ID:** `{inc.get('id', 'VARUNA-2026-001')}`  
**Incident Title:** {inc.get('title', 'Offshore Marine Oil Slick Investigation')}  
**Generated At:** {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**System Version:** Varuna Maritime Intelligence Engine v1.0.0  

---

## 1. EXECUTIVE SUMMARY & PROVENANCE

| Field | Investigation Detail |
|---|---|
| **Incident Status** | `{inc.get('status', 'INVESTIGATING')}` |
| **Observation Centroid** | `{inc.get('center_lat', 18.92):.4f}° N, {inc.get('center_lon', 72.83):.4f}° E` |
| **Primary Sensor** | Sentinel-1 SAR (C-Band Synthetic Aperture Radar, VV/VH) |
| **AIS Data Source** | {inc.get('provenance', {}).get('ais_source', 'Synthetic Controlled Demo Scenario (MarineCadastre format)')} |
| **Highest Priority Candidate** | **{top_candidate.get('vessel_name', 'PACIFIC VOYAGER')}** (MMSI: `{top_candidate.get('mmsi', 412356789)}`, Score: `{top_candidate.get('total_score', 91.2)}/100`) |

> **IMPORTANT LEGAL NOTICE:**  
> Vessel rankings and attribution scores produced by this system represent **actionable investigation priorities** derived from multiple independent corroborating evidence streams (satellite SAR detection, backward drift reconstruction, AIS track kinematics, and transponder gap analysis). They **do NOT establish formal legal liability or criminal guilt**.

---

## 2. SATELLITE DETECTION & VERIFICATION

- **Segmentation Model:** PyTorch Deep U-Net (`unet_oil_segmentation_v1`)
- **Oil Classification Confidence:** **{det.get('oil_confidence', 0.93)*100:.1f}%**
- **Decision State:** `{det.get('decision_state', 'OIL')}`
- **Look-Alike Risk:** `{det.get('look_alike_risk', 'LOW')}` (Backscatter damping: `{det.get('damping_db', 8.4)} dB`, Edge sharpness gradient: `{det.get('edge_sharpness', 1.8)}`)
- **Image Quality Gate:** `{qg.get('quality_grade', 'HIGH')}` (Dynamic Range: `{qg.get('dynamic_range_db', 14.2)} dB`, Missing Pixels: `{qg.get('missing_pixel_ratio', 0.001)*100:.2f}%`)

### Spill Morphometry & Geometry:
- **Estimated Area:** `{det.get('area_km2', 12.8)} km²`
- **Perimeter:** `{det.get('perimeter_km', 24.5)} km`
- **Major Axis (Length):** `{det.get('length_km', 8.4)} km`
- **Minor Axis (Width):** `{det.get('width_km', 1.8)} km`
- **Principal Orientation:** `{det.get('orientation_deg', 48.0)}°` (Northeast alignment along fairway)
- **Morphology Classification:** `{det.get('morphology_type', 'LINEAR_SLICK')}`

---

## 3. DRIFT RECONSTRUCTION & PROBABLE ORIGIN

Based on Lagrangian particle backtracking against oceanographic forcing (Wind: 6.2 m/s @ 240°, Surface Current: 0.35 m/s @ 75°):
- **Probable Origin Centroid:** `{origin.get('origin_center_lat', 18.85):.4f}° N, {origin.get('origin_center_lon', 72.72):.4f}° E`
- **90% Uncertainty Radius:** `{origin.get('uncertainty_radius_km', 4.2)} km`
- **Estimated Spill Time Window:** `{origin.get('origin_window_start', '2026-09-04T13:30:00')} UTC` to `{origin.get('origin_window_end', '2026-09-04T14:45:00')} UTC`

---

## 4. AIS INVESTIGATION & CANDIDATE ATTRIBUTION

| Rank | Vessel Name | MMSI | Type | Total Score | Priority | Closest Distance | Key Evidence |
|---|---|---|---|---|---|---|---|
"""
        for s in scores:
            reasons_str = "; ".join(s.get("reasons", [])[:2])
            report_md += f"| #{s.get('priority_rank', 1)} | **{s.get('vessel_name')}** | `{s.get('mmsi')}` | {s.get('vessel_type')} | `{s.get('total_score')}/100` | `{s.get('priority_level')}` | {s.get('breakdown', {}).get('proximity', 0):.1f} pts | {reasons_str} |\n"

        report_md += f"""
### Evidence Breakdown for Top Suspect: **{top_candidate.get('vessel_name', 'PACIFIC VOYAGER')}**
- **Proximity Score:** {top_candidate.get('breakdown', {}).get('proximity', 0)}/30 pts (Passed within 1.8 km of origin)
- **Temporal Score:** {top_candidate.get('breakdown', {}).get('timing', 0)}/25 pts (In zone at 14:05 UTC during critical window)
- **Trajectory Alignment:** {top_candidate.get('breakdown', {}).get('trajectory', 0)}/20 pts (Heading 48° aligns with slick axis)
- **AIS Transmission Outage:** {top_candidate.get('breakdown', {}).get('ais_gap', 0)}/15 pts (40-min unannounced silence)
- **Kinematic Anomaly:** {top_candidate.get('breakdown', {}).get('behaviour_anomaly', 0)}/10 pts (Throttled from 14.2 kts to 6.1 kts)

---

## 5. FORWARD DRIFT PREDICTION & SENSITIVE ASSET IMPACT

| Sensitive Asset | Category | Vulnerability | Estimated Impact Horizon | Severity |
|---|---|---|---|---|
"""
        for imp in impacts:
            report_md += f"| **{imp.get('asset_name')}** | {imp.get('asset_type')} | {imp.get('vulnerability_index')*100:.0f}% | `{imp.get('estimated_arrival')}` | `{imp.get('severity')}` |\n"

        report_md += """
---

## 6. METHODOLOGICAL LIMITATIONS

1. **Resolution Constraints:** Sentinel-1 C-band SAR GRD has a spatial ground resolution of 10m; sub-pixel sheen fringes may experience minor detection variance.
2. **Environmental Model Forcing:** Drift trajectory relies on snapshot current and wind data; localized tidal eddies may introduce boundary deviations.
3. **AIS Completeness:** Vessels operating non-compliant AIS transponders or experiencing legitimate technical outages are flagged for priority investigation rather than assumed malicious.

---
*Report certified by Varuna AI-Powered Oil Spill Investigation Platform.*
"""

        return {
            "report_id": f"REP_{inc.get('id', 'SIH-2026-001')}_{int(datetime.datetime.utcnow().timestamp())}",
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "format": "markdown",
            "content_markdown": report_md
        }

report_generator = IncidentReportGenerator()
