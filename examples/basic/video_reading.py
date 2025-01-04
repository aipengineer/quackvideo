from __future__ import annotations

from pathlib import Path

import fire
from tqdm import tqdm

from quackvideo.video.reader import VideoReader, VideoReaderConfig


def read_video_basic(
    video_path: str,
    display_metadata: bool = True,
) -> None:
    """
    Basic example of reading a video file and displaying its metadata.

    Args:
        video_path: Path to input video file
        display_metadata: Whether to display video metadata
    """
    # Initialize video reader with default configuration
    reader = VideoReader(video_path)

    # Display video metadata if requested
    if display_metadata:
        print("\nVideo Metadata:")
        print(f"Duration: {reader.metadata.duration:.2f} seconds")
        print(f"FPS: {reader.metadata.fps}")
        print(f"Resolution: {reader.metadata.width}x{reader.metadata.height}")
        print(f"Codec: {reader.metadata.codec}")
        print(f"Bitrate: {reader.metadata.bitrate} bps")
        print(f"Size: {reader.metadata.size_bytes / (1024*1024):.2f} MB")

    # Read and process frames
    print("\nReading frames...")
    frame_count = 0
    for frame in tqdm(reader.read_frames(), desc="Processing"):
        frame_count += 1

    print(f"\nProcessed {frame_count} frames")


def read_video_with_config(
    video_path: str,
    fps: float = 30.0,
    start_time: float = 0.0,
    end_time: float | None = None,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """
    Example of reading a video with custom configuration.

    Args:
        video_path: Path to input video file
        fps: Target frame rate
        start_time: Start time in seconds
        end_time: End time in seconds
        width: Target width (if None, maintains original)
        height: Target height (if None, maintains original)
    """
    # Create configuration
    config = VideoReaderConfig(
        fps=fps,
        start_time=start_time,
        end_time=end_time,
        resolution=(width, height) if width and height else None,
    )

    # Initialize reader with config
    reader = VideoReader(video_path, config)

    # Read and count frames
    frame_count = 0
    for frame in tqdm(reader.read_frames(), desc="Processing"):
        frame_count += 1

    print(f"\nProcessed {frame_count} frames from {start_time}s", end="")
    print(f" to {end_time}s" if end_time else " to end")


def extract_keyframes(
    video_path: str,
) -> None:
    """
    Example of extracting keyframes from a video.

    Args:
        video_path: Path to input video file
    """
    reader = VideoReader(video_path)

    print("\nExtracting keyframes...")
    keyframe_count = 0
    for timestamp, frame in tqdm(reader.extract_keyframes(), desc="Processing"):
        keyframe_count += 1
        print(f"Keyframe at {timestamp:.2f}s")

    print(f"\nExtracted {keyframe_count} keyframes")


def main() -> None:
    """Main entry point for video reading examples."""
    fire.Fire(
        {
            "basic": read_video_basic,
            "custom": read_video_with_config,
            "keyframes": extract_keyframes,
        }
    )


if __name__ == "__main__":
    main()
