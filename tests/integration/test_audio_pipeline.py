# tests/integration/test_audio_pipeline.py

import pytest
from quackvideo.synthetic.video import SyntheticVideoGenerator
from quackvideo.core.operations.audio import extract_audio, convert_audio
from quackvideo.core.utils import calculate_md5


def test_audio_pipeline(temp_output_dir):
    """
    Integration test:
    1) Generate a short synthetic video.
    2) Extract audio from it.
    3) Convert extracted audio to MP3.
    4) Compare MD5 checksums (sanity check).
    """
    # 1) Generate a short synthetic video
    video_gen = SyntheticVideoGenerator(width=320, height=240, duration=2, fps=10)
    synth_vid = video_gen.generate()

    # 2) Extract audio
    out_wav = temp_output_dir / "extracted.wav"
    extract_audio(input_video=synth_vid, output_audio=str(out_wav))
    assert out_wav.exists()

    # 3) Convert to MP3
    out_mp3 = temp_output_dir / "converted.mp3"
    convert_audio(
        input_audio=str(out_wav), output_audio=str(out_mp3), codec="libmp3lame"
    )
    assert out_mp3.exists()

    # 4) MD5 comparison (they will differ because WAV != MP3)
    wav_md5 = calculate_md5(str(out_wav))
    mp3_md5 = calculate_md5(str(out_mp3))
    assert wav_md5 != mp3_md5, "MD5 should differ for files with different formats."
