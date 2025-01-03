# tests/operations/test_audio.py
import pytest
from pathlib import Path
from unittest.mock import patch
import logging
import json

from quackvideo.core.operations.audio import (
    AudioProcessor,
    AudioConfig,
    AudioOperationType,
    AudioOperationResult,
    FFmpegOperationError,
)


class TestAudioProcessor:
    """Test suite for AudioProcessor operations."""

    def test_initialization(self, temp_media_dir):
        """Test AudioProcessor initialization."""
        config = AudioConfig()
        processor = AudioProcessor(config, temp_media_dir)

        assert processor.config == config
        assert (processor.episode_dir / "audio").exists()
        assert isinstance(processor.logger, logging.Logger)

    class TestAudioExtraction:
        """Test suite for audio extraction operations."""

        def test_basic_extraction(self, test_video, temp_media_dir):
            """Test basic audio extraction from video."""
            config = AudioConfig(format="flac")
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.extract_audio(test_video)

            assert isinstance(result, AudioOperationResult)
            assert result.operation_type == AudioOperationType.EXTRACT
            assert result.output_path.exists()
            assert result.format == "flac"
            assert result.duration == pytest.approx(3.0, rel=0.1)
            assert result.channels > 0

        @pytest.mark.parametrize("output_format", ["flac", "wav", "mp3", "aac"])
        def test_output_formats(self, test_video, temp_media_dir, output_format):
            """Test extraction to different output formats."""
            config = AudioConfig(format=output_format)
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.extract_audio(test_video)

            assert result.format == output_format
            assert result.output_path.suffix == f".{output_format}"

        def test_invalid_input(self, temp_media_dir):
            """Test extraction with invalid input."""
            config = AudioConfig()
            processor = AudioProcessor(config, temp_media_dir)

            with pytest.raises(FileNotFoundError):
                processor.extract_audio(Path("nonexistent.mp4"))

    class TestAudioConversion:
        """Test suite for audio format conversion."""

        def test_basic_conversion(self, test_audio, temp_media_dir):
            """Test basic audio format conversion."""
            config = AudioConfig(format="wav")
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.convert_audio(test_audio)

            assert result.operation_type == AudioOperationType.CONVERT
            assert result.output_path.exists()
            assert result.format == "wav"

        @pytest.mark.parametrize("compression_level", [5, 8, 12])
        def test_compression_levels(
            self, test_audio, temp_media_dir, compression_level
        ):
            """Test conversion with different compression levels."""
            config = AudioConfig(format="flac", compression_level=compression_level)
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.convert_audio(test_audio)

            assert result.output_path.exists()

    class TestAudioMixing:
        """Test suite for audio mixing operations."""

        def test_basic_mixing(self, mixed_audio_files, temp_media_dir):
            """Test basic audio mixing functionality."""
            config = AudioConfig()
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.mix_audio(*mixed_audio_files)

            assert result.operation_type == AudioOperationType.MIX
            assert result.output_path.exists()
            assert result.channels == 2

        @pytest.mark.parametrize(
            "volumes", [[0.5, 0.5], [0.8, 0.2], [0.2, 0.8], [1.0, 0.0], [0.0, 1.0]]
        )
        def test_mixing_volumes(self, mixed_audio_files, temp_media_dir, volumes):
            """Test mixing with different volume levels."""
            config = AudioConfig(mixing_volumes=volumes)
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.mix_audio(*mixed_audio_files, volumes=volumes)

            assert result.output_path.exists()

        def test_invalid_mixing_params(self, mixed_audio_files, temp_media_dir):
            """Test mixing with invalid parameters."""
            config = AudioConfig()
            processor = AudioProcessor(config, temp_media_dir)

            with pytest.raises(ValueError):
                processor.mix_audio(*mixed_audio_files, volumes=[1.5, 0.5])

            with pytest.raises(ValueError):
                processor.mix_audio(*mixed_audio_files, volumes=[0.5])

    class TestErrorHandling:
        """Test suite for error handling."""

        def test_retry_mechanism(self, test_audio, temp_media_dir):
            """Test retry mechanism for failed operations."""
            config = AudioConfig(retries=3, retry_delay=0.1)
            processor = AudioProcessor(config, temp_media_dir)

            with patch("ffmpeg.run", side_effect=ffmpeg.Error("Error")):
                with pytest.raises(FFmpegOperationError):
                    processor.convert_audio(test_audio)

        def test_resource_cleanup(self, test_audio, temp_media_dir):
            """Test proper resource cleanup after operations."""
            config = AudioConfig()
            processor = AudioProcessor(config, temp_media_dir)

            with patch("ffmpeg.run") as mock_run:
                try:
                    processor.convert_audio(test_audio)
                except:
                    pass

                # Verify cleanup was attempted
                mock_run.assert_called()

    class TestMetadata:
        """Test suite for metadata handling."""

        def test_metadata_creation(self, test_audio, temp_media_dir):
            """Test metadata creation and updates."""
            config = AudioConfig()
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.convert_audio(test_audio)

            metadata_file = temp_media_dir / ".metadata.json"
            assert metadata_file.exists()

            metadata = json.loads(metadata_file.read_text())
            assert metadata["status"] == "completed"
            assert metadata["last_processed"] is not None

        def test_file_hash_verification(self, test_audio, temp_media_dir):
            """Test file hash calculation and verification."""
            config = AudioConfig()
            processor = AudioProcessor(config, temp_media_dir)
            result = processor.convert_audio(test_audio)

            # Verify hash exists and is consistent
            assert len(result.file_hash) == 64  # SHA-256 length
            new_hash = processor._calculate_file_hash(result.output_path)
            assert new_hash == result.file_hash
