#!/bin/bash
# File: swap_audio.sh
# Usage: ./swap_audio.sh <base_directory>
#
# Description:
#   This script locates all "-mixed.flac" files within the "edited" directory of the provided base directory.
#   For each found audio file, it deduces the corresponding video file (located in "raw/video") by removing
#   the "-mixed" part from the filename. It then uses ffmpeg to swap the audio track in the video with the new FLAC audio,
#   copying the video stream without alteration.
#
#   Output video files are stored in the "edited" directory with the naming convention:
#     <base>-swapped.mp4
#
#   Example:
#     Audio: DJI_20250221185701_0003_D-mixed.flac (in "edited")
#     Video: DJI_20250221185701_0003_D.mp4 (or .MP4) in "raw/video"
#     Output: DJI_20250221185701_0003_D-swapped.mp4 in "edited"

# Check if the base directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <base_directory>"
  exit 1
fi

BASE_DIR="$1"
AUDIO_DIR="$BASE_DIR/edited"
VIDEO_DIR="$BASE_DIR/raw/video"

# Validate that the required directories exist
if [ ! -d "$AUDIO_DIR" ]; then
  echo "Error: Audio directory $AUDIO_DIR does not exist."
  exit 1
fi

if [ ! -d "$VIDEO_DIR" ]; then
  echo "Error: Video directory $VIDEO_DIR does not exist."
  exit 1
fi

found_any=false

# Iterate over all "-mixed.flac" files in the AUDIO_DIR
for audio_file in "$AUDIO_DIR"/*-mixed.flac; do
  # If no matching file exists, then notify and exit gracefully
  if [ ! -e "$audio_file" ]; then
    echo "No '-mixed.flac' files found in $AUDIO_DIR."
    exit 0
  fi

  found_any=true

  # Extract the base filename by removing the "-mixed.flac" suffix
  base=$(basename "$audio_file" -mixed.flac)

  # Deduce the corresponding video file in VIDEO_DIR (check for .mp4 and .MP4)
  video_file="$VIDEO_DIR/$base.mp4"
  if [ ! -f "$video_file" ]; then
    video_file="$VIDEO_DIR/$base.MP4"
  fi
  if [ ! -f "$video_file" ]; then
    echo "Warning: No corresponding video file found for $audio_file. Skipping..."
    continue
  fi

  # Define the output file in the AUDIO_DIR (using the defined naming convention)
  output="$AUDIO_DIR/${base}-swapped.mp4"

  echo "Processing:"
  echo "  Audio file: $audio_file"
  echo "  Video file: $video_file"
  echo "  Output file: $output"

  # Swap the audio track using ffmpeg:
  # - Copy the video stream without re-encoding (-c:v copy).
  # - Re-encode the new audio track to AAC at 320 kbps (-c:a aac -b:a 320k).
  # - Map the video stream from the original video and the audio from the FLAC file.
  # - Use the shortest stream length to avoid extra duration.
  ffmpeg -i "$video_file" -i "$audio_file" \
         -c:v copy -c:a aac -b:a 320k \
         -map 0:v:0 -map 1:a:0 \
         -shortest "$output"

  if [ $? -eq 0 ]; then
    echo "Success: Audio replaced in $video_file. Output: $output"
  else
    echo "Error: Failed to replace audio in $video_file using $audio_file."
  fi

  echo "-----------------------------------------"
done

if [ "$found_any" = false ]; then
  echo "No '-mixed.flac' files found in $AUDIO_DIR."
fi

echo "Audio swapping process complete."
