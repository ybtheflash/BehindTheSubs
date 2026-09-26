import React, { useState } from 'react';
import {
  AlertTriangle,
  Play,
  Check,
  Edit2,
  Save,
  X,
  VolumeX,
  Sparkles,
  Clock,
  Gauge
} from 'lucide-react';
import type { CueQC } from '../types';

interface QCReviewQueueProps {
  queue: CueQC[];
  onSeekVideo: (timestampSeconds: number) => void;
  onUpdateCue: (cueIndex: number, text: string, speaker: string, en?: string, hi?: string, action?: string) => void;
}

export const QCReviewQueue: React.FC<QCReviewQueueProps> = ({
  queue,
  onSeekVideo,
  onUpdateCue
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState<string>('');
  const [editSpeaker, setEditSpeaker] = useState<string>('');
  const [editEn, setEditEn] = useState<string>('');
  const [editHi, setEditHi] = useState<string>('');

  const handleStartEdit = (cue: CueQC) => {
    setEditingIndex(cue.cue_index);
    setEditText(cue.text);
    setEditSpeaker(cue.speaker);
    setEditEn(cue.translations?.en || '');
    setEditHi(cue.translations?.hi || '');
  };

  const handleSaveEdit = (cueIndex: number) => {
    onUpdateCue(cueIndex, editText, editSpeaker, editEn, editHi, 'edited');
    setEditingIndex(null);
  };

  const handleAccept = (cueIndex: number) => {
    onUpdateCue(cueIndex, '', '', undefined, undefined, 'accept');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-display)', color: '#ffffff' }}>
            Ranked Human Review Queue
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-dim)', marginTop: '2px' }}>
            Flagged cues prioritized by risk severity (Hallucinations, Low ASR Confidence, Speaker Mismatch, CPS)
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <span className="badge badge-high">{queue.filter(c => c.review_priority >= 0.65).length} High Priority</span>
          <span className="badge badge-med">{queue.filter(c => c.review_priority >= 0.35 && c.review_priority < 0.65).length} Review Advised</span>
        </div>
      </div>

      {queue.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <Check size={40} style={{ color: '#10b981', margin: '0 auto 12px auto' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff' }}>Review Queue Clean!</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '6px' }}>
            All subtitle cues meet speech overlap, CPS, and speaker continuity standards.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {queue.map(cue => {
            const isEditing = editingIndex === cue.cue_index;
            const isHigh = cue.review_priority >= 0.65;
            const priorityPct = Math.round(cue.review_priority * 100);

            return (
              <div
                key={cue.cue_index}
                className="glass-panel"
                style={{
                  padding: '20px',
                  borderLeft: isHigh ? '4px solid #ef4444' : '4px solid #f59e0b',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
                  {/* Cue Identifier & Timestamp Jump */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '16px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#ffffff' }}>
                      Cue #{cue.cue_index}
                    </span>
                    <button
                      className="btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                      onClick={() => onSeekVideo(cue.start)}
                      title="Jump to video timestamp"
                    >
                      <Play size={12} fill="currentColor" />
                      {cue.start.toFixed(2)}s – {cue.end.toFixed(2)}s
                    </button>
                    <span className="speaker-pill">{cue.speaker}</span>
                  </div>

                  {/* Priority Badge & Quick Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={`badge ${isHigh ? 'badge-high' : 'badge-med'}`}>
                      <AlertTriangle size={13} />
                      {isHigh ? 'HIGH RISK' : 'REVIEW'} ({priorityPct}%)
                    </span>

                    {!isEditing && (
                      <>
                        <button
                          className="btn-secondary"
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                          onClick={() => handleStartEdit(cue)}
                        >
                          <Edit2 size={13} />
                          Edit
                        </button>
                        <button
                          className="btn-primary"
                          style={{ padding: '6px 12px', fontSize: '12px', background: '#10b981' }}
                          onClick={() => handleAccept(cue.cue_index)}
                        >
                          <Check size={13} />
                          Accept
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Subtitle Dialogue / Editing Form */}
                {isEditing ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
                    <div className="edit-cue-grid-1">
                      <input
                        type="text"
                        value={editText}
                        onChange={e => setEditText(e.target.value)}
                        placeholder="Bengali text"
                        style={{
                          background: 'var(--bg-input)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '8px 12px',
                          color: '#ffffff',
                          fontSize: '15px'
                        }}
                      />
                      <input
                        type="text"
                        value={editSpeaker}
                        onChange={e => setEditSpeaker(e.target.value)}
                        placeholder="Speaker ID"
                        style={{
                          background: 'var(--bg-input)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '8px 12px',
                          color: '#fda4af',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '13px'
                        }}
                      />
                    </div>
                    <div className="edit-cue-grid-2">
                      <input
                        type="text"
                        value={editEn}
                        onChange={e => setEditEn(e.target.value)}
                        placeholder="English translation"
                        style={{
                          background: 'var(--bg-input)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '6px 10px',
                          color: 'var(--text-muted)',
                          fontSize: '13px'
                        }}
                      />
                      <input
                        type="text"
                        value={editHi}
                        onChange={e => setEditHi(e.target.value)}
                        placeholder="Hindi translation"
                        style={{
                          background: 'var(--bg-input)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '6px 10px',
                          color: 'var(--text-muted)',
                          fontSize: '13px'
                        }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '6px' }}>
                      <button className="btn-secondary" style={{ padding: '5px 12px', fontSize: '12px' }} onClick={() => setEditingIndex(null)}>
                        <X size={13} /> Cancel
                      </button>
                      <button className="btn-primary" style={{ padding: '5px 12px', fontSize: '12px' }} onClick={() => handleSaveEdit(cue.cue_index)}>
                        <Save size={13} /> Save Changes
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.25)',
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    marginBottom: '14px',
                    border: '1px solid rgba(255, 255, 255, 0.04)'
                  }}>
                    <div style={{ fontSize: '16px', fontWeight: 600, color: '#ffffff', lineHeight: '1.4' }}>
                      {cue.text}
                    </div>
                    {(cue.translations?.en || cue.translations?.hi) && (
                      <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '13px', color: 'var(--text-dim)' }}>
                        {cue.translations?.en && <div><b style={{ color: '#94a3b8' }}>EN:</b> {cue.translations.en}</div>}
                        {cue.translations?.hi && <div><b style={{ color: '#94a3b8' }}>HI:</b> {cue.translations.hi}</div>}
                      </div>
                    )}
                  </div>
                )}

                {/* Evidence Metrics Breakdown Cards */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '8px',
                  marginBottom: '12px'
                }}>
                  <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <VolumeX size={12} /> Speech Overlap
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: cue.speech_overlap < 0.35 ? '#ef4444' : '#10b981' }}>
                      {Math.round(cue.speech_overlap * 100)}%
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Sparkles size={12} /> ASR Confidence
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: cue.asr_confidence < 0.60 ? '#f59e0b' : '#10b981' }}>
                      {Math.round(cue.asr_confidence * 100)}%
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Gauge size={12} /> Reading Speed
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: cue.cps > 17 ? '#ef4444' : '#94a3b8' }}>
                      {cue.cps} CPS
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} /> Duration
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#94a3b8' }}>
                      {(cue.end - cue.start).toFixed(2)}s
                    </div>
                  </div>
                </div>

                {/* Flags and Evidence Log */}
                {cue.flags && cue.flags.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {cue.flags.map((flag, idx) => (
                      <div
                        key={idx}
                        style={{
                          fontSize: '12px',
                          color: flag.severity === 'HIGH' ? '#fca5a5' : '#fde68a',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <span style={{
                          fontWeight: 700,
                          fontSize: '10px',
                          padding: '1px 5px',
                          borderRadius: '4px',
                          background: flag.severity === 'HIGH' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)'
                        }}>
                          {flag.severity}
                        </span>
                        <span>{flag.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
