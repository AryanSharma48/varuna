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
        setIsVisible(entry.isIntersecting);
      },
      {
        threshold: 0.15,
        rootMargin: '0px 0px -80px 0px',
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
      className={`relative flex items-center md:justify-between mb-16 last:mb-0 transition-all duration-700 ease-out transform ${
        isVisible
          ? 'opacity-100 translate-y-0 scale-100'
          : 'opacity-0 translate-y-16 scale-95'
      }`}
    >
      {/* Node / Badge on the Roadmap track */}
      <div className="absolute left-6 md:left-1/2 -translate-x-1/2 z-20 flex items-center justify-center">
        <div
          className={`w-12 h-12 rounded-full transition-all duration-500 flex items-center justify-center font-mono font-bold text-sm ${
            isVisible
              ? 'liquid-glass border-2 border-white/40 text-white scale-105 shadow-[0_0_20px_rgba(255,255,255,0.15)]'
              : 'liquid-glass-subtle text-slate-400 scale-90 opacity-60'
          }`}
        >
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
        <div className={`liquid-glass hover:border-white/30 transition-all duration-300 rounded-2xl p-6 sm:p-7 shadow-xl hover:-translate-y-1`}>
          {/* Header Row */}
          <div
            className={`flex items-center gap-2 mb-2 ${
              isEven ? 'md:justify-end' : 'md:justify-start'
            }`}
          >
            <span className="text-[11px] font-bold tracking-widest text-sky-400 uppercase">
              {item.step} / {item.phase}
            </span>
          </div>

          {/* Title */}
          <h3 className="text-lg md:text-xl font-bold font-heading text-white mb-2 tracking-tight">
            {item.title}
          </h3>

          {/* Simple, Non-Jargon Description */}
          <p className="text-slate-200 text-xs md:text-sm leading-relaxed mb-4 font-normal font-sans">
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
                className="text-[11px] liquid-glass-subtle text-slate-200 px-2.5 py-0.5 rounded-lg font-medium"
              >
                {tag}
              </span>
            ))}
          </div>

          {/* Action Link */}
          <div className={isEven ? 'md:flex md:justify-end' : ''}>
            <button
              onClick={() => navigate(item.route)}
              className="text-xs font-semibold text-white transition-all inline-flex items-center gap-1.5 liquid-glass-interactive px-3.5 py-1.5 rounded-xl"
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
      <div className="text-center space-y-2 mb-16 max-w-2xl mx-auto liquid-glass rounded-2xl px-8 py-6 shadow-2xl">
        <h2 className="text-2xl md:text-3xl font-bold font-heading text-white tracking-tight">
          How Varuna Finds the Culprit
        </h2>
        <p className="text-slate-200 text-xs md:text-sm max-w-xl mx-auto leading-relaxed font-normal font-sans">
          Four automated steps that take you from a raw satellite picture of the open ocean to identifying the exact ship responsible for the oil spill.
        </p>
      </div>

      {/* Roadmap Timeline Container */}
      <div className="relative">
        {/* Continuous Vertical Connecting Line */}
        <div className="absolute top-6 bottom-6 left-6 md:left-1/2 -translate-x-1/2 w-0.5 bg-white/20 z-0"></div>

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
