# tests/conftest.py

import pytest
from pathlib import Path


@pytest.fixture
def temp_output_dir(tmp_path_factory):
    """
    Creates a temporary directory for test outputs, automatically cleaned up.
    """
    dir_path = tmp_path_factory.mktemp("test_outputs")
    return dir_path


# Synthetic fixtures for quick tests:
@pytest.fixture
def small_synth_video():
    """
    Returns a small synthetic video (a few seconds) for testing video-related functionality.
    """
    from quackvideo.synthetic.video import SyntheticVideoGenerator

    generator = SyntheticVideoGenerator(
        width=320,
        height=240,
        duration=3,  # seconds
        fps=10,
    )
    # Assuming generate() returns the path to the generated video file
    video_path = generator.generate()
    return video_path


@pytest.fixture
def small_synth_audio():
    """
    Returns a small synthetic audio clip (a few seconds) for testing audio-related functionality.
    """
    from quackvideo.synthetic.audio import SyntheticAudioGenerator

    generator = SyntheticAudioGenerator(
        duration=3,  # seconds
        sample_rate=16000,
    )
    # Assuming generate() returns the path to the generated audio file
    audio_path = generator.generate()
    return audio_path
