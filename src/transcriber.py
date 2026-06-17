"""Block A: YouTube audio extraction and ASR transcription."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TranscriptSegment:
    """A single transcription segment with timing."""

    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptResult:
    """Container for full transcript text plus per-segment details."""

    full_text: str
    segments: list[TranscriptSegment]


def download_youtube_audio(url: str, output_dir: Path) -> Path:
    """Download a YouTube video's best audio stream and convert it to WAV."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise ImportError(
            "yt-dlp is required for downloading YouTube audio. Install dependencies from requirements.txt."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = output_dir / "%(id)s.%(ext)s"

    ydl_opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(output_template),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = info.get("id")
    if not video_id:
        raise ValueError("Could not extract video id from YouTube metadata.")

    wav_path = output_dir / f"{video_id}.wav"
    if not wav_path.exists():
        raise FileNotFoundError(f"Expected WAV output not found at {wav_path}.")

    return wav_path


class FasterWhisperTranscriber:
    """Wrapper around faster-whisper for timestamped transcription."""

    def __init__(self, model_size: str = "small", device: str = "cpu") -> None:
        self.model_size = model_size
        self.device = device

    def transcribe(self, audio_path: Path, language: str | None = None) -> TranscriptResult:
        """Transcribe audio and return full text plus timestamped segments."""
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ImportError(
                "faster-whisper is required for transcription. Install dependencies from requirements.txt."
            ) from exc

        model = WhisperModel(self.model_size, device=self.device)
        segments_iterable, _info = model.transcribe(str(audio_path), language=language)

        segments: list[TranscriptSegment] = []
        for segment in segments_iterable:
            text = segment.text.strip()
            segments.append(
                TranscriptSegment(start=float(segment.start), end=float(segment.end), text=text)
            )

        full_text = " ".join(segment.text for segment in segments).strip()
        return TranscriptResult(full_text=full_text, segments=segments)
