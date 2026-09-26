import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  Loader2,
  Volume2,
  Mic,
  Camera,
  Layers,
  Users,
  Languages,
  Sparkles,
  ShieldCheck,
  FileCheck,
  Clock
} from 'lucide-react';
import type { PipelineTaskStatus } from '../types';

interface PipelineProgressProps {
  status: PipelineTaskStatus | null;
  onViewResults: () => void;
}

const STAGES = [
  { id: 'audio', label: 'Audio Extraction', icon: Volume2, detail: 'FFmpeg 16kHz mono normalization' },
  { id: 'vad', label: 'Voice Activity Detection', icon: Mic, detail: 'Silero VAD speech overlap' },
  { id: 'shot', label: 'Scene Boundary Detection', icon: Camera, detail: 'PySceneDetect cuts' },
  { id: 'asr', label: 'Bengali Speech Recognition', icon: Layers, detail: 'Modal Primary GPU • HF Failover' },
  { id: 'align', label: 'Word Timestamp Alignment', icon: Sparkles, detail: 'Precision boundary alignment' },
  { id: 'diarize', label: 'Speaker Diarization', icon: Users, detail: 'pyannote / acoustic clustering' },
  { id: 'merge', label: 'Speaker ↔ Word Merge', icon: Users, detail: 'Attribution reconciliation' },
  { id: 'cues', label: 'Cue Segmentation', icon: Layers, detail: 'CPS, line limits, punctuation' },
  { id: 'translate', label: 'AI Translation', icon: Languages, detail: 'Context-aware EN & HI tracks' },
  { id: 'qc', label: 'AI Quality Control Engine', icon: ShieldCheck, detail: 'Hallucination & risk scoring' },
  { id: 'export', label: 'Asset Export', icon: FileCheck, detail: 'WebVTT, SRT, QC reports' },
];

export const PipelineProgress: React.FC<PipelineProgressProps> = ({ status, onViewResults }) => {
  const [elapsed, setElapsed] = useState<number>(0);

  const currentStage = status?.stage;
  const percent = status?.percent || 0;
  const isComplete = status?.status === 'completed';

  useEffect(() => {
    if (isComplete) return;
    const interval = setInterval(() => {
      setElapsed(e => e + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isComplete]);

  if (!status) return null;

  const getEtaRemaining = () => {
    if (isComplete) return 0;
    if (percent >= 90) return 4;
    if (percent >= 70) return 8;
    if (percent >= 45) return 15;
    if (percent >= 25) return 22;
    return Math.max(10, 38 - elapsed);
  };

  // Determine stage state: 'done', 'active', 'pending'
  const getStageState = (_stageId: string, index: number) => {
    if (isComplete) return 'done';
    const currentIdx = STAGES.findIndex(s => s.id === currentStage);
    if (currentIdx === -1) return 'pending';
    if (index < currentIdx) return 'done';
    if (index === currentIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="two-col-grid">
      {/* Stages Column */}
      <div className="glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-display)' }}>
              {isComplete ? 'Pipeline Execution Complete' : 'Processing Pipeline...'}
            </h2>
            <div style={{ fontSize: '13px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Real-time multi-stage audio & speech processing
            </div>
          </div>
          <div style={{
            fontSize: '24px',
            fontWeight: 800,
            fontFamily: 'var(--font-mono)',
            color: isComplete ? '#10b981' : '#f43f5e'
          }}>
            {percent}%
          </div>
        </div>

        {/* Progress Bar */}
        <div style={{
          width: '100%',
          height: '8px',
          background: 'var(--bg-card)',
          borderRadius: 'var(--radius-full)',
          overflow: 'hidden',
          marginBottom: '28px'
        }}>
          <div style={{
            width: `${percent}%`,
            height: '100%',
            background: isComplete ? '#10b981' : 'var(--primary-gradient)',
            borderRadius: 'var(--radius-full)',
            transition: 'width 0.4s ease'
          }} />
        </div>

        {/* Stage List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {STAGES.map((stg, i) => {
            const state = getStageState(stg.id, i);
            const Icon = stg.icon;

            return (
              <div
                key={stg.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: state === 'active' ? 'rgba(244, 63, 94, 0.12)' : (state === 'done' ? 'rgba(16, 185, 129, 0.05)' : 'transparent'),
                  border: state === 'active' ? '1px solid var(--border-active)' : '1px solid transparent',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: state === 'done' ? 'rgba(16, 185, 129, 0.15)' : (state === 'active' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(255, 255, 255, 0.04)'),
                    color: state === 'done' ? '#10b981' : (state === 'active' ? '#fda4af' : 'var(--text-dim)'),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    {state === 'done' ? (
                      <CheckCircle2 size={16} />
                    ) : state === 'active' ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Icon size={16} />
                    )}
                  </div>
                  <div>
                    <div style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      color: state === 'pending' ? 'var(--text-dim)' : 'var(--text-main)'
                    }}>
                      {stg.label}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                      {stg.detail}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: '12px', fontWeight: 600 }}>
                  {state === 'done' && <span style={{ color: '#10b981' }}>Complete</span>}
                  {state === 'active' && <span style={{ color: '#fda4af' }}>Running...</span>}
                  {state === 'pending' && <span style={{ color: 'var(--text-dim)' }}>Queued</span>}
                </div>
              </div>
            );
          })}
        </div>

        {/* Free-Tier Hackathon Patience Notice & Real-time ETA */}
        {!isComplete && (
          <div style={{
            marginTop: '20px',
            padding: '14px 16px',
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, rgba(225, 29, 72, 0.16) 0%, rgba(20, 3, 7, 0.95) 100%)',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            boxShadow: '0 4px 18px rgba(0, 0, 0, 0.6)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={15} style={{ color: '#fda4af' }} />
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff' }}>
                  hoichoi Hackathon'26 • Free-Tier Cloud Notice
                </span>
              </div>
              <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: '#fda4af', fontWeight: 700 }}>
                Elapsed: {elapsed}s • ETA: ~{getEtaRemaining()}s
              </span>
            </div>
            <p style={{ fontSize: '12px', color: '#f3e5e7', lineHeight: '1.4' }}>
              Please be patient! We are running on free-tier Modal GPU instances with automatic Hugging Face failover. First-time container cold-starts may take 20–40 seconds if waking up from sleep.
            </p>
          </div>
        )}

        {isComplete && (
          <div style={{ marginTop: '24px', textAlign: 'right' }}>
            <button className="btn-primary" onClick={onViewResults}>
              Open Review Queue & QC Dashboard →
            </button>
          </div>
        )}
      </div>

      {/* Real-time Streaming Logs Window */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f43f5e' }}></div>
          <h3 style={{ fontSize: '15px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
            Pipeline Terminal Output
          </h3>
        </div>

        <div style={{
          flex: 1,
          minHeight: '440px',
          maxHeight: '520px',
          background: 'var(--bg-main)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '16px',
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: '#e2e8f0',
          overflowY: 'auto',
          lineHeight: '1.7',
          display: 'flex',
          flexDirection: 'column-reverse'
        }}>
          <div>
            {status.logs.map((log, index) => (
              <div
                key={index}
                style={{
                  color: log.includes('ERROR') ? '#ef4444' : (log.includes('[100%]') || log.includes('completed') ? '#10b981' : '#94a3b8'),
                  marginBottom: '4px'
                }}
              >
                {log}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
