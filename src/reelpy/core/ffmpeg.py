# src/reelpy/core/ffmpeg.py
from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional
from threading import Thread
from io import StringIO

import numpy as np

class FFmpegError(Exception):
    """Base exception for FFmpeg-related errors."""
    pass

class FFmpegTimeoutError(FFmpegError):
    """Raised when FFmpeg operation times out."""
    pass

def stream_reader(pipe, output_buffer, timeout=30):
    """Read from pipe and write to buffer with timeout."""
    def _read():
        try:
            for line in iter(pipe.readline, b''):
                try:
                    if isinstance(line, (bytes, bytearray)):
                        decoded_line = line.decode()
                    else:
                        decoded_line = str(line)
                    output_buffer.write(decoded_line)
                except (AttributeError, TypeError):
                    continue
        finally:
            pipe.close()

    thread = Thread(target=_read)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise FFmpegTimeoutError("FFmpeg operation timed out")

@dataclass
class FFmpegCommand:
    """Represents an FFmpeg command with its parameters."""
    input_path: Path
    output_path: Optional[Path] = None
    fps: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    resolution: Optional[tuple[int, int]] = None

    def build_command(self) -> list[str]:
        """Build the FFmpeg command with the specified parameters."""
        cmd = ["ffmpeg", "-i", str(self.input_path)]
        
        if self.start_time is not None:
            cmd.extend(["-ss", str(self.start_time)])
        
        if self.end_time is not None:
            duration = self.end_time - (self.start_time or 0)
            if duration > 0:
                cmd.extend(["-t", str(duration)])
        
        filters = [
            f"fps={self.fps}" if self.fps else None,
            f"scale={self.resolution[0]}:{self.resolution[1]}" if self.resolution else None
        ]
        filters = [f for f in filters if f is not None]
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        if self.output_path is not None:
            cmd.append(str(self.output_path))
        
        return cmd

class FFmpegWrapper:
    """High-level wrapper for FFmpeg operations."""
    
    TIMEOUT = 10  # Default timeout in seconds
    
    @staticmethod
    def get_video_info(video_path: Path, timeout: int = 10) -> tuple[int, int]:
        """Get video width and height."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            str(video_path)
        ]
        try:
            result = subprocess.check_output(cmd, text=True, timeout=timeout)
            data = json.loads(result)
            if not data.get("streams"):
                raise RuntimeError("Failed to get video info: No streams found")
            
            stream = data["streams"][0]
            width = stream["width"]
            height = stream["height"]
            
            return width, height
        except subprocess.TimeoutExpired:
            raise FFmpegTimeoutError("FFprobe operation timed out")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get video info: {e.stderr if e.stderr else str(e)}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid video info format: {str(e)}")

    @classmethod
    def extract_frames(
        cls,
        video_path: str | Path,
        fps: Optional[float] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        resolution: Optional[tuple[int, int]] = None,
        *,
        skip_validation: bool = False,
        timeout: int = 10
    ) -> Iterator[np.ndarray]:
        """Extract video frames."""
        video_path = Path(video_path)
        if not skip_validation and not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Get frame dimensions
        width, height = resolution if resolution else cls.get_video_info(video_path, timeout=timeout)

        # Build FFmpeg command
        cmd = FFmpegCommand(
            input_path=video_path,
            fps=fps,
            start_time=start_time,
            end_time=end_time,
            resolution=resolution,
        )

        ffmpeg_cmd = cmd.build_command()
        ffmpeg_cmd.extend([
            "-f", "image2pipe",
            "-pix_fmt", "rgb24",
            "-vcodec", "rawvideo",
            "-"
        ])

        process = None
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )

            error_output = StringIO()
            stderr_thread = Thread(target=stream_reader, args=(process.stderr, error_output, timeout))
            stderr_thread.daemon = True
            stderr_thread.start()

            def read_with_timeout():
                result = process.stdout.read(width * height * 3)
                if not result and process.poll() is not None:
                    return None
                return result

            while True:
                # Use threading to implement timeout for read operations
                read_thread = Thread(target=lambda: read_with_timeout())
                read_thread.daemon = True
                read_thread.start()
                read_thread.join(timeout)
                
                if read_thread.is_alive():
                    raise FFmpegTimeoutError("Frame read operation timed out")
                
                raw_frame = read_with_timeout()
                if not raw_frame:
                    break

                frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))
                yield frame

            process.wait(timeout=timeout)
            if process.returncode != 0:
                raise RuntimeError(f"Error during frame extraction: {error_output.getvalue()}")

        except (subprocess.TimeoutExpired, FFmpegTimeoutError) as e:
            raise FFmpegTimeoutError(f"FFmpeg operation timed out: {str(e)}")
        
        finally:
            if process:
                try:
                    process.stdout.close()
                    process.stderr.close()
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            process.kill()
                except Exception:
                    # Ensure process is killed even if cleanup fails
                    try:
                        process.kill()
                    except Exception:
                        pass