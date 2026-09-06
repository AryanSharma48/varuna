import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { inspectRaster, uploadSAR } from '../services/api';
import { KoreanGradation } from './KoreanGradation';
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
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans flex flex-col relative overflow-x-hidden">
      
      {/* Living Ocean Wave Ribbon Field (21st.dev Canvas) */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <KoreanGradation
          className="w-full h-full opacity-30"
          params={{
            wave: 22,
            motionAmount: 0.28,
            grain: 42,
            speed: 100
          }}
        />
      </div>


      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 md:px-12 py-4 shadow-sm relative z-10">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-800 text-white flex items-center justify-center font-bold text-sm rounded border border-blue-700">
              V
            </div>
            <div>
              <span className="font-bold text-white tracking-tight text-base block leading-none">
                VARUNA
              </span>
              <span className="text-[11px] text-slate-400 font-medium tracking-wide">
                Maritime Oil Spill Attribution Platform
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <span className="hidden sm:inline-flex items-center gap-2 px-3 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              RADAR ACTIVE
            </span>
            <button
              onClick={() => navigate('/gradation')}
              className="text-slate-300 hover:text-white transition-colors font-medium flex items-center gap-1.5 px-2.5 py-1 rounded hover:bg-slate-800 border border-transparent hover:border-slate-700"
              title="Open 21st.dev 그라데이션 Ribbon Field Interactive Lab"
            >
              <span>그라데이션 Lab</span>
            </button>
            <a 
              href="/docs" 
              target="_blank" 
              rel="noreferrer" 
              className="text-slate-300 hover:text-white underline font-medium"
            >
              API DOCS
            </a>
            <button
              onClick={handleLaunchDemo}
              className="bg-blue-800 hover:bg-blue-700 text-white font-bold px-4 py-2 rounded text-xs transition-colors border border-blue-700 shadow-sm"
            >
              OPEN DEMO
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto w-full px-6 md:px-12 py-10 space-y-8 flex-1 relative z-10">
        
        {/* Punchy Hero */}
        <section className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="inline-block px-3 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 text-xs font-semibold tracking-wider uppercase mb-1">
            NAVAL RADAR SURVEILLANCE &amp; AIS FUSION
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight leading-tight">
            Satellite Oil Spill Attribution
          </h1>
          <p className="text-sm md:text-base text-slate-400 leading-relaxed">
            Detect marine oil slicks from satellite SAR imagery, reconstruct discharge origin with reverse Lagrangian particle drift, and match vessel trajectories using AIS traffic data.
          </p>
        </section>

        {/* Primary Investigation Hub */}
        <section className="bg-slate-900 border border-slate-800 rounded-xl shadow-lg overflow-hidden">
          {/* Pathway Tabs */}
          <div className="flex border-b border-slate-800 bg-slate-950 p-1.5 gap-1.5">
            <button
              onClick={() => setActiveTab('demo')}
              className={`flex-1 py-2.5 px-4 text-xs font-bold rounded transition-colors text-center ${
                activeTab === 'demo'
                  ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Option 1: Open Benchmark Incident (VARUNA-2026-001)
            </button>
            <button
              onClick={() => setActiveTab('custom')}
              className={`flex-1 py-2.5 px-4 text-xs font-bold rounded transition-colors text-center ${
                activeTab === 'custom'
                  ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Option 2: Process Custom Satellite Observation
            </button>
          </div>

          {/* TAB 1: BENCHMARK DEMO */}
          {activeTab === 'demo' && (
            <div className="p-6 md:p-8 space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-wide">
                    PRE-CONFIGURED BENCHMARK INCIDENT
                  </div>
                  <div className="text-lg font-bold text-white">
                    Incident ID: VARUNA-2026-001
                  </div>
                </div>
                <div className="flex gap-2 text-xs">
                  <span className="px-2.5 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded font-medium">
                    DARTIS 2019 (ow-0388)
                  </span>
                  <span className="px-2.5 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded font-medium">
                    Sentinel-1B GRDH
                  </span>
                </div>
              </div>

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3.5 bg-slate-950 border border-slate-800 rounded">
                  <span className="text-slate-400 block text-[11px]">Centroid</span>
                  <strong className="text-slate-200 text-sm font-bold">31.98° N, 32.85° E</strong>
                  <span className="text-slate-500 block text-[10px] mt-0.5">Levantine Basin</span>
                </div>
                <div className="p-3.5 bg-slate-950 border border-slate-800 rounded">
                  <span className="text-slate-400 block text-[11px]">Slick Area</span>
                  <strong className="text-white text-sm font-bold">14.20 km²</strong>
                  <span className="text-slate-500 block text-[10px] mt-0.5">Perimeter: 28.4 km</span>
                </div>
                <div className="p-3.5 bg-slate-950 border border-slate-800 rounded">
                  <span className="text-slate-400 block text-[11px]">Lagrangian Drift</span>
                  <strong className="text-white text-sm font-bold">-6.0 Hours</strong>
                  <span className="text-slate-500 block text-[10px] mt-0.5">500 Particles Modeled</span>
                </div>
                <div className="p-3.5 bg-slate-950 border border-slate-800 rounded">
                  <span className="text-slate-400 block text-[11px]">Vessel Attribution</span>
                  <strong className="text-blue-400 text-sm font-bold">Ranked Suspects</strong>
                  <span className="text-slate-500 block text-[10px] mt-0.5">AIS Trajectory Matched</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-slate-800">
                <p className="text-xs text-slate-400">
                  Instant launch with pre-indexed SAR mask, origin confidence contours, and AIS suspect ranking.
                </p>
                <button
                  onClick={handleLaunchDemo}
                  className="w-full sm:w-auto bg-blue-800 hover:bg-blue-700 text-white font-bold text-xs px-8 py-3.5 rounded transition-colors border border-blue-700 shadow-sm whitespace-nowrap"
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
                <div className="p-3 bg-red-950 border border-red-800 text-red-200 rounded font-medium">
                  {submitError}
                </div>
              )}

              {/* Title */}
              <div>
                <label className="block text-slate-300 font-bold uppercase mb-1.5">
                  Investigation Title
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full border border-slate-700 rounded p-2.5 text-white bg-slate-950 focus:border-blue-600 focus:outline-none"
                  required
                />
              </div>

              {/* Quick Presets */}
              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded space-y-2">
                <span className="font-bold text-slate-300 uppercase text-[11px] block">
                  Quick Testing Presets (Georeferenced Sentinel-1 GeoTIFF)
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_mumbai_slick.tif', 'Mumbai Offshore Oil Slick — Sentinel-1 SAR')}
                    className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-slate-200 font-medium transition-colors"
                  >
                    Preset 1: Mumbai Offshore (18.925° N, 72.825° E) — Mineral Slick
                  </button>
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_gujarat_calm.tif', 'Gujarat Coast Look-Alike — Sentinel-1 SAR')}
                    className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-slate-200 font-medium transition-colors"
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
                className="border-2 border-dashed border-slate-700 hover:border-slate-500 bg-slate-950 p-6 text-center rounded transition-colors"
              >
                {isInspecting ? (
                  <div className="py-2 text-slate-300 font-semibold">
                    Inspecting GeoTIFF metadata...
                  </div>
                ) : (
                  <div className="space-y-2">
                    <label className="inline-block bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded cursor-pointer font-medium border border-slate-600">
                      Select Satellite Raster
                      <input
                        type="file"
                        onChange={(e) => e.target.files?.[0] && handleFileSelection(e.target.files[0])}
                        className="hidden"
                        accept=".tif,.tiff,.png,.jpg,.jpeg,.nc"
                      />
                    </label>
                    <span className="text-slate-400 text-[11px] block">
                      or drag &amp; drop GeoTIFF / Dual-Pol SAR PNG
                    </span>
                    {selectedFile && (
                      <div className="p-2 bg-slate-900 border border-slate-700 text-slate-200 font-semibold mt-2 inline-block rounded">
                        Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Metadata Box */}
              {fileMetadata && (
                <div className={`p-3 border rounded text-[11px] ${fileMetadata.has_georeference ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-slate-900 border-slate-700 text-slate-300'}`}>
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
                  <label className="block text-slate-300 font-semibold mb-1">Center Latitude (°N)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    className="w-full border border-slate-700 rounded p-2 text-white bg-slate-950 focus:border-blue-600 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Center Longitude (°E)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                    className="w-full border border-slate-700 rounded p-2 text-white bg-slate-950 focus:border-blue-600 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Wind Speed (m/s)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={windSpeed}
                    onChange={(e) => setWindSpeed(e.target.value)}
                    className="w-full border border-slate-700 rounded p-2 text-white bg-slate-950 focus:border-blue-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Current Speed (m/s)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={currentSpeed}
                    onChange={(e) => setCurrentSpeed(e.target.value)}
                    className="w-full border border-slate-700 rounded p-2 text-white bg-slate-950 focus:border-blue-600 focus:outline-none"
                  />
                </div>
              </div>

              {/* Submit */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-slate-800">
                <span className="text-slate-400 text-[11px]">
                  {selectedFile ? `Ready to process ${selectedFile.name}` : 'Using default Sentinel-1 observation if no file uploaded.'}
                </span>
                <button
                  type="submit"
                  disabled={isSubmitting || isInspecting}
                  className="w-full sm:w-auto bg-blue-800 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-xs px-8 py-3.5 rounded transition-colors border border-blue-700 shadow-sm"
                >
                  {isSubmitting ? 'RUNNING ML INFERENCE & DRIFT BACKTRACK...' : 'INITIALIZE PIPELINE →'}
                </button>
              </div>
            </form>
          )}
        </section>

        {/* 4-Step Investigation Roadmap */}
        <RoadmapSection />

      </main>

      {/* Clean Dark Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 px-6 md:px-12 py-4 text-xs text-slate-400 relative z-10">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>VARUNA • Sentinel-1 SAR × Lagrangian Drift × PostGIS AIS</span>
          <div className="flex items-center gap-4 text-[11px]">
            <a href="/docs" target="_blank" rel="noreferrer" className="hover:text-white underline">
              API Documentation
            </a>
            <span>•</span>
            <span className="text-slate-500">SIH 26143</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
