import React, { useState } from 'react';
import Layout from './components/Layout';
import BotConfigForm from './components/BotConfigForm';
import ResultView from './components/ResultView';
import GuideView from './components/GuideView';
import MonitorView from './components/MonitorView';
import { ViewState, BotConfig, GeneratedScript } from './types';
import { generateBotScript } from './services/geminiService';

const App: React.FC = () => {
  const [view, setView] = useState<ViewState>(ViewState.MONITOR);
  const [generatedScript, setGeneratedScript] = useState<GeneratedScript | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async (config: BotConfig) => {
    setIsGenerating(true);
    try {
      const result = await generateBotScript(config);
      setGeneratedScript(result);
      setView(ViewState.RESULT);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Generation failed");
    } finally {
      setIsGenerating(false);
    }
  };

  const renderContent = () => {
    switch (view) {
      case ViewState.MONITOR:
        return <MonitorView />;
      case ViewState.CONFIG:
        return <BotConfigForm onGenerate={handleGenerate} isGenerating={isGenerating} />;
      case ViewState.RESULT:
        return generatedScript ? (
          <ResultView result={generatedScript} onBack={() => setView(ViewState.CONFIG)} />
        ) : (
          <BotConfigForm onGenerate={handleGenerate} isGenerating={isGenerating} />
        );
      case ViewState.GUIDE:
        return <GuideView />;
      default:
        return <MonitorView />;
    }
  };

  return (
    <Layout view={view} setView={setView}>
      {renderContent()}
    </Layout>
  );
};

export default App;
