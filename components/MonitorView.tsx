import React, { useState, useEffect, useMemo } from 'react';
import { RefreshCw, Trash2, Video, Image as ImageIcon, Play, Download, Mic, CheckSquare, Square, Filter, Music, Cpu, HardDrive, Activity } from 'lucide-react';
import { SystemStats } from '../types';

interface MediaFile {
  name: string;
  url: string;
  type: 'video' | 'image' | 'audio';
  time: number;
  size: number;
}

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

const StatCard: React.FC<{ label: string; value: string; percent: number; icon: React.ReactNode; color: string }> = ({ label, value, percent, icon, color }) => (
  <div className="bg-termux-surface border border-termux-border rounded-xl p-4 flex items-center gap-4">
    <div className={`p-3 rounded-lg bg-opacity-10 ${color.replace('text-', 'bg-')}`}>
      <div className={color}>{icon}</div>
    </div>
    <div className="flex-1">
      <div className="flex justify-between items-end mb-1">
        <span className="text-gray-400 text-sm font-medium">{label}</span>
        <span className="text-white font-mono font-bold">{value}</span>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-500 ${color.replace('text-', 'bg-')}`} 
          style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
        />
      </div>
    </div>
  </div>
);

const MonitorView: React.FC = () => {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMedia, setSelectedMedia] = useState<MediaFile | null>(null);
  const [filterType, setFilterType] = useState<'all' | 'image' | 'video' | 'audio'>('all');
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedFileNames, setSelectedFileNames] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{msg: string, type: 'success'|'error'} | null>(null);

  const showToast = (msg: string, type: 'success'|'error' = 'success') => setToast({ msg, type });

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch Files
      const filesRes = await fetch('/api/files');
      if (filesRes.ok) setFiles(await filesRes.json());
      
      // Fetch Stats
      const statsRes = await fetch('/api/system');
      if (statsRes.ok) setStats(await statsRes.json());
      
    } catch (error) {
      console.error("Fetch error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

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
      } catch (e) { console.error(e); }
    }
    showToast(`成功删除 ${successCount} 个文件`);
    setSelectedFileNames(new Set());
    setIsSelectionMode(false);
    fetchData();
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
        showToast('文件已删除');
      }
    } catch (error) { showToast('删除失败', 'error'); }
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

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const renderPreview = (file: MediaFile) => {
    if (file.type === 'video') {
      return <video src={file.url} controls autoPlay className="w-full h-full object-contain bg-black" />;
    } else if (file.type === 'audio') {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gray-900 text-gray-400 p-8 relative overflow-hidden">
          <div className="flex gap-1 items-end h-24 mb-8 opacity-50">
             {[...Array(10)].map((_, i) => (
                <div key={i} className="w-2 bg-termux-accent animate-pulse" style={{ height: `${Math.random() * 100}%`, animationDelay: `${i * 0.1}s` }} />
             ))}
          </div>
          <Mic size={48} className="mb-6 text-white z-10" />
          <audio src={file.url} controls className="w-full max-w-md z-10 relative" />
        </div>
      );
    }
    return <img src={file.url} alt="Preview" className="w-full h-full object-contain" />;
  };

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      
      {/* System Stats Section */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          label="CPU Load" 
          value={`${stats?.cpu || 0}%`} 
          percent={stats?.cpu || 0} 
          icon={<Activity size={20} />} 
          color="text-blue-400" 
        />
        <StatCard 
          label="Memory" 
          value={stats ? `${formatBytes(stats.memory.used)}` : '-'} 
          percent={stats?.memory.percent || 0} 
          icon={<Cpu size={20} />} 
          color="text-purple-400" 
        />
        <StatCard 
          label="Disk" 
          value={stats ? `${formatBytes(stats.disk.used)}` : '-'} 
          percent={stats?.disk.percent || 0} 
          icon={<HardDrive size={20} />} 
          color="text-yellow-400" 
        />
         <div className="bg-termux-surface border border-termux-border rounded-xl p-4 flex flex-col justify-center gap-1">
            <span className="text-gray-400 text-sm">Uptime</span>
            <span className="text-white font-mono font-bold text-lg">
              {stats ? new Date(stats.uptime * 1000).toISOString().substr(11, 8) : '--:--:--'}
            </span>
            <span className="text-xs text-termux-dim mt-1 truncate">{stats?.platform || 'Loading...'}</span>
         </div>
      </section>

      {/* Media Toolbar */}
      <div className="flex items-center justify-between bg-termux-surface/50 p-4 rounded-xl border border-termux-border backdrop-blur">
         <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
            {[
              { id: 'all', label: 'All', icon: <Filter size={14} /> },
              { id: 'image', label: 'Images', icon: <ImageIcon size={14} /> },
              { id: 'video', label: 'Videos', icon: <Video size={14} /> },
              { id: 'audio', label: 'Audio', icon: <Music size={14} /> },
            ].map((tab) => (
               <button
                 key={tab.id}
                 onClick={() => setFilterType(tab.id as any)}
                 className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                   filterType === tab.id 
                   ? 'bg-termux-accent text-black' 
                   : 'text-gray-400 hover:text-white'
                 }`}
               >
                 {tab.icon} {tab.label}
               </button>
            ))}
         </div>

         <div className="flex items-center gap-2">
           {isSelectionMode ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400 hidden md:inline">{selectedFileNames.size} selected</span>
                <button onClick={deleteSelected} disabled={selectedFileNames.size === 0} className="p-2 bg-red-600/80 hover:bg-red-600 text-white rounded-lg transition-colors">
                  <Trash2 size={16} />
                </button>
                <button onClick={() => { setIsSelectionMode(false); setSelectedFileNames(new Set()); }} className="px-3 py-2 text-xs font-bold text-gray-400 hover:text-white uppercase">Cancel</button>
              </div>
           ) : (
              <button onClick={() => setIsSelectionMode(true)} className="px-3 py-2 text-xs font-bold bg-termux-dim text-termux-accent hover:bg-termux-dim/80 rounded-lg uppercase transition-colors">Select</button>
           )}
           <button onClick={fetchData} className={`p-2 hover:bg-white/10 rounded-lg text-termux-accent transition-colors ${loading ? 'animate-spin' : ''}`}>
             <RefreshCw size={16} />
           </button>
         </div>
      </div>

      {/* Preview Player */}
      {selectedMedia && !isSelectionMode && (
        <div className="relative bg-black border border-termux-border rounded-xl overflow-hidden shadow-2xl animate-fade-in">
           <div className="flex items-center justify-between p-3 bg-termux-surface border-b border-termux-border">
              <span className="text-sm font-mono text-gray-300">{selectedMedia.name}</span>
              <button onClick={() => setSelectedMedia(null)} className="text-xs text-red-400 hover:text-red-300 uppercase font-bold">Close Preview</button>
           </div>
           <div className="aspect-video flex items-center justify-center bg-[#050505]">
              {renderPreview(selectedMedia)}
           </div>
        </div>
      )}

      {/* Gallery Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {filteredFiles.map((file) => {
          const isSelected = selectedFileNames.has(file.name);
          return (
            <div 
              key={file.name}
              onClick={() => isSelectionMode ? toggleSelection(file.name) : setSelectedMedia(file)}
              className={`group relative aspect-square bg-termux-surface rounded-xl overflow-hidden border cursor-pointer transition-all ${
                isSelected 
                  ? 'border-termux-accent ring-2 ring-termux-accent/30' 
                  : (selectedMedia?.name === file.name ? 'border-termux-accent' : 'border-termux-border hover:border-gray-500')
              }`}
            >
              {isSelectionMode && (
                <div className="absolute top-2 right-2 z-10">
                   {isSelected ? <CheckSquare size={18} className="text-termux-accent fill-black" /> : <Square size={18} className="text-gray-400 fill-black/50" />}
                </div>
              )}

              <div className="w-full h-full flex items-center justify-center">
                {file.type === 'video' ? (
                  <>
                    <video src={file.url} className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity" muted />
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="p-2 rounded-full bg-black/50 backdrop-blur text-white"><Play size={16} fill="currentColor" /></div>
                    </div>
                  </>
                ) : file.type === 'audio' ? (
                   <div className="flex flex-col items-center gap-2 text-gray-500 group-hover:text-termux-accent">
                      <Mic size={32} />
                      <span className="text-[10px] uppercase font-bold tracking-wider">Audio Clip</span>
                   </div>
                ) : (
                  <img src={file.url} alt={file.name} loading="lazy" className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity" />
                )}
              </div>

              <div className="absolute bottom-0 inset-x-0 p-2 bg-gradient-to-t from-black/90 to-transparent pt-8 flex justify-between items-end">
                <span className="text-[10px] font-mono text-gray-400 truncate w-full">{new Date(file.time).toLocaleTimeString()}</span>
              </div>
            </div>
          );
        })}
        {filteredFiles.length === 0 && (
          <div className="col-span-full py-12 text-center text-gray-600 border-2 border-dashed border-termux-border rounded-xl">
            No media files found.
          </div>
        )}
      </div>

      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
};

export default MonitorView;
