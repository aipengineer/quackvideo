# src/quackvideo/video/reader.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Sequence

import ffmpeg
import numpy as np
from pydantic import BaseModel, Field, field_validator

from quackvideo.core.utils import (
    FrameComparisonConfig,
    detect_scene_change,
)

logger = logging.getLogger(__name__)


class VideoMetadata(BaseModel):
    """Video metadata information."""

    duration: float = Field(..., description="Duration in seconds")
    fps: float = Field(..., description="Frames per second")
    width: int = Field(..., description="Video width")
    height: int = Field(..., description="Video height")
    bitrate: int = Field(..., description="Video bitrate")
    codec: str = Field(..., description="Video codec")
    size_bytes: int = Field(..., description="File size in bytes")

    @field_validator("width", "height")
    def validate_dimensions(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Dimensions must be positive")
        return v

    @field_validator("fps", "duration")
    def validate_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class VideoReaderConfig(BaseModel):
    """Configuration for VideoReader."""

    fps: float | None = Field(default=None, description="Target frame rate")
    start_time: float | None = Field(default=None, description="Start time in seconds")
    end_time: float | None = Field(default=None, description="End time in seconds")
    resolution: tuple[int, int] | None = Field(
        default=None, description="Target resolution (width, height)"
    )
    skip_validation: bool = Field(default=False, description="Skip input validation")
    force_fps: bool = Field(default=False, description="Force exact FPS")

    @field_validator("fps")
    def validate_fps(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("FPS must be positive")
        return v

    @field_validator("start_time")
    def validate_start_time(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Start time must be non-negative")
        return v

    @field_validator("end_time", mode="after")
    def validate_end_time(cls, v: float | None, values) -> float | None:
        if v is not None:
            start_time = values.data.get("start_time", 0.0) or 0.0
            if v <= start_time:
                raise ValueError("End time must be greater than start time")
        return v

    @field_validator("resolution")
    def validate_resolution(cls, v: tuple[int, int] | None) -> tuple[int, int] | None:
        if v is not None and (v[0] <= 0 or v[1] <= 0):
            raise ValueError("Resolution dimensions must be positive")
        return v


class VideoReader:
    """High-level interface for reading video files using ffmpeg-python."""

    def __init__(
        self,
        video_path: str | Path,
        config: VideoReaderConfig | None = None,
        *,
        skip_validation: bool = False,
    ) -> None:
        self.video_path = Path(video_path)
        self.config = config or VideoReaderConfig(skip_validation=skip_validation)

        if not skip_validation and not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self._metadata = self._load_metadata()

    def _load_metadata(self) -> VideoMetadata:
        """Load video metadata using ffmpeg-python's probe."""
        try:
            probe = ffmpeg.probe(str(self.video_path))
            video_stream = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "video"
                ),
                None,
            )
            if not video_stream:
                raise ValueError("No video stream found")

            # Calculate FPS from frame rate fraction
            fps_num, fps_den = map(int, video_stream["r_frame_rate"].split("/"))
            fps = fps_num / fps_den

            return VideoMetadata(
                duration=float(probe["format"]["duration"]),
                fps=fps,
                width=int(video_stream["width"]),
                height=int(video_stream["height"]),
                bitrate=int(probe["format"].get("bit_rate", 0)),
                codec=video_stream["codec_name"],
                size_bytes=int(probe["format"]["size"]),
            )
        except ffmpeg.Error as e:
            raise RuntimeError(
                f"Failed to load video metadata: {e.stderr.decode() if e.stderr else str(e)}"
            )

    @property
    def metadata(self) -> VideoMetadata:
        """Get video metadata."""
        return self._metadata

    def read_frames(self) -> Iterator[np.ndarray]:
        """Read video frames according to configuration."""
        stream = ffmpeg.input(str(self.video_path))

        if self.config.start_time is not None:
            stream = stream.filter("setpts", f"PTS-{self.config.start_time}/TB")

        if self.config.fps is not None:
            stream = stream.filter("fps", fps=self.config.fps)

        if self.config.resolution is not None:
            stream = stream.filter(
                "scale", self.config.resolution[0], self.config.resolution[1]
            )

        if self.config.end_time is not None and self.config.start_time is not None:
            duration = self.config.end_time - self.config.start_time
            stream = stream.filter("trim", duration=duration)

        stream = stream.output(
            "pipe:", format="rawvideo", pix_fmt="rgb24"
        ).overwrite_output()

        try:
            process = stream.run_async(pipe_stdout=True, pipe_stderr=True)
            width = (
                self.config.resolution[0]
                if self.config.resolution
                else self.metadata.width
            )
            height = (
                self.config.resolution[1]
                if self.config.resolution
                else self.metadata.height
            )

            while True:
                in_bytes = process.stdout.read(width * height * 3)
                if not in_bytes:
                    break
                yield np.frombuffer(in_bytes, np.uint8).reshape((height, width, 3))

            process.wait()
            if process.returncode != 0:
                error = process.stderr.read().decode()
                raise RuntimeError(f"FFmpeg process failed: {error}")

        except Exception as e:
            logger.error(f"Error reading frames: {e}")
            raise
        finally:
            try:
                process.stdout.close()
                process.stderr.close()
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

    def extract_frames_range(
        self, start_time: float, end_time: float, *, frame_count: int | None = None
    ) -> Iterator[tuple[float, np.ndarray]]:
        """Extract frames within a specific time range."""
        if end_time <= start_time:
            raise ValueError("end_time must be greater than start_time")

        if frame_count is not None:
            timestamps = np.linspace(start_time, end_time, frame_count)
            for ts in timestamps:
                yield float(ts), self.extract_frame_at(ts)
        else:
            config = VideoReaderConfig(
                start_time=start_time,
                end_time=end_time,
                resolution=self.config.resolution,
                skip_validation=True,
            )
            reader = VideoReader(self.video_path, config, skip_validation=True)

            frame_duration = 1.0 / reader.metadata.fps
            current_time = start_time

            for frame in reader.read_frames():
                yield current_time, frame
                current_time += frame_duration

    def extract_keyframes(self) -> Iterator[tuple[float, np.ndarray]]:
        """Extract keyframes from the video."""
        try:
            probe = ffmpeg.probe(str(self.video_path))
            stream = (
                ffmpeg.input(str(self.video_path))
                .filter("select", "key")
                .output("pipe:", format="rawvideo", pix_fmt="rgb24")
                .overwrite_output()
            )

            process = stream.run_async(pipe_stdout=True, pipe_stderr=True)
            width = self.metadata.width
            height = self.metadata.height

            frame_size = width * height * 3
            timestamp = 0.0

            while True:
                in_bytes = process.stdout.read(frame_size)
                if not in_bytes:
                    break
                frame = np.frombuffer(in_bytes, np.uint8).reshape((height, width, 3))
                yield timestamp, frame
                timestamp += 1.0 / self.metadata.fps

            process.wait()
            if process.returncode != 0:
                error = process.stderr.read().decode()
                raise RuntimeError(f"FFmpeg process failed: {error}")

        except Exception as e:
            logger.error(f"Error extracting keyframes: {e}")
            raise

    def extract_scene_changes(
        self, threshold: float = 0.3
    ) -> Iterator[tuple[float, np.ndarray]]:
        """Extract frames at scene changes."""
        config = FrameComparisonConfig(threshold=threshold)
        frames = list(self.read_frames())

        if not frames:
            return

        prev_frame = frames[0]
        for i, frame in enumerate(frames[1:]):
            if detect_scene_change(prev_frame, frame, config=config):
                timestamp = (i + 1) / self.metadata.fps
                yield timestamp, frame
            prev_frame = frame

    def extract_frame_at(self, timestamp: float) -> np.ndarray:
        """Extract a single frame at the specified timestamp."""
        if timestamp < 0:
            raise ValueError("Timestamp must be non-negative")

        stream = (
            ffmpeg.input(str(self.video_path), ss=timestamp)
            .output("pipe:", format="rawvideo", pix_fmt="rgb24", vframes=1)
            .overwrite_output()
        )

        try:
            out, _ = stream.run(capture_stdout=True, capture_stderr=True)
            return np.frombuffer(out, np.uint8).reshape(
                (self.metadata.height, self.metadata.width, 3)
            )
        except ffmpeg.Error as e:
            raise RuntimeError(
                f"Failed to extract frame: {e.stderr.decode() if e.stderr else str(e)}"
            )
