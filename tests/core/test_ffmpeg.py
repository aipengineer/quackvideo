# tests/core/test_ffmpeg.py

import pytest
import os

from quackvideo.core.ffmpeg import build_ffmpeg_cmd, run_ffmpeg_process


def test_build_ffmpeg_cmd_basic():
    """
    Test constructing a basic ffmpeg command.
    """
    cmd = build_ffmpeg_cmd(
        input_file="input.mp4", output_file="output.mp4", codec="libx264"
    )
    assert isinstance(cmd, list), "FFmpeg command should be returned as a list of args."
    assert "input.mp4" in cmd
    assert "output.mp4" in cmd


@pytest.mark.parametrize("invalid_input", [None, "", 123])
def test_build_ffmpeg_cmd_invalid_input(invalid_input):
    """
    Ensure ValueError is raised when input_file is invalid.
    """
    with pytest.raises(ValueError):
        build_ffmpeg_cmd(input_file=invalid_input, output_file="output.mp4")


def test_run_ffmpeg_process_success(temp_output_dir, small_synth_video):
    """
    Test a real ffmpeg process run on a small synthetic video, ensuring it returns 0.
    """
    out_file = temp_output_dir / "test_converted.mp4"
    cmd = build_ffmpeg_cmd(
        input_file=small_synth_video, output_file=str(out_file), codec="libx264"
    )
    result = run_ffmpeg_process(cmd)
    assert result == 0, "FFmpeg process should return 0 on success."
    assert (
        out_file.exists() and os.path.getsize(out_file) > 0
    ), "Output file should be created."


def test_run_ffmpeg_process_failure():
    """
    Ensure a failing ffmpeg command raises an exception or returns non-zero.
    """
    with pytest.raises(RuntimeError):
        # Intentionally invalid input
        run_ffmpeg_process(["ffmpeg", "-i", "non_existent.mp4", "out.mp4"])
