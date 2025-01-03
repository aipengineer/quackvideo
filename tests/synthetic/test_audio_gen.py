# tests/synthetic/test_audio_gen.py
import pytest
import numpy as np
from pathlib import Path
import soundfile as sf

from quackvideo.synthetic.audio import (
    AudioGenerator,
    AudioConfig,
    AudioPattern,
    AudioGenerationError
)

class TestAudioGenerator:
    """Test suite for synthetic audio generation."""

    def test_initialization(self):
        """Test AudioGenerator initialization."""
        config = AudioConfig()
        generator = AudioGenerator(config)
        assert generator.config == config

    class TestBasicPatterns:
        """Test basic audio pattern generation."""

        @pytest.mark.parametrize("pattern", [
            AudioPattern.SINE,
            AudioPattern.WHITE_NOISE,
            AudioPattern.PURE_TONE,
            AudioPattern.MULTI_TONE,
            AudioPattern.FREQUENCY_SWEEP,
            AudioPattern.CHIRP
        ])
        def test_pattern_generation(self, pattern, temp_media_dir):
            """Test generation of all basic patterns."""
            config = AudioConfig(
                pattern=pattern,
                duration=1.0,
                sample_rate=44100,
                channels=2
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / f"{pattern.value}.flac")
            
            # Verify file exists and has correct properties
            assert output_file.exists()
            data, sample_rate = sf.read(output_file)
            
            assert sample_rate == 44100
            assert len(data.shape) == 2 if config.channels == 2 else 1
            assert data.shape[0] == int(config.duration * sample_rate)

        def test_sine_wave_properties(self, temp_media_dir):
            """Test specific properties of sine wave generation."""
            config = AudioConfig(
                pattern=AudioPattern.SINE,
                frequency=440.0,  # A4 note
                amplitude=0.5,
                duration=1.0
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / "sine.flac")
            
            data, _ = sf.read(output_file)
            
            # Verify amplitude
            assert np.max(np.abs(data)) == pytest.approx(0.5, rel=1e-2)
            
            # Verify frequency using FFT
            if len(data.shape) == 2:
                data = data.mean(axis=1)  # Convert to mono for frequency analysis
            
            fft = np.fft.fft(data)
            freqs = np.fft.fftfreq(len(data), 1/44100)
            peak_freq = abs(freqs[np.argmax(np.abs(fft))])
            assert peak_freq == pytest.approx(440.0, rel=1e-1)

    class TestAdvancedPatterns:
        """Test advanced audio pattern generation."""

        def test_frequency_sweep(self, temp_media_dir):
            """Test frequency sweep generation."""
            config = AudioConfig(
                pattern=AudioPattern.FREQUENCY_SWEEP,
                start_frequency=20.0,
                end_frequency=20000.0,
                duration=5.0
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / "sweep.flac")
            
            data, _ = sf.read(output_file)
            
            # Basic validation only - detailed frequency analysis would be complex
            assert output_file.exists()
            assert len(data) == int(5.0 * 44100)

        def test_multi_tone(self, temp_media_dir):
            """Test multi-tone generation."""
            frequencies = [440.0, 880.0, 1320.0]  # A4, A5, E6
            config = AudioConfig(
                pattern=AudioPattern.MULTI_TONE,
                frequencies=frequencies,
                duration=1.0
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / "multi_tone.flac")
            
            data, _ = sf.read(output_file)
            
            # Convert to mono if stereo
            if len(data.shape) == 2:
                data = data.mean(axis=1)
            
            # Verify presence of frequencies using FFT
            fft = np.fft.fft(data)
            freqs = np.fft.fftfreq(len(data), 1/44100)
            magnitude = np.abs(fft)
            
            for freq in frequencies:
                # Find peak near expected frequency
                freq_range = (freqs >= freq-10) & (freqs <= freq+10)
                assert np.any(magnitude[freq_range] > magnitude.mean())

    class TestConfiguration:
        """Test configuration handling."""

        @pytest.mark.parametrize("sample_rate", [8000, 44100, 48000, 96000])
        def test_sample_rates(self, sample_rate, temp_media_dir):
            """Test different sample rates."""
            config = AudioConfig(
                pattern=AudioPattern.SINE,
                sample_rate=sample_rate
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / "test.flac")
            
            _, sr = sf.read(output_file)
            assert sr == sample_rate

        @pytest.mark.parametrize("channels", [1, 2])
        def test_channel_configurations(self, channels, temp_media_dir):
            """Test mono and stereo output."""
            config = AudioConfig(
                pattern=AudioPattern.SINE,
                channels=channels
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / "test.flac")
            
            data, _ = sf.read(output_file)
            if channels == 1:
                assert len(data.shape) == 1 or data.shape[1] == 1
            else:
                assert data.shape[1] == 2

    class TestErrorHandling:
        """Test error handling."""

        def test_invalid_configuration(self):
            """Test invalid configuration handling."""
            with pytest.raises(ValueError):
                AudioConfig(frequency=-440.0)
            
            with pytest.raises(ValueError):
                AudioConfig(duration=-1.0)
            
            with pytest.raises(ValueError):
                AudioConfig(amplitude=1.5)

        def test_generation_errors(self, temp_media_dir):
            """Test handling of generation errors."""
            config = AudioConfig(pattern=AudioPattern.SINE)
            generator = AudioGenerator(config)
            
            # Test invalid output path
            with pytest.raises(AudioGenerationError):
                generator.generate(Path("/nonexistent/directory/test.flac"))
            
            # Test invalid file format
            with pytest.raises(AudioGenerationError):
                generator.generate(temp_media_dir / "test.invalid")

    class TestPerformance:
        """Test performance aspects."""

        def test_long_duration(self, temp_media_dir):
            """Test generating longer audio files."""
            config = AudioConfig(
                pattern=AudioPattern.SINE,
                duration=10.0  # 10 seconds
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / "long.flac")
            
            data, _ = sf.read(output_file)
            assert len(data) == int(10.0 * 44100)

        def test_high_sample_rate(self, temp_media_dir):
            """Test generating audio with high sample rate."""
            config = AudioConfig(
                pattern=AudioPattern.SINE,
                sample_rate=96000,
                duration=1.0
            )
            generator = AudioGenerator(config)
            output_file = generator.generate(temp_media_dir / "highsr.flac")
            
            _, sr = sf.read(output_file)
            assert sr == 96000