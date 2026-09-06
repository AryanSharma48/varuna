import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowRight, 
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileCode,
  Crosshair
} from 'lucide-react';
import { inspectRaster, uploadSAR } from '../services/api';

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
        message: 'Non-georeferenced image. Target coordinates can be manually specified below.'
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
      if (!res.ok) throw new Error('Failed to fetch sample GeoTIFF');
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
        // Automatically fetch default Mumbai sample if user clicks without selecting
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
      setSubmitError(err.message || 'Failed to initialize custom pipeline');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-white text-zinc-900 flex flex-col font-sans selection:bg-blue-600 selection:text-white overflow-y-auto">
      {/* Top Bar */}
      <header className="h-14 border-b border-zinc-200 px-8 flex items-center justify-between bg-white shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 bg-blue-600 flex items-center justify-center font-mono text-[11px] font-bold text-white">
            Δ
          </div>
          <span className="font-mono text-xs tracking-wider uppercase font-bold text-zinc-900">
            VARUNA / MARITIME ATTRIBUTION PLATFORM
          </span>
          <span className="text-zinc-300 text-xs">|</span>
          <span className="text-[11px] font-mono text-zinc-500">
            INTELLIGENCE SYSTEM
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-zinc-600">
          <span className="flex items-center gap-1.5 font-bold">
            <span className="w-2 h-2 bg-blue-600" />
            SYSTEM OPERATIONAL
          </span>
          <a 
            href="/docs" 
            target="_blank" 
            rel="noreferrer" 
            className="hover:text-black transition-colors border border-zinc-300 px-2.5 py-1 bg-zinc-50"
          >
            DOCS (FASTAPI)
          </a>
        </div>
      </header>

      {/* Main Container - Full scrollable wrapper */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 md:p-10 flex flex-col justify-start">
        {/* Hero Section */}
        <div className="mb-8">
          <div className="inline-block border border-blue-600 bg-blue-50 px-2.5 py-0.5 text-[11px] font-mono text-blue-700 mb-3 tracking-wider uppercase font-bold">
            SENTINEL-1 SAR × AIS EVIDENCE FUSION
          </div>
          <h1 className="text-3xl md:text-5xl font-black tracking-tight text-zinc-950 uppercase max-w-3xl leading-tight">
            Oil Spill Attribution & Origin Reconstruction
          </h1>
          <p className="mt-3 text-sm text-zinc-600 max-w-2xl leading-relaxed font-sans">
            Deterministic maritime evidence correlation platform. Connects satellite dual-pol SAR detection, 
            Lagrangian hydrodynamic backtracking, and indexed AIS vessel kinematic trajectories into an explainable audit dossier.
          </p>
        </div>

        {/* Two Clear Entry Points: Tabbed Switcher */}
        <div className="border border-zinc-300 bg-zinc-50 p-6 md:p-8">
          <div className="flex border-b border-zinc-200 mb-6">
            <button
              onClick={() => setActiveTab('demo')}
              className={`pb-3 px-6 text-xs font-mono tracking-wider uppercase font-bold border-b-2 transition-all ${
                activeTab === 'demo'
                  ? 'border-blue-600 text-blue-700 bg-white'
                  : 'border-transparent text-zinc-500 hover:text-zinc-800'
              }`}
            >
              Option 1: Open Demonstration Incident
            </button>
            <button
              onClick={() => setActiveTab('custom')}
              className={`pb-3 px-6 text-xs font-mono tracking-wider uppercase font-bold border-b-2 transition-all ${
                activeTab === 'custom'
                  ? 'border-blue-600 text-blue-700 bg-white'
                  : 'border-transparent text-zinc-500 hover:text-zinc-800'
              }`}
            >
              Option 2: Create Custom Investigation (Upload Satellite SAR)
            </button>
          </div>

          {/* Tab 1: Demonstration Incident */}
          {activeTab === 'demo' && (
            <div className="space-y-6">
              <div className="border border-zinc-300 bg-white p-5 font-mono text-xs">
                <div className="flex items-center justify-between pb-3 border-b border-zinc-200 mb-4">
                  <span className="font-bold text-zinc-950 text-sm">INCIDENT ID: VARUNA-2026-001</span>
                  <span className="bg-blue-600 text-white px-2 py-0.5 text-[10px] font-bold uppercase">
                    REPRODUCIBLE BENCHMARK DATASET
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-zinc-700 mb-4">
                  <div>
                    <span className="block text-zinc-400 text-[10px]">SCENE SENSOR</span>
                    <strong className="text-zinc-950">Sentinel-1B SAR C-Band</strong>
                  </div>
                  <div>
                    <span className="block text-zinc-400 text-[10px]">CENTROID COORDINATES</span>
                    <strong className="text-zinc-950">31.9827° N, 32.8490° E</strong>
                  </div>
                  <div>
                    <span className="block text-zinc-400 text-[10px]">DETECTION TYPE</span>
                    <strong className="text-blue-700 font-bold text-[10px]">Published Reference Oil-Slick Annotation</strong>
                  </div>
                  <div>
                    <span className="block text-zinc-400 text-[10px]">AIS CORRELATION</span>
                    <strong className="text-zinc-500">Unavailable for historical demo</strong>
                  </div>
                </div>

                <p className="text-zinc-600 text-xs font-sans leading-relaxed border-t border-zinc-200 pt-3">
                  Pre-configured controlled investigation package using real Sentinel-1 GRDH measurement data and the DARTIS 2019 dataset (ow-0388).
                  Demonstrates the full pipeline using deterministic geolocation with explicit limits where AIS/drift data are unavailable. 
                  Investigation Priority ≠ Proof of Responsibility.
                </p>
              </div>

              <div className="flex items-center justify-between pt-2">
                <div className="text-xs text-zinc-600 font-mono">
                  Press launch to begin the continuous investigation workflow.
                </div>
                <button
                  onClick={handleLaunchDemo}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-mono text-xs font-bold px-8 py-3.5 flex items-center gap-2 transition-colors"
                >
                  <span>LAUNCH INVESTIGATION WORKSPACE</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Tab 2: Custom SAR Observation Creation */}
          {activeTab === 'custom' && (
            <form onSubmit={handleCustomSubmit} className="space-y-5 text-xs font-mono">
              {submitError && (
                <div className="border border-red-500 bg-red-50 p-3 text-red-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{submitError}</span>
                </div>
              )}

              <div>
                <label className="block text-zinc-700 mb-1 uppercase text-[10px] font-bold">Investigation Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-white border border-zinc-300 p-2.5 text-zinc-950 font-sans focus:outline-none focus:border-blue-600"
                  required
                />
              </div>

              {/* Sample GeoTIFF Quick Loaders */}
              <div className="border border-zinc-200 bg-white p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase font-bold text-zinc-500 flex items-center gap-1.5">
                    <FileCode className="w-3.5 h-3.5 text-blue-600" />
                    TESTING PRESETS (CLICK TO LOAD REAL GEOREFERENCED GEOTIFF WITH WGS-84 TAGS)
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_mumbai_slick.tif', 'Mumbai Offshore Oil Slick — Sentinel-1 SAR')}
                    className="border border-zinc-300 hover:border-blue-600 hover:text-blue-700 bg-zinc-50 px-3 py-1.5 text-[11px] transition-colors flex items-center gap-1.5"
                  >
                    <span>Sample 1: Mumbai Offshore (18.925° N, 72.825° E)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleLoadSample('/sample_sar_gujarat_calm.tif', 'Gujarat Coast Look-Alike — Sentinel-1 SAR')}
                    className="border border-zinc-300 hover:border-blue-600 hover:text-blue-700 bg-zinc-50 px-3 py-1.5 text-[11px] transition-colors flex items-center gap-1.5"
                  >
                    <span>Sample 2: Gujarat Coast (20.825° N, 70.425° E)</span>
                  </button>
                </div>
              </div>

              {/* Upload Drop Area */}
              <div 
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files?.[0]) {
                    handleFileSelection(e.dataTransfer.files[0]);
                  }
                }}
                className="border border-dashed border-zinc-400 bg-white p-6 text-center hover:border-blue-600 transition-colors"
              >
                {isInspecting ? (
                  <div className="flex flex-col items-center justify-center py-2">
                    <Loader2 className="w-6 h-6 text-blue-600 animate-spin mb-2" />
                    <span className="text-zinc-700 font-bold">INSPECTING RASTER METADATA & PARSING EPSG TAGS...</span>
                  </div>
                ) : (
                  <>
                    <Upload className="w-6 h-6 text-blue-600 mx-auto mb-2" />
                    <label className="cursor-pointer text-zinc-900 font-bold block mb-1">
                      <span className="border-b border-blue-600 pb-0.5">DRAG & DROP OR SELECT SAR RASTER (GEOTIFF / DUAL-POL PNG)</span>
                      <input
                        type="file"
                        onChange={(e) => e.target.files?.[0] && handleFileSelection(e.target.files[0])}
                        className="hidden"
                        accept=".tif,.tiff,.png,.jpg,.jpeg,.nc"
                      />
                    </label>
                    <span className="text-[11px] text-zinc-500 block">
                      {selectedFile ? `Active File: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)` : 'Supports GeoTIFF (WGS84 / UTM), EXIF GPS JPEGs, and standard dual-pol imagery'}
                    </span>
                  </>
                )}
              </div>

              {/* Real Extracted Geospatial Metadata Box */}
              {fileMetadata && (
                <div className={`border p-4 ${fileMetadata.has_georeference ? 'border-blue-600 bg-blue-50/50' : 'border-zinc-300 bg-zinc-100'}`}>
                  <div className="flex items-center gap-2 mb-2 font-bold text-[11px]">
                    {fileMetadata.has_georeference ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-blue-600" />
                        <span className="text-blue-900 uppercase">COORDINATES EXTRACTED DIRECTLY FROM SATELLITE IMAGE TAGS</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-4 h-4 text-zinc-600" />
                        <span className="text-zinc-800 uppercase">STANDARD RASTER (NON-GEOREFERENCED)</span>
                      </>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] text-zinc-700">
                    <div>
                      <span className="block text-zinc-400 text-[10px]">METADATA SOURCE</span>
                      <strong>{fileMetadata.source}</strong>
                    </div>
                    <div>
                      <span className="block text-zinc-400 text-[10px]">PROJECTION CRS</span>
                      <strong>{fileMetadata.crs || 'Not Embedded'}</strong>
                    </div>
                    <div>
                      <span className="block text-zinc-400 text-[10px]">EXTRACTED CENTROID</span>
                      <strong className="text-blue-700">{lat}° N, {lon}° E</strong>
                    </div>
                    <div>
                      <span className="block text-zinc-400 text-[10px]">DIMENSIONS / BANDS</span>
                      <strong>{fileMetadata.width || 256} × {fileMetadata.height || 256} ({fileMetadata.band_count || 2} ch)</strong>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t border-zinc-200 text-[10px] text-zinc-600 font-sans">
                    {fileMetadata.message}
                  </div>
                </div>
              )}

              {/* Coordinates & Forcing Inputs */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] uppercase font-bold text-zinc-600 flex items-center gap-1">
                    <Crosshair className="w-3 h-3 text-blue-600" />
                    INVESTIGATION COORDINATES & OCEANOGRAPHIC FORCING (AUTO-FILLED OR EDITABLE)
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-zinc-700 mb-1 uppercase text-[10px] font-bold">Center Latitude (°N)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                      className="w-full bg-white border border-zinc-300 p-2 text-zinc-950 focus:border-blue-600 focus:outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-zinc-700 mb-1 uppercase text-[10px] font-bold">Center Longitude (°E)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={lon}
                      onChange={(e) => setLon(e.target.value)}
                      className="w-full bg-white border border-zinc-300 p-2 text-zinc-950 focus:border-blue-600 focus:outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-zinc-700 mb-1 uppercase text-[10px] font-bold">Wind Speed (m/s)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={windSpeed}
                      onChange={(e) => setWindSpeed(e.target.value)}
                      className="w-full bg-white border border-zinc-300 p-2 text-zinc-950 focus:border-blue-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-zinc-700 mb-1 uppercase text-[10px] font-bold">Current (m/s)</label>
                    <input
                      type="number"
                      step="0.05"
                      value={currentSpeed}
                      onChange={(e) => setCurrentSpeed(e.target.value)}
                      className="w-full bg-white border border-zinc-300 p-2 text-zinc-950 focus:border-blue-600 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-zinc-500">
                  {selectedFile ? `Ready to execute U-Net segmentation on ${selectedFile.name}` : 'Using default Sentinel-1 SAR observation if no custom raster is chosen'}
                </span>
                <button
                  type="submit"
                  disabled={isSubmitting || isInspecting}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-mono text-xs font-bold px-8 py-3.5 flex items-center gap-2 transition-colors"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>RUNNING ML INFERENCE & DRIFT BACKTRACK...</span>
                    </>
                  ) : (
                    <>
                      <span>INITIALIZE CUSTOM PIPELINE</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* 4-Pillar Pipeline Reference */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8 border-t border-zinc-200 pt-6">
          <div className="border border-zinc-200 bg-white p-4">
            <span className="font-mono text-[10px] text-blue-600 block mb-1 font-bold">01 / DETECTION</span>
            <strong className="text-zinc-950 text-xs block mb-1">U-Net & Look-Alike Gate</strong>
            <p className="text-zinc-600 text-[11px] leading-relaxed font-sans">
              Distinguishes mineral slicks from biogenic films via 6–18 dB backscatter damping analysis.
            </p>
          </div>

          <div className="border border-zinc-200 bg-white p-4">
            <span className="font-mono text-[10px] text-blue-600 block mb-1 font-bold">02 / RECONSTRUCTION</span>
            <strong className="text-zinc-950 text-xs block mb-1">Lagrangian Particle Drift</strong>
            <p className="text-zinc-600 text-[11px] leading-relaxed font-sans">
              500-particle stochastic advective-diffusive reverse simulation yields origin confidence contours.
            </p>
          </div>

          <div className="border border-zinc-200 bg-white p-4">
            <span className="font-mono text-[10px] text-blue-600 block mb-1 font-bold">03 / AIS CORRELATION</span>
            <strong className="text-zinc-950 text-xs block mb-1">Spatio-Temporal "Who Was Here?"</strong>
            <p className="text-zinc-600 text-[11px] leading-relaxed font-sans">
              Indexed corridor queries with transponder outage and course/speed anomaly detection.
            </p>
          </div>

          <div className="border border-zinc-200 bg-white p-4">
            <span className="font-mono text-[10px] text-blue-600 block mb-1 font-bold">04 / AUDIT DOSSIER</span>
            <strong className="text-zinc-950 text-xs block mb-1">Explainable Attribution</strong>
            <p className="text-zinc-600 text-[11px] leading-relaxed font-sans">
              Decomposed scoring rankings with legal disclaimer and zero-hallucination assistant tools.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-10 border-t border-zinc-200 px-8 flex items-center justify-between text-[11px] font-mono text-zinc-500 bg-white shrink-0">
        <div>VARUNA</div>
        <div>STRICT EVIDENCE SYSTEM</div>
      </footer>
    </div>
  );
};
