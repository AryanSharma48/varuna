import numpy as np
from services.characterisation.morphology import characterisation_service

def test_characterisation_linear_slick():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[45:55, 20:80] = 1 # Horizontal linear strip
    
    res = characterisation_service.characterisation_from_mask(
        binary_mask=mask,
        pixel_size_m=50.0,
        center_lat=18.92,
        center_lon=72.83
    )
    
    assert res["area_km2"] > 0.0
    assert res["length_km"] > res["width_km"]
    assert res["aspect_ratio"] >= 2.0
    assert res["morphology_type"] in ("LINEAR_SLICK", "FEATHERED_PLUME")
    assert "geojson" in res
    assert res["geojson"]["geometry"]["type"] == "Polygon"
