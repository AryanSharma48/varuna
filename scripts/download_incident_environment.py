import os
import json
import cdsapi
import copernicusmarine
from datetime import datetime, timedelta

def download_environment():
    base_dir = "demo/incidents/incident_001/environment"
    os.makedirs(base_dir, exist_ok=True)
    
    # 1. Bounding Box & Time window
    # Polygon center: ~ 31.92N, 32.89E
    # Let's use a generous buffer for a 48 hour drift (up to 1.5 degrees)
    lon_min, lon_max = 31.0, 35.0
    lat_min, lat_max = 30.0, 34.0
    
    end_time_actual = datetime(2019, 6, 10, 15, 48, 13)
    start_time = datetime(2019, 6, 8, 0, 0, 0)
    end_time = datetime(2019, 6, 13, 0, 0, 0)
    
    days = ["08", "09", "10", "11", "12", "13"]
    times = [f"{str(h).zfill(2)}:00" for h in range(24)]

    winds_path = os.path.join(base_dir, "winds.nc")
    currents_path = os.path.join(base_dir, "currents.nc")
    metadata_path = os.path.join(base_dir, "metadata.json")
    
    # 2. Download ERA5 Winds
    if not os.path.exists(winds_path):
        print("Downloading ERA5 Wind data from CDS API...")
        c = cdsapi.Client()
        c.retrieve(
            'reanalysis-era5-single-levels',
            {
                'product_type': 'reanalysis',
                'format': 'netcdf',
                'variable': [
                    '10m_u_component_of_wind', '10m_v_component_of_wind',
                ],
                'year': '2019',
                'month': '06',
                'day': days,
                'time': times,
                'area': [
                    lat_max, lon_min, lat_min, lon_max,
                ],
            },
            winds_path
        )
    else:
        print("Winds already downloaded.")

    # 3. Download Mediterranean Currents
    if not os.path.exists(currents_path):
        print("Downloading Copernicus Mediterranean Currents...")
        copernicusmarine.subset(
            dataset_id="cmems_mod_med_phy-cur_my_4.2km_PT1H-m",
            variables=["uo", "vo"],
            start_datetime=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            end_datetime=end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            minimum_longitude=lon_min,
            maximum_longitude=lon_max,
            minimum_latitude=lat_min,
            maximum_latitude=lat_max,
            output_filename=currents_path,
            force_download=True
        )
    else:
        print("Currents already downloaded.")
        
    # 4. Save metadata
    metadata = {
        "source": "Copernicus Marine & CDS API",
        "currents_product_id": "cmems_mod_med_phy-cur_my_4.2km_PT1H-m",
        "winds_product_id": "reanalysis-era5-single-levels",
        "retrieval_timestamp": datetime.utcnow().isoformat() + "Z",
        "spatial_bounds": {
            "lon_min": lon_min,
            "lon_max": lon_max,
            "lat_min": lat_min,
            "lat_max": lat_max
        },
        "temporal_bounds": {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z"
        },
        "variables": {
            "currents": ["uo", "vo"],
            "winds": ["10m_u_component_of_wind", "10m_v_component_of_wind"]
        },
        "resolution": "Hourly",
        "units": "m/s"
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("Environment data downloaded and cached successfully!")

if __name__ == "__main__":
    download_environment()
