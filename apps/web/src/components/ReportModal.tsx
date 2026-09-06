import React, { useState, useEffect } from 'react';
import { generateReport } from '../services/api';
import { X, Copy, Check, Printer } from 'lucide-react';

interface ReportModalProps {
  incidentId: string;
  onClose: () => void;
}

export const ReportModal: React.FC<ReportModalProps> = ({ incidentId, onClose }) => {
  const [report, setReport] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    generateReport(incidentId)
      .then((res) => {
        setReport(res.content_markdown);
        setLoading(false);
      })
      .catch((err) => {
        setReport(`Failed to generate report: ${err.message}`);
        setLoading(false);
      });
  }, [incidentId]);

  const handleCopy = () => {
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl h-[700px] bg-white border border-zinc-300 flex flex-col font-mono text-xs shadow-2xl text-zinc-900">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50">
          <div>
            <span className="text-[10px] text-zinc-500 uppercase block font-bold">AUDIT DOSSIER</span>
            <h3 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
              Official Incident Investigation Report
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 border border-zinc-300 bg-white hover:bg-zinc-100 text-zinc-700 flex items-center gap-1.5"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-blue-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'COPIED' : 'COPY MARKDOWN'}</span>
            </button>

            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold flex items-center gap-1.5"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>PRINT / PDF</span>
            </button>

            <button
              onClick={onClose}
              className="w-7 h-7 border border-zinc-300 hover:border-zinc-400 bg-white flex items-center justify-center text-zinc-600 hover:text-black ml-2"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto bg-white text-zinc-800 whitespace-pre-wrap leading-relaxed selection:bg-blue-600 selection:text-white">
          {loading ? (
            <div className="text-zinc-500 italic">
              Compiling multi-sensor evidence dossier...
            </div>
          ) : (
            report
          )}
        </div>
      </div>
    </div>
  );
};
