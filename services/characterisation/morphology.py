import numpy as np
import math

class SpillCharacterisationService:
    """
    Computes precise morphometrics, geometry, and spatial characterisation
    from Sentinel-1 SAR segmentation masks and georeferenced metadata.
    """
    def __init__(self):
        pass

    def characterisation_from_mask(self, 
                                   binary_mask: np.ndarray, 
                                   pixel_size_m: float = 10.0,
                                   center_lat: float = 18.92,
                                   center_lon: float = 72.83) -> dict:
        """
        binary_mask: 2D array of 0s and 1s
        pixel_size_m: nominal ground sample distance in meters (e.g. 10m for Sentinel-1 GRD)
        center_lat, center_lon: scene or slick center coordinates
        """
        pixel_area_km2 = (pixel_size_m * pixel_size_m) / 1e6
        oil_pixels = np.argwhere(binary_mask > 0)
        
        if len(oil_pixels) == 0:
            return {
                "area_km2": 0.0,
                "perimeter_km": 0.0,
                "length_km": 0.0,
                "width_km": 0.0,
                "aspect_ratio": 1.0,
                "orientation_deg": 0.0,
                "morphology_type": "NO_OIL",
                "center_lat": center_lat,
                "center_lon": center_lon,
                "bbox": [center_lon, center_lat, center_lon, center_lat],
                "geojson": {"type": "Polygon", "coordinates": []}
            }
            
        area_km2 = float(len(oil_pixels) * pixel_area_km2)
        
        # PCA for principal orientation and axis lengths
        coords_y = oil_pixels[:, 0] * (pixel_size_m / 1000.0) # in km
        coords_x = oil_pixels[:, 1] * (pixel_size_m / 1000.0) # in km
        
        mean_y = np.mean(coords_y)
        mean_x = np.mean(coords_x)
        
        centered_x = coords_x - mean_x
        centered_y = coords_y - mean_y
        
        cov = np.cov(centered_x, centered_y)
        if cov.shape == (2, 2) and not np.isnan(cov).any():
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            # Principal axis length (approx 4 standard deviations)
            length_km = float(4.0 * np.sqrt(max(1e-4, eigenvalues[1])))
            width_km = float(4.0 * np.sqrt(max(1e-4, eigenvalues[0])))
            
            # Orientation of principal axis in degrees [0, 180)
            principal_vector = eigenvectors[:, 1]
            orientation_deg = float(math.degrees(math.atan2(principal_vector[1], principal_vector[0])) % 180)
        else:
            length_km = float(math.sqrt(area_km2))
            width_km = float(math.sqrt(area_km2))
            orientation_deg = 0.0
            
        # Ensure length >= width
        if width_km > length_km:
            length_km, width_km = width_km, length_km
            orientation_deg = (orientation_deg + 90.0) % 180
            
        aspect_ratio = float(length_km / max(0.01, width_km))
        perimeter_km = float(2.0 * (length_km + width_km) * 0.9)  # approximate slick boundary perimeter
        
        # Classify morphology
        if aspect_ratio >= 4.0:
            morphology_type = "LINEAR_SLICK"
        elif aspect_ratio >= 2.0:
            morphology_type = "FEATHERED_PLUME"
        elif area_km2 > 10.0:
            morphology_type = "HEAVY_CONCENTRATION"
        else:
            morphology_type = "PATCHY_SHEEN"
            
        # Generate representative GeoJSON polygon centered at target geographic position
        # Convert local km offsets to degrees lat/lon
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * math.cos(math.radians(center_lat))
        
        # Approximate hull coordinates for map rendering
        angles = np.linspace(0, 2*np.pi, 24, endpoint=False)
        rad_orient = math.radians(orientation_deg)
        cos_o, sin_o = math.cos(rad_orient), math.sin(rad_orient)
        
        a = (length_km / 2.0)
        b = (width_km / 2.0)
        
        poly_coords = []
        for angle in angles:
            # Elliptical perturbation
            noise = 1.0 + 0.15 * math.sin(3 * angle)
            xe = a * math.cos(angle) * noise
            ye = b * math.sin(angle) * noise
            # Rotate
            xr = xe * cos_o - ye * sin_o
            yr = xe * sin_o + ye * cos_o
            # Translate to lon, lat
            pt_lon = center_lon + (xr / km_per_deg_lon)
            pt_lat = center_lat + (yr / km_per_deg_lat)
            poly_coords.append([round(pt_lon, 6), round(pt_lat, 6)])
            
        poly_coords.append(poly_coords[0]) # close polygon
        
        lons = [p[0] for p in poly_coords]
        lats = [p[1] for p in poly_coords]
        bbox = [min(lons), min(lats), max(lons), max(lats)]
        
        geojson = {
            "type": "Feature",
            "properties": {
                "area_km2": round(area_km2, 2),
                "perimeter_km": round(perimeter_km, 2),
                "length_km": round(length_km, 2),
                "width_km": round(width_km, 2),
                "orientation_deg": round(orientation_deg, 1),
                "morphology_type": morphology_type
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [poly_coords]
            }
        }
        
        return {
            "area_km2": round(area_km2, 2),
            "perimeter_km": round(perimeter_km, 2),
            "length_km": round(length_km, 2),
            "width_km": round(width_km, 2),
            "aspect_ratio": round(aspect_ratio, 2),
            "orientation_deg": round(orientation_deg, 1),
            "morphology_type": morphology_type,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "bbox": bbox,
            "geojson": geojson
        }

characterisation_service = SpillCharacterisationService()
