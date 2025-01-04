# src/quackvideo/core/utils.py
from __future__ import annotations

from collections.abc import Iterator
from enum import Enum
from typing import Callable

import ffmpeg
import numpy as np
from pydantic import BaseModel, Field, field_validator


class ComparisonMethod(str, Enum):
    """Methods for comparing frames."""

    MSE = "mse"  # Mean Squared Error
    MAE = "mae"  # Mean Absolute Error
    SSIM = "ssim"  # Structural Similarity Index


class FrameComparisonConfig(BaseModel):
    """Configuration for frame comparison operations."""

    method: ComparisonMethod = Field(
        default=ComparisonMethod.MSE, description="Method to use for frame comparison"
    )
    threshold: float = Field(
        default=0.3, description="Threshold for scene change detection"
    )
    black_threshold: float = Field(
        default=10.0,
        description="Maximum average pixel value to consider a frame black",
    )

    @field_validator("threshold")
    def validate_threshold(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        return v

    @field_validator("black_threshold")
    def validate_black_threshold(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Black threshold must be non-negative")
        return v


def calculate_frame_difference(
    frame1: np.ndarray,
    frame2: np.ndarray,
    method: ComparisonMethod = ComparisonMethod.MSE,
) -> float:
    """
    Calculate difference between two frames using ffmpeg filters where possible.

    Args:
        frame1: First frame (HxWx3)
        frame2: Second frame (HxWx3)
        method: Comparison method to use

    Returns:
        Difference score (lower means more similar)
    """
    if frame1.shape != frame2.shape:
        raise ValueError(f"Frame shapes don't match: {frame1.shape} vs {frame2.shape}")

    # Ensure frames are in correct format
    frame1 = frame1.astype(np.float32) / 255.0
    frame2 = frame2.astype(np.float32) / 255.0

    if method == ComparisonMethod.MSE:
        return float(np.mean((frame1 - frame2) ** 2))

    elif method == ComparisonMethod.MAE:
        return float(np.mean(np.abs(frame1 - frame2)))

    elif method == ComparisonMethod.SSIM:

        def _ssim(img1: np.ndarray, img2: np.ndarray) -> float:
            """Calculate SSIM between two frames."""
            C1 = (0.01 * 1) ** 2
            C2 = (0.03 * 1) ** 2

            mu1 = np.mean(img1)
            mu2 = np.mean(img2)

            sigma1 = np.std(img1)
            sigma2 = np.std(img2)
            sigma12 = np.mean((img1 - mu1) * (img2 - mu2))

            ssim = ((2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)) / (
                (mu1**2 + mu2**2 + C1) * (sigma1**2 + sigma2**2 + C2)
            )
            return float(ssim)

        return 1.0 - _ssim(frame1, frame2)

    else:
        raise ValueError(f"Unknown comparison method: {method}")


class FeatureExtractionMethod(str, Enum):
    """Methods for extracting features from frames."""

    HISTOGRAM = "histogram"
    AVERAGE_COLOR = "average_color"
    DCT = "dct"  # Discrete Cosine Transform


class FeatureExtractor(BaseModel):
    """Configuration and methods for feature extraction."""

    method: FeatureExtractionMethod = Field(
        default=FeatureExtractionMethod.HISTOGRAM,
        description="Method to use for feature extraction",
    )
    bins: int = Field(default=256, description="Number of bins for histogram")

    def extract(self, frame: np.ndarray) -> np.ndarray:
        """Extract features from a frame."""
        if self.method == FeatureExtractionMethod.HISTOGRAM:
            return np.array(
                [
                    np.histogram(frame[:, :, i], bins=self.bins, range=(0, 256))[0]
                    for i in range(3)
                ]
            ).flatten()

        elif self.method == FeatureExtractionMethod.AVERAGE_COLOR:
            return frame.mean(axis=(0, 1))

        elif self.method == FeatureExtractionMethod.DCT:
            # Use ffmpeg's DCT filter
            try:
                process = (
                    ffmpeg.input(
                        "pipe:",
                        format="rawvideo",
                        pix_fmt="rgb24",
                        s=f"{frame.shape[1]}x{frame.shape[0]}",
                    )
                    .filter("dctdnoiz")  # Apply DCT denoising filter
                    .output("pipe:", format="rawvideo", pix_fmt="rgb24")
                    .run_async(pipe_stdin=True, pipe_stdout=True)
                )

                process.stdin.write(frame.tobytes())
                process.stdin.close()

                out_bytes = process.stdout.read(frame.size)
                dct_frame = np.frombuffer(out_bytes, dtype=np.uint8).reshape(
                    frame.shape
                )
                return dct_frame.mean(axis=(0, 1))

            except ffmpeg.Error as e:
                raise ValueError(f"FFmpeg DCT extraction failed: {str(e)}")

        else:
            raise ValueError(f"Unknown feature extraction method: {self.method}")


def detect_black_frames(frame: np.ndarray, threshold: float = 10.0) -> bool:
    """
    Detect if a frame is mostly black.

    Args:
        frame: Input frame (HxWx3)
        threshold: Maximum average pixel value to consider black

    Returns:
        True if frame is considered black
    """
    return float(np.mean(frame)) < threshold


def detect_scene_change(
    frame1: np.ndarray, frame2: np.ndarray, config: FrameComparisonConfig | None = None
) -> bool:
    """
    Detect if there's a scene change between frames.

    Args:
        frame1: First frame (HxWx3)
        frame2: Second frame (HxWx3)
        config: Configuration for scene change detection

    Returns:
        True if scene change detected
    """
    config = config or FrameComparisonConfig()
    diff = calculate_frame_difference(frame1, frame2, config.method)
    return diff > config.threshold


def find_similar_frames(
    target_frame: np.ndarray,
    frame_iterator: Iterator[tuple[float, np.ndarray]],
    config: FrameComparisonConfig | None = None,
    feature_extractor: FeatureExtractor | None = None,
) -> Iterator[tuple[float, np.ndarray, float]]:
    """
    Find frames similar to a target frame.

    Args:
        target_frame: Frame to compare against (HxWx3)
        frame_iterator: Iterator of (timestamp, frame) tuples
        config: Configuration for frame comparison
        feature_extractor: Optional feature extractor for comparison

    Yields:
        Tuples of (timestamp, frame, difference_score)
    """
    config = config or FrameComparisonConfig()
    feature_extractor = feature_extractor or FeatureExtractor()

    # Extract features from target frame
    target_features = feature_extractor.extract(target_frame)

    for timestamp, frame in frame_iterator:
        try:
            # Extract features from current frame
            frame_features = feature_extractor.extract(frame)

            # Calculate difference using selected method
            diff = calculate_frame_difference(
                target_features.reshape(1, -1),
                frame_features.reshape(1, -1),
                config.method,
            )

            if diff <= config.threshold:
                yield timestamp, frame, diff

        except ValueError:
            continue  # Skip frames with incompatible dimensions
