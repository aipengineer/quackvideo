from __future__ import annotations

from pathlib import Path
from typing import Iterator

import fire
import numpy as np
from tqdm import tqdm

from quackvideo.video.reader import VideoReader, VideoReaderConfig
from quackvideo.video.writer import VideoWriter, VideoWriterConfig
from quackvideo.core.utils import FeatureExtractor, FeatureExtractionMethod


def manipulate_sequential(
    input_path: str,
    output_path: str,
    operation: str = "mirror",
) -> None:
    """
    Apply sequential frame manipulation.

    Args:
        input_path: Path to input video
        output_path: Path to save processed video
        operation: Type of manipulation ('mirror', 'rotate', 'invert')
    """
    reader = VideoReader(input_path)
    writer = VideoWriter(output_path, VideoWriterConfig(fps=reader.metadata.fps))

    def process_frame(frame: np.ndarray, op: str) -> np.ndarray:
        if op == "mirror":
            return np.fliplr(frame)
        elif op == "rotate":
            return np.rot90(frame)
        elif op == "invert":
            return 255 - frame
        else:
            raise ValueError(f"Unknown operation: {op}")

    processed_frames = []
    print(f"\nApplying {operation} operation to frames")

    for frame in tqdm(reader.read_frames(), desc="Processing"):
        processed = process_frame(frame, operation)
        processed_frames.append(processed)

    result = writer.write_frames(processed_frames)
    print(f"\nProcessed {result.frame_count} frames")
    print(f"Output saved to: {result.output_path}")


def manipulate_sliding_window(
    input_path: str,
    output_path: str,
    window_size: int = 5,
) -> None:
    """
    Apply manipulation using sliding window of frames.

    Args:
        input_path: Path to input video
        output_path: Path to save processed video
        window_size: Number of frames in sliding window
    """
    reader = VideoReader(input_path)
    writer = VideoWriter(output_path, VideoWriterConfig(fps=reader.metadata.fps))

    def process_window(frames: list[np.ndarray]) -> np.ndarray:
        """Average frames in the window."""
        return np.mean(frames, axis=0).astype(np.uint8)

    # Initialize frame buffer
    frame_buffer = []
    processed_frames = []

    print(f"\nProcessing with window size: {window_size}")

    for frame in tqdm(reader.read_frames(), desc="Processing"):
        frame_buffer.append(frame)

        if len(frame_buffer) >= window_size:
            processed = process_window(frame_buffer)
            processed_frames.append(processed)
            frame_buffer.pop(0)

    result = writer.write_frames(processed_frames)
    print(f"\nProcessed {result.frame_count} frames")
    print(f"Output saved to: {result.output_path}")


def manipulate_with_features(
    input_path: str,
    output_path: str,
    feature_method: str = "histogram",
    threshold: float = 0.5,
) -> None:
    """
    Manipulate frames based on feature analysis.

    Args:
        input_path: Path to input video
        output_path: Path to save processed video
        feature_method: Feature extraction method
        threshold: Feature difference threshold
    """
    reader = VideoReader(input_path)
    writer = VideoWriter(output_path, VideoWriterConfig(fps=reader.metadata.fps))

    extractor = FeatureExtractor(method=FeatureExtractionMethod(feature_method))

    def process_based_on_features(
        frame: np.ndarray, features: np.ndarray, base_features: np.ndarray
    ) -> np.ndarray:
        """Process frame based on feature difference."""
        diff = np.mean(np.abs(features - base_features))
        if diff > threshold:
            # Apply stronger effect for more different frames
            return np.flip(frame, axis=(0, 1))
        else:
            # Apply milder effect for similar frames
            return np.flip(frame, axis=1)

    # Read all frames first
    print("\nReading frames and extracting features")
    frames = []
    features = []

    for frame in tqdm(reader.read_frames(), desc="Analyzing"):
        frames.append(frame)
        features.append(extractor.extract(frame))

    features = np.array(features)
    base_features = features[0]  # Use first frame as reference

    # Process frames based on features
    print("\nProcessing frames based on feature analysis")
    processed_frames = []

    for frame, frame_features in tqdm(zip(frames, features), desc="Processing"):
        processed = process_based_on_features(frame, frame_features, base_features)
        processed_frames.append(processed)

    result = writer.write_frames(processed_frames)
    print(f"\nProcessed {result.frame_count} frames")
    print(f"Output saved to: {result.output_path}")


def main() -> None:
    """Main entry point for frame manipulation examples."""
    fire.Fire(
        {
            "sequential": manipulate_sequential,
            "window": manipulate_sliding_window,
            "features": manipulate_with_features,
        }
    )


if __name__ == "__main__":
    main()
