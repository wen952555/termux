import React, { useState } from 'react';
import { BotConfig } from '../types';
import { Terminal, Battery, Cpu, Camera, ShieldAlert, Command } from 'lucide-react';

interface BotConfigFormProps {
  onGenerate: (config: BotConfig) => void;
  isGenerating: boolean;
}

const FEATURE_PRESETS = [
  { id: 'system_monitor', label: '系统监控 (CPU/内存/磁盘)', icon: <Cpu size={16} /> },
  { id: 'termux_battery', label: '电池状态 (Termux API)', icon: <Battery size={16} /> },
  { id: 'remote_exec', label: '远程 Shell 执行', icon: <Terminal size={16} /> },
  { id: 'photo_capture', label: '拍照 (Termux API)', icon: <Camera size={16} /> },
  { id: 'service_manager', label: '服务管理 (Apache/SSH)', icon: <Command size={16} /> },
];

const BotConfigForm: React.FC<BotConfigFormProps> = ({ onGenerate, isGenerating }) => {
  const [config, setConfig] = useState<BotConfig>({
    botToken: '8091415322:AAFuS0PJKnu8hi0WHwXoSqHuJTZJNRFzzS4',
    chatId: '1878794912',
    features: ['system_monitor', 'termux_battery'],
    customPrompt: '请确保机器人所有的回复消息、日志输出以及状态报告都严格使用中文（简体）。'
  });

  const toggleFeature = (id: string) => {
    setConfig(prev => ({
      ...prev,
      features: prev.features.includes(id)
        ? prev.features.filter(f => f !== id)
        : [...prev.features, id]
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate(config);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="bg-termux-surface border border-termux-border rounded-xl p-6 shadow-lg shadow-black/50">
        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
          <span className="text-termux-text">./configure</span>
          <span className="text-gray-500 text-base font-normal">--new-bot</span>
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Credentials */}
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-400">Bot Token (已预填)</label>
              <input
                type="text"
                value={config.botToken}
                onChange={(e) => setConfig({ ...config, botToken: e.target.value })}
                placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                className="w-full bg-black border border-termux-border rounded-lg px-4 py-3 text-white focus:border-termux-accent focus:ring-1 focus:ring-termux-accent outline-none transition-colors font-mono text-sm"
              />
              <p className="text-xs text-gray-600">来自 Telegram @BotFather</p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-400">Admin Chat ID (已预填)</label>
              <input
                type="text"
                value={config.chatId}
                onChange={(e) => setConfig({ ...config, chatId: e.target.value })}
                placeholder="123456789"
                className="w-full bg-black border border-termux-border rounded-lg px-4 py-3 text-white focus:border-termux-accent focus:ring-1 focus:ring-termux-accent outline-none transition-colors font-mono text-sm"
              />
              <p className="text-xs text-gray-600">你的用户 ID (来自 @userinfobot)</p>
            </div>
          </div>

          {/* Features */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-400">启用模块</label>
            <div className="grid md:grid-cols-2 gap-3">
              {FEATURE_PRESETS.map(feature => (
                <div
                  key={feature.id}
                  onClick={() => toggleFeature(feature.id)}
                  className={`cursor-pointer p-4 rounded-lg border flex items-center gap-3 transition-all ${
                    config.features.includes(feature.id)
                      ? 'bg-termux-dim/30 border-termux-accent text-white'
                      : 'bg-black border-termux-border text-gray-500 hover:border-gray-500'
                  }`}
                >
                  <div className={config.features.includes(feature.id) ? 'text-termux-accent' : ''}>
                    {feature.icon}
                  </div>
                  <span className="text-sm font-medium">{feature.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Custom Prompt */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-400">自定义行为 (可选)</label>
            <textarea
              value={config.customPrompt}
              onChange={(e) => setConfig({ ...config, customPrompt: e.target.value })}
              placeholder="例如：检查我的 python 脚本 'miner.py' 是否在运行，如果没有则重启。每天上午 9 点发送报告。"
              rows={4}
              className="w-full bg-black border border-termux-border rounded-lg px-4 py-3 text-white focus:border-termux-accent focus:ring-1 focus:ring-termux-accent outline-none transition-colors font-mono text-sm resize-none"
            />
          </div>

          {/* Warning */}
          <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-4 flex gap-3">
            <ShieldAlert className="text-yellow-500 shrink-0" />
            <div className="text-xs text-yellow-200/80">
              <strong className="block text-yellow-500 mb-1">安全警告</strong>
              启用“远程 Shell 执行”将赋予机器人对 Termux 用户的完全控制权。请确保保管好您的 Token 和 Chat ID。生成的代码包含 ID 检查以防止未经授权的访问。
            </div>
          </div>

          <button
            type="submit"
            disabled={isGenerating}
            className={`w-full py-4 rounded-lg font-bold text-lg tracking-wide uppercase transition-all ${
              isGenerating
                ? 'bg-termux-border text-gray-500 cursor-not-allowed'
                : 'bg-termux-accent text-black hover:bg-green-400 hover:shadow-[0_0_20px_rgba(0,255,0,0.3)]'
            }`}
          >
            {isGenerating ? '正在编译逻辑...' : '生成机器人脚本'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default BotConfigForm;