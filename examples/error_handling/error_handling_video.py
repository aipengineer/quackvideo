from __future__ import annotations

from pathlib import Path

import fire
import numpy as np
from tqdm import tqdm

from quackvideo.video.reader import VideoReader, VideoReaderConfig
from quackvideo.video.writer import VideoWriter, VideoWriterConfig


def demonstrate_invalid_video_file() -> None:
    """
    Demonstrate handling of non-existent video file.
    """
    try:
        reader = VideoReader("nonexistent_video.mp4")
        for frame in reader.read_frames():
            pass
    except FileNotFoundError as e:
        print(f"Expected error - File not found: {e}")


def demonstrate_corrupt_video() -> None:
    """
    Demonstrate handling of corrupt video file.
    """
    # Create a "corrupt" video file
    corrupt_path = Path("corrupt_video.mp4")
    corrupt_path.write_bytes(b"This is not a valid video file")

    try:
        reader = VideoReader(str(corrupt_path))
        for frame in reader.read_frames():
            pass
    except RuntimeError as e:
        print(f"Expected error - Corrupt video: {e}")
    finally:
        corrupt_path.unlink()  # Clean up


def demonstrate_invalid_timestamps() -> None:
    """
    Demonstrate handling of invalid timestamp configurations.
    """
    # Create a valid video first
    writer = VideoWriter("temp.mp4", VideoWriterConfig(fps=30))
    frames = [np.zeros((100, 100, 3), dtype=np.uint8)] * 30  # 1 second of black frames
    writer.write_frames(frames)

    # Try invalid timestamp combinations
    try:
        config = VideoReaderConfig(start_time=-1.0)
        reader = VideoReader("temp.mp4", config)
        print("Trying negative start time...")
        for frame in reader.read_frames():
            pass
    except ValueError as e:
        print(f"Expected error - Invalid start time: {e}")

    try:
        config = VideoReaderConfig(start_time=2.0, end_time=1.0)
        reader = VideoReader("temp.mp4", config)
        print("Trying end_time before start_time...")
        for frame in reader.read_frames():
            pass
    except ValueError as e:
        print(f"Expected error - Invalid time range: {e}")

    # Clean up
    Path("temp.mp4").unlink()


def demonstrate_resolution_mismatch() -> None:
    """
    Demonstrate handling of resolution mismatches.
    """
    # Create a video with specific dimensions
    writer = VideoWriter("temp.mp4", VideoWriterConfig(fps=30))
    frames = [np.zeros((100, 100, 3), dtype=np.uint8)] * 30
    writer.write_frames(frames)

    try:
        # Try to read with mismatched resolution
        config = VideoReaderConfig(resolution=(50, 50))  # Non-multiple resolution
        reader = VideoReader("temp.mp4", config)
        print("Trying invalid resolution scaling...")
        for frame in reader.read_frames():
            pass
    except RuntimeError as e:
        print(f"Expected error - Resolution scaling: {e}")

    # Clean up
    Path("temp.mp4").unlink()


def demonstrate_timeout_handling() -> None:
    """
    Demonstrate handling of timeout scenarios.
    """
    # Create a large enough video to potentially trigger timeout
    writer = VideoWriter("large_temp.mp4", VideoWriterConfig(fps=30))
    frames = [np.zeros((1920, 1080, 3), dtype=np.uint8)] * 300  # 10 seconds of HD video
    writer.write_frames(frames)

    try:
        # Try to read with very short timeout
        reader = VideoReader("large_temp.mp4")
        print("Trying operation with short timeout...")
        for frame in reader.read_frames():
            pass
    except TimeoutError as e:
        print(f"Expected error - Operation timeout: {e}")

    # Clean up
    Path("large_temp.mp4").unlink()


def main() -> None:
    """Main entry point for video error handling examples."""
    fire.Fire(
        {
            "invalid_file": demonstrate_invalid_video_file,
            "corrupt": demonstrate_corrupt_video,
            "timestamps": demonstrate_invalid_timestamps,
            "resolution": demonstrate_resolution_mismatch,
            "timeout": demonstrate_timeout_handling,
        }
    )


if __name__ == "__main__":
    main()
