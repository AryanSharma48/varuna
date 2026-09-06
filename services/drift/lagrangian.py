import numpy as np
import math
from datetime import datetime, timedelta
from services.drift.environmental import EnvironmentalSnapshot

class LagrangianDriftEngine:
    """
    Standard Lagrangian Particle Transport Model for Oil Spill Origin Backtracking & Forward Trajectory Forecasting.
    Uses the empirical 3% windage factor + surface current advection + turbulent diffusion random walk.
    """
    def __init__(self, wind_drift_factor: float = 0.03, horizontal_diffusion_coeff: float = 2.0):
        self.wind_drift_factor = wind_drift_factor  # 3% rule
        self.diffusion_coeff = horizontal_diffusion_coeff  # m^2/s

    def simulate_backward_origin(self,
                                 slick_center_lat: float,
                                 slick_center_lon: float,
                                 detection_time: datetime,
                                 backtrack_hours: float = 6.0,
                                 particle_count: int = 500,
                                 env: EnvironmentalSnapshot = None) -> dict:
        """
        Backtracks particle ensemble from detected slick backwards in time to determine probable origin zone.
        """
        if env is None:
            env = EnvironmentalSnapshot()
            
        vel = env.get_velocity_components()
        # Net advection velocity (m/s) = Current + 0.03 * Wind
        u_net = vel["curr_u"] + self.wind_drift_factor * vel["wind_u"]
        v_net = vel["curr_v"] + self.wind_drift_factor * vel["wind_v"]
        
        # In backward simulation, particles move in OPPOSITE direction (-u_net, -v_net)
        dt_seconds = 300.0  # 5 minute time steps
        total_steps = int((backtrack_hours * 3600.0) / dt_seconds)
        
        # Initialize particles at slick center with slight Gaussian spread (500m)
        np.random.seed(42)
        dx_init = np.random.normal(0, 300, particle_count)
        dy_init = np.random.normal(0, 300, particle_count)
        
        # Convert meter displacements to lat/lon offsets
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * math.cos(math.radians(slick_center_lat))
        
        p_lons = slick_center_lon + (dx_init / m_per_deg_lon)
        p_lats = slick_center_lat + (dy_init / m_per_deg_lat)
        
        # Step backwards
        for _ in range(total_steps):
            # Advective step (negative direction for backtracking)
            dx_adv = -u_net * dt_seconds
            dy_adv = -v_net * dt_seconds
            
            # Turbulent diffusion step (random walk: sqrt(2 * D * dt) * N(0, 1))
            sigma_diff = math.sqrt(2.0 * self.diffusion_coeff * dt_seconds)
            dx_diff = np.random.normal(0, sigma_diff, particle_count)
            dy_diff = np.random.normal(0, sigma_diff, particle_count)
            
            p_lons += (dx_adv + dx_diff) / m_per_deg_lon
            p_lats += (dy_adv + dy_diff) / m_per_deg_lat
            
        origin_center_lat = float(np.mean(p_lats))
        origin_center_lon = float(np.mean(p_lons))
        
        # 90th percentile uncertainty radius in km
        distances_m = np.sqrt(((p_lons - origin_center_lon) * m_per_deg_lon)**2 + 
                              ((p_lats - origin_center_lat) * m_per_deg_lat)**2)
        uncertainty_radius_km = float(np.percentile(distances_m, 90) / 1000.0)
        
        origin_time_start = detection_time - timedelta(hours=backtrack_hours + 1.0)
        origin_time_end = detection_time - timedelta(hours=max(1.0, backtrack_hours - 1.0))
        
        # Build 3 confidence contour rings (50%, 75%, 90% probability)
        contours = []
        for prob, factor in [(0.50, 0.6), (0.75, 1.0), (0.90, 1.5)]:
            radius_km = uncertainty_radius_km * factor
            ring_coords = []
            for deg in range(0, 360, 15):
                rad = math.radians(deg)
                d_lat = (radius_km * 1000.0 * math.cos(rad)) / m_per_deg_lat
                d_lon = (radius_km * 1000.0 * math.sin(rad)) / m_per_deg_lon
                ring_coords.append([round(origin_center_lon + d_lon, 6), round(origin_center_lat + d_lat, 6)])
            ring_coords.append(ring_coords[0])
            contours.append({
                "probability": prob,
                "radius_km": round(radius_km, 2),
                "coordinates": ring_coords
            })
            
        origin_polygon_geojson = {
            "type": "Feature",
            "properties": {
                "type": "PROBABLE_ORIGIN_ZONE",
                "center_lat": round(origin_center_lat, 6),
                "center_lon": round(origin_center_lon, 6),
                "uncertainty_radius_km": round(uncertainty_radius_km, 2),
                "backtrack_hours": backtrack_hours,
                "origin_window_start": origin_time_start.isoformat(),
                "origin_window_end": origin_time_end.isoformat()
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [contours[1]["coordinates"]] # 75% contour as primary boundary
            }
        }
        
        return {
            "origin_center_lat": round(origin_center_lat, 6),
            "origin_center_lon": round(origin_center_lon, 6),
            "uncertainty_radius_km": round(uncertainty_radius_km, 2),
            "origin_window_start": origin_time_start.isoformat(),
            "origin_window_end": origin_time_end.isoformat(),
            "contours": contours,
            "geojson": origin_polygon_geojson,
            "forcing_used": vel
        }

    def simulate_forward_forecast(self,
                                  slick_center_lat: float,
                                  slick_center_lon: float,
                                  start_time: datetime,
                                  forecast_horizons_hours: list[float] = [6.0, 12.0, 24.0, 48.0],
                                  particle_count: int = 500,
                                  env: EnvironmentalSnapshot = None) -> list[dict]:
        """
        Simulates forward spill trajectory and spreading at +6h, +12h, +24h, +48h.
        """
        if env is None:
            env = EnvironmentalSnapshot()
            
        vel = env.get_velocity_components()
        u_net = vel["curr_u"] + self.wind_drift_factor * vel["wind_u"]
        v_net = vel["curr_v"] + self.wind_drift_factor * vel["wind_v"]
        
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * math.cos(math.radians(slick_center_lat))
        
        np.random.seed(42)
        p_lons = slick_center_lon + (np.random.normal(0, 400, particle_count) / m_per_deg_lon)
        p_lats = slick_center_lat + (np.random.normal(0, 400, particle_count) / m_per_deg_lat)
        
        dt_seconds = 300.0
        current_sim_time = 0.0
        forecast_results = []
        
        for horizon in sorted(forecast_horizons_hours):
            target_time = horizon * 3600.0
            steps_to_run = int((target_time - current_sim_time) / dt_seconds)
            
            for _ in range(steps_to_run):
                dx_adv = u_net * dt_seconds
                dy_adv = v_net * dt_seconds
                
                sigma_diff = math.sqrt(2.0 * self.diffusion_coeff * dt_seconds)
                dx_diff = np.random.normal(0, sigma_diff, particle_count)
                dy_diff = np.random.normal(0, sigma_diff, particle_count)
                
                p_lons += (dx_adv + dx_diff) / m_per_deg_lon
                p_lats += (dy_adv + dy_diff) / m_per_deg_lat
                
            current_sim_time = target_time
            
            c_lat = float(np.mean(p_lats))
            c_lon = float(np.mean(p_lons))
            
            # Spread radius increases with time due to diffusion
            spread_radius_km = float(np.percentile(
                np.sqrt(((p_lons - c_lon) * m_per_deg_lon)**2 + ((p_lats - c_lat) * m_per_deg_lat)**2), 90
            ) / 1000.0)
            
            # Form spread polygon
            ring_coords = []
            for deg in range(0, 360, 15):
                rad = math.radians(deg)
                d_lat = (spread_radius_km * 1000.0 * math.cos(rad)) / m_per_deg_lat
                d_lon = (spread_radius_km * 1000.0 * math.sin(rad)) / m_per_deg_lon
                ring_coords.append([round(c_lon + d_lon, 6), round(c_lat + d_lat, 6)])
            ring_coords.append(ring_coords[0])
            
            step_time = start_time + timedelta(hours=horizon)
            forecast_results.append({
                "horizon_hours": horizon,
                "step_label": f"+{int(horizon)}h",
                "timestamp": step_time.isoformat(),
                "center_lat": round(c_lat, 6),
                "center_lon": round(c_lon, 6),
                "spread_radius_km": round(spread_radius_km, 2),
                "geojson": {
                    "type": "Feature",
                    "properties": {
                        "horizon": f"+{int(horizon)}h",
                        "timestamp": step_time.isoformat(),
                        "spread_radius_km": round(spread_radius_km, 2)
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [ring_coords]
                    }
                }
            })
            
        return forecast_results

drift_engine = LagrangianDriftEngine()
