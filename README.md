# Bengali Subtitle & Closed-Caption Pipeline

An AI-native, end-to-end media localisation pipeline that transforms Bengali video into:

- **Speaker-attributed Bengali closed captions**
- **English subtitles**
- **Hindi subtitles**
- **Machine-readable QC reports**
- **A ranked human review queue**

Built for the **hoichoi AI Builders Hackathon — Problem 2: Bengali Subtitle & Closed-Caption Pipeline with Speaker Diarization**.

The system is designed around one production problem: **automated subtitles are only useful when a human can quickly identify which cues are trustworthy and which ones require review.**

---

## 1. What This Solves

Given a Bengali-language video:

```text
video.mp4
    │
    ▼
Audio extraction
    │
    ▼
Speech / non-speech analysis
    │
    ▼
Bengali ASR
    │
    ▼
Word-level alignment
    │
    ▼
Speaker diarization
    │
    ▼
Speaker ↔ word reconciliation
    │
    ▼
Subtitle cue segmentation
    │
    ├──────────────► Bengali CC (.vtt)
    │
    ▼
AI translation
    │
    ├──────────────► English subtitles (.srt)
    └──────────────► Hindi subtitles (.srt)
    
All stages
    │
    ▼
AI-assisted QC engine
    │
    ├── hallucination risk
    ├── ASR confidence
    ├── speech overlap
    ├── speaker continuity
    ├── CPS / readability
    ├── shot-boundary conflicts
    └── timing anomalies
              │
              ▼
       Ranked review queue
```

The goal is not simply to generate subtitles.

The goal is to produce **shippable subtitle assets with an evidence-based QC layer that tells a human exactly what needs attention.**

---

# 2. Core Architecture

```text
                         ┌─────────────────────┐
                         │      video.mp4      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  FFmpeg / Audio I/O │
                         └──────────┬──────────┘
                                    │
                   ┌────────────────┴────────────────┐
                   ▼                                 ▼
          ┌────────────────┐                ┌────────────────┐
          │ Speech / VAD   │                │ Shot Detection │
          │ Silero VAD     │                │ PySceneDetect  │
          └───────┬────────┘                └───────┬────────┘
                  │                                 │
                  └────────────────┬────────────────┘
                                   ▼
                         ┌─────────────────────┐
                         │      WhisperX       │
                         │ Bengali ASR         │
                         │ Word-level align.   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Speaker Diarization │
                         │      pyannote       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Speaker ↔ Word      │
                         │ Reconciliation      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Cue Segmentation    │
                         │ CPS / line length   │
                         │ shot boundaries     │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
           Bengali CC (.vtt)                Translation Layer
                                                    │
                                      ┌─────────────┴─────────────┐
                                      ▼                           ▼
                              English (.srt)               Hindi (.srt)
                                      │                           │
                                      └─────────────┬─────────────┘
                                                    ▼
                                           ┌─────────────────┐
                                           │    QC Engine    │
                                           └────────┬────────┘
                                                    │
                                                    ▼
                                           ┌─────────────────┐
                                           │ Ranked Review   │
                                           │ Queue + Report  │
                                           └─────────────────┘
```

---

# 3. AI / ML Components

| Stage | Technology | Purpose |
|---|---|---|
| Audio extraction | FFmpeg | Extract and normalize audio |
| VAD | Silero VAD | Detect speech vs non-speech |
| ASR | WhisperX / faster-whisper | Bengali transcription |
| Alignment | WhisperX alignment | Word-level timestamps |
| Diarization | pyannote.audio | Speaker segmentation |
| Shot detection | PySceneDetect | Detect visual boundaries |
| Translation | LLM | Bengali → English / Hindi |
| QC | Custom AI-assisted engine | Detect and rank subtitle risks |
| Output | WebVTT / SRT | Broadcast-compatible subtitle files |
| Demo | Streamlit | Live end-to-end demonstration |

WhisperX provides word-level timestamps through alignment and integrates speaker diarization through pyannote. Its current documentation also supports VAD preprocessing and recent versions continue to receive timestamp and diarization improvements.

For diarization, the implementation is designed around the current pyannote ecosystem rather than being hard-coded to the older `pyannote.audio 3.1` pipeline. The newer community diarization pipeline provides **exclusive speaker diarization**, which is useful when reconciling speaker turns with word-level transcription.

---

# 4. Why the QC Engine Is the Core Feature

A transcription pipeline can generate subtitles.

A production localisation pipeline needs to answer:

> **"Which subtitles can I trust, and which ones should a human review?"**

The QC engine therefore combines multiple independent signals.

```text
                    ┌─────────────────┐
                    │ Subtitle Cue    │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
    ASR confidence       VAD overlap       Speaker match
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
      CPS/readability   Shot boundary      Timing anomaly
                             │
                             ▼
                    ┌─────────────────┐
                    │ Risk Aggregator │
                    └────────┬────────┘
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
               LOW        MEDIUM        HIGH
                 │           │           │
                 └───────────┴───────────┘
                             ▼
                    Ranked Review Queue
```

### Example QC record

```json
{
  "cue_id": 184,
  "start": 1894.120,
  "end": 1897.800,
  "speaker": "SPEAKER_02",
  "text": "আমি কাল আসব।",
  "asr_confidence": 0.43,
  "speech_overlap": 0.18,
  "speaker_continuity": true,
  "shot_boundary_conflict": false,
  "cps": 8.7,
  "hallucination_risk": "HIGH",
  "review_priority": 0.91
}
```

The review queue is **generated automatically from these signals** rather than manually selecting suspicious cues.

---

# 5. Hallucination Detection

The hackathon specifically identifies **hallucinated subtitle text over silence or music** as a critical failure mode.

The pipeline therefore treats hallucination detection as a first-class stage.

### Detection strategy

```text
ASR output
     │
     ▼
Compare subtitle timing
against independent VAD timeline
     │
     ├── Mostly speech
     │       ↓
     │   continue
     │
     ├── Partial speech
     │       ↓
     │   MEDIUM RISK
     │
     └── Mostly non-speech
             ↓
         HIGH RISK
             ↓
      Human review queue
```

A cue is not automatically deleted solely because VAD disagrees with it.

Instead, the system preserves the evidence and routes suspicious cues to human review.

This reduces the risk of silently deleting legitimate speech while still surfacing likely hallucinations.

---

# 6. Speaker Attribution

Speaker diarization produces stable speaker segments such as:

```text
00:00:03.20 → 00:00:07.80    SPEAKER_00
00:00:08.10 → 00:00:11.40    SPEAKER_01
00:00:11.70 → 00:00:14.20    SPEAKER_00
```

These are reconciled with word-level timestamps:

```text
SPEAKER_00
"তুই আজ অফিসে যাচ্ছিস?"

SPEAKER_01
"না, আজকে আমার meeting আছে।"
```

The system also tracks speaker continuity so that an unexpected identity switch becomes a QC signal rather than silently appearing in the final subtitles.

Where available, **exclusive diarization** is used to simplify reconciliation between diarization segments and transcription timestamps.

---

# 7. Bengali + Code-Switched Speech

The pipeline does not force Bengali-only decoding.

Real Bengali dialogue may contain English words naturally:

```text
ওর office-এ একটা meeting আছে।
```

The ASR layer therefore preserves code-switched speech before subtitle segmentation and translation.

The translation layer receives the Bengali source transcript rather than translating isolated words independently.

---

# 8. Subtitle Presentation Rules

Generated cues are validated against configurable subtitle constraints.

### Default rules

- Maximum 2 lines
- Configurable maximum characters per line
- Configurable CPS threshold
- Minimum cue duration
- Maximum cue duration
- Avoid unnecessary cue fragmentation
- Avoid crossing detected shot boundaries where possible
- Preserve speaker attribution
- Preserve code-switched words where appropriate

Example:

```text
BAD

00:12:04.100 → 00:12:05.100

আমি কাল অফিসে
যাবো এবং তারপর আমরা
meeting করব।
```

Becomes:

```text
BETTER

00:12:04.100 → 00:12:06.400

আমি কাল অফিসে যাবো
এবং তারপর meeting করব।
```

All thresholds are configurable rather than treated as universal broadcast rules.

---

# 9. Translation

After Bengali cue generation, the source subtitles are translated into:

- English
- Hindi

The translation stage receives contextual information where available:

```text
Previous cue
Current cue
Next cue
Speaker
Scene boundary
```

This allows the model to preserve conversational meaning rather than translating every cue in isolation.

The output remains synchronized with the original Bengali cue timings.

---

# 10. Output

A successful pipeline run produces:

```text
outputs/
│
├── bn_captions.vtt
├── en_subtitles.srt
├── hi_subtitles.srt
│
└── qc/
    ├── qc_report.json
    └── qc_report.html
```

### Bengali WebVTT

```text
WEBVTT

00:00:04.120 --> 00:00:06.800
[SPEAKER_00]
তুই আজ অফিসে যাচ্ছিস?
```

### English SRT

```text
1
00:00:04,120 --> 00:00:06,800
Are you going to the office today?
```

### Hindi SRT

```text
1
00:00:04,120 --> 00:00:06,800
क्या तुम आज ऑफिस जा रहे हो?
```

---

# 11. Demo Experience

The live demo is designed around a simple workflow:

```text
UPLOAD VIDEO
     ↓
ANALYZE
     ↓
PROCESSING
     ↓
RESULTS
```

The results dashboard shows:

```text
┌─────────────────────────────────────────────┐
│ Bengali Subtitle Pipeline                   │
├─────────────────────────────────────────────┤
│                                             │
│  Cues generated              127            │
│  Speakers detected             4            │
│                                             │
│  ✓ Low risk                 109            │
│  ⚠ Review recommended        14            │
│  🔴 High risk                 4            │
│                                             │
├─────────────────────────────────────────────┤
│ REVIEW QUEUE                                │
│                                             │
│ 🔴 Cue #184   Hallucination risk    91%     │
│ 🟠 Cue #097   Speaker ambiguity     74%     │
│ 🟠 Cue #031   CPS violation         69%     │
│                                             │
└─────────────────────────────────────────────┘
```

Selecting a review item jumps the video to the relevant timestamp and displays the evidence behind the QC decision.

---

# 12. Repository Structure

```text
.
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── src/
│   ├── pipeline.py
│   │
│   ├── audio.py
│   ├── vad.py
│   ├── asr.py
│   ├── alignment.py
│   ├── diarize.py
│   ├── speaker_merge.py
│   │
│   ├── cue_segmenter.py
│   ├── shot_detect.py
│   │
│   ├── translate.py
│   │
│   ├── qc/
│   │   ├── hallucination.py
│   │   ├── confidence.py
│   │   ├── speaker.py
│   │   ├── readability.py
│   │   ├── timing.py
│   │   └── scorer.py
│   │
│   └── formats/
│       ├── vtt_writer.py
│       └── srt_writer.py
│
├── demo/
│   └── app.py
│
├── outputs/
│
└── tests/
    ├── test_qc.py
    ├── test_segmentation.py
    └── test_formats.py
```

---

# 13. Configuration

Create `.env` from `.env.example`:

```env
HF_TOKEN=
ANTHROPIC_API_KEY=

ASR_MODEL=large-v3
DIARIZATION_MODEL=pyannote/speaker-diarization-community-1

MAX_CPS=17
MAX_LINES=2
MAX_CHARS_PER_LINE=42

HALLUCINATION_HIGH_THRESHOLD=0.70
HALLUCINATION_MEDIUM_THRESHOLD=0.35
```

Secrets are never committed to the repository.

---

# 14. Installation

```bash
git clone <repo-url>
cd bengali-cc-pipeline

python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install FFmpeg separately and verify:

```bash
ffmpeg -version
```

WhisperX can be installed from PyPI and its current documentation supports GPU acceleration as well as CPU-only operation.

For pyannote diarization, a Hugging Face access token and acceptance of the required model terms may be necessary.

---

# 15. Running the Pipeline

```bash
python src/pipeline.py \
    --input videos/episode_01.mp4 \
    --lang bn \
    --translate en hi \
    --output outputs/
```

Launch the demo:

```bash
streamlit run demo/app.py
```

---

# 16. MVP Priorities

Because the hackathon has a 12-hour build window, implementation follows strict priorities.

### P0 — Must Work

```text
✓ Bengali ASR
✓ Word timestamps
✓ Speaker diarization
✓ Bengali WebVTT
✓ English subtitles
✓ Hindi subtitles
✓ QC report
✓ Ranked review queue
✓ Live demo
```

### P1 — Important

```text
✓ VAD hallucination detection
✓ Shot-boundary awareness
✓ Speaker continuity checks
✓ Subtitle readability checks
✓ Interactive timestamp review
```

### P2 — If Time Allows

```text
○ Speaker name inference
○ Advanced linguistic QC
○ Cast-list matching
○ Additional visual analytics
○ More sophisticated translation context
```

The system is intentionally designed so that P0 remains usable even if optional components have to be disabled.

---

# 17. 12-Hour Build Plan

| Time | Goal |
|---|---|
| 0:00–1:00 | Environment + FFmpeg + WhisperX smoke test |
| 1:00–2:30 | Bengali ASR + word alignment |
| 2:30–4:00 | Speaker diarization + speaker/word reconciliation |
| 4:00–5:00 | Bengali WebVTT + cue segmentation |
| 5:00–6:00 | English/Hindi translation |
| 6:00–7:30 | QC engine + hallucination detection |
| 7:30–8:30 | Ranked review queue |
| 8:30–9:30 | Streamlit demo |
| 9:30–10:30 | Run against sample assets + fix failures |
| 10:30–11:15 | UI polish + deployment |
| 11:15–12:00 | Explainer video + GitHub + final testing |

**Priority rule:** a working end-to-end pipeline beats an unfinished advanced feature.

---

# 18. Production-Minded Guardrails

The pipeline intentionally avoids silently "fixing" uncertain content.

Instead:

```text
LOW RISK
    ↓
Auto-accept

MEDIUM RISK
    ↓
Human review

HIGH RISK
    ↓
Human review required
```

This is especially important for:

- hallucinated speech
- uncertain speaker attribution
- overlapping speakers
- low-confidence transcription
- subtitle timing conflicts
- readability violations

The system exposes uncertainty rather than hiding it.

---

# 19. Auto-Disqualifier Checklist

The implementation must satisfy:

- [ ] No hand-corrected transcript is shipped as the pipeline output
- [ ] Bengali ASR is generated automatically
- [ ] Speaker attribution is generated automatically
- [ ] Hallucination risks are surfaced in the QC report
- [ ] Suspicious cues appear in a ranked review queue
- [ ] English and Hindi tracks are generated automatically
- [ ] Demo processes an uploaded video
- [ ] No cached output is required for the core demo
- [ ] Demo remains functional during judging

---

# 20. Known Limitations

### Speaker naming

Automatic diarization produces anonymous speaker IDs such as:

```text
SPEAKER_00
SPEAKER_01
```

Optional name inference may use cast information or conversational cues, but this is not required for the core pipeline.

### Translation

LLM translation quality depends on source transcription quality and available context.

### Subtitle style

CPS, line length, cue duration and other presentation constraints are configurable because exact broadcaster requirements can vary.

### Overlapping speech

Overlapping speakers remain inherently difficult for automated subtitle attribution. Such cases are surfaced through the QC system rather than silently treated as certain.

---

# 21. Why This Is AI-Native

AI is not an additional feature attached to a conventional subtitle generator.

AI is used throughout the core pipeline:

```text
Speech understanding
       ↓
Bengali transcription
       ↓
Word alignment
       ↓
Speaker understanding
       ↓
Context-aware translation
       ↓
Automated quality reasoning
       ↓
Human review prioritisation
```

The system therefore combines **speech AI + speaker intelligence + generative language AI + automated QC** into a single media-localisation workflow.

---

# 22. Hackathon Alignment

### Recognition

Bengali ASR with support for naturally code-switched Bengali-English speech.

### Attribution

Speaker diarization with stable speaker IDs across the runtime.

### Presentation

Cue segmentation and validation for readability, timing and shot boundaries.

### QC

Independent VAD and multiple confidence signals are used to surface likely hallucinations and other subtitle defects.

### Human-in-the-loop

The system does not pretend uncertain AI output is correct. It creates a ranked review queue so a human can focus attention where it matters most.

---

# 23. License / Credits

Built using:

- WhisperX
- faster-whisper
- pyannote.audio
- Silero VAD
- PySceneDetect
- FFmpeg
- Streamlit
- Anthropic API

Created for the **hoichoi AI Builders Hackathon — Problem 2: Speech & Language / Media Localisation**.