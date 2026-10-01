import React from 'react';

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
    phase: 'RADAR DETECTION',
    title: 'Spot the slick on radar',
    description:
      'Synthetic aperture radar on Sentinel-1 pierces cloud cover and darkness. Oil dampens surface capillary ripples, creating dark contrast patches against rough sea clutter.',
    tags: ['Sentinel-1 SAR', 'Cloud Penetration', 'Surface Roughness'],
    route: '/investigation/VARUNA-2026-001/satellite',
    buttonLabel: 'View Radar Scan →',
  },
  {
    step: '02',
    phase: 'VERIFICATION',
    title: 'Filter out look-alikes',
    description:
      'Low-wind zones, algal blooms, and upwelling also appear dark on radar. We evaluate boundary gradients, damping ratios, and wind speeds so patrol teams do not chase false alarms.',
    tags: ['Damping Ratio', 'False Alarm Filter', 'Confirmed Oil'],
    route: '/investigation/VARUNA-2026-001/overview',
    buttonLabel: 'Check Verification →',
  },
  {
    step: '03',
    phase: 'DRIFT BACKTRACK',
    title: 'Backtrack ocean drift',
    description:
      'Surface currents and wind push oil miles away from where the vessel dumped it. We run reverse Lagrangian particle simulations using NOAA winds and Copernicus currents to pinpoint the release point and time.',
    tags: ['NOAA Wind Fields', 'Copernicus Currents', 'Origin GPS Coordinates'],
    route: '/investigation/VARUNA-2026-001/origin',
    buttonLabel: 'Trace Origin Backtrack →',
  },
  {
    step: '04',
    phase: 'SHIP ATTRIBUTION',
    title: 'Identify suspect vessels',
    description:
      'We cross-reference the origin window with historical AIS ship broadcasts. Ships that crossed the release zone, slowed down, turned sharply, or switched off their transponders are scored as suspects.',
    tags: ['AIS Transponder Logs', 'Track Anomalies', 'Suspect Scoring'],
    route: '/investigation/VARUNA-2026-001/attribution',
    buttonLabel: 'Inspect Suspect Ships →',
  },
];

const RoadmapCard: React.FC<{
  item: RoadmapStep;
  index: number;
}> = ({ item, index }) => {
  const isEven = index % 2 === 0;

  return (
    <div
      className="relative flex items-center md:justify-between mb-16 last:mb-0"
    >
      {/* Node / Badge on the Roadmap track */}
      <div className="absolute left-6 md:left-1/2 -translate-x-1/2 z-20 flex items-center justify-center">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center font-mono font-bold text-sm liquid-glass text-white shadow-[0_0_20px_rgba(255,255,255,0.1)]"
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
        <div className="liquid-glass rounded-2xl p-6 sm:p-7 shadow-xl">
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
            className={`flex flex-wrap gap-1.5 ${
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
          How Varuna traces spills to the source
        </h2>
        <p className="text-slate-200 text-xs md:text-sm max-w-xl mx-auto leading-relaxed font-normal font-sans">
          Four stages from raw satellite radar to identifying which vessel dumped the oil.
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
