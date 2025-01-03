from __future__ import annotations

from collections.abc import Iterator
from enum import Enum
from pathlib import Path

import ffmpeg
import numpy as np
from pydantic import Field

from .base import SyntheticConfig, SyntheticGenerator


class AudioPattern(str, Enum):
    """Available audio test patterns."""

    SINE = "sine"
    WHITE_NOISE = "white_noise"
    SWEEP = "frequency_sweep"
    CHIRP = "chirp"
    PURE_TONE = "pure_tone"
    MULTI_TONE = "multi_tone"


class AudioConfig(SyntheticConfig):
    """Configuration for synthetic audio generation."""

    pattern: AudioPattern = Field(
        AudioPattern.SINE, description="Type of audio pattern"
    )
    sample_rate: int = Field(44100, description="Sample rate in Hz")
    frequency: float = Field(440.0, description="Base frequency in Hz")
    amplitude: float = Field(0.5, description="Signal amplitude (0-1)")
    channels: int = Field(2, description="Number of audio channels")
    format: str = Field("flac", description="Output audio format")

    # Pattern-specific settings
    sweep_start: float = Field(20.0, description="Start frequency for sweep (Hz)")
    sweep_end: float = Field(20000.0, description="End frequency for sweep (Hz)")
    chirp_rate: float = Field(
        100.0, description="Rate of frequency change for chirp (Hz/s)"
    )
    frequencies: list[float] = Field(
        default=[440.0, 880.0], description="Frequencies for multi-tone pattern"
    )


class AudioGenerator(SyntheticGenerator):
    """Generator for synthetic audio patterns."""

    def __init__(self, config: AudioConfig) -> None:
        super().__init__(config)
        self.config = config  # Type hint for IDE

    def _generate_samples(self) -> Iterator[np.ndarray]:
        """Generate audio samples based on selected pattern."""
        total_samples = int(self.config.duration * self.config.sample_rate)

        if self.config.pattern == AudioPattern.SINE:
            yield from self._generate_sine(total_samples)
        elif self.config.pattern == AudioPattern.WHITE_NOISE:
            yield from self._generate_white_noise(total_samples)
        elif self.config.pattern == AudioPattern.SWEEP:
            yield from self._generate_sweep(total_samples)
        elif self.config.pattern == AudioPattern.CHIRP:
            yield from self._generate_chirp(total_samples)
        elif self.config.pattern == AudioPattern.PURE_TONE:
            yield from self._generate_pure_tone(total_samples)
        elif self.config.pattern == AudioPattern.MULTI_TONE:
            yield from self._generate_multi_tone(total_samples)

    def _apply_envelope(
        self, samples: np.ndarray, attack_time: float = 0.01, release_time: float = 0.01
    ) -> np.ndarray:
        """Apply attack and release envelope to avoid clicks."""
        attack_samples = int(attack_time * self.config.sample_rate)
        release_samples = int(release_time * self.config.sample_rate)

        attack = np.linspace(0, 1, attack_samples)
        release = np.linspace(1, 0, release_samples)

        samples[:attack_samples] *= attack[:, np.newaxis]
        samples[-release_samples:] *= release[:, np.newaxis]

        return samples

    def _generate_sine(self, total_samples: int) -> Iterator[np.ndarray]:
        """Generate sine wave."""
        t = np.linspace(0, self.config.duration, total_samples)
        signal = self.config.amplitude * np.sin(2 * np.pi * self.config.frequency * t)
        stereo_signal = np.column_stack([signal] * self.config.channels)

        # Process in chunks
        chunk_size = self.config.sample_rate  # 1 second chunks
        for i in range(0, total_samples, chunk_size):
            chunk = stereo_signal[i : i + chunk_size]
            yield chunk.astype(np.float32)

    def _generate_white_noise(self, total_samples: int) -> Iterator[np.ndarray]:
        """Generate white noise."""
        chunk_size = self.config.sample_rate

        for _ in range(0, total_samples, chunk_size):
            size = min(chunk_size, total_samples - _)
            noise = np.random.uniform(-1, 1, (size, self.config.channels))
            yield (noise * self.config.amplitude).astype(np.float32)

    def _generate_sweep(self, total_samples: int) -> Iterator[np.ndarray]:
        """Generate frequency sweep (linear)."""
        t = np.linspace(0, self.config.duration, total_samples)
        freq_range = self.config.sweep_end - self.config.sweep_start
        freq_t = self.config.sweep_start + (freq_range * t / self.config.duration)

        # Integrate frequency to get phase
        phase = 2 * np.pi * np.cumsum(freq_t) / self.config.sample_rate
        signal = self.config.amplitude * np.sin(phase)
        stereo_signal = np.column_stack([signal] * self.config.channels)

        chunk_size = self.config.sample_rate
        for i in range(0, total_samples, chunk_size):
            chunk = stereo_signal[i : i + chunk_size]
            yield chunk.astype(np.float32)

    def _generate_chirp(self, total_samples: int) -> Iterator[np.ndarray]:
        """Generate chirp signal (exponential frequency change)."""
        t = np.linspace(0, self.config.duration, total_samples)
        freq_t = self.config.frequency * np.exp(self.config.chirp_rate * t)
        phase = 2 * np.pi * np.cumsum(freq_t) / self.config.sample_rate
        signal = self.config.amplitude * np.sin(phase)
        stereo_signal = np.column_stack([signal] * self.config.channels)

        chunk_size = self.config.sample_rate
        for i in range(0, total_samples, chunk_size):
            chunk = stereo_signal[i : i + chunk_size]
            yield self._apply_envelope(chunk).astype(np.float32)

    def _generate_pure_tone(self, total_samples: int) -> Iterator[np.ndarray]:
        """Generate pure tone with precise frequency."""
        t = np.linspace(0, self.config.duration, total_samples)
        signal = self.config.amplitude * np.sin(2 * np.pi * self.config.frequency * t)
        stereo_signal = np.column_stack([signal] * self.config.channels)

        chunk_size = self.config.sample_rate
        for i in range(0, total_samples, chunk_size):
            chunk = stereo_signal[i : i + chunk_size]
            yield self._apply_envelope(chunk).astype(np.float32)

    def _generate_multi_tone(self, total_samples: int) -> Iterator[np.ndarray]:
        """Generate multiple simultaneous tones."""
        t = np.linspace(0, self.config.duration, total_samples)
        signal = np.zeros(total_samples)

        # Sum multiple frequencies
        for freq in self.config.frequencies:
            signal += np.sin(2 * np.pi * freq * t)

        # Normalize and apply amplitude
        signal = signal / len(self.config.frequencies)
        signal *= self.config.amplitude

        stereo_signal = np.column_stack([signal] * self.config.channels)

        chunk_size = self.config.sample_rate
        for i in range(0, total_samples, chunk_size):
            chunk = stereo_signal[i : i + chunk_size]
            yield self._apply_envelope(chunk).astype(np.float32)

    def generate(self, output_path: Path) -> Path:
        """Generate synthetic audio file."""
        output_path = Path(output_path)

        # Set up FFmpeg process
        process = (
            ffmpeg.input(
                "pipe:",
                format="f32le",  # 32-bit float PCM
                acodec="pcm_f32le",
                ac=self.config.channels,
                ar=str(self.config.sample_rate),
            )
            .output(
                str(output_path),
                acodec="flac" if self.config.format == "flac" else "pcm_s16le",
                compression_level=8 if self.config.format == "flac" else None,
            )
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )

        try:
            # Write audio samples
            for samples in self._generate_samples():
                process.stdin.write(samples.tobytes())

            # Close stdin pipe
            process.stdin.close()
            process.wait()

            return output_path

        except Exception:
            if process.poll() is None:
                process.kill()
            raise
