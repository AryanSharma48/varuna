import React from 'react';
import { IncidentData } from '../types';

interface ForecastImpactPanelProps {
  data: IncidentData | null;
}

export const ForecastImpactPanel: React.FC<ForecastImpactPanelProps> = ({ data }) => {
  const impacts = data?.impacts || [];

  return (
    <div className="flex flex-col h-full bg-white border border-zinc-200 p-4 font-mono text-xs overflow-hidden text-zinc-900">
      <div className="flex items-center justify-between pb-3 border-b border-zinc-200 shrink-0">
        <div>
          <span className="text-[10px] text-zinc-500 uppercase block font-bold">HYDRODYNAMIC SPREAD</span>
          <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
            Drift Forecast & Sensitive Asset Impact
          </h2>
        </div>
        <span className="border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-600 bg-zinc-50 font-bold">
          +48H HORIZON
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pt-3 pr-1 text-xs">
        {/* Forecast Horizons */}
        <div className="grid grid-cols-4 gap-1.5 text-center">
          {['+6h', '+12h', '+24h', '+48h'].map((h) => (
            <div key={h} className="p-2 bg-zinc-50 border border-zinc-200">
              <span className="text-[9px] text-zinc-500 block uppercase font-bold">HORIZON</span>
              <strong className="text-xs text-blue-700">{h}</strong>
            </div>
          ))}
        </div>

        {/* Sensitive Assets List */}
        <div className="space-y-2">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block font-bold">
            COASTAL & MARINE ASSETS IN SPREAD PATH:
          </span>

          {impacts.map((asset) => {
            const isCrit = asset.severity === 'CRITICAL' || asset.severity === 'HIGH';

            return (
              <div
                key={asset.asset_id}
                className={`p-2.5 border ${
                  isCrit
                    ? 'bg-blue-50 border-blue-600'
                    : 'bg-zinc-50 border-zinc-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <strong className="text-zinc-950 text-xs font-bold">{asset.asset_name}</strong>
                  <span
                    className={`px-1.5 py-0.5 text-[10px] font-bold uppercase border ${
                      isCrit ? 'border-blue-600 text-blue-700 bg-white' : 'border-zinc-300 text-zinc-600 bg-white'
                    }`}
                  >
                    ETA: {asset.estimated_arrival}
                  </span>
                </div>

                <p className="text-[11px] text-zinc-600 mt-1 font-sans leading-relaxed">{asset.description}</p>

                <div className="flex items-center justify-between text-[10px] text-zinc-500 mt-2 font-bold">
                  <span>TYPE: {asset.asset_type}</span>
                  <span>VULNERABILITY: {(asset.vulnerability_index * 100).toFixed(0)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
