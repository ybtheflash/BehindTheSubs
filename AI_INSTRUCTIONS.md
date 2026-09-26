# AI BUILD INSTRUCTIONS — Bengali Subtitle & Closed-Caption Pipeline

## 0. Role

You are the primary AI software engineer responsible for implementing this project for the **hoichoi AI Builders Hackathon — Problem 2: Bengali Subtitle & Closed-Caption Pipeline with Speaker Diarization**.

The accompanying `README.md` is the product and architecture specification.

Your job is to turn that specification into a **working, demonstrable, end-to-end application within a very limited hackathon timeframe**.

Do not treat this as a theoretical architecture exercise.

**Working software is the priority.**

---

# 1. Primary Objective

Build an application that accepts a Bengali-language video and produces:

1. Bengali speaker-attributed closed captions (`.vtt`)
2. English subtitles (`.srt`)
3. Hindi subtitles (`.srt`)
4. A machine-readable QC report (`.json`)
5. A human-readable QC dashboard
6. A ranked review queue for suspicious subtitle cues
7. A live demo where the entire pipeline can be run from an uploaded video

The central differentiator is the **AI-assisted QC and human review workflow**.

Do not build a generic transcription application.

The product should answer:

> "Which generated subtitle cues can I trust, and which ones should a human review?"

---

# 2. Read Before Coding

Before creating or modifying code:

1. Read `README.md` completely.
2. Read this file completely.
3. Understand the complete pipeline.
4. Identify the P0 requirements.
5. Start implementation immediately after understanding the architecture.

Do not spend excessive time creating documentation before the pipeline works.

Do not redesign the architecture unless a technical blocker requires it.

---

# 3. Hackathon Constraints

This is a **solo 12-hour hackathon**.

The application must therefore prioritize:

```text
WORKING PIPELINE
>
RELIABLE DEMO
>
CORE AI FEATURES
>
QC QUALITY
>
UI POLISH
>
OPTIONAL FEATURES
```

Never sacrifice an end-to-end working pipeline for an optional feature.

If a feature becomes difficult or unreliable, implement the simplest production-plausible version and continue.

---

# 4. P0 Requirements — NON-NEGOTIABLE

The following must work before optional features are attempted:

```text
[ ] Video upload
[ ] Audio extraction
[ ] Bengali ASR
[ ] Word-level timestamps
[ ] Speaker diarization
[ ] Speaker ↔ word reconciliation
[ ] Bengali WebVTT generation
[ ] English subtitle generation
[ ] Hindi subtitle generation
[ ] QC analysis
[ ] Ranked review queue
[ ] QC JSON output
[ ] Interactive demo
```

The application must be capable of processing a fresh video rather than depending on pre-generated outputs.

---

# 5. P1 Requirements

After P0 is working:

```text
[ ] VAD-based hallucination detection
[ ] ASR confidence analysis
[ ] Speaker continuity analysis
[ ] CPS validation
[ ] Line-length validation
[ ] Cue duration validation
[ ] Shot-boundary awareness
[ ] Timestamp navigation from QC results
[ ] Visual QC dashboard
```

---

# 6. P2 Requirements

Only implement these if the core pipeline is already stable:

```text
[ ] Automatic speaker naming
[ ] Cast-list matching
[ ] Advanced linguistic QC
[ ] Advanced translation context
[ ] Additional analytics
[ ] UI animations
[ ] Advanced visualizations
```

Never allow P2 work to delay deployment.

---

# 7. Technology Direction

Use the architecture described in `README.md`.

Preferred components:

```text
Python
FFmpeg
WhisperX / faster-whisper
pyannote.audio
Silero VAD
PySceneDetect
LLM API for translation
Streamlit for demo UI
WebVTT
SRT
```

Use current stable versions compatible with the environment.

Do not unnecessarily pin old package versions merely because an older tutorial uses them.

Before changing the diarization implementation, verify compatibility between:

- WhisperX
- pyannote.audio
- torch
- CUDA / CPU environment

---

# 8. Environment Detection

Before installing heavy dependencies, inspect the runtime.

Determine:

```text
Python version
Operating system
CPU
GPU availability
CUDA version
Available RAM
Available disk space
```

Prefer GPU acceleration when available.

If GPU acceleration is unavailable, provide a CPU-compatible fallback where practical.

Do not make the entire application unusable simply because GPU inference is unavailable.

---

# 9. Dependency Installation Strategy

Heavy ML packages can consume significant time.

Install and test incrementally.

Recommended order:

```text
1. Python environment
2. FFmpeg
3. PyTorch
4. WhisperX / ASR dependencies
5. pyannote
6. VAD
7. PySceneDetect
8. LLM client
9. Streamlit
```

After every major installation, perform a minimal import/smoke test.

Do not wait until the end to discover dependency conflicts.

---

# 10. Secrets

Never hard-code API keys.

Use:

```text
.env
```

and provide:

```text
.env.example
```

Example:

```env
HF_TOKEN=
ANTHROPIC_API_KEY=

ASR_MODEL=large-v3

MAX_CPS=17
MAX_LINES=2
MAX_CHARS_PER_LINE=42
```

Never commit `.env`.

Ensure `.gitignore` contains:

```gitignore
.env
.venv/
__pycache__/
*.pyc
outputs/
```

---

# 11. Pipeline Implementation

Implement the pipeline as independent modules.

Preferred flow:

```text
video
  ↓
audio extraction
  ↓
VAD
  ↓
ASR
  ↓
alignment
  ↓
diarization
  ↓
speaker/word merge
  ↓
cue segmentation
  ↓
Bengali VTT
  ↓
translation
  ↓
English SRT
Hindi SRT
  ↓
QC
  ↓
review queue
```

Each stage should have a clear input and output structure.

Avoid passing loosely structured dictionaries everywhere.

Use typed Python data structures where useful.

---

# 12. Use Intermediate Data

Do not repeatedly recompute expensive ML stages.

Save intermediate artifacts where practical:

```text
artifacts/
├── audio.wav
├── vad.json
├── asr.json
├── aligned.json
├── diarization.json
├── merged.json
├── cues.json
└── qc.json
```

This is extremely important during development.

If translation breaks, the developer should not need to rerun WhisperX and diarization.

---

# 13. ASR

Use Bengali as the primary language.

Do not force Bengali-only vocabulary normalization.

Preserve naturally code-switched speech.

For example:

```text
ওর office-এ একটা meeting আছে।
```

should not automatically become:

```text
ওর অফিসে একটা মিটিং আছে।
```

unless normalization is explicitly desired.

Preserve the actual spoken content as much as possible.

---

# 14. Alignment

Use word-level timestamps whenever available.

Every word should ideally contain:

```json
{
  "word": "office",
  "start": 12.42,
  "end": 12.91
}
```

These timestamps are essential for:

- speaker assignment
- subtitle segmentation
- QC
- timing analysis

Do not generate subtitles using only whole-segment timestamps if word-level alignment is available.

---

# 15. Speaker Diarization

Run diarization over the audio rather than independently per subtitle cue.

The goal is stable identities:

```text
SPEAKER_00
SPEAKER_01
SPEAKER_02
```

Do not rename speakers unless there is reasonable evidence.

Unknown speakers are acceptable.

Incorrect speaker names are worse than anonymous speaker IDs.

---

# 16. Speaker ↔ Word Reconciliation

For each aligned word:

1. Find overlapping diarization segment(s).
2. Determine the best matching speaker.
3. Assign the speaker ID.
4. Track continuity.
5. Flag ambiguous overlap.

Example:

```text
SPEAKER_00
তুই আজ অফিসে যাচ্ছিস?

SPEAKER_01
না, আজকে আমার meeting আছে।
```

Do not blindly assign an entire ASR segment to one speaker when diarization indicates multiple speakers.

---

# 17. Cue Segmentation

Subtitle cues should be generated from word-level timestamps.

Do not split randomly by character count.

Prefer natural linguistic boundaries:

```text
sentence
phrase
speaker turn
pause
shot boundary
```

Subject to readability constraints.

The segmentation engine should consider:

```text
CPS
line length
cue duration
speaker changes
sentence boundaries
shot changes
```

---

# 18. Bengali Caption Output

Generate valid WebVTT.

Example:

```text
WEBVTT

00:00:04.120 --> 00:00:06.800
[SPEAKER_00]
তুই আজ অফিসে যাচ্ছিস?
```

Validate:

- timestamp format
- ordering
- no negative duration
- no overlapping invalid cues
- valid UTF-8
- maximum lines
- character limits

---

# 19. Translation

Translate from the Bengali source cues.

Do not translate independently generated English/Hindi text.

Preserve:

```text
speaker
timing
meaning
context
proper nouns
code-switching where appropriate
```

Use contextual windows when useful:

```text
previous cue
current cue
next cue
```

Do not allow the translation model to invent dialogue.

The source Bengali subtitle is authoritative.

---

# 20. QC Engine — MOST IMPORTANT

The QC engine is the most important custom component.

Every subtitle cue should receive measurable signals.

At minimum:

```text
ASR confidence
VAD speech overlap
speaker continuity
CPS
line count
character count
cue duration
shot boundary proximity
timing anomalies
```

Convert those signals into a review priority.

Example:

```text
review_priority = weighted combination of risk signals
```

Do not expose arbitrary numbers without explaining what they represent.

---

# 21. Hallucination Detection

This is a critical requirement.

Use an independent VAD signal rather than trusting ASR alone.

For each subtitle cue calculate:

```text
speech_overlap_ratio
```

Example:

```text
cue duration = 4.0 sec
speech overlap = 0.8 sec

speech_overlap_ratio = 0.20
```

Low speech overlap should increase hallucination risk.

However:

**Do not automatically delete the cue solely because VAD disagrees.**

Instead:

```text
LOW RISK
→ accept

MEDIUM RISK
→ review

HIGH RISK
→ mandatory review
```

This prevents legitimate quiet speech from being silently deleted.

---

# 22. QC Scoring

Create transparent signals.

Example:

```text
hallucination_risk
speaker_risk
readability_risk
timing_risk
overall_review_priority
```

Example conceptual output:

```json
{
  "cue_id": 184,
  "hallucination_risk": 0.91,
  "speaker_risk": 0.12,
  "readability_risk": 0.04,
  "timing_risk": 0.08,
  "review_priority": 0.86
}
```

Do not pretend these are statistically calibrated probabilities unless they actually are.

Call them:

```text
risk scores
confidence scores
review priority
```

where appropriate.

---

# 23. Review Queue

Sort cues by review priority.

The UI should make the queue immediately understandable.

Example:

```text
HIGH RISK
Cue #184
00:31:42

Hallucination risk: HIGH
Speaker confidence: LOW

[Watch]
[Review]
```

The reviewer should be able to click the cue and jump directly to the corresponding video timestamp.

This is one of the most important demo interactions.

---

# 24. QC Report

Generate both:

```text
qc_report.json
qc_report.html
```

JSON should contain enough information for another application to consume it.

HTML should be human-readable.

Example:

```text
Total cues: 127

Low risk:       109
Review:          14
High risk:        4
```

Include per-cue evidence.

---

# 25. Demo UI

Use Streamlit unless there is a strong reason not to.

The demo should have:

### Page 1 — Upload

```text
Upload Bengali video

[Choose file]

[Run Pipeline]
```

### Page 2 — Processing

Show stages:

```text
✓ Audio extracted
✓ Speech detected
✓ Bengali transcription
✓ Word alignment
✓ Speaker diarization
✓ Subtitle generation
✓ Translation
✓ QC analysis
```

### Page 3 — Results

Display:

```text
Bengali CC
English
Hindi
QC
```

### Page 4 — Review Queue

Display suspicious cues.

Clicking one should seek the video to that timestamp.

---

# 26. Do Not Build

Do NOT spend hackathon time building:

```text
❌ User authentication
❌ Multi-user accounts
❌ Cloud storage platform
❌ Production database
❌ Real-time transcription
❌ Real-time translation
❌ Real-time collaboration
❌ Complex role management
❌ Mobile application
❌ Custom ML model training
❌ Custom ASR model
❌ Full production deployment infrastructure
```

The hackathon asks for a working media-localisation pipeline, not a SaaS platform.

---

# 27. Error Handling

Every pipeline stage must fail gracefully.

Example:

```text
Diarization unavailable
↓
Continue with SPEAKER_UNKNOWN
↓
Mark attribution as unavailable in QC
```

Example:

```text
Translation API unavailable
↓
Preserve Bengali CC
↓
Show translation failure clearly
```

Never crash the entire demo because an optional feature failed.

---

# 28. Logging

Use structured logging.

Example:

```text
[INFO] Extracting audio
[INFO] Running Bengali ASR
[INFO] Alignment complete: 842 words
[INFO] Diarization complete: 4 speakers
[INFO] Generated 127 subtitle cues
[INFO] QC complete: 18 cues require review
```

Errors should contain enough information to debug them quickly.

---

# 29. Performance

Optimize for hackathon reliability.

Priorities:

```text
1. Correctness
2. Reliability
3. Reasonable processing time
4. Memory usage
5. UI speed
```

Do not prematurely optimize.

Cache expensive intermediate results.

Never rerun ASR just because the user wants to regenerate a translation.

---

# 30. Testing

At minimum test:

### Formats

```text
VTT timestamps
SRT timestamps
UTF-8 Bengali text
```

### Segmentation

```text
sentence boundary
speaker change
shot change
long cue
short cue
```

### QC

```text
normal speech
silence
music
low confidence ASR
speaker change
overlapping speakers
```

### Integration

Run the complete pipeline on at least one real sample video before polishing the UI.

---

# 31. Development Strategy

Always work in this order:

```text
MAKE IT RUN
     ↓
MAKE IT CORRECT
     ↓
MAKE IT ROBUST
     ↓
MAKE IT PRESENTABLE
```

Never reverse this order.

A beautiful dashboard with a broken pipeline is a failed submission.

---

# 32. Decision Rule When Something Breaks

When blocked by a dependency or model issue:

### First

Try the correct modern implementation.

### Second

Use the simplest compatible fallback.

### Third

Disable only the affected optional feature.

### Never

Spend an hour fighting one library while the rest of the application remains unbuilt.

Example:

```text
pyannote unavailable
        ↓
Do not stop the entire project
        ↓
Implement ASR + VAD + subtitles + QC
        ↓
Return to diarization afterward
```

---

# 33. AI Coding Rules

When generating code:

- Write complete runnable files.
- Do not provide pseudo-code when implementation is expected.
- Do not leave unexplained TODOs in P0 functionality.
- Preserve existing working code.
- Do not rewrite unrelated modules.
- Prefer small, testable functions.
- Use clear type hints.
- Keep configuration centralized.
- Do not hard-code API keys.
- Do not hard-code timestamps.
- Do not hard-code sample transcript content.
- Do not hard-code speaker identities.
- Do not hard-code brand/content-specific logic.
- Do not fake pipeline outputs.

If a feature is mocked, clearly label it as a mock.

---

# 34. AI-Native Requirement

AI must be part of the actual decision-making pipeline.

Do not build:

```text
Traditional subtitle generator
+
"AI" button
```

Instead:

```text
AI ASR
+
AI alignment
+
AI diarization
+
AI translation
+
AI QC reasoning
+
human review
```

The AI components must affect the actual output.

---

# 35. Demo Narrative

The 5-minute demo should follow this sequence:

```text
1. Upload Bengali video

2. Show pipeline processing

3. Show Bengali captions

4. Show speaker attribution

5. Show English + Hindi outputs

6. Open QC dashboard

7. Show a suspicious cue

8. Click it

9. Jump to exact video timestamp

10. Show why it was flagged

11. Download subtitle files + QC report

12. Explain how this prevents unsafe automated subtitle delivery
```

The key story is:

> **We don't just automate subtitle generation. We automate subtitle generation and tell the human exactly where the AI may be wrong.**

---

# 36. Final Hackathon Priorities

If time becomes extremely limited:

### Keep

```text
ASR
Diarization
Bengali VTT
EN/HI subtitles
QC
Review queue
Live demo
```

### Cut

```text
Speaker naming
Advanced analytics
Fancy UI
Extra exports
Optional heuristics
```

### Never cut

```text
Hallucination detection
QC evidence
Live processing
```

---

# 37. Final Rule

The finished system must be something a judge can understand in under one minute.

The judge should immediately see:

```text
BENGALI VIDEO
      ↓
AI UNDERSTANDS IT
      ↓
SUBTITLES GENERATED
      ↓
SPEAKERS IDENTIFIED
      ↓
TRANSLATIONS GENERATED
      ↓
AI CHECKS ITS OWN OUTPUT
      ↓
HUMAN GETS A PRIORITIZED REVIEW QUEUE
```

Build for that experience.

**Do not over-engineer. Do not fake results. Do not sacrifice the working pipeline for optional features.**