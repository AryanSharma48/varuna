import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { IncidentData } from '../types';
import { fetchIncident } from '../services/api';
import { IncidentMap } from './IncidentMap';
import { ForwardThreatAssessment } from './ForwardThreatAssessment';
import { VesselAttributionPanel } from './VesselAttributionPanel';
import { 
  ArrowLeft, 
  ArrowRight, 
  ChevronLeft, 
  ChevronRight, 
  CheckCircle2,
  FileText,
  Bot
} from 'lucide-react';
import { InvestigationReportResponse } from '../types';
import { generateReport } from '../services/api';
import { ReportModal } from './ReportModal';
import { AIInvestigatorModal } from './AIInvestigatorModal';

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
  const { id = 'VARUNA-2026-001' } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [data, setData] = useState<IncidentData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Report Modal state
  const [reportModalOpen, setReportModalOpen] = useState<boolean>(false);
  const [reportData, setReportData] = useState<InvestigationReportResponse | null>(null);
  const [generatingReport, setGeneratingReport] = useState<boolean>(false);
  const [aiModalOpen, setAiModalOpen] = useState<boolean>(false);

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setReportModalOpen(true);
    try {
      const res = await generateReport(id);
      setReportData(res);
    } catch (err: any) {
      console.error('Report generation error:', err);
    } finally {
      setGeneratingReport(false);
    }
  };

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
      <div className="h-screen w-screen bg-[#060c18] flex flex-col items-center justify-center text-slate-200 font-sans gap-3">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent animate-spin rounded-full" />
        <div className="text-xs uppercase tracking-widest text-slate-400 font-semibold">
          Loading Incident Pipeline...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-screen w-screen bg-[#060c18] flex flex-col items-center justify-center text-slate-300 font-sans p-6 text-center">
        <div className="liquid-glass border border-white/10 p-8 rounded-2xl max-w-sm w-full flex flex-col items-center shadow-2xl">
          <span className="text-xs text-rose-400 uppercase font-bold mb-2">Error Loading Incident</span>
          <p className="text-xs text-slate-400 mb-4">{error || 'Incident data unavailable'}</p>
          <button
            onClick={() => navigate('/')}
            className="w-full py-2.5 px-4 bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 text-xs font-semibold text-slate-200 hover:text-white rounded-xl transition-all shadow-sm"
          >
            Return to Overview
          </button>
        </div>
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
    <div className="h-screen w-screen bg-[#060c18] flex flex-col overflow-hidden font-sans select-none text-slate-100">
      {/* Top Header */}
      <header className="h-16 px-6 bg-[#060c18]/85 backdrop-blur-2xl border-b border-white/[0.08] flex items-center justify-between z-30 shrink-0 shadow-[0_4px_30px_rgba(0,0,0,0.3)]">
        {/* Left: Brand / Title */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-slate-300 hover:text-white px-3 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.12] border border-white/[0.08] backdrop-blur-md transition-all text-xs font-semibold shadow-sm hover:shadow-white/5"
            title="Return to Home"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Exit</span>
          </button>

          <div className="flex items-center gap-3">
            <span 
              className="text-2xl font-bold font-amita select-none bg-clip-text text-transparent hidden sm:inline-block leading-none"
              style={{ 
                fontFamily: "'Amita', cursive",
                backgroundImage: 'linear-gradient(180deg, #60a5fa, #1d4ed8)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                color: 'transparent'
              }}
            >
              वरुण
            </span>
            <div className="h-5 w-px bg-white/10 hidden sm:block" />
            <div>
              <h1 className="text-xs font-bold text-white tracking-wider uppercase font-heading">
                Oil Spill Investigation
              </h1>
              <p className="text-[11px] text-slate-400 font-normal">
                Incident 001 • Sentinel-1 SAR • 10 Jun 2019
              </p>
            </div>
          </div>
        </div>

        {/* Center: Workflow Stage Stepper */}
        <div className="hidden md:flex items-center gap-1 bg-white/[0.04] p-1 border border-white/[0.08] rounded-2xl backdrop-blur-xl shadow-inner">
          {STAGES.map((stg, idx) => {
            const isActive = idx === activeStageIndex;
            return (
              <button
                key={stg.id}
                onClick={() => goToStage(idx)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs rounded-xl transition-all ${
                  isActive
                    ? 'liquid-glass text-white font-bold shadow-md shadow-blue-500/20'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.06] font-medium'
                }`}
              >
                <span className="text-[10px] opacity-70 font-semibold">{stg.index}</span>
                <span>{stg.name}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Stage Navigation Buttons */}
        <div className="flex items-center gap-2">
          {/* AI Investigator Header Button */}
          <button
            onClick={() => setAiModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 text-xs text-cyan-200 hover:text-white font-bold bg-cyan-950/40 hover:bg-cyan-900/60 border border-cyan-400/40 hover:border-cyan-300 rounded-xl shadow-lg shadow-cyan-500/15 hover:shadow-cyan-500/30 transition-all cursor-pointer group mr-1"
            title="Open AI Investigator Chatbot (Groq Powered)"
          >
            <div className="relative flex items-center justify-center">
              <Bot className="w-3.5 h-3.5 text-cyan-400 group-hover:rotate-12 transition-transform" />
              <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
            </div>
            <span>AI Investigator</span>
            <span className="px-1.5 py-0.5 rounded bg-cyan-400/20 text-[9px] font-mono text-cyan-300 border border-cyan-400/30 hidden sm:inline">
              LLM
            </span>
          </button>

          <div className="h-4 w-px bg-white/10 hidden sm:block" />

          {activeStageIndex > 0 && (
            <button
              onClick={() => goToStage(activeStageIndex - 1)}
              className="flex items-center gap-1 px-3.5 py-1.5 text-xs font-semibold text-slate-300 hover:text-white bg-white/[0.05] hover:bg-white/[0.12] border border-white/[0.08] rounded-xl backdrop-blur-md transition-all shadow-sm"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
          )}

          {activeStageIndex < STAGES.length - 1 ? (
            <button
              onClick={() => goToStage(activeStageIndex + 1)}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs text-white font-bold bg-blue-600 hover:bg-blue-500 rounded-xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5 transition-all"
            >
              <span>Next: {currentStage.nextName}</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleGenerateReport}
              disabled={generatingReport}
              className="flex items-center gap-2 px-4 py-1.5 text-xs text-white font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5 transition-all border border-blue-400/30"
              title="Generate Official Preliminary Investigation Report"
            >
              <FileText className="w-3.5 h-3.5 text-blue-200" />
              <span>{generatingReport ? 'Generating...' : 'Generate Report'}</span>
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
        <aside className="w-96 h-full bg-[#060c18]/90 backdrop-blur-2xl border-l border-white/[0.08] p-6 flex flex-col justify-between shrink-0 shadow-2xl z-20 overflow-y-auto">
          {/* STAGE 1: Overview Panel */}
          {currentStage.id === 'overview' && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-white/[0.08] mb-5">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-slate-300 text-[10px] font-medium tracking-wider uppercase mb-1.5">
                    STAGE 01 / SCENE OVERVIEW
                  </span>
                  <h2 className="text-sm font-bold text-white uppercase tracking-wide font-heading">
                    Incident 001
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-3.5 rounded-2xl liquid-glass-subtle border border-white/[0.06] space-y-1">
                    <span className="text-[11px] text-slate-400 block font-medium">Detection:</span>
                    <div className="text-white font-semibold text-xs">
                      Reference spill
                    </div>
                  </div>

                  <div className="p-3.5 rounded-2xl liquid-glass-subtle border border-white/[0.06] space-y-1">
                    <span className="text-[11px] text-slate-400 block font-medium">Acquisition:</span>
                    <div className="text-slate-200 font-mono text-xs">
                      10 Jun 2019, 15:48 UTC
                    </div>
                  </div>

                  <div className="p-3.5 rounded-2xl liquid-glass-subtle border border-white/[0.06] space-y-1">
                    <span className="text-[11px] text-slate-400 block font-medium">Location:</span>
                    <div className="text-slate-200 font-mono text-xs">
                      31.9828° N, 32.8490° E
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Prompt */}
              <div className="pt-4 border-t border-white/[0.08]">
                <button
                  onClick={() => goToStage(1)}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
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
                <div className="pb-3 border-b border-white/[0.08] mb-4">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-slate-300 text-[10px] font-medium tracking-wider uppercase">
                      STAGE 02 / SAR SEGMENTATION
                    </span>
                    <span className="px-2.5 py-0.5 text-[10px] font-medium rounded-full bg-white/[0.05] border border-white/10 text-slate-300">
                      {morph.morphology_type === 'USER_DEFINED_SLICK' ? 'CUSTOM TRACED' : 'U-NET ACTIVE'}
                    </span>
                  </div>
                  <h2 className="text-sm font-bold text-white uppercase tracking-wide mt-2 font-heading">
                    Spill Features & Characterisation
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  {/* Area */}
                  <div className="p-3.5 rounded-2xl liquid-glass-subtle border border-white/[0.06]">
                    <span className="text-[10px] text-slate-400 uppercase block font-semibold">Total Spill Area:</span>
                    <div className="text-base font-extrabold text-white mt-0.5">
                      {morph.area_km2.toFixed(2)} km²
                      <span className="text-xs text-slate-400 font-normal ml-2">
                        ({(morph.area_km2 * 1_000_000).toLocaleString()} m²)
                      </span>
                    </div>
                  </div>

                  {/* Estimated Type of Oil */}
                  <div className="p-3 rounded-2xl liquid-glass-subtle border border-white/[0.06]">
                    <span className="text-[10px] text-slate-400 uppercase block font-semibold">Estimated Oil Type:</span>
                    <div className="font-semibold text-slate-200 mt-0.5 flex items-center gap-1.5 text-xs">
                      <span>Heavy Fuel Oil / Marine Bunker (HFO)</span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      High C-band radar damping ratio (-4.8 dB attenuation)
                    </div>
                  </div>

                  {/* Morphology & Dimensions */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2.5 rounded-xl liquid-glass-subtle border border-white/[0.06]">
                      <span className="text-[10px] text-slate-400 uppercase block font-medium">Perimeter:</span>
                      <strong className="text-slate-100 text-xs">{morph.perimeter_km.toFixed(1)} km</strong>
                    </div>
                    <div className="p-2.5 rounded-xl liquid-glass-subtle border border-white/[0.06]">
                      <span className="text-[10px] text-slate-400 uppercase block font-medium">Dimensions:</span>
                      <strong className="text-slate-100 text-xs">{morph.length_km.toFixed(1)} × {morph.width_km.toFixed(1)} km</strong>
                    </div>
                    <div className="p-2.5 rounded-xl liquid-glass-subtle border border-white/[0.06]">
                      <span className="text-[10px] text-slate-400 uppercase block font-medium">Orientation:</span>
                      <strong className="text-slate-100 text-xs">{morph.orientation_deg.toFixed(0)}° (NE-SW)</strong>
                    </div>
                    <div className="p-2.5 rounded-xl liquid-glass-subtle border border-white/[0.06]">
                      <span className="text-[10px] text-slate-400 uppercase block font-medium">Morphology:</span>
                      <strong className="text-slate-100 text-xs">
                        {morph.morphology_type === 'USER_DEFINED_SLICK' ? 'Custom Slick' : 'Linear Slick'}
                      </strong>
                    </div>
                  </div>

                  {/* Decision State & Verification */}
                  <div className="p-3 rounded-2xl liquid-glass-subtle border border-white/10 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Decision State:</span>
                      <span className="text-slate-200 font-semibold flex items-center gap-1.5 text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 text-slate-300" />
                        VERIFIED OIL SPILL
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-300">
                      Look-Alike Risk: <strong className="text-slate-200 font-semibold">Low (Biomembrane Ruled Out)</strong>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Detection Model: <span className="text-slate-300 font-mono text-[10px]">
                        {morph.morphology_type === 'USER_DEFINED_SLICK' ? 'User Manual Annotation' : 'PyTorch U-Net (Refined Deep-SAR)'}
                      </span>
                    </div>
                  </div>

                  {/* Location & Time */}
                  <div className="p-2.5 rounded-xl liquid-glass-subtle border border-white/[0.06] text-[11px] text-slate-400 space-y-0.5">
                    <div>Centroid: <strong className="text-slate-200 font-mono">{data.incident.center_lat.toFixed(4)}° N, {data.incident.center_lon.toFixed(4)}° E</strong></div>
                    <div>Sensing: <strong className="text-slate-200 font-mono">10 Jun 2019, 15:48:13 UTC</strong></div>
                  </div>
                </div>
              </div>

              {/* Navigation Action */}
              <div className="pt-3 border-t border-white/[0.08]">
                <button
                  onClick={() => goToStage(2)}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
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
                <div className="pb-3 border-b border-white/[0.08] mb-4">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-slate-300 text-[10px] font-medium tracking-wider uppercase mb-1.5">
                    STAGE 03 / BACKWARD DRIFT RECONSTRUCTION
                  </span>
                  <h2 className="text-sm font-bold text-white uppercase tracking-wide font-heading">
                    Probable Spill Origin
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-4 rounded-2xl liquid-glass-subtle border border-white/10 space-y-1.5">
                    <span className="text-[10px] text-slate-300 uppercase font-semibold block">OpenDrift Backward Simulation</span>
                    <div className="text-slate-300 text-xs leading-relaxed">
                      Simulated 1000 particles backward up to 48 hours using <b>ERA5 Winds</b> and <b>Copernicus Currents</b>.
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-white/[0.08]">
                <button
                  onClick={() => goToStage(3)}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
                >
                  <span>Proceed to AIS Correlation</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STAGE 4: AIS Spatio-Temporal Correlation */}
          {currentStage.id === 'ais' && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-white/[0.08] mb-4">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-slate-300 text-[10px] font-medium tracking-wider uppercase mb-1.5">
                    STAGE 04 / AIS CORRELATION
                  </span>
                  <h2 className="text-sm font-bold text-white uppercase tracking-wide font-heading">
                    Spatio-Temporal Vessel Traffic
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-3.5 rounded-2xl liquid-glass-subtle border border-white/[0.06] space-y-1.5">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Spatio-Temporal Search Window</span>
                    <div className="text-slate-200 text-xs leading-relaxed">
                      Correlating all historical AIS trajectories intersecting within 35 km of probable spill release origin between 13:45 and 15:45 UTC.
                    </div>
                  </div>

                  <div className="p-3.5 rounded-2xl liquid-glass-subtle border border-white/[0.06] space-y-2">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Correlated Candidates (3 Vessels):</span>
                    {data?.attribution_scores?.map((v) => (
                      <div key={v.mmsi} className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                        <div>
                          <div className="font-bold text-white text-xs">{v.vessel_name}</div>
                          <div className="text-[10px] text-slate-400">{v.vessel_type} • {v.flag}</div>
                        </div>
                        <span className="text-xs font-mono font-bold text-slate-300">
                          MMSI {v.mmsi}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-white/[0.08]">
                <button
                  onClick={() => goToStage(4)}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
                >
                  <span>Proceed to Attribution Scoring</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STAGE 5: Vessel Attribution Scoring & Comparison */}
          {currentStage.id === 'attribution' && (
            <div className="flex flex-col justify-between h-full">
              <div className="space-y-4">
                <div className="pb-3 border-b border-white/[0.08]">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-slate-300 text-[10px] font-medium tracking-wider uppercase mb-1.5">
                    STAGE 05 / VESSEL ATTRIBUTION
                  </span>
                  <h2 className="text-sm font-bold text-white uppercase tracking-wide font-heading">
                    Rankwise Vessel Attribution
                  </h2>
                </div>

                {/* Vessel Attribution Comparison Panel */}
                <VesselAttributionPanel data={data} />
              </div>

              <div className="pt-3 border-t border-white/[0.08]">
                <button
                  onClick={() => goToStage(5)}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
                >
                  <span>Proceed to Forward Spread</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* STAGE 6: Forward Spread & Dispersion */}
          {currentStage.id === 'forecast' && (
            <div className="flex flex-col justify-between h-full">
              <div>
                <div className="pb-3 border-b border-white/[0.08] mb-4">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-slate-300 text-[10px] font-medium tracking-wider uppercase mb-1.5">
                    STAGE 06 / FORWARD SPREAD FORECAST
                  </span>
                  <h2 className="text-sm font-bold text-white uppercase tracking-wide font-heading">
                    48-Hour Dispersion Simulation
                  </h2>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-4 rounded-2xl liquid-glass-subtle border border-white/10 space-y-1.5">
                    <span className="text-[10px] text-slate-300 uppercase font-semibold block">OpenDrift Forward Simulation</span>
                    <div className="text-slate-300 text-xs leading-relaxed">
                      1000 Lagrangian oil particles projected <b>48 hours forward</b> under realistic ERA5 wind & Copernicus Mediterranean hydrodynamic current fields.
                    </div>
                  </div>

                  {/* Dynamic Coastal, Fishery, EEZ & Endangered Habitat Assessment */}
                  <ForwardThreatAssessment data={data} />
                </div>
              </div>

              <div className="pt-3 border-t border-white/[0.08] space-y-2">
                <button
                  onClick={handleGenerateReport}
                  disabled={generatingReport}
                  className="w-full py-3 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-500 hover:from-blue-500 hover:to-indigo-400 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
                >
                  <FileText className="w-4 h-4" />
                  <span>{generatingReport ? 'Assembling Report...' : 'Generate Final Investigation Report'}</span>
                </button>

                <button
                  onClick={() => goToStage(0)}
                  className="w-full py-2.5 bg-white/[0.06] hover:bg-white/[0.12] text-slate-200 hover:text-white font-semibold text-xs rounded-xl flex items-center justify-center gap-2 transition-all border border-white/10 backdrop-blur-md shadow-sm"
                >
                  <span>Return to Overview</span>
                </button>
              </div>
            </div>
          )}
        </aside>
      </main>

      {/* Official Investigation Report Modal */}
      <ReportModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        reportData={reportData}
        loading={generatingReport}
        incidentId={id}
      />

      {/* Grounded AI Investigator Modal */}
      <AIInvestigatorModal
        isOpen={aiModalOpen}
        onClose={() => setAiModalOpen(false)}
        incidentId={id}
      />
    </div>
  );
};
