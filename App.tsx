import React, { useState, useEffect, useMemo } from 'react';
import { TerminalIcon } from './components/TerminalIcon';
import { RefreshCw, Trash2, Video, Image as ImageIcon, Play, Download, Mic, CheckSquare, Square, Filter, Music } from 'lucide-react';

interface MediaFile {
  name: string;
  url: string;
  type: 'video' | 'image' | 'audio';
  time: number;
  size: number;
}

// 简单的 Toast 组件
const Toast = ({ message, type, onClose }: { message: string, type: 'success' | 'error', onClose: () => void }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white font-medium animate-fade-in z-50 ${
      type === 'success' ? 'bg-green-600' : 'bg-red-600'
    }`}>
      {message}
    </div>
  );
};

const App: React.FC = () => {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMedia, setSelectedMedia] = useState<MediaFile | null>(null);
  
  // 筛选与选择状态
  const [filterType, setFilterType] = useState<'all' | 'image' | 'video' | 'audio'>('all');
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedFileNames, setSelectedFileNames] = useState<Set<string>>(new Set());
  
  // Toast
  const [toast, setToast] = useState<{msg: string, type: 'success'|'error'} | null>(null);

  const showToast = (msg: string, type: 'success'|'error' = 'success') => {
    setToast({ msg, type });
  };

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/files');
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      if (Array.isArray(data)) {
        setFiles(data);
      }
    } catch (error) {
      console.error("Network error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
    const interval = setInterval(fetchFiles, 10000); // 10秒自动刷新
    return () => clearInterval(interval);
  }, []);

  // 批量删除
  const deleteSelected = async () => {
    if (selectedFileNames.size === 0) return;
    if (!confirm(`确定要删除选中的 ${selectedFileNames.size} 个文件吗？`)) return;

    let successCount = 0;
    for (const filename of Array.from(selectedFileNames)) {
      try {
        const res = await fetch('/api/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename })
        });
        if (res.ok) successCount++;
      } catch (e) {
        console.error(e);
      }
    }

    showToast(`成功删除 ${successCount} 个文件`);
    setSelectedFileNames(new Set());
    setIsSelectionMode(false);
    fetchFiles();
  };

  // 单个删除
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
        showToast('文件已删除');
      }
    } catch (error) {
      showToast('删除失败', 'error');
    }
  };

  const toggleSelection = (filename: string) => {
    const newSet = new Set(selectedFileNames);
    if (newSet.has(filename)) newSet.delete(filename);
    else newSet.add(filename);
    setSelectedFileNames(newSet);
  };

  const filteredFiles = useMemo(() => {
    if (filterType === 'all') return files;
    return files.filter(f => f.type === filterType);
  }, [files, filterType]);

  const formatTime = (ms: number) => new Date(ms).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
  });

  // --- 渲染逻辑 ---

  const renderPreview = (file: MediaFile) => {
    if (file.type === 'video') {
      return (
        <video 
          src={file.url} 
          controls 
          autoPlay 
          className="w-full h-full object-contain bg-black" 
          key={file.name} 
        />
      );
    } else if (file.type === 'audio') {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gray-900 text-gray-400 p-8 relative overflow-hidden">
          {/* Audio Visualizer Effect */}
          <div className="flex gap-1 items-end h-24 mb-8 opacity-50">
             {[...Array(10)].map((_, i) => (
                <div key={i} className="w-2 bg-termux-accent animate-pulse" style={{ height: `${Math.random() * 100}%`, animationDelay: `${i * 0.1}s` }} />
             ))}
          </div>
          <Mic size={48} className="mb-6 text-white z-10" />
          <audio 
            src={file.url} 
            controls 
            className="w-full max-w-md z-10 relative" 
            key={file.name}
          />
        </div>
      );
    } else {
      return (
        <img 
          src={file.url} 
          alt="Preview" 
          className="w-full h-full object-contain"
        />
      );
    }
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'video': return <Video size={14} />;
      case 'audio': return <Music size={14} />;
      default: return <ImageIcon size={14} />;
    }
  };

  return (
    <div className="min-h-screen bg-black text-gray-300 font-mono selection:bg-green-900 selection:text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 text-termux-accent">
            <TerminalIcon className="w-6 h-6" />
            <h1 className="text-xl font-bold tracking-tight hidden md:block">Termux Monitor</h1>
            <span className="md:hidden font-bold">Monitor</span>
          </div>
          
          <div className="flex items-center gap-3">
             {/* 批量操作按钮 */}
             {isSelectionMode ? (
                <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1 animate-fade-in">
                  <span className="text-xs px-2">{selectedFileNames.size} 选定</span>
                  <button 
                    onClick={deleteSelected}
                    disabled={selectedFileNames.size === 0}
                    className="p-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Trash2 size={18} />
                  </button>
                  <button onClick={() => { setIsSelectionMode(false); setSelectedFileNames(new Set()); }} className="p-2 text-gray-400 hover:text-white">取消</button>
                </div>
             ) : (
                <button 
                  onClick={() => setIsSelectionMode(true)}
                  className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded text-gray-300 transition-colors"
                >
                  选择
                </button>
             )}

            <button 
              onClick={fetchFiles}
              disabled={loading}
              className="p-2 hover:bg-gray-800 rounded-full transition-colors active:scale-95 text-termux-accent"
            >
              <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 space-y-6">
        
        {/* Latest Preview Section */}
        {!isSelectionMode && selectedMedia && (
          <section className="animate-fade-in mb-8">
            <div className="flex items-center justify-between mb-2">
               <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-termux-accent animate-pulse"></div>
                <h2 className="text-sm font-bold uppercase text-gray-500 tracking-wider">Active Preview</h2>
               </div>
               <button onClick={() => setSelectedMedia(null)} className="text-xs text-gray-500 hover:text-white">Close</button>
            </div>
            <div className="relative aspect-video bg-gray-900 rounded-xl overflow-hidden border border-gray-800 shadow-2xl flex items-center justify-center">
               {renderPreview(selectedMedia)}
               <div className="absolute top-4 left-4 bg-black/60 backdrop-blur px-3 py-1 rounded text-white text-xs font-bold">
                 {selectedMedia.name}
               </div>
            </div>
          </section>
        )}

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {[
            { id: 'all', label: '全部', icon: <Filter size={14} /> },
            { id: 'image', label: '图片', icon: <ImageIcon size={14} /> },
            { id: 'video', label: '视频', icon: <Video size={14} /> },
            { id: 'audio', label: '音频', icon: <Music size={14} /> },
          ].map((tab) => (
             <button
               key={tab.id}
               onClick={() => setFilterType(tab.id as any)}
               className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap ${
                 filterType === tab.id 
                 ? 'bg-termux-accent text-black shadow-[0_0_10px_rgba(0,255,0,0.3)]' 
                 : 'bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-white'
               }`}
             >
               {tab.icon}
               {tab.label}
               <span className="ml-1 opacity-60 text-xs">
                 {tab.id === 'all' ? files.length : files.filter(f => f.type === tab.id).length}
               </span>
             </button>
          ))}
        </div>

        {/* Media Grid */}
        <section>
          {filteredFiles.length === 0 ? (
            <div className="text-center py-20 bg-gray-900/30 rounded-xl border border-dashed border-gray-800">
              <p className="text-gray-500">暂无此类文件</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {filteredFiles.map((file) => {
                const isSelected = selectedFileNames.has(file.name);
                return (
                  <div 
                    key={file.name}
                    onClick={() => {
                       if (isSelectionMode) toggleSelection(file.name);
                       else setSelectedMedia(file);
                    }}
                    className={`group relative aspect-square bg-gray-900 rounded-lg overflow-hidden border cursor-pointer transition-all duration-200 ${
                      isSelected 
                        ? 'border-termux-accent ring-2 ring-termux-accent/50 bg-gray-800' 
                        : (selectedMedia?.name === file.name ? 'border-termux-accent' : 'border-gray-800 hover:border-gray-600')
                    }`}
                  >
                    {/* Selection Checkbox Overlay */}
                    {isSelectionMode && (
                      <div className="absolute top-2 right-2 z-10 text-white">
                         {isSelected ? <CheckSquare className="text-termux-accent fill-black" /> : <Square className="text-gray-400 fill-black/50" />}
                      </div>
                    )}

                    {/* Content Preview */}
                    <div className="w-full h-full flex items-center justify-center overflow-hidden">
                      {file.type === 'video' ? (
                        <>
                          <video src={file.url} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" muted />
                          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <div className="w-8 h-8 rounded-full bg-black/50 backdrop-blur flex items-center justify-center text-white">
                              <Play size={14} fill="currentColor" />
                            </div>
                          </div>
                        </>
                      ) : file.type === 'audio' ? (
                         <div className="flex flex-col items-center gap-2 text-gray-500 group-hover:text-termux-accent transition-colors p-4 text-center">
                           <div className="p-3 bg-gray-800 rounded-full group-hover:bg-gray-700 transition-colors">
                              <Mic size={24} />
                           </div>
                           <span className="text-[10px] break-all line-clamp-2 leading-tight">{file.name}</span>
                         </div>
                      ) : (
                        <img src={file.url} alt={file.name} loading="lazy" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                      )}
                    </div>

                    {/* Type Badge */}
                    <div className="absolute top-2 left-2 bg-black/60 backdrop-blur px-1.5 py-0.5 rounded text-[10px] text-white flex items-center gap-1 font-bold tracking-wider border border-white/10">
                      {getFileIcon(file.type)} <span className="uppercase">{file.type}</span>
                    </div>

                    {/* Bottom Info Bar */}
                    <div className="absolute bottom-0 left-0 right-0 p-2 bg-black/90 backdrop-blur translate-y-full group-hover:translate-y-0 transition-transform flex items-center justify-between z-10">
                      <span className="text-[10px] text-gray-400 font-mono">{formatTime(file.time).split(' ')[1]}</span>
                      {!isSelectionMode && (
                        <div className="flex gap-1">
                          <a 
                            href={file.url} 
                            download
                            onClick={(e) => e.stopPropagation()}
                            className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                          >
                            <Download size={14} />
                          </a>
                          <button 
                            onClick={(e) => deleteFile(file.name, e)}
                            className="p-1 hover:bg-red-900/50 rounded text-gray-400 hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>

      {/* Toast Container */}
      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
};

export default App;