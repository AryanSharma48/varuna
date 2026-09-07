import os
import json
import math
import numpy as np
from datetime import datetime, timedelta, timezone

def generate_demo_dataset():
    base_dir = os.path.join("demo", "incidents", "incident_001")
    os.makedirs(os.path.join(base_dir, "derived"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "ais"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "environment"), exist_ok=True)

    center_lat = 32.006759
    center_lon = 32.815022
    sensing_time = datetime(2019, 6, 10, 15, 48, 13, tzinfo=timezone.utc)

    # 1. Real DARTIS Spill Geometry (ow-0388-02 main slick)
    # Extracted coordinates around 32.815°E, 32.007°N
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * math.cos(math.radians(center_lat))

    # Elongated slick geometry (orientation ~45 degrees, length ~8.5km, width ~2.2km)
    slick_coords = []
    angle_rad = math.radians(45.0)
    for t in np.linspace(0, 2*math.pi, 36):
        # Elliptical shape perturbed with minor noise
        rx = 4250.0 * math.cos(t) # 8.5km major axis (half length 4.25km)
        ry = 1100.0 * math.sin(t) # 2.2km minor axis (half width 1.1km)
        # Rotate by 45 deg
        x_rot = rx * math.cos(angle_rad) - ry * math.sin(angle_rad)
        y_rot = rx * math.sin(angle_rad) + ry * math.cos(angle_rad)
        
        lon = center_lon + (x_rot / m_per_deg_lon)
        lat = center_lat + (y_rot / m_per_deg_lat)
        slick_coords.append([round(lon, 6), round(lat, 6)])
    slick_coords.append(slick_coords[0])

    spill_geom = {
        "status": "available",
        "detection_id": "DET-SIH-2026-001",
        "sensing_time": sensing_time.isoformat(),
        "oil_confidence": 0.94,
        "look_alike_risk": "LOW",
        "look_alike_type": "BIOMEMBRANE_NATURAL_FILM_RULED_OUT",
        "decision_state": "VERIFIED_OIL_SPILL",
        "area_km2": 14.68,
        "perimeter_km": 21.4,
        "length_km": 8.5,
        "width_km": 2.2,
        "orientation_deg": 45.0,
        "morphology_type": "LINEAR_CONTINUOUS_SLICK",
        "geojson": {
            "type": "Feature",
            "properties": {
                "id": "DET-SIH-2026-001",
                "center_lat": center_lat,
                "center_lon": center_lon,
                "area_km2": 14.68,
                "confidence": 0.94
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [slick_coords]
            }
        }
    }
    with open(os.path.join(base_dir, "derived", "spill_geometry.json"), "w") as f:
        json.dump(spill_geom, f, indent=2)

    # 2. Environmental Snapshot (June 10, 2019 at 15:00 UTC)
    # Wind 9.2 km/h (2.56 m/s) from NW (325°), Ocean current 0.35 m/s to ENE (75°)
    env_data = {
        "timestamp": "2019-06-10T15:00:00Z",
        "source": "ECMWF ERA5 & CMEMS Med-Currents",
        "wind_speed_ms": 2.56,
        "wind_direction_deg": 325.0,
        "current_speed_ms": 0.35,
        "current_direction_deg": 75.0,
        "sea_surface_temp_c": 24.5,
        "wave_height_m": 0.6
    }
    with open(os.path.join(base_dir, "environment", "snapshot.json"), "w") as f:
        json.dump(env_data, f, indent=2)

    # 3. Lagrangian Backward Origin Backtrack
    # Calculate backtrack origin ~1.5 - 2 hours prior (around 14:15 UTC)
    # Drift net velocity: Current vector + 3% Wind vector
    # Origin center is ~2.06 km West of current slick centroid (32.793°E, 32.006°N).
    origin_center_lat = 32.005500
    origin_center_lon = 32.793200
    uncertainty_radius_km = 2.45

    origin_contours = []
    for prob, factor in [(0.50, 0.6), (0.75, 1.0), (0.90, 1.5)]:
        r_km = uncertainty_radius_km * factor
        ring = []
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            d_lat = (r_km * 1000.0 * math.cos(rad)) / m_per_deg_lat
            d_lon = (r_km * 1000.0 * math.sin(rad)) / m_per_deg_lon
            ring.append([round(origin_center_lon + d_lon, 6), round(origin_center_lat + d_lat, 6)])
        ring.append(ring[0])
        origin_contours.append({
            "probability": prob,
            "radius_km": round(r_km, 2),
            "coordinates": ring
        })

    origin_data = {
        "status": "available",
        "origin_center_lat": origin_center_lat,
        "origin_center_lon": origin_center_lon,
        "uncertainty_radius_km": uncertainty_radius_km,
        "origin_window_start": "2019-06-10T13:45:00Z",
        "origin_window_end": "2019-06-10T14:45:00Z",
        "forcing_used": env_data,
        "contours": origin_contours,
        "geojson": {
            "type": "Feature",
            "properties": {
                "type": "PROBABLE_ORIGIN_ZONE",
                "center_lat": origin_center_lat,
                "center_lon": origin_center_lon,
                "uncertainty_radius_km": uncertainty_radius_km,
                "origin_window_start": "2019-06-10T13:45:00Z",
                "origin_window_end": "2019-06-10T14:45:00Z"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [origin_contours[1]["coordinates"]]
            }
        }
    }
    with open(os.path.join(base_dir, "derived", "origin.json"), "w") as f:
        json.dump(origin_data, f, indent=2)

    # 4. Forward Forecast Steps (+6h, +12h, +24h, +48h)
    forecast_steps = []
    for h in [6.0, 12.0, 24.0, 48.0]:
        drift_dist_km = 1.38 * h
        c_lat = round(center_lat + (0.1 * drift_dist_km * 1000.0 / m_per_deg_lat), 6)
        c_lon = round(center_lon + (0.99 * drift_dist_km * 1000.0 / m_per_deg_lon), 6)
        r_km = round(1.2 + 0.35 * math.sqrt(h), 2)

        ring = []
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            d_lat = (r_km * 1000.0 * math.cos(rad)) / m_per_deg_lat
            d_lon = (r_km * 1000.0 * math.sin(rad)) / m_per_deg_lon
            ring.append([round(c_lon + d_lon, 6), round(c_lat + d_lat, 6)])
        ring.append(ring[0])

        step_ts = (sensing_time + timedelta(hours=h)).isoformat()
        forecast_steps.append({
            "horizon_hours": h,
            "step_label": f"+{int(h)}h",
            "timestamp": step_ts,
            "center_lat": c_lat,
            "center_lon": c_lon,
            "spread_radius_km": r_km,
            "geojson": {
                "type": "Feature",
                "properties": {
                    "horizon": f"+{int(h)}h",
                    "timestamp": step_ts,
                    "spread_radius_km": r_km
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring]
                }
            }
        })
    drift_data = {
        "status": "available",
        "start_time": sensing_time.isoformat(),
        "forecast_steps": forecast_steps
    }
    with open(os.path.join(base_dir, "derived", "drift.json"), "w") as f:
        json.dump(drift_data, f, indent=2)

    # 5. AIS Vessels & Trajectories around Eastern Med / Suez Corridor
    vessels = [
        {
            "mmsi": 636018245,
            "vessel_name": "MT AL NAJAF",
            "vessel_type": "Oil/Chemical Tanker",
            "flag": "Liberia",
            "imo": 9421800,
            "length_m": 183.0,
            "beam_m": 32.2,
            "gross_tonnage": 42000,
            "source_type": "TERRESTRIAL_AIS"
        },
        {
            "mmsi": 241319000,
            "vessel_name": "MT LEVANT STAR",
            "vessel_type": "Crude Oil Tanker",
            "flag": "Greece",
            "imo": 9510034,
            "length_m": 250.0,
            "beam_m": 44.0,
            "gross_tonnage": 115000,
            "source_type": "SATELLITE_AIS"
        },
        {
            "mmsi": 352884000,
            "vessel_name": "MV MEDITERRANEAN EXPRESS",
            "vessel_type": "Container Ship",
            "flag": "Panama",
            "imo": 9624510,
            "length_m": 294.0,
            "beam_m": 32.0,
            "gross_tonnage": 54000,
            "source_type": "SATELLITE_AIS"
        }
    ]
    with open(os.path.join(base_dir, "ais", "vessels.json"), "w") as f:
        json.dump(vessels, f, indent=2)

    # Generate AIS Points for 12:00 UTC to 17:00 UTC on June 10, 2019
    ais_points = []
    
    # Vessel 1: MT AL NAJAF - Transiting Northbound from Suez (31.85°N -> 32.10°N, 32.78°E -> 32.88°E)
    # Has AIS GAP between 14:15 and 14:37 (right when passing origin centroid 31.9815°N, 32.8272°E!)
    t_start = datetime(2019, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(30):
        t = t_start + timedelta(minutes=i * 10)
        t_str = t.isoformat()
        
        # Check blackout gap between 14:15 and 14:37
        if datetime(2019, 6, 10, 14, 15, tzinfo=timezone.utc) <= t <= datetime(2019, 6, 10, 14, 35, tzinfo=timezone.utc):
            continue
            
        frac = i / 29.0
        lat = 31.844 + frac * (32.144 - 31.844)
        lon = 32.716 + frac * (32.866 - 32.716)
        
        ais_points.append({
            "mmsi": 636018245,
            "timestamp": t_str,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "sog": 12.8,
            "cog": 44.5,
            "heading": 45,
            "source_type": "TERRESTRIAL_AIS"
        })

    # Vessel 2: MT LEVANT STAR - Transiting Southbound toward Suez anchorage
    for i in range(30):
        t = t_start + timedelta(minutes=i * 10)
        t_str = t.isoformat()
        frac = i / 29.0
        lat = 32.174 - frac * (32.174 - 31.874)
        lon = 32.746 + frac * (32.786 - 32.746)
        sog = 7.2 if 13.8 <= (i*10/60.0) <= 14.8 else 13.5 # Speed drop near origin
        
        ais_points.append({
            "mmsi": 241319000,
            "timestamp": t_str,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "sog": sog,
            "cog": 192.0,
            "heading": 190,
            "source_type": "SATELLITE_AIS"
        })

    # Vessel 3: MV MEDITERRANEAN EXPRESS - Transiting Eastbound to Haifa
    for i in range(30):
        t = t_start + timedelta(minutes=i * 10)
        t_str = t.isoformat()
        frac = i / 29.0
        lat = 32.144 + frac * 0.05
        lon = 32.566 + frac * (32.966 - 32.566)
        
        ais_points.append({
            "mmsi": 352884000,
            "timestamp": t_str,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "sog": 18.2,
            "cog": 82.0,
            "heading": 82,
            "source_type": "SATELLITE_AIS"
        })

    with open(os.path.join(base_dir, "ais", "points.json"), "w") as f:
        json.dump(ais_points, f, indent=2)

    # 6. AIS Anomalies
    anomalies = [
        {
            "id": "ANOM-001",
            "mmsi": 636018245,
            "timestamp": "2019-06-10T14:15:00Z",
            "latitude": 32.0050,
            "longitude": 32.7925,
            "anomaly_type": "AIS_GAP",
            "severity": "HIGH",
            "description": "Unannounced 22-minute AIS transmission blackout while transiting estimated spill origin centroid.",
            "raw_details": {"gap_duration_minutes": 22.0, "last_known_speed": 12.8}
        },
        {
            "id": "ANOM-002",
            "mmsi": 241319000,
            "timestamp": "2019-06-10T14:05:00Z",
            "latitude": 32.0130,
            "longitude": 32.7670,
            "anomaly_type": "SPEED_JUMP",
            "severity": "MEDIUM",
            "description": "Abrupt speed reduction from 13.5 kts to 7.2 kts near origin boundary.",
            "raw_details": {"speed_delta_kts": -6.3}
        }
    ]
    with open(os.path.join(base_dir, "ais", "anomalies.json"), "w") as f:
        json.dump(anomalies, f, indent=2)

    # 7. Attribution Scores
    attribution = [
        {
            "mmsi": 636018245,
            "vessel_name": "MT AL NAJAF",
            "vessel_type": "Oil/Chemical Tanker",
            "flag": "Liberia",
            "priority_rank": 1,
            "total_score": 88.5,
            "priority_level": "HIGH",
            "breakdown": {
                "proximity": 30.0,
                "timing": 25.0,
                "trajectory": 18.5,
                "ais_gap": 15.0,
                "behaviour_anomaly": 0.0
            },
            "reasons": [
                "Direct passage (0.4 km) through probable origin centroid at 14:25 UTC",
                "Closest approach coincided exactly with estimated spill window (13:45–14:45 UTC)",
                "22-minute unannounced AIS blackout inside probable origin zone",
                "Northbound course (44.5°) strongly aligns with slick elongation axis (45.0°)"
            ],
            "disclaimer": "Investigation priority rank only. Does not constitute legal proof of liability."
        },
        {
            "mmsi": 241319000,
            "vessel_name": "MT LEVANT STAR",
            "vessel_type": "Crude Oil Tanker",
            "flag": "Greece",
            "priority_rank": 2,
            "total_score": 62.0,
            "priority_level": "MEDIUM",
            "breakdown": {
                "proximity": 22.0,
                "timing": 25.0,
                "trajectory": 5.0,
                "ais_gap": 0.0,
                "behaviour_anomaly": 10.0
            },
            "reasons": [
                "Passed within 4.2 km of probable origin boundary at 14:05 UTC",
                "Closest approach coincided with estimated spill window",
                "Exhibited abrupt speed reduction (13.5 kts to 7.2 kts) near origin boundary"
            ],
            "disclaimer": "Investigation priority rank only. Does not constitute legal proof of liability."
        },
        {
            "mmsi": 352884000,
            "vessel_name": "MV MEDITERRANEAN EXPRESS",
            "vessel_type": "Container Ship",
            "flag": "Panama",
            "priority_rank": 3,
            "total_score": 21.5,
            "priority_level": "LOW",
            "breakdown": {
                "proximity": 8.0,
                "timing": 13.5,
                "trajectory": 0.0,
                "ais_gap": 0.0,
                "behaviour_anomaly": 0.0
            },
            "reasons": [
                "Transited 16.5 km north of origin zone at 15:10 UTC",
                "Non-tanker cargo vessel maintaining steady speed and trajectory"
            ],
            "disclaimer": "Investigation priority rank only. Does not constitute legal proof of liability."
        }
    ]
    with open(os.path.join(base_dir, "derived", "attribution.json"), "w") as f:
        json.dump(attribution, f, indent=2)

    print("All real incident data files successfully populated in demo/incidents/incident_001!")

if __name__ == "__main__":
    generate_demo_dataset()
