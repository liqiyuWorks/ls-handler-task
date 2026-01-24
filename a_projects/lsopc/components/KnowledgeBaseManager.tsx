import React, { useState, useEffect } from 'react';
import { Settings, Database, FileText, Upload, Link, Check, AlertCircle, RefreshCw, Trash2, FolderOpen, ArrowLeft, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Utility components for UI consistency
const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
    <div className={`glass-morphism rounded-xl border border-white/10 p-6 ${className}`}>
        {children}
    </div>
);

const Button: React.FC<{
    onClick?: () => void;
    children: React.ReactNode;
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    disabled?: boolean;
    className?: string;
}> = ({ onClick, children, variant = 'primary', disabled = false, className = '' }) => {
    const variants = {
        primary: "bg-orange-500 hover:bg-orange-600 text-white",
        secondary: "bg-white/10 hover:bg-white/20 text-white",
        danger: "bg-red-500/80 hover:bg-red-600 text-white",
        ghost: "hover:bg-white/5 text-gray-300 hover:text-white"
    };

    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
        >
            {children}
        </button>
    );
};

const Input: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = (props) => (
    <input
        {...props}
        className={`w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 transition-all ${props.className}`}
    />
);

// --- API Service Client ---
// const API_BASE = "http://localhost:8000/api/coze"; // Adjust if necessary
const API_BASE = "http://api.lsopc.cn/api/coze"; // Adjust if necessary

interface Dataset {
    dataset_id: string;
    name: string;
    description: string;
    doc_count: number;
    hit_count: number;
    status: number;
    format_type: number;
}

interface DocFile {
    document_id: string;
    name: string;
    size: number;
    type: string;
    status: number; // 0: processing, 1: done, 2: failed
    update_time: number;
}

const KnowledgeBaseManager: React.FC = () => {
    const navigate = useNavigate();

    // State
    const [token, setToken] = useState(localStorage.getItem('coze_token') || '');
    const [spaceId, setSpaceId] = useState(localStorage.getItem('coze_space_id') || '');
    const [showConfig, setShowConfig] = useState(!token || !spaceId);

    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
    const [files, setFiles] = useState<DocFile[]>([]);

    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Upload/Add URL State
    // Upload/Add URL State
    const [urlInput, setUrlInput] = useState('');
    // const [urlName, setUrlName] = useState(''); // Removed simple name state
    const [fileInput, setFileInput] = useState<FileList | null>(null);

    // Persist config
    useEffect(() => {
        if (token) localStorage.setItem('coze_token', token);
        if (spaceId) localStorage.setItem('coze_space_id', spaceId);
    }, [token, spaceId]);

    // Helpers
    const getHeaders = () => ({
        'x-coze-token': token,
        'x-coze-space-id': spaceId
    });

    const handleError = (err: any) => {
        const msg = err.response?.data?.detail || err.message || "Unknown error";
        setError(msg);
        setTimeout(() => setError(null), 5000);
    };

    const handleSuccess = (msg: string) => {
        setSuccess(msg);
        setTimeout(() => setSuccess(null), 3000);
    };

    // Actions
    const fetchDatasets = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/datasets?page_size=50`, { headers: getHeaders() });
            if (!res.ok) throw await res.json();
            const data = await res.json();
            setDatasets(data.data?.dataset_list || []);
            setShowConfig(false);
        } catch (err: any) {
            handleError(err);
            // If auth error, show config
            if (err.status === 401 || JSON.stringify(err).includes("401")) setShowConfig(true);
        } finally {
            setLoading(false);
        }
    };

    const fetchFiles = async (datasetId: string) => {
        setLoading(true);
        try {
            // Increase page_size to 100 to show more files by default
            const res = await fetch(`${API_BASE}/datasets/${datasetId}/files?size=100`, { headers: getHeaders() });
            if (!res.ok) throw await res.json();
            const data = await res.json();
            // API V1/OpenAPI difference handling: check root then data.data
            const docs = data.document_infos || data.data?.document_infos || [];
            setFiles(docs);
        } catch (err) {
            handleError(err);
        } finally {
            setLoading(false);
        }
    };

    const handleDatasetSelect = (ds: Dataset) => {
        setSelectedDataset(ds);
        fetchFiles(ds.dataset_id);
    };

    const handleUpload = async () => {
        if (!selectedDataset || !fileInput) return;
        setUploading(true);

        const formData = new FormData();
        formData.append('dataset_id', selectedDataset.dataset_id);
        // fileInput is now FileList or File[]
        if (fileInput instanceof FileList) {
            Array.from(fileInput).forEach(file => {
                formData.append('files', file);
            });
        } else if (fileInput) {
            formData.append('files', fileInput as any);
        }

        try {
            const res = await fetch(`${API_BASE}/files/upload`, {
                method: 'POST',
                headers: {
                    'x-coze-token': token,
                    'x-coze-space-id': spaceId
                },
                body: formData
            });
            if (!res.ok) throw await res.json();
            const result = await res.json();
            // result.results is array of {filename, status, ...}
            const successCount = result.results.filter((r: any) => r.status === 'success').length;
            const failCount = result.results.length - successCount;

            if (failCount === 0) {
                handleSuccess(`所有 ${successCount} 个文件上传成功`);
            } else {
                handleError(`上传成功 ${successCount} 个文件，${failCount} 个失败。`);
            }

            setFileInput(null);
            fetchFiles(selectedDataset.dataset_id);
        } catch (err) {
            handleError(err);
        } finally {
            setUploading(false);
        }
    };

    const handleAddUrl = async () => {
        if (!selectedDataset || !urlInput) return;
        setUploading(true);

        // Parse Multiple URLs
        // Format: Name | URL (one per line) OR just URL (auto name)
        const lines = urlInput.split('\n').filter(l => l.trim());
        const urlsToAdd = lines.map((line, idx) => {
            const parts = line.split('|');
            let u = parts[0].trim();
            let n = parts[1] ? parts[1].trim() : `Link ${Date.now()}_${idx}`;

            // Check if user swapped url/name or just pasted url
            if (u.startsWith('http')) {
                // u is url
            } else if (parts.length > 1 && parts[1].trim().startsWith('http')) {
                n = parts[0].trim();
                u = parts[1].trim();
            } else {
                // fallback, assume imports are names? no, assume urls as primary
                if (!u.startsWith('http')) {
                    // try to find url in string? simpler: require http
                }
            }
            return { url: u, name: n };
        }).filter(item => item.url.startsWith('http'));

        if (urlsToAdd.length === 0) {
            handleError("未找到有效 URL。使用格式：URL | 名称 (可选)");
            setUploading(false);
            return;
        }

        if (urlsToAdd.length > 10) {
            handleError("单次最多允许 10 个 URL");
            setUploading(false);
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/urls/add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getHeaders()
                },
                body: JSON.stringify({
                    dataset_id: selectedDataset.dataset_id,
                    urls: urlsToAdd,
                    update_interval: 24
                })
            });
            if (!res.ok) throw await res.json();
            handleSuccess(`${urlsToAdd.length} 个 URL 添加成功`);
            setUrlInput('');
            fetchFiles(selectedDataset.dataset_id);
        } catch (err) {
            handleError(err);
        } finally {
            setUploading(false);
        }
    };

    // Initial load
    useEffect(() => {
        if (token && spaceId && !showConfig) {
            fetchDatasets();
        }
    }, []);

    return (
        <div className="min-h-screen pt-24 pb-12 px-4 md:px-8 text-white">
            {/* Header */}
            <div className="max-w-7xl mx-auto flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <button onClick={() => navigate('/')} className="p-2 hover:bg-white/10 rounded-full transition">
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-pink-500 bg-clip-text text-transparent">
                            知识库管理
                        </h1>
                        <p className="text-gray-400 text-sm mt-1">Coze Knowledge Base Management</p>
                    </div>
                </div>

                <Button variant="secondary" onClick={() => setShowConfig(!showConfig)}>
                    <Settings size={18} />
                    {showConfig ? '关闭设置' : '设置'}
                </Button>
            </div>

            {/* Error/Success Toasts */}
            {error && (
                <div className="fixed top-24 right-8 z-50 bg-red-500/90 text-white px-6 py-3 rounded-lg shadow-xl flex items-center gap-3 animate-slideIn">
                    <AlertCircle size={20} /> {error}
                </div>
            )}
            {success && (
                <div className="fixed top-24 right-8 z-50 bg-green-500/90 text-white px-6 py-3 rounded-lg shadow-xl flex items-center gap-3 animate-slideIn">
                    <Check size={20} /> {success}
                </div>
            )}

            <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* Configuration Panel */}
                {showConfig && (
                    <div className="lg:col-span-12">
                        <Card className="animate-fadeIn">
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Settings className="text-orange-400" /> API 配置
                            </h2>
                            <div className="grid md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Coze API Token</label>
                                    <Input
                                        type="password"
                                        value={token}
                                        onChange={e => setToken(e.target.value)}
                                        placeholder="pat_..."
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Space ID</label>
                                    <Input
                                        value={spaceId}
                                        onChange={e => setSpaceId(e.target.value)}
                                        placeholder="743..."
                                    />
                                </div>
                            </div>
                            <div className="mt-6 flex justify-end">
                                <Button onClick={fetchDatasets} disabled={loading}>
                                    {loading ? <RefreshCw className="animate-spin" /> : <RefreshCw />}
                                    保存并连接
                                </Button>
                            </div>
                        </Card>
                    </div>
                )}

                {/* Main Content Area */}
                {selectedDataset ? (
                    // File List & Upload Area
                    <div className="lg:col-span-12 space-y-6 animate-fadeIn">
                        <div className="flex items-center gap-3 text-gray-400 mb-2">
                            <span
                                onClick={() => setSelectedDataset(null)}
                                className="cursor-pointer hover:text-orange-400 transition"
                            >
                                知识库列表
                            </span>
                            <span>/</span>
                            <span className="text-white font-medium">{selectedDataset.name}</span>
                        </div>

                        <div className="grid lg:grid-cols-3 gap-6">
                            {/* Left: Upload Tools */}
                            <div className="lg:col-span-1 space-y-6">
                                <Card>
                                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                                        <Upload className="text-blue-400" size={20} /> 上传文件
                                    </h3>
                                    <div className="border-2 border-dashed border-white/10 rounded-lg p-6 text-center hover:border-orange-500/50 transition">
                                        <input
                                            type="file"
                                            id="file-upload"
                                            className="hidden"
                                            multiple
                                            onChange={e => {
                                                if (e.target.files && e.target.files.length > 10) {
                                                    setError("单次最多允许 10 个文件");
                                                    e.target.value = "";
                                                    setFileInput(null);
                                                } else {
                                                    setFileInput(e.target.files);
                                                }
                                            }}
                                        />
                                        <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-2">
                                            {fileInput && fileInput.length > 0 ? (
                                                <div className="text-center">
                                                    <FileText className="text-orange-500 w-10 h-10 mx-auto" />
                                                    <span className="font-bold text-white">已选择 {fileInput.length} 个文件</span>
                                                </div>
                                            ) : (
                                                <FolderOpen className="text-gray-500 w-10 h-10" />
                                            )}
                                            <span className="text-sm text-gray-300">
                                                {fileInput && fileInput.length > 0 ?
                                                    Array.from(fileInput).map(f => f.name).slice(0, 3).join(', ') + (fileInput.length > 3 ? '...' : '')
                                                    : "点击选择文件（最多 10 个）"}
                                            </span>
                                        </label>
                                    </div>
                                    <div className="mt-4">
                                        <Button
                                            onClick={handleUpload}
                                            disabled={!fileInput || uploading}
                                            className="w-full justify-center"
                                        >
                                            {uploading ? '上传中...' : '上传选中文件'}
                                        </Button>
                                    </div>
                                </Card>

                                <Card>
                                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                                        <Link className="text-green-400" size={20} /> 添加 URL
                                    </h3>
                                    <div className="space-y-3">
                                        <textarea
                                            placeholder={`https://example.com | My Page\nhttps://google.com | Search`}
                                            value={urlInput}
                                            onChange={e => setUrlInput(e.target.value)}
                                            rows={5}
                                            className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50 transition-all resize-none text-xs font-mono"
                                        />
                                        <div className="text-xs text-gray-500">
                                            格式：URL | 名称 (可选)。每行一个。最多 10 个。
                                        </div>
                                        <Button
                                            onClick={handleAddUrl}
                                            disabled={!urlInput || uploading}
                                            className="w-full justify-center"
                                        >
                                            {uploading ? '添加中...' : '添加 URL'}
                                        </Button>
                                    </div>
                                </Card>
                            </div>

                            {/* Right: File List */}
                            <div className="lg:col-span-2">
                                <Card className="h-full min-h-[500px]">
                                    <div className="flex justify-between items-center mb-6">
                                        <h3 className="font-semibold text-lg">文档列表 ({files.length})</h3>
                                        <Button variant="ghost" onClick={() => fetchFiles(selectedDataset.dataset_id)}>
                                            <RefreshCw size={16} />
                                        </Button>
                                    </div>

                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left text-sm text-gray-300">
                                            <thead className="text-gray-500 border-b border-white/10">
                                                <tr>
                                                    <th className="pb-3 pl-2">名称</th>
                                                    <th className="pb-3 hidden md:table-cell">类型</th>
                                                    <th className="pb-3 hidden md:table-cell">大小</th>
                                                    <th className="pb-3">状态</th>
                                                    <th className="pb-3 hidden md:table-cell">更新时间</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5">
                                                {loading ? (
                                                    <tr><td colSpan={5} className="py-8 text-center text-gray-500">加载文件中...</td></tr>
                                                ) : files.length === 0 ? (
                                                    <tr><td colSpan={5} className="py-8 text-center text-gray-500">暂无文件</td></tr>
                                                ) : (
                                                    files.map((f) => (
                                                        <tr key={f.document_id} className="hover:bg-white/5 transition-colors group">
                                                            <td className="py-3 pl-2 font-medium text-white flex items-center gap-2">
                                                                <FileText size={16} className="text-orange-400 flex-shrink-0" />
                                                                <span className="truncate max-w-[150px] md:max-w-[200px]" title={f.name}>{f.name}</span>
                                                            </td>
                                                            <td className="py-3 hidden md:table-cell">{f.type || 'N/A'}</td>
                                                            <td className="py-3 hidden md:table-cell">{(f.size / 1024).toFixed(1)} KB</td>
                                                            <td className="py-3">
                                                                <span className={`px-2 py-0.5 rounded text-xs ${f.status === 1 ? 'bg-green-500/20 text-green-300' :
                                                                    f.status === 0 ? 'bg-blue-500/20 text-blue-300' : 'bg-red-500/20 text-red-300'
                                                                    }`}>
                                                                    {f.status === 1 ? '就绪' : f.status === 0 ? '处理中' : '失败'}
                                                                </span>
                                                            </td>
                                                            <td className="py-3 hidden md:table-cell">
                                                                {new Date(f.update_time * 1000).toLocaleDateString()}
                                                            </td>
                                                        </tr>
                                                    ))
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </Card>
                            </div>
                        </div>
                    </div>
                ) : (
                    // Dataset Grid
                    <div className="lg:col-span-12">
                        {/* Empty State / Loading */}
                        {loading && datasets.length === 0 && (
                            <div className="text-center py-20 text-gray-500">
                                <RefreshCw className="mx-auto w-10 h-10 animate-spin mb-4 text-orange-500/50" />
                                加载知识库中...
                            </div>
                        )}

                        {!loading && datasets.length === 0 && (
                            <div className="text-center py-20 text-gray-500">
                                <Database className="mx-auto w-12 h-12 mb-4 opacity-50" />
                                <p>未找到知识库</p>
                                <p className="text-sm mt-2">请检查您的 API Token 和 Space ID 配置</p>
                            </div>
                        )}

                        {/* Grid */}
                        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 animate-stagger">
                            {datasets.map((ds) => (
                                <Card key={ds.dataset_id} className="hover:border-orange-500/50 transition duration-300 group cursor-pointer relative overflow-hidden">
                                    <div
                                        className="absolute inset-0 bg-gradient-to-br from-orange-500/10 to-transparent opacity-0 group-hover:opacity-100 transition duration-500"
                                        onClick={() => handleDatasetSelect(ds)}
                                    />
                                    <div className="relative z-10 pointer-events-none">
                                        <div className="flex justify-between items-start mb-4">
                                            <div className="p-3 bg-white/5 rounded-lg group-hover:bg-orange-500/20 transition-colors">
                                                <Database className="text-orange-400" size={24} />
                                            </div>
                                            <span className={`px-2 py-1 rounded text-xs ${ds.status === 1 ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                                                {ds.status === 1 ? '正常' : '不可用'}
                                            </span>
                                        </div>
                                        <h3 className="text-xl font-bold mb-2 group-hover:text-orange-400 transition-colors">{ds.name}</h3>
                                        <p className="text-gray-400 text-sm line-clamp-2 h-10 mb-6">{ds.description || "暂无描述"}</p>

                                        <div className="grid grid-cols-2 gap-4 border-t border-white/5 pt-4">
                                            <div>
                                                <p className="text-xs text-gray-500 uppercase tracking-wider">文档数</p>
                                                <p className="text-lg font-mono">{ds.doc_count}</p>
                                            </div>
                                            <div>
                                                <p className="text-xs text-gray-500 uppercase tracking-wider">命中数</p>
                                                <p className="text-lg font-mono">{ds.hit_count}</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="absolute top-4 right-4 z-20">
                                        <button
                                            className="p-2 hover:bg-white/10 rounded-full opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto"
                                            onClick={(e) => { e.stopPropagation(); handleDatasetSelect(ds); }}
                                        >
                                            <ArrowRight size={20} />
                                        </button>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default KnowledgeBaseManager;
