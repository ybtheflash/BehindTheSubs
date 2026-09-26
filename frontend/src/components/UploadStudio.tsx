import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  Play,
  Film,
  Globe2,
  ShieldCheck,
  Sparkles,
  Key,
  Radio
} from 'lucide-react';
import type { ASRConfig, AIHealthStatus } from '../types';

interface UploadStudioProps {
  onStartPipeline: (
    videoPath: string,
    languages: string[],
    useCache: boolean,
    asrProvider: 'bengali_xlsr' | 'bengali_whisper' | 'gemini',
    asrApiKey?: string
  ) => void;
  isProcessing: boolean;
  onProviderChange?: (provider: 'bengali_xlsr' | 'bengali_whisper' | 'gemini') => void;
  onUploadSession?: (file: File) => void;
  aiHealth?: AIHealthStatus | null;
  onRefreshAi?: () => void;
}

export const UploadStudio: React.FC<UploadStudioProps> = ({
  onStartPipeline,
  isProcessing,
  onProviderChange,
  onUploadSession,
  aiHealth,
  onRefreshAi
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedPath, setUploadedPath] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [samples, setSamples] = useState<Array<{ name: string; path: string; size_mb: number }>>([]);
  const [selectedSample, setSelectedSample] = useState<string>('');
  const [translateEn, setTranslateEn] = useState<boolean>(true);
  const [translateHi, setTranslateHi] = useState<boolean>(true);
  const [translateBnRom, setTranslateBnRom] = useState<boolean>(true);
  const [translateHiRom, setTranslateHiRom] = useState<boolean>(true);
  const [useCache, setUseCache] = useState<boolean>(true);

  // ASR Engine State (Simplified, no local whisper options)
  const [asrConfig, setAsrConfig] = useState<ASRConfig | null>(null);
  const [asrProvider, setAsrProvider] = useState<'bengali_xlsr' | 'bengali_whisper' | 'gemini'>('bengali_xlsr');
  const [selectedGeminiKeyId, setSelectedGeminiKeyId] = useState<string>('auto');
  const [customGeminiApiKey, setCustomGeminiApiKey] = useState<string>('');

  // Fetch samples and ASR config on mount
  useEffect(() => {
    fetch('/api/samples')
      .then(res => res.json())
      .then(data => {
        if (data.samples && data.samples.length > 0) {
          setSamples(data.samples);
          setSelectedSample(data.samples[0].path);
        }
      })
      .catch(err => console.log('No preloaded samples found:', err));

    fetch('/api/config/asr')
      .then(res => res.json())
      .then((cfg: ASRConfig) => {
        setAsrConfig(cfg);
        if (cfg.default_provider) {
          const prov = (cfg.default_provider === 'bengali_whisper' || cfg.default_provider === 'gemini')
            ? cfg.default_provider
            : 'bengali_xlsr';
          setAsrProvider(prov as any);
          if (onProviderChange) onProviderChange(prov as any);
        }
      })
      .catch(err => console.log('Could not load ASR config:', err));
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setSelectedFile(file);
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.saved_path) {
        setUploadedPath(data.saved_path);
        setSelectedSample('');
      }
    } catch (err) {
      console.error('File upload failed:', err);
      alert('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleProviderSwitch = (provider: 'bengali_xlsr' | 'bengali_whisper' | 'gemini') => {
    setAsrProvider(provider);
    if (onProviderChange) onProviderChange(provider);
  };

  const handleStart = () => {
    const videoToRun = uploadedPath || selectedSample;
    if (!videoToRun) {
      alert('Please upload a video or select a sample clip to process.');
      return;
    }

    const languages: string[] = [];
    if (translateHi) languages.push('hi');
    if (translateBnRom) languages.push('bn_rom');
    if (translateHiRom) languages.push('hi_rom');
    if (translateEn) languages.push('en');

    let keyToSend: string | undefined = undefined;
    if (asrProvider === 'gemini') {
      if (selectedGeminiKeyId === 'custom') {
        keyToSend = customGeminiApiKey.trim();
      } else if (selectedGeminiKeyId !== 'auto' && asrConfig?.gemini_keys) {
        const found = asrConfig.gemini_keys.find(k => k.id === selectedGeminiKeyId);
        if (found) keyToSend = found.value;
      }
    }

    onStartPipeline(videoToRun, languages, useCache, asrProvider, keyToSend);
  };

  const activeVideo = uploadedPath
    ? (selectedFile?.name || 'Uploaded Video')
    : (samples.find(s => s.path === selectedSample)?.name || 'None');

  const geminiKeyCount = asrConfig?.gemini_keys?.length || 0;

  return (
    <div className="two-col-grid">
      {/* Left Column: Upload, Sessions & Sample Selection */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Video Upload Card */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <Film style={{ color: '#fda4af' }} size={20} />
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#ffffff' }}>Upload Bengali Video Asset</h2>
          </div>

          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '18px' }}>
            Accepts Bengali broadcast footage, web series clips, or film scenes (.mp4, .mkv, .mov).
          </p>

          <label style={{
            border: '2px dashed var(--border-active)',
            borderRadius: 'var(--radius-lg)',
            padding: '32px 24px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            background: 'rgba(20, 3, 7, 0.7)',
            transition: 'all 0.2s ease',
            gap: '12px'
          }}>
            <input
              type="file"
              accept="video/*,audio/*"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
              disabled={isUploading || isProcessing}
            />
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '50%',
              background: 'rgba(244, 63, 94, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fda4af',
              boxShadow: '0 0 16px rgba(225, 29, 72, 0.3)'
            }}>
              <UploadCloud size={26} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '15px', color: '#ffffff' }}>
                {isUploading ? 'Uploading video to pipeline...' : (selectedFile ? selectedFile.name : 'Choose a video file or drop it here')}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                MP4, MKV, MOV, WAV • Up to 2GB
              </div>
            </div>
          </label>
        </div>

        {/* Open Saved Session (.b2s / .json) - Zero Backend Storage */}
        <div className="glass-panel" style={{
          border: '1px solid rgba(244, 63, 94, 0.3)',
          background: 'linear-gradient(135deg, rgba(20, 3, 7, 0.85) 0%, rgba(30, 5, 10, 0.85) 100%)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <UploadCloud style={{ color: '#fda4af' }} size={18} />
              <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#ffffff' }}>Open Saved Session</h3>
            </div>
            <span style={{ fontSize: '10px', background: 'rgba(244, 63, 94, 0.2)', color: '#fda4af', padding: '2px 8px', borderRadius: '9999px', fontWeight: 700 }}>
              Zero Backend Storage
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '12px', lineHeight: '1.4' }}>
            Upload a previously downloaded <code>.b2s</code> or <code>.json</code> session file to restore all cues, translations, speaker diarization, and QC metrics directly in your browser.
          </p>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px dashed var(--border-active)',
            cursor: 'pointer',
            color: '#ffffff',
            fontSize: '13px',
            fontWeight: 600,
            transition: 'all 0.15s ease'
          }}>
            <input
              type="file"
              accept=".b2s,.json"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0 && onUploadSession) {
                  onUploadSession(e.target.files[0]);
                  e.target.value = '';
                }
              }}
            />
            <UploadCloud size={16} style={{ color: '#fda4af' }} />
            <span>Browse or Drop .b2s / .json Session File</span>
          </label>
        </div>

        {/* Pre-loaded Benchmark Clips */}
        {samples.length > 0 && (
          <div className="glass-panel">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <Sparkles style={{ color: '#f59e0b' }} size={18} />
              <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#ffffff' }}>Or Select a Test Benchmark Clip</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {samples.map(sample => (
                <div
                  key={sample.path}
                  onClick={() => {
                    setSelectedSample(sample.path);
                    setUploadedPath('');
                    setSelectedFile(null);
                  }}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    border: selectedSample === sample.path ? '1px solid #e11d48' : '1px solid var(--border-subtle)',
                    background: selectedSample === sample.path ? 'rgba(225, 29, 72, 0.15)' : 'var(--bg-card)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Film size={16} style={{ color: selectedSample === sample.path ? '#fda4af' : 'var(--text-dim)' }} />
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#ffffff' }}>{sample.name}</span>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                    {sample.size_mb} MB
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right Column: Execution Configuration & ASR Engine Switcher */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <ShieldCheck style={{ color: '#10b981' }} size={20} />
              <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#ffffff' }}>Pipeline Parameters</h2>
            </div>

            {/* Active Target */}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              marginBottom: '18px'
            }}>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Active Target Asset
              </div>
              <div style={{ fontSize: '14px', fontWeight: 700, marginTop: '2px', color: '#ffffff' }}>
                {activeVideo}
              </div>
            </div>

            {/* ASR ENGINE SWITCHER PANEL - Simple 3 Options */}
            <div style={{
              background: 'rgba(225, 29, 72, 0.06)',
              border: '1px solid var(--border-active)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              marginBottom: '20px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Radio size={14} style={{ color: '#fda4af' }} />
                  Speech Recognition (ASR) Engine
                </div>
                <span className="badge badge-low" style={{ fontSize: '10px' }}>Modal + HF Failover</span>
              </div>

              {/* Real-time AI Awake / Sleeping Status Banner for Hackathon Evaluation */}
              {aiHealth && (
                aiHealth.status === 'awake' ? (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.12)',
                    border: '1px solid rgba(16, 185, 129, 0.35)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '9px 12px',
                    marginBottom: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '6px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                      <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
                      <span style={{ fontSize: '12px', fontWeight: 700, color: '#34d399' }}>
                        AI GPU Models Awake & Ready
                      </span>
                    </div>
                    <span style={{ fontSize: '11px', color: '#6ee7b7', fontFamily: 'var(--font-mono)' }}>
                      XLS-R: {aiHealth.modal_xlsr?.latency_ms || 850}ms • Whisper: {aiHealth.modal_whisper?.latency_ms || 900}ms
                    </span>
                  </div>
                ) : (
                  <div style={{
                    background: 'rgba(251, 191, 36, 0.15)',
                    border: '1px solid rgba(251, 191, 36, 0.45)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 12px',
                    marginBottom: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }} className="animate-pulse">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fbbf24', boxShadow: '0 0 8px #fbbf24' }} />
                        <span style={{ fontSize: '12px', fontWeight: 800, color: '#fde68a' }}>
                          AI Server Waking Up (~{aiHealth.estimated_wakeup_seconds || 35}s Cold Start)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={onRefreshAi}
                        style={{ background: 'transparent', border: 'none', color: '#fbbf24', fontSize: '11px', fontWeight: 700, cursor: 'pointer', textDecoration: 'underline' }}
                      >
                        Recheck
                      </button>
                    </div>
                    <div style={{ fontSize: '11px', color: '#fef3c7', lineHeight: '1.4' }}>
                      Modal free-tier GPU instances are waking from sleep. Execution will wait for warm-up or automatically fail over to Hugging Face Spaces.
                    </div>
                  </div>
                )
              )}

              {/* Provider Selection Buttons (3 Simple Options) */}
              <div className="provider-grid">
                {/* 1. Bengali ASR (Primary) */}
                <button
                  type="button"
                  onClick={() => handleProviderSwitch('bengali_xlsr')}
                  style={{
                    padding: '10px 8px',
                    borderRadius: 'var(--radius-sm)',
                    border: asrProvider === 'bengali_xlsr' ? '2px solid #e11d48' : '1px solid var(--border-subtle)',
                    background: asrProvider === 'bengali_xlsr' ? 'rgba(225, 29, 72, 0.22)' : 'var(--bg-card)',
                    color: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, fontSize: '12px' }}>
                    <Sparkles size={13} style={{ color: '#fda4af' }} />
                    Bengali ASR (Primary)
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
                    Modal XLS-R • HF Failover
                  </div>
                </button>

                {/* 2. Regional Bengali ASR */}
                <button
                  type="button"
                  onClick={() => handleProviderSwitch('bengali_whisper')}
                  style={{
                    padding: '10px 8px',
                    borderRadius: 'var(--radius-sm)',
                    border: asrProvider === 'bengali_whisper' ? '2px solid #e11d48' : '1px solid var(--border-subtle)',
                    background: asrProvider === 'bengali_whisper' ? 'rgba(225, 29, 72, 0.22)' : 'var(--bg-card)',
                    color: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, fontSize: '12px' }}>
                    <Sparkles size={13} style={{ color: '#fda4af' }} />
                    Regional Bengali ASR
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
                    Modal Whisper • HF Failover
                  </div>
                </button>

                {/* 3. Gemini Flash */}
                <button
                  type="button"
                  onClick={() => handleProviderSwitch('gemini')}
                  style={{
                    padding: '10px 8px',
                    borderRadius: 'var(--radius-sm)',
                    border: asrProvider === 'gemini' ? '2px solid #e11d48' : '1px solid var(--border-subtle)',
                    background: asrProvider === 'gemini' ? 'rgba(225, 29, 72, 0.22)' : 'var(--bg-card)',
                    color: '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, fontSize: '12px' }}>
                    <Sparkles size={13} style={{ color: '#fda4af' }} />
                    Gemini Flash
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
                    Google Cloud
                  </div>
                </button>
              </div>

              {/* Bengali ASR (Primary) Info Panel */}
              {asrProvider === 'bengali_xlsr' && (
                <div style={{
                  background: 'var(--bg-card)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Sparkles size={12} style={{ color: '#fda4af' }} />
                      Bengali ASR (Primary) • Wav2Vec2
                    </div>
                    <span style={{ fontSize: '10px', background: 'rgba(244, 63, 94, 0.2)', color: '#fda4af', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                      Cloud Endpoint
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                    High-accuracy Bengali acoustic model with direct Wav2Vec2 inference. Automatically extracts 16kHz mono audio before transmission. Fast and verbatim transcription.
                  </div>
                </div>
              )}

              {/* Regional Bengali ASR Info Panel */}
              {asrProvider === 'bengali_whisper' && (
                <div style={{
                  background: 'var(--bg-card)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Sparkles size={12} style={{ color: '#fda4af' }} />
                      Regional Bengali ASR
                    </div>
                    <span style={{ fontSize: '10px', background: 'rgba(244, 63, 94, 0.2)', color: '#fda4af', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                      Cloud Failover
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                    Fine-tuned on diverse regional Bengali accents and conversational speech. Auto-extracts audio and includes automatic cloud failover.
                  </div>
                </div>
              )}

              {/* Gemini Flash API Key Selector & Multi-Key Panel */}
              {asrProvider === 'gemini' && (
                <div style={{
                  background: 'var(--bg-card)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Key size={12} style={{ color: '#fda4af' }} />
                      Gemini API Key Selection:
                    </div>
                    <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 600 }}>
                      {geminiKeyCount} Key{geminiKeyCount === 1 ? '' : 's'} in Pool
                    </span>
                  </div>

                  <select
                    value={selectedGeminiKeyId}
                    onChange={e => setSelectedGeminiKeyId(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '8px 10px',
                      color: '#ffffff',
                      fontSize: '13px',
                      marginBottom: '8px'
                    }}
                  >
                    <option value="auto">
                      🔄 Auto-Rotate Pool ({geminiKeyCount} Key{geminiKeyCount === 1 ? '' : 's'} with Failover)
                    </option>
                    {asrConfig?.gemini_keys?.map(k => (
                      <option key={k.id} value={k.id}>
                        🔑 {k.label}
                      </option>
                    ))}
                    <option value="custom">✍️ Enter Custom / Manual Gemini Key...</option>
                  </select>

                  {/* Manual Gemini Key Input Field */}
                  {selectedGeminiKeyId === 'custom' && (
                    <div style={{ marginTop: '6px' }}>
                      <input
                        type="password"
                        placeholder="Paste Google Gemini API key (AIzaSy...)..."
                        value={customGeminiApiKey}
                        onChange={e => setCustomGeminiApiKey(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'var(--bg-input)',
                          border: '1px solid #e11d48',
                          borderRadius: 'var(--radius-sm)',
                          padding: '8px 10px',
                          color: '#ffffff',
                          fontSize: '13px',
                          fontFamily: 'var(--font-mono)'
                        }}
                      />
                    </div>
                  )}

                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                    Model: <code>gemini-flash-latest</code> • Multimodal Audio Intelligence • Bengali verbatim & code-switching
                  </div>
                </div>
              )}
            </div>

            {/* Subtitle Translation Targets */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Globe2 size={15} style={{ color: '#fda4af' }} />
                Generate Subtitle Tracks:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', cursor: 'pointer', color: '#ffffff' }}>
                  <input type="checkbox" checked disabled style={{ accentColor: '#e11d48' }} />
                  <span>Bengali Closed Captions (.vtt)</span>
                  <span className="badge badge-low" style={{ fontSize: '10px', padding: '1px 6px' }}>Core bn</span>
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', cursor: 'pointer', color: '#ffffff' }}>
                  <input
                    type="checkbox"
                    checked={translateHi}
                    onChange={e => setTranslateHi(e.target.checked)}
                    style={{ accentColor: '#e11d48' }}
                  />
                  <span>Hindi Subtitles (.srt - हिन्दी Devanagari)</span>
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', cursor: 'pointer', color: '#ffffff' }}>
                  <input
                    type="checkbox"
                    checked={translateBnRom}
                    onChange={e => setTranslateBnRom(e.target.checked)}
                    style={{ accentColor: '#e11d48' }}
                  />
                  <span>Romanized Bengali Subtitles (.srt - Banglish Latin)</span>
                  <span className="badge" style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(244, 63, 94, 0.2)', color: '#fda4af' }}>OTT</span>
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', cursor: 'pointer', color: '#ffffff' }}>
                  <input
                    type="checkbox"
                    checked={translateHiRom}
                    onChange={e => setTranslateHiRom(e.target.checked)}
                    style={{ accentColor: '#e11d48' }}
                  />
                  <span>Romanized Hindi Subtitles (.srt - Hinglish Latin)</span>
                  <span className="badge" style={{ fontSize: '10px', padding: '1px 6px', background: 'rgba(244, 63, 94, 0.2)', color: '#fda4af' }}>OTT</span>
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', cursor: 'pointer', color: '#ffffff' }}>
                  <input
                    type="checkbox"
                    checked={translateEn}
                    onChange={e => setTranslateEn(e.target.checked)}
                    style={{ accentColor: '#e11d48' }}
                  />
                  <span>English Subtitles (.srt)</span>
                </label>
              </div>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-dim)', cursor: 'pointer', marginBottom: '16px' }}>
              <input
                type="checkbox"
                checked={useCache}
                onChange={e => setUseCache(e.target.checked)}
                style={{ accentColor: '#e11d48' }}
              />
              <span>Cache intermediate ML outputs in artifacts/</span>
            </label>
          </div>

          <button
            className="btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '14px', fontSize: '15px' }}
            onClick={handleStart}
            disabled={isProcessing || (!uploadedPath && !selectedSample)}
          >
            <Play size={18} fill="currentColor" />
            {isProcessing ? 'Pipeline Running...' : 'Execute B2S Pipeline'}
          </button>
        </div>
      </div>
    </div>
  );
};
