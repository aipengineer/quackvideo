# Updated `test_frame_extraction.py`
import logging
import json
import pytest
from unittest.mock import patch, Mock
import numpy as np
from pathlib import Path

from reelpy.video.reader import VideoReader, VideoReaderConfig, VideoMetadata

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@pytest.fixture
def video_metadata():
    return VideoMetadata(
        duration=3.0,
        fps=30.0,
        width=320,
        height=240,
        bitrate=500000,
        codec="h264",
        size_bytes=187500
    )

@pytest.fixture
def mock_ffmpeg_setup():
    """Set up FFmpeg mocking."""
    with patch('subprocess.run') as mock_run, \
         patch('subprocess.Popen') as mock_popen, \
         patch('pathlib.Path.exists', return_value=True):
        
        # Mock video info response
        mock_run.return_value = Mock(stdout=json.dumps({
            "streams": [{"width": 320, "height": 240}],
            "frames": [{"pkt_pts_time": str(i), "flags": "K"} for i in range(3)]
        }))

        # Create mock process
        mock_process = Mock()
        mock_process.stdout.read.side_effect = lambda size: np.zeros((240, 320, 3), dtype=np.uint8).tobytes() if size == 230400 else b""
        mock_process.stderr.readline.return_value = b""
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process

        yield mock_run, mock_popen

class TestFrameExtraction:
    @pytest.mark.timeout(10)  # Set a timeout of 10 seconds
    def test_extract_keyframes(self, mock_ffmpeg_setup, video_metadata):
        """Test keyframe extraction."""
        mock_run, mock_popen = mock_ffmpeg_setup

        with patch('quackvideo.video.reader.VideoReader._load_metadata', return_value=video_metadata):
            logger.debug("Starting keyframe extraction")
            reader = VideoReader("test.mp4", skip_validation=True)
            keyframes = list(reader.extract_keyframes())
            logger.debug("Finished keyframe extraction")

            assert len(keyframes) == 3

            for ts, frame in keyframes:
                assert isinstance(ts, float)
                assert isinstance(frame, np.ndarray)
                assert frame.shape == (240, 320, 3)

    @pytest.mark.timeout(10)  # Set a timeout of 10 seconds
    def test_extract_scene_changes(self, mock_ffmpeg_setup, video_metadata):
        """Test scene change detection."""
        mock_run, mock_popen = mock_ffmpeg_setup

        with patch('quackvideo.video.reader.VideoReader._load_metadata', return_value=video_metadata):
            reader = VideoReader("test.mp4", skip_validation=True)
            scenes = list(reader.extract_scene_changes(threshold=0.3))

            assert len(scenes) == 2
            timestamps = [t for t, _ in scenes]
            assert timestamps == pytest.approx([1.0, 2.0])

    @pytest.mark.timeout(10)  # Set a timeout of 10 seconds
    def test_extract_frame_sequence(self, mock_ffmpeg_setup, video_metadata):
        """Test frame sequence extraction."""
        mock_run, mock_popen = mock_ffmpeg_setup

        with patch('quackvideo.video.reader.VideoReader._load_metadata', return_value=video_metadata):
            reader = VideoReader("test.mp4", skip_validation=True)

            def test_sequence(timestamp: float, count: int, direction: str, expected_times: list[float]):
                frames = list(reader.extract_frame_sequence(timestamp, count, direction))
                assert len(frames) == count
                timestamps = [float(t) for t, _ in frames]
                assert timestamps == pytest.approx(expected_times, abs=1e-6)

                for _, frame in frames:
                    assert isinstance(frame, np.ndarray)
                    assert frame.shape == (240, 320, 3)

            # Test sequences
            test_sequence(1.0, 5, "both", [1.0 - 2/30, 1.0 - 1/30, 1.0, 1.0 + 1/30, 1.0 + 2/30])
            test_sequence(1.0, 3, "forward", [1.0, 1.0 + 1/30, 1.0 + 2/30])
            test_sequence(1.0, 3, "backward", [1.0 - 2/30, 1.0 - 1/30, 1.0])
