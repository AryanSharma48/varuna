import random
import math
from datetime import datetime, timedelta

class SyntheticAISGenerator:
    """
    Deterministic Synthetic AIS Scenario Generator.
    Generates realistic MarineCadastre-compatible AIS traffic with controlled ground truth,
    candidate vessels, anomalies (AIS gaps, course changes, speed drops), and background traffic.
    """
    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed

    def generate_scenario(self,
                          origin_lat: float = 18.85,
                          origin_lon: float = 72.72,
                          origin_time: datetime = datetime(2026, 9, 4, 14, 0, 0),
                          duration_hours: float = 12.0) -> dict:
        """
        Generates vessels and AIS points surrounding the spill origin over a timeline.
        """
        random.seed(self.random_seed)
        start_time = origin_time - timedelta(hours=6.0)
        
        # 1. Prime Candidate (Tanker: "PACIFIC VOYAGER", MMSI: 412356789)
        # Passes directly through origin at 13:45-14:15, throttles down from 14.2 to 6.1 kts,
        # goes 'dark' (AIS gap for 40 min), turns 45 deg, and resumes at 14:55.
        vessels = [
            {
                "mmsi": 412356789,
                "vessel_name": "PACIFIC VOYAGER",
                "vessel_type": "Crude Oil Tanker",
                "flag": "Panama",
                "imo": 9458214,
                "length_m": 274.0,
                "width_m": 48.0,
                "source_type": "synthetic",
                "is_ground_truth_target": True
            },
            {
                "mmsi": 211567890,
                "vessel_name": "NORDIC TRADER",
                "vessel_type": "Container Ship",
                "flag": "Liberia",
                "imo": 9321568,
                "length_m": 298.0,
                "width_m": 42.0,
                "source_type": "synthetic",
                "is_ground_truth_target": False
            },
            {
                "mmsi": 352678901,
                "vessel_name": "OCEAN EXPLORER",
                "vessel_type": "Bulk Carrier",
                "flag": "Marshall Islands",
                "imo": 9187642,
                "length_m": 225.0,
                "width_m": 32.0,
                "source_type": "synthetic",
                "is_ground_truth_target": False
            },
            {
                "mmsi": 419012345,
                "vessel_name": "SAGAR RATNA",
                "vessel_type": "Offshore Supply Vessel",
                "flag": "India",
                "imo": 9654123,
                "length_m": 78.0,
                "width_m": 16.0,
                "source_type": "synthetic",
                "is_ground_truth_target": False
            },
            {
                "mmsi": 419890123,
                "vessel_name": "MATSYA RANI",
                "vessel_type": "Fishing Vessel",
                "flag": "India",
                "imo": None,
                "length_m": 24.0,
                "width_m": 6.0,
                "source_type": "synthetic",
                "is_ground_truth_target": False
            }
        ]
        
        ais_points = []
        anomalies = []
        
        # Total steps (e.g., every 5 minutes over 12 hours)
        num_steps = int((duration_hours * 60) / 5)
        
        # Generate Prime Candidate Trajectory
        # Starts SW (18.65, 72.50), travels NE through origin (18.85, 72.72)
        cur_lat = origin_lat - 0.20
        cur_lon = origin_lon - 0.22
        heading = 48.0
        
        for step in range(num_steps):
            t = start_time + timedelta(minutes=step * 5)
            # Normal speed
            sog = 14.5 + random.uniform(-0.3, 0.3)
            
            # Anomaly region near origin between 13:40 and 14:40
            time_diff_origin = (t - origin_time).total_seconds() / 60.0 # in minutes
            
            if -25.0 <= time_diff_origin <= 20.0:
                # Dark ship AIS gap: suppress broadcasts between 13:50 and 14:30
                if -10.0 <= time_diff_origin <= 30.0:
                    if time_diff_origin == -10.0:
                        anomalies.append({
                            "id": f"anom_gap_{vessels[0]['mmsi']}",
                            "mmsi": vessels[0]["mmsi"],
                            "timestamp": t.isoformat(),
                            "latitude": round(cur_lat, 6),
                            "longitude": round(cur_lon, 6),
                            "anomaly_type": "AIS_GAP",
                            "severity": "HIGH",
                            "description": "AIS signal loss / 40-minute transmission gap detected in proximity to origin zone",
                            "raw_details": {"duration_min": 40.0, "last_sog": 6.2}
                        })
                    # Advance vessel coordinates physically without broadcasting
                    cur_lat += 0.005 * math.cos(math.radians(heading + 35.0))
                    cur_lon += 0.005 * math.sin(math.radians(heading + 35.0))
                    continue
                else:
                    # Slowdown & manoeuvre
                    sog = 6.2 + random.uniform(-0.5, 0.5)
                    heading = 85.0
                    anomalies.append({
                        "id": f"anom_spd_{vessels[0]['mmsi']}_{step}",
                        "mmsi": vessels[0]["mmsi"],
                        "timestamp": t.isoformat(),
                        "latitude": round(cur_lat, 6),
                        "longitude": round(cur_lon, 6),
                        "anomaly_type": "SPEED_JUMP",
                        "severity": "MEDIUM",
                        "description": f"Abrupt speed reduction from 14.2 kts to {sog:.1f} kts during transit",
                        "raw_details": {"prior_sog": 14.2, "new_sog": sog}
                    })
            else:
                heading = 48.0
                
            # Update coordinate based on SOG & heading
            dist_km = (sog * 1.852) * (5.0 / 60.0)
            cur_lat += (dist_km * math.cos(math.radians(heading))) / 111.0
            cur_lon += (dist_km * math.sin(math.radians(heading))) / (111.0 * math.cos(math.radians(cur_lat)))
            
            ais_points.append({
                "mmsi": vessels[0]["mmsi"],
                "timestamp": t.isoformat(),
                "latitude": round(cur_lat, 6),
                "longitude": round(cur_lon, 6),
                "sog": round(sog, 1),
                "cog": round(heading, 1),
                "heading": round(heading, 1),
                "nav_status": "Under way using engine",
                "source_type": "synthetic"
            })
            
        # Generate other normal traffic vessels
        # Vessel 1: NORDIC TRADER (Passes 12 km East, normal transit at 18 kts)
        n_lat = origin_lat - 0.30
        n_lon = origin_lon + 0.12
        for step in range(num_steps):
            t = start_time + timedelta(minutes=step * 5)
            sog = 18.2 + random.uniform(-0.2, 0.2)
            cog = 358.0 # Due North
            dist_km = (sog * 1.852) * (5.0 / 60.0)
            n_lat += (dist_km * math.cos(math.radians(cog))) / 111.0
            n_lon += (dist_km * math.sin(math.radians(cog))) / (111.0 * math.cos(math.radians(n_lat)))
            ais_points.append({
                "mmsi": vessels[1]["mmsi"],
                "timestamp": t.isoformat(),
                "latitude": round(n_lat, 6),
                "longitude": round(n_lon, 6),
                "sog": round(sog, 1),
                "cog": round(cog, 1),
                "heading": round(cog, 1),
                "nav_status": "Under way using engine",
                "source_type": "synthetic"
            })
            
        # Vessel 2: OCEAN EXPLORER (Passes 18 km West, normal transit at 12 kts)
        o_lat = origin_lat + 0.25
        o_lon = origin_lon - 0.20
        for step in range(num_steps):
            t = start_time + timedelta(minutes=step * 5)
            sog = 12.0 + random.uniform(-0.4, 0.4)
            cog = 175.0 # South
            dist_km = (sog * 1.852) * (5.0 / 60.0)
            o_lat += (dist_km * math.cos(math.radians(cog))) / 111.0
            o_lon += (dist_km * math.sin(math.radians(cog))) / (111.0 * math.cos(math.radians(o_lat)))
            ais_points.append({
                "mmsi": vessels[2]["mmsi"],
                "timestamp": t.isoformat(),
                "latitude": round(o_lat, 6),
                "longitude": round(o_lon, 6),
                "sog": round(sog, 1),
                "cog": round(cog, 1),
                "heading": round(cog, 1),
                "nav_status": "Under way using engine",
                "source_type": "synthetic"
            })
            
        # Vessel 3: SAGAR RATNA (Supply vessel stationary/loitering at offshore platform 22 km NW)
        s_lat = origin_lat + 0.15
        s_lon = origin_lon - 0.15
        for step in range(num_steps):
            t = start_time + timedelta(minutes=step * 5)
            ais_points.append({
                "mmsi": vessels[3]["mmsi"],
                "timestamp": t.isoformat(),
                "latitude": round(s_lat + random.uniform(-0.001, 0.001), 6),
                "longitude": round(s_lon + random.uniform(-0.001, 0.001), 6),
                "sog": round(random.uniform(0.1, 1.2), 1),
                "cog": round(random.uniform(0, 360), 1),
                "heading": round(120.0, 1),
                "nav_status": "Engaged in towing / stationary",
                "source_type": "synthetic"
            })
            
        # Vessel 4: MATSYA RANI (Coastal fishing boat 25 km SE near shore)
        f_lat = origin_lat - 0.18
        f_lon = origin_lon + 0.22
        for step in range(num_steps):
            t = start_time + timedelta(minutes=step * 5)
            ais_points.append({
                "mmsi": vessels[4]["mmsi"],
                "timestamp": t.isoformat(),
                "latitude": round(f_lat + random.uniform(-0.005, 0.005), 6),
                "longitude": round(f_lon + random.uniform(-0.005, 0.005), 6),
                "sog": round(random.uniform(2.0, 5.5), 1),
                "cog": round(random.uniform(0, 360), 1),
                "heading": None,
                "nav_status": "Engaged in fishing",
                "source_type": "synthetic"
            })
            
        return {
            "scenario_name": "VARUNA Controlled Maritime Scenario",
            "source_type": "synthetic",
            "generator_version": "1.0.0",
            "random_seed": self.random_seed,
            "origin_target": {"lat": origin_lat, "lon": origin_lon, "time": origin_time.isoformat()},
            "vessels": vessels,
            "ais_points": ais_points,
            "anomalies": anomalies
        }

synthetic_ais_generator = SyntheticAISGenerator()
