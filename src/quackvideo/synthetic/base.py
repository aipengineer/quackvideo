# src/quackvideo/synthetic/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class SyntheticConfig(BaseModel):
    """Base configuration for synthetic data generation."""

    duration: float = Field(10.0, description="Duration in seconds")
    fps: float = Field(30.0, description="Frames per second")
    width: int = Field(1920, description="Width in pixels")
    height: int = Field(1080, description="Height in pixels")
    output_dir: Path | None = None


class SyntheticGenerator(ABC):
    """Base class for synthetic data generators."""

    def __init__(self, config: SyntheticConfig) -> None:
        """Initialize generator with configuration."""
        self.config = config
        if self.config.output_dir:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate(self, output_path: Path) -> Path:
        """Generate synthetic data and save to file."""
        pass
