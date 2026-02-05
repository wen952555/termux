import React from 'react';

const GuideView: React.FC = () => {
  return (
    <div className="space-y-8 animate-fade-in text-gray-300">
      <div className="border-b border-termux-border pb-6">
        <h2 className="text-3xl font-bold text-white mb-2">Termux Setup Guide</h2>
        <p className="text-lg text-gray-400">Prerequisites for running your new Telegram Bot.</p>
      </div>

      <section className="space-y-4">
        <h3 className="text-xl font-bold text-termux-accent">1. Environment Check: Ubuntu vs Native</h3>
        <p>You mentioned having Ubuntu installed. You can run the bot in either environment, but there are trade-offs:</p>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-black border border-termux-border rounded-lg p-4">
            <h4 className="font-bold text-white mb-2">Native Termux (Recommended)</h4>
            <p className="text-sm text-gray-400">Best for hardware access (Battery, Camera, SMS) via Termux:API. Simplest setup.</p>
          </div>
          <div className="bg-black border border-termux-border rounded-lg p-4">
            <h4 className="font-bold text-white mb-2">Ubuntu (PRoot)</h4>
            <p className="text-sm text-gray-400">Best for running complex Linux software or standard databases. Hardware access requires extra configuration.</p>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h3 className="text-xl font-bold text-termux-accent">2. Install Dependencies</h3>
        <p>Run these commands in your chosen environment:</p>
        <div className="bg-black border border-termux-border rounded-lg p-4 font-mono text-sm text-termux-text">
          <p className="text-gray-500"># In Termux or Ubuntu:</p>
          <p>pip install python-telegram-bot psutil</p>
          <br/>
          <p className="text-gray-500"># If you need Termux API (Native Termux only):</p>
          <p>pkg install termux-api</p>
        </div>
      </section>

      <section className="space-y-4">
        <h3 className="text-xl font-bold text-termux-accent">3. Running the Bot</h3>
        <p>Copy the generated code into a file named <code className="bg-termux-dim px-1 rounded">bot.py</code>.</p>
        <div className="bg-black border border-termux-border rounded-lg p-4 font-mono text-sm text-termux-text">
          <p>python bot.py</p>
        </div>
        <p>To keep it running in the background, use <code className="text-white">tmux</code> (recommended) or <code className="text-white">nohup</code>.</p>
      </section>

      <section className="space-y-4">
        <h3 className="text-xl font-bold text-termux-accent">4. Accessing Termux API from Ubuntu</h3>
        <p>If you must run in Ubuntu but need battery/camera status, you typically need to:</p>
        <ul className="list-disc list-inside space-y-1 ml-4 text-gray-400 text-sm">
          <li>Ensure <code className="text-gray-300">termux-exec</code> is installed in Native Termux.</li>
          <li>Sometimes call the binary directly: <code className="text-gray-300">/data/data/com.termux/files/usr/bin/termux-battery-status</code></li>
        </ul>
      </section>
    </div>
  );
};

export default GuideView;
