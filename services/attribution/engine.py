import math
from datetime import datetime
from typing import Dict, Any, List
from apps.api.config import settings
from services.ais.trajectory import AISTrajectoryService

class VesselAttributionEngine:
    """
    Explainable Multi-Evidence Vessel Attribution Engine.
    Calculates transparent investigation priority scores based on:
    - Spatial Proximity to estimated origin
    - Temporal alignment with spill window
    - Trajectory heading alignment & intersection
    - AIS transmission gaps ('dark ship' periods)
    - Behavioural anomalies (speed drops, abrupt turns)
    """
    def __init__(self,
                 w_proximity: float = settings.WEIGHT_PROXIMITY,
                 w_timing: float = settings.WEIGHT_TIMING,
                 w_trajectory: float = settings.WEIGHT_TRAJECTORY,
                 w_ais_gap: float = settings.WEIGHT_AIS_GAP,
                 w_behaviour: float = settings.WEIGHT_BEHAVIOUR_ANOMALY):
        self.w_proximity = w_proximity
        self.w_timing = w_timing
        self.w_trajectory = w_trajectory
        self.w_ais_gap = w_ais_gap
        self.w_behaviour = w_behaviour

    def calculate_attribution(self,
                              candidate: Dict[str, Any],
                              track: List[Dict[str, Any]],
                              anomalies: List[Dict[str, Any]],
                              origin_lat: float,
                              origin_lon: float,
                              origin_window_start: datetime,
                              origin_window_end: datetime,
                              slick_orientation_deg: float = 45.0) -> Dict[str, Any]:
        """
        Calculates decomposable score (0 - 100) and rationale for a single candidate vessel.
        """
        reasons = []
        
        # 1. Proximity Score (30 max)
        min_dist_km = candidate.get("min_distance_to_origin_km", 999.0)
        if min_dist_km <= 2.0:
            raw_prox = 100.0
            reasons.append(f"Direct passage ({min_dist_km:.1f} km) through probable origin centroid")
        elif min_dist_km <= 10.0:
            raw_prox = 100.0 * (1.0 - (min_dist_km - 2.0) / 8.0)
            reasons.append(f"Close spatial proximity ({min_dist_km:.1f} km) to probable origin boundary")
        elif min_dist_km <= 25.0:
            raw_prox = 40.0 * (1.0 - (min_dist_km - 10.0) / 15.0)
            reasons.append(f"Moderate distance ({min_dist_km:.1f} km) from origin zone")
        else:
            raw_prox = 0.0
        score_prox = self.w_proximity * raw_prox
        
        # 2. Timing Score (25 max)
        cpa_time_str = candidate.get("closest_approach_time")
        if cpa_time_str:
            cpa_time = datetime.fromisoformat(cpa_time_str) if isinstance(cpa_time_str, str) else cpa_time_str
            cpa_naive = cpa_time.replace(tzinfo=None) if hasattr(cpa_time, 'tzinfo') and cpa_time.tzinfo else cpa_time
            w_start = origin_window_start.replace(tzinfo=None) if hasattr(origin_window_start, 'tzinfo') and origin_window_start.tzinfo else origin_window_start
            w_end = origin_window_end.replace(tzinfo=None) if hasattr(origin_window_end, 'tzinfo') and origin_window_end.tzinfo else origin_window_end

            if w_start <= cpa_naive <= w_end:
                raw_time = 100.0
                reasons.append(f"Closest approach ({cpa_naive.strftime('%H:%M UTC')}) coincided exactly with estimated spill window")
            else:
                diff_hours = min(
                    abs((cpa_naive - w_start).total_seconds()),
                    abs((cpa_naive - w_end).total_seconds())
                ) / 3600.0
                raw_time = max(0.0, 100.0 * (1.0 - diff_hours / 4.0))
                reasons.append(f"Passed within {diff_hours:.1f} hours of estimated spill window")
        else:
            raw_time = 0.0
        score_time = self.w_timing * raw_time
        
        # 3. Trajectory & Heading Alignment Score (20 max)
        # Check if vessel course aligns with linear slick orientation
        if track:
            avg_cog = sum(p.get("cog", 0.0) for p in track) / len(track)
            angle_diff = abs(avg_cog - slick_orientation_deg) % 180.0
            if angle_diff > 90.0:
                angle_diff = 180.0 - angle_diff
            alignment_factor = 1.0 - (angle_diff / 90.0)
            raw_traj = 100.0 * alignment_factor
            if alignment_factor > 0.7:
                reasons.append(f"Transit course ({avg_cog:.1f}°) strongly aligns with slick elongation axis ({slick_orientation_deg:.1f}°)")
        else:
            raw_traj = 50.0
        score_traj = self.w_trajectory * raw_traj
        
        # 4. AIS Gap Score (15 max)
        vessel_anomalies = [a for a in anomalies if a.get("mmsi") == candidate["mmsi"]]
        gap_anomalies = [a for a in vessel_anomalies if a.get("anomaly_type") == "AIS_GAP"]
        if gap_anomalies:
            raw_gap = 100.0
            reasons.append("Identified unannounced AIS transmission outage / gap in origin vicinity")
        else:
            raw_gap = 0.0
        score_gap = self.w_ais_gap * raw_gap
        
        # 5. Behaviour Anomaly Score (10 max)
        other_anomalies = [a for a in vessel_anomalies if a.get("anomaly_type") in ("SPEED_JUMP", "COURSE_DEVIATION")]
        if other_anomalies:
            raw_anom = min(100.0, len(other_anomalies) * 50.0)
            reasons.append("Exhibited atypical kinematic behavior (speed reduction or sharp course change)")
        else:
            raw_anom = 0.0
        score_anom = self.w_behaviour * raw_anom
        
        total_score = round(score_prox + score_time + score_traj + score_gap + score_anom, 1)
        
        if total_score >= 70.0:
            priority_level = "HIGH"
        elif total_score >= 40.0:
            priority_level = "MEDIUM"
        else:
            priority_level = "LOW"
            
        return {
            "mmsi": candidate["mmsi"],
            "vessel_name": candidate.get("vessel_name"),
            "vessel_type": candidate.get("vessel_type"),
            "flag": candidate.get("flag"),
            "total_score": total_score,
            "priority_level": priority_level,
            "breakdown": {
                "proximity": round(score_prox, 1),
                "timing": round(score_time, 1),
                "trajectory": round(score_traj, 1),
                "ais_gap": round(score_gap, 1),
                "behaviour_anomaly": round(score_anom, 1)
            },
            "reasons": reasons,
            "disclaimer": "Investigation priority rank only. Does not constitute legal proof of liability."
        }

    def rank_all_candidates(self,
                            candidates: List[Dict[str, Any]],
                            trajectories: Dict[int, List[Dict[str, Any]]],
                            anomalies: List[Dict[str, Any]],
                            origin_lat: float,
                            origin_lon: float,
                            origin_window_start: datetime,
                            origin_window_end: datetime,
                            slick_orientation_deg: float = 45.0) -> List[Dict[str, Any]]:
        ranked = []
        for cand in candidates:
            mmsi = cand["mmsi"]
            track = trajectories.get(mmsi, [])
            res = self.calculate_attribution(
                candidate=cand,
                track=track,
                anomalies=anomalies,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                origin_window_start=origin_window_start,
                origin_window_end=origin_window_end,
                slick_orientation_deg=slick_orientation_deg
            )
            ranked.append(res)
            
        ranked.sort(key=lambda x: x["total_score"], reverse=True)
        for idx, item in enumerate(ranked):
            item["priority_rank"] = idx + 1
        return ranked

attribution_engine = VesselAttributionEngine()
