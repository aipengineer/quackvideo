# test_ffmpeg.py
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from quackvideo.core.ffmpeg import FFmpegCommand, FFmpegTimeoutError, FFmpegWrapper


@pytest.fixture
def sample_video(tmp_path) -> Path:
    """Create a test video file using FFmpeg."""
    video_path = tmp_path / "test_video.mp4"

    # Generate a 3-second test video with a black and white pattern
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=3:size=320x240:rate=30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        pytest.skip(f"FFmpeg not available or failed to create test video: {e}")
    except FileNotFoundError:
        pytest.skip("FFmpeg not found in system path")

    return video_path


class TestFFmpegCommand:
    def test_basic_command_construction(self):
        """Test basic FFmpeg command construction."""
        cmd = FFmpegCommand(input_path=Path("input.mp4"))
        result = cmd.build_command()
        assert result == ["ffmpeg", "-i", "input.mp4"]

    def test_command_with_all_parameters(self):
        """Test FFmpeg command construction with all parameters."""
        cmd = FFmpegCommand(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            fps=30,
            start_time=1.5,
            end_time=4.5,
            resolution=(640, 480),
        )
        result = cmd.build_command()
        expected = [
            "ffmpeg",
            "-i",
            "input.mp4",
            "-ss",
            "1.5",
            "-t",
            "3.0",
            "-vf",
            "fps=30,scale=640:480",
            "output.mp4",
        ]
        assert result == expected


class TestFFmpegWrapper:
    def test_get_video_info(self, sample_video):
        """Test video info extraction."""
        width, height = FFmpegWrapper.get_video_info(sample_video)
        assert width == 320
        assert height == 240

    def test_file_not_found(self):
        """Test behavior when video file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            next(FFmpegWrapper.extract_frames("nonexistent.mp4"))

    def test_frame_extraction(self, sample_video):
        """Test basic frame extraction functionality."""
        frames = list(FFmpegWrapper.extract_frames(sample_video))

        assert len(frames) > 0
        first_frame = frames[0]
        assert isinstance(first_frame, np.ndarray)
        assert first_frame.ndim == 3
        assert first_frame.shape == (240, 320, 3)

    def test_frame_extraction_with_fps(self, sample_video):
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            frames = [np.zeros((240, 320, 3), dtype=np.uint8)] * 3  # 3 frames
            mock_process.stdout.read.side_effect = [f.tobytes() for f in frames] + [b""]
            mock_process.stderr.readline.return_value = b""
            mock_process.wait.return_value = 0
            mock_process.returncode = 0
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            with patch(
                "quackvideo.core.ffmpeg.FFmpegWrapper.get_video_info",
                return_value=(320, 240),
            ):
                frames = list(FFmpegWrapper.extract_frames(sample_video, fps=1))
                assert len(frames) == 3

    def test_frame_extraction_with_resolution(self, sample_video):
        """Test frame extraction with resolution specification."""
        target_width, target_height = 160, 120
        frames = list(
            FFmpegWrapper.extract_frames(
                sample_video, resolution=(target_width, target_height)
            )
        )

        assert len(frames) > 0
        for frame in frames:
            assert frame.shape == (target_height, target_width, 3)

    @patch("subprocess.Popen")
    @patch("quackvideo.core.ffmpeg.FFmpegWrapper.get_video_info")
    def test_ffmpeg_error_handling(self, mock_get_info, mock_popen, sample_video):
        """Test error handling when FFmpeg process fails."""
        # Mock video info
        mock_get_info.return_value = (320, 240)

        # Mock process failure with immediate return
        mock_process = Mock()
        mock_process.stdout.read.return_value = b""  # Return empty immediately
        mock_process.stderr.readline.return_value = b"Failed to process video"
        mock_process.wait.return_value = 1
        mock_process.returncode = 1
        mock_process.poll.return_value = 1  # Indicate process has finished
        mock_popen.return_value = mock_process

        with pytest.raises(RuntimeError, match="Error during frame extraction"):
            list(FFmpegWrapper.extract_frames(sample_video))

    def test_frame_extraction_timeout(self, sample_video):
        """Test timeout handling during frame extraction."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.stdout.read.side_effect = FFmpegTimeoutError(
                "Operation timed out"
            )
            mock_popen.return_value = mock_process

            with pytest.raises(FFmpegTimeoutError):
                list(FFmpegWrapper.extract_frames(sample_video, timeout=1))

    def test_get_video_info_error(self, sample_video):
        """Test error handling in get_video_info."""
        with patch("subprocess.run") as mock_run:
            # Mock ffprobe failure
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["ffprobe"], stderr=b"Error"
            )
            with pytest.raises(RuntimeError, match="Failed to get video info"):
                FFmpegWrapper.get_video_info(sample_video)

            # Mock empty output
            mock_run.side_effect = None
            mock_run.return_value = Mock(stdout="", stderr="")
            with pytest.raises(RuntimeError, match="Invalid video info format"):
                FFmpegWrapper.get_video_info(sample_video)

            # Mock invalid format
            mock_run.return_value = Mock(stdout="invalid", stderr="")
            with pytest.raises(RuntimeError, match="Invalid video info format"):
                FFmpegWrapper.get_video_info(sample_video)
