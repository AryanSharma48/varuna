import math
from typing import List, Dict, Any
from services.ais.trajectory import AISTrajectoryService

class SensitiveImpactService:
    """
    Evaluates spatial intersection and time-to-impact between forward oil drift predictions
    and critical marine/coastal assets:
    - Marine Protected Areas (MPA) / Marine Sanctuaries
    - High-density Commercial Fishing Grounds
    - Coral Reef Ecosystems
    - Commercial Seaports & Harbor Entrances
    - Public Beaches / Coastal Tourism Zones
    """
    def __init__(self):
        self.default_assets = [
            {
                "id": "asset_eez_egypt",
                "name": "Egypt Sovereign EEZ & Coastal Waters",
                "asset_type": "EXCLUSIVE_ECONOMIC_ZONE",
                "center_lat": 31.65,
                "center_lon": 32.95,
                "radius_km": 35.0,
                "vulnerability_index": 0.95,
                "description": "Direct offshore maritime jurisdiction & sovereign continental shelf waters of Egypt."
            },
            {
                "id": "asset_fish_portsaid",
                "name": "Port Said & Damietta Commercial Trawling Grounds",
                "asset_type": "COMMERCIAL_FISHERY",
                "center_lat": 31.55,
                "center_lon": 32.55,
                "radius_km": 20.0,
                "vulnerability_index": 0.90,
                "description": "High-density demersal fishery for Mediterranean red mullet, seabream & penaeid shrimp."
            },
            {
                "id": "asset_mpa_zaranik",
                "name": "Zaranik Protected Area & Lake Bardawil Lagoon",
                "asset_type": "ENDANGERED_HABITAT",
                "center_lat": 31.25,
                "center_lon": 33.25,
                "radius_km": 18.0,
                "vulnerability_index": 0.98,
                "description": "Ramsar sanctuary. Critical nesting beach for endangered Loggerhead (Caretta caretta) & Green Sea Turtles."
            },
            {
                "id": "asset_fish_sinai",
                "name": "North Sinai Artisanal Gillnet Fishery (El Arish)",
                "asset_type": "ARTISANAL_FISHERY",
                "center_lat": 31.35,
                "center_lon": 33.50,
                "radius_km": 18.0,
                "vulnerability_index": 0.85,
                "description": "Artisanal inshore fishing community waters and pelagic seasonal migration corridor."
            },
            {
                "id": "asset_mpa_manzala",
                "name": "Ashtoum El Gamil & Lake Manzala Estuarine Reserve",
                "asset_type": "RAMSAR_SANCTUARY",
                "center_lat": 31.32,
                "center_lon": 32.22,
                "radius_km": 15.0,
                "vulnerability_index": 0.88,
                "description": "Coastal barrier lagoon and mullet fry nursery providing vital estuarine biodiversity habitat."
            },
            {
                "id": "asset_eez_levant",
                "name": "Levant Maritime Border & Gaza Marine Sector",
                "asset_type": "TRANSBOUNDARY_EEZ",
                "center_lat": 31.55,
                "center_lon": 34.15,
                "radius_km": 28.0,
                "vulnerability_index": 0.78,
                "description": "Transboundary coastal current trajectory watch (72h downwind advection window)."
            }
        ]

    def assess_impact(self, 
                      forecast_steps: List[Dict[str, Any]], 
                      custom_assets: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Intersects forward drift polygons with sensitive assets and calculates estimated time of arrival (ETA).
        """
        assets = custom_assets or self.default_assets
        impacts = []
        
        for asset in assets:
            a_lat = asset["center_lat"]
            a_lon = asset["center_lon"]
            a_rad = asset["radius_km"]
            
            intersected_step = None
            min_dist_to_slick = float("inf")
            
            for step in forecast_steps:
                s_lat = step["center_lat"]
                s_lon = step["center_lon"]
                s_rad = step["spread_radius_km"]
                
                dist_km = AISTrajectoryService.haversine_km(a_lat, a_lon, s_lat, s_lon)
                if dist_km < min_dist_to_slick:
                    min_dist_to_slick = dist_km
                    
                # Check circular buffer intersection
                if dist_km <= (a_rad + s_rad):
                    intersected_step = step
                    break
                    
            if intersected_step:
                impact_severity = "CRITICAL" if asset["vulnerability_index"] >= 0.85 else "HIGH"
                impacts.append({
                    "asset_id": asset["id"],
                    "asset_name": asset["name"],
                    "asset_type": asset["asset_type"],
                    "vulnerability_index": asset["vulnerability_index"],
                    "description": asset["description"],
                    "estimated_arrival": intersected_step["step_label"],
                    "estimated_timestamp": intersected_step["timestamp"],
                    "severity": impact_severity,
                    "distance_to_core_km": round(min_dist_to_slick, 2) if min_dist_to_slick != float("inf") else None,
                    "geojson": self._asset_geojson(asset)
                })
            else:
                # Potential low/monitoring risk
                safe_dist = round(min_dist_to_slick, 2) if math.isfinite(min_dist_to_slick) else None
                impacts.append({
                    "asset_id": asset["id"],
                    "asset_name": asset["name"],
                    "asset_type": asset["asset_type"],
                    "vulnerability_index": asset["vulnerability_index"],
                    "description": asset["description"],
                    "estimated_arrival": "NO_IMPACT_PREDICTED_48H",
                    "estimated_timestamp": None,
                    "severity": "LOW",
                    "distance_to_core_km": safe_dist,
                    "geojson": self._asset_geojson(asset)
                })
                
        # Sort so highest risk / earliest arrival appears first
        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        impacts.sort(key=lambda x: severity_rank.get(x["severity"], 4))
        return impacts

    def _asset_geojson(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """Creates circular polygon GeoJSON for the asset area."""
        c_lat = asset["center_lat"]
        c_lon = asset["center_lon"]
        rad_km = asset["radius_km"]
        
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * math.cos(math.radians(c_lat))
        
        coords = []
        for deg in range(0, 360, 20):
            rad = math.radians(deg)
            d_lat = (rad_km * 1000.0 * math.cos(rad)) / m_per_deg_lat
            d_lon = (rad_km * 1000.0 * math.sin(rad)) / m_per_deg_lon
            coords.append([round(c_lon + d_lon, 6), round(c_lat + d_lat, 6)])
        coords.append(coords[0])
        
        return {
            "type": "Feature",
            "properties": {
                "id": asset["id"],
                "name": asset["name"],
                "asset_type": asset["asset_type"],
                "vulnerability": asset["vulnerability_index"]
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }

sensitive_impact_service = SensitiveImpactService()
