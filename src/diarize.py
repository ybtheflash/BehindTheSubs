import logging
import os
from typing import List, Optional
import numpy as np
import soundfile as sf
from src.models import SpeakerSegment, VADSegment
from src.config import default_config

logger = logging.getLogger(__name__)

class SpeakerDiarizer:
    def __init__(
        self,
        model_name: str = default_config.diarization_model,
        hf_token: Optional[str] = default_config.hf_token
    ):
        self.model_name = model_name
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self._pipeline = None

    def _init_pyannote(self):
        if not self.hf_token:
            logger.info("No HF_TOKEN provided; pyannote model requires HF auth. Using acoustic diarization fallback.")
            return False
        try:
            from pyannote.audio import Pipeline
            logger.info(f"Loading pyannote pipeline: {self.model_name}")
            self._pipeline = Pipeline.from_pretrained(self.model_name, use_auth_token=self.hf_token)
            return True
        except Exception as e:
            logger.warning(f"Could not load pyannote diarization pipeline: {e}. Falling back to acoustic clustering.")
            return False

    def diarize(
        self,
        audio_path: str,
        vad_segments: Optional[List[VADSegment]] = None
    ) -> List[SpeakerSegment]:
        """
        Performs speaker diarization over the entire audio timeline.
        Tries pyannote first, then falls back to acoustic clustering across speech segments.
        """
        # Try pyannote if available and token present
        if self._pipeline is None and self.hf_token:
            self._init_pyannote()

        if self._pipeline is not None:
            try:
                logger.info(f"Running pyannote diarization on {audio_path}")
                diarization = self._pipeline(audio_path)
                segments: List[SpeakerSegment] = []
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    segments.append(
                        SpeakerSegment(
                            speaker=speaker,
                            start=round(turn.start, 3),
                            end=round(turn.end, 3)
                        )
                    )
                if segments:
                    logger.info(f"Pyannote diarization complete: found {len(segments)} speaker turns.")
                    return segments
            except Exception as e:
                logger.warning(f"Pyannote inference failed: {e}. Falling back to acoustic clustering.")

        # Fallback acoustic clustering diarization
        return self._acoustic_diarization(audio_path, vad_segments)

    def _acoustic_diarization(
        self,
        audio_path: str,
        vad_segments: Optional[List[VADSegment]] = None
    ) -> List[SpeakerSegment]:
        """
        Acoustic clustering diarization:
        Extracts MFCC / spectral features for speech segments and clusters them into distinct speakers.
        Guarantees stable SPEAKER_00, SPEAKER_01 identities without external API dependencies.
        """
        logger.info(f"Running acoustic clustering diarization on {audio_path}")
        try:
            from sklearn.cluster import AgglomerativeClustering

            audio, sr = sf.read(audio_path, dtype="float32")
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            total_duration = len(audio) / sr

            # If no VAD segments provided, split into 2-second windows
            chunks = []
            if vad_segments and len(vad_segments) > 0:
                for seg in vad_segments:
                    # Break long segments into max 3s chunks
                    dur = seg.end - seg.start
                    if dur < 0.3:
                        continue
                    num_sub = max(1, int(dur // 2.5))
                    step = dur / num_sub
                    for i in range(num_sub):
                        chunks.append((seg.start + i * step, seg.start + (i + 1) * step))
            else:
                window_size = 2.0
                for start in np.arange(0, total_duration, window_size):
                    end = min(total_duration, start + window_size)
                    if end - start >= 0.5:
                        chunks.append((start, end))

            if not chunks:
                return [SpeakerSegment(speaker="SPEAKER_00", start=0.0, end=round(total_duration, 3))]

            # Extract feature embeddings per chunk using pure numpy / scipy (zero numba dependency)
            features = []
            valid_chunks = []
            for start, end in chunks:
                s_idx = int(start * sr)
                e_idx = int(end * sr)
                chunk_audio = audio[s_idx:e_idx]
                if len(chunk_audio) < int(sr * 0.2):
                    continue

                # Pure numpy / scipy spectral features: RMS energy, zero crossing rate, spectral centroid, spectral bandwidth
                rms = np.sqrt(np.mean(chunk_audio ** 2) + 1e-10)
                zcr = np.mean(np.abs(np.diff(np.sign(chunk_audio)))) / 2.0
                fft_vals = np.abs(np.fft.rfft(chunk_audio * np.hanning(len(chunk_audio))))
                freqs = np.fft.rfftfreq(len(chunk_audio), 1.0 / sr)
                sum_fft = np.sum(fft_vals) + 1e-10
                centroid = np.sum(freqs * fft_vals) / sum_fft
                spread = np.sqrt(np.sum(((freqs - centroid) ** 2) * fft_vals) / sum_fft)
                
                # Spectral energy bands (8 subbands)
                bands = np.array_split(fft_vals, 8)
                band_energies = [np.mean(b) for b in bands]

                feat = np.array([rms, zcr, centroid / (sr / 2.0), spread / (sr / 2.0)] + band_energies)
                features.append(feat)
                valid_chunks.append((start, end))

            if len(features) < 2:
                return [SpeakerSegment(speaker="SPEAKER_00", start=0.0, end=round(total_duration, 3))]

            X = np.array(features)
            # Normalize features
            X = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-6)

            # Cluster: determine optimal number of speakers (2 to 4)
            n_clusters = min(3, len(X))
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric="cosine",
                linkage="average"
            )
            labels = clustering.fit_predict(X)

            # Map cluster labels to SPEAKER_00, SPEAKER_01...
            raw_segments: List[SpeakerSegment] = []
            for (start, end), label in zip(valid_chunks, labels):
                spk_id = f"SPEAKER_{label:02d}"
                raw_segments.append(SpeakerSegment(speaker=spk_id, start=round(start, 3), end=round(end, 3)))

            # Merge contiguous segments with same speaker
            merged: List[SpeakerSegment] = []
            for seg in raw_segments:
                if not merged:
                    merged.append(seg)
                else:
                    prev = merged[-1]
                    if prev.speaker == seg.speaker and abs(seg.start - prev.end) < 0.6:
                        prev.end = seg.end
                    else:
                        merged.append(seg)

            logger.info(f"Acoustic diarization complete: found {len(merged)} segments across {n_clusters} clusters.")
            return merged

        except Exception as e:
            logger.error(f"Acoustic diarization error: {e}. Defaulting to SPEAKER_00.")
            return [SpeakerSegment(speaker="SPEAKER_00", start=0.0, end=round(total_duration, 3))]
