# src/quackvideo/video/writer.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import ffmpeg
import numpy as np
from pydantic import BaseModel, Field, field_validator
from tqdm import tqdm

logger = logging.getLogger(__name__)


class VideoEncodingPreset(str):
    """FFmpeg encoding presets."""

    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"


class VideoWriterConfig(BaseModel):
    """Configuration for VideoWriter."""

    fps: float = Field(
        default=30.0, description="Frames per second for the output video"
    )
    codec: str = Field(default="libx264", description="Video codec to use")
    crf: int = Field(
        default=23,
        description="Constant Rate Factor (0-51, lower means better quality)",
    )
    preset: VideoEncodingPreset = Field(
        default=VideoEncodingPreset.MEDIUM,
        description="Encoding preset (affects encoding speed vs compression ratio)",
    )
    pixel_format: str = Field(default="yuv420p", description="Output pixel format")
    bitrate: str | None = Field(
        default=None, description="Target bitrate (e.g., '2M', '5000K')"
    )

    @field_validator("fps")
    def validate_fps(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("FPS must be positive")
        return v

    @field_validator("crf")
    def validate_crf(cls, v: int) -> int:
        if not 0 <= v <= 51:
            raise ValueError("CRF must be between 0 and 51")
        return v

    @field_validator("bitrate")
    def validate_bitrate(cls, v: str | None) -> str | None:
        if v is not None:
            if not any(v.upper().endswith(unit) for unit in ["K", "M", "G"]):
                raise ValueError("Bitrate must end with K, M, or G (e.g., '2M')")
        return v


class WriteResult(BaseModel):
    """Result of video writing operation."""

    output_path: Path = Field(..., description="Path to the output video file")
    frame_count: int = Field(..., description="Number of frames written")
    duration: float = Field(..., description="Duration of the output video in seconds")


class VideoWriter:
    """High-level interface for writing video frames using ffmpeg-python."""

    def __init__(
        self, output_path: str | Path, config: VideoWriterConfig | None = None
    ) -> None:
        """
        Initialize VideoWriter.

        Args:
            output_path: Path where the video will be saved
            config: Configuration for video writing (optional)
        """
        self.output_path = Path(output_path)
        self.config = config or VideoWriterConfig()

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write_frames(self, frames: Sequence[np.ndarray]) -> WriteResult:
        """
        Write frames to a video file.

        Args:
            frames: Sequence of numpy arrays containing the video frames

        Returns:
            WriteResult containing information about the written video

        Raises:
            ValueError: If frames are empty or have inconsistent dimensions
            RuntimeError: If FFmpeg fails to write the video
        """
        if not frames:
            raise ValueError("No frames to write")

        # Check frame dimensions
        first_frame = frames[0]
        height, width = first_frame.shape[:2]

        # Create ffmpeg stream
        stream = (
            ffmpeg.input(
                "pipe:",
                format="rawvideo",
                pix_fmt="rgb24",
                s=f"{width}x{height}",
                r=self.config.fps,
            )
            .output(
                str(self.output_path),
                pix_fmt=self.config.pixel_format,
                vcodec=self.config.codec,
                preset=self.config.preset,
                crf=self.config.crf,
                **({"b:v": self.config.bitrate} if self.config.bitrate else {}),
            )
            .overwrite_output()
        )

        try:
            # Start FFmpeg process
            process = stream.run_async(pipe_stdin=True, pipe_stderr=True)

            # Write frames with progress bar
            with tqdm(total=len(frames), desc="Writing frames") as pbar:
                for frame in frames:
                    if frame.shape[:2] != (height, width):
                        raise ValueError(
                            f"Inconsistent frame dimensions. Expected {(height, width)}, "
                            f"got {frame.shape[:2]}"
                        )

                    process.stdin.write(frame.tobytes())
                    pbar.update(1)

            # Close input pipe and wait for FFmpeg
            process.stdin.close()
            process.wait()

            if process.returncode != 0:
                error_message = process.stderr.read().decode()
                raise RuntimeError(f"FFmpeg encoding failed: {error_message}")

            # Return write result
            return WriteResult(
                output_path=self.output_path,
                frame_count=len(frames),
                duration=len(frames) / self.config.fps,
            )

        except Exception as e:
            logger.error(f"Error writing video: {e}")
            raise

        finally:
            # Ensure cleanup
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=1)
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    def write_frames_from_stream(
        self, frame_iterator: Iterator[np.ndarray]
    ) -> WriteResult:
        """
        Write frames from an iterator to a video file.

        Args:
            frame_iterator: Iterator yielding numpy arrays containing video frames

        Returns:
            WriteResult containing information about the written video

        Raises:
            ValueError: If no frames are received or dimensions are inconsistent
            RuntimeError: If FFmpeg fails to write the video
        """
        # Get first frame to determine dimensions
        try:
            first_frame = next(frame_iterator)
        except StopIteration:
            raise ValueError("No frames received from iterator")

        height, width = first_frame.shape[:2]
        frame_count = 0

        # Create ffmpeg stream
        stream = (
            ffmpeg.input(
                "pipe:",
                format="rawvideo",
                pix_fmt="rgb24",
                s=f"{width}x{height}",
                r=self.config.fps,
            )
            .output(
                str(self.output_path),
                pix_fmt=self.config.pixel_format,
                vcodec=self.config.codec,
                preset=self.config.preset,
                crf=self.config.crf,
                **({"b:v": self.config.bitrate} if self.config.bitrate else {}),
            )
            .overwrite_output()
        )

        try:
            # Start FFmpeg process
            process = stream.run_async(pipe_stdin=True, pipe_stderr=True)

            # Write first frame
            process.stdin.write(first_frame.tobytes())
            frame_count += 1

            # Write remaining frames
            for frame in frame_iterator:
                if frame.shape[:2] != (height, width):
                    raise ValueError(
                        f"Inconsistent frame dimensions. Expected {(height, width)}, "
                        f"got {frame.shape[:2]}"
                    )

                process.stdin.write(frame.tobytes())
                frame_count += 1

            # Close input pipe and wait for FFmpeg
            process.stdin.close()
            process.wait()

            if process.returncode != 0:
                error_message = process.stderr.read().decode()
                raise RuntimeError(f"FFmpeg encoding failed: {error_message}")

            # Return write result
            return WriteResult(
                output_path=self.output_path,
                frame_count=frame_count,
                duration=frame_count / self.config.fps,
            )

        except Exception as e:
            logger.error(f"Error writing video stream: {e}")
            raise

        finally:
            # Ensure cleanup
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=1)
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
