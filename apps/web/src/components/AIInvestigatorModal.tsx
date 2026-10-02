import React, { useState, useRef, useEffect } from 'react';
import { 
  X, 
  Send, 
  Trash2, 
  Copy, 
  Check, 
  Database
} from 'lucide-react';
import { askAssistant } from '../services/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: Array<{ source?: string; details?: string; count?: number; [key: string]: any }>;
  model_used?: string;
}

interface AIInvestigatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  incidentId: string;
}

export const AIInvestigatorModal: React.FC<AIInvestigatorModalProps> = ({
  isOpen,
  onClose,
  incidentId
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `### 🌊 Welcome to Varuna AI Investigator
I am your grounded maritime intelligence assistant powered by **Groq LLaMA / GPT-OSS**.

I have ingested all empirical findings across the **6 investigation phases**:
1. **Scene Metadata & Quality Gate** (Sentinel-1 SAR C-Band)
2. **U-Net Spill Segmentation** (53.15 km², 96% oil confidence, look-alike ruled out)
3. **Lagrangian Backward Drift** (Probable centroid 31.9238°N, 32.8658°E | Window: 12:48–14:48 UTC)
4. **AIS Corridor Query** (3 vessels detected; 22-min dark ship blackout & speed jumps flagged)
5. **Multi-Factor Attribution Engine** (Rank #1: MT AL NAJAF at 89.9/100 vs other candidates)
6. **Forward Drift Forecast** (Impacts on Egypt EEZ & Port Said trawling grounds)

Ask me anything about suspect rankings, trajectory alignments, AIS gaps, or hydrodynamic dispersion.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      model_used: 'openai/gpt-oss-120b'
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  if (!isOpen) return null;

  const handleSend = async (queryToSend?: string) => {
    const text = (queryToSend ?? inputQuery).trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const historyPayload = messages
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role, content: m.content }));

      const res = await askAssistant(incidentId, text, historyPayload);

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: res.citations,
        model_used: res.model_used || 'openai/gpt-oss-120b'
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error('AI Investigator query error:', err);
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ **Unable to complete investigation inference**: ${err.message || 'Network error'}. Please try again.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome-cleared',
        role: 'assistant',
        content: 'Conversation history cleared. Ready for your next investigation query.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        model_used: 'openai/gpt-oss-120b'
      }
    ]);
  };

  // Custom lightweight Markdown-like formatter for structured presentation
  const renderFormattedContent = (content: string) => {
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let tableBuffer: string[] = [];

    const flushTable = (keyPrefix: number) => {
      if (tableBuffer.length >= 2) {
        const headerRow = tableBuffer[0]
          .split('|')
          .map(c => c.trim())
          .filter(Boolean);
        const dataRows = tableBuffer.slice(2).map(r =>
          r.split('|').map(c => c.trim()).filter(Boolean)
        );

        elements.push(
          <div key={`table-${keyPrefix}`} className="my-3 overflow-x-auto rounded-xl border border-white/10 bg-white/[0.02]">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.05] text-cyan-300 font-semibold">
                  {headerRow.map((h, i) => (
                    <th key={i} className="py-2.5 px-3.5">{formatInline(h)}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-200">
                {dataRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-white/[0.02] transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="py-2 px-3.5">{formatInline(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      tableBuffer = [];
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Table line
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        tableBuffer.push(trimmed);
        return;
      } else if (tableBuffer.length > 0) {
        flushTable(idx);
      }

      if (trimmed.startsWith('### ')) {
        elements.push(
          <h4 key={idx} className="text-xs font-bold uppercase tracking-wider text-cyan-400 mt-3 mb-1">
            {formatInline(trimmed.replace('### ', ''))}
          </h4>
        );
      } else if (trimmed.startsWith('## ')) {
        elements.push(
          <h3 key={idx} className="text-sm font-bold text-white mt-4 mb-2 flex items-center gap-1.5 border-b border-white/10 pb-1">
            {formatInline(trimmed.replace('## ', ''))}
          </h3>
        );
      } else if (trimmed.startsWith('# ')) {
        elements.push(
          <h2 key={idx} className="text-base font-extrabold text-white mt-3 mb-2">
            {formatInline(trimmed.replace('# ', ''))}
          </h2>
        );
      } else if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
        elements.push(
          <div key={idx} className="flex items-start gap-2 text-xs text-slate-200 my-1 leading-relaxed">
            <span className="text-cyan-400 mt-1 shrink-0">•</span>
            <span>{formatInline(trimmed.replace(/^[-•]\s*/, ''))}</span>
          </div>
        );
      } else if (trimmed.startsWith('> ')) {
        elements.push(
          <div key={idx} className="my-2 p-2.5 rounded-xl bg-cyan-950/30 border-l-2 border-cyan-400 text-[11px] text-cyan-200/90 italic">
            {formatInline(trimmed.replace('> ', ''))}
          </div>
        );
      } else if (trimmed === '---') {
        elements.push(<hr key={idx} className="border-white/10 my-3" />);
      } else if (trimmed.length > 0) {
        elements.push(
          <p key={idx} className="text-xs text-slate-200 my-1 leading-relaxed">
            {formatInline(trimmed)}
          </p>
        );
      } else {
        elements.push(<div key={idx} className="h-1" />);
      }
    });

    if (tableBuffer.length > 0) {
      flushTable(lines.length);
    }

    return elements;
  };

  const formatInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded bg-white/10 text-cyan-300 font-mono text-[10px]">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-4xl h-[90vh] bg-[#070e1e] border border-cyan-500/25 rounded-3xl shadow-[0_0_60px_rgba(6,182,212,0.12)] flex flex-col overflow-hidden text-slate-100 font-sans"
        onClick={e => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-heading">
                Varuna AI Investigator
              </h3>
              <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[10px] text-emerald-400 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Grounded Engine
              </span>
            </div>
            <p className="text-[11px] text-slate-400 flex items-center gap-1.5 mt-0.5">
              <span>Multi-Stage Fused Intelligence</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-400 font-mono text-[10px]">Groq (openai/gpt-oss-120b)</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleClearHistory}
              title="Clear Conversation"
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              title="Close Assistant"
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Chat Message Scroll Area */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div 
                key={msg.id} 
                className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`rounded-2xl p-4 shadow-md text-xs leading-relaxed ${
                    isUser 
                      ? 'max-w-[80%] bg-blue-600/30 text-white border border-blue-500/40 rounded-tr-sm' 
                      : 'w-full bg-white/[0.03] border border-white/10 text-slate-200 rounded-tl-sm backdrop-blur-md'
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 mb-2 pb-1 border-b border-white/10 text-[10px]">
                    <span className="font-semibold text-slate-300">
                      {isUser ? 'Investigator' : 'Varuna AI Intelligence'}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">{msg.timestamp}</span>
                      <button
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="text-slate-400 hover:text-white transition-colors"
                        title="Copy message"
                      >
                        {copiedId === msg.id ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1">
                    {renderFormattedContent(msg.content)}
                  </div>

                  {!isUser && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-white/10 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold flex items-center gap-1">
                        <Database className="w-2.5 h-2.5 text-cyan-400" /> Evidence Citations:
                      </span>
                      {msg.citations.map((c, cIdx) => (
                        <span 
                          key={cIdx}
                          className="px-2 py-0.5 rounded-md bg-white/[0.06] border border-white/10 text-[10px] text-cyan-300 font-mono"
                        >
                          {c.source || 'empirical_telemetry'}
                          {c.target ? `: ${c.target}` : ''}
                        </span>
                      ))}
                    </div>
                  )}

                  {!isUser && msg.model_used && (
                    <div className="mt-2 text-[9px] text-slate-400 font-mono text-right">
                      Inference Engine: {msg.model_used}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-white/[0.03] border border-white/10 text-xs text-slate-300">
              <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent animate-spin rounded-full" />
              <span className="text-cyan-300 font-medium">
                Analyzing 6-stage telemetry & running Groq neural inference...
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-white/[0.02] border-t border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <input
                ref={inputRef}
                type="text"
                value={inputQuery}
                onChange={e => setInputQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask the AI Investigator (e.g. Which ship was ranked #1 and why not the other?)..."
                disabled={loading}
                className="w-full bg-[#0a1226] border border-white/15 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 rounded-2xl py-3 px-4 text-xs text-white placeholder-slate-400 transition-all shadow-inner"
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={loading || !inputQuery.trim()}
              className="p-3 rounded-2xl bg-white/[0.08] hover:bg-white/[0.16] border border-white/15 text-slate-200 hover:text-white font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
              title="Send Query"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between mt-2 px-1 text-[10px] text-slate-400">
            <span>Press <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-slate-300 font-mono">Enter</kbd> to query</span>
            <span className="text-slate-400">Grounded in SAR, AIS, Lagrangian drift & attribution metrics</span>
          </div>
        </div>
      </div>
    </div>
  );
};
