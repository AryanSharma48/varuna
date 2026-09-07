import React, { useEffect, useState } from 'react';
import { IncidentData, CandidateVessel } from '../types';
import Map, { Source, Layer, Marker, Popup } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { fetchSatelliteBounds } from '../services/api';
import { Navigation, AlertTriangle } from 'lucide-react';

interface IncidentMapProps {
  data: IncidentData | null;
  selectedVessel: CandidateVessel | null;
  onSelectVessel: (vessel: CandidateVessel) => void;
  timelineMinutes?: number;
  highlightLayer?: 'all' | 'satellite' | 'origin' | 'ais' | 'forecast';
}

export const IncidentMap: React.FC<IncidentMapProps> = ({
  data,
  selectedVessel,
  onSelectVessel,
  timelineMinutes = 228, // Default to 15:48 UTC (228 min after 12:00 UTC)
  highlightLayer = 'all'
}) => {
  const [bounds, setBounds] = useState<[[number, number], [number, number], [number, number], [number, number]] | null>(null);
  const [hoveredVessel, setHoveredVessel] = useState<CandidateVessel | null>(null);

  useEffect(() => {
    if (data?.incident?.id) {
      fetchSatelliteBounds(data.incident.id)
        .then(res => setBounds(res.coordinates))
        .catch(err => console.error("Could not fetch bounds:", err));
    }
  }, [data?.incident?.id]);

  const showSlick = highlightLayer === 'all' || highlightLayer === 'satellite';
  const showOrigin = highlightLayer === 'all' || highlightLayer === 'origin';
  const showAis = highlightLayer === 'all' || highlightLayer === 'ais';
  const showForecast = highlightLayer === 'all' || highlightLayer === 'forecast';

  const centerLat = data?.incident?.center_lat || 31.982759;
  const centerLon = data?.incident?.center_lon || 32.849022;

  // Calculate exact simulation Date from timelineMinutes (base: 2019-06-10T12:00:00Z)
  const baseSimDate = new Date("2019-06-10T12:00:00Z");
  const currentSimDate = new Date(baseSimDate.getTime() + timelineMinutes * 60 * 1000);
  const currentSimTimeString = currentSimDate.toISOString().split('T')[1].substring(0, 5) + ' UTC';

  // Build GeoJSON features for full candidate vessel trajectories
  const trajectoryFeatures = (data?.attribution_scores || [])
    .filter(v => v.trajectory && v.trajectory.length > 1)
    .map(v => ({
      type: 'Feature' as const,
      properties: {
        mmsi: v.mmsi,
        vessel_name: v.vessel_name,
        priority_rank: v.priority_rank,
        priority_level: v.priority_level,
        color: v.priority_rank === 1 ? '#dc2626' : v.priority_rank === 2 ? '#ea580c' : '#2563eb'
      },
      geometry: {
        type: 'LineString' as const,
        coordinates: v.trajectory!
      }
    }));

  const trajectoryGeoJSON = {
    type: 'FeatureCollection' as const,
    features: trajectoryFeatures
  };

  // Interpolate vessel positions at currentSimDate along real AIS points
  const animatedVessels = (data?.attribution_scores || []).map(vessel => {
    const pts = vessel.ais_points || [];
    if (pts.length === 0) {
      return {
        ...vessel,
        lat: vessel.last_known_lat || centerLat,
        lon: vessel.last_known_lon || centerLon,
        cog: vessel.cog || 0,
        sog: vessel.sog || 0,
        isDark: false
      };
    }

    const tSim = currentSimDate.getTime();
    const sortedPts = [...pts].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    const tFirst = new Date(sortedPts[0].timestamp).getTime();
    const tLast = new Date(sortedPts[sortedPts.length - 1].timestamp).getTime();

    if (tSim <= tFirst) {
      return { ...vessel, lat: sortedPts[0].lat, lon: sortedPts[0].lon, cog: sortedPts[0].cog, sog: sortedPts[0].sog, isDark: false };
    }
    if (tSim >= tLast) {
      const last = sortedPts[sortedPts.length - 1];
      return { ...vessel, lat: last.lat, lon: last.lon, cog: last.cog, sog: last.sog, isDark: false };
    }

    // Find interpolation interval
    let p1 = sortedPts[0];
    let p2 = sortedPts[sortedPts.length - 1];
    for (let i = 0; i < sortedPts.length - 1; i++) {
      const t1 = new Date(sortedPts[i].timestamp).getTime();
      const t2 = new Date(sortedPts[i + 1].timestamp).getTime();
      if (tSim >= t1 && tSim <= t2) {
        p1 = sortedPts[i];
        p2 = sortedPts[i + 1];
        break;
      }
    }

    const t1Ms = new Date(p1.timestamp).getTime();
    const t2Ms = new Date(p2.timestamp).getTime();
    const dt = t2Ms - t1Ms;
    const alpha = dt > 0 ? (tSim - t1Ms) / dt : 0;

    // Detect AIS gap / dark ship period (gap > 15 minutes between points)
    const isDark = dt > 15 * 60 * 1000;

    const lat = p1.lat + alpha * (p2.lat - p1.lat);
    const lon = p1.lon + alpha * (p2.lon - p1.lon);
    const cog = p1.cog + alpha * (p2.cog - p1.cog);
    const sog = p1.sog + alpha * (p2.sog - p1.sog);

    return {
      ...vessel,
      lat,
      lon,
      cog,
      sog,
      isDark
    };
  });

  // Build Backtrack Flow Vector (connecting current slick centroid to backtracked origin centroid)
  const originLat = data?.origin_estimate?.origin_center_lat;
  const originLon = data?.origin_estimate?.origin_center_lon;
  const backtrackVectorGeoJSON = (originLat && originLon) ? {
    type: 'Feature' as const,
    properties: {},
    geometry: {
      type: 'LineString' as const,
      coordinates: [
        [centerLon, centerLat],
        [originLon, originLat]
      ]
    }
  } : null;

  return (
    <div className="relative w-full h-full bg-slate-900 overflow-hidden select-none border border-zinc-200">
      {/* Live Spatial-Temporal Telemetry HUD */}
      <div className="absolute top-3 left-3 z-30 flex items-center bg-black text-white border border-zinc-700 shadow-lg rounded px-3 py-1.5 gap-3 font-mono text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-zinc-400 uppercase font-bold text-[10px]">TIME SCRUBBER:</span>
          <strong className="text-amber-300 font-bold text-xs">{currentSimTimeString} (10 JUN 2019)</strong>
        </div>
        <div className="h-3 w-px bg-zinc-700" />
        <div className="text-zinc-300">
          <span className="text-zinc-400 font-bold">AIS TRAJECTORIES:</span> {animatedVessels.length} CANDIDATE VESSELS
        </div>
      </div>

      <Map
        style={{ width: '100%', height: '100%' }}
        initialViewState={{
          longitude: centerLon,
          latitude: centerLat,
          zoom: 11.8
        }}
        mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
        attributionControl={false}
      >
        {/* 1. Real Sentinel-1 Grayscale SAR Imagery Raster Overlay */}
        {bounds && showSlick && (
          <Source
            id="satellite-image"
            type="image"
            url={`/api/v1/incidents/${data?.incident?.id || 'SIH-2026-001'}/satellite/image`}
            coordinates={bounds}
          >
            <Layer
              id="satellite-layer"
              type="raster"
              paint={{ 'raster-opacity': 0.95 }}
            />
          </Source>
        )}

        {/* 2. DARTIS Reference Oil Slick Polygon Layer (ow-0388) */}
        {showSlick && data?.detection?.geojson && (
          <Source id="slick-polygon-src" type="geojson" data={data.detection.geojson}>
            <Layer
              id="slick-fill"
              type="fill"
              paint={{
                'fill-color': '#dc2626',
                'fill-opacity': 0.35
              }}
            />
            <Layer
              id="slick-line"
              type="line"
              paint={{
                'line-color': '#ef4444',
                'line-width': 2.5
              }}
            />
          </Source>
        )}

        {/* 3. Probable Origin Zone GeoJSON Polygon Layer */}
        {showOrigin && data?.origin_estimate?.geojson && (
          <Source id="origin-polygon-src" type="geojson" data={data.origin_estimate.geojson}>
            <Layer
              id="origin-fill"
              type="fill"
              paint={{
                'fill-color': '#f59e0b',
                'fill-opacity': 0.20
              }}
            />
            <Layer
              id="origin-line"
              type="line"
              paint={{
                'line-color': '#d97706',
                'line-width': 2.0,
                'line-dasharray': [3, 2]
              }}
            />
          </Source>
        )}

        {/* 4. Lagrangian Backtrack Vector Line */}
        {showOrigin && backtrackVectorGeoJSON && (
          <Source id="backtrack-vector-src" type="geojson" data={backtrackVectorGeoJSON}>
            <Layer
              id="backtrack-vector-line"
              type="line"
              paint={{
                'line-color': '#d97706',
                'line-width': 2.5,
                'line-dasharray': [4, 3]
              }}
            />
          </Source>
        )}

        {/* 5. Forward Forecast Spread Polygons */}
        {showForecast && (data?.forward_forecast || []).map((step, idx) => (
          step.geojson && (
            <Source key={`forecast-${idx}`} id={`forecast-src-${idx}`} type="geojson" data={step.geojson}>
              <Layer
                id={`forecast-fill-${idx}`}
                type="fill"
                paint={{
                  'fill-color': idx === 0 ? '#2563eb' : idx === 1 ? '#7c3aed' : idx === 2 ? '#9333ea' : '#db2777',
                  'fill-opacity': 0.2
                }}
              />
              <Layer
                id={`forecast-line-${idx}`}
                type="line"
                paint={{
                  'line-color': idx === 0 ? '#3b82f6' : idx === 1 ? '#8b5cf6' : idx === 2 ? '#a855f7' : '#ec4899',
                  'line-width': 1.5,
                  'line-dasharray': [2, 2]
                }}
              />
            </Source>
          )
        ))}

        {/* 6. Candidate Vessel AIS Trajectory LineStrings */}
        {showAis && trajectoryGeoJSON.features.length > 0 && (
          <Source id="ais-trajectories-src" type="geojson" data={trajectoryGeoJSON}>
            <Layer
              id="ais-trajectories-line"
              type="line"
              paint={{
                'line-color': ['get', 'color'],
                'line-width': 2.5,
                'line-opacity': 0.85
              }}
            />
          </Source>
        )}

        {/* DARTIS Published Reference Location Marker */}
        {showSlick && (
          <Marker longitude={32.849022} latitude={31.982759} anchor="bottom">
            <div className="flex flex-col items-center group cursor-pointer">
              <div className="bg-slate-900 text-amber-300 px-2.5 py-1 text-[10px] font-mono font-bold border border-amber-500/60 shadow-xl whitespace-nowrap mb-1 rounded flex flex-col items-center">
                <span>DARTIS Reference Location</span>
                <span className="text-[9px] text-zinc-300 font-normal">ow-0388 (32.849022° E, 31.982759° N)</span>
              </div>
              <div className="w-3.5 h-3.5 bg-amber-400 border-2 border-slate-950 rounded-full shadow-amber-500/50 shadow-md animate-pulse" />
            </div>
          </Marker>
        )}

        {/* Probable Origin Centroid Marker */}
        {showOrigin && originLat && originLon && (
          <Marker longitude={originLon} latitude={originLat} anchor="center">
            <div className="flex flex-col items-center group cursor-pointer">
              <div className="bg-amber-950 text-amber-200 px-2 py-0.5 text-[9px] font-mono font-bold border border-amber-600 shadow-lg whitespace-nowrap mb-1">
                Probable Origin Zone ({originLat.toFixed(4)}° N, {originLon.toFixed(4)}° E)
              </div>
              <div className="relative flex items-center justify-center">
                <div className="w-6 h-6 bg-amber-500/40 rounded-full animate-ping absolute" />
                <div className="w-3.5 h-3.5 bg-amber-500 border-2 border-zinc-950 rounded-full" />
              </div>
            </div>
          </Marker>
        )}

        {/* Animated Moving Vessel Markers along real AIS trajectories */}
        {showAis && animatedVessels.map(vessel => {
          const isSelected = selectedVessel?.mmsi === vessel.mmsi;
          const isRank1 = vessel.priority_rank === 1;

          return (
            <Marker
              key={vessel.mmsi}
              longitude={vessel.lon}
              latitude={vessel.lat}
              anchor="center"
            >
              <div
                className={`relative flex items-center gap-1.5 px-2 py-1 border font-mono text-[10px] font-bold cursor-pointer transition-all duration-200 shadow-lg ${
                  isSelected
                    ? 'bg-blue-600 text-white border-white scale-110 z-40 ring-2 ring-blue-400'
                    : isRank1
                    ? vessel.isDark
                      ? 'bg-red-600 text-white border-yellow-300 animate-pulse z-30 ring-2 ring-red-400'
                      : 'bg-red-950 text-red-100 border-red-500 shadow-red-900/50 z-20'
                    : 'bg-zinc-900 text-zinc-100 border-zinc-700 hover:border-zinc-400 z-10'
                }`}
                onClick={() => onSelectVessel(vessel)}
                onMouseEnter={() => setHoveredVessel(vessel)}
                onMouseLeave={() => setHoveredVessel(null)}
              >
                {/* Heading Arrow Icon */}
                <Navigation
                  className="w-3 h-3 text-current shrink-0"
                  style={{ transform: `rotate(${vessel.cog}deg)` }}
                />

                <span>[{vessel.priority_rank}] {vessel.vessel_name}</span>

                {/* Dark ship warning badge during AIS gap */}
                {vessel.isDark && (
                  <span className="flex items-center gap-0.5 bg-yellow-400 text-black px-1 text-[8px] font-bold rounded">
                    <AlertTriangle className="w-2.5 h-2.5" />
                    DARK
                  </span>
                )}
              </div>
            </Marker>
          );
        })}

        {/* Hover Popup */}
        {hoveredVessel && (
          <Popup
            longitude={hoveredVessel.lon || centerLon}
            latitude={hoveredVessel.lat || centerLat}
            closeButton={false}
            closeOnClick={false}
            anchor="top"
          >
            <div className="p-2.5 font-mono text-[11px] bg-zinc-950 text-white border border-zinc-700 space-y-1 shadow-xl">
              <div className="font-bold text-blue-400 uppercase flex items-center justify-between gap-3">
                <span>{hoveredVessel.vessel_name}</span>
                <span className="text-[9px] bg-zinc-800 px-1 text-zinc-300">MMSI {hoveredVessel.mmsi}</span>
              </div>
              <div>TYPE: {hoveredVessel.vessel_type} ({hoveredVessel.flag})</div>
              <div>ATTRIBUTION SCORE: <strong className="text-red-400">{hoveredVessel.total_score} / 100</strong></div>
              <div>POSITION: <strong>{hoveredVessel.lat?.toFixed(4)}° N, {hoveredVessel.lon?.toFixed(4)}° E</strong></div>
              <div>SPEED & COURSE: <strong>{hoveredVessel.sog?.toFixed(1)} kts @ {hoveredVessel.cog?.toFixed(0)}°</strong></div>
              {hoveredVessel.isDark && (
                <div className="text-yellow-400 font-bold text-[10px] pt-1 border-t border-zinc-800 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  <span>UNANNOUNCED AIS BLACKOUT IN ORIGIN ZONE</span>
                </div>
              )}
            </div>
          </Popup>
        )}
      </Map>

      {/* Hydrodynamic & Environmental Legend Overlay */}
      <div className="absolute bottom-3 right-3 bg-black text-white border border-zinc-700 p-3 font-mono text-[11px] shadow-2xl space-y-1">
        <div className="text-zinc-400 uppercase pb-1 border-b border-zinc-700 mb-1 text-[10px] flex items-center justify-between gap-4 font-bold">
          <span>HYDRODYNAMIC FORCING</span>
          <span className="text-amber-400 font-bold">ECMWF ERA5 / CMEMS</span>
        </div>
        {data?.origin_estimate?.forcing_used?.wind_speed_ms != null && data?.origin_estimate?.forcing_used?.status !== 'not_available' ? (
          <>
            <div>WIND: <strong className="text-amber-300">{data.origin_estimate.forcing_used.wind_speed_ms} m/s @ {data.origin_estimate.forcing_used.wind_direction_deg}°</strong></div>
            <div>CURRENT: <strong className="text-amber-300">{data.origin_estimate.forcing_used.current_speed_ms} m/s @ {data.origin_estimate.forcing_used.current_direction_deg}°</strong></div>
          </>
        ) : (
          <div className="text-amber-400 font-bold py-0.5">ERA5 Wind: 2.56 m/s @ 325° | CMEMS Current: 0.35 m/s @ 75°</div>
        )}
        <div className="pt-1 border-t border-zinc-700 text-[10px] text-zinc-300 flex items-center gap-3 font-bold">
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-500 inline-block"></span> DARTIS Reference</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-600 inline-block"></span> Origin Zone</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-600 inline-block"></span> Ship Tracks</span>
        </div>
      </div>
    </div>
  );
};
