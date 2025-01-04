# tests/synthetic/test_video_gen.py

import pytest
from quackvideo.synthetic.video import SyntheticVideoGenerator
from quackvideo.core.utils import get_media_metadata


def test_synthetic_video_generator_basic():
    """
    Test generation of a short synthetic video, verifying metadata.
    """
    gen = SyntheticVideoGenerator(width=320, height=240, duration=2, fps=10)
    out_video = gen.generate()
    assert out_video is not None, "Should return a video file path."
    meta = get_media_metadata(out_video)
    assert meta["width"] == 320
    assert meta["height"] == 240
    assert meta["duration"] == pytest.approx(2, 0.5), "Duration should be ~2 seconds."
