# tests/core/test_utils.py

import pytest
import os

from quackvideo.core.utils import calculate_md5, get_media_metadata


def test_calculate_md5(temp_output_dir):
    """
    Test MD5 calculation on a simple text file.
    """
    test_file = temp_output_dir / "dummy.txt"
    test_file.write_text("Hello world!")

    md5_hash = calculate_md5(str(test_file))
    # MD5 of "Hello world!" (no newline) is 3e25960a79dbc69b674cd4ec67a72c62
    assert md5_hash == "3e25960a79dbc69b674cd4ec67a72c62"


def test_get_media_metadata_video(small_synth_video):
    """
    Check that metadata for a synthetic video is properly retrieved.
    """
    meta = get_media_metadata(small_synth_video)
    assert meta["duration"] == pytest.approx(3, 0.5), "Duration should be ~3s"
    assert meta["width"] == 320
    assert meta["height"] == 240


def test_get_media_metadata_non_existent():
    """
    Ensure an invalid file triggers an exception or error for metadata retrieval.
    """
    with pytest.raises(FileNotFoundError):
        get_media_metadata("this_file_does_not_exist.mp4")
