import React, { useRef } from 'react';
import { Layers, CheckCircle2, Video, BarChart3, Download, Sparkles, UploadCloud, Save, Globe, RefreshCw } from 'lucide-react';
import type { AIHealthStatus } from '../types';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  reviewCount: number;
  activeProvider: string;
  hasSession: boolean;
  onDownloadSession: () => void;
  onUploadSession: (file: File) => void;
  aiHealth?: AIHealthStatus | null;
  onRefreshAi?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  reviewCount,
  activeProvider,
  hasSession,
  onDownloadSession,
  onUploadSession,
  aiHealth,
  onRefreshAi
}) => {
  const sessionFileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUploadSession(e.target.files[0]);
      e.target.value = ''; // Reset input so same file can be reloaded
    }
  };

  const getProviderLabel = () => {
    if (activeProvider === 'bengali_xlsr') return 'Bengali ASR (Primary)';
    if (activeProvider === 'bengali_whisper' || activeProvider === 'bengali_ai') return 'Regional Bengali ASR';
    if (activeProvider === 'gemini') return 'Gemini Flash';
    return 'Bengali ASR';
  };

  return (
    <header className="navbar">
      {/* Brand Identity & Tagline */}
      <div className="brand-container" style={{ cursor: 'pointer' }} onClick={() => setActiveTab('studio')}>
        <div className="brand-logo">B2S</div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="brand-title">B2S - Behind The Subs</h1>
            <span style={{
              fontSize: '10px',
              padding: '2px 8px',
              borderRadius: '9999px',
              background: 'rgba(244, 63, 94, 0.15)',
              border: '1px solid rgba(244, 63, 94, 0.35)',
              color: '#fda4af',
              fontWeight: 700,
              letterSpacing: '0.04em'
            }}>
              hoichoi Hackathon'26
            </span>
          </div>
          <div className="brand-tagline">
            Automated Bengali Subtitle & Closed-Caption Pipeline with Speaker Diarization
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${activeTab === 'studio' ? 'active' : ''}`}
          onClick={() => setActiveTab('studio')}
        >
          <Layers size={15} />
          Studio
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'review' ? 'active' : ''}`}
          onClick={() => setActiveTab('review')}
        >
          <CheckCircle2 size={15} />
          Review Queue
          {reviewCount > 0 && (
            <span style={{
              background: '#e11d48',
              color: '#ffffff',
              borderRadius: '9999px',
              padding: '1px 6px',
              fontSize: '10px',
              fontWeight: 800,
              marginLeft: '4px'
            }}>
              {reviewCount}
            </span>
          )}
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'player' ? 'active' : ''}`}
          onClick={() => setActiveTab('player')}
        >
          <Video size={15} />
          Subtitles & Player
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <BarChart3 size={15} />
          QC Analytics
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'exports' ? 'active' : ''}`}
          onClick={() => setActiveTab('exports')}
        >
          <Download size={15} />
          Deliverables
        </button>
      </nav>

      {/* Session Controls, Creator Links & Status */}
      <div className="navbar-controls">
        {/* Creator Profile Links: Website & GitHub */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <a
            href="https://ybtheflash.in"
            target="_blank"
            rel="noreferrer"
            title="Yubaraj Biswas's Website: ybtheflash.in"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              color: '#ffffff',
              padding: '6px 11px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 600,
              textDecoration: 'none',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.6)';
              e.currentTarget.style.background = 'rgba(225, 29, 72, 0.2)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
            }}
          >
            <Globe size={13} style={{ color: '#fda4af' }} />
            <span>ybtheflash.in</span>
          </a>

          <a
            href="https://github.com/ybtheflash"
            target="_blank"
            rel="noreferrer"
            title="GitHub: ybtheflash"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              color: '#ffffff',
              padding: '6px 11px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 600,
              textDecoration: 'none',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.6)';
              e.currentTarget.style.background = 'rgba(225, 29, 72, 0.2)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#fda4af" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
              <path d="M9 18c-4.51 2-5-2-7-2" />
            </svg>
            <span>ybtheflash</span>
          </a>
        </div>

        {/* Vertical Divider */}
        <div style={{ width: '1px', height: '20px', background: 'var(--border-subtle)', margin: '0 2px' }} />

        {/* Hidden File Input for Open Session */}
        <input
          type="file"
          ref={sessionFileInputRef}
          accept=".b2s,.json"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        {/* Open Session Button */}
        <button
          type="button"
          onClick={() => sessionFileInputRef.current?.click()}
          title="Open a previously saved .b2s or .json session (0 backend storage)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            color: '#f3e5e7',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.5)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
        >
          <UploadCloud size={14} style={{ color: '#fda4af' }} />
          Open Session
        </button>

        {/* Save Session Button (Active only when result exists) */}
        {hasSession && (
          <button
            type="button"
            onClick={onDownloadSession}
            title="Download workspace state as a .b2s session file"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)',
              border: 'none',
              color: '#ffffff',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(225, 29, 72, 0.35)',
              transition: 'all 0.15s ease'
            }}
          >
            <Save size={14} />
            Save Session
          </button>
        )}

        {/* AI Awake / Sleeping Status Indicator for Hackathon Judges */}
        {aiHealth && (
          <div
            onClick={onRefreshAi}
            title={
              aiHealth.status === 'awake'
                ? `Modal GPU Online! XLS-R: ${aiHealth.modal_xlsr?.latency_ms || 850}ms • Whisper: ${aiHealth.modal_whisper?.latency_ms || 900}ms. Click to recheck.`
                : `Modal AI container is cold-starting (~20-40s). Click to recheck status.`
            }
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontWeight: 700,
              color: aiHealth.status === 'awake' ? '#34d399' : '#fbbf24',
              background: aiHealth.status === 'awake' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(251, 191, 36, 0.15)',
              border: `1px solid ${aiHealth.status === 'awake' ? 'rgba(16, 185, 129, 0.35)' : 'rgba(251, 191, 36, 0.45)'}`,
              padding: '6px 12px',
              borderRadius: 'var(--radius-full)',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <span style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              background: aiHealth.status === 'awake' ? '#10b981' : '#fbbf24',
              boxShadow: `0 0 8px ${aiHealth.status === 'awake' ? '#10b981' : '#fbbf24'}`
            }} />
            <span>
              {aiHealth.status === 'awake'
                ? 'AI Awake (GPU Warm)'
                : `AI Waking Up (~${aiHealth.estimated_wakeup_seconds || 35}s)`}
            </span>
            <RefreshCw size={10} style={{ opacity: 0.6 }} />
          </div>
        )}

        {/* Active Engine Badge */}
        <div className="server-badge">
          <div className="status-dot"></div>
          <Sparkles size={13} style={{ color: '#fda4af' }} />
          <span>{getProviderLabel()}</span>
        </div>
      </div>
    </header>
  );
};

