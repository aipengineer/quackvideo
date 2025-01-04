# tests/core/test_models.py

import pytest
from pydantic import ValidationError

from quackvideo.core.operations.models import VideoConfig, AudioConfig


def test_video_config_valid():
    """
    Test a valid VideoConfig instantiation.
    """
    config = VideoConfig(width=1920, height=1080, codec="libx264")
    assert config.width == 1920
    assert config.height == 1080
    assert config.codec == "libx264"


def test_video_config_invalid():
    """
    Ensure invalid parameters raise ValidationError.
    """
    with pytest.raises(ValidationError):
        VideoConfig(width=-100, height=720, codec="")


def test_audio_config_valid():
    """
    Test a valid AudioConfig instantiation.
    """
    config = AudioConfig(sample_rate=44100, channels=2, codec="aac")
    assert config.sample_rate == 44100
    assert config.channels == 2
    assert config.codec == "aac"


def test_audio_config_invalid():
    """
    Ensure invalid parameters raise ValidationError.
    """
    with pytest.raises(ValidationError):
        AudioConfig(sample_rate=0, channels=-1)
