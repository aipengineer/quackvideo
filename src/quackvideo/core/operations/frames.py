# src/quackvideo/core/operations/frames.py
from __future__ import annotations

import hashlib
from pathlib import Path

import shlex
import ffmpeg
from tqdm import tqdm
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
        # Safely create output directory handling spaces
        output_dir = self.episode_dir / "frames" / video_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory: {output_dir}")
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
        try:
            # Convert to absolute path and check existence
            input_path = input_path.absolute()
            print(f"Processing input path: {input_path}")
            
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            # Get video info for frame count first
            probe = ffmpeg.probe(str(input_path))
            video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")

            try:
                self._total_frames = int(video_info["nb_frames"])
            except KeyError:
                duration = float(video_info["duration"])
                if "/" in self.config.fps:
                    num, den = map(int, self.config.fps.split("/"))
                    fps = num / den
                else:
                    fps = float(self.config.fps)
                self._total_frames = int(duration * fps)

            print(f"Calculated total frames: {self._total_frames}")

            # Create a frames directory without spaces
            safe_output_dir = self._output_dir.parent / self._output_dir.name.replace(" ", "_")
            if safe_output_dir != self._output_dir:
                print(f"Creating safe output directory: {safe_output_dir}")
                if self._output_dir.exists():
                    self._output_dir.rename(safe_output_dir)
                self._output_dir = safe_output_dir

            # Build the ffmpeg command
            stream = (
                ffmpeg
                .input(str(input_path))
                .output(
                    str(self._output_dir / f"frame_%04d.{self.config.format}"),
                    vf=f'fps={self.config.fps}',
                    **self._get_output_options()
                )
            )
                
            # Print the compiled command for debugging
            cmd = ffmpeg.compile(stream)
            print(f"FFmpeg command: {' '.join(cmd)}")
            
            return stream

        except Exception as e:
            print(f"Error in _build_ffmpeg_stream: {str(e)}")
            if hasattr(e, 'stderr'):
                print(f"FFmpeg stderr: {e.stderr.decode() if e.stderr else 'No stderr'}")
            raise

    def _get_output_options(self) -> dict:
        """Get output options based on format."""
        options = {'y': None}  # Add -y to overwrite files
        
        if self.config.format == "png":
            options.update({
                'vcodec': 'png',
                'compression_level': str(int((100 - self.config.quality) / 100 * 9))
            })
        elif self.config.format in ["jpg", "jpeg"]:
            options.update({
                'vcodec': 'mjpeg',
                'q:v': str(int((100 - self.config.quality) / 100 * 31))
            })
            
        return options

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
        """Extract frames from a video file."""
        print(f"Starting frame extraction for: {video_path}")
        video_path = Path(video_path).resolve()
        
        try:
            # Create output directory
            self._output_dir = self._create_output_directory(video_path)
            print(f"Output directory: {self._output_dir}")

            # Build the ffmpeg stream
            stream = self._build_ffmpeg_stream(video_path)
            
            # Run ffmpeg with progress monitoring
            try:
                current_frame = 0
                with tqdm(total=self._total_frames, desc="Extracting frames", unit="frames") as pbar:
                    process = (
                        ffmpeg
                        .run_async(stream, pipe_stderr=True, overwrite_output=True)
                    )
                    
                    # Count existing frames periodically to show progress
                    while process.poll() is None:  # While process is running
                        # Count actual frames written
                        frame_count = len(list(self._output_dir.glob(f"frame_*.{self.config.format}")))
                        if frame_count > current_frame:
                            pbar.update(frame_count - current_frame)
                            current_frame = frame_count
                            pbar.set_postfix({'saved': frame_count})
                    
                    if process.returncode != 0:
                        raise FFmpegOperationError(
                            f"FFmpeg process failed with return code {process.returncode}"
                        )

                    # Final frame count update
                    final_count = len(list(self._output_dir.glob(f"frame_*.{self.config.format}")))
                    if final_count > current_frame:
                        pbar.update(final_count - current_frame)
                        pbar.set_postfix({'saved': final_count})

                # Check the output files
                frame_files = {}
                for frame_path in sorted(self._output_dir.glob(f"frame_*.{self.config.format}")):
                    frame_files[frame_path.name] = self._calculate_frame_hash(frame_path)
                    
                print(f"Successfully extracted {len(frame_files)} frames")
                
                return FrameExtractionResult(
                    total_frames=len(frame_files),
                    output_directory=self._output_dir,
                    frame_files=frame_files
                )

            except ffmpeg.Error as e:
                stderr = e.stderr.decode('utf-8') if e.stderr else 'No stderr'
                print(f"FFmpeg error: {stderr}")
                raise FFmpegOperationError(f"FFmpeg operation failed: {stderr}")
                    
        except Exception as e:
            print(f"Error during frame extraction: {str(e)}")
            if hasattr(e, '__dict__'):
                print(f"Error details: {e.__dict__}")
            raise