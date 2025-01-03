# Quackvideo Examples

This directory contains example scripts demonstrating how to use the Quackvideo library for various video and audio operations.

## Available Examples

- `synthetic_generation.py`: Generate synthetic video and audio patterns for testing
- `frame_extraction.py`: Extract frames from videos with various parameters
- `audio_operations.py`: Handle audio operations (extraction, conversion, mixing)

## Usage

Each script can be run directly with Python using the Fire CLI interface. For example:

```bash
# Generate synthetic patterns
python synthetic_generation.py video video.mp4 --pattern color_bars --duration 10
python synthetic_generation.py audio audio1.flac --pattern sine --frequency 440
python synthetic_generation.py audio audio2.flac --pattern chirp --frequency 440

# Extract frames
python frame_extraction.py extract video.mp4 --fps "1/5"

# Audio operations
python audio_operations.py extract video.mp4
python audio_operations.py mix audio1.flac audio2.flac
```

# Output Structure
Operations create timestamped directories and files following this pattern:

```bash
output/
├── 2025-01-03-143022-video_frames/
│   ├── frame_0001.png
│   ├── frame_0002.png
│   └── ...
├── 2025-01-03-143022-audio.flac
└── .logs/
    └── operation.log
```