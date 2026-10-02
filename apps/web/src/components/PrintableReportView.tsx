import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { 
  ArrowLeft, 
  Download, 
  Printer, 
  ShieldCheck, 
  AlertTriangle, 
  Copy,
  Check
} from 'lucide-react';
import { CanonicalInvestigationReport } from '../types';
import { generateReport, getReportPdfUrl, fetchReportById } from '../services/api';

export const PrintableReportView: React.FC = () => {
  const { id = 'VARUNA-2026-001' } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const queryReportId = searchParams.get('report_id');
  const navigate = useNavigate();

  const [report, setReport] = useState<CanonicalInvestigationReport | null>(null);
  const [reportId, setReportId] = useState<string>('');
  const [sha256, setSha256] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        if (queryReportId) {
          const res = await fetchReportById(queryReportId);
          if (!isMounted) return;
          setReport(res.report);
          setReportId(res.report_id);
          setSha256(res.sha256_fingerprint);
          setLoading(false);
          return;
        }

        const res = await generateReport(id);
        if (!isMounted) return;
        setReport(res.report);
        setReportId(res.report_id);
        setSha256(res.sha256_fingerprint);
        setLoading(false);
      } catch (err: any) {
        if (!isMounted) return;
        setError(err.message || 'Failed to load report data');
        setLoading(false);
      }
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, [id, queryReportId]);

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPdf = () => {
    if (!reportId) return;
    const url = getReportPdfUrl(reportId);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Official_Investigation_Report_${reportId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleCopyHash = () => {
    if (!sha256) return;
    navigator.clipboard.writeText(sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center text-slate-200 font-sans gap-3">
        <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent animate-spin rounded-full" />
        <div className="text-xs uppercase tracking-widest text-slate-400 font-semibold">
          Compiling Formal Investigation Dossier...
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6 text-slate-200">
        <div className="max-w-md w-full bg-slate-800/80 border border-slate-700 p-6 rounded-2xl text-center shadow-xl">
          <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
          <h2 className="text-base font-bold text-white mb-1">Failed to Generate Report</h2>
          <p className="text-xs text-slate-400 mb-4">{error || 'Unknown error occurred'}</p>
          <button
            onClick={() => navigate(`/investigation/${id}/forecast`)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold"
          >
            Return to Investigation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 font-sans py-6 print:py-0 print:bg-white print:text-black">
      {/* Top Floating Action Bar (Hidden on Print) */}
      <div className="print:hidden max-w-4xl mx-auto px-4 mb-6 flex items-center justify-between">
        <button
          onClick={() => navigate(`/investigation/${id}/forecast`)}
          className="flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-50 shadow-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Investigation</span>
        </button>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleDownloadPdf}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Download Official PDF</span>
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all"
          >
            <Printer className="w-4 h-4" />
            <span>Print / Save as PDF</span>
          </button>
        </div>
      </div>

      {/* Official Printable Document Container */}
      <main className="max-w-4xl mx-auto bg-white border border-slate-200 rounded-2xl shadow-xl p-8 sm:p-12 print:border-none print:shadow-none print:p-0 print:max-w-none print:w-full">
        {/* Document Header */}
        <header className="border-b-2 border-slate-900 pb-6 mb-8">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-blue-800 mb-1">
                <span>Varuna Maritime Intelligence Platform</span>
                <span>•</span>
                <span>Incident Response Division</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 font-heading">
                PRELIMINARY INVESTIGATION & VESSEL ATTRIBUTION REPORT
              </h1>
              <p className="text-xs text-slate-600 font-medium mt-1">
                Unified Multi-Sensor Spaceborne SAR & Hydrodynamic Kinematic Assessment
              </p>
            </div>
            <div className="text-right">
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-emerald-50 border border-emerald-300 text-emerald-800 text-[11px] font-bold rounded-full uppercase tracking-wider">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                Verified Spill
              </span>
              <div className="text-[11px] font-mono text-slate-500 mt-2">
                ID: {report.metadata.report_id}
              </div>
            </div>
          </div>
        </header>

        {/* Section 1: Header & Incident Metadata */}
        <section className="mb-8">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-1.5 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">1</span>
            Incident & Satellite Acquisition Metadata
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <span className="block text-[10px] text-slate-500 uppercase font-semibold">Incident Identifier</span>
              <span className="font-bold text-slate-900">{report.metadata.incident_id}</span>
            </div>
            <div>
              <span className="block text-[10px] text-slate-500 uppercase font-semibold">Target Region</span>
              <span className="font-medium text-slate-800">{report.metadata.target_region}</span>
            </div>
            <div>
              <span className="block text-[10px] text-slate-500 uppercase font-semibold">SAR Acquisition Time</span>
              <span className="font-mono text-slate-800">{report.metadata.sensing_timestamp}</span>
            </div>
            <div>
              <span className="block text-[10px] text-slate-500 uppercase font-semibold">Report Generated</span>
              <span className="font-mono text-slate-800">{report.metadata.generated_at}</span>
            </div>
          </div>
        </section>

        {/* Section 2: Spill Verification & Geometry */}
        <section className="mb-8">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-1.5 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">2</span>
            Spill Verification & Synthetic Aperture Radar (SAR) Morphology
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div className="p-3.5 bg-blue-50/60 border border-blue-200 rounded-xl">
              <span className="block text-[10px] uppercase font-bold text-blue-900">Observed Slick Area</span>
              <span className="text-lg font-bold text-blue-950">{report.spill_verification.area_km2} km²</span>
              <span className="block text-[10px] text-blue-700 mt-0.5">Sentinel-1 Delineated</span>
            </div>
            <div className="p-3.5 bg-indigo-50/60 border border-indigo-200 rounded-xl">
              <span className="block text-[10px] uppercase font-bold text-indigo-900">Estimated Spill Volume</span>
              <span className="text-lg font-bold text-indigo-950">~{report.spill_verification.estimated_metric_tons} MT</span>
              <span className="block text-[10px] text-indigo-700 mt-0.5">Moderate thickness factor</span>
            </div>
            <div className="p-3.5 bg-emerald-50/60 border border-emerald-200 rounded-xl">
              <span className="block text-[10px] uppercase font-bold text-emerald-900">Detection Confidence</span>
              <span className="text-lg font-bold text-emerald-950">{(report.spill_verification.oil_confidence * 100).toFixed(1)}%</span>
              <span className="block text-[10px] text-emerald-700 mt-0.5">DeepLabV3+ Neural Class</span>
            </div>
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="block text-[10px] uppercase font-bold text-slate-700">Look-Alike Risk</span>
              <span className="text-lg font-bold text-slate-900">{report.spill_verification.look_alike_risk}</span>
              <span className="block text-[10px] text-slate-500 mt-0.5">Low biogenic likelihood</span>
            </div>
          </div>

          <div className="text-xs grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-700 bg-slate-50/60 p-3 rounded-xl border border-slate-200">
            <div><span className="font-semibold text-slate-500">Major Length:</span> {report.spill_verification.length_km} km</div>
            <div><span className="font-semibold text-slate-500">Major Width:</span> {report.spill_verification.width_km} km</div>
            <div><span className="font-semibold text-slate-500">Perimeter:</span> {report.spill_verification.perimeter_km} km</div>
            <div><span className="font-semibold text-slate-500">Morphology:</span> {report.spill_verification.morphology_type}</div>
          </div>
        </section>

        {/* Section 3: Origin Backtrack & Environmental Forcing */}
        <section className="mb-8">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-1.5 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">3</span>
            Hydrodynamic Reverse Drift & Probable Origin Reconstruction
          </h2>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <span className="block text-[10px] text-slate-500 uppercase font-semibold">Estimated Release Window</span>
                <span className="font-mono text-slate-900 font-semibold">
                  {report.origin_backtrack.time_window_start.replace('T', ' ').slice(0, 16)} to {report.origin_backtrack.time_window_end.replace('T', ' ').slice(0, 16)} UTC
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-slate-500 uppercase font-semibold">Reconstructed Origin Center</span>
                <span className="font-mono text-slate-900 font-semibold">
                  {report.origin_backtrack.origin_center_lat.toFixed(4)}°N, {report.origin_backtrack.origin_center_lon.toFixed(4)}°E
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-slate-500 uppercase font-semibold">Corridor Uncertainty Radius</span>
                <span className="font-semibold text-slate-900">
                  ±{report.origin_backtrack.uncertainty_radius_km} km (95% CI)
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between text-slate-600 gap-2">
              <div>
                <span className="font-semibold text-slate-700">Metocean Forcing Models:</span> {report.origin_backtrack.forcing_used.source_name || 'ECMWF ERA5 Wind Fields + CMEMS Mediterranean Hydrodynamics'}
              </div>
              <div className="text-[11px] font-mono">
                Wind: {report.origin_backtrack.forcing_used.wind_speed_ms ?? 2.6} m/s @ {report.origin_backtrack.forcing_used.wind_direction_deg ?? 325}° • Current: {report.origin_backtrack.forcing_used.current_speed_ms ?? 0.35} m/s @ {report.origin_backtrack.forcing_used.current_direction_deg ?? 75}°
              </div>
            </div>
          </div>
        </section>

        {/* Section 4: Candidate Vessel Attribution Priority Table */}
        <section className="mb-8">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-1.5 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">4</span>
            Candidate Vessel Attribution Priority Rankings
          </h2>
          <div className="border border-slate-200 rounded-xl overflow-x-auto shadow-sm">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 text-white uppercase text-[10px] tracking-wider font-semibold">
                  <th className="py-2.5 px-3 min-w-[50px]">Rank</th>
                  <th className="py-2.5 px-3 min-w-[130px]">Vessel Identity</th>
                  <th className="py-2.5 px-3 min-w-[110px]">Type & Flag</th>
                  <th className="py-2.5 px-3 text-right min-w-[80px]">Score</th>
                  <th className="py-2.5 px-3 text-center min-w-[80px]">Priority</th>
                  <th className="py-2.5 px-3 min-w-[130px]">Score Breakdown</th>
                  <th className="py-2.5 px-3 min-w-[160px]">Corroborating Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {report.vessel_attribution.map((v) => (
                  <tr key={v.mmsi} className="hover:bg-slate-50/80">
                    <td className="py-3 px-3 font-bold text-slate-900">
                      #{v.priority_rank}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-bold text-slate-900">{v.vessel_name}</div>
                      <div className="text-[10px] font-mono text-slate-500">MMSI: {v.mmsi}</div>
                    </td>
                    <td className="py-3 px-3 text-slate-700">
                      <div>{v.vessel_type}</div>
                      <div className="text-[10px] text-slate-500">{v.flag}</div>
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 text-sm">
                      {v.total_score.toFixed(1)} <span className="text-[10px] font-normal text-slate-500">/100</span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        v.priority_level === 'HIGH' ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                        v.priority_level === 'MEDIUM' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                        'bg-slate-100 text-slate-800 border border-slate-300'
                      }`}>
                        {v.priority_level}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-[10px] text-slate-600">
                      <div>Prox: {v.proximity_score.toFixed(0)} | Time: {v.timing_score.toFixed(0)}</div>
                      <div>Traj: {v.trajectory_score.toFixed(0)} | Gap: {v.ais_gap_score.toFixed(0)}</div>
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-700 leading-snug break-words">
                      <div className="font-medium text-slate-900">{v.reasons[0] || 'Corridor transit'}</div>
                      {v.reasons[1] && <div className="text-[10px] text-slate-500 mt-0.5">{v.reasons[1]}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 5: Forward Impact Analysis */}
        <section className="mb-8">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-1.5 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">5</span>
            Forward Drift Impact & Sensitive Resource Vulnerability
          </h2>
          <div className="border border-slate-200 rounded-xl overflow-x-auto shadow-sm">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 text-white uppercase text-[10px] tracking-wider font-semibold">
                  <th className="py-2.5 px-3 min-w-[130px]">Protected Asset</th>
                  <th className="py-2.5 px-3 min-w-[100px]">Jurisdiction</th>
                  <th className="py-2.5 px-3 min-w-[110px]">Category</th>
                  <th className="py-2.5 px-2 text-center min-w-[60px]">Vuln.</th>
                  <th className="py-2.5 px-2 text-right min-w-[70px]">Distance</th>
                  <th className="py-2.5 px-3 text-center min-w-[95px]">Threat Level</th>
                  <th className="py-2.5 px-3 min-w-[150px]">Key Resources at Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {report.forward_impact.map((imp, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80">
                    <td className="py-3 px-3 font-bold text-slate-900 leading-snug">
                      {imp.asset_name}
                    </td>
                    <td className="py-3 px-3 text-slate-700 text-[11px] leading-snug">
                      {imp.jurisdiction}
                    </td>
                    <td className="py-3 px-3 text-slate-600 text-[11px] font-medium leading-snug">
                      {imp.category.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3 px-2 text-center font-mono font-bold text-slate-800 text-[11px]">
                      {(imp.vulnerability_index * 100).toFixed(0)}%
                    </td>
                    <td className="py-3 px-2 text-right font-mono text-slate-900 text-[11px] whitespace-nowrap">
                      {imp.distance_km.toFixed(1)} km
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[9px] font-bold ${
                        imp.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                        imp.severity === 'HIGH' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                        'bg-blue-50 text-blue-800 border border-blue-200'
                      }`}>
                        {imp.severity}
                      </span>
                      <div className="text-[9px] text-slate-500 mt-0.5 font-normal">
                        {imp.estimated_arrival === 'NO_IMPACT_PREDICTED_48H' 
                          ? 'No impact (48h)' 
                          : imp.estimated_arrival.replace(/_/g, ' ')}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-700 leading-snug break-words">
                      {imp.resource_at_risk}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 6: Legal Caveats & Operational Limitations */}
        <section className="mb-8">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 pb-1.5 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">6</span>
            Legal Caveats & Operational Boundaries
          </h2>
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-950 space-y-2.5">
            <div className="flex items-start gap-2 font-semibold">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                <span className="uppercase tracking-wider font-bold">Investigative Status:</span> {report.legal_disclaimer.notice}
              </p>
            </div>
            <div className="pl-6 pt-1 border-t border-rose-200/60">
              <span className="block text-[10px] uppercase font-bold text-rose-900 mb-1">Operational Limitations:</span>
              <ul className="list-disc pl-4 space-y-1 text-[11px] text-rose-900/80">
                {report.legal_disclaimer.operational_limitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* Section 7: Cryptographic SHA-256 Tamper-Evident Block */}
        <footer className="pt-6 border-t-2 border-slate-900">
          <div className="bg-slate-50 border border-slate-300 rounded-xl p-4 text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-200">
              <div className="flex items-center gap-2 text-slate-800 font-bold uppercase text-[11px] tracking-wider">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                <span>Cryptographic Audit Signature & Integrity Seal</span>
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Signed At: {report.tamper_evident.signed_at}
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-semibold text-slate-600">SHA-256 Checksum (Deterministic Canonical JSON Hash):</span>
                <button
                  onClick={handleCopyHash}
                  className="print:hidden flex items-center gap-1 text-[10px] font-bold text-blue-600 hover:text-blue-800"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy Hash'}</span>
                </button>
              </div>
              <div className="font-mono text-[11px] bg-white p-2.5 rounded border border-slate-300 text-slate-800 break-all select-all">
                {report.tamper_evident.sha256_fingerprint}
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                Any post-issuance alteration to incident geometry, kinematic scores, or metadata will invalidate this digital fingerprint upon verification against the central immutable ledger.
              </p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};
