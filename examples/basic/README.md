## Video Reading Examples

The `video_reading.py` script demonstrates different ways to read and process video files using Quackvideo.

### Basic Usage

Read a video file and display its metadata:

```bash
python video_reading.py basic input_video.mp4
```

Custom Configuration
Read a video with specific parameters (fps, time range, resolution):

```bash
python video_reading.py custom input_video.mp4 \
    --fps 30 \
    --start_time 5.0 \
    --end_time 10.0 \
    --width 1280 \
    --height 720
```

### Keyframe Extraction

Extract and display keyframe timestamps from a video:

```bash
python video_reading.py keyframes input_video.mp4
```

## Video Writing Examples

The `video_writing.py` script demonstrates different ways to write videos using Quackvideo.

### Basic Solid Color Video

Create a video with a solid color:

```bash
python video_writing.py solid output.mp4 \
    --duration 5.0 \
    --fps 30 \
    --width 1280 \
    --height 720 \
    --color "[255,0,0]"  # Red
```

### Streaming Gradient Video

Create a video with a streaming gradient pattern:

```bash
python video_writing.py gradient output.mp4 \
    --duration 5.0 \
    --fps 30 \
    --width 1280 \
    --height 720
```

### High-Quality Video
Create a high-quality video with custom encoding settings:

```bash
python video_writing.py quality output.mp4 \
    --duration 5.0 \
    --fps 30 \
    --width 1920 \
    --height 1080
```

## Video Error Handling Examples

The `error_handling_video.py` script demonstrates how to handle various error scenarios when working with videos.

### Invalid File Handling

Demonstrate handling of non-existent video files:

```bash
python error_handling_video.py invalid_file
```

### Corrupt Video Handling

Demonstrate handling of corrupt video files:

```bash
python error_handling_video.py corrupt
```
### Invalid Timestamp Handling

Demonstrate handling of invalid timestamp configurations:

```bash
python error_handling_video.py timestamps
```

### Resolution Mismatch Handling

Demonstrate handling of resolution mismatches:

```bash
python error_handling_video.py resolution
```

### Timeout Handling

Demonstrate handling of timeout scenarios:

```bash
python error_handling_video.py timeout
```

## Frame Extraction Error Handling Examples

The `error_handling_frames.py` script demonstrates error handling scenarios specific to frame extraction operations.

### Run All Error Scenarios

Test all frame extraction error scenarios:

```bash
python error_handling_frames.py all
```

### Specific Error Scenarios

Test specific error scenarios:

```bash
# Test FPS-related errors
python error_handling_frames.py fps

# Test out-of-range extraction errors
python error_handling_frames.py range

# Test resolution-related errors
python error_handling_frames.py resolution

# Test extraction interruption handling
python error_handling_frames.py interruption

# Test timeout scenarios
python error_handling_frames.py timeout
```

## Frame Processing Examples

The `frame_processing.py` script demonstrates various frame processing and analysis capabilities.

### Scene Change Detection

Detect and save frames where scene changes occur:

```bash
python frame_processing.py scenes input.mp4 scenes.mp4 \
    --threshold 0.3
```

### Black Frame Detection
Analyze video for black frames and report their timestamps:

```bash
python frame_processing.py black input.mp4 \
    --threshold 10.0
```

### Feature Extraction

Extract and analyze frame features:

```bash
python frame_processing.py features input.mp4 \
    --method histogram \
    --output_path features.npy
```

## Frame Extraction Examples

The `frame_extraction_basic.py` script demonstrates various methods of frame extraction.

### Basic Frame Extraction

Extract frames at specified FPS:
```bash
python frame_extraction_basic.py basic \
    input.mp4 ./frames \
    --fps "1/2"  # Extract 1 frame every 2 seconds
```

### Resumable Extraction
Extract frames with resume capability:

```bash
python frame_extraction_basic.py resume \
    input.mp4 ./frames \
    --fps "1"
```

### Direct Frame Extraction
Extract frames directly using FFmpegWrapper:
```bash
python frame_extraction_basic.py direct \
    input.mp4 \
    --start_time 10 \
    --end_time 20 \
    --fps 5
```

### Frame Integrity Verification

Extract and verify frame integrity:

```bash
python frame_extraction_basic.py verify \
    input.mp4 ./frames \
    --fps "1"
```

## Frame Manipulation Examples

The `frame_manipulation.py` script demonstrates various frame manipulation techniques.

### Sequential Frame Manipulation

Apply basic operations to each frame:

```bash
python frame_manipulation.py sequential \
    input.mp4 output.mp4 \
    --operation mirror
```

Available operations: 'mirror', 'rotate', 'invert'

### Sliding Window Manipulation

Process frames using a sliding window approach:
```bash
python frame_manipulation.py window \
    input.mp4 output.mp4 \
    --window_size 5
```

### Feature-Based Manipulation

Manipulate frames based on feature analysis:

```bash
python frame_manipulation.py features \
    input.mp4 output.mp4 \
    --feature_method histogram \
    --threshold 0.5
```

# Jupyter Notebook Examples

The `notebook_examples.ipynb` notebook demonstrates interactive usage of Quackvideo in a Jupyter environment.

### Running the Notebook

1. Ensure Jupyter is installed:

```bash
pip install notebook
```

Start Jupyter:

```bash
jupyter notebook
```

Open notebook_examples.ipynb