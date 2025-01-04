from __future__ import annotations

from pathlib import Path

import fire
import numpy as np
from tqdm import tqdm

from quackvideo.video.writer import VideoWriter, VideoWriterConfig


def write_solid_color_video(
    output_path: str,
    duration: float = 5.0,
    fps: float = 30.0,
    width: int = 1280,
    height: int = 720,
    color: tuple[int, int, int] = (255, 0, 0),  # Red by default
) -> None:
    """
    Create a video with a solid color.

    Args:
        output_path: Path to save the video
        duration: Duration in seconds
        fps: Frames per second
        width: Frame width
        height: Frame height
        color: RGB color tuple
    """
    # Create configuration
    config = VideoWriterConfig(
        fps=fps,
        codec="libx264",
        crf=23,  # Medium quality
        preset="medium",
    )

    # Initialize writer
    writer = VideoWriter(output_path, config)

    # Generate solid color frames
    total_frames = int(duration * fps)
    frames = []

    # Create a single color frame
    color_frame = np.full((height, width, 3), color, dtype=np.uint8)

    # Duplicate the frame
    frames = [color_frame.copy() for _ in range(total_frames)]

    # Write frames
    result = writer.write_frames(frames)
    print(f"\nCreated video at: {result.output_path}")
    print(f"Duration: {result.duration:.2f}s")
    print(f"Frames: {result.frame_count}")


def write_streaming_gradient(
    output_path: str,
    duration: float = 5.0,
    fps: float = 30.0,
    width: int = 1280,
    height: int = 720,
) -> None:
    """
    Create a video with streaming gradient pattern.

    Args:
        output_path: Path to save the video
        duration: Duration in seconds
        fps: Frames per second
        width: Frame width
        height: Frame height
    """
    config = VideoWriterConfig(fps=fps, codec="libx264", crf=23, preset="medium")

    writer = VideoWriter(output_path, config)

    def frame_generator():
        total_frames = int(duration * fps)
        for i in range(total_frames):
            # Create gradient that changes over time
            t = i / total_frames
            gradient = np.linspace(0, 255 * (1 - t), width)
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 0] = gradient[None, :]  # Red channel
            frame[:, :, 1] = gradient[None, ::-1]  # Green channel
            frame[:, :, 2] = gradient[None, :]  # Blue channel
            yield frame

    # Write frames using streaming
    result = writer.write_frames_from_stream(frame_generator())
    print(f"\nCreated gradient video at: {result.output_path}")
    print(f"Duration: {result.duration:.2f}s")
    print(f"Frames: {result.frame_count}")


def write_high_quality(
    output_path: str,
    duration: float = 5.0,
    fps: float = 30.0,
    width: int = 1920,
    height: int = 1080,
) -> None:
    """
    Create a high-quality video with custom encoding settings.

    Args:
        output_path: Path to save the video
        duration: Duration in seconds
        fps: Frames per second
        width: Frame width
        height: Frame height
    """
    config = VideoWriterConfig(
        fps=fps,
        codec="libx264",
        crf=18,  # High quality
        preset="slow",  # Better compression
        pixel_format="yuv444p",  # Higher color quality
        bitrate="8M",
    )

    writer = VideoWriter(output_path, config)

    # Generate test pattern frames
    total_frames = int(duration * fps)
    frames = []

    for i in range(total_frames):
        # Create a test pattern
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Add some animated elements
        t = i / total_frames
        circle_x = int(width / 2 + width / 4 * np.cos(2 * np.pi * t))
        circle_y = int(height / 2 + height / 4 * np.sin(2 * np.pi * t))

        # Draw a moving circle
        y, x = np.ogrid[:height, :width]
        mask = (x - circle_x) ** 2 + (y - circle_y) ** 2 <= 100**2
        frame[mask] = [255, 255, 255]

        frames.append(frame)

    # Write frames
    result = writer.write_frames(frames)
    print(f"\nCreated high-quality video at: {result.output_path}")
    print(f"Duration: {result.duration:.2f}s")
    print(f"Frames: {result.frame_count}")


def main() -> None:
    """Main entry point for video writing examples."""
    fire.Fire(
        {
            "solid": write_solid_color_video,
            "gradient": write_streaming_gradient,
            "quality": write_high_quality,
        }
    )


if __name__ == "__main__":
    main()
