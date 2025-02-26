#!/bin/bash

# Check if the top-level directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <top_level_directory>"
  exit 1
fi

# Set the top-level directory and define subdirectories for video and audio
TOP_DIR="$1"
VIDEO_DIR="$TOP_DIR/raw/video"
AUDIO_DIR="$TOP_DIR/raw/audio"

# Verify that the VIDEO directory exists
if [ ! -d "$VIDEO_DIR" ]; then
  echo "Error: $VIDEO_DIR is not a valid directory."
  exit 1
fi

# Verify that the AUDIO directory exists, create it if it doesn't
if [ ! -d "$AUDIO_DIR" ]; then
  mkdir -p "$AUDIO_DIR"
fi

# Iterate over all .mp4 files in the VIDEO directory
for file in "$VIDEO_DIR"/*.mp4; do
  # Skip if no .mp4 files are found
  if [ ! -e "$file" ]; then
    echo "No .mp4 files found in $VIDEO_DIR."
    exit 0
  fi

  # Extract the base name without the .mp4 extension
  base=$(basename "$file" .mp4)
  
  # Construct the output file path in the AUDIO directory
  output="$AUDIO_DIR/${base}.flac"

  # Run ffmpeg command to extract audio from the video file
  ffmpeg -i "$file" -vn -acodec flac "$output"

  echo "Processed: $file -> $output"
done

echo "Audio extraction complete."
