import React, { useState } from 'react';
import { Download, ExternalLink, Trash2, AlertTriangle, RefreshCw, CheckCircle2, Save } from 'lucide-react';
import type { PipelineResult } from '../types';

interface ExportCenterProps {
  result?: PipelineResult | null;
  onClearData?: () => void;
  onDownloadSession?: () => void;
}

export const ExportCenter: React.FC<ExportCenterProps> = ({ result, onClearData, onDownloadSession }) => {
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [clearStatus, setClearStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const deliverables = [
    {
      type: 'session',
      title: 'B2S Session Workspace',
      ext: '.b2s',
      desc: 'Portable offline session. Re-open anytime in B2S to review, play, or edit. Zero backend storage.',
      badge: 'Client Session',
      isSession: true
    },
    {
      type: 'vtt',
      title: 'Bengali Closed Captions',
      ext: '.vtt',
      desc: 'Broadcast-compliant WebVTT format with speaker attribution tags [SPEAKER_XX].',
      badge: 'Bengali Source'
    },
    {
      type: 'srt_hi',
      title: 'Hindi Subtitles',
      ext: '.srt',
      desc: 'SubRip subtitle track in standard Devanagari script (हिन्दी) synchronized with Bengali speech.',
      badge: 'Hindi (Devanagari)'
    },
    {
      type: 'srt_bn_rom',
      title: 'Romanized Bengali Subtitles',
      ext: '.srt',
      desc: 'Phonetic Romanized Bengali subtitles (Banglish in Latin script) for global streaming & OTT viewers.',
      badge: 'Banglish (Latin)'
    },
    {
      type: 'srt_hi_rom',
      title: 'Romanized Hindi Subtitles',
      ext: '.srt',
      desc: 'Phonetic Romanized Hindi subtitles (Hinglish in Latin script) for non-Devanagari readers.',
      badge: 'Hinglish (Latin)'
    },
    {
      type: 'srt_en',
      title: 'English Subtitles',
      ext: '.srt',
      desc: 'SubRip subtitle track translated into idiomatic English with conversational context preservation.',
      badge: 'English'
    },
    {
      type: 'bundle',
      title: 'Complete Subtitle & QC Bundle',
      ext: '.zip',
      desc: 'All 5 subtitle tracks (.vtt, .srt) and QC audit reports packaged in a single production delivery archive.',
      badge: 'Full Delivery ZIP'
    },
    {
      type: 'qc_json',
      title: 'QC Machine Report',
      ext: '.json',
      desc: 'Complete automated QC evidence, risk scores, speech overlap, and flags.',
      badge: 'JSON API'
    },
    {
      type: 'qc_html',
      title: 'QC Interactive Dashboard',
      ext: '.html',
      desc: 'Standalone, human-readable HTML audit report for compliance teams.',
      badge: 'HTML Report'
    }
  ];

  const handleClearMemory = async () => {
    const confirm = window.confirm(
      "Are you sure you want to permanently delete ALL backend data?\n\n" +
      "This will:\n" +
      "• Delete all generated subtitle outputs (.vtt, .srt)\n" +
      "• Delete all QC audit reports (.json, .html)\n" +
      "• Delete all intermediate ML artifacts & ASR caches\n" +
      "• Delete uploaded video files\n" +
      "• Reset all in-memory pipeline queue and state\n\n" +
      "Press OK to completely clear memory."
    );
    if (!confirm) return;

    setIsClearing(true);
    setClearStatus(null);

    try {
      const res = await fetch('/api/clear', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setClearStatus({
          type: 'success',
          msg: data.message || 'All backend data, artifacts, uploads, and in-memory cache have been completely cleared.'
        });
        if (onClearData) {
          onClearData();
        }
      } else {
        setClearStatus({
          type: 'error',
          msg: data.detail || 'Failed to clear backend data.'
        });
      }
    } catch (err: any) {
      setClearStatus({
        type: 'error',
        msg: err?.message || 'Network error while attempting to clear backend memory.'
      });
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-display)', color: '#ffffff' }}>
          Shippable Subtitle Deliverables & Reports
        </h2>
        <div style={{ fontSize: '13px', color: 'var(--text-dim)', marginTop: '4px' }}>
          Production-ready subtitle files, client-side session downloads, and pipeline memory management
        </div>
      </div>

      {result ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
          {deliverables.map(deliv => (
            <div key={deliv.type} className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      width: '38px',
                      height: '38px',
                      borderRadius: '8px',
                      background: deliv.isSession ? 'rgba(225, 29, 72, 0.25)' : 'rgba(244, 63, 94, 0.15)',
                      color: '#fda4af',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      fontSize: '12px',
                      border: '1px solid rgba(244, 63, 94, 0.3)'
                    }}>
                      {deliv.isSession ? <Save size={16} /> : deliv.ext}
                    </div>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff' }}>{deliv.title}</h3>
                      <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Format: {deliv.ext.toUpperCase()}</span>
                    </div>
                  </div>
                  <span className="badge badge-low" style={{ fontSize: '10px' }}>{deliv.badge}</span>
                </div>

                <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: '1.5', marginBottom: '20px' }}>
                  {deliv.desc}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                {deliv.isSession ? (
                  <button
                    type="button"
                    onClick={onDownloadSession}
                    className="btn-primary"
                    style={{ flex: 1, justifyContent: 'center', padding: '10px 14px' }}
                  >
                    <Save size={14} />
                    Download {deliv.ext}
                  </button>
                ) : (
                  <a
                    href={`/api/export/${deliv.type}`}
                    download
                    className="btn-primary"
                    style={{ flex: 1, justifyContent: 'center', textDecoration: 'none', padding: '10px 14px' }}
                  >
                    <Download size={14} />
                    Download {deliv.ext}
                  </a>
                )}

                {deliv.type === 'qc_html' && (
                  <a
                    href={`/api/export/${deliv.type}`}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary"
                    style={{ textDecoration: 'none', padding: '10px 14px' }}
                    title="Open HTML report in new tab"
                  >
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '36px 20px' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            No deliverables generated yet. Run the pipeline in Pipeline Studio or open a saved session to inspect files.
          </p>
        </div>
      )}

      {/* Danger Zone: Full Backend Memory & Storage Purge */}
      <div style={{
        padding: '22px 24px',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid rgba(225, 29, 72, 0.35)',
        background: 'linear-gradient(135deg, rgba(225, 29, 72, 0.08) 0%, rgba(20, 3, 7, 0.8) 100%)',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', maxWidth: '650px' }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'rgba(225, 29, 72, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fda4af',
              flexShrink: 0
            }}>
              <Trash2 size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#fda4af' }}>
                Full Clear Memory & Purge Backend Data
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-dim)', marginTop: '3px', lineHeight: '1.4' }}>
                Wipes all generated subtitle deliverables (.vtt, .srt, .json, .html), ML artifacts (audio, VAD, shot cache), uploaded video files, and flushes in-memory pipeline state. Use this to start completely fresh.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClearMemory}
            disabled={isClearing}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: isClearing ? 'rgba(225, 29, 72, 0.25)' : 'rgba(225, 29, 72, 0.15)',
              border: '1px solid #e11d48',
              color: '#fda4af',
              padding: '11px 20px',
              borderRadius: 'var(--radius-md)',
              fontWeight: 700,
              fontSize: '13px',
              cursor: isClearing ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {isClearing ? (
              <>
                <RefreshCw size={14} className="spin" />
                Purging Backend Data...
              </>
            ) : (
              <>
                <Trash2 size={14} />
                Full Clear Memory
              </>
            )}
          </button>
        </div>

        {clearStatus && (
          <div style={{
            fontSize: '13px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            background: clearStatus.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(225, 29, 72, 0.15)',
            border: `1px solid ${clearStatus.type === 'success' ? '#10b981' : '#e11d48'}`,
            color: clearStatus.type === 'success' ? '#34d399' : '#fda4af',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {clearStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            {clearStatus.msg}
          </div>
        )}
      </div>
    </div>
  );
};
