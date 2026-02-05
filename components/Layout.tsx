import React from 'react';
import { TerminalIcon } from './TerminalIcon';
import { Bot, BookOpen, Activity } from 'lucide-react';
import { ViewState } from '../types';

interface LayoutProps {
  children: React.ReactNode;
  view: ViewState;
  setView: (view: ViewState) => void;
}

const Layout: React.FC<LayoutProps> = ({ children, view, setView }) => {
  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-termux-bg text-gray-300 font-mono selection:bg-termux-dim selection:text-white">
      {/* Sidebar / Header */}
      <aside className="w-full md:w-64 bg-termux-surface border-b md:border-b-0 md:border-r border-termux-border flex-shrink-0">
        <div className="p-6 border-b border-termux-border">
          <div className="flex items-center gap-3 text-termux-text">
            <TerminalIcon className="w-8 h-8" />
            <h1 className="text-xl font-bold tracking-tighter">BotGen AI</h1>
          </div>
          <p className="text-xs text-gray-500 mt-2">Termux Telegram Manager</p>
        </div>

        <nav className="p-4 space-y-2">
          <button
            onClick={() => setView(ViewState.MONITOR)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
              view === ViewState.MONITOR
                ? 'bg-termux-dim text-termux-accent border border-termux-dim'
                : 'hover:bg-gray-900 hover:text-white'
            }`}
          >
            <Activity size={20} />
            <span>Dashboard</span>
          </button>

          <button
            onClick={() => setView(ViewState.CONFIG)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
              view === ViewState.CONFIG || view === ViewState.GENERATING || view === ViewState.RESULT
                ? 'bg-termux-dim text-termux-accent border border-termux-dim'
                : 'hover:bg-gray-900 hover:text-white'
            }`}
          >
            <Bot size={20} />
            <span>Bot Generator</span>
          </button>

          <button
            onClick={() => setView(ViewState.GUIDE)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
              view === ViewState.GUIDE
                ? 'bg-termux-dim text-termux-accent border border-termux-dim'
                : 'hover:bg-gray-900 hover:text-white'
            }`}
          >
            <BookOpen size={20} />
            <span>Setup Guide</span>
          </button>
        </nav>

        <div className="md:absolute md:bottom-0 md:left-0 md:w-64 p-4 border-t border-termux-border hidden md:block">
          <div className="text-xs text-gray-600 text-center">
            Powered by Gemini 3 Flash
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto h-[calc(100vh-64px)] md:h-screen p-4 md:p-8">
        <div className="max-w-6xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
