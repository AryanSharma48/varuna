from datetime import datetime
from services.drift.lagrangian import drift_engine
from services.drift.environmental import EnvironmentalSnapshot

def test_backward_drift_simulation():
    env = EnvironmentalSnapshot(
        wind_speed_ms=6.0, wind_direction_deg=240.0,
        current_speed_ms=0.30, current_direction_deg=75.0
    )
    res = drift_engine.simulate_backward_origin(
        slick_center_lat=18.92,
        slick_center_lon=72.83,
        detection_time=datetime(2026, 9, 4, 15, 0, 0),
        backtrack_hours=6.0,
        particle_count=200,
        env=env
    )
    
    assert "origin_center_lat" in res
    assert "origin_center_lon" in res
    assert res["uncertainty_radius_km"] > 0.0
    assert len(res["contours"]) == 3
    assert res["geojson"]["geometry"]["type"] == "Polygon"

def test_forward_drift_forecast():
    env = EnvironmentalSnapshot()
    forecast = drift_engine.simulate_forward_forecast(
        slick_center_lat=18.92,
        slick_center_lon=72.83,
        start_time=datetime(2026, 9, 4, 15, 0, 0),
        forecast_horizons_hours=[6.0, 12.0, 24.0, 48.0],
        particle_count=200,
        env=env
    )
    
    assert len(forecast) == 4
    assert forecast[0]["step_label"] == "+6h"
    assert forecast[3]["step_label"] == "+48h"
    assert forecast[3]["spread_radius_km"] >= forecast[0]["spread_radius_km"]
