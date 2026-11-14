"""Google's YAMNet audio-event classifier (TFLite), used for its 'Music' score."""

import hashlib
import urllib.request
from pathlib import Path

import numpy as np
from ai_edge_litert.interpreter import Interpreter

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite"
_MODEL_SHA256 = "4d8b4a53282dc83ef04e3e7dbc4fbc98082e34e44ed798e16c3a0cdd4c584faf"
_MUSIC_CLASS = 132
SAMPLE_RATE = 16_000
WINDOW = 15_600  # samples per classification (0.975 s)
HOP = 7_680  # samples between classifications (0.48 s)


def ensure_model(directory: Path) -> Path:
    path = directory / "yamnet.tflite"
    if not path.exists():
        directory.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(MODEL_URL).read()
        if hashlib.sha256(data).hexdigest() != _MODEL_SHA256:
            raise RuntimeError(f"unexpected checksum for the YAMNet model downloaded from {MODEL_URL}")
        path.write_bytes(data)
    return path


def music_probability(samples: np.ndarray, model: Path) -> tuple[np.ndarray, np.ndarray]:
    """P(music) for each window of `samples`, and the time in seconds at the centre of each window."""
    interpreter = Interpreter(model_path=str(model))
    interpreter.allocate_tensors()
    source = interpreter.get_input_details()[0]["index"]
    target = interpreter.get_output_details()[0]["index"]
    count = (len(samples) - WINDOW) // HOP + 1
    scores = np.empty(count)
    for i in range(count):
        interpreter.set_tensor(source, samples[i * HOP : i * HOP + WINDOW])
        interpreter.invoke()
        scores[i] = interpreter.get_tensor(target)[0, _MUSIC_CLASS]
    return scores, (np.arange(count) * HOP + WINDOW / 2) / SAMPLE_RATE
