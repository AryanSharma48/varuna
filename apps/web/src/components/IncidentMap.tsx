import React from 'react';
import { IncidentData, CandidateVessel } from '../types';

interface IncidentMapProps {
  data: IncidentData | null;
  selectedVessel: CandidateVessel | null;
  onSelectVessel: (vessel: CandidateVessel) => void;
  timelineMinutes: number;
  highlightLayer?: 'all' | 'satellite' | 'origin' | 'ais' | 'forecast';
}

export const IncidentMap: React.FC<IncidentMapProps> = ({
  data,
  onSelectVessel,
  timelineMinutes,
  highlightLayer = 'all'
}) => {
  // Map Bounds
  const bounds = {
    minLon: 72.45,
    maxLon: 73.05,
    minLat: 18.65,
    maxLat: 19.15
  };

  const project = (lon: number, lat: number) => {
    const x = ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * 100;
    const y = ((bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat)) * 100;
    return { x, y };
  };

  const originCenter = data?.origin_estimate 
    ? project(data.origin_estimate.origin_center_lon, data.origin_estimate.origin_center_lat) 
    : { x: 45, y: 55 };
    
  const slickCenter = data?.incident 
    ? project(data.incident.center_lon, data.incident.center_lat) 
    : { x: 62, y: 46 };

  const frac = Math.min(1.0, Math.max(0.0, timelineMinutes / 720.0));

  // Vessel Positions
  const pvLon = 72.50 + frac * 0.40;
  const pvLat = 18.65 + frac * 0.45;
  const pvPos = project(pvLon, pvLat);

  const ntLon = 72.84;
  const ntLat = 18.65 + frac * 0.50;
  const ntPos = project(ntLon, ntLat);

  const oeLon = 72.52;
  const oeLat = 19.10 - frac * 0.42;
  const oePos = project(oeLon, oeLat);

  const srPos = project(72.57, 19.00);

  const showSlick = highlightLayer === 'all' || highlightLayer === 'satellite';
  const showOrigin = highlightLayer === 'all' || highlightLayer === 'origin';
  const showAis = highlightLayer === 'all' || highlightLayer === 'ais';
  const showForecast = highlightLayer === 'all' || highlightLayer === 'forecast';

  return (
    <div className="relative w-full h-full bg-black overflow-hidden select-none border border-zinc-800">
      {/* Strict Minimal Grid */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#3f3f46" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* Primary SVG Canvas */}
      <svg className="w-full h-full absolute inset-0" viewBox="0 0 100 100" preserveAspectRatio="none">
        {/* Coastline Polygon */}
        <path
          d="M 91 0 Q 88 35, 90 70 T 89 100 L 100 100 L 100 0 Z"
          fill="#09090b"
          stroke="#27272a"
          strokeWidth="0.8"
        />
        <text x="95" y="8" fill="#52525b" fontSize="2" fontFamily="monospace" textAnchor="middle">
          COASTLINE
        </text>

        {/* Forward Forecast Spread Cones */}
        {showForecast && (
          <g>
            <ellipse cx="68" cy="44" rx="4.5" ry="3.2" fill="rgba(37, 99, 235, 0.15)" stroke="#2563eb" strokeWidth="0.4" transform="rotate(-15 68 44)" />
            <text x="68" y="44" fill="#93c5fd" fontSize="1.8" fontFamily="monospace" textAnchor="middle">+6h SPREAD</text>

            <ellipse cx="74" cy="41" rx="6.5" ry="4.5" fill="rgba(37, 99, 235, 0.1)" stroke="#2563eb" strokeWidth="0.4" strokeDasharray="1,1" transform="rotate(-15 74 41)" />
            <text x="74" y="41" fill="#93c5fd" fontSize="1.8" fontFamily="monospace" textAnchor="middle">+12h SPREAD</text>

            <ellipse cx="80" cy="38" rx="9.0" ry="6.0" fill="rgba(37, 99, 235, 0.05)" stroke="#2563eb" strokeWidth="0.4" strokeDasharray="1.5,1.5" transform="rotate(-15 80 38)" />
            <text x="80" y="38" fill="#93c5fd" fontSize="1.8" fontFamily="monospace" textAnchor="middle">+24h SPREAD</text>
          </g>
        )}

        {/* Sensitive Protected Assets */}
        {showForecast && (
          <g>
            <circle cx="85" cy="25" r="6" fill="rgba(255, 255, 255, 0.04)" stroke="#ffffff" strokeWidth="0.4" strokeDasharray="1,1" />
            <text x="85" y="24" fill="#ffffff" fontSize="1.8" fontFamily="monospace" textAnchor="middle">MALVAN SANCTUARY</text>
            <text x="85" y="27" fill="#71717a" fontSize="1.4" fontFamily="monospace" textAnchor="middle">VULN: 95%</text>

            <circle cx="83" cy="48" r="7" fill="rgba(37, 99, 235, 0.08)" stroke="#2563eb" strokeWidth="0.4" strokeDasharray="1,1" />
            <text x="83" y="47" fill="#93c5fd" fontSize="1.8" fontFamily="monospace" textAnchor="middle">THANE CREEK</text>
            <text x="83" y="50" fill="#60a5fa" fontSize="1.4" fontFamily="monospace" textAnchor="middle">ETA: +6h</text>
          </g>
        )}

        {/* Backward Origin Probability Contours */}
        {showOrigin && (
          <g>
            <circle cx={originCenter.x} cy={originCenter.y} r="10.5" fill="rgba(37, 99, 235, 0.05)" stroke="#2563eb" strokeWidth="0.4" strokeDasharray="1,1" />
            <circle cx={originCenter.x} cy={originCenter.y} r="7.0" fill="rgba(37, 99, 235, 0.12)" stroke="#2563eb" strokeWidth="0.5" />
            <circle cx={originCenter.x} cy={originCenter.y} r="3.8" fill="rgba(37, 99, 235, 0.25)" stroke="#3b82f6" strokeWidth="0.6" />
            <circle cx={originCenter.x} cy={originCenter.y} r="0.8" fill="#ffffff" />
            <text x={originCenter.x} y={originCenter.y - 12} fill="#ffffff" fontSize="2" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
              PROBABLE ORIGIN (90% CONF: 4.2 KM)
            </text>
            <text x={originCenter.x} y={originCenter.y - 9.5} fill="#93c5fd" fontSize="1.5" fontFamily="monospace" textAnchor="middle">
              EST. SPILL WINDOW: 13:30–14:45 UTC
            </text>
          </g>
        )}

        {/* Observed Oil Slick Polygon */}
        {showSlick && (
          <g>
            <ellipse
              cx={slickCenter.x}
              cy={slickCenter.y}
              rx="9.5"
              ry="2.4"
              fill="rgba(255, 255, 255, 0.18)"
              stroke="#ffffff"
              strokeWidth="0.8"
              transform={`rotate(-42 ${slickCenter.x} ${slickCenter.y})`}
            />
            <circle cx={slickCenter.x} cy={slickCenter.y} r="0.8" fill="#ffffff" />
            <text x={slickCenter.x} y={slickCenter.y + 6} fill="#ffffff" fontSize="2" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
              OBSERVED OIL SLICK (12.80 KM²)
            </text>
            <text x={slickCenter.x} y={slickCenter.y + 8.5} fill="#a1a1aa" fontSize="1.5" fontFamily="monospace" textAnchor="middle">
              CONFIDENCE: 93% · LINEAR SLICK
            </text>
          </g>
        )}

        {/* AIS Tracks */}
        {showAis && (
          <g>
            <line x1="8" y1="92" x2="88" y2="8" stroke="#ffffff" strokeWidth="0.6" strokeDasharray="1.5,1.5" opacity="0.6" />
            <line x1="65" y1="95" x2="65" y2="5" stroke="#2563eb" strokeWidth="0.4" opacity="0.4" />
            <line x1="12" y1="5" x2="12" y2="95" stroke="#2563eb" strokeWidth="0.4" opacity="0.4" />
          </g>
        )}

        {/* AIS Anomaly Box */}
        {showAis && (
          <g>
            <circle cx={originCenter.x + 2} cy={originCenter.y - 1} r="2.5" fill="none" stroke="#ffffff" strokeWidth="0.6" strokeDasharray="1,1" />
            <rect x={originCenter.x - 14} y={originCenter.y + 3} width="32" height="6.5" fill="#000000" stroke="#ffffff" strokeWidth="0.5" />
            <text x={originCenter.x + 2} y={originCenter.y + 6.5} fill="#ffffff" fontSize="1.5" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
              [ANOMALY] 40-MIN AIS GAP DETECTED
            </text>
            <text x={originCenter.x + 2} y={originCenter.y + 8.5} fill="#a1a1aa" fontSize="1.2" fontFamily="monospace" textAnchor="middle">
              PACIFIC VOYAGER (SPEED DROP 14.2 TO 6.1 KTS)
            </text>
          </g>
        )}

        {/* Vessels */}
        {showAis && (
          <g>
            {/* Pacific Voyager */}
            <g
              className="cursor-pointer"
              onClick={() => {
                const pv = data?.attribution_scores.find(v => v.mmsi === 412356789);
                if (pv) onSelectVessel(pv);
              }}
            >
              <rect x={pvPos.x - 1.2} y={pvPos.y - 1.2} width="2.4" height="2.4" fill="#2563eb" stroke="#ffffff" strokeWidth="0.5" />
              <text x={pvPos.x + 3.5} y={pvPos.y} fill="#ffffff" fontSize="1.8" fontFamily="monospace" fontWeight="bold">
                PACIFIC VOYAGER #1
              </text>
              <text x={pvPos.x + 3.5} y={pvPos.y + 2.2} fill="#93c5fd" fontSize="1.4" fontFamily="monospace">
                SCORE: 91.2/100 · TANKER
              </text>
            </g>

            {/* Nordic Trader */}
            <g className="cursor-pointer" onClick={() => {
              const nt = data?.attribution_scores.find(v => v.mmsi === 211567890);
              if (nt) onSelectVessel(nt);
            }}>
              <rect x={ntPos.x - 1} y={ntPos.y - 1} width="2" height="2" fill="#52525b" stroke="#ffffff" strokeWidth="0.4" />
              <text x={ntPos.x + 3} y={ntPos.y} fill="#a1a1aa" fontSize="1.6" fontFamily="monospace">
                NORDIC TRADER
              </text>
            </g>

            {/* Ocean Explorer */}
            <g className="cursor-pointer" onClick={() => {
              const oe = data?.attribution_scores.find(v => v.mmsi === 352678901);
              if (oe) onSelectVessel(oe);
            }}>
              <rect x={oePos.x - 1} y={oePos.y - 1} width="2" height="2" fill="#52525b" stroke="#ffffff" strokeWidth="0.4" />
              <text x={oePos.x + 3} y={oePos.y} fill="#a1a1aa" fontSize="1.6" fontFamily="monospace">
                OCEAN EXPLORER
              </text>
            </g>

            {/* Sagar Ratna */}
            <g>
              <rect x={srPos.x - 0.8} y={srPos.y - 0.8} width="1.6" height="1.6" fill="#27272a" stroke="#71717a" strokeWidth="0.3" />
              <text x={srPos.x + 2.5} y={srPos.y} fill="#71717a" fontSize="1.4" fontFamily="monospace">
                SAGAR RATNA
              </text>
            </g>
          </g>
        )}
      </svg>

      {/* Telemetry Corner Overlay */}
      <div className="absolute bottom-3 right-3 bg-black border border-zinc-800 p-3 font-mono text-[11px] text-zinc-300">
        <div className="text-zinc-500 uppercase pb-1 border-b border-zinc-800 mb-1.5 text-[10px]">
          HYDRODYNAMIC FORCING
        </div>
        <div>WIND: <strong className="text-white">6.2 m/s @ 240°</strong></div>
        <div>CURRENT: <strong className="text-white">0.35 m/s @ 75°</strong></div>
      </div>
    </div>
  );
};
