import json
import subprocess
from unittest.mock import patch

import pytest
from reelpy.video.reader import VideoMetadata, VideoReader


@pytest.fixture
def mock_metadata():
    """Mock metadata for testing."""
    return {
        "streams": [
            {
                "width": 320,
                "height": 240,
                "r_frame_rate": "30000/1001",
                "codec_name": "h264",
            }
        ],
        "format": {"duration": "3.0", "bit_rate": "500000", "size": "187500"},
    }


class TestVideoMetadata:
    def test_metadata_loading(self, sample_video, mock_metadata):
        """Test basic metadata loading."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = json.dumps(mock_metadata)
            reader = VideoReader(sample_video)

            assert isinstance(reader.metadata, VideoMetadata)
            assert reader.duration == pytest.approx(3.0)
            assert reader.fps == pytest.approx(29.97, rel=0.01)
            assert reader.metadata.width == 320
            assert reader.metadata.height == 240
            assert reader.metadata.codec == "h264"
            assert reader.metadata.bitrate == 500000
            assert reader.metadata.size_bytes == 187500

    def test_metadata_error_handling(self, sample_video):
        """Test handling of metadata loading errors."""
        with patch("subprocess.run") as mock_run:
            # Test JSON decode error
            mock_run.return_value.stdout = "invalid json"
            with pytest.raises(RuntimeError, match="Failed to load video metadata"):
                VideoReader(sample_video)

            # Test empty streams
            mock_run.return_value.stdout = json.dumps({"streams": [], "format": {}})
            with pytest.raises(RuntimeError, match="Invalid video metadata format"):
                VideoReader(sample_video)

            # Test missing required fields
            mock_run.return_value.stdout = json.dumps(
                {"streams": [{"width": 320}], "format": {}}
            )
            with pytest.raises(RuntimeError, match="Invalid video metadata format"):
                VideoReader(sample_video)

            # Test subprocess error
            mock_run.side_effect = subprocess.CalledProcessError(
                1, cmd=[], stderr=b"error"
            )
            with pytest.raises(RuntimeError, match="Failed to load video metadata"):
                VideoReader(sample_video)
