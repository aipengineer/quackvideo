from __future__ import annotations

from pathlib import Path

import fire
from tqdm import tqdm

from quackvideo.core.ffmpeg import FFmpegWrapper
from quackvideo.core.operations.frames import FrameExtractor, FrameExtractionConfig


def extract_basic(
    input_path: str,
    output_dir: str,
    fps: str = "1",
) -> None:
    """
    Basic frame extraction demonstration.

    Args:
        input_path: Path to input video
        output_dir: Directory to save frames
        fps: Frames per second to extract (can be fraction like "1/2")
    """
    config = FrameExtractionConfig(fps=fps, format="png", quality=95)

    extractor = FrameExtractor(config, Path(output_dir))

    print(f"\nExtracting frames at {fps} FPS")
    result = extractor.extract_frames(Path(input_path))

    print(f"\nExtraction complete:")
    print(f"Total frames: {result.total_frames}")
    print(f"Output directory: {result.output_directory}")
    print("Frame hashes stored for integrity verification")


def extract_with_resume(
    input_path: str,
    output_dir: str,
    fps: str = "1",
) -> None:
    """
    Demonstrate frame extraction with resume capability.

    Args:
        input_path: Path to input video
        output_dir: Directory to save frames
        fps: Frames per second to extract
    """
    config = FrameExtractionConfig(fps=fps, format="png", quality=95)

    extractor = FrameExtractor(config, Path(output_dir))

    print(f"\nStarting extraction with resume capability")
    print("Note: You can interrupt (Ctrl+C) and restart to test resume")

    try:
        result = extractor.extract_frames(Path(input_path), resume=True)

        print(f"\nExtraction complete:")
        print(f"Total frames: {result.total_frames}")
        print(f"Output directory: {result.output_directory}")

    except KeyboardInterrupt:
        print("\nExtraction interrupted - can be resumed")
        return


def extract_frames_direct(
    input_path: str,
    start_time: float | None = None,
    end_time: float | None = None,
    fps: float | None = None,
) -> None:
    """
    Demonstrate direct frame extraction using FFmpegWrapper.

    Args:
        input_path: Path to input video
        start_time: Start time in seconds
        end_time: End time in seconds
        fps: Frames per second to extract
    """
    print(f"\nExtracting frames directly:")
    print(f"Time range: {start_time or 0}s to {end_time or 'end'}")
    print(f"FPS: {fps or 'original'}")

    frame_count = 0
    for frame in tqdm(
        FFmpegWrapper.extract_frames(
            video_path=input_path, fps=fps, start_time=start_time, end_time=end_time
        ),
        desc="Extracting",
    ):
        frame_count += 1

    print(f"\nExtracted {frame_count} frames")


def verify_frame_integrity(
    input_path: str,
    output_dir: str,
    fps: str = "1",
) -> None:
    """
    Demonstrate frame integrity verification.

    Args:
        input_path: Path to input video
        output_dir: Directory to save frames
        fps: Frames per second to extract
    """
    config = FrameExtractionConfig(fps=fps, format="png", quality=95)

    extractor = FrameExtractor(config, Path(output_dir))

    # First extraction
    print("\nPerforming initial extraction")
    result = extractor.extract_frames(Path(input_path))
    initial_hashes = result.frame_files.copy()

    # Verify integrity
    print("\nVerifying frame integrity")
    result = extractor.extract_frames(Path(input_path), resume=True)

    if result.frame_files == initial_hashes:
        print("Frame integrity verified - all hashes match")
    else:
        print("Frame integrity mismatch detected")

    print(f"Verified {len(result.frame_files)} frames")


def main() -> None:
    """Main entry point for frame extraction examples."""
    fire.Fire(
        {
            "basic": extract_basic,
            "resume": extract_with_resume,
            "direct": extract_frames_direct,
            "verify": verify_frame_integrity,
        }
    )


if __name__ == "__main__":
    main()
