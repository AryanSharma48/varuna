import math
from datetime import datetime

class EnvironmentalSnapshot:
    """
    Oceanographic and meteorological forcing data provider.
    Maintains wind, surface currents, and wave parameters for reproducible drift modeling.
    """
    def __init__(self,
                 wind_speed_ms: float = 6.2,
                 wind_direction_deg: float = 240.0, # wind blowing FROM 240 (SW) towards NE (60)
                 current_speed_ms: float = 0.35,
                 current_direction_deg: float = 75.0, # current heading 75 deg (ENE)
                 sea_surface_temp_c: float = 28.5,
                 wave_height_m: float = 1.2,
                 source_name: str = "ECMWF / HYCOM Reanalysis Demo Snapshot",
                 timestamp: datetime = None):
        self.wind_speed_ms = wind_speed_ms
        self.wind_direction_deg = wind_direction_deg
        self.current_speed_ms = current_speed_ms
        self.current_direction_deg = current_direction_deg
        self.sea_surface_temp_c = sea_surface_temp_c
        self.wave_height_m = wave_height_m
        self.source_name = source_name
        self.timestamp = timestamp or datetime.utcnow()

    def get_velocity_components(self) -> dict:
        """
        Computes u (eastward) and v (northward) vector components in m/s.
        Wind direction is meteorologically 'from', so drift is opposite (direction + 180).
        Current direction is oceanographically 'towards'.
        """
        # Wind drift direction (blowing towards)
        wind_towards_deg = (self.wind_direction_deg + 180.0) % 360.0
        wind_rad = math.radians(wind_towards_deg)
        wind_u = self.wind_speed_ms * math.sin(wind_rad)
        wind_v = self.wind_speed_ms * math.cos(wind_rad)
        
        # Ocean current direction (heading towards)
        curr_rad = math.radians(self.current_direction_deg)
        curr_u = self.current_speed_ms * math.sin(curr_rad)
        curr_v = self.current_speed_ms * math.cos(curr_rad)
        
        return {
            "wind_u": wind_u,
            "wind_v": wind_v,
            "curr_u": curr_u,
            "curr_v": curr_v,
            "wind_speed_ms": self.wind_speed_ms,
            "wind_direction_deg": self.wind_direction_deg,
            "current_speed_ms": self.current_speed_ms,
            "current_direction_deg": self.current_direction_deg,
            "source_name": self.source_name
        }
