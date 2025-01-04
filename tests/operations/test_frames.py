# tests/operations/test_frames.py

import pytest
import os

from quackvideo.core.operations.frames import extract_frames


def test_extract_frames_basic(temp_output_dir, small_synth_video):
    """
    Extract frames from a short synthetic video. Check that a reasonable number
    of frames is extracted and that the frames are non-empty image files.
    """
    frames_dir = temp_output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    num_extracted = extract_frames(
        input_video=small_synth_video,
        output_dir=str(frames_dir),
        fps=2,  # 2 frames per second
    )
    frame_files = list(frames_dir.glob("frame_*.png"))

    assert (
        len(frame_files) == num_extracted
    ), "Number of extracted frames should match return value."
    for frame_file in frame_files:
        assert frame_file.stat().st_size > 0, f"{frame_file.name} should not be empty."


def test_extract_frames_invalid_input(temp_output_dir):
    """
    Invalid input should raise FileNotFoundError or a custom error.
    """
    with pytest.raises(FileNotFoundError):
        extract_frames(input_video="no_such_file.mp4", output_dir=str(temp_output_dir))
