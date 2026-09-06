import React from 'react';

export const SubmarineRadarOverlay: React.FC = () => {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none">
      {/* Center Radar Scope Display */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1100px] h-[1100px] flex items-center justify-center">
        
        {/* Concentric Range Rings (Solid 1px Matte Lines - No Glow) */}
        <div className="absolute w-[280px] h-[280px] rounded-full border border-slate-700/60" />
        <div className="absolute w-[540px] h-[540px] rounded-full border border-slate-700/50 border-dashed" />
        <div className="absolute w-[800px] h-[800px] rounded-full border border-slate-700/40" />
        <div className="absolute w-[1060px] h-[1060px] rounded-full border border-slate-700/30 border-dashed" />

        {/* Outer Compass Degree Ring */}
        <div className="absolute w-[1080px] h-[1080px] rounded-full border border-slate-700/60 flex items-center justify-center">
          <span className="absolute top-2 text-[11px] text-slate-400 font-semibold tracking-widest">
            000° N
          </span>
          <span className="absolute bottom-2 text-[11px] text-slate-400 font-semibold tracking-widest">
            180° S
          </span>
          <span className="absolute right-2 text-[11px] text-slate-400 font-semibold tracking-widest">
            090° E
          </span>
          <span className="absolute left-2 text-[11px] text-slate-400 font-semibold tracking-widest">
            270° W
          </span>
        </div>

        {/* Crosshair Azimuth Lines (Solid 1px Matte Lines) */}
        <div className="absolute top-0 bottom-0 left-1/2 w-[1px] bg-slate-700/50 -translate-x-1/2" />
        <div className="absolute left-0 right-0 top-1/2 h-[1px] bg-slate-700/50 -translate-y-1/2" />
        <div className="absolute w-full h-[1px] bg-slate-800/40 rotate-45" />
        <div className="absolute w-full h-[1px] bg-slate-800/40 -rotate-45" />

        {/* Mechanical Sonar Sweep Beam */}
        <div className="absolute w-[1060px] h-[1060px] rounded-full animate-sonar-sweep pointer-events-none overflow-hidden">
          <div
            className="w-1/2 h-1/2 ml-auto origin-bottom-left border-b border-blue-400/40"
            style={{
              background: 'conic-gradient(from 180deg at 0% 100%, rgba(59, 130, 246, 0.15) 0deg, rgba(59, 130, 246, 0) 35deg)'
            }}
          />
        </div>


        {/* Military Radar Contact Symbology (Solid Matte Markers) */}
        {/* Contact 1: Slick Target */}
        <div className="absolute top-[42%] left-[58%] flex items-center gap-1.5">
          <div className="w-2 h-2 bg-amber-500 rounded-none rotate-45" />
          <span className="text-[10px] text-slate-300 font-medium bg-slate-900 px-1.5 py-0.5 border border-slate-700">
            TGT-01 (14.2 km²)
          </span>
        </div>

        {/* Contact 2: AIS Vessel Track */}
        <div className="absolute top-[32%] left-[45%] flex items-center gap-1.5">
          <div className="w-2 h-2 bg-blue-500 rounded-none" />
          <span className="text-[10px] text-slate-300 font-medium bg-slate-900 px-1.5 py-0.5 border border-slate-700">
            AIS-88 (TANKER)
          </span>
        </div>

        {/* Contact 3: Buoy Reference */}
        <div className="absolute top-[65%] left-[38%] flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 bg-slate-400 rounded-full" />
          <span className="text-[10px] text-slate-400 font-medium bg-slate-900 px-1.5 py-0.5 border border-slate-800">
            BUOY-04
          </span>
        </div>

      </div>

      {/* Submarine Telemetry Badges (Corner Heads-Up Data - Matte Solid Boxes) */}
      <div className="absolute top-16 left-6 text-[11px] text-slate-400 space-y-0.5 bg-slate-900/90 p-3 rounded border border-slate-800">
        <div className="text-slate-200 font-bold">RADAR SCOPE: ACTIVE</div>
        <div>SENSOR: SENTINEL-1 C-BAND SAR</div>
        <div>SWEEP: 360° MECHANICAL SCAN</div>
      </div>

      <div className="absolute top-16 right-6 text-[11px] text-slate-400 space-y-0.5 text-right bg-slate-900/90 p-3 rounded border border-slate-800">
        <div className="text-slate-200 font-bold">RANGE: 120 NM</div>
        <div>GRID: WGS-84 (EPSG:4326)</div>
        <div>BEARING: 032° AZIMUTH</div>
      </div>
    </div>
  );
};
