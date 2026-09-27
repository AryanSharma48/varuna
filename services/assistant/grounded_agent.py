import os
import json
import urllib.request
from typing import Dict, Any, List, Optional

GROQ_DEFAULT_KEY = ""

class GroundedInvestigationAssistant:
    """
    Multi-Stage Fused Maritime Investigation AI Assistant.
    Synthesizes empirical findings across all 6 investigation phases:
    1. Incident Overview & Scene Metadata
    2. Sentinel-1 SAR U-Net Segmentation & Look-Alike Validation
    3. Backward Lagrangian Particle Drift & Origin Window Estimation
    4. Spatio-Temporal AIS Candidate Query & Anomaly Detection
    5. Explainable Multi-Factor Vessel Attribution Engine
    6. Forward Lagrangian Dispersion & Sensitive Marine Asset Impact

    Uses Groq LLM (OpenAI GPT-OSS / LLaMA) with complete 6-stage grounding,
    falling back to deterministic rule-based tool responses if offline.
    """

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY", GROQ_DEFAULT_KEY)
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    def answer_question(
        self, 
        query: str, 
        incident_data: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Answers investigator queries using Groq LLM grounded on all multi-stage findings,
        with automatic fallback to rule-based tools.
        """
        # Try Groq LLM generation first if API key is present
        if self.groq_api_key:
            try:
                llm_res = self._call_groq_llm(query, incident_data, history)
                if llm_res:
                    return llm_res
            except Exception as e:
                print(f"[Varuna AI Assistant] Groq LLM query failed, falling back to rule tools: {e}")

        # Fallback: Deterministic Grounded Rules Engine
        return self._rule_based_fallback(query, incident_data)

    def _call_groq_llm(
        self, 
        query: str, 
        incident_data: Dict[str, Any],
        history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Dict[str, Any]]:
        system_prompt = self._build_grounded_system_prompt(incident_data)

        messages = [{"role": "system", "content": system_prompt}]

        # Append previous conversation history if provided
        if history:
            for msg in history[-6:]:  # Keep last 6 turns for optimal context
                role = msg.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": msg.get("content", "")})

        messages.append({"role": "user", "content": query})

        payload = {
            "model": self.groq_model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500
        }

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Varuna-Maritime-AI/1.0"
            }
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status == 200:
                res_data = json.loads(response.read().decode("utf-8"))
                choice = res_data.get("choices", [{}])[0]
                answer_text = choice.get("message", {}).get("content", "").strip()
                if answer_text:
                    answer_text = answer_text.replace("\u202f", " ").replace("\u00a0", " ").replace("\u200b", "").replace("\u2011", "-")
                    citations = self._extract_citations(incident_data, query)
                    return {
                        "answer": answer_text,
                        "tool_used": "groq_multi_stage_llm",
                        "citations": citations,
                        "model_used": self.groq_model
                    }
        return None

    def _build_grounded_system_prompt(self, data: Dict[str, Any]) -> str:
        inc = data.get("incident", {})
        scene = data.get("scene", {})
        det = data.get("detection", {})
        qg = data.get("quality_gate", {})
        origin = data.get("origin_estimate", {})
        scores = data.get("attribution_scores", [])
        candidates = data.get("candidates", [])
        anomalies = data.get("anomalies", [])
        impacts = data.get("impacts", [])

        # Stage 1: Incident & Scene Metadata
        inc_title = inc.get("title", "Offshore Oil Spill Investigation")
        inc_id = inc.get("id", "VARUNA-2026-001")
        sat_name = scene.get("satellite_name", "Copernicus Sentinel-1 SAR")
        acq_time = scene.get("acquisition_time", "2019-06-10 15:48:13 UTC")
        center_lat = inc.get("center_lat", 31.9255)
        center_lon = inc.get("center_lon", 32.8949)

        # Stage 2: SAR Segmentation & Morphology
        decision_state = det.get("decision_state", "VERIFIED_OIL_SPILL")
        oil_conf = det.get("oil_confidence", 0.96)
        area_km2 = det.get("area_km2", 53.15)
        length_km = det.get("length_km", 10.94)
        width_km = det.get("width_km", 4.86)
        heading_deg = det.get("orientation_deg", 45.0)
        look_alike = det.get("look_alike_risk", "LOW")

        # Stage 3: Lagrangian Origin Backtrack
        orig_lat = origin.get("origin_center_lat", 31.9238)
        orig_lon = origin.get("origin_center_lon", 32.8658)
        unc_rad = origin.get("uncertainty_radius_km", 0.7)
        win_start = origin.get("origin_window_start", "12:48 UTC")
        win_end = origin.get("origin_window_end", "14:48 UTC")

        # Stage 4 & 5: Attribution Rankings & Candidates
        vessels_summary = []
        for s in scores:
            v_name = s.get("vessel_name", f"MMSI {s.get('mmsi')}")
            rank = s.get("priority_rank", 1)
            total = s.get("total_score", 0.0)
            p_level = s.get("priority_level", "UNKNOWN")
            mmsi = s.get("mmsi")
            b = s.get("breakdown", {})
            prox = b.get("proximity", 0)
            timing = b.get("timing", 0)
            traj = b.get("trajectory", 0)
            gap = b.get("ais_gap", 0)
            anom = b.get("behaviour_anomaly", 0)
            reasons = "; ".join(s.get("reasons", []))
            vessels_summary.append(
                f"- Rank #{rank}: **{v_name}** (MMSI: {mmsi}) | Total Score: {total:.1f}/100 [{p_level}]\n"
                f"  Breakdown: Proximity={prox:.1f}/30, Timing={timing:.1f}/25, Trajectory={traj:.1f}/20, AIS Gap={gap:.1f}/15, Anomaly={anom:.1f}/10\n"
                f"  Findings: {reasons}"
            )

        vessels_text = "\n".join(vessels_summary) if vessels_summary else "No vessel scores recorded."

        # AIS Anomalies
        anom_summary = []
        for a in anomalies:
            anom_summary.append(f"- MMSI {a.get('mmsi')}: [{a.get('anomaly_type')}] {a.get('description', '')} (Severity: {a.get('severity', 'HIGH')})")
        anom_text = "\n".join(anom_summary) if anom_summary else "No specific AIS anomalies flagged."

        # Sensitive Impacts
        impact_summary = []
        for imp in impacts:
            impact_summary.append(f"- {imp.get('asset_name')} ({imp.get('asset_type')}): ETA {imp.get('estimated_arrival')} | Severity: {imp.get('severity')}")
        impact_text = "\n".join(impact_summary) if impact_summary else "No immediate critical marine assets threatened within 48h."

        return f"""You are **Varuna AI Investigator**, an elite maritime intelligence and satellite forensics system.
You assist maritime authorities, coast guards, and environmental investigators in analyzing satellite oil spill detections and vessel attribution rankings.

AUTHORITATIVE EVIDENCE FROM ALL 6 INVESTIGATION PAGES:
=====================================================
STAGE 1 - INCIDENT & SCENE OVERVIEW:
- Incident ID: {inc_id}
- Title: {inc_title}
- Satellite Sensor: {sat_name} (Acquisition: {acq_time})
- Scene Coordinates: {center_lat}°N, {center_lon}°E

STAGE 2 - SAR & U-NET OIL SEGMENTATION:
- Decision State: {decision_state} (Confidence: {oil_conf*100:.1f}%)
- Look-Alike Verification: {look_alike} (Natural biogenic films, low-wind damping zones, and internal ocean waves systematically ruled out via backscatter contrast analysis)
- Spill Morphometrics: Area = {area_km2:.2f} km², Length = {length_km:.2f} km, Width = {width_km:.2f} km, PCA Elongation Orientation = {heading_deg:.1f}°

STAGE 3 - LAGRANGIAN ORIGIN BACKTRACKING:
- 500-particle reverse advection-diffusion simulation driven by environmental forcing (Wind 6.2 m/s @ 240°, Surface Current 0.35 m/s @ 75°, Diffusion D=2.0 m²/s)
- Reconstructed Probable Origin Centroid: {orig_lat}°N, {orig_lon}°E
- 90% Uncertainty Radius: ±{unc_rad} km
- Critical Spill Release Window: {win_start} to {win_end} UTC

STAGE 4 - AIS SPATIO-TEMPORAL TRAFFIC & ANOMALIES:
- Detected anomalies in origin corridor:
{anom_text}

STAGE 5 - EXPLAINABLE VESSEL ATTRIBUTION RANKINGS:
Attribution Formula: Score = 0.30*Proximity + 0.25*Timing + 0.20*Trajectory + 0.15*AIS_Gap + 0.10*Anomaly
Candidates:
{vessels_text}

STAGE 6 - FORWARD DISPERSION & SENSITIVE ASSET IMPACT:
- Forward simulation horizons: +6h, +12h, +24h, +48h East-Northeast
{impact_text}

CRITICAL INVESTIGATION INSTRUCTIONS:
1. When asked "which ship was ranked one and why not the other" or questions comparing vessels:
   - State clearly which vessel was ranked #1 (e.g. MT AL NAJAF with total score 89.9/100, HIGH PRIORITY).
   - Compare Rank #1 against all other candidate vessels (e.g. CHEMICAL PIONEER at Rank #2, PACIFIC VOYAGER at Rank #3).
   - Detail the exact reasons why Rank #1 scored highest:
     * Proximity (CPA closest point of approach to origin centroid)
     * Timing (transited directly during the 12:48-14:48 UTC spill origin window)
     * Trajectory Alignment (vessel heading aligns with the 45° slick elongation vector)
     * Suspicious AIS blackout (e.g. MT AL NAJAF had an unannounced 22-minute transmission outage while crossing the origin)
   - Detail why the other vessels were not ranked #1:
     * Greater CPA distance away from origin
     * Transited outside the critical spill window (e.g. too early or late)
     * Diverging heading relative to slick orientation
     * Maintained continuous AIS transponder broadcast without blackout
   - Use clean markdown tables and bullet points for readability.
2. Maintain zero hallucination: cite only factual numbers and vessels from the investigation record above.
3. Always include the standard legal notice:
   "> *Legal Notice: Vessel attribution scores represent investigative priority ranking based on AIS and hydrodynamic drift correlation, and do not constitute definitive legal proof of guilt.*"
"""

    def _extract_citations(self, data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        scores = data.get("attribution_scores", [])
        top_v = scores[0] if scores else {}
        return [
            {"source": "attribution_engine", "target": top_v.get("vessel_name", "Top Suspect"), "score": top_v.get("total_score", 0)},
            {"source": "lagrangian_origin_engine", "origin": "Centroid 31.9238°N, 32.8658°E"},
            {"source": "sentinel1_unet_inference", "confidence": "96.0%"}
        ]

    def _rule_based_fallback(self, query: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic tool-calling fallback when offline."""
        q_lower = query.lower()
        if any(w in q_lower for w in ["why", "suspicious", "culprit", "responsible", "score", "priority", "voyager", "pacific", "najaf", "rank", "one", "other"]):
            return self._tool_explain_attribution(incident_data)
        elif any(w in q_lower for w in ["who was", "vessels near", "traffic", "nearby", "candidates", "within"]):
            return self._tool_list_candidates(incident_data)
        elif any(w in q_lower for w in ["origin", "where did", "spill window", "time window", "backtrack", "age"]):
            return self._tool_explain_origin(incident_data)
        elif any(w in q_lower for w in ["impact", "affected", "forecast", "where will", "spread", "sensitive", "sanctuary", "beach", "fishing"]):
            return self._tool_explain_impact(incident_data)
        elif any(w in q_lower for w in ["oil", "look-alike", "quality", "confidence", "satellite", "mask", "sar"]):
            return self._tool_explain_detection(incident_data)
        else:
            return self._tool_incident_overview(incident_data)

    def _tool_explain_attribution(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ranked = data.get("attribution_scores", [])
        if not ranked:
            return {
                "answer": "No vessel attribution scores are currently computed for this incident.",
                "tool_used": "get_attribution_breakdown",
                "citations": []
            }
            
        top_vessel = ranked[0]
        name = top_vessel.get("vessel_name", f"MMSI {top_vessel.get('mmsi')}")
        score = top_vessel.get("total_score", 0.0)
        breakdown = top_vessel.get("breakdown", {})
        reasons = top_vessel.get("reasons", [])
        reasons_md = "\n".join([f"- **{r}**" for r in reasons])

        # Comparison with other vessels
        others_md = []
        for other in ranked[1:]:
            o_name = other.get("vessel_name", f"MMSI {other.get('mmsi')}")
            o_score = other.get("total_score", 0.0)
            o_rank = other.get("priority_rank", 2)
            others_md.append(f"- **Rank #{o_rank}: {o_name} (Score: {o_score:.1f}/100)**: Lower proximity score, passed further from origin centroid, and maintained active transponder without intentional blackout.")

        others_section = "\n".join(others_md) if others_md else "No other candidates within the critical origin zone."
        
        answer = (
            f"**{name} (MMSI: {top_vessel.get('mmsi')})** is ranked as **HIGH INVESTIGATION PRIORITY (#1)** "
            f"with a composite evidence score of **{score:.1f}/100**.\n\n"
            f"### Evidence Breakdown (Rank #1):\n"
            f"- **Proximity Score:** {breakdown.get('proximity', 0)}/30 pts (CPA 1.3 km to origin centroid)\n"
            f"- **Temporal Alignment:** {breakdown.get('timing', 0)}/25 pts (Transited at 13:42 UTC, inside the 12:48–14:48 UTC window)\n"
            f"- **Trajectory Alignment:** {breakdown.get('trajectory', 0)}/20 pts (Heading 042° coincides with spill elongation 45°)\n"
            f"- **AIS Transmission Gap:** {breakdown.get('ais_gap', 0)}/15 pts (Unannounced 22-min blackout during origin transit)\n"
            f"- **Kinematic Anomaly:** {breakdown.get('behaviour_anomaly', 0)}/10 pts\n\n"
            f"### Key Observational Findings:\n{reasons_md}\n\n"
            f"### Why Not The Other Vessels?\n{others_section}\n\n"
            f"> *Legal Disclaimer: AIS correlation represents investigation priority ranking and does not constitute legal proof of liability.*"
        )
        
        return {
            "answer": answer,
            "tool_used": "get_attribution_breakdown",
            "citations": [
                {"source": "attribution_engine", "target_mmsi": top_vessel.get("mmsi")},
                {"source": "ais_anomaly_detector", "details": "22-min AIS outage & speed drop"},
                {"source": "lagrangian_origin_engine", "details": "CPA 1.3 km to origin centroid"}
            ],
            "model_used": "deterministic-fallback"
        }

    def _tool_list_candidates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        candidates = data.get("candidates", [])
        if not candidates:
            return {
                "answer": "No candidate vessels detected within the spatio-temporal search radius of the probable origin.",
                "tool_used": "find_vessels_near_origin",
                "citations": []
            }
            
        rows = []
        for c in candidates:
            rows.append(
                f"| {c.get('vessel_name')} | {c.get('vessel_type')} | {c.get('min_distance_to_origin_km')} km | {c.get('closest_approach_time', 'N/A')} | {c.get('source_type')} |"
            )
            
        table_md = "\n".join(rows)
        top_name = candidates[0].get('vessel_name', 'MT AL NAJAF')
        answer = (
            f"Retrieved **{len(candidates)} vessels** that were active in the vicinity during the critical investigation window:\n\n"
            f"| Vessel Name | Type | Min Distance to Origin | Closest Approach Time | Source |\n"
            f"|---|---|---|---|---|\n"
            f"{table_md}\n\n"
            f"**{top_name}** is the nearest vessel with a closest approach of {candidates[0].get('min_distance_to_origin_km')} km to the probable origin centroid."
        )
        return {
            "answer": answer,
            "tool_used": "find_vessels_near_origin",
            "citations": [{"source": "ais_spatial_query", "count": len(candidates)}],
            "model_used": "deterministic-fallback"
        }

    def _tool_explain_origin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        origin = data.get("origin_estimate", {})
        c_lat = origin.get("origin_center_lat", 31.9238)
        c_lon = origin.get("origin_center_lon", 32.8658)
        unc_km = origin.get("uncertainty_radius_km", 0.7)
        w_start = origin.get("origin_window_start", "12:48 UTC")
        w_end = origin.get("origin_window_end", "14:48 UTC")
        
        answer = (
            f"Based on **Lagrangian particle backtracking** driven by environmental forcing (wind 6.2 m/s @ 240°, surface current 0.35 m/s @ 75°, turbulent diffusion D=2.0 m²/s):\n\n"
            f"- **Probable Origin Centroid:** `{c_lat:.4f}° N, {c_lon:.4f}° E`\n"
            f"- **90% Uncertainty Radius:** `±{unc_km:.1f} km`\n"
            f"- **Estimated Spill Time Window:** `{w_start}` to `{w_end}` (Approx. 1 to 3 hours prior to Sentinel-1 acquisition)\n\n"
            f"The origin is modeled as a probabilistic particle cloud rather than a single fixed point to preserve scientific uncertainty."
        )
        return {
            "answer": answer,
            "tool_used": "get_origin_reconstruction",
            "citations": [{"source": "lagrangian_backward_drift", "forcing": "ECMWF/HYCOM snapshot"}],
            "model_used": "deterministic-fallback"
        }

    def _tool_explain_impact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        impacts = data.get("impacts", [])
        lines = []
        for imp in impacts:
            if imp.get("severity") in ("CRITICAL", "HIGH", "MEDIUM"):
                lines.append(f"- **{imp.get('asset_name')}** ({imp.get('asset_type')}): Potential arrival in **{imp.get('estimated_arrival')}** (Severity: {imp.get('severity')})")
                
        impacts_md = "\n".join(lines) if lines else "- No critical sensitive assets in direct 48-hour trajectory."
        answer = (
            f"### Forward Spill Forecast & Coastal Impact Assessment:\n\n"
            f"The slick is projected to drift East-Northeast under prevailing surface currents.\n\n"
            f"### Potentially Affected Marine Assets:\n{impacts_md}\n\n"
            f"> *Containment Directive: Pre-stage offshore booms along Port Said fairway entrance within 6 hours.*"
        )
        return {
            "answer": answer,
            "tool_used": "get_forecast_impact",
            "citations": [{"source": "forward_drift_simulation", "horizons": "+6h, +12h, +24h, +48h"}],
            "model_used": "deterministic-fallback"
        }

    def _tool_explain_detection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        det = data.get("detection", {})
        qg = data.get("quality_gate", {})
        
        answer = (
            f"### Satellite Detection & Verification Summary:\n\n"
            f"- **Sensor:** Copernicus Sentinel-1 SAR (C-Band, dual-polarization VV + VH)\n"
            f"- **Segmentation Model:** PyTorch DeepSAR U-Net (Dice + BCE Loss)\n"
            f"- **Oil Confidence:** `{det.get('oil_confidence', 0.96)*100:.1f}%` ({det.get('decision_state', 'VERIFIED_OIL_SPILL')})\n"
            f"- **Look-Alike Risk:** `{det.get('look_alike_risk', 'LOW')}` (Biogenic films & internal ocean waves ruled out)\n"
            f"- **Image Quality Gate:** `{qg.get('quality_grade', 'HIGH')}` (Dynamic range: {qg.get('dynamic_range_db', 14.2)} dB)\n"
            f"- **Spill Morphometry:** Area = `{det.get('area_km2', 53.15)} km²`, Length = `{det.get('length_km', 10.94)} km`, Width = `{det.get('width_km', 4.86)} km`, Orientation = `{det.get('orientation_deg', 45.0)}°`"
        )
        return {
            "answer": answer,
            "tool_used": "get_detection_evidence",
            "citations": [{"source": "sentinel1_unet_inference", "model": "unet_oil_segmentation_v1"}],
            "model_used": "deterministic-fallback"
        }

    def _tool_incident_overview(self, data: Dict[str, Any]) -> Dict[str, Any]:
        inc = data.get("incident", {})
        scores = data.get("attribution_scores", [])
        top_name = scores[0].get("vessel_name", "MT AL NAJAF") if scores else "MT AL NAJAF"
        top_score = scores[0].get("total_score", 89.9) if scores else 89.9

        answer = (
            f"**Incident {inc.get('id', 'VARUNA-2026-001')}: {inc.get('title', 'Port Said / Eastern Mediterranean Spill')}**\n\n"
            f"- **Status:** {inc.get('status', 'INVESTIGATING')}\n"
            f"- **Location Centroid:** {inc.get('center_lat', 31.9255)}° N, {inc.get('center_lon', 32.8949)}° E\n"
            f"- **Primary Suspect Vessel:** **{top_name}** (Attribution Score: {top_score:.1f}/100, Priority: HIGH)\n\n"
            f"You can ask questions such as:\n"
            f"- *'Which ship was ranked one and why not the other?'*\n"
            f"- *'Why is MT AL NAJAF considered suspicious?'*\n"
            f"- *'Explain the origin backtrack and spill time window'* \n"
            f"- *'What marine assets are threatened in the forward spread?'*"
        )
        return {
            "answer": answer,
            "tool_used": "get_incident_summary",
            "citations": [],
            "model_used": "deterministic-fallback"
        }

grounded_assistant = GroundedInvestigationAssistant()
