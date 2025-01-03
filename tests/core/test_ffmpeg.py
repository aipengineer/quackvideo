# tests/core/test_ffmpeg.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import ffmpeg

from quackvideo.core.ffmpeg import (
    FFmpegWrapper,
    FFmpegCommand,
    FFmpegOperationError,
    FFmpegTimeoutError,
)


class TestFFmpegCommand:
    def test_command_initialization(self):
        """Test basic command initialization."""
        cmd = FFmpegCommand(input_path=Path("input.mp4"))
        assert cmd.input_path == Path("input.mp4")
        assert cmd.output_path is None

    def test_command_building(self):
        """Test FFmpeg command construction."""
        cmd = FFmpegCommand(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            fps=30,
            start_time=1.0,
            end_time=4.0,
            resolution=(640, 480),
        )
        result = cmd.build_command()
        expected = [
            "ffmpeg",
            "-i",
            "input.mp4",
            "-ss",
            "1.0",
            "-t",
            "3.0",
            "-vf",
            "fps=30,scale=640:480",
            "output.mp4",
        ]
        assert result == expected

    def test_command_validation(self):
        """Test command parameter validation."""
        with pytest.raises(ValueError):
            FFmpegCommand(input_path=Path("input.mp4"), fps=-1)

        with pytest.raises(ValueError):
            FFmpegCommand(input_path=Path("input.mp4"), resolution=(0, 480))


class TestFFmpegWrapper:
    def test_initialization(self, check_ffmpeg):
        """Test wrapper initialization."""
        wrapper = FFmpegWrapper()
        assert wrapper.timeout == 30  # Default timeout

    def test_ffmpeg_version(self, check_ffmpeg):
        """Test FFmpeg version checking."""
        version = FFmpegWrapper.get_ffmpeg_version()
        assert isinstance(version, str)
        assert version.startswith("ff")

    def test_probe_video(self, test_video):
        """Test video probing functionality."""
        info = FFmpegWrapper.probe_video(test_video)
        assert "streams" in info
        assert "format" in info

        # Verify video stream information
        video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        assert video_stream["width"] == 320
        assert video_stream["height"] == 240

    @patch("subprocess.Popen")
    def test_stream_handling(self, mock_popen, test_video):
        """Test FFmpeg stream handling."""
        mock_process = Mock()
        mock_process.stdout.read.return_value = b""
        mock_process.stderr.readline.return_value = b""
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process

        wrapper = FFmpegWrapper()
        stream = ffmpeg.input(str(test_video))
        wrapper.run_ffmpeg(stream)

        mock_popen.assert_called_once()

    def test_error_handling(self, test_video):
        """Test FFmpeg error handling."""
        wrapper = FFmpegWrapper()

        # Test invalid input
        with pytest.raises(FileNotFoundError):
            wrapper.probe_video(Path("nonexistent.mp4"))

        # Test FFmpeg error
        with pytest.raises(FFmpegOperationError):
            stream = ffmpeg.input("invalid")
            wrapper.run_ffmpeg(stream)

        # Test timeout
        with pytest.raises(FFmpegTimeoutError):
            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.poll.return_value = None  # Process never finishes
                mock_popen.return_value = mock_process

                wrapper = FFmpegWrapper(timeout=0.1)
                stream = ffmpeg.input(str(test_video))
                wrapper.run_ffmpeg(stream)

    @patch("subprocess.Popen")
    def test_progress_callback(self, mock_popen, test_video):
        """Test progress callback functionality."""
        progress_data = []

        def progress_callback(data):
            progress_data.append(data)

        mock_process = Mock()
        mock_process.stderr.readline.side_effect = [
            b"frame=  10 fps=25 time=1.0 bitrate=1000k\n",
            b"frame=  20 fps=25 time=2.0 bitrate=1000k\n",
            b"",
        ]
        mock_process.poll.side_effect = [None, None, 0]
        mock_popen.return_value = mock_process

        wrapper = FFmpegWrapper()
        stream = ffmpeg.input(str(test_video))
        wrapper.run_ffmpeg(stream, progress_callback=progress_callback)

        assert len(progress_data) == 2
        assert all("frame" in data for data in progress_data)

    def test_resource_cleanup(self, test_video):
        """Test proper resource cleanup."""
        wrapper = FFmpegWrapper()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = 0
            mock_popen.return_value = mock_process

            stream = ffmpeg.input(str(test_video))
            wrapper.run_ffmpeg(stream)

            mock_process.stdout.close.assert_called_once()
            mock_process.stderr.close.assert_called_once()
            mock_process.wait.assert_called_once()

    @pytest.mark.parametrize(
        "input_args,expected_args",
        [
            ({}, ["-hide_banner"]),
            ({"loglevel": "error"}, ["-hide_banner", "-loglevel", "error"]),
            ({"y": None}, ["-hide_banner", "-y"]),
        ],
    )
    def test_global_options(self, input_args, expected_args):
        """Test FFmpeg global options handling."""
        cmd = FFmpegCommand(input_path=Path("input.mp4"), global_options=input_args)
        result = cmd.build_command()
        for arg in expected_args:
            assert arg in result
