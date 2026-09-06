import React, { useState } from 'react';
import { askAssistant } from '../services/api';
import { X, Send, Terminal } from 'lucide-react';

interface InvestigationAssistantProps {
  incidentId: string;
  onClose: () => void;
}

interface Message {
  sender: 'user' | 'assistant';
  text: string;
  toolUsed?: string;
}

export const InvestigationAssistant: React.FC<InvestigationAssistantProps> = ({
  incidentId,
  onClose
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'assistant',
      text: "Grounded Investigation Assistant initialized. Responses strictly retrieved from PostGIS AIS queries, Lagrangian backtrack coordinates, and U-Net metrics without speculation.",
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const suggestedQuestions = [
    "Why is Pacific Voyager ranked #1?",
    "Who was near the origin zone?",
    "What was the estimated spill window & origin?",
    "Which sensitive areas could be affected in 12 hours?"
  ];

  const handleSend = async (queryText?: string) => {
    const q = queryText || input;
    if (!q.trim() || loading) return;

    setMessages((prev) => [...prev, { sender: 'user', text: q }]);
    setInput('');
    setLoading(true);

    try {
      const res = await askAssistant(incidentId, q);
      setMessages((prev) => [
        ...prev,
        { sender: 'assistant', text: res.answer, toolUsed: res.tool_used }
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { sender: 'assistant', text: `Query execution failed: ${err.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl h-[580px] bg-white border border-zinc-300 flex flex-col font-mono text-xs shadow-2xl text-zinc-900">
        {/* Header */}
        <div className="px-5 py-3 border-b border-zinc-200 flex items-center justify-between bg-zinc-50">
          <div>
            <span className="text-[10px] text-zinc-500 uppercase block font-bold">DETERMINISTIC RETRIEVAL</span>
            <h3 className="text-xs font-bold text-zinc-950 uppercase tracking-wider">
              Grounded Investigation Assistant
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 border border-zinc-300 hover:border-zinc-400 bg-white flex items-center justify-center text-zinc-600 hover:text-black"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Suggested Queries */}
        <div className="px-4 py-2 border-b border-zinc-200 bg-zinc-50 flex gap-2 overflow-x-auto text-[11px]">
          {suggestedQuestions.map((sq, i) => (
            <button
              key={i}
              onClick={() => handleSend(sq)}
              className="px-2.5 py-1 border border-zinc-300 bg-white hover:bg-zinc-100 text-zinc-700 whitespace-nowrap"
            >
              {sq}
            </button>
          ))}
        </div>

        {/* Messages */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-white">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`p-3 border leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-blue-50 border-blue-500 text-zinc-950 ml-8'
                  : 'bg-zinc-50 border-zinc-200 text-zinc-800 mr-8'
              }`}
            >
              <div className="text-[10px] text-zinc-500 uppercase mb-1 font-bold">
                {m.sender === 'user' ? 'INVESTIGATOR' : 'AGENT (GROUNDED)'}
              </div>
              <div className="whitespace-pre-line font-sans text-xs">{m.text}</div>
              {m.toolUsed && (
                <div className="mt-2 pt-2 border-t border-zinc-200 text-[10px] text-blue-700 flex items-center gap-1.5 font-bold">
                  <Terminal className="w-3 h-3" />
                  <span>TOOL: {m.toolUsed}()</span>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="text-zinc-500 text-xs italic">
              Querying PostGIS and trajectory indices...
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-3 border-t border-zinc-200 bg-zinc-50 flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask factual question (e.g. 'Why is Pacific Voyager ranked #1?')..."
            className="flex-1 bg-white border border-zinc-300 px-3 py-2 text-zinc-950 placeholder-zinc-400 focus:outline-none focus:border-blue-600"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-bold"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
