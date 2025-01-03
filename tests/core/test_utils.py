# tests/core/test_utils.py
import numpy as np
import pytest
from pathlib import Path
from datetime import datetime

from quackvideo.core.utils import (
    calculate_frame_difference,
    detect_black_frames,
    detect_scene_change,
    extract_frame_features,
    find_similar_frames,
    get_file_hash,
    validate_file_type,
    parse_progress_line,
)


@pytest.fixture
def sample_frames():
    """Create sample frames for testing."""
    height, width = 240, 320

    frames = {
        "black": np.zeros((height, width, 3), dtype=np.uint8),
        "white": np.full((height, width, 3), 255, dtype=np.uint8),
        "gradient": np.tile(np.linspace(0, 255, width, dtype=np.uint8), (height, 1, 3)),
        "random": np.random.randint(0, 256, (height, width, 3), dtype=np.uint8),
    }
    return frames


class TestFrameAnalysis:
    def test_frame_difference_calculation(self, sample_frames):
        """Test different methods of frame difference calculation."""
        black = sample_frames["black"]
        white = sample_frames["white"]

        # Test MSE
        mse = calculate_frame_difference(black, white, method="mse")
        assert mse == pytest.approx(65025.0)  # (255^2 for black vs white)

        # Test MAE
        mae = calculate_frame_difference(black, white, method="mae")
        assert mae == pytest.approx(255.0)

        # Test SSIM
        ssim = calculate_frame_difference(black, white, method="ssim")
        assert 0 <= ssim <= 1

        # Test invalid method
        with pytest.raises(ValueError):
            calculate_frame_difference(black, white, method="invalid")

    @pytest.mark.parametrize("threshold", [10.0, 30.0, 50.0])
    def test_black_frame_detection(self, sample_frames, threshold):
        """Test black frame detection with different thresholds."""
        assert detect_black_frames(sample_frames["black"], threshold)
        assert not detect_black_frames(sample_frames["white"], threshold)
        assert not detect_black_frames(sample_frames["gradient"], threshold)

    @pytest.mark.parametrize(
        "method,threshold", [("mse", 1000), ("mae", 50), ("ssim", 0.5)]
    )
    def test_scene_change_detection(self, sample_frames, method, threshold):
        """Test scene change detection with different methods and thresholds."""
        assert detect_scene_change(
            sample_frames["black"],
            sample_frames["white"],
            threshold=threshold,
            method=method,
        )

        assert not detect_scene_change(
            sample_frames["black"],
            sample_frames["black"],
            threshold=threshold,
            method=method,
        )


class TestFrameFeatures:
    def test_histogram_features(self, sample_frames):
        """Test histogram feature extraction."""
        features = extract_frame_features(sample_frames["gradient"], method="histogram")
        assert isinstance(features, np.ndarray)
        assert features.shape == (256 * 3,)  # RGB histogram
        assert features.dtype == np.float32

    def test_average_color(self, sample_frames):
        """Test average color feature extraction."""
        features = extract_frame_features(
            sample_frames["white"], method="average_color"
        )
        assert isinstance(features, np.ndarray)
        assert features.shape == (3,)  # RGB averages
        assert np.all(features == 255)  # White frame

    def test_invalid_feature_method(self, sample_frames):
        """Test invalid feature extraction method."""
        with pytest.raises(ValueError):
            extract_frame_features(sample_frames["black"], method="invalid")


class TestFrameSimilarity:
    def test_similar_frame_finding(self, sample_frames):
        """Test finding similar frames."""
        frames = [
            (0.0, sample_frames["black"]),
            (1.0, sample_frames["black"].copy()),  # Similar
            (2.0, sample_frames["white"]),  # Different
            (3.0, sample_frames["gradient"]),  # Different
        ]

        similar = list(
            find_similar_frames(
                sample_frames["black"], iter(frames), threshold=0.1, method="mse"
            )
        )

        assert len(similar) == 2  # Original and copy
        assert all(score <= 0.1 for _, _, score in similar)


class TestFileUtils:
    def test_file_hash_calculation(self, tmp_path):
        """Test file hash calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        hash1 = get_file_hash(test_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 length

        # Test consistency
        hash2 = get_file_hash(test_file)
        assert hash1 == hash2

        # Test different content
        test_file.write_text("different content")
        hash3 = get_file_hash(test_file)
        assert hash1 != hash3

    def test_file_type_validation(self, tmp_path):
        """Test file type validation."""
        video_file = tmp_path / "test.mp4"
        video_file.touch()

        audio_file = tmp_path / "test.flac"
        audio_file.touch()

        # Test valid extensions
        assert validate_file_type(video_file, [".mp4", ".mov"])
        assert validate_file_type(audio_file, [".flac", ".wav"])

        # Test invalid extensions
        assert not validate_file_type(video_file, [".avi"])
        assert not validate_file_type(audio_file, [".mp3"])


class TestProgressParsing:
    @pytest.mark.parametrize(
        "line,expected",
        [
            (
                b"frame=  123 fps=30 q=28.0 size=    384kB time=00:00:04.12 bitrate= 763.9kbits/s",
                {"frame": 123, "fps": 30, "time": 4.12, "size": 384, "bitrate": 763.9},
            ),
            (
                b"frame=  456 fps=29.97 q=-1.0 size=    768kB time=00:00:15.00 bitrate= 419.4kbits/s",
                {
                    "frame": 456,
                    "fps": 29.97,
                    "time": 15.0,
                    "size": 768,
                    "bitrate": 419.4,
                },
            ),
        ],
    )
    def test_progress_line_parsing(self, line, expected):
        """Test FFmpeg progress line parsing."""
        result = parse_progress_line(line)
        for key, value in expected.items():
            assert result[key] == pytest.approx(value, rel=1e-2)

    def test_invalid_progress_line(self):
        """Test parsing invalid progress lines."""
        invalid_lines = [
            b"",
            b"invalid",
            b"frame= abc fps=30",
        ]
        for line in invalid_lines:
            result = parse_progress_line(line)
            assert result == {}
