import React, { useState } from 'react';
import { 
  X, 
  Download, 
  Printer, 
  Copy, 
  Check, 
  FileText, 
  ExternalLink,
  ShieldCheck
} from 'lucide-react';
import { InvestigationReportResponse } from '../types';
import { getReportPdfUrl } from '../services/api';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportData: InvestigationReportResponse | null;
  loading: boolean;
  incidentId: string;
}

export const ReportModal: React.FC<ReportModalProps> = ({
  isOpen,
  onClose,
  reportData,
  loading,
  incidentId
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const copyHash = () => {
    if (reportData?.sha256_fingerprint) {
      navigator.clipboard.writeText(reportData.sha256_fingerprint);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadPdf = () => {
    if (!reportData) return;
    const url = getReportPdfUrl(reportData.report_id);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Official_Investigation_Report_${reportData.report_id}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleOpenPrintableView = () => {
    if (!reportData) return;
    const url = `/investigation/${incidentId}/report?report_id=${encodeURIComponent(reportData.report_id)}`;
    const newWindow = window.open(url, '_blank');
    if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
      // If browser blocked popup window, navigate directly in current window
      window.location.href = url;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-lg bg-[#0b1329] border border-white/10 rounded-3xl shadow-2xl overflow-hidden text-slate-200 font-sans"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-heading">
                Final Investigation Report
              </h3>
              <p className="text-[10px] text-slate-400">
                Incident {incidentId}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body - Focused with Two Buttons in the Middle */}
        <div className="p-8 flex flex-col items-center justify-center text-center">
          {loading ? (
            <div className="py-10 flex flex-col items-center justify-center gap-4">
              <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent animate-spin rounded-full" />
              <div className="text-center">
                <p className="text-xs font-semibold text-white uppercase tracking-wider">
                  Compiling Final Investigation Report...
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Synthesizing Sentinel-1 SAR morphology, drift backtrack, and AIS kinematic attribution
                </p>
              </div>
            </div>
          ) : reportData ? (
            <div className="w-full space-y-6">
              {/* Status & Icon */}
              <div className="flex flex-col items-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600/20 to-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-3 shadow-lg shadow-emerald-500/10">
                  <ShieldCheck className="w-8 h-8 text-emerald-400" />
                </div>
                <h2 className="text-lg font-bold text-white font-heading tracking-tight">
                  Investigation Report Ready
                </h2>
                <p className="text-xs text-slate-300 mt-1 max-w-sm mx-auto">
                  Multi-sensor satellite SAR, hydrodynamic reverse drift, and AIS vessel attribution dossier successfully generated.
                </p>
              </div>

              {/* The Two Main Action Buttons in the Middle */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <button
                  onClick={handleDownloadPdf}
                  className="w-full sm:w-auto flex-1 flex items-center justify-center gap-2 px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5 transition-all cursor-pointer"
                >
                  <Download className="w-4 h-4" />
                  <span>Download PDF</span>
                </button>

                <button
                  onClick={handleOpenPrintableView}
                  className="w-full sm:w-auto flex-1 flex items-center justify-center gap-2 px-6 py-3.5 bg-white/[0.08] hover:bg-white/[0.15] text-slate-100 hover:text-white border border-white/15 hover:border-white/30 rounded-xl text-xs font-bold shadow-lg hover:-translate-y-0.5 transition-all cursor-pointer"
                >
                  <Printer className="w-4 h-4 text-sky-400" />
                  <span>Print View</span>
                  <ExternalLink className="w-3 h-3 opacity-60 ml-0.5" />
                </button>
              </div>

              {/* Tamper-Evident SHA-256 Fingerprint */}
              <div className="p-3 rounded-xl bg-black/40 border border-white/10 text-left">
                <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                  <span className="font-mono">ID: {reportData.report_id}</span>
                  <button
                    onClick={copyHash}
                    className="flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-300 font-semibold transition-colors cursor-pointer"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copied ? 'Copied' : 'Copy Hash'}</span>
                  </button>
                </div>
                <code className="text-[10px] text-sky-300 font-mono break-all block bg-white/[0.02] p-1.5 rounded select-all">
                  {reportData.sha256_fingerprint}
                </code>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-slate-400 text-xs">
              No report generated yet.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-white/10 bg-white/[0.02] flex items-center justify-between text-xs">
          <span className="text-[10px] text-slate-500 font-mono">
            Varuna Maritime Intelligence Platform • Confidential
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white/10 hover:bg-white/15 text-slate-200 hover:text-white rounded-xl text-xs font-medium transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
