import React from 'react';
import { NavLink, useParams } from 'react-router-dom';
import { 
  Sparkles, 
  MapPin, 
  Radio, 
  Ship, 
  TrendingUp, 
  FileText, 
  Bot,
  LayoutDashboard
} from 'lucide-react';

interface SubrouteNavProps {
  onOpenReport: () => void;
  onOpenAssistant: () => void;
}

export const SubrouteNav: React.FC<SubrouteNavProps> = ({ onOpenReport, onOpenAssistant }) => {
  const { id = 'VARUNA-2026-001' } = useParams();

  const links = [
    { to: `/investigation/${id}/overview`, label: '01. Overview', icon: LayoutDashboard },
    { to: `/investigation/${id}/satellite`, label: '02. Satellite & Quality', icon: Sparkles },
    { to: `/investigation/${id}/origin`, label: '03. Origin Backtrack', icon: MapPin },
    { to: `/investigation/${id}/ais`, label: '04. AIS & Anomalies', icon: Radio },
    { to: `/investigation/${id}/attribution`, label: '05. Candidate Ranking', icon: Ship },
    { to: `/investigation/${id}/forecast`, label: '06. Drift & Impact', icon: TrendingUp },
  ];

  return (
    <nav className="h-10 bg-white border-b border-zinc-200 px-6 flex items-center justify-between text-xs font-mono shrink-0 select-none">
      <div className="flex items-center gap-1 overflow-x-auto">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `px-3 py-1.5 flex items-center gap-1.5 transition-colors uppercase tracking-wider ${
                  isActive
                    ? 'bg-blue-600 text-white font-bold'
                    : 'text-zinc-600 hover:text-black hover:bg-zinc-100'
                }`
              }
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{link.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={onOpenAssistant}
          className="px-3 py-1 bg-zinc-50 hover:bg-zinc-100 text-zinc-700 hover:text-black border border-zinc-300 flex items-center gap-1.5 transition-colors text-[11px]"
        >
          <Bot className="w-3.5 h-3.5 text-blue-600" />
          <span>ASSISTANT</span>
        </button>

        <button
          onClick={onOpenReport}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white font-bold flex items-center gap-1.5 transition-colors text-[11px]"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>REPORT</span>
        </button>
      </div>
    </nav>
  );
};
