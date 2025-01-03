from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import fire

from quackvideo.core.operations.audio import (
    AudioProcessor,
    AudioConfig,
    AudioOperationType,
)
from quackvideo.synthetic.audio import AudioGenerator, AudioPattern


def extract_audio(
    video_path: str,
    output_dir: str,
    format: str = "flac",
    compression_level: int = 8,
) -> None:
    """Extract audio from video."""
    config = AudioConfig(
        format=format,
        compression_level=compression_level,
    )

    processor = AudioProcessor(config, Path(output_dir))
    result = processor.extract_audio(Path(video_path))
    print(f"Extracted audio saved to: {result.output_path}")


def convert_audio(
    audio_path: str,
    output_dir: str,
    format: str = "flac",
    compression_level: int = 8,
) -> None:
    """Convert audio format."""
    config = AudioConfig(
        format=format,
        compression_level=compression_level,
    )

    processor = AudioProcessor(config, Path(output_dir))
    result = processor.convert_audio(Path(audio_path))
    print(f"Converted audio saved to: {result.output_path}")


def mix_audio(
    audio_path1: str,
    audio_path2: str,
    output_dir: str,
    volumes: List[float] = [0.10, 0.90],
    format: str = "flac",
) -> None:
    """Mix two audio files."""
    config = AudioConfig(
        format=format,
        mixing_volumes=volumes,
    )

    processor = AudioProcessor(config, Path(output_dir))
    result = processor.mix_audio(Path(audio_path1), Path(audio_path2), volumes=volumes)
    print(f"Mixed audio saved to: {result.output_path}")


def mix_with_synthetic(
    output_dir: str,
    pattern1: str = "sine",
    pattern2: str = "white_noise",
    volumes: List[float] = [0.10, 0.90],
) -> None:
    """Generate and mix synthetic audio."""
    output_dir = Path(output_dir)
    audio_path1 = output_dir / "synthetic1.flac"
    audio_path2 = output_dir / "synthetic2.flac"

    # Generate first audio
    gen1 = AudioGenerator(AudioConfig(pattern=AudioPattern(pattern1)))
    audio1 = gen1.generate(audio_path1)

    # Generate second audio
    gen2 = AudioGenerator(AudioConfig(pattern=AudioPattern(pattern2)))
    audio2 = gen2.generate(audio_path2)

    # Mix audio files
    mix_audio(str(audio1), str(audio2), str(output_dir), volumes=volumes)


def main() -> None:
    """Main entry point for audio operations."""
    fire.Fire(
        {
            "extract": extract_audio,
            "convert": convert_audio,
            "mix": mix_audio,
            "synthetic": mix_with_synthetic,
        }
    )


if __name__ == "__main__":
    main()
