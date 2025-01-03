from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from reelpy.video.reader import VideoReader, VideoReaderConfig
from reelpy.video.writer import VideoWriter, VideoWriterConfig


@pytest.fixture
def sample_video(tmp_path) -> Path:
    """Create a test video file."""
    video_path = tmp_path / "test_video.mp4"

    # Generate test video using FFmpeg
    import subprocess

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=3:size=320x240:rate=30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    return video_path


class TestVideoReaderConfig:
    def test_default_config(self):
        """Test default configuration."""
        config = VideoReaderConfig()
        assert config.fps is None
        assert config.start_time is None
        assert config.end_time is None
        assert config.resolution is None

    def test_invalid_fps(self):
        """Test validation of invalid FPS."""
        with pytest.raises(ValidationError):
            VideoReaderConfig(fps=-1)

    def test_invalid_time(self):
        """Test validation of invalid time values."""
        # Test negative end_time
        with pytest.raises(ValueError):
            VideoReaderConfig(end_time=-1)

        # Test end_time <= start_time
        with pytest.raises(ValueError):
            VideoReaderConfig(start_time=1.0, end_time=0.5)

        # Test negative start_time gets clamped to 0
        config = VideoReaderConfig(start_time=-1.0)
        assert config.start_time == 0.0

    def test_invalid_resolution(self):
        """Test validation of invalid resolution."""
        with pytest.raises(ValidationError):
            VideoReaderConfig(resolution=(0, 100))

        with pytest.raises(ValidationError):
            VideoReaderConfig(resolution=(100, -1))


class TestVideoReader:
    def test_file_not_found(self):
        """Test behavior when video file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            VideoReader("nonexistent.mp4")

    def test_read_frames(self, sample_video):
        """Test basic frame reading."""
        reader = VideoReader(sample_video)
        frames = list(reader.read_frames())

        assert len(frames) > 0
        assert all(isinstance(f, np.ndarray) for f in frames)
        assert all(f.shape == (240, 320, 3) for f in frames)

    def test_read_frames_with_config(self, sample_video):
        """Test frame reading with configuration."""
        config = VideoReaderConfig(fps=1, resolution=(160, 120))
        reader = VideoReader(sample_video, config)
        frames = list(reader.read_frames())

        assert len(frames) > 0
        assert all(f.shape == (120, 160, 3) for f in frames)

    def test_extract_frame_at(self, sample_video):
        """Test single frame extraction."""
        reader = VideoReader(sample_video)

        # Test multiple timestamps
        for timestamp in [0.0, 0.5, 1.0, 1.5, 2.0]:
            frame = reader.extract_frame_at(timestamp)
            assert isinstance(frame, np.ndarray)
            assert frame.shape == (240, 320, 3)

        # Test with different resolution
        reader_with_res = VideoReader(
            sample_video, VideoReaderConfig(resolution=(160, 120))
        )
        frame = reader_with_res.extract_frame_at(1.0)
        assert frame.shape == (120, 160, 3)

    def test_extract_frame_at_invalid_time(self, sample_video):
        """Test frame extraction with invalid timestamp."""
        reader = VideoReader(sample_video)

        # Test negative timestamp
        with pytest.raises(ValueError):
            reader.extract_frame_at(-1)

        # Test timestamp beyond video duration
        with pytest.raises(RuntimeError):
            reader.extract_frame_at(1000)


class TestVideoWriterConfig:
    def test_default_config(self):
        """Test default configuration."""
        config = VideoWriterConfig()
        assert config.fps == 30.0
        assert config.codec == "libx264"
        assert config.crf == 23
        assert config.preset == "medium"
        assert config.pixel_format == "yuv420p"

    def test_invalid_fps(self):
        """Test validation of invalid FPS."""
        with pytest.raises(ValidationError):
            VideoWriterConfig(fps=0)

    def test_invalid_crf(self):
        """Test validation of invalid CRF."""
        with pytest.raises(ValidationError):
            VideoWriterConfig(crf=52)

    def test_invalid_preset(self):
        """Test validation of invalid preset."""
        with pytest.raises(ValidationError):
            VideoWriterConfig(preset="invalid")


class TestVideoWriter:
    def test_write_frames(self, tmp_path, sample_video):
        """Test writing frames to video."""
        # First read some frames
        reader = VideoReader(sample_video)
        frames = list(reader.read_frames())

        # Write frames to new video
        output_path = tmp_path / "output.mp4"
        writer = VideoWriter(output_path)
        writer.write_frames(frames)

        assert output_path.exists()

        # Verify the written video
        new_reader = VideoReader(output_path)
        new_frames = list(new_reader.read_frames())
        assert len(new_frames) > 0

    def test_write_empty_frames(self, tmp_path):
        """Test writing empty frames."""
        writer = VideoWriter(tmp_path / "empty.mp4")
        with pytest.raises(ValueError):
            writer.write_frames([])

    def test_write_inconsistent_frames(self, tmp_path):
        """Test writing frames with inconsistent dimensions."""
        frames = [
            np.zeros((240, 320, 3), dtype=np.uint8),
            np.zeros((480, 640, 3), dtype=np.uint8),  # Different dimensions
        ]

        writer = VideoWriter(tmp_path / "inconsistent.mp4")
        with pytest.raises(ValueError):
            writer.write_frames(frames)
