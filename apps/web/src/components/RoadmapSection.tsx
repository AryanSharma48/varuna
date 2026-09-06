import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface RoadmapStep {
  step: string;
  phase: string;
  title: string;
  description: string;
  tags: string[];
  route: string;
  buttonLabel: string;
  icon: React.ReactNode;
}

const stepsData: RoadmapStep[] = [
  {
    step: '01',
    phase: 'DETECTION',
    title: 'Scan & Spot the Spill',
    description:
      'Satellites take high-resolution radar photos of the ocean day and night, even through storm clouds. Our smart system instantly scans the water surface to detect dark patches where oil has leaked.',
    tags: ['Satellite Radar', 'Day & Night Vision', 'All-Weather'],
    route: '/investigation/SIH-2026-001/satellite',
    buttonLabel: 'View Satellite Scan →',
    icon: (
      <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    step: '02',
    phase: 'VERIFICATION',
    title: 'Filter Out False Alarms',
    description:
      'Natural occurrences like seaweed clusters, algae blooms, or glassy calm waters can look just like oil on camera. We analyze the water ripples so authorities never waste time investigating harmless sea life.',
    tags: ['Wave Ripple Check', 'Zero False Alarms', 'Confirmed Oil'],
    route: '/investigation/SIH-2026-001/overview',
    buttonLabel: 'Check Verification →',
    icon: (
      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    step: '03',
    phase: 'DRIFT BACKTRACK',
    title: 'Rewind the Ocean Currents',
    description:
      'Wind and ocean tides push floating oil miles away from where it was dropped. We simulate sea currents backward in time like a rewind tape to find the exact time and GPS location the spill started.',
    tags: ['Water & Wind Currents', 'Reverse Simulation', 'Origin Point Found'],
    route: '/investigation/SIH-2026-001/origin',
    buttonLabel: 'Trace Origin Backtrack →',
    icon: (
      <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    step: '04',
    phase: 'ATTRIBUTION',
    title: 'Find the Responsible Ship',
    description:
      'We cross-reference the spill origin with live ship GPS records. Vessels that crossed the spill area, made sudden erratic turns, slowed down, or secretly turned off their tracking beacons are ranked as prime suspects.',
    tags: ['Ship GPS Logs', 'Blackout Tracking', 'Evidence Report'],
    route: '/investigation/SIH-2026-001/attribution',
    buttonLabel: 'Inspect Suspect Ships →',
    icon: (
      <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
];

const RoadmapCard: React.FC<{
  item: RoadmapStep;
  index: number;
}> = ({ item, index }) => {
  const [isVisible, setIsVisible] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      {
        threshold: 0.15,
        rootMargin: '0px 0px -50px 0px',
      }
    );

    if (cardRef.current) {
      observer.observe(cardRef.current);
    }

    return () => {
      observer.disconnect();
    };
  }, []);

  const isEven = index % 2 === 0;

  return (
    <div
      ref={cardRef}
      className={`relative flex items-center md:justify-between mb-12 last:mb-0 transition-all duration-700 ease-out transform ${
        isVisible
          ? 'opacity-100 translate-y-0'
          : 'opacity-0 translate-y-12'
      }`}
    >
      {/* Node / Badge on the Roadmap track */}
      <div className="absolute left-6 md:left-1/2 -translate-x-1/2 z-20 flex items-center justify-center">
        <div className="w-12 h-12 rounded-full bg-slate-900 border-2 border-blue-500 shadow-md flex items-center justify-center text-white font-mono font-bold text-sm">
          {item.step}
        </div>
      </div>

      {/* Card Content - Staggered Left and Right on Desktop */}
      <div
        className={`w-full pl-16 md:pl-0 ${
          isEven
            ? 'md:w-[44%] md:mr-auto md:text-right'
            : 'md:w-[44%] md:ml-auto md:text-left'
        }`}
      >
        <div className="bg-slate-900/90 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all rounded-xl p-6 shadow-md">
          {/* Header Row */}
          <div
            className={`flex items-center gap-2 mb-2 ${
              isEven ? 'md:justify-end' : 'md:justify-start'
            }`}
          >
            <div className="p-1.5 rounded bg-slate-800/80 border border-slate-700/60 inline-flex">
              {item.icon}
            </div>
            <span className="text-[11px] font-bold tracking-widest text-blue-400 uppercase">
              {item.step} / {item.phase}
            </span>
          </div>

          {/* Title */}
          <h3 className="text-lg md:text-xl font-bold text-white mb-2 tracking-tight">
            {item.title}
          </h3>

          {/* Simple, Non-Jargon Description */}
          <p className="text-slate-300 text-xs md:text-sm leading-relaxed mb-4">
            {item.description}
          </p>

          {/* Tags */}
          <div
            className={`flex flex-wrap gap-1.5 mb-4 ${
              isEven ? 'md:justify-end' : 'md:justify-start'
            }`}
          >
            {item.tags.map((tag, tIdx) => (
              <span
                key={tIdx}
                className="text-[11px] bg-slate-950/80 border border-slate-800 text-slate-400 px-2.5 py-0.5 rounded font-medium"
              >
                {tag}
              </span>
            ))}
          </div>

          {/* Action Link */}
          <div className={isEven ? 'md:flex md:justify-end' : ''}>
            <button
              onClick={() => navigate(item.route)}
              className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded border border-slate-700"
            >
              {item.buttonLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export const RoadmapSection: React.FC = () => {
  return (
    <section className="py-16 relative z-10 max-w-5xl mx-auto px-4 sm:px-6">
      {/* Section Title */}
      <div className="text-center space-y-3 mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-blue-950/60 border border-blue-800/50 text-blue-300 text-xs font-semibold tracking-wider uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
          INVESTIGATION PIPELINE ROADMAP
        </div>
        <h2 className="text-2xl md:text-4xl font-extrabold text-white tracking-tight">
          How Varuna Finds the Culprit
        </h2>
        <p className="text-slate-400 text-sm max-w-xl mx-auto leading-relaxed">
          Four automated steps that take you from a raw satellite picture of the open ocean to identifying the exact ship responsible for the oil spill.
        </p>
      </div>

      {/* Roadmap Timeline Container */}
      <div className="relative">
        {/* Continuous Vertical Connecting Line */}
        <div className="absolute top-6 bottom-6 left-6 md:left-1/2 -translate-x-1/2 w-0.5 bg-gradient-to-b from-blue-500 via-indigo-500 to-slate-800 z-0"></div>

        {/* Roadmap Steps */}
        <div className="relative z-10 space-y-2">
          {stepsData.map((item, index) => (
            <RoadmapCard key={item.step} item={item} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
};
