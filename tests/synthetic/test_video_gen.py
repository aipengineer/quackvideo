# tests/synthetic/test_video_gen.py
import pytest
import numpy as np
from pathlib import Path
import cv2
import ffmpeg

from quackvideo.synthetic.video import (
    VideoGenerator,
    VideoConfig,
    VideoPattern,
    VideoGenerationError,
)


class TestVideoGenerator:
    """Test suite for synthetic video generation."""

    def test_initialization(self):
        """Test VideoGenerator initialization."""
        config = VideoConfig()
        generator = VideoGenerator(config)
        assert generator.config == config

    class TestBasicPatterns:
        """Test basic video pattern generation."""

        @pytest.mark.parametrize(
            "pattern",
            [
                VideoPattern.COLOR_BARS,
                VideoPattern.GRADIENT,
                VideoPattern.CHECKERBOARD,
                VideoPattern.MOVING_BOX,
                VideoPattern.PULSE,
            ],
        )
        def test_pattern_generation(self, pattern, temp_media_dir):
            """Test generation of all basic patterns."""
            config = VideoConfig(
                pattern=pattern, duration=1.0, width=640, height=480, fps=30.0
            )
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / f"{pattern.value}.mp4")

            # Verify file exists and properties
            assert output_file.exists()
            probe = ffmpeg.probe(str(output_file))
            video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")

            assert int(video_info["width"]) == 640
            assert int(video_info["height"]) == 480
            assert float(probe["format"]["duration"]) == pytest.approx(1.0, rel=1e-1)

        def test_color_bars_pattern(self, temp_media_dir):
            """Test specific properties of color bars pattern."""
            config = VideoConfig(pattern=VideoPattern.COLOR_BARS, width=640, height=480)
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / "bars.mp4")

            # Read first frame
            cap = cv2.VideoCapture(str(output_file))
            ret, frame = cap.read()
            cap.release()

            assert ret
            assert frame.shape == (480, 640, 3)

            # Verify color bar properties (basic check)
            # Each bar should have different colors
            unique_colors = set(tuple(pixel) for row in frame for pixel in row)
            assert len(unique_colors) >= 7  # At least 7 different colors

    class TestMotionPatterns:
        """Test patterns with motion."""

        def test_moving_box(self, temp_media_dir):
            """Test moving box pattern properties."""
            config = VideoConfig(
                pattern=VideoPattern.MOVING_BOX, duration=2.0, fps=30.0
            )
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / "moving_box.mp4")

            # Check multiple frames for motion
            cap = cv2.VideoCapture(str(output_file))
            frames = []
            while len(frames) < 10:  # Check first 10 frames
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            cap.release()

            # Verify motion by comparing frames
            differences = [
                np.mean(np.abs(frames[i + 1] - frames[i]))
                for i in range(len(frames) - 1)
            ]
            assert any(diff > 0 for diff in differences)  # Should have motion

        def test_pulse_pattern(self, temp_media_dir):
            """Test pulse pattern properties."""
            config = VideoConfig(pattern=VideoPattern.PULSE, duration=1.0, fps=30.0)
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / "pulse.mp4")

            # Check brightness variations
            cap = cv2.VideoCapture(str(output_file))
            brightnesses = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                brightness = np.mean(frame)
                brightnesses.append(brightness)
            cap.release()

            # Should have variation in brightness
            assert max(brightnesses) - min(brightnesses) > 10

    class TestConfiguration:
        """Test configuration handling."""

        @pytest.mark.parametrize(
            "resolution", [(640, 480), (1280, 720), (1920, 1080), (3840, 2160)]
        )
        def test_resolutions(self, resolution, temp_media_dir):
            """Test different resolutions."""
            width, height = resolution
            config = VideoConfig(
                pattern=VideoPattern.COLOR_BARS, width=width, height=height
            )
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / "test.mp4")

            probe = ffmpeg.probe(str(output_file))
            video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
            assert int(video_info["width"]) == width
            assert int(video_info["height"]) == height

        @pytest.mark.parametrize("fps", [24.0, 30.0, 60.0])
        def test_frame_rates(self, fps, temp_media_dir):
            """Test different frame rates."""
            config = VideoConfig(pattern=VideoPattern.COLOR_BARS, fps=fps)
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / "test.mp4")

            probe = ffmpeg.probe(str(output_file))
            video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
            assert float(eval(video_info["r_frame_rate"])) == pytest.approx(
                fps, rel=1e-1
            )

    class TestErrorHandling:
        """Test error handling."""

        def test_invalid_configuration(self):
            """Test invalid configuration handling."""
            with pytest.raises(ValueError):
                VideoConfig(width=-640)

            with pytest.raises(ValueError):
                VideoConfig(height=0)

            with pytest.raises(ValueError):
                VideoConfig(fps=-30.0)

            with pytest.raises(ValueError):
                VideoConfig(duration=-1.0)

        def test_generation_errors(self, temp_media_dir):
            """Test handling of generation errors."""
            config = VideoConfig()
            generator = VideoGenerator(config)

            with pytest.raises(VideoGenerationError):
                generator.generate(Path("/nonexistent/directory/test.mp4"))

            # Test invalid output format
            with pytest.raises(VideoGenerationError):
                generator.generate(temp_media_dir / "test.invalid")

    class TestPerformance:
        """Test performance aspects."""

        def test_long_duration(self, temp_media_dir):
            """Test generating longer videos."""
            config = VideoConfig(
                pattern=VideoPattern.COLOR_BARS,
                duration=5.0,  # 5 seconds
            )
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / "long.mp4")

            probe = ffmpeg.probe(str(output_file))
            assert float(probe["format"]["duration"]) == pytest.approx(5.0, rel=1e-1)

        def test_high_resolution(self, temp_media_dir):
            """Test generating high resolution video."""
            config = VideoConfig(
                pattern=VideoPattern.COLOR_BARS,
                width=3840,
                height=2160,  # 4K
                duration=1.0,
            )
            generator = VideoGenerator(config)
            output_file = generator.generate(temp_media_dir / "4k.mp4")

            probe = ffmpeg.probe(str(output_file))
            video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
            assert int(video_info["width"]) == 3840
            assert int(video_info["height"]) == 2160
