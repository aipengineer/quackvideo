# src/quackvideo/core/operations/base.py
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar
from urllib.parse import quote

import ffmpeg
from pydantic import BaseModel
from tqdm import tqdm

from ..operations.models import (
    FFmpegBaseConfig,
    MediaType,
    OutputMetadata,
    ProcessingMetadata,
)

T = TypeVar("T", bound=FFmpegBaseConfig)
R = TypeVar("R", bound=BaseModel)  # For operation results


class FFmpegOperationError(Exception):
    """Base exception for FFmpeg operation errors."""

    def __init__(self, message: str, ffmpeg_error: str | None = None):
        super().__init__(message)
        self.ffmpeg_error = ffmpeg_error


class FFmpegTimeoutError(FFmpegOperationError):
    """Raised when an FFmpeg operation times out."""

    pass


class FFmpegOperation(ABC, Generic[T, R]):
    """Base class for FFmpeg operations."""

    def __init__(
        self,
        config: T,
        episode_dir: Path,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialize FFmpeg operation.

        Args:
            config: Operation configuration
            episode_dir: Directory for episode files
            logger: Optional logger instance
        """
        self.config = config
        self.episode_dir = Path(episode_dir)
        self.logger = logger or self._setup_logger()

        # Ensure episode directory exists
        self.episode_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the operation."""
        logger = logging.getLogger(f"ffmpeg_operation.{self.__class__.__name__}")
        logger.setLevel(logging.INFO)

        # Create logs directory
        log_dir = self.episode_dir / ".logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create file handler
        handler = logging.FileHandler(log_dir / f"{self.__class__.__name__}.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _create_metadata_file(self, metadata: ProcessingMetadata) -> None:
        """Create or update metadata file for the operation."""
        metadata_file = self.episode_dir / ".metadata.json"
        metadata_file.write_text(metadata.model_dump_json(indent=2))

    @abstractmethod
    def _build_ffmpeg_stream(self, input_path: Path) -> ffmpeg.Stream:
        """
        Build FFmpeg stream for the operation.

        Must be implemented by subclasses to define specific FFmpeg operations.
        """
        pass

    @abstractmethod
    def _process_output(self, result: Any, metadata: ProcessingMetadata) -> R:
        """
        Process operation output.

        Must be implemented by subclasses to handle operation-specific results.
        """
        pass

    def _validate_input_file(self, input_path: Path, media_type: MediaType) -> None:
        """Validate input file exists and has correct format."""
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if (
            input_path.suffix.lower()
            not in self.config.compatible_formats[media_type.value]
        ):
            raise ValueError(
                f"Unsupported file format for {media_type.value}: {input_path.suffix}"
            )

    def _get_output_path(self, input_path: Path, operation_type: str) -> Path:
        """Generate output path with timestamp."""
        timestamp = time.strftime("%Y-%m-%d-%H%M%S")
        safe_name = quote(input_path.stem)
        return (
            self.episode_dir
            / f"{timestamp}-{safe_name}-{operation_type}{input_path.suffix}"
        )

    def execute_with_retry(
        self,
        input_path: Path,
        media_type: MediaType,
        operation_type: str,
        progress_desc: str = "Processing",
    ) -> R:
        """
        Execute FFmpeg operation with retry logic and progress tracking.

        Args:
            input_path: Path to input file
            media_type: Type of media being processed
            operation_type: Type of operation being performed
            progress_desc: Description for progress bar

        Returns:
            Operation result of type R

        Raises:
            FFmpegOperationError: If operation fails after all retries
        """
        self._validate_input_file(input_path, media_type)

        metadata = ProcessingMetadata()
        self._create_metadata_file(metadata)

        output_metadata = OutputMetadata(
            original_filename=input_path.name,
            operation_type=operation_type,
            output_path=self._get_output_path(input_path, operation_type),
        )

        last_error = None
        for attempt in range(self.config.retries):
            try:
                # Build and run FFmpeg stream
                stream = self._build_ffmpeg_stream(input_path)

                # Create progress bar
                with tqdm(desc=progress_desc) as pbar:

                    def on_progress(progress: dict[str, Any]) -> None:
                        if "total_size" in progress and "size" in progress:
                            pbar.total = progress["total_size"]
                            pbar.n = progress["size"]
                            pbar.refresh()

                    # Run FFmpeg operation
                    result = ffmpeg.run(
                        stream,
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                    )

                # Process and return results
                metadata.status = "completed"
                self._create_metadata_file(metadata)
                return self._process_output(result, metadata)

            except ffmpeg.Error as e:
                last_error = FFmpegOperationError(
                    f"FFmpeg operation failed on attempt {attempt + 1}/{self.config.retries}",
                    ffmpeg_error=e.stderr.decode() if e.stderr else None,
                )
                self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}")

                if attempt < self.config.retries - 1:
                    time.sleep(self.config.retry_delay)
                continue

            except Exception as e:
                last_error = FFmpegOperationError(str(e))
                self.logger.error(f"Unexpected error: {e}")
                break

        metadata.status = "failed"
        self._create_metadata_file(metadata)
        raise last_error or FFmpegOperationError(
            "Operation failed with no specific error"
        )

    def cleanup(self) -> None:
        """Clean up any temporary files or resources."""
        pass

    def __enter__(self) -> FFmpegOperation[T, R]:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()
