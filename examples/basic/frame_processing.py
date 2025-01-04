from __future__ import annotations

from pathlib import Path
from typing import Iterator

import fire
import numpy as np
from tqdm import tqdm

from quackvideo.video.reader import VideoReader, VideoReaderConfig
from quackvideo.video.writer import VideoWriter, VideoWriterConfig
from quackvideo.core.utils import (
    FeatureExtractor,
    FeatureExtractionMethod,
    detect_scene_change,
    detect_black_frames,
    FrameComparisonConfig,
)


def process_scene_changes(
    input_path: str,
    output_path: str,
    threshold: float = 0.3,
) -> None:
    """
    Detect and save frames where scene changes occur.

    Args:
        input_path: Path to input video
        output_path: Path to save detected scene frames
        threshold: Threshold for scene change detection
    """
    reader = VideoReader(input_path)
    config = FrameComparisonConfig(threshold=threshold)

    print(f"\nAnalyzing video for scene changes (threshold: {threshold})")

    frames = list(tqdm(reader.read_frames(), desc="Reading frames"))
    if len(frames) < 2:
        print("Video too short for scene detection")
        return

    scene_changes = []
    prev_frame = frames[0]

    for i, frame in enumerate(tqdm(frames[1:], desc="Detecting scenes")):
        if detect_scene_change(prev_frame, frame, config):
            timestamp = (i + 1) / reader.metadata.fps
            scene_changes.append((timestamp, frame))
        prev_frame = frame

    print(f"\nDetected {len(scene_changes)} scene changes")

    if scene_changes:
        # Save scene change frames as video
        writer = VideoWriter(
            output_path,
            VideoWriterConfig(fps=1),  # 1 frame per second for easy viewing
        )
        writer.write_frames([frame for _, frame in scene_changes])
        print(f"Saved scene change frames to: {output_path}")


def analyze_black_frames(
    input_path: str,
    threshold: float = 10.0,
) -> None:
    """
    Detect and report black frames in a video.

    Args:
        input_path: Path to input video
        threshold: Maximum average pixel value to consider black
    """
    reader = VideoReader(input_path)

    black_frames = []
    total_frames = 0

    print(f"\nAnalyzing video for black frames (threshold: {threshold})")

    for frame in tqdm(reader.read_frames(), desc="Processing"):
        if detect_black_frames(frame, threshold):
            timestamp = total_frames / reader.metadata.fps
            black_frames.append(timestamp)
        total_frames += 1

    if black_frames:
        print(f"\nDetected {len(black_frames)} black frames at timestamps:")
        for timestamp in black_frames:
            print(f"  - {timestamp:.2f}s")
    else:
        print("\nNo black frames detected")

    print(f"Total frames analyzed: {total_frames}")


def extract_features(
    input_path: str,
    method: str = "histogram",
    output_path: str | None = None,
) -> None:
    """
    Extract and analyze frame features.

    Args:
        input_path: Path to input video
        method: Feature extraction method ('histogram' or 'average_color')
        output_path: Optional path to save feature data
    """
    reader = VideoReader(input_path)
    extractor = FeatureExtractor(method=FeatureExtractionMethod(method))

    features = []
    print(f"\nExtracting features using method: {method}")

    for frame in tqdm(reader.read_frames(), desc="Processing"):
        frame_features = extractor.extract(frame)
        features.append(frame_features)

    features = np.array(features)

    print(f"\nExtracted features shape: {features.shape}")

    if output_path:
        np.save(output_path, features)
        print(f"Saved features to: {output_path}")

    # Basic feature analysis
    print("\nFeature Statistics:")
    print(f"Mean: {np.mean(features):.2f}")
    print(f"Std: {np.std(features):.2f}")
    print(f"Min: {np.min(features):.2f}")
    print(f"Max: {np.max(features):.2f}")


def main() -> None:
    """Main entry point for frame processing examples."""
    fire.Fire(
        {
            "scenes": process_scene_changes,
            "black": analyze_black_frames,
            "features": extract_features,
        }
    )


if __name__ == "__main__":
    main()
