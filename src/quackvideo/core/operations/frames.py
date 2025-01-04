# src/quackvideo/core/operations/frames.py
from __future__ import annotations

import hashlib
from pathlib import Path

import ffmpeg
from pydantic import BaseModel

from .base import FFmpegOperation, FFmpegOperationError
from .models import FrameExtractionConfig, MediaType, ProcessingMetadata


class FrameExtractionResult(BaseModel):
    """Result of frame extraction operation."""

    total_frames: int
    output_directory: Path
    frame_files: dict[str, str]  # filename -> hash


class FrameExtractor(FFmpegOperation[FrameExtractionConfig, FrameExtractionResult]):
    """Handles video frame extraction operations."""

    def __init__(
        self,
        config: FrameExtractionConfig,
        episode_dir: Path,
    ) -> None:
        """
        Initialize frame extractor.

        Args:
            config: Frame extraction configuration
            episode_dir: Directory for episode files
        """
        super().__init__(config, episode_dir)
        self._frames_processed = 0

    def _create_output_directory(self, video_path: Path) -> Path:
        """Create directory for extracted frames."""
        output_dir = self.episode_dir / "frames" / video_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _calculate_frame_hash(self, frame_path: Path) -> str:
        """Calculate SHA-256 hash of a frame file."""
        sha256_hash = hashlib.sha256()
        with frame_path.open("rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _verify_existing_frames(
        self, output_dir: Path, metadata: ProcessingMetadata
    ) -> dict[str, str]:
        """
        Verify integrity of existing frames.

        Returns:
            Dict mapping filename to hash for valid frames
        """
        valid_frames = {}
        existing_frames = list(output_dir.glob(f"frame_*.{self.config.format}"))

        if not existing_frames:
            return {}

        self.logger.info(f"Found {len(existing_frames)} existing frames")

        for frame_path in existing_frames:
            try:
                current_hash = self._calculate_frame_hash(frame_path)
                stored_hash = metadata.frame_integrity.get(frame_path.name)

                if stored_hash and current_hash == stored_hash:
                    valid_frames[frame_path.name] = current_hash
                else:
                    self.logger.warning(
                        f"Frame integrity check failed for {frame_path.name}, "
                        "will re-extract"
                    )
                    frame_path.unlink()
            except Exception as e:
                self.logger.error(f"Error verifying frame {frame_path}: {e}")
                frame_path.unlink()

        return valid_frames

    def _build_ffmpeg_stream(self, input_path: Path) -> ffmpeg.Stream:
        """Build FFmpeg stream for frame extraction."""
        stream = ffmpeg.input(str(input_path))

        # Apply fps filter
        stream = stream.filter("fps", fps=self.config.fps)

        # Get frame count using ffprobe
        probe = ffmpeg.probe(str(input_path))
        video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")

        try:
            # Try to get frame count directly
            self._total_frames = int(video_info["nb_frames"])
        except KeyError:
            # Calculate frame count from duration and fps if nb_frames not available
            duration = float(video_info["duration"])
            fps_num, fps_den = map(int, self.config.fps.split("/"))
            self._total_frames = int(duration * fps_num / fps_den)

        return stream

    def _process_output(
        self, result: Any, metadata: ProcessingMetadata
    ) -> FrameExtractionResult:
        """Process extracted frames and update metadata."""
        frame_files = {}
        for frame_path in sorted(
            self._output_dir.glob(f"frame_*.{self.config.format}")
        ):
            frame_hash = self._calculate_frame_hash(frame_path)
            frame_files[frame_path.name] = frame_hash
            metadata.frame_integrity[frame_path.name] = frame_hash

        metadata.total_frames = self._total_frames
        metadata.completed_frames = len(frame_files)
        metadata.last_processed = max(frame_files.keys(), default=None)

        self._create_metadata_file(metadata)

        return FrameExtractionResult(
            total_frames=self._total_frames,
            output_directory=self._output_dir,
            frame_files=frame_files,
        )

    def extract_frames(
        self,
        video_path: Path,
        resume: bool = True,
    ) -> FrameExtractionResult:
        """
        Extract frames from a video file.

        Args:
            video_path: Path to video file
            resume: Whether to resume from previous extraction

        Returns:
            FrameExtractionResult with extraction details
        """
        self._output_dir = self._create_output_directory(video_path)

        # Load or create metadata
        metadata_file = self.episode_dir / ".metadata.json"
        if metadata_file.exists() and resume:
            metadata = ProcessingMetadata.model_validate_json(metadata_file.read_text())
            valid_frames = self._verify_existing_frames(self._output_dir, metadata)

            if valid_frames:
                self.logger.info(
                    f"Resuming extraction with {len(valid_frames)} valid frames"
                )
        else:
            metadata = ProcessingMetadata()
            valid_frames = {}

        try:
            # Build FFmpeg command
            stream = self._build_ffmpeg_stream(video_path)

            # Set up output pattern for frames
            output_pattern = str(self._output_dir / f"frame_%04d.{self.config.format}")

            # Configure output options based on format
            if self.config.format == "png":
                stream = ffmpeg.output(
                    stream,
                    output_pattern,
                    vcodec="png",
                    compression_level=str(int((100 - self.config.quality) / 100 * 9)),
                )
            elif self.config.format == "jpg" or self.config.format == "jpeg":
                stream = ffmpeg.output(
                    stream,
                    output_pattern,
                    vcodec="mjpeg",
                    qscale=str(int((100 - self.config.quality) / 100 * 31)),
                )
            else:
                raise FFmpegOperationError(
                    f"Unsupported output format: {self.config.format}"
                )

            # Execute frame extraction
            return self.execute_with_retry(
                video_path,
                MediaType.VIDEO,
                "frame_extraction",
                progress_desc="Extracting frames",
            )

        except Exception as e:
            self.logger.error(f"Frame extraction failed: {e}")
            metadata.status = "failed"
            self._create_metadata_file(metadata)
            raise
