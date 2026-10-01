import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { inspectRaster, uploadSAR } from '../services/api';
import { WavesShader } from './WavesShader';
import { RoadmapSection } from './RoadmapSection';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'demo' | 'custom'>('demo');

  // Custom Form Inputs
  const [title, setTitle] = useState('Arabian Sea Sector 4: Sentinel-1 Observation');
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
    navigate('/investigation/VARUNA-2026-001/overview');
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
      
      {/* Animated WebGL Waves Flow Shader Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <WavesShader className="w-full h-full" />
      </div>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto w-full px-4 sm:px-6 md:px-10 py-10 space-y-10 flex-1 relative z-10">
        
        {/* Hero Title - Seamless without background box */}
        <section className="text-center max-w-7xl mx-auto py-12 sm:py-16 md:py-20 flex items-center justify-center">
          <h1 className="flex items-center justify-center w-full">
            <span 
              className="text-6xl sm:text-8xl md:text-9xl lg:text-[10rem] xl:text-[12rem] font-bold tracking-normal leading-none font-amita select-none bg-clip-text text-transparent"
              style={{ 
                fontFamily: "'Amita', cursive",
                backgroundImage: 'linear-gradient(180deg, #0b1d3a, #1a56db)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                color: 'transparent'
              }}
            >
              वरुण
            </span>
          </h1>
        </section>

        {/* Primary Investigation Hub */}
        <section className="liquid-glass rounded-2xl shadow-2xl overflow-hidden">
          {/* Pathway Tabs */}
          <div className="flex p-1.5 gap-1.5 bg-white/5 backdrop-blur-md">
            <button
              onClick={() => setActiveTab('demo')}
              className={`flex-1 py-2.5 px-4 text-xs font-bold rounded-xl transition-all text-center ${
                activeTab === 'demo'
                  ? 'liquid-glass text-white shadow-md'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              Option 1: View Sample Incident (14.2 km² Levantine Basin Slick)
            </button>
            <button
              onClick={() => setActiveTab('custom')}
              className={`flex-1 py-2.5 px-4 text-xs font-bold rounded-xl transition-all text-center ${
                activeTab === 'custom'
                  ? 'liquid-glass text-white shadow-md'
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              Option 2: Upload Your Own Satellite Image
            </button>
          </div>

          {/* TAB 1: BENCHMARK DEMO */}
          {activeTab === 'demo' && (
            <div className="p-6 md:p-8 space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3 pb-4">
                <div>
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wide">
                    VERIFIED SAMPLE INCIDENT
                  </div>
                  <div className="text-lg font-bold text-white">
                    Incident VARUNA-2026-001 (Eastern Mediterranean)
                  </div>
                </div>
                <div className="flex gap-2 text-xs">
                  <span className="px-2.5 py-1 liquid-glass-subtle text-slate-200 rounded-lg font-medium">
                    DARTIS 2019 (ow-0388)
                  </span>
                  <span className="px-2.5 py-1 liquid-glass-subtle text-slate-200 rounded-lg font-medium">
                    Sentinel-1B Radar
                  </span>
                </div>
              </div>

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3.5 liquid-glass-subtle rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Centroid</span>
                  <strong className="text-white text-sm font-bold">31.98° N, 32.85° E</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">Levantine Basin</span>
                </div>
                <div className="p-3.5 liquid-glass-subtle rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Slick Area</span>
                  <strong className="text-white text-sm font-bold">14.20 km²</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">28.4 km perimeter</span>
                </div>
                <div className="p-3.5 liquid-glass-subtle rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Drift Backtrack</span>
                  <strong className="text-white text-sm font-bold">6 hours back</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">500 particles tracked</span>
                </div>
                <div className="p-3.5 liquid-glass-subtle rounded-xl">
                  <span className="text-slate-300 block text-[11px]">Suspect Vessels</span>
                  <strong className="text-sky-400 text-sm font-bold">3 ships flagged</strong>
                  <span className="text-slate-400 block text-[10px] mt-0.5">Ranked by track and speed</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4">
                <p className="text-xs text-slate-300">
                  Inspect the radar oil mask, drift probability contours, and ranked suspect ship trajectories for this spill.
                </p>
                <button
                  onClick={handleLaunchDemo}
                  className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-8 py-3.5 rounded-xl transition-all shadow-lg hover:shadow-blue-500/25 whitespace-nowrap"
                >
                  Open Investigation Workspace →
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: CUSTOM SATELLITE INGESTION */}
          {activeTab === 'custom' && (
            <form onSubmit={handleCustomSubmit} className="p-6 md:p-8 space-y-6 text-xs">
              {submitError && (
                <div className="p-3 bg-red-950/80 backdrop-blur-md text-red-200 rounded-xl font-medium">
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
                  className="w-full rounded-xl p-2.5 text-white bg-white/5 backdrop-blur-md focus:outline-none focus:ring-1 focus:ring-sky-400"
                  required
                />
              </div>

              {/* Quick Presets */}
              <div className="p-4 liquid-glass-subtle rounded-2xl space-y-2.5">
                <span className="font-bold text-slate-200 uppercase text-[11px] block">
                  Quick test images (Sentinel-1 GeoTIFF)
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_mumbai_slick.tif', 'Mumbai Offshore Oil Slick (Sentinel-1 SAR)')}
                    className="px-3 py-1.5 liquid-glass-interactive rounded-xl text-slate-200 font-medium"
                  >
                    Preset 1: Mumbai offshore mineral slick (18.925° N, 72.825° E)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_gujarat_calm.tif', 'Gujarat Coast Look-Alike (Sentinel-1 SAR)')}
                    className="px-3 py-1.5 liquid-glass-interactive rounded-xl text-slate-200 font-medium"
                  >
                    Preset 2: Gujarat coast calm-water false alarm (20.825° N, 70.425° E)
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
                className="bg-white/5 backdrop-blur-md p-6 text-center rounded-2xl transition-all hover:bg-white/[0.08]"
              >
                {isInspecting ? (
                  <div className="py-2 text-slate-200 font-semibold">
                    Reading image coordinates and metadata...
                  </div>
                ) : (
                  <div className="space-y-2">
                    <label className="inline-block liquid-glass-interactive text-white px-4 py-2 rounded-xl cursor-pointer font-medium">
                      Select Satellite Image
                      <input
                        type="file"
                        onChange={(e) => e.target.files?.[0] && handleFileSelection(e.target.files[0])}
                        className="hidden"
                        accept=".tif,.tiff,.png,.jpg,.jpeg,.nc"
                      />
                    </label>
                    <span className="text-slate-300 text-[11px] block">
                      or drag and drop a GeoTIFF or SAR image
                    </span>
                    {selectedFile && (
                      <div className="p-2 liquid-glass-subtle text-slate-200 font-semibold mt-2 inline-block rounded-xl">
                        Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Metadata Box */}
              {fileMetadata && (
                <div className="p-3.5 rounded-2xl text-[11px] liquid-glass-subtle text-slate-200">
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
                    className="w-full rounded-xl p-2 text-white bg-white/5 backdrop-blur-md focus:outline-none focus:ring-1 focus:ring-sky-400"
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
                    className="w-full rounded-xl p-2 text-white bg-white/5 backdrop-blur-md focus:outline-none focus:ring-1 focus:ring-sky-400"
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
                    className="w-full rounded-xl p-2 text-white bg-white/5 backdrop-blur-md focus:outline-none focus:ring-1 focus:ring-sky-400"
                  />
                </div>
                <div>
                  <label className="block text-slate-200 font-semibold mb-1">Current Speed (m/s)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={currentSpeed}
                    onChange={(e) => setCurrentSpeed(e.target.value)}
                    className="w-full rounded-xl p-2 text-white bg-white/5 backdrop-blur-md focus:outline-none focus:ring-1 focus:ring-sky-400"
                  />
                </div>
              </div>

              {/* Submit */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4">
                <span className="text-slate-300 text-[11px]">
                  {selectedFile ? `Ready to process ${selectedFile.name}` : 'Using default Sentinel-1 observation if no file uploaded.'}
                </span>
                <button
                  type="submit"
                  disabled={isSubmitting || isInspecting}
                  className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-xs px-8 py-3.5 rounded-xl transition-all shadow-lg hover:shadow-blue-500/25"
                >
                  {isSubmitting ? 'Analyzing radar image and calculating drift...' : 'Start Investigation →'}
                </button>
              </div>
            </form>
          )}
        </section>

{/* The Crisis & The Solution Spotlight */}
        <section className="liquid-glass rounded-3xl overflow-hidden shadow-2xl w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 items-stretch">
            
            {/* Left Content Column */}
            <div className="lg:col-span-6 p-6 sm:p-8 md:p-10 lg:p-12 flex flex-col justify-center space-y-6 sm:space-y-8">
              
              {/* Problem */}
              <div className="space-y-3">
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
