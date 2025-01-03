# tests/conftest.py
import pytest
from pathlib import Path
import subprocess
import numpy as np
from quackvideo.core.operations.models import (
    FFmpegProcessingConfig, 
    FrameExtractionConfig,
    AudioConfig
)
from quackvideo.synthetic.audio import AudioPattern, AudioGenerator, AudioConfig
from quackvideo.synthetic.video import VideoPattern, VideoGenerator, VideoConfig

@pytest.fixture(scope="session")
def check_ffmpeg():
    """Check if FFmpeg is available before running tests."""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("FFmpeg not available. Please install FFmpeg to run these tests.")

@pytest.fixture
def test_video(tmp_path, check_ffmpeg) -> Path:
    """Create a test video with known properties."""
    video_path = tmp_path / "test_video.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=3:size=320x240:rate=30",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-g", "30",  # Force keyframe every 30 frames
        "-preset", "ultrafast",
        str(video_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video_path

@pytest.fixture
def test_audio(tmp_path) -> Path:
    """Create a test audio file with specific properties."""
    config = AudioConfig(
        pattern=AudioPattern.SINE,
        duration=2.0,
        frequency=440.0,
        format="flac"
    )
    generator = AudioGenerator(config)
    return generator.generate(tmp_path / "test.flac")

@pytest.fixture
def mixed_audio_files(tmp_path) -> tuple[Path, Path]:
    """Create two different test audio files for mixing tests."""
    configs = [
        AudioConfig(pattern=AudioPattern.SINE, frequency=440.0),
        AudioConfig(pattern=AudioPattern.WHITE_NOISE)
    ]
    files = []
    for i, config in enumerate(configs):
        generator = AudioGenerator(config)
        files.append(generator.generate(tmp_path / f"test_{i}.flac"))
    return tuple(files)

@pytest.fixture
def test_frames() -> dict[str, np.ndarray]:
    """Generate test frames with known patterns."""
    height, width = 240, 320
    return {
        'black': np.zeros((height, width, 3), dtype=np.uint8),
        'white': np.full((height, width, 3), 255, dtype=np.uint8),
        'gradient': np.tile(np.linspace(0, 255, width, dtype=np.uint8), (height, 1, 3))
    }

@pytest.fixture
def temp_media_dir(tmp_path) -> Path:
    """Create temporary directory structure for media files."""
    media_dir = tmp_path / "media"
    for subdir in ['video', 'audio', 'frames', 'output', 'temp']:
        (media_dir / subdir).mkdir(parents=True)
    return media_dir

@pytest.fixture
def mock_video_info():
    """Mock video metadata for testing."""
    return {
        "streams": [
            {
                "width": 320,
                "height": 240,
                "r_frame_rate": "30000/1001",
                "codec_name": "h264",
            }
        ],
        "format": {
            "duration": "3.0",
            "bit_rate": "500000",
            "size": "187500"
        }
    }

@pytest.fixture
def mock_ffmpeg():
    """Mock FFmpeg for faster testing."""
    with patch("ffmpeg.run") as mock_run:
        mock_run.return_value = (b"", b"")
        yield mock_run