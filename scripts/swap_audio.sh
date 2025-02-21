#!/bin/bash
# File: swap_audio.sh
# Usage: ./swap_audio.sh <directory_path>
#
# Description:
#   This script locates all "-mixed.flac" files within the specified directory.
#   For each found audio file, it deduces the corresponding video file by removing
#   the "-mixed" part from the filename. For example:
#     Audio: DJI_20250221185701_0003_D-mixed.flac
#     Video: DJI_20250221185701_0003_D.mp4 (or DJI_20250221185701_0003_D.MP4)
#
#   It then uses ffmpeg to swap the audio track in the video with the new FLAC audio,
#   copying the video stream without alteration.
#
#   The script provides logging and diagnostic messages for robust operation.

# Check if the directory path is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory_path>"
  exit 1
fi

INPUT_DIRECTORY="$1"

# Validate the input directory
if [ ! -d "$INPUT_DIRECTORY" ]; then
  echo "Error: $INPUT_DIRECTORY is not a valid directory."
  exit 1
fi

found_any=false

# Iterate over all "-mixed.flac" files in the directory
for audio_file in "$INPUT_DIRECTORY"/*-mixed.flac; do
  # If no files match the pattern, notify and exit
  if [ ! -e "$audio_file" ]; then
    echo "No '-mixed.flac' files found in $INPUT_DIRECTORY."
    exit 0
  fi

  found_any=true

  # Extract the directory and base name by removing the "-mixed.flac" suffix
  dir=$(dirname "$audio_file")
  base=$(basename "$audio_file" -mixed.flac)

  # Deduce the corresponding video file (checking for .mp4 and .MP4)
  video_file="$dir/$base.mp4"
  if [ ! -f "$video_file" ]; then
    video_file="$dir/$base.MP4"
  fi
  if [ ! -f "$video_file" ]; then
    echo "Warning: No corresponding video file for $audio_file. Skipping..."
    continue
  fi

  # Define the output file name (appending -swapped to the base name)
  output="$dir/${base}-swapped.mp4"

  echo "Processing:"
  echo "  Audio file: $audio_file"
  echo "  Video file: $video_file"
  echo "  Output file: $output"

  # Use ffmpeg to replace the video's audio track:
  # - Copy the video stream without re-encoding (-c:v copy).
  # - Re-encode the new audio track to AAC at 320 kbps (-c:a aac -b:a 320k).
  # - Map the video stream from the original video and the audio from the FLAC file.
  # - Use the shortest stream length to prevent extra duration.
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
  echo "No '-mixed.flac' files found in $INPUT_DIRECTORY."
fi

echo "Audio swapping process complete."
