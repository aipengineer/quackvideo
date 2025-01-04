from __future__ import annotations

from pathlib import Path

import fire
import numpy as np
from tqdm import tqdm

from quackvideo.core.ffmpeg import FFmpegWrapper, FFmpegError, FFmpegTimeoutError
from quackvideo.core.operations.frames import FrameExtractor, FrameExtractionConfig


def demonstrate_frame_extraction_errors() -> None:
    """
    Demonstrate handling of frame extraction errors.
    """
    # Create a very short test video
    temp_path = Path("temp_test.mp4")
    try:
        # Create a test video with FFmpeg
        frames = [
            np.zeros((100, 100, 3), dtype=np.uint8)
        ] * 30  # 1 second of black frames
        write_test_video(temp_path, frames)

        # Try various error scenarios
        demonstrate_invalid_fps(temp_path)
        demonstrate_out_of_range_extraction(temp_path)
        demonstrate_resolution_errors(temp_path)
        demonstrate_extraction_interruption(temp_path)

    finally:
        # Clean up
        if temp_path.exists():
            temp_path.unlink()


def write_test_video(path: Path, frames: list[np.ndarray]) -> None:
    """Helper function to write a test video."""
    stream = (
        ffmpeg.input("pipe:", format="rawvideo", pix_fmt="rgb24", s="100x100", r=30)
        .output(str(path), pix_fmt="yuv420p")
        .overwrite_output()
    )

    process = stream.run_async(pipe_stdin=True)
    for frame in frames:
        process.stdin.write(frame.tobytes())
    process.stdin.close()
    process.wait()


def demonstrate_invalid_fps(video_path: Path) -> None:
    """
    Demonstrate handling of invalid FPS configurations.
    """
    print("\nTesting invalid FPS scenarios:")

    # Test negative FPS
    try:
        config = FrameExtractionConfig(fps="-1/1")
        extractor = FrameExtractor(config, Path("output"))
        extractor.extract_frames(video_path)
    except ValueError as e:
        print(f"Expected error - Negative FPS: {e}")

    # Test zero FPS
    try:
        config = FrameExtractionConfig(fps="0/1")
        extractor = FrameExtractor(config, Path("output"))
        extractor.extract_frames(video_path)
    except ValueError as e:
        print(f"Expected error - Zero FPS: {e}")

    # Test invalid FPS format
    try:
        config = FrameExtractionConfig(fps="invalid")
        extractor = FrameExtractor(config, Path("output"))
        extractor.extract_frames(video_path)
    except ValueError as e:
        print(f"Expected error - Invalid FPS format: {e}")


def demonstrate_out_of_range_extraction(video_path: Path) -> None:
    """
    Demonstrate handling of out-of-range frame extraction attempts.
    """
    print("\nTesting out-of-range extraction scenarios:")

    try:
        # Try to extract frames beyond video duration
        config = FrameExtractionConfig()
        extractor = FrameExtractor(config, Path("output"))
        list(
            FFmpegWrapper.extract_frames(
                video_path,
                start_time=100.0,  # Way beyond our 1-second video
            )
        )
    except FFmpegError as e:
        print(f"Expected error - Out of range extraction: {e}")


def demonstrate_resolution_errors(video_path: Path) -> None:
    """
    Demonstrate handling of resolution-related errors.
    """
    print("\nTesting resolution error scenarios:")

    # Test invalid resolution values
    try:
        config = FrameExtractionConfig()
        list(
            FFmpegWrapper.extract_frames(
                video_path,
                resolution=(-1, 100),  # Negative width
            )
        )
    except ValueError as e:
        print(f"Expected error - Negative resolution: {e}")

    # Test zero resolution
    try:
        config = FrameExtractionConfig()
        list(
            FFmpegWrapper.extract_frames(
                video_path,
                resolution=(0, 0),  # Zero resolution
            )
        )
    except ValueError as e:
        print(f"Expected error - Zero resolution: {e}")


def demonstrate_extraction_interruption(video_path: Path) -> None:
    """
    Demonstrate handling of interrupted frame extraction.
    """
    print("\nTesting extraction interruption handling:")

    try:
        config = FrameExtractionConfig()
        frames_iterator = FFmpegWrapper.extract_frames(video_path)

        # Simulate interruption after first frame
        first_frame = next(frames_iterator)
        raise KeyboardInterrupt("Simulated interruption")

    except KeyboardInterrupt as e:
        print(f"Expected error - Extraction interrupted: {e}")
        # Verify cleanup occurred
        print("Verifying cleanup after interruption...")


def demonstrate_timeout_scenarios(video_path: Path) -> None:
    """
    Demonstrate handling of timeout scenarios during frame extraction.
    """
    print("\nTesting timeout scenarios:")

    try:
        # Set a very short timeout
        list(
            FFmpegWrapper.extract_frames(
                video_path,
                timeout=0.001,  # Unrealistically short timeout
            )
        )
    except FFmpegTimeoutError as e:
        print(f"Expected error - Operation timeout: {e}")


def main() -> None:
    """Main entry point for frame extraction error handling examples."""
    fire.Fire(
        {
            "all": demonstrate_frame_extraction_errors,
            "fps": lambda: demonstrate_frame_extraction_errors(Path("temp_test.mp4")),
            "range": lambda: demonstrate_out_of_range_extraction(Path("temp_test.mp4")),
            "resolution": lambda: demonstrate_resolution_errors(Path("temp_test.mp4")),
            "interruption": lambda: demonstrate_extraction_interruption(
                Path("temp_test.mp4")
            ),
            "timeout": lambda: demonstrate_timeout_scenarios(Path("temp_test.mp4")),
        }
    )


if __name__ == "__main__":
    main()
