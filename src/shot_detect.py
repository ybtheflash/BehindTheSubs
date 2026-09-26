import logging
from typing import List
from pathlib import Path
from src.models import ShotBoundary

logger = logging.getLogger(__name__)

class ShotBoundaryDetector:
    """
    Detects scene/shot cuts in video using PySceneDetect.
    Fails gracefully if video processing is unavailable.
    """

    def __init__(self, threshold: float = 27.0):
        self.threshold = threshold

    def detect_shots(self, video_path: str) -> List[ShotBoundary]:
        path = Path(video_path)
        if not path.exists():
            logger.warning(f"Video file does not exist for shot detection: {video_path}")
            return []

        try:
            from scenedetect import detect, ContentDetector
            logger.info(f"Running shot detection on {video_path} with ContentDetector(threshold={self.threshold})")
            scene_list = detect(str(path), ContentDetector(threshold=self.threshold))

            boundaries: List[ShotBoundary] = []
            for scene in scene_list:
                start_sec = round(scene[0].get_seconds(), 3)
                end_sec = round(scene[1].get_seconds(), 3)
                boundaries.append(ShotBoundary(start=start_sec, end=end_sec))

            logger.info(f"Detected {len(boundaries)} shots/scenes.")
            return boundaries
        except Exception as e:
            logger.warning(f"Shot detection failed or skipped: {e}. Continuing without shot boundaries.")
            return []

    @staticmethod
    def crosses_shot_boundary(
        cue_start: float,
        cue_end: float,
        shot_boundaries: List[ShotBoundary],
        margin: float = 0.15
    ) -> bool:
        """
        Returns True if the cue interval [cue_start, cue_end] crosses an internal cut/boundary.
        (i.e. A cut occurs strictly inside the cue with more than margin seconds from edges).
        """
        for shot in shot_boundaries:
            # Cut point is shot.end or next shot.start
            cut = shot.end
            if (cue_start + margin) < cut < (cue_end - margin):
                return True
        return False
