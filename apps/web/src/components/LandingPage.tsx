import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { inspectRaster, uploadSAR } from '../services/api';
import { SmokeShader } from './SmokeShader';
import { RoadmapSection } from './RoadmapSection';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'demo' | 'custom'>('demo');

  // Custom Form Inputs
  const [title, setTitle] = useState('Arabian Sea Sector 4 — Sentinel-1 Observation');
  const [lat, setLat] = useState('18.9200');
  const [lon, setLon] = useState('72.8300');
  const [windSpeed, setWindSpeed] = useState('6.2');
  const [currentSpeed, setCurrentSpeed] = useState('0.35');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileMetadata, setFileMetadata] = useState<any | null>(null);
  const [isInspecting, setIsInspecting] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleLaunchDemo = () => {
    navigate('/investigation/SIH-2026-001/overview');
  };

  const handleFileSelection = async (file: File) => {
    setSelectedFile(file);
    setSubmitError(null);
    setIsInspecting(true);

    try {
      const meta = await inspectRaster(file);
      setFileMetadata(meta);
      if (meta.has_georeference) {
        setLat(meta.center_lat.toFixed(4));
        setLon(meta.center_lon.toFixed(4));
      }
    } catch (err: any) {
      console.warn('Metadata inspection notice:', err.message);
      setFileMetadata({
        has_georeference: false,
        source: 'Standard Raster',
        message: 'Non-georeferenced file. Centroid coordinates must be entered manually.'
      });
    } finally {
      setIsInspecting(false);
    }
  };

  const handleLoadSample = async (sampleUrl: string, sampleTitle: string) => {
    setIsInspecting(true);
    setSubmitError(null);
    try {
      const res = await fetch(sampleUrl);
      if (!res.ok) throw new Error('Failed to load sample');
      const blob = await res.blob();
      const file = new File([blob], sampleUrl.split('/').pop() || 'sample.tif', { type: 'image/tiff' });
      setTitle(sampleTitle);
      await handleFileSelection(file);
    } catch (err: any) {
      setSubmitError(`Could not load sample: ${err.message}`);
    } finally {
      setIsInspecting(false);
    }
  };

  const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      let fileToUpload = selectedFile;
      if (!fileToUpload) {
        const sampleRes = await fetch('/sample_sar_mumbai_slick.tif');
        const blob = await sampleRes.blob();
        fileToUpload = new File([blob], 'sentinel1_observation.tif', { type: 'image/tiff' });
      }

      const formData = new FormData();
      formData.append('file', fileToUpload);
      formData.append('title', title);
      formData.append('lat', lat);
      formData.append('lon', lon);
      formData.append('wind_speed_ms', windSpeed);
      formData.append('current_speed_ms', currentSpeed);

      const res = await uploadSAR(formData);
      navigate(res.redirect_url);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to initialize pipeline');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-slate-100 font-sans flex flex-col relative overflow-x-hidden">
      
      {/* Animated WebGL Smoke Flow Shader Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <SmokeShader className="w-full h-full opacity-60" />
      </div>

      {/* Top-Left Brand Capsule (No full-width ribbon bar) */}
      <div className="pt-6 px-4 sm:px-6 md:px-10 max-w-[1600px] mx-auto w-full flex items-center justify-start relative z-30">
        <div className="inline-flex items-center gap-3.5 liquid-glass px-4 py-3 rounded-2xl border border-white/20 shadow-2xl backdrop-blur-2xl">
          <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center font-extrabold text-xl font-heading border border-white/20 shrink-0">
            V
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-white tracking-tight text-xl sm:text-2xl font-heading leading-tight drop-shadow-sm">
              VARUNA
            </span>
            <span className="text-xs sm:text-sm text-slate-200 font-medium font-sans tracking-wide">
              Maritime Oil Spill Attribution Platform
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto w-full px-4 sm:px-6 md:px-10 py-10 space-y-10 flex-1 relative z-10">
        
        {/* Punchy Hero Centerpiece */}
        <section className="text-center max-w-5xl mx-auto liquid-glass rounded-3xl px-6 sm:px-12 md:px-16 py-12 md:py-16 border border-white/20">
          <div className="space-y-5">

            {/* Dominant Headline (Crisp, High Contrast, No Glows) */}
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold font-heading text-white tracking-tight leading-[1.08]">
              Satellite Oil Spill <br className="hidden sm:inline" />
              Attribution
            </h1>

            {/* Explanatory Deck */}
            <p className="text-sm sm:text-base md:text-lg text-slate-300 leading-relaxed max-w-3xl mx-auto font-normal font-sans">
              Detect marine oil slicks from satellite SAR imagery, reconstruct discharge origin with reverse Lagrangian particle drift, and match rogue vessel trajectories using AIS forensics.
            </p>
          </div>
        </section>

        {/* The Crisis & The Solution Spotlight */}
        <section className="liquid-glass rounded-3xl overflow-hidden shadow-2xl w-full border border-white/15">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 items-stretch">
            
            {/* Left Content Column */}
            <div className="lg:col-span-6 p-6 sm:p-8 md:p-10 lg:p-12 flex flex-col justify-between space-y-6">
              
              {/* Problem: Oil Spills in Harsh Reality */}
              <div className="space-y-3">
                <h2 className="text-xl sm:text-2xl font-bold font-heading text-white tracking-tight leading-snug">
                  Millions of Tonnes of Toxic Crude &amp; Bilge Dumped in Complete Secrecy
                </h2>

                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal font-sans">
                  Oil spills are catastrophic, suffocating oceanic ecosystems, wiping out coastal fisheries, and decimating marine wildlife for generations. Rogue vessels routinely exploit the open ocean’s vastness—purposely turning off AIS trackers under dark hours to illegally flush toxic bilge and wash cargo tanks with near-total impunity.
                </p>
              </div>

              {/* Solution: How Varuna Solves It */}
              <div className="border-t border-white/10 pt-5 space-y-3">
                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">
                  <strong className="text-white font-bold">Varuna eliminates the blind spots.</strong> By combining all-weather space radar satellites with backward Lagrangian ocean drift simulation and AIS pattern forensics, Varuna rewinds oceanic currents to pinpoint the exact discharge coordinate, matches rogue vessel trajectories, and generates court-admissible attribution evidence.
                </p>

                <div className="flex flex-wrap gap-2 pt-1 text-[11px] font-medium text-slate-200">
                  <span className="liquid-glass-interactive px-3 py-1 rounded-xl text-white font-medium text-[11px]">
                    Zero-Blindspot Radar
                  </span>
                  <span className="liquid-glass-interactive px-3 py-1 rounded-xl text-white font-medium text-[11px]">
                    Reverse Ocean Drift
                  </span>
                  <span className="liquid-glass-interactive px-3 py-1 rounded-xl text-white font-medium text-[11px]">
                    AIS Ghost-Ship Forensics
                  </span>
                </div>
              </div>

            </div>

            {/* Right Column: User's Oil Spill Image */}
            <div className="lg:col-span-6 relative min-h-[300px] sm:min-h-[360px] lg:min-h-full overflow-hidden border-t lg:border-t-0 lg:border-l border-white/10">
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

        {/* Primary Investigation Hub */}
        <section className="liquid-glass rounded-2xl shadow-2xl overflow-hidden border border-white/15">
          {/* Pathway Tabs */}
          <div className="flex border-b border-white/10 p-1.5 gap-1.5 bg-white/5 backdrop-blur-md">
            <button
              onClick={() => setActiveTab('demo')}
              className={`flex-1 py-2.5 px-4 text-xs font-bold rounded-xl transition-all text-center ${
                activeTab === 'demo'
                  ? 'liquid-glass text-white shadow-md border border-white/25'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              Option 1: Open Benchmark Incident (VARUNA-2026-001)
            </button>
            <button
              onClick={() => setActiveTab('custom')}
              className={`flex-1 py-2.5 px-4 text-xs font-bold rounded-xl transition-all text-center ${
                activeTab === 'custom'
                  ? 'liquid-glass text-white shadow-md border border-white/25'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              Option 2: Process Custom Satellite Observation
            </button>
          </div>

          {/* TAB 1: BENCHMARK DEMO */}
          {activeTab === 'demo' && (
            <div className="p-6 md:p-8 space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
                <div>
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wide">
                    PRE-CONFIGURED BENCHMARK INCIDENT
                  </div>
                  <div className="text-lg font-bold text-white">
                    Incident ID: VARUNA-2026-001
                  </div>
                </div>
                <div className="flex gap-2 text-xs">
                  <span className="px-2.5 py-1 liquid-glass-subtle text-slate-200 rounded-lg font-medium">
                    DARTIS 2019 (ow-0388)
                  </span>
                  <span className="px-2.5 py-1 liquid-glass-subtle text-slate-200 rounded-lg font-medium">
                    Sentinel-1B GRDH
                  </span>
                </div>
              </div>

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3.5 liquid-glass-subtle border border-white/10 rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Centroid</span>
                  <strong className="text-white text-sm font-bold">31.98° N, 32.85° E</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">Levantine Basin</span>
                </div>
                <div className="p-3.5 liquid-glass-subtle border border-white/10 rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Slick Area</span>
                  <strong className="text-white text-sm font-bold">14.20 km²</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">Perimeter: 28.4 km</span>
                </div>
                <div className="p-3.5 liquid-glass-subtle border border-white/10 rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Lagrangian Drift</span>
                  <strong className="text-white text-sm font-bold">-6.0 Hours</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">500 Particles Modeled</span>
                </div>
                <div className="p-3.5 liquid-glass-subtle border border-white/10 rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Vessel Attribution</span>
                  <strong className="text-sky-400 text-sm font-bold">Ranked Suspects</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">AIS Trajectory Matched</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/10">
                <p className="text-xs text-slate-300">
                  Instant launch with pre-indexed SAR mask, origin confidence contours, and AIS suspect ranking.
                </p>
                <button
                  onClick={handleLaunchDemo}
                  className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-8 py-3.5 rounded-xl transition-all shadow-lg hover:shadow-blue-500/25 whitespace-nowrap border border-white/20"
                >
                  LAUNCH INVESTIGATION WORKSPACE →
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: CUSTOM SATELLITE INGESTION */}
          {activeTab === 'custom' && (
            <form onSubmit={handleCustomSubmit} className="p-6 md:p-8 space-y-6 text-xs">
              {submitError && (
                <div className="p-3 bg-red-950/80 backdrop-blur-md border border-red-500/50 text-red-200 rounded-xl font-medium">
                  {submitError}
                </div>
              )}

              {/* Title */}
              <div>
                <label className="block text-slate-200 font-bold uppercase mb-1.5">
                  Investigation Title
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full border border-white/15 rounded-xl p-2.5 text-white bg-black/40 backdrop-blur-md focus:border-sky-400 focus:outline-none"
                  required
                />
              </div>

              {/* Quick Presets */}
              <div className="p-4 liquid-glass-subtle border border-white/10 rounded-2xl space-y-2.5">
                <span className="font-bold text-slate-200 uppercase text-[11px] block">
                  Quick Testing Presets (Georeferenced Sentinel-1 GeoTIFF)
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_mumbai_slick.tif', 'Mumbai Offshore Oil Slick — Sentinel-1 SAR')}
                    className="px-3 py-1.5 liquid-glass-interactive rounded-xl text-slate-200 font-medium"
                  >
                    Preset 1: Mumbai Offshore (18.925° N, 72.825° E) — Mineral Slick
                  </button>
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_gujarat_calm.tif', 'Gujarat Coast Look-Alike — Sentinel-1 SAR')}
                    className="px-3 py-1.5 liquid-glass-interactive rounded-xl text-slate-200 font-medium"
                  >
                    Preset 2: Gujarat Coast (20.825° N, 70.425° E) — Calm Sea Look-Alike
                  </button>
                </div>
              </div>

              {/* File Dropzone */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files?.[0]) {
                    handleFileSelection(e.dataTransfer.files[0]);
                  }
                }}
                className="border-2 border-dashed border-white/20 hover:border-white/40 bg-white/5 backdrop-blur-md p-6 text-center rounded-2xl transition-all"
              >
                {isInspecting ? (
                  <div className="py-2 text-slate-200 font-semibold">
                    Inspecting GeoTIFF metadata...
                  </div>
                ) : (
                  <div className="space-y-2">
                    <label className="inline-block liquid-glass-interactive text-white px-4 py-2 rounded-xl cursor-pointer font-medium">
                      Select Satellite Raster
                      <input
                        type="file"
                        onChange={(e) => e.target.files?.[0] && handleFileSelection(e.target.files[0])}
                        className="hidden"
                        accept=".tif,.tiff,.png,.jpg,.jpeg,.nc"
                      />
                    </label>
                    <span className="text-slate-300 text-[11px] block">
                      or drag &amp; drop GeoTIFF / Dual-Pol SAR PNG
                    </span>
                    {selectedFile && (
                      <div className="p-2 liquid-glass-subtle border border-white/15 text-slate-200 font-semibold mt-2 inline-block rounded-xl">
                        Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Metadata Box */}
              {fileMetadata && (
                <div className={`p-3.5 border border-white/10 rounded-2xl text-[11px] liquid-glass-subtle text-slate-200`}>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Source</span>
                      <strong className="text-white">{fileMetadata.source}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">CRS</span>
                      <strong className="text-slate-200">{fileMetadata.crs || 'Unprojected'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Centroid</span>
                      <strong className="text-slate-200">{lat}° N, {lon}° E</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Dimensions</span>
                      <strong className="text-white">{fileMetadata.width || 256} × {fileMetadata.height || 256}</strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Coordinates & Forcing */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <label className="block text-slate-200 font-semibold mb-1">Center Latitude (°N)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    className="w-full border border-white/15 rounded-xl p-2 text-white bg-black/40 backdrop-blur-md focus:border-sky-400 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-200 font-semibold mb-1">Center Longitude (°E)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                    className="w-full border border-white/15 rounded-xl p-2 text-white bg-black/40 backdrop-blur-md focus:border-sky-400 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-200 font-semibold mb-1">Wind Speed (m/s)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={windSpeed}
                    onChange={(e) => setWindSpeed(e.target.value)}
                    className="w-full border border-white/15 rounded-xl p-2 text-white bg-black/40 backdrop-blur-md focus:border-sky-400 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-200 font-semibold mb-1">Current Speed (m/s)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={currentSpeed}
                    onChange={(e) => setCurrentSpeed(e.target.value)}
                    className="w-full border border-white/15 rounded-xl p-2 text-white bg-black/40 backdrop-blur-md focus:border-sky-400 focus:outline-none"
                  />
                </div>
              </div>

              {/* Submit */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/10">
                <span className="text-slate-300 text-[11px]">
                  {selectedFile ? `Ready to process ${selectedFile.name}` : 'Using default Sentinel-1 observation if no file uploaded.'}
                </span>
                <button
                  type="submit"
                  disabled={isSubmitting || isInspecting}
                  className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-xs px-8 py-3.5 rounded-xl transition-all border border-white/20 shadow-lg hover:shadow-blue-500/25"
                >
                  {isSubmitting ? 'RUNNING ML INFERENCE & DRIFT BACKTRACK...' : 'INITIALIZE PIPELINE →'}
                </button>
              </div>
            </form>
          )}
        </section>

      </main>

      {/* Clean Dark Footer */}
      <footer className="liquid-glass border-t border-white/10 px-6 md:px-12 py-4 text-xs text-slate-300 relative z-10">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>VARUNA • Sentinel-1 SAR × Lagrangian Drift × PostGIS AIS</span>
          <div className="flex items-center gap-4 text-[11px]">
            <a href="/docs" target="_blank" rel="noreferrer" className="hover:text-white underline">
              API Documentation
            </a>
            <span>•</span>
            <span className="text-slate-400">SIH 26143</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
