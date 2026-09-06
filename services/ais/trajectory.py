import math
from datetime import datetime
from typing import List, Dict, Any

class AISTrajectoryService:
    """
    Trajectory reconstruction, spatio-temporal querying ("Who Was Here?"),
    and time-indexed vessel replay interpolation.
    """
    def __init__(self):
        pass

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes great-circle distance between two points in km."""
        r = 6371.0 # Earth radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def build_trajectories(self, ais_points: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Groups and sorts points by MMSI and timestamp."""
        trajectories = {}
        for pt in ais_points:
            mmsi = pt["mmsi"]
            if mmsi not in trajectories:
                trajectories[mmsi] = []
            trajectories[mmsi].append(pt)
            
        for mmsi in trajectories:
            trajectories[mmsi].sort(key=lambda p: p["timestamp"])
        return trajectories

    def who_was_here(self,
                     ais_points: List[Dict[str, Any]],
                     vessels: List[Dict[str, Any]],
                     origin_lat: float,
                     origin_lon: float,
                     origin_window_start: datetime,
                     origin_window_end: datetime,
                     search_radius_km: float = 35.0) -> List[Dict[str, Any]]:
        """
        Spatio-temporal filtering pipeline:
        1. All Traffic
        2. Spatially relevant (within search_radius_km)
        3. Temporally relevant (during or surrounding origin window)
        4. Trajectory closest approach computation (CPA)
        """
        vessel_map = {v["mmsi"]: v for v in vessels}
        trajectories = self.build_trajectories(ais_points)
        candidates = []
        
        # Ensure window bounds are timezone-naive UTC for consistent comparison
        w_start = origin_window_start.replace(tzinfo=None) if hasattr(origin_window_start, 'tzinfo') and origin_window_start.tzinfo else origin_window_start
        w_end = origin_window_end.replace(tzinfo=None) if hasattr(origin_window_end, 'tzinfo') and origin_window_end.tzinfo else origin_window_end

        for mmsi, track in trajectories.items():
            v_info = vessel_map.get(mmsi, {"vessel_name": f"MMSI {mmsi}", "vessel_type": "Unknown", "source_type": "synthetic"})
            
            min_dist_km = float("inf")
            closest_point = None
            points_in_window = []
            
            for pt in track:
                pt_time = datetime.fromisoformat(pt["timestamp"]) if isinstance(pt["timestamp"], str) else pt["timestamp"]
                pt_time_naive = pt_time.replace(tzinfo=None) if hasattr(pt_time, 'tzinfo') and pt_time.tzinfo else pt_time
                dist_km = self.haversine_km(pt["latitude"], pt["longitude"], origin_lat, origin_lon)
                
                if dist_km < min_dist_km:
                    min_dist_km = dist_km
                    closest_point = pt
                    
                if w_start <= pt_time_naive <= w_end:
                    points_in_window.append(pt)
                    
            if min_dist_km <= search_radius_km:
                # Build GeoJSON track
                coords = [[p["longitude"], p["latitude"]] for p in track]
                track_geojson = {
                    "type": "Feature",
                    "properties": {
                        "mmsi": mmsi,
                        "vessel_name": v_info.get("vessel_name"),
                        "vessel_type": v_info.get("vessel_type")
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    }
                }
                
                candidates.append({
                    "mmsi": mmsi,
                    "vessel_name": v_info.get("vessel_name", f"Vessel {mmsi}"),
                    "vessel_type": v_info.get("vessel_type", "Cargo"),
                    "flag": v_info.get("flag", "Unknown"),
                    "source_type": v_info.get("source_type", "synthetic"),
                    "min_distance_to_origin_km": round(min_dist_km, 2),
                    "closest_approach_time": closest_point["timestamp"] if closest_point else None,
                    "points_in_critical_window": len(points_in_window),
                    "total_points": len(track),
                    "track_geojson": track_geojson
                })
                
        # Sort by distance to origin
        candidates.sort(key=lambda c: c["min_distance_to_origin_km"])
        return candidates

    def get_interpolated_positions_at_time(self, 
                                           trajectories: Dict[int, List[Dict[str, Any]]], 
                                           target_time: datetime) -> List[Dict[str, Any]]:
        """
        Interpolates all vessel positions at an exact replay timestamp.
        """
        current_positions = []
        
        for mmsi, track in trajectories.items():
            if not track:
                continue
                
            pts = []
            for p in track:
                t = datetime.fromisoformat(p["timestamp"]) if isinstance(p["timestamp"], str) else p["timestamp"]
                pts.append((t, p))
                
            pts.sort(key=lambda x: x[0])
            
            # Check if target_time is within or near track
            if target_time < pts[0][0] or target_time > pts[-1][0]:
                continue
                
            # Find surrounding points
            for i in range(len(pts) - 1):
                t1, p1 = pts[i]
                t2, p2 = pts[i+1]
                if t1 <= target_time <= t2:
                    dt_total = (t2 - t1).total_seconds()
                    if dt_total == 0:
                        frac = 0.0
                    else:
                        frac = (target_time - t1).total_seconds() / dt_total
                        
                    interp_lat = p1["latitude"] + frac * (p2["latitude"] - p1["latitude"])
                    interp_lon = p1["longitude"] + frac * (p2["longitude"] - p1["longitude"])
                    interp_sog = p1["sog"] + frac * (p2["sog"] - p1["sog"])
                    interp_cog = p1["cog"]
                    
                    current_positions.append({
                        "mmsi": mmsi,
                        "timestamp": target_time.isoformat(),
                        "latitude": round(interp_lat, 6),
                        "longitude": round(interp_lon, 6),
                        "sog": round(interp_sog, 1),
                        "cog": round(interp_cog, 1),
                        "heading": p1.get("heading")
                    })
                    break
                    
        return current_positions

ais_trajectory_service = AISTrajectoryService()
