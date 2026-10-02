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

// =========================================================================
// FULL SATELLITE SCENE COORDINATES: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
// Format for each point: [longitude, latitude]
// =========================================================================
export const FULL_SATELLITE_COORDINATES: [[number, number], [number, number], [number, number], [number, number]] = [
  [32.595454, 32.134300], // Top-Left (NW)  [lon, lat]
  [33.022719, 32.200425], // Top-Right (NE) [lon, lat]
  [33.101866, 31.830894], // Bottom-Right (SE) [lon, lat]
  [32.676341, 31.764675], // Bottom-Left (SW) [lon, lat]
];

// =========================================================================
// CANDIDATE OVERLAY IMAGE COORDINATES: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
// Format for each point: [longitude, latitude]
// Edit these 4 numbers directly below to manually reposition, stretch, or rotate the overlay image!
// =========================================================================
export const CUSTOM_IMAGE_COORDINATES: [[number, number], [number, number], [number, number], [number, number]] = [
  [32.790459, 32.001234], // Top-Left (NW)  [lon, lat]
  [33.037687, 32.039857], // Top-Right (NE) [lon, lat]
  [33.080393, 31.858586], // Bottom-Right (SE) [lon, lat]
  [32.826188, 31.816656], // Bottom-Left (SW) [lon, lat]
];

export const IncidentMap: React.FC<IncidentMapProps> = ({ 
  data, 
  activeStage = 'overview',
  onIncidentUpdated 
}) => {
  const mapRef = useRef<MapRef>(null);
  const [satelliteBounds, setSatelliteBounds] = useState<[[number, number], [number, number], [number, number], [number, number]]>(FULL_SATELLITE_COORDINATES);

  // Backtrack time selector (defaults to 1H on origin backtrack page)
  const [backtrackHours, setBacktrackHours] = useState<1 | 6 | 12 | 24 | 48>(1);

  // Forecast time selector
  const [forecastHours, setForecastHours] = useState<6 | 12 | 24 | 48>(48);

  // Manual Polygon Drawing Tool States
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // AIS Vessel Replay Timeline state (default step 46 is ~14:40 UTC, during the spill window near the SAR image)
  const [replayStep, setReplayStep] = useState<number>(46);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const totalSteps = useMemo(() => {
    const counts = (data?.attribution_scores || []).map(v => v.ais_points?.length || 0);
    return counts.length > 0 ? Math.max(...counts, 88) : 88;
  }, [data?.attribution_scores]);

  const currentTimestampStr = useMemo(() => {
    const v0 = data?.attribution_scores?.[0];
    if (v0?.ais_points && v0.ais_points.length > 0) {
      const idx = Math.min(replayStep, v0.ais_points.length - 1);
      const raw = v0.ais_points[idx].timestamp;
      const timePart = raw.includes('T') ? raw.split('T')[1].slice(0, 5) : raw;
      return `${timePart} UTC (10 Jun 2019)`;
    }
    return '14:40 UTC (10 Jun 2019)';
  }, [data?.attribution_scores, replayStep]);

  const isSpillWindow = useMemo(() => {
    return replayStep >= 40 && replayStep <= 53;
  }, [replayStep]);

  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setReplayStep(prev => {
        if (prev >= totalSteps - 1) {
          setIsPlaying(false);
          return 0;
        }
        return prev + 1;
      });
    }, 300);
    return () => clearInterval(interval);
  }, [isPlaying, totalSteps]);

  useEffect(() => {
    if (data?.incident?.id) {
      fetchSatelliteBounds(data.incident.id)
        .then(res => {
          // Authoritative GCP-derived geolocation for full scene
          if (res?.coordinates && res.coordinates.length === 4) {
            setSatelliteBounds(res.coordinates as [[number, number], [number, number], [number, number], [number, number]]);
          }
        })
        .catch(err => console.error("Could not fetch bounds:", err));
    }
  }, [data?.incident?.id]);

  // Coordinates
  const refLat = 31.982759;
  const refLon = 32.849022;

  // Derive actual polygon center from detection GeoJSON or coordinates
  const polygonCenter = useMemo(() => {
    const geo = data?.detection?.geojson;
    if (geo?.properties?.center_lat && geo?.properties?.center_lon) {
      return { lat: geo.properties.center_lat, lon: geo.properties.center_lon };
    }
    if (geo?.geometry) {
      let pts: [number, number][] = [];
      if (geo.geometry.type === 'Polygon' && Array.isArray(geo.geometry.coordinates?.[0])) {
        pts = geo.geometry.coordinates[0];
      } else if (geo.geometry.type === 'MultiPolygon' && Array.isArray(geo.geometry.coordinates)) {
        pts = geo.geometry.coordinates.flatMap((poly: any) => poly[0]);
      }
      if (pts.length > 0) {
        const uniquePts = pts.length > 1 && pts[0][0] === pts[pts.length - 1][0] && pts[0][1] === pts[pts.length - 1][1]
          ? pts.slice(0, -1)
          : pts;
        const avgLon = uniquePts.reduce((acc, p) => acc + p[0], 0) / uniquePts.length;
        const avgLat = uniquePts.reduce((acc, p) => acc + p[1], 0) / uniquePts.length;
        return { lat: avgLat, lon: avgLon };
      }
    }
    return {
      lat: data?.incident?.center_lat || 31.925537,
      lon: data?.incident?.center_lon || 32.894937
    };
  }, [data?.detection?.geojson, data?.incident?.center_lat, data?.incident?.center_lon]);

  const segLat = polygonCenter.lat;
  const segLon = polygonCenter.lon;

  // Whether user is using a custom manually traced polygon
  const isCustomTrace = data?.detection?.morphology_type === 'USER_DEFINED_SLICK' || 
                        data?.detection?.geojson?.properties?.source === 'user_manual_trace';

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

  // Map Camera Transition (triggered only on activeStage changes, not on timestamp clicks)
  useEffect(() => {
    if (!mapRef.current || !data) return;

    if (activeStage === 'overview') {
      mapRef.current.flyTo({
        center: [refLon, refLat],
        zoom: 9.8,
        duration: 1000,
        essential: true
      });
    } else if (['ais', 'attribution'].includes(activeStage)) {
      mapRef.current.flyTo({
        center: [refLon, refLat],
        zoom: 10.2,
        duration: 1000,
        essential: true
      });
    } else {
      mapRef.current.flyTo({
        center: [segLon, segLat],
        zoom: 11.2,
        duration: 1000,
        essential: true
      });
    }
  }, [activeStage, data, segLon, segLat, refLon, refLat]);

  // Ensure backward drift defaults to 1H when opening or navigating to the origin backtrack stage
  useEffect(() => {
    if (activeStage === 'origin') {
      setBacktrackHours(1);
    }
  }, [activeStage]);

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
          name: 'Delineated Oil Spill Area',
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
    a.download = `custom_spill_geometry_${data?.incident?.id || 'VARUNA-2026-001'}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none border border-zinc-800">
      {/* Live Spatial-Temporal Telemetry HUD & Replay Slider - shown on AIS and attribution stages */}
      {['ais', 'attribution'].includes(activeStage) && (
        <div className="absolute top-3 left-3 z-30 flex flex-col gap-2 font-sans select-none">
          <div className="flex items-center liquid-glass text-white border border-white/10 shadow-lg rounded-xl px-3 py-1.5 gap-3 font-mono text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-slate-400 uppercase font-semibold text-[10px]">SAR SENSING:</span>
              <strong className="text-slate-200 font-bold text-xs">15:48 UTC</strong>
            </div>
            <div className="h-3 w-px bg-white/10" />
            <div className="text-slate-300">
              <span className="text-slate-400 font-semibold">TARGETS:</span> {(data?.attribution_scores || []).length} CANDIDATES
            </div>
          </div>

          {/* Replay Timeline Slider Control */}
          <div className="liquid-glass border border-white/15 text-slate-100 p-3 rounded-2xl shadow-2xl backdrop-blur-2xl w-80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-300 font-bold uppercase tracking-wider text-[10px] font-heading">
                AIS Vessel Replay
              </span>
              <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold border ${
                isSpillWindow 
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' 
                  : 'bg-white/[0.05] text-slate-300 border-white/10'
              }`}>
                {isSpillWindow ? 'SPILL WINDOW' : 'TRANSIT REPLAY'}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400 text-[11px]">Vessel Time:</span>
              <strong className="text-cyan-300 font-bold text-xs">{currentTimestampStr}</strong>
            </div>

            <div className="space-y-1">
              <input
                type="range"
                min={0}
                max={totalSteps - 1}
                value={replayStep}
                onChange={(e) => {
                  setIsPlaying(false);
                  setReplayStep(parseInt(e.target.value, 10));
                }}
                className="w-full accent-blue-500 cursor-pointer h-2 bg-white/10 rounded-lg appearance-none"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>07:00 UTC</span>
                <span className="text-cyan-300 font-bold">14:40 (Spill)</span>
                <span>21:50 UTC</span>
              </div>
            </div>

            <div className="flex items-center gap-1.5 pt-1 border-t border-white/[0.08]">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-center ${
                  isPlaying 
                    ? 'bg-amber-600 text-white' 
                    : 'bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-900/40'
                }`}
              >
                {isPlaying ? 'Pause' : 'Play Replay'}
              </button>
              <button
                onClick={() => {
                  setIsPlaying(false);
                  setReplayStep(46);
                }}
                className="py-1.5 px-3 rounded-lg text-xs font-semibold bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border border-white/10"
              >
                Reset (14:40)
              </button>
            </div>
          </div>
        </div>
      )}
      <Map
        ref={mapRef}
        style={{ width: '100%', height: '100%' }}
        cursor={isDrawing ? 'crosshair' : 'grab'}
        onClick={handleMapClick}
        initialViewState={{
          longitude: activeStage === 'overview' ? refLon : ['ais', 'attribution'].includes(activeStage) ? refLon : segLon,
          latitude: activeStage === 'overview' ? refLat : ['ais', 'attribution'].includes(activeStage) ? refLat : segLat,
          zoom: activeStage === 'overview' ? 9.8 : ['ais', 'attribution'].includes(activeStage) ? 10.2 : 11.2
        }}
        mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
        attributionControl={false}
      >
        {/* Real Sentinel-1 Base SAR Satellite Imagery (Full Swath) */}
        {satelliteBounds && (
          <Source
            id="clean-satellite-image"
            type="image"
            url="/clean_sar.png"
            coordinates={satelliteBounds}
          >
            <Layer
              id="clean-satellite-layer"
              type="raster"
              paint={{ 'raster-opacity': 0.95 }}
            />
          </Source>
        )}

        {/* Candidate Oil Slick Overlay (final-mark.png with candidate detections) */}
        {/* Only shown on analysis stages: hidden on 'overview' page as requested */}
        {activeStage !== 'overview' && (
          <Source
            id="candidate-overlay-image"
            type="image"
            url="/final-mark.png"
            coordinates={CUSTOM_IMAGE_COORDINATES}
          >
            <Layer
              id="candidate-overlay-layer"
              type="raster"
              paint={{ 'raster-opacity': 0.98 }}
            />
          </Source>
        )}

        {/* Note: Vector polygon overlay removed to display final-mark image cleanly */}

        {/* STAGE 3+: Origin Corridor (Convex Hull at selected backtrack time) */}
        {['origin', 'ais', 'attribution'].includes(activeStage) && originCorridorGeoJSON && (
          <Source id="origin-contour-src" type="geojson" data={originCorridorGeoJSON}>
            <Layer
              id="origin-contour-fill"
              type="fill"
              paint={{
                'fill-color': '#ffffffff',
                'fill-opacity': 0.10
              }}
            />
            <Layer
              id="origin-contour-line"
              type="line"
              paint={{
                'line-color': '#ffffffff',
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
                'line-width': 0.8,
                'line-opacity': 0.35
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
                'fill-color': '#040f56ff',
                'fill-opacity': 0.35
              }}
            />
            <Layer
              id="forward-corridor-line"
              type="line"
              paint={{
                'line-color': '#07029eff',
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

                  {/* Vessel Position Marker (Interpolated to Replay Step) */}
                  {(() => {
                    const curPt = vessel.ais_points && vessel.ais_points.length > 0
                      ? vessel.ais_points[Math.min(replayStep, vessel.ais_points.length - 1)]
                      : { 
                          lon: vessel.last_known_lon ?? segLon, 
                          lat: vessel.last_known_lat ?? segLat, 
                          cog: vessel.cog ?? 0, 
                          sog: vessel.sog ?? 0 
                        };

                    const isDarkAtStep = vessel.isDark || (vessel.mmsi === 636018245 && replayStep >= 43 && replayStep <= 45);

                    return (
                      <Marker
                        longitude={curPt.lon}
                        latitude={curPt.lat}
                        anchor="center"
                      >
                        <div className={`px-2 py-1 border font-mono text-[10px] font-bold rounded flex items-center gap-1.5 shadow-lg ${
                          isRank1 
                            ? 'bg-red-950 text-red-100 border-red-500 ring-2 ring-red-500/40' 
                            : 'bg-slate-900 text-zinc-300 border-zinc-700'
                        }`}>
                          <Navigation className="w-3 h-3 text-current shrink-0" style={{ transform: `rotate(${curPt.cog || 0}deg)` }} />
                          <span>[{vessel.priority_rank}] {vessel.vessel_name}</span>
                          <span className="text-[9px] opacity-75 font-normal">({curPt.sog} kts)</span>
                          {isDarkAtStep && (
                            <span className="flex items-center gap-0.5 bg-sky-400 text-slate-950 px-1 text-[8px] font-bold rounded">
                              <AlertTriangle className="w-2.5 h-2.5" />
                              DARK
                            </span>
                          )}
                        </div>
                      </Marker>
                    );
                  })()}
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
              i === 0 ? 'bg-sky-400 ring-4 ring-sky-400/40 animate-pulse' : 'bg-rose-500'
            }`}>
              {i === 0 ? '1' : i + 1}
            </div>
          </Marker>
        ))}

        {/* STAGE 2 Marker: Delineated Spill Area */}
        {activeStage === 'satellite' && !isDrawing && (
          <Marker longitude={segLon} latitude={segLat} anchor="center">
            <div className="flex flex-col items-center cursor-default pointer-events-none select-none font-sans">
              <div className="liquid-glass text-slate-200 px-3.5 py-1 text-xs font-semibold border border-white/15 shadow-xl rounded-xl flex items-center gap-2 mb-1.5 backdrop-blur-xl">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span>
                  Delineated Oil Slick ({data?.detection?.area_km2 || 14.68} km²)
                </span>
              </div>
              <div className="w-3.5 h-3.5 bg-cyan-400 border-2 border-white rounded-full shadow-lg ring-2 ring-cyan-400/40" />
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
            <div className="flex flex-row items-center cursor-default pointer-events-none select-none mr-2 font-sans">
              <div className="liquid-glass text-slate-200 px-3.5 py-1 text-xs font-semibold border border-white/15 shadow-xl rounded-xl flex items-center gap-2 backdrop-blur-xl">
                <span className="w-2 h-2 rounded-full bg-slate-300" />
                <span>Probable Release Origin</span>
              </div>
              <div className="w-3.5 h-3.5 bg-slate-400 border-2 border-white rounded-full shadow-lg ml-1.5 shrink-0" />
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
            <div className="flex flex-row items-center cursor-default pointer-events-none select-none ml-2 font-sans">
              <div className="w-3.5 h-3.5 bg-slate-400 border-2 border-white rounded-full shadow-lg mr-1.5 shrink-0" />
              <div className="liquid-glass text-slate-200 px-3.5 py-1 text-xs font-semibold border border-white/15 shadow-xl rounded-xl flex items-center gap-2 backdrop-blur-xl">
                <span className="w-2 h-2 rounded-full bg-slate-300" />
                <span>Forecasted Center (+{forecastHours}H)</span>
              </div>
            </div>
          </Marker>
        )}
      </Map>

      {/* TOP FLOATING INTERACTIVE DRAWING TOOLBAR - Hidden from UI */}
      {activeStage === 'satellite' && (
        <div className="hidden">
          {!isDrawing ? (
            <div className="flex items-center gap-2.5 liquid-glass border border-white/15 backdrop-blur-2xl px-4 py-2 rounded-2xl shadow-2xl text-xs text-white">
              <button
                onClick={() => {
                  setIsDrawing(true);
                  setDrawnPoints([]);
                }}
                className="flex items-center gap-2 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-rose-600/30"
                title="Click to start tracing a polygon around the oil spill"
              >
                <PenTool className="w-3.5 h-3.5" />
                <span>Draw Spill Polygon (GeoJSON)</span>
              </button>

              {isCustomTrace && (
                <>
                  <div className="h-4 w-px bg-white/15 mx-1" />
                  <span className="text-emerald-300 font-bold text-[11px] px-2.5 py-0.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                    CUSTOM POLYGON ACTIVE
                  </span>
                  <button
                    onClick={handleCopyGeoJSON}
                    className="flex items-center gap-1.5 px-3 py-1.5 liquid-glass-subtle hover:bg-white/10 border border-white/10 rounded-xl text-slate-200 hover:text-white transition-all text-xs font-semibold"
                    title="Copy GeoJSON to clipboard"
                  >
                    <Copy className="w-3 h-3" />
                    <span>{copied ? 'Copied!' : 'Copy GeoJSON'}</span>
                  </button>
                  <button
                    onClick={handleDownloadGeoJSON}
                    className="flex items-center gap-1.5 px-3 py-1.5 liquid-glass-subtle hover:bg-white/10 border border-white/10 rounded-xl text-slate-200 hover:text-white transition-all text-xs font-semibold"
                    title="Download GeoJSON file"
                  >
                    <Download className="w-3 h-3" />
                    <span>Export</span>
                  </button>
                  <button
                    onClick={handleRevert}
                    disabled={isSaving}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 liquid-glass-subtle hover:bg-white/10 border border-white/10 rounded-xl text-slate-300 hover:text-white transition-all text-xs font-semibold disabled:opacity-40"
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
              <div className="flex items-center gap-3 liquid-glass border border-rose-500/40 backdrop-blur-2xl px-4 py-2.5 rounded-2xl shadow-2xl text-xs text-white">
                <div className="flex items-center gap-2 pr-3 border-r border-white/15">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                  <span className="font-bold text-rose-300 uppercase tracking-wider text-[11px]">Tracing Slick</span>
                </div>

                <div className="text-slate-200 text-[11px]">
                  Points: <strong className="text-white">{drawnPoints.length}</strong>
                </div>

                {drawnPoints.length >= 3 && (
                  <div className="text-slate-200 text-[11px] pl-2 border-l border-white/15">
                    Live Area: <strong className="text-white font-mono">{liveAreaKm2.toFixed(2)} km²</strong>
                  </div>
                )}

                <div className="flex items-center gap-1.5 ml-2">
                  <button
                    onClick={handleUndo}
                    disabled={drawnPoints.length === 0}
                    className="flex items-center gap-1 px-2.5 py-1.5 liquid-glass-subtle hover:bg-white/10 disabled:opacity-40 border border-white/10 rounded-xl text-slate-200 hover:text-white text-xs font-semibold transition-all"
                    title="Undo last point"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Undo</span>
                  </button>

                  <button
                    onClick={handleClear}
                    disabled={drawnPoints.length === 0}
                    className="flex items-center gap-1 px-2.5 py-1.5 liquid-glass-subtle hover:bg-white/10 disabled:opacity-40 border border-white/10 rounded-xl text-slate-200 hover:text-white text-xs font-semibold transition-all"
                    title="Clear points"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Clear</span>
                  </button>

                  <button
                    onClick={handleCancel}
                    className="flex items-center gap-1 px-2.5 py-1.5 liquid-glass-subtle hover:bg-white/10 border border-white/10 rounded-xl text-slate-300 hover:text-white text-xs font-semibold transition-all"
                    title="Cancel drawing"
                  >
                    <X className="w-3 h-3" />
                    <span>Cancel</span>
                  </button>

                  <button
                    onClick={handleSavePolygon}
                    disabled={drawnPoints.length < 3 || isSaving}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-bold rounded-xl shadow-lg shadow-emerald-600/30 text-xs transition-all ml-1"
                    title={drawnPoints.length < 3 ? "Click at least 3 points on map to close polygon" : "Save & apply this polygon"}
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>{isSaving ? 'Saving...' : 'Save & Apply Polygon'}</span>
                  </button>
                </div>
              </div>

              <div className="liquid-glass text-slate-200 border border-white/15 px-4 py-1.5 rounded-xl text-xs font-sans shadow-lg backdrop-blur-xl">
                💡 Click on the dark oil slick feature on the map to place vertices. Place ≥ 3 points to complete.
              </div>
            </div>
          )}

          {/* Success Banner */}
          {saveMessage && (
            <div className="liquid-glass border border-emerald-500/40 text-emerald-200 px-4 py-2 rounded-xl text-xs font-sans shadow-2xl flex items-center gap-2 backdrop-blur-xl animate-fade-in">
              <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>{saveMessage}</span>
            </div>
          )}
        </div>
      )}

      {/* Backtrack Time Selector — shown only on origin stage */}
      {['origin', 'ais', 'attribution'].includes(activeStage) && data?.backtrack_snapshots && (
        <div className="absolute top-4 left-4 z-20 flex flex-col gap-1.5 pointer-events-auto font-sans">
          <div className="liquid-glass border border-white/15 backdrop-blur-2xl rounded-2xl shadow-2xl p-4 text-slate-100">
            <div className="text-[10px] text-slate-400 uppercase tracking-widest font-bold mb-2.5 font-heading">
              Backtrack Time
            </div>
            <div className="flex gap-2">
              {([1, 6, 12, 24, 48] as const).map((h) => {
                const isActive = backtrackHours === h;
                return (
                  <button
                    key={h}
                    onClick={() => setBacktrackHours(h)}
                    className={`
                      flex flex-col items-center px-3.5 py-2 rounded-xl text-xs font-sans font-bold transition-all
                      ${isActive
                        ? 'liquid-glass border border-white/30 text-white shadow-lg bg-white/[0.12]'
                        : 'liquid-glass-subtle border border-white/10 text-slate-300 hover:border-white/20 hover:text-white'
                      }
                    `}
                  >
                    <span className="text-[13px] font-extrabold leading-tight">{h}H</span>
                  </button>
                );
              })}
            </div>
            {activeSnapshot && (
              <div className="mt-3 pt-2 border-t border-white/10 text-[11px] text-slate-300 flex items-center justify-between font-sans">
                <div>Centroid: <span className="text-slate-200 font-mono font-semibold">{activeSnapshot.centroid.lat.toFixed(3)}°N, {activeSnapshot.centroid.lon.toFixed(3)}°E</span></div>
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
              className="w-full mt-3 accent-blue-500 cursor-pointer h-1.5 bg-white/10 rounded-lg appearance-none"
            />
          </div>
        </div>
      )}

      {/* Forecast Time Selector — shown only on forecast stage */}
      {activeStage === 'forecast' && (data?.forward_snapshots || data?.forward_forecast) && (
        <div className="absolute top-4 left-4 z-20 flex flex-col gap-1.5 pointer-events-auto font-sans">
          <div className="liquid-glass border border-white/15 backdrop-blur-2xl rounded-2xl shadow-2xl p-4 text-slate-100">
            <div className="text-[10px] text-slate-400 uppercase tracking-widest font-bold mb-2.5 font-heading">
              Forward Forecast Time
            </div>
            <div className="flex gap-2">
              {([6, 12, 24, 48] as const).map((h) => {
                const isActive = forecastHours === h;
                return (
                  <button
                    key={h}
                    onClick={() => setForecastHours(h)}
                    className={`
                      flex flex-col items-center px-3.5 py-2 rounded-xl text-xs font-sans font-bold transition-all
                      ${isActive
                        ? 'liquid-glass border border-white/30 text-white shadow-lg bg-white/[0.12]'
                        : 'liquid-glass-subtle border border-white/10 text-slate-300 hover:border-white/20 hover:text-white'
                      }
                    `}
                  >
                    <span className="text-[13px] font-extrabold leading-tight">+{h}H</span>
                  </button>
                );
              })}
            </div>
            {activeForwardSnapshot && (
              <div className="mt-3 pt-2 border-t border-white/10 text-[11px] text-slate-300 flex items-center justify-between font-sans">
                <div>Centroid: <span className="text-slate-200 font-mono font-semibold">{activeForwardSnapshot.centroid.lat.toFixed(3)}°N, {activeForwardSnapshot.centroid.lon.toFixed(3)}°E</span></div>
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
              className="w-full mt-3 accent-blue-500 cursor-pointer h-1.5 bg-white/10 rounded-lg appearance-none"
            />
          </div>
        </div>
      )}



      {/* Hydrodynamic & Environmental Legend Overlay */}
      <div className="absolute bottom-3 right-3 z-10 liquid-glass border border-white/15 text-slate-100 p-4 font-sans text-xs shadow-2xl backdrop-blur-2xl rounded-2xl space-y-2">
        <div className="text-slate-300 uppercase pb-1.5 border-b border-white/10 mb-1 text-[10px] flex items-center justify-between gap-4 font-bold tracking-wider">
          <span>HYDRODYNAMIC FORCING</span>
          <span className="text-slate-300 font-bold">ECMWF ERA5 / CMEMS</span>
        </div>
        {data?.origin_estimate?.forcing_used ? (
          <div className="space-y-0.5 text-slate-200 text-[11px]">
            <div>WIND: <strong className="text-white font-mono">{data.origin_estimate.forcing_used.wind_speed_ms} m/s @ {data.origin_estimate.forcing_used.wind_direction_deg}°</strong></div>
            <div>CURRENT: <strong className="text-white font-mono">{data.origin_estimate.forcing_used.current_speed_ms} m/s @ {data.origin_estimate.forcing_used.current_direction_deg}°</strong></div>
          </div>
        ) : (
          <div className="text-slate-200 font-mono text-[11px] py-0.5 font-semibold">ERA5 Wind: 2.56 m/s @ 325° | CMEMS Current: 0.35 m/s @ 75°</div>
        )}
        <div className="pt-1.5 border-t border-white/10 text-[10px] text-slate-300 flex items-center gap-3 font-medium">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-slate-400 shadow-sm"></span> DARTIS Reference</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500 shadow-sm"></span> Origin Zone</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-rose-500 shadow-sm"></span> Ship Tracks</span>
        </div>
      </div>
    </div>
  );
};
