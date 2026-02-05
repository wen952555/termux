import React, { useState, useEffect } from 'react';
import { TerminalIcon } from './components/TerminalIcon';
import { RefreshCw, Trash2, Video, Image as ImageIcon, Play, Download, Mic } from 'lucide-react';

interface MediaFile {
  name: string;
  url: string;
  type: 'video' | 'image' | 'audio';
  time: number;
  size: number;
}

const App: React.FC = () => {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMedia, setSelectedMedia] = useState<MediaFile | null>(null);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/files');
      if (!res.ok) {
        console.error(`API Error: ${res.status} ${res.statusText}`);
        return;
      }
      
      const text = await res.text();
      try {
        const data = JSON.parse(text);
        if (Array.isArray(data)) {
          setFiles(data);
        } else {
          console.error("API returned non-array:", data);
          setFiles([]);
        }
      } catch (e) {
        console.error("JSON Parse Error:", e, "Response Text:", text);
      }
    } catch (error) {
      console.error("Network error:", error);
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定要删除这个文件吗？')) return;
    
    try {
      const res = await fetch('/api/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      
      if (res.ok) {
        setFiles(prev => prev.filter(f => f.name !== filename));
        if (selectedMedia?.name === filename) setSelectedMedia(null);
      } else {
        alert('删除失败');
      }
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  useEffect(() => {
    fetchFiles();
    const interval = setInterval(fetchFiles, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (ms: number) => new Date(ms).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
  });

  const renderPreview = (file: MediaFile) => {
    if (file.type === 'video') {
      return (
        <video 
          src={file.url} 
          controls 
          autoPlay 
          className="w-full h-full object-contain" 
          key={file.name} 
        />
      );
    } else if (file.type === 'audio') {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gray-900 text-gray-400 p-8">
          <Mic size={64} className="mb-8 text-termux-accent animate-pulse" />
          <audio 
            src={file.url} 
            controls 
            className="w-full max-w-md" 
            key={file.name}
          />
        </div>
      );
    } else {
      return (
        <img 
          src={file.url} 
          alt="Latest" 
          className="w-full h-full object-contain"
        />
      );
    }
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'video': return <Video size={10} />;
      case 'audio': return <Mic size={10} />;
      default: return <ImageIcon size={10} />;
    }
  };

  return (
    <div className="min-h-screen bg-black text-gray-300 font-mono selection:bg-green-900 selection:text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 text-green-500">
            <TerminalIcon className="w-6 h-6" />
            <h1 className="text-xl font-bold tracking-tight">Termux Monitor</h1>
          </div>
          <button 
            onClick={fetchFiles}
            disabled={loading}
            className="p-2 hover:bg-gray-800 rounded-full transition-colors active:scale-95"
          >
            <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 space-y-8">
        {/* Latest Capture / Live Preview Area */}
        {files.length > 0 && (
          <section className="animate-fade-in">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
              <h2 className="text-sm font-bold uppercase text-gray-500 tracking-wider">Latest Capture</h2>
            </div>
            <div className="relative aspect-video bg-gray-900 rounded-xl overflow-hidden border border-gray-800 shadow-2xl group flex items-center justify-center">
               {renderPreview(selectedMedia || files[0])}
               
               <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 to-transparent pointer-events-none">
                 <p className="text-white font-bold">{(selectedMedia || files[0]).name}</p>
                 <p className="text-xs text-gray-400">{formatTime((selectedMedia || files[0]).time)}</p>
               </div>
            </div>
          </section>
        )}

        {/* Gallery Grid */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">Media Library ({files.length})</h2>
          </div>

          {files.length === 0 ? (
            <div className="text-center py-20 bg-gray-900/30 rounded-xl border border-dashed border-gray-800">
              <p className="text-gray-500">暂无媒体文件</p>
              <p className="text-xs text-gray-600 mt-2">在 Telegram Bot 中使用 /start 拍摄或录音</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {files.map((file) => (
                <div 
                  key={file.name}
                  onClick={() => setSelectedMedia(file)}
                  className={`group relative aspect-square bg-gray-900 rounded-lg overflow-hidden border cursor-pointer transition-all ${
                    selectedMedia?.name === file.name ? 'border-green-500 ring-1 ring-green-500' : 'border-gray-800 hover:border-gray-600'
                  }`}
                >
                  {/* Thumbnail Logic */}
                  {file.type === 'video' ? (
                    <>
                      <video src={file.url} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="w-10 h-10 rounded-full bg-black/50 backdrop-blur flex items-center justify-center text-white">
                          <Play size={16} fill="currentColor" />
                        </div>
                      </div>
                    </>
                  ) : file.type === 'audio' ? (
                     <div className="w-full h-full flex items-center justify-center bg-gray-800 text-gray-500 group-hover:text-termux-accent transition-colors">
                       <Mic size={48} />
                     </div>
                  ) : (
                    <img src={file.url} alt={file.name} loading="lazy" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                  )}

                  {/* Type Badge */}
                  <div className="absolute top-2 left-2 bg-black/60 px-2 py-1 rounded text-xs text-white flex items-center gap-1">
                    {getFileIcon(file.type)} <span className="uppercase">{file.type}</span>
                  </div>

                  {/* Overlay Controls */}
                  <div className="absolute bottom-0 left-0 right-0 p-2 bg-black/80 backdrop-blur translate-y-full group-hover:translate-y-0 transition-transform flex items-center justify-between">
                    <span className="text-[10px] text-gray-400 truncate max-w-[60%]">{formatTime(file.time)}</span>
                    <div className="flex gap-2">
                      <a 
                        href={file.url} 
                        download 
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 hover:bg-gray-700 rounded text-gray-300 hover:text-white"
                      >
                        <Download size={14} />
                      </a>
                      <button 
                        onClick={(e) => deleteFile(file.name, e)}
                        className="p-1.5 hover:bg-red-900/50 rounded text-gray-300 hover:text-red-400"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default App;