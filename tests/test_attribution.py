from datetime import datetime
from services.ais.synthetic import synthetic_ais_generator
from services.ais.trajectory import ais_trajectory_service
from services.attribution.engine import attribution_engine

def test_attribution_ranking():
    origin_time = datetime(2026, 9, 4, 14, 0, 0)
    scenario = synthetic_ais_generator.generate_scenario(
        origin_lat=18.85,
        origin_lon=72.72,
        origin_time=origin_time
    )
    
    candidates = ais_trajectory_service.who_was_here(
        ais_points=scenario["ais_points"],
        vessels=scenario["vessels"],
        origin_lat=18.85,
        origin_lon=72.72,
        origin_window_start=datetime(2026, 9, 4, 13, 30, 0),
        origin_window_end=datetime(2026, 9, 4, 14, 30, 0)
    )
    
    trajectories = ais_trajectory_service.build_trajectories(scenario["ais_points"])
    
    ranked = attribution_engine.rank_all_candidates(
        candidates=candidates,
        trajectories=trajectories,
        anomalies=scenario["anomalies"],
        origin_lat=18.85,
        origin_lon=72.72,
        origin_window_start=datetime(2026, 9, 4, 13, 30, 0),
        origin_window_end=datetime(2026, 9, 4, 14, 30, 0),
        slick_orientation_deg=48.0
    )
    
    assert len(ranked) > 0
    top = ranked[0]
    assert top["vessel_name"] == "PACIFIC VOYAGER"
    assert top["total_score"] >= 70.0
    assert top["priority_level"] == "HIGH"
    assert "proximity" in top["breakdown"]
    assert "timing" in top["breakdown"]
    assert "trajectory" in top["breakdown"]
    assert "ais_gap" in top["breakdown"]
    assert "behaviour_anomaly" in top["breakdown"]
    assert len(top["reasons"]) >= 2
