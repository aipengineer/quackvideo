from __future__ import annotations

from pathlib import Path
from typing import Optional

import fire

from quackvideo.core.operations.frames import FrameExtractor, FrameExtractionConfig
from quackvideo.synthetic.video import VideoGenerator, VideoConfig, VideoPattern


def extract_frames(
    video_path: str,
    output_dir: str,
    fps: str = "1/5",
    format: str = "png",
    quality: int = 100,
    skip_validation: bool = False,
) -> None:
    """
    Extract frames from video file.

    Args:
        video_path: Input video file
        output_dir: Output directory
        fps: Frames per second (e.g. "1/5" for 1 frame every 5 seconds)
        format: Output format (png/jpg)
        quality: Output quality (1-100)
        skip_validation: Skip input validation
    """
    config = FrameExtractionConfig(
        fps=fps,
        format=format,
        quality=quality,
    )

    extractor = FrameExtractor(config, Path(output_dir))
    result = extractor.extract_frames(Path(video_path))
    print(f"Extracted {result.total_frames} frames to: {result.output_directory}")


def extract_with_synthetic(
    output_dir: str,
    pattern: str = "color_bars",
    duration: float = 10.0,
    fps_extract: str = "1/5",
) -> None:
    """
    Generate synthetic video and extract frames.

    Args:
        output_dir: Output directory
        pattern: Video pattern type
        duration: Video duration in seconds
        fps_extract: Frame extraction rate
    """
    # Generate synthetic video
    output_dir = Path(output_dir)
    video_path = output_dir / "synthetic.mp4"

    video_config = VideoConfig(
        pattern=VideoPattern(pattern),
        duration=duration,
    )

    generator = VideoGenerator(video_config)
    video_file = generator.generate(video_path)

    # Extract frames
    extract_frames(str(video_file), str(output_dir), fps=fps_extract)


def main() -> None:
    """Main entry point for frame extraction."""
    fire.Fire(
        {
            "extract": extract_frames,
            "synthetic": extract_with_synthetic,
        }
    )


if __name__ == "__main__":
    main()
