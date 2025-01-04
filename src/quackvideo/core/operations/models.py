# src/quackvideo/core/operations/models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from urllib.parse import quote

from pydantic import BaseModel, Field, field_validator, model_validator


class MediaType(str, Enum):
    """Types of media that can be processed."""

    VIDEO = "video"
    AUDIO = "audio"


class FFmpegBaseConfig(BaseModel):
    """Base configuration for FFmpeg operations."""

    timeout: int = Field(10, description="Operation timeout in seconds")
    retries: int = Field(5, description="Number of retries for failed operations")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")


class FrameExtractionConfig(FFmpegBaseConfig):
    """Configuration for frame extraction."""

    fps: str = Field("1/5", description="Frames per second to extract")
    format: str = Field("png", description="Output format for frames")
    quality: int = Field(100, description="Output quality (1-100)")

    @field_validator("quality")
    def validate_quality(cls, v: int) -> int:
        if not 1 <= v <= 100:
            raise ValueError("Quality must be between 1 and 100")
        return v


class AudioConfig(FFmpegBaseConfig):
    """Configuration for audio operations."""

    format: str = Field("flac", description="Output audio format")
    compression_level: int = Field(8, description="Compression level")
    mixing_volumes: list[float] = Field(
        default=[0.10, 0.90], description="Volume levels for mixing audio tracks"
    )

    @field_validator("compression_level")
    def validate_compression(cls, v: int) -> int:
        if not 0 <= v <= 12:
            raise ValueError("Compression level must be between 0 and 12")
        return v

    @field_validator("mixing_volumes")
    def validate_volumes(cls, v: list[float]) -> list[float]:
        if not all(0 <= vol <= 1 for vol in v):
            raise ValueError("Volume levels must be between 0 and 1")
        return v


class OutputMetadata(BaseModel):
    """Metadata for operation outputs."""

    timestamp: datetime = Field(default_factory=datetime.now)
    original_filename: str
    operation_type: str
    output_path: Path

    @property
    def filename(self) -> str:
        """Generate timestamped filename."""
        timestamp_str = self.timestamp.strftime("%Y-%m-%d-%H%M%S")
        safe_filename = quote(self.original_filename)
        return f"{timestamp_str}-{safe_filename}"


class ProcessingMetadata(BaseModel):
    """Metadata for tracking processing progress."""

    started_at: datetime = Field(default_factory=datetime.now)
    total_frames: int | None = None
    completed_frames: int = Field(default=0)
    status: str = Field(default="in_progress")
    frame_integrity: dict[str, str] = Field(default_factory=dict)
    last_processed: str | None = None

    @model_validator(mode="after")
    def validate_progress(self) -> ProcessingMetadata:
        if self.total_frames is not None:
            if self.completed_frames > self.total_frames:
                raise ValueError(
                    f"Completed frames ({self.completed_frames}) cannot exceed "
                    f"total frames ({self.total_frames})"
                )
        return self


class FFmpegProcessingConfig(BaseModel):
    """Main configuration for FFmpeg processing."""

    frame_extraction: FrameExtractionConfig = Field(
        default_factory=FrameExtractionConfig, description="Frame extraction settings"
    )
    audio: AudioConfig = Field(
        default_factory=AudioConfig, description="Audio processing settings"
    )
    compatible_formats: dict[str, list[str]] = Field(
        default={
            "video": [".mp4", ".mov", ".avi", ".mkv"],
            "audio": [".wav", ".mp3", ".aac", ".flac", ".m4a"],
        },
        description="Compatible file formats",
    )

    @field_validator("compatible_formats")
    def validate_formats(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        for media_type in MediaType:
            if media_type.value not in v:
                raise ValueError(f"Missing format list for {media_type.value}")
        return v
