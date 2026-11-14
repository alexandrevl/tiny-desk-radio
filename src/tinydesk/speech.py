"""Local speech-to-text with mlx-whisper (macOS on Apple Silicon): what is sung and said, with times."""

import numpy as np

from tinydesk.lyrics import Phrase

MODEL = "mlx-community/whisper-large-v3-turbo"


def transcribe(samples: np.ndarray, language: str) -> list[Phrase]:
    try:
        import mlx_whisper
    except ImportError as error:
        raise RuntimeError(
            "transcription needs mlx-whisper, which only installs on macOS with Apple Silicon"
        ) from error
    result = mlx_whisper.transcribe(
        samples, path_or_hf_repo=MODEL, language=language, condition_on_previous_text=False, verbose=None
    )
    return [Phrase(s["start"], s["end"], s["text"].strip()) for s in result["segments"] if s["text"].strip()]
