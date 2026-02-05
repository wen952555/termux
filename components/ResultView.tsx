import React, { useState } from 'react';
import { GeneratedScript } from '../types';
import { Copy, Check, Download, ArrowLeft } from 'lucide-react';

interface ResultViewProps {
  result: GeneratedScript;
  onBack: () => void;
}

const ResultView: React.FC<ResultViewProps> = ({ result, onBack }) => {
  const [copiedCode, setCopiedCode] = useState(false);
  const [activeTab, setActiveTab] = useState<'code' | 'instructions'>('code');

  const handleCopy = () => {
    navigator.clipboard.writeText(result.code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([result.code], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'termux_bot.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={20} />
          <span>Back to Config</span>
        </button>
        
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('code')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'code' ? 'bg-termux-dim text-termux-accent' : 'bg-transparent text-gray-500 hover:text-white'
            }`}
          >
            bot.py
          </button>
          <button
            onClick={() => setActiveTab('instructions')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'instructions' ? 'bg-termux-dim text-termux-accent' : 'bg-transparent text-gray-500 hover:text-white'
            }`}
          >
            README.md
          </button>
        </div>
      </div>

      <div className="bg-termux-surface border border-termux-border rounded-xl overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 bg-black/50 border-b border-termux-border">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500/50" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
            <div className="w-3 h-3 rounded-full bg-green-500/50" />
          </div>
          {activeTab === 'code' && (
            <div className="flex gap-2">
              <button 
                onClick={handleCopy}
                className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"
                title="Copy to Clipboard"
              >
                {copiedCode ? <Check size={18} className="text-termux-accent" /> : <Copy size={18} />}
              </button>
              <button 
                onClick={handleDownload}
                className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"
                title="Download .py file"
              >
                <Download size={18} />
              </button>
            </div>
          )}
        </div>
        
        <div className="relative">
          {activeTab === 'code' ? (
            <pre className="p-6 overflow-x-auto bg-[#0c0c0c] text-sm md:text-base font-mono leading-relaxed">
              <code className="text-gray-300">
                {result.code.split('\n').map((line, i) => (
                  <div key={i} className="table-row">
                    <span className="table-cell select-none text-gray-700 w-10 text-right pr-4">{i + 1}</span>
                    <span className="table-cell">{line}</span>
                  </div>
                ))}
              </code>
            </pre>
          ) : (
            <div className="p-6 bg-[#0c0c0c] text-gray-300 prose prose-invert max-w-none">
              <pre className="whitespace-pre-wrap font-sans">
                {result.instructions}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResultView;
