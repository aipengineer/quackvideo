from __future__ import annotations

from pathlib import Path
from typing import Optional

import fire

from quackvideo.synthetic.video import VideoPattern, VideoConfig, VideoGenerator
from quackvideo.synthetic.audio import AudioPattern, AudioConfig, AudioGenerator


def generate_video(
    output_path: str,
    pattern: str = "color_bars",
    duration: float = 10.0,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    bitrate: str = "2M",
) -> None:
    """
    Generate synthetic video pattern.
    
    Args:
        output_path: Path to save the video
        pattern: Pattern type (color_bars, gradient, checkerboard, moving_box, pulse)
        duration: Duration in seconds
        width: Frame width
        height: Frame height
        fps: Frames per second
        bitrate: Output video bitrate
    """
    try:
        pattern = VideoPattern(pattern)
    except ValueError:
        print(f"Invalid pattern. Available patterns: {[p.value for p in VideoPattern]}")
        return

    config = VideoConfig(
        pattern=pattern,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        bitrate=bitrate,
    )

    generator = VideoGenerator(config)
    output_file = generator.generate(Path(output_path))
    print(f"Generated video saved to: {output_file}")


def generate_audio(
    output_path: str,
    pattern: str = "sine",
    duration: float = 10.0,
    frequency: float = 440.0,
    sample_rate: int = 44100,
    channels: int = 2,
    amplitude: float = 0.5,
    format: str = "flac",
) -> None:
    """
    Generate synthetic audio pattern.
    
    Args:
        output_path: Path to save the audio
        pattern: Pattern type (sine, white_noise, frequency_sweep, chirp, pure_tone, multi_tone)
        duration: Duration in seconds
        frequency: Base frequency in Hz
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        amplitude: Signal amplitude (0-1)
        format: Output audio format
    """
    try:
        pattern = AudioPattern(pattern)
    except ValueError:
        print(f"Invalid pattern. Available patterns: {[p.value for p in AudioPattern]}")
        return

    config = AudioConfig(
        pattern=pattern,
        duration=duration,
        frequency=frequency,
        sample_rate=sample_rate,
        channels=channels,
        amplitude=amplitude,
        format=format,
    )

    generator = AudioGenerator(config)
    output_file = generator.generate(Path(output_path))
    print(f"Generated audio saved to: {output_file}")


def main() -> None:
    """Main entry point for synthetic media generation."""
    fire.Fire({
        "video": generate_video,
        "audio": generate_audio,
    })


if __name__ == "__main__":
    main()