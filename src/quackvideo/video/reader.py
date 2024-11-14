# src/quackvideo/video/reader.py
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, field_validator

from reelpy.core.ffmpeg import FFmpegWrapper
from reelpy.core.utils import detect_scene_change  # Make sure this is implemented in utils.py

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class VideoMetadata:
    """Video metadata information."""
    duration: float
    fps: float
    width: int
    height: int
    bitrate: int
    codec: str
    size_bytes: int

class VideoReaderConfig(BaseModel):
    """Configuration for VideoReader."""
    fps: Optional[float] = Field(default=None)
    start_time: Optional[float] = Field(default=None)
    end_time: Optional[float] = Field(default=None)
    resolution: Optional[tuple[int, int]] = Field(default=None)
    skip_validation: bool = Field(default=False)
    force_fps: bool = Field(default=False)
    
    @field_validator("fps")
    def validate_fps(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("FPS must be positive")
        return v
    
    @field_validator("start_time")
    def validate_start_time(cls, v: Optional[float], info) -> Optional[float]:
        if v is None or info.data.get("skip_validation", False):
            return v
        return max(0.0, v) if v is not None else v
    
    @field_validator("end_time")
    def validate_end_time(cls, v: Optional[float], info) -> Optional[float]:
        if v is None or info.data.get("skip_validation", False):
            return v
        start_time = info.data.get("start_time", 0.0) or 0.0
        if v is not None and v <= start_time:
            raise ValueError("end_time must be greater than start_time")
        return v
    
    @field_validator("resolution")
    def validate_resolution(cls, v: Optional[tuple[int, int]]) -> Optional[tuple[int, int]]:
        if v is not None and (v[0] <= 0 or v[1] <= 0):
            raise ValueError("Resolution dimensions must be positive")
        return v

class VideoReader:
    def __init__(
        self,
        video_path: str | Path,
        config: Optional[VideoReaderConfig] = None,
        *,
        skip_validation: bool = False
    ) -> None:
        self.video_path = Path(video_path)
        self.config = config or VideoReaderConfig(skip_validation=skip_validation)
        
        if not skip_validation and not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        
        self._metadata = self._load_metadata()
    
    @property
    def metadata(self) -> VideoMetadata:
        """Get video metadata."""
        return self._metadata
    
    @property
    def duration(self) -> float:
        """Get video duration in seconds."""
        return self._metadata.duration
    
    @property
    def fps(self) -> float:
        """Get video FPS."""
        return self._metadata.fps

    def extract_frames_range(
        self,
        start_time: float,
        end_time: float,
        *,
        frame_count: Optional[int] = None
    ) -> Iterator[Tuple[float, np.ndarray]]:
        """Extract frames within a specific time range."""
        if end_time <= start_time:
            raise ValueError("end_time must be greater than start_time")
        
        if frame_count is not None:
            # Use numpy to generate exact timestamps
            timestamps = np.linspace(start_time, end_time, frame_count)
            for ts in timestamps:
                yield float(ts), self.extract_frame_at(ts)
        else:
            # Use FFmpeg's native frame extraction
            temp_config = VideoReaderConfig(
                start_time=start_time,
                end_time=end_time,
                resolution=self.config.resolution,
                skip_validation=True
            )
            
            reader = VideoReader(self.video_path, temp_config, skip_validation=True)
            frame_duration = 1.0 / self.fps
            current_time = start_time
            
            for frame in reader.read_frames():
                yield current_time, frame
                current_time += frame_duration
    
    def _load_metadata(self) -> VideoMetadata:
        """Load video metadata using FFprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-show_entries", "format=duration,bit_rate,size",
            "-of", "json",
            str(self.video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            if not data.get("streams"):
                raise ValueError("No streams found in video")
            if not data.get("format"):
                raise ValueError("No format information found in video")
            
            stream = data["streams"][0]
            fmt = data["format"]
            
            if not all(key in stream for key in ["width", "height", "r_frame_rate", "codec_name"]):
                raise ValueError("Missing required stream metadata")
            
            fps_num, fps_den = map(int, stream["r_frame_rate"].split("/"))
            fps = fps_num / fps_den
            
            return VideoMetadata(
                duration=float(fmt["duration"]),
                fps=fps,
                width=stream["width"],
                height=stream["height"],
                bitrate=int(fmt.get("bit_rate", 0)),
                codec=stream["codec_name"],
                size_bytes=int(fmt["size"])
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to load video metadata: {e}")
        except (KeyError, ValueError, IndexError) as e:
            raise RuntimeError(f"Invalid video metadata format: {e}")
    
    def read_frames(self) -> Iterator[np.ndarray]:
        """Read video frames according to the configuration."""
        return FFmpegWrapper.extract_frames(
            video_path=self.video_path,
            fps=self.config.fps,
            start_time=self.config.start_time,
            end_time=self.config.end_time,
            resolution=self.config.resolution,
            skip_validation=self.config.skip_validation
        )

    def extract_keyframes(self) -> Iterator[Tuple[float, np.ndarray]]:
        """Extract keyframes from the video."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "frame=pkt_pts_time,flags",
            "-of", "json",
            str(self.video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            if "frames" not in data:
                data = {"frames": [{"pkt_pts_time": "0.0", "flags": "K"}]}  # Default frame if none found
                
            keyframe_times = []
            for frame in data["frames"]:
                if "K" in frame.get("flags", "") and "pkt_pts_time" in frame:
                    try:
                        timestamp = float(frame["pkt_pts_time"])
                        keyframe_times.append(timestamp)
                    except (ValueError, TypeError):
                        continue
            
            for timestamp in keyframe_times:
                frame = self.extract_frame_at(timestamp)
                yield timestamp, frame
                
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to extract keyframes: {e}")


    def extract_scene_changes(
        self,
        threshold: float = 0.3
    ) -> Iterator[tuple[float, np.ndarray]]:
        """Extract frames at scene changes."""
        # Use FFmpeg's scene detection filter
        temp_config = VideoReaderConfig(
            fps=self.config.fps,
            start_time=self.config.start_time,
            end_time=self.config.end_time,
            resolution=self.config.resolution,
            skip_validation=True,
            force_fps=True  # Now this will work with updated model
        )

        reader = VideoReader(self.video_path, temp_config, skip_validation=True)
        
        # Ensure force_fps is set in config
        reader.config.force_fps = True

        frames = list(reader.read_frames())

        if not frames:
            return

        scene_changes = []
        prev_frame = frames[0]
        for i, frame in enumerate(frames[1:]):  # Start from the second frame
            if detect_scene_change(prev_frame, frame, threshold=threshold):
                # Calculate timestamp based on frame index and FPS
                timestamp = (i + 1) / reader.fps
                scene_changes.append((timestamp, frame))
            prev_frame = frame

        yield from scene_changes
    
    def extract_frame_sequence(
        self,
        timestamp: float,
        frame_count: int,
        direction: str = "both"
    ) -> Iterator[tuple[float, np.ndarray]]:
        """
        Extract a sequence of frames around a timestamp.
        
        Args:
            timestamp: Center timestamp in seconds
            frame_count: Number of frames to extract
            direction: One of "both", "forward", or "backward"
            
        Yields:
            Tuple of (timestamp, frame)
        """
        if direction not in {"both", "forward", "backward"}:
            raise ValueError('direction must be one of "both", "forward", or "backward"')
        
        frame_duration = 1.0 / self.fps
        
        if direction == "both":
            half_count = frame_count // 2
            start_time = timestamp - (half_count * frame_duration)
            frame_count = frame_count
        elif direction == "forward":
            start_time = timestamp
        else:  # backward
            # Ensure non-negative start time (important for backward sequences)
            start_time = max(0, start_time)
        
        # Use exact frame count to ensure precise timing
        end_time = start_time + (frame_count * frame_duration)
        yield from self.extract_frames_range(
            float(start_time), 
            float(end_time),
            frame_count=frame_count
        )
    
    @property
    def width(self) -> int:
        """Original video width."""
        return self._width
    
    @property
    def height(self) -> int:
        """Original video height."""
        return self._height
    
    @property
    def resolution(self) -> tuple[int, int]:
        """Current output resolution (width, height)."""
        if self.config.resolution:
            return self.config.resolution
        return (self._width, self._height)
    
    def read_frames(self) -> Iterator[np.ndarray]:
        """
        Read video frames according to the configuration.
        
        Yields:
            Iterator of numpy arrays containing the video frames
        """
        return FFmpegWrapper.extract_frames(
            video_path=self.video_path,
            fps=self.config.fps,
            start_time=self.config.start_time,
            end_time=self.config.end_time,
            resolution=self.config.resolution
        )
    
    def extract_frame_at(
        self,
        timestamp: float,
        *,
        _reuse_reader: bool = False
    ) -> np.ndarray:
        """Extract a single frame at the specified timestamp."""
        if timestamp < 0:
            raise ValueError("Timestamp must be non-negative")
        
        if not _reuse_reader:
            # Calculate window ensuring non-negative times
            start_time = max(0, timestamp - 0.1)
            end_time = timestamp + 0.1
            
            temp_config = VideoReaderConfig(
                fps=25,  # Higher FPS for accurate frame selection
                start_time=start_time,
                end_time=end_time,
                resolution=self.config.resolution,
                skip_validation=True
            )
            
            reader = VideoReader(
                self.video_path, 
                temp_config, 
                skip_validation=True
            )
            frames = list(reader.read_frames())
        else:
            frames = list(self.read_frames())
        
        if not frames:
            raise RuntimeError(f"Failed to extract frame at timestamp {timestamp}")
        
        # Return the frame closest to the desired timestamp
        return frames[len(frames) // 2]