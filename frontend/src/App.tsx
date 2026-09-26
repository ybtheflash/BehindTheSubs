import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { UploadStudio } from './components/UploadStudio';
import { PipelineProgress } from './components/PipelineProgress';
import { QCReviewQueue } from './components/QCReviewQueue';
import { VideoPlayer } from './components/VideoPlayer';
import { QCDashboard } from './components/QCDashboard';
import { ExportCenter } from './components/ExportCenter';
import type { PipelineResult, PipelineTaskStatus, AIHealthStatus } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('studio');
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<PipelineTaskStatus | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [seekTime, setSeekTime] = useState<number | null>(null);
  const [activeProvider, setActiveProvider] = useState<'bengali_xlsr' | 'bengali_whisper' | 'gemini'>('bengali_xlsr');
  const [aiHealth, setAiHealth] = useState<AIHealthStatus | null>(null);

  // Poll AI Awake/Sleeping status
  const checkAiHealth = async () => {
    try {
      const res = await fetch('/api/health/ai');
      if (res.ok) {
        const data: AIHealthStatus = await res.json();
        setAiHealth(data);
      }
    } catch (err) {
      console.error('Error checking AI health:', err);
    }
  };

  useEffect(() => {
    checkAiHealth();
    const interval = setInterval(checkAiHealth, 30000); // check every 30s
    return () => clearInterval(interval);
  }, []);

  // Check if results exist on startup
  useEffect(() => {
    fetch('/api/results')
      .then(res => res.json())
      .then(data => {
        if (data && data.cues) {
          setResult(data);
        }
      })
      .catch(() => {});
  }, []);

  // Poll active task status
  useEffect(() => {
    if (!activeTaskId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/pipeline/status/${activeTaskId}`);
        if (!res.ok) return;
        const statusData: PipelineTaskStatus = await res.json();
        setTaskStatus(statusData);

        if (statusData.status === 'completed' && statusData.result) {
          setResult(statusData.result);
          setActiveTaskId(null);
        } else if (statusData.status === 'failed') {
          setActiveTaskId(null);
        }
      } catch (err) {
        console.error('Error polling pipeline status:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeTaskId]);

  const handleStartPipeline = async (
    videoPath: string,
    languages: string[],
    useCache: boolean,
    asrProvider: 'bengali_xlsr' | 'bengali_whisper' | 'gemini',
    asrApiKey?: string
  ) => {
    setActiveProvider(asrProvider);
    setResult(null); // Clear previous run's data immediately
    try {
      const res = await fetch('/api/pipeline/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: videoPath,
          target_languages: languages,
          use_cache: useCache,
          asr_provider: asrProvider,
          asr_api_key: asrApiKey
        })
      });
      const data = await res.json();
      if (data.task_id) {
        setActiveTaskId(data.task_id);
        setTaskStatus({
          task_id: data.task_id,
          status: 'pending',
          percent: 0,
          stage: 'init',
          logs: [`Pipeline started with ASR provider: ${asrProvider}...`]
        });
        setActiveTab('studio');
      }
    } catch (err) {
      console.error('Failed to start pipeline:', err);
      alert('Failed to trigger pipeline.');
    }
  };

  const handleSeekVideo = (timestamp: number) => {
    setSeekTime(timestamp);
    setActiveTab('player');
  };

  const handleUpdateCue = async (
    cueIndex: number,
    text: string,
    speaker: string,
    en?: string,
    hi?: string,
    action?: string
  ) => {
    try {
      const res = await fetch('/api/cue/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cue_index: cueIndex,
          text: text || undefined,
          speaker: speaker || undefined,
          translation_en: en,
          translation_hi: hi,
          action: action
        })
      });

      if (res.ok) {
        // Refresh active result
        const refreshed = await fetch('/api/results').then(r => r.json());
        setResult(refreshed);
      }
    } catch (err) {
      console.error('Failed to update cue:', err);
    }
  };

  // Client-Side Session Download (Zero Backend Storage)
  const handleDownloadSession = () => {
    if (!result) {
      alert('No active session or results to save.');
      return;
    }
    const sessionPayload = {
      format: 'B2S_SESSION_V1',
      appName: 'B2S - Behind The Subs',
      tagline: 'Automated Bengali Subtitle & Closed-Caption Pipeline with Speaker Diarization',
      exportedAt: new Date().toISOString(),
      result: result
    };
    const blob = new Blob([JSON.stringify(sessionPayload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const dateStr = new Date().toISOString().slice(0, 10);
    link.download = `b2s_session_${dateStr}.b2s`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Client-Side Session Upload (Zero Backend Storage)
  const handleUploadSession = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const parsed = JSON.parse(text);
        if (parsed.result && parsed.result.cues) {
          setResult(parsed.result);
          setActiveTab('review');
        } else if (parsed.cues) {
          setResult(parsed);
          setActiveTab('review');
        } else {
          alert('Invalid session file format. Could not find subtitle cues.');
        }
      } catch (err) {
        console.error('Failed to parse session file:', err);
        alert('Could not parse the selected session file.');
      }
    };
    reader.readAsText(file);
  };

  const reviewQueue = result?.qc_report?.review_queue || [];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        reviewCount={reviewQueue.length}
        activeProvider={activeProvider}
        hasSession={Boolean(result)}
        onDownloadSession={handleDownloadSession}
        onUploadSession={handleUploadSession}
        aiHealth={aiHealth}
        onRefreshAi={checkAiHealth}
      />

      <main className="main-content" style={{ flex: 1 }}>
        {/* Studio Tab: Upload & Execution */}
        {activeTab === 'studio' && (
          <div>
            {activeTaskId || (taskStatus && taskStatus.status === 'processing') ? (
              <PipelineProgress
                status={taskStatus}
                onViewResults={() => setActiveTab('review')}
              />
            ) : (
              <UploadStudio
                onStartPipeline={handleStartPipeline}
                isProcessing={Boolean(activeTaskId)}
                onProviderChange={setActiveProvider}
                onUploadSession={handleUploadSession}
                aiHealth={aiHealth}
                onRefreshAi={checkAiHealth}
              />
            )}
          </div>
        )}

        {/* Review Queue Tab */}
        {activeTab === 'review' && (
          <QCReviewQueue
            queue={reviewQueue}
            onSeekVideo={handleSeekVideo}
            onUpdateCue={handleUpdateCue}
          />
        )}

        {/* Video Player & Synchronized Subtitles Tab */}
        {activeTab === 'player' && result && (
          <VideoPlayer
            videoUrl="/api/video"
            cues={result.cues}
            currentTime={currentTime}
            onTimeUpdate={setCurrentTime}
            seekTime={seekTime}
          />
        )}

        {activeTab === 'player' && !result && (
          <div className="glass-panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff' }}>No Video Loaded</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '6px' }}>
              Run the pipeline in the Pipeline Studio first or open a saved session to inspect video playback and subtitles.
            </p>
          </div>
        )}

        {/* QC Analytics Dashboard Tab */}
        {activeTab === 'dashboard' && result && (
          <QCDashboard
            report={result.qc_report}
            onSeekVideo={handleSeekVideo}
          />
        )}

        {activeTab === 'dashboard' && !result && (
          <div className="glass-panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff' }}>No Analytics Data</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '6px' }}>
              Run the pipeline or open a saved session to generate QC analytics and charts.
            </p>
          </div>
        )}

        {/* Deliverables & Exports Tab */}
        {activeTab === 'exports' && (
          <ExportCenter
            result={result}
            onClearData={() => {
              setResult(null);
              setTaskStatus(null);
              setActiveTaskId(null);
            }}
            onDownloadSession={handleDownloadSession}
          />
        )}
      </main>

      {/* Required Attribution & Tagline Footer */}
      <footer style={{
        textAlign: 'center',
        padding: '24px 20px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'rgba(12, 2, 4, 0.95)',
        color: '#f3e5e7',
        fontSize: '13px',
        fontWeight: 500,
        letterSpacing: '0.02em',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '6px'
      }}>
        <div style={{ color: '#ffffff', fontWeight: 600 }}>
          Made by <a href="https://ybtheflash.in" target="_blank" rel="noreferrer" style={{ color: '#fda4af', textDecoration: 'none', fontWeight: 700 }}>Yubaraj Biswas</a> (<a href="https://github.com/ybtheflash" target="_blank" rel="noreferrer" style={{ color: '#fda4af', textDecoration: 'none' }}>@ybtheflash</a>) for hoichoi Hackathon'26.
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
          Automated Bengali Subtitle & Closed-Caption Pipeline with Speaker Diarization • B2S - Behind The Subs
        </div>
      </footer>
    </div>
  );
};

export default App;
