# tests/operations/test_audio.py

import pytest
import os

from quackvideo.core.operations.audio import extract_audio, mix_audio, convert_audio
from quackvideo.core.utils import calculate_md5, get_media_metadata


def test_extract_audio(temp_output_dir, small_synth_video):
    """
    Extract audio from a synthetic video. Check that output is created and non-empty.
    """
    out_path = temp_output_dir / "extracted.wav"
    extract_audio(input_video=small_synth_video, output_audio=str(out_path))
    assert out_path.exists()
    assert os.path.getsize(out_path) > 0
    meta = get_media_metadata(str(out_path))
    assert meta["duration"] > 0, "Extracted audio should have a positive duration."


def test_mix_audio(temp_output_dir, small_synth_audio):
    """
    Mix two synthetic audio files into one. Verifies that output is created.
    """
    out_path = temp_output_dir / "mixed.wav"
    mix_audio(
        audio_paths=[small_synth_audio, small_synth_audio], output_audio=str(out_path)
    )
    assert out_path.exists()
    assert os.path.getsize(out_path) > 0
    meta = get_media_metadata(str(out_path))
    assert meta["duration"] > 0, "Mixed audio should have a positive duration."


def test_convert_audio(temp_output_dir, small_synth_audio):
    """
    Convert audio from WAV to MP3. Check MD5 or basic metadata for validity.
    """
    out_path = temp_output_dir / "converted.mp3"
    convert_audio(
        input_audio=small_synth_audio, output_audio=str(out_path), codec="libmp3lame"
    )
    assert out_path.exists(), "Converted MP3 file should exist."
    assert os.path.getsize(out_path) > 0
    md5_hash = calculate_md5(str(out_path))
    assert len(md5_hash) == 32, "MD5 hash should be 32 characters long."
