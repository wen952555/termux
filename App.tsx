import React, { useState } from 'react';
import Layout from './components/Layout';
import BotConfigForm from './components/BotConfigForm';
import ResultView from './components/ResultView';
import GuideView from './components/GuideView';
import { generateBotScript } from './services/geminiService';
import { ViewState, BotConfig, GeneratedScript } from './types';
import { HashRouter } from 'react-router-dom';

const App: React.FC = () => {
  const [view, setView] = useState<ViewState>(ViewState.CONFIG);
  const [generatedResult, setGeneratedResult] = useState<GeneratedScript | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (config: BotConfig) => {
    setView(ViewState.GENERATING);
    setError(null);
    try {
      const result = await generateBotScript(config);
      setGeneratedResult(result);
      setView(ViewState.RESULT);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred.");
      setView(ViewState.CONFIG);
    }
  };

  const renderContent = () => {
    switch (view) {
      case ViewState.CONFIG:
      case ViewState.GENERATING:
        return (
          <>
            {error && (
              <div className="mb-6 bg-red-900/20 border border-red-500/50 text-red-200 p-4 rounded-lg">
                Error: {error}
              </div>
            )}
            {view === ViewState.GENERATING ? (
              <div className="flex flex-col items-center justify-center h-96 space-y-6">
                <div className="relative w-24 h-24">
                  <div className="absolute inset-0 border-4 border-termux-dim rounded-full"></div>
                  <div className="absolute inset-0 border-4 border-termux-accent rounded-full border-t-transparent animate-spin"></div>
                </div>
                <div className="text-center space-y-2">
                  <h3 className="text-xl font-bold text-white">Generating Script...</h3>
                  <p className="text-gray-500">Writing Python code optimized for Termux</p>
                </div>
              </div>
            ) : (
              <BotConfigForm onGenerate={handleGenerate} isGenerating={false} />
            )}
          </>
        );
      case ViewState.RESULT:
        return generatedResult ? (
          <ResultView 
            result={generatedResult} 
            onBack={() => setView(ViewState.CONFIG)} 
          />
        ) : (
          <div>No result found</div>
        );
      case ViewState.GUIDE:
        return <GuideView />;
      default:
        return <div>Unknown state</div>;
    }
  };

  return (
    <HashRouter>
      <Layout view={view} setView={setView}>
        {renderContent()}
      </Layout>
    </HashRouter>
  );
};

export default App;
