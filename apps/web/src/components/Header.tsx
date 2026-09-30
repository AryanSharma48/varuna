import React from 'react';
import { IncidentData } from '../types';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface HeaderProps {
  data: IncidentData | null;
}

export const Header: React.FC<HeaderProps> = ({ data }) => {
  const navigate = useNavigate();
  const quality = data?.scene?.quality_score || 'HIGH';
  const confidence = data?.detection?.oil_confidence ? Math.round(data.detection.oil_confidence * 100) : 93;
  const decision = data?.detection?.decision_state || 'OIL';

  return (
    <header className="h-12 px-6 bg-white border-b border-zinc-200 flex items-center justify-between z-30 shrink-0 font-mono text-xs text-zinc-900">
      {/* Brand & Back to Landing */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1.5 text-zinc-600 hover:text-black px-2 py-1 border border-zinc-300 hover:border-zinc-400 bg-zinc-50 transition-colors uppercase text-[11px]"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>EXIT</span>
        </button>

        <div className="flex items-center gap-2">
          <span className="font-bold text-black tracking-wider uppercase">VARUNA</span>
          <span className="text-zinc-300">/</span>
          <span className="text-zinc-800 uppercase font-bold">
            {data?.incident?.id || 'VARUNA-2026-001'}
          </span>
          <span className="text-zinc-500 text-[11px] truncate max-w-xs font-sans">
            ({data?.incident.title})
          </span>
        </div>
      </div>

      {/* Telemetry Status Badges */}
      <div className="flex items-center gap-2">
        <div className="border border-zinc-300 px-2.5 py-1 bg-zinc-50 flex items-center gap-1.5">
          <span className="text-zinc-500 uppercase">DECISION:</span>
          <span className="font-bold text-black">{decision}</span>
        </div>

        <div className="border border-zinc-300 px-2.5 py-1 bg-zinc-50 flex items-center gap-1.5">
          <span className="text-zinc-500 uppercase">CONFIDENCE:</span>
          <span className="font-bold text-blue-700">{confidence}%</span>
        </div>

        <div className="border border-zinc-300 px-2.5 py-1 bg-zinc-50 flex items-center gap-1.5">
          <span className="text-zinc-500 uppercase">QUALITY:</span>
          <span className="font-bold text-black">{quality}</span>
        </div>
      </div>
    </header>
  );
};
