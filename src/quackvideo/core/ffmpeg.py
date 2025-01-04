# src/quackvideo/core/ffmpeg.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Optional

import ffmpeg
import numpy as np
from pydantic import BaseModel, Field, field_validator
from tqdm import tqdm


class FFmpegError(Exception):
    """Base exception for FFmpeg-related errors."""

    pass


class FFmpegTimeoutError(FFmpegError):
    """Raised when FFmpeg operation times out."""

    pass


class FFmpegCommand(BaseModel):
    """Represents an FFmpeg command with its parameters."""

    input_path: Path = Field(..., description="Path to input file")
    output_path: Path | None = Field(None, description="Path to output file")
    fps: float | None = Field(None, description="Frames per second")
    start_time: float | None = Field(None, description="Start time in seconds")
    end_time: float | None = Field(None, description="End time in seconds")
    resolution: tuple[int, int] | None = Field(
        None, description="Output resolution (width, height)"
    )

    @field_validator("fps")
    def validate_fps(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("FPS must be positive")
        return v

    @field_validator("start_time", "end_time")
    def validate_time(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Time values must be non-negative")
        return v

    @field_validator("resolution")
    def validate_resolution(cls, v: tuple[int, int] | None) -> tuple[int, int] | None:
        if v is not None:
            width, height = v
            if width <= 0 or height <= 0:
                raise ValueError("Resolution dimensions must be positive")
        return v

    def build_stream(self) -> ffmpeg.Stream:
        """Build the FFmpeg stream with the specified parameters."""
        stream = ffmpeg.input(str(self.input_path))

        if self.start_time is not None:
            stream = stream.filter("setpts", f"PTS-{self.start_time}/TB")

        if self.fps is not None:
            stream = stream.filter("fps", fps=self.fps)

        if self.resolution is not None:
            stream = stream.filter("scale", self.resolution[0], self.resolution[1])

        if self.end_time is not None and self.start_time is not None:
            duration = self.end_time - self.start_time
            if duration > 0:
                stream = stream.filter("setpts", f"PTS-STARTPTS")
                stream = stream.filter("trim", duration=duration)

        return stream


class VideoInfo(BaseModel):
    """Video information from probe."""

    width: int = Field(..., description="Video width in pixels")
    height: int = Field(..., description="Video height in pixels")
    duration: float = Field(..., description="Video duration in seconds")
    fps: float = Field(..., description="Video frames per second")


class FFmpegWrapper:
    """High-level wrapper for FFmpeg operations using ffmpeg-python."""

    TIMEOUT: int = 10  # Default timeout in seconds

    @staticmethod
    def get_video_info(video_path: Path, timeout: int = 10) -> VideoInfo:
        """Get video information using ffmpeg-python's probe."""
        try:
            probe = ffmpeg.probe(str(video_path))
            video_stream = next(
                (
                    stream
                    for stream in probe["streams"]
                    if stream["codec_type"] == "video"
                ),
                None,
            )
            if not video_stream:
                raise FFmpegError("No video stream found")

            # Extract fps from frame rate string (e.g., "24/1")
            fps_num, fps_den = map(int, video_stream["r_frame_rate"].split("/"))
            fps = fps_num / fps_den

            return VideoInfo(
                width=int(video_stream["width"]),
                height=int(video_stream["height"]),
                duration=float(probe["format"]["duration"]),
                fps=fps,
            )
        except ffmpeg.Error as e:
            raise FFmpegError(
                f"Failed to probe video: {e.stderr.decode() if e.stderr else str(e)}"
            )

    @classmethod
    def extract_frames(
        cls,
        video_path: str | Path,
        fps: float | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        resolution: tuple[int, int] | None = None,
        *,
        skip_validation: bool = False,
        timeout: int = 10,
    ) -> Iterator[np.ndarray]:
        """Extract video frames using ffmpeg-python."""
        video_path = Path(video_path)
        if not skip_validation and not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Get video info
        video_info = cls.get_video_info(video_path, timeout=timeout)
        width, height = (
            resolution if resolution else (video_info.width, video_info.height)
        )

        # Build FFmpeg command
        cmd = FFmpegCommand(
            input_path=video_path,
            fps=fps,
            start_time=start_time,
            end_time=end_time,
            resolution=resolution,
        )

        stream = (
            cmd.build_stream()
            .output("pipe:", format="rawvideo", pix_fmt="rgb24")
            .overwrite_output()
        )

        try:
            process = stream.run_async(pipe_stdout=True, pipe_stderr=True)

            # Set up progress bar
            with tqdm(desc="Extracting frames", unit="frame") as pbar:
                while True:
                    try:
                        in_bytes = process.stdout.read(width * height * 3)
                        if not in_bytes:
                            break

                        frame = np.frombuffer(in_bytes, np.uint8).reshape(
                            (height, width, 3)
                        )
                        pbar.update(1)
                        yield frame

                    except Exception as e:
                        process.stdout.close()
                        process.stderr.close()
                        process.terminate()
                        raise FFmpegError(f"Frame extraction failed: {str(e)}")

            process.wait(timeout=timeout)
            if process.returncode != 0:
                error_msg = (
                    process.stderr.read().decode()
                    if process.stderr
                    else "Unknown error"
                )
                raise FFmpegError(f"FFmpeg process failed: {error_msg}")

        except Exception as e:
            raise FFmpegError(f"Frame extraction failed: {str(e)}")

        finally:
            try:
                process.stdout.close()
                process.stderr.close()
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except Exception:
                        process.kill()
            except Exception:
                pass
