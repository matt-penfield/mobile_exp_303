import numpy as np
import librosa


# Krumhansl-Schmuckler key profiles
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _detect_key(chroma: np.ndarray) -> tuple[str, str, float]:
    """
    Detect musical key using chroma features and Krumhansl-Schmuckler algorithm.
    Returns (note_name, mode, correlation_confidence).
    """
    # Average chroma across time
    chroma_avg = np.mean(chroma, axis=1)

    best_corr = -1
    best_key = 0
    best_mode = "major"

    for i in range(12):
        # Rotate profile to test each key
        major_rotated = np.roll(MAJOR_PROFILE, i)
        minor_rotated = np.roll(MINOR_PROFILE, i)

        major_corr = np.corrcoef(chroma_avg, major_rotated)[0, 1]
        minor_corr = np.corrcoef(chroma_avg, minor_rotated)[0, 1]

        if major_corr > best_corr:
            best_corr = major_corr
            best_key = i
            best_mode = "major"

        if minor_corr > best_corr:
            best_corr = minor_corr
            best_key = i
            best_mode = "minor"

    return NOTE_NAMES[best_key], best_mode, float(best_corr)


def analyze_audio(audio_path: str) -> dict:
    """
    Analyze audio file for key and tempo.
    Returns dict with key, mode, bpm, and confidence values.
    """
    # Load audio (mono, 22050 Hz sample rate — librosa default)
    y, sr = librosa.load(audio_path, sr=22050, mono=True)

    # Key detection via chroma features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    key, mode, key_confidence = _detect_key(chroma)

    # Tempo detection
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])

    # Round BPM to nearest integer
    bpm = round(bpm)

    return {
        "key": key,
        "mode": mode,
        "bpm": bpm,
        "key_confidence": round(key_confidence, 3),
    }
