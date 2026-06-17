"""Block B: Speaker diarization scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SpeakerSegment:
    """Represents a diarized speaker segment."""

    start: float
    end: float
    speaker: str


def diarize_audio(audio_path: Path) -> list[SpeakerSegment]:
    """Run speaker diarization and return labeled time segments.

    This scaffold tries to load `pyannote.audio`, but returns a safe mock segment
    if the model is not configured yet.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        from pyannote.audio import Pipeline

        _ = Pipeline  # Structural import placeholder for real integration.
    except Exception:
        return [SpeakerSegment(start=0.0, end=0.0, speaker="SPEAKER_00")]

    # TODO: Replace this placeholder with authenticated pyannote pipeline usage.
    return [SpeakerSegment(start=0.0, end=0.0, speaker="SPEAKER_00")]
