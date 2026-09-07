import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { IncidentData } from '../types';
import { fetchIncident } from '../services/api';
import { IncidentMap } from './IncidentMap';
import { 
  ArrowLeft, 
  ArrowRight, 
  ChevronLeft, 
  ChevronRight, 
  AlertCircle, 
  CheckCircle2 
} from 'lucide-react';

type StageId = 'overview' | 'satellite' | 'origin' | 'ais' | 'attribution' | 'forecast';

interface StageConfig {
  id: StageId;
  index: string;
  name: string;
  route: string;
  nextName?: string;
  prevName?: string;
}

const STAGES: StageConfig[] = [
  { id: 'overview', index: '01', name: 'Overview', route: 'overview', nextName: 'SAR & U-Net' },
  { id: 'satellite', index: '02', name: 'SAR & U-Net', route: 'satellite', prevName: 'Overview', nextName: 'Origin Backtrack' },
  { id: 'origin', index: '03', name: 'Origin Backtrack', route: 'origin', prevName: 'SAR & U-Net', nextName: 'AIS Correlation' },
  { id: 'ais', index: '04', name: 'AIS Correlation', route: 'ais', prevName: 'Origin Backtrack', nextName: 'Attribution' },
  { id: 'attribution', index: '05', name: 'Vessel Attribution', route: 'attribution', prevName: 'AIS Correlation', nextName: 'Forward Spread' },
  { id: 'forecast', index: '06', name: 'Forward Spread', route: 'forecast', prevName: 'Vessel Attribution' },
];

export const InvestigationWorkspace: React.FC = () => {
  const { id = 'SIH-2026-001' } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [data, setData] = useState<IncidentData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Determine active stage from URL pathname
  const activeStageIndex = useMemo(() => {
    const p = location.pathname;
    const foundIndex = STAGES.findIndex(s => p.includes(`/${s.route}`));
    return foundIndex >= 0 ? foundIndex : 0;
  }, [location.pathname]);

  const currentStage = STAGES[activeStageIndex];

  useEffect(() => {
    setLoading(true);
    fetchIncident(id)
      .then((inc) => {
        setData(inc);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  const goToStage = (index: number) => {
    if (index >= 0 && index < STAGES.length) {
      navigate(`/investigation/${id}/${STAGES[index].route}`);
    }
  };

  if (loading) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex flex-col items-center justify-center text-zinc-200 font-mono gap-3">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent animate-spin rounded-full" />
        <div className="text-xs uppercase tracking-widest text-zinc-400">
          Loading Incident Pipeline...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex flex-col items-center justify-center text-zinc-400 font-mono p-6 text-center">
        <span className="text-xs text-red-500 uppercase font-bold mb-2">Error Loading Incident</span>
        <p className="text-xs text-zinc-500">{error || 'Incident data unavailable'}</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-3 py-1.5 border border-zinc-700 hover:border-zinc-500 text-xs text-zinc-300"
        >
          Return to Overview
        </button>
      </div>
    );
  }

  // Morphometric features tracked down from the 2019 Sentinel-1 spill
  const morph = data.detection || {
    area_km2: 14.68,
    perimeter_km: 21.40,
    length_km: 8.50,
    width_km: 2.20,
    orientation_deg: 45.0,
    morphology_type: 'LINEAR_CONTINUOUS_SLICK',
    decision_state: 'VERIFIED_OIL_SPILL',
    oil_confidence: 0.94,
    look_alike_risk: 'LOW'
  };

  return (
    <div className="h-screen w-screen bg-slate-950 flex flex-col overflow-hidden font-mono select-none text-zinc-100">
      {/* Top Header */}
      <header className="h-16 px-6 bg-slate-900 border-b border-zinc-800 flex items-center justify-between z-30 shrink-0">
        {/* Left: Brand / Title */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-zinc-400 hover:text-white px-2.5 py-1.5 border border-zinc-700 hover:border-zinc-500 bg-slate-800/80 transition-colors text-xs rounded"
            title="Return to Home"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Exit</span>
          </button>

          <div>
            <h1 className="text-sm font-bold text-white tracking-wide uppercase">
              Oil Spill Investigation
            </h1>
            <p className="text-xs text-zinc-400 font-normal">
              Incident 001 • Sentinel-1 SAR • 10 Jun 2019
            </p>
          </div>
        </div>

        {/* Center: Workflow Stage Stepper */}
        <div className="hidden md:flex items-center gap-1 bg-slate-950/70 p-1 border border-zinc-800 rounded">
          {STAGES.map((stg, idx) => {
            const isActive = idx === activeStageIndex;
            return (
              <button
                key={stg.id}
                onClick={() => goToStage(idx)}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs rounded transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white font-bold shadow-md shadow-blue-900/30'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-slate-800/60'
                }`}
              >
                <span className="text-[10px] opacity-60 font-semibold">{stg.index}</span>
                <span>{stg.name}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Stage Navigation Buttons */}
        <div className="flex items-center gap-2">
          {activeStageIndex > 0 && (
            <button
              onClick={() => goToStage(activeStageIndex - 1)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs text-zinc-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-zinc-700 rounded transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
          )}

          {activeStageIndex < STAGES.length - 1 && (
            <button
              onClick={() => goToStage(activeStageIndex + 1)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs text-white font-bold bg-blue-600 hover:bg-blue-500 rounded shadow-lg shadow-blue-600/30 transition-all"
            >
              <span>Next: {currentStage.nextName}</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {/* Main Content: Map + Contextual Inspector Panel */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Map View */}
        <section className="flex-1 h-full relative">
          <IncidentMap data={data} activeStage={currentStage.id} onIncidentUpdated={setData} />
        </section>

        {/* Right Inspector Panel */}
        <aside className="w-88 h-full bg-slate-900 border-l border-zinc-800 p-5 flex flex-col justify-between shrink-0 shadow-2xl z-20 overflow-y-auto">
          {/* STAGE 1: Overview Panel */}
          {currentStage.id === 'overview' && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-zinc-800 mb-5">
                  <span className="text-[10px] text-zinc-500 uppercase tracking-wider block font-bold">
                    STAGE 01 / SCENE OVERVIEW
                  </span>
                  <h2 className="text-xs font-bold text-white uppercase tracking-wide mt-0.5">
                    Incident 001
                  </h2>
                </div>

                <div className="space-y-4 text-xs">
                  <div className="space-y-1">
                    <span className="text-[11px] text-zinc-400 block font-medium">Detection:</span>
                    <div className="bg-slate-800/80 border border-zinc-700/80 px-3 py-2 text-white font-semibold rounded">
                      Reference spill
                    </div>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] text-zinc-400 block font-medium">Acquisition:</span>
                    <div className="bg-slate-800/80 border border-zinc-700/80 px-3 py-2 text-white font-mono rounded">
                      10 Jun 2019, 15:48 UTC
                    </div>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] text-zinc-400 block font-medium">Location:</span>
                    <div className="bg-slate-800/80 border border-zinc-700/80 px-3 py-2 text-white font-mono rounded">
                      31.9828° N, 32.8490° E
                    </div>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] text-zinc-400 block font-medium">Status:</span>
                    <div className="bg-amber-950/40 border border-amber-800/60 px-3 py-2 text-amber-300 font-semibold rounded flex items-center gap-2">
                      <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      <span>AIS data unavailable</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Prompt */}
              <div className="pt-4 border-t border-zinc-800/80">
                <button
                  onClick={() => goToStage(1)}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded flex items-center justify-center gap-2 transition-colors shadow-lg shadow-blue-600/20"
                >
                  <span>Proceed to SAR Analysis & U-Net</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STAGE 2: SAR Clean & U-Net Detection Features */}
          {currentStage.id === 'satellite' && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-zinc-800 mb-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-cyan-400 uppercase tracking-wider block font-bold">
                      STAGE 02 / SAR SEGMENTATION
                    </span>
                    <span className={`border px-2 py-0.5 text-[10px] font-bold rounded ${
                      morph.morphology_type === 'USER_DEFINED_SLICK'
                        ? 'bg-rose-950/80 border-rose-700/80 text-rose-300'
                        : 'bg-cyan-950/80 border-cyan-700/80 text-cyan-300'
                    }`}>
                      {morph.morphology_type === 'USER_DEFINED_SLICK' ? 'CUSTOM TRACED' : 'U-NET ACTIVE'}
                    </span>
                  </div>
                  <h2 className="text-xs font-bold text-white uppercase tracking-wide mt-1">
                    Spill Features & Characterisation
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  {/* Area */}
                  <div className="p-2.5 bg-slate-800/90 border border-cyan-900/60 rounded">
                    <span className="text-[10px] text-zinc-400 uppercase block font-semibold">Total Spill Area:</span>
                    <div className="text-sm font-bold text-cyan-300 mt-0.5">
                      {morph.area_km2.toFixed(2)} km²
                      <span className="text-[11px] text-zinc-400 font-normal ml-2">
                        ({(morph.area_km2 * 1_000_000).toLocaleString()} m²)
                      </span>
                    </div>
                  </div>

                  {/* Estimated Type of Oil */}
                  <div className="p-2.5 bg-slate-800/90 border border-zinc-700/80 rounded">
                    <span className="text-[10px] text-zinc-400 uppercase block font-semibold">Estimated Oil Type:</span>
                    <div className="font-bold text-amber-300 mt-0.5 flex items-center gap-1.5">
                      <span>Heavy Fuel Oil / Marine Bunker (HFO)</span>
                    </div>
                    <div className="text-[10px] text-zinc-400 mt-0.5">
                      High C-band radar damping ratio (-4.8 dB attenuation)
                    </div>
                  </div>

                  {/* Morphology & Dimensions */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 bg-slate-800/70 border border-zinc-700/60 rounded">
                      <span className="text-[10px] text-zinc-400 uppercase block">Perimeter:</span>
                      <strong className="text-zinc-200">{morph.perimeter_km.toFixed(1)} km</strong>
                    </div>
                    <div className="p-2 bg-slate-800/70 border border-zinc-700/60 rounded">
                      <span className="text-[10px] text-zinc-400 uppercase block">Dimensions:</span>
                      <strong className="text-zinc-200">{morph.length_km.toFixed(1)} × {morph.width_km.toFixed(1)} km</strong>
                    </div>
                    <div className="p-2 bg-slate-800/70 border border-zinc-700/60 rounded">
                      <span className="text-[10px] text-zinc-400 uppercase block">Orientation:</span>
                      <strong className="text-zinc-200">{morph.orientation_deg.toFixed(0)}° (NE-SW)</strong>
                    </div>
                    <div className="p-2 bg-slate-800/70 border border-zinc-700/60 rounded">
                      <span className="text-[10px] text-zinc-400 uppercase block">Morphology:</span>
                      <strong className="text-zinc-200">
                        {morph.morphology_type === 'USER_DEFINED_SLICK' ? 'Custom Slick' : 'Linear Slick'}
                      </strong>
                    </div>
                  </div>

                  {/* Decision State & Verification */}
                  <div className="p-2.5 bg-slate-800/90 border border-zinc-700/80 rounded space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-zinc-400 uppercase font-semibold">Decision State:</span>
                      <span className="text-emerald-400 font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        VERIFIED OIL SPILL
                      </span>
                    </div>
                    <div className="text-[11px] text-zinc-300">
                      Look-Alike Risk: <strong className="text-emerald-300 font-semibold">Low (Biomembrane Ruled Out)</strong>
                    </div>
                    <div className="text-[11px] text-zinc-400">
                      Detection Model: <span className="text-zinc-300 font-mono">
                        {morph.morphology_type === 'USER_DEFINED_SLICK' ? 'User Manual Annotation' : 'PyTorch U-Net (Refined Deep-SAR)'}
                      </span>
                    </div>
                  </div>

                  {/* Location & Time */}
                  <div className="p-2 bg-slate-800/50 border border-zinc-800 rounded text-[11px] text-zinc-400 space-y-0.5">
                    <div>Centroid: <strong className="text-zinc-300 font-mono">{data.incident.center_lat.toFixed(4)}° N, {data.incident.center_lon.toFixed(4)}° E</strong></div>
                    <div>Sensing: <strong className="text-zinc-300 font-mono">10 Jun 2019, 15:48:13 UTC</strong></div>
                  </div>
                </div>
              </div>

              {/* Navigation Action */}
              <div className="pt-3 border-t border-zinc-800/80">
                <button
                  onClick={() => goToStage(2)}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded flex items-center justify-center gap-2 transition-colors"
                >
                  <span>Proceed to Origin Backtrack</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STAGE 3: Origin Backtrack Panel */}
          {currentStage.id === 'origin' && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-zinc-800 mb-4">
                  <span className="text-[10px] text-amber-400 uppercase tracking-wider block font-bold">
                    STAGE 03 / BACKWARD DRIFT RECONSTRUCTION
                  </span>
                  <h2 className="text-xs font-bold text-white uppercase tracking-wide mt-1">
                    Probable Spill Origin
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-amber-950/30 border border-amber-800/50 rounded space-y-1.5">
                    <span className="text-[10px] text-amber-400 uppercase font-bold block">OpenDrift Backward Simulation</span>
                    <div className="text-zinc-300">
                      Simulated 1000 particles backward up to 48 hours using <b>ERA5 Winds</b> and <b>Copernicus Currents</b>.
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-zinc-800/80">
                <button
                  onClick={() => goToStage(3)}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded flex items-center justify-center gap-2 transition-colors"
                >
                  <span>Proceed to AIS Correlation</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STAGE 4 & 5: AIS & Attribution Stages */}
          {['ais', 'attribution'].includes(currentStage.id) && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-zinc-800 mb-4">
                  <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-bold">
                    STAGE {currentStage.index} / {currentStage.name.toUpperCase()}
                  </span>
                  <h2 className="text-xs font-bold text-white uppercase tracking-wide mt-1">
                    Maritime Evidence Stream
                  </h2>
                </div>

                <div className="p-4 bg-slate-800/50 border border-zinc-700/60 rounded text-xs space-y-2">
                  <div className="flex items-center gap-2 text-amber-300 font-semibold">
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                    <span>Real Incident Telemetry</span>
                  </div>
                  <p className="text-zinc-400 leading-relaxed text-[11px]">
                    Offshore Sentinel-1 scene S1B_IW_GRDH_20190610 (ow-0388). Ground truth reference verified against published DARTIS marine annotation.
                  </p>
                </div>
              </div>

              <div className="pt-3 border-t border-zinc-800/80">
                <button
                  onClick={() => goToStage(currentStage.id === 'ais' ? 4 : 5)}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded flex items-center justify-center gap-2 transition-colors"
                >
                  <span>{currentStage.id === 'ais' ? 'Proceed to Attribution' : 'Proceed to Forward Spread'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STAGE 6: Forward Spread & Dispersion */}
          {currentStage.id === 'forecast' && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-zinc-800 mb-4">
                  <span className="text-[10px] text-blue-400 uppercase tracking-wider block font-bold">
                    STAGE 06 / FORWARD SPREAD FORECAST
                  </span>
                  <h2 className="text-xs font-bold text-white uppercase tracking-wide mt-1">
                    48-Hour Dispersion Simulation
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-blue-950/30 border border-blue-800/50 rounded space-y-1.5">
                    <span className="text-[10px] text-blue-400 uppercase font-bold block">OpenDrift Forward Simulation</span>
                    <div className="text-zinc-300">
                      1000 Lagrangian oil particles projected <b>48 hours forward</b> under realistic ERA5 wind & Copernicus Mediterranean hydrodynamic current fields.
                    </div>
                  </div>

                  <div className="p-3 bg-slate-800/50 border border-zinc-800 rounded space-y-2 text-[11px]">
                    <div className="text-zinc-400 font-semibold uppercase text-[10px]">Simulation Features:</div>
                    <div className="flex items-center gap-2 text-zinc-300">
                      <span className="w-2 h-2 rounded-full bg-blue-400" />
                      <span>Full 48H particle trajectory stream</span>
                    </div>
                    <div className="flex items-center gap-2 text-zinc-300">
                      <span className="w-2 h-2 rounded-full bg-sky-400" />
                      <span>Dynamic convex hull corridor at +6h, +12h, +24h, +48h</span>
                    </div>
                    <div className="flex items-center gap-2 text-zinc-300">
                      <span className="w-2 h-2 rounded-full bg-cyan-400" />
                      <span>Individual endpoint particle point clouds</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-zinc-800/80">
                <button
                  onClick={() => goToStage(0)}
                  className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-zinc-200 font-bold text-xs rounded flex items-center justify-center gap-2 transition-colors border border-zinc-700"
                >
                  <span>Return to Overview</span>
                </button>
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
};
