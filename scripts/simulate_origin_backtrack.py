import os
import json
import numpy as np
from datetime import datetime, timedelta
from opendrift.models.openoil import OpenOil
from opendrift.readers import reader_netCDF_CF_generic
from scipy.spatial import ConvexHull

def convex_hull_geojson(lons_arr, lats_arr, label, hours):
    points = np.column_stack((lons_arr, lats_arr))
    if len(points) < 4:
        return None
    try:
        hull = ConvexHull(points)
        hull_pts = points[hull.vertices]
        hull_pts = np.vstack((hull_pts, hull_pts[0]))  # close ring
        return {
            "type": "Feature",
            "properties": {
                "name": label,
                "hours_backtracked": hours
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [hull_pts.tolist()]
            }
        }
    except Exception as e:
        print(f"ConvexHull error for {label}: {e}")
        return None

def main():
    base_dir = "demo/incidents/incident_001"
    env_dir = os.path.join(base_dir, "environment")
    derived_dir = os.path.join(base_dir, "derived")

    # 1. Initialize OpenOil model
    o = OpenOil(loglevel=20)

    # 2. Add Readers
    currents_file = os.path.join(env_dir, "currents.nc")
    winds_file = os.path.join(env_dir, "winds.nc")

    reader_currents = reader_netCDF_CF_generic.Reader(
        currents_file,
        standard_name_mapping={
            'eastward_sea_water_velocity': 'x_sea_water_velocity',
            'northward_sea_water_velocity': 'y_sea_water_velocity'
        }
    )
    reader_winds = reader_netCDF_CF_generic.Reader(winds_file)
    o.add_reader([reader_currents, reader_winds])

    # 3. Load the user-traced spill polygon
    spill_file = os.path.join(derived_dir, "custom_user_spill.geojson")
    with open(spill_file) as f:
        spill_data = json.load(f)

    coords = spill_data["geometry"]["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    end_time = datetime(2019, 6, 10, 15, 48, 13)

    # 4. Seed 1000 particles within the polygon
    o.seed_within_polygon(lons, lats, number=1000, time=end_time)

    # 5. Run backward simulation 48 hours, output every 30 min
    print("Running OpenDrift reverse simulation (48h backward)...")
    o.run(
        duration=timedelta(hours=48),
        time_step=timedelta(minutes=-15),
        time_step_output=timedelta(minutes=30)
    )

    # 6. Extract full trajectory data
    print("Extracting particle trajectories...")
    # OpenDrift get_property returns shape (n_timesteps, n_particles)
    lon_raw = o.get_property('lon')[0].values   # (n_timesteps, n_particles)
    lat_raw = o.get_property('lat')[0].values
    status_raw = o.get_property('status')[0].values
    times_raw = o.get_time_array()[0]       # list/array of datetimes

    # Transpose to (n_particles, n_timesteps) for easier per-particle iteration
    lon = lon_raw.T   # now (n_particles, n_timesteps)
    lat = lat_raw.T
    status = status_raw.T

    n_particles, n_timesteps = lon.shape
    print(f"Particles: {n_particles}, Timesteps: {n_timesteps}")

    # Simulation is backward: index 0 = observed time (T=0), index N = T-12h
    # Step interval is 30 min output steps per hour (2/hr)
    steps_per_hour = 2  # 30-min output steps per hour
    
    snapshot_hours = [1, 6, 12, 24, 48]
    snapshot_indices = {h: min(h * steps_per_hour, n_timesteps - 1) for h in snapshot_hours}
    
    print(f"Snapshot indices: {snapshot_indices}")

    # ---- 7. Export per-timestamp slice GeoJSONs (particle endpoint positions) ----
    snapshot_data = {}
    for hours, t_idx in snapshot_indices.items():
        pts_lons = lon[:, t_idx]
        pts_lats = lat[:, t_idx]
        active = status[:, t_idx] == 0

        active_lons = pts_lons[active]
        active_lats = pts_lats[active]

        # Point cloud
        point_features = []
        for i in range(len(active_lons)):
            point_features.append({
                "type": "Feature",
                "properties": {"particle_id": int(np.where(active)[0][i]), "hours_back": hours},
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(active_lons[i]), float(active_lats[i])]
                }
            })

        # Convex hull corridor
        hull_feat = convex_hull_geojson(active_lons, active_lats, f"Probable Origin at T-{hours}h", hours)

        snapshot_data[str(hours)] = {
            "hours": hours,
            "t_index": t_idx,
            "active_particles": int(np.sum(active)),
            "centroid": {
                "lon": float(np.mean(active_lons)),
                "lat": float(np.mean(active_lats))
            },
            "point_cloud": {
                "type": "FeatureCollection",
                "features": point_features
            },
            "hull": hull_feat
        }
        print(f"  T-{hours}h: {np.sum(active)} active particles, centroid @ {np.mean(active_lons):.4f}E {np.mean(active_lats):.4f}N")

    # Write snapshots
    with open(os.path.join(derived_dir, "backtrack_snapshots.json"), "w") as f:
        json.dump(snapshot_data, f)
    print("Wrote backtrack_snapshots.json")

    # ---- 8. Full-trajectory LineStrings (full 48h, truncated per particle) ----
    traj_features = []
    for p in range(n_particles):
        line_coords = []
        for t_idx in range(n_timesteps):
            if status[p, t_idx] == 0:
                line_coords.append([float(lon[p, t_idx]), float(lat[p, t_idx])])
        if len(line_coords) > 1:
            traj_features.append({
                "type": "Feature",
                "properties": {"particle_id": p},
                "geometry": {"type": "LineString", "coordinates": line_coords}
            })

    with open(os.path.join(derived_dir, "backtrack_particles.geojson"), "w") as f:
        json.dump({"type": "FeatureCollection", "features": traj_features}, f)
    print(f"Wrote backtrack_particles.geojson ({len(traj_features)} trajectories)")

    # ---- 9. Use 48h hull as the primary origin corridor ----
    hull_primary = snapshot_data["48"]["hull"]
    if hull_primary:
        with open(os.path.join(derived_dir, "origin_corridor.geojson"), "w") as f:
            json.dump(hull_primary, f)
        print("Wrote origin_corridor.geojson (48h hull)")

    # ---- 10. Summary ----
    summary = {
        "observed_spill_centroid": {"lat": float(np.mean(lats)), "lon": float(np.mean(lons))},
        "satellite_acquisition_time": end_time.isoformat() + "Z",
        "backtrack_duration_hours": 48,
        "number_of_particles": n_particles,
        "wind_data_source": "ERA5 (CDS API)",
        "current_data_source": "Copernicus Mediterranean Reanalysis",
        "simulation_timestep_minutes": 15,
        "output_step_minutes": 30,
        "n_timesteps": n_timesteps,
        "snapshots": {
            str(h): {
                "hours_back": h,
                "centroid": snapshot_data[str(h)]["centroid"],
                "active_particles": snapshot_data[str(h)]["active_particles"]
            }
            for h in snapshot_hours
        },
        "earliest_backtracked_time": str(times_raw[-1]) + "Z",
        "latest_backtracked_time": str(times_raw[0]) + "Z"
    }
    with open(os.path.join(derived_dir, "backtrack_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("OpenDrift reverse simulation complete. All GeoJSON outputs generated.")


if __name__ == "__main__":
    main()
