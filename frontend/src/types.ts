export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  confidence: number;
  speaker?: string | null;
}

export interface SubtitleCue {
  index: number;
  start: number;
  end: number;
  speaker: string;
  text: string;
  duration?: number;
  cps?: number;
  words?: WordTimestamp[];
  translations?: Record<string, string>;
}

export interface QCFlag {
  flag_type: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH';
  score: number;
  message: string;
  evidence: Record<string, any>;
}

export interface CueQC {
  cue_index: number;
  start: number;
  end: number;
  speaker: string;
  text: string;
  asr_confidence: number;
  speech_overlap: number;
  speaker_continuity: boolean;
  cps: number;
  line_count: number;
  max_char_per_line: number;
  shot_boundary_conflict: boolean;
  hallucination_risk: 'LOW' | 'MEDIUM' | 'HIGH';
  speaker_risk: 'LOW' | 'MEDIUM' | 'HIGH';
  readability_risk: 'LOW' | 'MEDIUM' | 'HIGH';
  timing_risk: 'LOW' | 'MEDIUM' | 'HIGH';
  review_priority: number;
  flags: QCFlag[];
  translations?: Record<string, string>;
}

export interface PipelineQCReport {
  total_cues: number;
  low_risk_count: number;
  medium_risk_count: number;
  high_risk_count: number;
  avg_cps: number;
  total_speech_duration: number;
  speaker_distribution: Record<string, number>;
  cues: CueQC[];
  review_queue: CueQC[];
}

export interface PipelineResult {
  video_path: string;
  audio_path: string;
  language: string;
  cues: SubtitleCue[];
  qc_report: PipelineQCReport;
  vtt_path: string;
  srt_en_path: string;
  srt_hi_path: string;
  srt_bn_rom_path?: string;
  srt_hi_rom_path?: string;
  qc_json_path: string;
  qc_html_path: string;
  asr_provider?: string;
  created_at?: string;
}

export interface PipelineTaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  percent: number;
  stage: string;
  logs: string[];
  video_path?: string;
  error?: string;
  result?: PipelineResult;
}

export interface MaskedKey {
  id: string;
  label: string;
  value: string;
}

export interface ASRConfig {
  default_provider: 'bengali_xlsr' | 'bengali_whisper' | 'bengali_ai' | 'gemini' | 'whisper.cpp' | 'faster-whisper' | 'mimo';
  bengali_xlsr_available?: boolean;
  bengali_xlsr_model?: string;
  bengali_whisper_available?: boolean;
  bengali_whisper_model?: string;
  bengali_ai_available?: boolean;
  bengali_ai_model?: string;
  mimo_translation_configured?: boolean;
  mimo_configured: boolean;
  mimo_keys: MaskedKey[];
  mimo_model: string;
  mimo_base_url: string;
  gemini_configured: boolean;
  gemini_keys: MaskedKey[];
  gemini_model: string;
  whisper_cpp_available?: boolean;
  whisper_cpp_version?: string;
  whisper_model: string;
  whisper_device: string;
}

export interface AIHealthStatus {
  status: 'awake' | 'sleeping' | 'checking' | 'error';
  modal_xlsr?: {
    status: string;
    latency_ms: number | null;
    url: string;
  };
  modal_whisper?: {
    status: string;
    latency_ms: number | null;
    url: string;
  };
  estimated_wakeup_seconds: number;
  message: string;
}


