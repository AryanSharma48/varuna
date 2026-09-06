import React from 'react';
import { IncidentData } from '../types';

interface EvidenceFusionPanelProps {
  data: IncidentData | null;
}

export const EvidenceFusionPanel: React.FC<EvidenceFusionPanelProps> = ({ data }) => {
  const items = data?.evidence_items || [];

  return (
    <div className="flex flex-col h-full bg-white border border-zinc-200 p-4 font-mono text-xs overflow-hidden text-zinc-900">
      <div className="flex items-center justify-between pb-3 border-b border-zinc-200 shrink-0">
        <div>
          <span className="text-[10px] text-zinc-500 uppercase block font-bold">AUDITABLE CHAIN</span>
          <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
            Structured Evidence Review
          </h2>
        </div>
        <span className="border border-zinc-200 px-2 py-0.5 text-[10px] text-zinc-600 bg-zinc-50 font-bold">
          {items.length} SIGNALS
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 pt-3 pr-1 text-xs">
        {items.map((item, idx) => (
          <div key={item.id} className="p-3 bg-zinc-50 border border-zinc-200">
            <div className="flex items-center justify-between pb-1 border-b border-zinc-200 mb-1.5">
              <strong className="text-zinc-950 text-xs font-bold">{item.title}</strong>
              <span className="text-[10px] text-zinc-500 font-bold">STAGE {idx + 1}</span>
            </div>
            <p className="text-[11px] text-zinc-600 font-sans leading-relaxed">{item.content}</p>
            <div className="mt-2 text-[10px] text-blue-700 font-bold">
              CATEGORY: {item.category}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
