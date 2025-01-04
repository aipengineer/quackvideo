# src/quackvideo/synthetic/video.py
from __future__ import annotations

import math
from collections.abc import Iterator
from enum import Enum
from pathlib import Path

import ffmpeg
import numpy as np
from pydantic import Field

from .base import SyntheticConfig, SyntheticGenerator


class VideoPattern(str, Enum):
    """Available video test patterns."""

    COLOR_BARS = "color_bars"
    GRADIENT = "gradient"
    CHECKERBOARD = "checkerboard"
    MOVING_BOX = "moving_box"
    PULSE = "pulse"


class VideoConfig(SyntheticConfig):
    """Configuration for synthetic video generation."""

    pattern: VideoPattern = Field(
        VideoPattern.COLOR_BARS, description="Type of test pattern"
    )
    bitrate: str = Field("2M", description="Output video bitrate")
    codec: str = Field("libx264", description="Video codec")
    pixel_format: str = Field("yuv420p", description="Pixel format")


class VideoGenerator(SyntheticGenerator):
    """Generator for synthetic video patterns."""

    def __init__(self, config: VideoConfig) -> None:
        super().__init__(config)
        self.config = config  # Type hint for IDE

    def _generate_frames(self) -> Iterator[np.ndarray]:
        """Generate frames based on selected pattern."""
        total_frames = int(self.config.duration * self.config.fps)

        if self.config.pattern == VideoPattern.COLOR_BARS:
            yield from self._generate_color_bars(total_frames)
        elif self.config.pattern == VideoPattern.GRADIENT:
            yield from self._generate_gradient(total_frames)
        elif self.config.pattern == VideoPattern.CHECKERBOARD:
            yield from self._generate_checkerboard(total_frames)
        elif self.config.pattern == VideoPattern.MOVING_BOX:
            yield from self._generate_moving_box(total_frames)
        elif self.config.pattern == VideoPattern.PULSE:
            yield from self._generate_pulse(total_frames)

    def _generate_color_bars(self, total_frames: int) -> Iterator[np.ndarray]:
        """Generate color bars test pattern."""
        colors = [
            (255, 255, 255),  # White
            (255, 255, 0),  # Yellow
            (0, 255, 255),  # Cyan
            (0, 255, 0),  # Green
            (255, 0, 255),  # Magenta
            (255, 0, 0),  # Red
            (0, 0, 255),  # Blue
            (0, 0, 0),  # Black
        ]

        bar_width = self.config.width // len(colors)
        frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)

        for i, color in enumerate(colors):
            start = i * bar_width
            end = (i + 1) * bar_width if i < len(colors) - 1 else self.config.width
            frame[:, start:end] = color

        for _ in range(total_frames):
            yield frame

    def _generate_gradient(self, total_frames: int) -> Iterator[np.ndarray]:
        """Generate moving gradient pattern."""
        x = np.linspace(0, 1, self.config.width)
        y = np.linspace(0, 1, self.config.height)
        xx, yy = np.meshgrid(x, y)

        for frame_idx in range(total_frames):
            t = frame_idx / self.config.fps
            frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)

            # Create moving gradient
            pattern = np.sin(2 * np.pi * (xx + yy + t))
            frame[..., 0] = ((pattern + 1) * 127.5).astype(np.uint8)  # Red
            frame[..., 1] = (
                (np.roll(pattern, self.config.width // 3) + 1) * 127.5
            ).astype(np.uint8)  # Green
            frame[..., 2] = (
                (np.roll(pattern, -self.config.width // 3) + 1) * 127.5
            ).astype(np.uint8)  # Blue

            yield frame

    def _generate_checkerboard(self, total_frames: int) -> Iterator[np.ndarray]:
        """Generate animated checkerboard pattern."""
        check_size = 64
        for frame_idx in range(total_frames):
            frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
            offset = frame_idx % (check_size * 2)

            for i in range(0, self.config.height, check_size):
                for j in range(0, self.config.width, check_size):
                    if ((i + j + offset) // check_size) % 2:
                        frame[i : i + check_size, j : j + check_size] = 255

            yield frame

    def _generate_moving_box(self, total_frames: int) -> Iterator[np.ndarray]:
        """Generate moving box pattern."""
        box_size = 100
        for frame_idx in range(total_frames):
            frame = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)

            # Calculate box position
            t = frame_idx / total_frames
            x = int(
                (self.config.width - box_size) * (0.5 + 0.5 * math.cos(2 * math.pi * t))
            )
            y = int(
                (self.config.height - box_size)
                * (0.5 + 0.5 * math.sin(2 * math.pi * t))
            )

            # Draw box
            frame[y : y + box_size, x : x + box_size] = [255, 0, 0]  # Red box
            yield frame

    def _generate_pulse(self, total_frames: int) -> Iterator[np.ndarray]:
        """Generate pulsing pattern."""
        for frame_idx in range(total_frames):
            t = frame_idx / self.config.fps
            intensity = int(127.5 * (1 + math.sin(2 * math.pi * t)))

            frame = np.full(
                (self.config.height, self.config.width, 3), intensity, dtype=np.uint8
            )
            yield frame

    def generate(self, output_path: Path) -> Path:
        """Generate synthetic video file."""
        output_path = Path(output_path)

        # Set up FFmpeg process
        process = (
            ffmpeg.input(
                "pipe:",
                format="rawvideo",
                pix_fmt="rgb24",
                s=f"{self.config.width}x{self.config.height}",
                r=str(self.config.fps),
            )
            .output(
                str(output_path),
                vcodec=self.config.codec,
                pix_fmt=self.config.pixel_format,
                video_bitrate=self.config.bitrate,
            )
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )

        try:
            # Write frames
            for frame in self._generate_frames():
                process.stdin.write(frame.tobytes())

            # Close stdin pipe
            process.stdin.close()
            process.wait()

            return output_path

        except Exception:
            if process.poll() is None:
                process.kill()
            raise
