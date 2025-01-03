# tests/core/test_models.py
import pytest
from pathlib import Path
from datetime import datetime
from pydantic import ValidationError

from quackvideo.core.operations.models import (
    MediaType,
    FFmpegBaseConfig,
    FrameExtractionConfig,
    AudioConfig,
    OutputMetadata,
    ProcessingMetadata,
    FFmpegProcessingConfig
)

class TestMediaType:
    def test_media_types(self):
        """Test media type enumeration."""
        assert MediaType.VIDEO.value == "video"
        assert MediaType.AUDIO.value == "audio"
        assert len(MediaType) == 2

class TestFFmpegBaseConfig:
    def test_default_values(self):
        """Test default configuration values."""
        config = FFmpegBaseConfig()
        assert config.timeout == 10
        assert config.retries == 5
        assert config.retry_delay == 1.0

    def test_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValidationError):
            FFmpegBaseConfig(timeout=-1)
        
        with pytest.raises(ValidationError):
            FFmpegBaseConfig(retries=0)
        
        with pytest.raises(ValidationError):
            FFmpegBaseConfig(retry_delay=-1.0)

class TestFrameExtractionConfig:
    def test_default_values(self):
        """Test default frame extraction configuration."""
        config = FrameExtractionConfig()
        assert config.fps == "1/5"
        assert config.format == "png"
        assert config.quality == 100

    @pytest.mark.parametrize("fps", [
        "1/1",
        "1/30",
        "24/1",
        "30/1",
        "60/1"
    ])
    def test_valid_fps_values(self, fps):
        """Test valid FPS specifications."""
        config = FrameExtractionConfig(fps=fps)
        assert config.fps == fps

    @pytest.mark.parametrize("invalid_fps", [
        "0/1",
        "1/0",
        "-1/1",
        "invalid",
        "30",
    ])
    def test_invalid_fps_values(self, invalid_fps):
        """Test invalid FPS specifications."""
        with pytest.raises(ValidationError):
            FrameExtractionConfig(fps=invalid_fps)

    @pytest.mark.parametrize("format,quality", [
        ("png", 100),
        ("jpg", 90),
        ("jpeg", 75),
        ("png", 50),
    ])
    def test_format_quality_combinations(self, format, quality):
        """Test various format and quality combinations."""
        config = FrameExtractionConfig(format=format, quality=quality)
        assert config.format == format
        assert config.quality == quality

    def test_invalid_quality(self):
        """Test quality validation."""
        with pytest.raises(ValidationError):
            FrameExtractionConfig(quality=101)
        with pytest.raises(ValidationError):
            FrameExtractionConfig(quality=0)

class TestAudioConfig:
    def test_default_values(self):
        """Test default audio configuration."""
        config = AudioConfig()
        assert config.format == "flac"
        assert config.compression_level == 8
        assert config.mixing_volumes == [0.10, 0.90]

    @pytest.mark.parametrize("format", ["flac", "wav", "mp3", "aac"])
    def test_valid_formats(self, format):
        """Test valid audio formats."""
        config = AudioConfig(format=format)
        assert config.format == format

    def test_compression_validation(self):
        """Test compression level validation."""
        with pytest.raises(ValidationError):
            AudioConfig(compression_level=13)
        with pytest.raises(ValidationError):
            AudioConfig(compression_level=-1)

    def test_volume_validation(self):
        """Test mixing volume validation."""
        with pytest.raises(ValidationError):
            AudioConfig(mixing_volumes=[1.5, 0.5])
        with pytest.raises(ValidationError):
            AudioConfig(mixing_volumes=[-0.1, 0.5])
        with pytest.raises(ValidationError):
            AudioConfig(mixing_volumes=[0.5])  # Wrong length

class TestOutputMetadata:
    def test_metadata_creation(self):
        """Test output metadata creation."""
        metadata = OutputMetadata(
            original_filename="test.mp4",
            operation_type="frame_extraction",
            output_path=Path("/tmp/output")
        )
        assert isinstance(metadata.timestamp, datetime)
        assert metadata.original_filename == "test.mp4"
        assert metadata.operation_type == "frame_extraction"

    def test_filename_generation(self):
        """Test filename generation with timestamps."""
        metadata = OutputMetadata(
            original_filename="test video.mp4",
            operation_type="frame_extraction",
            output_path=Path("/tmp/output")
        )
        filename = metadata.filename
        assert isinstance(filename, str)
        assert "test%20video.mp4" in filename
        assert metadata.timestamp.strftime("%Y-%m-%d") in filename

class TestProcessingMetadata:
    def test_default_values(self):
        """Test default processing metadata."""
        metadata = ProcessingMetadata()
        assert metadata.completed_frames == 0
        assert metadata.status == "in_progress"
        assert isinstance(metadata.frame_integrity, dict)
        assert metadata.last_processed is None

    def test_frame_tracking(self):
        """Test frame tracking validation."""
        metadata = ProcessingMetadata(total_frames=10)
        assert metadata.total_frames == 10
        
        metadata.completed_frames = 5
        assert metadata.completed_frames == 5
        
        with pytest.raises(ValidationError):
            metadata.completed_frames = 11  # Can't complete more than total

    def test_integrity_tracking(self):
        """Test frame integrity tracking."""
        metadata = ProcessingMetadata()
        metadata.frame_integrity["frame_001.png"] = "hash1"
        metadata.frame_integrity["frame_002.png"] = "hash2"
        
        assert len(metadata.frame_integrity) == 2
        assert metadata.frame_integrity["frame_001.png"] == "hash1"

class TestFFmpegProcessingConfig:
    def test_default_values(self):
        """Test default FFmpeg processing configuration."""
        config = FFmpegProcessingConfig()
        assert isinstance(config.frame_extraction, FrameExtractionConfig)
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.compatible_formats, dict)

    def test_format_validation(self):
        """Test format compatibility validation."""
        with pytest.raises(ValidationError):
            FFmpegProcessingConfig(compatible_formats={"video": []})
        
        with pytest.raises(ValidationError):
            FFmpegProcessingConfig(compatible_formats={})

    def test_format_compatibility(self):
        """Test format compatibility checking."""
        config = FFmpegProcessingConfig()
        
        # Video formats
        assert ".mp4" in config.compatible_formats["video"]
        assert ".mov" in config.compatible_formats["video"]
        
        # Audio formats
        assert ".wav" in config.compatible_formats["audio"]
        assert ".flac" in config.compatible_formats["audio"]

    def test_config_updating(self):
        """Test configuration updating."""
        config = FFmpegProcessingConfig()
        
        # Update frame extraction settings
        config.frame_extraction.fps = "1/1"
        assert config.frame_extraction.fps == "1/1"
        
        # Update audio settings
        config.audio.format = "wav"
        assert config.audio.format == "wav"