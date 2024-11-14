import numpy as np
import pytest
from reelpy.core.utils import (
    calculate_frame_difference,
    detect_black_frames,
    detect_scene_change,
    extract_frame_features,
    find_similar_frames
)

@pytest.fixture
def sample_frames():
    """Create sample frames for testing."""
    height, width = 240, 320
    
    # Create a black frame
    black_frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Create a white frame
    white_frame = np.full((height, width, 3), 255, dtype=np.uint8)
    
    # Create a gradient frame
    x = np.linspace(0, 255, width, dtype=np.uint8)
    gradient = np.tile(x, (height, 1))
    gradient_frame = np.stack([gradient] * 3, axis=-1)
    
    return black_frame, white_frame, gradient_frame

class TestFrameUtils:
    def test_frame_difference(self, sample_frames):
        """Test frame difference calculation methods."""
        black_frame, white_frame, gradient_frame = sample_frames
        
        # Test MSE - (255^2 = 65025) for black vs white
        mse = calculate_frame_difference(black_frame, white_frame, method="mse")
        assert mse == pytest.approx(65025.0, rel=1e-3)
        
        # Test MAE
        mae = calculate_frame_difference(black_frame, white_frame, method="mae")
        assert mae == pytest.approx(255.0, rel=1e-3)
        
        # Test SSIM
        ssim = calculate_frame_difference(black_frame, white_frame, method="ssim")
        assert 0 <= ssim <= 1
        
        # Test frame shape mismatch
        wrong_shape = np.zeros((100, 100, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="Frame shapes don't match"):
            calculate_frame_difference(black_frame, wrong_shape)
    
    def test_black_frame_detection(self, sample_frames):
        """Test black frame detection."""
        black_frame, white_frame, gradient_frame = sample_frames
        
        assert detect_black_frames(black_frame, threshold=10.0)
        assert not detect_black_frames(white_frame, threshold=10.0)
        assert not detect_black_frames(gradient_frame, threshold=10.0)
    
    def test_scene_change_detection(self, sample_frames):
        """Test scene change detection."""
        black_frame, white_frame, gradient_frame = sample_frames
        
        # Clear scene change
        assert detect_scene_change(black_frame, white_frame, threshold=0.3)
        
        # No scene change
        assert not detect_scene_change(black_frame, black_frame, threshold=0.3)
        
        # Test different methods
        assert detect_scene_change(black_frame, white_frame, threshold=0.3, method="mae")
        assert detect_scene_change(black_frame, white_frame, threshold=0.3, method="ssim")
    
    def test_feature_extraction(self, sample_frames):
        """Test frame feature extraction."""
        black_frame, white_frame, gradient_frame = sample_frames
        
        # Test histogram features
        hist_features = extract_frame_features(black_frame, method="histogram")
        assert isinstance(hist_features, np.ndarray)
        assert hist_features.shape == (256 * 3,)  # RGB histogram
        
        # Test average color features
        avg_features = extract_frame_features(black_frame, method="average_color")
        assert isinstance(avg_features, np.ndarray)
        assert avg_features.shape == (3,)  # RGB averages
        
        # Test invalid method
        with pytest.raises(ValueError):
            extract_frame_features(black_frame, method="invalid")
    
    def test_similar_frames_finding(self, sample_frames):
        """Test similar frame finding."""
        black_frame, white_frame, gradient_frame = sample_frames
        
        # Create an iterator of frames with timestamps
        frames = [
            (0.0, black_frame),
            (1.0, black_frame.copy()),  # Similar to black_frame
            (2.0, white_frame),  # Different
            (3.0, gradient_frame)  # Different
        ]
        
        similar = list(find_similar_frames(
            black_frame,
            iter(frames),
            threshold=0.1,
            method="mse"
        ))
        
        assert len(similar) == 2  # Should find original and copy
        for timestamp, frame, score in similar:
            assert score <= 0.1