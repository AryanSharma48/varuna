from datetime import datetime
from services.ais.synthetic import synthetic_ais_generator
from services.ais.trajectory import ais_trajectory_service
from services.ais.anomaly import ais_anomaly_detector

def test_synthetic_scenario_and_who_was_here():
    origin_time = datetime(2026, 9, 4, 14, 0, 0)
    scenario = synthetic_ais_generator.generate_scenario(
        origin_lat=18.85,
        origin_lon=72.72,
        origin_time=origin_time
    )
    
    assert len(scenario["vessels"]) >= 5
    assert len(scenario["ais_points"]) > 100
    assert len(scenario["anomalies"]) >= 1
    
    candidates = ais_trajectory_service.who_was_here(
        ais_points=scenario["ais_points"],
        vessels=scenario["vessels"],
        origin_lat=18.85,
        origin_lon=72.72,
        origin_window_start=datetime(2026, 9, 4, 13, 30, 0),
        origin_window_end=datetime(2026, 9, 4, 14, 30, 0),
        search_radius_km=35.0
    )
    
    assert len(candidates) > 0
    # Pacific Voyager should be the closest candidate
    top = candidates[0]
    assert top["vessel_name"] == "PACIFIC VOYAGER"
    assert top["min_distance_to_origin_km"] < 5.0

def test_anomaly_detection_rules():
    origin_time = datetime(2026, 9, 4, 14, 0, 0)
    scenario = synthetic_ais_generator.generate_scenario(
        origin_lat=18.85,
        origin_lon=72.72,
        origin_time=origin_time
    )
    
    trajectories = ais_trajectory_service.build_trajectories(scenario["ais_points"])
    target_track = trajectories.get(412356789, [])
    
    anomalies = ais_anomaly_detector.detect_anomalies(
        mmsi=412356789,
        track=target_track,
        origin_lat=18.85,
        origin_lon=72.72
    )
    
    assert len(anomalies) >= 1
    types = [a["anomaly_type"] for a in anomalies]
    assert "AIS_GAP" in types
