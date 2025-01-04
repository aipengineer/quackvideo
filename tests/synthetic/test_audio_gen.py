# tests/synthetic/test_audio_gen.py

import pytest
from quackvideo.synthetic.audio import SyntheticAudioGenerator
from quackvideo.core.utils import get_media_metadata


def test_synthetic_audio_generator_basic():
    """
    Test generation of a short synthetic audio clip, verifying metadata.
    """
    gen = SyntheticAudioGenerator(duration=2, sample_rate=8000)
    out_audio = gen.generate()
    assert out_audio is not None, "Should return an audio file path."
    meta = get_media_metadata(out_audio)
    assert meta["duration"] == pytest.approx(2, 0.5), "Duration should be ~2s."
    assert meta["sample_rate"] == 8000, "Sample rate should match the generator."
