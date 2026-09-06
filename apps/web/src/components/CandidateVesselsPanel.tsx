import React from 'react';
import { CandidateVessel } from '../types';

interface CandidateVesselsPanelProps {
  candidates: CandidateVessel[];
  selectedVessel: CandidateVessel | null;
  onSelectVessel: (vessel: CandidateVessel) => void;
}

export const CandidateVesselsPanel: React.FC<CandidateVesselsPanelProps> = ({
  candidates,
  selectedVessel,
  onSelectVessel
}) => {
  return (
    <div className="flex flex-col h-full bg-white border border-zinc-200 p-4 font-mono text-xs overflow-hidden text-zinc-900">
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-3 border-b border-zinc-200 shrink-0">
        <div>
          <span className="text-[10px] text-zinc-500 uppercase block font-bold">MULTI-SIGNAL CORRELATION</span>
          <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
            Candidate Vessel Attribution
          </h2>
        </div>
        <span className="border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-600 bg-zinc-50 font-bold">
          {candidates.length} CANDIDATES
        </span>
      </div>

      {/* Candidate List */}
      <div className="flex-1 overflow-y-auto space-y-2 pt-3 pr-1">
        {candidates.length > 0 ? (
          candidates.map((vessel) => {
          const isSelected = selectedVessel?.mmsi === vessel.mmsi;
          const isHigh = vessel.priority_level === 'HIGH';

          return (
            <div
              key={vessel.mmsi}
              onClick={() => onSelectVessel(vessel)}
              className={`p-3 cursor-pointer transition-all border ${
                isSelected
                  ? 'bg-blue-50 border-blue-600'
                  : 'bg-zinc-50 border-zinc-200 hover:border-zinc-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-zinc-500">#{vessel.priority_rank}</span>
                  <strong className="text-zinc-950 font-bold">{vessel.vessel_name}</strong>
                </div>
                <span
                  className={`px-1.5 py-0.5 text-[10px] uppercase font-bold border ${
                    isHigh
                      ? 'border-blue-600 bg-blue-100 text-blue-800'
                      : 'border-zinc-200 text-zinc-500 bg-white'
                  }`}
                >
                  {vessel.priority_level} PRIORITY
                </span>
              </div>

              <div className="flex justify-between text-zinc-600 text-[11px] mt-1">
                <span>{vessel.vessel_type}</span>
                <span>MMSI: {vessel.mmsi}</span>
              </div>

              {/* Score Bar */}
              <div className="mt-2">
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-zinc-500 font-bold">PRIORITY SCORE</span>
                  <span className={isHigh ? 'text-blue-700 font-bold' : 'text-zinc-950 font-bold'}>
                    {vessel.total_score} / 100
                  </span>
                </div>
                <div className="w-full h-1 bg-zinc-200">
                  <div
                    className={`h-full ${isHigh ? 'bg-blue-600' : 'bg-zinc-500'}`}
                    style={{ width: `${vessel.total_score}%` }}
                  />
                </div>
              </div>

              {/* Decomposed Breakdown when selected */}
              {isSelected && (
                <div className="mt-3 pt-3 border-t border-zinc-200 space-y-2">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Score Decomposition:</div>
                  <div className="grid grid-cols-2 gap-1 text-[10px]">
                    <div className="p-1.5 bg-white border border-zinc-200">
                      PROXIMITY: <strong className="text-zinc-950">+{vessel.breakdown.proximity}</strong>
                    </div>
                    <div className="p-1.5 bg-white border border-zinc-200">
                      TIMING: <strong className="text-zinc-950">+{vessel.breakdown.timing}</strong>
                    </div>
                    <div className="p-1.5 bg-white border border-zinc-200">
                      TRAJECTORY: <strong className="text-zinc-950">+{vessel.breakdown.trajectory}</strong>
                    </div>
                    <div className="p-1.5 bg-white border border-zinc-200">
                      AIS GAP: <strong className="text-blue-700">+{vessel.breakdown.ais_gap}</strong>
                    </div>
                  </div>

                  <div className="space-y-1 mt-2 text-[10px] text-zinc-600">
                    {vessel.reasons.map((r, i) => (
                      <div key={i} className="flex items-start gap-1">
                        <span className="text-blue-600 shrink-0 font-bold">·</span>
                        <span>{r}</span>
                      </div>
                    ))}
                  </div>

                  <div className="p-2 bg-white border border-zinc-200 text-[10px] text-zinc-500 leading-tight">
                    Investigation Priority ≠ Proof of Responsibility.
                  </div>
                </div>
              )}
            </div>
          );
        })
        ) : (
          <div className="p-6 border border-zinc-200 bg-zinc-50 text-center text-zinc-500 font-bold text-xs uppercase mt-4">
            AIS data unavailable for this demonstration incident.
          </div>
        )}
      </div>
    </div>
  );
};
