import React, { useState, useRef, useEffect } from 'react';
import { Play, Subtitles } from 'lucide-react';
import type { SubtitleCue } from '../types';

interface VideoPlayerProps {
  videoUrl: string;
  cues: SubtitleCue[];
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  seekTime: number | null;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  cues,
  currentTime,
  onTimeUpdate,
  seekTime
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [selectedTrack, setSelectedTrack] = useState<'bn' | 'en' | 'hi' | 'bn_rom' | 'hi_rom' | 'none'>('bn');
  const [playbackRate, setPlaybackRate] = useState<number>(1.0);
  const timelineRef = useRef<HTMLDivElement>(null);

  // Jump video when seekTime changes from parent (e.g. clicking Review Queue)
  useEffect(() => {
    if (seekTime !== null && videoRef.current) {
      videoRef.current.currentTime = seekTime;
      videoRef.current.play().catch(() => {});
    }
  }, [seekTime]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  // Find currently active cue
  const activeCue = cues.find(c => currentTime >= c.start && currentTime <= c.end);

  // Auto-scroll timeline to active cue
  useEffect(() => {
    if (activeCue && timelineRef.current) {
      const el = document.getElementById(`cue-item-${activeCue.index}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [activeCue]);

  const getActiveText = () => {
    if (!activeCue || selectedTrack === 'none') return '';
    if (selectedTrack === 'bn') return activeCue.text;
    if (selectedTrack === 'hi') return activeCue.translations?.hi || activeCue.text;
    if (selectedTrack === 'bn_rom') return activeCue.translations?.bn_rom || activeCue.text;
    if (selectedTrack === 'hi_rom') return activeCue.translations?.hi_rom || activeCue.translations?.hi || activeCue.text;
    if (selectedTrack === 'en') return activeCue.translations?.en || activeCue.text;
    return activeCue.text;
  };

  return (
    <div className="player-grid">
      {/* Video & Player Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div className="glass-panel" style={{ padding: '0', overflow: 'hidden', position: 'relative', background: '#000000' }}>
          <video
            ref={videoRef}
            src={videoUrl}
            style={{ width: '100%', height: 'auto', display: 'block', maxHeight: '480px' }}
            onTimeUpdate={handleTimeUpdate}
            controls
          />

          {/* Subtitle Overlay */}
          {activeCue && selectedTrack !== 'none' && (
            <div style={{
              position: 'absolute',
              bottom: '54px',
              left: '50%',
              transform: 'translateX(-50%)',
              textAlign: 'center',
              pointerEvents: 'none',
              width: '90%',
              zIndex: 10
            }}>
              <div style={{
                display: 'inline-block',
                background: 'rgba(0, 0, 0, 0.8)',
                padding: '8px 18px',
                borderRadius: '8px',
                fontSize: '18px',
                fontWeight: 600,
                color: '#ffffff',
                lineHeight: '1.4',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                <span style={{ color: '#fda4af', fontSize: '13px', display: 'block', marginBottom: '2px', fontFamily: 'var(--font-mono)' }}>
                  [{activeCue.speaker}]
                </span>
                {getActiveText()}
              </div>
            </div>
          )}
        </div>

        {/* Subtitle Track Selector & Quick Controls */}
        <div className="glass-panel track-selector-bar" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <Subtitles size={18} style={{ color: '#fda4af' }} />
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>Active Track:</span>
            <div className="track-btn-group">
              <button
                className={`nav-tab-btn ${selectedTrack === 'bn' ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setSelectedTrack('bn')}
              >
                🇧🇩 Bengali
              </button>
              <button
                className={`nav-tab-btn ${selectedTrack === 'hi' ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setSelectedTrack('hi')}
              >
                🇮🇳 Hindi
              </button>
              <button
                className={`nav-tab-btn ${selectedTrack === 'bn_rom' ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setSelectedTrack('bn_rom')}
                title="Romanized Bengali (Banglish in Latin script)"
              >
                🔤 Banglish
              </button>
              <button
                className={`nav-tab-btn ${selectedTrack === 'hi_rom' ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setSelectedTrack('hi_rom')}
                title="Romanized Hindi (Hinglish in Latin script)"
              >
                🔤 Hinglish
              </button>
              <button
                className={`nav-tab-btn ${selectedTrack === 'en' ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setSelectedTrack('en')}
              >
                🇬🇧 English
              </button>
              <button
                className={`nav-tab-btn ${selectedTrack === 'none' ? 'active' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setSelectedTrack('none')}
              >
                Off
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Speed:</span>
            {[0.75, 1.0, 1.25, 1.5].map(rate => (
              <button
                key={rate}
                onClick={() => {
                  setPlaybackRate(rate);
                  if (videoRef.current) videoRef.current.playbackRate = rate;
                }}
                style={{
                  background: playbackRate === rate ? 'rgba(225, 29, 72, 0.25)' : 'transparent',
                  color: playbackRate === rate ? '#fda4af' : 'var(--text-dim)',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                {rate}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Synchronized Side-by-Side Transcript Timeline */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '560px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff' }}>Synchronized Transcript</h3>
          <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            {cues.length} Cues
          </span>
        </div>

        <div
          ref={timelineRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            paddingRight: '6px'
          }}
        >
          {cues.map(cue => {
            const isActive = activeCue?.index === cue.index;

            return (
              <div
                key={cue.index}
                id={`cue-item-${cue.index}`}
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = cue.start;
                    videoRef.current.play().catch(() => {});
                  }
                }}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: isActive ? 'rgba(225, 29, 72, 0.16)' : 'var(--bg-card)',
                  border: isActive ? '1px solid var(--primary)' : '1px solid transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="speaker-pill">{cue.speaker}</span>
                    <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                      {cue.start.toFixed(2)}s – {cue.end.toFixed(2)}s
                    </span>
                  </div>
                  {isActive && (
                    <span style={{ fontSize: '11px', color: '#fda4af', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Play size={10} fill="currentColor" /> Active
                    </span>
                  )}
                </div>

                <div style={{ fontSize: '14px', fontWeight: 600, color: '#ffffff', lineHeight: '1.4' }}>
                  {cue.text}
                </div>

                {(cue.translations?.en || cue.translations?.hi || cue.translations?.bn_rom || cue.translations?.hi_rom) && (
                  <div style={{ marginTop: '6px', fontSize: '12px', color: 'var(--text-dim)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    {cue.translations?.hi && <div><b style={{ color: '#fbbf24' }}>HI (हिन्दी):</b> {cue.translations.hi}</div>}
                    {cue.translations?.bn_rom && <div><b style={{ color: '#fda4af' }}>BN (Banglish):</b> {cue.translations.bn_rom}</div>}
                    {cue.translations?.hi_rom && <div><b style={{ color: '#fda4af' }}>HI (Hinglish):</b> {cue.translations.hi_rom}</div>}
                    {cue.translations?.en && <div><b style={{ color: '#f3e5e7' }}>EN:</b> {cue.translations.en}</div>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
