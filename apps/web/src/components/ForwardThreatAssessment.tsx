import React, { useState, useMemo } from 'react';
import { IncidentData } from '../types';
import { MapPin } from 'lucide-react';

interface SensitiveAsset {
  id: string;
  name: string;
  category: 'EEZ' | 'Fishery' | 'Habitat';
  categoryLabel: string;
  lat: number;
  lon: number;
  vulnerabilityIndex: number;
  baseSeverity: 'CRITICAL' | 'HIGH' | 'ELEVATED' | 'ADVISORY';
  speciesOrEconomy: string;
  description: string;
  jurisdiction: string;
  cardinalDir: string;
}

const REGIONAL_ASSETS: SensitiveAsset[] = [
  {
    id: 'egypt_eez',
    name: 'Egypt Sovereign EEZ & Coast',
    category: 'EEZ',
    categoryLabel: 'EEZ Jurisdiction',
    lat: 31.65,
    lon: 32.95,
    vulnerabilityIndex: 0.96,
    baseSeverity: 'CRITICAL',
    speciesOrEconomy: 'Sovereign Territorial Waters & Coastal Baseline',
    description: 'Direct offshore surface exposure. Within 26 km of mainland Sinai & Port Said barrier coast.',
    jurisdiction: 'Arab Republic of Egypt',
    cardinalDir: 'S'
  },
  {
    id: 'zaranik_reserve',
    name: 'Zaranik Sanctuary & Lake Bardawil',
    category: 'Habitat',
    categoryLabel: 'Endangered Habitat',
    lat: 31.25,
    lon: 33.25,
    vulnerabilityIndex: 0.98,
    baseSeverity: 'CRITICAL',
    speciesOrEconomy: 'Loggerhead & Green Turtles (Caretta caretta, Chelonia mydas)',
    description: 'Ramsar wetland site. Critical nesting beach for endangered sea turtles and 250k+ migratory waterfowl.',
    jurisdiction: 'North Sinai Biosphere Reserve',
    cardinalDir: 'SE'
  },
  {
    id: 'portsaid_fishery',
    name: 'Port Said & Damietta Trawling Shelf',
    category: 'Fishery',
    categoryLabel: 'Commercial Fishery',
    lat: 31.55,
    lon: 32.55,
    vulnerabilityIndex: 0.92,
    baseSeverity: 'HIGH',
    speciesOrEconomy: 'Mediterranean Red Mullet, Seabream & Penaeid Shrimp',
    description: 'High-density demersal harvesting grounds supplying major Nile Delta fish markets.',
    jurisdiction: 'Egyptian General Authority for Fish Resources (GAFRD)',
    cardinalDir: 'SW'
  },
  {
    id: 'manzala_estuary',
    name: 'Ashtoum El Gamil / Lake Manzala',
    category: 'Habitat',
    categoryLabel: 'Endangered Habitat',
    lat: 31.32,
    lon: 32.22,
    vulnerabilityIndex: 0.88,
    baseSeverity: 'ELEVATED',
    speciesOrEconomy: 'Mullet & Seabass Fry Nursery, Coastal Avian Sanctuary',
    description: 'Brackish barrier lagoon providing essential fish larvae recruitment and coastal marsh protection.',
    jurisdiction: 'Egyptian Environmental Affairs Agency (EEAA)',
    cardinalDir: 'SW'
  },
  {
    id: 'sinai_fishery',
    name: 'North Sinai Inshore Fishery (El Arish)',
    category: 'Fishery',
    categoryLabel: 'Artisanal Fishery',
    lat: 31.35,
    lon: 33.50,
    vulnerabilityIndex: 0.85,
    baseSeverity: 'ELEVATED',
    speciesOrEconomy: 'Artisanal Gillnet Fleet & Migratory Pelagic Stocks',
    description: 'Small-scale coastal fisheries supporting North Sinai artisanal fishermen communities.',
    jurisdiction: 'Sinai Marine Cooperative',
    cardinalDir: 'ESE'
  },
  {
    id: 'levant_eez',
    name: 'Levant Maritime Border & Gaza Sector',
    category: 'EEZ',
    categoryLabel: 'EEZ Jurisdiction',
    lat: 31.55,
    lon: 34.15,
    vulnerabilityIndex: 0.78,
    baseSeverity: 'ADVISORY',
    speciesOrEconomy: 'Transboundary Marine Corridor',
    description: 'Downwind coastal current watch corridor for potential cross-border drift (72h advection window).',
    jurisdiction: 'Eastern Mediterranean Transboundary Zone',
    cardinalDir: 'ENE'
  }
];

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

interface ForwardThreatAssessmentProps {
  data: IncidentData | null;
}

export const ForwardThreatAssessment: React.FC<ForwardThreatAssessmentProps> = ({ data }) => {
  const [selectedCategory, setSelectedCategory] = useState<'ALL' | 'Fishery' | 'EEZ' | 'Habitat'>('ALL');

  // Approximate current/latest drift location from OpenDrift +48H snapshot, fallback to forecast or incident center
  const driftLocation = useMemo(() => {
    const snap48 = data?.forward_snapshots ? data.forward_snapshots['48'] : null;
    if (snap48?.centroid) {
      return { lat: snap48.centroid.lat, lon: snap48.centroid.lon, label: '+48H Projected Centroid' };
    }
    const fwdStep = data?.forward_forecast?.[data.forward_forecast.length - 1];
    if (fwdStep) {
      return { lat: fwdStep.center_lat, lon: fwdStep.center_lon, label: `${fwdStep.step_label} Drift Center` };
    }
    return {
      lat: data?.incident?.center_lat || 31.9255,
      lon: data?.incident?.center_lon || 32.8949,
      label: 'Spill Observed Center'
    };
  }, [data]);

  // Compute live distances from the approx drift location
  const assessedAssets = useMemo(() => {
    return REGIONAL_ASSETS.map(asset => {
      const distKm = Math.round(haversineKm(driftLocation.lat, driftLocation.lon, asset.lat, asset.lon));
      
      // Dynamic severity adjustment based on distance
      let dynamicSeverity = asset.baseSeverity;
      if (distKm <= 35) dynamicSeverity = 'CRITICAL';
      else if (distKm <= 55) dynamicSeverity = 'HIGH';
      else if (distKm <= 75) dynamicSeverity = 'ELEVATED';
      else dynamicSeverity = 'ADVISORY';

      return {
        ...asset,
        distanceKm: distKm,
        severity: dynamicSeverity
      };
    }).sort((a, b) => a.distanceKm - b.distanceKm);
  }, [driftLocation]);

  const filteredAssets = useMemo(() => {
    if (selectedCategory === 'ALL') return assessedAssets;
    return assessedAssets.filter(a => a.category === selectedCategory);
  }, [assessedAssets, selectedCategory]);

  const nearestCoastKm = useMemo(() => {
    const egypt = assessedAssets.find(a => a.id === 'egypt_eez');
    return egypt ? Math.max(14, Math.round(egypt.distanceKm * 0.75)) : 26;
  }, [assessedAssets]);

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40 ring-1 ring-rose-500/20';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'ELEVATED':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      case 'ADVISORY':
      default:
        return 'bg-sky-500/20 text-sky-300 border-sky-500/30';
    }
  };

  return (
    <div className="space-y-3 font-sans">
      {/* Dynamic Telemetry Strip: Drift Vector & Distance to Coast */}
      <div className="p-3 rounded-2xl liquid-glass-subtle border border-white/10 space-y-2">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px] font-heading">
            Coastal Drift Threat
          </span>
          <span className="text-slate-400 font-mono text-[10px] tracking-wider uppercase">
            Estimated
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <div className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06]">
            <span className="text-[10px] text-slate-400 block font-medium">Nearest Coast:</span>
            <span className="text-white font-bold font-mono text-xs">~{nearestCoastKm} km South</span>
            <span className="text-[9px] text-slate-400 block mt-0.5">North Sinai Shoreline</span>
          </div>

          <div className="p-2 rounded-xl bg-white/[0.04] border border-white/[0.06]">
            <span className="text-[10px] text-slate-400 block font-medium">Trajectory Vector:</span>
            <span className="text-cyan-300 font-bold font-mono text-xs">SSE (165°)</span>
            <span className="text-[9px] text-slate-400 block mt-0.5">ERA5 Wind + CMEMS</span>
          </div>
        </div>

        <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-white/[0.06]">
          <span>Projected 48H Center:</span>
          <span className="text-slate-200 font-mono font-semibold">
            {driftLocation.lat.toFixed(3)}°N, {driftLocation.lon.toFixed(3)}°E
          </span>
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.06]">
        {(['ALL', 'Fishery', 'EEZ', 'Habitat'] as const).map(cat => {
          const isActive = selectedCategory === cat;
          const label = cat === 'ALL' ? 'All (6)' : cat === 'Fishery' ? 'Fisheries (2)' : cat === 'EEZ' ? 'EEZ (2)' : 'Habitats (2)';
          return (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`flex-1 py-1 px-1 rounded-lg text-[10px] font-semibold transition-all text-center truncate ${
                isActive 
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-900/40' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Sensitive Assets Threat Cards */}
      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {filteredAssets.map(asset => {
          return (
            <div
              key={asset.id}
              className="p-3 rounded-2xl liquid-glass-subtle border border-white/[0.08] hover:border-white/20 transition-all space-y-1.5"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <h4 className="text-xs font-bold text-white tracking-wide truncate">
                  {asset.name}
                </h4>
                <span className={`px-2 py-0.5 text-[9px] font-extrabold uppercase rounded-full border shrink-0 ${getSeverityBadge(asset.severity)}`}>
                  {asset.severity}
                </span>
              </div>

              {/* Distance & Category Badges */}
              <div className="flex items-center justify-between text-[10px] text-slate-300">
                <span className="flex items-center gap-1 text-slate-400 font-medium">
                  <MapPin className="w-3 h-3 text-rose-400" />
                  <strong className="text-white font-mono">~{asset.distanceKm} km</strong> ({asset.cardinalDir})
                </span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/10 text-slate-300">
                  {asset.categoryLabel}
                </span>
              </div>

              {/* Species or Economic Resource */}
              <div className="text-[11px] text-slate-200 font-medium leading-snug">
                <span className="text-[10px] text-slate-400 block text-[9px] uppercase font-bold tracking-wider mb-0.5">
                  Vulnerable Resource:
                </span>
                {asset.speciesOrEconomy}
              </div>

              {/* Description */}
              <p className="text-[10px] text-slate-400 leading-relaxed pt-1 border-t border-white/[0.06]">
                {asset.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
