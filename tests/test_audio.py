from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from audio.pipeline import AudioRecorder, convert_wav, record_wav


def make_wav(sample_rate: int = 44_100, seconds: float = 0.02) -> bytes:
    samples = np.zeros(int(sample_rate * seconds), dtype=np.float32)
    output = BytesIO()
    sf.write(output, samples, sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


def test_convert_wav_resamples_and_mono():
    source = make_wav(sample_rate=44_100)

    converted = convert_wav(source, 16_000)

    audio, sample_rate = sf.read(BytesIO(converted), dtype="float32")
    assert sample_rate == 16_000
    assert audio.ndim == 1
    assert len(audio) > 0


def test_convert_wav_rejects_empty_audio():
    output = BytesIO()
    sf.write(output, np.array([], dtype=np.float32), 16_000, format="WAV")

    try:
        convert_wav(output.getvalue(), 16_000)
    except ValueError as error:
        assert str(error) == "Audio cannot be empty"
    else:
        raise AssertionError("Expected ValueError")


@pytest.mark.parametrize("duration", [0, -1])
def test_record_wav_rejects_invalid_time_limits(duration):
    with pytest.raises(ValueError):
        record_wav(duration_seconds=duration)


def test_audio_recorder_rejects_stop_before_start():
    recorder = AudioRecorder()

    with pytest.raises(RuntimeError, match="No recording is in progress"):
        recorder.stop()
