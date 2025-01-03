from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path

import ffmpeg
from pydantic import BaseModel

from .base import FFmpegOperation, FFmpegOperationError
from .models import AudioConfig, MediaType, ProcessingMetadata


class AudioOperationType(str, Enum):
    """Types of audio operations."""

    EXTRACT = "extract"
    CONVERT = "convert"
    MIX = "mix"


class AudioOperationResult(BaseModel):
    """Result of audio operation."""

    operation_type: AudioOperationType
    output_path: Path
    format: str
    duration: float
    sample_rate: int
    channels: int
    bit_depth: int
    file_hash: str


class AudioProcessor(FFmpegOperation[AudioConfig, AudioOperationResult]):
    """Handles audio processing operations."""

    def __init__(
        self,
        config: AudioConfig,
        episode_dir: Path,
    ) -> None:
        """
        Initialize audio processor.

        Args:
            config: Audio processing configuration
            episode_dir: Directory for episode files
        """
        super().__init__(config, episode_dir)
        self._output_dir = self.episode_dir / "audio"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of an audio file."""
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_audio_info(self, file_path: Path) -> dict:
        """Get audio file information using ffprobe."""
        try:
            probe = ffmpeg.probe(str(file_path))
            audio_info = next(
                stream for stream in probe["streams"] if stream["codec_type"] == "audio"
            )
            return {
                "duration": float(probe["format"]["duration"]),
                "sample_rate": int(audio_info["sample_rate"]),
                "channels": int(audio_info["channels"]),
                "bit_depth": int(audio_info.get("bits_per_sample", 16)),
            }
        except Exception as e:
            raise FFmpegOperationError(f"Failed to get audio info: {e}")

    def _build_ffmpeg_stream(
        self,
        input_path: Path,
        operation_type: AudioOperationType,
        secondary_input: Path | None = None,
        volumes: list[float] | None = None,
    ) -> ffmpeg.Stream:
        """Build FFmpeg stream for audio operation."""
        if operation_type == AudioOperationType.EXTRACT:
            # Extract audio from video
            stream = ffmpeg.input(str(input_path)).audio.output(
                "pipe:", format=self.config.format
            )

        elif operation_type == AudioOperationType.CONVERT:
            # Convert audio format
            stream = ffmpeg.input(str(input_path)).output(
                "pipe:",
                format=self.config.format,
                compression_level=self.config.compression_level,
            )

        elif operation_type == AudioOperationType.MIX:
            if not secondary_input or not volumes:
                raise FFmpegOperationError(
                    "Secondary input and volumes required for mixing"
                )

            # Create streams for both inputs
            input1 = ffmpeg.input(str(input_path)).audio
            input2 = ffmpeg.input(str(secondary_input)).audio

            # Apply volume adjustments
            input1 = input1.filter("volume", volume=volumes[0])
            input2 = input2.filter("volume", volume=volumes[1])

            # Mix the streams
            stream = ffmpeg.filter([input1, input2], "amix", inputs=2).output(
                "pipe:", format=self.config.format
            )

        else:
            raise FFmpegOperationError(f"Unknown operation type: {operation_type}")

        return stream

    def _process_output(
        self, result: Any, metadata: ProcessingMetadata
    ) -> AudioOperationResult:
        """Process operation output and update metadata."""
        output_path = Path(metadata.last_processed) if metadata.last_processed else None
        if not output_path or not output_path.exists():
            raise FFmpegOperationError("Output file not found")

        audio_info = self._get_audio_info(output_path)
        file_hash = self._calculate_file_hash(output_path)

        return AudioOperationResult(
            operation_type=metadata.status,
            output_path=output_path,
            format=self.config.format,
            duration=audio_info["duration"],
            sample_rate=audio_info["sample_rate"],
            channels=audio_info["channels"],
            bit_depth=audio_info["bit_depth"],
            file_hash=file_hash,
        )

    def extract_audio(
        self,
        video_path: Path,
    ) -> AudioOperationResult:
        """
        Extract audio track from video file.

        Args:
            video_path: Path to video file

        Returns:
            AudioOperationResult with extraction details
        """
        try:
            # Create output path
            output_path = self._output_dir / (
                f"{video_path.stem}_audio.{self.config.format}"
            )

            # Execute extraction
            stream = self._build_ffmpeg_stream(video_path, AudioOperationType.EXTRACT)

            result = self.execute_with_retry(
                video_path,
                MediaType.VIDEO,
                "audio_extraction",
                progress_desc="Extracting audio",
            )

            return result

        except Exception as e:
            self.logger.error(f"Audio extraction failed: {e}")
            raise

    def convert_audio(
        self,
        audio_path: Path,
    ) -> AudioOperationResult:
        """
        Convert audio to specified format.

        Args:
            audio_path: Path to audio file

        Returns:
            AudioOperationResult with conversion details
        """
        try:
            output_path = self._output_dir / (
                f"{audio_path.stem}_converted.{self.config.format}"
            )

            stream = self._build_ffmpeg_stream(audio_path, AudioOperationType.CONVERT)

            return self.execute_with_retry(
                audio_path,
                MediaType.AUDIO,
                "audio_conversion",
                progress_desc="Converting audio",
            )

        except Exception as e:
            self.logger.error(f"Audio conversion failed: {e}")
            raise

    def mix_audio(
        self,
        audio_path1: Path,
        audio_path2: Path,
        volumes: list[float] | None = None,
    ) -> AudioOperationResult:
        """
        Mix two audio files.

        Args:
            audio_path1: Path to first audio file
            audio_path2: Path to second audio file
            volumes: Optional list of volume levels [vol1, vol2]

        Returns:
            AudioOperationResult with mixing details
        """
        try:
            volumes = volumes or self.config.mixing_volumes

            # Validate inputs
            for path in [audio_path1, audio_path2]:
                self._validate_input_file(path, MediaType.AUDIO)

            # Create output path
            output_path = self._output_dir / (
                f"{audio_path1.stem}_{audio_path2.stem}_mixed.{self.config.format}"
            )

            stream = self._build_ffmpeg_stream(
                audio_path1,
                AudioOperationType.MIX,
                secondary_input=audio_path2,
                volumes=volumes,
            )

            return self.execute_with_retry(
                audio_path1,  # Use first file as primary input
                MediaType.AUDIO,
                "audio_mixing",
                progress_desc="Mixing audio",
            )

        except Exception as e:
            self.logger.error(f"Audio mixing failed: {e}")
            raise
