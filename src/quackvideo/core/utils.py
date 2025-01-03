# src/quackvideo/core/utils.py
from collections.abc import Iterator

import numpy as np


def calculate_frame_difference(
    frame1: np.ndarray, frame2: np.ndarray, method: str = "mse"
) -> float:
    """
    Calculate difference between two frames.

    Args:
        frame1: First frame (HxWx3)
        frame2: Second frame (HxWx3)
        method: One of "mse", "mae", "ssim"

    Returns:
        Difference score (lower means more similar)
    """
    # Ensure frames have same shape
    if frame1.shape != frame2.shape:
        raise ValueError(f"Frame shapes don't match: {frame1.shape} vs {frame2.shape}")

    # Ensure frames are in correct format
    frame1 = frame1.astype(np.float32)
    frame2 = frame2.astype(np.float32)

    if method == "mse":
        return float(np.mean((frame1 - frame2) ** 2))
    elif method == "mae":
        return float(np.mean(np.abs(frame1 - frame2)))
    elif method == "ssim":
        # Simplified SSIM implementation
        def _ssim(img1, img2):
            C1 = (0.01 * 255) ** 2
            C2 = (0.03 * 255) ** 2

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
        raise ValueError(f"Unknown method: {method}")


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
    frame1: np.ndarray, frame2: np.ndarray, threshold: float = 0.3, method: str = "mse"
) -> bool:
    """
    Detect if there's a scene change between frames.

    Args:
        frame1: First frame (HxWx3)
        frame2: Second frame (HxWx3)
        threshold: Difference threshold to consider a scene change
        method: Difference calculation method

    Returns:
        True if scene change detected
    """
    diff = calculate_frame_difference(frame1, frame2, method)
    return diff > threshold


def extract_frame_features(frame: np.ndarray, method: str = "histogram") -> np.ndarray:
    """
    Extract features from a frame for comparison.

    Args:
        frame: Input frame (HxWx3)
        method: Feature extraction method

    Returns:
        Feature vector
    """
    if method == "histogram":
        hist = np.array(
            [
                np.histogram(frame[:, :, i], bins=256, range=(0, 256))[0]
                for i in range(3)
            ]
        )
        return hist.flatten()
    elif method == "average_color":
        return frame.mean(axis=(0, 1))
    else:
        raise ValueError(f"Unknown method: {method}")


def find_similar_frames(
    target_frame: np.ndarray,
    frame_iterator: Iterator[tuple[float, np.ndarray]],
    threshold: float = 0.1,
    method: str = "mse",
) -> Iterator[tuple[float, np.ndarray, float]]:
    """
    Find frames similar to a target frame.

    Args:
        target_frame: Frame to compare against (HxWx3)
        frame_iterator: Iterator of (timestamp, frame) tuples
        threshold: Maximum difference to consider similar
        method: Comparison method

    Yields:
        Tuples of (timestamp, frame, difference_score)
    """
    target_frame = target_frame.astype(np.float32)

    for timestamp, frame in frame_iterator:
        try:
            diff = calculate_frame_difference(target_frame, frame, method)
            if diff <= threshold:
                yield timestamp, frame, diff
        except ValueError:
            continue  # Skip frames with incompatible dimensions
