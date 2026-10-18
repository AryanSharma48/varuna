import React from 'react';
import { useNavigate } from 'react-router-dom';
import { WavesShader } from './WavesShader';
import { RoadmapSection } from './RoadmapSection';
import { Play, ShieldAlert, Satellite, Compass, Ship, FileCheck, ArrowRight } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const handleLaunchDemo = () => {
    navigate('/investigation/VARUNA-2026-001/overview');
  };

  return (
    <div className="min-h-screen bg-black text-slate-100 font-sans flex flex-col relative overflow-x-hidden">
      
      {/* Animated WebGL Waves Flow Shader Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <WavesShader className="w-full h-full" />
      </div>

      {/* Main Content */}
      <main className="max-w-[1500px] mx-auto w-full px-4 sm:px-6 md:px-10 py-10 space-y-12 flex-1 relative z-10">
        
        {/* Hero Title */}
        <section className="text-center max-w-5xl mx-auto pt-8 pb-4 flex flex-col items-center justify-center space-y-4">
          <h1 className="flex items-center justify-center w-full">
            <span 
              className="text-6xl sm:text-8xl md:text-9xl lg:text-[10rem] font-bold tracking-normal leading-none font-amita select-none bg-clip-text text-transparent"
              style={{ 
                fontFamily: "'Amita', cursive",
                backgroundImage: 'linear-gradient(180deg, #38bdf8, #1d4ed8)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                color: 'transparent'
              }}
            >
              वरुण
            </span>
          </h1>

          <div className="space-y-2">
            <p className="text-xs sm:text-sm md:text-base font-semibold tracking-widest uppercase text-sky-400">
              Autonomous Maritime Oil Spill Forensic Attribution Platform
            </p>
            <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
              Detect dark bilge discharges via Sentinel-1 SAR, model reverse Lagrangian ocean drift, and correlate AIS ship trajectories to identify polluting vessels with verifiable legal evidence.
            </p>
          </div>
        </section>

        {/* PRIMARY JUDGES CTA HUB (Prominent, Central, High Impact) */}
        <section className="max-w-4xl mx-auto w-full">
          <div className="relative group">
            {/* Ambient Glow */}
            <div className="absolute -inset-1 bg-gradient-to-r from-sky-500 via-blue-600 to-cyan-400 rounded-3xl blur-xl opacity-40 group-hover:opacity-60 transition duration-1000"></div>
            
            <div className="relative liquid-glass rounded-3xl p-6 sm:p-10 md:p-12 border border-sky-400/30 shadow-2xl backdrop-blur-2xl text-center space-y-8">
              
              {/* Headline */}
              <div className="space-y-2 max-w-2xl mx-auto pt-2">
                <h2 className="text-2xl sm:text-4xl md:text-5xl font-extrabold text-white tracking-tight leading-tight">
                  Eastern Mediterranean Oil Discharge Investigation
                </h2>
                <p className="text-sm sm:text-base text-slate-300">
                  Full multi-stage evaluation pipeline preloaded with verified Sentinel-1 radar scene, Lagrangian drift particles, and AIS historical vessel tracking data.
                </p>
              </div>

              {/* 4 Feature Badges */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-left">
                <div className="p-3.5 liquid-glass-subtle rounded-2xl border border-white/5 space-y-1">
                  <div className="flex items-center gap-1.5 text-sky-400 text-xs font-bold">
                    <Satellite className="w-4 h-4" />
                    <span>Sentinel-1 SAR</span>
                  </div>
                  <div className="text-base sm:text-lg font-bold text-white">14.20 km²</div>
                  <div className="text-[11px] text-slate-400">Verified Mineral Slick</div>
                </div>

                <div className="p-3.5 liquid-glass-subtle rounded-2xl border border-white/5 space-y-1">
                  <div className="flex items-center gap-1.5 text-cyan-400 text-xs font-bold">
                    <Compass className="w-4 h-4" />
                    <span>Lagrangian Drift</span>
                  </div>
                  <div className="text-base sm:text-lg font-bold text-white">-6h Backtrack</div>
                  <div className="text-[11px] text-slate-400">500 Ocean Particles</div>
                </div>

                <div className="p-3.5 liquid-glass-subtle rounded-2xl border border-white/5 space-y-1">
                  <div className="flex items-center gap-1.5 text-amber-400 text-xs font-bold">
                    <Ship className="w-4 h-4" />
                    <span>AIS Telemetry</span>
                  </div>
                  <div className="text-base sm:text-lg font-bold text-white">3 Suspects</div>
                  <div className="text-[11px] text-slate-400">Dark Vessel Flagged</div>
                </div>

                <div className="p-3.5 liquid-glass-subtle rounded-2xl border border-white/5 space-y-1">
                  <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-bold">
                    <FileCheck className="w-4 h-4" />
                    <span>Dossier</span>
                  </div>
                  <div className="text-base sm:text-lg font-bold text-white">SHA-256 PDF</div>
                  <div className="text-[11px] text-slate-400">Legal Grade Evidence</div>
                </div>
              </div>

              {/* MASSIVE CENTRAL CTA BUTTON */}
              <div className="pt-2 flex flex-col items-center justify-center space-y-3">
                <button
                  id="btn-launch-demo"
                  onClick={handleLaunchDemo}
                  className="w-full sm:w-auto min-w-[320px] sm:min-w-[420px] group/btn inline-flex items-center justify-center gap-3 px-8 sm:px-12 py-5 sm:py-6 text-base sm:text-xl font-extrabold text-white bg-blue-600 hover:bg-blue-500 active:bg-blue-700 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-200"
                >
                  <Play className="w-6 h-6 fill-white text-white group-hover/btn:scale-110 transition-transform" />
                  <span className="tracking-wide">Launch Investigation Demo</span>
                  <ArrowRight className="w-6 h-6 text-white group-hover/btn:translate-x-1 transition-transform" />
                </button>

                <p className="text-xs text-slate-400 flex items-center justify-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>Instant Interactive Demo • No Upload or Setup Required</span>
                </p>
              </div>

            </div>
          </div>
        </section>

        {/* The Crisis & The Solution Spotlight */}
        <section className="liquid-glass rounded-3xl overflow-hidden shadow-2xl w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 items-stretch">
            
            {/* Left Content Column */}
            <div className="lg:col-span-6 p-6 sm:p-8 md:p-10 lg:p-12 flex flex-col justify-center space-y-6 sm:space-y-8">
              
              {/* Problem */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-red-400 text-xs sm:text-sm font-bold uppercase tracking-wider">
                  <ShieldAlert className="w-4 h-4" />
                  <span>The Enforcement Challenge</span>
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold font-heading text-white tracking-tight leading-tight">
                  Tankers dump oily bilge at night and turn off transponders to avoid fines.
                </h2>

                <p className="text-base sm:text-lg text-slate-200 leading-relaxed font-normal font-sans">
                  Most marine oil pollution does not come from tanker shipwrecks. It comes from cargo vessels routinely washing tanks and flushing oily engine bilge into open waters, knowing coast guards rarely catch them.
                </p>
              </div>

              {/* Solution */}
              <div className="space-y-4">
                <p className="text-base sm:text-lg text-slate-200 leading-relaxed">
                  <strong className="text-white font-bold">Varuna traces the slick back to the ship.</strong> We analyze satellite radar to spot fresh slicks, simulate ocean currents backward to find where the oil was dropped, and match that window with ship tracking data.
                </p>

                <div className="flex flex-wrap gap-2.5 pt-2 text-xs sm:text-sm font-medium text-slate-200">
                  <span className="liquid-glass-interactive px-3.5 py-1.5 rounded-xl text-white font-medium text-xs sm:text-sm">
                    Satellite Radar Detection
                  </span>
                  <span className="liquid-glass-interactive px-3.5 py-1.5 rounded-xl text-white font-medium text-xs sm:text-sm">
                    Reverse Drift Backtrack
                  </span>
                  <span className="liquid-glass-interactive px-3.5 py-1.5 rounded-xl text-white font-medium text-xs sm:text-sm">
                    Vessel AIS Forensics
                  </span>
                </div>
              </div>

            </div>

            {/* Right Column: Oil Spill Image */}
            <div className="lg:col-span-6 relative min-h-[300px] sm:min-h-[360px] lg:min-h-full overflow-hidden">
              <img
                src="/oil_spill_disaster.jpg?v=2"
                alt="Aerial view of marine oil spill disaster and response vessel"
                className="absolute inset-0 w-full h-full object-cover object-center transform hover:scale-105 transition-transform duration-700 ease-out"
              />
            </div>

          </div>
        </section>

        {/* 4-Step Investigation Roadmap */}
        <RoadmapSection />

      </main>
    </div>
  );
};
