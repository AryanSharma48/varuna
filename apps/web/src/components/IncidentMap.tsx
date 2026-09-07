import React, { useEffect, useState, useMemo, useRef } from 'react';
import { IncidentData } from '../types';
import Map, { Source, Layer, Marker, MapRef } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { fetchSatelliteBounds, applyCustomSpillGeometry, revertSpillGeometry } from '../services/api';
import { 
  PenTool, 
  Check, 
  X, 
  RotateCcw, 
  Trash2, 
  Copy, 
  Download, 
  RefreshCw,
  Navigation,
  AlertTriangle
} from 'lucide-react';

interface IncidentMapProps {
  data: IncidentData | null;
  activeStage?: 'overview' | 'satellite' | 'origin' | 'ais' | 'attribution' | 'forecast';
  onIncidentUpdated?: (updatedData: IncidentData) => void;
}

export const IncidentMap: React.FC<IncidentMapProps> = ({ 
  data, 
  activeStage = 'overview',
  onIncidentUpdated 
}) => {
  const mapRef = useRef<MapRef>(null);
  const [bounds, setBounds] = useState<[[number, number], [number, number], [number, number], [number, number]] | null>(null);

  // Backtrack time selector
  const [backtrackHours, setBacktrackHours] = useState<1 | 6 | 12 | 24 | 48>(12);

  // Forecast time selector
  const [forecastHours, setForecastHours] = useState<6 | 12 | 24 | 48>(48);

  // Manual Polygon Drawing Tool States
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (data?.incident?.id) {
      fetchSatelliteBounds(data.incident.id)
        .then(res => {
          // Authoritative GCP-derived geolocation
          setBounds(res.coordinates as [[number, number], [number, number], [number, number], [number, number]]);
        })
        .catch(err => console.error("Could not fetch bounds:", err));
    }
  }, [data?.incident?.id]);

  // Coordinates
  const refLat = 31.982759;
  const refLon = 32.849022;

  const segLat = data?.incident?.center_lat || 32.006759;
  const segLon = data?.incident?.center_lon || 32.815022;

  // Whether user is using a custom manually traced polygon
  const isCustomTrace = data?.detection?.morphology_type === 'USER_DEFINED_SLICK' || 
                        data?.detection?.geojson?.properties?.source === 'user_manual_trace';

  // 1. Build GeoJSON for Segmented Spill Polygon
  const segmentedGeoJSON = useMemo(() => {
    if (data?.detection?.geojson) {
      return data.detection.geojson;
    }
    return null;
  }, [data]);

  // 2. Origin contour GeoJSON
  const originGeoJSON = data?.origin_estimate?.geojson || null;

  // 3. Backtrack snapshot GeoJSON (driven by selected hour)
  const snapshots = data?.backtrack_snapshots;
  const activeSnapshot = snapshots ? snapshots[String(backtrackHours)] : null;
  const originCorridorGeoJSON = activeSnapshot?.hull || data?.origin_corridor || originGeoJSON;
  // Full trajectory lines for the selected time window (truncated to selected step)
  const backtrackParticlesGeoJSON = useMemo(() => {
    const particles = data?.backtrack_particles;
    if (!particles) return null;
    if (!snapshots) return particles;
    const snapshot = snapshots[String(backtrackHours)];
    if (!snapshot) return particles;
    const tIdx = snapshot.t_index; // number of timesteps to include
    // Slice each trajectory to only show first tIdx+1 points (from observed time → selected backtrack time)
    return {
      ...particles,
      features: particles.features.map((f: any) => ({
        ...f,
        geometry: {
          ...f.geometry,
          coordinates: f.geometry.coordinates.slice(0, tIdx + 1)
        }
      }))
    };
  }, [data?.backtrack_particles, snapshots, backtrackHours]);

  // 4. Forward spread snapshot GeoJSON (driven by selected forecast hour)
  const forwardSnapshots = data?.forward_snapshots;
  const activeForwardSnapshot = forwardSnapshots ? forwardSnapshots[String(forecastHours)] : null;
  const forwardCorridorGeoJSON = activeForwardSnapshot?.hull || data?.forward_corridor || null;

  // Full trajectory lines for forward simulation (truncated to selected forecast step)
  const forwardParticlesGeoJSON = useMemo(() => {
    const particles = data?.forward_particles;
    if (!particles) return null;
    if (!forwardSnapshots) return particles;
    const snapshot = forwardSnapshots[String(forecastHours)];
    if (!snapshot) return particles;
    const tIdx = snapshot.t_index; // number of timesteps to include
    return {
      ...particles,
      features: particles.features.map((f: any) => ({
        ...f,
        geometry: {
          ...f.geometry,
          coordinates: f.geometry.coordinates.slice(0, tIdx + 1)
        }
      }))
    };
  }, [data?.forward_particles, forwardSnapshots, forecastHours]);

  const forwardPointCloudGeoJSON = activeForwardSnapshot?.point_cloud || null;

  // 3. Real-time Geodesic Planar Area Calculation for drawn points
  const liveAreaKm2 = useMemo(() => {
    if (drawnPoints.length < 3) return 0;
    const avgLatRad = (drawnPoints.reduce((s, p) => s + p[1], 0) / drawnPoints.length) * (Math.PI / 180);
    const mPerDegLat = 111132.95;
    const mPerDegLon = 111132.95 * Math.cos(avgLatRad);
    let areaM2 = 0;
    for (let i = 0; i < drawnPoints.length; i++) {
      const j = (i + 1) % drawnPoints.length;
      const xi = drawnPoints[i][0] * mPerDegLon;
      const yi = drawnPoints[i][1] * mPerDegLat;
      const xj = drawnPoints[j][0] * mPerDegLon;
      const yj = drawnPoints[j][1] * mPerDegLat;
      areaM2 += (xi * yj - xj * yi);
    }
    return Math.abs(areaM2) / 2.0 / 1e6;
  }, [drawnPoints]);

  // 4. Drawing LineString GeoJSON (live preview)
  const drawnLineGeoJSON = useMemo(() => {
    if (drawnPoints.length < 2) return null;
    return {
      type: 'Feature' as const,
      properties: {},
      geometry: {
        type: 'LineString' as const,
        coordinates: drawnPoints
      }
    };
  }, [drawnPoints]);

  // 5. Drawing Polygon GeoJSON (live preview when >= 3 points)
  const drawnPolyGeoJSON = useMemo(() => {
    if (drawnPoints.length < 3) return null;
    return {
      type: 'Feature' as const,
      properties: {},
      geometry: {
        type: 'Polygon' as const,
        coordinates: [[...drawnPoints, drawnPoints[0]]]
      }
    };
  }, [drawnPoints]);

  // Map Click Handler for Manual Tracing
  const handleMapClick = (e: any) => {
    if (!isDrawing) return;
    const lng = parseFloat(e.lngLat.lng.toFixed(6));
    const lat = parseFloat(e.lngLat.lat.toFixed(6));
    setDrawnPoints(prev => [...prev, [lng, lat]]);
  };

  // Undo last vertex
  const handleUndo = () => {
    setDrawnPoints(prev => prev.slice(0, -1));
  };

  // Clear all vertices
  const handleClear = () => {
    setDrawnPoints([]);
  };

  // Map Camera Transition
  useEffect(() => {
    if (!mapRef.current || !data) return;

    if (activeStage === 'forecast') {
      const step = data.forward_forecast?.find(s => s.horizon_hours === forecastHours);
      if (step) {
        mapRef.current.flyTo({
          center: [step.center_lon, step.center_lat],
          zoom: 10,
          duration: 1000,
          essential: true
        });
      }
    } else if (['satellite', 'origin', 'ais', 'attribution'].includes(activeStage)) {
      mapRef.current.flyTo({
        center: [segLon, segLat + 0.03],
        zoom: 11.2,
        duration: 1000,
        essential: true
      });
    } else {
      mapRef.current.flyTo({
        center: [refLon, refLat],
        zoom: 11.2,
        duration: 1000,
        essential: true
      });
    }
  }, [activeStage, forecastHours, data, segLon, segLat, refLon, refLat]);

  // Cancel drawing mode
  const handleCancel = () => {
    setIsDrawing(false);
    setDrawnPoints([]);
  };

  // Save & Apply Polygon
  const handleSavePolygon = async () => {
    if (drawnPoints.length < 3 || !data?.incident?.id) return;
    setIsSaving(true);
    try {
      const closed = [...drawnPoints, drawnPoints[0]];
      const lons = drawnPoints.map(p => p[0]);
      const lats = drawnPoints.map(p => p[1]);
      const c_lon = parseFloat((lons.reduce((a, b) => a + b, 0) / lons.length).toFixed(6));
      const c_lat = parseFloat((lats.reduce((a, b) => a + b, 0) / lats.length).toFixed(6));
      const finalArea = parseFloat(liveAreaKm2.toFixed(2));

      const geojson = {
        type: 'Feature',
        properties: {
          id: `CUSTOM-${data.incident.id}`,
          name: 'User-Traced Spill Area',
          source: 'user_manual_trace',
          center_lat: c_lat,
          center_lon: c_lon,
          area_km2: finalArea,
          updated_at: new Date().toISOString()
        },
        geometry: {
          type: 'Polygon',
          coordinates: [closed]
        }
      };

      // Expose globally for instant developer inspection
      (window as any).__LAST_DRAWN_SPILL_GEOJSON = geojson;
      console.log('MANUAL OIL SPILL POLYGON SAVED:', JSON.stringify(geojson, null, 2));

      const updated = await applyCustomSpillGeometry(data.incident.id, {
        geojson,
        area_km2: finalArea,
        center_lat: c_lat,
        center_lon: c_lon
      });

      if (onIncidentUpdated) {
        onIncidentUpdated(updated);
      }

      setIsDrawing(false);
      setDrawnPoints([]);
      setSaveMessage(`Custom Polygon Saved (${finalArea} km²)! Drift & AIS recalculated.`);
      setTimeout(() => setSaveMessage(null), 6000);
    } catch (err: any) {
      alert(`Error saving custom polygon: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Revert to original U-Net baseline
  const handleRevert = async () => {
    if (!data?.incident?.id) return;
    setIsSaving(true);
    try {
      const reverted = await revertSpillGeometry(data.incident.id);
      if (onIncidentUpdated) {
        onIncidentUpdated(reverted);
      }
      setSaveMessage('Reverted to original U-Net baseline.');
      setTimeout(() => setSaveMessage(null), 4000);
    } catch (err: any) {
      alert(`Error reverting: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Copy current active GeoJSON to clipboard
  const handleCopyGeoJSON = () => {
    const targetGeoJSON = data?.detection?.geojson || (window as any).__LAST_DRAWN_SPILL_GEOJSON;
    if (!targetGeoJSON) return;
    navigator.clipboard.writeText(JSON.stringify(targetGeoJSON, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  // Download GeoJSON file
  const handleDownloadGeoJSON = () => {
    const targetGeoJSON = data?.detection?.geojson || (window as any).__LAST_DRAWN_SPILL_GEOJSON;
    if (!targetGeoJSON) return;
    const blob = new Blob([JSON.stringify(targetGeoJSON, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `custom_spill_geometry_${data?.incident?.id || 'SIH-2026-001'}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none border border-zinc-800">
      {/* Live Spatial-Temporal Telemetry HUD - shown on AIS and attribution stages */}
      {['ais', 'attribution'].includes(activeStage) && (
        <div className="absolute top-3 left-3 z-30 flex items-center bg-black text-white border border-zinc-700 shadow-lg rounded px-3 py-1.5 gap-3 font-mono text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-zinc-400 uppercase font-bold text-[10px]">INCIDENT TIME:</span>
            <strong className="text-amber-300 font-bold text-xs">15:48 UTC (10 JUN 2019)</strong>
          </div>
          <div className="h-3 w-px bg-zinc-700" />
          <div className="text-zinc-300">
            <span className="text-zinc-400 font-bold">AIS TRAJECTORIES:</span> {(data?.attribution_scores || []).length} CANDIDATE VESSELS
          </div>
        </div>
      )}
      <Map
        ref={mapRef}
        style={{ width: '100%', height: '100%' }}
        cursor={isDrawing ? 'crosshair' : 'grab'}
        onClick={handleMapClick}
        initialViewState={{
          longitude: ['satellite', 'origin', 'ais', 'attribution', 'forecast'].includes(activeStage) ? segLon : refLon,
          latitude: (['satellite', 'origin', 'ais', 'attribution', 'forecast'].includes(activeStage) ? segLat : refLat) + 0.03,
          zoom: 11.2
        }}
        mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
        attributionControl={false}
      >
        {/* Real Sentinel-1 Grayscale SAR Imagery Raster Overlay */}
        {bounds && (
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

        {/* STAGE 2+: Real Segmented Spill Polygon (User-Drawn or Baseline) */}
        {activeStage !== 'overview' && segmentedGeoJSON && (
          <Source id="segmented-spill-src" type="geojson" data={segmentedGeoJSON}>
            <Layer
              id="segmented-spill-fill"
              type="fill"
              paint={{
                'fill-color': isCustomTrace ? '#06b6d4' : '#06b6d4',
                'fill-opacity': 0.40
              }}
            />
            <Layer
              id="segmented-spill-line"
              type="line"
              paint={{
                'line-color': '#22d3ee',
                'line-width': 2.5
              }}
            />
          </Source>
        )}

        {/* STAGE 3+: Origin Corridor (Convex Hull at selected backtrack time) */}
        {['origin', 'ais', 'attribution'].includes(activeStage) && originCorridorGeoJSON && (
          <Source id="origin-contour-src" type="geojson" data={originCorridorGeoJSON}>
            <Layer
              id="origin-contour-fill"
              type="fill"
              paint={{
                'fill-color': '#f59e0b',
                'fill-opacity': 0.10
              }}
            />
            <Layer
              id="origin-contour-line"
              type="line"
              paint={{
                'line-color': '#fbbf24',
                'line-width': 1.5,
                'line-dasharray': [4, 3]
              }}
            />
          </Source>
        )}

        {/* STAGE 3+: Backtrack Particle Trajectories */}
        {['origin', 'ais', 'attribution'].includes(activeStage) && backtrackParticlesGeoJSON && (
          <Source id="backtrack-particles-src" type="geojson" data={backtrackParticlesGeoJSON}>
            <Layer
              id="backtrack-particles-line"
              type="line"
              paint={{
                'line-color': '#fcd34d',
                'line-width': 0.7,
                'line-opacity': 0.30
              }}
            />
          </Source>
        )}


        {/* STAGE 6: Forward Spread Corridor (OpenDrift Convex Hull) */}
        {activeStage === 'forecast' && forwardCorridorGeoJSON && (
          <Source id="forward-corridor-src" type="geojson" data={forwardCorridorGeoJSON}>
            <Layer
              id="forward-corridor-fill"
              type="fill"
              paint={{
                'fill-color': '#2563eb',
                'fill-opacity': 0.15
              }}
            />
            <Layer
              id="forward-corridor-line"
              type="line"
              paint={{
                'line-color': '#60a5fa',
                'line-width': 1.8,
                'line-dasharray': [4, 3]
              }}
            />
          </Source>
        )}

        {/* STAGE 6: Forward Particle Trajectories */}
        {activeStage === 'forecast' && forwardParticlesGeoJSON && (
          <Source id="forward-particles-src" type="geojson" data={forwardParticlesGeoJSON}>
            <Layer
              id="forward-particles-line"
              type="line"
              paint={{
                'line-color': '#38bdf8',
                'line-width': 0.8,
                'line-opacity': 0.35
              }}
            />
          </Source>
        )}

        {/* STAGE 6: Forward Particle Point Cloud (Current Endpoints) */}
        {activeStage === 'forecast' && forwardPointCloudGeoJSON && (
          <Source id="forward-pointcloud-src" type="geojson" data={forwardPointCloudGeoJSON}>
            <Layer
              id="forward-pointcloud-pts"
              type="circle"
              paint={{
                'circle-radius': 2.2,
                'circle-color': '#0ea5e9',
                'circle-opacity': 0.75
              }}
            />
          </Source>
        )}

        {/* Fallback to mocked forecast bounding boxes if OpenDrift outputs not present */}
        {activeStage === 'forecast' && !forwardCorridorGeoJSON && !forwardParticlesGeoJSON && data?.forward_forecast && data.forward_forecast.map((step, idx) => {
          if (!step.geojson || step.horizon_hours > forecastHours) return null;
          return (
            <Source key={`fwd-${idx}`} id={`fwd-step-${idx}`} type="geojson" data={step.geojson}>
              <Layer
                id={`fwd-fill-${idx}`}
                type="fill"
                paint={{
                  'fill-color': '#3b82f6',
                  'fill-opacity': step.horizon_hours === forecastHours ? 0.35 : 0.12
                }}
              />
              <Layer
                id={`fwd-line-${idx}`}
                type="line"
                paint={{
                  'line-color': '#60a5fa',
                  'line-width': step.horizon_hours === forecastHours ? 2.0 : 1.0,
                  'line-dasharray': [2, 2]
                }}
              />
            </Source>
          );
        })}

        {/* STAGE 4 & 5: AIS Candidate Vessel Tracks & Markers */}
        {['ais', 'attribution'].includes(activeStage) && data?.attribution_scores && (
          <>
            {data.attribution_scores.map(vessel => {
              const isRank1 = vessel.priority_rank === 1;
              const hasTrajectory = vessel.trajectory && vessel.trajectory.length > 1;

              return (
                <React.Fragment key={vessel.mmsi}>
                  {/* Trajectory line */}
                  {hasTrajectory && (
                    <Source
                      id={`vessel-track-${vessel.mmsi}`}
                      type="geojson"
                      data={{
                        type: 'Feature',
                        properties: {},
                        geometry: {
                          type: 'LineString',
                          coordinates: vessel.trajectory as number[][]
                        }
                      }}
                    >
                      <Layer
                        id={`vessel-line-${vessel.mmsi}`}
                        type="line"
                        paint={{
                          'line-color': isRank1 ? '#ef4444' : '#64748b',
                          'line-width': isRank1 ? 2.5 : 1.5,
                          'line-dasharray': isRank1 ? [4, 2] : [2, 2]
                        }}
                      />
                    </Source>
                  )}

                  {/* Vessel Position Marker */}
                  {(vessel.last_known_lon != null && vessel.last_known_lat != null) && (
                    <Marker
                      longitude={vessel.last_known_lon}
                      latitude={vessel.last_known_lat}
                      anchor="center"
                    >
                      <div className={`px-2 py-1 border font-mono text-[10px] font-bold rounded flex items-center gap-1.5 shadow-lg ${
                        isRank1 
                          ? 'bg-red-950 text-red-100 border-red-500 ring-2 ring-red-500/40' 
                          : 'bg-slate-900 text-zinc-300 border-zinc-700'
                      }`}>
                        <Navigation className="w-3 h-3 text-current" style={{ transform: `rotate(${vessel.cog || 0}deg)` }} />
                        <span>[{vessel.priority_rank}] {vessel.vessel_name}</span>
                        {vessel.isDark && (
                          <span className="flex items-center gap-0.5 bg-yellow-400 text-black px-1 text-[8px] font-bold rounded">
                            <AlertTriangle className="w-2.5 h-2.5" />
                            DARK
                          </span>
                        )}
                      </div>
                    </Marker>
                  )}
                </React.Fragment>
              );
            })}
          </>
        )}

        {/* LIVE DRAWING PREVIEW LAYERS */}
        {isDrawing && drawnPolyGeoJSON && (
          <Source id="draw-polygon-src" type="geojson" data={drawnPolyGeoJSON}>
            <Layer
              id="draw-poly-fill"
              type="fill"
              paint={{
                'fill-color': '#f43f5e',
                'fill-opacity': 0.35
              }}
            />
            <Layer
              id="draw-poly-border"
              type="line"
              paint={{
                'line-color': '#fb7185',
                'line-width': 2.5
              }}
            />
          </Source>
        )}

        {isDrawing && drawnLineGeoJSON && (
          <Source id="draw-line-src" type="geojson" data={drawnLineGeoJSON}>
            <Layer
              id="draw-line-preview"
              type="line"
              paint={{
                'line-color': '#f43f5e',
                'line-width': 2.5,
                'line-dasharray': [3, 2]
              }}
            />
          </Source>
        )}

        {/* Placed Vertex Markers during Drawing */}
        {isDrawing && drawnPoints.map(([lon, lat], i) => (
          <Marker key={`vertex-${i}`} longitude={lon} latitude={lat} anchor="center">
            <div className={`w-3.5 h-3.5 rounded-full border-2 border-white shadow-lg flex items-center justify-center text-[8px] font-bold text-white cursor-pointer ${
              i === 0 ? 'bg-amber-400 ring-4 ring-amber-400/40 animate-pulse' : 'bg-rose-500'
            }`}>
              {i === 0 ? '1' : i + 1}
            </div>
          </Marker>
        ))}

        {/* STAGE 2 Marker: Segmented Spill Area */}
        {activeStage === 'satellite' && !isDrawing && (
          <Marker longitude={segLon} latitude={segLat} anchor="bottom">
            <div className="flex flex-col items-center cursor-default pointer-events-none select-none">
              <div className="bg-slate-900/95 text-cyan-300 px-3 py-1 text-xs font-mono font-bold border border-cyan-400/80 shadow-2xl rounded flex items-center gap-1.5 mb-1.5 backdrop-blur">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span>
                  {isCustomTrace ? 'User-Traced Spill' : 'Segmented Oil Spill'} ({data?.detection?.area_km2 || 14.68} km²)
                </span>
              </div>
              <div className="w-3.5 h-3.5 bg-cyan-500 border-2 border-white rounded-full shadow-lg" />
            </div>
          </Marker>
        )}

        {/* STAGE 3 Marker: Probable Origin */}
        {activeStage === 'origin' && data?.origin_estimate && (
          <Marker
            longitude={data.origin_estimate.origin_center_lon}
            latitude={data.origin_estimate.origin_center_lat}
            anchor="right"
          >
            <div className="flex flex-row items-center cursor-default pointer-events-none select-none mr-2">
              <div className="bg-slate-900/95 text-amber-300 px-3 py-1 text-xs font-mono font-bold border border-amber-500/80 shadow-2xl rounded flex items-center gap-1.5 backdrop-blur">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <span>Probable Release Origin</span>
              </div>
              <div className="w-3.5 h-3.5 bg-amber-500 border-2 border-white rounded-full shadow-lg ml-1.5 shrink-0" />
            </div>
          </Marker>
        )}

        {/* STAGE 6 Marker: Forward Forecast Centroid */}
        {activeStage === 'forecast' && activeForwardSnapshot?.centroid && (
          <Marker
            longitude={activeForwardSnapshot.centroid.lon}
            latitude={activeForwardSnapshot.centroid.lat}
            anchor="left"
          >
            <div className="flex flex-row items-center cursor-default pointer-events-none select-none ml-2">
              <div className="w-3.5 h-3.5 bg-blue-500 border-2 border-white rounded-full shadow-lg mr-1.5 shrink-0" />
              <div className="bg-slate-900/95 text-blue-300 px-3 py-1 text-xs font-mono font-bold border border-blue-500/80 shadow-2xl rounded flex items-center gap-1.5 backdrop-blur">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                <span>Forecasted Center (+{forecastHours}H)</span>
              </div>
            </div>
          </Marker>
        )}
      </Map>

      {/* TOP FLOATING INTERACTIVE DRAWING TOOLBAR */}
      {activeStage === 'satellite' && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2">
          {!isDrawing ? (
            <div className="flex items-center gap-2 bg-slate-900/95 border border-zinc-700 backdrop-blur-md px-3.5 py-2 rounded-lg shadow-2xl font-mono text-xs text-white">
              <button
                onClick={() => {
                  setIsDrawing(true);
                  setDrawnPoints([]);
                }}
                className="flex items-center gap-2 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded transition-colors shadow-lg shadow-rose-600/30"
                title="Click to start tracing a polygon around the oil spill"
              >
                <PenTool className="w-3.5 h-3.5" />
                <span>Draw Spill Polygon (GeoJSON)</span>
              </button>

              {isCustomTrace && (
                <>
                  <div className="h-4 w-px bg-zinc-700 mx-1" />
                  <span className="text-emerald-400 font-bold text-[11px] px-2 py-0.5 bg-emerald-950/60 border border-emerald-800/60 rounded">
                    CUSTOM POLYGON ACTIVE
                  </span>
                  <button
                    onClick={handleCopyGeoJSON}
                    className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 border border-zinc-700 hover:border-zinc-500 rounded text-zinc-300 hover:text-white transition-colors text-[11px]"
                    title="Copy GeoJSON to clipboard"
                  >
                    <Copy className="w-3 h-3" />
                    <span>{copied ? 'Copied!' : 'Copy GeoJSON'}</span>
                  </button>
                  <button
                    onClick={handleDownloadGeoJSON}
                    className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 border border-zinc-700 hover:border-zinc-500 rounded text-zinc-300 hover:text-white transition-colors text-[11px]"
                    title="Download GeoJSON file"
                  >
                    <Download className="w-3 h-3" />
                    <span>Export</span>
                  </button>
                  <button
                    onClick={handleRevert}
                    disabled={isSaving}
                    className="flex items-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 border border-zinc-700 hover:border-zinc-500 rounded text-zinc-400 hover:text-white transition-colors text-[11px]"
                    title="Reset to default detection"
                  >
                    <RefreshCw className={`w-3 h-3 ${isSaving ? 'animate-spin' : ''}`} />
                    <span>Reset</span>
                  </button>
                </>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <div className="flex items-center gap-3 bg-slate-900/95 border border-rose-500/80 backdrop-blur-md px-4 py-2.5 rounded-lg shadow-2xl font-mono text-xs text-white">
                <div className="flex items-center gap-2 pr-3 border-r border-zinc-700">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                  <span className="font-bold text-rose-300 uppercase tracking-wider text-[11px]">Tracing Slick</span>
                </div>

                <div className="text-zinc-300 text-[11px]">
                  Points: <strong className="text-white">{drawnPoints.length}</strong>
                </div>

                {drawnPoints.length >= 3 && (
                  <div className="text-zinc-300 text-[11px] pl-2 border-l border-zinc-700">
                    Live Area: <strong className="text-cyan-300">{liveAreaKm2.toFixed(2)} km²</strong>
                  </div>
                )}

                <div className="flex items-center gap-1.5 ml-2">
                  <button
                    onClick={handleUndo}
                    disabled={drawnPoints.length === 0}
                    className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 border border-zinc-700 rounded text-zinc-300 hover:text-white text-[11px]"
                    title="Undo last point"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Undo</span>
                  </button>

                  <button
                    onClick={handleClear}
                    disabled={drawnPoints.length === 0}
                    className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 border border-zinc-700 rounded text-zinc-300 hover:text-white text-[11px]"
                    title="Clear points"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Clear</span>
                  </button>

                  <button
                    onClick={handleCancel}
                    className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 border border-zinc-700 rounded text-zinc-400 hover:text-white text-[11px]"
                    title="Cancel drawing"
                  >
                    <X className="w-3 h-3" />
                    <span>Cancel</span>
                  </button>

                  <button
                    onClick={handleSavePolygon}
                    disabled={drawnPoints.length < 3 || isSaving}
                    className="flex items-center gap-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-bold rounded shadow-lg shadow-emerald-600/30 text-[11px] transition-all ml-1"
                    title={drawnPoints.length < 3 ? "Click at least 3 points on map to close polygon" : "Save & apply this polygon"}
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>{isSaving ? 'Saving...' : 'Save & Apply Polygon'}</span>
                  </button>
                </div>
              </div>

              <div className="bg-slate-950/90 text-zinc-300 border border-zinc-800 px-3 py-1 rounded text-[10px] font-mono shadow-md backdrop-blur">
                💡 Click on the dark oil slick feature on the map to place vertices. Place ≥ 3 points to complete.
              </div>
            </div>
          )}

          {/* Success Banner */}
          {saveMessage && (
            <div className="bg-emerald-950/95 border border-emerald-600 text-emerald-200 px-4 py-1.5 rounded text-xs font-mono shadow-2xl flex items-center gap-2 animate-fade-in">
              <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>{saveMessage}</span>
            </div>
          )}
        </div>
      )}

      {/* Backtrack Time Selector — shown only on origin stage */}
      {['origin', 'ais', 'attribution'].includes(activeStage) && data?.backtrack_snapshots && (
        <div className="absolute top-4 left-4 z-20 flex flex-col gap-1.5 pointer-events-auto">
          <div className="bg-slate-900/95 border border-zinc-700 backdrop-blur-md rounded-lg shadow-2xl px-3 py-2">
            <div className="text-[9px] text-amber-400 uppercase tracking-widest font-bold mb-2">Backtrack Time</div>
            <div className="flex gap-1.5">
              {([1, 6, 12, 24, 48] as const).map((h) => {
                const snap = data.backtrack_snapshots![String(h)];
                const isActive = backtrackHours === h;
                return (
                  <button
                    key={h}
                    onClick={() => setBacktrackHours(h)}
                    className={`
                      flex flex-col items-center px-3 py-1.5 rounded text-xs font-mono font-bold transition-all border
                      ${isActive
                        ? 'bg-amber-500/20 border-amber-400 text-amber-300 shadow-lg shadow-amber-900/30'
                        : 'bg-slate-800/80 border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
                      }
                    `}
                  >
                    <span className="text-[13px] leading-tight">{h}H</span>
                    <span className="text-[8px] opacity-70 mt-0.5">{snap ? `${snap.active_particles} pts` : '—'}</span>
                  </button>
                );
              })}
            </div>
            {activeSnapshot && (
              <div className="mt-2 pt-1.5 border-t border-zinc-800 text-[9px] text-zinc-400 font-mono flex items-center justify-between">
                <div>Centroid: <span className="text-amber-300">{activeSnapshot.centroid.lat.toFixed(3)}°N, {activeSnapshot.centroid.lon.toFixed(3)}°E</span></div>
              </div>
            )}
            <input
              type="range"
              min="1"
              max="48"
              step="1"
              value={backtrackHours}
              onChange={(e) => {
                const val = parseInt(e.target.value);
                const closest = [1, 6, 12, 24, 48].reduce((prev, curr) => Math.abs(curr - val) < Math.abs(prev - val) ? curr : prev) as 1 | 6 | 12 | 24 | 48;
                setBacktrackHours(closest);
              }}
              className="w-full mt-3 accent-amber-500 cursor-pointer h-1 bg-zinc-800 rounded-lg appearance-none"
            />
          </div>
        </div>
      )}

      {/* Forecast Time Selector — shown only on forecast stage */}
      {activeStage === 'forecast' && (data?.forward_snapshots || data?.forward_forecast) && (
        <div className="absolute top-4 left-4 z-20 flex flex-col gap-1.5 pointer-events-auto">
          <div className="bg-slate-900/95 border border-zinc-700 backdrop-blur-md rounded-lg shadow-2xl px-3 py-2">
            <div className="text-[9px] text-blue-400 uppercase tracking-widest font-bold mb-2">Forward Forecast Time</div>
            <div className="flex gap-1.5">
              {([6, 12, 24, 48] as const).map((h) => {
                const snap = data?.forward_snapshots ? data.forward_snapshots[String(h)] : null;
                const isActive = forecastHours === h;
                return (
                  <button
                    key={h}
                    onClick={() => setForecastHours(h)}
                    className={`
                      flex flex-col items-center px-3 py-1.5 rounded text-xs font-mono font-bold transition-all border
                      ${isActive
                        ? 'bg-blue-500/20 border-blue-400 text-blue-300 shadow-lg shadow-blue-900/30'
                        : 'bg-slate-800/80 border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
                      }
                    `}
                  >
                    <span className="text-[13px] leading-tight">+{h}H</span>
                    <span className="text-[8px] opacity-70 mt-0.5">{snap ? `${snap.active_particles} pts` : '—'}</span>
                  </button>
                );
              })}
            </div>
            {activeForwardSnapshot && (
              <div className="mt-2 pt-1.5 border-t border-zinc-800 text-[9px] text-zinc-400 font-mono flex items-center justify-between">
                <div>Centroid: <span className="text-blue-300">{activeForwardSnapshot.centroid.lat.toFixed(3)}°N, {activeForwardSnapshot.centroid.lon.toFixed(3)}°E</span></div>
              </div>
            )}
            <input
              type="range"
              min="6"
              max="48"
              step="6"
              value={forecastHours}
              onChange={(e) => {
                const val = parseInt(e.target.value);
                const closest = [6, 12, 24, 48].reduce((prev, curr) => Math.abs(curr - val) < Math.abs(prev - val) ? curr : prev) as 6 | 12 | 24 | 48;
                setForecastHours(closest);
              }}
              className="w-full mt-3 accent-blue-500 cursor-pointer h-1 bg-zinc-800 rounded-lg appearance-none"
            />
          </div>
        </div>
      )}

      {/* Dynamic Minimal Map Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-slate-900/90 text-white backdrop-blur border border-zinc-700 px-3.5 py-2 rounded shadow-xl font-mono text-xs flex items-center gap-4">
        {activeStage === 'satellite' && (
          <>
            <div className="flex items-center gap-2">
              <span className={`w-3 h-3 ${isCustomTrace ? 'bg-cyan-500/50 border border-cyan-300' : 'bg-cyan-500/40 border border-cyan-400'} inline-block rounded-sm`} />
              <span className="font-semibold text-cyan-200">
                {isCustomTrace ? 'Custom Traced Slick' : 'Segmented Oil Spill'} ({data?.detection?.area_km2 || 14.68} km²)
              </span>
            </div>
            <div className="h-3 w-px bg-zinc-700" />
          </>
        )}
        {['origin', 'ais', 'attribution'].includes(activeStage) && (
          <>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-px border-t-2 border-dashed border-amber-400 inline-block" style={{width: 16}} />
              <span className="font-semibold text-amber-200">Origin Corridor (T-{backtrackHours}h)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-px bg-yellow-300 inline-block" style={{width: 16}} />
              <span className="text-yellow-200">Drift Trajectories</span>
            </div>
            <div className="h-3 w-px bg-zinc-700" />
          </>
        )}
        {activeStage === 'forecast' && (
          <>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-px border-t-2 border-dashed border-blue-400 inline-block" style={{width: 16}} />
              <span className="font-semibold text-blue-200">Spread Corridor (T+{forecastHours}h)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-px bg-sky-400 inline-block" style={{width: 16}} />
              <span className="text-sky-200">Forward Trajectories</span>
            </div>
            <div className="h-3 w-px bg-zinc-700" />
          </>
        )}
        <div className="text-zinc-400 text-[11px] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          Sentinel-1 SAR C-Band
        </div>
      </div>

      {/* Hydrodynamic & Environmental Legend Overlay */}
      <div className="absolute bottom-3 right-3 z-10 bg-black text-white border border-zinc-700 p-3 font-mono text-[11px] shadow-2xl space-y-1">
        <div className="text-zinc-400 uppercase pb-1 border-b border-zinc-700 mb-1 text-[10px] flex items-center justify-between gap-4 font-bold">
          <span>HYDRODYNAMIC FORCING</span>
          <span className="text-amber-400 font-bold">ECMWF ERA5 / CMEMS</span>
        </div>
        {data?.origin_estimate?.forcing_used ? (
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
