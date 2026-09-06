import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { IncidentData, CandidateVessel } from '../types';
import { fetchIncident, traceOrigin, forecastSpill, analyzeSAR } from '../services/api';
import { Header } from './Header';
import { SubrouteNav } from './SubrouteNav';
import { IncidentMap } from './IncidentMap';
import { TimelineSlider } from './TimelineSlider';
import { CandidateVesselsPanel } from './CandidateVesselsPanel';
import { SpillCharacterisationPanel } from './SpillCharacterisationPanel';
import { ForecastImpactPanel } from './ForecastImpactPanel';
import { EvidenceFusionPanel } from './EvidenceFusionPanel';
import { InvestigationAssistant } from './InvestigationAssistant';
import { ReportModal } from './ReportModal';
import { 
  MapPin, 
  TrendingUp,
  Sparkles 
} from 'lucide-react';

export const InvestigationWorkspace: React.FC = () => {
  const { id = 'SIH-2026-001' } = useParams();
  const location = useLocation();

  const [data, setData] = useState<IncidentData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedVessel, setSelectedVessel] = useState<CandidateVessel | null>(null);
  const [timelineMinutes, setTimelineMinutes] = useState<number>(240);

  const [isAssistantOpen, setIsAssistantOpen] = useState<boolean>(false);
  const [isReportOpen, setIsReportOpen] = useState<boolean>(false);

  const [isTracing, setIsTracing] = useState<boolean>(false);
  const [isForecasting, setIsForecasting] = useState<boolean>(false);

  const pathname = location.pathname;
  let activeView: 'overview' | 'satellite' | 'origin' | 'ais' | 'attribution' | 'forecast' = 'overview';
  if (pathname.includes('/satellite')) activeView = 'satellite';
  else if (pathname.includes('/origin')) activeView = 'origin';
  else if (pathname.includes('/ais')) activeView = 'ais';
  else if (pathname.includes('/attribution')) activeView = 'attribution';
  else if (pathname.includes('/forecast')) activeView = 'forecast';

  useEffect(() => {
    setLoading(true);
    fetchIncident(id)
      .then((inc) => {
        setData(inc);
        if (inc.attribution_scores && inc.attribution_scores.length > 0) {
          setSelectedVessel(inc.attribution_scores[0]);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  const handleTraceOrigin = async () => {
    if (!data) return;
    setIsTracing(true);
    try {
      const res = await traceOrigin(data.incident.id, {
        slick_lat: data.incident.center_lat,
        slick_lon: data.incident.center_lon,
        backtrack_hours: 6.0
      });
      setData((prev) => prev ? {
        ...prev,
        origin_estimate: {
          id: 'ORIGIN_LIVE',
          origin_center_lat: res.origin_center_lat,
          origin_center_lon: res.origin_center_lon,
          uncertainty_radius_km: res.uncertainty_radius_km,
          origin_window_start: res.origin_window_start,
          origin_window_end: res.origin_window_end,
          geojson: res.geojson,
          forcing_used: res.forcing_used
        }
      } : null);
    } catch (err) {
      console.error(err);
    } finally {
      setIsTracing(false);
    }
  };

  const handleForecastSpill = async () => {
    if (!data) return;
    setIsForecasting(true);
    try {
      const res = await forecastSpill(data.incident.id, {
        slick_lat: data.incident.center_lat,
        slick_lon: data.incident.center_lon
      });
      if (res.forecast_steps) {
        setData((prev) => prev ? {
          ...prev,
          forward_forecast: res.forecast_steps,
          impacts: res.impacts
        } : null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsForecasting(false);
    }
  };

  if (loading) {
    return (
      <div className="h-screen w-screen bg-white flex flex-col items-center justify-center text-zinc-900 font-mono gap-3">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent animate-spin" />
        <div className="text-xs uppercase tracking-widest text-zinc-600">
          INITIALIZING MARITIME INTELLIGENCE ENGINE...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-screen w-screen bg-white flex flex-col items-center justify-center text-zinc-600 font-mono p-6 text-center">
        <span className="text-xs text-red-600 uppercase font-bold mb-2">ERROR LOADING INCIDENT</span>
        <p className="text-xs">{error}</p>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-zinc-100 flex flex-col overflow-hidden font-mono select-none text-zinc-900">
      {/* Top Header */}
      <Header data={data} />

      {/* Subroute Navigation Bar */}
      <SubrouteNav
        onOpenReport={() => setIsReportOpen(true)}
        onOpenAssistant={() => setIsAssistantOpen(true)}
      />

      {/* Main Workspace Layout */}
      <main className="flex-1 flex overflow-hidden p-3 gap-3">
        {/* Left / Center Map Section */}
        <section className="flex-1 flex flex-col overflow-hidden gap-2">
          {/* Action Ribbon */}
          <div className="h-9 bg-white border border-zinc-200 px-3 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-zinc-500 uppercase">SUBROUTE STAGE:</span>
              <strong className="text-zinc-950 uppercase tracking-wider text-[11px]">
                {activeView === 'overview' && '01 / FULL EVIDENCE CORRELATION'}
                {activeView === 'satellite' && '02 / SENTINEL-1 SAR QUALITY & LOOK-ALIKE'}
                {activeView === 'origin' && '03 / LAGRANGIAN BACKWARD DRIFT RECONSTRUCTION'}
                {activeView === 'ais' && '04 / SPATIO-TEMPORAL AIS & ANOMALIES'}
                {activeView === 'attribution' && '05 / EXPLAINABLE CANDIDATE ATTRIBUTION'}
                {activeView === 'forecast' && '06 / FORWARD DRIFT (+48H) & IMPACT'}
              </strong>
            </div>

            <div className="flex items-center gap-2">
              {activeView === 'satellite' && (
                <button
                  onClick={async () => {
                    if (!data) return;
                    setIsTracing(true);
                    try {
                      const res = await analyzeSAR(data.incident.id);
                      setData((prev) => prev ? {
                        ...prev,
                        detection: {
                          ...prev.detection!,
                          decision_state: res.decision_state,
                          oil_confidence: res.oil_confidence,
                          look_alike_risk: res.look_alike_risk,
                          look_alike_type: res.look_alike_type,
                          area_km2: res.morphometrics.area_km2,
                          length_km: res.morphometrics.length_km,
                          width_km: res.morphometrics.width_km,
                          orientation_deg: res.morphometrics.orientation_deg,
                          morphology_type: res.morphometrics.morphology_type
                        }
                      } : null);
                    } finally {
                      setIsTracing(false);
                    }
                  }}
                  disabled={isTracing}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-3 py-1 text-[11px] flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isTracing ? 'RUNNING U-NET...' : 'EXECUTE PYTORCH U-NET & LOOK-ALIKE'}</span>
                </button>
              )}

              {activeView === 'origin' && (
                <button
                  onClick={handleTraceOrigin}
                  disabled={isTracing}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-3 py-1 text-[11px] flex items-center gap-1.5"
                >
                  <MapPin className="w-3.5 h-3.5" />
                  <span>{isTracing ? 'BACKTRACKING...' : 'RUN LIVE BACKTRACK'}</span>
                </button>
              )}

              {activeView === 'forecast' && (
                <button
                  onClick={handleForecastSpill}
                  disabled={isForecasting}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-3 py-1 text-[11px] flex items-center gap-1.5"
                >
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span>{isForecasting ? 'FORECASTING...' : 'RUN FORWARD SPREAD'}</span>
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 relative overflow-hidden">
            <IncidentMap
              data={data}
              selectedVessel={selectedVessel}
              onSelectVessel={setSelectedVessel}
              timelineMinutes={timelineMinutes}
              highlightLayer={
                activeView === 'satellite' ? 'satellite' :
                activeView === 'origin' ? 'origin' :
                activeView === 'ais' || activeView === 'attribution' ? 'ais' :
                activeView === 'forecast' ? 'forecast' : 'all'
              }
            />
          </div>

          <TimelineSlider
            data={data}
            timelineMinutes={timelineMinutes}
            onChangeTimeline={setTimelineMinutes}
          />
        </section>

        {/* Right Side Dedicated Inspector Panel */}
        <aside className="w-[440px] shrink-0 flex flex-col overflow-hidden">
          {activeView === 'overview' && (
            <EvidenceFusionPanel data={data} />
          )}

          {activeView === 'satellite' && (
            <SpillCharacterisationPanel data={data} />
          )}

          {activeView === 'origin' && (
            <div className="flex flex-col h-full bg-white border border-zinc-200 p-4 font-mono text-xs overflow-hidden space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-200 shrink-0">
                <div>
                  <span className="text-[10px] text-zinc-500 uppercase block">HYDRODYNAMIC RECONSTRUCTION</span>
                  <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
                    {data?.incident?.title || 'Lagrangian Backward Simulation'}
                  </h2>
                </div>
                <span className="border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-600 bg-zinc-50">
                  500 PARTICLES
                </span>
              </div>

              <div className="space-y-3 overflow-y-auto">
                {data?.origin_estimate ? (
                  <>
                    <div className="p-3 bg-blue-50 border border-blue-600 space-y-2">
                      <span className="text-[10px] text-blue-700 uppercase tracking-wider block font-bold">
                        PROBABLE ORIGIN REGION
                      </span>
                      <div>CENTROID: <strong className="text-zinc-950">{data.origin_estimate.origin_center_lat.toFixed(4)}° N, {data.origin_estimate.origin_center_lon.toFixed(4)}° E</strong></div>
                      <div>90% UNCERTAINTY: <strong className="text-zinc-950">{data.origin_estimate.uncertainty_radius_km} km</strong></div>
                      <div>ESTIMATED SPILL WINDOW: <strong className="text-zinc-950">{data.origin_estimate.origin_window_start.split('T')[1].substring(0,5)} – {data.origin_estimate.origin_window_end.split('T')[1].substring(0,5)} UTC</strong></div>
                    </div>

                    <div className="p-3 bg-zinc-50 border border-zinc-200 space-y-2">
                      <span className="text-[10px] text-zinc-500 uppercase tracking-wider block font-bold">
                        FORCING APPLIED:
                      </span>
                      <div>SURFACE CURRENT: <span className="text-zinc-900">{data.origin_estimate.forcing_used.current_speed_ms} m/s @ {data.origin_estimate.forcing_used.current_direction_deg}°</span></div>
                      <div>SURFACE WIND: <span className="text-zinc-900">{data.origin_estimate.forcing_used.wind_speed_ms} m/s @ {data.origin_estimate.forcing_used.wind_direction_deg}°</span></div>
                      <div>SOURCE: <span className="text-zinc-900">{data.origin_estimate.forcing_used.source_name}</span></div>
                    </div>
                  </>
                ) : (
                  <div className="p-6 border border-zinc-200 bg-zinc-50 text-center text-zinc-500 font-bold text-xs uppercase">
                    Data unavailable for this demonstration incident.
                  </div>
                )}

                <button
                  onClick={handleTraceOrigin}
                  disabled={isTracing}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold flex items-center justify-center gap-2"
                >
                  <MapPin className="w-4 h-4" />
                  <span>{isTracing ? 'SIMULATING DRIFT...' : 'RE-SIMULATE BACKWARD PARTICLES'}</span>
                </button>
              </div>
            </div>
          )}

          {activeView === 'ais' && (
            <div className="flex flex-col h-full bg-white border border-zinc-200 p-4 font-mono text-xs overflow-hidden space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-200 shrink-0">
                <div>
                  <span className="text-[10px] text-zinc-500 uppercase block">SPATIO-TEMPORAL QUERY</span>
                  <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
                    "Who Was Here?" & Anomalies
                  </h2>
                </div>
                <span className="border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-600 bg-zinc-50">
                  RADIUS: 35 KM
                </span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2.5">
                {data?.anomalies && data.anomalies.length > 0 ? (
                  data.anomalies.map(anomaly => (
                    <div key={anomaly.id} className="p-3 bg-blue-50 border border-blue-600 space-y-1.5">
                      <div className="flex items-center justify-between text-blue-800 font-bold text-[11px]">
                        <span>[{anomaly.severity} ANOMALY] {anomaly.anomaly_type}</span>
                        <span>MMSI {anomaly.mmsi}</span>
                      </div>
                      <p className="text-zinc-700 font-sans text-xs">
                        {anomaly.description}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="p-6 border border-zinc-200 bg-zinc-50 text-center text-zinc-500 font-bold text-xs uppercase mt-4">
                    AIS data unavailable for this demonstration incident.
                  </div>
                )}
              </div>
            </div>
          )}

          {activeView === 'attribution' && (
            <CandidateVesselsPanel
              candidates={data.attribution_scores}
              selectedVessel={selectedVessel}
              onSelectVessel={setSelectedVessel}
            />
          )}

          {activeView === 'forecast' && (
            <ForecastImpactPanel data={data} />
          )}
        </aside>
      </main>

      {/* Modals */}
      {isAssistantOpen && (
        <InvestigationAssistant
          incidentId={data.incident.id}
          onClose={() => setIsAssistantOpen(false)}
        />
      )}

      {isReportOpen && (
        <ReportModal
          incidentId={data.incident.id}
          onClose={() => setIsReportOpen(false)}
        />
      )}
    </div>
  );
};
