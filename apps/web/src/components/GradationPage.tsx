import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KoreanGradation, DEFAULT_GRADATION_PARAMS, GradientParams } from './KoreanGradation';

export const GradationPage: React.FC = () => {
  const navigate = useNavigate();
  const [params, setParams] = useState<GradientParams>({
    ...DEFAULT_GRADATION_PARAMS,
    motionAmount: 0.25 // small default so swaying is immediately appreciated, with 0 available
  });
  const [renderMode, setRenderMode] = useState<'canvas' | 'css'>('canvas');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const cssSnippet = `/* 21st.dev 그라데이션 Ribbon Field Gradient (CSS Approximation) */
.gradient {
  background-color: #FFFFFF;
  background-image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.210'/></svg>"), linear-gradient(32deg, #FFFFFF 4.32%, #FFFFFF 33.18%, #78B8F9 37.86%, #78B8F9 58.14%, #5667FF 58.86%, #5667FF 79.64%, #4D2FF9 80%, #4D2FF9 100%);
  background-size: 120px 120px, auto;
  background-blend-mode: overlay, normal;
}`;

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden flex flex-col bg-slate-950 font-sans text-slate-100 select-none">
      {/* Background Gradient Layer */}
      {renderMode === 'canvas' ? (
        <KoreanGradation
          className="absolute inset-0 w-full h-full"
          params={params}
        />
      ) : (
        <div
          className="absolute inset-0 w-full h-full"
          style={{
            backgroundColor: '#FFFFFF',
            backgroundImage: `url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.210'/></svg>"), linear-gradient(32deg, #FFFFFF 4.32%, #FFFFFF 33.18%, #78B8F9 37.86%, #78B8F9 58.14%, #5667FF 58.86%, #5667FF 79.64%, #4D2FF9 80%, #4D2FF9 100%)`,
            backgroundSize: '120px 120px, auto',
            backgroundBlendMode: 'overlay, normal'
          }}
        />
      )}

      {/* Floating HUD Top Header */}
      <header className="relative z-20 px-6 py-4 flex items-center justify-between pointer-events-auto">
        <div className="flex items-center gap-3 bg-slate-900/80 backdrop-blur-md px-4 py-2 rounded-lg border border-slate-700/70 shadow-lg">
          <button
            onClick={() => navigate('/')}
            className="text-xs font-semibold text-slate-300 hover:text-white transition-colors"
          >
            ← Back to Platform
          </button>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-white tracking-wide">
              그라데이션 (21st.dev)
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-900/80 border border-blue-600/60 text-blue-200 font-semibold uppercase">
              Ribbon Field
            </span>
          </div>
        </div>

        {/* Mode Switcher */}
        <div className="flex items-center gap-2 bg-slate-900/80 backdrop-blur-md p-1 rounded-lg border border-slate-700/70 shadow-lg">
          <button
            onClick={() => setRenderMode('canvas')}
            className={`px-3 py-1.5 rounded text-xs font-semibold transition-all ${
              renderMode === 'canvas'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            WebGL Canvas (Active Wave & Sway)
          </button>
          <button
            onClick={() => setRenderMode('css')}
            className={`px-3 py-1.5 rounded text-xs font-semibold transition-all ${
              renderMode === 'css'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            CSS Static Approximation
          </button>
        </div>
      </header>

      {/* Interactive Controls & Parameters Deck */}
      <div className="relative z-20 mt-auto p-6 flex flex-col md:flex-row items-end justify-between gap-4 pointer-events-none">
        
        {/* Color Palette Pill Bar */}
        <div className="pointer-events-auto bg-slate-900/85 backdrop-blur-md border border-slate-700/70 p-4 rounded-xl shadow-2xl space-y-2 max-w-sm">
          <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
            Palette Breakdown (4 Spectral Stops)
          </div>
          <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
            <div className="p-2 rounded bg-white text-slate-950 font-bold border border-slate-300 shadow-sm">
              <div>#FFFFFF</div>
              <div className="text-[9px] opacity-75">18% White</div>
            </div>
            <div className="p-2 rounded bg-[#78B8F9] text-slate-950 font-bold shadow-sm">
              <div>#78B8F9</div>
              <div className="text-[9px] opacity-75">57% Sky Blue</div>
            </div>
            <div className="p-2 rounded bg-[#5667FF] text-white font-bold shadow-sm">
              <div>#5667FF</div>
              <div className="text-[9px] opacity-85">60% Ultramarine</div>
            </div>
            <div className="p-2 rounded bg-[#4D2FF9] text-white font-bold shadow-sm">
              <div>#4D2FF9</div>
              <div className="text-[9px] opacity-85">100% Iris</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-400 leading-tight pt-1">
            Sine wave offset: <code className="text-blue-300 font-mono">(wave/100) * 0.35 * sin(cross * 2.4 * 2π + clock)</code>
          </div>
        </div>

        {/* Real-Time Parameter Sliders */}
        <div className="pointer-events-auto bg-slate-900/85 backdrop-blur-md border border-slate-700/70 p-5 rounded-xl shadow-2xl space-y-3 w-full md:w-96">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Motion & Physics Controls
            </span>
            <span className="text-[10px] font-semibold text-emerald-400">
              60 FPS Lock
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Wave Amplitude (Bending):</span>
                <span className="font-bold text-blue-400">{params.wave}</span>
              </div>
              <input
                type="range"
                min="0"
                max="50"
                step="1"
                value={params.wave}
                onChange={(e) => setParams(prev => ({ ...prev, wave: parseFloat(e.target.value) }))}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Motion Amount (Sway):</span>
                <span className="font-bold text-blue-400">{params.motionAmount.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={params.motionAmount}
                onChange={(e) => setParams(prev => ({ ...prev, motionAmount: parseFloat(e.target.value) }))}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Grain Intensity:</span>
                <span className="font-bold text-blue-400">{params.grain}</span>
              </div>
              <input
                type="range"
                min="0"
                max="80"
                step="2"
                value={params.grain}
                onChange={(e) => setParams(prev => ({ ...prev, grain: parseFloat(e.target.value) }))}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-slate-300">Reverse Direction:</span>
              <button
                onClick={() => setParams(prev => ({ ...prev, motionReverse: !prev.motionReverse }))}
                className={`px-3 py-1 rounded text-[11px] font-semibold transition-colors ${
                  params.motionReverse ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'
                }`}
              >
                {params.motionReverse ? 'Reversed (-1)' : 'Forward (+1)'}
              </button>
            </div>
          </div>

          <div className="flex gap-2 pt-2 border-t border-slate-800">
            <button
              onClick={() => handleCopy(cssSnippet, 'css')}
              className="flex-1 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-semibold transition-colors"
            >
              {copiedKey === 'css' ? 'Copied CSS!' : 'Copy CSS'}
            </button>
            <button
              onClick={() => handleCopy(JSON.stringify(params, null, 2), 'json')}
              className="flex-1 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors border border-slate-700"
            >
              {copiedKey === 'json' ? 'Copied JSON!' : 'Copy JSON'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
