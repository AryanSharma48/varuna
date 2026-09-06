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
          <span className="text-[10px] text-zinc-500 uppercase block font-bold">REFERENCE OIL-SLICK ANNOTATION</span>
          <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
            DARTIS Reference Annotation (ow-0388)
          </h2>
          <span className="text-[10px] text-amber-700 font-semibold block mt-0.5">
            Investigation priority ≠ proof of responsibility.
          </span>
        </div>
        <span className="border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] text-amber-900 font-bold rounded">
          DARTIS / OW-0388
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pt-3 pr-1 text-xs">
        {/* Verification Status */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 bg-zinc-50 border border-zinc-200">
            <span className="text-[10px] text-zinc-500 block uppercase font-bold">CLASSIFICATION</span>
            <span className="text-xs font-bold text-zinc-950 mt-1 block">
              {det?.decision_state || 'DATA UNAVAILABLE'}
            </span>
          </div>

          <div className="p-2.5 bg-zinc-50 border border-zinc-200">
            <span className="text-[10px] text-zinc-500 block uppercase font-bold">LOOK-ALIKE RISK</span>
            <span className="text-xs font-bold text-blue-700 mt-1 block">
              {det?.look_alike_risk || 'N/A'}
            </span>
          </div>
        </div>

        {/* Morphometrics Grid */}
        <div className="p-3 bg-zinc-50 border border-zinc-200 space-y-2">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block font-bold">
            SLICK MORPHOMETRY (PCA & CONTOURS):
          </span>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>AREA: <strong className="text-zinc-950">{det?.area_km2 ? `${det.area_km2} km²` : 'N/A'}</strong></div>
            <div>PERIMETER: <strong className="text-zinc-950">{det?.perimeter_km ? `${det.perimeter_km} km` : 'N/A'}</strong></div>
            <div>LENGTH: <strong className="text-zinc-950">{det?.length_km ? `${det.length_km} km` : 'N/A'}</strong></div>
            <div>WIDTH: <strong className="text-zinc-950">{det?.width_km ? `${det.width_km} km` : 'N/A'}</strong></div>
            <div>ORIENTATION: <strong className="text-zinc-950">{det?.orientation_deg ? `${det.orientation_deg}°` : 'N/A'}</strong></div>
            <div>TYPE: <strong className="text-blue-700">{det?.morphology_type || 'N/A'}</strong></div>
          </div>
        </div>

        {/* Image Quality Gate */}
        <div className="p-3 bg-zinc-50 border border-zinc-200 space-y-2">
          <div className="flex items-center justify-between text-[10px] text-zinc-500 font-bold">
            <span>IMAGE QUALITY GATE</span>
            <span className="text-zinc-950">{data?.scene?.quality_score || 'N/A'}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-zinc-700">
            <div>DYNAMIC RANGE: <span className="text-zinc-950 font-bold">{qg?.dynamic_range_db ? `${qg.dynamic_range_db.toFixed(1)} dB` : 'N/A'}</span></div>
            <div>MISSING PIXELS: <span className="text-zinc-950 font-bold">{qg?.missing_pixel_ratio ? `${(qg.missing_pixel_ratio * 100).toFixed(2)}%` : 'N/A'}</span></div>
            <div>WIND REGIME: <span className="text-zinc-950 font-bold">{qg?.wind_speed_ms ? `${qg.wind_speed_ms} m/s` : 'N/A'}</span></div>
            <div>COAST CLEARANCE: <span className="text-zinc-950 font-bold">{qg?.coastal_distance_km ? `${qg.coastal_distance_km} km` : 'N/A'}</span></div>
          </div>
        </div>

        {/* Probable Origin Summary */}
        <div className="p-3 bg-zinc-50 border border-zinc-200 space-y-1">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider block font-bold">
            PROBABLE ORIGIN RECONSTRUCTED
          </span>
          {data?.origin_estimate ? (
            <>
              <div className="text-[11px] text-zinc-800">
                Centroid: <strong className="text-zinc-950">{data.origin_estimate.origin_center_lat.toFixed(4)}° N, {data.origin_estimate.origin_center_lon.toFixed(4)}° E</strong> ({data.origin_estimate.uncertainty_radius_km} km 90% confidence)
              </div>
              <div className="text-[10px] text-zinc-600">
                Time Window: {data.origin_estimate.origin_window_start.split('T')[1].substring(0, 5)} – {data.origin_estimate.origin_window_end.split('T')[1].substring(0, 5)} UTC
              </div>
            </>
          ) : (
             <div className="text-[11px] text-zinc-800 italic">
               Origin backtracking unavailable for this incident.
             </div>
          )}
        </div>
      </div>
    </div>
  );
};
