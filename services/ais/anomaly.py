import math
from datetime import datetime
from typing import List, Dict, Any
from services.ais.trajectory import AISTrajectoryService

class AISAnomalyDetector:
    """
    Transparent rule-based AIS anomaly detection engine.
    Detects:
    - AIS transmission gaps while under way
    - Speed jumps & unrealistic acceleration
    - Teleport coordinate jumps
    - Abrupt course deviations near origin
    - Disappearance/reappearance ('Dark ship' behavior)
    """
    def __init__(self,
                 max_allowed_gap_minutes: float = 30.0,
                 max_plausible_speed_knots: float = 35.0,
                 max_course_change_deg: float = 50.0):
        self.max_gap_min = max_allowed_gap_minutes
        self.max_speed_kts = max_plausible_speed_knots
        self.max_course_deg = max_course_change_deg

    def detect_anomalies(self, 
                         mmsi: int, 
                         track: List[Dict[str, Any]], 
                         origin_lat: float, 
                         origin_lon: float) -> List[Dict[str, Any]]:
        anomalies = []
        if len(track) < 2:
            return anomalies
            
        # Ensure chronological order
        sorted_track = sorted(track, key=lambda p: p["timestamp"])
        
        for i in range(len(sorted_track) - 1):
            p1 = sorted_track[i]
            p2 = sorted_track[i+1]
            
            t1 = datetime.fromisoformat(p1["timestamp"]) if isinstance(p1["timestamp"], str) else p1["timestamp"]
            t2 = datetime.fromisoformat(p2["timestamp"]) if isinstance(p2["timestamp"], str) else p2["timestamp"]
            
            dt_min = (t2 - t1).total_seconds() / 60.0
            dist_km = AISTrajectoryService.haversine_km(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"])
            dist_to_origin_km = AISTrajectoryService.haversine_km(p1["latitude"], p1["longitude"], origin_lat, origin_lon)
            
            # 1. AIS Gap Detection
            if dt_min > self.max_gap_min and (p1["sog"] > 2.0 or p2["sog"] > 2.0):
                severity = "HIGH" if dist_to_origin_km < 15.0 else "MEDIUM"
                anomalies.append({
                    "id": f"anom_gap_{mmsi}_{i}",
                    "mmsi": mmsi,
                    "timestamp": p1["timestamp"],
                    "latitude": p1["latitude"],
                    "longitude": p1["longitude"],
                    "anomaly_type": "AIS_GAP",
                    "severity": severity,
                    "description": f"AIS transmission stopped for {int(dt_min)} minutes while vessel was under way ({p1['sog']} kts)",
                    "raw_details": {
                        "gap_minutes": round(dt_min, 1),
                        "distance_to_origin_km": round(dist_to_origin_km, 2)
                    }
                })
                
            # 2. Implied Speed between successive points
            if dt_min > 0:
                implied_speed_kts = (dist_km / 1.852) / (dt_min / 60.0)
                if implied_speed_kts > self.max_speed_kts:
                    anomalies.append({
                        "id": f"anom_speed_{mmsi}_{i}",
                        "mmsi": mmsi,
                        "timestamp": p2["timestamp"],
                        "latitude": p2["latitude"],
                        "longitude": p2["longitude"],
                        "anomaly_type": "SPEED_JUMP",
                        "severity": "HIGH",
                        "description": f"Physically impossible implied speed ({implied_speed_kts:.1f} kts) between AIS updates",
                        "raw_details": {
                            "implied_speed_kts": round(implied_speed_kts, 1),
                            "dt_minutes": round(dt_min, 1)
                        }
                    })
                    
            # 3. Course deviation near origin
            cog1 = p1.get("cog", 0.0)
            cog2 = p2.get("cog", 0.0)
            dcog = abs(cog2 - cog1)
            if dcog > 180.0:
                dcog = 360.0 - dcog
                
            if dcog > self.max_course_deg and dist_to_origin_km < 10.0 and dt_min <= 15.0:
                anomalies.append({
                    "id": f"anom_course_{mmsi}_{i}",
                    "mmsi": mmsi,
                    "timestamp": p2["timestamp"],
                    "latitude": p2["latitude"],
                    "longitude": p2["longitude"],
                    "anomaly_type": "COURSE_DEVIATION",
                    "severity": "MEDIUM",
                    "description": f"Abrupt course change of {dcog:.1f}° within {dist_to_origin_km:.1f} km of origin region",
                    "raw_details": {
                        "course_change_deg": round(dcog, 1),
                        "distance_to_origin_km": round(dist_to_origin_km, 2)
                    }
                })
                
        return anomalies

ais_anomaly_detector = AISAnomalyDetector()
