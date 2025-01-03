# tests/integration/test_audio_pipeline.py
import pytest
from pathlib import Path
import soundfile as sf

from quackvideo.core.operations.audio import (
    AudioProcessor,
    AudioConfig,
    AudioOperationType
)
from quackvideo.synthetic.audio import (
    AudioGenerator,
    AudioPattern,
    AudioConfig as SyntheticAudioConfig
)

class TestAudioPipeline:
    """Integration tests for complete audio processing workflows."""

    class TestExtractionPipeline:
        """Test video to audio extraction workflow."""
        
        def test_video_to_audio_pipeline(self, test_video, temp_media_dir):
            """Test complete video to audio extraction and processing pipeline."""
            # Step 1: Extract audio from video
            config = AudioConfig(format="flac")
            processor = AudioProcessor(config, temp_media_dir)
            extract_result = processor.extract_audio(test_video)
            
            assert extract_result.operation_type == AudioOperationType.EXTRACT
            assert extract_result.format == "flac"
            
            # Step 2: Convert to different format
            wav_config = AudioConfig(format="wav")
            wav_processor = AudioProcessor(wav_config, temp_media_dir)
            convert_result = wav_processor.convert_audio(extract_result.output_path)
            
            assert convert_result.operation_type == AudioOperationType.CONVERT
            assert convert_result.format == "wav"
            
            # Verify audio properties are preserved
            assert convert_result.duration == pytest.approx(extract_result.duration, rel=1e-1)
            assert convert_result.channels == extract_result.channels

    class TestMixingPipeline:
        """Test audio mixing workflow with synthetic sources."""
        
        def test_synthetic_mixing_pipeline(self, temp_media_dir):
            """Test mixing pipeline with synthetic audio sources."""
            # Step 1: Generate two different synthetic audio files
            configs = [
                SyntheticAudioConfig(
                    pattern=AudioPattern.SINE,
                    frequency=440.0,  # A4 note
                    duration=2.0
                ),
                SyntheticAudioConfig(
                    pattern=AudioPattern.SINE,
                    frequency=880.0,  # A5 note
                    duration=2.0
                )
            ]
            
            audio_files = []
            for i, config in enumerate(configs):
                generator = AudioGenerator(config)
                audio_files.append(
                    generator.generate(temp_media_dir / f"synthetic_{i}.flac")
                )
            
            # Step 2: Mix the audio files
            mix_config = AudioConfig(
                format="flac",
                mixing_volumes=[0.5, 0.5]
            )
            processor = AudioProcessor(mix_config, temp_media_dir)
            mix_result = processor.mix_audio(audio_files[0], audio_files[1])
            
            assert mix_result.operation_type == AudioOperationType.MIX
            assert mix_result.channels == 2
            
            # Verify mixed audio properties
            data, sr = sf.read(mix_result.output_path)
            assert sr == 44100  # Default sample rate
            assert len(data) == int(2.0 * sr)  # 2-second duration

    class TestComplexPipeline:
        """Test complex audio processing pipeline."""
        
        def test_multi_stage_processing(self, test_video, temp_media_dir):
            """Test multi-stage audio processing pipeline."""
            # Step 1: Extract audio from video
            extract_config = AudioConfig(format="flac")
            extractor = AudioProcessor(extract_config, temp_media_dir)
            video_audio = extractor.extract_audio(test_video)
            
            # Step 2: Generate synthetic audio
            synthetic_config = SyntheticAudioConfig(
                pattern=AudioPattern.WHITE_NOISE,
                duration=video_audio.duration
            )
            generator = AudioGenerator(synthetic_config)
            synthetic_audio = generator.generate(temp_media_dir / "noise.flac")
            
            # Step 3: Mix video audio with synthetic
            mix_config = AudioConfig(
                format="flac",
                mixing_volumes=[0.8, 0.2]  # 80% original, 20% noise
            )
            mixer = AudioProcessor(mix_config, temp_media_dir)
            mixed = mixer.mix_audio(video_audio.output_path, synthetic_audio)
            
            # Step 4: Convert final result to different format
            final_config = AudioConfig(format="wav")
            converter = AudioProcessor(final_config, temp_media_dir)
            final_result = converter.convert_audio(mixed.output_path)
            
            # Verify final output
            assert final_result.output_path.exists()
            assert final_result.format == "wav"
            assert final_result.duration == pytest.approx(video_audio.duration, rel=1e-1)

    class TestErrorRecovery:
        """Test error recovery in complex pipelines."""
        
        def test_pipeline_error_recovery(self, test_video, temp_media_dir):
            """Test recovery from errors in multi-stage pipeline."""
            # Step 1: Start with valid extraction
            config = AudioConfig(format="flac")
            processor = AudioProcessor(config, temp_media_dir)
            result1 = processor.extract_audio(test_video)
            
            # Step 2: Simulate failure in mixing
            with pytest.raises(Exception):
                processor.mix_audio(
                    result1.output_path,
                    Path("nonexistent.flac")
                )
            
            # Step 3: Verify we can continue processing
            convert_config = AudioConfig(format="wav")
            converter = AudioProcessor(convert_config, temp_media_dir)
            result2 = converter.convert_audio(result1.output_path)
            
            assert result2.output_path.exists()

    class TestResourceManagement:
        """Test resource management in complex pipelines."""
        
        def test_resource_cleanup(self, test_video, temp_media_dir):
            """Test proper resource cleanup in multi-stage pipeline."""
            processors = []
            results = []
            
            try:
                # Step 1: Extract audio
                extract_config = AudioConfig(format="flac")
                processor1 = AudioProcessor(extract_config, temp_media_dir)
                processors.append(processor1)
                results.append(processor1.extract_audio(test_video))
                
                # Step 2: Convert format
                convert_config = AudioConfig(format="wav")
                processor2 = AudioProcessor(convert_config, temp_media_dir)
                processors.append(processor2)
                results.append(processor2.convert_audio(results[0].output_path))
                
            finally:
                # Clean up processors
                for processor in processors:
                    processor.cleanup()
                
                # Verify output files still exist
                for result in results:
                    assert result.output_path.exists()