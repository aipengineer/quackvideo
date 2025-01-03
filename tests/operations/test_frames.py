# tests/operations/test_frames.py
import pytest
import json
from pathlib import Path
from unittest.mock import patch

from quackvideo.core.operations.frames import (
    FrameExtractor,
    FrameExtractionConfig,
    FrameExtractionResult,
    FFmpegOperationError
)

class TestFrameExtractor:
    """Test suite for frame extraction operations."""

    def test_initialization(self, temp_media_dir):
        """Test FrameExtractor initialization."""
        config = FrameExtractionConfig()
        extractor = FrameExtractor(config, temp_media_dir)
        
        assert extractor.config == config
        assert (extractor.episode_dir / "frames").exists()
        assert isinstance(extractor.logger, logging.Logger)

    class TestBasicExtraction:
        """Test suite for basic frame extraction operations."""

        def test_basic_extraction(self, test_video, temp_media_dir):
            """Test basic frame extraction functionality."""
            config = FrameExtractionConfig(fps="1/1")
            extractor = FrameExtractor(config, temp_media_dir)
            result = extractor.extract_frames(test_video)
            
            assert isinstance(result, FrameExtractionResult)
            assert result.total_frames > 0
            assert result.output_directory.exists()
            assert len(list(result.output_directory.glob("*.png"))) == result.total_frames

        @pytest.mark.parametrize("fps,expected_count", [
            ("1/1", 3),    # 1 frame per second for 3-second video
            ("1/2", 2),    # 1 frame every 2 seconds
            ("2/1", 6),    # 2 frames per second
            ("1/3", 1),    # 1 frame every 3 seconds
            ("30/1", 90),  # 30 frames per second
        ])
        def test_fps_variations(self, test_video, temp_media_dir, fps, expected_count):
            """Test extraction with different FPS settings."""
            config = FrameExtractionConfig(fps=fps)
            extractor = FrameExtractor(config, temp_media_dir)
            result = extractor.extract_frames(test_video)
            
            assert result.total_frames == expected_count
            assert len(list(result.output_directory.glob("*.png"))) == expected_count

    class TestOutputFormats:
        """Test suite for different output formats."""

        @pytest.mark.parametrize("format,quality", [
            ("png", 100),
            ("jpg", 95),
            ("png", 50),
            ("jpg", 75)
        ])
        def test_format_quality_combinations(self, test_video, temp_media_dir, format, quality):
            """Test different format and quality combinations."""
            config = FrameExtractionConfig(format=format, quality=quality)
            extractor = FrameExtractor(config, temp_media_dir)
            result = extractor.extract_frames(test_video)
            
            # Verify file format
            frames = list(result.output_directory.glob(f"*.{format}"))
            assert len(frames) > 0
            assert all(f.suffix == f".{format}" for f in frames)

        def test_invalid_format(self, test_video, temp_media_dir):
            """Test handling of invalid output format."""
            config = FrameExtractionConfig(format="invalid")
            extractor = FrameExtractor(config, temp_media_dir)
            
            with pytest.raises(FFmpegOperationError):
                extractor.extract_frames(test_video)

    class TestFrameIntegrity:
        """Test suite for frame integrity verification."""

        def test_hash_verification(self, test_video, temp_media_dir):
            """Test frame hash calculation and verification."""
            config = FrameExtractionConfig()
            extractor = FrameExtractor(config, temp_media_dir)
            result = extractor.extract_frames(test_video)
            
            # Verify each frame's hash
            for filename, hash_value in result.frame_files.items():
                frame_path = result.output_directory / filename
                assert frame_path.exists()
                current_hash = extractor._calculate_frame_hash(frame_path)
                assert current_hash == hash_value

        def test_corrupted_frame_handling(self, test_video, temp_media_dir):
            """Test handling of corrupted frames during verification."""
            config = FrameExtractionConfig()
            extractor = FrameExtractor(config, temp_media_dir)
            result = extractor.extract_frames(test_video)
            
            # Corrupt a frame
            frame_path = next(result.output_directory.glob("*.png"))
            frame_path.write_bytes(b"corrupted data")
            
            # Attempt to verify frames
            valid_frames = extractor._verify_existing_frames(
                result.output_directory,
                ProcessingMetadata(frame_integrity=result.frame_files)
            )
            
            assert len(valid_frames) == result.total_frames - 1

    class TestResumeCapability:
        """Test suite for resume functionality."""

        def test_basic_resume(self, test_video, temp_media_dir):
            """Test basic resume functionality."""
            config = FrameExtractionConfig()
            extractor = FrameExtractor(config, temp_media_dir)
            
            # Initial extraction
            result1 = extractor.extract_frames(test_video)
            original_frames = set(result1.frame_files.keys())
            
            # Delete some frames
            for frame in list(result1.output_directory.glob("*.png"))[:2]:
                frame.unlink()
            
            # Resume extraction
            result2 = extractor.extract_frames(test_video, resume=True)
            final_frames = set(result2.frame_files.keys())
            
            assert final_frames == original_frames

        def test_resume_with_corrupted_metadata(self, test_video, temp_media_dir):
            """Test resume with corrupted metadata."""
            config = FrameExtractionConfig()
            extractor = FrameExtractor(config, temp_media_dir)
            
            # Initial extraction
            result1 = extractor.extract_frames(test_video)
            
            # Corrupt metadata
            metadata_file = temp_media_dir / ".metadata.json"
            metadata_file.write_text("corrupted json")
            
            # Resume should start fresh
            result2 = extractor.extract_frames(test_video, resume=True)
            assert len(result2.frame_files) == result1.total_frames

    class TestErrorHandling:
        """Test suite for error handling."""

        def test_invalid_input(self, temp_media_dir):
            """Test handling of invalid input files."""
            config = FrameExtractionConfig()
            extractor = FrameExtractor(config, temp_media_dir)
            
            with pytest.raises(FileNotFoundError):
                extractor.extract_frames(Path("nonexistent.mp4"))
            
            # Test corrupt file
            invalid_file = temp_media_dir / "invalid.mp4"
            invalid_file.write_bytes(b"not a video file")
            with pytest.raises(FFmpegOperationError):
                extractor.extract_frames(invalid_file)

        def test_retry_mechanism(self, test_video, temp_media_dir):
            """Test retry mechanism for failed operations."""
            config = FrameExtractionConfig(retries=3, retry_delay=0.1)
            extractor = FrameExtractor(config, temp_media_dir)
            
            with patch('ffmpeg.run', side_effect=ffmpeg.Error("Error")):
                with pytest.raises(FFmpegOperationError):
                    extractor.extract_frames(test_video)

    class TestProgress:
        """Test suite for progress tracking."""

        def test_progress_tracking(self, test_video, temp_media_dir):
            """Test progress tracking during extraction."""
            config = FrameExtractionConfig()
            extractor = FrameExtractor(config, temp_media_dir)
            
            progress_updates = []
            def progress_callback(progress):
                progress_updates.append(progress)
            
            result = extractor.extract_frames(
                test_video,
                progress_callback=progress_callback
            )
            
            assert len(progress_updates) > 0
            assert all("frame" in update for update in progress_updates)
            assert progress_updates[-1]["frame"] == result.total_frames