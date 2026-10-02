import React, { useState } from 'react';
import { IncidentData, CandidateVessel, AISAnomalyItem } from '../types';

interface VesselAttributionPanelProps {
  data: IncidentData | null;
}

export const VesselAttributionPanel: React.FC<VesselAttributionPanelProps> = ({ data }) => {
  const [selectedMmsi, setSelectedMmsi] = useState<number | null>(null);

  const vessels: CandidateVessel[] = data?.attribution_scores || [];
  const anomalies: AISAnomalyItem[] = data?.anomalies || [];

  // Sort vessels by priority_rank ascending (Rank 1, 2, 3)
  const sortedVessels = [...vessels].sort((a, b) => a.priority_rank - b.priority_rank);

  const getRankBadgeStyle = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40 ring-1 ring-rose-500/30';
      case 2:
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 3:
      default:
        return 'bg-sky-500/20 text-sky-300 border-sky-500/30';
    }
  };

  const getRankTitle = (rank: number) => {
    switch (rank) {
      case 1:
        return 'RANK 1 • PRIME CANDIDATE';
      case 2:
        return 'RANK 2 • SECONDARY SUSPECT';
      case 3:
      default:
        return 'RANK 3 • LOW CORRELATION';
    }
  };

  return (
    <div className="space-y-3 font-sans">
      {/* Quick Rank Switcher Tabs */}
      <div className="flex items-center gap-1.5 bg-white/[0.03] p-1 rounded-xl border border-white/[0.06]">
        {sortedVessels.map((v) => {
          const isSelected = selectedMmsi === v.mmsi || (selectedMmsi === null && v.priority_rank === 1);
          return (
            <button
              key={v.mmsi}
              onClick={() => setSelectedMmsi(v.mmsi)}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-center truncate ${
                isSelected
                  ? v.priority_rank === 1
                    ? 'bg-rose-600 text-white shadow-md shadow-rose-900/40'
                    : 'bg-blue-600 text-white shadow-md shadow-blue-900/40'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
              }`}
            >
              #{v.priority_rank} {v.vessel_name.replace('MT ', '').replace('MV ', '')} ({v.total_score.toFixed(1)})
            </button>
          );
        })}
      </div>

      {/* Rankwise Comparison Cards */}
      <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
        {sortedVessels.map((vessel) => {
          const vAnomalies = anomalies.filter((a) => a.mmsi === vessel.mmsi);
          const isSelected = selectedMmsi === vessel.mmsi || (selectedMmsi === null && vessel.priority_rank === 1);

          return (
            <div
              key={vessel.mmsi}
              className={`p-4 rounded-2xl liquid-glass-subtle border transition-all space-y-3 ${
                isSelected
                  ? vessel.priority_rank === 1
                    ? 'border-rose-500/50 ring-1 ring-rose-500/20 bg-rose-950/10'
                    : 'border-blue-500/50 ring-1 ring-blue-500/20 bg-blue-950/10'
                  : 'border-white/[0.08] hover:border-white/20'
              }`}
            >
              {/* Card Header: Rank & Score */}
              <div className="flex items-start justify-between gap-2 border-b border-white/[0.08] pb-2.5">
                <div>
                  <span className={`inline-block px-2.5 py-0.5 text-[10px] font-extrabold uppercase rounded-full border mb-1.5 ${getRankBadgeStyle(vessel.priority_rank)}`}>
                    {getRankTitle(vessel.priority_rank)}
                  </span>
                  <h3 className="text-base font-extrabold text-white tracking-wide font-heading">
                    {vessel.vessel_name}
                  </h3>
                  <div className="text-xs text-slate-400 mt-0.5 font-medium">
                    {vessel.vessel_type} • {vessel.flag}
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-[10px] text-slate-400 uppercase font-semibold">Attribution Score</div>
                  <div className={`text-xl font-black font-mono tracking-tight mt-0.5 ${
                    vessel.priority_rank === 1 ? 'text-rose-400' : vessel.priority_rank === 2 ? 'text-amber-400' : 'text-sky-400'
                  }`}>
                    {vessel.total_score.toFixed(1)}
                    <span className="text-xs text-slate-400 font-normal"> / 100</span>
                  </div>
                  <span className="text-[9px] text-slate-400 block mt-0.5">
                    MMSI: {vessel.mmsi}
                  </span>
                </div>
              </div>

              {/* Score Breakdown (5 Component Metrics) */}
              <div className="space-y-1.5">
                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block">
                  Score Breakdown by Metric:
                </span>
                <div className="grid grid-cols-2 gap-1.5 text-xs">
                  <div className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-between">
                    <span className="text-slate-400 text-[11px]">Proximity (30%):</span>
                    <strong className="text-white font-mono text-xs">{vessel.breakdown.proximity.toFixed(1)} / 30</strong>
                  </div>
                  <div className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-between">
                    <span className="text-slate-400 text-[11px]">Timing (25%):</span>
                    <strong className="text-white font-mono text-xs">{vessel.breakdown.timing.toFixed(1)} / 25</strong>
                  </div>
                  <div className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-between">
                    <span className="text-slate-400 text-[11px]">Course Vector (20%):</span>
                    <strong className="text-white font-mono text-xs">{vessel.breakdown.trajectory.toFixed(1)} / 20</strong>
                  </div>
                  <div className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-between">
                    <span className="text-slate-400 text-[11px]">AIS Gap Outage (15%):</span>
                    <strong className={`font-mono text-xs ${vessel.breakdown.ais_gap > 0 ? 'text-rose-400 font-bold' : 'text-white'}`}>
                      {vessel.breakdown.ais_gap.toFixed(1)} / 15
                    </strong>
                  </div>
                </div>

                {vessel.breakdown.behaviour_anomaly > 0 && (
                  <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs">
                    <span className="text-amber-300 text-[11px]">Kinematic Anomaly (10%):</span>
                    <strong className="text-amber-300 font-mono text-xs">+{vessel.breakdown.behaviour_anomaly.toFixed(1)} pts</strong>
                  </div>
                )}
              </div>

              {/* Why Ranked Here: Evidence & Causation Reasons */}
              <div className="space-y-1.5 pt-1 border-t border-white/[0.08]">
                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block">
                  Why Ranked Here (Evidence):
                </span>
                <ul className="space-y-1 text-xs text-slate-200">
                  {vessel.reasons.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2 leading-snug">
                      <span className="text-cyan-400 font-bold text-xs mt-0.5">•</span>
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* AIS Anomalies Section */}
              <div className="space-y-1.5 pt-1 border-t border-white/[0.08]">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-slate-400 uppercase font-bold tracking-wider">
                    Detected AIS Anomalies:
                  </span>
                  <span className="font-mono text-slate-400">
                    {vAnomalies.length > 0 ? `${vAnomalies.length} Anomaly Recorded` : 'None'}
                  </span>
                </div>

                {vAnomalies.length > 0 ? (
                  <div className="space-y-1.5">
                    {vAnomalies.map((anom) => (
                      <div
                        key={anom.id}
                        className={`p-2.5 rounded-xl border text-xs space-y-1 ${
                          anom.severity === 'HIGH'
                            ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
                            : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold uppercase text-[10px] tracking-wide">
                            {anom.anomaly_type.replace('_', ' ')}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold ${
                            anom.severity === 'HIGH' ? 'bg-rose-950/80 text-rose-300 border border-rose-800' : 'bg-amber-950/80 text-amber-300 border border-amber-800'
                          }`}>
                            {anom.severity} SEVERITY
                          </span>
                        </div>
                        <p className="text-[11px] leading-relaxed text-slate-200">
                          {anom.description}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-2 rounded-xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-slate-400">
                    No transmission gaps, course divergences, or kinematic anomalies registered for this vessel.
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
