import pytest
import subprocess
from pathlib import Path
import numpy as np

@pytest.fixture(scope="session")
def check_ffmpeg():
    """Check if FFmpeg is available before running tests."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            capture_output=True,
            text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(
            "FFmpeg not available. Please install FFmpeg to run these tests.",
            allow_module_level=True
        )

@pytest.fixture
def sample_video(tmp_path) -> Path:
    """Create a test video file with known properties."""
    video_path = tmp_path / "test_video.mp4"
    
    # Create a video with specific test patterns
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=3:size=320x240:rate=30",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-g", "30",  # Force keyframe every 30 frames
        "-profile:v", "baseline",
        "-preset", "ultrafast",  # Fast encoding for tests
        str(video_path)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        pytest.skip(f"FFmpeg failed to create test video: {e}")
    except FileNotFoundError:
        pytest.skip("FFmpeg not found in system path")
        
    return video_path

@pytest.fixture
def mock_video_info():
    """Mock video information for testing."""
    return {
        "width": 320,
        "height": 240,
        "fps": 30,
        "duration": 3.0,
        "bitrate": 500000,
        "codec": "h264",
        "size": 187500
    }