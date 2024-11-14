# src/reelpy/video/writer.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

import numpy as np
from pydantic import BaseModel, Field, field_validator

class VideoWriterConfig(BaseModel):
    """Configuration for VideoWriter."""
    fps: float = Field(
        default=30.0,
        description="Frames per second for the output video"
    )
    codec: str = Field(
        default="libx264",
        description="Video codec to use"
    )
    crf: int = Field(
        default=23,
        description="Constant Rate Factor (0-51, lower means better quality)"
    )
    preset: str = Field(
        default="medium",
        description="Encoding preset (affects encoding speed vs compression ratio)"
    )
    pixel_format: str = Field(
        default="yuv420p",
        description="Output pixel format"
    )
    
    @field_validator("fps")
    def validate_fps(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("FPS must be positive")
        return v
    
    @field_validator("crf")
    def validate_crf(cls, v: int) -> int:
        if not 0 <= v <= 51:
            raise ValueError("CRF must be between 0 and 51")
        return v
    
    @field_validator("preset")
    def validate_preset(cls, v: str) -> str:
        valid_presets = {
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow"
        }
        if v not in valid_presets:
            raise ValueError(f"Invalid preset. Must be one of: {valid_presets}")
        return v

class VideoWriter:
    """High-level interface for writing video frames."""
    
    def __init__(
        self,
        output_path: str | Path,
        config: Optional[VideoWriterConfig] = None
    ) -> None:
        """
        Initialize VideoWriter.
        
        Args:
            output_path: Path where the video will be saved
            config: Configuration for video writing (optional)
        """
        self.output_path = Path(output_path)
        self.config = config or VideoWriterConfig()
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def write_frames(self, frames: Sequence[np.ndarray]) -> None:
        """
        Write frames to a video file.
        
        Args:
            frames: Sequence of numpy arrays containing the video frames
            
        Raises:
            ValueError: If frames are empty or have inconsistent dimensions
            RuntimeError: If FFmpeg fails to write the video
        """
        if not frames:
            raise ValueError("No frames to write")
        
        # Check frame dimensions
        first_frame = frames[0]
        height, width = first_frame.shape[:2]
        
        cmd = [
            "ffmpeg", "-y",  # Overwrite output file
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.config.fps),
            "-i", "-",  # Read from pipe
            "-c:v", self.config.codec,
            "-preset", self.config.preset,
            "-crf", str(self.config.crf),
            "-pix_fmt", self.config.pixel_format,
            str(self.output_path)
        ]
        
        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        
        try:
            # Write frames
            for frame in frames:
                if frame.shape[:2] != (height, width):
                    raise ValueError(
                        f"Inconsistent frame dimensions. Expected {(height, width)}, "
                        f"got {frame.shape[:2]}"
                    )
                
                process.stdin.write(frame.tobytes())
            
            # Close input pipe and wait for FFmpeg
            process.stdin.close()
            process.wait()
            
            if process.returncode != 0:
                error_message = process.stderr.read().decode()
                raise RuntimeError(f"Error writing video: {error_message}")
                
        finally:
            process.stdin.close()
            process.stderr.close()
            if process.poll() is None:
                process.terminate()