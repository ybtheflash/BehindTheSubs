import logging
from typing import List, Optional
from src.models import WordTimestamp, SubtitleCue, ShotBoundary
from src.config import default_config

logger = logging.getLogger(__name__)

BENGALI_SENTENCE_ENDINGS = ("।", "?", "!", ".", "…")

class SubtitleCueSegmenter:
    """
    Segments word-level timestamps into readable, broadcast-standard subtitle cues.
    Respects speaker turns, natural sentence breaks, CPS, line lengths, and pauses.
    """

    def __init__(
        self,
        max_cps: float = default_config.max_cps,
        max_lines: int = default_config.max_lines,
        max_chars_per_line: int = default_config.max_chars_per_line,
        min_cue_duration: float = default_config.min_cue_duration,
        max_cue_duration: float = default_config.max_cue_duration
    ):
        self.max_cps = max_cps
        self.max_lines = max_lines
        self.max_chars_per_line = max_chars_per_line
        self.min_cue_duration = min_cue_duration
        self.max_cue_duration = max_cue_duration

    def segment(
        self,
        words: List[WordTimestamp],
        shot_boundaries: Optional[List[ShotBoundary]] = None
    ) -> List[SubtitleCue]:
        if not words:
            return []

        cues: List[SubtitleCue] = []
        current_words: List[WordTimestamp] = []
        current_speaker: Optional[str] = None
        cue_index = 1

        for i, word in enumerate(words):
            if not current_words:
                current_words.append(word)
                current_speaker = word.speaker or "SPEAKER_00"
                continue

            prev_word = current_words[-1]
            next_word = words[i + 1] if i + 1 < len(words) else None

            # Conditions to flush current cue:
            speaker_changed = (word.speaker != current_speaker)
            pause_gap = (word.start - prev_word.end) >= 0.75  # 750ms silence pause
            ends_sentence = any(prev_word.word.endswith(punct) for punct in BENGALI_SENTENCE_ENDINGS)
            
            projected_duration = word.end - current_words[0].start
            duration_exceeded = projected_duration > self.max_cue_duration

            # Line & character capacity check
            test_text = " ".join(w.word for w in current_words + [word])
            length_exceeded = len(test_text) > (self.max_chars_per_line * self.max_lines)

            # Shot boundary check
            crosses_shot = False
            if shot_boundaries:
                for shot in shot_boundaries:
                    if prev_word.end <= shot.end <= word.start:
                        crosses_shot = True
                        break

            should_split = (
                speaker_changed or
                duration_exceeded or
                length_exceeded or
                (ends_sentence and (prev_word.end - current_words[0].start) >= self.min_cue_duration) or
                (pause_gap and (prev_word.end - current_words[0].start) >= self.min_cue_duration) or
                crosses_shot
            )

            if should_split and current_words:
                cue = self._build_cue(cue_index, current_words, current_speaker, next_word_start=word.start)
                cues.append(cue)
                cue_index += 1
                current_words = [word]
                current_speaker = word.speaker or "SPEAKER_00"
            else:
                current_words.append(word)

        if current_words:
            cue = self._build_cue(cue_index, current_words, current_speaker, next_word_start=None)
            cues.append(cue)

        logger.info(f"Segmented {len(words)} words into {len(cues)} subtitle cues.")
        return cues

    def _build_cue(
        self,
        index: int,
        words: List[WordTimestamp],
        speaker: str,
        next_word_start: Optional[float] = None
    ) -> SubtitleCue:
        start = words[0].start
        end = words[-1].end

        # Ensure minimum cue duration if gap permits
        raw_duration = end - start
        if raw_duration < self.min_cue_duration:
            needed = self.min_cue_duration - raw_duration
            if next_word_start is not None:
                max_extend = max(0.0, next_word_start - end - 0.05)
                end += min(needed, max_extend)
            else:
                end += needed

        # Format lines nicely
        raw_text = " ".join(w.word for w in words)
        formatted_text = self._format_lines(raw_text)

        return SubtitleCue(
            index=index,
            start=round(start, 3),
            end=round(end, 3),
            speaker=speaker,
            text=formatted_text,
            words=list(words)
        )

    def _format_lines(self, text: str) -> str:
        """
        Wraps text into at most 2 balanced lines without breaking words.
        """
        words = text.split()
        if len(words) <= 4 or len(text) <= self.max_chars_per_line:
            return text

        # Find best split point near the middle
        midpoint = len(text) // 2
        best_split_idx = -1
        min_diff = float("inf")
        current_len = 0

        for i in range(len(words) - 1):
            current_len += len(words[i]) + 1
            diff = abs(current_len - midpoint)
            if diff < min_diff and current_len <= (self.max_chars_per_line + 5):
                min_diff = diff
                best_split_idx = i

        if best_split_idx != -1:
            line1 = " ".join(words[:best_split_idx + 1])
            line2 = " ".join(words[best_split_idx + 1:])
            return f"{line1}\n{line2}"

        return text
