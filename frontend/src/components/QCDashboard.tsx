import React, { useState } from 'react';
import { Users, Search } from 'lucide-react';
import type { PipelineQCReport } from '../types';

interface QCDashboardProps {
  report: PipelineQCReport;
  onSeekVideo: (time: number) => void;
}

export const QCDashboard: React.FC<QCDashboardProps> = ({ report, onSeekVideo }) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterRisk, setFilterRisk] = useState<'ALL' | 'HIGH' | 'MED' | 'LOW'>('ALL');

  const filteredCues = report.cues.filter(c => {
    const matchesSearch = c.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.speaker.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.translations?.en && c.translations.en.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (filterRisk === 'HIGH') return c.review_priority >= 0.65;
    if (filterRisk === 'MED') return c.review_priority >= 0.35 && c.review_priority < 0.65;
    if (filterRisk === 'LOW') return c.review_priority < 0.35;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        <div className="glass-panel" style={{ padding: '18px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Total Subtitle Cues
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, marginTop: '6px', color: '#ffffff' }}>
            {report.total_cues}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '18px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            High Risk (Needs Review)
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, marginTop: '6px', color: '#ef4444' }}>
            {report.high_risk_count}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '18px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Review Recommended
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, marginTop: '6px', color: '#f59e0b' }}>
            {report.medium_risk_count}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '18px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Low Risk (Auto-Accepted)
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, marginTop: '6px', color: '#10b981' }}>
            {report.low_risk_count}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '18px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Average Reading Speed
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, marginTop: '6px', color: '#ffffff' }}>
            {report.avg_cps} <span style={{ fontSize: '14px', color: 'var(--text-dim)', fontWeight: 500 }}>CPS</span>
          </div>
        </div>
      </div>

      {/* Speaker Breakdown Card */}
      <div className="glass-panel" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <Users size={18} style={{ color: '#fda4af' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff' }}>Speaker Turn Distribution</h3>
        </div>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          {Object.entries(report.speaker_distribution || {}).map(([spk, count]) => (
            <div
              key={spk}
              style={{
                background: 'var(--bg-card)',
                padding: '10px 18px',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                border: '1px solid var(--border-subtle)'
              }}
            >
              <span className="speaker-pill">{spk}</span>
              <span style={{ fontSize: '14px', fontWeight: 700 }}>{count} cues</span>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                ({report.total_cues > 0 ? Math.round((count / report.total_cues) * 100) : 0}%)
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="dashboard-filter-bar">
        <div style={{ position: 'relative', flex: 1, maxWidth: '420px' }}>
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input
            type="text"
            placeholder="Search dialogue text or speakers..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-full)',
              padding: '10px 16px 10px 40px',
              color: 'var(--text-main)',
              fontSize: '14px'
            }}
          />
        </div>

        <div style={{ display: 'flex', background: 'var(--bg-card)', padding: '4px', borderRadius: 'var(--radius-full)', gap: '4px', overflowX: 'auto', maxWidth: '100%' }}>
          {(['ALL', 'HIGH', 'MED', 'LOW'] as const).map(filter => (
            <button
              key={filter}
              className={`nav-tab-btn ${filterRisk === filter ? 'active' : ''}`}
              style={{ padding: '6px 14px', fontSize: '12px', whiteSpace: 'nowrap' }}
              onClick={() => setFilterRisk(filter)}
            >
              {filter === 'ALL' ? 'All Cues' : `${filter} Risk`}
            </button>
          ))}
        </div>
      </div>

      {/* Detailed Cue Inspection Table */}
      <div className="glass-panel table-responsive" style={{ padding: '0' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--bg-card)', borderBottom: '1px solid var(--border-subtle)' }}>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>CUE</th>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>TIMESTAMPS</th>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>SPEAKER</th>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>BENGALI TEXT</th>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>RISK PRIORITY</th>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>VAD OVERLAP</th>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>ASR CONF</th>
              <th style={{ padding: '14px 18px', textAlign: 'left', fontSize: '12px', color: 'var(--text-dim)' }}>CPS</th>
            </tr>
          </thead>
          <tbody>
            {filteredCues.map(cue => {
              const isHigh = cue.review_priority >= 0.65;
              const isMed = cue.review_priority >= 0.35 && cue.review_priority < 0.65;
              const priorityPct = Math.round(cue.review_priority * 100);

              return (
                <tr
                  key={cue.cue_index}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    transition: 'background 0.15s ease',
                    cursor: 'pointer'
                  }}
                  onClick={() => onSeekVideo(cue.start)}
                >
                  <td style={{ padding: '14px 18px', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                    #{cue.cue_index}
                  </td>
                  <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-muted)' }}>
                    {cue.start.toFixed(2)}s – {cue.end.toFixed(2)}s
                  </td>
                  <td style={{ padding: '14px 18px' }}>
                    <span className="speaker-pill">{cue.speaker}</span>
                  </td>
                  <td style={{ padding: '14px 18px', fontWeight: 600, maxWidth: '280px', color: '#ffffff' }}>
                    {cue.text}
                  </td>
                  <td style={{ padding: '14px 18px' }}>
                    <span className={`badge ${isHigh ? 'badge-high' : (isMed ? 'badge-med' : 'badge-low')}`}>
                      {isHigh ? 'HIGH' : (isMed ? 'REVIEW' : 'LOW')} ({priorityPct}%)
                    </span>
                  </td>
                  <td style={{ padding: '14px 18px', fontWeight: 700, color: cue.speech_overlap < 0.35 ? '#ef4444' : '#10b981' }}>
                    {Math.round(cue.speech_overlap * 100)}%
                  </td>
                  <td style={{ padding: '14px 18px', fontWeight: 700, color: cue.asr_confidence < 0.60 ? '#f59e0b' : '#10b981' }}>
                    {Math.round(cue.asr_confidence * 100)}%
                  </td>
                  <td style={{ padding: '14px 18px', color: cue.cps > 17 ? '#ef4444' : 'var(--text-muted)' }}>
                    {cue.cps}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
