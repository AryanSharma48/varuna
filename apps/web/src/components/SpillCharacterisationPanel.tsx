import React from 'react';
import { IncidentData } from '../types';

interface SpillCharacterisationPanelProps {
  data: IncidentData | null;
}

export const SpillCharacterisationPanel: React.FC<SpillCharacterisationPanelProps> = ({ data }) => {
  const det = data?.detection;
  const qg = data?.scene?.quality_details;

  return (
    <div className="flex flex-col h-full bg-white border border-zinc-200 p-4 font-mono text-xs overflow-hidden text-zinc-900">
      <div className="flex items-center justify-between pb-3 border-b border-zinc-200 shrink-0">
        <div>
          <span className="text-[10px] text-zinc-500 uppercase block font-bold">SAR COMPUTER VISION</span>
          <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
            Satellite Characterisation & Look-Alike Filter
          </h2>
        </div>
        <span className="border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-600 bg-zinc-50 font-bold">
          U-NET V1.0
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pt-3 pr-1 text-xs">
        {/* Verification Status */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 bg-zinc-50 border border-zinc-200">
            <span className="text-[10px] text-zinc-500 block uppercase font-bold">CLASSIFICATION</span>
            <span className="text-xs font-bold text-zinc-950 mt-1 block">
              {det?.decision_state || 'OIL'}
            </span>
          </div>

          <div className="p-2.5 bg-zinc-50 border border-zinc-200">
            <span className="text-[10px] text-zinc-500 block uppercase font-bold">LOOK-ALIKE RISK</span>
            <span className="text-xs font-bold text-blue-700 mt-1 block">
              {det?.look_alike_risk || 'LOW RISK'}
            </span>
          </div>
        </div>

        {/* Morphometrics Grid */}
        <div className="p-3 bg-zinc-50 border border-zinc-200 space-y-2">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block font-bold">
            SLICK MORPHOMETRY (PCA & CONTOURS):
          </span>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>AREA: <strong className="text-zinc-950">{det?.area_km2 || 12.8} km²</strong></div>
            <div>PERIMETER: <strong className="text-zinc-950">{det?.perimeter_km || 24.5} km</strong></div>
            <div>LENGTH: <strong className="text-zinc-950">{det?.length_km || 8.4} km</strong></div>
            <div>WIDTH: <strong className="text-zinc-950">{det?.width_km || 1.8} km</strong></div>
            <div>ORIENTATION: <strong className="text-zinc-950">{det?.orientation_deg || 48.0}° NE</strong></div>
            <div>TYPE: <strong className="text-blue-700">{det?.morphology_type || 'LINEAR_SLICK'}</strong></div>
          </div>
        </div>

        {/* Image Quality Gate */}
        <div className="p-3 bg-zinc-50 border border-zinc-200 space-y-2">
          <div className="flex items-center justify-between text-[10px] text-zinc-500 font-bold">
            <span>IMAGE QUALITY GATE</span>
            <span className="text-zinc-950">{data?.scene?.quality_score || 'HIGH'}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-zinc-700">
            <div>DYNAMIC RANGE: <span className="text-zinc-950 font-bold">{qg?.dynamic_range_db || 14.2} dB</span></div>
            <div>MISSING PIXELS: <span className="text-zinc-950 font-bold">{(qg?.missing_pixel_ratio ? qg.missing_pixel_ratio * 100 : 0.1).toFixed(2)}%</span></div>
            <div>WIND REGIME: <span className="text-zinc-950 font-bold">6.2 m/s (OPTIMAL)</span></div>
            <div>COAST CLEARANCE: <span className="text-zinc-950 font-bold">{qg?.coastal_distance_km || 18.4} km</span></div>
          </div>
        </div>

        {/* Probable Origin Summary */}
        <div className="p-3 bg-blue-50 border border-blue-600 space-y-1">
          <span className="text-[10px] text-blue-700 uppercase tracking-wider block font-bold">
            PROBABLE ORIGIN RECONSTRUCTED
          </span>
          <div className="text-[11px] text-zinc-800">
            Centroid: <strong className="text-zinc-950">18.8500° N, 72.7200° E</strong> (4.2 km 90% confidence)
          </div>
          <div className="text-[10px] text-zinc-600">
            Time Window: 13:30 – 14:45 UTC
          </div>
        </div>
      </div>
    </div>
  );
};
